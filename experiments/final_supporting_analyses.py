"""Final-stage conformal, peak, and downsampling reporting helpers."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from models import forecasting as F
from experiments.runner import prepare_split_windows
from timetrack.constants import SAMPLING_SECONDS
from timetrack.metrics import mae


def split_conformal_from_residuals(
    y_cal: np.ndarray,
    p_cal: np.ndarray,
    y_test: np.ndarray,
    p_test: np.ndarray,
    nominal: float,
) -> dict[str, float]:
    """Leakage-safe split conformal using calibration residuals only."""
    resid = np.abs(np.asarray(y_cal, dtype=float) - np.asarray(p_cal, dtype=float))
    resid = resid[np.isfinite(resid)]
    n = len(resid)
    if n == 0:
        q = 0.0
    else:
        level = min(1.0, np.ceil((n + 1) * nominal) / n)
        q = float(np.quantile(resid, level))
    yt = np.asarray(y_test, dtype=float)
    pt = np.asarray(p_test, dtype=float)
    lo, hi = pt - q, pt + q
    cover = float(np.mean((yt >= lo) & (yt <= hi))) if len(yt) else float("nan")
    width = float(np.mean(hi - lo)) if len(yt) else float("nan")
    rng = float(np.nanmax(yt) - np.nanmin(yt)) if len(yt) else float("nan")
    return {
        "nominal_coverage": float(nominal),
        "empirical_coverage": cover,
        "average_interval_width": width,
        "normalized_interval_width": float(width / rng) if rng and np.isfinite(rng) and rng > 0 else float("nan"),
        "halfwidth": q,
        "interval_type": "independently_calibrated",
        "point_forecast_coherent": False,
    }


def peak_threshold(train: np.ndarray, mode: str = "q95", k: float = 3.0) -> float:
    tr = np.asarray(train, dtype=float)
    tr = tr[np.isfinite(tr)]
    if mode.startswith("q"):
        return float(np.quantile(tr, float(mode[1:]) / 100.0))
    med = float(np.median(tr))
    mad = float(np.median(np.abs(tr - med))) + 1e-12
    return med + k * 1.4826 * mad


def peak_metrics(y_true, y_pred, thr, sampling_seconds: float = SAMPLING_SECONDS) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float).reshape(-1)
    y_pred = np.asarray(y_pred, dtype=float).reshape(-1)
    t_peaks = np.flatnonzero(y_true > thr)
    p_peaks = np.flatnonzero(y_pred > thr)
    days = max((len(y_true) * sampling_seconds) / 86400.0, 1e-9)
    if len(t_peaks) == 0:
        return {
            "peak_precision": float("nan"),
            "peak_recall": float("nan"),
            "peak_f1": float("nan"),
            "peak_magnitude_mae": float("nan"),
            "peak_timing_mae_steps": float("nan"),
            "high_load_mae": float("nan"),
            "false_alarms_per_day": float(len(p_peaks) / days),
            "lead_time_success": float("nan"),
        }
    hits = 0
    timing, mag = [], []
    for i in t_peaks:
        if len(p_peaks):
            j = int(p_peaks[np.argmin(np.abs(p_peaks - i))])
            if abs(j - i) <= 2:
                hits += 1
                timing.append(abs(j - i))
                mag.append(abs(y_true[i] - y_pred[i]))
    recall = hits / len(t_peaks)
    if len(p_peaks) == 0:
        precision = 0.0
    else:
        ph = sum(1 for i in p_peaks if np.any(np.abs(t_peaks - i) <= 2))
        precision = ph / len(p_peaks)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    high = y_true > thr
    high_mae = float(np.mean(np.abs(y_true[high] - y_pred[high]))) if high.any() else float("nan")
    # lead-time success: predicted peak within 2 steps before true peak
    lead_hits = 0
    for i in t_peaks:
        if np.any((p_peaks >= i - 2) & (p_peaks <= i)):
            lead_hits += 1
    return {
        "peak_precision": float(precision),
        "peak_recall": float(recall),
        "peak_f1": float(f1),
        "peak_magnitude_mae": float(np.mean(mag)) if mag else float("nan"),
        "peak_timing_mae_steps": float(np.mean(timing)) if timing else float("nan"),
        "high_load_mae": high_mae,
        "false_alarms_per_day": float((len(p_peaks) - hits) / days),
        "lead_time_success": float(lead_hits / len(t_peaks)),
    }


def downsample_series(y: np.ndarray, factor: int) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    n = (len(y) // factor) * factor
    if n == 0:
        return y[:0]
    return y[:n].reshape(-1, factor).mean(axis=1)


def downsampling_eval_row(
    panel: pd.DataFrame,
    split,
    target: str,
    *,
    model_name: str,
    horizon_native: int,
    context_native: int,
    factor: int,
    seed: int = 0,
) -> dict[str, Any]:
    """Equivalent wall-clock context/horizon under aggregation factor."""
    import time

    h = max(1, int(round(horizon_native / factor)))
    c = max(4, int(round(context_native / factor)))
    flat = model_name in {"ridge", "lightgbm"}
    # Factor>1 full grid uses aggregation in the final runner; helper retains native fit for smoke.
    windows = prepare_split_windows(panel, split, target, horizon_native, context_native, flat=flat)
    model = F.build_model(model_name, horizon=horizon_native, context_length=context_native, seed=seed)
    if factor == 1:
        h, c = horizon_native, context_native

    t0 = time.perf_counter()
    model.fit(windows["train"].X, windows["train"].y, windows["val"].X, windows["val"].y)
    train_s = time.perf_counter() - t0
    t1 = time.perf_counter()
    pred = model.predict(windows["test"].X)
    infer_s = time.perf_counter() - t1
    yt = np.asarray(windows["test"].y, dtype=float)
    if yt.ndim > 1:
        yt = yt[:, 0]
        pred = np.asarray(pred, dtype=float)
        if pred.ndim > 1:
            pred = pred[:, 0]
    return {
        "target": target,
        "model": model_name,
        "factor": factor,
        "horizon": h,
        "context": c,
        "mae": float(mae(yt, pred)),
        "train_seconds": float(train_s),
        "inference_seconds": float(infer_s),
        "n_test": int(len(yt)),
        "resolution_label": {1: "native", 2: "x2", 4: "approx_3min", 7: "approx_5min"}.get(factor, f"x{factor}"),
    }
