"""Regression tests: joint prediction width H is not evaluation lead time."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.final_hierarchy_runner import _first_step
from timetrack.constants import OUTAGE_END, OUTAGE_START
from timetrack.splits import build_windows, fold_to_split_spec, make_outer_chronological_folds


def _lightweight_panel() -> pd.DataFrame:
    compute = pd.read_csv(ROOT / "compute_dataset.csv", parse_dates=["timestamp"])
    panel = pd.DataFrame({"timestamp": compute["timestamp"]})
    panel["cluster_UM"] = compute["cluster UM"]
    outage_start = pd.Timestamp(OUTAGE_START)
    outage_end = pd.Timestamp(OUTAGE_END)
    ts = panel["timestamp"]
    panel["segment"] = np.where(
        ts < outage_start,
        "pre_outage",
        np.where(ts >= outage_end, "post_outage", "in_outage"),
    )
    return panel


@pytest.fixture(scope="module")
def panel():
    return _lightweight_panel()


def test_first_step_extracts_component_zero_only():
    y = np.arange(16, dtype=float).reshape(1, 16)
    assert _first_step(y).shape == (1,)
    assert float(_first_step(y)[0]) == 0.0
    y1 = np.array([7.0])
    assert float(_first_step(y1)[0]) == 7.0


@pytest.mark.parametrize("H", [1, 8, 16])
def test_build_windows_target_indices_are_o_plus_1_through_o_plus_H(panel, H):
    context = 32
    folds = make_outer_chronological_folds(panel, n_folds=3, val_frac_within_train=0.15)
    split = fold_to_split_spec(folds[0])
    # Choose an origin deep enough for H=16 inside the test block
    lo, hi = int(split.test_idx.min()), int(split.test_idx.max())
    o = lo + context + 50
    assert o + 16 <= hi
    values = panel[["cluster_UM"]].to_numpy(dtype=float)
    ds = build_windows(values, np.array([o]), context, H, panel_for_gap_check=panel)
    assert int(ds.target_idx[0]) == o + 1
    y = np.asarray(ds.y)
    if H == 1:
        assert y.ndim == 1
        assert float(y[0]) == float(panel["cluster_UM"].iloc[o + 1])
    else:
        assert y.shape == (1, H)
        for k in range(H):
            assert float(y[0, k]) == float(panel["cluster_UM"].iloc[o + 1 + k])
    # Frozen metric path scores only lead-1
    scored = _first_step(y)
    assert float(scored.reshape(-1)[0]) == float(panel["cluster_UM"].iloc[o + 1])


def test_larger_width_drops_final_origins_not_changes_scored_lead(panel):
    context = 32
    folds = make_outer_chronological_folds(panel, n_folds=3, val_frac_within_train=0.15)
    split = fold_to_split_spec(folds[0])
    from experiments.runner import prepare_split_windows

    w1 = prepare_split_windows(panel, split, "cluster_UM", 1, context, flat=True)
    w16 = prepare_split_windows(panel, split, "cluster_UM", 16, context, flat=True)
    assert len(w16["test"].origin_idx) <= len(w1["test"].origin_idx)
    # Scored timestamps are always o+1
    for ds in (w1["test"], w16["test"]):
        assert np.all(ds.target_idx == ds.origin_idx + 1)
        # And _first_step values match panel at those timestamps
        y = _first_step(ds.y)
        truth = panel["cluster_UM"].to_numpy()[ds.target_idx]
        np.testing.assert_allclose(y, truth)


def test_manuscript_does_not_claim_lead_time_for_output_width_figures():
    """Guard against reintroducing misleading figure filenames as sole includes."""
    tex = (ROOT / "fgcs" / "manuscript.tex").read_text()
    assert "cpu_accuracy_vs_output_width.pdf" in tex
    # Caption must state first-component scoring
    assert "first predicted component" in tex or "first multi-output component" in tex
    # Must not claim minutes-ahead x-axis for the width figure
    assert "minutes ahead" not in tex.lower()
