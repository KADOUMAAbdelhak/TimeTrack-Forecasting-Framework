#!/usr/bin/env python3
"""Independent validation for the Phase 4D Materna preflight."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BITBRAINS = ROOT / "independent_validation/05_bitbrains_factorial"
sys.path.insert(0, str(BITBRAINS))
sys.path.insert(0, str(HERE))

from run_phase4d_audit import (  # noqa: E402
    TRACE_DATASETS, legal_origins_structure_only, phase_origins, read_vm, structural_pool,
)
from src import CONTEXTS, RESOURCE_ORDER  # noqa: E402
from src.cleaning import clean_and_segment  # noqa: E402
from src.panel import scaler_rows  # noqa: E402
from src.splits import build_folds  # noqa: E402
from src.training import build_model, parameter_count  # noqa: E402
from src.transforms import transform_resource  # noqa: E402


EXPECTED_HEAD = "d9c8ed80a90085d989d1dacc40f1c27377a4a76f"
EXPECTED_ARCHIVE = "1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4"
EXPECTED_CONFIG = "064ef5a4864f5590b8149242c4011c37a49aee35cf60a4690f6aa126b98fce27"
TAGS = {
    "phase4c-v2-bitbrains-external-confirmation-freeze-v1": EXPECTED_HEAD,
    "phase4c-v2-dual-environment-execution-freeze-v1": "549020a1a0b19d3c633d21cd13d2c8ff007225f1",
    "phase4c-v2-execution-conformance-freeze-v1": "30cb7b042726b6e6db8c6bf5ed43324b620ca42e",
    "phase4c-bitbrains-training-scale-amendment-freeze-v1": "5a643567f466c66a5134e41d8c0ae05f8b971763",
    "phase4b-bitbrains-factorial-protocol-freeze-v1": "b162b8907f5f063ef969c02bd5d175edd3471028",
    "phase4a-external-confirmation-design-freeze-v1": "59f5bed3fd7b385739d08dc088965341a29c2809",
    "phase3d-posthoc-research-boundary-freeze-v1": "f9b11adb5dc3a0c2802703ceb1cbafb060c6f341",
    "phase3c-lstm-factorial-scientific-freeze-v1": "b2064719631736f00bc87446252226d9c743c58b",
    "phase3b-lstm-factorial-protocol-freeze-v1": "42c98ea0f63549ecc8e073352a4fe1247a263aaf",
    "phase3a-multiresource-design-freeze-v1": "70eea336302aebfaaa20c79b1972b1ebb835442c",
    "neural-v2-protocol-freeze-v1": "08697069cf54f4c94cbd2a449b3e2050405328fb",
    "neural-v2-dlinear-scientific-freeze-v1": "2aa7e795fa3c7ccb5657ced43c19eb3e5922a1b6",
    "neural-v2-lstm-scientific-freeze-v1": "2845aafb44ebf2d4541e14f8a4af5c6c6176146a",
    "neural-v2-patchtst-scientific-freeze-v1": "102c05d4eb6e09fea2a0288ec037267b9c6e9569",
    "phase2a-benchmark-protocol-freeze-v1": "0b4269270b0a121f0ba1e19355c6cd24b72abeb5",
    "phase2b1-corrected-deterministic-freeze-v1": "bdc7c9243cb33cbb3fadee7b911810a164d8da43",
}
INVENTORIES = {
    "independent_validation/05_bitbrains_factorial/PHASE4C_V2_SCIENTIFIC_CHECKPOINT_SHA256.csv": "07102b449e3a5e6222f206c4509322a74ddadc1cbafed3dd1341b1ce26f7992b",
    "independent_validation/05_bitbrains_factorial/outputs/scientific_v2/runtime/PHASE4C_V2_EXECUTION_ARTIFACT_SHA256.csv": "42e085403d331bc903afd484582bf4d57c68477513ef6a948c3d40c2c5cf4377",
    "independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_EXECUTION_CORRECTION_SHA256.csv": "e01a6f35050474b328ecf2f88823bbf1114f84857e4162d221330ba0b211bfd4",
    "independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_ARTIFACT_SHA256.csv": "323b5a0ca9ba1a7c0180a4faf973f74676dd6a40f99106ab497ebf51baeb4dc0",
    "independent_validation/05_bitbrains_factorial/PHASE4B_ARTIFACT_SHA256.csv": "4e0de1ce213408c5d3860cca985a4d44669b9b04c0c34aadf72b52bf4d17ddf8",
    "independent_validation/PHASE4A_ARTIFACT_SHA256.csv": "b3fb2186d16fcdd28862a2ba6dd6c76c701d66dc5387ce9aa57bf04b3e1f7cc3",
    "multiresource/05_posthoc_audit/PHASE3D_ARTIFACT_SHA256.csv": "cd3ea3d730e99546e52c55720508685e269bb77017fcde27ecd6cbf0dca2f7a2",
    "multiresource/04_lstm_factorial/PHASE3C_SCIENTIFIC_ARTIFACT_SHA256.csv": "95bbb842f60bbc8c2c1bc11704c413e8e654594476d16c40850a217913c5155e",
    "multiresource/04_lstm_factorial/PHASE3B_ARTIFACT_SHA256.csv": "7e4d5b7dd858ecb79dab0ea3355fad0b029e34a18cbfb15b25d114e1886ead65",
    "multiresource/PHASE3A_ARTIFACT_SHA256.csv": "3bc8472b69aa345a6e9e1917ac90377609b2f1f50bf6167f169c078aabec2ef0",
    "benchmark/neural_v2/NEURAL_V2_ARTIFACT_SHA256.csv": "5af4ae5bc9f275cd658ca0a8ee3a075a4abcd6bbba145ea14ef3e78075d58681",
    "benchmark/neural_v2/DLINEAR_SCIENTIFIC_ARTIFACT_SHA256.csv": "fd4e0fe3a1413c6f9a0b942627858354e736e4beb479f77ef71ae2c3aa46d41a",
    "benchmark/neural_v2/LSTM_SCIENTIFIC_ARTIFACT_SHA256.csv": "d67142e064478670df91470eabca059c67de03766050cdc54f087e158591c88f",
    "benchmark/neural_v2/PATCHTST_SCIENTIFIC_ARTIFACT_SHA256.csv": "59cd587415b43d100ff5e27f76a27b596afe4316e17209ef2bcd624bc37fab58",
    "benchmark/phase2b1_corrected/CORRECTION_ARTIFACT_SHA256.csv": "daa408a710c2db7e4c1cb4199c0aa2b3bf30b550c7eb5aa64cda3ae983dd07db",
}
RAW_TIMETRACK = {
    "data/raw/compute_dataset.csv": "9204c25fe1079a18982f811131910d03f60d075aea29353f4198e434ecbe8904",
    "data/raw/detailed_cpu_cores_dataset.csv": "8630691e51d926269ebdc4f1df5c6848e2e879eafb67aa68958b5667713f708c",
    "data/raw/disk_dataset.csv": "2e4dcc1e2a79380dbba876422e42a6741a08da5cb55c15d29fb63a610d24aa6f",
    "data/raw/network_dataset.csv": "75ffdd7fc260010ad3a4549af3b3978eb1aa7657e5f992969b0c5a58e4fcf1d2",
    "data/raw/packet-loss-dataset.csv": "e586455adbb3561795ad6309c71ea3d8fb650251ec68c19c85ba08d2b4a5eb37",
    "data/raw/throughputs_dataset.csv": "22739d4527c56a15ba11ebf4090dc44138bc5549cea88d0eddc126a70053393f",
}

# These Phase 4C amendment-manifest entries were prospectively replaced by the
# later execution-correction freeze.  Their corrected identities are verified
# independently through PHASE4C_V2_EXECUTION_CORRECTION_SHA256.csv above, so
# requiring the earlier byte identities as well would make the two legitimate
# frozen checkpoints impossible to validate simultaneously.
SUPERSEDED_INVENTORY_ENTRIES = {
    "independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_ARTIFACT_SHA256.csv": {
        "independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_PROTOCOL_VALIDATION.json",
        "independent_validation/05_bitbrains_factorial/protocol_amendment/validate_phase4c_v2_protocol.py",
        "independent_validation/05_bitbrains_factorial/run_phase4c_scientific.py",
        "independent_validation/05_bitbrains_factorial/validate_phase4c_environment.py",
    }
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_inventory(relative: str, expected_hash: str) -> tuple[int, list[str]]:
    path = ROOT / relative
    failures = []
    if sha256(path) != expected_hash:
        failures.append(f"inventory_hash:{relative}")
    rows = list(csv.DictReader(path.open(newline="")))
    for row in rows:
        item_relative = row.get("relative_path") or row.get("path")
        if item_relative in SUPERSEDED_INVENTORY_ENTRIES.get(relative, set()):
            continue
        item = ROOT / item_relative
        size = int(row.get("byte_size") or row.get("size_bytes"))
        if not item.is_file() or item.stat().st_size != size or sha256(item) != row["sha256"]:
            failures.append(f"inventory_entry:{relative}:{item}")
    return len(rows), failures


def recompute_vm(vm_id: str) -> dict[str, object]:
    zero_resource = Counter({resource: 0 for resource in RESOURCE_ORDER})
    zero_trace = Counter({trace: 0 for trace in TRACE_DATASETS})
    failed_partitions = 0
    for trace in TRACE_DATASETS:
        clean = clean_and_segment(read_vm(trace, vm_id))
        folds = build_folds(clean.frame, trace, vm_id, legal_origins_structure_only(clean.frame))
        for fold in folds:
            for phase in ("inner", "final"):
                for length in CONTEXTS:
                    rows = scaler_rows(phase_origins(fold, phase), length)
                    native = clean.frame.loc[rows, list(RESOURCE_ORDER)].to_numpy(float)
                    failed = []
                    for index, resource in enumerate(RESOURCE_ORDER):
                        transformed = transform_resource(native[:, index], resource)
                        q25, q75 = np.quantile(transformed, [0.25, 0.75])
                        if float(q75 - q25) <= 0:
                            zero_resource[resource] += 1; failed.append(resource)
                    if failed:
                        failed_partitions += 1; zero_trace[trace] += 1
    return {"VM_ID": vm_id, "eligible": failed_partitions == 0, "failed_partitions": failed_partitions, "zero_resource": dict(zero_resource), "zero_trace": dict(zero_trace)}


def main() -> None:
    failures = []
    checks: dict[str, object] = {}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != EXPECTED_HEAD:
        failures.append(f"head:{head}")
    tag_results = {}
    for tag, expected in TAGS.items():
        observed = subprocess.check_output(["git", "rev-parse", f"{tag}^{{}}"], cwd=ROOT, text=True).strip()
        tag_results[tag] = observed
        if observed != expected:
            failures.append(f"tag:{tag}")
    checks["frozen_tags"] = {"count": len(tag_results), "status": "PASS" if not any(item.startswith("tag:") for item in failures) else "FAIL"}
    inventory_counts = {}
    for relative, expected_hash in INVENTORIES.items():
        count, found = verify_inventory(relative, expected_hash); failures.extend(found); inventory_counts[relative] = count
    checks["frozen_inventories"] = inventory_counts
    for relative, expected in RAW_TIMETRACK.items():
        if sha256(ROOT / relative) != expected:
            failures.append(f"timetrack_raw:{relative}")
    canonical = sha256(ROOT / "discovery/02_dependency_analysis/outputs/canonical_panel.parquet")
    if canonical != "c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a":
        failures.append("canonical_panel")
    archive_hashes = {
        path.name: sha256(path) for path in sorted((ROOT / "data/external/raw").glob("gwa_t_*.zip"))
    }
    if archive_hashes.get("gwa_t_13_materna.zip") != EXPECTED_ARCHIVE:
        failures.append("materna_archive")
    checks["raw_integrity"] = {"timetrack_raw": "6/6 PASS", "canonical_panel_sha256": canonical, "external_archives": archive_hashes}

    shared, structural_counts = structural_pool()
    eligibility = pd.read_csv(HERE / "TRAINING_SCALE_ELIGIBILITY.csv", dtype={"VM_ID": str})
    workers = min(4, os.cpu_count() or 1)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        recomputed = list(executor.map(recompute_vm, sorted(shared, key=lambda value: int(value)), chunksize=2))
    recomputed_by_id = {row["VM_ID"]: row for row in recomputed}
    for row in eligibility.itertuples(index=False):
        expected = recomputed_by_id[str(row.VM_ID)]
        if bool(row.MATERNA_TEMPORAL_SCALE_ELIGIBLE) != expected["eligible"] or int(row.number_zero_iqr_partitions) != expected["failed_partitions"]:
            failures.append(f"scale_reproduction:{row.VM_ID}")
    eligible_ids = {row["VM_ID"] for row in recomputed if row["eligible"]}
    if len(shared) != 398 or len(eligible_ids) != 74:
        failures.append("structural_or_scale_count")
    checks["scale_eligibility"] = {"structural_common_pool": len(shared), "eligible": len(eligible_ids), "partitions_recomputed": len(shared) * 90}

    candidate = pd.read_csv(HERE / "manifests/CANDIDATE_35_VM_COHORT.csv", dtype={"entity_id": str})
    ranked = sorted((hashlib.sha256(f"phase4a-v1|Materna-shared|{vm}".encode()).hexdigest(), vm) for vm in eligible_ids)[:35]
    if list(candidate.sort_values("rank").entity_id) != [vm for _, vm in ranked]:
        failures.append("candidate_selection")
    support = pd.read_parquet(HERE / "manifests/MATERNA_SUPPORT_MANIFEST.parquet")
    if len(support) != 1575 or support.duplicated(["environment", "vm_id", "fold", "L"]).any():
        failures.append("support_shape")
    reproduced = 0; leakage = 0; mismatch = 0
    selected_scaler_zero = 0; minimum_failures = 0
    minima = json.loads((HERE / "configs/materna_phase4d_preflight.json").read_text())["support_minima"]
    for vm_id in candidate.entity_id:
        for trace in TRACE_DATASETS:
            clean = clean_and_segment(read_vm(trace, vm_id))
            folds = build_folds(clean.frame, trace, vm_id, legal_origins_structure_only(clean.frame))
            timestamps = clean.frame.timestamp_seconds.to_numpy(np.int64)
            for fold in folds:
                group = support[support.environment.eq(trace) & support.vm_id.astype(str).eq(vm_id) & support.fold.eq(fold.fold)]
                if len(group) != 3 or set(group.L) != set(CONTEXTS): mismatch += 1; continue
                for split, minimum in minima.items():
                    values = getattr(fold, split); minimum_failures += int(len(values) < minimum)
                    expected_hash = hashlib.sha256("".join(f"{value}\n" for value in timestamps[values]).encode()).hexdigest()
                    mismatch += int(group[f"{split}_hash"].nunique() != 1 or group[f"{split}_hash"].iloc[0] != expected_hash)
                leakage += int(timestamps[fold.inner_train + max((1,2,4,9,18))].max() >= timestamps[fold.inner_validation[0]])
                leakage += int(timestamps[fold.outer_train + max((1,2,4,9,18))].max() >= timestamps[fold.outer_test[0]])
                for phase in ("inner", "final"):
                    for length in CONTEXTS:
                        rows = scaler_rows(phase_origins(fold, phase), length)
                        native = clean.frame.loc[rows, list(RESOURCE_ORDER)].to_numpy(float)
                        for index, resource in enumerate(RESOURCE_ORDER):
                            q25, q75 = np.quantile(transform_resource(native[:, index], resource), [0.25, 0.75])
                            selected_scaler_zero += int(float(q75 - q25) <= 0)
                reproduced += 3
    if reproduced != 1575 or mismatch or leakage or selected_scaler_zero or minimum_failures:
        failures.append("candidate_support_reproduction")
    checks["support"] = {"records": len(support), "reproduced": reproduced, "mismatches": mismatch, "leakage_violations": leakage, "scale_failures": selected_scaler_zero, "minimum_failures": minimum_failures}

    config = json.loads((HERE / "configs/materna_phase4d_preflight.json").read_text())
    scientific_config_path = HERE / "configs/materna_replication_v1.json"
    scientific_config = json.loads(scientific_config_path.read_text())
    expected_parameters = {"S1": 50757, "S2": 51525, "M1": 52500}
    observed_parameters = {"S1": parameter_count(build_model("S1", 1)), "S2": parameter_count(build_model("S2", 4)), "M1": parameter_count(build_model("M1", 4))}
    if observed_parameters != expected_parameters:
        failures.append("architecture_parameters")
    if config["sample_leads"] != [1,2,4,9,18] or config["contexts"] != [4,9,18] or config["training"] != {"optimizer":"Adam","learning_rate":0.001,"batch_size":256,"max_epochs":50,"patience":7,"gradient_clip":1.0,"seeds":[0,1,2],"M1_loss":"equal_mean_of_four_resource_MSE_losses"}:
        failures.append("protocol_config")
    if sha256(scientific_config_path) != EXPECTED_CONFIG:
        failures.append("scientific_config_hash")
    if scientific_config["archive"]["sha256"] != EXPECTED_ARCHIVE:
        failures.append("scientific_config_archive")
    if scientific_config["population"] != {
        "rule": "structurally eligible in all three Materna traces AND nonzero transformed-resource IQR in every scientific scaler-fit partition across Materna-T1, Materna-T2, and Materna-T3",
        "structural_common_pool": 398,
        "training_scale_eligible": 74,
        "training_scale_rejected": 324,
        "retention_percent": 18.592964824120603,
        "selected_count": 35,
        "selection_key": "phase4a-v1|Materna-shared|<exact-VM-ID>",
        "selected_ids_in_rank_order": list(candidate.sort_values("rank").entity_id),
        "cohort_sha256": "4c9e8f4cfa5cf26c4188924c486cdfbe9d78972eec1f84f5e0f23b1e94353140",
        "selection_record_sha256": "63c1a7266057c4344bfd6211ee7d3fd2deba283e4b41797fc4e412483469b24b",
        "replacement_after_freeze_permitted": False,
    }:
        failures.append("scientific_config_population")
    expected_classification = {
        "unit": "per_trace_and_comparison",
        "BROAD_POSITIVE": {"overall_gain_minimum": 0.01, "positive_horizons_minimum": 4, "positive_VMs_minimum": 25, "positive_folds_minimum": 4, "positive_seeds_minimum": 2, "all_required": True},
        "CONDITIONALLY_POSITIVE": {"overall_gain_strictly_positive": True, "positive_horizons_minimum": 3, "positive_VMs_minimum": 15, "positive_folds_minimum": 3, "positive_seeds_minimum": 2, "exclude_BROAD_POSITIVE": True, "all_required": True},
        "BROAD_NEGATIVE": {"overall_gain_maximum": -0.01, "positive_horizons_maximum": 1, "positive_VMs_maximum": 10, "positive_folds_maximum": 1, "positive_seeds_maximum": 1, "all_required": True},
        "otherwise": "NEUTRAL_OR_MIXED",
        "change_after_execution_permitted": False,
    }
    if scientific_config["classification_rules"] != expected_classification:
        failures.append("scientific_config_classification")
    if scientific_config["horizons"]["sample_leads"] != [1,2,4,9,18] or scientific_config["contexts"]["sample_lengths"] != [4,9,18] or scientific_config["seeds"] != [0,1,2]:
        failures.append("scientific_config_grid")
    if scientific_config["architecture"]["S1"]["parameters_per_model"] != 50757 or scientific_config["architecture"]["S2"]["parameters_per_model"] != 51525 or scientific_config["architecture"]["M1"]["parameters_total"] != 52500:
        failures.append("scientific_config_architecture")
    if scientific_config["publication_role"]["label"] != "SECONDARY_TEMPORAL_REPLICATION" or scientific_config["scientific_execution_authorized_by_this_freeze"]:
        failures.append("scientific_config_role_or_authorization")
    checks["architecture"] = observed_parameters

    timings = pd.read_csv(HERE / "pilot/PILOT_TIMINGS.csv", dtype={"vm_id": str})
    expected_specs = {(trace, formulation, resource if formulation != "M1" else "ALL") for trace in TRACE_DATASETS for formulation in ("S1","S2","M1") for resource in (RESOURCE_ORDER if formulation != "M1" else ("ALL",))}
    observed_specs = set(zip(timings.trace, timings.formulation, timings.target))
    if len(timings) != 27 or observed_specs != expected_specs or set(timings.epochs_trained) != {5} or set(timings.fold) != {1} or set(timings.seed) != {0} or set(timings.L) != {9}:
        failures.append("pilot_identity")
    if timings.outer_test_targets_accessed.astype(bool).any() or timings.outer_test_predictions_generated.astype(bool).any() or timings.scientific_predictive_metrics_computed.astype(bool).any():
        failures.append("pilot_access")
    workload = json.loads((HERE / "outputs/SCIENTIFIC_WORKLOAD.json").read_text())
    if workload["combined_three_trace"] != {"inner_total":42525,"final_total":14175,"fit_total":56700,"metric_rows":94500,"selected_contexts":4725}:
        failures.append("workload")
    checks["pilot"] = {"models": len(timings), "epochs_each": 5, "outer_test_accesses": 0, "scientific_predictive_metrics": 0}
    checks["workload"] = workload

    audit_source = ast.parse((HERE / "run_phase4d_audit.py").read_text())
    audit_imports = {alias.name for node in ast.walk(audit_source) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    if any(name.startswith("torch") or name.endswith("training") or "models" in name for name in audit_imports):
        failures.append("model_code_in_scale_audit")
    forbidden_outputs = [path.relative_to(HERE).as_posix() for path in HERE.rglob("*") if path.is_file() and any(token in path.as_posix().lower() for token in ("scientific_predictions", "scientific_metrics", "model_checkpoints", "outer_test_predictions"))]
    if forbidden_outputs:
        failures.append("scientific_outputs_present")
    inventory = HERE / "PHASE4D_MATERNA_PREFLIGHT_ARTIFACT_SHA256.csv"
    if inventory.exists():
        inventory_result = subprocess.run(
            [sys.executable, str(HERE / "build_phase4d_preflight_inventory.py"), "--verify"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if inventory_result.returncode:
            failures.append("phase4d_artifact_inventory")
    result = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "checks": checks,
        "materna_scientific_forecasting_fits": 0,
        "outer_test_accesses": 0,
        "scientific_predictive_outcomes_inspected": 0,
        "persistence_forecasting_comparisons": 0,
        "new_architectures": 0,
        "phase4c_decisions_modified": 0,
    }
    (HERE / "PHASE4D_MATERNA_PREFLIGHT_VALIDATION.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
