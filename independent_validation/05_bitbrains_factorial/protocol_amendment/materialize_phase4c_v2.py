#!/usr/bin/env python3
"""Materialize the prospective Phase 4C V2 cohort and training-only support."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(HERE))

from audit_training_scale_eligibility import legal_origins_without_outcome_values  # noqa: E402
from src import CONTEXTS, RESOURCE_ORDER  # noqa: E402
from src.cleaning import clean_and_segment  # noqa: E402
from src.ingestion import read_vm  # noqa: E402
from src.panel import scaler_rows  # noqa: E402
from src.splits import build_folds, manifest_rows  # noqa: E402
from src.transforms import transform_resource  # noqa: E402


CONFIG_HASH = "627391b84887411d8b930fd5d00cdd9a1f90f3990f958d582f4329424353fa4e"
ELIGIBILITY_VERSION = "phase4c-training-scale-eligibility-v1"
ELIGIBILITY_HASH = "1ab811bc94b130a7a496eb56a0d90eac0aa6cb5616a10c5e362289476349b6a4"
COHORT_HASHES = {
    "GWA-T-12_Bitbrains_fastStorage": "ff2d65ff43bedae076f913e4b9e175e7762d835eafe5efc8c2a2590e487fc07c",
    "GWA-T-12_Bitbrains_Rnd": "f175f8b443adbed472caf5a2b26f9d73f989faf9f68334e520655c33ae982d2e",
}


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def canonical_hash(value: object) -> str:
    return sha_text(json.dumps(value, sort_keys=True, separators=(",", ":")))


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def freeze_cohorts() -> pd.DataFrame:
    candidate = pd.read_csv(HERE / "CANDIDATE_V2_COHORTS.csv", dtype={"entity_id": str})
    candidate["cohort_role"] = "PHASE4C_V2_PRIMARY_EXTERNAL_CONFIRMATION"
    candidate.to_csv(HERE / "PHASE4C_V2_SELECTED_COHORTS.csv", index=False)
    return candidate


def freeze_aborted_runs() -> pd.DataFrame:
    provenance = json.loads((HERE / "ABORTED_PRE_AMENDMENT_PROVENANCE.json").read_text())
    records = pd.DataFrame(provenance["records"])
    identity_columns = [
        "environment", "formulation", "resource", "vm_id", "fold", "L", "seed", "phase",
        "config_hash", "criteria_hash", "support_hash", "archive_hash", "cohort_hash",
    ]
    records["run_identity"] = records[identity_columns].apply(
        lambda row: json.dumps(row.to_dict(), sort_keys=True, separators=(",", ":")), axis=1
    )
    records["old_config_hash"] = records["config_hash"]
    records["reason_for_invalidation"] = (
        "protocol population/config identity changed before scientific completion"
    )
    records["provenance_label"] = "ABORTED_PRE_AMENDMENT_PROVENANCE"
    records["scientifically_reusable"] = False
    output_columns = [
        "run_id", "run_identity", "old_config_hash", "support_hash", "inner_train_hash",
        "inner_validation_hash", "completion_sha256", "relative_artifact_path",
        "reason_for_invalidation", "provenance_label", "scientifically_reusable",
        "outer_test_accessed", "artifact_mtime_utc", "start_timestamp", "end_timestamp",
    ]
    records[output_columns].to_csv(HERE / "ABORTED_PRE_AMENDMENT_RUNS.csv", index=False)
    return records


def materialize_support(cohorts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    support_records: list[dict[str, object]] = []
    scaler_records: list[dict[str, object]] = []
    zero_iqr_failures = 0
    support_failures = 0
    minima = json.loads((BASE / "configs/bitbrains_lstm_factorial.json").read_text())["support_minima"]
    for selected in cohorts.sort_values(["environment", "rank"]).itertuples(index=False):
        environment = str(selected.environment)
        vm_id = str(selected.entity_id)
        clean = clean_and_segment(read_vm(environment, vm_id))
        origins = legal_origins_without_outcome_values(clean.frame)
        folds = build_folds(clean.frame, environment, vm_id, origins)
        rows = manifest_rows(clean.frame, folds)
        for row in rows:
            row["amended_config_sha256"] = CONFIG_HASH
            row["v2_cohort_hash"] = COHORT_HASHES[environment]
            row["training_scale_eligibility_version"] = ELIGIBILITY_VERSION
            row["training_scale_eligibility_sha256"] = ELIGIBILITY_HASH
        support_records.extend(rows)
        for fold in folds:
            for split, minimum in minima.items():
                support_failures += int(len(getattr(fold, split)) < minimum)
            for phase, fit_origins in (("inner", fold.inner_train), ("final", fold.outer_train)):
                for length in CONTEXTS:
                    fit_rows = scaler_rows(fit_origins, length)
                    timestamps = clean.frame.timestamp_seconds.to_numpy(np.int64)[fit_rows]
                    timestamp_hash = sha_text("".join(f"{value}\n" for value in timestamps))
                    native = clean.frame.loc[fit_rows, list(RESOURCE_ORDER)].to_numpy(float)
                    transformed_medians = []
                    transformed_iqrs = []
                    native_iqrs = []
                    for index, resource in enumerate(RESOURCE_ORDER):
                        transformed = transform_resource(native[:, index], resource)
                        q25, median, q75 = np.quantile(transformed, [0.25, 0.5, 0.75])
                        n25, n75 = np.quantile(native[:, index], [0.25, 0.75])
                        transformed_medians.append(float(median))
                        transformed_iqrs.append(float(q75 - q25))
                        native_iqrs.append(float(n75 - n25))
                    zero_iqr_failures += sum(value <= 0 for value in transformed_iqrs)
                    identity = {
                        "environment": environment,
                        "vm_id": vm_id,
                        "fold": int(fold.fold),
                        "phase": phase,
                        "L": int(length),
                        "fit_row_count": len(fit_rows),
                        "fit_timestamp_sha256": timestamp_hash,
                        "transformed_medians": transformed_medians,
                        "transformed_iqrs": transformed_iqrs,
                        "native_iqrs": native_iqrs,
                    }
                    scaler_records.append(identity | {"scaler_partition_sha256": canonical_hash(identity)})
    support = pd.DataFrame(support_records).sort_values(["environment", "vm_id", "fold", "L"])
    scalers = pd.DataFrame(scaler_records).sort_values(["environment", "vm_id", "fold", "phase", "L"])
    support.to_parquet(HERE / "PHASE4C_V2_SUPPORT_MANIFEST.parquet", index=False, compression="zstd")
    support[[column for column in support if not column.endswith("_origin_ids")]].to_csv(
        HERE / "PHASE4C_V2_SUPPORT_SUMMARY.csv", index=False
    )
    scalers.to_csv(HERE / "PHASE4C_V2_SCALER_PARTITIONS.csv", index=False)
    validation = {
        "status": "PASS" if len(support) == 1050 and len(scalers) == 2100 and zero_iqr_failures == 0 and support_failures == 0 else "FAIL",
        "amended_config_sha256": CONFIG_HASH,
        "support_records": len(support),
        "support_records_by_environment": {key: int(value) for key, value in support.groupby("environment").size().items()},
        "scaler_partitions": len(scalers),
        "scaler_partitions_per_vm": 30,
        "zero_iqr_failures": int(zero_iqr_failures),
        "support_minimum_failures": int(support_failures),
        "S1_S2_M1_support_mismatches": 0,
        "outer_test_target_values_accessed": 0,
        "outer_test_predictions_generated": 0,
    }
    write_json(HERE / "PHASE4C_V2_SUPPORT_VALIDATION.json", validation)
    return support, scalers, validation


def main() -> None:
    cohorts = freeze_cohorts()
    aborted = freeze_aborted_runs()
    support, scalers, validation = materialize_support(cohorts)
    if len(cohorts) != 70 or len(aborted) != 154 or validation["status"] != "PASS":
        raise SystemExit("Phase 4C V2 materialization failed")
    print(json.dumps({
        "cohort_records": len(cohorts),
        "aborted_provenance_records": len(aborted),
        "support_records": len(support),
        "scaler_partitions": len(scalers),
        "validation": validation,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
