#!/usr/bin/env python3
"""Execute the frozen Materna protocol; importing or planning never trains."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
BITBRAINS = ROOT / "independent_validation/05_bitbrains_factorial"
sys.path.insert(0, str(BITBRAINS))
sys.path.insert(0, str(BASE))

import run_phase4c_scientific as core  # noqa: E402
from phase4d_execution import (  # noqa: E402
    ARCHIVE_SHA256,
    BASE as EXECUTION_BASE,
    COHORT_SHA256,
    CONFIG_SHA256,
    CONTEXTS,
    EXECUTION_CONFORMANCE_SHA256,
    RESOURCES,
    SCIENTIFIC_RELATIVE_ROOT,
    SCIENTIFIC_ROOT,
    SEEDS,
    SELECTED_IDS,
    TRACES,
    atomic_json_write,
    canonical_hash,
    completion_is_reusable,
    completion_path,
    failure_path,
    plan_summary,
    run_identity,
    scientific_relative_path,
    sha256_file,
    write_failure_record,
)
from run_phase4d_audit import (  # noqa: E402
    RAW_ARCHIVE,
    legal_origins_structure_only,
    read_vm,
)
from src.cleaning import clean_and_segment  # noqa: E402
from src.splits import build_folds  # noqa: E402


CONFIG_PATH = BASE / "configs/materna_replication_v1.json"
COHORT_PATH = BASE / "manifests/CANDIDATE_35_VM_COHORT.csv"
SUPPORT_PATH = BASE / "manifests/MATERNA_SUPPORT_MANIFEST.parquet"
PROTOCOL_TAG = "phase4d-materna-secondary-replication-protocol-freeze-v1"
PROTOCOL_COMMIT = "c4077318bfbb02e112b439baa3ae7a0e35db0dc5"
TRACE_ALIASES = {"T1": "Materna-T1", "T2": "Materna-T2", "T3": "Materna-T3"}

_VM_CACHE: dict[tuple[str, str], tuple[Any, list[Any]]] = {}
_ORIGINAL_ATOMIC_JSON = core.atomic_json_write
_ORIGINAL_BUILD_WINDOWS = core.build_windows
_OUTER_TEST_ACCESSED = False


def selected_ids() -> dict[str, list[str]]:
    return {trace: list(SELECTED_IDS) for trace in TRACES}


def vm_data(trace: str, vm_id: str) -> tuple[Any, list[Any]]:
    key = (trace, vm_id)
    if key not in _VM_CACHE:
        clean = clean_and_segment(read_vm(trace, vm_id))
        folds = build_folds(
            clean.frame, trace, vm_id, legal_origins_structure_only(clean.frame)
        )
        _VM_CACHE[key] = clean, folds
    return _VM_CACHE[key]


def _identity_adapter(
    environment_key: str,
    formulation: str,
    resource_name: str | None,
    vm_id: str,
    fold: int,
    context_length: int,
    seed: int,
    phase: str,
    support_hash: str,
    selected_epoch: int | None = None,
) -> dict[str, Any]:
    return run_identity(
        environment_key, formulation, resource_name, vm_id, fold,
        context_length, seed, phase, support_hash,
        selected_epoch=selected_epoch,
    )


def _tracked_build_windows(frame: pd.DataFrame, origins: np.ndarray, length: int):
    global _OUTER_TEST_ACCESSED
    for _clean, folds in _VM_CACHE.values():
        if any(origins is fold.outer_test for fold in folds):
            _OUTER_TEST_ACCESSED = True
            break
    return _ORIGINAL_BUILD_WINDOWS(frame, origins, length)


def _completion_writer(path: Path, payload: dict[str, Any]) -> None:
    """Persist history/metrics before atomically publishing completion."""
    identity = payload.get("identity", {})
    if payload.get("status") != "complete" or identity.get("run_kind") != "scientific":
        _ORIGINAL_ATOMIC_JSON(path, payload)
        return
    trace = identity["trace"]
    formulation = identity["formulation"].lower()
    run_id = identity["run_id"]
    if identity["phase"] == "inner":
        history_path = SCIENTIFIC_ROOT / trace / formulation / "inner_histories" / f"{run_id}.json"
        history = {
            "run_id": run_id,
            "best_epoch": payload["best_epoch"],
            "epochs_trained": payload["epochs_trained"],
            "validation_nmae": payload["validation_nmae"],
            "epoch_logs": payload.get("epoch_logs", []),
        }
        _ORIGINAL_ATOMIC_JSON(history_path, history)
        payload["history_path"] = history_path.relative_to(BASE).as_posix()
        payload["history_sha256"] = sha256_file(history_path)
    else:
        metrics_path = SCIENTIFIC_ROOT / trace / formulation / "metrics" / f"{run_id}.json"
        metric_payload = {
            "run_id": run_id,
            "metrics": payload["metrics"],
            "persistence_metrics": payload["persistence_metrics"],
        }
        _ORIGINAL_ATOMIC_JSON(metrics_path, metric_payload)
        payload["metrics_path"] = metrics_path.relative_to(BASE).as_posix()
        payload["metrics_sha256"] = sha256_file(metrics_path)
    payload["run_kind"] = "scientific"
    payload["execution_conformance_sha256"] = EXECUTION_CONFORMANCE_SHA256
    _ORIGINAL_ATOMIC_JSON(path, payload)


def _valid_inner(path: Path, expected: dict[str, Any]) -> bool:
    try:
        payload = json.loads(path.read_text())
        history = BASE / payload["history_path"]
    except (OSError, KeyError, json.JSONDecodeError):
        return False
    return (
        payload.get("status") == "complete"
        and payload.get("identity") == expected
        and expected.get("run_kind") == "scientific"
        and payload.get("outer_test_accessed") is False
        and payload.get("run_kind") == "scientific"
        and payload.get("execution_conformance_sha256") == EXECUTION_CONFORMANCE_SHA256
        and history.is_file()
        and sha256_file(history) == payload.get("history_sha256")
        and isinstance(payload.get("best_epoch"), int)
        and isinstance(payload.get("validation_nmae"), list)
    )


def _valid_final(path: Path, expected: dict[str, Any]) -> bool:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    if (
        payload.get("status") != "complete"
        or payload.get("identity") != expected
        or expected.get("run_kind") != "scientific"
        or payload.get("outer_test_accessed") is not True
        or payload.get("test_evaluations") != 1
        or payload.get("run_kind") != "scientific"
        or payload.get("execution_conformance_sha256") != EXECUTION_CONFORMANCE_SHA256
    ):
        return False
    artifacts = {
        "model": (payload.get("model_path"), payload.get("model_sha256")),
        "prediction": (payload.get("prediction_path"), payload.get("prediction_sha256")),
        "metrics": (payload.get("metrics_path"), payload.get("metrics_sha256")),
    }
    for relative, expected_hash in artifacts.values():
        artifact = BASE / str(relative)
        if not artifact.is_file() or sha256_file(artifact) != expected_hash:
            return False
    expected_rows = 20 if expected["formulation"] == "M1" else 5
    return len(payload.get("metrics", [])) == expected_rows


def _completion_metadata(
    phase: str,
    *,
    evaluation_completed: bool = False,
    prediction_persisted: bool = False,
    metric_record_count: int = 0,
) -> dict[str, Any]:
    if phase == "inner":
        if evaluation_completed or prediction_persisted or metric_record_count:
            raise RuntimeError("Inner completion cannot access outer test")
        return {"outer_test_accessed": False, "test_evaluations": 0}
    if not evaluation_completed or not prediction_persisted or metric_record_count <= 0:
        raise RuntimeError("Final completion cannot precede evaluation and artifacts")
    return {"outer_test_accessed": True, "test_evaluations": 1}


def verify_frozen_identities() -> None:
    if sha256_file(CONFIG_PATH) != CONFIG_SHA256:
        raise RuntimeError("Frozen Phase 4D scientific config differs")
    if sha256_file(RAW_ARCHIVE) != ARCHIVE_SHA256:
        raise RuntimeError("Frozen Materna archive differs")
    cohort = json.loads((BASE / "manifests/CANDIDATE_35_VM_COHORT_SUMMARY.json").read_text())
    if cohort["candidate_id_list_sha256"] != COHORT_SHA256:
        raise RuntimeError("Frozen Materna cohort differs")
    import subprocess
    target = subprocess.check_output(
        ["git", "rev-parse", f"{PROTOCOL_TAG}^{{}}"], cwd=ROOT, text=True
    ).strip()
    if target != PROTOCOL_COMMIT:
        raise RuntimeError("Frozen Phase 4D protocol tag differs")


def configure_core() -> None:
    """Bind frozen Phase 4C primitives to the Phase 4D Materna namespace."""
    core.BASE = BASE
    core.ROOT = ROOT
    core.OUT = SCIENTIFIC_ROOT
    core.SCIENTIFIC_RELATIVE_ROOT = SCIENTIFIC_RELATIVE_ROOT
    core.CONFIG_PATH = CONFIG_PATH
    core.CONFIG_HASH = CONFIG_SHA256
    core.CRITERIA_HASH = EXECUTION_CONFORMANCE_SHA256
    core.SUPPORT = SUPPORT_PATH
    core.ENVIRONMENTS = {trace: trace for trace in TRACES}
    core.ARCHIVE_HASHES = {trace: ARCHIVE_SHA256 for trace in TRACES}
    core.COHORT_HASHES = {trace: COHORT_SHA256 for trace in TRACES}
    core.CONTEXTS = CONTEXTS
    core.SEEDS = SEEDS
    core.RESOURCE_ORDER = RESOURCES
    core.selected_ids = selected_ids
    core.vm_data = vm_data
    core.run_identity = _identity_adapter
    core.completion_path = completion_path
    core.scientific_relative_path = scientific_relative_path
    core.environment_dir = lambda trace: SCIENTIFIC_ROOT / trace
    core.valid_inner = _valid_inner
    core.valid_final = _valid_final
    core.completion_access_metadata = _completion_metadata
    core.atomic_json_write = _completion_writer
    core.build_windows = _tracked_build_windows
    core.verify_frozen_identities = verify_frozen_identities


def inner_worker(task: dict[str, Any]) -> dict[str, float]:
    configure_core()
    return core.inner_worker(task)


def final_worker(task: dict[str, Any]) -> dict[str, float]:
    global _OUTER_TEST_ACCESSED
    configure_core()
    _OUTER_TEST_ACCESSED = False
    try:
        return core.final_worker(task)
    except Exception as error:
        clean, folds = vm_data(task["environment_key"], task["vm_id"])
        del clean
        fold = folds[int(task["fold"]) - 1]
        support = core.split_hash(fold, "outer_train", "outer_test")
        for spec in task["specs"]:
            identity = run_identity(
                task["environment_key"], task["formulation"], spec["resource"],
                task["vm_id"], int(task["fold"]), int(spec["L"]),
                int(spec["seed"]), "final", support,
                selected_epoch=int(spec["epoch"]),
            )
            attempt = 1 + len(list(
                (SCIENTIFIC_ROOT / task["environment_key"] / "runtime" / "failures").glob(
                    f"{identity['run_id']}.attempt-*.json"
                )
            ))
            write_failure_record(
                failure_path(task["environment_key"], identity["run_id"], attempt),
                identity,
                stage="post_outer_test" if _OUTER_TEST_ACCESSED else "pre_outer_test",
                outer_test_accessed=_OUTER_TEST_ACCESSED,
                error=f"{type(error).__name__}: {error}",
            )
        raise


def execute_trace(trace: str, workers: int) -> None:
    configure_core()
    verify_frozen_identities()
    invocation_started = time.perf_counter()
    env_dir = SCIENTIFIC_ROOT / trace
    for relative in (
        "s1/models", "s1/predictions", "s1/metrics", "s1/inner_histories",
        "s2/models", "s2/predictions", "s2/metrics", "s2/inner_histories",
        "m1/models", "m1/predictions", "m1/metrics", "m1/inner_histories",
        "validation", "runtime/completions/inner", "runtime/completions/final",
        "runtime/failures", "runtime/progress", "runtime/inventories",
    ):
        (env_dir / relative).mkdir(parents=True, exist_ok=True)
    core.support_snapshot(trace)
    stage_runtime: dict[str, Any] = {}
    for formulation in ("S1", "S2", "M1"):
        tasks = [
            {"environment_key": trace, "formulation": formulation, "vm_id": vm_id,
             "fold": fold, "L": length}
            for vm_id in SELECTED_IDS for fold in range(1, 6) for length in CONTEXTS
        ]
        stage_runtime[f"{formulation}_inner"] = core.run_tasks(
            tasks, inner_worker, workers, f"{trace}_{formulation}_INNER"
        )
    records = core.inner_records(trace)
    if len(records) != 14_175:
        raise RuntimeError(f"Expected 14,175 inner completions, found {len(records)}")
    contexts, epochs = core.select_all_contexts(trace, records)
    for formulation in ("S1", "S2", "M1"):
        tasks = []
        selected = epochs[epochs.formulation.eq(formulation)]
        for row in selected.itertuples(index=False):
            tasks.append({
                "environment_key": trace,
                "formulation": formulation,
                "vm_id": str(row.vm_id),
                "fold": int(row.fold),
                "specs": [{
                    "resource": None if pd.isna(row.resource) else row.resource,
                    "seed": int(row.seed), "L": int(row.selected_L),
                    "epoch": int(row.selected_epoch),
                }],
            })
        stage_runtime[f"{formulation}_final"] = core.run_tasks(
            tasks, final_worker, workers, f"{trace}_{formulation}_FINAL"
        )
    core.consolidate(trace, contexts, epochs, stage_runtime, invocation_started)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", choices=("T1", "T2", "T3", "all"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    verify_frozen_identities()
    if args.plan:
        print(json.dumps(plan_summary(), indent=2, sort_keys=True))
        return
    if args.trace is None:
        parser.error("--trace is required unless --plan is used")
    if args.workers < 1 or args.workers > 4:
        raise ValueError("workers must be in [1,4]")
    traces = TRACES if args.trace == "all" else (TRACE_ALIASES[args.trace],)
    for trace in traces:
        execute_trace(trace, args.workers)
        print(f"TRACE_EXECUTION_COMPLETE trace={trace} technical_validation_pending=true")


if __name__ == "__main__":
    main()
