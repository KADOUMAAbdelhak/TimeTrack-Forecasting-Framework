"""Tests for hierarchical reconciliation operators and safeguards."""

from __future__ import annotations

import numpy as np
import pytest

from models.hybrid.reconciliation import (
    RAW_CONFLICTING_CORE_LABELS,
    assert_not_using_raw_conflicting_labels,
    bond0_hierarchy,
    bottom_up,
    coherence_error,
    core_weighted_cpu_hierarchy,
    cu_to_weighted_contrib,
    disk_hierarchy,
    estimate_residual_covariance,
    is_coherent,
    machine_core_counts,
    mask_missing_children,
    memory_hierarchy,
    mint_shrink_reconcile,
    nonnegative_project_bottom,
    ols_reconcile,
    reconcile,
    verify_summing_identity,
    wls_reconcile,
)
from timetrack.constants import MACHINE_TO_HOST


def test_memory_exact_coherence():
    h = memory_hierarchy()
    rng = np.random.default_rng(0)
    bottom = rng.uniform(1e9, 2e9, size=(50, 7))
    _, top = bottom_up(bottom)
    assert is_coherent(bottom, top)
    assert coherence_error(bottom, top) < 1e-6
    full = h.project(bottom)
    assert verify_summing_identity(h, bottom, full)


def test_disk_exact_coherence():
    h = disk_hierarchy()
    rng = np.random.default_rng(1)
    bottom = rng.uniform(0, 1e6, size=(40, 7))
    out = reconcile("bottom_up", h, bottom, bottom.sum(axis=1) * 0)  # top ignored
    assert out["coherence_error"] < 1e-6
    assert verify_summing_identity(h, out["bottom"], out["full"])


def test_cpu_core_weighted_aggregation():
    cores = machine_core_counts()
    assert cores["machine05"] == 20
    assert cores["machine07"] == 24
    assert MACHINE_TO_HOST["machine05"] == "pegase"
    assert MACHINE_TO_HOST["machine07"] == "phaedra"
    h = core_weighted_cpu_hierarchy()
    assert h.meta["core_counts"]["machine05"] == 20
    assert "raw_conflicting_labels" in h.meta
    rng = np.random.default_rng(2)
    cu = rng.uniform(0, 100, size=(30, 7))
    contrib = cu_to_weighted_contrib(cu)
    out = reconcile("bottom_up", h, contrib, np.zeros(30))
    assert is_coherent(out["bottom"], out["top"])
    expected_top = contrib.sum(axis=1)
    np.testing.assert_allclose(out["top"], expected_top)


def test_prevent_swapped_raw_core_labels():
    bad = dict(RAW_CONFLICTING_CORE_LABELS)
    with pytest.raises(AssertionError, match="swapped"):
        assert_not_using_raw_conflicting_labels(bad)
    # verified mapping must pass
    assert_not_using_raw_conflicting_labels(machine_core_counts())


def test_bond0_approximate_hierarchy_structure():
    h = bond0_hierarchy("acamas", "transmitted")
    assert h.top_name.endswith("bond0")
    assert h.n_bottom == 4
    assert h.meta["relation"] == "approximate_sum"
    rng = np.random.default_rng(3)
    bottom = rng.uniform(0, 1e8, size=(20, h.n_bottom))
    out = reconcile("ols", h, bottom, bottom.sum(axis=1) * 1.01)
    assert out["coherence_error"] < 1e-4 * (1 + np.mean(np.abs(out["top"])))
    assert out["summing_ok"]


def test_nonnegative_projection():
    h = memory_hierarchy()
    bottom = np.array([[-1.0, 2.0, -3.0, 4.0, 5.0, -0.5, 1.0]])
    top = np.array([10.0])
    out = reconcile("ols", h, bottom, top, nonnegative=True)
    assert np.all(out["bottom"] >= 0)
    assert is_coherent(out["bottom"], out["top"], atol=1e-6)


def test_shape_validation():
    h = memory_hierarchy()
    with pytest.raises(ValueError, match="width"):
        reconcile("ols", h, np.ones((5, 3)), np.ones(5))
    with pytest.raises(ValueError, match="batch"):
        reconcile("ols", h, np.ones((5, 7)), np.ones(4))
    with pytest.raises(ValueError, match="width"):
        ols_reconcile(h, np.ones((5, 3)))


def test_singular_covariance_mint():
    h = memory_hierarchy()
    n = 8
    # Rank-deficient covariance
    cov = np.ones((n, n))
    yhat = np.arange(n, dtype=float)
    rec = mint_shrink_reconcile(h, yhat, cov, shrink=0.5)
    assert rec.shape == (n,)
    assert np.isfinite(rec).all()
    # Exact singular diagonal-zero case
    cov0 = np.zeros((n, n))
    rec0 = mint_shrink_reconcile(h, yhat, cov0, shrink=0.1)
    assert np.isfinite(rec0).all()


def test_missing_child_series_handling():
    h = memory_hierarchy()
    bottom = np.ones((10, 7))
    mask = np.zeros((10, 7), dtype=bool)
    mask[:, 2] = True
    filled = mask_missing_children(bottom, mask, fill=0.0)
    assert np.all(filled[:, 2] == 0)
    out = reconcile("bottom_up", h, bottom, np.zeros(10), missing_mask=mask)
    assert out["bottom"].shape == (10, 7)
    assert is_coherent(out["bottom"], out["top"])


def test_reproducibility():
    h = disk_hierarchy()
    rng = np.random.default_rng(42)
    bottom = rng.normal(size=(25, 7))
    top = rng.normal(size=25)
    a = reconcile("wls", h, bottom, top, series_var=np.ones(8))
    b = reconcile("wls", h, bottom, top, series_var=np.ones(8))
    np.testing.assert_allclose(a["full"], b["full"])
    np.testing.assert_allclose(a["coherence_error"], b["coherence_error"])


def test_covariance_from_train_only_api():
    """API documents train/inner residuals; shape and finite covariance."""
    rng = np.random.default_rng(7)
    y_true = rng.normal(size=(100, 8))
    y_pred = y_true + rng.normal(scale=0.1, size=(100, 8))
    cov = estimate_residual_covariance(y_true, y_pred)
    assert cov.shape == (8, 8)
    assert np.isfinite(cov).all()
    # Tiny sample falls back to identity
    cov1 = estimate_residual_covariance(y_true[:1], y_pred[:1])
    np.testing.assert_allclose(cov1, np.eye(8))


def test_ols_wls_mint_produce_s_b():
    h = memory_hierarchy()
    rng = np.random.default_rng(9)
    bottom = rng.uniform(1, 10, size=(15, 7))
    top = bottom.sum(axis=1) + rng.normal(scale=0.5, size=15)
    for method in ("ols", "wls", "mint"):
        kwargs = {}
        if method == "wls":
            kwargs["series_var"] = np.linspace(0.5, 2.0, 8)
        if method == "mint":
            kwargs["residual_cov"] = np.eye(8) * 0.3 + 0.1
        out = reconcile(method, h, bottom, top, **kwargs)
        assert verify_summing_identity(h, out["bottom"], out["full"], atol=1e-5)
        assert out["coherence_error"] < 1e-5


def test_independent_not_forced_coherent():
    h = memory_hierarchy()
    bottom = np.ones((5, 7))
    top = np.full(5, 100.0)
    out = reconcile("independent", h, bottom, top)
    assert out["coherence_error"] > 1.0
