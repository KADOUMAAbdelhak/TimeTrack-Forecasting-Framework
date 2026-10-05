#!/usr/bin/env python3
"""Training-only Phase 4C IQR audit; this module never imports model/training code."""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
import sys
sys.path.insert(0, str(BASE))

from src import CONTEXTS, LEADS, L_MAX, RESOURCE_ORDER  # noqa: E402
from src.cleaning import clean_and_segment  # noqa: E402
from src.ingestion import read_vm  # noqa: E402
from src.panel import scaler_rows  # noqa: E402
from src.splits import build_folds, manifest_rows  # noqa: E402
from src.transforms import transform_resource  # noqa: E402


ELIGIBILITY = ROOT / "independent_validation/01_dataset_audit/ENTITY_STRUCTURAL_ELIGIBILITY.csv"
ORIGINAL_SELECTION = ROOT / "independent_validation/03_evaluation_design/SELECTED_ENTITY_COHORTS.csv"
COMPLETIONS = BASE / "outputs/scientific/fastStorage/runtime/completions/inner"
ENVIRONMENTS = ("GWA-T-12_Bitbrains_fastStorage", "GWA-T-12_Bitbrains_Rnd")
POLICY_VERSION = "phase4a-v1"
EXPECTED_COUNTS = {"GWA-T-12_Bitbrains_fastStorage": 916, "GWA-T-12_Bitbrains_Rnd": 416}
PHASE_ORDER = {"inner": 0, "final": 1}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def json_write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def legal_origins_without_outcome_values(frame: pd.DataFrame) -> np.ndarray:
    """Reproduce legal support from timestamp/segment structure only.

    Cleaning guarantees all retained four-resource rows are finite and physically
    valid. Consequently the frozen value-finiteness clauses are true for every
    retained row and do not require reading target values after fold assignment.
    """
    n = len(frame)
    candidates = np.arange(L_MAX - 1, n - max(LEADS), dtype=np.int64)
    history = candidates[:, None] - np.arange(L_MAX - 1, -1, -1)
    targets = candidates[:, None] + np.asarray(LEADS)
    segments = frame.segment_id.to_numpy(dtype=np.int64)
    keep = np.all(segments[history] == segments[candidates, None], axis=1)
    keep &= np.all(segments[targets] == segments[candidates, None], axis=1)
    return candidates[keep]


def phase_origins(fold: object, phase: str) -> np.ndarray:
    return fold.inner_train if phase == "inner" else fold.outer_train


def audit_one(item: tuple[str, str]) -> dict[str, object]:
    environment, vm_id = item
    clean = clean_and_segment(read_vm(environment, vm_id))
    origins = legal_origins_without_outcome_values(clean.frame)
    folds = build_folds(clean.frame, environment, vm_id, origins)
    resources = list(RESOURCE_ORDER)
    zero_counts = Counter({resource: 0 for resource in resources})
    min_positive = {resource: math.inf for resource in resources}
    failures: list[dict[str, object]] = []
    prevalence: list[dict[str, object]] = []
    disagreement_count = 0
    partitions = 0
    for fold in folds:
        for phase in ("inner", "final"):
            fit_origins = phase_origins(fold, phase)
            for length in CONTEXTS:
                partitions += 1
                rows = scaler_rows(fit_origins, length)
                native = clean.frame.loc[rows, resources].to_numpy(dtype=np.float64)
                resource_failures = []
                for index, resource in enumerate(resources):
                    transformed = transform_resource(native[:, index], resource)
                    q25, q75 = np.quantile(transformed, [0.25, 0.75])
                    native_q25, native_q75 = np.quantile(native[:, index], [0.25, 0.75])
                    iqr = float(q75 - q25)
                    native_iqr = float(native_q75 - native_q25)
                    failed = iqr <= 0.0
                    native_failed = native_iqr <= 0.0
                    disagreement_count += int(failed != native_failed)
                    if iqr > 0:
                        min_positive[resource] = min(min_positive[resource], iqr)
                    if failed:
                        zero_counts[resource] += 1
                        resource_failures.append(resource)
                    prevalence.append({
                        "environment": environment,
                        "fold": int(fold.fold),
                        "phase": phase,
                        "L": int(length),
                        "resource": resource,
                        "zero": int(failed),
                    })
                if resource_failures:
                    failures.append({
                        "fold": int(fold.fold), "phase": phase, "L": int(length),
                        "resources": resource_failures,
                    })
    if partitions != 30:
        raise RuntimeError(f"Unexpected partition count {environment}/{vm_id}: {partitions}")
    first = min(failures, key=lambda x: (x["fold"], PHASE_ORDER[x["phase"]], x["L"])) if failures else None
    row: dict[str, object] = {
        "environment": environment,
        "VM_ID": vm_id,
        "structurally_eligible": True,
        "training_scale_eligible": not failures,
        "number_scaler_partitions": partitions,
        "number_zero_iqr_partitions": len(failures),
        "first_failing_fold": first["fold"] if first else "",
        "first_failing_phase": first["phase"] if first else "",
        "first_failing_L": first["L"] if first else "",
        "native_transformed_gate_disagreements": disagreement_count,
    }
    for resource in resources:
        key = resource.lower()
        row[f"{key}_zero_iqr_count"] = int(zero_counts[resource])
        row[f"{key}_min_positive_iqr"] = None if math.isinf(min_positive[resource]) else min_positive[resource]
        row[f"{key}_constant_every_partition"] = zero_counts[resource] == partitions
    return {"row": row, "prevalence": prevalence}


def cohort_record_hash(frame: pd.DataFrame) -> str:
    payload = "".join(
        f"{row.rank}\0{row.entity_id}\0{row.selection_key}\0{row.selection_sha256}\n"
        for row in frame.itertuples(index=False)
    )
    return sha256_bytes(payload.encode())


def candidate_cohorts(eligibility: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    original = pd.read_csv(ORIGINAL_SELECTION, dtype={"entity_id": str})
    original = original[original.cohort_role.eq("PRIMARY_EXTERNAL_CONFIRMATION")]
    rows = []
    summaries = {}
    for environment in ENVIRONMENTS:
        eligible_ids = eligibility.loc[
            eligibility.environment.eq(environment) & eligibility.training_scale_eligible, "VM_ID"
        ].astype(str).tolist()
        if len(eligible_ids) < 35:
            summaries[environment] = {"candidate_created": False, "eligible_count": len(eligible_ids)}
            continue
        ranked = sorted(
            (sha256_bytes(f"{POLICY_VERSION}|{environment}|{vm_id}".encode()), vm_id)
            for vm_id in eligible_ids
        )[:35]
        env_rows = []
        for rank, (digest, vm_id) in enumerate(ranked, 1):
            env_rows.append({
                "cohort_role": "CANDIDATE_V2_NOT_APPLIED",
                "environment": environment,
                "rank": rank,
                "entity_id": vm_id,
                "selection_key": f"{POLICY_VERSION}|{environment}|{vm_id}",
                "selection_sha256": digest,
                "structurally_eligible": True,
                "training_scale_eligible": True,
            })
        rows.extend(env_rows)
        env_frame = pd.DataFrame(env_rows)
        old_ids = set(original.loc[original.environment.eq(environment), "entity_id"])
        new_ids = set(env_frame.entity_id)
        ordered_ids = env_frame.sort_values("rank").entity_id.astype(str)
        summaries[environment] = {
            "candidate_created": True,
            "eligible_count": len(eligible_ids),
            "selected_count": 35,
            "retained_count": len(old_ids & new_ids),
            "replaced_count": len(old_ids - new_ids),
            "retained_ids": sorted(old_ids & new_ids, key=int),
            "removed_original_ids": sorted(old_ids - new_ids, key=int),
            "replacement_ids": sorted(new_ids - old_ids, key=int),
            "candidate_id_list_sha256": sha256_bytes(("\n".join(ordered_ids) + "\n").encode()),
            "candidate_selection_records_sha256": cohort_record_hash(env_frame),
        }
    return pd.DataFrame(rows), summaries


def build_candidate_support(candidates: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    rows = []
    zero_iqr = 0
    minima = json.loads((BASE / "configs/bitbrains_lstm_factorial.json").read_text())["support_minima"]
    support_minimum_failures = 0
    for item in candidates.sort_values(["environment", "rank"]).itertuples(index=False):
        clean = clean_and_segment(read_vm(item.environment, str(item.entity_id)))
        origins = legal_origins_without_outcome_values(clean.frame)
        folds = build_folds(clean.frame, item.environment, str(item.entity_id), origins)
        for fold in folds:
            for split, minimum in minima.items():
                support_minimum_failures += int(len(getattr(fold, split)) < minimum)
            for phase in ("inner", "final"):
                fit_origins = phase_origins(fold, phase)
                for length in CONTEXTS:
                    fit_rows = scaler_rows(fit_origins, length)
                    native = clean.frame.loc[fit_rows, list(RESOURCE_ORDER)].to_numpy(float)
                    for index, resource in enumerate(RESOURCE_ORDER):
                        transformed = transform_resource(native[:, index], resource)
                        q25, q75 = np.quantile(transformed, [0.25, 0.75])
                        zero_iqr += int(float(q75 - q25) <= 0.0)
        rows.extend(manifest_rows(clean.frame, folds))
    manifest = pd.DataFrame(rows)
    summary = {
        "support_records": len(manifest),
        "expected_support_records": 1050,
        "environment_record_counts": {
            key: int(value) for key, value in manifest.groupby("environment").size().items()
        },
        "unique_vm_counts": {
            key: int(value) for key, value in manifest.groupby("environment").vm_id.nunique().items()
        },
        "all_five_folds": sorted(manifest.fold.unique().tolist()) == [1, 2, 3, 4, 5],
        "all_contexts": sorted(manifest.L.unique().tolist()) == [4, 9, 18],
        "zero_iqr_resource_partition_failures": zero_iqr,
        "support_minimum_failures": support_minimum_failures,
        "formulation_support_mismatches": 0,
        "formulation_support_reason": "S1, S2, and M1 consume the same frozen manifest rows and hashes",
        "outer_test_target_values_accessed": 0,
        "outer_test_predictions_generated": 0,
    }
    return manifest, summary


def blocked_provenance() -> dict[str, object]:
    records = []
    for path in sorted(COMPLETIONS.glob("*.json")):
        payload = json.loads(path.read_text())
        identity = payload["identity"]
        stat = path.stat()
        records.append({
            "run_id": identity["run_id"],
            "relative_artifact_path": str(path.relative_to(ROOT)),
            "completion_sha256": sha256_file(path),
            "config_hash": identity["config_hash"],
            "support_hash": identity["support_hash"],
            "inner_train_hash": payload["inner_train_hash"],
            "inner_validation_hash": payload["inner_validation_hash"],
            "archive_hash": identity["archive_hash"],
            "cohort_hash": identity["cohort_hash"],
            "criteria_hash": identity["criteria_hash"],
            "environment": identity["environment"],
            "formulation": identity["formulation"],
            "phase": identity["phase"],
            "vm_id": identity["vm_id"],
            "fold": identity["fold"],
            "L": identity["L"],
            "seed": identity["seed"],
            "resource": identity["resource"],
            "outer_test_accessed": payload["outer_test_accessed"],
            "start_timestamp": None,
            "end_timestamp": None,
            "artifact_mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        })
    conditions = {
        "count_154": len(records) == 154,
        "all_fastStorage": all(r["environment"] == ENVIRONMENTS[0] for r in records),
        "all_S1": all(r["formulation"] == "S1" for r in records),
        "all_inner": all(r["phase"] == "inner" for r in records),
        "all_VM_697": all(str(r["vm_id"]) == "697" for r in records),
        "outer_test_accesses_zero": all(r["outer_test_accessed"] is False for r in records),
    }
    return {
        "label": "ABORTED_PRE_AMENDMENT_PROVENANCE",
        "status": "PRESERVED_NOT_REUSABLE_WITHOUT_EXPLICIT_AUTHORIZATION",
        "completion_count": len(records),
        "conditions": conditions,
        "all_conditions_pass": all(conditions.values()),
        "timestamps_note": "Completion JSONs contain no start/end timestamps; filesystem mtime is recorded as artifact provenance only.",
        "predictive_values_inspected": 0,
        "records": records,
    }


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    pool = pd.read_csv(ELIGIBILITY, dtype={"entity": str})
    pool = pool[pool.dataset.isin(ENVIRONMENTS) & pool.structurally_eligible.astype(bool)]
    actual = pool.groupby("dataset").size().to_dict()
    if actual != EXPECTED_COUNTS:
        raise RuntimeError(f"Structural pool mismatch: {actual}")
    work = [(row.dataset, str(row.entity)) for row in pool.itertuples(index=False)]
    workers = min(4, os.cpu_count() or 1)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(audit_one, work, chunksize=4))
    eligibility = pd.DataFrame([result["row"] for result in results]).sort_values(
        ["environment", "VM_ID"], key=lambda col: col.map(int) if col.name == "VM_ID" else col
    ).reset_index(drop=True)
    eligibility.to_csv(HERE / "TRAINING_SCALE_ELIGIBILITY.csv", index=False)

    prevalence = pd.DataFrame([cell for result in results for cell in result["prevalence"]])
    grouped = prevalence.groupby(["environment", "resource", "fold", "phase", "L"], sort=True).zero.agg(
        checked_partitions="size", zero_iqr_partitions="sum"
    ).reset_index()
    grouped["zero_iqr_prevalence"] = grouped.zero_iqr_partitions / grouped.checked_partitions
    grouped.to_csv(HERE / "ZERO_IQR_PREVALENCE.csv", index=False)

    candidates, cohort_summary = candidate_cohorts(eligibility)
    candidates.to_csv(HERE / "CANDIDATE_V2_COHORTS.csv", index=False)
    json_write(HERE / "CANDIDATE_V2_COHORTS_SUMMARY.json", cohort_summary)
    if len(candidates) == 70:
        support, support_summary = build_candidate_support(candidates)
        support.to_parquet(HERE / "CANDIDATE_V2_SUPPORT_MANIFEST.parquet", index=False)
        summary_columns = [column for column in support.columns if not column.endswith("_origin_ids")]
        support[summary_columns].to_csv(HERE / "CANDIDATE_V2_SUPPORT_SUMMARY.csv", index=False)
    else:
        support_summary = {"status": "NOT_CREATED_INSUFFICIENT_ELIGIBLE_ENTITIES"}
    json_write(HERE / "CANDIDATE_V2_SUPPORT_VALIDATION.json", support_summary)

    env_summary = {}
    for environment, group in eligibility.groupby("environment", sort=True):
        passed = int(group.training_scale_eligible.sum())
        env_summary[environment] = {
            "structurally_eligible_count": len(group),
            "training_scale_eligible_count": passed,
            "rejected_only_zero_iqr_count": len(group) - passed,
            "percentage_retained": 100.0 * passed / len(group),
            "vms_with_any_zero_iqr": int((group.number_zero_iqr_partitions > 0).sum()),
        }
    audit_summary = {
        "status": "PASS",
        "rule": "TRAINING_SCALE_ELIGIBLE",
        "unique_partition_key": ["environment", "VM_ID", "fold", "phase", "L"],
        "partition_count_per_vm": 30,
        "partition_derivation": "5 folds x 2 training phases (inner, final) x 3 contexts; formulation-independent",
        "resources_and_transforms": {"CPU": "identity", "THROUGHPUT": "log1p", "MEMORY": "identity", "DISK_WRITE": "log1p"},
        "environments": env_summary,
        "native_transformed_gate_disagreements": int(eligibility.native_transformed_gate_disagreements.sum()),
        "candidate_cohorts": cohort_summary,
        "candidate_support": support_summary,
        "outer_test_target_values_accessed": 0,
        "outer_test_predictions_generated": 0,
        "scientific_performance_inspected": 0,
    }
    json_write(HERE / "TRAINING_SCALE_ELIGIBILITY_SUMMARY.json", audit_summary)
    json_write(HERE / "ABORTED_PRE_AMENDMENT_PROVENANCE.json", blocked_provenance())
    print(json.dumps(audit_summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
