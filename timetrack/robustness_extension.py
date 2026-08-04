"""Robustness extension config validation and claim helpers."""

from __future__ import annotations

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
)


def load_robustness_config(path: Path | str | None = None) -> dict[str, Any]:
    path = Path(path) if path else ROOT / "configs" / "final_robustness_extension.yaml"
    return yaml.safe_load(path.read_text())


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
    if grid != EXPECTED_ALPHA_GRID:
        errs.append(f"ewma_alpha_grid must be {EXPECTED_ALPHA_GRID}")
    if cfg.get("freeze_tag") != "final-robustness-extension-freeze-v1":
        errs.append("freeze_tag must be final-robustness-extension-freeze-v1")
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
    dlin = packs.get("dlinear_seed_robustness") or {}
    if dlin and list(dlin.get("seeds") or []) != [1, 2]:
        errs.append("dlinear_seed_robustness seeds must be [1, 2] only")
    if require_frozen:
        for key in ("implementation_commit", "freeze_commit"):
            val = str(cfg.get(key) or "")
            if not val or val.upper() == "PENDING":
                errs.append(f"{key} still PENDING")
            if len(val) != 40:
                errs.append(f"{key} must be 40-char commit")
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
        # mixed improvement and degradation among non-neutral seeds
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
