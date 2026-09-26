from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from src.metrics import comparison_gain, inverse_one, macro_mae, per_lead_metrics
from src.runner import parameter_accounting, planned_counts
from src.selection import SelectionRow, select_context
from src.transforms import ResourceScaler
from src.validation import atomic_json_write, completion_valid, run_identity


def _rows(formulation, scores):
    shape = (4, 8) if formulation == "M1" else (8,)
    return [SelectionRow(formulation, length, seed, np.full(shape, scores[length]), seed + 1) for length in (32, 64, 128) for seed in (0, 1, 2)]


def test_s1_selection_objective(): assert select_context(_rows("S1", {32:2,64:1,128:3}), "S1").context_length == 64
def test_s2_selection_objective(): assert select_context(_rows("S2", {32:3,64:2,128:1}), "S2").context_length == 128
def test_m1_equal_resource_selection_objective(): assert select_context(_rows("M1", {32:2,64:1,128:3}), "M1").context_length == 64
def test_smaller_context_tie_break(): assert select_context(_rows("S1", {32:1,64:1,128:1}), "S1").context_length == 32
def test_per_seed_epoch_retention(): assert select_context(_rows("S1", {32:2,64:1,128:3}), "S1").best_epoch_by_seed == {0:1,1:2,2:3}


def test_inverse_transform_metric_correctness():
    values = np.column_stack([np.arange(1, 101), np.arange(100, 200), np.arange(1000, 1100), np.arange(5, 105)]).astype(float); scaler = ResourceScaler.fit(values)
    native = np.arange(110, 118, dtype=float)[None, :]; transformed = np.log1p(native); scaled = (transformed - scaler.transformed_median[1]) / scaler.transformed_iqr[1]
    restored, rate, _ = inverse_one(scaled, scaler, "THROUGHPUT")
    np.testing.assert_allclose(restored, native); assert rate == 0
    result = per_lead_metrics(native, restored, scaler.native_iqr[1]); assert np.allclose(result["mae"], 0)


def test_macro_seed_then_equal_cell_semantics():
    frame = pd.DataFrame([{"formulation":"S1","machine":m,"fold":f,"seed":s,"resource":"CPU","lead":1,"mae":v} for m,f,s,v in [("m1",1,0,1),("m1",1,1,3),("m2",1,0,10),("m2",1,1,10)]])
    assert macro_mae(frame).iloc[0].macro_mae == 6


def test_comparison_semantics(): assert comparison_gain(10, 8) == 20
def test_planned_fit_counts(): assert planned_counts()["TOTAL"] == {"inner_fits":2835,"final_fits":945,"total_fits":3780,"metric_rows":10080}
def test_parameter_accounting_system_counts():
    values = parameter_accounting(); assert values["S1"]["total_parameters_four_models"] == 203808 and values["S2"]["total_parameters_four_models"] == 206880 and values["M1"]["total_shared_system_parameters"] == 53280


def test_run_id_uniqueness_and_identity_fields():
    base = dict(formulation="S1", resource="CPU", machine="machine01", fold=1, context_length=32, seed=0, phase="inner", config_hash="c", support_hash="s")
    first = run_identity(**base); second = run_identity(**{**base, "seed":1})
    assert first["run_id"] != second["run_id"]
    assert {"formulation","resource","machine","fold","L","seed","phase","config_hash","support_hash"}.issubset(first)


def test_atomic_completion_and_artifact_validation(tmp_path):
    artifact = tmp_path / "result.bin"; artifact.write_bytes(b"ok")
    identity = run_identity(formulation="M1", resource=None, machine="machine01", fold=1, context_length=64, seed=0, phase="final", config_hash="c", support_hash="s")
    record = tmp_path / "complete.json"; atomic_json_write(record, {"status":"complete", "identity":identity})
    expected = {"result.bin": hashlib.sha256(b"ok").hexdigest()}
    assert completion_valid(record, identity, expected)
    artifact.write_bytes(b"bad"); assert not completion_valid(record, identity, expected)


def test_incomplete_record_not_resumable(tmp_path):
    path = tmp_path / "x.json"; path.write_text(json.dumps({"status":"running"}))
    assert not completion_valid(path, {}, {})
