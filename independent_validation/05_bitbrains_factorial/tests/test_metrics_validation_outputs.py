from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.metrics import environment_macro, equal_environment_synthesis, per_lead_metrics
from src.validation import completion_valid, run_identity, scientific_workload_counts


BASE = Path(__file__).resolve().parents[1]


def test_native_metrics_shape():
    y = np.arange(50, dtype=float).reshape(10, 5)
    result = per_lead_metrics(y, y + 1, 2.0, y)
    assert all(values.shape == (5,) for values in result.values())


def test_environment_non_pooling():
    rows = pd.DataFrame({
        "environment": ["a", "b"], "formulation": ["S1", "S1"],
        "vm_id": ["1", "1"], "fold": [1, 1], "seed": [0, 0],
        "resource": ["CPU", "CPU"], "lead": [1, 1], "mae": [1.0, 2.0],
    })
    with pytest.raises(ValueError, match="cannot be pooled"):
        environment_macro(rows)


def test_equal_environment_synthesis_not_vm_weighted():
    frame = pd.DataFrame({
        "environment": ["GWA-T-12_Bitbrains_fastStorage", "GWA-T-12_Bitbrains_Rnd"],
        "formulation": ["S1", "S1"], "resource": ["CPU", "CPU"],
        "lead": [1, 1], "macro_mae": [1.0, 3.0],
    })
    assert equal_environment_synthesis(frame).macro_mae.iloc[0] == 2.0


def test_run_identity_contains_all_frozen_keys():
    identity = run_identity(
        environment="env", formulation="S1", resource="CPU", vm_id="1", fold=1,
        context_length=9, seed=0, phase="inner", config_hash="a", support_hash="b",
        archive_hash="c", cohort_hash="d",
    )
    assert set(identity) == {
        "environment", "formulation", "resource", "vm_id", "fold", "L", "seed",
        "phase", "config_hash", "support_hash", "archive_hash", "cohort_hash", "run_id",
    }


def test_completion_requires_identity_and_artifact_hash(tmp_path):
    identity = run_identity(
        environment="env", formulation="M1", resource=None, vm_id="1", fold=1,
        context_length=9, seed=0, phase="inner", config_hash="a", support_hash="b",
        archive_hash="c", cohort_hash="d",
    )
    artifact = tmp_path / "artifact.txt"; artifact.write_text("ok")
    import hashlib
    expected = {"artifact.txt": hashlib.sha256(artifact.read_bytes()).hexdigest()}
    completion = tmp_path / "completion.json"
    completion.write_text(json.dumps({"status": "complete", "identity": identity}))
    assert completion_valid(completion, identity, expected)


def test_scientific_workload_counts():
    counts = scientific_workload_counts()
    assert counts == {
        "S1_inner": 6300, "S1_final": 2100, "S2_inner": 6300, "S2_final": 2100,
        "M1_inner": 1575, "M1_final": 525, "inner_total": 14175,
        "final_total": 4725, "fit_total": 18900, "metric_rows": 31500,
    }


def test_generated_support_and_pilot_boundaries():
    support_path = BASE / "manifests/EXTERNAL_SUPPORT_MANIFEST.parquet"
    pilot_path = BASE / "pilot/PILOT_DATA_ACCESS.json"
    if not support_path.exists() or not pilot_path.exists():
        pytest.skip("Generated artifacts are validated after runner execution")
    support = pd.read_parquet(support_path)
    access = json.loads(pilot_path.read_text())
    assert len(support) == 1050
    assert access["pilot_models"] == 18
    assert access["epochs_per_model"] == [5]
    assert access["outer_test_targets_accessed"] is False
    assert access["outer_test_predictions_generated"] == 0
    assert access["scientific_context_selections"] == 0
    assert access["scientific_final_refits"] == 0


def test_generated_support_is_context_invariant():
    path = BASE / "manifests/EXTERNAL_SUPPORT_SUMMARY.csv"
    if not path.exists():
        pytest.skip("Generated artifacts are validated after runner execution")
    frame = pd.read_csv(path, dtype={"vm_id": str})
    for _, group in frame.groupby(["environment", "vm_id", "fold"]):
        assert set(group.L) == {4, 9, 18}
        for split in ("inner_train", "inner_validation", "outer_train", "outer_test"):
            assert group[f"{split}_hash"].nunique() == 1
            assert group[f"{split}_count"].nunique() == 1
