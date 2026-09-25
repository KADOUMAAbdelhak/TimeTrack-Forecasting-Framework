#!/usr/bin/env python3
"""Disjoint resumable final-fit worker for the PatchTST scientific run."""

from __future__ import annotations

import argparse
import json
import time

from benchmark.neural_v2.run_dlinear_scientific import (
    atomic_parquet,
    prediction_frame,
    valid_final_record,
)
from benchmark.neural_v2.run_patchtst_scientific import (
    CONFIG,
    CRITERIA,
    DECISION,
    DLINEAR_INVENTORY,
    EXPECTED_CRITERIA_HASH,
    EXPECTED_DECISION_HASH,
    EXPECTED_DLINEAR_INVENTORY_HASH,
    EXPECTED_LSTM_INVENTORY_HASH,
    LSTM_INVENTORY,
    OUT,
    ROOT,
)
from benchmark.neural_v2.src.data import build_windows, load_canonical_panel, sha256_file
from benchmark.neural_v2.src.metrics import per_lead_metrics
from benchmark.neural_v2.src.splits import build_supported_folds
from benchmark.neural_v2.src.training import fit_final_fixed_epochs, parameter_count, predict
from benchmark.neural_v2.src.validation import atomic_json_write, run_id


ALLOWED_FEATURES = ("F0_LOCAL", "F1_THROUGHPUT")
ALLOWED_MACHINES = tuple(f"machine{number:02d}" for number in range(1, 8))
SEEDS = (0, 1, 2)


def execute(feature: str, machines: list[str]) -> None:
    if sha256_file(DECISION) != EXPECTED_DECISION_HASH:
        raise RuntimeError("Frozen Neural-v2 decision hash differs")
    if sha256_file(CRITERIA) != EXPECTED_CRITERIA_HASH:
        raise RuntimeError("Prospective PatchTST criteria hash differs")
    if sha256_file(DLINEAR_INVENTORY) != EXPECTED_DLINEAR_INVENTORY_HASH:
        raise RuntimeError("Frozen DLinear scientific inventory differs")
    if sha256_file(LSTM_INVENTORY) != EXPECTED_LSTM_INVENTORY_HASH:
        raise RuntimeError("Frozen LSTM scientific inventory differs")
    panel = load_canonical_panel()
    config_hash = sha256_file(CONFIG)
    completed = 0
    reused = 0
    for machine in machines:
        for fold_number in range(1, 6):
            cell_payload = {
                "model": "PatchTST",
                "feature_set": feature,
                "machine": machine,
                "fold": fold_number,
            }
            cell_id = run_id(cell_payload)
            selection_record = json.loads((OUT / "progress/selections" / f"{cell_id}.json").read_text())
            length = int(selection_record["selected_L"])
            fold = build_supported_folds(panel, machine, length)[fold_number - 1]
            outer_train = build_windows(panel, machine, feature, length, fold.outer_train_indices)
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
                        "leads": [1, 2, 4, 8, 16, 32, 64, 128],
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
                    completed += 1
                else:
                    reused += 1
                print(
                    f"FINAL-WORKER feature={feature} machine={machine} fold={fold_number} "
                    f"seed={seed} new={completed} reused={reused}",
                    flush=True,
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature", choices=ALLOWED_FEATURES, required=True)
    parser.add_argument("--machines", nargs="+", choices=ALLOWED_MACHINES, required=True)
    parser.add_argument("--acknowledge-patchtst-final-only", action="store_true")
    args = parser.parse_args()
    if not args.acknowledge_patchtst_final_only:
        raise SystemExit("Worker requires --acknowledge-patchtst-final-only")
    execute(args.feature, args.machines)


if __name__ == "__main__":
    main()
