from __future__ import annotations

import inspect

import numpy as np

from benchmark.neural_v2.src.selection import InnerResult, select_context
from benchmark.neural_v2.src.training import (
    FeatureStandardizer,
    fit_final_fixed_epochs,
    fit_inner,
    predict,
)


def synthetic_data(seed: int = 7):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(48, 32, 1)).astype(np.float32)
    y = np.repeat(X[:, -1, :], 8, axis=1).astype(np.float32)
    return X, y


def test_transform_is_fit_on_training_only():
    X, _ = synthetic_data()
    scaler = FeatureStandardizer.fit(X[:32])
    expected = X[:32].mean(axis=(0, 1), keepdims=True)
    assert np.array_equal(scaler.mean, expected)
    extreme_validation = X[32:] + 1_000_000
    scaler.transform(extreme_validation)
    assert np.array_equal(scaler.mean, expected)


def test_deterministic_seed_initialization():
    X, y = synthetic_data()
    first = fit_inner(
        "DLinear", 32, 1, 0, X[:32], y[:32], X[32:], y[32:], fixed_epochs=1
    )
    second = fit_inner(
        "DLinear", 32, 1, 0, X[:32], y[:32], X[32:], y[32:], fixed_epochs=1
    )
    assert np.array_equal(predict(first, X[32:]), predict(second, X[32:]))


def test_seed_mean_context_selection_and_tie_break():
    rows = []
    for context in (32, 64, 128):
        for seed in (0, 1, 2):
            score = 1.0 if context in (32, 64) else 2.0
            rows.append(InnerResult(context, seed, (score,) * 8, 3 + seed))
    selection = select_context(rows)
    assert selection.context_length == 32
    assert selection.best_epoch_by_seed == {0: 3, 1: 4, 2: 5}


def test_selection_rejects_missing_seed():
    rows = [
        InnerResult(context, seed, (1.0,) * 8, 1)
        for context in (32, 64, 128)
        for seed in (0, 1)
    ]
    try:
        select_context(rows)
    except ValueError as error:
        assert "seeds" in str(error)
    else:
        raise AssertionError("Selection accepted an incomplete seed set")


def test_per_seed_best_epoch_is_recorded():
    X, y = synthetic_data()
    result = fit_inner(
        "DLinear", 32, 1, 2, X[:32], y[:32], X[32:], y[32:], fixed_epochs=2
    )
    assert result.epochs_trained == 2
    assert 1 <= result.best_epoch <= 2


def test_outer_retrain_uses_exact_fixed_epoch_count():
    X, y = synthetic_data()
    result = fit_final_fixed_epochs("DLinear", 32, 1, 1, X, y, epoch_count=3)
    assert result.epochs_trained == 3
    assert result.best_epoch == 3
    assert result.validation_seconds == 0.0


def test_outer_retrain_api_has_no_test_or_validation_inputs():
    parameters = inspect.signature(fit_final_fixed_epochs).parameters
    assert not any("test" in name or "validation" in name for name in parameters)
