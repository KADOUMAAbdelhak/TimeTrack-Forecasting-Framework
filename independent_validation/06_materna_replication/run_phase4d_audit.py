#!/usr/bin/env python3
"""Phase 4D structural, scale-eligibility, cohort, and support preflight.

This module intentionally imports no model or optimizer code.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import sys
import zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BITBRAINS = ROOT / "independent_validation/05_bitbrains_factorial"
sys.path.insert(0, str(BITBRAINS))

from src import CONTEXTS, LEADS, L_MAX, RESOURCE_ORDER  # noqa: E402
from src.cleaning import clean_and_segment  # noqa: E402
from src.ingestion import RawVM  # noqa: E402
from src.panel import scaler_rows  # noqa: E402
from src.splits import build_folds, manifest_rows  # noqa: E402
from src.transforms import transform_resource  # noqa: E402


CONFIG_PATH = HERE / "configs/materna_phase4d_preflight.json"
ELIGIBILITY_SOURCE = ROOT / "independent_validation/01_dataset_audit/ENTITY_STRUCTURAL_ELIGIBILITY.csv"
PHASE4A_SELECTION = ROOT / "independent_validation/03_evaluation_design/SELECTED_ENTITY_COHORTS.csv"
RAW_ARCHIVE = ROOT / "data/external/raw/gwa_t_13_materna.zip"
OUTPUTS = HERE / "outputs"
MANIFESTS = HERE / "manifests"
TRACE_DATASETS = {
    "Materna-T1": "GWA-T-13_Materna_trace_1",
    "Materna-T2": "GWA-T-13_Materna_trace_2",
    "Materna-T3": "GWA-T-13_Materna_trace_3",
}
TRACE_FOLDERS = {"Materna-T1": "Materna-Trace-1", "Materna-T2": "Materna-Trace-2", "Materna-T3": "Materna-Trace-3"}
POLICY_VERSION = "phase4a-v1"
SELECTION_ENVIRONMENT = "Materna-shared"
EXPECTED_STRUCTURAL = {"Materna-T1": 475, "Materna-T2": 483, "Materna-T3": 495}
EXPECTED_COMMON = 398
PHASE_ORDER = {"inner": 0, "final": 1}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def canonical_hash(value: object) -> str:
    return sha256_text(json.dumps(value, sort_keys=True, separators=(",", ":")))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\t", " ").strip().lower())


def find_column(columns: list[str], *parts: str) -> str:
    matches = [column for column in columns if all(part in normalized(column) for part in parts)]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one column containing {parts}, found {matches}")
    return matches[0]


def required_columns(columns: list[str]) -> dict[str, str]:
    return {
        "timestamp": find_column(columns, "timestamp"),
        "cpu": find_column(columns, "cpu usage", "[%]"),
        "memory": find_column(columns, "memory usage", "[kb]"),
        "disk_write": find_column(columns, "disk write throughput"),
        "received": find_column(columns, "network received throughput"),
        "transmitted": find_column(columns, "network transmitted throughput"),
    }


def numeric(series: pd.Series) -> np.ndarray:
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce").to_numpy(float)


def read_vm(trace: str, vm_id: str) -> RawVM:
    folder = TRACE_FOLDERS[trace].lower()
    with zipfile.ZipFile(RAW_ARCHIVE) as bundle:
        names = sorted(
            name for name in bundle.namelist()
            if name.lower().endswith(".csv")
            and folder in name.lower()
            and Path(name).stem == vm_id
        )
        if len(names) != 1:
            raise RuntimeError(f"Expected one Materna member for {trace}/{vm_id}, found {names}")
        member = names[0]
        payload = bundle.read(member)
    frame = pd.read_csv(io.BytesIO(payload), sep=";", engine="c")
    frame.columns = [column.strip() for column in frame.columns]
    columns = required_columns(list(frame.columns))
    parsed_time = pd.to_datetime(frame[columns["timestamp"]], format="%d.%m.%Y %H:%M:%S", utc=True, errors="coerce")
    if parsed_time.isna().any():
        raise RuntimeError(f"Unparseable Materna timestamp: {trace}/{vm_id}")
    seconds = (
        parsed_time.to_numpy(dtype="datetime64[ns]").astype("int64") // 1_000_000_000
    )
    parsed = pd.DataFrame({
        "timestamp_seconds": seconds,
        "CPU": numeric(frame[columns["cpu"]]),
        "MEMORY": numeric(frame[columns["memory"]]),
        "DISK_WRITE": numeric(frame[columns["disk_write"]]),
        "network_received": numeric(frame[columns["received"]]),
        "network_transmitted": numeric(frame[columns["transmitted"]]),
        "raw_member": member,
    })
    member_record = {
        "environment": trace,
        "vm_id": vm_id,
        "archive_filename": RAW_ARCHIVE.name,
        "member_path": member,
        "member_byte_size": len(payload),
        "member_sha256": hashlib.sha256(payload).hexdigest(),
    }
    return RawVM(trace, vm_id, parsed, [member_record], RAW_ARCHIVE, sha256_file(RAW_ARCHIVE))


def legal_origins_structure_only(frame: pd.DataFrame) -> np.ndarray:
    candidates = np.arange(L_MAX - 1, len(frame) - max(LEADS), dtype=np.int64)
    history = candidates[:, None] - np.arange(L_MAX - 1, -1, -1)
    targets = candidates[:, None] + np.asarray(LEADS)
    segments = frame.segment_id.to_numpy(np.int64)
    keep = np.all(segments[history] == segments[candidates, None], axis=1)
    keep &= np.all(segments[targets] == segments[candidates, None], axis=1)
    return candidates[keep]


def phase_origins(fold: object, phase: str) -> np.ndarray:
    return fold.inner_train if phase == "inner" else fold.outer_train


def structural_pool() -> tuple[set[str], dict[str, int]]:
    source = pd.read_csv(ELIGIBILITY_SOURCE, dtype={"entity": str})
    pools = {}
    for trace, dataset in TRACE_DATASETS.items():
        ids = set(source.loc[source.dataset.eq(dataset) & source.structurally_eligible.astype(bool), "entity"])
        pools[trace] = ids
    counts = {trace: len(ids) for trace, ids in pools.items()}
    if counts != EXPECTED_STRUCTURAL:
        raise RuntimeError(f"Frozen Materna structural counts differ: {counts}")
    shared = set.intersection(*pools.values())
    if len(shared) != EXPECTED_COMMON:
        raise RuntimeError(f"Frozen Materna common pool differs: {len(shared)}")
    return shared, counts


def audit_vm(vm_id: str) -> dict[str, object]:
    zero_by_resource = Counter({resource: 0 for resource in RESOURCE_ORDER})
    zero_by_trace = Counter({trace: 0 for trace in TRACE_DATASETS})
    partition_failures: list[tuple[str, int, str, int, tuple[str, ...]]] = []
    prevalence = Counter()
    total_partitions = 0
    disagreement = 0
    for trace in TRACE_DATASETS:
        clean = clean_and_segment(read_vm(trace, vm_id))
        origins = legal_origins_structure_only(clean.frame)
        folds = build_folds(clean.frame, trace, vm_id, origins)
        for fold in folds:
            for phase in ("inner", "final"):
                fit_origins = phase_origins(fold, phase)
                for length in CONTEXTS:
                    total_partitions += 1
                    rows = scaler_rows(fit_origins, length)
                    native = clean.frame.loc[rows, list(RESOURCE_ORDER)].to_numpy(float)
                    failed_resources = []
                    for index, resource in enumerate(RESOURCE_ORDER):
                        transformed = transform_resource(native[:, index], resource)
                        q25, q75 = np.quantile(transformed, [0.25, 0.75])
                        n25, n75 = np.quantile(native[:, index], [0.25, 0.75])
                        failed = float(q75 - q25) <= 0.0
                        disagreement += int(failed != (float(n75 - n25) <= 0.0))
                        prevalence[(trace, resource, fold.fold, phase, length, "checked")] += 1
                        prevalence[(trace, resource, fold.fold, phase, length, "zero")] += int(failed)
                        if failed:
                            zero_by_resource[resource] += 1
                            failed_resources.append(resource)
                    if failed_resources:
                        zero_by_trace[trace] += 1
                        partition_failures.append((trace, fold.fold, phase, length, tuple(failed_resources)))
    if total_partitions != 90:
        raise RuntimeError(f"Expected 90 scaler partitions for {vm_id}, got {total_partitions}")
    first = min(partition_failures, key=lambda x: (list(TRACE_DATASETS).index(x[0]), x[1], PHASE_ORDER[x[2]], x[3])) if partition_failures else None
    row = {
        "VM_ID": vm_id,
        "structurally_eligible_all_three_traces": True,
        "MATERNA_TEMPORAL_SCALE_ELIGIBLE": not partition_failures,
        "number_scaler_partitions": total_partitions,
        "number_zero_iqr_partitions": len(partition_failures),
        "cpu_zero_iqr_count": zero_by_resource["CPU"],
        "throughput_zero_iqr_count": zero_by_resource["THROUGHPUT"],
        "memory_zero_iqr_count": zero_by_resource["MEMORY"],
        "disk_write_zero_iqr_count": zero_by_resource["DISK_WRITE"],
        "T1_zero_iqr_partition_count": zero_by_trace["Materna-T1"],
        "T2_zero_iqr_partition_count": zero_by_trace["Materna-T2"],
        "T3_zero_iqr_partition_count": zero_by_trace["Materna-T3"],
        "first_failing_trace": first[0] if first else "",
        "first_failing_fold": first[1] if first else "",
        "first_failing_phase": first[2] if first else "",
        "first_failing_L": first[3] if first else "",
        "native_transformed_gate_disagreements": disagreement,
    }
    return {"row": row, "prevalence": dict(prevalence)}


def selection_record_hash(frame: pd.DataFrame) -> str:
    payload = "".join(
        f"{row.rank}\0{row.entity_id}\0{row.selection_key}\0{row.selection_sha256}\n"
        for row in frame.itertuples(index=False)
    )
    return sha256_text(payload)


def select_candidate(eligibility: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    eligible = eligibility.loc[eligibility.MATERNA_TEMPORAL_SCALE_ELIGIBLE, "VM_ID"].astype(str)
    ranked = sorted((sha256_text(f"{POLICY_VERSION}|{SELECTION_ENVIRONMENT}|{vm_id}"), vm_id) for vm_id in eligible)
    chosen = ranked[:35]
    rows = [{
        "cohort_role": "PHASE4D_CANDIDATE_SECONDARY_TEMPORAL_REPLICATION",
        "environment": "GWA-T-13_Materna_shared_all_three",
        "rank": rank,
        "entity_id": vm_id,
        "selection_key": f"{POLICY_VERSION}|{SELECTION_ENVIRONMENT}|{vm_id}",
        "selection_sha256": digest,
        "structurally_eligible_all_three_traces": True,
        "MATERNA_TEMPORAL_SCALE_ELIGIBLE": True,
    } for rank, (digest, vm_id) in enumerate(chosen, 1)]
    selected = pd.DataFrame(rows)
    original = pd.read_csv(PHASE4A_SELECTION, dtype={"entity_id": str})
    original = original[original.environment.eq("GWA-T-13_Materna_shared_all_three")]
    old_ids, new_ids = set(original.entity_id), set(selected.entity_id)
    ordered_ids = selected.sort_values("rank").entity_id
    summary = {
        "starting_structural_common_pool": EXPECTED_COMMON,
        "training_scale_eligible_count": int(len(eligible)),
        "retention_percent": 100.0 * len(eligible) / EXPECTED_COMMON,
        "selected_count": len(selected),
        "original_phase4a_selected_retained": len(old_ids & new_ids),
        "original_phase4a_ids_retained": sorted(old_ids & new_ids, key=int),
        "original_phase4a_ids_replaced": sorted(old_ids - new_ids, key=int),
        "replacement_ids": sorted(new_ids - old_ids, key=int),
        "candidate_id_list_sha256": sha256_text("\n".join(ordered_ids) + "\n"),
        "selection_record_sha256": selection_record_hash(selected),
        "selection_basis": "ascending SHA-256 after structural and scale eligibility filtering",
        "selection_salt": "phase4a-v1|Materna-shared|<exact-VM-ID>",
        "predictive_outcomes_used": 0,
    }
    return selected, summary


def materialize_support(selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    config = json.loads(CONFIG_PATH.read_text())
    minima = config["support_minima"]
    support_rows, scaler_records, segment_rows, failure_rows = [], [], [], []
    zero_iqr = 0
    for selected_row in selected.sort_values("rank").itertuples(index=False):
        vm_id = str(selected_row.entity_id)
        for trace in TRACE_DATASETS:
            clean = clean_and_segment(read_vm(trace, vm_id))
            segment_rows.extend(clean.segments)
            origins = legal_origins_structure_only(clean.frame)
            folds = build_folds(clean.frame, trace, vm_id, origins)
            support_rows.extend(manifest_rows(clean.frame, folds))
            for fold in folds:
                for split, minimum in minima.items():
                    observed = len(getattr(fold, split))
                    if observed < minimum:
                        failure_rows.append({"trace": trace, "VM_ID": vm_id, "fold": fold.fold, "split": split, "observed": observed, "required": minimum})
                for phase in ("inner", "final"):
                    fit_origins = phase_origins(fold, phase)
                    for length in CONTEXTS:
                        rows = scaler_rows(fit_origins, length)
                        native = clean.frame.loc[rows, list(RESOURCE_ORDER)].to_numpy(float)
                        medians, iqrs, native_iqrs = [], [], []
                        for index, resource in enumerate(RESOURCE_ORDER):
                            transformed = transform_resource(native[:, index], resource)
                            q25, median, q75 = np.quantile(transformed, [0.25, 0.5, 0.75])
                            n25, n75 = np.quantile(native[:, index], [0.25, 0.75])
                            medians.append(float(median)); iqrs.append(float(q75 - q25)); native_iqrs.append(float(n75 - n25))
                        zero_iqr += sum(value <= 0 for value in iqrs)
                        timestamp_ids = clean.frame.timestamp_seconds.to_numpy(np.int64)[rows]
                        identity = {
                            "trace": trace, "VM_ID": vm_id, "fold": int(fold.fold), "phase": phase, "L": int(length),
                            "fit_row_count": len(rows),
                            "fit_timestamp_sha256": sha256_text("".join(f"{value}\n" for value in timestamp_ids)),
                            "transformed_medians": medians, "transformed_iqrs": iqrs, "native_iqrs": native_iqrs,
                        }
                        scaler_records.append(identity | {"scaler_partition_sha256": canonical_hash(identity)})
    support = pd.DataFrame(support_rows).sort_values(["environment", "vm_id", "fold", "L"])
    scalers = pd.DataFrame(scaler_records).sort_values(["trace", "VM_ID", "fold", "phase", "L"])
    segments = pd.DataFrame(segment_rows).sort_values(["environment", "vm_id", "segment_id"])
    failures = pd.DataFrame(failure_rows, columns=["trace", "VM_ID", "fold", "split", "observed", "required"])
    split_hash_mismatches = 0
    for (_trace, _vm, _fold), group in support.groupby(["environment", "vm_id", "fold"]):
        for split in ("inner_train", "inner_validation", "outer_train", "outer_test"):
            split_hash_mismatches += int(group[f"{split}_hash"].nunique() != 1)
    summary = {
        "status": "PASS" if len(support) == 1575 and len(scalers) == 3150 and zero_iqr == 0 and len(failures) == 0 and split_hash_mismatches == 0 else "FAIL",
        "support_records": len(support),
        "expected_support_records": 1575,
        "records_by_trace": {key: int(value) for key, value in support.groupby("environment").size().items()},
        "selected_common_vms": int(support.vm_id.astype(str).nunique()),
        "scaler_partitions": len(scalers),
        "expected_scaler_partitions": 3150,
        "zero_iqr_failures": int(zero_iqr),
        "support_minimum_failures": len(failures),
        "formulation_support_mismatches": split_hash_mismatches,
        "segment_count": len(segments),
        "outer_test_target_values_accessed": 0,
        "outer_test_predictions_generated": 0,
    }
    return support, scalers, segments, failures, summary


def main() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    config = json.loads(CONFIG_PATH.read_text())
    if sha256_file(RAW_ARCHIVE) != config["archive"]["sha256"]:
        raise RuntimeError("Materna raw archive SHA-256 mismatch")
    shared, structural_counts = structural_pool()
    workers = min(4, os.cpu_count() or 1)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(audit_vm, sorted(shared, key=lambda value: (int(value) if value.isdigit() else math.inf, value)), chunksize=2))
    eligibility = pd.DataFrame([result["row"] for result in results]).sort_values("VM_ID", key=lambda col: col.map(int)).reset_index(drop=True)
    eligibility.to_csv(HERE / "TRAINING_SCALE_ELIGIBILITY.csv", index=False)
    aggregate = Counter()
    for result in results:
        aggregate.update(result["prevalence"])
    prevalence_rows = []
    for trace in TRACE_DATASETS:
        for resource in RESOURCE_ORDER:
            for fold in range(1, 6):
                for phase in ("inner", "final"):
                    for length in CONTEXTS:
                        checked = aggregate[(trace, resource, fold, phase, length, "checked")]
                        zero = aggregate[(trace, resource, fold, phase, length, "zero")]
                        prevalence_rows.append({
                            "trace": trace, "resource": resource, "fold": fold, "phase": phase, "L": length,
                            "checked_partitions": checked, "zero_iqr_partitions": zero,
                            "zero_iqr_prevalence": zero / checked,
                        })
    prevalence = pd.DataFrame(prevalence_rows)
    prevalence.to_csv(HERE / "ZERO_IQR_PREVALENCE.csv", index=False)
    eligible_count = int(eligibility.MATERNA_TEMPORAL_SCALE_ELIGIBLE.sum())
    if eligible_count < 35:
        summary = {"status": "MATERNA_COHORT_INSUFFICIENT_AFTER_SCALE_FILTER", "structural_common_pool": len(shared), "training_scale_eligible_count": eligible_count}
        write_json(OUTPUTS / "TRAINING_SCALE_ELIGIBILITY_SUMMARY.json", summary)
        print(json.dumps(summary, indent=2)); raise SystemExit(2)
    selected, cohort_summary = select_candidate(eligibility)
    selected.to_csv(MANIFESTS / "CANDIDATE_35_VM_COHORT.csv", index=False)
    write_json(MANIFESTS / "CANDIDATE_35_VM_COHORT_SUMMARY.json", cohort_summary)
    support, scalers, segments, failures, support_summary = materialize_support(selected)
    support.to_parquet(MANIFESTS / "MATERNA_SUPPORT_MANIFEST.parquet", index=False, compression="zstd")
    support[[column for column in support if not column.endswith("_origin_ids")]].to_csv(MANIFESTS / "MATERNA_SUPPORT_SUMMARY.csv", index=False)
    scalers.to_csv(MANIFESTS / "MATERNA_SCALER_PARTITIONS.csv", index=False)
    segments.to_csv(MANIFESTS / "MATERNA_SEGMENT_SUMMARY.csv", index=False)
    failures.to_csv(MANIFESTS / "MATERNA_SUPPORT_FAILURES.csv", index=False)
    write_json(MANIFESTS / "MATERNA_SUPPORT_VALIDATION.json", support_summary)
    resource_failures = {resource: int(eligibility[f"{resource.lower()}_zero_iqr_count"].sum()) for resource in RESOURCE_ORDER}
    trace_failures = {trace: int(eligibility[f"T{index}_zero_iqr_partition_count"].sum()) for index, trace in enumerate(TRACE_DATASETS, 1)}
    summary = {
        "status": "PASS" if support_summary["status"] == "PASS" else "FAIL",
        "archive_sha256": sha256_file(RAW_ARCHIVE),
        "structural_counts": structural_counts,
        "structural_common_pool": len(shared),
        "unique_scaler_partition_key": ["trace", "VM_ID", "fold", "phase", "L"],
        "partitions_per_vm": 90,
        "partitions_checked": int(len(shared) * 90),
        "resource_partition_cells_checked": int(len(shared) * 90 * 4),
        "training_scale_eligible_count": eligible_count,
        "training_scale_rejected_count": len(shared) - eligible_count,
        "retention_percent": 100.0 * eligible_count / len(shared),
        "vms_with_any_zero_iqr": int((eligibility.number_zero_iqr_partitions > 0).sum()),
        "zero_iqr_resource_cell_failures_by_resource": resource_failures,
        "zero_iqr_partitions_by_trace": trace_failures,
        "native_transformed_gate_disagreements": int(eligibility.native_transformed_gate_disagreements.sum()),
        "candidate_cohort": cohort_summary,
        "candidate_support": support_summary,
        "scientific_forecasting_fits": 0,
        "outer_test_target_accesses": 0,
        "scientific_predictive_outcomes_inspected": 0,
    }
    write_json(OUTPUTS / "TRAINING_SCALE_ELIGIBILITY_SUMMARY.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
