"""Train-derived peak forecasting metrics (development)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.runner import prepare_split_windows
from models import forecasting as F
from models.hybrid.reconciliation import memory_hierarchy, reconcile
from timetrack.data import build_analysis_panel, dataset_fingerprint
from timetrack.evaluation_stage import ExperimentStage
from timetrack.metrics import mae
from timetrack.splits import fold_to_split_spec, make_outer_chronological_folds

TARGETS = (
    "cluster_mean_CU",
    "machine01_DWT",
    "machine01_tx_bond0",
    "machine01_rx_bond0",
    "averageRttWithGoogleDns",
    "jitterWithGoogleDns",
    "cluster_UM",
)
HORIZON = 1
CONTEXT = 32


def peak_threshold(train: np.ndarray, mode: str = "q95", k: float = 3.0) -> float:
    tr = np.asarray(train, dtype=float)
    tr = tr[np.isfinite(tr)]
    if mode.startswith("q"):
        q = float(mode[1:]) / 100.0
        return float(np.quantile(tr, q))
    med = float(np.median(tr))
    mad = float(np.median(np.abs(tr - med))) + 1e-12
    return med + k * 1.4826 * mad


def peak_eval(y_true, y_pred, thr, sampling_seconds=42.285):
    y_true = np.asarray(y_true, dtype=float).reshape(-1)
    y_pred = np.asarray(y_pred, dtype=float).reshape(-1)
    t_peaks = np.flatnonzero(y_true > thr)
    p_peaks = np.flatnonzero(y_pred > thr)
    if len(t_peaks) == 0:
        return {
            "peak_precision": float("nan"),
            "peak_recall": float("nan"),
            "peak_f1": float("nan"),
            "peak_magnitude_mae": float("nan"),
            "peak_timing_mae_steps": float("nan"),
            "high_load_mae": float("nan"),
            "false_alarms_per_day": float(len(p_peaks) / max((len(y_true) * sampling_seconds) / 86400.0, 1e-9)),
            "n_true_peaks": 0,
            "n_pred_peaks": int(len(p_peaks)),
        }
    hits = 0
    timing = []
    mag = []
    for i in t_peaks:
        if len(p_peaks):
            j = p_peaks[np.argmin(np.abs(p_peaks - i))]
            if abs(j - i) <= 2:
                hits += 1
                timing.append(abs(j - i))
                mag.append(abs(y_true[i] - y_pred[i]))
    recall = hits / len(t_peaks)
    if len(p_peaks) == 0:
        precision = 0.0
    else:
        ph = 0
        for i in p_peaks:
            if np.any(np.abs(t_peaks - i) <= 2):
                ph += 1
        precision = ph / len(p_peaks)
    f1 = 0.0 if (precision + recall) == 0 else 2 * precision * recall / (precision + recall)
    high = y_true > thr
    high_mae = float(np.mean(np.abs(y_true[high] - y_pred[high]))) if high.any() else float("nan")
    days = max((len(y_true) * sampling_seconds) / 86400.0, 1e-9)
    fa = (len(p_peaks) - hits) / days
    return {
        "peak_precision": float(precision),
        "peak_recall": float(recall),
        "peak_f1": float(f1),
        "peak_magnitude_mae": float(np.mean(mag)) if mag else float("nan"),
        "peak_timing_mae_steps": float(np.mean(timing)) if timing else float("nan"),
        "high_load_mae": high_mae,
        "false_alarms_per_day": float(fa),
        "n_true_peaks": int(len(t_peaks)),
        "n_pred_peaks": int(len(p_peaks)),
    }


def main():
    panel = build_analysis_panel()
    fp = dataset_fingerprint()
    folds = make_outer_chronological_folds(panel, n_folds=3)
    rows = []
    for fold in folds:
        split = fold_to_split_spec(fold)
        for target in TARGETS:
            if target not in panel.columns:
                continue
            windows = prepare_split_windows(panel, split, target, HORIZON, CONTEXT, flat=True)
            y_train = panel.loc[split.train_idx, target].to_numpy(float)
            for model_name in ("persistence", "ridge", "lightgbm"):
                model = F.build_model(model_name, horizon=HORIZON, context_length=CONTEXT, seed=0)
                model.fit(windows["train"].X, windows["train"].y, windows["val"].X, windows["val"].y)
                pred = np.asarray(model.predict(windows["test"].X), dtype=float).reshape(-1)
                y = np.asarray(windows["test"].y, dtype=float).reshape(-1)
                for mode in ("q90", "q95", "mad"):
                    thr = peak_threshold(y_train, mode=mode)
                    ev = peak_eval(y, pred, thr)
                    rows.append(
                        {
                            "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                            "eligible_for_final_claims": False,
                            "target": target,
                            "model": model_name,
                            "method": "point",
                            "threshold_mode": mode,
                            "threshold": thr,
                            "outer_fold": fold.fold_id,
                            "mae": mae(y, pred),
                            **ev,
                        }
                    )
            # C1 bottom_up for cluster_UM if applicable
            if target == "cluster_UM":
                from scripts.run_hierarchy_dev import _fit_predict, _align_by_origins, MACHINES
                from models.hybrid.reconciliation import memory_hierarchy

                packs = [_fit_predict(panel, split, f"{m}_UM", HORIZON, CONTEXT, "ridge") for m in MACHINES]
                top = _fit_predict(panel, split, "cluster_UM", HORIZON, CONTEXT, "ridge")
                al = _align_by_origins(packs, top)
                out = reconcile("bottom_up", memory_hierarchy(), al["pb_test"], al["pt_test"])
                for mode in ("q90", "q95"):
                    thr = peak_threshold(al["yt_train"], mode=mode)
                    ev = peak_eval(al["yt_test"], out["top"], thr)
                    rows.append(
                        {
                            "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                            "eligible_for_final_claims": False,
                            "target": target,
                            "model": "ridge",
                            "method": "c1_bottom_up",
                            "threshold_mode": mode,
                            "threshold": thr,
                            "outer_fold": fold.fold_id,
                            "mae": mae(al["yt_test"], out["top"]),
                            **ev,
                        }
                    )

    df = pd.DataFrame(rows)
    out = ROOT / "results" / "development" / "metrics"
    figs = ROOT / "results" / "development" / "figures"
    out.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "peak_metrics.csv", index=False)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sub = df[df.threshold_mode == "q95"]
    fig, ax = plt.subplots(figsize=(6, 4))
    for model, g in sub.groupby("model"):
        ax.scatter(g["false_alarms_per_day"], g["peak_recall"], label=model, alpha=0.7)
    ax.set_xlabel("false alarms / day")
    ax.set_ylabel("peak recall")
    ax.set_title("Peak recall vs false alarms (q95, dev)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figs / "peak_recall_vs_false_alarm.pdf")
    fig.savefig(figs / "peak_recall_vs_false_alarm.png", dpi=120)
    plt.close(fig)
    (out / "peak_metrics.meta.json").write_text(
        json.dumps({"eligible_for_final_claims": False, "fingerprint": fp["fingerprint"], "n": len(df)}, indent=2)
    )
    print(df.groupby(["target", "model"])["peak_recall"].mean().head(20))
    print("wrote peak metrics", len(df))


if __name__ == "__main__":
    main()
