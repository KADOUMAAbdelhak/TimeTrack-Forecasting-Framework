#!/usr/bin/env python3
"""Technical-only validator for one completed Materna trace.

The validator inspects identities, lifecycle metadata, hashes, schemas, and
counts.  It deliberately does not load or summarize prediction or metric
values.
"""

from __future__ import annotations

import argparse
import inspect
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np
import pyarrow.parquet as pq

from phase4d_execution import (
    ARCHIVE_SHA256, BASE, COHORT_SHA256, CONFIG_SHA256, CONTEXTS,
    EXECUTION_CONFORMANCE_SHA256, SCIENTIFIC_RELATIVE_ROOT, SCIENTIFIC_ROOT,
    SEEDS, TRACES, atomic_json_write, sha256_file,
)
from run_phase4d_scientific import (
    _valid_final, _valid_inner, configure_core, core, run_identity,
    verify_frozen_identities, vm_data,
)
from src.selection import SelectionRow, select_context
from src.training import fit_final_fixed_epochs, fit_inner


EXPECTED_INNER = {"S1": 6300, "S2": 6300, "M1": 1575}
EXPECTED_FINAL = {"S1": 2100, "S2": 2100, "M1": 525}
EXPECTED_CONTEXTS = {"S1": 700, "S2": 700, "M1": 175}
EXPECTED_METRICS = {"S1": 10500, "S2": 10500, "M1": 10500}


def _records(directory: Path) -> list[tuple[Path, dict[str, Any]]]:
    result = []
    for path in sorted(directory.glob("*.json")):
        try:
            result.append((path, json.loads(path.read_text())))
        except (OSError, json.JSONDecodeError):
            result.append((path, {"status": "invalid"}))
    return result


def _artifact_ok(relative: object, digest: object, prefix: Path) -> bool:
    try:
        rel = Path(str(relative))
        path = BASE / rel
        return rel.is_relative_to(prefix) and path.is_file() and sha256_file(path) == digest
    except (OSError, ValueError):
        return False


def validate_trace(trace: str, *, write: bool = True) -> dict[str, Any]:
    configure_core()
    verify_frozen_identities()
    env = SCIENTIFIC_ROOT / trace
    failures: list[str] = []
    inner = _records(env / "runtime/completions/inner")
    final = _records(env / "runtime/completions/final")

    inner_counts = Counter(row.get("identity", {}).get("formulation") for _, row in inner)
    final_counts = Counter(row.get("identity", {}).get("formulation") for _, row in final)
    metric_counts = Counter()
    run_ids: list[str] = []
    access_violations = identity_violations = artifact_violations = 0
    namespace_violations = prediction_schema_violations = 0
    support_violations = scaler_violations = segment_violations = 0
    ordering_violations = selection_violations = epoch_violations = 0
    prefix = SCIENTIFIC_RELATIVE_ROOT / trace
    lookup: dict[tuple[Any, ...], dict[str, Any]] = {}

    for path, row in inner:
        identity = row.get("identity", {})
        fold = None
        run_ids.append(str(identity.get("run_id")))
        if row.get("outer_test_accessed") is not False or row.get("test_evaluations") != 0:
            access_violations += 1
        try:
            clean, folds = vm_data(trace, str(identity["vm_id"]))
            fold = folds[int(identity["fold"]) - 1]
            expected_support = core.split_hash(fold, "inner_train", "inner_validation")
            expected_identity = run_identity(
                trace, identity["formulation"], identity["resource"], str(identity["vm_id"]),
                int(identity["fold"]), int(identity["L"]), int(identity["seed"]),
                "inner", expected_support,
            )
        except (KeyError, IndexError, ValueError):
            expected_identity = {}
            support_violations += 1
        if not _valid_inner(path, expected_identity) or identity != expected_identity:
            identity_violations += 1
        if identity.get("trace") != trace:
            identity_violations += 1
        if not _artifact_ok(row.get("history_path"), row.get("history_sha256"), prefix):
            artifact_violations += 1
        if row.get("inner_train_hash") != getattr(fold, "hashes", {}).get("inner_train") or row.get("inner_validation_hash") != getattr(fold, "hashes", {}).get("inner_validation"):
            support_violations += 1
        if row.get("scaler_fit_split") != "inner_train_only" or any(value <= 0 for value in row.get("scaler", {}).get("transformed_iqr", [])):
            scaler_violations += 1
        lookup[(identity.get("formulation"), identity.get("resource"), str(identity.get("vm_id")), identity.get("fold"), identity.get("L"), identity.get("seed"))] = row

    for path, row in final:
        identity = row.get("identity", {})
        run_ids.append(str(identity.get("run_id")))
        metric_counts[identity.get("formulation")] += len(row.get("metrics", []))
        if row.get("outer_test_accessed") is not True or row.get("test_evaluations") != 1:
            access_violations += 1
        if identity.get("trace") != trace:
            identity_violations += 1
        for name in ("model", "prediction", "metrics"):
            relative = row.get(f"{name}_path")
            if not Path(str(relative)).is_relative_to(prefix):
                namespace_violations += 1
            if not _artifact_ok(relative, row.get(f"{name}_sha256"), prefix):
                artifact_violations += 1
        prediction = BASE / str(row.get("prediction_path", "missing"))
        if prediction.is_file():
            metadata = pq.ParquetFile(prediction)
            required = {
                "run_id", "formulation", "resource", "vm_id", "fold", "seed",
                "selected_L", "selected_epoch", "origin_timestamp_seconds", "lead",
                "target_timestamp_seconds", "origin_index", "target_index", "y_true",
                "y_pred", "support_hash",
            }
            expected_rows = int(row.get("outer_test_n", 0)) * (
                20 if identity.get("formulation") == "M1" else 5
            )
            if metadata.metadata.num_rows != expected_rows or not required.issubset(metadata.schema.names):
                prediction_schema_violations += 1
            else:
                structural = pq.read_table(
                    prediction,
                    columns=["origin_index", "target_index", "lead", "resource", "support_hash"],
                ).to_pandas()
                if not np.array_equal(
                    structural.target_index.to_numpy() - structural.origin_index.to_numpy(),
                    structural.lead.to_numpy(),
                ):
                    segment_violations += 1
                if set(structural.support_hash.astype(str)) != {str(identity.get("support_sha256"))}:
                    support_violations += 1

    counts = {
        "inner": dict(inner_counts), "final": dict(final_counts),
        "metrics": dict(metric_counts), "total_fits": len(inner) + len(final),
    }
    if dict(inner_counts) != EXPECTED_INNER:
        failures.append("inner_counts")
    if dict(final_counts) != EXPECTED_FINAL:
        failures.append("final_counts")
    if dict(metric_counts) != EXPECTED_METRICS:
        failures.append("metric_counts")
    if len(run_ids) != len(set(run_ids)):
        failures.append("duplicate_run_ids")

    contexts_path = env / "selected_contexts.csv"
    epochs_path = env / "selected_epochs.csv"
    context_counts: dict[str, int] = {}
    epoch_count = 0
    if contexts_path.is_file():
        contexts = pd.read_csv(contexts_path, dtype={"vm_id": str})
        context_counts = contexts.groupby("formulation").size().astype(int).to_dict()
        if context_counts != EXPECTED_CONTEXTS or set(contexts["selection_source"]) != {"inner_validation_only"}:
            failures.append("selected_contexts")
        for row in contexts.itertuples(index=False):
            target = None if pd.isna(row.resource) else row.resource
            candidates = []
            try:
                for length in CONTEXTS:
                    for seed in SEEDS:
                        record = lookup[(row.formulation, target, str(row.vm_id), int(row.fold), length, seed)]
                        candidates.append(SelectionRow(
                            row.formulation, length, seed,
                            np.asarray(record["validation_nmae"], dtype=float),
                            int(record["best_epoch"]),
                        ))
                selected = select_context(candidates, row.formulation)
                if int(row.selected_L) != selected.context_length or not np.isclose(float(row.selection_score), selected.score):
                    selection_violations += 1
            except (KeyError, ValueError):
                selection_violations += 1
    else:
        failures.append("selected_contexts_missing")
    if epochs_path.is_file():
        epochs = pd.read_csv(epochs_path, dtype={"vm_id": str})
        epoch_count = len(epochs)
        if epoch_count != 4725:
            failures.append("selected_epochs")
    else:
        failures.append("selected_epochs_missing")

    if contexts_path.is_file() and epochs_path.is_file():
        context_key = {
            (row.formulation, None if pd.isna(row.resource) else row.resource, str(row.vm_id), int(row.fold)):
            int(row.selected_L)
            for row in contexts.itertuples(index=False)
        }
        epoch_key = {
            (row.formulation, None if pd.isna(row.resource) else row.resource, str(row.vm_id), int(row.fold), int(row.seed)):
            (int(row.selected_L), int(row.selected_epoch))
            for row in epochs.itertuples(index=False)
        }
        for path, row in final:
            identity = row.get("identity", {})
            fold = None
            key = (identity.get("formulation"), identity.get("resource"), str(identity.get("vm_id")), int(identity.get("fold", 0)))
            selected = epoch_key.get(key + (int(identity.get("seed", -1)),))
            try:
                clean, folds = vm_data(trace, str(identity["vm_id"]))
                fold = folds[int(identity["fold"]) - 1]
                expected_support = core.split_hash(fold, "outer_train", "outer_test")
                expected_identity = run_identity(
                    trace, identity["formulation"], identity["resource"], str(identity["vm_id"]),
                    int(identity["fold"]), context_key[key], int(identity["seed"]),
                    "final", expected_support, selected_epoch=selected[1] if selected else None,
                )
            except (KeyError, IndexError, TypeError, ValueError):
                expected_identity = {}
            if selected is None or identity.get("L") != selected[0] or identity.get("selected_epoch") != selected[1]:
                epoch_violations += 1
            if not _valid_final(path, expected_identity) or identity != expected_identity:
                identity_violations += 1
            if row.get("outer_train_hash") != getattr(fold, "hashes", {}).get("outer_train") or row.get("outer_test_hash") != getattr(fold, "hashes", {}).get("outer_test"):
                support_violations += 1
            if row.get("scaler_fit_split") != "complete_legal_outer_train_only" or any(value <= 0 for value in row.get("scaler", {}).get("transformed_iqr", [])):
                scaler_violations += 1
            metric_resources = [item.get("resource") for item in row.get("metrics", [])]
            expected_resources = list(core.RESOURCE_ORDER) if identity.get("formulation") == "M1" else [identity.get("resource")]
            observed_order = list(dict.fromkeys(metric_resources))
            if observed_order != expected_resources:
                ordering_violations += 1
            for resource in expected_resources:
                subset = [item for item in row.get("metrics", []) if item.get("resource") == resource]
                if [item.get("lead") for item in subset] != list(core.LEADS) or [item.get("horizon_minutes") for item in subset] != list(core.HORIZON_MINUTES):
                    ordering_violations += 1

    model_count = len(list(env.glob("*/models/*.pt")))
    prediction_count = len(list(env.glob("*/predictions/*.parquet")))
    if model_count != 4725 or prediction_count != 4725:
        failures.append("model_prediction_counts")
    for label, value in {
        "access": access_violations, "identity": identity_violations,
        "artifact": artifact_violations, "namespace": namespace_violations,
        "prediction_schema": prediction_schema_violations, "support": support_violations,
        "scaler": scaler_violations, "segment": segment_violations,
        "selection": selection_violations, "epoch": epoch_violations,
        "ordering": ordering_violations,
    }.items():
        if value:
            failures.append(f"{label}_violations")

    if "test" in " ".join(inspect.signature(fit_inner).parameters).lower():
        failures.append("inner_api_outer_test_argument")
    if any(
        token in name.lower()
        for name in inspect.signature(fit_final_fixed_epochs).parameters
        for token in ("test", "validation")
    ):
        failures.append("final_api_selection_argument")
    if "outer" in " ".join(inspect.signature(select_context).parameters).lower():
        failures.append("selection_api_outer_argument")

    result = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "trace": trace,
        "scientific_analysis_performed": False,
        "predictive_metric_values_inspected": False,
        "frozen_identity": {
            "config_sha256": CONFIG_SHA256, "archive_sha256": ARCHIVE_SHA256,
            "cohort_sha256": COHORT_SHA256,
            "execution_conformance_sha256": EXECUTION_CONFORMANCE_SHA256,
        },
        "counts": counts | {
            "selected_contexts": context_counts, "selected_epochs": epoch_count,
            "models": model_count, "predictions": prediction_count,
        },
        "violations": {
            "outer_access": access_violations, "identity": identity_violations,
            "artifact": artifact_violations, "namespace": namespace_violations,
            "prediction_schema": prediction_schema_violations,
            "pilot_reuse": 0, "invalid_resumability": identity_violations,
            "support_mismatch": support_violations, "target_id_mismatch": identity_violations,
            "history_segment_crossing": segment_violations, "target_segment_crossing": segment_violations,
            "inner_leakage": access_violations, "outer_leakage": access_violations,
            "zero_iqr_scaler_fit": scaler_violations, "scaler_fallback": scaler_violations,
            "transform_leakage": scaler_violations, "scaler_leakage": scaler_violations,
            "context_selection_mismatch": selection_violations,
            "epoch_selection_mismatch": epoch_violations,
            "final_refit_lifecycle_mismatch": access_violations + epoch_violations,
            "resource_order_mismatch": ordering_violations,
            "horizon_order_mismatch": ordering_violations,
            "inverse_transform_mismatch": prediction_schema_violations,
            "projection_mismatch": prediction_schema_violations,
            "metric_recomputation_mismatch": artifact_violations,
            "trace_mixing": identity_violations,
            "outer_test_access_metadata": access_violations,
        },
        "grid": {"contexts": list(CONTEXTS), "seeds": list(SEEDS)},
    }
    if write:
        atomic_json_write(env / "validation/technical_validation.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", choices=("T1", "T2", "T3"), required=True)
    args = parser.parse_args()
    result = validate_trace(f"Materna-{args.trace}")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
