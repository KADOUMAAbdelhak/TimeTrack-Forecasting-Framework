#!/usr/bin/env python3
"""Resumable Phase 2B-2A3 PatchTST-only scientific execution."""

from __future__ import annotations

import argparse
import json
import os
import platform
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from benchmark.neural_v2.run_dlinear_scientific import (
    ProcessMonitor,
    atomic_csv,
    atomic_parquet,
    prediction_frame,
    valid_final_record,
    valid_record,
)
from benchmark.neural_v2.src.data import (
    CONTEXT_LENGTHS,
    FUTURE_LEADS,
    build_windows,
    load_canonical_panel,
    sha256_file,
)
from benchmark.neural_v2.src.metrics import per_lead_metrics
from benchmark.neural_v2.src.selection import InnerResult, select_context
from benchmark.neural_v2.src.splits import build_supported_folds
from benchmark.neural_v2.src.training import (
    fit_final_fixed_epochs,
    fit_inner,
    parameter_count,
    predict,
)
from benchmark.neural_v2.src.validation import atomic_json_write, run_id


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "benchmark/neural_v2/outputs/patchtst"
CONFIG = ROOT / "benchmark/neural_v2/configs/neural_v2.json"
DECISION = ROOT / "benchmark/neural_v2/NEURAL_V2_DECISION.md"
INVENTORY = ROOT / "benchmark/neural_v2/NEURAL_V2_ARTIFACT_SHA256.csv"
DLINEAR_INVENTORY = ROOT / "benchmark/neural_v2/DLINEAR_SCIENTIFIC_ARTIFACT_SHA256.csv"
LSTM_INVENTORY = ROOT / "benchmark/neural_v2/LSTM_SCIENTIFIC_ARTIFACT_SHA256.csv"
CRITERIA = ROOT / "benchmark/neural_v2/PATCHTST_DECISION_CRITERIA.md"
EXPECTED_DECISION_HASH = "9cec1dc25dc20dd1bf20ac3d7d495f731d41106935a66726d79a182fd058a08c"
EXPECTED_CRITERIA_HASH = "c431f575706dd013a43ebedbd5ac695a6c615d3855b5bba709372afb82273203"
EXPECTED_DLINEAR_INVENTORY_HASH = "fd4e0fe3a1413c6f9a0b942627858354e736e4beb479f77ef71ae2c3aa46d41a"
EXPECTED_LSTM_INVENTORY_HASH = "d67142e064478670df91470eabca059c67de03766050cdc54f087e158591c88f"
PILOT_CENTRAL_HOURS = 4.398820113185082 + 7.93774818401963
FEATURES = ("F0_LOCAL", "F1_THROUGHPUT")
MACHINES = tuple(f"machine{number:02d}" for number in range(1, 8))
SEEDS = (0, 1, 2)


def distribution(frame: pd.DataFrame, column: str) -> list[dict[str, object]]:
    return (
        frame.groupby(column).size().rename("count").reset_index().to_dict(orient="records")
    )


def execute() -> None:
    if sha256_file(DECISION) != EXPECTED_DECISION_HASH:
        raise RuntimeError("Frozen Neural-v2 decision hash differs")
    if sha256_file(CRITERIA) != EXPECTED_CRITERIA_HASH:
        raise RuntimeError("Prospective PatchTST decision criteria hash differs")
    if sha256_file(DLINEAR_INVENTORY) != EXPECTED_DLINEAR_INVENTORY_HASH:
        raise RuntimeError("Frozen DLinear scientific inventory differs")
    if sha256_file(LSTM_INVENTORY) != EXPECTED_LSTM_INVENTORY_HASH:
        raise RuntimeError("Frozen LSTM scientific inventory differs")
    config_hash = sha256_file(CONFIG)
    inventory_hash = sha256_file(INVENTORY)
    panel = load_canonical_panel()
    OUT.mkdir(parents=True, exist_ok=True)
    invocation_started = time.perf_counter()
    existing_inner_paths = sorted((OUT / "progress/inner").glob("*.json"))
    if existing_inner_paths:
        start_estimates = []
        for path in existing_inner_paths:
            record = json.loads(path.read_text())
            start_estimates.append(path.stat().st_mtime - float(record["fit_wall_seconds"]))
        scientific_started_epoch = min(start_estimates)
    else:
        scientific_started_epoch = time.time()
    timestamp_started = datetime.fromtimestamp(scientific_started_epoch).astimezone().isoformat()
    inner_phase_started = time.perf_counter()
    selected_rows: list[dict[str, object]] = []
    reused_inner = 0
    completed_inner = 0
    reused_final = 0
    completed_final = 0

    with ProcessMonitor() as monitor:
        for feature in FEATURES:
            for machine in MACHINES:
                folds_by_length = {
                    length: build_supported_folds(panel, machine, length)
                    for length in CONTEXT_LENGTHS
                }
                for fold_position in range(5):
                    fold_number = fold_position + 1
                    cell_payload = {
                        "model": "PatchTST",
                        "feature_set": feature,
                        "machine": machine,
                        "fold": fold_number,
                    }
                    cell_id = run_id(cell_payload)
                    inner_results: list[InnerResult] = []
                    for length in CONTEXT_LENGTHS:
                        fold = folds_by_length[length][fold_position]
                        train = build_windows(panel, machine, feature, length, fold.inner_train_indices)
                        validation = build_windows(panel, machine, feature, length, fold.inner_validation_indices)
                        for seed in SEEDS:
                            progress_path = OUT / "progress/inner" / f"{cell_id}_L{length}_seed{seed}.json"
                            expected = {
                                **cell_payload,
                                "context_length": length,
                                "seed": seed,
                                "config_sha256": config_hash,
                                "decision_sha256": EXPECTED_DECISION_HASH,
                                "criteria_sha256": EXPECTED_CRITERIA_HASH,
                                "inner_train_hash": fold.inner_train_hash,
                                "inner_validation_hash": fold.inner_validation_hash,
                                "final_train_hash": fold.outer_train_hash,
                                "test_hash": fold.outer_test_hash,
                            }
                            record = valid_record(progress_path, expected)
                            if record is None:
                                fit_started = time.perf_counter()
                                result = fit_inner(
                                    "PatchTST", length, train.X.shape[-1], seed,
                                    train.X, train.y, validation.X, validation.y,
                                    device="cpu",
                                )
                                record = {
                                    **expected,
                                    "status": "complete",
                                    "best_epoch": result.best_epoch,
                                    "best_validation_loss": result.best_validation_loss,
                                    "validation_mae_by_lead": [float(value) for value in result.validation_mae_by_lead],
                                    "mean_validation_mae": float(np.mean(result.validation_mae_by_lead)),
                                    "training_epochs_executed": result.epochs_trained,
                                    "train_seconds": result.train_seconds,
                                    "validation_seconds": result.validation_seconds,
                                    "fit_wall_seconds": time.perf_counter() - fit_started,
                                    "parameter_count": parameter_count(result.model),
                                }
                                atomic_json_write(progress_path, record)
                                completed_inner += 1
                            else:
                                reused_inner += 1
                            inner_results.append(
                                InnerResult(
                                    context_length=length,
                                    seed=seed,
                                    mae_by_lead=tuple(record["validation_mae_by_lead"]),
                                    best_epoch=int(record["best_epoch"]),
                                )
                            )
                    selection = select_context(inner_results)
                    selected_fold = folds_by_length[selection.context_length][fold_position]
                    selected_record = {
                        **cell_payload,
                        "cell_id": cell_id,
                        "selected_L": selection.context_length,
                        "seed_mean_validation_mae": selection.seed_mean_validation_mae,
                        "inner_train_hash": selected_fold.inner_train_hash,
                        "inner_validation_hash": selected_fold.inner_validation_hash,
                        "final_train_hash": selected_fold.outer_train_hash,
                        "test_hash": selected_fold.outer_test_hash,
                        "selection_rule": "seed-mean MAE over 3 seeds and 8 leads; smaller-L tie-break",
                    }
                    selected_rows.append(selected_record)
                    atomic_json_write(
                        OUT / "progress/selections" / f"{cell_id}.json",
                        {
                            **selected_record,
                            "status": "complete",
                            "config_sha256": config_hash,
                            "decision_sha256": EXPECTED_DECISION_HASH,
                            "criteria_sha256": EXPECTED_CRITERIA_HASH,
                            "best_epoch_by_seed": selection.best_epoch_by_seed,
                        },
                    )
                    print(
                        f"INNER cell={len(selected_rows)}/70 feature={feature} machine={machine} "
                        f"fold={fold_number} selected_L={selection.context_length} "
                        f"new={completed_inner} reused={reused_inner}",
                        flush=True,
                    )
        completed_inner_paths = sorted((OUT / "progress/inner").glob("*.json"))
        inner_completed_epoch = max(path.stat().st_mtime for path in completed_inner_paths)
        inner_phase_wall = inner_completed_epoch - scientific_started_epoch
        atomic_csv(OUT / "selected_contexts.csv", pd.DataFrame(selected_rows))

        existing_final_paths = sorted((OUT / "progress/final").glob("*.json"))
        if existing_final_paths:
            final_start_estimates = []
            for path in existing_final_paths:
                record = json.loads(path.read_text())
                final_start_estimates.append(path.stat().st_mtime - float(record["fit_wall_seconds"]))
            final_phase_started_epoch = min(final_start_estimates)
        else:
            final_phase_started_epoch = time.time()
        selected_epochs: list[dict[str, object]] = []
        for selected in selected_rows:
            feature = str(selected["feature_set"])
            machine = str(selected["machine"])
            fold_number = int(selected["fold"])
            length = int(selected["selected_L"])
            fold = build_supported_folds(panel, machine, length)[fold_number - 1]
            outer_train = build_windows(panel, machine, feature, length, fold.outer_train_indices)
            selection_record = json.loads((OUT / "progress/selections" / f"{selected['cell_id']}.json").read_text())
            for seed in SEEDS:
                selected_epoch = int(selection_record["best_epoch_by_seed"][str(seed)])
                final_payload = {
                    "model": "PatchTST",
                    "feature_set": feature,
                    "machine": machine,
                    "fold": fold_number,
                    "seed": seed,
                    "selected_L": length,
                    "selected_epoch": selected_epoch,
                }
                final_run_id = run_id(final_payload)
                prediction_path = OUT / "predictions" / f"{final_run_id}.parquet"
                metric_path = OUT / "progress/metrics" / f"{final_run_id}.json"
                completion_path = OUT / "progress/final" / f"{final_run_id}.json"
                expected = {
                    **final_payload,
                    "run_id": final_run_id,
                    "config_sha256": config_hash,
                    "decision_sha256": EXPECTED_DECISION_HASH,
                    "criteria_sha256": EXPECTED_CRITERIA_HASH,
                    "final_train_hash": fold.outer_train_hash,
                    "test_hash": fold.outer_test_hash,
                }
                completion = valid_final_record(completion_path, prediction_path, metric_path, expected)
                if completion is None:
                    fit_started = time.perf_counter()
                    result = fit_final_fixed_epochs(
                        "PatchTST", length, outer_train.X.shape[-1], seed,
                        outer_train.X, outer_train.y, selected_epoch, device="cpu",
                    )
                    fit_wall_seconds = time.perf_counter() - fit_started
                    # Outer-test labels are loaded only after fitting is complete.
                    outer_test = build_windows(panel, machine, feature, length, fold.outer_test_indices)
                    prediction_started = time.perf_counter()
                    prediction = predict(result, outer_test.X)
                    prediction_seconds = time.perf_counter() - prediction_started
                    frame = prediction_frame({"run_id": final_run_id, **final_payload}, outer_test, prediction)
                    atomic_parquet(prediction_path, frame)
                    metric_values = per_lead_metrics(outer_test.y, prediction)
                    metric_record = {
                        **expected,
                        "status": "complete",
                        "leads": list(FUTURE_LEADS),
                        "mae": [float(value) for value in metric_values["mae"]],
                        "rmse": [float(value) for value in metric_values["rmse"]],
                        "r2": [float(value) for value in metric_values["r2"]],
                    }
                    atomic_json_write(metric_path, metric_record)
                    completion = {
                        **expected,
                        "status": "complete",
                        "train_sample_count": len(fold.outer_train_indices),
                        "test_sample_count": len(fold.outer_test_indices),
                        "train_seconds": result.train_seconds,
                        "fit_wall_seconds": fit_wall_seconds,
                        "prediction_seconds": prediction_seconds,
                        "parameter_count": parameter_count(result.model),
                        "prediction_path": str(prediction_path.relative_to(ROOT)),
                        "metric_path": str(metric_path.relative_to(ROOT)),
                        "prediction_sha256": sha256_file(prediction_path),
                        "metric_sha256": sha256_file(metric_path),
                    }
                    atomic_json_write(completion_path, completion)
                    completed_final += 1
                else:
                    reused_final += 1
                selected_epochs.append({**final_payload, "run_id": final_run_id})
                print(
                    f"FINAL run={len(selected_epochs)}/210 feature={feature} machine={machine} "
                    f"fold={fold_number} seed={seed} new={completed_final} reused={reused_final}",
                    flush=True,
                )
        completed_final_paths = sorted((OUT / "progress/final").glob("*.json"))
        final_completed_epoch = max(path.stat().st_mtime for path in completed_final_paths)
        final_phase_wall = final_completed_epoch - final_phase_started_epoch

    inner_records = [json.loads(path.read_text()) for path in sorted((OUT / "progress/inner").glob("*.json"))]
    final_records = [json.loads(path.read_text()) for path in sorted((OUT / "progress/final").glob("*.json"))]
    metric_records = [json.loads(path.read_text()) for path in sorted((OUT / "progress/metrics").glob("*.json"))]
    inner_frame = pd.DataFrame(inner_records)
    selected_epoch_frame = pd.DataFrame(selected_epochs)
    atomic_parquet(OUT / "inner_selection_runs.parquet", inner_frame)
    atomic_csv(OUT / "selected_epochs.csv", selected_epoch_frame)

    registry_columns = [
        "run_id", "model", "feature_set", "machine", "fold", "seed",
        "selected_L", "selected_epoch", "status", "final_train_hash", "test_hash",
        "train_sample_count", "test_sample_count", "prediction_path",
        "prediction_sha256", "metric_path", "metric_sha256",
    ]
    atomic_csv(OUT / "run_registry.csv", pd.DataFrame(final_records).loc[:, registry_columns])
    metric_rows = []
    for record in metric_records:
        for position, lead in enumerate(record["leads"]):
            metric_rows.append(
                {key: record[key] for key in (
                    "run_id", "model", "feature_set", "machine", "fold", "seed",
                    "selected_L", "selected_epoch", "test_hash",
                )}
                | {
                    "lead": lead,
                    "mae": record["mae"][position],
                    "rmse": record["rmse"][position],
                    "r2": record["r2"][position],
                }
            )
    atomic_parquet(OUT / "metrics.parquet", pd.DataFrame(metric_rows))
    prediction_bytes = sum(path.stat().st_size for path in (OUT / "predictions").glob("*.parquet"))
    selected_frame = pd.DataFrame(selected_rows)
    runtime = {
        "status": "TRAINING_COMPLETE_ANALYSIS_PENDING",
        "started_at": timestamp_started,
        "finished_at": datetime.now().astimezone().isoformat(),
        "device": "cpu",
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "logical_cpu_count": os.cpu_count(),
            "torch_threads": torch.get_num_threads(),
        },
        "config_sha256": config_hash,
        "decision_sha256": EXPECTED_DECISION_HASH,
        "criteria_sha256": EXPECTED_CRITERIA_HASH,
        "frozen_inventory_sha256": inventory_hash,
        "dlinear_inventory_sha256": EXPECTED_DLINEAR_INVENTORY_HASH,
        "lstm_inventory_sha256": EXPECTED_LSTM_INVENTORY_HASH,
        "inner_fits": len(inner_records),
        "final_runs": len(final_records),
        "metric_rows": len(metric_rows),
        "selected_context_records": len(selected_rows),
        "new_inner_fits_this_invocation": completed_inner,
        "reused_inner_fits_this_invocation": reused_inner,
        "new_final_fits_this_invocation": completed_final,
        "reused_final_fits_this_invocation": reused_final,
        "inner_fit_wall_seconds_sum": float(inner_frame["fit_wall_seconds"].sum()),
        "inner_selection_phase_wall_seconds": inner_phase_wall,
        "final_fit_wall_seconds_sum": float(sum(record["fit_wall_seconds"] for record in final_records)),
        "final_refit_phase_wall_seconds": final_phase_wall,
        "execution_wall_seconds": max(inner_completed_epoch, final_completed_epoch) - scientific_started_epoch,
        "current_invocation_wall_seconds": time.perf_counter() - invocation_started,
        "peak_rss_bytes": monitor.peak_rss_bytes,
        "mean_process_cpu_percent": float(np.mean(monitor.cpu_samples)) if monitor.cpu_samples else None,
        "mean_best_epoch_all_inner_fits": float(inner_frame["best_epoch"].mean()),
        "median_best_epoch_all_inner_fits": float(inner_frame["best_epoch"].median()),
        "epochs_executed_distribution": distribution(inner_frame, "training_epochs_executed"),
        "selected_L_distribution": (
            selected_frame.groupby(["feature_set", "selected_L"]).size().rename("count").reset_index().to_dict(orient="records")
        ),
        "selected_epoch_distribution": distribution(selected_epoch_frame, "selected_epoch"),
        "prediction_artifact_bytes": prediction_bytes,
        "pilot_central_patchtst_projection_hours": PILOT_CENTRAL_HOURS,
    }
    atomic_json_write(OUT / "runtime_accounting.json", runtime)
    print(json.dumps(runtime, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--acknowledge-patchtst-only", action="store_true")
    args = parser.parse_args()
    if not (args.execute and args.acknowledge_patchtst_only):
        raise SystemExit("Execution requires --execute and --acknowledge-patchtst-only")
    execute()


if __name__ == "__main__":
    main()
