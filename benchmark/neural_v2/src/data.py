"""Canonical neural-v2 data access and exact common-support windows."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
PANEL_PATH = (
    ROOT
    / "discovery"
    / "02_dependency_analysis"
    / "outputs"
    / "canonical_panel.parquet"
)
EXPECTED_PANEL_SHA256 = (
    "c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a"
)
FUTURE_LEADS = (1, 2, 4, 8, 16, 32, 64, 128)
CONTEXT_LENGTHS = (32, 64, 128)
FEATURE_SETS = ("F0_LOCAL", "F1_THROUGHPUT")


@dataclass(frozen=True)
class WindowBatch:
    X: np.ndarray
    y: np.ndarray
    origin_indices: np.ndarray
    sample_ids: np.ndarray
    origin_timestamps: np.ndarray
    target_timestamps: np.ndarray
    segment_ids: np.ndarray
    feature_names: tuple[str, ...]
    sample_set_hash: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_canonical_panel() -> pd.DataFrame:
    if sha256_file(PANEL_PATH) != EXPECTED_PANEL_SHA256:
        raise RuntimeError("Canonical panel differs from the frozen Phase 2A input")
    panel = pd.read_parquet(PANEL_PATH)
    panel["timestamp"] = pd.to_datetime(panel["timestamp"], errors="raise")
    if panel["timestamp"].duplicated().any():
        raise RuntimeError("Canonical timestamps are not unique")
    if not panel["timestamp"].is_monotonic_increasing:
        raise RuntimeError("Canonical timestamps are not increasing")
    return panel


def feature_columns(machine: str, feature_set: str) -> tuple[str, ...]:
    definitions = {
        "F0_LOCAL": (f"{machine}__cpu_utilization",),
        "F1_THROUGHPUT": (
            f"{machine}__cpu_utilization",
            f"{machine}__throughput_total",
        ),
    }
    if feature_set not in definitions:
        raise KeyError(f"Unsupported neural-v2 feature set: {feature_set}")
    return definitions[feature_set]


def sample_set_hash(origin_indices: np.ndarray) -> str:
    values = np.asarray(origin_indices, dtype="<i8")
    return hashlib.sha256(values.tobytes()).hexdigest()


def f1_finite_origins(
    panel: pd.DataFrame,
    machine: str,
    context_length: int,
    candidate_origins: np.ndarray,
) -> np.ndarray:
    """Filter origins using one max-history F1 support for all L, F0, and F1."""
    if context_length not in CONTEXT_LENGTHS:
        raise ValueError(f"Unsupported context length: {context_length}")
    origins = np.asarray(candidate_origins, dtype=np.int64)
    if origins.ndim != 1 or (len(origins) and np.any(np.diff(origins) <= 0)):
        raise ValueError("Candidate origins must be a sorted one-dimensional set")
    if not len(origins):
        return origins
    support_length = max(CONTEXT_LENGTHS)
    history = origins[:, None] - np.arange(support_length - 1, -1, -1)
    targets = origins[:, None] + np.asarray(FUTURE_LEADS)
    inside = (history[:, 0] >= 0) & (targets[:, -1] < len(panel))
    keep_origins = origins[inside]
    history = history[inside]
    targets = targets[inside]
    if not len(keep_origins):
        return keep_origins
    segments = panel["segment_id"].to_numpy()
    same_history_segment = np.all(
        segments[history] == segments[keep_origins, None], axis=1
    )
    same_target_segment = np.all(
        segments[targets] == segments[keep_origins, None], axis=1
    )
    cpu = panel[f"{machine}__cpu_utilization"].to_numpy(dtype=float)
    throughput = panel[f"{machine}__throughput_total"].to_numpy(dtype=float)
    finite_history = np.isfinite(cpu[history]).all(axis=1) & np.isfinite(
        throughput[history]
    ).all(axis=1)
    finite_targets = np.isfinite(cpu[targets]).all(axis=1)
    keep = (
        same_history_segment
        & same_target_segment
        & finite_history
        & finite_targets
    )
    return keep_origins[keep]


def build_windows(
    panel: pd.DataFrame,
    machine: str,
    feature_set: str,
    context_length: int,
    origin_indices: np.ndarray,
) -> WindowBatch:
    """Build F0 or F1 windows only after enforcing the shared F1 support."""
    origins = np.asarray(origin_indices, dtype=np.int64)
    supported = f1_finite_origins(panel, machine, context_length, origins)
    if not np.array_equal(origins, supported):
        raise ValueError("Origins do not satisfy exact neural-v2 F1 common support")
    features = feature_columns(machine, feature_set)
    history = origins[:, None] - np.arange(context_length - 1, -1, -1)
    targets = origins[:, None] + np.asarray(FUTURE_LEADS)
    values = panel.loc[:, list(features)].to_numpy(dtype=np.float32)
    cpu = panel[f"{machine}__cpu_utilization"].to_numpy(dtype=np.float32)
    timestamps = panel["timestamp"].to_numpy()
    segments = panel["segment_id"].to_numpy()
    X = values[history]
    y = cpu[targets]
    sample_ids = np.asarray(
        [f"{machine}:{origin}" for origin in origins], dtype=object
    )
    return WindowBatch(
        X=X,
        y=y,
        origin_indices=origins,
        sample_ids=sample_ids,
        origin_timestamps=timestamps[origins],
        target_timestamps=timestamps[targets],
        segment_ids=segments[origins],
        feature_names=features,
        sample_set_hash=sample_set_hash(origins),
    )
