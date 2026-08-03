"""Tests for validation-only ensembles."""

from __future__ import annotations

import numpy as np

from models.ensembles.strategies import ensemble_predict, oof_stacking, simple_mean


def test_simple_mean():
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([3.0, 2.0, 1.0])
    np.testing.assert_allclose(simple_mean([a, b]), [2.0, 2.0, 2.0])


def test_inverse_mae_prefers_better():
    y = np.array([0.0, 0.0, 0.0, 0.0])
    good = np.array([0.1, -0.1, 0.0, 0.0])
    bad = np.array([2.0, 2.0, 2.0, 2.0])
    out = ensemble_predict("inverse_mae", [good, bad], y_val=y, preds_val=[good, bad])
    assert out["weights"][0] > out["weights"][1]


def test_stacking_rejects_small_n():
    y = np.ones(50)
    preds = [y + 0.1, y - 0.1]
    w, meta = oof_stacking(y, preds, min_samples=200)
    assert meta["accepted"] is False
    np.testing.assert_allclose(w, [0.5, 0.5])
