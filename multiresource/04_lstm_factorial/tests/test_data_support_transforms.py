from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data import CONTEXT_LENGTHS, FUTURE_LEADS, RESOURCE_ORDER, TARGET_SUFFIXES, TRANSFORMS, build_raw_windows, formulation_view, sample_set_hash, target_columns
from src.splits import assert_context_invariant_support
from src.support import four_resource_finite_origins
from src.transforms import ResourceScaler, fit_partition_scaler, transform_resource


def test_resource_order_exact(): assert RESOURCE_ORDER == ("CPU", "THROUGHPUT", "MEMORY", "DISK_WRITE")
def test_horizon_order_exact(): assert FUTURE_LEADS == (1, 2, 4, 8, 16, 32, 64, 128)
def test_contexts_exact(): assert CONTEXT_LENGTHS == (32, 64, 128)
def test_target_definitions_exact(): assert TARGET_SUFFIXES == {"CPU":"cpu_utilization", "THROUGHPUT":"throughput_total", "MEMORY":"memory_used", "DISK_WRITE":"disk_write"}
def test_transforms_exact(): assert TRANSFORMS == {"CPU":"identity", "THROUGHPUT":"log1p", "MEMORY":"identity", "DISK_WRITE":"log1p"}
def test_machine_columns_exact(): assert target_columns("machine01") == ("machine01__cpu_utilization", "machine01__throughput_total", "machine01__memory_used", "machine01__disk_write")
def test_throughput_transform(): np.testing.assert_allclose(transform_resource(np.array([0., 3.]), "THROUGHPUT"), np.log1p([0., 3.]))
def test_disk_transform(): np.testing.assert_allclose(transform_resource(np.array([0., 7.]), "DISK_WRITE"), np.log1p([0., 7.]))
def test_log_transform_rejects_negative():
    with pytest.raises(ValueError): transform_resource(np.array([-1.]), "THROUGHPUT")


def test_scaler_roundtrip_and_projection():
    values = np.column_stack([np.arange(1, 101), np.arange(100, 200), np.arange(1000, 1100), np.arange(5, 105)]).astype(float)
    scaler = ResourceScaler.fit(values)
    scaled = scaler.transform(values.reshape(10, 10, 4))
    restored, rates = scaler.inverse(scaled)
    np.testing.assert_allclose(restored, values.reshape(10, 10, 4), rtol=1e-6)
    assert np.all(rates == 0)


def test_physical_projection_clips_negative():
    values = np.column_stack([np.arange(1, 101), np.arange(100, 200), np.arange(1000, 1100), np.arange(5, 105)]).astype(float)
    scaler = ResourceScaler.fit(values)
    scaled = np.zeros((2, 4)); scaled[:, 1] = -100; scaled[:, 3] = -100
    native, rates = scaler.inverse(scaled)
    assert np.all(native[:, [1, 3]] == 0) and np.all(rates[[1, 3]] == 1)


def test_zero_iqr_is_fatal():
    with pytest.raises(ValueError): ResourceScaler.fit(np.ones((20, 4)))


def test_scaler_fit_is_train_only(panel, machine01_folds):
    fold = machine01_folds[64][0]
    scaler = fit_partition_scaler(panel, "machine01", fold.inner_train, 64)
    altered = panel.copy()
    altered.loc[fold.inner_validation, "machine01__cpu_utilization"] = 1e12
    second = fit_partition_scaler(altered, "machine01", fold.inner_train, 64)
    np.testing.assert_array_equal(scaler.transformed_median, second.transformed_median)
    np.testing.assert_array_equal(scaler.transformed_iqr, second.transformed_iqr)


def test_context_support_is_identical(machine01_folds): assert_context_invariant_support(machine01_folds)
def test_shorter_context_does_not_gain_origins(machine01_folds):
    for fold in range(5):
        assert len(machine01_folds[32][fold].inner_train) == len(machine01_folds[128][fold].inner_train)


def test_common_support_finite_for_all_resources(panel, machine01_folds):
    origins = machine01_folds[64][0].inner_train[:20]
    supported = four_resource_finite_origins(panel, "machine01", origins)
    np.testing.assert_array_equal(supported, origins)


def test_common_support_rejects_one_missing_resource(panel, machine01_folds):
    origins = machine01_folds[64][0].inner_train[:3]
    altered = panel.copy(); altered.loc[origins[1], "machine01__memory_used"] = np.nan
    assert origins[1] not in four_resource_finite_origins(altered, "machine01", origins)


def test_inner_and_outer_purges(machine01_folds, panel):
    timestamps = panel.timestamp.to_numpy(); fold = machine01_folds[64][0]
    assert timestamps[fold.inner_train + 128].max() < timestamps[fold.inner_validation[0]]
    assert timestamps[fold.outer_train + 128].max() < timestamps[fold.outer_test[0]]


def test_segment_safety(panel, machine01_folds):
    fold = machine01_folds[64][0]; origins = fold.inner_train[:10]
    windows = build_raw_windows(panel, "machine01", 64, origins)
    segments = panel.segment_id.to_numpy(); histories = origins[:, None] - np.arange(63, -1, -1); targets = origins[:, None] + np.asarray(FUTURE_LEADS)
    assert np.all(segments[histories] == segments[origins, None]) and np.all(segments[targets] == segments[origins, None])


def test_s1_s2_m1_views_share_ids(panel, machine01_folds):
    origins = machine01_folds[64][0].inner_train[:5]; windows = build_raw_windows(panel, "machine01", 64, origins)
    assert windows.support_hash == sample_set_hash(origins)
    assert formulation_view(windows, "S1", "CPU")[0].shape == (5, 64, 1)
    assert formulation_view(windows, "S2", "CPU")[0].shape == (5, 64, 4)
    assert formulation_view(windows, "M1")[1].shape == (5, 4, 8)
