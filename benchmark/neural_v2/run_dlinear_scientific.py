#!/usr/bin/env python3
"""Resumable Phase 2B-2A1 DLinear-only scientific execution."""

from __future__ import annotations

import argparse
import json
import os
import platform
import threading
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
import torch

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
OUT = ROOT / "benchmark/neural_v2/outputs/dlinear"
CONFIG = ROOT / "benchmark/neural_v2/configs/neural_v2.json"
DECISION = ROOT / "benchmark/neural_v2/NEURAL_V2_DECISION.md"
INVENTORY = ROOT / "benchmark/neural_v2/NEURAL_V2_ARTIFACT_SHA256.csv"
CRITERIA = ROOT / "benchmark/neural_v2/DLINEAR_DECISION_CRITERIA.md"
EXPECTED_DECISION_HASH = (
    "9cec1dc25dc20dd1bf20ac3d7d495f731d41106935a66726d79a182fd058a08c"
)
FEATURES = ("F0_LOCAL", "F1_THROUGHPUT")
MACHINES = tuple(f"machine{number:02d}" for number in range(1, 8))
SEEDS = (0, 1, 2)


class ProcessMonitor:
    def __init__(self) -> None:
        self.process = psutil.Process()
        self.stop = threading.Event()
        self.peak_rss_bytes = self.process.memory_info().rss
        self.cpu_samples: list[float] = []
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        self.process.cpu_percent(interval=None)
        while not self.stop.wait(0.1):
            self.peak_rss_bytes = max(
                self.peak_rss_bytes, self.process.memory_info().rss
            )
            self.cpu_samples.append(self.process.cpu_percent(interval=None))

    def __enter__(self) -> "ProcessMonitor":
        self.thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.stop.set()
        self.thread.join()
        self.peak_rss_bytes = max(
            self.peak_rss_bytes, self.process.memory_info().rss
        )


def atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    os.replace(temporary, path)


def atomic_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(temporary, index=False, engine="pyarrow")
    os.replace(temporary, path)


def valid_record(path: Path, expected: dict[str, object]) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("status") != "complete":
        return None
    if not all(payload.get(key) == value for key, value in expected.items()):
        return None
    return payload


def valid_final_record(
    completion_path: Path,
    prediction_path: Path,
    metric_path: Path,
    expected: dict[str, object],
) -> dict | None:
    payload = valid_record(completion_path, expected)
    if payload is None or not prediction_path.exists() or not metric_path.exists():
        return None
    if payload.get("prediction_sha256") != sha256_file(prediction_path):
        return None
    if payload.get("metric_sha256") != sha256_file(metric_path):
        return None
    return payload


def prediction_frame(
    run_payload: dict[str, object], batch, prediction: np.ndarray
) -> pd.DataFrame:
    sample_n = len(batch.origin_indices)
    lead_n = len(FUTURE_LEADS)
    return pd.DataFrame(
        {
            **{
                key: np.repeat(value, sample_n * lead_n)
                for key, value in run_payload.items()
            },
            "lead": np.tile(np.asarray(FUTURE_LEADS), sample_n),
            "origin_timestamp": np.repeat(batch.origin_timestamps, lead_n),
            "target_timestamp": batch.target_timestamps.reshape(-1),
            "sample_id": np.repeat(batch.sample_ids, lead_n),
            "origin_index": np.repeat(batch.origin_indices, lead_n),
            "target_index": (
                np.repeat(batch.origin_indices, lead_n)
                + np.tile(np.asarray(FUTURE_LEADS), sample_n)
            ),
            "segment_id": np.repeat(batch.segment_ids, lead_n),
            "y_true": batch.y.reshape(-1),
            "y_pred": prediction.reshape(-1),
            "sample_set_hash": np.repeat(
                batch.sample_set_hash, sample_n * lead_n
            ),
        }
    )


def execute() -> None:
    if sha256_file(DECISION) != EXPECTED_DECISION_HASH:
        raise RuntimeError("Frozen Neural-v2 decision hash differs")
    config_hash = sha256_file(CONFIG)
    inventory_hash = sha256_file(INVENTORY)
    criteria_hash = sha256_file(CRITERIA)
    panel = load_canonical_panel()
    OUT.mkdir(parents=True, exist_ok=True)
    invocation_started = time.perf_counter()
    timestamp_started = datetime.now().astimezone().isoformat()
    inner_phase_started = time.perf_counter()
    selected_rows: list[dict] = []
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
                        "model": "DLinear",
                        "feature_set": feature,
                        "machine": machine,
                        "fold": fold_number,
                    }
                    cell_id = run_id(cell_payload)
                    inner_results: list[InnerResult] = []
                    for length in CONTEXT_LENGTHS:
                        fold = folds_by_length[length][fold_position]
                        train = build_windows(
                            panel,
                            machine,
                            feature,
                            length,
                            fold.inner_train_indices,
                        )
                        validation = build_windows(
                            panel,
                            machine,
                            feature,
                            length,
                            fold.inner_validation_indices,
                        )
                        for seed in SEEDS:
                            progress_path = (
                                OUT
                                / "progress/inner"
                                / f"{cell_id}_L{length}_seed{seed}.json"
                            )
                            expected = {
                                **cell_payload,
                                "context_length": length,
                                "seed": seed,
                                "config_sha256": config_hash,
                                "decision_sha256": EXPECTED_DECISION_HASH,
                                "inner_train_hash": fold.inner_train_hash,
                                "inner_validation_hash": (
                                    fold.inner_validation_hash
                                ),
                                "final_train_hash": fold.outer_train_hash,
                                "test_hash": fold.outer_test_hash,
                            }
                            record = valid_record(progress_path, expected)
                            if record is None:
                                fit_started = time.perf_counter()
                                result = fit_inner(
                                    "DLinear",
                                    length,
                                    train.X.shape[-1],
                                    seed,
                                    train.X,
                                    train.y,
                                    validation.X,
                                    validation.y,
                                    device="cpu",
                                )
                                record = {
                                    **expected,
                                    "status": "complete",
                                    "best_epoch": result.best_epoch,
                                    "best_validation_loss": (
                                        result.best_validation_loss
                                    ),
                                    "validation_mae_by_lead": [
                                        float(value)
                                        for value in result.validation_mae_by_lead
                                    ],
                                    "mean_validation_mae": float(
                                        np.mean(result.validation_mae_by_lead)
                                    ),
                                    "training_epochs_executed": (
                                        result.epochs_trained
                                    ),
                                    "train_seconds": result.train_seconds,
                                    "validation_seconds": (
                                        result.validation_seconds
                                    ),
                                    "fit_wall_seconds": (
                                        time.perf_counter() - fit_started
                                    ),
                                    "parameter_count": parameter_count(
                                        result.model
                                    ),
                                }
                                atomic_json_write(progress_path, record)
                            inner_results.append(
                                InnerResult(
                                    context_length=length,
                                    seed=seed,
                                    mae_by_lead=tuple(
                                        record["validation_mae_by_lead"]
                                    ),
                                    best_epoch=int(record["best_epoch"]),
                                )
                            )
                    selection = select_context(inner_results)
                    selected_fold = folds_by_length[selection.context_length][
                        fold_position
                    ]
                    selected_record = {
                        **cell_payload,
                        "cell_id": cell_id,
                        "selected_L": selection.context_length,
                        "seed_mean_validation_mae": (
                            selection.seed_mean_validation_mae
                        ),
                        "inner_train_hash": selected_fold.inner_train_hash,
                        "inner_validation_hash": (
                            selected_fold.inner_validation_hash
                        ),
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
                            "best_epoch_by_seed": (
                                selection.best_epoch_by_seed
                            ),
                        },
                    )
        inner_phase_wall = time.perf_counter() - inner_phase_started
        atomic_csv(OUT / "selected_contexts.csv", pd.DataFrame(selected_rows))

        final_phase_started = time.perf_counter()
        selected_epochs: list[dict] = []
        for selected in selected_rows:
            feature = selected["feature_set"]
            machine = selected["machine"]
            fold_number = int(selected["fold"])
            length = int(selected["selected_L"])
            fold = build_supported_folds(panel, machine, length)[fold_number - 1]
            outer_train = build_windows(
                panel,
                machine,
                feature,
                length,
                fold.outer_train_indices,
            )
            selection_record = json.loads(
                (
                    OUT
                    / "progress/selections"
                    / f"{selected['cell_id']}.json"
                ).read_text()
            )
            for seed in SEEDS:
                selected_epoch = int(
                    selection_record["best_epoch_by_seed"][str(seed)]
                )
                final_payload = {
                    "model": "DLinear",
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
                completion_path = (
                    OUT / "progress/final" / f"{final_run_id}.json"
                )
                expected = {
                    **final_payload,
                    "run_id": final_run_id,
                    "config_sha256": config_hash,
                    "decision_sha256": EXPECTED_DECISION_HASH,
                    "final_train_hash": fold.outer_train_hash,
                    "test_hash": fold.outer_test_hash,
                }
                completion = valid_final_record(
                    completion_path,
                    prediction_path,
                    metric_path,
                    expected,
                )
                if completion is None:
                    fit_started = time.perf_counter()
                    result = fit_final_fixed_epochs(
                        "DLinear",
                        length,
                        outer_train.X.shape[-1],
                        seed,
                        outer_train.X,
                        outer_train.y,
                        selected_epoch,
                        device="cpu",
                    )
                    fit_wall_seconds = time.perf_counter() - fit_started
                    # Outer-test labels are loaded only after fitting is complete.
                    outer_test = build_windows(
                        panel,
                        machine,
                        feature,
                        length,
                        fold.outer_test_indices,
                    )
                    prediction_started = time.perf_counter()
                    prediction = predict(result, outer_test.X)
                    prediction_seconds = time.perf_counter() - prediction_started
                    frame = prediction_frame(
                        {"run_id": final_run_id, **final_payload},
                        outer_test,
                        prediction,
                    )
                    atomic_parquet(prediction_path, frame)
                    metrics = per_lead_metrics(outer_test.y, prediction)
                    metric_record = {
                        **expected,
                        "status": "complete",
                        "leads": list(FUTURE_LEADS),
                        "mae": [float(value) for value in metrics["mae"]],
                        "rmse": [float(value) for value in metrics["rmse"]],
                        "r2": [float(value) for value in metrics["r2"]],
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
                selected_epochs.append(
                    {
                        **final_payload,
                        "run_id": final_run_id,
                        "selected_epoch": selected_epoch,
                    }
                )
        final_phase_wall = time.perf_counter() - final_phase_started

    inner_records = [
        json.loads(path.read_text())
        for path in sorted((OUT / "progress/inner").glob("*.json"))
    ]
    final_records = [
        json.loads(path.read_text())
        for path in sorted((OUT / "progress/final").glob("*.json"))
    ]
    metric_records = [
        json.loads(path.read_text())
        for path in sorted((OUT / "progress/metrics").glob("*.json"))
    ]
    inner_frame = pd.DataFrame(inner_records)
    atomic_parquet(OUT / "inner_selection_runs.parquet", inner_frame)
    atomic_csv(OUT / "selected_epochs.csv", pd.DataFrame(selected_epochs))

    registry_columns = [
        "run_id",
        "model",
        "feature_set",
        "machine",
        "fold",
        "seed",
        "selected_L",
        "selected_epoch",
        "status",
        "final_train_hash",
        "test_hash",
        "train_sample_count",
        "test_sample_count",
        "prediction_path",
        "prediction_sha256",
        "metric_path",
        "metric_sha256",
    ]
    atomic_csv(
        OUT / "run_registry.csv",
        pd.DataFrame(final_records).loc[:, registry_columns],
    )
    metric_rows = []
    for record in metric_records:
        for position, lead in enumerate(record["leads"]):
            metric_rows.append(
                {
                    key: record[key]
                    for key in (
                        "run_id",
                        "model",
                        "feature_set",
                        "machine",
                        "fold",
                        "seed",
                        "selected_L",
                        "selected_epoch",
                        "test_hash",
                    )
                }
                | {
                    "lead": lead,
                    "mae": record["mae"][position],
                    "rmse": record["rmse"][position],
                    "r2": record["r2"][position],
                }
            )
    atomic_parquet(OUT / "metrics.parquet", pd.DataFrame(metric_rows))
    prediction_bytes = sum(
        path.stat().st_size for path in (OUT / "predictions").glob("*.parquet")
    )
    epochs = inner_frame["best_epoch"].astype(int)
    selected_distribution = (
        pd.DataFrame(selected_rows)
        .groupby(["feature_set", "selected_L"])
        .size()
        .rename("count")
        .reset_index()
        .to_dict(orient="records")
    )
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
        "frozen_inventory_sha256": inventory_hash,
        "decision_criteria_sha256": criteria_hash,
        "inner_fits": len(inner_records),
        "final_runs": len(final_records),
        "metric_rows": len(metric_rows),
        "selected_context_records": len(selected_rows),
        "inner_fit_wall_seconds_sum": float(inner_frame["fit_wall_seconds"].sum()),
        "inner_selection_phase_wall_seconds": inner_phase_wall,
        "final_fit_wall_seconds_sum": float(
            sum(record["fit_wall_seconds"] for record in final_records)
        ),
        "final_refit_phase_wall_seconds": final_phase_wall,
        "execution_wall_seconds": time.perf_counter() - invocation_started,
        "peak_rss_bytes": monitor.peak_rss_bytes,
        "mean_process_cpu_percent": (
            float(np.mean(monitor.cpu_samples)) if monitor.cpu_samples else None
        ),
        "mean_best_epoch_all_inner_fits": float(epochs.mean()),
        "median_best_epoch_all_inner_fits": float(epochs.median()),
        "selected_L_distribution": selected_distribution,
        "prediction_artifact_bytes": prediction_bytes,
        "pilot_central_dlinear_projection_hours": 0.19980739012466953,
    }
    atomic_json_write(OUT / "runtime_accounting.json", runtime)
    print(json.dumps(runtime, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--acknowledge-first-scientific-dlinear", action="store_true"
    )
    args = parser.parse_args()
    if not (args.execute and args.acknowledge_first_scientific_dlinear):
        raise SystemExit(
            "Execution requires --execute and "
            "--acknowledge-first-scientific-dlinear"
        )
    execute()


if __name__ == "__main__":
    main()
