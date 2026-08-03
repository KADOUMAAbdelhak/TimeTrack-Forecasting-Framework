"""Tests enforcing pilot/final evaluation isolation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.runner import append_all_runs, build_final_leaderboards, build_leaderboards
from timetrack.evaluation_stage import (
    ExperimentStage,
    annotate_run_result,
    assert_eligible_for_final_leaderboard,
    filter_final_eligible,
    results_root_for_stage,
)


def _fake_result(run_id: str, stage: ExperimentStage, mae: float = 1.0) -> dict:
    r = {
        "run_id": run_id,
        "scope": "local",
        "target": "cluster_mean_CU",
        "model": "persistence",
        "horizon": 1,
        "context": 32,
        "seed": 0,
        "metrics_test": {
            "mae": mae,
            "rmse": mae,
            "mse": mae**2,
            "smape": 1.0,
            "mape": 1.0,
            "mape_fraction_excluded": 0.0,
            "mase": 1.0,
            "r2": 0.0,
            "nrmse": 0.1,
            "medae": mae,
            "maxae": mae,
            "peak_recall": None,
            "peak_precision": None,
        },
        "model_metadata": {"training_time_sec": 0.1, "inference_time_sec": 0.01, "n_parameters": 0},
        "runtime_sec": 0.2,
        "n_test_windows": 10,
        "config_meta": {},
    }
    return annotate_run_result(r, stage)


def test_stage_roots_differ():
    assert results_root_for_stage("pilot") != results_root_for_stage("final")
    assert results_root_for_stage("pilot").name == "pilot"
    assert results_root_for_stage("final").name == "final"


def test_pilot_metadata_not_eligible():
    r = _fake_result("pilot_run", ExperimentStage.PILOT)
    assert r["experiment_stage"] == "pilot"
    assert r["eligible_for_final_claims"] is False
    assert r["evaluation_role"] == "development_benchmark"


def test_final_metadata_eligible():
    r = _fake_result("final_run", ExperimentStage.FINAL)
    assert r["experiment_stage"] == "final"
    assert r["eligible_for_final_claims"] is True


def test_assert_rejects_pilot_rows():
    pilot = _fake_result("p1", ExperimentStage.PILOT)
    with pytest.raises(AssertionError, match="ineligible"):
        assert_eligible_for_final_leaderboard([pilot])


def test_filter_final_eligible_drops_pilot():
    df = pd.DataFrame(
        [
            _rowish(_fake_result("p1", ExperimentStage.PILOT)),
            _rowish(_fake_result("f1", ExperimentStage.FINAL)),
        ]
    )
    out = filter_final_eligible(df)
    assert list(out["run_id"]) == ["f1"]


def _rowish(r: dict) -> dict:
    return {
        "run_id": r["run_id"],
        "experiment_stage": r["experiment_stage"],
        "eligible_for_final_claims": r["eligible_for_final_claims"],
        "target": r["target"],
        "model": r["model"],
        "horizon": r["horizon"],
        "context": r["context"],
        "seed": r["seed"],
        "mae": r["metrics_test"]["mae"],
    }


def test_append_refuses_mixed_stages():
    a = _fake_result("a", ExperimentStage.PILOT)
    b = _fake_result("b", ExperimentStage.FINAL)
    with pytest.raises(AssertionError, match="mixed|mismatched"):
        append_all_runs([a, b])


def test_build_final_leaderboard_rejects_pilot_csv(tmp_path, monkeypatch):
    import experiments.runner as runner
    import timetrack.evaluation_stage as es

    monkeypatch.setattr(es, "FINAL_ROOT", tmp_path / "final")
    monkeypatch.setattr(es, "PILOT_ROOT", tmp_path / "pilot")

    final_metrics = tmp_path / "final" / "metrics"
    final_metrics.mkdir(parents=True)
    # Contaminated file: pilot rows wrongly placed under final path
    df = pd.DataFrame(
        [
            {
                "run_id": "bad",
                "experiment_stage": "pilot",
                "eligible_for_final_claims": False,
                "target": "cluster_mean_CU",
                "model": "persistence",
                "horizon": 1,
                "context": 32,
                "seed": 0,
                "mae": 1.0,
                "rmse": 1.0,
                "mse": 1.0,
                "smape": 1.0,
                "mape": 1.0,
                "mape_fraction_excluded": 0.0,
                "mase": 1.0,
                "r2": 0.0,
                "nrmse": 0.1,
                "medae": 1.0,
                "maxae": 1.0,
                "peak_recall": None,
                "peak_precision": None,
                "training_time_sec": 0.0,
                "inference_time_sec": 0.0,
                "n_parameters": 0,
                "runtime_sec": 0.0,
                "n_test_windows": 1,
            }
        ]
    )
    csv_path = final_metrics / "all_runs.csv"
    df.to_csv(csv_path, index=False)

    with pytest.raises(AssertionError):
        build_final_leaderboards(csv_path)


def test_pilot_leaderboard_rejects_final_contamination(tmp_path, monkeypatch):
    import timetrack.evaluation_stage as es

    monkeypatch.setattr(es, "PILOT_ROOT", tmp_path / "pilot")
    monkeypatch.setattr(es, "FINAL_ROOT", tmp_path / "final")
    pilot_metrics = tmp_path / "pilot" / "metrics"
    pilot_metrics.mkdir(parents=True)
    df = pd.DataFrame(
        [
            {
                "run_id": "f",
                "experiment_stage": "final",
                "eligible_for_final_claims": True,
                "target": "cluster_mean_CU",
                "model": "persistence",
                "horizon": 1,
                "context": 32,
                "seed": 0,
                "mae": 1.0,
                "rmse": 1.0,
                "mse": 1.0,
                "smape": 1.0,
                "mape": 1.0,
                "mape_fraction_excluded": 0.0,
                "mase": 1.0,
                "r2": 0.0,
                "nrmse": 0.1,
                "medae": 1.0,
                "maxae": 1.0,
                "peak_recall": None,
                "peak_precision": None,
                "training_time_sec": 0.0,
                "inference_time_sec": 0.0,
                "n_parameters": 0,
                "runtime_sec": 0.0,
                "n_test_windows": 1,
            }
        ]
    )
    csv_path = pilot_metrics / "all_runs.csv"
    df.to_csv(csv_path, index=False)
    with pytest.raises(AssertionError, match="final-stage"):
        build_leaderboards(csv_path, stage=ExperimentStage.PILOT)


def test_migrated_pilot_runs_are_ineligible():
    """If migration has run, every pilot raw JSON must be ineligible."""
    raw = ROOT / "results" / "pilot" / "metrics" / "raw_runs"
    if not raw.exists() or not any(raw.glob("*.json")):
        pytest.skip("pilot migration not present yet")
    for path in list(raw.glob("*.json"))[:20]:
        data = json.loads(path.read_text())
        assert data.get("experiment_stage") == "pilot"
        assert data.get("eligible_for_final_claims") is False
