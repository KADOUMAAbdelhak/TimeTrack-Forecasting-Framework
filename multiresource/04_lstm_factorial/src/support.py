"""Maximum-history common support for the four-resource factorial."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .data import FUTURE_LEADS, L_MAX, target_columns


def four_resource_finite_origins(panel: pd.DataFrame, machine: str, candidates: np.ndarray) -> np.ndarray:
    origins = np.asarray(candidates, dtype=np.int64)
    if origins.ndim != 1 or (len(origins) and np.any(np.diff(origins) <= 0)):
        raise ValueError("Candidate origins must be sorted and unique")
    if not len(origins):
        return origins
    history = origins[:, None] - np.arange(L_MAX - 1, -1, -1)
    targets = origins[:, None] + np.asarray(FUTURE_LEADS)
    inside = (history[:, 0] >= 0) & (targets[:, -1] < len(panel))
    origins, history, targets = origins[inside], history[inside], targets[inside]
    if not len(origins):
        return origins
    segments = panel.segment_id.to_numpy(dtype=np.int64)
    values = panel.loc[:, list(target_columns(machine))].to_numpy(dtype=np.float64)
    keep = (
        np.all(segments[history] == segments[origins, None], axis=1)
        & np.all(segments[targets] == segments[origins, None], axis=1)
        & np.isfinite(values[history]).all(axis=(1, 2))
        & np.isfinite(values[targets]).all(axis=(1, 2))
    )
    return origins[keep]
