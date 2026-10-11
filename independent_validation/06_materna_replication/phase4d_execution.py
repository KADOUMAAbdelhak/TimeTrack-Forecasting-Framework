"""Canonical Phase 4D scientific namespace, identity, and completion semantics."""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
SCIENTIFIC_RELATIVE_ROOT = Path("outputs/scientific_v1")
SCIENTIFIC_ROOT = (BASE / SCIENTIFIC_RELATIVE_ROOT).resolve()

PROTOCOL_COMMIT = "c4077318bfbb02e112b439baa3ae7a0e35db0dc5"
PROTOCOL_TAG = "phase4d-materna-secondary-replication-protocol-freeze-v1"
CONFIG_SHA256 = "064ef5a4864f5590b8149242c4011c37a49aee35cf60a4690f6aa126b98fce27"
ARCHIVE_SHA256 = "1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4"
COHORT_SHA256 = "4c9e8f4cfa5cf26c4188924c486cdfbe9d78972eec1f84f5e0f23b1e94353140"
SELECTION_RECORD_SHA256 = "63c1a7266057c4344bfd6211ee7d3fd2deba283e4b41797fc4e412483469b24b"
EXECUTION_CONFORMANCE_SHA256 = "3f5a780128f0d7931a44078d2f55f8168e3b444d51d2eb03cd635266b6bd368b"

TRACES = ("Materna-T1", "Materna-T2", "Materna-T3")
FORMULATIONS = ("S1", "S2", "M1")
RESOURCES = ("CPU", "THROUGHPUT", "MEMORY", "DISK_WRITE")
CONTEXTS = (4, 9, 18)
SEEDS = (0, 1, 2)
FOLDS = (1, 2, 3, 4, 5)
SELECTED_IDS = (
    "74", "134", "397", "266", "380", "281", "393", "227", "128", "299",
    "272", "08", "75", "133", "440", "306", "343", "305", "26", "302",
    "498", "103", "303", "76", "493", "416", "478", "442", "246", "345",
    "04", "98", "105", "92", "508",
)

REQUIRED_IDENTITY_FIELDS = (
    "run_kind", "trace", "environment", "formulation", "resource", "vm_id", "fold", "L",
    "seed", "phase", "config_sha256", "archive_sha256", "cohort_sha256",
    "support_sha256", "execution_conformance_sha256", "run_id",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def scientific_path(*parts: str | Path) -> Path:
    """Resolve a path and reject every escape from outputs/scientific_v1."""
    candidate = SCIENTIFIC_ROOT.joinpath(*(str(part) for part in parts)).resolve()
    if not candidate.is_relative_to(SCIENTIFIC_ROOT):
        raise ValueError("Phase 4D scientific artifact escaped outputs/scientific_v1")
    return candidate


def scientific_relative_path(*parts: str | Path) -> Path:
    return scientific_path(*parts).relative_to(BASE)


def completion_path(trace: str, phase: str, run_id: str) -> Path:
    if trace not in TRACES or phase not in {"inner", "final"}:
        raise ValueError("Invalid completion trace or phase")
    return scientific_path(trace, "runtime", "completions", phase, f"{run_id}.json")


def failure_path(trace: str, run_id: str, attempt: int) -> Path:
    if trace not in TRACES or attempt < 1:
        raise ValueError("Invalid failure trace or attempt")
    return scientific_path(trace, "runtime", "failures", f"{run_id}.attempt-{attempt}.json")


def run_identity(
    trace: str,
    formulation: str,
    resource: str | None,
    vm_id: str,
    fold: int,
    context_length: int | str,
    seed: int,
    phase: str,
    support_sha256: str,
    *,
    selected_epoch: int | None = None,
    run_kind: str = "scientific",
    config_sha256: str = CONFIG_SHA256,
    archive_sha256: str = ARCHIVE_SHA256,
    cohort_sha256: str = COHORT_SHA256,
    execution_conformance_sha256: str = EXECUTION_CONFORMANCE_SHA256,
) -> dict[str, Any]:
    if trace not in TRACES or formulation not in FORMULATIONS:
        raise ValueError("Invalid trace or formulation")
    expected_resources = RESOURCES if formulation in {"S1", "S2"} else (None,)
    if resource not in expected_resources:
        raise ValueError("Resource does not match formulation")
    if str(vm_id) not in SELECTED_IDS or fold not in FOLDS or seed not in SEEDS:
        raise ValueError("Identity is outside the frozen cohort/fold/seed grid")
    if phase not in {"inner", "final"}:
        raise ValueError("Invalid phase")
    if run_kind not in {"scientific", "technical_pilot"}:
        raise ValueError("Invalid run kind")
    payload: dict[str, Any] = {
        "run_kind": run_kind,
        "trace": trace,
        "environment": trace,
        "formulation": formulation,
        "resource": resource,
        "vm_id": str(vm_id),
        "fold": int(fold),
        "L": context_length,
        "seed": int(seed),
        "phase": phase,
        "config_sha256": config_sha256,
        "archive_sha256": archive_sha256,
        "cohort_sha256": cohort_sha256,
        "support_sha256": support_sha256,
        "execution_conformance_sha256": execution_conformance_sha256,
    }
    if selected_epoch is not None:
        payload["selected_epoch"] = int(selected_epoch)
    payload["run_id"] = canonical_hash(payload)
    return payload


def pilot_identity(**overrides: Any) -> dict[str, Any]:
    values = {
        "trace": "Materna-T1", "formulation": "S1", "resource": "CPU",
        "vm_id": "74", "fold": 1, "context_length": 9, "seed": 0,
        "phase": "inner", "support_sha256": "pilot-support",
        "run_kind": "technical_pilot", "config_sha256": "technical-pilot-config",
        "execution_conformance_sha256": "technical-pilot-execution",
    }
    values.update(overrides)
    return run_identity(**values)


def artifact_record(path: Path, *, base: Path = BASE) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "path": resolved.relative_to(base.resolve()).as_posix(),
        "sha256": sha256_file(resolved),
        "bytes": resolved.stat().st_size,
    }


def _artifact_valid(record: dict[str, Any], *, base: Path) -> bool:
    try:
        path = (base / record["path"]).resolve()
        if not path.is_relative_to(base.resolve()):
            return False
        return (
            path.is_file()
            and path.stat().st_size == int(record["bytes"])
            and sha256_file(path) == record["sha256"]
        )
    except (KeyError, OSError, ValueError, TypeError):
        return False


def write_successful_completion(
    path: Path,
    identity: dict[str, Any],
    artifacts: dict[str, Path],
    *,
    training_finished: bool,
    evaluation_completed: bool = False,
    evaluation_count: int = 0,
    base: Path = BASE,
) -> dict[str, Any]:
    """Atomically emit only a fully valid reusable completion."""
    if identity.get("run_kind") != "scientific":
        raise RuntimeError("Only scientific identities can create scientific completions")
    if not training_finished:
        raise RuntimeError("Training must finish before successful completion")
    phase = identity.get("phase")
    if phase == "inner":
        if evaluation_completed or evaluation_count or "prediction" in artifacts:
            raise RuntimeError("Inner completion cannot access outer test")
        outer_test_accessed = False
    elif phase == "final":
        required = {"model", "prediction", "metrics"}
        if not evaluation_completed or evaluation_count != 1 or not required.issubset(artifacts):
            raise RuntimeError("Final completion requires one evaluation and model/prediction/metrics")
        outer_test_accessed = True
    else:
        raise ValueError("Invalid completion phase")
    records = {name: artifact_record(value, base=base) for name, value in artifacts.items()}
    payload = {
        "status": "complete",
        "identity": identity,
        "phase": phase,
        "outer_test_accessed": outer_test_accessed,
        "outer_test_evaluations": evaluation_count,
        "artifacts": records,
        "atomic_completion": True,
    }
    atomic_json_write(path, payload)
    return payload


def write_failure_record(
    path: Path,
    identity: dict[str, Any],
    *,
    stage: str,
    outer_test_accessed: bool,
    error: str,
) -> dict[str, Any]:
    payload = {
        "status": "failed",
        "identity": identity,
        "stage": stage,
        "outer_test_accessed": bool(outer_test_accessed),
        "error": error,
        "reusable": False,
    }
    atomic_json_write(path, payload)
    return payload


def completion_is_reusable(
    path: Path,
    expected_identity: dict[str, Any],
    *,
    base: Path = BASE,
) -> bool:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    if (
        payload.get("status") != "complete"
        or payload.get("identity") != expected_identity
        or expected_identity.get("run_kind") != "scientific"
        or payload.get("phase") != expected_identity.get("phase")
        or payload.get("atomic_completion") is not True
    ):
        return False
    phase = expected_identity["phase"]
    expected_access = phase == "final"
    expected_evaluations = 1 if phase == "final" else 0
    if payload.get("outer_test_accessed") is not expected_access:
        return False
    if payload.get("outer_test_evaluations") != expected_evaluations:
        return False
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        return False
    required = {"model", "prediction", "metrics"} if phase == "final" else {"history"}
    if not required.issubset(artifacts):
        return False
    return all(_artifact_valid(record, base=base) for record in artifacts.values())


def plan_support_sha(trace: str, vm_id: str, fold: int, phase: str) -> str:
    return canonical_hash({"trace": trace, "vm_id": vm_id, "fold": fold, "phase": phase})


def iter_expected_plan() -> Iterable[dict[str, Any]]:
    """Enumerate 56,700 deterministic fit slots without loading data or training."""
    for trace in TRACES:
        for formulation in FORMULATIONS:
            resources = RESOURCES if formulation in {"S1", "S2"} else (None,)
            for resource in resources:
                for vm_id in SELECTED_IDS:
                    for fold in FOLDS:
                        inner_support = plan_support_sha(trace, vm_id, fold, "inner")
                        for length in CONTEXTS:
                            for seed in SEEDS:
                                yield run_identity(
                                    trace, formulation, resource, vm_id, fold, length,
                                    seed, "inner", inner_support,
                                )
                        final_support = plan_support_sha(trace, vm_id, fold, "final")
                        for seed in SEEDS:
                            yield run_identity(
                                trace, formulation, resource, vm_id, fold,
                                "SELECTED_L", seed, "final", final_support,
                            )


def plan_summary() -> dict[str, Any]:
    identities = list(iter_expected_plan())
    ids = [row["run_id"] for row in identities]
    by_trace = Counter(row["trace"] for row in identities)
    by_phase = Counter(row["phase"] for row in identities)
    by_formulation_phase = Counter(
        f"{row['formulation']}_{row['phase']}" for row in identities
    )
    pilot_ids = {
        pilot_identity(trace=trace, formulation=formulation, resource=resource)["run_id"]
        for trace in TRACES
        for formulation, resource in (("S1", "CPU"), ("M1", None))
    }
    scientific_ids = set(ids)
    return {
        "status": "PASS",
        "run_kind": "scientific",
        "total_run_ids": len(ids),
        "unique_run_ids": len(scientific_ids),
        "duplicate_run_ids": len(ids) - len(scientific_ids),
        "per_trace": dict(sorted(by_trace.items())),
        "inner_total": by_phase["inner"],
        "final_total": by_phase["final"],
        "by_formulation_phase": dict(sorted(by_formulation_phase.items())),
        "pilot_scientific_collisions": len(pilot_ids & scientific_ids),
        "identity_fields": list(REQUIRED_IDENTITY_FIELDS),
        "final_L_semantics": "SELECTED_L placeholder; numeric L is inserted after inner selection",
        "optimizer_executions": 0,
        "real_outer_test_accesses": 0,
    }
