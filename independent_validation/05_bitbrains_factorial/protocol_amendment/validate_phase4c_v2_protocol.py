#!/usr/bin/env python3
"""Independent zero-training validator for the prospective Phase 4C V2 protocol."""

from __future__ import annotations

import ast
import hashlib
import io
import json
import subprocess
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
PHASE4B_COMMIT = "b162b8907f5f063ef969c02bd5d175edd3471028"
PHASE4B_CONFIG_HASH = "deedcd31616861f1f6ee4517cc0552a05d54d0b334364f9674b06a1dcab6dc1a"
CRITERIA_HASH = "79df6a168d7021dbafd6080640a506d22699e9d4989d422f924b178600465f12"
CONFIG_HASH = "627391b84887411d8b930fd5d00cdd9a1f90f3990f958d582f4329424353fa4e"
DECISION_HASH = "4261300afd29362cf3d7faecc068bfc8170d5ac046691e80dd7b642d0a0add57"
ELIGIBILITY_HASH = "1ab811bc94b130a7a496eb56a0d90eac0aa6cb5616a10c5e362289476349b6a4"
AUDIT_VALIDATION_HASH = "033a81db0059f5084298de1cc8649f480144fbe6eca2386bca4fedb88e365458"
AMENDMENT_TAG = "phase4c-bitbrains-training-scale-amendment-freeze-v1"
AMENDMENT_COMMIT = "5a643567f466c66a5134e41d8c0ae05f8b971763"
AMENDMENT_INVENTORY_HASH = "323b5a0ca9ba1a7c0180a4faf973f74676dd6a40f99106ab497ebf51baeb4dc0"
AMENDMENT_TREE_HASH = "3fa66a780e4e87553325ae8bb136d31289f560c37fce20f1f3a2be514bb6de74"
EXECUTION_CORRECTION_HASH = "bd0a51380409290dd9deefd2cf25bbc783b018b559121bd21ba37fdfcb07e86d"
EXPECTED_COHORTS = {
    "GWA-T-12_Bitbrains_fastStorage": {
        "id": "ff2d65ff43bedae076f913e4b9e175e7762d835eafe5efc8c2a2590e487fc07c",
        "records": "168ccae403488cc06a60b5a2d6da1c57a88f32f793c4356bcecdfa4bf445d648",
    },
    "GWA-T-12_Bitbrains_Rnd": {
        "id": "f175f8b443adbed472caf5a2b26f9d73f989faf9f68334e520655c33ae982d2e",
        "records": "09f6b782a8cc5df7683e1dccf6a05551b0bf91daa64fde7868c1c145f48f0357",
    },
}
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


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def verify_inventory(path: Path) -> tuple[int, list[str]]:
    frame = pd.read_csv(path)
    bad = []
    for row in frame.itertuples(index=False):
        artifact = ROOT / row.relative_path
        if not artifact.is_file() or artifact.stat().st_size != int(row.byte_size) or sha256(artifact) != row.sha256:
            bad.append(str(row.relative_path))
    return len(frame), bad


def record_hash(frame: pd.DataFrame) -> str:
    payload = "".join(
        f"{row.rank}\0{row.entity_id}\0{row.selection_key}\0{row.selection_sha256}\n"
        for row in frame.sort_values("rank").itertuples(index=False)
    )
    return sha_text(payload)


def verify_historical_amendment() -> dict[str, object]:
    tag_target = subprocess.check_output(
        ["git", "rev-parse", f"{AMENDMENT_TAG}^{{}}"], cwd=ROOT, text=True
    ).strip()
    inventory_path = "independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_ARTIFACT_SHA256.csv"
    inventory_bytes = subprocess.check_output(["git", "show", f"{AMENDMENT_TAG}:{inventory_path}"], cwd=ROOT)
    inventory = pd.read_csv(io.BytesIO(inventory_bytes))
    bad = []
    for row in inventory.itertuples(index=False):
        try:
            payload = subprocess.check_output(["git", "show", f"{AMENDMENT_TAG}:{row.relative_path}"], cwd=ROOT)
        except subprocess.CalledProcessError:
            bad.append(str(row.relative_path))
            continue
        if len(payload) != int(row.byte_size) or hashlib.sha256(payload).hexdigest() != row.sha256:
            bad.append(str(row.relative_path))
    tree_payload = "".join(
        f"{row.relative_path},{row.byte_size},{row.sha256}\n"
        for row in inventory.sort_values("relative_path").itertuples(index=False)
    )
    return {
        "tag_target": tag_target,
        "inventory_entries": len(inventory),
        "inventory_sha256": hashlib.sha256(inventory_bytes).hexdigest(),
        "tree_sha256": hashlib.sha256(tree_payload.encode()).hexdigest(),
        "artifact_failures": bad,
        "pass": tag_target == AMENDMENT_COMMIT
        and hashlib.sha256(inventory_bytes).hexdigest() == AMENDMENT_INVENTORY_HASH
        and hashlib.sha256(tree_payload.encode()).hexdigest() == AMENDMENT_TREE_HASH
        and not bad,
    }


def main() -> None:
    failures: list[str] = []
    checks: dict[str, object] = {}

    phase4a_count, phase4a_bad = verify_inventory(ROOT / "independent_validation/PHASE4A_ARTIFACT_SHA256.csv")
    phase4b_count, phase4b_bad = verify_inventory(BASE / "PHASE4B_ARTIFACT_SHA256.csv")
    checks.update({
        "phase4a_inventory_entries": phase4a_count,
        "phase4a_modified_artifacts": phase4a_bad,
        "phase4b_inventory_entries": phase4b_count,
        "phase4b_modified_artifacts": phase4b_bad,
    })
    if phase4a_bad: failures.append("phase4a_frozen_artifacts")
    if phase4b_bad: failures.append("phase4b_frozen_artifacts")
    tag = subprocess.check_output(["git", "rev-parse", "phase4b-bitbrains-factorial-protocol-freeze-v1^{}"], cwd=ROOT, text=True).strip()
    checks["phase4b_tag_target"] = tag
    if tag != PHASE4B_COMMIT: failures.append("phase4b_tag")
    historical = verify_historical_amendment()
    checks["historical_phase4c_v2_amendment"] = historical
    if not historical["pass"]: failures.append("historical_phase4c_v2_amendment")

    criteria_hash = sha256(BASE / "EXTERNAL_SCIENTIFIC_DECISION_CRITERIA.md")
    audit_validation_hash = sha256(HERE / "TRAINING_SCALE_ELIGIBILITY_VALIDATION.json")
    audit_validation = json.loads((HERE / "TRAINING_SCALE_ELIGIBILITY_VALIDATION.json").read_text())
    checks.update({
        "phase4c_criteria_sha256": criteria_hash,
        "training_scale_audit_validation_sha256": audit_validation_hash,
        "training_scale_audit_validation_status": audit_validation.get("status"),
    })
    if criteria_hash != CRITERIA_HASH: failures.append("phase4c_criteria")
    if audit_validation_hash != AUDIT_VALIDATION_HASH or audit_validation.get("status") != "PASS": failures.append("scale_audit_validation")

    base_config_path = BASE / "configs/bitbrains_lstm_factorial.json"
    v2_config_path = BASE / "configs/bitbrains_lstm_factorial_phase4c_v2.json"
    base_config = json.loads(base_config_path.read_text())
    v2 = json.loads(v2_config_path.read_text())
    checks["phase4b_config_sha256"] = sha256(base_config_path)
    checks["phase4c_v2_config_sha256"] = sha256(v2_config_path)
    if checks["phase4b_config_sha256"] != PHASE4B_CONFIG_HASH: failures.append("phase4b_config")
    if checks["phase4c_v2_config_sha256"] != CONFIG_HASH: failures.append("v2_config")
    unchanged_keys = [
        "archives", "batch_size", "contexts", "dropout", "folds", "gradient_clip",
        "hidden_size", "horizon_minutes", "inner_validation_fraction", "layers",
        "learning_rate", "max_epochs", "outer_initial_train_fraction",
        "outer_test_fraction", "patience", "resource_order", "sample_leads", "seeds",
        "segment_gap_seconds", "support_minima",
    ]
    changed_frozen_settings = [key for key in unchanged_keys if v2.get(key) != base_config.get(key)]
    checks["changed_frozen_setting_keys"] = changed_frozen_settings
    if changed_frozen_settings: failures.append("frozen_settings_changed")
    semantic_checks = {
        "optimizer_Adam": v2["optimizer"] == "Adam",
        "four_resources": v2["resource_order"] == ["CPU", "THROUGHPUT", "MEMORY", "DISK_WRITE"],
        "transforms_unchanged": v2["transforms"] == {"CPU": "identity", "THROUGHPUT": "log1p", "MEMORY": "identity", "DISK_WRITE": "log1p"},
        "no_scaler_fallback": not any(v2["scaling"][key] for key in ("fallback", "epsilon", "alternate_statistic")),
        "M1_equal_loss": v2["loss"]["M1"] == "equal_arithmetic_mean_of_four_resource_MSEs",
        "contexts_unchanged": v2["contexts"] == [4, 9, 18],
        "horizons_unchanged": v2["sample_leads"] == [1, 2, 4, 9, 18],
        "folds_unchanged": v2["folds"] == 5,
        "architecture_unchanged": set(v2["architecture"]) >= {"S1", "S2", "M1"},
        "context_selection_unchanged": v2["context_selection"]["tie_break"] == "smaller_L",
        "epoch_lifecycle_unchanged": v2["epoch_lifecycle"]["outer_test_evaluations"] == 1,
        "aggregation_unchanged": v2["aggregation"]["order"] == "seed_mean_then_equal_weight_vm_fold_cells",
        "bootstrap_unchanged": v2["bootstrap"]["replicates"] == 10000 and v2["bootstrap"]["cluster"].startswith("VM_"),
        "H1_H2_H3_unchanged": set(v2["hypotheses"]) == {"H1", "H2", "H3"},
    }
    checks["scientific_semantics"] = semantic_checks
    if not all(semantic_checks.values()): failures.append("scientific_semantics")
    if sha256(HERE / "PHASE4C_PROTOCOL_AMENDMENT_DECISION.md") != DECISION_HASH: failures.append("amendment_decision")
    if sha256(HERE / "TRAINING_SCALE_ELIGIBILITY.csv") != ELIGIBILITY_HASH: failures.append("eligibility_identity")

    eligibility = pd.read_csv(HERE / "TRAINING_SCALE_ELIGIBILITY.csv", dtype={"VM_ID": str})
    cohorts = pd.read_csv(HERE / "PHASE4C_V2_SELECTED_COHORTS.csv", dtype={"entity_id": str})
    reproduced_hashes = {}
    cohort_counts = {}
    for environment, expected in EXPECTED_COHORTS.items():
        pool = eligibility[eligibility.environment.eq(environment) & eligibility.training_scale_eligible]
        ranked = sorted(
            (sha_text(f"phase4a-v1|{environment}|{vm_id}"), vm_id)
            for vm_id in pool.VM_ID.astype(str)
        )[:35]
        group = cohorts[cohorts.environment.eq(environment)].sort_values("rank")
        expected_ids = [vm_id for _, vm_id in ranked]
        observed_ids = group.entity_id.tolist()
        id_hash = sha_text("\n".join(observed_ids) + "\n")
        selection_hash = record_hash(group)
        reproduced_hashes[environment] = {"id_list": id_hash, "selection_records": selection_hash}
        cohort_counts[environment] = len(group)
        if observed_ids != expected_ids or id_hash != expected["id"] or selection_hash != expected["records"]:
            failures.append(f"cohort_reproduction:{environment}")
        selected_eligibility = pool[pool.VM_ID.isin(observed_ids)]
        if len(selected_eligibility) != 35 or not selected_eligibility.training_scale_eligible.all():
            failures.append(f"cohort_eligibility:{environment}")
    checks["v2_cohort_counts"] = cohort_counts
    checks["v2_cohort_hashes"] = reproduced_hashes

    support = pd.read_parquet(HERE / "PHASE4C_V2_SUPPORT_MANIFEST.parquet")
    scalers = pd.read_csv(HERE / "PHASE4C_V2_SCALER_PARTITIONS.csv")
    support_validation = json.loads((HERE / "PHASE4C_V2_SUPPORT_VALIDATION.json").read_text())
    transformed_iqrs = scalers.transformed_iqrs.map(json.loads)
    zero_iqr = sum(value <= 0 for values in transformed_iqrs for value in values)
    selected_scaler_counts = scalers.groupby(["environment", "vm_id"]).size()
    checks.update({
        "v2_support_records": len(support),
        "v2_support_records_by_environment": support.groupby("environment").size().astype(int).to_dict(),
        "v2_scaler_partitions": len(scalers),
        "v2_scaler_partitions_per_vm_unique": sorted(selected_scaler_counts.unique().tolist()),
        "v2_zero_iqr_failures": zero_iqr,
        "v2_support_failures": support_validation["support_minimum_failures"],
        "v2_S1_S2_M1_support_mismatches": support_validation["S1_S2_M1_support_mismatches"],
    })
    if len(support) != 1050 or support.groupby("environment").size().to_dict() != {key: 525 for key in EXPECTED_COHORTS}: failures.append("support_counts")
    if len(scalers) != 2100 or sorted(selected_scaler_counts.unique()) != [30]: failures.append("scaler_partition_counts")
    if zero_iqr or support_validation["support_minimum_failures"] or support_validation["S1_S2_M1_support_mismatches"]: failures.append("support_or_iqr")

    aborted = pd.read_csv(HERE / "ABORTED_PRE_AMENDMENT_RUNS.csv", dtype={"run_id": str})
    completion_files = sorted((BASE / "outputs/scientific/fastStorage/runtime/completions/inner").glob("*.json"))
    completion_hashes = {path.relative_to(ROOT).as_posix(): sha256(path) for path in completion_files}
    bad_aborted = [
        row.run_id for row in aborted.itertuples(index=False)
        if completion_hashes.get(row.relative_artifact_path) != row.completion_sha256
        or row.provenance_label != "ABORTED_PRE_AMENDMENT_PROVENANCE"
        or bool(row.scientifically_reusable)
        or bool(row.outer_test_accessed)
    ]
    checks["aborted_pre_amendment_runs"] = len(aborted)
    checks["aborted_artifact_identity_failures"] = bad_aborted
    if len(aborted) != 154 or len(completion_files) != 154 or bad_aborted: failures.append("aborted_provenance")

    runner_source = (BASE / "run_phase4c_scientific.py").read_text()
    ast.parse(runner_source)
    identity_tokens = [
        '"config_hash": CONFIG_HASH', '"cohort_hash": COHORT_HASHES[environment_key]',
        '"training_scale_eligibility_version": TRAINING_SCALE_ELIGIBILITY_VERSION',
        '"training_scale_eligibility_hash": TRAINING_SCALE_ELIGIBILITY_HASH',
    ]
    missing_identity_tokens = [token for token in identity_tokens if token not in runner_source]
    checks["runner_missing_v2_identity_tokens"] = missing_identity_tokens
    runner_literals = {
        node.value for node in ast.walk(ast.parse(runner_source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    routing_checks = {
        "canonical_root_defined": 'SCIENTIFIC_RELATIVE_ROOT = Path("outputs/scientific_v2")' in runner_source,
        "model_uses_canonical_builder": 'relative_model = scientific_relative_path(' in runner_source,
        "prediction_uses_canonical_builder": 'relative_prediction = scientific_relative_path(' in runner_source,
        "no_legacy_scientific_path_literal": not any(
            value == "outputs/scientific" or value.startswith("outputs/scientific/")
            for value in runner_literals
        ),
        "inner_access_false_enforced": 'completion_access_metadata("inner")' in runner_source,
        "final_access_true_guarded": 'completion_access_metadata(' in runner_source and 'evaluation_completed=True' in runner_source,
        "correction_identity_present": EXECUTION_CORRECTION_HASH in runner_source,
    }
    checks["corrected_runner_routing_and_access"] = routing_checks
    if missing_identity_tokens or not all(routing_checks.values()): failures.append("runner_v2_identity_or_conformance")

    v2_output = BASE / "outputs/scientific_v2"
    valid_fit_files = list(v2_output.glob("*/runtime/completions/**/*.json")) if v2_output.exists() else []
    prediction_files = list(v2_output.glob("**/predictions/*.parquet")) if v2_output.exists() else []
    raw_hashes = {name: sha256(ROOT / "data/external/raw" / name) for name in ARCHIVES}
    from benchmark.src.data import PANEL_PATH, verify_raw_hashes
    checks.update({
        "external_archive_hashes": raw_hashes,
        "timetrack_raw_hashes_unchanged": bool(verify_raw_hashes()),
        "canonical_panel_sha256": sha256(PANEL_PATH),
        "new_valid_scientific_fit_count": len(valid_fit_files),
        "optimizer_executions_during_amendment": 0,
        "outer_test_target_values_accessed": 0,
        "outer_test_predictions_generated": len(prediction_files),
        "scientific_predictive_outcomes_inspected": 0,
    })
    if raw_hashes != ARCHIVES or not checks["timetrack_raw_hashes_unchanged"]: failures.append("raw_hashes")
    if len(valid_fit_files) != 0 or len(prediction_files) != 0: failures.append("v2_scientific_outputs")

    result = {"status": "PASS" if not failures else "FAIL", "failures": failures, "checks": checks}
    (HERE / "PHASE4C_V2_PROTOCOL_VALIDATION.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
