"""Benchmark invariants, deterministic IDs, and output schemas."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


RUN_REGISTRY_COLUMNS = [
    "run_id",
    "model",
    "feature_set",
    "machine",
    "outer_fold",
    "context_length",
    "config_json",
    "seed",
    "status",
]
METRIC_COLUMNS = [
    "run_id",
    "machine",
    "outer_fold",
    "lead",
    "model",
    "feature_set",
    "seed",
    "mae",
    "rmse",
    "r2",
    "mae_change_vs_persistence_pct",
    "mae_change_vs_same_model_f0_pct",
]
SELECTED_CONFIG_COLUMNS = [
    "model",
    "feature_set",
    "machine",
    "outer_fold",
    "context_length",
    "config_json",
    "selection_metric",
    "inner_validation_mae",
]


def deterministic_run_id(
    model: str,
    feature_set: str,
    machine: str,
    outer_fold: int,
    context_length: int,
    config: dict[str, Any],
    seed: int | None,
) -> str:
    payload = {
        "model": model,
        "feature_set": feature_set,
        "machine": machine,
        "outer_fold": outer_fold,
        "context_length": context_length,
        "config": config,
        "seed": seed,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()[:24]


def train_only_scaled(
    train: np.ndarray, validation: np.ndarray, test: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, StandardScaler]:
    shape = train.shape
    scaler = StandardScaler()
    train_2d = train.reshape(-1, shape[-1])
    scaler.fit(train_2d)

    def transform(values: np.ndarray) -> np.ndarray:
        transformed = scaler.transform(values.reshape(-1, values.shape[-1]))
        return transformed.reshape(values.shape).astype(np.float32)

    return transform(train), transform(validation), transform(test), scaler


def prepare_output_schemas(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "predictions").mkdir(exist_ok=True)
    pd.DataFrame(columns=RUN_REGISTRY_COLUMNS).to_csv(
        output_dir / "run_registry.csv", index=False
    )
    pd.DataFrame(columns=METRIC_COLUMNS).to_parquet(
        output_dir / "metrics.parquet", index=False
    )
    pd.DataFrame(columns=SELECTED_CONFIG_COLUMNS).to_csv(
        output_dir / "selected_configs.csv", index=False
    )
    schema = {
        "format": "parquet partitioned by run_id",
        "columns": [
            "run_id",
            "origin_timestamp",
            "machine",
            "outer_fold",
            "lead",
            "y_true",
            "y_pred",
            "segment_id",
        ],
    }
    (output_dir / "predictions" / "_SCHEMA.json").write_text(
        json.dumps(schema, indent=2) + "\n"
    )
