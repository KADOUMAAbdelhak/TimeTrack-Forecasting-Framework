"""Stable external run identity and atomic validated completion records."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def canonical_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run_identity(
    *, environment: str, formulation: str, resource: str | None, vm_id: str,
    fold: int, context_length: int, seed: int, phase: str, config_hash: str,
    support_hash: str, archive_hash: str, cohort_hash: str,
) -> dict[str, Any]:
    payload = {
        "environment": environment,
        "formulation": formulation,
        "resource": resource,
        "vm_id": vm_id,
        "fold": fold,
        "L": context_length,
        "seed": seed,
        "phase": phase,
        "config_hash": config_hash,
        "support_hash": support_hash,
        "archive_hash": archive_hash,
        "cohort_hash": cohort_hash,
    }
    payload["run_id"] = canonical_hash(payload)[:24]
    return payload


def atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def completion_valid(path: Path, expected_identity: dict[str, Any], expected_artifacts: dict[str, str]) -> bool:
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    if payload.get("status") != "complete" or payload.get("identity") != expected_identity:
        return False
    for relative, expected_hash in expected_artifacts.items():
        artifact = path.parent / relative
        if not artifact.is_file() or hashlib.sha256(artifact.read_bytes()).hexdigest() != expected_hash:
            return False
    return True


def scientific_workload_counts(vm_count: int = 35, folds: int = 5, contexts: int = 3, seeds: int = 3) -> dict[str, int]:
    counts = {
        "S1_inner": 4 * vm_count * folds * contexts * seeds,
        "S1_final": 4 * vm_count * folds * seeds,
        "S2_inner": 4 * vm_count * folds * contexts * seeds,
        "S2_final": 4 * vm_count * folds * seeds,
        "M1_inner": vm_count * folds * contexts * seeds,
        "M1_final": vm_count * folds * seeds,
    }
    counts["inner_total"] = counts["S1_inner"] + counts["S2_inner"] + counts["M1_inner"]
    counts["final_total"] = counts["S1_final"] + counts["S2_final"] + counts["M1_final"]
    counts["fit_total"] = counts["inner_total"] + counts["final_total"]
    counts["metric_rows"] = 31_500
    return counts
