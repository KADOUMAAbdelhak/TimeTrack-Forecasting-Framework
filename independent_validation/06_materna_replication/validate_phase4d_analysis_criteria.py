#!/usr/bin/env python3
"""Validate the prospective Materna analysis-criteria freeze without result inspection."""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import subprocess
from pathlib import Path


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
SCIENTIFIC_ROOT = BASE / "outputs/scientific_v1"
CRITERIA = BASE / "PHASE4D_MATERNA_SCIENTIFIC_ANALYSIS_CRITERIA.json"
OUTPUT = BASE / "PHASE4D_MATERNA_SCIENTIFIC_ANALYSIS_CRITERIA_VALIDATION.json"
HEAVY_INVENTORY = SCIENTIFIC_ROOT / "runtime/PHASE4D_EXECUTION_ARTIFACT_SHA256.csv"
HEAVY_SUMMARY = SCIENTIFIC_ROOT / "runtime/PHASE4D_EXECUTION_INVENTORY_SUMMARY.json"
COMPACT_INVENTORY = BASE / "PHASE4D_MATERNA_EXECUTION_CHECKPOINT_SHA256.csv"
COMPACT_SUMMARY = BASE / "PHASE4D_MATERNA_EXECUTION_CHECKPOINT_SUMMARY.json"

EXECUTION_COMMIT = "dba05d2505e91170f7d4de69027f4692e5b30584"
EXECUTION_TAG = "phase4d-materna-three-trace-execution-freeze-v1"
CONFORMANCE_COMMIT = "5e7a42acf47dc0f14a73e7188c17831629f2229d"
CONFORMANCE_TAG = "phase4d-materna-execution-conformance-freeze-v1"
PROTOCOL_COMMIT = "c4077318bfbb02e112b439baa3ae7a0e35db0dc5"
PROTOCOL_TAG = "phase4d-materna-secondary-replication-protocol-freeze-v1"
CONFIG_SHA256 = "064ef5a4864f5590b8149242c4011c37a49aee35cf60a4690f6aa126b98fce27"
HEAVY_SHA256 = "8484e62b2dae596ece90308c18ea617ec904ea55ceb4fbfc76e2fcaa55dd1718"
HEAVY_TREE = "3d9a6ffe1b7d520bc5ca0e3f36e147f39e87590c88f8289a26c962a09e6756e1"
COMPACT_SHA256 = "ba7e4e3cc39b6d3a9318db6e27573a41edc115e654ef82866ec9a080b5065d84"
COMPACT_TREE = "abb816d612d9ab84d9bd118536e74793d4556b1258995c612efc6382c977248d"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def verify_inventory(path: Path, expected_entries: int, expected_inventory: str,
                     expected_tree: str) -> dict:
    rows = list(csv.DictReader(path.open(newline="")))
    failures = []
    tree = hashlib.sha256()
    total_bytes = 0
    for row in rows:
        artifact = ROOT / row["relative_path"]
        size = int(row["byte_size"])
        total_bytes += size
        tree.update(f"{row['relative_path']},{size},{row['sha256']}\n".encode())
        if not artifact.is_file():
            failures.append(f"missing:{row['relative_path']}")
            continue
        if artifact.stat().st_size != size:
            failures.append(f"size:{row['relative_path']}")
            continue
        if sha256_file(artifact) != row["sha256"]:
            failures.append(f"sha256:{row['relative_path']}")
    observed = {
        "entries": len(rows),
        "verified": len(rows) - len(failures),
        "failures": failures,
        "total_bytes": total_bytes,
        "inventory_sha256": sha256_file(path),
        "tree_sha256": tree.hexdigest(),
    }
    observed["status"] = "PASS" if (
        len(rows) == expected_entries
        and not failures
        and observed["inventory_sha256"] == expected_inventory
        and observed["tree_sha256"] == expected_tree
    ) else "FAIL"
    return observed


def classify(gain: float, horizons: int, vms: int, folds: int, seeds: int) -> str:
    if gain >= 1 and horizons >= 4 and vms >= 25 and folds >= 4 and seeds >= 2:
        return "BROAD_POSITIVE"
    if gain > 0 and horizons >= 3 and vms >= 15 and folds >= 3 and seeds >= 2:
        return "CONDITIONALLY_POSITIVE"
    if gain <= -1 and horizons <= 1 and vms <= 10 and folds <= 1 and seeds <= 1:
        return "BROAD_NEGATIVE"
    return "NEUTRAL_OR_MIXED"


def cross_resource_decision(positive: int, broad_negative: int, mean_sign: int) -> str:
    if positive >= 3 and mean_sign > 0 and broad_negative <= 1:
        return "CROSS_RESOURCE_INPUT_SUPPORTED"
    if (positive <= 1 and mean_sign <= 0) or broad_negative >= 2:
        return "CROSS_RESOURCE_INPUT_NOT_SUPPORTED"
    return "CROSS_RESOURCE_INPUT_MIXED"


def shared_decision(positive: int, broad_negative: int, material_negative: int,
                    mean_sign: int, strong_tradeoff: bool) -> str:
    negative_transfer = (
        (positive >= 1 and max(broad_negative, material_negative) >= 2)
        or strong_tradeoff
    )
    not_supported = positive <= 1 and mean_sign <= 0
    supported = positive >= 3 and mean_sign > 0 and broad_negative == 0
    conditional = mean_sign > 0 and positive >= 2 and not supported
    if negative_transfer:
        return "SHARED_REPRESENTATION_NEGATIVE_TRANSFER"
    if not_supported:
        return "SHARED_REPRESENTATION_NOT_SUPPORTED"
    if supported:
        return "SHARED_REPRESENTATION_SUPPORTED"
    if conditional:
        return "SHARED_REPRESENTATION_CONDITIONALLY_SUPPORTED"
    return "SHARED_REPRESENTATION_NOT_SUPPORTED"


def joint_decision(positive: int, negative: int, mean_sign: int) -> str:
    if positive >= 3 and mean_sign > 0:
        return "JOINT_SYSTEM_BROADLY_BENEFICIAL"
    if negative >= 3 and mean_sign < 0:
        return "JOINT_SYSTEM_BROADLY_HARMFUL"
    return "JOINT_SYSTEM_MIXED"


def r1_decision(supported: int, mean_sign: int, positive_synthesized: int,
                trace_differs: bool, sign_changes: int, class_changes: int) -> str:
    broad = supported >= 2 and mean_sign > 0 and positive_synthesized >= 3
    temporal = not broad and (trace_differs or sign_changes >= 2 or class_changes >= 2)
    not_supported = (
        supported == 0 and mean_sign <= 0 and positive_synthesized <= 1 and not temporal
    )
    if broad:
        return "R1_BROAD_CROSS_RESOURCE_BENEFIT"
    if temporal:
        return "R1_RESOURCE_TEMPORAL_DEPENDENCE_CONFIRMED"
    if not_supported:
        return "R1_CROSS_RESOURCE_INPUT_NOT_SUPPORTED"
    return "R1_MIXED_OR_INCONCLUSIVE"


def r2_decision(supported: int, conditional: int, mean_sign: int,
                positive_synthesized: int, material_mixed: bool) -> str:
    negative = (
        supported == 0 and conditional <= 1 and mean_sign <= 0
        and positive_synthesized <= 1
    )
    mixed = supported == 0 and material_mixed
    benefit = (
        supported + conditional >= 2 and mean_sign > 0 and positive_synthesized >= 3
    )
    if negative:
        return "R2_NEGATIVE_SHARING_REPLICATED"
    if mixed:
        return "R2_MIXED_SHARING_EFFECT"
    if benefit:
        return "R2_SHARING_BENEFIT_REPLICATED"
    return "R2_INCONCLUSIVE"


def r3_decision(all_negative: bool, harmful: int, mean_sign: int,
                positive_synthesized: int, beneficial: int) -> str:
    replicated = all_negative and harmful >= 2
    partial = mean_sign <= 0 and positive_synthesized <= 2 and not replicated
    benefit = positive_synthesized >= 3 and mean_sign > 0 and beneficial >= 2
    if replicated:
        return "R3_JOINT_SYSTEM_UNDERPERFORMANCE_REPLICATED"
    if partial:
        return "R3_JOINT_SYSTEM_PARTIAL_UNDERPERFORMANCE"
    if benefit:
        return "R3_JOINT_SYSTEM_BENEFIT"
    return "R3_MIXED_OR_INCONCLUSIVE"


def r4_decision(variable_count: int, global_decisions_differ: bool) -> str:
    if variable_count >= 2 or global_decisions_differ:
        return "R4_TEMPORAL_HETEROGENEITY_CONFIRMED"
    if variable_count == 1:
        return "R4_TEMPORAL_HETEROGENEITY_WEAK"
    return "R4_TEMPORAL_HETEROGENEITY_NOT_SUPPORTED"


def decision_consistency() -> dict:
    resource_examples = {
        classify(1, 4, 25, 4, 2),
        classify(0.1, 3, 15, 3, 2),
        classify(-1, 1, 10, 1, 1),
        classify(0, 5, 35, 5, 3),
    }
    cross_labels = set()
    shared_labels = set()
    joint_labels = set()
    r1_labels = set()
    r2_labels = set()
    r3_labels = set()
    r4_labels = set()
    for positive, negative, mean_sign in itertools.product(range(5), range(5), (-1, 0, 1)):
        if positive + negative > 4:
            continue
        cross_labels.add(cross_resource_decision(positive, negative, mean_sign))
        joint_labels.add(joint_decision(positive, negative, mean_sign))
        for material_negative, tradeoff in itertools.product(range(5), (False, True)):
            shared_labels.add(shared_decision(
                positive, negative, material_negative, mean_sign, tradeoff
            ))
    for supported, mean_sign, positive, differs, sign_changes, class_changes in itertools.product(
        range(4), (-1, 0, 1), range(5), (False, True), range(5), range(5)
    ):
        r1_labels.add(r1_decision(
            supported, mean_sign, positive, differs, sign_changes, class_changes
        ))
    for supported, conditional, mean_sign, positive, mixed in itertools.product(
        range(4), range(4), (-1, 0, 1), range(5), (False, True)
    ):
        if supported + conditional <= 3:
            r2_labels.add(r2_decision(supported, conditional, mean_sign, positive, mixed))
    for all_negative, harmful, mean_sign, positive, beneficial in itertools.product(
        (False, True), range(4), (-1, 0, 1), range(5), range(4)
    ):
        r3_labels.add(r3_decision(all_negative, harmful, mean_sign, positive, beneficial))
    for variable_count, differs in itertools.product(range(13), (False, True)):
        r4_labels.add(r4_decision(variable_count, differs))
    expected = {
        "resource": {"BROAD_POSITIVE", "CONDITIONALLY_POSITIVE", "BROAD_NEGATIVE", "NEUTRAL_OR_MIXED"},
        "cross": {"CROSS_RESOURCE_INPUT_SUPPORTED", "CROSS_RESOURCE_INPUT_NOT_SUPPORTED", "CROSS_RESOURCE_INPUT_MIXED"},
        "shared": {"SHARED_REPRESENTATION_SUPPORTED", "SHARED_REPRESENTATION_CONDITIONALLY_SUPPORTED", "SHARED_REPRESENTATION_NEGATIVE_TRANSFER", "SHARED_REPRESENTATION_NOT_SUPPORTED"},
        "joint": {"JOINT_SYSTEM_BROADLY_BENEFICIAL", "JOINT_SYSTEM_BROADLY_HARMFUL", "JOINT_SYSTEM_MIXED"},
        "R1": {"R1_BROAD_CROSS_RESOURCE_BENEFIT", "R1_RESOURCE_TEMPORAL_DEPENDENCE_CONFIRMED", "R1_CROSS_RESOURCE_INPUT_NOT_SUPPORTED", "R1_MIXED_OR_INCONCLUSIVE"},
        "R2": {"R2_NEGATIVE_SHARING_REPLICATED", "R2_MIXED_SHARING_EFFECT", "R2_SHARING_BENEFIT_REPLICATED", "R2_INCONCLUSIVE"},
        "R3": {"R3_JOINT_SYSTEM_UNDERPERFORMANCE_REPLICATED", "R3_JOINT_SYSTEM_PARTIAL_UNDERPERFORMANCE", "R3_JOINT_SYSTEM_BENEFIT", "R3_MIXED_OR_INCONCLUSIVE"},
        "R4": {"R4_TEMPORAL_HETEROGENEITY_CONFIRMED", "R4_TEMPORAL_HETEROGENEITY_WEAK", "R4_TEMPORAL_HETEROGENEITY_NOT_SUPPORTED"},
    }
    observed = {
        "resource": resource_examples,
        "cross": cross_labels,
        "shared": shared_labels,
        "joint": joint_labels,
        "R1": r1_labels,
        "R2": r2_labels,
        "R3": r3_labels,
        "R4": r4_labels,
    }
    return {
        "status": "PASS" if all(observed[key] == value for key, value in expected.items()) else "FAIL",
        "all_labels_reachable": all(observed[key] == value for key, value in expected.items()),
        "deterministic_precedence": True,
        "residual_shared_states_have_frozen_fallback": True,
        "observed_labels": {key: sorted(value) for key, value in observed.items()},
    }


def validate_schema(criteria: dict) -> dict:
    required = {
        "schema_version", "freeze_scope", "protected_execution", "dimensions",
        "primary_aggregation", "secondary_aggregation", "positive_count_semantics",
        "resource_classification", "mechanical_definitions", "trace_decisions",
        "temporal_synthesis", "bootstrap", "persistence_interpretation", "R1",
        "R2", "R3", "R4", "cross_study_synthesis", "cross_study_claim_gates",
        "final_paper_scope_gate", "experimentation_stop_gate",
    }
    missing = sorted(required - set(criteria))
    exact = (
        criteria.get("schema_version") == "phase4d-materna-scientific-analysis-criteria-v1"
        and criteria.get("bootstrap", {}).get("rng_seed") == 20261007
        and criteria.get("bootstrap", {}).get("replicates") == 10000
        and criteria.get("primary_aggregation", {}).get("pool_individual_predictions") is False
        and criteria.get("temporal_synthesis", {}).get("weighting") == "equal_trace_weight_only"
    )
    return {"status": "PASS" if not missing and exact else "FAIL", "missing_keys": missing, "exact_constants": exact}


def validate_thresholds(criteria: dict) -> dict:
    expected = {
        "BROAD_POSITIVE": (1.0, 4, 25, 4, 2),
        "CONDITIONALLY_POSITIVE": (0.0, 3, 15, 3, 2),
        "BROAD_NEGATIVE": (-1.0, 1, 10, 1, 1),
    }
    rules = criteria["resource_classification"]
    observed = {
        "BROAD_POSITIVE": (
            rules["BROAD_POSITIVE"]["overall_gain_minimum_percent"],
            rules["BROAD_POSITIVE"]["positive_horizons_minimum"],
            rules["BROAD_POSITIVE"]["positive_VMs_minimum"],
            rules["BROAD_POSITIVE"]["positive_folds_minimum"],
            rules["BROAD_POSITIVE"]["positive_seeds_minimum"],
        ),
        "CONDITIONALLY_POSITIVE": (
            rules["CONDITIONALLY_POSITIVE"]["overall_gain_strictly_greater_than_percent"],
            rules["CONDITIONALLY_POSITIVE"]["positive_horizons_minimum"],
            rules["CONDITIONALLY_POSITIVE"]["positive_VMs_minimum"],
            rules["CONDITIONALLY_POSITIVE"]["positive_folds_minimum"],
            rules["CONDITIONALLY_POSITIVE"]["positive_seeds_minimum"],
        ),
        "BROAD_NEGATIVE": (
            rules["BROAD_NEGATIVE"]["overall_gain_maximum_percent"],
            rules["BROAD_NEGATIVE"]["positive_horizons_maximum"],
            rules["BROAD_NEGATIVE"]["positive_VMs_maximum"],
            rules["BROAD_NEGATIVE"]["positive_folds_maximum"],
            rules["BROAD_NEGATIVE"]["positive_seeds_maximum"],
        ),
    }
    return {"status": "PASS" if observed == expected else "FAIL", "unchanged": observed == expected}


def artifact_absence() -> dict:
    forbidden_roots = [
        SCIENTIFIC_ROOT / name for name in
        ("analysis", "comparisons", "figures", "bootstrap", "synthesis")
    ]
    present_roots = [path.relative_to(ROOT).as_posix() for path in forbidden_roots if path.exists()]
    forbidden_name_tokens = ("bootstrap", "formulation_gain", "scientific_figure", "temporal_synthesis")
    matching_files = []
    for path in SCIENTIFIC_ROOT.rglob("*"):
        if path.is_file() and any(token in path.name.lower() for token in forbidden_name_tokens):
            matching_files.append(path.relative_to(ROOT).as_posix())
    return {
        "status": "PASS" if not present_roots and not matching_files else "FAIL",
        "formulation_comparison_artifacts": 0 if not present_roots and not matching_files else len(present_roots) + len(matching_files),
        "bootstrap_artifacts": 0,
        "scientific_figures": 0,
        "present_forbidden_roots": present_roots,
        "matching_forbidden_files": matching_files,
    }


def main() -> None:
    criteria = json.loads(CRITERIA.read_text())
    schema = validate_schema(criteria)
    thresholds = validate_thresholds(criteria)
    decisions = decision_consistency()

    identities = {
        "execution_tag_target": git("rev-parse", f"{EXECUTION_TAG}^{{}}"),
        "conformance_tag_target": git("rev-parse", f"{CONFORMANCE_TAG}^{{}}"),
        "protocol_tag_target": git("rev-parse", f"{PROTOCOL_TAG}^{{}}"),
        "execution_checkpoint_is_ancestor": subprocess.run(
            ["git", "merge-base", "--is-ancestor", EXECUTION_COMMIT, "HEAD"], cwd=ROOT
        ).returncode == 0,
        "config_sha256": sha256_file(BASE / "configs/materna_replication_v1.json"),
    }
    identity_pass = (
        identities["execution_tag_target"] == EXECUTION_COMMIT
        and identities["conformance_tag_target"] == CONFORMANCE_COMMIT
        and identities["protocol_tag_target"] == PROTOCOL_COMMIT
        and identities["execution_checkpoint_is_ancestor"]
        and identities["config_sha256"] == CONFIG_SHA256
    )
    identities["status"] = "PASS" if identity_pass else "FAIL"

    heavy_summary = json.loads(HEAVY_SUMMARY.read_text())
    compact_summary = json.loads(COMPACT_SUMMARY.read_text())
    heavy = verify_inventory(HEAVY_INVENTORY, 141785, HEAVY_SHA256, HEAVY_TREE)
    compact = verify_inventory(COMPACT_INVENTORY, 42, COMPACT_SHA256, COMPACT_TREE)
    heavy["summary_matches"] = (
        heavy_summary["file_count"] == 141785
        and heavy_summary["inventory_sha256"] == HEAVY_SHA256
        and heavy_summary["execution_tree_sha256"] == HEAVY_TREE
    )
    compact["summary_matches"] = (
        compact_summary["entry_count"] == 42
        and compact_summary["compact_inventory_sha256"] == COMPACT_SHA256
        and compact_summary["execution_checkpoint_tree_sha256"] == COMPACT_TREE
    )
    if not heavy["summary_matches"]:
        heavy["status"] = "FAIL"
    if not compact["summary_matches"]:
        compact["status"] = "FAIL"

    absence = artifact_absence()
    checks = {
        "criteria_schema": schema,
        "decision_rule_consistency": decisions,
        "resource_thresholds": thresholds,
        "frozen_identities": identities,
        "heavy_execution_inventory": heavy,
        "compact_execution_checkpoint": compact,
        "result_artifact_absence": absence,
    }
    failures = [name for name, check in checks.items() if check["status"] != "PASS"]
    output = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "checks": checks,
        "analysis_lock": {
            "gains_calculated": 0,
            "bootstrap_executed": 0,
            "R1_evaluated": False,
            "R2_evaluated": False,
            "R3_evaluated": False,
            "R4_evaluated": False,
            "scientific_figures": 0,
            "predictive_metric_values_scientifically_inspected": False,
        },
        "inspection_boundary": {
            "method": "criteria, Git identities, technical summaries, file names, byte sizes, and SHA-256 hashes only",
            "scientific_table_parser_used": False,
            "prediction_parser_used": False,
            "predictive_values_read": False,
        },
    }
    OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
