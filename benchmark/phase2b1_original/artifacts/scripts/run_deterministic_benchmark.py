#!/usr/bin/env python3
"""Execute the frozen B0-B2 benchmark without modifying Phase 2A sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from benchmark.src.data import load_canonical_panel
from benchmark.src.features import FEATURE_SET_IDS, feature_columns
from benchmark.src.metrics import per_lead_metrics
from benchmark.src.models.lightgbm_model import LightGBMForecaster
from benchmark.src.models.ridge import RidgeForecaster
from benchmark.src.selection import (
    lightgbm_configurations,
    ridge_configurations,
    select_from_inner_validation,
)
from benchmark.src.splits import build_inner_split, build_outer_folds
from benchmark.src.validation import deterministic_run_id
from benchmark.src.windows import (
    FUTURE_LEADS,
    finite_feature_origins,
    joint_eligible_origins,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "benchmark" / "outputs"
PREDICTIONS = OUTPUTS / "predictions"
CHECKPOINTS = Path("/tmp/timetrack_phase2b1_0b426927")
MACHINES = [f"machine{number:02d}" for number in range(1, 8)]
MODEL_ORDER = {"Persistence": 0, "Ridge": 1, "LightGBM": 2}
TIE_RULES = {
    "Ridge": "inner MAE, shorter L, smaller alpha",
    "LightGBM": (
        "inner MAE, shorter L, smaller num_leaves, lower learning_rate, "
        "fewer n_estimators"
    ),
}


def index_hash(indices: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(indices, dtype="<i8").tobytes()).hexdigest()


def arrays(
    panel: pd.DataFrame,
    machine: str,
    feature_set: str,
    context_length: int,
    indices: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    features = feature_columns(machine, feature_set)
    values = panel[features].to_numpy(dtype=np.float32)
    history_positions = indices[:, None] - np.arange(
        context_length - 1, -1, -1, dtype=np.int64
    )
    X = values[history_positions]
    target = panel[f"{machine}__cpu_utilization"].to_numpy(dtype=np.float32)
    y = target[indices[:, None] + np.asarray(FUTURE_LEADS)]
    if not np.isfinite(X).all() or not np.isfinite(y).all():
        raise RuntimeError("Non-finite values passed to a benchmark model")
    return X, y


def prediction_frame(
    panel: pd.DataFrame,
    run_id: str,
    model: str,
    feature_set: str,
    machine: str,
    fold: int,
    indices: np.ndarray,
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> pd.DataFrame:
    if y_true.shape != y_pred.shape or y_true.shape[1] != len(FUTURE_LEADS):
        raise RuntimeError("Prediction shape does not match the frozen target vector")
    timestamps = panel["timestamp"].to_numpy()
    segment = panel["segment_id"].to_numpy()
    leads = np.asarray(FUTURE_LEADS, dtype=np.int16)
    repeated_indices = np.repeat(indices, len(leads))
    return pd.DataFrame(
        {
            "run_id": run_id,
            "model": model,
            "feature_set": feature_set,
            "machine": machine,
            "fold": np.int8(fold),
            "lead": np.tile(leads, len(indices)),
            "sample_id": [
                f"{machine}:{origin}" for origin in repeated_indices.tolist()
            ],
            "origin_index": repeated_indices,
            "origin_timestamp": np.repeat(timestamps[indices], len(leads)),
            "target_index": (
                indices[:, None] + leads.astype(np.int64)
            ).reshape(-1),
            "target_timestamp": timestamps[
                indices[:, None] + leads.astype(np.int64)
            ].reshape(-1),
            "segment_id": np.repeat(segment[indices], len(leads)),
            "y_true": y_true.reshape(-1),
            "y_pred": y_pred.reshape(-1),
        }
    )


def write_prediction(frame: pd.DataFrame, run_id: str) -> str:
    PREDICTIONS.mkdir(parents=True, exist_ok=True)
    destination = PREDICTIONS / f"{run_id}.parquet"
    temporary = destination.with_suffix(".tmp.parquet")
    frame.to_parquet(
        temporary,
        index=False,
        compression="zstd",
        use_dictionary=["run_id", "model", "feature_set", "machine", "lead"],
    )
    temporary.replace(destination)
    return str(destination.relative_to(ROOT))


def metric_records(
    run_id: str,
    machine: str,
    fold: int,
    model: str,
    feature_set: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    sample_hash: str,
) -> list[dict[str, Any]]:
    metrics = per_lead_metrics(y_true, y_pred)
    records = []
    for row in metrics.itertuples(index=False):
        records.append(
            {
                "run_id": run_id,
                "machine": machine,
                "outer_fold": fold,
                "lead": int(row.lead),
                "model": model,
                "feature_set": feature_set,
                "seed": None,
                "mae": float(row.mae),
                "rmse": float(row.rmse),
                "r2": float(row.r2),
                "mae_change_vs_persistence_pct": None,
                "mae_change_vs_same_model_f0_pct": None,
                "n_samples": int(len(y_true)),
                "sample_set_hash": sample_hash,
            }
        )
    return records


def save_run(
    panel: pd.DataFrame,
    machine: str,
    fold: int,
    model: str,
    feature_set: str,
    context_length: int,
    config: dict[str, Any],
    indices: np.ndarray,
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    run_id = deterministic_run_id(
        model=model,
        feature_set=feature_set,
        machine=machine,
        outer_fold=fold,
        context_length=context_length,
        config=config,
        seed=None,
    )
    sample_hash = index_hash(indices)
    frame = prediction_frame(
        panel,
        run_id,
        model,
        feature_set,
        machine,
        fold,
        indices,
        y_true,
        y_pred,
    )
    prediction_path = write_prediction(frame, run_id)
    registry = {
        "run_id": run_id,
        "model": model,
        "feature_set": feature_set,
        "machine": machine,
        "outer_fold": fold,
        "context_length": context_length,
        "config_json": json.dumps(config, sort_keys=True, separators=(",", ":")),
        "seed": None,
        "status": "completed",
        "train_sample_count": None,
        "test_sample_count": int(len(indices)),
        "test_sample_set_hash": sample_hash,
        "prediction_path": prediction_path,
    }
    return registry, metric_records(
        run_id,
        machine,
        fold,
        model,
        feature_set,
        y_true,
        y_pred,
        sample_hash,
    )


def select_ridge(
    panel: pd.DataFrame,
    machine: str,
    feature_set: str,
    inner_train: np.ndarray,
    inner_validation: np.ndarray,
) -> tuple[pd.Series, int, int]:
    score_rows = []
    fit_count = 0
    for context_length in (32, 64, 128):
        train_indices = finite_feature_origins(
            panel, machine, feature_set, context_length, inner_train
        )
        validation_indices = finite_feature_origins(
            panel, machine, feature_set, context_length, inner_validation
        )
        X_train, y_train = arrays(
            panel, machine, feature_set, context_length, train_indices
        )
        X_validation, y_validation = arrays(
            panel, machine, feature_set, context_length, validation_indices
        )
        flattened_train = X_train.reshape(len(X_train), -1)
        flattened_validation = X_validation.reshape(len(X_validation), -1)
        scaler = StandardScaler()
        scaled_train = scaler.fit_transform(flattened_train)
        scaled_validation = scaler.transform(flattened_validation)
        for alpha in (0.01, 0.1, 1.0, 10.0, 100.0):
            model = Ridge(alpha=alpha)
            model.fit(scaled_train, y_train)
            prediction = model.predict(scaled_validation)
            score_rows.append(
                {
                    "context_length": context_length,
                    "alpha": alpha,
                    "inner_validation_mae": float(
                        np.mean(np.abs(y_validation - prediction))
                    ),
                    "inner_train_n": len(train_indices),
                    "inner_validation_n": len(validation_indices),
                    "inner_train_hash": index_hash(train_indices),
                    "inner_validation_hash": index_hash(validation_indices),
                }
            )
            fit_count += 1
    scores = pd.DataFrame(score_rows)
    tie_count = int(
        scores["inner_validation_mae"].eq(scores["inner_validation_mae"].min()).sum()
    )
    return select_from_inner_validation(scores, "Ridge"), fit_count, tie_count


def select_lightgbm(
    panel: pd.DataFrame,
    machine: str,
    feature_set: str,
    inner_train: np.ndarray,
    inner_validation: np.ndarray,
) -> tuple[pd.Series, int, int]:
    score_rows = []
    fit_count = 0
    configurations = lightgbm_configurations()
    for context_length in (32, 64, 128):
        train_indices = finite_feature_origins(
            panel, machine, feature_set, context_length, inner_train
        )
        validation_indices = finite_feature_origins(
            panel, machine, feature_set, context_length, inner_validation
        )
        X_train, y_train = arrays(
            panel, machine, feature_set, context_length, train_indices
        )
        X_validation, y_validation = arrays(
            panel, machine, feature_set, context_length, validation_indices
        )
        for config in (
            value
            for value in configurations
            if value["context_length"] == context_length
        ):
            model = LightGBMForecaster(
                num_leaves=int(config["num_leaves"]),
                learning_rate=float(config["learning_rate"]),
                n_estimators=int(config["n_estimators"]),
            )
            model.fit(X_train, y_train)
            prediction = model.predict(X_validation)
            score_rows.append(
                {
                    **config,
                    "inner_validation_mae": float(
                        np.mean(np.abs(y_validation - prediction))
                    ),
                    "inner_train_n": len(train_indices),
                    "inner_validation_n": len(validation_indices),
                    "inner_train_hash": index_hash(train_indices),
                    "inner_validation_hash": index_hash(validation_indices),
                }
            )
            fit_count += len(FUTURE_LEADS)
    scores = pd.DataFrame(score_rows)
    tie_count = int(
        scores["inner_validation_mae"].eq(scores["inner_validation_mae"].min()).sum()
    )
    return select_from_inner_validation(scores, "LightGBM"), fit_count, tie_count


def selected_record(
    selected: pd.Series,
    model: str,
    feature_set: str,
    machine: str,
    fold: int,
    candidate_count: int,
    tie_count: int,
) -> dict[str, Any]:
    if model == "Ridge":
        config = {"alpha": float(selected["alpha"])}
    else:
        config = {
            "num_leaves": int(selected["num_leaves"]),
            "learning_rate": float(selected["learning_rate"]),
            "n_estimators": int(selected["n_estimators"]),
        }
    return {
        "model": model,
        "feature_set": feature_set,
        "machine": machine,
        "outer_fold": fold,
        "context_length": int(selected["context_length"]),
        "config_json": json.dumps(config, sort_keys=True, separators=(",", ":")),
        "selection_metric": "mean_eight_lead_inner_validation_mae",
        "inner_validation_mae": float(selected["inner_validation_mae"]),
        "candidate_configuration_count": candidate_count,
        "exact_minimum_tie_count": tie_count,
        "tie_break_rule": TIE_RULES[model],
        "inner_train_n": int(selected["inner_train_n"]),
        "inner_validation_n": int(selected["inner_validation_n"]),
        "inner_train_sample_set_hash": selected["inner_train_hash"],
        "inner_validation_sample_set_hash": selected["inner_validation_hash"],
        "outer_test_columns_available_to_selector": False,
    }


def process_machine(family: str, machine: str) -> dict[str, Any]:
    started = time.perf_counter()
    panel = load_canonical_panel()
    eligible = joint_eligible_origins(panel, machine)
    folds = build_outer_folds(panel, eligible)
    registries: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    selected_configs: list[dict[str, Any]] = []
    candidate_fits = 0
    final_models = 0
    for outer in folds:
        inner = build_inner_split(panel, outer.train_indices)
        for feature_set in FEATURE_SET_IDS:
            if family == "Persistence":
                evaluation_indices = finite_feature_origins(
                    panel,
                    machine,
                    feature_set,
                    128,
                    outer.test_indices,
                )
                _, y_test = arrays(
                    panel, machine, feature_set, 128, evaluation_indices
                )
                target = panel[f"{machine}__cpu_utilization"].to_numpy(
                    dtype=np.float32
                )
                prediction = np.repeat(
                    target[evaluation_indices, None], len(FUTURE_LEADS), axis=1
                )
                registry, run_metrics = save_run(
                    panel,
                    machine,
                    outer.fold,
                    family,
                    feature_set,
                    0,
                    {},
                    evaluation_indices,
                    y_test,
                    prediction,
                )
                registry["train_sample_count"] = 0
            else:
                if family == "Ridge":
                    selected, fits, tie_count = select_ridge(
                        panel,
                        machine,
                        feature_set,
                        inner.train_indices,
                        inner.validation_indices,
                    )
                    candidate_count = len(ridge_configurations())
                elif family == "LightGBM":
                    selected, fits, tie_count = select_lightgbm(
                        panel,
                        machine,
                        feature_set,
                        inner.train_indices,
                        inner.validation_indices,
                    )
                    candidate_count = len(lightgbm_configurations())
                else:
                    raise KeyError(family)
                candidate_fits += fits
                context_length = int(selected["context_length"])
                train_indices = finite_feature_origins(
                    panel,
                    machine,
                    feature_set,
                    context_length,
                    outer.train_indices,
                )
                test_indices = finite_feature_origins(
                    panel,
                    machine,
                    feature_set,
                    context_length,
                    outer.test_indices,
                )
                X_train, y_train = arrays(
                    panel, machine, feature_set, context_length, train_indices
                )
                X_test, y_test = arrays(
                    panel, machine, feature_set, context_length, test_indices
                )
                if family == "Ridge":
                    config = {"alpha": float(selected["alpha"])}
                    final_model = RidgeForecaster(alpha=config["alpha"])
                    final_models += 1
                else:
                    config = {
                        "num_leaves": int(selected["num_leaves"]),
                        "learning_rate": float(selected["learning_rate"]),
                        "n_estimators": int(selected["n_estimators"]),
                    }
                    final_model = LightGBMForecaster(**config)
                    final_models += len(FUTURE_LEADS)
                final_model.fit(X_train, y_train)
                prediction = final_model.predict(X_test)
                registry, run_metrics = save_run(
                    panel,
                    machine,
                    outer.fold,
                    family,
                    feature_set,
                    context_length,
                    config,
                    test_indices,
                    y_test,
                    prediction,
                )
                registry["train_sample_count"] = int(len(train_indices))
                selected_configs.append(
                    selected_record(
                        selected,
                        family,
                        feature_set,
                        machine,
                        outer.fold,
                        candidate_count,
                        tie_count,
                    )
                )
            registries.append(registry)
            metrics.extend(run_metrics)
    return {
        "family": family,
        "machine": machine,
        "registry": registries,
        "metrics": metrics,
        "selected_configs": selected_configs,
        "candidate_fits": candidate_fits,
        "final_models": final_models,
        "runtime_seconds": time.perf_counter() - started,
        "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
    }


def checkpoint_path(family: str, machine: str) -> Path:
    return CHECKPOINTS / f"{family}_{machine}.json"


def write_checkpoint(result: dict[str, Any]) -> None:
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    destination = checkpoint_path(result["family"], result["machine"])
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, separators=(",", ":")))
    temporary.replace(destination)


def load_checkpoints() -> list[dict[str, Any]]:
    results = []
    for family in MODEL_ORDER:
        for machine in MACHINES:
            path = checkpoint_path(family, machine)
            if path.exists():
                results.append(json.loads(path.read_text()))
    return results


def consolidate() -> None:
    results = load_checkpoints()
    registry = pd.DataFrame(
        [row for result in results for row in result["registry"]]
    )
    metrics = pd.DataFrame([row for result in results for row in result["metrics"]])
    selected = pd.DataFrame(
        [row for result in results for row in result["selected_configs"]]
    )
    if len(registry):
        registry["_model_order"] = registry["model"].map(MODEL_ORDER)
        registry = registry.sort_values(
            ["_model_order", "machine", "outer_fold", "feature_set"]
        ).drop(columns="_model_order")
    if len(metrics):
        metrics["_model_order"] = metrics["model"].map(MODEL_ORDER)
        metrics = metrics.sort_values(
            ["_model_order", "machine", "outer_fold", "feature_set", "lead"]
        ).drop(columns="_model_order")
    if len(selected):
        selected["_model_order"] = selected["model"].map(MODEL_ORDER)
        selected = selected.sort_values(
            ["_model_order", "machine", "outer_fold", "feature_set"]
        ).drop(columns="_model_order")
    registry.to_csv(OUTPUTS / "run_registry.csv", index=False)
    metrics.to_parquet(OUTPUTS / "metrics.parquet", index=False, compression="zstd")
    selected.to_csv(OUTPUTS / "selected_configs.csv", index=False)
    runtime_path = OUTPUTS / "deterministic_runtime.json"
    previous_families = {}
    if runtime_path.exists():
        previous_families = json.loads(runtime_path.read_text()).get("families", {})
    runtime = {
        "families": {
            family: {
                "completed_machines": sum(
                    result["family"] == family for result in results
                ),
                "worker_runtime_seconds_sum": sum(
                    result["runtime_seconds"]
                    for result in results
                    if result["family"] == family
                ),
                "candidate_fits": sum(
                    result["candidate_fits"]
                    for result in results
                    if result["family"] == family
                ),
                "final_models": sum(
                    result["final_models"]
                    for result in results
                    if result["family"] == family
                ),
                "peak_worker_rss_bytes": max(
                    (
                        result["peak_rss_bytes"]
                        for result in results
                        if result["family"] == family
                    ),
                    default=0,
                ),
                **(
                    {
                        "wall_runtime_seconds": previous_families[family][
                            "wall_runtime_seconds"
                        ]
                    }
                    if family in previous_families
                    and "wall_runtime_seconds" in previous_families[family]
                    else {}
                ),
            }
            for family in MODEL_ORDER
        },
        "registered_runs": len(registry),
        "metric_rows": len(metrics),
    }
    runtime_path.write_text(json.dumps(runtime, indent=2) + "\n")


def execute_family(family: str, workers: int) -> None:
    pending = [
        machine
        for machine in MACHINES
        if not checkpoint_path(family, machine).exists()
    ]
    if not pending:
        print(f"{family}: all machine checkpoints already exist", flush=True)
        consolidate()
        return
    started = time.perf_counter()
    context = get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as executor:
        futures = {
            executor.submit(process_machine, family, machine): machine
            for machine in pending
        }
        for future in as_completed(futures):
            machine = futures[future]
            result = future.result()
            write_checkpoint(result)
            print(
                f"{family} {machine}: 30 runs completed in "
                f"{result['runtime_seconds']:.1f}s",
                flush=True,
            )
            consolidate()
    elapsed = time.perf_counter() - started
    runtime_path = OUTPUTS / "deterministic_runtime.json"
    runtime = json.loads(runtime_path.read_text())
    runtime["families"][family]["wall_runtime_seconds"] = elapsed
    runtime_path.write_text(json.dumps(runtime, indent=2) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--family",
        required=True,
        choices=list(MODEL_ORDER),
    )
    parser.add_argument("--workers", type=int, default=min(7, os.cpu_count() or 1))
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    execute_family(arguments.family, arguments.workers)
