"""Prediction-time gating features for regime-aware routing.

All features use only information available at the forecast origin (no future targets).
"""

from __future__ import annotations

import numpy as np


def gating_feature_vector(
    context_window: np.ndarray,
    *,
    hour: float | None = None,
    is_weekend: float | None = None,
    entity_index: float | None = None,
    n_entities: int = 7,
) -> np.ndarray:
    """
    context_window: (context,) or (context, n_features) target channel in last dim/col 0.
    """
    x = np.asarray(context_window, dtype=float)
    if x.ndim == 2:
        x = x[:, 0]
    x = x[np.isfinite(x)]
    if len(x) == 0:
        feats = [0.0] * 8
    else:
        recent = x[-min(16, len(x)) :]
        # lag-1 autocorr estimate on recent window
        if len(recent) >= 3:
            a, b = recent[1:], recent[:-1]
            if np.std(a) > 1e-12 and np.std(b) > 1e-12:
                ac = float(np.corrcoef(a, b)[0, 1])
            else:
                ac = 0.0
        else:
            ac = 0.0
        feats = [
            float(np.std(recent)),
            float(np.mean(np.abs(np.diff(recent)))) if len(recent) > 1 else 0.0,
            float(np.mean(recent)),
            float(np.max(recent)),
            ac,
            float(np.mean(np.abs(recent) < 1e-12)),
            float(hour if hour is not None else -1.0),
            float(is_weekend if is_weekend is not None else -1.0),
        ]
    if entity_index is not None:
        oh = np.zeros(n_entities, dtype=float)
        ei = int(entity_index)
        if 0 <= ei < n_entities:
            oh[ei] = 1.0
        feats.extend(oh.tolist())
    return np.asarray(feats, dtype=float)


def batch_gating_features(
    X: np.ndarray,
    *,
    hours: np.ndarray | None = None,
    weekends: np.ndarray | None = None,
    entity_indices: np.ndarray | None = None,
    n_entities: int = 7,
) -> np.ndarray:
    X = np.asarray(X)
    n = len(X)
    rows = []
    for i in range(n):
        rows.append(
            gating_feature_vector(
                X[i],
                hour=None if hours is None else float(hours[i]),
                is_weekend=None if weekends is None else float(weekends[i]),
                entity_index=None if entity_indices is None else float(entity_indices[i]),
                n_entities=n_entities,
            )
        )
    return np.stack(rows, axis=0)
