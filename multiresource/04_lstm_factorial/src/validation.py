"""Stable run identities and atomic validated completion records."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def canonical_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run_identity(*, formulation: str, resource: str | None, machine: str, fold: int, context_length: int, seed: int, phase: str, config_hash: str, support_hash: str) -> dict[str, Any]:
    payload = {"formulation": formulation, "resource": resource, "machine": machine, "fold": fold, "L": context_length, "seed": seed, "phase": phase, "config_hash": config_hash, "support_hash": support_hash}
    payload["run_id"] = canonical_hash(payload)[:24]
    return payload


def atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def completion_valid(path: Path, expected_identity: dict[str, Any], expected_artifacts: dict[str, str]) -> bool:
    if not path.exists():
        return False
    try: payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError): return False
    if payload.get("status") != "complete" or payload.get("identity") != expected_identity:
        return False
    for relative, expected_hash in expected_artifacts.items():
        artifact = path.parent / relative
        if not artifact.exists() or hashlib.sha256(artifact.read_bytes()).hexdigest() != expected_hash:
            return False
    return True
