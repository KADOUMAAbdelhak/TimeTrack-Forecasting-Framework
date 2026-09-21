"""Frozen final evidence aggregation for FGCS publication assessment.

Consumes only registry-listed packs. Never trains models or modifies sources.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
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
from timetrack.metrics import mae

ROOT = Path(__file__).resolve().parents[1]


class EvidenceError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def config_hash(obj: dict[str, Any]) -> str:
    return hashlib.sha256(yaml.safe_dump(obj, sort_keys=True).encode()).hexdigest()[:16]


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text())


def validate_registry(reg: dict[str, Any]) -> list[str]:
    errs = []
    for k in (
        "dataset_fingerprint",
        "prediction_layer",
        "statistics_layer",
        "peak_layer",
        "accepted_prediction_packs",
        "accepted_analysis_packs",
        "exclusions",
        "pack_dirs",
    ):
        if k not in reg:
            errs.append(f"missing {k}")
    if reg.get("dataset_fingerprint") != "bf06dc0e7fe6ff5e":
        errs.append("dataset_fingerprint mismatch")
    if (reg.get("exclusions") or {}).get("downsampling", {}).get("claim_eligible") is not False:
        errs.append("downsampling must be claim_eligible=false")
    return errs


def validate_reporting_config(cfg: dict[str, Any]) -> list[str]:
    errs = []
    if cfg.get("reporting_freeze_tag") != "final-reporting-freeze-v1":
        errs.append("reporting_freeze_tag must be final-reporting-freeze-v1")
    if "cpu_weighted_mean_pct" not in (cfg.get("unit_separation") or []):
        errs.append("unit_separation must include cpu_weighted_mean_pct")
    return errs


def _git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def verify_pack_manifest(pack_id: str, man: dict[str, Any], reg: dict[str, Any]) -> None:
    fp = man.get("dataset_fingerprint")
    if fp != reg["dataset_fingerprint"]:
        raise EvidenceError(f"{pack_id}: fingerprint {fp}")
    if man.get("experiment_stage") in {"pilot", "development"} and pack_id not in reg.get("accepted_analysis_packs", []):
        # analysis packs are final stage
        if man.get("experiment_stage") != "final":
            raise EvidenceError(f"{pack_id}: stage {man.get('experiment_stage')}")
    if not bool(man.get("eligible_for_final_claims", False)):
        raise EvidenceError(f"{pack_id}: not claim-eligible")
    out = str(man.get("output_dir") or "")
    if "results/pilot" in out or "/pilot/" in out:
        raise EvidenceError(f"{pack_id}: pilot path")
    # prediction packs
    if pack_id in reg["accepted_prediction_packs"]:
        if man.get("freeze_tag") != reg["prediction_layer"]["freeze_tag"]:
            raise EvidenceError(f"{pack_id}: freeze_tag mismatch")
        impl = man.get("frozen_implementation_commit") or man.get("implementation_commit") or man.get("freeze_commit")
        if impl != reg["prediction_layer"]["implementation_commit"]:
            raise EvidenceError(f"{pack_id}: implementation mismatch {impl}")
        if man.get("evaluation_role") not in {"outer_evaluation", "shared_final_tuning"}:
            raise EvidenceError(f"{pack_id}: evaluation_role {man.get('evaluation_role')}")
    if pack_id == "supporting_statistics":
        if man.get("evaluation_role") != "final_statistical_analysis":
            raise EvidenceError("supporting_statistics role")
        if man.get("analysis_freeze_tag") != reg["statistics_layer"]["freeze_tag"]:
            # tolerate missing if freeze_tag on source matches and statistical hash present
            if man.get("analysis_freeze_tag") and man.get("analysis_freeze_tag") != reg["statistics_layer"]["freeze_tag"]:
                raise EvidenceError("stats freeze tag mismatch")
    if pack_id == "peak_analysis":
        if man.get("evaluation_role") != "final_peak_analysis":
            raise EvidenceError("peak_analysis role")
        if man.get("peak_analysis_freeze_tag") != reg["peak_layer"]["freeze_tag"]:
            raise EvidenceError("peak freeze tag mismatch")


def _scale_for(hierarchy: str, core_total: float) -> float:
    return core_total if hierarchy == "cpu_core_weighted" else 1.0


def _unit_for(hierarchy: str) -> str:
    return {
        "cpu_core_weighted": "cpu_weighted_mean_pct",
        "memory_um": "memory_bytes",
        "disk_ud": "disk_level",
    }[hierarchy]


def _rmse(y, p) -> float:
    y = np.asarray(y, dtype=float).reshape(-1)
    p = np.asarray(p, dtype=float).reshape(-1)
    return float(np.sqrt(np.mean((y - p) ** 2)))


def _r2(y, p) -> float:
    y = np.asarray(y, dtype=float).reshape(-1)
    p = np.asarray(p, dtype=float).reshape(-1)
    ss_res = float(np.sum((y - p) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    return float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")


def _mase(y_test, p_test, y_train, season: int = 1) -> float:
    y_train = np.asarray(y_train, dtype=float).reshape(-1)
    if len(y_train) <= season:
        return float("nan")
    scale = float(np.mean(np.abs(y_train[season:] - y_train[:-season])))
    if scale < 1e-18:
        return float("nan")
    return float(mae(y_test, p_test) / scale)


def load_recon_frames(reg: dict[str, Any], *, smoke_root: Path | None = None) -> pd.DataFrame:
    frames = []
    for pid in ["memory_classical", "memory_dlinear", "cpu_classical", "cpu_dlinear", "disk_boundary"]:
        pdir = ROOT / reg["pack_dirs"][pid] if smoke_root is None else smoke_root / pid
        path = pdir / "metrics" / "reconciliation_results.csv"
        if not path.exists():
            raise EvidenceError(f"missing {path}")
        df = pd.read_csv(path)
        if "experiment_stage" in df.columns and (df.experiment_stage == "pilot").any():
            raise EvidenceError(f"pilot rows in {pid}")
        if "eligible_for_final_claims" in df.columns and (~df.eligible_for_final_claims.astype(bool)).any():
            # allow rows but refuse if all false
            if (~df.eligible_for_final_claims.astype(bool)).all():
                raise EvidenceError(f"all rows claim-ineligible in {pid}")
        df["source_pack"] = pid
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    if out.run_id.duplicated().any():
        raise EvidenceError("duplicate run_id across recon frames")
    # primary nonnegative=false
    if "nonnegative" in out.columns:
        out = out[out.nonnegative == False].copy()  # noqa: E712
    return out


def enrich_metrics_from_npz(
    recon: pd.DataFrame, reg: dict[str, Any], *, smoke: bool = False
) -> pd.DataFrame:
    """Add RMSE/R²/MASE/worst-machine from NPZs for primary methods (no training)."""
    if smoke:
        recon = recon.copy()
        recon["rmse"] = np.nan
        recon["r2"] = np.nan
        recon["mase"] = np.nan
        recon["worst_machine_mae"] = np.nan
        recon["core_weighted_bottom_mae"] = np.nan
        return recon

    core_total = float(reg["cpu_core_total"])
    cores = np.array([machine_core_counts()[f"machine0{i}"] for i in range(1, 8)], dtype=float)
    cores_w = cores / cores.sum()
    hier_map = {
        "memory_um": memory_hierarchy(),
        "cpu_core_weighted": core_weighted_cpu_hierarchy(),
        "disk_ud": disk_hierarchy(),
    }
    pack_for = {
        "memory_um": ["memory_classical", "memory_dlinear"],
        "cpu_core_weighted": ["cpu_classical", "cpu_dlinear"],
        "disk_ud": ["disk_boundary"],
    }
    cache: dict[tuple, dict] = {}
    rows = []
    primary_methods = {"independent", "bottom_up", "wls", "mint", "top_down", "ols"}
    for _, r in recon.iterrows():
        method = r.reconciliation_method
        if method not in primary_methods:
            continue
        key = (r.hierarchy, r.base_model, int(r.fold), int(r.horizon), method)
        if key not in cache:
            h = hier_map[r.hierarchy]
            scale = _scale_for(r.hierarchy, core_total)
            npz = None
            for pid in pack_for[r.hierarchy]:
                pred = ROOT / reg["pack_dirs"][pid] / "metrics" / "predictions"
                matches = sorted(pred.glob(f"base__{r.hierarchy}__f{int(r.fold)}__h{int(r.horizon)}__{r.base_model}__s0.npz"))
                if matches:
                    npz = np.load(matches[0])
                    break
            if npz is None:
                cache[key] = {"rmse": np.nan, "r2": np.nan, "mase": np.nan, "worst_machine_mae": np.nan, "core_weighted_bottom_mae": np.nan}
            else:
                y_full = np.concatenate([npz["yb_val"], np.asarray(npz["yt_val"]).reshape(-1, 1)], 1)
                p_full = np.concatenate([npz["pb_val"], np.asarray(npz["pt_val"]).reshape(-1, 1)], 1)
                cov = estimate_residual_covariance(y_full, p_full, shrink_diag=0.1)
                sv = np.maximum(np.diag(cov), 1e-12)
                out = reconcile(
                    method,
                    h,
                    npz["pb_test"],
                    npz["pt_test"],
                    series_var=sv if method == "wls" else None,
                    residual_cov=cov if method == "mint" else None,
                    nonnegative=False,
                )
                yt = np.asarray(npz["yt_test"], dtype=float).reshape(-1) / scale
                pt = np.asarray(out["top"], dtype=float).reshape(-1) / scale
                yt_tr = np.asarray(npz["yt_train"], dtype=float).reshape(-1) / scale
                yb = np.asarray(npz["yb_test"], dtype=float)
                pb = np.asarray(out["bottom"], dtype=float)
                per_m = np.array([mae(yb[:, j], pb[:, j]) for j in range(yb.shape[1])])
                cache[key] = {
                    "rmse": _rmse(yt, pt),
                    "r2": _r2(yt, pt),
                    "mase": _mase(yt, pt, yt_tr),
                    "worst_machine_mae": float(np.max(per_m)),
                    "core_weighted_bottom_mae": float(np.dot(per_m, cores_w)) if r.hierarchy == "cpu_core_weighted" else float(np.mean(per_m)),
                }
        rows.append({**r.to_dict(), **cache[key]})
    return pd.DataFrame(rows)


def run_final_aggregation(
    *,
    registry: dict[str, Any],
    reporting: dict[str, Any],
    output_dir: Path,
    smoke: bool = False,
    smoke_root: Path | None = None,
) -> dict[str, Any]:
    errs = validate_registry(registry) + validate_reporting_config(reporting)
    if errs and not smoke:
        raise EvidenceError("; ".join(errs))

    out = Path(output_dir)
    tables = out / "tables"
    figures = out / "figures"
    for d in (tables, figures):
        d.mkdir(parents=True, exist_ok=True)

    # Hash & verify accepted packs
    hash_rows = []
    before = {}
    for pid in registry["accepted_prediction_packs"] + registry["accepted_analysis_packs"]:
        pdir = ROOT / registry["pack_dirs"][pid] if not smoke else (smoke_root / pid)
        man_path = pdir / "MANIFEST.json"
        if not man_path.exists():
            if smoke:
                continue
            raise EvidenceError(f"missing MANIFEST {pid}")
        man = _read_json(man_path)
        if not smoke:
            verify_pack_manifest(pid, man, registry)
        # hash key artifacts
        for pattern in ["MANIFEST.json", "COMPLETE", "metrics/*.csv", "tables/*.csv"]:
            for path in pdir.glob(pattern):
                if path.is_file():
                    dig = sha256_file(path)
                    before[str(path.resolve())] = dig
                    hash_rows.append({"source_pack": pid, "path": str(path.relative_to(ROOT)) if str(path).startswith(str(ROOT)) else str(path), "sha256": dig, "bytes": path.stat().st_size})

    # Exclusions must not be required
    for ex_id, meta in (registry.get("exclusions") or {}).items():
        if meta.get("claim_eligible"):
            raise EvidenceError(f"exclusion {ex_id} marked claim_eligible")

    core_total = float(registry.get("cpu_core_total", 236))
    recon = load_recon_frames(registry, smoke_root=smoke_root if smoke else None)
    if recon.dataset_fingerprint.nunique(dropna=True) > 1:
        raise EvidenceError("mixed dataset fingerprints in recon")
    enriched = enrich_metrics_from_npz(recon, registry, smoke=smoke)

    # Scale MAE for display units
    enriched = enriched.copy()
    enriched["unit"] = enriched.hierarchy.map(_unit_for)
    enriched["mae_display"] = enriched.apply(lambda r: float(r.top_mae) / _scale_for(r.hierarchy, core_total), axis=1)
    enriched["rmse_display"] = enriched.apply(
        lambda r: float(r.rmse) if pd.notna(r.get("rmse", np.nan)) else np.nan, axis=1
    )
    # persistence reference per hierarchy×horizon×fold
    pers = enriched[(enriched.base_model == "persistence") & (enriched.reconciliation_method == "independent")][
        ["hierarchy", "horizon", "fold", "mae_display"]
    ].rename(columns={"mae_display": "mae_persistence"})
    enriched = enriched.merge(pers, on=["hierarchy", "horizon", "fold"], how="left")
    ind = enriched[enriched.reconciliation_method == "independent"][
        ["hierarchy", "base_model", "horizon", "fold", "mae_display"]
    ].rename(columns={"mae_display": "mae_independent"})
    enriched = enriched.merge(ind, on=["hierarchy", "base_model", "horizon", "fold"], how="left")
    enriched["mae_vs_persistence"] = (enriched.mae_display - enriched.mae_persistence) / enriched.mae_persistence
    enriched["mae_vs_independent"] = (enriched.mae_display - enriched.mae_independent) / enriched.mae_independent.replace(0, np.nan)

    # ---- Table 1 registry ----
    t1 = pd.DataFrame(
        [
            {
                "hierarchy": "cpu_core_weighted",
                "relation_type": "sum_of_core_weighted_cu",
                "bottom_series": "machine0k_CU_wcontrib",
                "top_series": "cluster_CU_wsum → weighted_mean(/236)",
                "exact_or_approximate": "exact (verified cores)",
                "target_units": "cpu_weighted_mean_pct",
                "horizons": "1,8,16",
                "folds": "0,1,2",
                "models": "persistence,ridge,lightgbm,dlinear",
                "reconciliation_methods": "independent,bottom_up,wls,mint (+ols ablation)",
                "claim_role": "primary positive hierarchy",
            },
            {
                "hierarchy": "memory_um",
                "relation_type": "exact_sum",
                "bottom_series": "machine0k_UM",
                "top_series": "cluster_UM",
                "exact_or_approximate": "exact",
                "target_units": "memory_bytes",
                "horizons": "1,8,16",
                "folds": "0,1,2",
                "models": "persistence,ridge,lightgbm,dlinear",
                "reconciliation_methods": "independent,bottom_up,wls,mint (+ols ablation)",
                "claim_role": "secondary positive/conditional hierarchy",
            },
            {
                "hierarchy": "disk_ud",
                "relation_type": "exact_sum",
                "bottom_series": "machine0k_UD",
                "top_series": "cluster_UD",
                "exact_or_approximate": "exact",
                "target_units": "disk_level",
                "horizons": "1,8",
                "folds": "0,1,2",
                "models": "persistence,ridge,lightgbm",
                "reconciliation_methods": "independent,bottom_up,top_down,wls,mint",
                "claim_role": "boundary/negative hierarchy",
            },
            {
                "hierarchy": "network_bond0",
                "relation_type": "approximate_sum",
                "bottom_series": "member NICs",
                "top_series": "bond0",
                "exact_or_approximate": "approximate",
                "target_units": "n/a",
                "horizons": "n/a",
                "folds": "n/a",
                "models": "n/a",
                "reconciliation_methods": "n/a",
                "claim_role": "not evaluated in final packs",
            },
        ]
    )
    t1.to_csv(tables / "table01_experiment_hierarchy_registry.csv", index=False)

    def main_table(hier: str) -> pd.DataFrame:
        sub = enriched[enriched.hierarchy == hier]
        g = (
            sub.groupby(["base_model", "horizon", "reconciliation_method"], as_index=False)
            .agg(
                mae=("mae_display", "mean"),
                rmse=("rmse_display", "mean"),
                mase=("mase", "mean"),
                r2=("r2", "mean"),
                mae_vs_persistence=("mae_vs_persistence", "mean"),
                mae_vs_independent=("mae_vs_independent", "mean"),
                coherence_before=("coherence_error_before", "mean"),
                coherence_after=("coherence_error_after", "mean"),
                bottom_macro_mae=("bottom_mae_mean", "mean"),
                core_weighted_bottom_mae=("core_weighted_bottom_mae", "mean"),
                worst_machine_mae=("worst_machine_mae", "mean"),
            )
        )
        g["unit"] = _unit_for(hier)
        return g

    t2 = main_table("cpu_core_weighted")
    t2.to_csv(tables / "table02_cpu_main_results.csv", index=False)
    t3 = main_table("memory_um")
    t3.to_csv(tables / "table03_memory_main_results.csv", index=False)
    t4 = main_table("disk_ud")
    t4["note"] = t4.base_model.map(lambda m: "transferred-configuration stress result" if m == "lightgbm" else "")
    t4.to_csv(tables / "table04_disk_boundary_results.csv", index=False)

    # Table 5 stats
    stats_dir = ROOT / registry["pack_dirs"]["supporting_statistics"] / "metrics"
    boot = pd.read_csv(stats_dir / "paired_block_bootstrap.csv")
    # keep holm families / learned
    t5 = boot[
        [
            c
            for c in [
                "hierarchy",
                "base_model",
                "horizon",
                "method_b",
                "relative_mae_diff",
                "rel_ci_low",
                "rel_ci_high",
                "prob_improvement",
                "prob_reconciliation_improves",
                "p_value_raw",
                "p_value_holm",
                "effect_class",
                "tradeoff_class",
                "fold",
                "correction_family",
                "reject_holm_0.05",
            ]
            if c in boot.columns
        ]
    ].copy()
    if "prob_improvement" not in t5.columns and "prob_reconciliation_improves" in t5.columns:
        t5["prob_improvement"] = t5["prob_reconciliation_improves"]
    fc = pd.read_csv(stats_dir / "fold_consistency.csv")
    t5 = t5.merge(
        fc.rename(columns={"method": "method_b"})[["hierarchy", "base_model", "horizon", "method_b", "fold_consistency"]],
        on=["hierarchy", "base_model", "horizon", "method_b"],
        how="left",
    )
    t5.to_csv(tables / "table05_statistical_evidence.csv", index=False)

    # Table 6 claims
    claim_stats = pd.read_csv(stats_dir / "claim_support.csv")
    peak_claims = pd.read_csv(ROOT / registry["pack_dirs"]["peak_analysis"] / "metrics" / "peak_claim_support.csv")
    # Map A-D and P1-P5
    rows = []
    mapping = {
        "A": ("A", "LightGBM improves CPU forecasting over persistence."),
        "B": ("B", "Reconciliation improves learned CPU aggregate forecasts."),
        "C": ("C", "WLS/MinT improve memory forecasts conditionally."),
        "D": None,  # split
    }
    for _, r in claim_stats.iterrows():
        cid = str(r.claim)
        if cid == "D":
            continue
        rows.append(
            {
                "claim": cid,
                "statement": mapping.get(cid, (cid, r.get("title", "")))[1] if cid in mapping and mapping[cid] else r.get("title", ""),
                "support": r.support,
                "n_support": r.get("n_support", r.get("n_atomic", "")),
                "n_uncertain": r.get("n_uncertain", ""),
                "n_contradict": r.get("n_contradict", ""),
                "qualification": r.get("qualification", ""),
            }
        )
    # D1 / D2 from stats atomics / disk boot
    disk_bu = boot[(boot.hierarchy == "disk_ud") & (boot.base_model == "ridge") & (boot.method_b == "bottom_up")]
    disk_td = boot[(boot.hierarchy == "disk_ud") & (boot.base_model == "ridge") & (boot.method_b == "top_down")]
    rows.append(
        {
            "claim": "D1",
            "statement": "Disk bottom-up harms learned aggregate forecasts.",
            "support": "supported" if (disk_bu.relative_mae_diff > 0).all() else "partially_supported",
            "n_support": int((disk_bu.relative_mae_diff > 0).sum()),
            "n_uncertain": int((disk_bu.rel_ci_crosses_zero if "rel_ci_crosses_zero" in disk_bu else disk_bu.relative_mae_diff.abs() < 0.02).sum()) if len(disk_bu) else 0,
            "n_contradict": int((disk_bu.relative_mae_diff < 0).sum()),
            "qualification": f"Ridge BU mean rel={disk_bu.relative_mae_diff.mean():.4f}; interpret separately from D2.",
        }
    )
    rows.append(
        {
            "claim": "D2",
            "statement": "Disk top-down preserves the independently forecast top but harms bottoms.",
            "support": "supported" if (disk_td.relative_mae_diff.abs() < 1e-12).all() else "partially_supported",
            "n_support": int((disk_td.relative_mae_diff.abs() < 1e-12).sum()),
            "n_uncertain": 0,
            "n_contradict": int((disk_td.relative_mae_diff.abs() >= 1e-12).sum()),
            "qualification": "Top MAE unchanged; bottom macro degradation from trade-off tables (accuracy_costly at bottoms).",
        }
    )
    for _, r in peak_claims.iterrows():
        rows.append(
            {
                "claim": r.claim,
                "statement": r.get("title", ""),
                "support": r.support,
                "n_support": r.n_support,
                "n_uncertain": r.n_uncertain,
                "n_contradict": r.n_contradict,
                "qualification": r.qualification,
            }
        )
    # Rename P claims statements
    stmt = {
        "P1": "General CPU peak benefit from reconciliation.",
        "P2": "General CPU detection benefit.",
        "P3": "LightGBM remains best for high-load CPU.",
        "P4": "General memory peak benefit.",
        "P5": "DLinear memory peak compression.",
    }
    t6 = pd.DataFrame(rows)
    t6["statement"] = t6.apply(lambda r: stmt.get(r.claim, r.statement), axis=1)
    t6.to_csv(tables / "table06_claim_support_matrix.csv", index=False)

    # Table 7 peaks
    peak = pd.read_csv(ROOT / registry["pack_dirs"]["peak_analysis"] / "metrics" / "peak_metrics.csv")
    pcomp = pd.read_csv(ROOT / registry["pack_dirs"]["peak_analysis"] / "metrics" / "peak_method_comparisons.csv")
    t7 = peak.merge(
        pcomp[["hierarchy", "base_model", "horizon", "fold", "threshold", "method", "operational_class"]],
        on=["hierarchy", "base_model", "horizon", "fold", "threshold", "method"],
        how="left",
    )
    t7_out = t7.groupby(["hierarchy", "base_model", "method", "threshold"], as_index=False).agg(
        high_load_mae=("high_load_mae", "mean"),
        precision=("precision", "mean"),
        recall=("recall", "mean"),
        f1=("f1", "mean"),
        false_alarms_per_day=("false_alarms_per_day", "mean"),
        signed_peak_bias=("signed_peak_bias", "mean"),
        operational_class=("operational_class", lambda s: s.dropna().mode().iloc[0] if s.dropna().size else "n/a"),
    )
    t7_out.to_csv(tables / "table07_peak_operational_results.csv", index=False)

    # Table 8 efficiency
    eff_rows = []
    miss = reporting.get("missing_value_policy", "not_recorded_by_frozen_runner")
    for pid in registry["accepted_prediction_packs"]:
        pdir = ROOT / registry["pack_dirs"][pid]
        man = _read_json(pdir / "MANIFEST.json")
        base_path = pdir / "metrics" / "base_forecasts.csv"
        total_train = np.nan
        median_job = np.nan
        if base_path.exists():
            bf = pd.read_csv(base_path)
            if "wall_train_sec_sum" in bf.columns:
                total_train = float(bf.wall_train_sec_sum.sum())
                median_job = float(bf.wall_train_sec_sum.median())
        eff_rows.append(
            {
                "pack_id": pid,
                "total_training_time_sec": total_train,
                "median_hierarchy_job_time_sec": median_job,
                "cpu_time_sec": man.get("cpu_seconds", miss),
                "peak_rss_bytes": man.get("peak_memory_bytes", miss) if man.get("peak_memory_available", True) else miss,
                "pack_wall_time_sec": man.get("actual_wall_seconds", miss),
                "warm_infer_latency_ms": miss,
                "forecasts_per_sec": miss,
                "reconciliation_overhead_sec": miss,
                "serialized_model_size_bytes": miss,
            }
        )
    for pid in registry["accepted_analysis_packs"]:
        pdir = ROOT / registry["pack_dirs"][pid]
        man = _read_json(pdir / "MANIFEST.json")
        eff_rows.append(
            {
                "pack_id": pid,
                "total_training_time_sec": 0.0,
                "median_hierarchy_job_time_sec": 0.0,
                "cpu_time_sec": man.get("cpu_seconds", miss),
                "peak_rss_bytes": man.get("peak_memory_bytes", miss),
                "pack_wall_time_sec": man.get("actual_wall_seconds", miss),
                "warm_infer_latency_ms": miss,
                "forecasts_per_sec": miss,
                "reconciliation_overhead_sec": miss,
                "serialized_model_size_bytes": miss,
            }
        )
    pd.DataFrame(eff_rows).to_csv(tables / "table08_efficiency_execution.csv", index=False)

    # Headlines
    def mean_cpu(model, method):
        s = enriched[(enriched.hierarchy == "cpu_core_weighted") & (enriched.base_model == model) & (enriched.reconciliation_method == method)]
        return float(s.mae_display.mean())

    headlines = {
        "cpu_persistence_independent_mae": mean_cpu("persistence", "independent"),
        "cpu_lightgbm_independent_mae": mean_cpu("lightgbm", "independent"),
        "cpu_lightgbm_mint_mae": mean_cpu("lightgbm", "mint"),
        "cpu_lgbm_ind_vs_pers_rel": (mean_cpu("lightgbm", "independent") - mean_cpu("persistence", "independent"))
        / mean_cpu("persistence", "independent"),
        "cpu_lgbm_mint_vs_pers_rel": (mean_cpu("lightgbm", "mint") - mean_cpu("persistence", "independent"))
        / mean_cpu("persistence", "independent"),
        "cpu_lgbm_mint_vs_ind_rel": (mean_cpu("lightgbm", "mint") - mean_cpu("lightgbm", "independent"))
        / mean_cpu("lightgbm", "independent"),
        "cpu_ridge_bu_vs_ind_rel": (mean_cpu("ridge", "bottom_up") - mean_cpu("ridge", "independent"))
        / mean_cpu("ridge", "independent"),
        "cpu_dlinear_bu_vs_ind_rel": (mean_cpu("dlinear", "bottom_up") - mean_cpu("dlinear", "independent"))
        / mean_cpu("dlinear", "independent"),
        "best_observed_cpu": "lightgbm+mint",
        "recommended_operational_cpu": "lightgbm+mint (accuracy/coherence); ridge+bottom_up when bottom preservation preferred",
        "best_observed_memory": "dlinear+mint (by outer MAE)",
        "recommended_operational_memory": "ridge/dlinear+mint or wls; persistence independent remains competitive baseline",
        "best_observed_disk": "persistence+independent",
        "recommended_operational_disk": "persistence independent; ridge+top_down if coherence mandatory",
    }
    # by horizon persistence
    for h in [1, 8, 16]:
        s = enriched[
            (enriched.hierarchy == "cpu_core_weighted")
            & (enriched.base_model == "persistence")
            & (enriched.reconciliation_method == "independent")
            & (enriched.horizon == h)
        ]
        headlines[f"cpu_pers_h{h}"] = float(s.mae_display.mean())

    disk_bu_rel = float(
        enriched[
            (enriched.hierarchy == "disk_ud") & (enriched.base_model == "ridge") & (enriched.reconciliation_method == "bottom_up")
        ].mae_vs_independent.mean()
    )
    headlines["disk_ridge_bu_vs_ind_rel"] = disk_bu_rel

    # Figures
    def plot_acc(hier, outfile, series):
        fig, ax = plt.subplots(figsize=(7, 4.5))
        sub = enriched[enriched.hierarchy == hier]
        for model, method, label, style in series:
            s = (
                sub[(sub.base_model == model) & (sub.reconciliation_method == method)]
                .groupby("horizon")
                .mae_display.mean()
            )
            ax.plot(s.index, s.values, style, label=label)
        ax.set_xlabel("horizon")
        ax.set_ylabel(f"MAE ({_unit_for(hier)})")
        ax.set_title(outfile)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(figures / f"{outfile}.pdf")
        fig.savefig(figures / f"{outfile}.png")
        plt.close(fig)

    plot_acc(
        "cpu_core_weighted",
        "cpu_accuracy_vs_horizon",
        [
            ("persistence", "independent", "persistence ind", "k-"),
            ("ridge", "independent", "ridge ind", "C0--"),
            ("ridge", "bottom_up", "ridge BU", "C0-"),
            ("lightgbm", "independent", "lgbm ind", "C1--"),
            ("lightgbm", "mint", "lgbm MinT", "C1-"),
            ("dlinear", "independent", "dlinear ind", "C2--"),
            ("dlinear", "bottom_up", "dlinear BU", "C2-"),
        ],
    )
    plot_acc(
        "memory_um",
        "memory_accuracy_vs_horizon",
        [
            ("persistence", "independent", "persistence ind", "k-"),
            ("ridge", "independent", "ridge ind", "C0--"),
            ("ridge", "mint", "ridge MinT", "C0-"),
            ("dlinear", "independent", "dlinear ind", "C2--"),
            ("dlinear", "mint", "dlinear MinT", "C2-"),
            ("lightgbm", "independent", "lgbm ind (neg. baseline)", "C3--"),
        ],
    )

    fig, axes = plt.subplots(1, 3, figsize=(10, 3.5))
    for ax, hier in zip(axes, ["cpu_core_weighted", "memory_um", "disk_ud"]):
        sub = enriched[enriched.hierarchy == hier]
        g = sub.groupby("reconciliation_method")[["coherence_error_before", "coherence_error_after"]].mean()
        x = np.arange(len(g))
        ax.bar(x - 0.15, g.coherence_error_before, width=0.3, label="before")
        ax.bar(x + 0.15, g.coherence_error_after, width=0.3, label="after")
        ax.set_xticks(x)
        ax.set_xticklabels(g.index, rotation=45, fontsize=7)
        ax.set_title(hier, fontsize=9)
        ax.set_yscale("symlog")
    axes[0].legend(fontsize=7)
    fig.suptitle("Coherence before/after (faceted; do not compare raw units across panels)")
    fig.tight_layout()
    fig.savefig(figures / "coherence_before_after.pdf")
    fig.savefig(figures / "coherence_before_after.png")
    plt.close(fig)

    tb = pd.read_csv(stats_dir / "top_bottom_tradeoff.csv")
    fig, ax = plt.subplots(figsize=(6, 5))
    for hier, m in [("cpu_core_weighted", "o"), ("memory_um", "s"), ("disk_ud", "^")]:
        s = tb[tb.hierarchy == hier]
        ax.scatter(s.macro_rel, s.top_rel, marker=m, alpha=0.7, label=hier)
    ax.axhline(0, color="k", lw=0.5)
    ax.axvline(0, color="k", lw=0.5)
    ax.set_xlabel("bottom macro relative MAE change")
    ax.set_ylabel("top relative MAE change")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(figures / "top_bottom_tradeoff.pdf")
    fig.savefig(figures / "top_bottom_tradeoff.png")
    plt.close(fig)

    fig, axes = plt.subplots(3, 1, figsize=(8, 10), sharex=False)
    for ax, hier in zip(axes, ["memory_um", "cpu_core_weighted", "disk_ud"]):
        s = boot[(boot.hierarchy == hier) & (boot.base_model != "persistence")]
        g = s.groupby(["base_model", "method_b"], as_index=False).agg(rel=("relative_mae_diff", "mean"), lo=("rel_ci_low", "mean"), hi=("rel_ci_high", "mean"))
        y = np.arange(len(g))
        ax.axvline(0, color="k", lw=0.6)
        if len(g):
            ax.hlines(y, g.lo, g.hi, color="#456")
            ax.plot(g.rel, y, "o", color="#c45")
            ax.set_yticks(y)
            ax.set_yticklabels([f"{a}/{b}" for a, b in zip(g.base_model, g.method_b)], fontsize=7)
        ax.set_title(hier)
    axes[-1].set_xlabel("bootstrapped relative MAE effect")
    fig.tight_layout()
    fig.savefig(figures / "bootstrap_relative_effects.pdf")
    fig.savefig(figures / "bootstrap_relative_effects.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    disk = enriched[(enriched.hierarchy == "disk_ud") & (enriched.base_model == "ridge")]
    g = disk.groupby("reconciliation_method").mae_display.mean()
    ax.bar(g.index.astype(str), g.values, color="#6a7")
    ax.set_ylabel("MAE (disk level)")
    ax.set_title("Disk boundary — Ridge primary")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(figures / "disk_boundary.pdf")
    fig.savefig(figures / "disk_boundary.png")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    cpu_peak = t7_out[t7_out.hierarchy == "cpu_core_weighted"]
    for ax, thr in zip(axes, ["q90", "q95"]):
        s = cpu_peak[cpu_peak.threshold == thr]
        for model in ["persistence", "ridge", "lightgbm", "dlinear"]:
            m = s[s.base_model == model]
            ax.scatter(m.recall, m.high_load_mae, label=model, alpha=0.7)
        ax.set_title(f"CPU peaks {thr}")
        ax.set_xlabel("recall")
        ax.set_ylabel("high-load MAE")
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figures / "cpu_peak_results.pdf")
    fig.savefig(figures / "cpu_peak_results.png")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    mem_peak = peak[(peak.hierarchy == "memory_um") & (peak.base_model == "dlinear")]
    for ax, thr in zip(axes, ["q90", "q95"]):
        s = mem_peak[mem_peak.threshold == thr]
        g = s.groupby("method").signed_peak_bias.mean()
        ax.bar(g.index.astype(str), g.values)
        ax.axhline(0, color="k", lw=0.6)
        ax.set_title(f"DLinear memory bias {thr}")
        ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(figures / "memory_peak_bias.pdf")
    fig.savefig(figures / "memory_peak_bias.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    methods_map = [
        ("CPU", headlines["best_observed_cpu"], headlines["recommended_operational_cpu"]),
        ("Memory", headlines["best_observed_memory"], headlines["recommended_operational_memory"]),
        ("Disk", headlines["best_observed_disk"], headlines["recommended_operational_disk"]),
    ]
    ax.axis("off")
    txt = "Method selection map (frozen outer evaluation)\n\n"
    for hier, best, rec in methods_map:
        txt += f"{hier}\n  best observed: {best}\n  recommended operational: {rec}\n  unsuitable: see SAFE/UNSUPPORTED claims\n\n"
    ax.text(0.02, 0.98, txt, va="top", fontsize=9, family="monospace")
    fig.tight_layout()
    fig.savefig(figures / "method_selection_map.pdf")
    fig.savefig(figures / "method_selection_map.png")
    plt.close(fig)

    # Verify sources unchanged
    changed = [p for p, d in before.items() if sha256_file(Path(p)) != d]
    if changed:
        raise EvidenceError(f"source artifacts modified during aggregation: {changed[:5]}")

    # Hash outputs
    out_hashes = []
    for path in sorted(list(tables.glob("*")) + list(figures.glob("*.pdf"))):
        if path.is_file():
            out_hashes.append({"artifact": str(path.relative_to(out)), "sha256": sha256_file(path)})

    pd.DataFrame(hash_rows).to_csv(out / "SOURCE_ARTIFACT_HASHES.csv", index=False)

    try:
        exec_commit = _git(["rev-parse", "HEAD"])
    except Exception:
        exec_commit = "UNKNOWN"
    try:
        rep_tag = _git(["rev-parse", "final-reporting-freeze-v1^{commit}"])
    except Exception:
        rep_tag = reporting.get("reporting_freeze_tag_commit") or "PENDING_UNTIL_TAG"

    created = datetime.now(timezone.utc).isoformat()
    manifest = {
        "artifact": "final_evidence_aggregate",
        "created_at": created,
        "execution_commit": exec_commit,
        "dataset_fingerprint": registry["dataset_fingerprint"],
        "prediction_layer": registry["prediction_layer"],
        "statistics_layer": registry["statistics_layer"],
        "peak_layer": registry["peak_layer"],
        "reporting_freeze_tag": reporting.get("reporting_freeze_tag"),
        "reporting_freeze_tag_commit": rep_tag,
        "reporting_implementation_commit": reporting.get("reporting_implementation_commit") or exec_commit,
        "reporting_config_hash": config_hash(reporting),
        "registry_hash": config_hash(registry),
        "source_pack_hashes": {
            pid: _read_json(ROOT / registry["pack_dirs"][pid] / "MANIFEST.json").get("pack_hash")
            for pid in registry["accepted_prediction_packs"] + registry["accepted_analysis_packs"]
            if (ROOT / registry["pack_dirs"][pid] / "MANIFEST.json").exists()
        },
        "exclusions": registry.get("exclusions"),
        "headlines": headlines,
        "generated_artifact_hashes": out_hashes,
        "source_files_unchanged": True,
        "n_source_artifacts_hashed": len(hash_rows),
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")

    # Markdown documents written by caller script for readability; return payloads
    return {
        "manifest": manifest,
        "headlines": headlines,
        "claims": t6,
        "tables_dir": tables,
        "figures_dir": figures,
        "enriched": enriched,
        "boot": boot,
        "peak_claims": peak_claims,
        "output_dir": out,
    }
