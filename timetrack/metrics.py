"""Forecast evaluation metrics with explicit MAPE zero handling."""

from __future__ import annotations

from typing import Any

import numpy as np

from timetrack.constants import MAPE_ZERO_EPS


def _as_1d(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=float).reshape(-1)
    return a


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    return float(np.mean(np.abs(y_true - y_pred)))


def mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    return float(np.mean((y_true - y_pred) ** 2))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mse(y_true, y_pred)))


def medae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    return float(np.median(np.abs(y_true - y_pred)))


def maxae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    return float(np.max(np.abs(y_true - y_pred)))


def r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Standard R²; negative values preserved (not clamped)."""
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return float("nan")
    return float(1.0 - ss_res / ss_tot)


def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    denom = np.abs(y_true) + np.abs(y_pred)
    mask = denom > 0
    if not np.any(mask):
        return float("nan")
    return float(np.mean(2.0 * np.abs(y_pred[mask] - y_true[mask]) / denom[mask]) * 100.0)


def mape(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    eps: float = MAPE_ZERO_EPS,
) -> dict[str, float]:
    """
    MAPE with explicit zero policy: exclude |y| < eps from the average.
    Returns mape_pct and fraction_excluded.
    """
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    mask = np.abs(y_true) >= eps
    excluded = float(1.0 - mask.mean()) if len(mask) else 1.0
    if not np.any(mask):
        return {"mape": float("nan"), "mape_fraction_excluded": excluded, "mape_eps": eps}
    val = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)
    return {"mape": val, "mape_fraction_excluded": excluded, "mape_eps": eps}


def mase(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_train: np.ndarray,
    seasonality: int = 1,
) -> float:
    """MASE scaled by seasonal naive MAE on training series."""
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    y_train = _as_1d(y_train)
    if len(y_train) <= seasonality:
        return float("nan")
    scale = np.mean(np.abs(y_train[seasonality:] - y_train[:-seasonality]))
    if scale == 0:
        return float("nan")
    return float(np.mean(np.abs(y_true - y_pred)) / scale)


def nrmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    rng = float(np.max(y_true) - np.min(y_true))
    if rng == 0:
        return float("nan")
    return rmse(y_true, y_pred) / rng


def peak_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    train: np.ndarray,
    quantile: float = 0.95,
    tol: int = 0,
) -> dict[str, float]:
    """Peak event precision/recall where peaks are y_true > train quantile."""
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    thr = float(np.quantile(_as_1d(train), quantile))
    true_peaks = np.flatnonzero(y_true > thr)
    pred_peaks = np.flatnonzero(y_pred > thr)
    if len(true_peaks) == 0:
        return {
            "peak_threshold": thr,
            "peak_recall": float("nan"),
            "peak_precision": float("nan"),
            "n_true_peaks": 0,
            "n_pred_peaks": int(len(pred_peaks)),
        }
    hits = 0
    for i in true_peaks:
        if np.any(np.abs(pred_peaks - i) <= tol):
            hits += 1
    recall = hits / len(true_peaks)
    if len(pred_peaks) == 0:
        precision = 0.0
    else:
        phits = 0
        for i in pred_peaks:
            if np.any(np.abs(true_peaks - i) <= tol):
                phits += 1
        precision = phits / len(pred_peaks)
    return {
        "peak_threshold": thr,
        "peak_recall": float(recall),
        "peak_precision": float(precision),
        "n_true_peaks": int(len(true_peaks)),
        "n_pred_peaks": int(len(pred_peaks)),
    }


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_train: np.ndarray | None = None,
    seasonality: int = 1,
) -> dict[str, Any]:
    y_true_f, y_pred_f = _as_1d(y_true), _as_1d(y_pred)
    if y_true_f.shape != y_pred_f.shape:
        raise ValueError(f"shape mismatch {y_true_f.shape} vs {y_pred_f.shape}")
    out: dict[str, Any] = {
        "mae": mae(y_true_f, y_pred_f),
        "mse": mse(y_true_f, y_pred_f),
        "rmse": rmse(y_true_f, y_pred_f),
        "medae": medae(y_true_f, y_pred_f),
        "maxae": maxae(y_true_f, y_pred_f),
        "r2": r2_score(y_true_f, y_pred_f),
        "smape": smape(y_true_f, y_pred_f),
        "nrmse": nrmse(y_true_f, y_pred_f),
        "n": int(len(y_true_f)),
    }
    out.update(mape(y_true_f, y_pred_f))
    if y_train is not None:
        out["mase"] = mase(y_true_f, y_pred_f, y_train, seasonality=seasonality)
        out.update(peak_metrics(y_true_f, y_pred_f, y_train))
    return out
