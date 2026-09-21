"""MASE edge-case policy tests."""

from __future__ import annotations

import numpy as np
import pytest

from timetrack.metrics import (
    MASE_SCALE_EPS,
    compute_metrics,
    mase,
    mase_result,
    naive_scale,
    nanmean_valid,
)


def test_constant_series_undefined_mase():
    y_train = np.ones(50)
    r = mase_result(np.ones(10), np.ones(10) * 1.1, y_train)
    assert r["mase_valid"] is False
    assert r["mase_invalid_reason"] == "zero_naive_scale"
    assert np.isnan(r["mase"])
    assert np.isfinite(r["nmae_train_range"]) or np.isnan(r["nmae_train_range"])  # range 0 → nan


def test_near_constant_below_eps_undefined():
    y_train = np.full(40, 5.0)
    y_train[0] = 5.0 + 1e-15
    r = mase_result(np.full(5, 5.0), np.full(5, 5.1), y_train, scale_eps=1e-12)
    assert r["mase_valid"] is False
    assert np.isnan(r["mase"])
    assert r["mase_invalid_reason"] in {"zero_naive_scale", "near_zero_naive_scale"}


def test_one_observation_series():
    r = naive_scale(np.array([1.0]))
    assert r["valid"] is False
    assert r["reason"] == "insufficient_observations"
    assert np.isnan(mase(np.array([1.0]), np.array([2.0]), np.array([1.0])))


def test_missing_values_in_train_use_finite_pairs():
    y_train = np.arange(100, dtype=float)
    y_train[10:15] = np.nan
    scale = naive_scale(y_train)
    assert scale["valid"] is True
    assert scale["n_pairs"] == 93
    r = mase_result(np.array([1.0, 2.0]), np.array([1.5, 2.5]), y_train)
    assert r["mase_valid"] is True
    assert np.isfinite(r["mase"])
    assert r["mase_scale"] > 0


def test_all_missing_train():
    y_train = np.full(20, np.nan)
    r = naive_scale(y_train)
    assert r["valid"] is False
    assert r["reason"] == "insufficient_finite_pairs"


def test_per_fold_denominator_isolation():
    """Different train folds must yield different scales (no reuse)."""
    rng = np.random.default_rng(0)
    fold0 = rng.normal(scale=1.0, size=200)
    fold1 = rng.normal(scale=5.0, size=200)
    s0 = naive_scale(fold0)["scale"]
    s1 = naive_scale(fold1)["scale"]
    assert s1 > s0 * 2


def test_held_out_entity_isolation():
    """Scale for machine A must not use machine B values."""
    a = np.linspace(0, 10, 100)
    b = np.linspace(0, 1000, 100)
    sa = naive_scale(a)["scale"]
    mixed = np.concatenate([a, b])
    sm = naive_scale(mixed)["scale"]
    assert sa != sm
    # caller responsibility: pass only held-in / allowed train; API itself is series-local
    assert naive_scale(a)["scale"] == pytest.approx(sa)


def test_normal_valid_series():
    rng = np.random.default_rng(1)
    y_train = np.cumsum(rng.normal(size=300))
    y_true = y_train[-50:] + rng.normal(scale=0.1, size=50)
    y_pred = y_true + 0.05
    r = mase_result(y_true, y_pred, y_train)
    assert r["mase_valid"] is True
    assert np.isfinite(r["mase"])
    assert np.isfinite(r["rmsse"])
    assert r["mase_invalid_reason"] == ""
    assert mase(y_true, y_pred, y_train) == pytest.approx(r["mase"])


def test_compute_metrics_includes_validity_flags():
    y_train = np.ones(30)
    out = compute_metrics(np.ones(5), np.zeros(5), y_train=y_train)
    assert out["mase_valid"] is False
    assert np.isnan(out["mase"])
    assert out["mae"] == 1.0


def test_nanmean_valid_excludes_invalid():
    vals = np.array([1.0, np.nan, 3.0, 100.0])
    valid = np.array([True, True, True, False])
    assert nanmean_valid(vals, valid) == pytest.approx(2.0)
    assert np.isnan(nanmean_valid(np.array([np.nan, np.nan])))
