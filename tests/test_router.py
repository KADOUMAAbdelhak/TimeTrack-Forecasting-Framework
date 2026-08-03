"""Tests for validation-only routers and mixtures."""

from __future__ import annotations

import numpy as np

from models.ensembles.constrained_mixture import apply_mixture, fit_constrained_mixture
from models.ensembles.gating_features import gating_feature_vector
from models.ensembles.router import RegimeRouter, RouterConfig, StaticRouter, oracle_selector


def test_static_router_deterministic():
    cfg = RouterConfig(constituent_names=("a", "b"), seed=0)
    key = ("t", 1)
    y = np.array([0.0, 0.0, 0.0, 1.0])
    preds = {"a": np.array([0.0, 0.0, 0.0, 0.0]), "b": np.array([1.0, 1.0, 1.0, 1.0])}
    r1 = StaticRouter(cfg).fit([key], {key: y}, {key: preds})
    r2 = StaticRouter(cfg).fit([key], {key: y}, {key: preds})
    assert r1.selection_[key] == r2.selection_[key] == "a"


def test_mixture_weights_constraints():
    y = np.linspace(0, 1, 200)
    preds = [y + 0.1, y - 0.05, y + 0.2]
    out = fit_constrained_mixture(y, preds, min_samples=50)
    w = out["weights"]
    assert np.all(w >= -1e-12)
    assert abs(w.sum() - 1.0) < 1e-8
    p = apply_mixture(preds, w)
    assert p.shape == y.shape


def test_gating_no_future_feature():
    ctx = np.arange(32, dtype=float)
    g = gating_feature_vector(ctx, hour=10, is_weekend=0)
    assert g.shape[0] >= 8
    assert np.isfinite(g).all()


def test_oracle_is_upper_bound_not_deployable():
    y = np.array([0.0, 1.0, 2.0])
    preds = {"a": np.array([0.0, 0.0, 0.0]), "b": np.array([9.0, 1.0, 2.0])}
    p, sel = oracle_selector(y, preds)
    assert np.allclose(p, [0.0, 1.0, 2.0])
    assert list(sel) == ["a", "b", "b"]


def test_regime_router_fallback_small_n():
    cfg = RouterConfig(constituent_names=("a", "b"), min_val_samples=100, seed=0)
    key = ("t", 1)
    y = np.ones(20)
    X = np.random.default_rng(0).normal(size=(20, 8))
    preds = {"a": y, "b": y + 1}
    r = RegimeRouter(cfg).fit([key], {key: X}, {key: y}, {key: preds})
    assert key in r.fallback_
    p, names = r.predict_key(key, X, preds)
    assert len(p) == 20
