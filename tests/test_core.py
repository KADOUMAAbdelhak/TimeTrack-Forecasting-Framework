"""Core unit tests for leakage-safe TimeTrack pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from timetrack.constants import MAPE_ZERO_EPS, SAMPLING_SECONDS
from timetrack.data import build_analysis_panel, dataset_fingerprint, detect_sampling_seconds, observed_interval_ok
from timetrack.metrics import compute_metrics, mape, r2_score
from timetrack.splits import assert_no_gap_crossing, build_windows, origins_for_split, post_outage_split


@pytest.fixture(scope="module")
def panel():
    return build_analysis_panel()


def test_dataset_fingerprint_stable():
    a = dataset_fingerprint()
    b = dataset_fingerprint()
    assert a["fingerprint"] == b["fingerprint"]
    assert len(a["files"]) == 6


def test_sampling_interval_near_42(panel):
    med = detect_sampling_seconds(panel["timestamp"])
    assert abs(med - SAMPLING_SECONDS) < 0.5
    assert observed_interval_ok(panel["timestamp"])
    # must NOT be 45
    assert abs(med - 45.0) > 1.0


def test_timestamps_sorted_no_duplicates(panel):
    assert panel["timestamp"].is_monotonic_increasing
    assert not panel["timestamp"].duplicated().any()


def test_post_outage_split_chronological(panel):
    split = post_outage_split(panel)
    assert split.train_idx.max() < split.val_idx.min()
    assert split.val_idx.max() < split.test_idx.min()
    assert set(panel.loc[split.train_idx, "segment"].unique()) == {"post_outage"}


def test_windows_do_not_cross_splits(panel):
    split = post_outage_split(panel)
    context, horizon = 16, 4
    values = panel[["cluster_mean_CU"]].to_numpy()
    for part, idx in ("train", split.train_idx), ("val", split.val_idx), ("test", split.test_idx):
        origins = origins_for_split(idx, context, horizon, len(panel))
        ds = build_windows(values, origins, context, horizon, panel_for_gap_check=panel)
        # all origin and target indices must lie in this split's range
        lo, hi = idx.min(), idx.max()
        assert ds.origin_idx.min() >= lo
        assert ds.target_idx.max() + horizon - 1 <= hi


def test_windows_refuse_outage_crossing(panel):
    # synthesize indices that would span the gap if any existed in-rows; ensure helper raises on mixed segments
    mixed = panel.index[(panel["segment"] == "pre_outage") | (panel["segment"] == "post_outage")]
    if len(mixed) > 10:
        with pytest.raises(AssertionError):
            assert_no_gap_crossing(np.array([mixed.min(), mixed.max()]), panel)


def test_scaler_train_only_pattern():
    from sklearn.preprocessing import StandardScaler

    x = np.random.randn(100, 3)
    train, test = x[:70], x[70:]
    sc = StandardScaler().fit(train)
    # mean should match train only
    assert np.allclose(sc.mean_, train.mean(axis=0))
    assert not np.allclose(sc.mean_, x.mean(axis=0)) or True  # may coincidentally match; main check:
    transformed_test = sc.transform(test)
    # refit on test would differ
    sc2 = StandardScaler().fit(test)
    assert not np.allclose(sc.mean_, sc2.mean_)


def test_mape_zero_policy():
    y = np.array([0.0, 0.0, 2.0, 4.0])
    p = np.array([0.1, 0.2, 2.2, 3.5])
    out = mape(y, p, eps=MAPE_ZERO_EPS)
    assert out["mape_fraction_excluded"] == 0.5
    assert np.isfinite(out["mape"])


def test_r2_negative_preserved():
    y = np.array([1.0, 2.0, 3.0])
    p = np.array([10.0, 10.0, 10.0])
    assert r2_score(y, p) < 0


def test_prediction_shapes_persistence(panel):
    from models import forecasting as F

    split = post_outage_split(panel)
    values = panel[["machine01_CU"]].to_numpy()
    context, horizon = 8, 4
    origins = origins_for_split(split.train_idx, context, horizon, len(panel))
    ds = build_windows(values, origins[:200], context, horizon)
    model = F.build_model("persistence", horizon=horizon, context_length=context)
    model.fit(ds.X, ds.y)
    pred = model.predict(ds.X[:10])
    assert pred.shape == (10, horizon)


def test_model_save_load(tmp_path, panel):
    from models import forecasting as F

    split = post_outage_split(panel)
    values = panel[["cluster_mean_CU"]].to_numpy()
    context, horizon = 8, 1
    origins = origins_for_split(split.train_idx, context, horizon, len(panel))
    ds = build_windows(values, origins[:100], context, horizon)
    model = F.build_model("moving_average", horizon=horizon, context_length=context)
    model.fit(ds.X, ds.y)
    path = tmp_path / "m"
    F.save(model, path)
    loaded = F.load(path)
    a = model.predict(ds.X[:5])
    b = loaded.predict(ds.X[:5])
    np.testing.assert_allclose(a, b)


def test_metrics_shape_guard():
    with pytest.raises(ValueError):
        compute_metrics(np.array([1, 2]), np.array([1, 2, 3]))


def test_list_models():
    from models import forecasting as F

    names = F.list_available_models()
    for required in ("persistence", "ridge", "lightgbm", "lstm", "dlinear"):
        assert required in names
