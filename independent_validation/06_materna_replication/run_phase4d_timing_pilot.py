#!/usr/bin/env python3
"""Run the bounded 27-model Phase 4D inner-only timing pilot."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BITBRAINS = ROOT / "independent_validation/05_bitbrains_factorial"
sys.path.insert(0, str(BITBRAINS))
sys.path.insert(0, str(HERE))

from run_phase4d_audit import TRACE_DATASETS, legal_origins_structure_only, read_vm  # noqa: E402
from src import RESOURCE_ORDER  # noqa: E402
from src.cleaning import clean_and_segment  # noqa: E402
from src.panel import build_windows  # noqa: E402
from src.splits import build_folds  # noqa: E402
from src.training import fit_inner, parameter_count, serialized_state_bytes  # noqa: E402
from src.transforms import fit_partition_scaler, scale_windows  # noqa: E402


PILOT = HERE / "pilot"
MANIFESTS = HERE / "manifests"
OUTPUTS = HERE / "outputs"
EPOCHS = 5
CONTEXT = 9
SEED = 0
FOLD = 1


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run_fit(trace: str, vm_id: str, formulation: str, target: str, X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray) -> dict[str, object]:
    started = time.perf_counter()
    result = fit_inner(
        formulation, None if formulation == "M1" else target, SEED,
        X_train, y_train, X_val, y_val, fixed_epochs=EPOCHS,
    )
    wall = time.perf_counter() - started
    train_seconds = float(sum(result.epoch_train_seconds))
    validation_seconds = float(sum(result.epoch_validation_seconds))
    row = {
        "trace": trace,
        "vm_id": vm_id,
        "formulation": formulation,
        "target": target,
        "parameter_count": parameter_count(result.model),
        "fold": FOLD,
        "seed": SEED,
        "L": CONTEXT,
        "epochs_trained": result.epochs_trained,
        "training_samples": len(X_train),
        "validation_samples": len(X_val),
        "seconds_per_epoch": train_seconds / EPOCHS,
        "validation_seconds_per_epoch": validation_seconds / EPOCHS,
        "five_epoch_fit_seconds": wall,
        "samples_per_second": len(X_train) * EPOCHS / train_seconds,
        "peak_rss_bytes": result.peak_rss_bytes,
        "serialized_model_bytes": serialized_state_bytes(result.model),
        "input_dimensions": f"N,{CONTEXT},{X_train.shape[-1]}",
        "output_dimensions": "N,4,5" if formulation == "M1" else "N,5",
        "outer_test_targets_accessed": False,
        "outer_test_predictions_generated": False,
        "scientific_predictive_metrics_computed": False,
        "pilot_label": "NON_SCIENTIFIC_INNER_VALIDATION_TIMING_ONLY",
    }
    del result
    return row


def project(timings: pd.DataFrame, support: pd.DataFrame) -> dict[str, object]:
    scenarios = {}
    per_trace = {}
    for trace in TRACE_DATASETS:
        trace_support = support[support.environment.eq(trace)]
        unique_final = trace_support[trace_support.L.eq(18)]
        trace_timings = timings[timings.trace.eq(trace)]
        rates = {
            formulation: float(group.samples_per_second.median())
            for formulation, group in trace_timings.groupby("formulation")
        }
        validation_seconds = {
            formulation: float(group.validation_seconds_per_epoch.median())
            for formulation, group in trace_timings.groupby("formulation")
        }
        sample_totals = {
            "S1_inner": int(trace_support.inner_train_count.sum() * 4 * 3),
            "S1_final": int(unique_final.outer_train_count.sum() * 4 * 3),
            "S2_inner": int(trace_support.inner_train_count.sum() * 4 * 3),
            "S2_final": int(unique_final.outer_train_count.sum() * 4 * 3),
            "M1_inner": int(trace_support.inner_train_count.sum() * 3),
            "M1_final": int(unique_final.outer_train_count.sum() * 3),
        }
        fit_counts = {"S1_inner": 6300, "S1_final": 2100, "S2_inner": 6300, "S2_final": 2100, "M1_inner": 1575, "M1_final": 525}
        trace_projection = {}
        for epochs in (10, 25, 50):
            seconds = 0.0
            detail = {}
            for key, samples in sample_totals.items():
                formulation, phase = key.split("_")
                value = epochs * samples / rates[formulation]
                if phase == "inner":
                    value += epochs * fit_counts[key] * validation_seconds[formulation]
                detail[f"{key}_fit_hours"] = value / 3600.0
                seconds += value
            detail["aggregate_fit_hours"] = seconds / 3600.0
            detail["one_worker_wall_hours"] = seconds / 3600.0
            detail["four_worker_wall_hours"] = seconds / 14400.0
            trace_projection[str(epochs)] = detail
        per_trace[trace] = {"samples_per_second": rates, "scenarios": trace_projection}
    for epochs in (10, 25, 50):
        total = sum(per_trace[trace]["scenarios"][str(epochs)]["aggregate_fit_hours"] for trace in TRACE_DATASETS)
        scenarios[str(epochs)] = {
            "effective_epochs": epochs,
            "combined_fit_hours": total,
            "combined_one_worker_wall_hours": total,
            "combined_four_worker_wall_hours": total / 4,
        }
    return {
        "method": "pilot formulation/trace throughput applied to exact candidate support sample counts; inner validation overhead retained",
        "per_trace": per_trace,
        "combined_scenarios": scenarios,
    }


def main() -> None:
    PILOT.mkdir(parents=True, exist_ok=True)
    selected = pd.read_csv(MANIFESTS / "CANDIDATE_35_VM_COHORT.csv", dtype={"entity_id": str})
    vm_id = str(selected.sort_values("rank").iloc[0].entity_id)
    rows = []
    for trace in TRACE_DATASETS:
        clean = clean_and_segment(read_vm(trace, vm_id))
        origins = legal_origins_structure_only(clean.frame)
        fold = build_folds(clean.frame, trace, vm_id, origins)[0]
        scaler = fit_partition_scaler(clean.frame, fold.inner_train, CONTEXT)
        X_train, y_train, _ = build_windows(clean.frame, fold.inner_train, CONTEXT)
        X_val, y_val, _ = build_windows(clean.frame, fold.inner_validation, CONTEXT)
        X_train, y_train = scale_windows(X_train, y_train, scaler)
        X_val, y_val = scale_windows(X_val, y_val, scaler)
        for formulation in ("S1", "S2"):
            for index, resource in enumerate(RESOURCE_ORDER):
                train_x = X_train[:, :, index:index + 1] if formulation == "S1" else X_train
                val_x = X_val[:, :, index:index + 1] if formulation == "S1" else X_val
                rows.append(run_fit(trace, vm_id, formulation, resource, train_x, y_train[:, index, :], val_x, y_val[:, index, :]))
        rows.append(run_fit(trace, vm_id, "M1", "ALL", X_train, y_train, X_val, y_val))
    timings = pd.DataFrame(rows)
    timings.to_csv(PILOT / "PILOT_TIMINGS.csv", index=False)
    access = {
        "pilot_models": len(timings),
        "expected_pilot_models": 27,
        "epochs_per_model": [5],
        "inner_train_validation_only": True,
        "outer_test_targets_accessed": 0,
        "outer_test_predictions_generated": 0,
        "scientific_predictive_metrics_computed": 0,
        "scientific_context_selections": 0,
        "scientific_final_refits": 0,
    }
    write_json(PILOT / "PILOT_DATA_ACCESS.json", access)
    support = pd.read_parquet(MANIFESTS / "MATERNA_SUPPORT_MANIFEST.parquet")
    runtime = project(timings, support)
    workload = {
        "per_trace": {"S1_inner": 6300, "S1_final": 2100, "S2_inner": 6300, "S2_final": 2100, "M1_inner": 1575, "M1_final": 525, "inner_total": 14175, "final_total": 4725, "fit_total": 18900, "metric_rows": 31500, "selected_contexts": 1575},
        "combined_three_trace": {"inner_total": 42525, "final_total": 14175, "fit_total": 56700, "metric_rows": 94500, "selected_contexts": 4725},
    }
    write_json(OUTPUTS / "SCIENTIFIC_WORKLOAD.json", workload)
    write_json(PILOT / "RUNTIME_PROJECTION.json", runtime)
    phase4c_storage = json.loads((BITBRAINS / "pilot/STORAGE_PROJECTION.json").read_text())
    scale = 1.5
    storage = {
        "projection_basis": "Phase 4C retained-byte projection scaled from two to three 35-VM environments",
        "model_artifact_bytes": int(round(phase4c_storage["model_artifact_bytes_both_environments"] * scale)),
        "prediction_payload_bytes": int(round(phase4c_storage["prediction_payload_bytes_both_environments"] * scale)),
        "metrics_and_manifests_bytes": int(round(phase4c_storage["metrics_and_manifests_bytes"] * scale)),
        "total_retained_scientific_bytes": int(round(phase4c_storage["total_retained_scientific_bytes"] * scale)),
        "heavy_outputs_created_during_preflight": 0,
    }
    write_json(PILOT / "STORAGE_PROJECTION.json", storage)
    central = runtime["combined_scenarios"]["25"]["combined_four_worker_wall_hours"]
    decision = {
        "decision": "FULL_35_VM_THREE_TRACE_REPLICATION_EXPENSIVE_BUT_FEASIBLE" if central <= 48 else "PROSPECTIVE_COHORT_REDUCTION_REQUIRED",
        "basis": ["support", "scale_eligibility", "runtime", "memory", "storage", "implementation_correctness"],
        "predictive_performance_used": 0,
        "central_25_epoch_four_worker_wall_hours": central,
    }
    write_json(PILOT / "COMPUTE_FEASIBILITY_DECISION.json", decision)
    print(json.dumps({"pilot": access, "runtime": runtime["combined_scenarios"], "storage": storage, "compute": decision}, indent=2, sort_keys=True))
    if len(timings) != 27 or set(timings.epochs_trained) != {5}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
