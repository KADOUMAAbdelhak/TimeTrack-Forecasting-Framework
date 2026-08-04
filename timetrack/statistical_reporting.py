"""Frozen final-analysis statistical reporting for experiment-freeze-v2 predictions.

Consumes stored outer-evaluation NPZ predictions only. Never trains or retunes models.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from models.hybrid.reconciliation import (
    coherence_error,
    core_weighted_cpu_hierarchy,
    disk_hierarchy,
    estimate_residual_covariance,
    machine_core_counts,
    memory_hierarchy,
    reconcile,
)
from timetrack.stats_bootstrap import (
    holm_adjust_with_ranks,
    paired_moving_block_bootstrap_effects,
    select_block_length,
)

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_TRAINING_IMPORTS = (
    "lightgbm",
    "torch",
    "sklearn.linear_model",
    "models.baselines",
    "models.dlinear",
)


class ProvenanceError(ValueError):
    """Raised when source prediction provenance fails frozen checks."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def config_hash(cfg: dict[str, Any]) -> str:
    blob = yaml.safe_dump(cfg, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def effect_class(rel: float) -> str:
    if rel <= -0.05:
        return "substantial_improvement"
    if rel <= -0.02:
        return "modest_improvement"
    if rel < 0.02:
        return "accuracy_neutral"
    if rel < 0.05:
        return "modest_degradation"
    return "substantial_degradation"


def fold_consistency_label(rels: list[float]) -> str:
    """Classify fold-level relative effects (negative = improvement)."""
    if not rels:
        return "mixed"
    if any(r >= 0.20 for r in rels):
        return "unstable"
    improve = [r < 0 for r in rels]
    degrade = [r > 0 for r in rels]
    if all(degrade):
        return "consistently_harmful"
    if all(improve) and all(r > -1 or True for r in rels) and max(rels) <= 0.02:
        # all improve and no fold worsens by more than 2% (worsen would be positive)
        return "strongly_consistent"
    if sum(improve) >= 2 and max(rels) <= 0.05:
        return "directionally_consistent"
    if any(improve) and any(degrade):
        return "mixed"
    return "mixed"


def tradeoff_class(
    top_rel: float,
    macro_rel: float,
    worst_rel: float,
    coherence_after: float,
    *,
    coherence_before: float | None = None,
) -> str:
    """Freeze trade-off labels from top/bottom/coherence changes."""
    coh_ok = float(coherence_after) < 1e-6
    if coherence_before is not None:
        coh_ok = coh_ok and (float(coherence_after) <= float(coherence_before) + 1e-12)
    top_imp = top_rel < -0.02
    top_neu = abs(top_rel) <= 0.02
    top_deg = top_rel > 0.02
    bot_ok = macro_rel <= 0.02
    bot_mat_deg = macro_rel > 0.02 or worst_rel > 0.02
    bot_costly = macro_rel > 0.05
    catastrophic_bottom = macro_rel >= 0.20 or worst_rel >= 0.20
    if top_deg or bot_costly:
        return "accuracy_costly_coherence"
    if top_imp and bot_ok and coh_ok:
        return "pareto_improvement"
    if top_imp and bot_mat_deg and coh_ok:
        return "aggregate_focused_improvement"
    if top_neu and coh_ok and not catastrophic_bottom and not bot_costly:
        return "coherence_only"
    if top_imp and coh_ok:
        return "aggregate_focused_improvement"
    return "accuracy_costly_coherence"


def classify_claim_support(
    *,
    n_support: int,
    n_uncertain: int,
    n_contradict: int,
    n_total: int,
    horizon_ok: bool,
    folds_ok: bool,
    has_substantial_contradiction: bool,
) -> str:
    if n_total <= 0:
        return "unsupported"
    if has_substantial_contradiction or (n_contradict > n_support and n_contradict >= max(1, n_total // 2)):
        if n_contradict > n_support:
            return "contradicted"
    frac_sup = n_support / n_total
    if (
        frac_sup >= 0.80
        and not has_substantial_contradiction
        and horizon_ok
        and folds_ok
        and n_contradict == 0
    ):
        return "supported"
    if n_support > (n_uncertain + n_contradict) or frac_sup > 0.5:
        return "partially_supported"
    if n_contradict > n_support:
        return "contradicted"
    return "unsupported"


def load_statistics_config(path: Path | None = None) -> dict[str, Any]:
    path = path or (ROOT / "configs" / "final_statistics.yaml")
    return yaml.safe_load(path.read_text())


def validate_statistics_config(cfg: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    required = {
        "analysis_freeze_tag",
        "source_experiment_freeze_tag",
        "source_frozen_implementation_commit",
        "dataset_fingerprint",
        "bootstrap",
        "holm_families",
        "claim_definitions",
        "source_packs",
        "effect_classification",
        "fold_consistency",
        "tradeoff_classification",
        "alpha",
    }
    missing = required - set(cfg)
    if missing:
        errs.append(f"missing keys: {sorted(missing)}")
    boot = cfg.get("bootstrap") or {}
    for k in ("method", "n_boot", "seed", "acf_threshold", "lower", "upper"):
        if k not in boot:
            errs.append(f"bootstrap missing {k}")
    if int(boot.get("n_boot", 0)) != 5000:
        errs.append("bootstrap.n_boot must be 5000 for frozen protocol")
    if int(boot.get("seed", -1)) != 0:
        errs.append("bootstrap.seed must be 0")
    if boot.get("method") != "paired_moving_block":
        errs.append("bootstrap.method must be paired_moving_block")
    families = list(cfg.get("holm_families") or [])
    expected = {
        "memory_ridge",
        "memory_dlinear",
        "memory_lightgbm",
        "cpu_ridge",
        "cpu_dlinear",
        "cpu_lightgbm",
        "disk_ridge",
        "disk_lightgbm",
    }
    if set(families) != expected:
        errs.append(f"holm_families must equal {sorted(expected)}, got {families}")
    if cfg.get("source_experiment_freeze_tag") != "experiment-freeze-v2":
        errs.append("source_experiment_freeze_tag must be experiment-freeze-v2")
    return errs


def _git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _load_manifest(pack_dir: Path) -> dict[str, Any]:
    path = pack_dir / "MANIFEST.json"
    if not path.exists():
        raise ProvenanceError(f"missing MANIFEST.json: {pack_dir}")
    return json.loads(path.read_text())


def verify_source_pack_manifest(
    man: dict[str, Any],
    *,
    stats_cfg: dict[str, Any],
    pack_id: str,
) -> None:
    checks = {
        "freeze_tag": stats_cfg["source_experiment_freeze_tag"],
        "frozen_implementation_commit": stats_cfg["source_frozen_implementation_commit"],
        "dataset_fingerprint": stats_cfg["dataset_fingerprint"],
        "experiment_stage": "final",
        "eligible_for_final_claims": True,
        "evaluation_role": "outer_evaluation",
    }
    # accept freeze_commit / implementation_commit aliases
    impl = man.get("frozen_implementation_commit") or man.get("implementation_commit") or man.get("freeze_commit")
    if impl != stats_cfg["source_frozen_implementation_commit"]:
        raise ProvenanceError(
            f"{pack_id}: frozen implementation mismatch: {impl} != {stats_cfg['source_frozen_implementation_commit']}"
        )
    if man.get("freeze_tag") != checks["freeze_tag"]:
        raise ProvenanceError(f"{pack_id}: freeze_tag={man.get('freeze_tag')}")
    if man.get("dataset_fingerprint") != checks["dataset_fingerprint"]:
        raise ProvenanceError(f"{pack_id}: dataset_fingerprint mismatch")
    if man.get("experiment_stage") != "final":
        raise ProvenanceError(f"{pack_id}: experiment_stage={man.get('experiment_stage')}")
    if not bool(man.get("eligible_for_final_claims")):
        raise ProvenanceError(f"{pack_id}: not eligible_for_final_claims")
    if man.get("evaluation_role") != "outer_evaluation":
        raise ProvenanceError(f"{pack_id}: evaluation_role={man.get('evaluation_role')}")
    cfg_hash = man.get("config_hash")
    expected_cfg = stats_cfg.get("source_config_hash")
    if expected_cfg and cfg_hash != expected_cfg:
        raise ProvenanceError(f"{pack_id}: config_hash {cfg_hash} != {expected_cfg}")
    # refuse development/pilot artifact roots
    out = str(man.get("output_dir") or "")
    if "results/development" in out or "results/pilot" in out or "/pilot/" in out:
        raise ProvenanceError(f"{pack_id}: development/pilot path refused: {out}")


@dataclass(frozen=True)
class HierarchySpec:
    name: str
    pack_ids: tuple[str, ...]
    hierarchy: Any
    scale_top: float
    models: tuple[str, ...]
    methods: tuple[str, ...]
    horizons: tuple[int, ...]
    unit: str


def _hierarchy_specs(artifact_root: Path) -> dict[str, HierarchySpec]:
    cores = float(sum(machine_core_counts().values()))
    return {
        "memory_um": HierarchySpec(
            "memory_um",
            ("memory_classical", "memory_dlinear"),
            memory_hierarchy(),
            1.0,
            ("persistence", "ridge", "lightgbm", "dlinear"),
            ("bottom_up", "wls", "mint"),
            (1, 8, 16),
            "memory_level",
        ),
        "cpu_core_weighted": HierarchySpec(
            "cpu_core_weighted",
            ("cpu_classical", "cpu_dlinear"),
            core_weighted_cpu_hierarchy(),
            cores,
            ("persistence", "ridge", "lightgbm", "dlinear"),
            ("bottom_up", "wls", "mint"),
            (1, 8, 16),
            "cpu_weighted_mean_pct",
        ),
        "disk_ud": HierarchySpec(
            "disk_ud",
            ("disk_boundary",),
            disk_hierarchy(),
            1.0,
            ("persistence", "ridge", "lightgbm"),
            ("bottom_up", "top_down", "wls", "mint"),
            (1, 8),
            "disk_level",
        ),
    }


def _pack_dir(artifact_root: Path, pack_id: str, pack_dirs: dict[str, str]) -> Path:
    return artifact_root / pack_dirs[pack_id]


def load_base_npz(pack_dirs: list[Path], model: str, fold: int, horizon: int) -> tuple[Any, Path]:
    for p in pack_dirs:
        pred = p / "metrics" / "predictions"
        if not pred.exists():
            continue
        matches = sorted(pred.glob(f"base__*__f{fold}__h{horizon}__{model}__s0.npz"))
        if matches:
            return np.load(matches[0]), matches[0]
    raise ProvenanceError(f"missing NPZ for model={model} fold={fold} horizon={horizon} in {pack_dirs}")


def reconcile_once(h, data, method: str) -> dict[str, np.ndarray]:
    yb, pb = data["yb_test"], data["pb_test"]
    yt, pt = data["yt_test"], data["pt_test"]
    yb_val, pb_val = data["yb_val"], data["pb_val"]
    yt_val, pt_val = data["yt_val"], data["pt_val"]
    y_full = np.concatenate([yb_val, yt_val.reshape(-1, 1)], 1)
    p_full = np.concatenate([pb_val, pt_val.reshape(-1, 1)], 1)
    cov = estimate_residual_covariance(y_full, p_full, shrink_diag=0.1)
    series_var = np.maximum(np.diag(cov), 1e-12)
    out = reconcile(
        method,
        h,
        pb,
        pt,
        series_var=series_var if method == "wls" else None,
        residual_cov=cov if method == "mint" else None,
        nonnegative=False,
    )
    return {
        "yt": np.asarray(yt, dtype=float).reshape(-1),
        "pt_ind": np.asarray(pt, dtype=float).reshape(-1),
        "pt_rec": np.asarray(out["top"], dtype=float).reshape(-1),
        "yb": np.asarray(yb, dtype=float),
        "pb_ind": np.asarray(pb, dtype=float),
        "pb_rec": np.asarray(out["bottom"], dtype=float),
        "coherence_before": float(coherence_error(pb, pt)),
        "coherence_after": float(coherence_error(out["bottom"], out["top"])),
    }


def _series_mae(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(y, dtype=float).reshape(-1) - np.asarray(p, dtype=float).reshape(-1))))


def _bottom_stats(yb: np.ndarray, pb_a: np.ndarray, pb_b: np.ndarray, weights: np.ndarray | None) -> dict[str, float]:
    # yb, pb: (n, n_bottom)
    ea = np.abs(yb - pb_a)
    eb = np.abs(yb - pb_b)
    mae_a = ea.mean(axis=0)
    mae_b = eb.mean(axis=0)
    macro_a = float(np.mean(mae_a))
    macro_b = float(np.mean(mae_b))
    if weights is None:
        w = np.ones(mae_a.shape[0], dtype=float)
    else:
        w = np.asarray(weights, dtype=float)
        w = w / w.sum()
    w_a = float(np.dot(mae_a, w))
    w_b = float(np.dot(mae_b, w))
    worst_a = float(np.max(mae_a))
    worst_b = float(np.max(mae_b))
    improved = int(np.sum(mae_b < mae_a - 1e-15))
    degraded = int(np.sum(mae_b > mae_a + 1e-15))
    return {
        "macro_independent": macro_a,
        "macro_reconciled": macro_b,
        "macro_rel": (macro_b - macro_a) / max(macro_a, 1e-18),
        "weighted_independent": w_a,
        "weighted_reconciled": w_b,
        "weighted_rel": (w_b - w_a) / max(w_a, 1e-18),
        "worst_independent": worst_a,
        "worst_reconciled": worst_b,
        "worst_rel": (worst_b - worst_a) / max(worst_a, 1e-18),
        "machines_improved": improved,
        "machines_degraded": degraded,
    }


def correction_family(hierarchy: str, model: str) -> str | None:
    """Map to frozen Holm family; persistence returns None (descriptive only)."""
    if model == "persistence":
        return None
    prefix = {"memory_um": "memory", "cpu_core_weighted": "cpu", "disk_ud": "disk"}[hierarchy]
    return f"{prefix}_{model}"


def run_final_statistics(
    *,
    stats_cfg: dict[str, Any],
    source_cfg: dict[str, Any],
    output_dir: Path,
    smoke: bool = False,
    smoke_pred_root: Path | None = None,
) -> dict[str, Any]:
    """Execute frozen timestamp-level statistical analysis."""
    errs = validate_statistics_config(stats_cfg)
    if errs and not smoke:
        raise ValueError("invalid final_statistics config: " + "; ".join(errs))

    t0 = time.perf_counter()
    cpu0 = time.process_time()
    start_iso = datetime.now(timezone.utc).isoformat()

    artifact_root = ROOT / (source_cfg.get("artifact_root") or "results/final/packs")
    pack_dirs_map = {p["id"]: p["pack_dir"] for p in source_cfg["packs"]}
    source_pack_ids = list(stats_cfg["source_packs"])
    boot = stats_cfg["bootstrap"]
    n_boot = int(boot["n_boot"]) if not smoke else int(boot.get("smoke_n_boot", 50))
    seed = int(boot["seed"])
    acf = float(boot["acf_threshold"])
    b_lo = int(boot["lower"])
    b_hi = int(boot["upper"])
    context = int(stats_cfg.get("context", source_cfg.get("context", 32)))
    alpha = float(stats_cfg.get("alpha", 0.05))

    # Provenance + hashes of source predictions
    source_hash_rows = []
    source_pack_hashes = {}
    pred_paths_before: dict[str, str] = {}
    for pid in source_pack_ids:
        pdir = artifact_root / pack_dirs_map[pid] if not smoke else (smoke_pred_root or artifact_root) / pack_dirs_map.get(pid, pid)
        if smoke and smoke_pred_root is not None:
            pdir = smoke_pred_root / pid
        man = _load_manifest(pdir) if (pdir / "MANIFEST.json").exists() else {}
        if not smoke:
            verify_source_pack_manifest(man, stats_cfg=stats_cfg, pack_id=pid)
            source_pack_hashes[pid] = man.get("pack_hash")
            if man.get("config_hash") and stats_cfg.get("source_config_hash"):
                if man["config_hash"] != stats_cfg["source_config_hash"]:
                    raise ProvenanceError(f"{pid} config_hash mismatch")
        pred_dir = pdir / "metrics" / "predictions"
        if not pred_dir.exists():
            raise ProvenanceError(f"{pid}: missing predictions dir")
        for npz in sorted(pred_dir.glob("*.npz")):
            digest = sha256_file(npz)
            pred_paths_before[str(npz.resolve())] = digest
            source_hash_rows.append(
                {
                    "source_pack": pid,
                    "path": str(npz.relative_to(ROOT)) if str(npz).startswith(str(ROOT)) else str(npz),
                    "sha256": digest,
                    "bytes": npz.stat().st_size,
                }
            )

    specs = _hierarchy_specs(artifact_root)
    if smoke and smoke_pred_root is not None:
        # rewrite pack paths for smoke
        pass

    def paths_for(spec: HierarchySpec) -> list[Path]:
        if smoke and smoke_pred_root is not None:
            return [smoke_pred_root / pid for pid in spec.pack_ids]
        return [artifact_root / pack_dirs_map[pid] for pid in spec.pack_ids]

    boot_rows: list[dict[str, Any]] = []
    rel_rows: list[dict[str, Any]] = []
    claim_a_rows: list[dict[str, Any]] = []
    seen_keys: set[tuple] = set()
    cores_w = np.array([machine_core_counts()[m] for m in machine_core_counts()], dtype=float)

    for hier_name, spec in specs.items():
        h = spec.hierarchy
        scale = float(spec.scale_top)
        weights = cores_w if hier_name == "cpu_core_weighted" else None
        for model in spec.models:
            for horizon in spec.horizons:
                for fold in (0, 1, 2):
                    try:
                        data, npz_path = load_base_npz(paths_for(spec), model, fold, horizon)
                    except ProvenanceError:
                        if smoke:
                            continue
                        if model == "dlinear" and hier_name == "disk_ud":
                            continue
                        raise
                    key = (hier_name, model, horizon, fold)
                    if key in seen_keys:
                        raise ProvenanceError(f"duplicate prediction key {key}")
                    seen_keys.add(key)

                    resid = np.asarray(data["yt_val"], dtype=float) - np.asarray(data["pt_val"], dtype=float)
                    bl_info = select_block_length(
                        resid,
                        forecast_horizon=int(horizon),
                        context_length=context,
                        acf_threshold=acf,
                        lower=b_lo,
                        upper=b_hi,
                    )
                    block_length = int(bl_info["block_length"])

                    ind = reconcile_once(h, data, "independent")
                    yt = ind["yt"] / scale
                    pt_ind = ind["pt_ind"] / scale

                    for method in spec.methods:
                        rec = reconcile_once(h, data, method)
                        pt_rec = rec["pt_rec"] / scale
                        n = min(len(yt), len(pt_ind), len(pt_rec))
                        if n <= 0:
                            raise ProvenanceError(f"empty series {key} {method}")
                        # identical timestamps: require equal lengths after shared trim
                        if not (len(ind["yt"]) == len(rec["yt"]) == len(data["yt_test"])):
                            raise ProvenanceError(f"timestamp length mismatch {key} {method}")
                        e_ind = np.abs(yt[:n] - pt_ind[:n])
                        e_rec = np.abs(yt[:n] - pt_rec[:n])
                        effects = paired_moving_block_bootstrap_effects(
                            e_rec,
                            e_ind,
                            block_size=block_length,
                            n_boot=n_boot,
                            seed=seed,
                        )
                        bot = _bottom_stats(ind["yb"][:n], ind["pb_ind"][:n], rec["pb_rec"][:n], weights)
                        top_rel = effects["relative_mae_diff"]
                        trade = tradeoff_class(
                            float(top_rel),
                            float(bot["macro_rel"]),
                            float(bot["worst_rel"]),
                            float(rec["coherence_after"]),
                            coherence_before=float(ind["coherence_before"]),
                        )
                        fam = correction_family(hier_name, model)
                        row = {
                            "hierarchy": hier_name,
                            "unit": spec.unit,
                            "base_model": model,
                            "horizon": int(horizon),
                            "fold": int(fold),
                            "method_a": "independent",
                            "method_b": method,
                            "npz_path": str(npz_path),
                            "correction_family": fam or f"{hier_name.split('_')[0]}_persistence_descriptive",
                            "in_holm_family": fam is not None,
                            "effect_class": effect_class(float(top_rel)),
                            "tradeoff_class": trade,
                            "coherence_before": float(ind["coherence_before"]),
                            "coherence_after": float(rec["coherence_after"]),
                            **effects,
                            **bot,
                        }
                        # rename CI fields for absolute table clarity
                        row["ci_low"] = row.pop("abs_ci_low")
                        row["ci_high"] = row.pop("abs_ci_high")
                        boot_rows.append(row)
                        rel_rows.append(
                            {
                                "hierarchy": hier_name,
                                "base_model": model,
                                "horizon": int(horizon),
                                "fold": int(fold),
                                "method_b": method,
                                "relative_mae_diff": effects["relative_mae_diff"],
                                "rel_ci_low": effects["rel_ci_low"],
                                "rel_ci_high": effects["rel_ci_high"],
                                "rel_ci_crosses_zero": effects["rel_ci_crosses_zero"],
                                "prob_improvement": effects["prob_improvement"],
                                "p_value_raw": effects["p_value_raw"],
                                "n_boot": effects["n_boot"],
                                "block_length": effects["block_length"],
                                "n_paired": effects["n_paired"],
                            }
                        )

                    # Claim A: CPU lightgbm vs persistence independent
                    if hier_name == "cpu_core_weighted" and model == "lightgbm":
                        data_p, path_p = load_base_npz(paths_for(spec), "persistence", fold, horizon)
                        ind_p = reconcile_once(h, data_p, "independent")
                        yt_p = ind_p["yt"] / scale
                        pt_p = ind_p["pt_ind"] / scale
                        n2 = min(len(yt), len(pt_ind), len(yt_p), len(pt_p))
                        if n2 <= 0:
                            raise ProvenanceError("claim A empty")
                        # align by shared length (outer eval origins are fold-aligned within pack)
                        e_lg = np.abs(yt[:n2] - pt_ind[:n2])
                        e_pe = np.abs(yt_p[:n2] - pt_p[:n2])
                        if len(yt[:n2]) != len(yt_p[:n2]):
                            raise ProvenanceError("claim A unpaired lengths")
                        effects_a = paired_moving_block_bootstrap_effects(
                            e_lg,
                            e_pe,
                            block_size=block_length,
                            n_boot=n_boot,
                            seed=seed,
                        )
                        claim_a_rows.append(
                            {
                                "claim": "A",
                                "atomic_id": f"A_cpu_lgbm_vs_pers_h{horizon}_f{fold}",
                                "hierarchy": hier_name,
                                "horizon": int(horizon),
                                "fold": int(fold),
                                "method_a": "persistence_independent",
                                "method_b": "lightgbm_independent",
                                "correction_family": "cpu_base_model_lightgbm_vs_persistence",
                                "npz_lightgbm": str(npz_path),
                                "npz_persistence": str(path_p),
                                "effect_class": effect_class(float(effects_a["relative_mae_diff"])),
                                **effects_a,
                            }
                        )

    boot_df = pd.DataFrame(boot_rows)
    rel_df = pd.DataFrame(rel_rows)
    if boot_df.empty:
        raise RuntimeError("no bootstrap comparisons produced")

    # Holm within frozen families only
    holm_parts = []
    for fam in stats_cfg["holm_families"]:
        sub = boot_df[boot_df["correction_family"] == fam].copy()
        if sub.empty:
            continue
        ranked = holm_adjust_with_ranks(sub["p_value_raw"].tolist())
        sub = sub.reset_index(drop=True)
        sub["p_value_holm"] = [r["adjusted_p"] for r in ranked]
        sub["holm_rank"] = [r["rank"] for r in ranked]
        sub["family_size"] = len(sub)
        sub["alpha"] = alpha
        sub["reject_holm_0.05"] = sub["p_value_holm"] <= alpha
        holm_parts.append(sub)
    # descriptive persistence rows (no holm)
    pers = boot_df[boot_df["in_holm_family"] == False].copy()  # noqa: E712
    if not pers.empty:
        pers["p_value_holm"] = np.nan
        pers["holm_rank"] = np.nan
        pers["family_size"] = 0
        pers["alpha"] = alpha
        pers["reject_holm_0.05"] = False
        holm_parts.append(pers)
    holm_df = pd.concat(holm_parts, ignore_index=True) if holm_parts else boot_df.copy()

    # merge holm columns back onto boot_df order
    merge_cols = [
        "hierarchy",
        "base_model",
        "horizon",
        "fold",
        "method_b",
        "p_value_holm",
        "holm_rank",
        "family_size",
        "alpha",
        "reject_holm_0.05",
    ]
    boot_df = boot_df.drop(columns=[c for c in merge_cols[5:] if c in boot_df.columns], errors="ignore")
    boot_df = boot_df.merge(
        holm_df[merge_cols],
        on=["hierarchy", "base_model", "horizon", "fold", "method_b"],
        how="left",
    )

    # Fold consistency
    fc_rows = []
    for (hier, model, horizon, method), g in boot_df.groupby(["hierarchy", "base_model", "horizon", "method_b"]):
        rels = list(g.sort_values("fold")["relative_mae_diff"])
        wins = sum(1 for r in rels if r < 0)
        losses = sum(1 for r in rels if r > 0)
        ties = len(rels) - wins - losses
        fc_rows.append(
            {
                "hierarchy": hier,
                "base_model": model,
                "horizon": int(horizon),
                "method": method,
                "n_folds": len(rels),
                "wins": wins,
                "ties": ties,
                "losses": losses,
                "mean_rel": float(np.mean(rels)),
                "best_fold_rel": float(min(rels)),
                "worst_fold_rel": float(max(rels)),
                "fold_consistency": fold_consistency_label(rels),
                "fold_rels": ";".join(f"{r:.6g}" for r in rels),
            }
        )
    fc_df = pd.DataFrame(fc_rows)

    # Top/bottom tradeoff aggregated
    tb_df = (
        boot_df.groupby(["hierarchy", "base_model", "horizon", "method_b"], as_index=False)
        .agg(
            top_rel=("relative_mae_diff", "mean"),
            macro_rel=("macro_rel", "mean"),
            weighted_rel=("weighted_rel", "mean"),
            worst_rel=("worst_rel", "mean"),
            machines_improved=("machines_improved", "mean"),
            machines_degraded=("machines_degraded", "mean"),
            coherence_before=("coherence_before", "mean"),
            coherence_after=("coherence_after", "mean"),
        )
    )
    tb_df["tradeoff_class"] = [
        tradeoff_class(float(r.top_rel), float(r.macro_rel), float(r.worst_rel), float(r.coherence_after), coherence_before=float(r.coherence_before))
        for r in tb_df.itertuples()
    ]

    # Claims
    claim_atomic = []
    claim_a_df = pd.DataFrame(claim_a_rows)
    for _, r in claim_a_df.iterrows():
        direction_support = r["relative_mae_diff"] < 0 and not r.get("rel_ci_crosses_zero", True)
        uncertain = bool(r.get("rel_ci_crosses_zero", True)) and r["relative_mae_diff"] < 0
        contradict = r["relative_mae_diff"] > 0
        if r["relative_mae_diff"] < 0 and not r.get("rel_ci_crosses_zero", True):
            verdict = "support"
        elif r["relative_mae_diff"] > 0 and not r.get("rel_ci_crosses_zero", True):
            verdict = "contradict"
        else:
            verdict = "uncertain"
        claim_atomic.append(
            {
                "claim": "A",
                "atomic_id": r["atomic_id"],
                "hierarchy": r["hierarchy"],
                "base_model": "lightgbm",
                "horizon": r["horizon"],
                "fold": r["fold"],
                "method": "vs_persistence",
                "relative_mae_diff": r["relative_mae_diff"],
                "rel_ci_low": r["rel_ci_low"],
                "rel_ci_high": r["rel_ci_high"],
                "p_value_raw": r["p_value_raw"],
                "reject_holm": False,  # filled after claim-A holm
                "verdict": verdict,
                "effect_class": r["effect_class"],
            }
        )

    # Holm for claim A family separately
    if not claim_a_df.empty:
        ranked_a = holm_adjust_with_ranks(claim_a_df["p_value_raw"].tolist())
        claim_a_df = claim_a_df.reset_index(drop=True)
        claim_a_df["p_value_holm"] = [x["adjusted_p"] for x in ranked_a]
        claim_a_df["holm_rank"] = [x["rank"] for x in ranked_a]
        claim_a_df["family_size"] = len(claim_a_df)
        claim_a_df["reject_holm_0.05"] = claim_a_df["p_value_holm"] <= alpha
        a_idx = 0
        for row in claim_atomic:
            if row["claim"] == "A":
                row["reject_holm"] = bool(claim_a_df.loc[a_idx, "reject_holm_0.05"])
                row["p_value_holm"] = float(claim_a_df.loc[a_idx, "p_value_holm"])
                a_idx += 1

    def add_recon_claim(claim_id: str, mask: pd.Series, expected_direction: str) -> None:
        sub = boot_df[mask]
        for _, r in sub.iterrows():
            rel = float(r["relative_mae_diff"])
            cross = bool(r["rel_ci_crosses_zero"])
            if expected_direction == "improve":
                if rel < 0 and not cross:
                    verdict = "support"
                elif rel > 0 and not cross:
                    verdict = "contradict"
                else:
                    verdict = "uncertain"
            else:  # degrade
                if rel > 0 and not cross:
                    verdict = "support"
                elif rel < 0 and not cross:
                    verdict = "contradict"
                else:
                    verdict = "uncertain"
            claim_atomic.append(
                {
                    "claim": claim_id,
                    "atomic_id": f"{claim_id}_{r.hierarchy}_{r.base_model}_h{int(r.horizon)}_f{int(r.fold)}_{r.method_b}",
                    "hierarchy": r["hierarchy"],
                    "base_model": r["base_model"],
                    "horizon": int(r["horizon"]),
                    "fold": int(r["fold"]),
                    "method": r["method_b"],
                    "relative_mae_diff": rel,
                    "rel_ci_low": r["rel_ci_low"],
                    "rel_ci_high": r["rel_ci_high"],
                    "p_value_raw": r["p_value_raw"],
                    "p_value_holm": r.get("p_value_holm"),
                    "reject_holm": bool(r.get("reject_holm_0.05", False)),
                    "verdict": verdict,
                    "effect_class": r["effect_class"],
                }
            )

    add_recon_claim(
        "B",
        (boot_df.hierarchy == "cpu_core_weighted")
        & (boot_df.base_model.isin(["ridge", "lightgbm", "dlinear"]))
        & (boot_df.method_b.isin(["bottom_up", "wls", "mint"])),
        "improve",
    )
    add_recon_claim(
        "C",
        (boot_df.hierarchy == "memory_um")
        & (boot_df.base_model.isin(["ridge", "dlinear"]))
        & (boot_df.method_b.isin(["wls", "mint"])),
        "improve",
    )
    # Claim D: BU degrades (support if degrade); TD preserves top (support if |rel|<=2% and coherence-only-ish)
    d_bu = (boot_df.hierarchy == "disk_ud") & (boot_df.base_model == "ridge") & (boot_df.method_b == "bottom_up")
    add_recon_claim("D", d_bu, "degrade")
    d_td = boot_df[(boot_df.hierarchy == "disk_ud") & (boot_df.base_model == "ridge") & (boot_df.method_b == "top_down")]
    for _, r in d_td.iterrows():
        rel = float(r["relative_mae_diff"])
        if abs(rel) <= 0.02:
            verdict = "support"
        elif rel < -0.02:
            verdict = "uncertain"
        else:
            verdict = "contradict"
        claim_atomic.append(
            {
                "claim": "D",
                "atomic_id": f"D_disk_ridge_h{int(r.horizon)}_f{int(r.fold)}_top_down",
                "hierarchy": r["hierarchy"],
                "base_model": "ridge",
                "horizon": int(r["horizon"]),
                "fold": int(r["fold"]),
                "method": "top_down",
                "relative_mae_diff": rel,
                "rel_ci_low": r["rel_ci_low"],
                "rel_ci_high": r["rel_ci_high"],
                "p_value_raw": r["p_value_raw"],
                "p_value_holm": r.get("p_value_holm"),
                "reject_holm": bool(r.get("reject_holm_0.05", False)),
                "verdict": verdict,
                "effect_class": r["effect_class"],
            }
        )

    atomic_df = pd.DataFrame(claim_atomic)

    def summarize_claim(claim_id: str, qualification: str) -> dict[str, Any]:
        sub = atomic_df[atomic_df.claim == claim_id]
        n_sup = int((sub.verdict == "support").sum())
        n_unc = int((sub.verdict == "uncertain").sum())
        n_con = int((sub.verdict == "contradict").sum())
        n_tot = len(sub)
        rels = sub["relative_mae_diff"].astype(float)
        # horizon consistency: every required horizon has majority support
        horizon_ok = True
        folds_ok = True
        for h, hg in sub.groupby("horizon"):
            if (hg.verdict == "support").mean() < 0.5:
                horizon_ok = False
            for _, fg in hg.groupby("fold"):
                pass
            # at least two folds support per horizon (when 3 folds present)
            fold_support = hg.groupby("fold").apply(lambda x: (x.verdict == "support").any())
            if fold_support.sum() < min(2, fold_support.shape[0]):
                # looser: count folds with majority support among that fold's atomics
                fold_maj = hg.groupby("fold").apply(lambda x: (x.verdict == "support").mean() >= 0.5)
                if int(fold_maj.sum()) < 2:
                    folds_ok = False
        has_sub_con = bool(((sub.verdict == "contradict") & (sub.effect_class == "substantial_improvement")).any()) or bool(
            ((sub.verdict == "contradict") & (sub["relative_mae_diff"].abs() >= 0.05)).any()
        )
        # for degrade claims, substantial contradiction is substantial improvement
        if claim_id == "D":
            has_sub_con = bool(((sub.verdict == "contradict") & (sub["relative_mae_diff"] <= -0.05)).any())
        support = classify_claim_support(
            n_support=n_sup,
            n_uncertain=n_unc,
            n_contradict=n_con,
            n_total=n_tot,
            horizon_ok=horizon_ok,
            folds_ok=folds_ok,
            has_substantial_contradiction=has_sub_con,
        )
        return {
            "claim": claim_id,
            "support": support,
            "n_atomic": n_tot,
            "n_support": n_sup,
            "n_uncertain": n_unc,
            "n_contradict": n_con,
            "median_rel_effect": float(rels.median()) if n_tot else float("nan"),
            "min_rel_effect": float(rels.min()) if n_tot else float("nan"),
            "max_rel_effect": float(rels.max()) if n_tot else float("nan"),
            "min_ci_low": float(sub["rel_ci_low"].min()) if n_tot else float("nan"),
            "max_ci_high": float(sub["rel_ci_high"].max()) if n_tot else float("nan"),
            "holm_reject_count": int(sub["reject_holm"].fillna(False).sum()),
            "fold_direction_consistency": "ok" if folds_ok else "inconsistent",
            "horizon_consistency": "ok" if horizon_ok else "inconsistent",
            "qualification": qualification,
        }

    claim_summaries = [
        summarize_claim("A", "CPU LightGBM independent vs persistence; separate Holm family; not reconciliation."),
        summarize_claim("B", "CPU recon (ridge/lgbm/dlinear × BU/WLS/MinT); bottoms unchanged under BU."),
        summarize_claim("C", "Memory WLS/MinT for Ridge/DLinear only; LightGBM remains negative baseline."),
        summarize_claim(
            "D",
            "Disk Ridge BU degrades aggregate; Ridge TD preserves independent top (bottom may still be costly).",
        ),
    ]
    claim_df = pd.DataFrame(claim_summaries)

    # Method selection
    sel_rows = []
    for hier, label, cands, unsuitable, neg in [
        (
            "cpu_core_weighted",
            "cpu",
            [("lightgbm", "mint"), ("ridge", "bottom_up"), ("dlinear", "bottom_up"), ("lightgbm", "bottom_up")],
            "WLS/MinT when machine-level Pareto required",
            "WLS/MinT may degrade machines vs bottom_up",
        ),
        (
            "memory_um",
            "memory",
            [("dlinear", "mint"), ("ridge", "mint"), ("dlinear", "wls"), ("ridge", "wls"), ("persistence", "independent")],
            "lightgbm as accuracy leader vs persistence",
            "memory LightGBM weak vs persistence",
        ),
        (
            "disk_ud",
            "disk",
            [("persistence", "independent"), ("ridge", "top_down"), ("ridge", "mint")],
            "bottom_up for learned models; lightgbm transferred hparams",
            "disk BU harmful; LGBM transferred-stress",
        ),
    ]:
        scores = []
        for m, meth in cands:
            if meth == "independent":
                sub = boot_df[(boot_df.hierarchy == hier) & (boot_df.base_model == m)]
                if sub.empty:
                    continue
                mae = float(sub.groupby(["fold", "horizon"]).mae_independent.first().mean())
            else:
                sub = boot_df[(boot_df.hierarchy == hier) & (boot_df.base_model == m) & (boot_df.method_b == meth)]
                if sub.empty:
                    continue
                mae = float(sub.mae_reconciled.mean())
            scores.append((f"{m}+{meth}", mae, meth))
        scores.sort(key=lambda x: x[1])
        best = scores[0]
        coh = [s for s in scores if s[2] in ("mint", "wls", "bottom_up", "top_down") or s[2] == "independent"]
        best_coh = sorted(coh, key=lambda x: x[1])[0]
        sel_rows.append(
            {
                "hierarchy": label,
                "best_pure_accuracy": best[0],
                "best_pure_accuracy_mae": best[1],
                "best_accuracy_coherence": best_coh[0],
                "best_accuracy_coherence_mae": best_coh[1],
                "unsuitable": unsuitable,
                "negative_findings": neg,
            }
        )
    sel_df = pd.DataFrame(sel_rows)

    # Write artifacts
    out = Path(output_dir)
    met = out / "metrics"
    tab = out / "tables"
    fig = out / "figures"
    for d in (met, tab, fig):
        d.mkdir(parents=True, exist_ok=True)

    hash_df = pd.DataFrame(source_hash_rows)
    hash_df.to_csv(met / "source_prediction_hashes.csv", index=False)

    boot_df.to_csv(met / "paired_block_bootstrap.csv", index=False)
    rel_df.to_csv(met / "relative_effect_bootstrap.csv", index=False)
    holm_df.to_csv(met / "holm_corrected_tests.csv", index=False)
    fc_df.to_csv(met / "fold_consistency.csv", index=False)
    tb_df.to_csv(met / "top_bottom_tradeoff.csv", index=False)
    claim_df.to_csv(met / "claim_support.csv", index=False)
    atomic_df.to_csv(met / "claim_atomic_evidence.csv", index=False)
    if not claim_a_df.empty:
        claim_a_df.to_csv(met / "claim_A_fold_details.csv", index=False)

    boot_df.to_csv(tab / "statistical_comparisons.csv", index=False)
    claim_df.to_csv(tab / "claim_support_summary.csv", index=False)
    sel_df.to_csv(tab / "method_selection.csv", index=False)

    # Minimal tex table
    tex_cols = [
        "hierarchy",
        "base_model",
        "horizon",
        "method_b",
        "relative_mae_diff",
        "rel_ci_low",
        "rel_ci_high",
        "prob_improvement",
        "p_value_raw",
        "p_value_holm",
        "effect_class",
    ]
    tex_df = (
        boot_df[boot_df.in_holm_family]
        .groupby(["hierarchy", "base_model", "horizon", "method_b"], as_index=False)
        .agg(
            relative_mae_diff=("relative_mae_diff", "mean"),
            rel_ci_low=("rel_ci_low", "mean"),
            rel_ci_high=("rel_ci_high", "mean"),
            prob_improvement=("prob_improvement", "mean"),
            p_value_raw=("p_value_raw", "mean"),
            p_value_holm=("p_value_holm", "mean"),
        )
    )
    tex_df["effect_class"] = tex_df["relative_mae_diff"].map(effect_class)
    lines = [
        r"\begin{tabular}{llrrrrrrl}",
        r"\hline",
        r"hier & model & h & method & rel & lo & hi & pHolm & class \\",
        r"\hline",
    ]
    for r in tex_df.itertuples():
        lines.append(
            f"{r.hierarchy} & {r.base_model} & {int(r.horizon)} & {r.method_b} & "
            f"{r.relative_mae_diff:.3f} & {r.rel_ci_low:.3f} & {r.rel_ci_high:.3f} & "
            f"{r.p_value_holm:.3g} & {r.effect_class} \\\\"
        )
    lines += [r"\hline", r"\end{tabular}", ""]
    (tab / "statistical_comparisons.tex").write_text("\n".join(lines))

    def forest(ax, sub, title):
        g = sub.groupby(["base_model", "horizon", "method_b"], as_index=False).agg(
            mean_rel=("relative_mae_diff", "mean"), lo=("rel_ci_low", "mean"), hi=("rel_ci_high", "mean")
        )
        g = g[g.base_model != "persistence"]
        g["label"] = g.apply(lambda r: f"{r.base_model} h{int(r.horizon)} {r.method_b}", axis=1)
        y = np.arange(len(g))
        ax.axvline(0, color="k", lw=0.8)
        if len(g):
            ax.hlines(y, g.lo, g.hi, color="#456")
            ax.plot(g.mean_rel, y, "o", color="#c45")
            ax.set_yticks(y)
            ax.set_yticklabels(g.label, fontsize=7)
        ax.set_xlabel("relative MAE effect (bootstrapped)")
        ax.set_title(title)

    for hier, name in [
        ("memory_um", "bootstrap_effects_memory"),
        ("cpu_core_weighted", "bootstrap_effects_cpu"),
        ("disk_ud", "bootstrap_effects_disk"),
    ]:
        fig_p, ax = plt.subplots(figsize=(8, 10))
        forest(ax, boot_df[boot_df.hierarchy == hier], name)
        fig_p.tight_layout()
        fig_p.savefig(fig / f"{name}.pdf")
        fig_p.savefig(fig / f"{name}.png")
        plt.close(fig_p)

    fig_p, ax = plt.subplots(figsize=(7, 6))
    for hier, marker in [("cpu_core_weighted", "o"), ("memory_um", "s"), ("disk_ud", "^")]:
        s = tb_df[tb_df.hierarchy == hier]
        ax.scatter(s.macro_rel, s.top_rel, label=hier, alpha=0.75, marker=marker)
    ax.axhline(0, color="k", lw=0.6)
    ax.axvline(0, color="k", lw=0.6)
    ax.set_xlabel("macro bottom relative MAE change")
    ax.set_ylabel("top relative MAE change")
    ax.set_title("Top vs bottom trade-off")
    ax.legend(fontsize=8)
    fig_p.tight_layout()
    fig_p.savefig(fig / "top_bottom_tradeoff.pdf")
    fig_p.savefig(fig / "top_bottom_tradeoff.png")
    plt.close(fig_p)

    # Verify source hashes unchanged
    changed = []
    for path_str, digest in pred_paths_before.items():
        now = sha256_file(Path(path_str))
        if now != digest:
            changed.append(path_str)
    if changed:
        raise RuntimeError(f"source predictions modified during analysis: {changed[:5]}")

    end_iso = datetime.now(timezone.utc).isoformat()
    wall = time.perf_counter() - t0
    cpu = time.process_time() - cpu0

    try:
        exec_commit = _git(["rev-parse", "HEAD"])
    except Exception:
        exec_commit = "UNKNOWN"
    try:
        analysis_tag_commit = _git(["rev-parse", "final-analysis-freeze-v1"])
    except Exception:
        analysis_tag_commit = stats_cfg.get("analysis_freeze_tag_commit") or "PENDING_UNTIL_TAG"
    try:
        src_tag_commit = _git(["rev-parse", "experiment-freeze-v2"])
    except Exception:
        src_tag_commit = stats_cfg.get("source_experiment_freeze_tag_commit") or "UNKNOWN"

    stats_hash = config_hash(stats_cfg)
    manifest = {
        "pack_id": "supporting_statistics",
        "required": True,
        "dependencies": source_pack_ids,
        "experiment_stage": "final",
        "eligible_for_final_claims": True,
        "evaluation_role": "final_statistical_analysis",
        "source_experiment_freeze_tag": stats_cfg["source_experiment_freeze_tag"],
        "source_experiment_freeze_tag_commit": src_tag_commit,
        "source_frozen_implementation_commit": stats_cfg["source_frozen_implementation_commit"],
        "analysis_freeze_tag": stats_cfg.get("analysis_freeze_tag", "final-analysis-freeze-v1"),
        "analysis_freeze_tag_commit": analysis_tag_commit,
        "analysis_implementation_commit": stats_cfg.get("analysis_implementation_commit") or exec_commit,
        "execution_commit": exec_commit,
        "freeze_tag": stats_cfg["source_experiment_freeze_tag"],
        "freeze_tag_commit": src_tag_commit,
        "freeze_commit": stats_cfg["source_frozen_implementation_commit"],
        "frozen_implementation_commit": stats_cfg["source_frozen_implementation_commit"],
        "implementation_commit": stats_cfg["source_frozen_implementation_commit"],
        "dataset_fingerprint": stats_cfg["dataset_fingerprint"],
        "config_hash": stats_cfg.get("source_config_hash"),
        "statistical_config_hash": stats_hash,
        "source_pack_hashes": source_pack_hashes,
        "bootstrap_n_boot": n_boot,
        "bootstrap_seed": seed,
        "start_time": start_iso,
        "end_time": end_iso,
        "actual_wall_seconds": wall,
        "cpu_seconds": cpu,
        "comparisons_completed": int(len(boot_df)),
        "comparisons_failed": 0,
        "status": "complete",
        "output_dir": str(out.resolve()),
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    status = {
        "pack_id": "supporting_statistics",
        "status": "complete",
        "completed_runs": ["supporting_statistics"],
        "failed_runs": [],
        "skipped_runs": [],
        "total_runs": 1,
        "wall_seconds": wall,
        "cpu_seconds": cpu,
        "start_time": start_iso,
        "end_time": end_iso,
    }
    (out / "RUN_STATUS.json").write_text(json.dumps(status, indent=2) + "\n")
    (out / "COMPLETE").write_text(end_iso + "\n")

    return {
        "manifest": manifest,
        "n_comparisons": len(boot_df),
        "claims": claim_df,
        "method_selection": sel_df,
        "wall_seconds": wall,
        "source_hashes_unchanged": True,
    }
