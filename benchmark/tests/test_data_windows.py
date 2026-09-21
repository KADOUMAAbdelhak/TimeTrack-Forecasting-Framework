from __future__ import annotations

import numpy as np
import pytest

from benchmark.src.data import (
    EXPECTED_PANEL_SHA256,
    PANEL_PATH,
    raw_hashes,
    sha256_file,
    verify_raw_hashes,
)
from benchmark.src.features import (
    FEATURE_SET_IDS,
    feature_columns,
    validate_lomo_exclusion,
)
from benchmark.src.windows import (
    CONTEXT_LENGTHS,
    FUTURE_LEADS,
    build_windows,
    finite_feature_origins,
    joint_eligible_origins,
)


def test_exact_canonical_panel_loading(panel):
    assert sha256_file(PANEL_PATH) == EXPECTED_PANEL_SHA256
    assert panel.shape == (41356, 116)
    assert panel.timestamp.is_monotonic_increasing


def test_no_raw_data_mutation(panel):
    before = raw_hashes()
    _ = joint_eligible_origins(panel, "machine01")
    after = raw_hashes()
    assert before == after
    assert verify_raw_hashes()


def test_frozen_feature_definitions():
    assert len(FEATURE_SET_IDS) == 6
    assert feature_columns("machine01", "F0_LOCAL") == [
        "machine01__cpu_utilization"
    ]
    assert feature_columns("machine01", "F5_THROUGHPUT_LOMO_MEDIAN") == [
        "machine01__cpu_utilization",
        "machine01__throughput_total",
        "machine01__lomo_cpu_utilization_median",
    ]


def test_lomo_excludes_target_machine(registry):
    assert all(
        validate_lomo_exclusion(registry, f"machine{i:02d}") for i in range(1, 8)
    )


def test_target_vector_and_exact_leads(panel):
    assert FUTURE_LEADS == [1, 2, 4, 8, 16, 32, 64, 128]
    origins = joint_eligible_origins(panel, "machine01")[:3]
    batch = build_windows(panel, "machine01", "F0_LOCAL", 32, origins)
    expected = np.column_stack(
        [
            panel["machine01__cpu_utilization"].iloc[origins + lead].to_numpy()
            for lead in FUTURE_LEADS
        ]
    )
    assert batch.y.shape == (3, 8)
    assert np.allclose(batch.y, expected)


def test_segment_safe_histories_and_targets(panel):
    origins = finite_feature_origins(
        panel,
        "machine01",
        "F5_THROUGHPUT_LOMO_MEDIAN",
        128,
        joint_eligible_origins(panel, "machine01"),
    )
    batch = build_windows(
        panel, "machine01", "F5_THROUGHPUT_LOMO_MEDIAN", 128, origins[:20]
    )
    assert batch.X.shape == (20, 128, 3)
    assert batch.y.shape == (20, 8)
    segment = panel.segment_id.to_numpy()
    for origin in origins[:20]:
        assert segment[origin - 127] == segment[origin]
        assert all(segment[origin + lead] == segment[origin] for lead in FUTURE_LEADS)


def test_invalid_cross_segment_window_rejected(panel):
    starts = panel.index[panel.segment_id.diff().fillna(0).ne(0)].tolist()
    origin = starts[0] + 10
    with pytest.raises(ValueError, match="segment"):
        build_windows(
            panel,
            "machine01",
            "F0_LOCAL",
            CONTEXT_LENGTHS[-1],
            np.asarray([origin]),
        )
