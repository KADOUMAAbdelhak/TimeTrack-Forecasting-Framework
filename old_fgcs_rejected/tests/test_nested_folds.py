"""Nested / rolling-origin fold leakage tests."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from timetrack.data import build_analysis_panel
from timetrack.splits import (
    assert_no_gap_crossing,
    build_windows,
    fold_to_split_spec,
    make_inner_rolling_folds,
    make_outer_chronological_folds,
    nested_fold_plan,
    origins_for_split,
)


@pytest.fixture(scope="module")
def panel():
    return build_analysis_panel()


def test_outer_folds_expanding_and_disjoint(panel):
    folds = make_outer_chronological_folds(panel, n_folds=3)
    assert len(folds) == 3
    # expanding train spans
    assert len(folds[0].train_idx) < len(folds[1].train_idx) <= len(folds[2].train_idx) + len(folds[2].val_idx)
    for f in folds:
        assert f.train_idx.max() < f.val_idx.min() <= f.val_idx.max() < f.test_idx.min()
        assert_no_gap_crossing(np.arange(f.train_idx.min(), f.test_idx.max() + 1), panel)


def test_inner_folds_never_touch_outer_test(panel):
    outer = make_outer_chronological_folds(panel, n_folds=3)
    for of in outer:
        span = np.concatenate([of.train_idx, of.val_idx])
        inner = make_inner_rolling_folds(panel, span, n_inner=3, mode="expanding")
        test_set = set(of.test_idx.tolist())
        for inn in inner:
            assert not test_set.intersection(inn.train_idx.tolist())
            assert not test_set.intersection(inn.val_idx.tolist())
            assert inn.test_idx is None


def test_nested_plan_serializable(panel):
    plan = nested_fold_plan(panel, n_outer=3, n_inner=3)
    assert len(plan) == 3
    assert all("outer" in p and "inner" in p for p in plan)
    assert all(len(p["inner"]) >= 1 for p in plan)


def test_windows_respect_outer_fold_boundaries(panel):
    folds = make_outer_chronological_folds(panel, n_folds=3)
    f = folds[1]
    split = fold_to_split_spec(f)
    values = panel[["cluster_mean_CU"]].to_numpy()
    context, horizon = 16, 4
    for part, idx in ("train", split.train_idx), ("val", split.val_idx), ("test", split.test_idx):
        origins = origins_for_split(idx, context, horizon, len(panel))
        ds = build_windows(values, origins, context, horizon, panel_for_gap_check=panel)
        lo, hi = int(idx.min()), int(idx.max())
        assert ds.origin_idx.min() >= lo
        assert (ds.target_idx + horizon - 1).max() <= hi


def test_sliding_inner_mode(panel):
    outer = make_outer_chronological_folds(panel, n_folds=3)[0]
    span = np.concatenate([outer.train_idx, outer.val_idx])
    inner = make_inner_rolling_folds(panel, span, n_inner=2, mode="sliding", min_train=800)
    assert len(inner) >= 1
    for inn in inner:
        assert inn.meta["mode"] == "sliding"
