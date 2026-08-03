"""Nonnegative constrained mixture weights from inner OOF predictions."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.linear_model import Ridge


def fit_constrained_mixture(
    y_val: np.ndarray,
    preds_val: list[np.ndarray],
    *,
    l2: float = 1.0,
    min_samples: int = 100,
) -> dict[str, Any]:
    """
    Learn nonnegative weights summing to 1 via projected ridge on validation preds.
    Regularizes toward uniform when sample is small.
    """
    y = np.asarray(y_val, dtype=float).reshape(-1)
    P = np.column_stack([np.asarray(p, dtype=float).reshape(-1) for p in preds_val])
    k = P.shape[1]
    if len(y) < min_samples:
        w = np.ones(k) / k
        return {"weights": w, "accepted": False, "reason": "insufficient_samples", "n": len(y)}
    # Solve unconstrained ridge then project
    reg = Ridge(alpha=l2, fit_intercept=False, positive=True)
    reg.fit(P, y)
    w = np.maximum(reg.coef_, 0.0)
    if w.sum() <= 0:
        w = np.ones(k) / k
    else:
        w = w / w.sum()
    # Shrink toward uniform
    uni = np.ones(k) / k
    shrink = min(1.0, l2 / (l2 + len(y)))
    w = (1 - shrink) * w + shrink * uni
    w = np.maximum(w, 0.0)
    w = w / w.sum()
    return {"weights": w, "accepted": True, "reason": "", "n": len(y)}


def apply_mixture(preds: list[np.ndarray], weights: np.ndarray) -> np.ndarray:
    w = np.asarray(weights, dtype=float).reshape(-1)
    w = w / w.sum()
    stacked = np.stack([np.asarray(p, dtype=float) for p in preds], axis=0)
    return np.tensordot(w, stacked, axes=(0, 0))
