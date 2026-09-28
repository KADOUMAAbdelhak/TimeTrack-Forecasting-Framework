"""Direct, identity-preserving ingestion from frozen official Bitbrains ZIPs."""

from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/external/raw"
CONFIG_PATH = BASE / "configs/bitbrains_lstm_factorial.json"
SELECTION_PATH = ROOT / "independent_validation/03_evaluation_design/SELECTED_ENTITY_COHORTS.csv"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\t", " ").strip().lower())


def _find(columns: list[str], *parts: str) -> str:
    matches = [column for column in columns if all(part in normalized(column) for part in parts)]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one column containing {parts}, found {matches}")
    return matches[0]


def required_columns(columns: list[str]) -> dict[str, str]:
    return {
        "timestamp": _find(columns, "timestamp"),
        "cpu": _find(columns, "cpu usage", "[%]"),
        "memory": _find(columns, "memory usage", "[kb]"),
        "disk_write": _find(columns, "disk write throughput"),
        "network_received": _find(columns, "network received throughput"),
        "network_transmitted": _find(columns, "network transmitted throughput"),
    }


def numeric(series: pd.Series) -> np.ndarray:
    return pd.to_numeric(
        series.astype(str).str.replace(",", ".", regex=False), errors="coerce"
    ).to_numpy(dtype=np.float64)


def selected_ids() -> dict[str, list[str]]:
    frame = pd.read_csv(SELECTION_PATH, dtype={"entity_id": str})
    frame = frame[frame.cohort_role.eq("PRIMARY_EXTERNAL_CONFIRMATION")]
    return {
        environment: list(group.sort_values("rank").entity_id)
        for environment, group in frame.groupby("environment", sort=True)
    }


@dataclass(frozen=True)
class RawVM:
    environment: str
    vm_id: str
    frame: pd.DataFrame
    members: list[dict[str, object]]
    archive_path: Path
    archive_sha256: str


def archive_path(environment: str) -> Path:
    definition = config()["archives"][environment]
    path = RAW / definition["filename"]
    if not path.is_file() or sha256_file(path) != definition["sha256"]:
        raise RuntimeError(f"Frozen archive identity mismatch: {environment}")
    return path


def member_names(bundle: zipfile.ZipFile, vm_id: str) -> list[str]:
    names = sorted(
        name
        for name in bundle.namelist()
        if name.lower().endswith(".csv") and Path(name).stem == vm_id
    )
    if not names:
        raise RuntimeError(f"No raw member for VM {vm_id}")
    return names


def parse_timestamp_seconds(series: pd.Series) -> np.ndarray:
    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=np.float64)
    finite = values[np.isfinite(values)]
    if not finite.size or np.any(finite < 1_000_000_000) or np.any(finite >= 10_000_000_000):
        raise RuntimeError("Bitbrains timestamp is not a 10-digit Unix-second value")
    if np.any(values != np.floor(values)):
        raise RuntimeError("Bitbrains timestamps must be integral Unix seconds")
    return values


def read_vm(environment: str, vm_id: str) -> RawVM:
    path = archive_path(environment)
    rows = []
    identities: list[dict[str, object]] = []
    with zipfile.ZipFile(path) as bundle:
        for member in member_names(bundle, vm_id):
            payload = bundle.read(member)
            frame = pd.read_csv(io.BytesIO(payload), sep=";", engine="c")
            frame.columns = [column.strip() for column in frame.columns]
            columns = required_columns(list(frame.columns))
            parsed = pd.DataFrame({
                "timestamp_seconds": parse_timestamp_seconds(frame[columns["timestamp"]]),
                "CPU": numeric(frame[columns["cpu"]]),
                "MEMORY": numeric(frame[columns["memory"]]),
                "DISK_WRITE": numeric(frame[columns["disk_write"]]),
                "network_received": numeric(frame[columns["network_received"]]),
                "network_transmitted": numeric(frame[columns["network_transmitted"]]),
            })
            parsed["raw_member"] = member
            rows.append(parsed)
            identities.append({
                "environment": environment,
                "vm_id": vm_id,
                "archive_filename": path.name,
                "member_path": member,
                "member_byte_size": len(payload),
                "member_sha256": sha256_bytes(payload),
            })
    combined = pd.concat(rows, ignore_index=True).sort_values("timestamp_seconds", kind="stable").reset_index(drop=True)
    return RawVM(environment, vm_id, combined, identities, path, sha256_file(path))

