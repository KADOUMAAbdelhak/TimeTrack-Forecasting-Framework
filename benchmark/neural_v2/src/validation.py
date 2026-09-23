"""Stable IDs, output schemas, and atomic resumability records."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


PREDICTION_COLUMNS = (
    "run_id",
    "model",
    "feature_set",
    "machine",
    "outer_fold",
    "seed",
    "lead",
    "sample_id",
    "origin_index",
    "origin_timestamp",
    "target_timestamp",
    "y_true",
    "y_pred",
    "sample_set_hash",
)
METRIC_COLUMNS = (
    "run_id",
    "model",
    "feature_set",
    "machine",
    "outer_fold",
    "seed",
    "lead",
    "mae",
    "rmse",
    "r2",
)


def run_id(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()[:24]


def atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def completion_is_valid(path: Path, expected: dict[str, Any]) -> bool:
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    required = {
        "run_id",
        "status",
        "prediction_sha256",
        "metric_sha256",
        "sample_set_hash",
        "config_sha256",
    }
    return (
        required.issubset(payload)
        and payload["status"] == "complete"
        and all(payload.get(key) == value for key, value in expected.items())
    )
