#!/usr/bin/env python3
"""Disjoint resumable inner-fit worker for the LSTM scientific run."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

from benchmark.neural_v2.run_dlinear_scientific import valid_record
from benchmark.neural_v2.run_lstm_scientific import (
    CONFIG,
    CRITERIA,
    DECISION,
    EXPECTED_CRITERIA_HASH,
    EXPECTED_DECISION_HASH,
    OUT,
)
from benchmark.neural_v2.src.data import CONTEXT_LENGTHS, build_windows, load_canonical_panel, sha256_file
from benchmark.neural_v2.src.splits import build_supported_folds
from benchmark.neural_v2.src.training import fit_inner, parameter_count
from benchmark.neural_v2.src.validation import atomic_json_write, run_id


ALLOWED_FEATURES = ("F0_LOCAL", "F1_THROUGHPUT")
ALLOWED_MACHINES = tuple(f"machine{number:02d}" for number in range(1, 8))
SEEDS = (0, 1, 2)


def execute(feature: str, machines: list[str]) -> None:
    if sha256_file(DECISION) != EXPECTED_DECISION_HASH:
        raise RuntimeError("Frozen Neural-v2 decision hash differs")
    if sha256_file(CRITERIA) != EXPECTED_CRITERIA_HASH:
        raise RuntimeError("Prospective LSTM criteria hash differs")
    panel = load_canonical_panel()
    config_hash = sha256_file(CONFIG)
    completed = 0
    reused = 0
    for machine in machines:
        folds_by_length = {
            length: build_supported_folds(panel, machine, length)
            for length in CONTEXT_LENGTHS
        }
        for fold_position in range(5):
            fold_number = fold_position + 1
            cell_payload = {
                "model": "LSTM",
                "feature_set": feature,
                "machine": machine,
                "fold": fold_number,
            }
            cell_id = run_id(cell_payload)
            # Scheduling order only: stagger expensive contexts relative to
            # the main runner. Selection still consumes the same 3x3 grid.
            for length in reversed(CONTEXT_LENGTHS):
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
                            "LSTM", length, train.X.shape[-1], seed,
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
                        completed += 1
                    else:
                        reused += 1
                    print(
                        f"WORKER feature={feature} machine={machine} fold={fold_number} "
                        f"L={length} seed={seed} new={completed} reused={reused}",
                        flush=True,
                    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature", choices=ALLOWED_FEATURES, required=True)
    parser.add_argument("--machines", nargs="+", choices=ALLOWED_MACHINES, required=True)
    parser.add_argument("--acknowledge-lstm-inner-only", action="store_true")
    args = parser.parse_args()
    if not args.acknowledge_lstm_inner_only:
        raise SystemExit("Worker requires --acknowledge-lstm-inner-only")
    execute(args.feature, args.machines)


if __name__ == "__main__":
    main()
