#!/usr/bin/env python3
"""Project full neural-v2 CPU cost from measured pilot throughput."""

from __future__ import annotations

import json
from pathlib import Path

from benchmark.neural_v2.src.data import CONTEXT_LENGTHS, load_canonical_panel
from benchmark.neural_v2.src.splits import build_supported_folds
from benchmark.neural_v2.src.validation import atomic_json_write


ROOT = Path(__file__).resolve().parents[3]
PILOT_PATH = ROOT / "benchmark/neural_v2/pilot/timing_results.json"
OUTPUT_PATH = ROOT / "benchmark/neural_v2/pilot/runtime_projection.json"
FEATURES = ("F0_LOCAL", "F1_THROUGHPUT")
MODELS = ("DLinear", "LSTM", "TCN-v2", "PatchTST")
MACHINES = tuple(f"machine{number:02d}" for number in range(1, 8))
SEEDS = (0, 1, 2)


def context_cost_factor(model: str, context_length: int) -> float:
    if model == "PatchTST":
        patch_count = 1 + (context_length - 8) // 4
        return patch_count / 15.0
    return context_length / 64.0


def main() -> None:
    pilot = json.loads(PILOT_PATH.read_text())
    measured = {
        (row["model"], row["feature_set"]): row for row in pilot["runs"]
    }
    panel = load_canonical_panel()
    support: dict[int, list[tuple[int, int, int, int]]] = {
        length: [] for length in CONTEXT_LENGTHS
    }
    for machine in MACHINES:
        for length in CONTEXT_LENGTHS:
            for fold in build_supported_folds(panel, machine, length):
                support[length].append(
                    (
                        len(fold.inner_train_indices),
                        len(fold.inner_validation_indices),
                        len(fold.outer_train_indices),
                        len(fold.outer_test_indices),
                    )
                )
    scenarios = {
        "optimistic": {
            "mean_epochs": 10,
            "selected_context_assumption": 32,
            "per_fit_overhead_seconds": 0.04,
        },
        "central": {
            "mean_epochs": 25,
            "selected_context_assumption": 64,
            "per_fit_overhead_seconds": 0.08,
        },
        "conservative": {
            "mean_epochs": 50,
            "selected_context_assumption": 128,
            "per_fit_overhead_seconds": 0.15,
        },
    }
    projections = {}
    for scenario_name, assumptions in scenarios.items():
        epochs = assumptions["mean_epochs"]
        selected_length = assumptions["selected_context_assumption"]
        overhead = assumptions["per_fit_overhead_seconds"]
        by_model_feature = {}
        total_seconds = 0.0
        for model in MODELS:
            for feature in FEATURES:
                row = measured[(model, feature)]
                train_rate = row["train_seconds"] / (
                    pilot["train_samples"] * pilot["epochs"]
                )
                validation_rate = row["validation_seconds"] / (
                    pilot["validation_samples"] * pilot["epochs"]
                )
                inner_seconds = 0.0
                inner_fits = 0
                for length in CONTEXT_LENGTHS:
                    factor = context_cost_factor(model, length)
                    for train_n, validation_n, _outer_n, _test_n in support[length]:
                        per_epoch = factor * (
                            train_n * train_rate + validation_n * validation_rate
                        )
                        inner_seconds += len(SEEDS) * (
                            epochs * per_epoch + overhead
                        )
                        inner_fits += len(SEEDS)
                final_seconds = 0.0
                final_fits = 0
                final_factor = context_cost_factor(model, selected_length)
                for _train_n, _validation_n, outer_n, _test_n in support[
                    selected_length
                ]:
                    per_epoch = final_factor * outer_n * train_rate
                    final_seconds += len(SEEDS) * (
                        epochs * per_epoch + overhead
                    )
                    final_fits += len(SEEDS)
                cell_seconds = inner_seconds + final_seconds
                by_model_feature[f"{model}/{feature}"] = {
                    "inner_fits": inner_fits,
                    "final_fits": final_fits,
                    "projected_seconds": cell_seconds,
                    "projected_hours": cell_seconds / 3600.0,
                }
                total_seconds += cell_seconds
        projections[scenario_name] = {
            "assumptions": assumptions,
            "by_model_feature": by_model_feature,
            "total_seconds": total_seconds,
            "total_hours": total_seconds / 3600.0,
            "total_days": total_seconds / 86400.0,
        }
    average_test_samples = sum(
        row[3] for row in support[64]
    ) / len(support[64])
    payload = {
        "basis": (
            "Measured five-epoch CPU train/validation seconds per sample at L=64, "
            "scaled by exact neural-v2 support sizes and linear history cost; "
            "PatchTST scales by patch count."
        ),
        "uncertainty": (
            "Epoch count and selected context are unknown before scientific inner "
            "selection; hardware contention, cache effects, and nonlinear sequence "
            "cost can change realized time."
        ),
        "fit_counts": {
            "inner": 2520,
            "final": 840,
            "total": 3360,
            "final_metric_rows": 6720,
        },
        "support_summary": {
            "machine_fold_cells_per_context": len(support[64]),
            "average_outer_test_samples_at_L64": average_test_samples,
        },
        "scenarios": projections,
    }
    atomic_json_write(OUTPUT_PATH, payload)


if __name__ == "__main__":
    main()
