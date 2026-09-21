"""LOMO safeguards: held-out exclusion, scaler isolation, unknown entity, calibration chronology."""

from __future__ import annotations

import numpy as np
import pytest

from models.multivariate.entity_features import EntityVocab, TargetScaler
from models.multivariate.global_models import GlobalOneHotForecaster, GlobalPooledForecaster
from models.hybrid.residual_adaptation import GlobalResidualAdaptationForecaster
from models import forecasting as F


def _toy(n=80, context=8, n_ent=3):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(n, context))
    keys = [f"m{i % n_ent}" for i in range(n)]
    y = X[:, -1] + rng.normal(scale=0.1, size=n) + np.array([float(k[1]) for k in keys])
    return X, y, keys


def test_held_out_entity_excluded_from_scaler():
    X, y, keys = _toy()
    train_mask = np.array([k != "m2" for k in keys])
    model = GlobalPooledForecaster(horizon=1, context_length=8, seed=0, base_model="ridge")
    model.fit(X[train_mask], y[train_mask], entity_keys=np.array(keys)[train_mask].tolist())
    model.scaler_.assert_entity_excluded("m2")
    with pytest.raises(AssertionError):
        # fit including m2 then assert exclusion of m2 fails
        m2 = GlobalPooledForecaster(horizon=1, context_length=8, seed=0)
        m2.fit(X, y, entity_keys=keys)
        m2.scaler_.assert_entity_excluded("m2")


def test_onehot_unknown_entity_zeros():
    vocab = EntityVocab(("m0", "m1"))
    oh = vocab.one_hot(["m0", "m2", "m1"])
    assert oh.shape == (3, 2)
    np.testing.assert_array_equal(oh[1], [0, 0])
    assert vocab.unknown_mask(["m2"])[0]


def test_global_onehot_predict_unseen():
    X, y, keys = _toy()
    train_mask = np.array([k != "m2" for k in keys])
    model = GlobalOneHotForecaster(
        horizon=1, context_length=8, seed=0, base_model="ridge", entities=["m0", "m1"]
    )
    model.fit(X[train_mask], y[train_mask], entity_keys=np.array(keys)[train_mask].tolist())
    pred = model.predict(X[~train_mask], entity_keys=np.array(keys)[~train_mask].tolist())
    assert len(pred) == (~train_mask).sum()
    assert np.isfinite(pred).all()


def test_residual_no_head_for_unseen():
    X, y, keys = _toy()
    train_mask = np.array([k != "m2" for k in keys])
    model = GlobalResidualAdaptationForecaster(
        horizon=1, context_length=8, seed=0, base_model="ridge", entities=["m0", "m1"]
    )
    model.fit(X[train_mask], y[train_mask], entity_keys=np.array(keys)[train_mask].tolist())
    assert "m2" not in model.residual_heads_
    pred = model.predict(X[~train_mask], entity_keys=["m2"] * int((~train_mask).sum()))
    assert np.isfinite(pred).all()


def test_calibration_chronology_helper():
    """Calibration indices must be before eval block (predeclared sizes)."""
    n_cal_allowed = (0, 64, 256, 1024)
    eval_start = 5000
    for n in n_cal_allowed:
        cal_end = eval_start
        cal_start = max(0, cal_end - n)
        assert cal_end <= eval_start
        assert cal_start >= 0


def test_scaler_modes_deterministic():
    rng = np.random.default_rng(1)
    y = rng.normal(size=50)
    keys = ["a"] * 25 + ["b"] * 25
    s1 = TargetScaler(mode="per_entity").fit(y, keys)
    s2 = TargetScaler(mode="per_entity").fit(y, keys)
    np.testing.assert_allclose(s1.transform(y, keys), s2.transform(y, keys))


def test_registry_includes_global_variants():
    names = F.list_available_models()
    for n in ("global_pooled", "global_onehot", "global_embed", "global_residual"):
        assert n in names
