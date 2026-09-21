from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from benchmark.src.selection import (
    lightgbm_configurations,
    ridge_configurations,
    select_from_inner_validation,
)
from benchmark.src.splits import (
    build_inner_split,
    build_outer_folds,
    validate_against_phase1c,
)
from benchmark.src.validation import deterministic_run_id, train_only_scaled
from benchmark.src.windows import joint_eligible_origins


def test_phase1c_boundary_equivalence(panel):
    result = validate_against_phase1c(panel)
    assert result == {"checked": 280, "failures": 0, "pass": True}


def test_five_nonoverlapping_expanding_outer_folds(panel):
    eligible = joint_eligible_origins(panel, "machine01")
    folds = build_outer_folds(panel, eligible)
    assert len(folds) == 5
    assert all(
        len(folds[index].train_indices) < len(folds[index + 1].train_indices)
        for index in range(4)
    )
    test_sets = [set(fold.test_indices.tolist()) for fold in folds]
    assert all(
        test_sets[left].isdisjoint(test_sets[right])
        for left in range(5)
        for right in range(left + 1, 5)
    )


def test_outer_and_inner_target_time_purge(panel):
    eligible = joint_eligible_origins(panel, "machine01")
    outer = build_outer_folds(panel, eligible)[0]
    timestamps = panel.timestamp.to_numpy()
    assert np.all(
        timestamps[outer.train_indices + 128] < outer.first_test_origin_timestamp
    )
    inner = build_inner_split(panel, outer.train_indices)
    assert np.all(
        timestamps[inner.train_indices + 128]
        < inner.first_validation_origin_timestamp
    )
    assert len(inner.validation_indices) > 0


def test_train_only_scaling():
    train = np.asarray([[[0.0]], [[2.0]]], dtype=np.float32)
    validation = np.asarray([[[100.0]]], dtype=np.float32)
    test = np.asarray([[[200.0]]], dtype=np.float32)
    scaled_train, scaled_validation, scaled_test, scaler = train_only_scaled(
        train, validation, test
    )
    assert scaler.mean_[0] == 1.0
    assert np.isclose(scaled_train.mean(), 0)
    assert scaled_validation.item() == 99.0
    assert scaled_test.item() == 199.0


def test_frozen_configuration_grids():
    assert len(ridge_configurations()) == 15
    assert len(lightgbm_configurations()) == 24


def test_selection_rejects_outer_test_columns():
    scores = pd.DataFrame(
        {
            "context_length": [32],
            "alpha": [1.0],
            "inner_validation_mae": [1.0],
            "outer_test_mae": [0.5],
        }
    )
    with pytest.raises(ValueError, match="forbidden"):
        select_from_inner_validation(scores, "Ridge")


def test_deterministic_run_ids():
    arguments = ("Ridge", "F1_THROUGHPUT", "machine01", 1, 64, {"alpha": 1.0}, None)
    assert deterministic_run_id(*arguments) == deterministic_run_id(*arguments)
    changed = deterministic_run_id(
        "Ridge", "F1_THROUGHPUT", "machine01", 2, 64, {"alpha": 1.0}, None
    )
    assert changed != deterministic_run_id(*arguments)
