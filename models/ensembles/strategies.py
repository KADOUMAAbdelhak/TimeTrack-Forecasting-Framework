"""Validation-only ensemble strategies for frozen constituent forecasts.

Weights learned from inner/validation residuals only — never outer labels.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.linear_model import LinearRegression


def simple_mean(preds: list[np.ndarray]) -> np.ndarray:
    return np.mean(np.stack([np.asarray(p, dtype=float) for p in preds], axis=0), axis=0)


def inverse_mae_weights(y_val: np.ndarray, preds_val: list[np.ndarray], eps: float = 1e-12) -> np.ndarray:
    maes = np.array([float(np.mean(np.abs(np.asarray(p) - y_val))) for p in preds_val], dtype=float)
    w = 1.0 / np.maximum(maes, eps)
    return w / w.sum()


def weighted_average(preds: list[np.ndarray], weights: np.ndarray) -> np.ndarray:
    w = np.asarray(weights, dtype=float).reshape(-1)
    w = w / w.sum()
    stacked = np.stack([np.asarray(p, dtype=float) for p in preds], axis=0)
    return np.tensordot(w, stacked, axes=(0, 0))


def nonnegative_constrained_weights(
    y_val: np.ndarray,
    preds_val: list[np.ndarray],
    max_iter: int = 500,
) -> np.ndarray:
    """NNLS-style weights via projected gradient on validation MAE surrogate (MSE)."""
    P = np.column_stack([np.asarray(p, dtype=float).reshape(-1) for p in preds_val])
    y = np.asarray(y_val, dtype=float).reshape(-1)
    k = P.shape[1]
    w = np.ones(k) / k
    lr = 0.05
    for _ in range(max_iter):
        grad = P.T @ (P @ w - y) / len(y)
        w = np.maximum(w - lr * grad, 0.0)
        s = w.sum()
        if s <= 0:
            w = np.ones(k) / k
        else:
            w = w / s
    return w


def oof_stacking(
    y_val: np.ndarray,
    preds_val: list[np.ndarray],
    min_samples: int = 200,
) -> tuple[np.ndarray, dict[str, Any]]:
    """
    Linear stacking on validation predictions.
    Rejects (returns equal weights) when meta-training sample is too small.
    """
    n = len(np.asarray(y_val).reshape(-1))
    k = len(preds_val)
    if n < min_samples:
        return np.ones(k) / k, {"accepted": False, "reason": f"n_val={n}<{min_samples}", "n": n}
    P = np.column_stack([np.asarray(p, dtype=float).reshape(-1) for p in preds_val])
    y = np.asarray(y_val, dtype=float).reshape(-1)
    reg = LinearRegression(positive=True)
    reg.fit(P, y)
    w = np.maximum(reg.coef_, 0.0)
    if w.sum() <= 0:
        w = np.ones(k) / k
    else:
        w = w / w.sum()
    return w, {"accepted": True, "intercept": float(reg.intercept_), "n": n}


def ensemble_predict(
    method: str,
    preds_test: list[np.ndarray],
    *,
    y_val: np.ndarray | None = None,
    preds_val: list[np.ndarray] | None = None,
) -> dict[str, Any]:
    method = method.lower()
    if method in {"mean", "simple_mean"}:
        return {"pred": simple_mean(preds_test), "weights": np.ones(len(preds_test)) / len(preds_test), "method": method}
    if y_val is None or preds_val is None:
        raise ValueError(f"{method} requires validation preds/labels")
    if method == "inverse_mae":
        w = inverse_mae_weights(y_val, preds_val)
    elif method in {"nnls", "nonnegative"}:
        w = nonnegative_constrained_weights(y_val, preds_val)
    elif method == "stacking":
        w, meta = oof_stacking(y_val, preds_val)
        return {"pred": weighted_average(preds_test, w), "weights": w, "method": method, **meta}
    else:
        raise ValueError(method)
    return {"pred": weighted_average(preds_test, w), "weights": w, "method": method}
