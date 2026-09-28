"""Maximum-history four-resource common support and stable sample identities."""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from . import LEADS, L_MAX, RESOURCE_ORDER


def legal_origins(frame: pd.DataFrame) -> np.ndarray:
    n = len(frame)
    candidates = np.arange(L_MAX - 1, n - max(LEADS), dtype=np.int64)
    if not len(candidates):
        return candidates
    history = candidates[:, None] - np.arange(L_MAX - 1, -1, -1)
    targets = candidates[:, None] + np.asarray(LEADS)
    segments = frame.segment_id.to_numpy(dtype=np.int64)
    values = frame.loc[:, list(RESOURCE_ORDER)].to_numpy(dtype=np.float64)
    keep = (
        np.all(segments[history] == segments[candidates, None], axis=1)
        & np.all(segments[targets] == segments[candidates, None], axis=1)
        & np.isfinite(values[history]).all(axis=(1, 2))
        & np.isfinite(values[targets]).all(axis=(1, 2))
    )
    return candidates[keep]


def origin_ids(frame: pd.DataFrame, origins: np.ndarray) -> np.ndarray:
    return frame.timestamp_seconds.to_numpy(dtype=np.int64)[np.asarray(origins, dtype=np.int64)]


def sample_set_hash(ids: np.ndarray) -> str:
    values = np.asarray(ids, dtype=np.int64)
    payload = "".join(f"{value}\n" for value in values)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def support_hash(frame: pd.DataFrame, origins: np.ndarray) -> str:
    return sample_set_hash(origin_ids(frame, origins))


def assert_context_invariant(support_by_context: dict[int, np.ndarray]) -> None:
    if set(support_by_context) != {4, 9, 18}:
        raise ValueError("All frozen contexts are required")
    reference = np.asarray(support_by_context[18])
    for length, observed in support_by_context.items():
        if not np.array_equal(reference, np.asarray(observed)):
            raise RuntimeError(f"Shorter context gained or lost origins at L={length}")

