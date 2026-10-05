from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import run_phase4c_scientific as runner


def test_v2_final_model_path_uses_isolated_namespace() -> None:
    path = runner.scientific_relative_path("fastStorage", "s1", "models", "run.pt")
    assert path.as_posix().startswith("outputs/scientific_v2/")


def test_v2_final_prediction_path_uses_isolated_namespace() -> None:
    path = runner.scientific_relative_path("Rnd", "m1", "predictions", "run.parquet")
    assert path.as_posix().startswith("outputs/scientific_v2/")


def test_v2_inner_completion_path_uses_isolated_namespace() -> None:
    path = runner.completion_path("fastStorage", "inner", "run")
    assert path.is_relative_to(runner.BASE / "outputs/scientific_v2")


def test_no_v2_path_builder_returns_legacy_namespace() -> None:
    paths = [
        runner.scientific_relative_path("fastStorage", "s1", "models", "x.pt"),
        runner.scientific_relative_path("fastStorage", "s1", "predictions", "x.parquet"),
        runner.completion_path("fastStorage", "inner", "x").relative_to(runner.BASE),
        runner.completion_path("Rnd", "final", "x").relative_to(runner.BASE),
    ]
    assert all(path.as_posix().startswith("outputs/scientific_v2/") for path in paths)
    assert all(not path.as_posix().startswith("outputs/scientific/") for path in paths)


def test_inner_completion_metadata_denies_outer_test_access() -> None:
    metadata = runner.completion_access_metadata("inner")
    assert metadata["outer_test_accessed"] is False
    assert metadata["execution_correction_sha256"] == runner.EXECUTION_CORRECTION_HASH


def test_successful_final_completion_metadata_records_outer_test_access() -> None:
    metadata = runner.completion_access_metadata(
        "final", evaluation_completed=True, prediction_persisted=True, metric_record_count=5
    )
    assert metadata["outer_test_accessed"] is True


def test_final_completion_cannot_precede_authorized_evaluation() -> None:
    with pytest.raises(RuntimeError):
        runner.completion_access_metadata(
            "final", evaluation_completed=False, prediction_persisted=True, metric_record_count=5
        )


@pytest.mark.parametrize(
    ("evaluation_completed", "prediction_persisted", "metric_record_count"),
    [(False, False, 0), (True, False, 5), (True, True, 0)],
)
def test_failure_before_complete_test_stage_never_records_true(
    evaluation_completed: bool, prediction_persisted: bool, metric_record_count: int
) -> None:
    with pytest.raises(RuntimeError):
        runner.completion_access_metadata(
            "final",
            evaluation_completed=evaluation_completed,
            prediction_persisted=prediction_persisted,
            metric_record_count=metric_record_count,
        )


def test_pre_amendment_completion_cannot_resume_as_corrected_v2(tmp_path: Path) -> None:
    expected = {"run_id": "old-run", "config_hash": runner.CONFIG_HASH}
    path = tmp_path / "old.json"
    path.write_text(json.dumps({
        "status": "complete",
        "identity": expected,
        "best_epoch": 1,
        "validation_nmae": [1.0] * 5,
        "outer_test_accessed": False,
    }))
    assert runner.valid_inner(path, expected) is False


def test_v2_scientific_config_hash_is_unchanged() -> None:
    assert runner.digest(runner.CONFIG_PATH) == "627391b84887411d8b930fd5d00cdd9a1f90f3990f958d582f4329424353fa4e"


def test_v2_scientific_criteria_hash_is_unchanged() -> None:
    assert runner.digest(runner.CRITERIA) == "79df6a168d7021dbafd6080640a506d22699e9d4989d422f924b178600465f12"
