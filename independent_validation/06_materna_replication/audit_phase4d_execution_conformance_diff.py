#!/usr/bin/env python3
"""Audit the implementation-only delta from the frozen Phase 4D protocol."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from phase4d_execution import BASE, PROTOCOL_COMMIT, sha256_file
from validate_phase4d_preflight import PROTECTED_PROTOCOL_PATHS, verify_historical_protocol


ROOT = BASE.parents[1]
RESULT = BASE / "PHASE4D_EXECUTION_CONFORMANCE_DIFF_AUDIT.json"
PREFIX = "independent_validation/06_materna_replication/"
ALLOWED = {
    PREFIX + name for name in (
        "PHASE4D_EXECUTION_CONFORMANCE_DECISION.md",
        "PHASE4D_EXECUTION_CONFORMANCE_FREEZE_MANIFEST.md",
        "PHASE4D_EXECUTION_CONFORMANCE_SHA256.csv",
        "PHASE4D_EXECUTION_CONFORMANCE_INVENTORY_SUMMARY.json",
        "PHASE4D_EXECUTION_CONFORMANCE_VALIDATION.json",
        "PHASE4D_EXECUTION_CONFORMANCE_DIFF_AUDIT.json",
        "PHASE4D_DRY_RUN_PLAN_SUMMARY.json",
        "PHASE4D_MATERNA_PREFLIGHT_VALIDATION.json",
        "audit_phase4d_execution_conformance_diff.py",
        "build_phase4d_execution_conformance_inventory.py",
        "phase4d_execution.py",
        "run_phase4d_scientific.py",
        "tests/test_phase4d_execution_conformance.py",
        "validate_phase4d_combined.py",
        "validate_phase4d_execution_conformance.py",
        "validate_phase4d_preflight.py",
        "validate_phase4d_trace.py",
    )
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    tracked = set(filter(None, git("diff", "--name-only", PROTOCOL_COMMIT).splitlines()))
    untracked = set(filter(None, git("ls-files", "--others", "--exclude-standard", "--", PREFIX).splitlines()))
    changed = sorted(tracked | untracked)
    unexpected = sorted(set(changed) - ALLOWED)
    historical_failures = verify_historical_protocol()
    protected_changed = sorted(path for path in PROTECTED_PROTOCOL_PATHS if path in changed)
    scientific_setting_mutations = sorted(
        path for path in changed if any(token in path for token in (
            "/configs/", "/manifests/CANDIDATE_", "/manifests/MATERNA_SUPPORT_",
            "TRAINING_SCALE_ELIGIBILITY.csv", "ZERO_IQR_PREVALENCE.csv",
        ))
    )
    failures = []
    if unexpected:
        failures.append("unexpected_diff_paths")
    if historical_failures:
        failures.append("historical_or_protected_integrity")
    if protected_changed or scientific_setting_mutations:
        failures.append("scientific_setting_mutation")
    result = {
        "status": "PASS" if not failures else "FAIL", "failures": failures,
        "base_commit": PROTOCOL_COMMIT, "changed_paths": changed,
        "unexpected_paths": unexpected, "protected_protocol_paths_changed": protected_changed,
        "scientific_setting_mutations": scientific_setting_mutations,
        "historical_protocol_failures": historical_failures,
        "zero_changes": {
            key: True for key in (
                "materna_config", "cohort_ids", "cohort_ordering", "support",
                "transforms", "scaler", "horizons", "contexts", "folds", "seeds",
                "architecture", "optimizer", "training_hyperparameters", "M1_loss",
                "classification_rules", "bootstrap", "R1_R2_R3_R4", "publication_role",
            )
        },
        "audit_script_sha256": sha256_file(Path(__file__)),
    }
    RESULT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
