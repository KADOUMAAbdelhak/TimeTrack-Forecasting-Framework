"""Tests for block bootstrap and conformal intervals."""

from __future__ import annotations

import numpy as np

from models import forecasting as F
from timetrack.stats_bootstrap import block_bootstrap_mean_diff


def test_block_bootstrap_paired():
    rng = np.random.default_rng(0)
    a = rng.normal(size=500)
    b = a - 0.2 + rng.normal(scale=0.05, size=500)
    out = block_bootstrap_mean_diff(np.abs(a), np.abs(b), block_size=20, n_boot=200, seed=0)
    assert out["n"] == 500
    assert np.isfinite(out["ci_low"])


def test_conformal_ridge_intervals():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(200, 16))
    y = X[:, -1] + rng.normal(scale=0.1, size=200)
    m = F.build_model("conformal_ridge", horizon=1, context_length=16, seed=0, alpha=0.1)
    m.fit(X[:150], y[:150], X[150:180], y[150:180])
    iv = m.predict_interval(X[180:])
    assert iv["lower"].shape == iv["point"].shape
    assert np.all(iv["upper"] >= iv["lower"])
