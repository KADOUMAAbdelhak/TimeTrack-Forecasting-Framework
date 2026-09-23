from __future__ import annotations

import json

import numpy as np

from benchmark.neural_v2.src.metrics import matched_gains, per_lead_metrics, seed_summary
from benchmark.neural_v2.src.validation import (
    METRIC_COLUMNS,
    PREDICTION_COLUMNS,
    atomic_json_write,
    completion_is_valid,
    run_id,
)
from benchmark.neural_v2.run_neural_v2 import execution_scale


def test_metric_and_prediction_schema():
    assert len(PREDICTION_COLUMNS) == len(set(PREDICTION_COLUMNS))
    assert len(METRIC_COLUMNS) == len(set(METRIC_COLUMNS))
    assert {"seed", "lead", "sample_set_hash", "y_true", "y_pred"}.issubset(
        PREDICTION_COLUMNS
    )
    assert {"mae", "rmse", "r2"}.issubset(METRIC_COLUMNS)


def test_metrics_and_exact_matched_gains():
    truth = np.tile(np.arange(8, dtype=float), (4, 1))
    f0 = per_lead_metrics(truth, truth + 2)
    f1 = per_lead_metrics(truth, truth + 1)
    gains = matched_gains(f0, f1)
    assert np.allclose(gains["mae_gain_pct"], 50.0)
    assert np.allclose(gains["rmse_gain_pct"], 50.0)


def test_seed_summary_retains_robustness_fields():
    summary = seed_summary(np.asarray([[1.0, -1.0], [2.0, 1.0], [3.0, 2.0]]))
    assert np.array_equal(summary["positive_seed_count"], [3, 2])
    assert np.allclose(summary["mean"], [2.0, 2.0 / 3.0])


def test_run_ids_are_unique_and_stable():
    base = {
        "model": "DLinear",
        "feature_set": "F0_LOCAL",
        "machine": "machine01",
        "fold": 1,
        "seed": 0,
        "context_length": 64,
    }
    assert run_id(base) == run_id(dict(reversed(list(base.items()))))
    changed = dict(base, seed=1)
    assert run_id(base) != run_id(changed)


def test_atomic_completion_validation(tmp_path):
    path = tmp_path / "completion.json"
    payload = {
        "run_id": "abc",
        "status": "complete",
        "prediction_sha256": "p",
        "metric_sha256": "m",
        "sample_set_hash": "s",
        "config_sha256": "c",
    }
    atomic_json_write(path, payload)
    assert json.loads(path.read_text()) == payload
    assert completion_is_valid(path, {"run_id": "abc", "config_sha256": "c"})
    assert not completion_is_valid(path, {"run_id": "different"})


def test_exact_full_execution_scale():
    assert execution_scale() == {
        "selection_cells": 280,
        "inner_fits": 2520,
        "final_fits": 840,
        "total_fits": 3360,
        "final_metric_rows": 6720,
    }
