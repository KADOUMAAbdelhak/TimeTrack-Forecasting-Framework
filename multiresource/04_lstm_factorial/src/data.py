"""Frozen Phase 3B targets and segment-safe four-resource windows."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
PANEL_PATH = ROOT / "discovery/02_dependency_analysis/outputs/canonical_panel.parquet"
EXPECTED_PANEL_SHA256 = "c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a"
RESOURCE_ORDER = ("CPU", "THROUGHPUT", "MEMORY", "DISK_WRITE")
FUTURE_LEADS = (1, 2, 4, 8, 16, 32, 64, 128)
CONTEXT_LENGTHS = (32, 64, 128)
L_MAX = 128
MACHINES = tuple(f"machine{i:02d}" for i in range(1, 8))
TARGET_SUFFIXES = {
    "CPU": "cpu_utilization",
    "THROUGHPUT": "throughput_total",
    "MEMORY": "memory_used",
    "DISK_WRITE": "disk_write",
}
TRANSFORMS = {"CPU": "identity", "THROUGHPUT": "log1p", "MEMORY": "identity", "DISK_WRITE": "log1p"}


@dataclass(frozen=True)
class RawWindows:
    X: np.ndarray
    y: np.ndarray
    origins: np.ndarray
    sample_ids: np.ndarray
    origin_timestamps: np.ndarray
    target_timestamps: np.ndarray
    support_hash: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_panel() -> pd.DataFrame:
    if sha256_file(PANEL_PATH) != EXPECTED_PANEL_SHA256:
        raise RuntimeError("Canonical panel differs from the frozen Phase 2A input")
    panel = pd.read_parquet(PANEL_PATH)
    panel["timestamp"] = pd.to_datetime(panel["timestamp"], errors="raise")
    if panel.timestamp.duplicated().any() or not panel.timestamp.is_monotonic_increasing:
        raise RuntimeError("Canonical timestamps must be unique and increasing")
    return panel


def target_columns(machine: str) -> tuple[str, ...]:
    if machine not in MACHINES:
        raise ValueError(f"Unknown machine: {machine}")
    return tuple(f"{machine}__{TARGET_SUFFIXES[r]}" for r in RESOURCE_ORDER)


def sample_set_hash(origins: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(origins, dtype="<i8").tobytes()).hexdigest()


def build_raw_windows(panel: pd.DataFrame, machine: str, context_length: int, origins: np.ndarray) -> RawWindows:
    if context_length not in CONTEXT_LENGTHS:
        raise ValueError("Context length must be one of 32, 64, 128")
    origins = np.asarray(origins, dtype=np.int64)
    if origins.ndim != 1 or (len(origins) and np.any(np.diff(origins) <= 0)):
        raise ValueError("Origins must be one-dimensional, sorted, and unique")
    history = origins[:, None] - np.arange(context_length - 1, -1, -1)
    targets = origins[:, None] + np.asarray(FUTURE_LEADS)
    if len(origins) and (history.min() < 0 or targets.max() >= len(panel)):
        raise ValueError("Window outside canonical panel")
    segments = panel.segment_id.to_numpy(dtype=np.int64)
    if len(origins) and (not np.all(segments[history] == segments[origins, None]) or not np.all(segments[targets] == segments[origins, None])):
        raise ValueError("Window crosses canonical temporal segment")
    values = panel.loc[:, list(target_columns(machine))].to_numpy(dtype=np.float32)
    X, y = values[history], values[targets].transpose(0, 2, 1)
    if not np.isfinite(X).all() or not np.isfinite(y).all():
        raise ValueError("Non-finite four-resource window")
    timestamps = panel.timestamp.to_numpy()
    return RawWindows(
        X=X,
        y=y,
        origins=origins,
        sample_ids=np.asarray([f"{machine}:{x}" for x in origins], dtype=object),
        origin_timestamps=timestamps[origins],
        target_timestamps=timestamps[targets],
        support_hash=sample_set_hash(origins),
    )


def formulation_view(windows: RawWindows, formulation: str, resource: str | None = None) -> tuple[np.ndarray, np.ndarray]:
    if formulation not in {"S1", "S2", "M1"}:
        raise ValueError(formulation)
    if formulation == "M1":
        if resource is not None:
            raise ValueError("M1 has no single target resource")
        return windows.X, windows.y
    if resource not in RESOURCE_ORDER:
        raise ValueError("S1/S2 require one frozen target resource")
    index = RESOURCE_ORDER.index(resource)
    X = windows.X[:, :, index:index + 1] if formulation == "S1" else windows.X
    return X, windows.y[:, index, :]
