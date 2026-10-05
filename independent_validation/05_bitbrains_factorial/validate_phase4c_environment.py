#!/usr/bin/env python3
"""Technical-only gate for one completed Phase 4C environment."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from run_phase4c_scientific import (
    AMENDMENT_DECISION_HASH,
    ARCHIVE_HASHES,
    BASE,
    COHORT_HASHES,
    CONFIG_HASH,
    CONTEXTS,
    CRITERIA_HASH,
    ENVIRONMENTS,
    EXECUTION_CORRECTION_HASH,
    OUT,
    PHASE4B_DECISION_HASH,
    RESOURCE_ORDER,
    SCIENTIFIC_RELATIVE_ROOT,
    SEEDS,
    TRAINING_SCALE_ELIGIBILITY_HASH,
    TRAINING_SCALE_ELIGIBILITY_VERSION,
    completion_path,
    digest,
    run_identity,
    split_hash,
    vm_data,
)
from src.selection import SelectionRow, select_context
from src.training import fit_final_fixed_epochs, fit_inner
from src.validation import atomic_json_write


EXPECTED = {
    "inner": {"S1": 6_300, "S2": 6_300, "M1": 1_575},
    "final": {"S1": 2_100, "S2": 2_100, "M1": 525},
    "metrics": {"S1": 10_500, "S2": 10_500, "M1": 10_500},
    "selected_contexts": {"S1": 700, "S2": 700, "M1": 175},
}


def relative_hash(path_value: str) -> tuple[Path, str]:
    path = BASE / path_value
    return path, digest(path) if path.is_file() else "MISSING"


def read_records(directory: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(directory.glob("*.json")):
        try:
            records.append(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError) as error:
            records.append({"status": "invalid", "path": str(path), "error": str(error)})
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", choices=tuple(ENVIRONMENTS), required=True)
    args = parser.parse_args()
    key = args.environment
    environment = ENVIRONMENTS[key]
    env_dir = OUT / key
    failures: list[str] = []
    checks: dict[str, Any] = {
        "environment": environment,
        "environment_key": key,
        "scientific_analysis_performed": False,
        "scientific_metric_values_inspected": False,
    }

    identities = {
        "config_sha256": digest(BASE / "configs/bitbrains_lstm_factorial_phase4c_v2.json"),
        "phase4b_decision_sha256": digest(BASE / "EXTERNAL_FACTORIAL_DECISION.md"),
        "criteria_sha256": digest(BASE / "EXTERNAL_SCIENTIFIC_DECISION_CRITERIA.md"),
        "archive_sha256": ARCHIVE_HASHES[key],
        "cohort_sha256": COHORT_HASHES[key],
        "amendment_decision_sha256": digest(BASE / "protocol_amendment/PHASE4C_PROTOCOL_AMENDMENT_DECISION.md"),
        "training_scale_eligibility_sha256": digest(BASE / "protocol_amendment/TRAINING_SCALE_ELIGIBILITY.csv"),
    }
    checks["identities"] = identities
    if identities["config_sha256"] != CONFIG_HASH:
        failures.append("config_hash")
    if identities["phase4b_decision_sha256"] != PHASE4B_DECISION_HASH:
        failures.append("phase4b_decision_hash")
    if identities["criteria_sha256"] != CRITERIA_HASH:
        failures.append("criteria_hash")
    if identities["amendment_decision_sha256"] != AMENDMENT_DECISION_HASH:
        failures.append("amendment_decision_hash")
    if identities["training_scale_eligibility_sha256"] != TRAINING_SCALE_ELIGIBILITY_HASH:
        failures.append("training_scale_eligibility_hash")

    inner = read_records(env_dir / "runtime/completions/inner")
    final = read_records(env_dir / "runtime/completions/final")
    if any(row.get("status") != "complete" for row in inner + final):
        failures.append("noncomplete_or_invalid_completion")
    inner_ids = [row.get("identity", {}).get("run_id") for row in inner]
    final_ids = [row.get("identity", {}).get("run_id") for row in final]
    if len(inner_ids) != len(set(inner_ids)):
        failures.append("duplicate_inner_run_id")
    if len(final_ids) != len(set(final_ids)):
        failures.append("duplicate_final_run_id")

    inner_counts = {
        formulation: sum(row.get("identity", {}).get("formulation") == formulation for row in inner)
        for formulation in ("S1", "S2", "M1")
    }
    final_counts = {
        formulation: sum(row.get("identity", {}).get("formulation") == formulation for row in final)
        for formulation in ("S1", "S2", "M1")
    }
    metric_counts = {
        formulation: sum(
            len(row.get("metrics", []))
            for row in final
            if row.get("identity", {}).get("formulation") == formulation
        )
        for formulation in ("S1", "S2", "M1")
    }
    checks["counts"] = {
        "inner": inner_counts,
        "final": final_counts,
        "metrics": metric_counts,
        "total_fits": len(inner) + len(final),
    }
    if inner_counts != EXPECTED["inner"]:
        failures.append(f"inner_counts:{inner_counts}")
    if final_counts != EXPECTED["final"]:
        failures.append(f"final_counts:{final_counts}")
    if metric_counts != EXPECTED["metrics"]:
        failures.append(f"metric_counts:{metric_counts}")

    lookup: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in inner:
        identity = row.get("identity", {})
        if (
            identity.get("environment") != environment
            or identity.get("config_hash") != CONFIG_HASH
            or identity.get("criteria_hash") != CRITERIA_HASH
            or identity.get("archive_hash") != ARCHIVE_HASHES[key]
            or identity.get("cohort_hash") != COHORT_HASHES[key]
            or identity.get("phase4c_amendment_decision_hash") != AMENDMENT_DECISION_HASH
            or identity.get("training_scale_eligibility_version") != TRAINING_SCALE_ELIGIBILITY_VERSION
            or identity.get("training_scale_eligibility_hash") != TRAINING_SCALE_ELIGIBILITY_HASH
            or row.get("outer_test_accessed") is not False
            or row.get("execution_correction_sha256") != EXECUTION_CORRECTION_HASH
            or row.get("scaler_fit_split") != "inner_train_only"
        ):
            failures.append(f"inner_identity_or_leakage:{identity.get('run_id')}")
            continue
        target = identity.get("resource")
        expected_shape = (4, 5) if identity.get("formulation") == "M1" else (5,)
        if np.asarray(row.get("validation_nmae")).shape != expected_shape:
            failures.append(f"inner_objective_shape:{identity.get('run_id')}")
        clean, folds = vm_data(key, str(identity["vm_id"]))
        fold = folds[int(identity["fold"]) - 1]
        expected_support = split_hash(fold, "inner_train", "inner_validation")
        expected_identity = run_identity(
            key, identity["formulation"], target, str(identity["vm_id"]),
            int(identity["fold"]), int(identity["L"]), int(identity["seed"]),
            "inner", expected_support,
        )
        if identity != expected_identity:
            failures.append(f"inner_run_identity:{identity.get('run_id')}")
        lookup[(
            identity["formulation"], target, str(identity["vm_id"]),
            int(identity["fold"]), int(identity["L"]), int(identity["seed"]),
        )] = row

    contexts = pd.read_csv(env_dir / "selected_contexts.csv", dtype={"vm_id": str})
    epochs = pd.read_csv(env_dir / "selected_epochs.csv", dtype={"vm_id": str})
    context_counts = contexts.groupby("formulation").size().astype(int).to_dict()
    checks["selected_context_counts"] = context_counts
    if context_counts != EXPECTED["selected_contexts"]:
        failures.append(f"selected_context_counts:{context_counts}")
    if len(epochs) != 4_725:
        failures.append(f"selected_epoch_count:{len(epochs)}")
    if set(contexts.selection_source) != {"inner_validation_only"}:
        failures.append("context_selection_source")

    recomputed_contexts = 0
    epoch_lookup: dict[tuple[Any, ...], int] = {}
    for row in contexts.itertuples(index=False):
        target = None if pd.isna(row.resource) else row.resource
        candidates = []
        for length in CONTEXTS:
            for seed in SEEDS:
                record = lookup[(row.formulation, target, str(row.vm_id), int(row.fold), length, seed)]
                candidates.append(SelectionRow(
                    row.formulation, length, seed,
                    np.asarray(record["validation_nmae"], dtype=float),
                    int(record["best_epoch"]),
                ))
        result = select_context(candidates, row.formulation)
        if int(row.selected_L) != result.context_length or not np.isclose(row.selection_score, result.score):
            failures.append(f"selection_recompute:{row.formulation}:{row.vm_id}:{row.fold}:{target}")
        for seed, epoch in result.best_epoch_by_seed.items():
            epoch_lookup[(row.formulation, target, str(row.vm_id), int(row.fold), seed)] = epoch
        recomputed_contexts += 1
    checks["context_selections_recomputed"] = recomputed_contexts

    artifact_failures = 0
    prediction_schema_failures = 0
    for row in final:
        identity = row.get("identity", {})
        target = identity.get("resource")
        epoch_key = (
            identity.get("formulation"), target, str(identity.get("vm_id")),
            int(identity.get("fold", 0)), int(identity.get("seed", -1)),
        )
        selected_epoch = epoch_lookup.get(epoch_key)
        selected_context_row = contexts[
            contexts.formulation.eq(identity.get("formulation"))
            & contexts.vm_id.eq(str(identity.get("vm_id")))
            & contexts.fold.eq(int(identity.get("fold", 0)))
            & (
                contexts.resource.isna()
                if target is None else contexts.resource.eq(target)
            )
        ]
        if len(selected_context_row) != 1:
            failures.append(f"final_selection_lookup:{identity.get('run_id')}")
            continue
        selected_L = int(selected_context_row.selected_L.iloc[0])
        clean, folds = vm_data(key, str(identity["vm_id"]))
        fold = folds[int(identity["fold"]) - 1]
        expected_support = split_hash(fold, "outer_train", "outer_test")
        expected_identity = run_identity(
            key, identity["formulation"], target, str(identity["vm_id"]),
            int(identity["fold"]), selected_L, int(identity["seed"]),
            "final", expected_support, selected_epoch=selected_epoch,
        )
        if identity != expected_identity:
            failures.append(f"final_run_identity:{identity.get('run_id')}")
        if (
            row.get("scaler_fit_split") != "complete_legal_outer_train_only"
            or row.get("test_evaluations") != 1
            or row.get("outer_test_accessed") is not True
            or row.get("execution_correction_sha256") != EXECUTION_CORRECTION_HASH
            or row.get("outer_train_hash") != fold.hashes["outer_train"]
            or row.get("outer_test_hash") != fold.hashes["outer_test"]
            or not row.get("metrics")
        ):
            failures.append(f"final_lifecycle:{identity.get('run_id')}")
        for artifact_name in ("model", "prediction"):
            relative = Path(row.get(f"{artifact_name}_path", "missing"))
            if not relative.is_relative_to(SCIENTIFIC_RELATIVE_ROOT):
                failures.append(f"artifact_namespace:{artifact_name}:{identity.get('run_id')}")
            path, observed_hash = relative_hash(relative.as_posix())
            if observed_hash != row.get(f"{artifact_name}_sha256"):
                artifact_failures += 1
                failures.append(f"artifact_hash:{artifact_name}:{identity.get('run_id')}")
        prediction_path = BASE / row.get("prediction_path", "missing")
        if prediction_path.is_file():
            metadata = pq.ParquetFile(prediction_path).metadata
            expected_rows = int(row.get("outer_test_n", 0)) * (20 if identity["formulation"] == "M1" else 5)
            if metadata.num_rows != expected_rows:
                prediction_schema_failures += 1
                failures.append(f"prediction_row_count:{identity.get('run_id')}")
            required_columns = {
                "run_id", "environment", "formulation", "resource", "vm_id", "fold",
                "seed", "selected_L", "selected_epoch", "origin_timestamp_seconds",
                "lead", "horizon_minutes", "target_timestamp_seconds", "y_true", "y_pred",
                "support_hash",
            }
            if not required_columns.issubset(set(pq.ParquetFile(prediction_path).schema.names)):
                prediction_schema_failures += 1
                failures.append(f"prediction_schema:{identity.get('run_id')}")
    checks["artifact_hash_failures"] = artifact_failures
    checks["prediction_schema_failures"] = prediction_schema_failures

    inner_signature = inspect.signature(fit_inner)
    final_signature = inspect.signature(fit_final_fixed_epochs)
    if "test" in " ".join(inner_signature.parameters).lower():
        failures.append("inner_api_test_argument")
    if any("test" in name or "validation" in name for name in final_signature.parameters):
        failures.append("final_api_validation_or_test_argument")
    checks["inner_api_parameters"] = list(inner_signature.parameters)
    checks["final_api_parameters"] = list(final_signature.parameters)

    comparison_files = [path.as_posix() for path in (OUT / "comparisons").glob("*") if path.is_file()]
    synthesis_files = [path.as_posix() for path in (OUT / "synthesis").glob("*") if path.is_file()]
    figure_files = [path.as_posix() for path in (OUT / "figures").glob("*") if path.is_file()]
    if comparison_files or synthesis_files or figure_files:
        failures.append("analysis_artifacts_exist_before_dual_environment_completion")
    checks["analysis_artifacts"] = {
        "comparisons": len(comparison_files),
        "synthesis": len(synthesis_files),
        "figures": len(figure_files),
    }

    result = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "checks": checks,
    }
    destination = env_dir / "validation/technical_validation.json"
    atomic_json_write(destination, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
