from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from benchmark.neural_v2.src.data import (
    CONTEXT_LENGTHS,
    FEATURE_SETS,
    FUTURE_LEADS,
    build_windows,
    f1_finite_origins,
    feature_columns,
)
from benchmark.neural_v2.src.splits import build_supported_folds


ROOT = Path(__file__).resolve().parents[3]


def test_exact_protocol_constants():
    assert FUTURE_LEADS == (1, 2, 4, 8, 16, 32, 64, 128)
    assert CONTEXT_LENGTHS == (32, 64, 128)
    assert FEATURE_SETS == ("F0_LOCAL", "F1_THROUGHPUT")


def test_config_has_only_allowed_features():
    config = json.loads(
        (ROOT / "benchmark/neural_v2/configs/neural_v2.json").read_text()
    )
    assert config["feature_sets"] == ["F0_LOCAL", "F1_THROUGHPUT"]
    forbidden = {"lomo", "memory", "disk", "rtt", "jitter", "packet", "core"}
    assert not forbidden.intersection(
        " ".join(config["feature_sets"]).lower().split()
    )


def test_feature_columns_are_cpu_and_total_throughput_only():
    assert feature_columns("machine01", "F0_LOCAL") == (
        "machine01__cpu_utilization",
    )
    assert feature_columns("machine01", "F1_THROUGHPUT") == (
        "machine01__cpu_utilization",
        "machine01__throughput_total",
    )
    with pytest.raises(KeyError):
        feature_columns("machine01", "F2_LOMO_MEAN")


def test_f0_f1_have_identical_support_and_targets(panel):
    fold = build_supported_folds(panel, "machine01", 64)[0]
    f0 = build_windows(
        panel, "machine01", "F0_LOCAL", 64, fold.inner_train_indices[:128]
    )
    f1 = build_windows(
        panel, "machine01", "F1_THROUGHPUT", 64, fold.inner_train_indices[:128]
    )
    assert np.array_equal(f0.origin_indices, f1.origin_indices)
    assert np.array_equal(f0.sample_ids, f1.sample_ids)
    assert np.array_equal(f0.y, f1.y)
    assert f0.sample_set_hash == f1.sample_set_hash
    assert f0.X.shape[-1] == 1 and f1.X.shape[-1] == 2


def test_supported_fold_purges_and_nonoverlap(panel):
    timestamps = panel["timestamp"].to_numpy()
    folds = build_supported_folds(panel, "machine01", 64)
    assert len(folds) == 5
    previous_tests: set[int] = set()
    for fold in folds:
        assert not previous_tests.intersection(fold.outer_test_indices.tolist())
        assert np.all(
            timestamps[fold.outer_train_indices + 128]
            < timestamps[fold.outer_test_indices[0]]
        )
        assert np.all(
            timestamps[fold.inner_train_indices + 128]
            < timestamps[fold.inner_validation_indices[0]]
        )
        previous_tests.update(fold.outer_test_indices.tolist())


def test_support_is_identical_across_candidate_context_lengths(panel):
    hashes = []
    for context_length in CONTEXT_LENGTHS:
        fold = build_supported_folds(panel, "machine01", context_length)[0]
        hashes.append(
            (
                fold.inner_train_hash,
                fold.inner_validation_hash,
                fold.outer_train_hash,
                fold.outer_test_hash,
            )
        )
    assert len(set(hashes)) == 1


def test_segment_boundaries_and_nonfinite_throughput_are_rejected():
    size = 220
    panel = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=size, freq="min"),
            "segment_id": np.where(np.arange(size) < 100, 0, 1),
            "machine01__cpu_utilization": np.ones(size),
            "machine01__throughput_total": np.ones(size),
        }
    )
    panel.loc[80, "machine01__throughput_total"] = np.nan
    origins = np.asarray([63, 90, 120], dtype=np.int64)
    supported = f1_finite_origins(panel, "machine01", 32, origins)
    assert supported.size == 0


def test_patch_input_contains_no_future_target(panel):
    fold = build_supported_folds(panel, "machine01", 32)[0]
    origin = fold.inner_train_indices[-1:]
    original = build_windows(panel, "machine01", "F1_THROUGHPUT", 32, origin)
    changed = panel.copy()
    changed.loc[origin[0] + 1, "machine01__cpu_utilization"] += 1000
    modified = build_windows(changed, "machine01", "F1_THROUGHPUT", 32, origin)
    assert np.array_equal(original.X, modified.X)
    assert not np.array_equal(original.y, modified.y)
