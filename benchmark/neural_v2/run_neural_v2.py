#!/usr/bin/env python3
"""Guarded, resumable scientific neural-v2 execution driver.

The default action is plan-only. Scientific execution requires both explicit
flags and was not invoked during the neural-v2 design/preflight phase.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from .src.data import (
    CONTEXT_LENGTHS,
    FEATURE_SETS,
    FUTURE_LEADS,
    build_windows,
    load_canonical_panel,
    sha256_file,
)
from .src.metrics import per_lead_metrics
from .src.selection import InnerResult, select_context
from .src.splits import build_supported_folds
from .src.training import fit_final_fixed_epochs, fit_inner, predict
from .src.validation import atomic_json_write, completion_is_valid, run_id


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "benchmark/neural_v2/configs/neural_v2.json"
DECISION_PATH = ROOT / "benchmark/neural_v2/NEURAL_V2_DECISION.md"
OUTPUT_ROOT = ROOT / "benchmark/neural_v2/outputs"
EXPECTED_DECISION_SHA256 = (
    "9cec1dc25dc20dd1bf20ac3d7d495f731d41106935a66726d79a182fd058a08c"
)
MODELS = ("DLinear", "LSTM", "TCN-v2", "PatchTST")
MACHINES = tuple(f"machine{number:02d}" for number in range(1, 8))
SEEDS = (0, 1, 2)


def execution_scale() -> dict[str, int]:
    cells = len(MODELS) * len(FEATURE_SETS) * len(MACHINES) * 5
    inner = cells * len(CONTEXT_LENGTHS) * len(SEEDS)
    final = cells * len(SEEDS)
    return {
        "selection_cells": cells,
        "inner_fits": inner,
        "final_fits": final,
        "total_fits": inner + final,
        "final_metric_rows": final * len(FUTURE_LEADS),
    }


def _load_inner(path: Path, expected: dict[str, object]) -> InnerResult | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("status") != "complete" or not all(
        payload.get(key) == value for key, value in expected.items()
    ):
        return None
    return InnerResult(
        context_length=int(payload["context_length"]),
        seed=int(payload["seed"]),
        mae_by_lead=tuple(float(value) for value in payload["mae_by_lead"]),
        best_epoch=int(payload["best_epoch"]),
    )


def _atomic_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(temporary, index=False, engine="pyarrow")
    os.replace(temporary, path)


def _prediction_frame(
    payload: dict[str, object], batch, prediction: np.ndarray
) -> pd.DataFrame:
    rows = []
    for lead_position, lead in enumerate(FUTURE_LEADS):
        for sample_position, sample_id in enumerate(batch.sample_ids):
            rows.append(
                {
                    **payload,
                    "lead": lead,
                    "sample_id": sample_id,
                    "origin_index": int(batch.origin_indices[sample_position]),
                    "origin_timestamp": batch.origin_timestamps[sample_position],
                    "target_timestamp": batch.target_timestamps[
                        sample_position, lead_position
                    ],
                    "y_true": float(batch.y[sample_position, lead_position]),
                    "y_pred": float(prediction[sample_position, lead_position]),
                    "sample_set_hash": batch.sample_set_hash,
                }
            )
    return pd.DataFrame(rows)


def execute() -> None:
    if sha256_file(DECISION_PATH) != EXPECTED_DECISION_SHA256:
        raise RuntimeError("Prospective decision hash changed; refusing execution")
    config_sha256 = sha256_file(CONFIG_PATH)
    panel = load_canonical_panel()
    for model_name in MODELS:
        for feature_set in FEATURE_SETS:
            for machine in MACHINES:
                folds_by_length = {
                    length: build_supported_folds(panel, machine, length)
                    for length in CONTEXT_LENGTHS
                }
                for fold_index in range(5):
                    cell = {
                        "model": model_name,
                        "feature_set": feature_set,
                        "machine": machine,
                        "outer_fold": fold_index + 1,
                    }
                    cell_id = run_id(cell)
                    inner_results = []
                    for length in CONTEXT_LENGTHS:
                        fold = folds_by_length[length][fold_index]
                        train = build_windows(
                            panel,
                            machine,
                            feature_set,
                            length,
                            fold.inner_train_indices,
                        )
                        validation = build_windows(
                            panel,
                            machine,
                            feature_set,
                            length,
                            fold.inner_validation_indices,
                        )
                        for seed in SEEDS:
                            progress_path = (
                                OUTPUT_ROOT
                                / "selection_progress"
                                / cell_id
                                / f"L{length}_seed{seed}.json"
                            )
                            expected = {
                                "config_sha256": config_sha256,
                                "decision_sha256": EXPECTED_DECISION_SHA256,
                                "train_sample_set_hash": train.sample_set_hash,
                                "validation_sample_set_hash": validation.sample_set_hash,
                                "context_length": length,
                                "seed": seed,
                            }
                            completed = _load_inner(progress_path, expected)
                            if completed is None:
                                fitted = fit_inner(
                                    model_name,
                                    length,
                                    train.X.shape[-1],
                                    seed,
                                    train.X,
                                    train.y,
                                    validation.X,
                                    validation.y,
                                )
                                completed = InnerResult(
                                    context_length=length,
                                    seed=seed,
                                    mae_by_lead=tuple(
                                        float(value)
                                        for value in fitted.validation_mae_by_lead
                                    ),
                                    best_epoch=fitted.best_epoch,
                                )
                                atomic_json_write(
                                    progress_path,
                                    {
                                        **expected,
                                        "status": "complete",
                                        "mae_by_lead": list(completed.mae_by_lead),
                                        "best_epoch": completed.best_epoch,
                                    },
                                )
                            inner_results.append(completed)
                    selection = select_context(inner_results)
                    selection_path = (
                        OUTPUT_ROOT / "selections" / f"{cell_id}.json"
                    )
                    atomic_json_write(
                        selection_path,
                        {
                            **cell,
                            "status": "complete",
                            "config_sha256": config_sha256,
                            "decision_sha256": EXPECTED_DECISION_SHA256,
                            "context_length": selection.context_length,
                            "seed_mean_validation_mae": (
                                selection.seed_mean_validation_mae
                            ),
                            "best_epoch_by_seed": selection.best_epoch_by_seed,
                        },
                    )
                    selected_fold = folds_by_length[selection.context_length][
                        fold_index
                    ]
                    outer_train = build_windows(
                        panel,
                        machine,
                        feature_set,
                        selection.context_length,
                        selected_fold.outer_train_indices,
                    )
                    outer_test = build_windows(
                        panel,
                        machine,
                        feature_set,
                        selection.context_length,
                        selected_fold.outer_test_indices,
                    )
                    for seed in SEEDS:
                        final_payload = {
                            **cell,
                            "seed": seed,
                            "context_length": selection.context_length,
                        }
                        final_run_id = run_id(final_payload)
                        prediction_path = (
                            OUTPUT_ROOT / "predictions" / f"{final_run_id}.parquet"
                        )
                        metric_path = (
                            OUTPUT_ROOT / "metrics" / f"{final_run_id}.json"
                        )
                        completion_path = (
                            OUTPUT_ROOT / "completion" / f"{final_run_id}.json"
                        )
                        expected_completion = {
                            "run_id": final_run_id,
                            "config_sha256": config_sha256,
                            "sample_set_hash": outer_test.sample_set_hash,
                        }
                        if completion_is_valid(
                            completion_path, expected_completion
                        ) and prediction_path.exists() and metric_path.exists():
                            continue
                        fitted = fit_final_fixed_epochs(
                            model_name,
                            selection.context_length,
                            outer_train.X.shape[-1],
                            seed,
                            outer_train.X,
                            outer_train.y,
                            selection.best_epoch_by_seed[seed],
                        )
                        prediction = predict(fitted, outer_test.X)
                        frame = _prediction_frame(
                            {"run_id": final_run_id, **final_payload},
                            outer_test,
                            prediction,
                        )
                        _atomic_parquet(prediction_path, frame)
                        metrics = per_lead_metrics(outer_test.y, prediction)
                        atomic_json_write(
                            metric_path,
                            {
                                "run_id": final_run_id,
                                **final_payload,
                                "leads": list(FUTURE_LEADS),
                                **{
                                    key: [float(value) for value in values]
                                    for key, values in metrics.items()
                                },
                            },
                        )
                        atomic_json_write(
                            completion_path,
                            {
                                **expected_completion,
                                "status": "complete",
                                "decision_sha256": EXPECTED_DECISION_SHA256,
                                "prediction_sha256": sha256_file(prediction_path),
                                "metric_sha256": sha256_file(metric_path),
                            },
                        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--acknowledge-scientific-run", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print(json.dumps(execution_scale(), indent=2))
        return
    if not args.acknowledge_scientific_run:
        raise SystemExit(
            "Scientific execution requires --acknowledge-scientific-run"
        )
    execute()


if __name__ == "__main__":
    main()
