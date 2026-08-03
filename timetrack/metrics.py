"""Forecast evaluation metrics with explicit MAPE/MASE edge-case policies."""

from __future__ import annotations

from typing import Any

import numpy as np

from timetrack.constants import MAPE_ZERO_EPS

# Minimum naive-scale denominator for a valid MASE (absolute units of the series).
MASE_SCALE_EPS = 1e-12
# Minimum number of finite lag-1 pairs required to estimate the MASE denominator.
MASE_MIN_PAIRS = 2


def _as_1d(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=float).reshape(-1)
    return a


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if not np.any(mask):
        return float("nan")
    return float(np.mean(np.abs(y_true[mask] - y_pred[mask])))


def mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if not np.any(mask):
        return float("nan")
    return float(np.mean((y_true[mask] - y_pred[mask]) ** 2))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    v = mse(y_true, y_pred)
    return float(np.sqrt(v)) if np.isfinite(v) else float("nan")


def medae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if not np.any(mask):
        return float("nan")
    return float(np.median(np.abs(y_true[mask] - y_pred[mask])))


def maxae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if not np.any(mask):
        return float("nan")
    return float(np.max(np.abs(y_true[mask] - y_pred[mask])))


def r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Standard R²; negative values preserved (not clamped)."""
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if mask.sum() < 2:
        return float("nan")
    yt, yp = y_true[mask], y_pred[mask]
    ss_res = np.sum((yt - yp) ** 2)
    ss_tot = np.sum((yt - np.mean(yt)) ** 2)
    if ss_tot == 0:
        return float("nan")
    return float(1.0 - ss_res / ss_tot)


def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    denom = np.abs(y_true) + np.abs(y_pred)
    mask = (denom > 0) & np.isfinite(y_true) & np.isfinite(y_pred)
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
    finite = np.isfinite(y_true) & np.isfinite(y_pred)
    mask = finite & (np.abs(y_true) >= eps)
    excluded = float(1.0 - mask.mean()) if len(mask) else 1.0
    if not np.any(mask):
        return {"mape": float("nan"), "mape_fraction_excluded": excluded, "mape_eps": eps}
    val = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)
    return {"mape": val, "mape_fraction_excluded": excluded, "mape_eps": eps}


def naive_scale(
    y_train: np.ndarray,
    seasonality: int = 1,
    *,
    scale_eps: float = MASE_SCALE_EPS,
    min_pairs: int = MASE_MIN_PAIRS,
) -> dict[str, Any]:
    """
    Estimate MASE/RMSSE denominator from outer-training target only.

    Default naive: mean(|y[t] - y[t-seasonality]|) over finite pairs.
    Never silently substitutes 0/inf for an undefined scale.
    """
    y_train = _as_1d(y_train)
    if seasonality < 1:
        return {
            "scale": float("nan"),
            "valid": False,
            "reason": "invalid_seasonality",
            "n_pairs": 0,
        }
    if len(y_train) <= seasonality:
        return {
            "scale": float("nan"),
            "valid": False,
            "reason": "insufficient_observations",
            "n_pairs": 0,
        }
    a = y_train[seasonality:]
    b = y_train[:-seasonality]
    pair_ok = np.isfinite(a) & np.isfinite(b)
    n_pairs = int(pair_ok.sum())
    if n_pairs < min_pairs:
        return {
            "scale": float("nan"),
            "valid": False,
            "reason": "insufficient_finite_pairs",
            "n_pairs": n_pairs,
        }
    diffs = np.abs(a[pair_ok] - b[pair_ok])
    scale = float(np.mean(diffs))
    if not np.isfinite(scale):
        return {
            "scale": float("nan"),
            "valid": False,
            "reason": "non_finite_scale",
            "n_pairs": n_pairs,
        }
    if scale < scale_eps:
        # Distinguish constant vs near-constant
        reason = "zero_naive_scale" if scale == 0.0 else "near_zero_naive_scale"
        return {"scale": scale, "valid": False, "reason": reason, "n_pairs": n_pairs}
    return {"scale": scale, "valid": True, "reason": "", "n_pairs": n_pairs}


def train_range(y_train: np.ndarray) -> float:
    y = _as_1d(y_train)
    y = y[np.isfinite(y)]
    if len(y) == 0:
        return float("nan")
    return float(np.max(y) - np.min(y))


def mase_result(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_train: np.ndarray,
    seasonality: int = 1,
    *,
    scale_eps: float = MASE_SCALE_EPS,
) -> dict[str, Any]:
    """
    MASE with explicit validity metadata.

    Policy:
    - denominator from training target only (caller must pass outer-train / allowed train);
    - undefined when scale < scale_eps or too few finite lag pairs;
    - never replace undefined MASE with 0 or inf for ranking.
    """
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    scale_info = naive_scale(y_train, seasonality=seasonality, scale_eps=scale_eps)
    mae_val = mae(y_true, y_pred)
    rng = train_range(y_train)
    nmae_range = float(mae_val / rng) if np.isfinite(mae_val) and np.isfinite(rng) and rng > scale_eps else float("nan")

    # RMSSE: sqrt(mean sq err) / scale
    rmsse = float("nan")
    if scale_info["valid"] and np.isfinite(mae_val):
        # use rmse / scale
        r = rmse(y_true, y_pred)
        if np.isfinite(r):
            rmsse = float(r / scale_info["scale"])

    out: dict[str, Any] = {
        "mase": float("nan"),
        "mase_valid": bool(scale_info["valid"]),
        "mase_invalid_reason": scale_info["reason"],
        "mase_scale": scale_info["scale"],
        "mase_n_pairs": scale_info["n_pairs"],
        "rmsse": rmsse,
        "nmae_train_range": nmae_range,
    }
    if scale_info["valid"] and np.isfinite(mae_val):
        out["mase"] = float(mae_val / scale_info["scale"])
    elif not np.isfinite(mae_val):
        out["mase_valid"] = False
        if not out["mase_invalid_reason"]:
            out["mase_invalid_reason"] = "non_finite_mae"
    return out


def mase(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_train: np.ndarray,
    seasonality: int = 1,
) -> float:
    """Backward-compatible scalar MASE; NaN when undefined (see mase_result)."""
    return float(mase_result(y_true, y_pred, y_train, seasonality=seasonality)["mase"])


def nrmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true, y_pred = _as_1d(y_true), _as_1d(y_pred)
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if not np.any(mask):
        return float("nan")
    yt = y_true[mask]
    rng = float(np.max(yt) - np.min(yt))
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
    tr = _as_1d(train)
    tr = tr[np.isfinite(tr)]
    if len(tr) == 0:
        return {
            "peak_threshold": float("nan"),
            "peak_recall": float("nan"),
            "peak_precision": float("nan"),
            "n_true_peaks": 0,
            "n_pred_peaks": 0,
        }
    thr = float(np.quantile(tr, quantile))
    true_peaks = np.flatnonzero(np.isfinite(y_true) & (y_true > thr))
    pred_peaks = np.flatnonzero(np.isfinite(y_pred) & (y_pred > thr))
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
        "n": int(np.sum(np.isfinite(y_true_f) & np.isfinite(y_pred_f))),
    }
    out.update(mape(y_true_f, y_pred_f))
    if y_train is not None:
        out.update(mase_result(y_true_f, y_pred_f, y_train, seasonality=seasonality))
        out.update(peak_metrics(y_true_f, y_pred_f, y_train))
    return out


def nanmean_valid(values: np.ndarray, valid: np.ndarray | None = None) -> float:
    """Mean ignoring NaN; optionally restricted to valid mask. Empty → NaN."""
    v = np.asarray(values, dtype=float).reshape(-1)
    if valid is not None:
        v = v[np.asarray(valid, dtype=bool).reshape(-1)]
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return float("nan")
    return float(np.mean(v))
