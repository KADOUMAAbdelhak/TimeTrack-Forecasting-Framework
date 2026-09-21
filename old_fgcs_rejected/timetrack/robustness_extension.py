"""Robustness extension config validation and claim helpers."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_ALPHA_GRID = [0.05, 0.10, 0.20, 0.30, 0.50, 0.70, 0.90]
PROTECTED_TAGS = (
    "experiment-freeze-v2",
    "final-analysis-freeze-v1",
    "final-peak-analysis-freeze-v1",
    "final-reporting-freeze-v1",
    "final-robustness-extension-freeze-v1",
)

# Provenance fields filled at/after freeze tagging. Excluded from the scientific
# config hash so implementation and provenance commits share one hash, and so
# runtime manifest fields cannot silently diverge.
SCIENTIFIC_CONFIG_EXCLUDE_TOP = frozenset(
    {
        "implementation_commit",
        "freeze_commit",
        "freeze_tag_commit",
        "frozen_scientific_config_hash",  # self-reference; verified separately
    }
)

# Documented hashing boundary (also in FINAL_ROBUSTNESS_EXTENSION_PROTOCOL.md):
# scientific_config_hash covers dataset/context/folds/grids/hparams/pack matrix/
# wall-clock limits/artifact roots/seed reuse maps. It excludes git commit SHAs
# that are stamped after the scientific content is locked.


def load_robustness_config(path: Path | str | None = None) -> dict[str, Any]:
    path = Path(path) if path else ROOT / "configs" / "final_robustness_extension.yaml"
    return yaml.safe_load(path.read_text())


def scientific_config_view(cfg: dict[str, Any]) -> dict[str, Any]:
    """Return the frozen scientific payload used for config hashing."""
    view = copy.deepcopy(cfg)
    for k in SCIENTIFIC_CONFIG_EXCLUDE_TOP:
        view.pop(k, None)
    return view


def scientific_config_hash(cfg: dict[str, Any]) -> str:
    payload = scientific_config_view(cfg)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]


def config_hash(cfg: dict[str, Any]) -> str:
    """Alias used by runners/manifests: always the scientific hash."""
    return scientific_config_hash(cfg)


def validate_robustness_config(cfg: dict[str, Any], *, require_frozen: bool = False) -> list[str]:
    errs: list[str] = []
    if cfg.get("source_experiment_freeze_tag") != "experiment-freeze-v2":
        errs.append("source_experiment_freeze_tag must be experiment-freeze-v2")
    if cfg.get("dataset_fingerprint") != "bf06dc0e7fe6ff5e":
        errs.append("dataset_fingerprint mismatch")
    if int(cfg.get("context", -1)) != 32:
        errs.append("context must be 32")
    if int(cfg.get("n_outer_folds", -1)) != 3:
        errs.append("n_outer_folds must be 3")
    grid = [float(x) for x in (cfg.get("ewma_alpha_grid") or [])]
    if len(grid) != len(EXPECTED_ALPHA_GRID) or any(
        abs(a - b) > 1e-12 for a, b in zip(grid, EXPECTED_ALPHA_GRID)
    ):
        errs.append(f"ewma_alpha_grid must be {EXPECTED_ALPHA_GRID}")
    if cfg.get("freeze_tag") != "final-robustness-extension-freeze-v2":
        errs.append("freeze_tag must be final-robustness-extension-freeze-v2")
    if int(cfg.get("lightgbm_n_jobs", 0)) != -1:
        errs.append("lightgbm_n_jobs must be -1 to match experiment-freeze-v2 seed-0")
    packs = {p["id"]: p for p in (cfg.get("packs") or [])}
    for pid in (
        "ewma_baselines",
        "lightgbm_seed_robustness",
        "dlinear_seed_robustness",
        "robustness_statistics",
    ):
        if pid not in packs:
            errs.append(f"missing pack {pid}")
    ewma = packs.get("ewma_baselines") or {}
    if ewma and int(ewma.get("estimated_base_fits", 0)) != 192:
        errs.append("ewma_baselines estimated_base_fits must be 192")
    lgbm = packs.get("lightgbm_seed_robustness") or {}
    if lgbm and "disk_ud" in (lgbm.get("hierarchies") or []):
        errs.append("lightgbm_seed_robustness must not include disk_ud")
    if lgbm and list(lgbm.get("seeds") or []) != [1, 2]:
        errs.append("lightgbm_seed_robustness seeds must be [1, 2] only")
    if lgbm:
        if int(lgbm.get("stop_launching_new_runs_minutes", -1)) != 27:
            errs.append("lightgbm_seed_robustness stop_launching_new_runs_minutes must be 27")
        if int(lgbm.get("hard_wall_clock_minutes", -1)) != 30:
            errs.append("lightgbm_seed_robustness hard_wall_clock_minutes must be 30")
    dlin = packs.get("dlinear_seed_robustness") or {}
    if dlin and list(dlin.get("seeds") or []) != [1, 2]:
        errs.append("dlinear_seed_robustness seeds must be [1, 2] only")

    computed = scientific_config_hash(cfg)
    frozen = cfg.get("frozen_scientific_config_hash")
    if require_frozen:
        for key in ("implementation_commit", "freeze_commit"):
            val = str(cfg.get(key) or "")
            if not val or val.upper() == "PENDING":
                errs.append(f"{key} still PENDING")
            elif len(val) != 40:
                errs.append(f"{key} must be 40-char commit")
        if not frozen or str(frozen).upper() == "PENDING":
            errs.append("frozen_scientific_config_hash still PENDING")
        elif str(frozen) != computed:
            errs.append(
                f"frozen_scientific_config_hash {frozen} != computed scientific hash {computed}"
            )
    elif frozen and str(frozen).upper() != "PENDING" and str(frozen) != computed:
        errs.append(
            f"frozen_scientific_config_hash {frozen} != computed scientific hash {computed}"
        )
    return errs


def assert_config_hashes_agree(
    cfg: dict[str, Any],
    *,
    executed_hash: str | None = None,
    manifest_hash: str | None = None,
) -> list[str]:
    """Fail when frozen / validated / executed / manifest scientific hashes disagree."""
    errs: list[str] = []
    computed = scientific_config_hash(cfg)
    frozen = cfg.get("frozen_scientific_config_hash")
    if frozen and str(frozen).upper() != "PENDING" and str(frozen) != computed:
        errs.append(f"frozen!=validated: {frozen} vs {computed}")
    if executed_hash is not None and executed_hash != computed:
        errs.append(f"executed!=validated: {executed_hash} vs {computed}")
    if manifest_hash is not None and manifest_hash != computed:
        errs.append(f"manifest!=validated: {manifest_hash} vs {computed}")
    if (
        frozen
        and str(frozen).upper() != "PENDING"
        and executed_hash is not None
        and manifest_hash is not None
        and not (str(frozen) == computed == executed_hash == manifest_hash)
    ):
        errs.append("frozen/validated/executed/manifest scientific hashes must all agree")
    return errs


def seed_claim_supported(
    relative_effects: list[float],
    *,
    neutral_band: float = 0.02,
) -> bool:
    """Primary stochastic claim rule across three seeds.

    Supported if all three share direction, or two support and the third is
    within ±neutral_band of zero (accuracy-neutral), and none show substantial
    opposite behavior.
    """
    if len(relative_effects) != 3:
        return False
    signs = []
    for e in relative_effects:
        if abs(e) <= neutral_band:
            signs.append(0)
        else:
            signs.append(1 if e < 0 else -1)  # negative rel MAE = improvement
    if any(s == -1 for s in signs) and any(s == 1 for s in signs):
        non_neutral = [s for s in signs if s != 0]
        if len(set(non_neutral)) > 1:
            return False
    supporting = sum(1 for s in signs if s == 1)
    neutral = sum(1 for s in signs if s == 0)
    opposing = sum(1 for s in signs if s == -1)
    if opposing > 0 and supporting == 0:
        return False
    if supporting == 3:
        return True
    if supporting == 2 and neutral == 1:
        return True
    if supporting == 2 and opposing == 1:
        return False
    if supporting == 1 and neutral == 2:
        return False
    return supporting >= 2 and opposing == 0


def lightgbm_execution_fingerprint(seed: int, *, family: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Exact LightGBM constructor fields for seed comparability audits."""
    key = "lightgbm_cpu" if family == "cpu" else "lightgbm_memory"
    params = cfg[key]
    return {
        "n_estimators": int(params["n_estimators"]),
        "learning_rate": float(params["learning_rate"]),
        "num_leaves": int(params["num_leaves"]),
        "max_depth": -1,
        "random_state": int(seed),
        "n_jobs": int(cfg.get("lightgbm_n_jobs", -1)),
        "verbosity": -1,
        # Defaults from LightGBM sklearn 4.7 (not explicitly passed; recorded for audit)
        "subsample_default": 1.0,
        "subsample_freq_default": 0,
        "colsample_bytree_default": 1.0,
        "boosting_type_default": "gbdt",
        "explicit_subsample_passed": False,
        "explicit_feature_fraction_passed": False,
    }
