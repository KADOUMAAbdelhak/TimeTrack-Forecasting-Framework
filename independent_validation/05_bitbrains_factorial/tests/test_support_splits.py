from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src import CONTEXTS, LEADS
from src.panel import build_windows
from src.splits import assert_support_minima, build_folds, manifest_rows
from src.support import assert_context_invariant, legal_origins, origin_ids, sample_set_hash, support_hash


def test_horizon_and_context_order():
    assert LEADS == (1, 2, 4, 9, 18)
    assert CONTEXTS == (4, 9, 18)


def test_maximum_history_support(synthetic_panel):
    origins = legal_origins(synthetic_panel)
    assert origins[0] == 17
    assert origins[-1] == len(synthetic_panel) - 19


def test_shorter_context_gains_no_origins(synthetic_panel):
    origins = legal_origins(synthetic_panel)
    assert_context_invariant({4: origins.copy(), 9: origins.copy(), 18: origins.copy()})


def test_four_resource_finite_support(synthetic_panel):
    synthetic_panel.loc[100, "MEMORY"] = np.nan
    origins = legal_origins(synthetic_panel)
    forbidden = set(range(100, 118)) | {100 - lead for lead in LEADS}
    assert not (forbidden & set(origins.tolist()))


def test_target_segment_safety(synthetic_panel):
    synthetic_panel.loc[200:, "segment_id"] = 1
    origins = legal_origins(synthetic_panel)
    assert not any(origin < 200 <= origin + 18 for origin in origins)


def test_window_shapes_and_segment_safety(synthetic_panel):
    origins = legal_origins(synthetic_panel)[:10]
    X, y, persistence = build_windows(synthetic_panel, origins, 9)
    assert X.shape == (10, 9, 4)
    assert y.shape == (10, 4, 5)
    assert persistence.shape == (10, 4, 5)


def test_five_outer_folds(synthetic_panel):
    origins = legal_origins(synthetic_panel)
    folds = build_folds(synthetic_panel, "env", "vm", origins)
    assert [fold.fold for fold in folds] == [1, 2, 3, 4, 5]
    assert all(len(fold.outer_test) > 0 for fold in folds)


def test_max_lead_outer_purge(synthetic_panel):
    origins = legal_origins(synthetic_panel)
    for fold in build_folds(synthetic_panel, "env", "vm", origins):
        target_times = synthetic_panel.timestamp_seconds.to_numpy()[fold.outer_train + max(LEADS)]
        test_start = synthetic_panel.timestamp_seconds.iloc[fold.outer_test[0]]
        assert np.all(target_times < test_start)


def test_inner_latest_15_percent_and_purge(synthetic_panel):
    origins = legal_origins(synthetic_panel)
    for fold in build_folds(synthetic_panel, "env", "vm", origins):
        assert len(fold.inner_validation) == math.ceil(0.15 * len(fold.outer_train))
        target_times = synthetic_panel.timestamp_seconds.to_numpy()[fold.inner_train + max(LEADS)]
        validation_start = synthetic_panel.timestamp_seconds.iloc[fold.inner_validation[0]]
        assert np.all(target_times < validation_start)


def test_support_hash_determinism(synthetic_panel):
    origins = legal_origins(synthetic_panel)
    assert support_hash(synthetic_panel, origins) == support_hash(synthetic_panel, origins.copy())
    assert sample_set_hash(origin_ids(synthetic_panel, origins)) == support_hash(synthetic_panel, origins)


def test_manifest_context_support_equality(synthetic_panel):
    origins = legal_origins(synthetic_panel)
    rows = pd.DataFrame(manifest_rows(synthetic_panel, build_folds(synthetic_panel, "env", "vm", origins)))
    assert len(rows) == 15
    for _, group in rows.groupby("fold"):
        assert group.outer_test_hash.nunique() == 1
        assert group.inner_train_hash.nunique() == 1


def test_support_gate_pass_and_fail(synthetic_panel):
    folds = build_folds(synthetic_panel, "env", "vm", legal_origins(synthetic_panel))
    assert not assert_support_minima(folds, {"inner_train": 1, "inner_validation": 1, "outer_train": 1, "outer_test": 1})
    assert assert_support_minima(folds, {"inner_train": 1_000_000})
