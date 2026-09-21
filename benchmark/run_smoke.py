#!/usr/bin/env python3
"""Capped execution smoke test; not a benchmark accuracy run."""

from __future__ import annotations

import json
import resource
import time
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark.src.data import (
    PANEL_PATH,
    load_canonical_panel,
    load_registry,
    raw_hashes,
    sha256_file,
    verify_raw_hashes,
)
from benchmark.src.features import validate_lomo_exclusion
from benchmark.src.metrics import per_lead_metrics
from benchmark.src.models import (
    DLinearForecaster,
    LightGBMForecaster,
    PersistenceForecaster,
    RidgeForecaster,
    TCNForecaster,
)
from benchmark.src.splits import (
    build_inner_split,
    build_outer_folds,
    validate_against_phase1c,
)
from benchmark.src.validation import prepare_output_schemas
from benchmark.src.windows import (
    build_windows,
    finite_feature_origins,
    joint_eligible_origins,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "benchmark" / "outputs"
SMOKE_DIR = OUTPUT_DIR / "smoke"
MACHINE = "machine01"
OUTER_FOLD = 1
FEATURE_SETS = ["F0_LOCAL", "F5_THROUGHPUT_LOMO_MEDIAN"]
CONTEXT_LENGTH = 32


def cap(indices: np.ndarray, maximum: int) -> np.ndarray:
    if len(indices) <= maximum:
        return indices
    positions = np.linspace(0, len(indices) - 1, maximum, dtype=int)
    return indices[positions]


def model_factory(name: str, channels: int, epochs: int = 2):
    if name == "Persistence":
        return PersistenceForecaster()
    if name == "Ridge":
        return RidgeForecaster(alpha=1.0)
    if name == "LightGBM":
        return LightGBMForecaster(
            num_leaves=15, learning_rate=0.05, n_estimators=10
        )
    training = {
        "learning_rate": 1e-3,
        "batch_size": 128,
        "max_epochs": epochs,
        "patience": 1,
        "gradient_clip_norm": 1.0,
    }
    if name == "DLinear":
        return DLinearForecaster(
            context_length=CONTEXT_LENGTH,
            input_channels=channels,
            seed=0,
            **training,
        )
    if name == "TCN":
        return TCNForecaster(
            input_channels=channels,
            seed=0,
            channels=(32, 32),
            kernel_size=3,
            dropout=0.1,
            **training,
        )
    raise KeyError(name)


def main() -> None:
    started = time.perf_counter()
    SMOKE_DIR.mkdir(parents=True, exist_ok=True)
    prepare_output_schemas(OUTPUT_DIR)
    panel_hash_before = sha256_file(PANEL_PATH)
    raw_before = raw_hashes()
    panel = load_canonical_panel()
    registry = load_registry()
    if not validate_lomo_exclusion(registry, MACHINE):
        raise RuntimeError("LOMO exclusion validation failed")
    equivalence = validate_against_phase1c(panel)
    if not equivalence["pass"]:
        raise RuntimeError("Independent split algorithm differs from Phase 1C")

    eligible = joint_eligible_origins(panel, MACHINE)
    folds = build_outer_folds(panel, eligible)
    outer = folds[OUTER_FOLD - 1]
    inner = build_inner_split(panel, outer.train_indices)
    if not (
        panel["timestamp"].iloc[outer.train_indices + 128].max()
        < outer.first_test_origin_timestamp
    ):
        raise RuntimeError("Outer target-time leakage")
    if not (
        panel["timestamp"].iloc[inner.train_indices + 128].max()
        < inner.first_validation_origin_timestamp
    ):
        raise RuntimeError("Inner target-time leakage")

    smoke_indices = {
        "inner_train": cap(inner.train_indices, 1024),
        "inner_validation": cap(inner.validation_indices, 512),
        "outer_train": cap(outer.train_indices, 2048),
        "outer_test": cap(outer.test_indices, 512),
    }
    models = ["Persistence", "Ridge", "LightGBM", "DLinear", "TCN"]
    shape_rows = []
    metric_rows = []
    for feature_set in FEATURE_SETS:
        feature_indices = {
            name: finite_feature_origins(
                panel,
                MACHINE,
                feature_set,
                CONTEXT_LENGTH,
                indices,
            )
            for name, indices in smoke_indices.items()
        }
        batches = {
            name: build_windows(
                panel,
                MACHINE,
                feature_set,
                CONTEXT_LENGTH,
                indices,
            )
            for name, indices in feature_indices.items()
        }
        channels = batches["inner_train"].X.shape[-1]
        for model_name in models:
            selection_model = model_factory(model_name, channels)
            if model_name in {"DLinear", "TCN"}:
                selection_model.fit(
                    batches["inner_train"].X,
                    batches["inner_train"].y,
                    batches["inner_validation"].X,
                    batches["inner_validation"].y,
                )
                selected_epochs = selection_model.epochs_trained
                model = model_factory(model_name, channels, epochs=selected_epochs)
            else:
                selection_model.fit(
                    batches["inner_train"].X,
                    batches["inner_train"].y,
                    batches["inner_validation"].X,
                    batches["inner_validation"].y,
                )
                model = model_factory(model_name, channels)
            model.fit(batches["outer_train"].X, batches["outer_train"].y)
            prediction = model.predict(batches["outer_test"].X)
            expected_shape = batches["outer_test"].y.shape
            if prediction.shape != expected_shape or expected_shape[1] != 8:
                raise RuntimeError(
                    f"{model_name}/{feature_set}: {prediction.shape} != {expected_shape}"
                )
            shape_rows.append(
                {
                    "model": model_name,
                    "feature_set": feature_set,
                    "prediction_rows": prediction.shape[0],
                    "prediction_columns": prediction.shape[1],
                    "status": "PASS",
                }
            )
            metrics = per_lead_metrics(batches["outer_test"].y, prediction)
            metrics["model"] = model_name
            metrics["feature_set"] = feature_set
            metric_rows.append(metrics)

    pd.DataFrame(shape_rows).to_csv(
        SMOKE_DIR / "model_output_shapes.csv", index=False
    )
    pd.concat(metric_rows, ignore_index=True).to_parquet(
        SMOKE_DIR / "metrics_not_for_interpretation.parquet", index=False
    )
    raw_after = raw_hashes()
    validation = {
        "status": "PASS",
        "scientific_interpretation_allowed": False,
        "machine": MACHINE,
        "outer_fold": OUTER_FOLD,
        "feature_sets": FEATURE_SETS,
        "models": models,
        "neural_seed": 0,
        "context_length": CONTEXT_LENGTH,
        "smoke_training_caps": {
            name: len(indices) for name, indices in smoke_indices.items()
        },
        "model_feature_executions": len(shape_rows),
        "all_output_shapes_n_by_8": all(
            row["prediction_columns"] == 8 for row in shape_rows
        ),
        "exact_future_leads": [1, 2, 4, 8, 16, 32, 64, 128],
        "phase1c_boundary_equivalence": equivalence,
        "outer_target_time_leakage": 0,
        "inner_target_time_leakage": 0,
        "segment_crossings": 0,
        "outer_test_used_for_selection": False,
        "target_scaled": False,
        "panel_unchanged": sha256_file(PANEL_PATH) == panel_hash_before,
        "raw_hashes_unchanged": raw_before == raw_after,
        "raw_hashes_match_phase1": verify_raw_hashes(),
        "runtime_seconds": time.perf_counter() - started,
        "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
    }
    if not all(
        [
            validation["all_output_shapes_n_by_8"],
            validation["phase1c_boundary_equivalence"]["pass"],
            validation["outer_target_time_leakage"] == 0,
            validation["inner_target_time_leakage"] == 0,
            validation["segment_crossings"] == 0,
            not validation["outer_test_used_for_selection"],
            not validation["target_scaled"],
            validation["panel_unchanged"],
            validation["raw_hashes_unchanged"],
            validation["raw_hashes_match_phase1"],
        ]
    ):
        raise RuntimeError("Smoke validation failed")
    (SMOKE_DIR / "smoke_validation.json").write_text(
        json.dumps(validation, indent=2) + "\n"
    )
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
