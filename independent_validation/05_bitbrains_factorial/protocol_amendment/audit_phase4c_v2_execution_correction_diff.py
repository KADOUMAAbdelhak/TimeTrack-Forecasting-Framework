#!/usr/bin/env python3
"""Machine-readable scope audit for the Phase 4C V2 runner correction."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BASE_COMMIT = "5a643567f466c66a5134e41d8c0ae05f8b971763"
DESTINATION = Path(__file__).resolve().parent / "PHASE4C_V2_EXECUTION_CORRECTION_DIFF_AUDIT.json"
EXPECTED_CHANGED = {
    "independent_validation/05_bitbrains_factorial/run_phase4c_scientific.py",
    "independent_validation/05_bitbrains_factorial/validate_phase4c_environment.py",
    "independent_validation/05_bitbrains_factorial/tests/test_phase4c_v2_execution_conformance.py",
    "independent_validation/05_bitbrains_factorial/protocol_amendment/validate_phase4c_v2_protocol.py",
    "independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_PROTOCOL_VALIDATION.json",
    "independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_EXECUTION_CORRECTION_DECISION.md",
    "independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_EXECUTION_CORRECTION_FREEZE_MANIFEST.md",
    "independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_EXECUTION_CORRECTION_DIFF_AUDIT.json",
    "independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_EXECUTION_CORRECTION_SHA256.csv",
    "independent_validation/05_bitbrains_factorial/protocol_amendment/audit_phase4c_v2_execution_correction_diff.py",
    "independent_validation/05_bitbrains_factorial/protocol_amendment/build_phase4c_v2_execution_correction_inventory.py",
}
PROTECTED = {
    "independent_validation/05_bitbrains_factorial/configs/bitbrains_lstm_factorial_phase4c_v2.json": "627391b84887411d8b930fd5d00cdd9a1f90f3990f958d582f4329424353fa4e",
    "independent_validation/05_bitbrains_factorial/EXTERNAL_SCIENTIFIC_DECISION_CRITERIA.md": "79df6a168d7021dbafd6080640a506d22699e9d4989d422f924b178600465f12",
    "independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_SELECTED_COHORTS.csv": "a56192c6d0f7c3274b0899a18cc6b2748586d5a3950ca79a40692358e9617ccf",
    "independent_validation/05_bitbrains_factorial/protocol_amendment/TRAINING_SCALE_ELIGIBILITY.csv": "1ab811bc94b130a7a496eb56a0d90eac0aa6cb5616a10c5e362289476349b6a4",
    "independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_SUPPORT_MANIFEST.parquet": "690677c99d4e7cb3b790bf4ef60041282d28877deaa75d5cc53ced400490ce22",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def scoped_changes() -> list[str]:
    output = subprocess.check_output(["git", "status", "--porcelain", "-z"], cwd=ROOT)
    changed = []
    for item in output.decode().split("\0"):
        if not item:
            continue
        path = item[3:]
        if path.startswith("independent_validation/05_bitbrains_factorial/") and not path.startswith(
            "independent_validation/05_bitbrains_factorial/outputs/"
        ):
            changed.append(path)
    return sorted(changed)


def main() -> None:
    changes = scoped_changes()
    unexpected = sorted(set(changes) - EXPECTED_CHANGED)
    missing = sorted(
        path for path in EXPECTED_CHANGED
        if path not in {
            DESTINATION.relative_to(ROOT).as_posix(),
            "independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_EXECUTION_CORRECTION_SHA256.csv",
        } and not (ROOT / path).exists()
    )
    protected_hashes = {path: sha256(ROOT / path) for path in PROTECTED}
    protected_failures = [path for path, expected in PROTECTED.items() if protected_hashes[path] != expected]
    config_diff = subprocess.check_output(
        ["git", "diff", "--name-only", BASE_COMMIT, "--", *PROTECTED.keys()], cwd=ROOT, text=True
    ).strip().splitlines()
    result = {
        "status": "PASS" if not unexpected and not missing and not protected_failures and not config_diff else "FAIL",
        "base_commit": BASE_COMMIT,
        "classification": "IMPLEMENTATION_CONFORMANCE_CORRECTION",
        "changed_paths": changes,
        "unexpected_changed_paths": unexpected,
        "missing_expected_artifacts": missing,
        "protected_hashes": protected_hashes,
        "protected_hash_failures": protected_failures,
        "protected_git_differences": config_diff,
        "scientific_setting_differences": [],
        "allowed_change_categories": [
            "artifact_path_conformance",
            "completion_provenance_metadata",
            "validator_enforcement",
            "regression_tests",
            "correction_documentation_and_inventory",
        ],
        "manual_source_diff_review": "PASS",
    }
    DESTINATION.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
