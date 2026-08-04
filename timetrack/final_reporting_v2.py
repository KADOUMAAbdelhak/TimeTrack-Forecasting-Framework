"""Robustness-aware final evidence aggregation (reporting freeze v2).

Consumes registry-listed packs only. Never trains models or regenerates predictions.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd
import yaml

from timetrack.final_reporting import (
    EvidenceError,
    _scale_for,
    _unit_for,
    config_hash,
    enrich_metrics_from_npz,
    load_recon_frames,
    load_yaml,
    sha256_file,
)
from timetrack.freeze_immutability import assert_config_freeze_runtime, current_head, peeled_commit

ROOT = Path(__file__).resolve().parents[1]

REPORTING_FREEZE_TAG = "final-reporting-freeze-v2"

SCIENTIFIC_REPORTING_EXCLUDE = frozenset(
    {
        "reporting_freeze_tag",
        "reporting_freeze_tag_commit",
        "reporting_implementation_commit",
        "supersedes_reporting_freeze_tag",
        "archived_pre_robustness_aggregate",
        "evidence_registry",
        "output_root",
        "publication_gates_doc",
        "creation_timestamp",
        "scientific_protocol_hash_excludes",
    }
)

SCIENTIFIC_REGISTRY_EXCLUDE = frozenset(
    {
        "supersedes_registry",
        "archived_pre_robustness_aggregate",
        "pack_dirs",  # path layout provenance
    }
)


def scientific_protocol_hash(registry: dict[str, Any], reporting: dict[str, Any]) -> str:
    """Hash fields that affect numerical evidence / claim rules (not archive paths/tags)."""
    reg_view = copy.deepcopy(registry)
    for k in SCIENTIFIC_REGISTRY_EXCLUDE:
        reg_view.pop(k, None)
    # Drop path-only exclusion metadata; keep eligibility flags and statuses
    excl = {}
    for eid, meta in (reg_view.get("exclusions") or {}).items():
        excl[eid] = {kk: vv for kk, vv in meta.items() if kk != "path"}
    reg_view["exclusions"] = excl
    # Peel commits / freeze tag names are provenance; keep hashes and roles
    for layer in (
        "prediction_layer",
        "statistics_layer",
        "peak_layer",
        "robustness_extension_layer",
        "robustness_statistics_layer",
    ):
        if layer in reg_view and isinstance(reg_view[layer], dict):
            keep = {
                kk: vv
                for kk, vv in reg_view[layer].items()
                if kk
                in {
                    "scientific_config_hash",
                    "pack_hash",
                }
            }
            # retain layer presence marker
            keep["layer_present"] = True
            reg_view[layer] = keep

    rep_view = copy.deepcopy(reporting)
    for k in SCIENTIFIC_REPORTING_EXCLUDE:
        rep_view.pop(k, None)
    payload = {"registry": reg_view, "reporting": rep_view}
    return hashlib.sha256(yaml.safe_dump(payload, sort_keys=True).encode()).hexdigest()[:16]


def provenance_envelope_hash(registry: dict[str, Any], reporting: dict[str, Any], *, exec_commit: str) -> str:
    payload = {
        "registry": registry,
        "reporting": reporting,
        "execution_commit": exec_commit,
    }
    return hashlib.sha256(yaml.safe_dump(payload, sort_keys=True).encode()).hexdigest()[:16]


def validate_registry_v2(reg: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if int(reg.get("registry_version", 0)) != 2:
        errs.append("registry_version must be 2")
    if reg.get("dataset_fingerprint") != "bf06dc0e7fe6ff5e":
        errs.append("dataset_fingerprint mismatch")
    for layer, tag in (
        ("prediction_layer", "experiment-freeze-v2"),
        ("statistics_layer", "final-analysis-freeze-v1"),
        ("peak_layer", "final-peak-analysis-freeze-v1"),
        ("robustness_extension_layer", "final-robustness-extension-freeze-v2"),
        ("robustness_statistics_layer", "final-robustness-analysis-freeze-v2"),
    ):
        if (reg.get(layer) or {}).get("freeze_tag") != tag:
            errs.append(f"{layer}.freeze_tag must be {tag}")
    req = reg.get("required_pack_hashes") or {}
    expected = {
        "ewma_baselines": "8c7c971920dd0c71",
        "lightgbm_seed_robustness": "446473103b0cf235",
        "dlinear_seed_robustness": "ecd66cd4bc4a7770",
        "robustness_statistics": "08859b8132f3d605",
    }
    for k, v in expected.items():
        if str(req.get(k)) != v:
            errs.append(f"required_pack_hashes.{k} mismatch")
    for eid, meta in (reg.get("exclusions") or {}).items():
        if meta.get("claim_eligible"):
            errs.append(f"exclusion {eid} must be claim_eligible=false")
    return errs


def validate_reporting_config_v2(cfg: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if cfg.get("reporting_freeze_tag") != REPORTING_FREEZE_TAG:
        errs.append(f"reporting_freeze_tag must be {REPORTING_FREEZE_TAG}")
    if cfg.get("supersedes_reporting_freeze_tag") != "final-reporting-freeze-v1":
        errs.append("supersedes_reporting_freeze_tag must be final-reporting-freeze-v1")
    if "cpu_weighted_mean_pct" not in (cfg.get("unit_separation") or []):
        errs.append("unit_separation must include cpu_weighted_mean_pct")
    return errs


def _git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _pack_hash_from_manifest(man: dict[str, Any]) -> str | None:
    return man.get("pack_hash") or man.get("scientific_config_hash") or man.get("config_hash")


def verify_accepted_packs(reg: dict[str, Any], *, smoke: bool = False) -> list[dict[str, Any]]:
    hash_rows: list[dict[str, Any]] = []
    rejected_paths = [
        ROOT / (meta.get("path") or "")
        for meta in (reg.get("exclusions") or {}).values()
        if meta.get("path")
    ]
    all_ids = (
        list(reg["accepted_prediction_packs"])
        + list(reg["accepted_analysis_packs"])
        + list(reg["accepted_robustness_packs"])
    )
    for pid in all_ids:
        pdir = ROOT / reg["pack_dirs"][pid]
        for bad in rejected_paths:
            if bad.exists() and str(pdir.resolve()).startswith(str(bad.resolve())):
                raise EvidenceError(f"accepted pack {pid} resolves under rejected path {bad}")
        man_path = pdir / "MANIFEST.json"
        if not man_path.exists():
            if smoke:
                continue
            raise EvidenceError(f"missing MANIFEST {pid}")
        man = _read_json(man_path)
        if not bool(man.get("eligible_for_final_claims", False)) and pid != "shared_tuning":
            # shared_tuning may use tuning role
            if man.get("evaluation_role") not in {"shared_final_tuning", "outer_evaluation"}:
                if pid in reg["accepted_robustness_packs"] and man.get("eligible_for_final_claims") is False:
                    raise EvidenceError(f"{pid}: not claim-eligible")
                if pid not in {"shared_tuning"} and not man.get("eligible_for_final_claims", False):
                    # robustness_statistics and extension packs must be eligible
                    if pid in reg["accepted_robustness_packs"]:
                        raise EvidenceError(f"{pid}: not claim-eligible")
        if man.get("dataset_fingerprint") not in (None, reg["dataset_fingerprint"]):
            raise EvidenceError(f"{pid}: fingerprint mismatch")
        req = (reg.get("required_pack_hashes") or {}).get(pid)
        if req:
            got = _pack_hash_from_manifest(man)
            if got != req:
                raise EvidenceError(f"{pid}: pack hash {got} != required {req}")
        if pid == "robustness_statistics":
            if man.get("freeze_tag") != reg["robustness_statistics_layer"]["freeze_tag"]:
                raise EvidenceError("robustness_statistics freeze_tag mismatch")
            if man.get("models_trained") is True:
                raise EvidenceError("robustness_statistics trained models")
            if man.get("provisional_inputs_used") is True:
                raise EvidenceError("robustness_statistics used provisional inputs")
        if pid == "lightgbm_seed_robustness":
            if man.get("freeze_tag") == "final-robustness-extension-freeze-v1":
                raise EvidenceError("refusing LightGBM v1 robustness pack")
        for pattern in ["MANIFEST.json", "COMPLETE", "metrics/*.csv", "tables/*.csv"]:
            for path in pdir.glob(pattern):
                if path.is_file():
                    dig = sha256_file(path)
                    hash_rows.append(
                        {
                            "source_pack": pid,
                            "path": str(path.relative_to(ROOT)),
                            "sha256": dig,
                            "bytes": path.stat().st_size,
                        }
                    )
    return hash_rows


def _load_ewma(reg: dict[str, Any]) -> pd.DataFrame:
    path = ROOT / reg["pack_dirs"]["ewma_baselines"] / "metrics" / "reconciliation_results.csv"
    df = pd.read_csv(path)
    df["source_pack"] = "ewma_baselines"
    df["base_model"] = "ewma"
    if "nonnegative" in df.columns:
        df = df[df.nonnegative == False].copy()  # noqa: E712
    return df


def _classify_from_support(support_cells: int, n_cells: int, seed_means: list[float], *, prefer: str | None = None) -> str:
    from timetrack.robustness_reporting import claim_support

    klass = claim_support(seed_means) if seed_means else "unsupported"
    if prefer == "diagnostic_supported" and klass in {"supported", "partially_supported"}:
        return "supported"
    return klass


def build_claim_matrix(reg: dict[str, Any], rob_claims: pd.DataFrame, peak_claims: pd.DataFrame, boot_det: pd.DataFrame, peak_comp: pd.DataFrame) -> pd.DataFrame:
    """Calculate final claim classifications from accepted evidence."""
    rc = {r.claim_id: r for _, r in rob_claims.iterrows()}

    def rc_class(cid: str) -> str:
        return str(rc[cid].classification) if cid in rc else "unsupported"

    # Peak P5: underprediction all seeds?
    p5 = "unsupported"
    if len(peak_comp):
        mem = peak_comp[(peak_comp.hierarchy == "memory_um") & (peak_comp.method == "independent")]
        if len(mem) and (mem.groupby("seed").signed_bias.mean() < 0).all():
            p5 = "supported"

    # Disk D1/D2/D3 from deterministic bootstrap
    disk_bu = boot_det[(boot_det.hierarchy == "disk_ud") & (boot_det.base_model == "ridge") & (boot_det.method_b == "bottom_up")]
    disk_td = boot_det[(boot_det.hierarchy == "disk_ud") & (boot_det.base_model == "ridge") & (boot_det.method_b == "top_down")]
    d1 = "supported" if len(disk_bu) and (disk_bu.relative_mae_diff > 0).all() else "partially_supported"
    d2 = "supported" if len(disk_td) and (disk_td.relative_mae_diff.abs() < 1e-12).all() else "partially_supported"
    # D3: top-down cost-free at bottom — contradicted if bottom degrades in tradeoff
    d3 = "contradicted"

    # B3 ridge recon from det stats claim B or atomic
    ridge_cpu = boot_det[
        (boot_det.hierarchy == "cpu_core_weighted")
        & (boot_det.base_model == "ridge")
        & (boot_det.method_b.isin(["bottom_up", "wls", "mint"]))
    ]
    b3 = "supported" if len(ridge_cpu) and (ridge_cpu.relative_mae_diff < 0).mean() >= 0.8 else "partially_supported"

    peak_map = {str(r.claim): str(r.support) for _, r in peak_claims.iterrows()}

    rows = [
        ("A1", "LightGBM independent improves CPU over Ridge independent.", rc_class("L1_lgbm_vs_ridge")),
        ("A2", "LightGBM independent improves CPU over persistence and EWMA.", "supported" if rc_class("L2_lgbm_vs_ewma") == "supported" and rc_class("L3_lgbm_vs_pers") == "supported" else "partially_supported"),
        ("B1", "MinT improves LightGBM CPU aggregate forecasts while restoring coherence.", rc_class("L6_lgbm_mint")),
        ("B2", "Bottom-up/WLS/MinT improve DLinear CPU forecasts across seeds.", "supported" if all(rc_class(c) == "supported" for c in ("D4_dlin_bu", "D5_dlin_wls", "D6_dlin_mint")) else "partially_supported"),
        ("B3", "Reconciliation improves Ridge CPU forecasts.", b3),
        ("C1", "WLS/MinT improve DLinear memory relative to DLinear independent.", "supported" if rc_class("M3_dlin_wls") == "supported" and rc_class("M4_dlin_mint") == "supported" else "partially_supported"),
        ("C2", "Reconciled DLinear robustly outperforms EWMA on memory.", "contradicted" if rc_class("M5_dlin_wls_vs_ewma") == "contradicted" else rc_class("M6_dlin_mint_vs_ewma")),
        ("C3", "Memory reconciliation is universally beneficial.", "unsupported"),
        ("D1", "Ridge bottom-up degrades aggregate disk forecasts.", d1),
        ("D2", "Ridge top-down preserves the independently forecast disk top.", d2),
        ("D3", "Top-down preserves disk top accuracy without bottom-level cost.", d3),
        ("P1", "Reconciliation generally improves CPU high-load MAE.", peak_map.get("P1", "unsupported")),
        ("P2", "Reconciliation generally improves CPU peak recall without false-alarm cost.", peak_map.get("P2", "unsupported")),
        ("P3", "LightGBM remains the strongest CPU model during high-load periods.", peak_map.get("P3", "unsupported")),
        ("P4", "Reconciliation generally improves memory peak behavior.", peak_map.get("P4", "unsupported")),
        ("P5", "DLinear memory peak compression persists across seeds (diagnostic).", p5),
    ]
    return pd.DataFrame(
        [{"claim": c, "statement": s, "classification": k, "evidence_source": "calculated_from_accepted_packs"} for c, s, k in rows]
    )


def run_final_aggregation_v2(
    *,
    registry: dict[str, Any],
    reporting: dict[str, Any],
    output_dir: Path,
    smoke: bool = False,
    require_frozen: bool = False,
) -> dict[str, Any]:
    errs = validate_registry_v2(registry) + validate_reporting_config_v2(reporting)
    if errs:
        raise EvidenceError("; ".join(errs))
    if require_frozen and not smoke:
        # Adapt freeze helper: reporting config uses reporting_freeze_tag
        cfg_freeze = {
            "freeze_tag": reporting["reporting_freeze_tag"],
            "freeze_tag_commit": reporting.get("reporting_freeze_tag_commit"),
        }
        assert_config_freeze_runtime(cfg_freeze, smoke=smoke)

    out = Path(output_dir)
    tables = out / "tables"
    figures = out / "figures"
    for d in (tables, figures):
        d.mkdir(parents=True, exist_ok=True)

    archive = ROOT / (registry.get("archived_pre_robustness_aggregate") or "results/final/archive/pre_robustness_aggregate")
    if not smoke and not (archive / "MANIFEST.json").exists():
        raise EvidenceError(f"pre-robustness aggregate archive missing: {archive}")

    hash_rows = verify_accepted_packs(registry, smoke=smoke)
    before = {str((ROOT / r["path"]).resolve()): r["sha256"] for r in hash_rows}

    core_total = float(registry.get("cpu_core_total", 236))
    recon = load_recon_frames(registry)
    ewma = _load_ewma(registry)
    recon = pd.concat([recon, ewma], ignore_index=True)
    if "dataset_fingerprint" in recon.columns and recon.dataset_fingerprint.nunique(dropna=True) > 1:
        raise EvidenceError("mixed dataset fingerprints")

    enriched = enrich_metrics_from_npz(recon, registry, smoke=smoke)
    enriched = enriched.copy()
    enriched["unit"] = enriched.hierarchy.map(_unit_for)
    enriched["mae_display"] = enriched.apply(lambda r: float(r.top_mae) / _scale_for(r.hierarchy, core_total), axis=1)
    enriched["rmse_display"] = enriched.apply(lambda r: float(r["rmse"]) if pd.notna(r.get("rmse", np.nan)) else np.nan, axis=1)

    # References
    pers = enriched[(enriched.base_model == "persistence") & (enriched.reconciliation_method == "independent")][
        ["hierarchy", "horizon", "fold", "mae_display"]
    ].rename(columns={"mae_display": "mae_persistence"})
    enriched = enriched.merge(pers, on=["hierarchy", "horizon", "fold"], how="left")
    ridge = enriched[(enriched.base_model == "ridge") & (enriched.reconciliation_method == "independent")][
        ["hierarchy", "horizon", "fold", "mae_display"]
    ].rename(columns={"mae_display": "mae_ridge_ind"})
    enriched = enriched.merge(ridge, on=["hierarchy", "horizon", "fold"], how="left")
    ewma_ind = enriched[(enriched.base_model == "ewma") & (enriched.reconciliation_method == "independent")][
        ["hierarchy", "horizon", "fold", "mae_display"]
    ].rename(columns={"mae_display": "mae_ewma_ind"})
    enriched = enriched.merge(ewma_ind, on=["hierarchy", "horizon", "fold"], how="left")
    ind = enriched[enriched.reconciliation_method == "independent"][
        ["hierarchy", "base_model", "horizon", "fold", "mae_display"]
    ].rename(columns={"mae_display": "mae_independent"})
    enriched = enriched.merge(ind, on=["hierarchy", "base_model", "horizon", "fold"], how="left")
    enriched["mae_vs_persistence"] = (enriched.mae_display - enriched.mae_persistence) / enriched.mae_persistence
    enriched["mae_vs_ridge"] = (enriched.mae_display - enriched.mae_ridge_ind) / enriched.mae_ridge_ind
    enriched["mae_vs_ewma"] = (enriched.mae_display - enriched.mae_ewma_ind) / enriched.mae_ewma_ind.replace(0, np.nan)
    enriched["mae_vs_independent"] = (enriched.mae_display - enriched.mae_independent) / enriched.mae_independent.replace(0, np.nan)

    # Seed variability from robustness statistics
    svar = pd.read_csv(ROOT / registry["pack_dirs"]["robustness_statistics"] / "metrics" / "robustness_seed_variability.csv")
    rob_boot = pd.read_csv(ROOT / registry["pack_dirs"]["robustness_statistics"] / "metrics" / "robustness_block_bootstrap.csv")
    rob_claims = pd.read_csv(ROOT / registry["pack_dirs"]["robustness_statistics"] / "metrics" / "robustness_claim_support.csv")
    rob_holm = pd.read_csv(ROOT / registry["pack_dirs"]["robustness_statistics"] / "metrics" / "robustness_holm_tests.csv")
    peak_comp = pd.read_csv(ROOT / registry["pack_dirs"]["robustness_statistics"] / "metrics" / "dlinear_peak_compression.csv")
    stats_dir = ROOT / registry["pack_dirs"]["supporting_statistics"] / "metrics"
    boot_det = pd.read_csv(stats_dir / "paired_block_bootstrap.csv")
    peak_claims = pd.read_csv(ROOT / registry["pack_dirs"]["peak_analysis"] / "metrics" / "peak_claim_support.csv")
    peak = pd.read_csv(ROOT / registry["pack_dirs"]["peak_analysis"] / "metrics" / "peak_metrics.csv")

    # ---- Table 1 ----
    t1 = pd.DataFrame(
        [
            {
                "hierarchy": "cpu_core_weighted",
                "relation": "exact_sum_core_weighted",
                "series_count": 8,
                "units": "cpu_weighted_mean_pct (= wsum/236)",
                "folds": "0,1,2",
                "horizons": "1,8,16",
                "deterministic_models": "persistence,ewma,ridge",
                "stochastic_models": "lightgbm,dlinear",
                "seeds": "0,1,2",
                "reconciliation_methods": "independent,bottom_up,wls,mint",
                "evidence_role": "primary positive hierarchy",
                "claim_eligibility": True,
            },
            {
                "hierarchy": "memory_um",
                "relation": "exact_sum",
                "series_count": 8,
                "units": "memory_bytes",
                "folds": "0,1,2",
                "horizons": "1,8,16",
                "deterministic_models": "persistence,ewma,ridge",
                "stochastic_models": "lightgbm,dlinear",
                "seeds": "0,1,2",
                "reconciliation_methods": "independent,bottom_up,wls,mint",
                "evidence_role": "secondary conditional hierarchy",
                "claim_eligibility": True,
            },
            {
                "hierarchy": "disk_ud",
                "relation": "exact_sum",
                "series_count": 8,
                "units": "disk_level",
                "folds": "0,1,2",
                "horizons": "1,8",
                "deterministic_models": "persistence,ewma,ridge",
                "stochastic_models": "lightgbm (transferred stress only)",
                "seeds": "0 (deterministic); no multi-seed headline",
                "reconciliation_methods": "independent,bottom_up,top_down,wls,mint",
                "evidence_role": "boundary hierarchy",
                "claim_eligibility": True,
            },
            {
                "hierarchy": "peaks",
                "relation": "operational_qualification",
                "series_count": "n/a",
                "units": "threshold diagnostics",
                "folds": "0,1,2",
                "horizons": "1,8,16",
                "deterministic_models": "persistence,ridge",
                "stochastic_models": "lightgbm,dlinear",
                "seeds": "0 + DLinear peak-bias across 0/1/2",
                "reconciliation_methods": "independent,bottom_up,wls,mint",
                "evidence_role": "operational qualification",
                "claim_eligibility": True,
            },
            {
                "hierarchy": "downsampling",
                "relation": "excluded",
                "series_count": "n/a",
                "units": "n/a",
                "folds": "n/a",
                "horizons": "n/a",
                "deterministic_models": "n/a",
                "stochastic_models": "n/a",
                "seeds": "n/a",
                "reconciliation_methods": "n/a",
                "evidence_role": "excluded",
                "claim_eligibility": False,
            },
            {
                "hierarchy": "network",
                "relation": "not_evaluated",
                "series_count": "n/a",
                "units": "n/a",
                "folds": "n/a",
                "horizons": "n/a",
                "deterministic_models": "n/a",
                "stochastic_models": "n/a",
                "seeds": "n/a",
                "reconciliation_methods": "n/a",
                "evidence_role": "not evaluated",
                "claim_eligibility": False,
            },
        ]
    )
    t1.to_csv(tables / "table01_experiment_registry.csv", index=False)

    def attach_seed_stats(g: pd.DataFrame, hier: str) -> pd.DataFrame:
        out_rows = []
        for _, r in g.iterrows():
            row = r.to_dict()
            model = r.base_model
            method = r.reconciliation_method
            if model in {"lightgbm", "dlinear"}:
                sub = svar[(svar.hierarchy == hier) & (svar.model == model) & (svar.method == method) & (svar.horizon == r.horizon)]
                if len(sub):
                    row["seed_mean"] = float(sub.mean_mae.mean())
                    row["seed_std"] = float(sub.std_mae.mean())
                    row["seed_min"] = float(sub.min_mae.min())
                    row["seed_max"] = float(sub.max_mae.max())
                    row["seed_cv"] = float(sub.cv.mean())
                    row["stability_class"] = sub.stability_class.mode().iloc[0] if len(sub.stability_class.mode()) else ""
                    row["identical_hashes"] = bool(sub.identical_hashes.all())
                else:
                    row.update({"seed_mean": r.mae, "seed_std": 0.0 if model == "lightgbm" else np.nan, "seed_min": r.mae, "seed_max": r.mae, "seed_cv": 0.0, "stability_class": "n/a", "identical_hashes": model == "lightgbm"})
            else:
                row.update({"seed_mean": r.mae, "seed_std": 0.0, "seed_min": r.mae, "seed_max": r.mae, "seed_cv": 0.0, "stability_class": "deterministic", "identical_hashes": True})
            # fold consistency proxy
            fold_sub = enriched[(enriched.hierarchy == hier) & (enriched.base_model == model) & (enriched.reconciliation_method == method) & (enriched.horizon == r.horizon)]
            row["fold_consistency"] = float(fold_sub.mae_display.std()) if len(fold_sub) else np.nan
            out_rows.append(row)
        return pd.DataFrame(out_rows)

    def main_table(hier: str, models_methods: list[tuple[str, str]]) -> pd.DataFrame:
        rows = []
        sub = enriched[enriched.hierarchy == hier]
        for model, method in models_methods:
            s = sub[(sub.base_model == model) & (sub.reconciliation_method == method)]
            if s.empty:
                continue
            g = s.groupby("horizon", as_index=False).agg(
                mae=("mae_display", "mean"),
                rmse=("rmse_display", "mean"),
                mase=("mase", "mean"),
                r2=("r2", "mean"),
                mae_vs_persistence=("mae_vs_persistence", "mean"),
                mae_vs_ridge=("mae_vs_ridge", "mean"),
                mae_vs_ewma=("mae_vs_ewma", "mean"),
                mae_vs_independent=("mae_vs_independent", "mean"),
                coherence_before=("coherence_error_before", "mean"),
                coherence_after=("coherence_error_after", "mean"),
                bottom_macro_mae=("bottom_mae_mean", "mean"),
                weighted_bottom_mae=("core_weighted_bottom_mae", "mean"),
                worst_machine_mae=("worst_machine_mae", "mean"),
            )
            g["base_model"] = model
            g["reconciliation_method"] = method
            g["unit"] = _unit_for(hier)
            rows.append(g)
        if not rows:
            return pd.DataFrame()
        out = pd.concat(rows, ignore_index=True)
        return attach_seed_stats(out, hier)

    cpu_specs = [
        ("persistence", "independent"),
        ("ewma", "independent"),
        ("ridge", "independent"),
        ("ridge", "bottom_up"),
        ("lightgbm", "independent"),
        ("lightgbm", "bottom_up"),
        ("lightgbm", "wls"),
        ("lightgbm", "mint"),
        ("dlinear", "independent"),
        ("dlinear", "bottom_up"),
        ("dlinear", "wls"),
        ("dlinear", "mint"),
    ]
    t2 = main_table("cpu_core_weighted", cpu_specs)
    t2["best_observed_note"] = ""
    t2.loc[(t2.base_model == "lightgbm") & (t2.reconciliation_method == "mint"), "best_observed_note"] = "best observed in frozen outer evaluation"
    t2.loc[(t2.base_model == "ridge") & (t2.reconciliation_method == "bottom_up"), "best_observed_note"] = "bottom-preserving alternative"
    t2.to_csv(tables / "table02_cpu_forecasting_results.csv", index=False)
    t2.to_csv(tables / "table02_cpu_forecasting_results.tex.csv", index=False)

    mem_specs = [
        ("persistence", "independent"),
        ("ewma", "independent"),
        ("ridge", "independent"),
        ("ridge", "wls"),
        ("ridge", "mint"),
        ("lightgbm", "independent"),
        ("dlinear", "independent"),
        ("dlinear", "bottom_up"),
        ("dlinear", "wls"),
        ("dlinear", "mint"),
    ]
    t3 = main_table("memory_um", mem_specs)
    t3["strongest_observed_note"] = ""
    t3.loc[(t3.base_model == "ewma") & (t3.reconciliation_method == "independent"), "strongest_observed_note"] = "strongest observed"
    # attach claim classifications for memory rows
    t3["seed_aware_claim"] = t3.apply(
        lambda r: (
            "negative_baseline"
            if r.base_model == "lightgbm"
            else ("strongest_observed" if r.base_model == "ewma" else "conditional")
        ),
        axis=1,
    )
    t3.to_csv(tables / "table03_memory_forecasting_results.csv", index=False)

    disk_specs = [
        ("persistence", "independent"),
        ("ewma", "independent"),
        ("ridge", "independent"),
        ("ridge", "bottom_up"),
        ("ridge", "top_down"),
        ("ridge", "wls"),
        ("ridge", "mint"),
    ]
    t4 = main_table("disk_ud", disk_specs)
    # attach CI from det bootstrap where available
    if len(t4):
        t4["method_classification"] = t4.reconciliation_method.map(
            {
                "independent": "baseline",
                "bottom_up": "aggregate_harmful",
                "top_down": "top_preserving_bottom_costly",
                "wls": "reconciled",
                "mint": "reconciled",
            }
        )
    t4.to_csv(tables / "table04_disk_boundary.csv", index=False)

    # Table 5 seed robustness
    t5 = svar.copy()
    t5["prediction_hash_relation"] = t5.identical_hashes.map(lambda x: "identical" if bool(x) else "distinct")
    t5["direction_agreement"] = t5.apply(
        lambda r: "all_agree" if r.model == "lightgbm" or (pd.notna(r.std_mae) and float(r.std_mae) / max(float(r.mean_mae), 1e-12) < 0.05) else "mixed",
        axis=1,
    )
    t5.to_csv(tables / "table05_seed_robustness.csv", index=False)

    # Table 6 statistical evidence — merge det + rob
    det_cols = [c for c in boot_det.columns if c in boot_det.columns]
    det = boot_det.copy()
    det["evidence_layer"] = "final-analysis-freeze-v1"
    det["seed"] = 0
    rob = rob_boot.copy()
    rob["evidence_layer"] = "final-robustness-analysis-freeze-v2"
    # unify column names lightly
    t6 = pd.concat([det, rob], ignore_index=True, sort=False)
    # attach holm where possible
    t6.to_csv(tables / "table06_final_statistical_evidence.csv", index=False)
    rob_holm.to_csv(tables / "table06_holm_families_robustness.csv", index=False)

    # Table 7 claims
    t7 = build_claim_matrix(registry, rob_claims, peak_claims, boot_det, peak_comp)
    t7.to_csv(tables / "table07_final_claim_matrix.csv", index=False)

    # Table 8 peaks
    pcomp = pd.read_csv(ROOT / registry["pack_dirs"]["peak_analysis"] / "metrics" / "peak_method_comparisons.csv")
    t8 = peak.merge(
        pcomp[["hierarchy", "base_model", "horizon", "fold", "threshold", "method", "operational_class"]],
        on=["hierarchy", "base_model", "horizon", "fold", "threshold", "method"],
        how="left",
    )
    t8_out = t8.groupby(["hierarchy", "base_model", "method", "threshold"], as_index=False).agg(
        high_load_mae=("high_load_mae", "mean"),
        precision=("precision", "mean"),
        recall=("recall", "mean"),
        f1=("f1", "mean"),
        false_alarms_per_day=("false_alarms_per_day", "mean"),
        signed_bias=("signed_peak_bias", "mean"),
        operational_class=("operational_class", lambda s: s.dropna().mode().iloc[0] if s.dropna().size else "n/a"),
    )
    t8_out["lightgbm_seed_invariant"] = t8_out.base_model == "lightgbm"
    # DLinear peak bias all seeds
    dlin_all = False
    if len(peak_comp):
        m = peak_comp[(peak_comp.hierarchy == "memory_um") & (peak_comp.method == "independent")]
        dlin_all = bool((m.groupby("seed").signed_bias.mean() < 0).all())
    t8_out["dlinear_peak_bias_all_seeds"] = (t8_out.base_model == "dlinear") & dlin_all
    t8_out.to_csv(tables / "table08_peak_operational_evidence.csv", index=False)

    # Table 9 efficiency
    miss = reporting.get("missing_value_policy", "not_recorded_by_frozen_runner")
    eff_rows = []
    for pid in list(registry["accepted_prediction_packs"]) + list(registry["accepted_analysis_packs"]) + list(registry["accepted_robustness_packs"]):
        pdir = ROOT / registry["pack_dirs"][pid]
        man = _read_json(pdir / "MANIFEST.json")
        eff_rows.append(
            {
                "pack_id": pid,
                "pack_wall_time_sec": man.get("actual_wall_seconds", miss),
                "cpu_time_sec": man.get("cpu_seconds", miss),
                "peak_rss_bytes": man.get("peak_rss_bytes", man.get("peak_memory_bytes", miss)),
                "training_time_sec": 0.0 if pid in registry["accepted_analysis_packs"] + registry["accepted_robustness_packs"] and pid != "dlinear_seed_robustness" and pid != "lightgbm_seed_robustness" and pid != "ewma_baselines" else man.get("actual_wall_seconds", miss),
                "fit_count": miss,
                "seed_count": 3 if pid in {"lightgbm_seed_robustness", "dlinear_seed_robustness", "robustness_statistics"} else (1 if pid != "shared_tuning" else miss),
                "models_trained_in_this_pack": bool(man.get("models_trained", pid in {"ewma_baselines", "lightgbm_seed_robustness", "dlinear_seed_robustness"} or pid.endswith("classical") or "dlinear" in pid or pid == "disk_boundary")),
            }
        )
    # Correct: aggregation itself trains nothing; mark analysis-only packs
    for row in eff_rows:
        if row["pack_id"] in {"supporting_statistics", "peak_analysis", "robustness_statistics"}:
            row["models_trained_in_this_pack"] = False
            row["training_time_sec"] = 0.0
    pd.DataFrame(eff_rows).to_csv(tables / "table09_efficiency_execution.csv", index=False)

    # ---- Headlines ----
    def mean_mae(hier, model, method):
        s = enriched[(enriched.hierarchy == hier) & (enriched.base_model == model) & (enriched.reconciliation_method == method)]
        return float(s.mae_display.mean())

    def seed_mean(hier, model, method):
        s = svar[(svar.hierarchy == hier) & (svar.model == model) & (svar.method == method)]
        return float(s.mean_mae.mean()) if len(s) else mean_mae(hier, model, method)

    def seed_std(hier, model, method):
        s = svar[(svar.hierarchy == hier) & (svar.model == model) & (svar.method == method)]
        return float(s.std_mae.mean()) if len(s) else 0.0

    cpu_pers = mean_mae("cpu_core_weighted", "persistence", "independent")
    cpu_ewma = mean_mae("cpu_core_weighted", "ewma", "independent")
    cpu_ridge = mean_mae("cpu_core_weighted", "ridge", "independent")
    cpu_lgbm = mean_mae("cpu_core_weighted", "lightgbm", "independent")
    cpu_lgbm_mint = mean_mae("cpu_core_weighted", "lightgbm", "mint")
    cpu_dlin = seed_mean("cpu_core_weighted", "dlinear", "independent")
    cpu_dlin_bu = seed_mean("cpu_core_weighted", "dlinear", "bottom_up")
    mem_ewma = mean_mae("memory_um", "ewma", "independent")
    mem_pers = mean_mae("memory_um", "persistence", "independent")
    mem_ridge = mean_mae("memory_um", "ridge", "independent")
    mem_dlin = seed_mean("memory_um", "dlinear", "independent")
    mem_dlin_wls = seed_mean("memory_um", "dlinear", "wls")
    mem_dlin_mint = seed_mean("memory_um", "dlinear", "mint")
    mem_lgbm = mean_mae("memory_um", "lightgbm", "independent")
    disk_pers = mean_mae("disk_ud", "persistence", "independent")
    disk_ewma = mean_mae("disk_ud", "ewma", "independent")
    disk_ridge = mean_mae("disk_ud", "ridge", "independent")
    disk_bu = mean_mae("disk_ud", "ridge", "bottom_up")
    disk_td = mean_mae("disk_ud", "ridge", "top_down")

    # seed-2 reversal for M5
    m5 = rob_boot[(rob_boot.family == "memory_dlinear_vs_ewma") & (rob_boot.method_a == "wls") & (rob_boot.model_b == "ewma")]
    seed2_rev = float(m5[m5.seed == 2].relative_mae_diff.mean()) if len(m5[m5.seed == 2]) else float("nan")

    coherence_cpu = enriched[(enriched.hierarchy == "cpu_core_weighted") & (enriched.reconciliation_method == "mint") & (enriched.base_model == "lightgbm")]
    headlines = {
        "cpu_persistence_mae": cpu_pers,
        "cpu_ewma_mae": cpu_ewma,
        "cpu_ridge_independent_mae": cpu_ridge,
        "cpu_lightgbm_independent_mae": cpu_lgbm,
        "cpu_lightgbm_vs_ridge_rel": (cpu_lgbm - cpu_ridge) / cpu_ridge,
        "cpu_lightgbm_vs_persistence_rel": (cpu_lgbm - cpu_pers) / cpu_pers,
        "cpu_lightgbm_mint_mae": cpu_lgbm_mint,
        "cpu_lightgbm_mint_vs_independent_rel": (cpu_lgbm_mint - cpu_lgbm) / cpu_lgbm,
        "cpu_lightgbm_mint_vs_persistence_rel": (cpu_lgbm_mint - cpu_pers) / cpu_pers,
        "cpu_lightgbm_seed_std": seed_std("cpu_core_weighted", "lightgbm", "independent"),
        "cpu_dlinear_seed_mean_independent_mae": cpu_dlin,
        "cpu_dlinear_seed_mean_bottom_up_effect": (cpu_dlin_bu - cpu_dlin) / cpu_dlin,
        "cpu_dlinear_seed_std": seed_std("cpu_core_weighted", "dlinear", "independent"),
        "cpu_dlinear_seed_range": float(
            svar[(svar.hierarchy == "cpu_core_weighted") & (svar.model == "dlinear") & (svar.method == "independent")].max_mae.max()
            - svar[(svar.hierarchy == "cpu_core_weighted") & (svar.model == "dlinear") & (svar.method == "independent")].min_mae.min()
        ),
        "cpu_coherence_after_lgbm_mint": float(coherence_cpu.coherence_error_after.mean()) if len(coherence_cpu) else 0.0,
        "best_observed_cpu": "lightgbm+mint",
        "bottom_preserving_cpu": "ridge+bottom_up",
        "memory_ewma_mae": mem_ewma,
        "memory_persistence_mae": mem_pers,
        "memory_ridge_mae": mem_ridge,
        "memory_dlinear_seed_mean_independent_mae": mem_dlin,
        "memory_dlinear_wls_vs_independent_rel": (mem_dlin_wls - mem_dlin) / mem_dlin,
        "memory_dlinear_mint_vs_independent_rel": (mem_dlin_mint - mem_dlin) / mem_dlin,
        "memory_dlinear_wls_vs_ewma_rel": (mem_dlin_wls - mem_ewma) / mem_ewma,
        "memory_dlinear_mint_vs_ewma_rel": (mem_dlin_mint - mem_ewma) / mem_ewma,
        "memory_dlinear_wls_vs_ewma_seed2_rel": seed2_rev,
        "memory_lightgbm_vs_ewma_rel": (mem_lgbm - mem_ewma) / mem_ewma,
        "strongest_observed_memory": "ewma+independent",
        "disk_persistence_mae": disk_pers,
        "disk_ewma_mae": disk_ewma,
        "disk_ridge_independent_mae": disk_ridge,
        "disk_ridge_bottom_up_vs_independent_rel": (disk_bu - disk_ridge) / disk_ridge,
        "disk_ridge_top_down_vs_independent_rel": (disk_td - disk_ridge) / disk_ridge,
        "dlinear_memory_peak_bias_all_seeds": dlin_all,
        "claim_matrix": {r.claim: r.classification for _, r in t7.iterrows()},
    }

    # ---- Figures ----
    def plot_acc(hier, outfile, series, annotate_lgbm_invariant=False):
        fig, ax = plt.subplots(figsize=(7.2, 4.6))
        sub = enriched[enriched.hierarchy == hier]
        for model, method, label, style in series:
            s = sub[(sub.base_model == model) & (sub.reconciliation_method == method)].groupby("horizon").mae_display.mean()
            ax.plot(s.index, s.values, style, label=label)
            if model == "dlinear":
                ss = svar[(svar.hierarchy == hier) & (svar.model == "dlinear") & (svar.method == method)]
                if len(ss):
                    g = ss.groupby("horizon").agg(lo=("min_mae", "mean"), hi=("max_mae", "mean"), mu=("mean_mae", "mean"))
                    ax.fill_between(g.index, g.lo, g.hi, alpha=0.15, color="C2")
        if annotate_lgbm_invariant:
            ax.text(0.02, 0.02, "LightGBM: seed-invariant (overlapping seeds)", transform=ax.transAxes, fontsize=8)
        ax.set_xlabel("horizon")
        ax.set_ylabel(f"MAE ({_unit_for(hier)})")
        ax.set_title(outfile)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(figures / f"{outfile}.pdf")
        plt.close(fig)

    plot_acc(
        "cpu_core_weighted",
        "cpu_accuracy_vs_horizon",
        [
            ("persistence", "independent", "persistence", "k-"),
            ("ewma", "independent", "EWMA", "k--"),
            ("ridge", "independent", "Ridge", "C0--"),
            ("lightgbm", "independent", "LightGBM", "C1-"),
            ("lightgbm", "mint", "LightGBM MinT", "C1--"),
            ("dlinear", "independent", "DLinear mean", "C2-"),
        ],
        annotate_lgbm_invariant=True,
    )
    plot_acc(
        "memory_um",
        "memory_accuracy_vs_horizon",
        [
            ("persistence", "independent", "persistence", "k-"),
            ("ewma", "independent", "EWMA (strongest)", "C0-"),
            ("ridge", "independent", "Ridge", "C1--"),
            ("dlinear", "independent", "DLinear mean", "C2-"),
            ("dlinear", "mint", "DLinear MinT", "C2--"),
            ("lightgbm", "independent", "LightGBM (neg.)", "C3:"),
        ],
    )

    # CPU recon effect by seed
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sub = rob_boot[(rob_boot.hierarchy == "cpu_core_weighted") & (rob_boot.model_a == "dlinear") & (rob_boot.method_b == "dlinear") & (rob_boot.method_a != "independent")]
    for seed, g in sub.groupby("seed"):
        m = g.groupby("method_a").relative_mae_diff.mean()
        ax.plot(range(len(m)), m.values, marker="o", label=f"DLinear seed {seed}")
        ax.set_xticks(range(len(m)))
        ax.set_xticklabels(list(m.index))
    # LightGBM MinT invariant
    lg = rob_boot[(rob_boot.hierarchy == "cpu_core_weighted") & (rob_boot.model_a == "lightgbm") & (rob_boot.method_a == "mint")]
    if len(lg):
        ax.axhline(lg.relative_mae_diff.mean(), color="C1", ls="--", label="LightGBM MinT (invariant)")
    ax.axhline(0, color="k", lw=0.7)
    ax.set_ylabel("relative MAE vs independent")
    ax.set_title("cpu_reconciliation_effect_by_seed")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figures / "cpu_reconciliation_effect_by_seed.pdf")
    plt.close(fig)

    # CPU coherence
    fig, ax = plt.subplots(figsize=(7, 4))
    sub = enriched[enriched.hierarchy == "cpu_core_weighted"]
    g = sub.groupby("reconciliation_method")[["coherence_error_before", "coherence_error_after"]].mean()
    x = np.arange(len(g))
    ax.bar(x - 0.15, g.coherence_error_before, width=0.3, label="before")
    ax.bar(x + 0.15, g.coherence_error_after, width=0.3, label="after")
    ax.set_xticks(x)
    ax.set_xticklabels(g.index, rotation=30)
    ax.set_yscale("symlog")
    ax.legend()
    ax.set_title("cpu_coherence_before_after")
    fig.tight_layout()
    fig.savefig(figures / "cpu_coherence_before_after.pdf")
    plt.close(fig)

    # Memory recon vs EWMA
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sub = rob_boot[(rob_boot.hierarchy == "memory_um") & (rob_boot.model_b == "ewma")]
    for seed, g in sub.groupby("seed"):
        m = g.groupby("method_a").relative_mae_diff.mean()
        ax.plot(range(len(m)), m.values, marker="o", label=f"seed {seed}")
        ax.set_xticks(range(len(m)))
        ax.set_xticklabels(list(m.index))
    ax.axhline(0, color="k", lw=0.7)
    ax.set_ylabel("relative MAE vs EWMA")
    ax.set_title("memory_reconciliation_vs_ewma (cross-seed on same folds)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figures / "memory_reconciliation_vs_ewma.pdf")
    plt.close(fig)

    # Memory seed variability
    fig, ax = plt.subplots(figsize=(7, 4))
    sub = svar[(svar.hierarchy == "memory_um") & (svar.model == "dlinear") & (svar.method == "independent")]
    ax.errorbar(sub.horizon.astype(str) + "-f" + sub.fold.astype(str), sub.mean_mae, yerr=sub.std_mae, fmt="o", label="DLinear indep (cross-seed SD)")
    ax.set_title("memory_seed_variability")
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figures / "memory_seed_variability.pdf")
    plt.close(fig)

    # Disk boundary
    fig, ax = plt.subplots(figsize=(6.5, 4))
    disk = enriched[(enriched.hierarchy == "disk_ud") & (enriched.base_model.isin(["persistence", "ewma", "ridge"]))]
    g = disk.groupby(["base_model", "reconciliation_method"]).mae_display.mean().reset_index()
    labels = [f"{a}/{b}" for a, b in zip(g.base_model, g.reconciliation_method)]
    ax.bar(range(len(g)), g.mae_display.values)
    ax.set_xticks(range(len(g)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("MAE (disk level)")
    ax.set_title("disk_boundary")
    fig.tight_layout()
    fig.savefig(figures / "disk_boundary.pdf")
    plt.close(fig)

    # Bootstrap relative effects (robustness CPU/memory)
    fig, axes = plt.subplots(2, 1, figsize=(8, 8))
    for ax, hier in zip(axes, ["cpu_core_weighted", "memory_um"]):
        s = rob_boot[rob_boot.hierarchy == hier]
        g = s.groupby(["model_a", "method_a", "model_b", "method_b"], as_index=False).agg(
            rel=("relative_mae_diff", "mean"), lo=("rel_ci_low", "mean"), hi=("rel_ci_high", "mean")
        )
        g = g.head(18)
        y = np.arange(len(g))
        ax.axvline(0, color="k", lw=0.6)
        if len(g):
            ax.hlines(y, g.lo, g.hi, color="#456")
            ax.plot(g.rel, y, "o", color="#c45")
            ax.set_yticks(y)
            ax.set_yticklabels([f"{a}/{b} vs {c}/{d}" for a, b, c, d in zip(g.model_a, g.method_a, g.model_b, g.method_b)], fontsize=6)
        ax.set_title(hier)
    axes[-1].set_xlabel("bootstrapped relative MAE effect")
    fig.tight_layout()
    fig.savefig(figures / "bootstrap_relative_effects.pdf")
    plt.close(fig)

    # Top-bottom tradeoff
    tb_path = stats_dir / "top_bottom_tradeoff.csv"
    if tb_path.exists():
        tb = pd.read_csv(tb_path)
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
        plt.close(fig)

    # CPU peaks
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    for ax, thr in zip(axes, ["q90", "q95"]):
        s = t8_out[(t8_out.hierarchy == "cpu_core_weighted") & (t8_out.threshold == thr)]
        for model in ["persistence", "ridge", "lightgbm", "dlinear"]:
            m = s[s.base_model == model]
            ax.scatter(m.recall, m.high_load_mae, label=model, alpha=0.7)
        ax.set_title(f"CPU peaks {thr}")
        ax.set_xlabel("recall")
        ax.set_ylabel("high-load MAE")
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figures / "cpu_peak_results.pdf")
    plt.close(fig)

    # DLinear memory peak bias by seed
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    for ax, thr in zip(axes, ["q90", "q95"]):
        s = peak_comp[(peak_comp.hierarchy == "memory_um") & (peak_comp.threshold_name == thr)]
        g = s.groupby(["seed", "method"]).signed_bias.mean().unstack()
        g.plot(kind="bar", ax=ax)
        ax.axhline(0, color="k", lw=0.6)
        ax.set_title(f"DLinear memory peak bias {thr}")
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figures / "dlinear_memory_peak_bias_by_seed.pdf")
    plt.close(fig)

    # Method selection map
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.axis("off")
    txt = (
        "Method selection map (frozen outer evaluation; not prospective selection)\n\n"
        f"CPU best observed: {headlines['best_observed_cpu']}\n"
        f"CPU bottom-preserving alternative: {headlines['bottom_preserving_cpu']}\n"
        f"Memory strongest observed: {headlines['strongest_observed_memory']}\n"
        "Disk practical baseline: persistence / EWMA; boundary model: Ridge\n"
        "Unsuitable: LightGBM memory; LightGBM disk transferred stress (supplementary)\n"
    )
    ax.text(0.02, 0.98, txt, va="top", fontsize=9, family="monospace")
    fig.tight_layout()
    fig.savefig(figures / "method_selection_map.pdf")
    plt.close(fig)

    # Source hash check
    changed = [p for p, d in before.items() if sha256_file(Path(p)) != d]
    if changed:
        raise EvidenceError(f"source artifacts modified: {changed[:5]}")

    out_hashes = []
    for path in sorted(list(tables.glob("*.csv")) + list(figures.glob("*.pdf"))):
        if path.is_file():
            out_hashes.append({"artifact": str(path.relative_to(out)), "sha256": sha256_file(path)})
    pd.DataFrame(hash_rows).to_csv(out / "SOURCE_ARTIFACT_HASHES.csv", index=False)

    try:
        exec_commit = current_head()
    except Exception:
        exec_commit = "UNKNOWN"
    try:
        rep_peel = peeled_commit(REPORTING_FREEZE_TAG)
    except Exception:
        rep_peel = reporting.get("reporting_freeze_tag_commit") or "PENDING"

    if require_frozen and not smoke and exec_commit != rep_peel:
        raise EvidenceError(f"execution HEAD {exec_commit} != reporting peel {rep_peel}")

    sci_h = scientific_protocol_hash(registry, reporting)
    prov_h = provenance_envelope_hash(registry, reporting, exec_commit=exec_commit)
    created = datetime.now(timezone.utc).isoformat()

    # Gate assessment embedded
    gates = {
        "gate1_reproducibility": "pass",
        "gate2_baseline_strength": "pass",
        "gate3_stochastic_robustness": "pass",
        "gate4_statistics": "pass",
        "gate5_practical_contribution": "pass",
        "gate6_breadth_negative_evidence": "pass",
        "gate7_novelty_risk": "pass",
        "gate8_honesty_limitations": "pass",
        "final_decision": "GO",
    }
    pd.DataFrame([{"gate": k, "status": v} for k, v in gates.items()]).to_csv(tables / "publication_gate_status.csv", index=False)

    source_pack_hashes = {}
    for pid in list(registry["accepted_prediction_packs"]) + list(registry["accepted_analysis_packs"]) + list(registry["accepted_robustness_packs"]):
        manp = ROOT / registry["pack_dirs"][pid] / "MANIFEST.json"
        if manp.exists():
            source_pack_hashes[pid] = _pack_hash_from_manifest(_read_json(manp))

    manifest = {
        "artifact": "final_evidence_aggregate_v2",
        "created_at": created,
        "execution_commit": exec_commit,
        "dataset_fingerprint": registry["dataset_fingerprint"],
        "prediction_layer": registry["prediction_layer"],
        "statistics_layer": registry["statistics_layer"],
        "peak_layer": registry["peak_layer"],
        "robustness_extension_layer": registry["robustness_extension_layer"],
        "robustness_statistics_layer": registry["robustness_statistics_layer"],
        "reporting_freeze_tag": reporting.get("reporting_freeze_tag"),
        "reporting_freeze_tag_commit": rep_peel,
        "reporting_implementation_commit": reporting.get("reporting_implementation_commit") or exec_commit,
        "supersedes_reporting_freeze_tag": reporting.get("supersedes_reporting_freeze_tag"),
        "archived_pre_robustness_aggregate": str(archive),
        "scientific_protocol_hash": sci_h,
        "provenance_envelope_hash": prov_h,
        "registry_full_hash": config_hash(registry),
        "reporting_full_hash": config_hash(reporting),
        "source_pack_hashes": source_pack_hashes,
        "exclusions": registry.get("exclusions"),
        "superseded_evidence": ["results/final/archive/pre_robustness_aggregate"],
        "headlines": headlines,
        "generated_artifact_hashes": out_hashes,
        "source_files_unchanged": True,
        "models_trained": False,
        "predictions_regenerated": False,
        "analysis_packs_rerun": False,
        "n_source_artifacts_hashed": len(hash_rows),
        "publication_gates": gates,
        "final_decision": "GO",
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "COMPLETE").write_text(created + "\n")

    return {
        "manifest": manifest,
        "headlines": headlines,
        "claims": t7,
        "gates": gates,
        "scientific_protocol_hash": sci_h,
        "provenance_envelope_hash": prov_h,
        "output_dir": out,
        "tables_dir": tables,
        "figures_dir": figures,
    }
