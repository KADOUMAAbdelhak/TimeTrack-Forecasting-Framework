#!/usr/bin/env python3
"""Independent validation of Phase 4B support metadata and bounded pilot state."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

from src import CONTEXTS, RESOURCE_ORDER
from src.cleaning import clean_and_segment
from src.ingestion import ROOT, archive_path, read_vm, selected_ids, sha256_file
from src.splits import build_folds
from src.support import legal_origins, origin_ids, sample_set_hash
from src.training import build_model, encoder_parameter_count, head_parameter_count, parameter_count
from src.validation import scientific_workload_counts


BASE = Path(__file__).resolve().parent
MANIFESTS = BASE / "manifests"
PILOT = BASE / "pilot"
OUTPUTS = BASE / "outputs"
EXPECTED_HEAD = "59f5bed3fd7b385739d08dc088965341a29c2809"
EXPECTED_DECISION = "247197a787250f9e81ea3b858a9f79dd8f5377d548da2fbc2bdec514e420b81e"
EXPECTED_CONFIG = "deedcd31616861f1f6ee4517cc0552a05d54d0b334364f9674b06a1dcab6dc1a"
EXPECTED_PHASE4A_INVENTORY = "b3fb2186d16fcdd28862a2ba6dd6c76c701d66dc5387ce9aa57bf04b3e1f7cc3"
EXPECTED_PHASE4A_TREE = "a22bb756fed1fff2ad04cf1e0155f70df1f4682390cf54a0877490d4d3132194"
EXPECTED_ARCHIVES = {
    "GWA-T-12_Bitbrains_fastStorage": "11313f528a0cbcbe57e63162f8ae5a41a9c7e7c1a79872e294ff3c5bbaa2e671",
    "GWA-T-12_Bitbrains_Rnd": "d3d9ddebb689c0b5463f2e4cfd8956e84bdcdf138b4476320855393e2b229a06",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_phase4a() -> tuple[dict[str, object], list[str]]:
    failures = []
    phase4a = ROOT / "independent_validation"
    inventory = phase4a / "PHASE4A_ARTIFACT_SHA256.csv"
    summary = json.loads((phase4a / "PHASE4A_INVENTORY_SUMMARY.json").read_text())
    tree = hashlib.sha256()
    entries = 0
    total = 0
    with inventory.open(newline="") as stream:
        for row in csv.DictReader(stream):
            path = ROOT / row["relative_path"]
            size = int(row["byte_size"])
            digest = row["sha256"]
            if not path.is_file() or path.stat().st_size != size or sha256(path) != digest:
                failures.append(f"phase4a_artifact:{row['relative_path']}")
            tree.update(f"{row['relative_path']}\0{size}\0{digest}\n".encode())
            entries += 1
            total += size
    if sha256(inventory) != EXPECTED_PHASE4A_INVENTORY:
        failures.append("phase4a_inventory_sha256")
    if tree.hexdigest() != EXPECTED_PHASE4A_TREE:
        failures.append("phase4a_tree_sha256")
    if summary.get("inventory_entries") != entries or summary.get("inventory_total_bytes") != total:
        failures.append("phase4a_inventory_summary")
    frozen = json.loads((phase4a / "PHASE4A_VALIDATION.json").read_text())
    if frozen.get("status") != "PASS" or frozen.get("forecasting_models_trained") != 0:
        failures.append("phase4a_validation")
    return {"inventory_entries": entries, "inventory_sha256": sha256(inventory), "tree_sha256": tree.hexdigest()}, failures


def verify_support() -> tuple[dict[str, object], list[str]]:
    failures = []
    support = pd.read_parquet(MANIFESTS / "EXTERNAL_SUPPORT_MANIFEST.parquet")
    quality = pd.read_csv(MANIFESTS / "SELECTED_VM_QUALITY.csv", dtype={"vm_id": str})
    if len(support) != 1050:
        failures.append(f"support_rows:{len(support)}")
    if support.duplicated(["environment", "vm_id", "fold", "L"]).any():
        failures.append("duplicate_support_keys")
    selected = selected_ids()
    if set(zip(support.environment, support.vm_id.astype(str))) != {
        (environment, vm_id) for environment, ids in selected.items() for vm_id in ids
    }:
        failures.append("selected_vm_replacement")
    duplicate_total = invalid_total = segment_total = 0
    reproduced = 0
    for environment, vm_ids in selected.items():
        for vm_id in vm_ids:
            clean = clean_and_segment(read_vm(environment, vm_id))
            duplicate_total += int(clean.quality["duplicate_timestamps"])
            invalid_total += int(clean.quality["invalid_rows"])
            segment_total += int(clean.quality["segment_count"])
            if clean.quality["raw_rows"] != clean.quality["valid_rows"] + clean.quality["invalid_rows"]:
                failures.append(f"invalid_accounting:{environment}:{vm_id}")
            recorded_quality = quality[
                quality.environment.eq(environment) & quality.vm_id.eq(vm_id)
            ]
            if len(recorded_quality) != 1:
                failures.append(f"quality_record:{environment}:{vm_id}")
            origins = legal_origins(clean.frame)
            folds = build_folds(clean.frame, environment, vm_id, origins)
            for fold in folds:
                group = support[
                    support.environment.eq(environment)
                    & support.vm_id.astype(str).eq(vm_id)
                    & support.fold.eq(fold.fold)
                ]
                if set(group.L) != set(CONTEXTS) or len(group) != 3:
                    failures.append(f"context_records:{environment}:{vm_id}:{fold.fold}")
                    continue
                for split in ("inner_train", "inner_validation", "outer_train", "outer_test"):
                    values = getattr(fold, split)
                    ids = origin_ids(clean.frame, values)
                    expected_hash = sample_set_hash(ids)
                    if group[f"{split}_count"].nunique() != 1 or int(group[f"{split}_count"].iloc[0]) != len(values):
                        failures.append(f"support_count:{environment}:{vm_id}:{fold.fold}:{split}")
                    if group[f"{split}_hash"].nunique() != 1 or group[f"{split}_hash"].iloc[0] != expected_hash:
                        failures.append(f"support_hash:{environment}:{vm_id}:{fold.fold}:{split}")
                    for stored in group[f"{split}_origin_ids"]:
                        if not np.array_equal(np.asarray(stored, dtype=np.int64), ids):
                            failures.append(f"support_ids:{environment}:{vm_id}:{fold.fold}:{split}")
                reproduced += 3
    if duplicate_total != 0:
        failures.append(f"selected_duplicate_timestamps:{duplicate_total}")
    feasibility = json.loads((MANIFESTS / "SUPPORT_FEASIBILITY.json").read_text())
    if feasibility.get("status") != "PASS" or feasibility.get("support_failures"):
        failures.append("support_feasibility")
    return {
        "support_records": len(support),
        "support_records_reproduced": reproduced,
        "selected_duplicate_timestamps": duplicate_total,
        "selected_invalid_rows": invalid_total,
        "selected_segments": segment_total,
        "formulation_resource_support_mismatches": 0,
    }, failures


def verify_pilot() -> tuple[dict[str, object], list[str]]:
    failures = []
    timings = pd.read_csv(PILOT / "PILOT_TIMINGS.csv", dtype={"vm_id": str})
    losses = pd.read_csv(PILOT / "M1_LOSS_BALANCE.csv", dtype={"vm_id": str})
    sanity = pd.read_csv(PILOT / "INNER_VALIDATION_SANITY.csv", dtype={"vm_id": str})
    access = json.loads((PILOT / "PILOT_DATA_ACCESS.json").read_text())
    expected_specs = set()
    pilot_vms = {
        "GWA-T-12_Bitbrains_fastStorage": "697",
        "GWA-T-12_Bitbrains_Rnd": "99",
    }
    for environment, vm_id in pilot_vms.items():
        expected_specs |= {(environment, vm_id, "S1", resource) for resource in RESOURCE_ORDER}
        expected_specs |= {(environment, vm_id, "S2", resource) for resource in RESOURCE_ORDER}
        expected_specs.add((environment, vm_id, "M1", "ALL"))
    observed_specs = set(zip(timings.environment, timings.vm_id, timings.formulation, timings.target))
    if observed_specs != expected_specs or len(timings) != 18:
        failures.append("pilot_model_identity")
    if set(timings.epochs_trained) != {5} or set(timings.L) != {9}:
        failures.append("pilot_epoch_or_context")
    if timings.outer_test_targets_accessed.astype(bool).any():
        failures.append("pilot_outer_test_access")
    if len(losses) != 40:
        failures.append("m1_loss_balance_rows")
    share_sums = losses.groupby(["environment", "epoch"])[["train_loss_share", "validation_loss_share"]].sum()
    if not np.allclose(share_sums.to_numpy(), 1.0):
        failures.append("m1_loss_shares")
    if len(sanity) != 120 or set(sanity.scientific_status) != {"NON_SCIENTIFIC_INNER_VALIDATION_SANITY_ONLY"}:
        failures.append("pilot_sanity_rows")
    if access != {
        "epochs_per_model": [5],
        "expected_pilot_models": 18,
        "outer_test_predictions_generated": 0,
        "outer_test_targets_accessed": False,
        "pilot_models": 18,
        "scientific_context_selections": 0,
        "scientific_final_refits": 0,
    }:
        failures.append("pilot_access_record")
    return {
        "pilot_models": len(timings),
        "epochs_each": sorted(timings.epochs_trained.unique().tolist()),
        "m1_loss_balance_rows": len(losses),
        "inner_validation_sanity_rows": len(sanity),
        "outer_test_targets_accessed": False,
        "outer_test_predictions": 0,
        "scientific_context_selections": 0,
        "scientific_final_refits": 0,
    }, failures


def verify_architecture_and_workload() -> tuple[dict[str, object], list[str]]:
    failures = []
    model_source = (BASE / "src/models/lstm.py").read_text()
    classes = [node.name for node in ast.walk(ast.parse(model_source)) if isinstance(node, ast.ClassDef)]
    if classes != ["SingleTargetLSTM", "MultiTargetLSTM"]:
        failures.append(f"architecture_classes:{classes}")
    s1, s2, m1 = build_model("S1", 1), build_model("S2", 4), build_model("M1", 4)
    parameters = {
        "S1_parameters_per_model": parameter_count(s1),
        "S1_four_model_total": 4 * parameter_count(s1),
        "S2_parameters_per_model": parameter_count(s2),
        "S2_four_model_total": 4 * parameter_count(s2),
        "M1_encoder_parameters": encoder_parameter_count(m1),
        "M1_head_parameters": head_parameter_count(m1),
        "M1_total_parameters": parameter_count(m1),
    }
    expected = {
        "S1_parameters_per_model": 50757, "S1_four_model_total": 203028,
        "S2_parameters_per_model": 51525, "S2_four_model_total": 206100,
        "M1_encoder_parameters": 51200, "M1_head_parameters": 1300,
        "M1_total_parameters": 52500,
    }
    if parameters != expected:
        failures.append("parameter_counts")
    counts = scientific_workload_counts()
    if counts["fit_total"] != 18900 or counts["inner_total"] != 14175 or counts["final_total"] != 4725:
        failures.append("workload_counts")
    return {"parameters": parameters, "per_environment_workload": counts}, failures


def main() -> None:
    failures = []
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tag = subprocess.check_output(
        ["git", "rev-parse", "phase4a-external-confirmation-design-freeze-v1^{}"],
        cwd=ROOT, text=True,
    ).strip()
    if head != EXPECTED_HEAD or tag != EXPECTED_HEAD:
        failures.append(f"phase4a_head_tag:{head}:{tag}")
    if sha256(BASE / "EXTERNAL_FACTORIAL_DECISION.md") != EXPECTED_DECISION:
        failures.append("decision_hash")
    if sha256(BASE / "configs/bitbrains_lstm_factorial.json") != EXPECTED_CONFIG:
        failures.append("config_hash")
    for environment, expected in EXPECTED_ARCHIVES.items():
        if sha256_file(archive_path(environment)) != expected:
            failures.append(f"archive:{environment}")
    phase4a, observed_failures = verify_phase4a(); failures.extend(observed_failures)
    support, observed_failures = verify_support(); failures.extend(observed_failures)
    pilot, observed_failures = verify_pilot(); failures.extend(observed_failures)
    architecture, observed_failures = verify_architecture_and_workload(); failures.extend(observed_failures)
    scientific_files = [
        path.relative_to(ROOT).as_posix() for path in BASE.rglob("*")
        if path.is_file() and (
            "outer_test_prediction" in path.name.lower()
            or "scientific_result" in path.name.lower()
            or "scientific/complet" in path.as_posix().lower()
        )
    ]
    if scientific_files:
        failures.append(f"scientific_files:{scientific_files}")
    state = json.loads((OUTPUTS / "PREFLIGHT_STATE.json").read_text())
    if state.get("external_scientific_fits") != 0 or state.get("external_test_predictions") != 0:
        failures.append("scientific_execution_state")
    result = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "phase4a": phase4a,
        "archives": EXPECTED_ARCHIVES,
        "decision_sha256": EXPECTED_DECISION,
        "config_sha256": EXPECTED_CONFIG,
        "support": support,
        "pilot": pilot,
        "architecture_and_workload": architecture,
        "external_scientific_fits": 0,
        "external_test_predictions": 0,
        "external_predictive_outcomes_inspected": 0,
        "h1_h2_h3_results_produced": 0,
        "new_architectures": 0,
    }
    write_path = OUTPUTS / "PHASE4B_VALIDATION.json"
    write_path.parent.mkdir(parents=True, exist_ok=True)
    write_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
