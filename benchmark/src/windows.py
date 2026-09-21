"""Segment-safe contiguous history and multi-lead target windows."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .features import common_finite_columns, feature_columns


FUTURE_LEADS = [1, 2, 4, 8, 16, 32, 64, 128]
CONTEXT_LENGTHS = [32, 64, 128]


@dataclass(frozen=True)
class WindowBatch:
    X: np.ndarray
    y: np.ndarray
    origin_indices: np.ndarray
    origin_timestamps: np.ndarray
    latest_target_timestamps: np.ndarray
    segment_ids: np.ndarray
    feature_names: tuple[str, ...]
    context_length: int


def joint_eligible_origins(
    panel: pd.DataFrame,
    machine: str,
    max_context: int = 128,
    require_common_feature_intersection: bool = False,
) -> np.ndarray:
    if max_context not in CONTEXT_LENGTHS:
        raise ValueError(max_context)
    target = f"{machine}__cpu_utilization"
    segments = panel["segment_id"]
    eligible = np.ones(len(panel), dtype=bool)
    start_segment = segments.shift(max_context - 1)
    end_segment = segments.shift(-max(FUTURE_LEADS))
    eligible &= segments.eq(start_segment).to_numpy()
    eligible &= segments.eq(end_segment).to_numpy()
    for lead in FUTURE_LEADS:
        eligible &= panel[target].shift(-lead).notna().to_numpy()
    columns = (
        common_finite_columns(machine)
        if require_common_feature_intersection
        else [target]
    )
    for column in columns:
        for lag in range(max_context):
            eligible &= panel[column].shift(lag).notna().to_numpy()
    return np.flatnonzero(eligible)


def finite_feature_origins(
    panel: pd.DataFrame,
    machine: str,
    feature_set: str,
    context_length: int,
    origin_indices: np.ndarray,
) -> np.ndarray:
    """Filter a fixed structural split to one feature set's finite histories."""
    columns = feature_columns(machine, feature_set)
    keep = np.ones(len(origin_indices), dtype=bool)
    for column in columns:
        values = panel[column].to_numpy(dtype=float)
        for lag in range(context_length):
            keep &= np.isfinite(values[origin_indices - lag])
    return np.asarray(origin_indices, dtype=np.int64)[keep]


def build_windows(
    panel: pd.DataFrame,
    machine: str,
    feature_set: str,
    context_length: int,
    origin_indices: np.ndarray,
) -> WindowBatch:
    if context_length not in CONTEXT_LENGTHS:
        raise ValueError(context_length)
    features = feature_columns(machine, feature_set)
    target = f"{machine}__cpu_utilization"
    segments = panel["segment_id"].to_numpy()
    timestamps = panel["timestamp"].to_numpy()
    X = np.empty((len(origin_indices), context_length, len(features)), dtype=np.float32)
    y = np.empty((len(origin_indices), len(FUTURE_LEADS)), dtype=np.float32)
    for row, origin in enumerate(origin_indices):
        start = origin - context_length + 1
        target_positions = origin + np.asarray(FUTURE_LEADS)
        if start < 0 or target_positions[-1] >= len(panel):
            raise ValueError("Window lies outside canonical panel")
        if segments[start] != segments[origin] or np.any(
            segments[target_positions] != segments[origin]
        ):
            raise ValueError("Window crosses canonical temporal segment")
        X[row] = panel.loc[start:origin, features].to_numpy(dtype=np.float32)
        y[row] = panel.loc[target_positions, target].to_numpy(dtype=np.float32)
    if not np.isfinite(X).all() or not np.isfinite(y).all():
        raise ValueError("Non-finite benchmark window")
    return WindowBatch(
        X=X,
        y=y,
        origin_indices=origin_indices.astype(np.int64),
        origin_timestamps=timestamps[origin_indices],
        latest_target_timestamps=timestamps[origin_indices + max(FUTURE_LEADS)],
        segment_ids=segments[origin_indices],
        feature_names=tuple(features),
        context_length=context_length,
    )
