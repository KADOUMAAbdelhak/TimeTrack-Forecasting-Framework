"""Final-stage hierarchical reconciliation runner (C1).

Writes only under results/final/. Reuses base forecasts across reconciliation
methods. Smoke mode exercises one hierarchy end-to-end without HPO.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.runner import prepare_split_windows
from models import forecasting as F
from models.hybrid.reconciliation import (
    coherence_error,
    estimate_residual_covariance,
    is_coherent,
    machine_core_counts,
    reconcile,
)
from timetrack.data import build_analysis_panel, dataset_fingerprint
from timetrack.efficiency import EfficiencyRecord, measure_inference_latencies, timed_train
from timetrack.evaluation_stage import ExperimentStage
from timetrack.hierarchy_registry import final_hierarchy_registry, summing_matrix_hash
from timetrack.metrics import mae
from timetrack.splits import fold_to_split_spec, make_outer_chronological_folds
from timetrack.stats_bootstrap import (
    holm_adjust,
    paired_block_bootstrap_comparison,
    select_block_length,
)

FLAT_MODELS = {
    "ridge",
    "lasso",
    "elasticnet",
    "random_forest",
    "extra_trees",
    "lightgbm",
    "xgboost",
    "catboost",
}


def _first_step(y: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    if y.ndim > 1:
        return y[:, 0]
    return y.reshape(-1)


def _config_hash(cfg: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _run_key(**parts: Any) -> str:
    return "__".join(f"{k}={v}" for k, v in sorted(parts.items()))


def _model_kwargs(cfg: dict[str, Any], model_name: str) -> dict[str, Any]:
    return dict((cfg.get("model_kwargs") or {}).get(model_name) or {})


def _fit_predict_series(
    panel: pd.DataFrame,
    split,
    target: str,
    horizon: int,
    context: int,
    model_name: str,
    seed: int,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    flat = model_name in FLAT_MODELS
    kwargs = _model_kwargs(cfg, model_name)
    windows = prepare_split_windows(panel, split, target, horizon, context, flat=flat)
    model = F.build_model(model_name, horizon=horizon, context_length=context, seed=seed, **kwargs)

    def _fit():
        return model.fit(windows["train"].X, windows["train"].y, windows["val"].X, windows["val"].y)

    _, wall_train, cpu_train, peak_rss = timed_train(_fit)

    # Cold + warm inference on a fixed val batch (exclude dataset loading)
    X_batch = windows["val"].X if len(windows["val"].X) else windows["test"].X
    eff_proto = cfg.get("efficiency_protocol") or {}
    lat = measure_inference_latencies(
        model.predict,
        X_batch,
        n_warm=int(eff_proto.get("warmup", 3)),
        n_repeat=int(eff_proto.get("repeats", 11)),
    )
    t0 = time.perf_counter()
    pred_val = model.predict(windows["val"].X)
    pred_test = model.predict(windows["test"].X)
    e2e = time.perf_counter() - t0

    ser_bytes = None
    try:
        import tempfile
        import joblib

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "m.joblib"
            joblib.dump(model, path)
            ser_bytes = float(path.stat().st_size)
    except Exception:
        ser_bytes = None

    eff = EfficiencyRecord(
        wall_train_sec=float(wall_train),
        cpu_train_sec=float(cpu_train),
        peak_rss_mb=float(peak_rss),
        n_parameters=getattr(model.metadata, "n_parameters", None),
        serialized_model_bytes=ser_bytes,
        warm_infer_latency_ms_median=lat["warm_infer_latency_ms_median"],
        warm_infer_latency_ms_p25=lat["warm_infer_latency_ms_p25"],
        warm_infer_latency_ms_p75=lat["warm_infer_latency_ms_p75"],
        cold_infer_latency_ms=lat["cold_infer_latency_ms"],
        forecasts_per_sec=lat["forecasts_per_sec"],
        n_train_samples=int(len(windows["train"].X)),
        n_prediction_origins=int(len(windows["test"].X)),
        end_to_end_latency_sec=float(e2e),
    )
    return {
        "y_train": _first_step(windows["train"].y),
        "y_val": _first_step(windows["val"].y),
        "y_test": _first_step(windows["test"].y),
        "p_val": _first_step(pred_val),
        "p_test": _first_step(pred_test),
        "origin_val": windows["val"].origin_idx,
        "origin_test": windows["test"].origin_idx,
        "efficiency": eff,
        "model_metadata": model.metadata.to_dict(),
    }


def _align(packs: list[dict], top_pack: dict) -> dict[str, Any]:
    ov = set(top_pack["origin_val"].tolist())
    ot = set(top_pack["origin_test"].tolist())
    for p in packs:
        ov &= set(p["origin_val"].tolist())
        ot &= set(p["origin_test"].tolist())
    ov = np.array(sorted(ov), dtype=int)
    ot = np.array(sorted(ot), dtype=int)

    def _take(pack, which, origins):
        src_o = pack[f"origin_{which}"]
        idx = {int(o): i for i, o in enumerate(src_o)}
        ii = [idx[int(o)] for o in origins]
        return pack[f"y_{which}"][ii], pack[f"p_{which}"][ii]

    return {
        "yb_val": np.column_stack([_take(p, "val", ov)[0] for p in packs]),
        "pb_val": np.column_stack([_take(p, "val", ov)[1] for p in packs]),
        "yb_test": np.column_stack([_take(p, "test", ot)[0] for p in packs]),
        "pb_test": np.column_stack([_take(p, "test", ot)[1] for p in packs]),
        "yt_val": _take(top_pack, "val", ov)[0],
        "pt_val": _take(top_pack, "val", ov)[1],
        "yt_test": _take(top_pack, "test", ot)[0],
        "pt_test": _take(top_pack, "test", ot)[1],
        "origin_test": ot,
        "yb_train_list": [p["y_train"] for p in packs],
        "yt_train": top_pack["y_train"],
        "bottom_eff": [p.get("efficiency") for p in packs],
        "top_eff": top_pack.get("efficiency"),
    }


def _prepare_cpu_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Materialize z_k = verified_core_count_k * machine_k_CU and cluster_CU_wsum."""
    out = panel.copy()
    cores = machine_core_counts()
    cols = []
    for m, c in cores.items():
        col = f"{m}_CU"
        if col not in out.columns:
            raise KeyError(col)
        z = out[col].to_numpy(dtype=float) * float(c)
        out[f"{m}_CU_wcontrib"] = z
        cols.append(f"{m}_CU_wcontrib")
    out["cluster_CU_wsum"] = out[cols].sum(axis=1)
    return out


def run_hierarchy_once(
    panel: pd.DataFrame,
    entry: dict[str, Any],
    *,
    fold_id: int,
    folds,
    horizon: int,
    context: int,
    model_name: str,
    seed: int,
    methods: list[str],
    nonnegative_flags: list[bool],
    cfg: dict[str, Any],
    fp: dict[str, Any],
    cfg_hash: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fit base forecasts once; apply all reconciliation methods."""
    h = entry["hierarchy"]
    split = fold_to_split_spec(folds[fold_id])
    work = _prepare_cpu_panel(panel) if entry["name"] == "cpu_core_weighted" else panel

    bottom_packs = []
    for name in h.bottom_names:
        bottom_packs.append(
            _fit_predict_series(work, split, name, horizon, context, model_name, seed, cfg)
        )
    top_pack = _fit_predict_series(work, split, h.top_name, horizon, context, model_name, seed, cfg)
    aligned = _align(bottom_packs, top_pack)

    # Covariance from validation residuals only (not outer test)
    y_full_val = np.concatenate([aligned["yb_val"], aligned["yt_val"].reshape(-1, 1)], axis=1)
    p_full_val = np.concatenate([aligned["pb_val"], aligned["pt_val"].reshape(-1, 1)], axis=1)
    t_cov0 = time.perf_counter()
    cov = estimate_residual_covariance(y_full_val, p_full_val, shrink_diag=0.1)
    cov_sec = time.perf_counter() - t_cov0
    series_var = np.maximum(np.diag(cov), 1e-12)
    try:
        cond = float(np.linalg.cond(cov))
    except np.linalg.LinAlgError:
        cond = float("inf")

    # Block length from train residuals of top series (base independent)
    train_resid = aligned["yt_train"] - np.nanmean(aligned["yt_train"])  # placeholder scale
    # Use val residuals as train-derived residual proxy for ACF (pre-outer)
    val_resid = aligned["yt_val"] - aligned["pt_val"]
    bl_info = select_block_length(
        val_resid,
        forecast_horizon=horizon,
        context_length=context,
        acf_threshold=float((cfg.get("bootstrap_policy") or {}).get("acf_threshold", 0.1)),
        lower=int((cfg.get("bootstrap_policy") or {}).get("lower", 8)),
        upper=int((cfg.get("bootstrap_policy") or {}).get("upper", 256)),
    )

    pending_freeze = str(cfg.get("freeze_commit", "")).upper().startswith("PENDING")
    meta_common = {
        "experiment_stage": (
            ExperimentStage.DEVELOPMENT.value if pending_freeze else ExperimentStage.FINAL.value
        ),
        "eligible_for_final_claims": (not pending_freeze),
        "evaluation_role": "smoke_validation" if pending_freeze else "outer_evaluation",
        "freeze_commit": cfg.get("freeze_commit"),
        "freeze_tag": cfg.get("freeze_tag"),
        "dataset_fingerprint": fp.get("fingerprint"),
        "config_hash": cfg_hash,
        "dependency_lock_hash": cfg.get("dependency_lock_hash"),
        "fold": fold_id,
        "seed": seed,
        "hierarchy": entry["name"],
        "horizon": horizon,
        "context": context,
        "base_model": model_name,
        "summing_matrix_hash": entry.get("summing_matrix_hash") or summing_matrix_hash(h),
        "hierarchy_metadata_hash": entry.get("hierarchy_metadata_hash"),
        "covariance_estimation_source": "outer_train_val_residuals",
        "covariance_condition_number": cond,
        "shrinkage_parameter": 0.1,
        "block_length": bl_info["block_length"],
        "block_length_policy": bl_info,
    }

    base_rows = []
    for i, name in enumerate(list(h.bottom_names) + [h.top_name]):
        pack = bottom_packs[i] if i < len(bottom_packs) else top_pack
        y_test = pack["y_test"]
        p_test = pack["p_test"]
        # Align to shared test origins
        # (use aligned for bottoms/top)
        if i < len(h.bottom_names):
            y_t = aligned["yb_test"][:, i]
            p_t = aligned["pb_test"][:, i]
        else:
            y_t = aligned["yt_test"]
            p_t = aligned["pt_test"]
        eff = pack["efficiency"].to_dict()
        base_rows.append(
            {
                **meta_common,
                "target": name,
                "reconciliation_method": "base_forecast",
                "mae": float(mae(y_t, p_t)),
                "n_test": int(len(y_t)),
                **{f"eff_{k}": v for k, v in eff.items() if not isinstance(v, dict)},
            }
        )

    recon_rows = []
    yhat_b = aligned["pb_test"]
    yhat_t = aligned["pt_test"]
    yb_true = aligned["yb_test"]
    yt_true = aligned["yt_test"]
    coh_before = coherence_error(yhat_b, yhat_t)

    for method in methods:
        for nn in nonnegative_flags:
            t_fit0 = time.perf_counter()
            # fitting WLS/MinT params already done via cov; method application is inference
            cov_used = cov if method == "mint" else None
            var_used = series_var if method == "wls" else None
            fit_sec = time.perf_counter() - t_fit0
            t_inf0 = time.perf_counter()
            try:
                out = reconcile(
                    method,
                    h,
                    yhat_b,
                    yhat_t,
                    series_var=var_used,
                    residual_cov=cov_used,
                    nonnegative=nn,
                )
                fallback = None
            except Exception as exc:  # noqa: BLE001
                # numerical fallback to OLS
                out = reconcile("ols", h, yhat_b, yhat_t, nonnegative=nn)
                fallback = f"fallback_ols_due_to:{type(exc).__name__}"
            infer_sec = time.perf_counter() - t_inf0
            bottom_r, top_r = out["bottom"], out["top"]
            coh_after = coherence_error(bottom_r, top_r)
            adj = float(np.mean(np.abs(np.concatenate([bottom_r - yhat_b, (top_r - yhat_t).reshape(-1, 1)], axis=1))))
            top_mae = float(mae(yt_true, top_r))
            bottom_mae = float(np.mean([mae(yb_true[:, j], bottom_r[:, j]) for j in range(yb_true.shape[1])]))
            recon_rows.append(
                {
                    **meta_common,
                    "target": h.top_name,
                    "reconciliation_method": method,
                    "nonnegative": nn,
                    "numerical_fallback": fallback,
                    "coherence_error_before": float(coh_before),
                    "coherence_error_after": float(coh_after),
                    "is_coherent_after": bool(is_coherent(bottom_r, top_r, atol=1e-4)),
                    "reconciliation_adjustment_magnitude": adj,
                    "top_mae": top_mae,
                    "bottom_mae_mean": bottom_mae,
                    "mae": top_mae,
                    "recon_fit_sec": float(fit_sec + cov_sec),
                    "recon_infer_sec": float(infer_sec),
                    "cov_estimate_sec": float(cov_sec),
                    "n_test": int(len(yt_true)),
                    "y_true_top": yt_true.tolist(),
                    "y_pred_top": top_r.tolist(),
                    "y_pred_independent_top": yhat_t.tolist(),
                }
            )
    return base_rows, recon_rows


def _write_smoke_artifacts(recon_df: pd.DataFrame, out_root: Path) -> None:
    metrics = out_root / "metrics"
    tables = out_root / "tables"
    figures = out_root / "figures"
    for d in (metrics, tables, figures):
        d.mkdir(parents=True, exist_ok=True)

    slim = recon_df.drop(columns=[c for c in recon_df.columns if c.startswith("y_")], errors="ignore")
    slim.to_csv(metrics / "reconciliation_results.csv", index=False)
    summary = (
        slim.groupby(["hierarchy", "base_model", "reconciliation_method"], as_index=False)["top_mae"]
        .mean()
        .sort_values("top_mae")
    )
    summary.to_csv(tables / "main_comparison.csv", index=False)
    md_lines = ["| " + " | ".join(summary.columns) + " |", "| " + " | ".join(["---"] * len(summary.columns)) + " |"]
    for _, row in summary.iterrows():
        md_lines.append("| " + " | ".join(str(row[c]) for c in summary.columns) + " |")
    (tables / "main_comparison.md").write_text("\n".join(md_lines) + "\n")
    with open(tables / "main_comparison.tex", "w") as f:
        f.write(summary.to_latex(index=False, float_format="%.4f"))

    # One figure: coherence before/after
    fig, ax = plt.subplots(figsize=(6, 4))
    for method, g in slim.groupby("reconciliation_method"):
        ax.scatter(
            g["coherence_error_before"].mean(),
            g["coherence_error_after"].mean(),
            label=method,
            s=80,
        )
    ax.set_xlabel("Coherence error before")
    ax.set_ylabel("Coherence error after")
    ax.set_title("Smoke: coherence before/after")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures / "coherence_before_after.pdf")
    fig.savefig(figures / "coherence_before_after.png", dpi=150)
    plt.close(fig)


def run_smoke(cfg: dict[str, Any], *, resume: bool = True) -> dict[str, Any]:
    smoke = cfg.get("smoke") or {}
    out_root = ROOT / "results" / "final"
    out_root.mkdir(parents=True, exist_ok=True)
    fp = dataset_fingerprint()
    if fp["fingerprint"] != cfg.get("dataset_fingerprint"):
        raise RuntimeError(
            f"dataset fingerprint mismatch: got {fp['fingerprint']} expected {cfg.get('dataset_fingerprint')}"
        )
    panel = build_analysis_panel()
    folds = make_outer_chronological_folds(panel, n_folds=int(cfg["folds"]["n_outer"]))
    cfg_hash = _config_hash(cfg)
    registry = final_hierarchy_registry(include_network=False)

    hier_names = smoke.get("hierarchies") or ["memory_um"]
    models = smoke.get("models") or ["persistence", "ridge"]
    horizons = smoke.get("horizons") or [1]
    fold_ids = smoke.get("outer_folds") or [0]
    context = int(smoke.get("context", 32))
    seeds = smoke.get("seeds") or [0]
    methods = smoke.get("reconciliation_methods") or ["independent", "bottom_up", "wls", "mint"]
    nn_flags = smoke.get("nonnegative") or [False]

    all_base, all_recon = [], []
    for hname in hier_names:
        entry = registry[hname]
        for fold_id in fold_ids:
            for horizon in horizons:
                for model_name in models:
                    for seed in seeds:
                        key = _run_key(
                            hierarchy=hname, fold=fold_id, h=horizon, model=model_name, seed=seed
                        )
                        cache = out_root / "metrics" / "smoke_cache" / f"{key}.json"
                        if resume and cache.exists():
                            data = json.loads(cache.read_text())
                            all_base.extend(data["base"])
                            all_recon.extend(data["recon"])
                            continue
                        base_rows, recon_rows = run_hierarchy_once(
                            panel,
                            entry,
                            fold_id=int(fold_id),
                            folds=folds,
                            horizon=int(horizon),
                            context=context,
                            model_name=model_name,
                            seed=int(seed),
                            methods=methods,
                            nonnegative_flags=nn_flags,
                            cfg=cfg,
                            fp=fp,
                            cfg_hash=cfg_hash,
                        )
                        cache.parent.mkdir(parents=True, exist_ok=True)
                        # do not persist huge prediction vectors in cache for smoke success marker
                        slim_recon = []
                        for r in recon_rows:
                            rr = {k: v for k, v in r.items() if not k.startswith("y_")}
                            slim_recon.append(rr)
                        cache.write_text(json.dumps({"base": base_rows, "recon": slim_recon}, default=str))
                        all_base.extend(base_rows)
                        all_recon.extend(recon_rows)

    base_df = pd.DataFrame(all_base)
    recon_df = pd.DataFrame(all_recon)
    (out_root / "metrics").mkdir(parents=True, exist_ok=True)
    base_df.to_csv(out_root / "metrics" / "base_forecasts.csv", index=False)
    _write_smoke_artifacts(recon_df, out_root)

    # Efficiency extract
    eff_cols = [c for c in base_df.columns if c.startswith("eff_")]
    if eff_cols:
        base_df[["hierarchy", "base_model", "target", "horizon", "fold", *eff_cols]].to_csv(
            out_root / "metrics" / "efficiency.csv", index=False
        )

    # Bootstrap on smoke top predictions if present
    boot_rows = []
    boot_cfg = cfg.get("bootstrap_policy") or {}
    for (hier, model), g in recon_df.groupby(["hierarchy", "base_model"]):
        ind = g[g["reconciliation_method"] == "independent"]
        if ind.empty:
            continue
        # Need stored predictions — re-run comparison only if y_ columns exist
        if "y_true_top" not in g.columns:
            continue
        y_true = np.asarray(ind.iloc[0]["y_true_top"], dtype=float)
        y_ind = np.asarray(ind.iloc[0]["y_pred_top"], dtype=float)
        bl = int(ind.iloc[0].get("block_length", 32))
        for method in ("bottom_up", "wls", "mint"):
            sub = g[g["reconciliation_method"] == method]
            if sub.empty:
                continue
            y_m = np.asarray(sub.iloc[0]["y_pred_top"], dtype=float)
            cmp_ = paired_block_bootstrap_comparison(
                y_true,
                y_ind,
                y_m,
                block_length=bl,
                n_boot=int(boot_cfg.get("n_boot", 200)),
                seed=int(boot_cfg.get("seed", 0)),
            )
            boot_rows.append(
                {
                    "hierarchy": hier,
                    "base_model": model,
                    "method_a": "independent",
                    "method_b": method,
                    **cmp_,
                }
            )
    if boot_rows:
        boot_df = pd.DataFrame(boot_rows)
        boot_df["p_holm"] = holm_adjust(boot_df["p_value_approx"].tolist())
        boot_df.to_csv(out_root / "metrics" / "paired_block_bootstrap.csv", index=False)
        boot_df.to_csv(out_root / "metrics" / "holm_corrected_tests.csv", index=False)

    # Coherence summary
    coh = recon_df.groupby("reconciliation_method", as_index=False).agg(
        coherence_before=("coherence_error_before", "mean"),
        coherence_after=("coherence_error_after", "mean"),
        top_mae=("top_mae", "mean"),
    )
    coh.to_csv(out_root / "metrics" / "coherence.csv", index=False)
    recon_df.drop(columns=[c for c in recon_df.columns if c.startswith("y_")], errors="ignore").to_csv(
        out_root / "metrics" / "hierarchy_summary.csv", index=False
    )

    # Verify coherence for non-independent methods
    bad = recon_df[
        (recon_df["reconciliation_method"] != "independent") & (~recon_df["is_coherent_after"].astype(bool))
    ]
    if len(bad):
        raise RuntimeError(f"coherence verification failed for {len(bad)} rows")

    manifest = {
        "tier": "smoke",
        "experiment_stage": "development" if str(cfg.get("freeze_commit", "")).upper().startswith("PENDING") else "final",
        "eligible_for_final_claims": not str(cfg.get("freeze_commit", "")).upper().startswith("PENDING"),
        "evaluation_role": "smoke_validation",
        "dataset_fingerprint": fp["fingerprint"],
        "config_hash": cfg_hash,
        "freeze_commit": cfg.get("freeze_commit"),
        "freeze_tag": cfg.get("freeze_tag"),
        "n_base_rows": len(base_df),
        "n_recon_rows": len(recon_df),
        "artifacts": [
            "metrics/base_forecasts.csv",
            "metrics/reconciliation_results.csv",
            "metrics/coherence.csv",
            "tables/main_comparison.csv",
            "figures/coherence_before_after.pdf",
        ],
        "note": "Pre-freeze smoke artifacts are not eligible for FGCS claims.",
    }
    (out_root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def load_final_config(path: Path | None = None) -> dict[str, Any]:
    path = path or (ROOT / "configs" / "final_fgcs.yaml")
    return yaml.safe_load(path.read_text())
