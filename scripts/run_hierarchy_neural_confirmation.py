"""Targeted neural hierarchy confirmation for memory_um and cpu_core_weighted."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models.hybrid.reconciliation import (
    core_weighted_cpu_hierarchy,
    cu_to_weighted_contrib,
    estimate_residual_covariance,
    machine_core_counts,
    memory_hierarchy,
    reconcile,
    weighted_contrib_to_mean_cu,
)
from scripts.run_hierarchy_dev import (
    CONTEXT,
    MACHINES,
    _align_by_origins,
    _fit_predict,
)
from timetrack.data import build_analysis_panel, dataset_fingerprint
from timetrack.evaluation_stage import ExperimentStage
from timetrack.metrics import mae, mase_result
from timetrack.splits import fold_to_split_spec, make_outer_chronological_folds

HORIZONS = (1, 8, 16)
SEEDS = (0, 1)
MODELS = ("lstm", "dlinear")
METHODS = ("independent", "bottom_up", "wls", "mint", "bottom_up_nn")
# Bound neural cost in confirmation screen
NEURAL_EPOCHS = 4


def _patch_fit(panel, split, target, horizon, model, seed):
    # reuse hierarchy helper but inject seed/epochs via monkeypatch of build — call local
    from experiments.runner import prepare_split_windows
    from models import forecasting as F
    import time

    flat = False
    kwargs = {"epochs": NEURAL_EPOCHS, "patience": 2, "num_threads": 1}
    if model == "dlinear":
        kwargs.update({"timeout_sec": 90, "max_batches_per_epoch": 40})
    windows = prepare_split_windows(panel, split, target, horizon, CONTEXT, flat=flat)
    m = F.build_model(model, horizon=horizon, context_length=CONTEXT, seed=seed, **kwargs)
    t0 = time.perf_counter()
    m.fit(windows["train"].X, windows["train"].y, windows["val"].X, windows["val"].y)
    train_s = time.perf_counter() - t0
    pred_val = m.predict(windows["val"].X)
    pred_test = m.predict(windows["test"].X)

    def first(y):
        y = np.asarray(y, dtype=float)
        return y[:, 0] if y.ndim > 1 else y.reshape(-1)

    return {
        "y_train": first(windows["train"].y),
        "y_val": first(windows["val"].y),
        "y_test": first(windows["test"].y),
        "p_val": first(pred_val),
        "p_test": first(pred_test),
        "origin_val": windows["val"].origin_idx,
        "origin_test": windows["test"].origin_idx,
        "train_s": train_s,
        "infer_s": m.metadata.inference_time_sec or 0.0,
    }


def run_memory(panel, split, fold_id, model, horizon, seed):
    h = memory_hierarchy()
    bottoms = [f"{m}_UM" for m in MACHINES]
    packs = [_patch_fit(panel, split, c, horizon, model, seed) for c in bottoms]
    top = _patch_fit(panel, split, "cluster_UM", horizon, model, seed)
    al = _align_by_origins(packs, top)
    cov = estimate_residual_covariance(
        np.concatenate([al["yb_val"], al["yt_val"].reshape(-1, 1)], 1),
        np.concatenate([al["pb_val"], al["pt_val"].reshape(-1, 1)], 1),
        shrink_diag=0.1,
    )
    var = np.maximum(np.diag(cov), 1e-12)
    rows = []
    for method in METHODS:
        kwargs = {}
        tag = method
        nn = False
        if method == "bottom_up_nn":
            method, nn, tag = "bottom_up", True, "bottom_up_nn"
        if method == "wls":
            kwargs["series_var"] = var
        if method == "mint":
            kwargs["residual_cov"] = cov
        out = reconcile(method, h, al["pb_test"], al["pt_test"], nonnegative=nn, **kwargs)
        mr = mase_result(al["yt_test"], out["top"], al["yt_train"])
        rows.append(
            {
                "hierarchy": h.name,
                "model": model,
                "horizon": horizon,
                "seed": seed,
                "outer_fold": fold_id,
                "method": tag,
                "top_mae": mae(al["yt_test"], out["top"]),
                "top_mase": mr["mase"],
                "mase_valid": mr["mase_valid"],
                "coherence_error": out["coherence_error"],
                "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                "eligible_for_final_claims": False,
            }
        )
    return rows


def run_cpu(panel, split, fold_id, model, horizon, seed):
    h = core_weighted_cpu_hierarchy()
    packs = [_patch_fit(panel, split, f"{m}_CU", horizon, model, seed) for m in MACHINES]
    top = _patch_fit(panel, split, "cluster_mean_CU", horizon, model, seed)
    al = _align_by_origins(packs, top)
    yb, pb = al["yb_test"], al["pb_test"]
    zb, zp = cu_to_weighted_contrib(yb), cu_to_weighted_contrib(pb)
    zb_val, zp_val = cu_to_weighted_contrib(al["yb_val"]), cu_to_weighted_contrib(al["pb_val"])
    div = float(sum(machine_core_counts().values()))
    pt_w = al["pt_test"] * div
    pt_w_val = al["pt_val"] * div
    zt_val = zb_val.sum(1)
    cov = estimate_residual_covariance(
        np.concatenate([zb_val, zt_val.reshape(-1, 1)], 1),
        np.concatenate([zp_val, pt_w_val.reshape(-1, 1)], 1),
        shrink_diag=0.1,
    )
    var = np.maximum(np.diag(cov), 1e-12)
    cores = machine_core_counts()
    w = np.array([cores[m] for m in MACHINES], dtype=float)
    rows = []
    for method in METHODS:
        kwargs = {}
        tag = method
        nn = False
        mth = method
        if method == "bottom_up_nn":
            mth, nn, tag = "bottom_up", True, "bottom_up_nn"
        if mth == "wls":
            kwargs["series_var"] = var
        if mth == "mint":
            kwargs["residual_cov"] = cov
        if mth == "independent":
            top_mean = al["pt_test"]
            bottom_cu = pb
            coh = float(np.mean(np.abs(zp.sum(1) - pt_w)))
            yt = al["yt_test"]
        else:
            out = reconcile(mth, h, zp, pt_w, nonnegative=nn, **kwargs)
            top_mean = weighted_contrib_to_mean_cu(out["top"])
            bottom_cu = out["bottom"] / w.reshape(1, -1)
            coh = out["coherence_error"]
            yt = weighted_contrib_to_mean_cu(zb.sum(1))
        mr = mase_result(yt, top_mean, al["yt_train"])
        rows.append(
            {
                "hierarchy": h.name,
                "model": model,
                "horizon": horizon,
                "seed": seed,
                "outer_fold": fold_id,
                "method": tag,
                "top_mae": mae(yt, top_mean),
                "top_mase": mr["mase"],
                "mase_valid": mr["mase_valid"],
                "coherence_error": coh,
                "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                "eligible_for_final_claims": False,
            }
        )
    return rows


def main():
    panel = build_analysis_panel()
    fp = dataset_fingerprint()
    folds = make_outer_chronological_folds(panel, n_folds=3)
    rows = []
    for fold in folds:
        split = fold_to_split_spec(fold)
        for model in MODELS:
            for horizon in HORIZONS:
                for seed in SEEDS:
                    print(f"{fold.fold_id} {model} h={horizon} seed={seed}", flush=True)
                    rows += run_memory(panel, split, fold.fold_id, model, horizon, seed)
                    rows += run_cpu(panel, split, fold.fold_id, model, horizon, seed)
    df = pd.DataFrame(rows)
    tables = ROOT / "results" / "development" / "tables"
    figs = ROOT / "results" / "development" / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)
    df.to_csv(tables / "hierarchy_neural_confirmation.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    g = df.groupby(["hierarchy", "method", "model"], as_index=False)["top_mae"].mean()
    fig, ax = plt.subplots(figsize=(8, 4))
    for (hname, model), sub in g.groupby(["hierarchy", "model"]):
        ax.plot(sub["method"], sub["top_mae"], marker="o", label=f"{hname}:{model}")
    ax.tick_params(axis="x", rotation=30)
    ax.set_ylabel("mean top MAE")
    ax.set_title("Neural hierarchy confirmation (dev)")
    ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(figs / "hierarchy_neural_confirmation.pdf")
    fig.savefig(figs / "hierarchy_neural_confirmation.png", dpi=120)
    plt.close(fig)
    (tables / "hierarchy_neural_confirmation.meta.json").write_text(
        json.dumps({"eligible_for_final_claims": False, "fingerprint": fp["fingerprint"], "n": len(df)}, indent=2)
    )
    print(df.groupby(["hierarchy", "method"])["top_mae"].mean())
    print("wrote neural confirmation", len(df))


if __name__ == "__main__":
    main()
