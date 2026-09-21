"""Development-stage hierarchical reconciliation benchmark (multi-hierarchy).

Uses nested outer folds only. Not eligible for final claims.
Produces:
  results/development/metrics/hierarchy_all_runs.csv
  results/development/metrics/hierarchy_summary.csv
  results/development/tables/hierarchy_comparison.csv|.md
  results/development/figures/hierarchy_accuracy_vs_coherence.pdf
  results/development/figures/hierarchy_adjustment_by_horizon.pdf
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.runner import prepare_split_windows
from models import forecasting as F
from models.hybrid.reconciliation import (
    BOND_MEMBER_IFACES,
    bond0_hierarchy,
    bottom_up,
    coherence_error,
    core_weighted_cpu_hierarchy,
    cu_to_weighted_contrib,
    disk_hierarchy,
    estimate_residual_covariance,
    is_coherent,
    machine_core_counts,
    memory_hierarchy,
    reconcile,
    weighted_contrib_to_mean_cu,
)
from timetrack.constants import MACHINE_TO_HOST
from timetrack.data import build_analysis_panel, dataset_fingerprint, load_throughputs
from timetrack.evaluation_stage import ExperimentStage
from timetrack.metrics import mae, mase
from timetrack.splits import (
    assert_no_gap_crossing,
    build_windows,
    fold_to_split_spec,
    make_outer_chronological_folds,
    origins_for_split,
)

MACHINES = [f"machine0{i}" for i in range(1, 8)]
# Tree/linear screen is the primary hierarchy expansion; dlinear optional (slow across 8 series).
MODELS = ("persistence", "ridge", "lightgbm")
HORIZONS = (1, 8)
CONTEXT = 32
SEED = 0
BOND_AGG_ERR_MAX = 0.02  # relative mean abs aggregation error threshold
DLINEAR_HORIZONS = (1,)
INCLUDE_DLINEAR = False
if INCLUDE_DLINEAR:
    MODELS = MODELS + ("dlinear",)


def _first_step(y: np.ndarray, horizon: int) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    if y.ndim > 1:
        return y[:, 0]
    return y.reshape(-1)


def _valid_origins_for_cols(panel, cols, split_idx, context, horizon) -> np.ndarray:
    """Origins valid for EVERY column (shared timestamps; drops NaN/gap mismatches)."""
    base = origins_for_split(split_idx, context, horizon, len(panel))
    if len(base) == 0:
        return base
    mats = np.column_stack([panel[c].to_numpy(dtype=float) for c in cols])
    # Pre-filter gap crossings on base (once)
    gap_ok = []
    for o in base:
        o = int(o)
        start = o - context + 1
        t1 = o + horizon
        try:
            assert_no_gap_crossing(np.arange(start, t1 + 1), panel)
            gap_ok.append(o)
        except AssertionError:
            continue
    if not gap_ok:
        return np.asarray([], dtype=int)
    gap_ok = np.asarray(gap_ok, dtype=int)
    # Vectorized NaN check per origin window
    ok = []
    for o in gap_ok:
        start = o - context + 1
        t1 = o + horizon
        block = mats[start : t1 + 1]
        if not np.isnan(block).any():
            ok.append(o)
    return np.asarray(ok, dtype=int)


def _shared_origins(panel, split, cols, horizon, context=CONTEXT) -> dict[str, np.ndarray]:
    return {
        "train": _valid_origins_for_cols(panel, cols, split.train_idx, context, horizon),
        "val": _valid_origins_for_cols(panel, cols, split.val_idx, context, horizon),
        "test": _valid_origins_for_cols(panel, cols, split.test_idx, context, horizon),
    }


def _fit_predict(panel, split, target, horizon, context, model_name, seed=SEED):
    # Match experiments/runner.py flat policy
    flat = model_name in {
        "ridge",
        "lasso",
        "elasticnet",
        "random_forest",
        "extra_trees",
        "lightgbm",
        "xgboost",
        "catboost",
    }
    kwargs = {}
    if model_name == "dlinear":
        kwargs["epochs"] = 5  # development screen budget (neural/modern candidate)
    windows = prepare_split_windows(panel, split, target, horizon, context, flat=flat)
    model = F.build_model(model_name, horizon=horizon, context_length=context, seed=seed, **kwargs)
    t0 = time.perf_counter()
    model.fit(windows["train"].X, windows["train"].y, windows["val"].X, windows["val"].y)
    train_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    pred_val = model.predict(windows["val"].X)
    pred_test = model.predict(windows["test"].X)
    infer_s = time.perf_counter() - t1
    return {
        "y_train": _first_step(windows["train"].y, horizon),
        "y_val": _first_step(windows["val"].y, horizon),
        "y_test": _first_step(windows["test"].y, horizon),
        "p_val": _first_step(pred_val, horizon),
        "p_test": _first_step(pred_test, horizon),
        "origin_val": windows["val"].origin_idx,
        "origin_test": windows["test"].origin_idx,
        "train_s": train_s,
        "infer_s": infer_s,
    }


def _align_by_origins(packs: list[dict], top_pack: dict) -> dict:
    """Intersect val/test origins across bottom packs + top; return aligned arrays."""
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
        return (
            pack[f"y_{which}"][ii],
            pack[f"p_{which}"][ii],
        )

    yb_val = np.column_stack([_take(p, "val", ov)[0] for p in packs])
    pb_val = np.column_stack([_take(p, "val", ov)[1] for p in packs])
    yb_test = np.column_stack([_take(p, "test", ot)[0] for p in packs])
    pb_test = np.column_stack([_take(p, "test", ot)[1] for p in packs])
    yt_val, pt_val = _take(top_pack, "val", ov)
    yt_test, pt_test = _take(top_pack, "test", ot)
    # train series for MASE: use full train vectors (not origin-aligned)
    yb_train = np.column_stack([p["y_train"][: min(len(p["y_train"]) for p in packs)] for p in packs])
    # better: truncate each to min length independently is wrong for MASE scale — use each series train as-is via list
    return {
        "yb_val": yb_val,
        "pb_val": pb_val,
        "yb_test": yb_test,
        "pb_test": pb_test,
        "yt_val": yt_val,
        "pt_val": pt_val,
        "yt_test": yt_test,
        "pt_test": pt_test,
        "yb_train_list": [p["y_train"] for p in packs],
        "yt_train": top_pack["y_train"],
    }

def _attach_nic_columns(panel: pd.DataFrame, host: str) -> pd.DataFrame:
    thr = load_throughputs()
    # align by row order (same length as compute after load_throughputs merge pattern)
    out = panel.copy()
    for iface in BOND_MEMBER_IFACES[host]:
        for direction in ("transmitted", "received"):
            col = f"{direction}_throughput_{host}:-network-device-{iface}"
            if col in thr.columns:
                out[col] = thr[col].values[: len(out)]
    bond_tx = f"transmitted_throughput_{host}:-network-device-bond0"
    bond_rx = f"received_throughput_{host}:-network-device-bond0"
    if bond_tx in thr.columns:
        out[bond_tx] = thr[bond_tx].values[: len(out)]
    if bond_rx in thr.columns:
        out[bond_rx] = thr[bond_rx].values[: len(out)]
    return out


def _bond_agg_rel_error(panel: pd.DataFrame, host: str, direction: str = "transmitted") -> float:
    h = bond0_hierarchy(host, direction)
    B = panel[list(h.bottom_names)].to_numpy(dtype=float)
    T = panel[h.top_name].to_numpy(dtype=float)
    mask = np.isfinite(B).all(axis=1) & np.isfinite(T)
    if mask.sum() < 100:
        return float("inf")
    s = B[mask].sum(axis=1)
    t = T[mask]
    scale = np.mean(np.abs(t)) + 1e-12
    return float(np.mean(np.abs(s - t)) / scale)


def _score_hierarchy(
    hierarchy_name: str,
    method: str,
    y_bottom: np.ndarray,
    y_top: np.ndarray,
    out: dict,
    y_train_top: np.ndarray,
    y_train_bottom: np.ndarray,
    p_bottom_base: np.ndarray,
    p_top_base: np.ndarray,
    train_s: float,
    infer_s: float,
    *,
    outer_fold: int,
    model: str,
    horizon: int,
    extra: dict | None = None,
) -> dict:
    bottom = out["bottom"]
    top = out["top"]
    adj = float(np.mean(np.abs(bottom - p_bottom_base)) + np.mean(np.abs(top - p_top_base)))
    child_maes = [mae(y_bottom[:, i], bottom[:, i]) for i in range(y_bottom.shape[1])]
    child_mases = [
        mase(y_bottom[:, i], bottom[:, i], y_train_bottom[:, i]) for i in range(y_bottom.shape[1])
    ]
    row = {
        "experiment_stage": ExperimentStage.DEVELOPMENT.value,
        "eligible_for_final_claims": False,
        "hierarchy": hierarchy_name,
        "method": method,
        "model": model,
        "horizon": horizon,
        "context": CONTEXT,
        "outer_fold": outer_fold,
        "top_mae": mae(y_top, top),
        "top_mase": mase(y_top, top, y_train_top),
        "bottom_mae_macro": float(np.nanmean(child_maes)),
        "bottom_mase_macro": float(np.nanmean(child_mases)),
        "worst_child_mae": float(np.nanmax(child_maes)),
        "coherence_error": out["coherence_error"],
        "coherent": bool(
            is_coherent(bottom, top, atol=1e-3 * (1 + np.mean(np.abs(top))), rtol=1e-5)
        ),
        "adjustment_mae": adj,
        "train_seconds_total": train_s,
        "infer_seconds_total": infer_s,
        "n_test": int(len(y_top)),
    }
    if extra:
        row.update(extra)
    return row


def run_sum_hierarchy(
    panel,
    split,
    outer_fold: int,
    hierarchy,
    bottom_cols: list[str],
    top_col: str,
    model: str,
    horizon: int,
    *,
    nonnegative_variants: bool = True,
) -> list[dict]:
    """Fit per-series models and evaluate reconciliation methods."""
    bottom_packs = [_fit_predict(panel, split, c, horizon, CONTEXT, model) for c in bottom_cols]
    top_pack = _fit_predict(panel, split, top_col, horizon, CONTEXT, model)
    al = _align_by_origins(bottom_packs, top_pack)
    yb_val, pb_val = al["yb_val"], al["pb_val"]
    yb_test, pb_test = al["yb_test"], al["pb_test"]
    yt_val, pt_val = al["yt_val"], al["pt_val"]
    yt_test, pt_test = al["yt_test"], al["pt_test"]
    yt_train = al["yt_train"]
    yb_train_list = al["yb_train_list"]

    # residual cov / vars from VAL only (inner), never outer test
    full_true_val = np.concatenate([yb_val, yt_val.reshape(-1, 1)], axis=1)
    full_pred_val = np.concatenate([pb_val, pt_val.reshape(-1, 1)], axis=1)
    resid_cov = estimate_residual_covariance(full_true_val, full_pred_val, shrink_diag=0.1)
    series_var = np.maximum(np.diag(resid_cov), 1e-12)

    train_s = sum(p["train_s"] for p in bottom_packs) + top_pack["train_s"]
    infer_s = sum(p["infer_s"] for p in bottom_packs) + top_pack["infer_s"]

    methods = [
        ("independent", {}),
        ("bottom_up", {}),
        ("top_down", {}),
        ("ols", {}),
        ("wls", {"series_var": series_var}),
        ("mint", {"residual_cov": resid_cov}),
    ]
    if nonnegative_variants:
        methods += [
            ("bottom_up", {"nonnegative": True, "_tag": "bottom_up_nn"}),
            ("ols", {"nonnegative": True, "_tag": "ols_nn"}),
        ]

    rows = []
    for method, kwargs in methods:
        tag = kwargs.pop("_tag", method)
        nn = bool(kwargs.pop("nonnegative", False))
        t0 = time.perf_counter()
        out = reconcile(method, hierarchy, pb_test, pt_test, nonnegative=nn, **kwargs)
        recon_s = time.perf_counter() - t0
        bottom = out["bottom"]
        top = out["top"]
        adj = float(np.mean(np.abs(bottom - pb_test)) + np.mean(np.abs(top - pt_test)))
        child_maes = [mae(yb_test[:, i], bottom[:, i]) for i in range(yb_test.shape[1])]
        child_mases = [
            mase(yb_test[:, i], bottom[:, i], yb_train_list[i]) for i in range(yb_test.shape[1])
        ]
        rows.append(
            {
                "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                "eligible_for_final_claims": False,
                "hierarchy": hierarchy.name,
                "method": tag,
                "model": model,
                "horizon": horizon,
                "context": CONTEXT,
                "outer_fold": outer_fold,
                "top_mae": mae(yt_test, top),
                "top_mase": mase(yt_test, top, yt_train),
                "bottom_mae_macro": float(np.nanmean(child_maes)),
                "bottom_mase_macro": float(np.nanmean(child_mases)),
                "worst_child_mae": float(np.nanmax(child_maes)),
                "coherence_error": out["coherence_error"],
                "coherent": bool(
                    is_coherent(bottom, top, atol=1e-3 * (1 + np.mean(np.abs(top))), rtol=1e-5)
                ),
                "adjustment_mae": adj,
                "train_seconds_total": train_s,
                "infer_seconds_total": infer_s + recon_s,
                "n_test": int(len(yt_test)),
            }
        )
    return rows


def run_cpu_hierarchy(panel, split, outer_fold, model, horizon) -> list[dict]:
    """Fit CU locals; reconcile on core-weighted contributions."""
    h = core_weighted_cpu_hierarchy()
    bottom_cols = [f"{m}_CU" for m in MACHINES]
    packs = [_fit_predict(panel, split, c, horizon, CONTEXT, model) for c in bottom_cols]
    top_pack = _fit_predict(panel, split, "cluster_mean_CU", horizon, CONTEXT, model)
    al = _align_by_origins(packs, top_pack)
    yb, pb = al["yb_test"], al["pb_test"]
    yb_val, pb_val = al["yb_val"], al["pb_val"]
    yb_train_list = al["yb_train_list"]
    yt_cu, pt_cu = al["yt_test"], al["pt_test"]
    yt_cu_val, pt_cu_val = al["yt_val"], al["pt_val"]
    yt_cu_train = al["yt_train"]

    zb, zp = cu_to_weighted_contrib(yb), cu_to_weighted_contrib(pb)
    zb_val, zp_val = cu_to_weighted_contrib(yb_val), cu_to_weighted_contrib(pb_val)
    zt, zt_val = zb.sum(1), zb_val.sum(1)
    n_tr = min(map(len, yb_train_list))
    zt_train = cu_to_weighted_contrib(np.column_stack([p[:n_tr] for p in yb_train_list])).sum(1)
    cores = machine_core_counts()
    div = float(sum(cores.values()))
    pt_w = pt_cu * div
    pt_w_val = pt_cu_val * div

    full_true_val = np.concatenate([zb_val, zt_val.reshape(-1, 1)], axis=1)
    full_pred_val = np.concatenate([zp_val, pt_w_val.reshape(-1, 1)], axis=1)
    resid_cov = estimate_residual_covariance(full_true_val, full_pred_val, shrink_diag=0.1)
    series_var = np.maximum(np.diag(resid_cov), 1e-12)

    train_s = sum(p["train_s"] for p in packs) + top_pack["train_s"]
    infer_s = sum(p["infer_s"] for p in packs) + top_pack["infer_s"]

    rows = []
    child_maes = [mae(yb[:, i], pb[:, i]) for i in range(7)]
    rows.append(
        {
            "experiment_stage": ExperimentStage.DEVELOPMENT.value,
            "eligible_for_final_claims": False,
            "hierarchy": h.name,
            "method": "independent",
            "model": model,
            "horizon": horizon,
            "context": CONTEXT,
            "outer_fold": outer_fold,
            "top_mae": mae(yt_cu, pt_cu),
            "top_mase": mase(yt_cu, pt_cu, yt_cu_train),
            "bottom_mae_macro": float(np.nanmean(child_maes)),
            "bottom_mase_macro": float(
                np.nanmean([mase(yb[:, i], pb[:, i], yb_train_list[i]) for i in range(7)])
            ),
            "worst_child_mae": float(np.nanmax(child_maes)),
            "coherence_error": coherence_error(zp, pt_w),
            "coherent": False,
            "adjustment_mae": 0.0,
            "train_seconds_total": train_s,
            "infer_seconds_total": infer_s,
            "n_test": int(len(yt_cu)),
            "top_metric_scale": "cluster_mean_CU",
        }
    )

    for method, kwargs, tag in [
        ("bottom_up", {}, "bottom_up"),
        ("top_down", {}, "top_down"),
        ("ols", {}, "ols"),
        ("wls", {"series_var": series_var}, "wls"),
        ("mint", {"residual_cov": resid_cov}, "mint"),
        ("bottom_up", {"nonnegative": True}, "bottom_up_nn"),
    ]:
        nn = bool(kwargs.pop("nonnegative", False))
        out = reconcile(method, h, zp, pt_w, nonnegative=nn, **kwargs)
        top_mean = weighted_contrib_to_mean_cu(out["top"])
        w = np.array([cores[m] for m in MACHINES], dtype=float)
        bottom_cu = out["bottom"] / w.reshape(1, -1)
        child_maes = [mae(yb[:, i], bottom_cu[:, i]) for i in range(7)]
        adj = float(np.mean(np.abs(bottom_cu - pb)) + np.mean(np.abs(top_mean - pt_cu)))
        rows.append(
            {
                "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                "eligible_for_final_claims": False,
                "hierarchy": h.name,
                "method": tag,
                "model": model,
                "horizon": horizon,
                "context": CONTEXT,
                "outer_fold": outer_fold,
                "top_mae": mae(yt_cu, top_mean),
                "top_mae_vs_weighted_mean": mae(weighted_contrib_to_mean_cu(zt), top_mean),
                "top_mase": mase(
                    weighted_contrib_to_mean_cu(zt),
                    top_mean,
                    weighted_contrib_to_mean_cu(zt_train),
                ),
                "bottom_mae_macro": float(np.nanmean(child_maes)),
                "bottom_mase_macro": float(
                    np.nanmean([mase(yb[:, i], bottom_cu[:, i], yb_train_list[i]) for i in range(7)])
                ),
                "worst_child_mae": float(np.nanmax(child_maes)),
                "coherence_error": coherence_error(out["bottom"], out["top"]),
                "coherent": is_coherent(
                    out["bottom"], out["top"], atol=1e-3 * (1 + np.mean(np.abs(out["top"])))
                ),
                "adjustment_mae": adj,
                "train_seconds_total": train_s,
                "infer_seconds_total": infer_s,
                "n_test": int(len(yt_cu)),
                "top_metric_scale": "weighted_mean_CU",
            }
        )
    return rows


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    keys = ["hierarchy", "method", "model", "horizon"]
    aggs = {
        "top_mae": ["mean", "std"],
        "top_mase": ["mean", "std"],
        "bottom_mae_macro": ["mean", "std"],
        "worst_child_mae": ["mean", "max"],
        "coherence_error": ["mean", "max"],
        "adjustment_mae": ["mean"],
        "infer_seconds_total": ["mean"],
        "outer_fold": "count",
    }
    out = df.groupby(keys, dropna=False).agg(aggs)
    out.columns = ["_".join(c).strip("_") for c in out.columns]
    return out.reset_index()


def write_figures(df: pd.DataFrame, fig_dir: Path) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    # accuracy vs coherence (fold-mean)
    g = (
        df.groupby(["hierarchy", "method", "model"], as_index=False)
        .agg(top_mae=("top_mae", "mean"), coherence_error=("coherence_error", "mean"))
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    for method, sub in g.groupby("method"):
        ax.scatter(sub["coherence_error"] + 1e-12, sub["top_mae"], label=method, alpha=0.75)
    ax.set_xscale("log")
    ax.set_xlabel("coherence error (log)")
    ax.set_ylabel("top MAE (mean over folds/horizons/models in group)")
    ax.set_title("Development: hierarchy accuracy vs coherence")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(fig_dir / "hierarchy_accuracy_vs_coherence.pdf")
    fig.savefig(fig_dir / "hierarchy_accuracy_vs_coherence.png", dpi=120)
    plt.close(fig)

    g2 = df.groupby(["horizon", "method"], as_index=False).agg(adjustment_mae=("adjustment_mae", "mean"))
    fig, ax = plt.subplots(figsize=(8, 4))
    for method, sub in g2.groupby("method"):
        ax.plot(sub["horizon"], sub["adjustment_mae"], marker="o", label=method)
    ax.set_xlabel("horizon")
    ax.set_ylabel("mean |adjustment|")
    ax.set_title("Reconciliation adjustment by horizon")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(fig_dir / "hierarchy_adjustment_by_horizon.pdf")
    fig.savefig(fig_dir / "hierarchy_adjustment_by_horizon.png", dpi=120)
    plt.close(fig)


def main():
    panel = build_analysis_panel()
    fp = dataset_fingerprint()
    folds = make_outer_chronological_folds(panel, n_folds=3)

    # Network: pick first host with acceptable bond0 aggregation error
    net_host = None
    net_dir = "transmitted"
    for host in ("acamas", "dedale", "perse"):
        p2 = _attach_nic_columns(panel, host)
        err = _bond_agg_rel_error(p2, host, net_dir)
        if err <= BOND_AGG_ERR_MAX:
            net_host, panel_net, net_err = host, p2, err
            break
    else:
        panel_net, net_err = None, None

    rows: list[dict] = []
    for fold in folds:
        split = fold_to_split_spec(fold)
        for model in MODELS:
            for horizon in HORIZONS:
                if model == "dlinear" and horizon not in DLINEAR_HORIZONS:
                    continue
                print(f"fold={fold.fold_id} model={model} h={horizon} memory/disk/cpu...", flush=True)
                rows += run_sum_hierarchy(
                    panel,
                    split,
                    fold.fold_id,
                    memory_hierarchy(),
                    [f"{m}_UM" for m in MACHINES],
                    "cluster_UM",
                    model,
                    horizon,
                )
                rows += run_sum_hierarchy(
                    panel,
                    split,
                    fold.fold_id,
                    disk_hierarchy(),
                    [f"{m}_UD" for m in MACHINES],
                    "cluster_UD",
                    model,
                    horizon,
                )
                rows += run_cpu_hierarchy(panel, split, fold.fold_id, model, horizon)

                if panel_net is not None and net_host is not None:
                    h = bond0_hierarchy(net_host, net_dir)
                    rows += run_sum_hierarchy(
                        panel_net,
                        split,
                        fold.fold_id,
                        h,
                        list(h.bottom_names),
                        h.top_name,
                        model,
                        horizon,
                        nonnegative_variants=True,
                    )
                    # annotate last network rows
                    for r in rows:
                        if r.get("hierarchy") == h.name and r.get("outer_fold") == fold.fold_id and r.get("model") == model and r.get("horizon") == horizon:
                            r["bond_agg_rel_error"] = net_err
                            r["bond_host"] = net_host

    df = pd.DataFrame(rows)
    metrics_dir = ROOT / "results" / "development" / "metrics"
    tables_dir = ROOT / "results" / "development" / "tables"
    fig_dir = ROOT / "results" / "development" / "figures"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    all_path = metrics_dir / "hierarchy_all_runs.csv"
    df.to_csv(all_path, index=False)
    summary = summarize(df)
    summary.to_csv(metrics_dir / "hierarchy_summary.csv", index=False)

    # Comparison table: relative to independent within hierarchy×model×horizon
    comps = []
    for keys, g in df.groupby(["hierarchy", "model", "horizon", "outer_fold"]):
        base = g[g["method"] == "independent"]
        if base.empty:
            continue
        b = base.iloc[0]
        for _, r in g.iterrows():
            comps.append(
                {
                    "hierarchy": keys[0],
                    "model": keys[1],
                    "horizon": keys[2],
                    "outer_fold": keys[3],
                    "method": r["method"],
                    "top_mae": r["top_mae"],
                    "top_mae_vs_indep": r["top_mae"] - b["top_mae"],
                    "top_mae_rel": (r["top_mae"] / b["top_mae"]) if b["top_mae"] else np.nan,
                    "bottom_mae_macro": r["bottom_mae_macro"],
                    "worst_child_mae": r["worst_child_mae"],
                    "coherence_error": r["coherence_error"],
                    "coherent": r["coherent"],
                    "adjustment_mae": r["adjustment_mae"],
                }
            )
    comp = pd.DataFrame(comps)
    comp.to_csv(tables_dir / "hierarchy_comparison.csv", index=False)

    # Markdown pivot: mean top_mae_rel by hierarchy×method
    pivot = (
        comp.groupby(["hierarchy", "method"], as_index=False)
        .agg(
            mean_top_mae_rel=("top_mae_rel", "mean"),
            mean_coherence=("coherence_error", "mean"),
            mean_worst_child=("worst_child_mae", "mean"),
            frac_coherent=("coherent", "mean"),
        )
        .sort_values(["hierarchy", "mean_top_mae_rel"])
    )
    md = ["# Hierarchy comparison (development)", "", f"Fingerprint: `{fp['fingerprint']}`", ""]
    md.append(pivot.to_markdown(index=False))
    md.append("")
    md.append("eligible_for_final_claims: false")
    (tables_dir / "hierarchy_comparison.md").write_text("\n".join(md))

    write_figures(df, fig_dir)

    meta = {
        "experiment_stage": ExperimentStage.DEVELOPMENT.value,
        "eligible_for_final_claims": False,
        "dataset_fingerprint": fp["fingerprint"],
        "models": list(MODELS),
        "horizons": list(HORIZONS),
        "n_folds": len(folds),
        "n_rows": len(df),
        "bond_host": net_host,
        "bond_agg_rel_error": net_err,
        "note": "Expanded hierarchical development screen; do not declare a single-fold winner.",
    }
    (metrics_dir / "hierarchy_all_runs.meta.json").write_text(json.dumps(meta, indent=2))
    print(summary.head(20).to_string(index=False))
    print("wrote", all_path, "rows=", len(df))


if __name__ == "__main__":
    main()
