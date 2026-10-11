#!/usr/bin/env python3
"""Zero-training validation of the Phase 4D execution implementation."""

from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from phase4d_execution import (
    ARCHIVE_SHA256, BASE, COHORT_SHA256, CONFIG_SHA256,
    EXECUTION_CONFORMANCE_SHA256, REQUIRED_IDENTITY_FIELDS, SCIENTIFIC_ROOT,
    TRACES, completion_is_reusable, completion_path, pilot_identity, plan_summary,
    run_identity, scientific_path, sha256_file, write_successful_completion,
)
from run_phase4d_scientific import CONFIG_PATH, SUPPORT_PATH, verify_frozen_identities
from validate_phase4d_preflight import PROTECTED_PROTOCOL_PATHS, verify_historical_protocol


ROOT = BASE.parents[1]
RESULT = BASE / "PHASE4D_EXECUTION_CONFORMANCE_VALIDATION.json"
TEST = BASE / "tests/test_phase4d_execution_conformance.py"


def main() -> None:
    failures: list[str] = []
    verify_frozen_identities()
    historical_failures = verify_historical_protocol()
    failures.extend(historical_failures)
    if sha256_file(CONFIG_PATH) != CONFIG_SHA256:
        failures.append("config_sha256")
    cohort = json.loads((BASE / "manifests/CANDIDATE_35_VM_COHORT_SUMMARY.json").read_text())
    if cohort.get("candidate_id_list_sha256") != COHORT_SHA256:
        failures.append("cohort_sha256")

    root_files_before = sorted(path for path in SCIENTIFIC_ROOT.rglob("*") if path.is_file()) if SCIENTIFIC_ROOT.exists() else []
    if root_files_before:
        failures.append("scientific_artifacts_preexist")

    plan = plan_summary()
    expected_plan = {
        "total_run_ids": 56700, "unique_run_ids": 56700,
        "duplicate_run_ids": 0, "pilot_scientific_collisions": 0,
        "inner_total": 42525, "final_total": 14175,
    }
    for key, expected in expected_plan.items():
        if plan.get(key) != expected:
            failures.append(f"plan:{key}")
    if plan.get("per_trace") != {trace: 18900 for trace in TRACES}:
        failures.append("plan:per_trace")

    identity = run_identity("Materna-T1", "S1", "CPU", "74", 1, 4, 0, "inner", "synthetic")
    if not set(REQUIRED_IDENTITY_FIELDS).issubset(identity):
        failures.append("identity_schema")
    if identity == pilot_identity(support_sha256="synthetic"):
        failures.append("pilot_identity_collision")
    try:
        escaped = scientific_path("..", "legacy")
        del escaped
        failures.append("namespace_escape")
    except ValueError:
        pass
    if not completion_path("Materna-T1", "inner", identity["run_id"]).is_relative_to(SCIENTIFIC_ROOT):
        failures.append("canonical_output_root")

    lifecycle = {}
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        artifact = tmp / "history.json"
        artifact.write_text("{}\n")
        completion = tmp / "complete.json"
        payload = write_successful_completion(
            completion, identity, {"history": artifact}, training_finished=True, base=tmp
        )
        lifecycle["inner_outer_test_accessed"] = payload["outer_test_accessed"]
        lifecycle["inner_reusable"] = completion_is_reusable(completion, identity, base=tmp)
        if payload["outer_test_accessed"] or not lifecycle["inner_reusable"]:
            failures.append("inner_completion_lifecycle")

    suite = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(TEST)], cwd=ROOT,
        env=os.environ | {"PYTHONPATH": f"{BASE}:{ROOT / 'independent_validation/05_bitbrains_factorial'}"},
        text=True, capture_output=True,
    )
    if suite.returncode:
        failures.append("conformance_tests")
    test_result = (suite.stdout + suite.stderr).strip()

    for path in (BASE / "validate_phase4d_trace.py", BASE / "validate_phase4d_combined.py"):
        if not path.is_file():
            failures.append(f"missing_validator:{path.name}")
    if "outer" in " ".join(inspect.signature(__import__("src.selection", fromlist=["select_context"]).select_context).parameters).lower():
        failures.append("selection_outer_argument")

    root_files_after = sorted(path for path in SCIENTIFIC_ROOT.rglob("*") if path.is_file()) if SCIENTIFIC_ROOT.exists() else []
    if root_files_after != root_files_before:
        failures.append("validator_created_scientific_artifact")
    state = {
        "scientific_fits": 0, "optimizer_executions": 0,
        "scientific_outer_test_accesses": 0, "scientific_predictions": 0,
        "predictive_outcomes_inspected": 0, "scientific_figures": 0,
        "scientific_v1_real_execution_artifacts": len(root_files_after),
    }
    result = {
        "status": "PASS" if not failures else "FAIL", "failures": failures,
        "classification": "IMPLEMENTATION_CONFORMANCE_CHECKPOINT",
        "decision_sha256": EXECUTION_CONFORMANCE_SHA256,
        "historical_protocol_integrity": "PASS" if not historical_failures else "FAIL",
        "current_protected_protocol_paths": len(PROTECTED_PROTOCOL_PATHS),
        "config_sha256": CONFIG_SHA256, "archive_sha256": ARCHIVE_SHA256,
        "cohort_sha256": COHORT_SHA256, "support_manifest_sha256": sha256_file(SUPPORT_PATH),
        "scientific_output_root": SCIENTIFIC_ROOT.relative_to(ROOT).as_posix(),
        "run_identity_fields": list(REQUIRED_IDENTITY_FIELDS), "dry_run_plan": plan,
        "atomic_completion_lifecycle": lifecycle, "test_result": test_result,
        "test_returncode": suite.returncode, "scientific_state": state,
        "scientific_analysis_performed": False,
    }
    RESULT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
