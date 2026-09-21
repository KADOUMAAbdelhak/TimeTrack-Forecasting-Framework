"""Dataset loading, fingerprinting, and panel construction."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from timetrack.constants import (
    HOST_TO_MACHINE,
    MACHINE_TO_HOST,
    OUTAGE_END,
    OUTAGE_START,
    RAW_FILES,
    SAMPLING_SECONDS,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def file_md5(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def dataset_fingerprint(raw_dir: Path | None = None) -> dict[str, Any]:
    raw_dir = raw_dir or RAW_DIR
    fp: dict[str, Any] = {"sampling_seconds_assumed": SAMPLING_SECONDS, "files": {}}
    for name in RAW_FILES:
        path = raw_dir / name
        if not path.exists():
            # fall back to project root originals
            path = PROJECT_ROOT / name
        if not path.exists():
            raise FileNotFoundError(f"Missing raw file: {name}")
        fp["files"][name] = {
            "path": str(path),
            "md5": file_md5(path),
            "size_bytes": path.stat().st_size,
        }
    fp["fingerprint"] = hashlib.sha256(
        json.dumps(fp["files"], sort_keys=True).encode()
    ).hexdigest()[:16]
    return fp


def _read_csv(name: str, raw_dir: Path | None = None) -> pd.DataFrame:
    raw_dir = raw_dir or RAW_DIR
    path = raw_dir / name
    if not path.exists():
        path = PROJECT_ROOT / name
    df = pd.read_csv(path)
    if "timestamp" not in df.columns:
        raise ValueError(f"{name} missing timestamp")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if df["timestamp"].isna().any():
        raise ValueError(f"{name}: failed to parse some timestamps")
    if not df["timestamp"].is_monotonic_increasing:
        raise ValueError(f"{name}: timestamps not sorted")
    if df["timestamp"].duplicated().any():
        raise ValueError(f"{name}: duplicate timestamps")
    return df


def detect_sampling_seconds(ts: pd.Series) -> float:
    diffs = ts.diff().dt.total_seconds().dropna()
    # exclude long gaps (> 3x median of small diffs)
    med = float(diffs.median())
    core = diffs[diffs < med * 3]
    return float(core.median()) if len(core) else med


def load_compute(raw_dir: Path | None = None) -> pd.DataFrame:
    return _read_csv("compute_dataset.csv", raw_dir)


def load_disk(raw_dir: Path | None = None) -> pd.DataFrame:
    df = _read_csv("disk_dataset.csv", raw_dir)
    # normalize typo without mutating raw file on disk
    if "machie02 FD" in df.columns and "machine02 FD" not in df.columns:
        df = df.rename(columns={"machie02 FD": "machine02 FD"})
    return df


def load_network(raw_dir: Path | None = None) -> pd.DataFrame:
    return _read_csv("network_dataset.csv", raw_dir)


def load_throughputs(raw_dir: Path | None = None) -> pd.DataFrame:
    return _read_csv("throughputs_dataset.csv", raw_dir)


def load_packet_loss(raw_dir: Path | None = None) -> pd.DataFrame:
    return _read_csv("packet-loss-dataset.csv", raw_dir)


def build_analysis_panel(raw_dir: Path | None = None) -> pd.DataFrame:
    """Wide panel of high-priority series aligned on compute timestamps."""
    compute = load_compute(raw_dir)
    disk = load_disk(raw_dir)
    network = load_network(raw_dir)
    thruput = load_throughputs(raw_dir)
    packet = load_packet_loss(raw_dir)

    panel = pd.DataFrame({"timestamp": compute["timestamp"]})

    for i in range(1, 8):
        m = f"machine0{i}"
        panel[f"{m}_CU"] = compute[f"{m} CU"]
        panel[f"{m}_UM"] = compute[f"{m} UM"]
        panel[f"{m}_AM"] = compute[f"{m} AM"]
        panel[f"{m}_DRT"] = compute[f"{m} DRT"]
        panel[f"{m}_DWT"] = compute[f"{m} DWT"]
        panel[f"{m}_UD"] = disk[f"{m} UD"]
        panel[f"{m}_FD"] = disk[f"{m} FD"]
        panel[f"{m}_UD_diff"] = disk[f"{m} UD"].diff()

    panel["cluster_UM"] = compute["cluster UM"]
    panel["cluster_AM"] = compute["cluster AM"]
    panel["cluster_UD"] = compute["cluster UD"]
    panel["cluster_mean_CU"] = panel[[f"machine0{i}_CU" for i in range(1, 8)]].mean(axis=1)

    panel = panel.merge(network, on="timestamp", how="left")

    for host, machine in HOST_TO_MACHINE.items():
        tx = f"transmitted_throughput_{host}:-network-device-bond0"
        rx = f"received_throughput_{host}:-network-device-bond0"
        panel[f"{machine}_tx_bond0"] = thruput[tx].values
        panel[f"{machine}_rx_bond0"] = thruput[rx].values
        # also hostname aliases
        panel[f"tx_bond0_{host}"] = thruput[tx].values
        panel[f"rx_bond0_{host}"] = thruput[rx].values

    drop_cols = [c for c in packet.columns if c.startswith("drop_packet_")]
    err_cols = [c for c in packet.columns if c.startswith("err_packet_")]
    panel["drop_packet_sum"] = packet[drop_cols].fillna(0).sum(axis=1).values
    panel["err_packet_sum"] = packet[err_cols].fillna(0).sum(axis=1).values
    panel["drop_any_event"] = (packet[drop_cols].fillna(0).gt(0).any(axis=1)).astype(float).values

    # segment / calendar flags (concat once to avoid fragmentation)
    outage_start = pd.Timestamp(OUTAGE_START)
    outage_end = pd.Timestamp(OUTAGE_END)
    ts = panel["timestamp"]
    extra = pd.DataFrame(
        {
            "segment": np.where(
                ts < outage_start,
                "pre_outage",
                np.where(ts >= outage_end, "post_outage", "in_outage"),
            ),
            "hour": ts.dt.hour,
            "dow": ts.dt.dayofweek,
            "is_weekend": (ts.dt.dayofweek >= 5).astype(int),
            "is_workhours": ts.dt.hour.between(9, 17).astype(int),
        },
        index=panel.index,
    )
    panel = pd.concat([panel, extra], axis=1)

    panel.attrs["sampling_seconds"] = detect_sampling_seconds(panel["timestamp"])
    panel.attrs["machine_to_host"] = MACHINE_TO_HOST
    return panel.copy()


def observed_interval_ok(ts: pd.Series, expected: float = SAMPLING_SECONDS, tol: float = 1.0) -> bool:
    med = detect_sampling_seconds(ts)
    return abs(med - expected) <= tol
