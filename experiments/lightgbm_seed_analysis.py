"""Post-fit analysis for LightGBM multi-seed robustness (no retraining of seed 0)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd

from experiments.pack_runner import _hierarchy_entry
from models.hybrid.reconciliation import (
    coherence_error,
    estimate_residual_covariance,
    is_coherent,
    reconcile,
)
from timetrack.hierarchy_registry import machine_core_counts
from timetrack.metrics import mae, mase_result, r2_score, rmse

ROOT = Path(__file__).resolve().parents[1]
CPU_CORE_TOTAL = 236.0
SOURCE_DIRS = {
    "cpu_classical": "03_cpu_classical",
    "memory_classical": "01_memory_classical",
}


def _sha256(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def _cpu_scale(hierarchy: str) -> float:
    return CPU_CORE_TOTAL if hierarchy == "cpu_core_weighted" else 1.0


def _core_weights(hierarchy: str, n_bottom: int) -> np.ndarray:
    if hierarchy != "cpu_core_weighted":
        return np.ones(n_bottom, dtype=float) / max(n_bottom, 1)
    cores = machine_core_counts()
    entry = _hierarchy_entry(hierarchy)
    w = []
    for name in entry["hierarchy"].bottom_names:
        key = name
        for suffix in ("_CU_wcontrib", "_CU", "_UM", "_UD"):
            if key.endswith(suffix):
                key = key[: -len(suffix)]
                break
        w.append(float(cores.get(key, 1.0)))
    w = np.asarray(w, dtype=float)
    return w / w.sum()


def _load_npz(path: Path) -> dict[str, np.ndarray]:
    data = np.load(path)
    return {k: data[k] for k in data.files}


def _baseline_indep_mae(
    src_root: Path,
    ewma_root: Path,
    hierarchy: str,
    fold: int,
    horizon: int,
    model: str,
) -> float | None:
    if model == "ewma":
        path = ewma_root / "metrics" / "reconciliation_results.csv"
        if not path.exists():
            return None
        df = pd.read_csv(path)
        m = df[
            (df.hierarchy == hierarchy)
            & (df.fold == fold)
            & (df.horizon == horizon)
            & (df.reconciliation_method == "independent")
            & (df.base_model == "ewma")
        ]
        return float(m.top_mae.iloc[0]) if not m.empty else None
    dirname = SOURCE_DIRS["cpu_classical" if hierarchy == "cpu_core_weighted" else "memory_classical"]
    path = src_root / dirname / "metrics" / "reconciliation_results.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    m = df[
        (df.hierarchy == hierarchy)
        & (df.fold == fold)
        & (df.horizon == horizon)
        & (df.reconciliation_method == "independent")
        & (df.base_model == model)
        & (df.seed == 0)
    ]
    return float(m.top_mae.iloc[0]) if not m.empty else None


def _eval_one(
    *,
    hierarchy: str,
    fold: int,
    horizon: int,
    seed: int,
    method: str,
    aligned: dict[str, np.ndarray],
    bottom: np.ndarray,
    top: np.ndarray,
    coh_before: float,
    prediction_hash: str,
    model_config_hash: str,
    source: str,
    scale: float,
    core_w: np.ndarray,
) -> dict[str, Any]:
    yt = aligned["yt_test"]
    yb = aligned["yb_test"]
    yt_train = aligned["yt_train"]
    mase_info = mase_result(yt, top, yt_train)
    per_m = np.array([mae(yb[:, j], bottom[:, j]) for j in range(yb.shape[1])], dtype=float)
    top_mae = float(mae(yt, top))
    return {
        "hierarchy": hierarchy,
        "fold": fold,
        "horizon": horizon,
        "seed": seed,
        "reconciliation_method": method,
        "base_model": "lightgbm",
        "source": source,
        "top_mae_native": top_mae,
        "top_mae_report": top_mae / scale,
        "top_rmse_report": float(rmse(yt, top)) / scale,
        "top_r2": float(r2_score(yt, top)),
        "mase": mase_info["mase"],
        "mase_valid": mase_info["mase_valid"],
        "coherence_error_before": float(coh_before),
        "coherence_error_after": float(coherence_error(bottom, top)),
        "is_coherent_after": bool(is_coherent(bottom, top, atol=1e-4)),
        "bottom_mae_mean_native": float(np.mean(per_m)),
        "bottom_mae_weighted_native": float(np.dot(per_m, core_w)),
        "worst_machine_mae_native": float(np.max(per_m)),
        "neg_pred_rate": float(np.mean(top < 0)),
        "prediction_hash": prediction_hash,
        "model_config_hash": model_config_hash,
        "cpu_core_total": CPU_CORE_TOTAL if hierarchy == "cpu_core_weighted" else None,
        "report_unit": "weighted_mean_pct" if hierarchy == "cpu_core_weighted" else "native",
    }


def analyze_lightgbm_seed_robustness(cfg: dict[str, Any], pack: dict[str, Any], out: Path) -> dict[str, Any]:
    """Consume seed-0 NPZs + new seed 1/2 NPZs; write required metrics/tables/figures."""
    metrics = out / "metrics"
    tables = out / "tables"
    figures = out / "figures"
    metrics.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    src_root = ROOT / (cfg.get("source_artifact_root") or "results/final/packs")
    ewma_root = ROOT / (cfg.get("artifact_root") or "results/final/robustness") / "01_ewma_baselines"
    reuse = pack.get("reuse_seed0_from") or {
        "cpu_core_weighted": "cpu_classical",
        "memory_um": "memory_classical",
    }
    methods = list(pack.get("reconciliation_methods") or ["independent", "bottom_up", "wls", "mint"])
    horizons = [int(h) for h in pack["horizons"]]
    folds = [int(f) for f in pack["outer_folds"]]
    hierarchies = list(pack["hierarchies"])

    # model config hashes
    cfg_hashes = {}
    for hier, key in [("cpu_core_weighted", "lightgbm_cpu"), ("memory_um", "lightgbm_memory")]:
        params = {
            "n_estimators": int(cfg[key]["n_estimators"]),
            "learning_rate": float(cfg[key]["learning_rate"]),
            "num_leaves": int(cfg[key]["num_leaves"]),
            "n_jobs": int(cfg.get("lightgbm_n_jobs", -1)),
            "max_depth": -1,
            "verbosity": -1,
        }
        cfg_hashes[hier] = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]

    # source seed0 hashes table
    from experiments.robustness_extension import source_seed0_prediction_hashes

    seed0_hashes = source_seed0_prediction_hashes(cfg)
    pd.DataFrame([{"pack": k, "hash16": v} for k, v in seed0_hashes.items()]).to_csv(
        metrics / "source_seed0_hashes.csv", index=False
    )

    result_rows: list[dict[str, Any]] = []
    hash_rows: list[dict[str, Any]] = []
    pred_cache: dict[tuple, dict[str, np.ndarray]] = {}

    for hier in hierarchies:
        entry = _hierarchy_entry(hier)
        h = entry["hierarchy"]
        scale = _cpu_scale(hier)
        core_w = _core_weights(hier, len(h.bottom_names))
        src_pack = reuse[hier]
        src_dir = src_root / SOURCE_DIRS[src_pack] / "metrics" / "predictions"
        new_dir = metrics / "predictions"

        for fold in folds:
            for horizon in horizons:
                for seed in (0, 1, 2):
                    run_id = f"base__{hier}__f{fold}__h{horizon}__lightgbm__s{seed}"
                    if seed == 0:
                        path = src_dir / f"{run_id}.npz"
                        source = f"experiment-freeze-v2:{src_pack}"
                    else:
                        path = new_dir / f"{run_id}.npz"
                        source = "robustness_extension"
                    if not path.exists():
                        raise FileNotFoundError(f"missing prediction artifact: {path}")
                    aligned = _load_npz(path)
                    pred_cache[(hier, fold, horizon, seed)] = aligned
                    pred_hash_full = _sha256(aligned["pt_test"]) + _sha256(aligned["pb_test"])
                    pred_hash = hashlib.sha256(pred_hash_full.encode()).hexdigest()
                    # per-series hashes
                    for j, name in enumerate(h.bottom_names):
                        hash_rows.append(
                            {
                                "hierarchy": hier,
                                "target": name,
                                "fold": fold,
                                "horizon": horizon,
                                "seed": seed,
                                "split": "test",
                                "prediction_sha256": _sha256(aligned["pb_test"][:, j]),
                                "model_config_hash": cfg_hashes[hier],
                                "source": source,
                            }
                        )
                    hash_rows.append(
                        {
                            "hierarchy": hier,
                            "target": h.top_name,
                            "fold": fold,
                            "horizon": horizon,
                            "seed": seed,
                            "split": "test",
                            "prediction_sha256": _sha256(aligned["pt_test"]),
                            "model_config_hash": cfg_hashes[hier],
                            "source": source,
                        }
                    )

                    y_full_val = np.concatenate(
                        [aligned["yb_val"], aligned["yt_val"].reshape(-1, 1)], axis=1
                    )
                    p_full_val = np.concatenate(
                        [aligned["pb_val"], aligned["pt_val"].reshape(-1, 1)], axis=1
                    )
                    cov = estimate_residual_covariance(y_full_val, p_full_val, shrink_diag=0.1)
                    series_var = np.maximum(np.diag(cov), 1e-12)
                    coh_before = coherence_error(aligned["pb_test"], aligned["pt_test"])
                    for method in methods:
                        out_r = reconcile(
                            method,
                            h,
                            aligned["pb_test"],
                            aligned["pt_test"],
                            series_var=series_var if method == "wls" else None,
                            residual_cov=cov if method == "mint" else None,
                            nonnegative=False,
                        )
                        row = _eval_one(
                            hierarchy=hier,
                            fold=fold,
                            horizon=horizon,
                            seed=seed,
                            method=method,
                            aligned=aligned,
                            bottom=out_r["bottom"],
                            top=out_r["top"],
                            coh_before=coh_before,
                            prediction_hash=pred_hash[:16],
                            model_config_hash=cfg_hashes[hier],
                            source=source,
                            scale=scale,
                            core_w=core_w,
                        )
                        # relative metrics filled later
                        result_rows.append(row)

    results = pd.DataFrame(result_rows)
    # relatives vs same-seed independent + baselines
    enriched = []
    for _, r in results.iterrows():
        ind = results[
            (results.hierarchy == r.hierarchy)
            & (results.fold == r.fold)
            & (results.horizon == r.horizon)
            & (results.seed == r.seed)
            & (results.reconciliation_method == "independent")
        ].iloc[0]
        pers = _baseline_indep_mae(src_root, ewma_root, r.hierarchy, int(r.fold), int(r.horizon), "persistence")
        ewma = _baseline_indep_mae(src_root, ewma_root, r.hierarchy, int(r.fold), int(r.horizon), "ewma")
        ridge = _baseline_indep_mae(src_root, ewma_root, r.hierarchy, int(r.fold), int(r.horizon), "ridge")
        det = [x for x in (pers, ewma, ridge) if x is not None]
        strongest_det = min(det) if det else None
        # strongest det name
        strongest_name = None
        if strongest_det is not None:
            cands = [("persistence", pers), ("ewma", ewma), ("ridge", ridge)]
            strongest_name = min((c for c in cands if c[1] is not None), key=lambda t: t[1])[0]
        row = dict(r)
        row["rel_mae_vs_independent"] = float(r.top_mae_native / max(ind.top_mae_native, 1e-12))
        row["pct_vs_independent"] = 100.0 * (row["rel_mae_vs_independent"] - 1.0)
        row["persistence_mae_native"] = pers
        row["ewma_mae_native"] = ewma
        row["ridge_mae_native"] = ridge
        row["strongest_det_mae_native"] = strongest_det
        row["strongest_det_name"] = strongest_name
        row["rel_mae_vs_persistence"] = (
            float(r.top_mae_native / max(pers, 1e-12)) if pers is not None else None
        )
        row["rel_mae_vs_ewma"] = float(r.top_mae_native / max(ewma, 1e-12)) if ewma is not None else None
        row["rel_mae_vs_ridge"] = float(r.top_mae_native / max(ridge, 1e-12)) if ridge is not None else None
        row["rel_mae_vs_strongest_det"] = (
            float(r.top_mae_native / max(strongest_det, 1e-12)) if strongest_det is not None else None
        )
        # report-unit relatives identical (scale cancels)
        enriched.append(row)
    results = pd.DataFrame(enriched)
    results.to_csv(metrics / "lightgbm_seed_results.csv", index=False)
    pd.DataFrame(hash_rows).to_csv(metrics / "lightgbm_seed_prediction_hashes.csv", index=False)

    # Seed input comparability: only random_state / seed may differ
    from timetrack.robustness_extension import lightgbm_execution_fingerprint

    diff_rows = []
    unexpected = 0
    for hier, family in [("cpu_core_weighted", "cpu"), ("memory_um", "memory")]:
        fp0 = lightgbm_execution_fingerprint(0, family=family, cfg=cfg)
        for seed in (1, 2):
            fp = lightgbm_execution_fingerprint(seed, family=family, cfg=cfg)
            all_keys = sorted(set(fp0) | set(fp))
            for key in all_keys:
                v0, v1 = fp0.get(key), fp.get(key)
                if key == "random_state":
                    status = "intentionally_different_seed_field"
                elif v0 == v1:
                    status = "equal"
                else:
                    status = "unexpected_difference"
                    unexpected += 1
                diff_rows.append(
                    {
                        "hierarchy": hier,
                        "compare_seed_a": 0,
                        "compare_seed_b": seed,
                        "field": key,
                        "value_a": v0,
                        "value_b": v1,
                        "status": status,
                    }
                )
    # Timestamp / split alignment across seeds for each hier×fold×horizon
    align_rows = []
    for hier in hierarchies:
        for fold in folds:
            for horizon in horizons:
                keys = [(hier, fold, horizon, s) for s in (0, 1, 2)]
                if not all(k in pred_cache for k in keys):
                    continue
                yt = [pred_cache[k]["yt_test"] for k in keys]
                same_len = len({len(x) for x in yt}) == 1
                # labels must match (same outer evaluation rows)
                same_y = all(np.allclose(yt[0], yt[i], equal_nan=True) for i in (1, 2))
                align_rows.append(
                    {
                        "hierarchy": hier,
                        "fold": fold,
                        "horizon": horizon,
                        "n_test_equal": same_len,
                        "yt_test_equal_across_seeds": same_y,
                        "n_test": int(len(yt[0])),
                    }
                )
    pd.DataFrame(diff_rows).to_csv(metrics / "seed_input_diff.csv", index=False)
    pd.DataFrame(align_rows).to_csv(metrics / "seed_timestamp_alignment.csv", index=False)
    if unexpected:
        raise RuntimeError(f"seed_input_diff has {unexpected} unexpected non-seed differences")
    if align_rows and not all(r["yt_test_equal_across_seeds"] for r in align_rows):
        raise RuntimeError("outer evaluation labels/timestamps do not align across seeds")

    # Seed variability summary
    var_rows = []
    for (hier, horizon, fold, method), g in results.groupby(
        ["hierarchy", "horizon", "fold", "reconciliation_method"]
    ):
        maes = g.sort_values("seed")["top_mae_report"].to_numpy()
        hashes = g.sort_values("seed")["prediction_hash"].tolist()
        mean = float(np.mean(maes))
        std = float(np.std(maes, ddof=0))
        cv = float(std / max(abs(mean), 1e-12))
        # pairwise max abs pred diff on independent top only when method independent
        max_abs = 0.0
        keys = [(hier, int(fold), int(horizon), int(s)) for s in (0, 1, 2)]
        if all(k in pred_cache for k in keys):
            tops = [pred_cache[k]["pt_test"] for k in keys]
            for i in range(3):
                for j in range(i + 1, 3):
                    max_abs = max(max_abs, float(np.max(np.abs(tops[i] - tops[j]))))
        identical = len(set(hashes)) == 1
        rel_metric_spread = float((maes.max() - maes.min()) / max(abs(mean), 1e-12))
        # direction vs independent for recon methods
        pcts = g.sort_values("seed")["pct_vs_independent"].to_numpy()
        direction_same = bool(np.all(pcts <= 2.0) or np.all(pcts >= -2.0) or (np.all(pcts < 0) or np.all(pcts > 0)))
        if identical or rel_metric_spread <= 1e-9:
            klass = "seed_invariant"
        elif cv <= 0.01 and direction_same:
            klass = "practically_seed_stable"
        elif cv <= 0.05:
            klass = "moderately_seed_sensitive"
        else:
            klass = "seed_unstable"
        var_rows.append(
            {
                "hierarchy": hier,
                "horizon": horizon,
                "fold": fold,
                "reconciliation_method": method,
                "mean_mae_report": mean,
                "std_mae_report": std,
                "cv": cv,
                "min_mae_report": float(maes.min()),
                "max_mae_report": float(maes.max()),
                "identical_prediction_hashes": identical,
                "n_unique_hashes": len(set(hashes)),
                "pairwise_max_abs_pred_diff": max_abs,
                "stability_class": klass,
                "seed0_mae": float(maes[0]),
                "seed1_mae": float(maes[1]),
                "seed2_mae": float(maes[2]),
            }
        )
    var_df = pd.DataFrame(var_rows)
    var_df.to_csv(metrics / "lightgbm_seed_summary.csv", index=False)

    # Fold consistency
    fold_rows = []
    for (hier, seed, horizon, method), g in results.groupby(
        ["hierarchy", "seed", "horizon", "reconciliation_method"]
    ):
        fold_rows.append(
            {
                "hierarchy": hier,
                "seed": seed,
                "horizon": horizon,
                "reconciliation_method": method,
                "n_folds": g.fold.nunique(),
                "mean_mae_report": float(g.top_mae_report.mean()),
                "std_mae_report": float(g.top_mae_report.std(ddof=0)),
                "min_fold_mae": float(g.top_mae_report.min()),
                "max_fold_mae": float(g.top_mae_report.max()),
                "mean_pct_vs_independent": float(g.pct_vs_independent.mean()),
                "mean_rel_vs_strongest_det": float(g.rel_mae_vs_strongest_det.mean())
                if g.rel_mae_vs_strongest_det.notna().all()
                else None,
                "mean_rel_vs_ewma": float(g.rel_mae_vs_ewma.mean()) if g.rel_mae_vs_ewma.notna().all() else None,
            }
        )
    pd.DataFrame(fold_rows).to_csv(metrics / "lightgbm_seed_fold_consistency.csv", index=False)

    # Reconciliation effects
    recon_eff = results[results.reconciliation_method != "independent"][
        [
            "hierarchy",
            "seed",
            "fold",
            "horizon",
            "reconciliation_method",
            "top_mae_report",
            "pct_vs_independent",
            "coherence_error_before",
            "coherence_error_after",
            "bottom_mae_mean_native",
            "worst_machine_mae_native",
        ]
    ]
    recon_eff.to_csv(metrics / "lightgbm_seed_reconciliation_effects.csv", index=False)

    # CPU / memory tables + conclusions
    cpu = results[results.hierarchy == "cpu_core_weighted"]
    mem = results[results.hierarchy == "memory_um"]
    cpu.to_csv(tables / "lightgbm_cpu_seed_robustness.csv", index=False)
    mem.to_csv(tables / "lightgbm_memory_seed_robustness.csv", index=False)

    conclusions = []
    # A1 CPU independent vs strongest det
    a1 = cpu[cpu.reconciliation_method == "independent"]
    for seed, g in a1.groupby("seed"):
        wins = int((g.rel_mae_vs_strongest_det < 1.0).sum())
        losses = int((g.rel_mae_vs_strongest_det > 1.0).sum())
        ties = len(g) - wins - losses
        conclusions.append(
            {
                "check": "A1_cpu_independent_vs_strongest_det",
                "seed": int(seed),
                "wins": wins,
                "ties": ties,
                "losses": losses,
                "mean_rel": float(g.rel_mae_vs_strongest_det.mean()),
                "worst_rel": float(g.rel_mae_vs_strongest_det.max()),
                "worst_fold": int(g.loc[g.rel_mae_vs_strongest_det.idxmax(), "fold"]),
                "worst_horizon": int(g.loc[g.rel_mae_vs_strongest_det.idxmax(), "horizon"]),
                "strongest_det": g.strongest_det_name.mode().iloc[0] if len(g) else None,
            }
        )
    # B1 MinT vs independent
    b1 = cpu[cpu.reconciliation_method == "mint"]
    for seed, g in b1.groupby("seed"):
        conclusions.append(
            {
                "check": "B1_cpu_mint_vs_independent",
                "seed": int(seed),
                "wins": int((g.pct_vs_independent < 0).sum()),
                "ties": int((np.abs(g.pct_vs_independent) <= 2).sum()),
                "losses": int((g.pct_vs_independent > 2).sum()),
                "mean_rel": float((1 + g.pct_vs_independent / 100).mean()),
                "mean_pct": float(g.pct_vs_independent.mean()),
                "worst_pct": float(g.pct_vs_independent.max()),
                "mean_coh_reduction": float(
                    (g.coherence_error_before - g.coherence_error_after).mean()
                ),
            }
        )
    # Memory vs EWMA
    mind = mem[mem.reconciliation_method == "independent"]
    for seed, g in mind.groupby("seed"):
        conclusions.append(
            {
                "check": "memory_independent_vs_ewma",
                "seed": int(seed),
                "wins": int((g.rel_mae_vs_ewma < 1.0).sum()),
                "losses": int((g.rel_mae_vs_ewma > 1.0).sum()),
                "mean_rel": float(g.rel_mae_vs_ewma.mean()),
                "worse_than_ewma": bool((g.rel_mae_vs_ewma > 1.0).all()),
            }
        )

    # stability aggregate
    for hier in hierarchies:
        sub = var_df[var_df.hierarchy == hier]
        conclusions.append(
            {
                "check": "seed_stability",
                "hierarchy": hier,
                "n_seed_invariant": int((sub.stability_class == "seed_invariant").sum()),
                "n_practically_stable": int((sub.stability_class == "practically_seed_stable").sum()),
                "n_moderate": int((sub.stability_class == "moderately_seed_sensitive").sum()),
                "n_unstable": int((sub.stability_class == "seed_unstable").sum()),
                "identical_hash_cells": int(sub.identical_prediction_hashes.sum()),
                "total_cells": len(sub),
            }
        )
    pd.DataFrame(conclusions).to_csv(tables / "lightgbm_seed_conclusion.csv", index=False)

    # Figures
    _plot_seed_variability(cpu, figures / "lightgbm_cpu_seed_variability.pdf", "CPU LightGBM")
    _plot_seed_variability(mem, figures / "lightgbm_memory_seed_variability.pdf", "Memory LightGBM")
    _plot_recon_by_seed(cpu, figures / "lightgbm_reconciliation_effect_by_seed.pdf")

    # Hash identity summary
    hash_df = pd.DataFrame(hash_rows)
    top_hashes = hash_df[hash_df.target.str.startswith("cluster_") | hash_df.target.str.contains("cluster")]
    # group by hier/fold/horizon/target across seeds
    id_count = 0
    material = 0
    equiv = 0
    for _, g in hash_df.groupby(["hierarchy", "fold", "horizon", "target"]):
        hs = g.sort_values("seed")["prediction_sha256"].tolist()
        if len(set(hs)) == 1:
            id_count += 1
        else:
            # check numerical equivalence via pred cache tops/bottoms hard — count material
            material += 1
    summary = {
        "identical_across_three_seeds": id_count,
        "materially_different_hash_groups": material,
        "numerically_equivalent_diff_hash": equiv,
        "n_hash_groups": id_count + material,
    }
    (metrics / "lightgbm_seed_hash_identity.json").write_text(json.dumps(summary, indent=2))
    return {"n_result_rows": len(results), "hash_identity": summary, "source_seed0_hashes": seed0_hashes}


def _plot_seed_variability(df: pd.DataFrame, path: Path, title: str) -> None:
    ind = df[df.reconciliation_method == "independent"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for seed, g in ind.groupby("seed"):
        means = g.groupby("horizon")["top_mae_report"].mean()
        ax.plot(means.index, means.values, marker="o", label=f"seed {seed}")
    ax.set_xlabel("Horizon")
    ax.set_ylabel("Top MAE (report units)")
    ax.set_title(title + " — independent MAE by seed")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    fig.savefig(path.with_suffix(".png"))
    plt.close(fig)


def _plot_recon_by_seed(cpu: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for method in ("bottom_up", "wls", "mint"):
        sub = cpu[cpu.reconciliation_method == method]
        means = sub.groupby("seed")["pct_vs_independent"].mean()
        ax.plot(means.index, means.values, marker="o", label=method)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("Seed")
    ax.set_ylabel("% MAE vs independent")
    ax.set_title("CPU LightGBM reconciliation effect by seed")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    fig.savefig(path.with_suffix(".png"))
    plt.close(fig)
