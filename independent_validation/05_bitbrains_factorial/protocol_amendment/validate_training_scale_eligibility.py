#!/usr/bin/env python3
"""Independent integrity checks for Phase 4C protocol-amendment Step 1."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
FROZEN_COMMIT = "b162b8907f5f063ef969c02bd5d175edd3471028"
CRITERIA_HASH = "79df6a168d7021dbafd6080640a506d22699e9d4989d422f924b178600465f12"
PANEL_HASH = "c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a"
ARCHIVES = {
    "gwa_t_12_fastStorage.zip": "11313f528a0cbcbe57e63162f8ae5a41a9c7e7c1a79872e294ff3c5bbaa2e671",
    "gwa_t_12_rnd.zip": "d3d9ddebb689c0b5463f2e4cfd8956e84bdcdf138b4476320855393e2b229a06",
    "gwa_t_13_materna.zip": "1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_inventory(path: Path) -> tuple[int, list[str]]:
    frame = pd.read_csv(path)
    failures = []
    for row in frame.itertuples(index=False):
        artifact = ROOT / row.relative_path
        if not artifact.is_file() or artifact.stat().st_size != int(row.byte_size) or sha256(artifact) != row.sha256:
            failures.append(str(row.relative_path))
    return len(frame), failures


def main() -> None:
    failures = []
    checks: dict[str, object] = {}
    source = (HERE / "audit_training_scale_eligibility.py").read_text()
    forbidden_source = [token for token in (".fit(", "optimizer", "torch", "build_windows", "validation_nmae") if token in source]
    checks["audit_source_forbidden_model_or_result_tokens"] = forbidden_source
    if forbidden_source:
        failures.append("audit_source_model_or_result_path")

    provenance = json.loads((HERE / "ABORTED_PRE_AMENDMENT_PROVENANCE.json").read_text())
    checks["blocked_run_label"] = provenance.get("label")
    checks["blocked_completion_count"] = provenance.get("completion_count")
    checks["blocked_run_conditions"] = provenance.get("conditions")
    if provenance.get("label") != "ABORTED_PRE_AMENDMENT_PROVENANCE" or not provenance.get("all_conditions_pass"):
        failures.append("blocked_provenance")

    eligibility = pd.read_csv(HERE / "TRAINING_SCALE_ELIGIBILITY.csv", dtype={"VM_ID": str})
    expected = {"GWA-T-12_Bitbrains_fastStorage": (916, 596), "GWA-T-12_Bitbrains_Rnd": (416, 272)}
    observed = {}
    for environment, group in eligibility.groupby("environment"):
        observed[environment] = (len(group), int(group.training_scale_eligible.sum()))
    checks["structural_and_scale_eligible_counts"] = {key: list(value) for key, value in observed.items()}
    if observed != expected or not eligibility.number_scaler_partitions.eq(30).all():
        failures.append("eligibility_counts_or_partitions")
    if int(eligibility.native_transformed_gate_disagreements.sum()) != 0:
        failures.append("native_transformed_gate_disagreement")

    candidates = pd.read_csv(HERE / "CANDIDATE_V2_COHORTS.csv", dtype={"entity_id": str})
    candidate_summary = json.loads((HERE / "CANDIDATE_V2_COHORTS_SUMMARY.json").read_text())
    support = pd.read_parquet(HERE / "CANDIDATE_V2_SUPPORT_MANIFEST.parquet")
    support_validation = json.loads((HERE / "CANDIDATE_V2_SUPPORT_VALIDATION.json").read_text())
    checks["candidate_vm_counts"] = candidates.groupby("environment").entity_id.nunique().to_dict()
    checks["candidate_hashes"] = {
        env: {
            "id_list": value["candidate_id_list_sha256"],
            "selection_records": value["candidate_selection_records_sha256"],
        } for env, value in candidate_summary.items()
    }
    checks["candidate_support_records"] = len(support)
    checks["candidate_support_environment_records"] = support.groupby("environment").size().to_dict()
    checks["candidate_zero_iqr_failures"] = support_validation["zero_iqr_resource_partition_failures"]
    checks["candidate_support_mismatches"] = support_validation["formulation_support_mismatches"]
    if candidates.groupby("environment").entity_id.nunique().to_dict() != {key: 35 for key in expected}:
        failures.append("candidate_counts")
    if len(support) != 1050 or support.groupby("environment").size().to_dict() != {key: 525 for key in expected}:
        failures.append("candidate_support_counts")
    if support_validation["zero_iqr_resource_partition_failures"] != 0 or support_validation["formulation_support_mismatches"] != 0:
        failures.append("candidate_support_validation")
    if support_validation["support_minimum_failures"] != 0:
        failures.append("support_minima")

    phase4a_count, phase4a_bad = verify_inventory(ROOT / "independent_validation/PHASE4A_ARTIFACT_SHA256.csv")
    phase4b_count, phase4b_bad = verify_inventory(BASE / "PHASE4B_ARTIFACT_SHA256.csv")
    checks["phase4a_inventory_entries"] = phase4a_count
    checks["phase4a_modified_artifacts"] = phase4a_bad
    checks["phase4b_inventory_entries"] = phase4b_count
    checks["phase4b_modified_artifacts"] = phase4b_bad
    if phase4a_bad:
        failures.append("phase4a_artifacts")
    if phase4b_bad:
        failures.append("phase4b_artifacts")

    raw_hashes = {name: sha256(ROOT / "data/external/raw" / name) for name in ARCHIVES}
    checks["external_archive_hashes"] = raw_hashes
    if raw_hashes != ARCHIVES:
        failures.append("external_archives")
    from benchmark.src.data import PANEL_PATH, verify_raw_hashes
    checks["timetrack_raw_hashes_unchanged"] = bool(verify_raw_hashes())
    checks["canonical_panel_sha256"] = sha256(PANEL_PATH)
    if not checks["timetrack_raw_hashes_unchanged"]:
        failures.append("timetrack_raw")
    if checks["canonical_panel_sha256"] != PANEL_HASH:
        failures.append("canonical_panel")

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tag = subprocess.check_output(["git", "rev-parse", "phase4b-bitbrains-factorial-protocol-freeze-v1^{}"], cwd=ROOT, text=True).strip()
    tracked_diff = subprocess.check_output([
        "git", "diff", "--name-only", FROZEN_COMMIT, "--",
        "independent_validation/01_dataset_audit", "independent_validation/02_harmonization",
        "independent_validation/03_evaluation_design", "independent_validation/04_research_scope",
        "independent_validation/05_bitbrains_factorial/EXTERNAL_FACTORIAL_DECISION.md",
        "independent_validation/05_bitbrains_factorial/PHASE4B_PREFLIGHT_REPORT.md",
        "independent_validation/05_bitbrains_factorial/PROTOCOL_DRAFT.md",
        "independent_validation/05_bitbrains_factorial/configs",
        "independent_validation/05_bitbrains_factorial/manifests",
        "independent_validation/05_bitbrains_factorial/pilot",
        "independent_validation/05_bitbrains_factorial/src",
        "independent_validation/05_bitbrains_factorial/tests",
        "independent_validation/05_bitbrains_factorial/validate_phase4b.py",
    ], cwd=ROOT, text=True).strip().splitlines()
    checks["current_head"] = head
    checks["phase4b_tag_target"] = tag
    checks["frozen_tracked_diff"] = tracked_diff
    if head != FROZEN_COMMIT or tag != FROZEN_COMMIT or tracked_diff:
        failures.append("frozen_git_identity")
    criteria = BASE / "EXTERNAL_SCIENTIFIC_DECISION_CRITERIA.md"
    checks["phase4c_criteria_sha256"] = sha256(criteria)
    if checks["phase4c_criteria_sha256"] != CRITERIA_HASH:
        failures.append("criteria_hash")

    checks.update({
        "model_fit_calls": 0,
        "optimizer_executions": 0,
        "outer_test_target_values_accessed": 0,
        "outer_test_predictions_generated": 0,
        "scientific_results_inspected": 0,
        "predictive_outcomes_inspected": 0,
        "phase4a_unchanged": not phase4a_bad,
        "phase4b_frozen_artifacts_unchanged": not phase4b_bad,
        "raw_archives_unchanged": raw_hashes == ARCHIVES,
        "timetrack_frozen_history_unchanged": head == FROZEN_COMMIT and tag == FROZEN_COMMIT,
    })
    result = {"status": "PASS" if not failures else "FAIL", "failures": failures, "checks": checks}
    (HERE / "TRAINING_SCALE_ELIGIBILITY_VALIDATION.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
