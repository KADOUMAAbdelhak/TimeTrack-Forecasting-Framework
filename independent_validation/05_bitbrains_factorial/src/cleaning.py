"""Frozen physical-validity filtering and gap-based segmentation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import RESOURCE_ORDER
from .ingestion import RawVM


MAX_GAP_SECONDS = 450


@dataclass(frozen=True)
class CleanVM:
    environment: str
    vm_id: str
    frame: pd.DataFrame
    quality: dict[str, object]
    segments: list[dict[str, object]]
    members: list[dict[str, object]]
    archive_sha256: str


def validity_reasons(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    return {
        "cpu_nonfinite": ~np.isfinite(frame.CPU),
        "cpu_below_zero": np.isfinite(frame.CPU) & (frame.CPU < 0),
        "cpu_above_100": np.isfinite(frame.CPU) & (frame.CPU > 100),
        "network_received_nonfinite": ~np.isfinite(frame.network_received),
        "network_received_negative": np.isfinite(frame.network_received) & (frame.network_received < 0),
        "network_transmitted_nonfinite": ~np.isfinite(frame.network_transmitted),
        "network_transmitted_negative": np.isfinite(frame.network_transmitted) & (frame.network_transmitted < 0),
        "memory_nonfinite": ~np.isfinite(frame.MEMORY),
        "memory_negative": np.isfinite(frame.MEMORY) & (frame.MEMORY < 0),
        "disk_write_nonfinite": ~np.isfinite(frame.DISK_WRITE),
        "disk_write_negative": np.isfinite(frame.DISK_WRITE) & (frame.DISK_WRITE < 0),
    }


def clean_and_segment(raw: RawVM) -> CleanVM:
    frame = raw.frame.sort_values("timestamp_seconds", kind="stable").reset_index(drop=True).copy()
    duplicate_count = int(frame.timestamp_seconds.duplicated(keep=False).sum())
    if duplicate_count:
        raise RuntimeError(f"Duplicate timestamps for {raw.environment}/{raw.vm_id}: {duplicate_count}")
    reasons = validity_reasons(frame)
    invalid = np.logical_or.reduce(list(reasons.values()))
    throughput = frame.network_received.to_numpy(float) + frame.network_transmitted.to_numpy(float)
    throughput_invalid = ~np.isfinite(throughput) | (throughput < 0)
    reasons["throughput_total_invalid"] = throughput_invalid
    invalid |= throughput_invalid
    valid = frame.loc[~invalid].copy()
    valid["THROUGHPUT"] = throughput[~invalid]
    valid = valid[["timestamp_seconds", *RESOURCE_ORDER, "raw_member"]].reset_index(drop=True)
    gaps = valid.timestamp_seconds.diff().to_numpy(float)
    valid["segment_id"] = np.cumsum(np.nan_to_num(gaps, nan=0.0) > MAX_GAP_SECONDS).astype(np.int64)
    valid["timestamp_utc"] = pd.to_datetime(valid.timestamp_seconds, unit="s", utc=True)
    segments = []
    largest_gap = float(np.nanmax(gaps)) if len(valid) > 1 else 0.0
    for segment_id, group in valid.groupby("segment_id", sort=True):
        internal = np.diff(group.timestamp_seconds.to_numpy(float))
        segments.append({
            "environment": raw.environment,
            "vm_id": raw.vm_id,
            "segment_id": int(segment_id),
            "start_timestamp_utc": group.timestamp_utc.iloc[0].isoformat(),
            "end_timestamp_utc": group.timestamp_utc.iloc[-1].isoformat(),
            "observations": len(group),
            "duration_seconds": float(group.timestamp_seconds.iloc[-1] - group.timestamp_seconds.iloc[0]),
            "median_cadence_seconds": float(np.median(internal)) if len(internal) else np.nan,
            "largest_internal_gap_seconds": float(np.max(internal)) if len(internal) else 0.0,
            "vm_largest_valid_gap_seconds": largest_gap,
        })
    quality = {
        "environment": raw.environment,
        "vm_id": raw.vm_id,
        "raw_rows": len(frame),
        "valid_rows": len(valid),
        "invalid_rows": int(invalid.sum()),
        "invalid_fraction": float(invalid.mean()) if len(frame) else np.nan,
        "duplicate_timestamps": duplicate_count,
        "segment_count": len(segments),
        "largest_valid_gap_seconds": largest_gap,
        **{f"reason_{key}": int(mask.sum()) for key, mask in reasons.items()},
    }
    return CleanVM(raw.environment, raw.vm_id, valid, quality, segments, raw.members, raw.archive_sha256)

