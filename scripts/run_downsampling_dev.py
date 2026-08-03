"""Downsampling forecasting study (development)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from models import forecasting as F
from scripts.run_peak_metrics_dev import peak_eval, peak_threshold
from timetrack.constants import SAMPLING_SECONDS
from timetrack.data import build_analysis_panel, dataset_fingerprint
from timetrack.evaluation_stage import ExperimentStage
from timetrack.metrics import mae, mase_result
from timetrack.splits import build_windows, fold_to_split_spec, make_outer_chronological_folds, origins_for_split

TARGETS = (
    "cluster_mean_CU",
    "cluster_UM",
    "machine01_DWT",
    "machine01_tx_bond0",
    "averageRttWithGoogleDns",
    "jitterWithGoogleDns",
)
FACTORS = (
    ("native", 1),
    ("2x", 2),
    ("approx_3min", 4),
    ("approx_5min", 7),
)
HORIZONS = (1, 8)
SEED = 0


def downsample_series(values: np.ndarray, factor: int) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    n = len(values) - (len(values) % factor)
    if n <= 0:
        return values[:0]
    v = values[:n].reshape(-1, factor)
    # nanmean per bin
    with np.errstate(all="ignore"):
        out = np.nanmean(v, axis=1)
    return out


def downsample_panel(panel: pd.DataFrame, cols: list[str], factor: int) -> pd.DataFrame:
    keep = ["timestamp", "segment", *cols]
    keep = [c for c in keep if c in panel.columns]
    if factor == 1:
        return panel[keep].copy()
    n = len(panel) - (len(panel) % factor)
    idx = np.arange(0, n, factor)
    out = {"timestamp": panel["timestamp"].iloc[idx].values}
    if "segment" in panel.columns:
        # take segment at bin start (bins do not cross outage by construction of post-outage folds)
        out["segment"] = panel["segment"].iloc[idx].values
    for c in cols:
        out[c] = downsample_series(panel[c].to_numpy(float), factor)
    return pd.DataFrame(out)


def main():
    panel = build_analysis_panel()
    fp = dataset_fingerprint()
    folds = make_outer_chronological_folds(panel, n_folds=3)
    rows = []
    for fold in folds:
        split = fold_to_split_spec(fold)
        # timestamp bounds
        t0 = panel["timestamp"].iloc[int(split.train_idx.min())]
        t1 = panel["timestamp"].iloc[int(split.train_idx.max())]
        v0 = panel["timestamp"].iloc[int(split.val_idx.min())]
        v1 = panel["timestamp"].iloc[int(split.val_idx.max())]
        e0 = panel["timestamp"].iloc[int(split.test_idx.min())]
        e1 = panel["timestamp"].iloc[int(split.test_idx.max())]

        for label, factor in FACTORS:
            context = max(4, int(round(32 / factor)))
            for target in TARGETS:
                if target not in panel.columns:
                    continue
                dpanel = downsample_panel(panel, [target], factor)
                # rebuild split by timestamps
                ts = pd.to_datetime(dpanel["timestamp"])
                train_idx = np.flatnonzero((ts >= t0) & (ts <= t1))
                val_idx = np.flatnonzero((ts >= v0) & (ts <= v1))
                test_idx = np.flatnonzero((ts >= e0) & (ts <= e1))
                if len(train_idx) < context + 10 or len(test_idx) < 10:
                    continue
                values = dpanel[[target]].to_numpy(float)
                for horizon in HORIZONS:
                    o_tr = origins_for_split(train_idx, context, horizon, len(dpanel))
                    o_va = origins_for_split(val_idx, context, horizon, len(dpanel))
                    o_te = origins_for_split(test_idx, context, horizon, len(dpanel))
                    try:
                        tr = build_windows(values, o_tr, context, horizon, flat=True, panel_for_gap_check=dpanel)
                        va = build_windows(values, o_va, context, horizon, flat=True, panel_for_gap_check=dpanel)
                        te = build_windows(values, o_te, context, horizon, flat=True, panel_for_gap_check=dpanel)
                    except ValueError:
                        continue
                    y_train = values[train_idx, 0]
                    for model_name in ("persistence", "ridge"):
                        model = F.build_model(model_name, horizon=horizon, context_length=context, seed=SEED)
                        model.fit(tr.X, tr.y, va.X, va.y)
                        pred = np.asarray(model.predict(te.X), dtype=float)
                        y = np.asarray(te.y, dtype=float)
                        if pred.ndim > 1:
                            pred, y = pred[:, 0], y[:, 0]
                        mr = mase_result(y, pred, y_train)
                        thr = peak_threshold(y_train, "q95")
                        pk = peak_eval(y, pred, thr, sampling_seconds=SAMPLING_SECONDS * factor)
                        rows.append(
                            {
                                "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                                "eligible_for_final_claims": False,
                                "resolution": label,
                                "factor": factor,
                                "target": target,
                                "model": model_name,
                                "horizon_steps": horizon,
                                "wallclock_horizon_sec": horizon * SAMPLING_SECONDS * factor,
                                "context_steps": context,
                                "outer_fold": fold.fold_id,
                                "mae": mae(y, pred),
                                "mase": mr["mase"],
                                "mase_valid": mr["mase_valid"],
                                "peak_recall": pk["peak_recall"],
                                "peak_magnitude_mae": pk["peak_magnitude_mae"],
                                "train_seconds": model.metadata.training_time_sec,
                                "infer_seconds": model.metadata.inference_time_sec,
                                "n_test": len(y),
                            }
                        )

    df = pd.DataFrame(rows)
    tables = ROOT / "results" / "development" / "tables"
    figs = ROOT / "results" / "development" / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)
    df.to_csv(tables / "downsampling_comparison.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    g = df[(df.horizon_steps == 1) & (df.model == "ridge")].groupby(["resolution", "target"], as_index=False)["mae"].mean()
    fig, ax = plt.subplots(figsize=(8, 4))
    for target, sub in g.groupby("target"):
        order = ["native", "2x", "approx_3min", "approx_5min"]
        sub = sub.set_index("resolution").reindex(order)
        ax.plot(order, sub["mae"], marker="o", label=target)
    ax.set_ylabel("MAE")
    ax.set_title("Error vs sampling resolution (ridge, h=1 steps)")
    ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(figs / "error_vs_sampling_resolution.pdf")
    fig.savefig(figs / "error_vs_sampling_resolution.png", dpi=120)
    plt.close(fig)

    g2 = df[(df.horizon_steps == 1) & (df.model == "ridge")].groupby(["resolution", "target"], as_index=False)["peak_recall"].mean()
    fig, ax = plt.subplots(figsize=(8, 4))
    for target, sub in g2.groupby("target"):
        order = ["native", "2x", "approx_3min", "approx_5min"]
        sub = sub.set_index("resolution").reindex(order)
        ax.plot(order, sub["peak_recall"], marker="o", label=target)
    ax.set_ylabel("peak recall (q95)")
    ax.set_title("Peak retention vs sampling resolution")
    ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(figs / "peak_retention_vs_resolution.pdf")
    fig.savefig(figs / "peak_retention_vs_resolution.png", dpi=120)
    plt.close(fig)

    (tables / "downsampling_comparison.meta.json").write_text(
        json.dumps({"eligible_for_final_claims": False, "fingerprint": fp["fingerprint"], "n": len(df)}, indent=2)
    )
    print(df.groupby(["resolution", "model"])["mae"].mean())
    print("wrote downsampling", len(df))


if __name__ == "__main__":
    main()
