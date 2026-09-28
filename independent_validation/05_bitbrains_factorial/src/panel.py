"""Window construction over already-clean, contiguous Bitbrains panels."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import LEADS, RESOURCE_ORDER


def build_windows(frame: pd.DataFrame, origins: np.ndarray, context_length: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    origins = np.asarray(origins, dtype=np.int64)
    history = origins[:, None] - np.arange(context_length - 1, -1, -1)
    targets = origins[:, None] + np.asarray(LEADS)
    values = frame.loc[:, list(RESOURCE_ORDER)].to_numpy(dtype=np.float64)
    segments = frame.segment_id.to_numpy(dtype=np.int64)
    if len(origins) and (
        not np.all(segments[history] == segments[origins, None])
        or not np.all(segments[targets] == segments[origins, None])
    ):
        raise RuntimeError("Window crosses a segment boundary")
    X = values[history]
    y = np.moveaxis(values[targets], 1, 2)
    persistence = np.repeat(values[origins, :, None], len(LEADS), axis=2)
    if not np.isfinite(X).all() or not np.isfinite(y).all():
        raise RuntimeError("Window contains non-finite values")
    return X, y, persistence


def scaler_rows(origins: np.ndarray, context_length: int) -> np.ndarray:
    origins = np.asarray(origins, dtype=np.int64)
    history = (origins[:, None] - np.arange(context_length - 1, -1, -1)).ravel()
    targets = (origins[:, None] + np.asarray(LEADS)).ravel()
    return np.unique(np.concatenate([history, targets]))

