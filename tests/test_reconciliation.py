"""Tests for hierarchical coherence and reconciliation operators."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models.hybrid.reconciliation import (
    bottom_up,
    coherence_error,
    is_coherent,
    machine_core_counts,
    memory_hierarchy,
    ols_reconcile,
    reconcile,
    top_down_proportional,
)


def test_machine_core_counts_use_host_mapping_not_swapped_labels():
    cores = machine_core_counts()
    # correlation mapping: m05->pegase(20), m07->phaedra(24)
    assert cores["machine05"] == 20
    assert cores["machine07"] == 24
    assert cores["machine02"] == 48
    assert sum(cores.values()) == 236


def test_bottom_up_exact_coherence():
    rng = np.random.default_rng(0)
    bottom = rng.random((32, 7))
    b2, top = bottom_up(bottom)
    assert is_coherent(b2, top, atol=1e-12)
    assert coherence_error(b2, top) < 1e-12


def test_ols_reconciliation_produces_coherent_forecasts():
    h = memory_hierarchy()
    rng = np.random.default_rng(1)
    n = 50
    bottom = rng.normal(1e9, 1e8, size=(n, 7))
    # incoherent top
    top = bottom.sum(axis=1) + rng.normal(0, 1e8, size=n)
    assert coherence_error(bottom, top) > 1e6
    full = np.concatenate([bottom, top.reshape(-1, 1)], axis=1)
    rec = ols_reconcile(h, full)
    assert is_coherent(rec[:, :-1], rec[:, -1], atol=1e-4 * np.mean(np.abs(rec[:, -1])))


def test_reconcile_methods_api():
    h = memory_hierarchy()
    rng = np.random.default_rng(2)
    bottom = np.abs(rng.normal(1.0, 0.2, size=(20, 7)))
    top = bottom.sum(axis=1) + rng.normal(0, 0.5, size=20)
    for method in ("independent", "bottom_up", "top_down", "ols", "wls"):
        out = reconcile(method, h, bottom, top, series_var=np.ones(8))
        if method != "independent":
            assert out["coherence_error"] < 1e-6 or method == "top_down"
            if method in {"bottom_up", "ols", "wls"}:
                assert is_coherent(out["bottom"], out["top"], atol=1e-5)


def test_top_down_preserves_top():
    rng = np.random.default_rng(3)
    base = np.abs(rng.random((10, 7)))
    top = rng.random(10) * 7
    b, t = top_down_proportional(base, top)
    np.testing.assert_allclose(t, top)
    np.testing.assert_allclose(b.sum(axis=1), top, rtol=1e-10)


def test_nonnegative_projection_keeps_coherence():
    h = memory_hierarchy()
    bottom = np.array([[1.0, -2.0, 3.0, 0.5, -0.1, 2.0, 1.0]])
    top = np.array([10.0])
    out = reconcile("ols", h, bottom, top, nonnegative=True)
    assert np.all(out["bottom"] >= 0)
    assert is_coherent(out["bottom"], out["top"], atol=1e-8)
