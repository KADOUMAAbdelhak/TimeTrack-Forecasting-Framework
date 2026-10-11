"""Synthetic-only regression tests for Phase 4D execution conformance."""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]
BITBRAINS = ROOT / "independent_validation/05_bitbrains_factorial"
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BITBRAINS))

import phase4d_execution as execution  # noqa: E402
from src.selection import select_context  # noqa: E402
from src.training import fit_final_fixed_epochs, fit_inner  # noqa: E402


def identity(**overrides):
    values = {
        "trace": "Materna-T1", "formulation": "S1", "resource": "CPU",
        "vm_id": "74", "fold": 1, "context_length": 9, "seed": 0,
        "phase": "inner", "support_sha256": "support",
    }
    values.update(overrides)
    return execution.run_identity(**values)


def artifact(tmp_path: Path, name: str, value: str = "payload") -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)
    return path


def test_scientific_root_is_v1():
    assert execution.SCIENTIFIC_RELATIVE_ROOT.as_posix() == "outputs/scientific_v1"


@pytest.mark.parametrize("parts", [
    ("Materna-T1", "runtime", "x.json"),
    ("Materna-T2", "s1", "models", "x.pt"),
    ("Materna-T3", "validation", "result.json"),
])
def test_scientific_paths_remain_under_root(parts):
    assert execution.scientific_path(*parts).is_relative_to(execution.SCIENTIFIC_ROOT)


def test_scientific_path_rejects_escape():
    with pytest.raises(ValueError):
        execution.scientific_path("..", "pilot", "x.json")


def test_pilot_path_is_not_scientific_root():
    pilot = BASE / "pilot/PILOT_TIMINGS.csv"
    assert not pilot.resolve().is_relative_to(execution.SCIENTIFIC_ROOT)


def test_identity_contains_every_required_field():
    assert set(execution.REQUIRED_IDENTITY_FIELDS).issubset(identity())


def test_pilot_and_scientific_identity_cannot_match():
    assert execution.pilot_identity() != identity()
    assert execution.pilot_identity()["run_id"] != identity()["run_id"]


def test_identity_equality_is_exact():
    expected = identity()
    changed = identity(config_sha256="different")
    assert expected != changed and expected["run_id"] != changed["run_id"]


def test_plan_has_56700_runs():
    assert execution.plan_summary()["total_run_ids"] == 56_700


def test_plan_has_56700_unique_ids():
    summary = execution.plan_summary()
    assert summary["unique_run_ids"] == 56_700
    assert summary["duplicate_run_ids"] == 0


@pytest.mark.parametrize("trace", execution.TRACES)
def test_each_trace_has_18900_runs(trace):
    assert execution.plan_summary()["per_trace"][trace] == 18_900


def test_plan_formulation_phase_counts():
    assert execution.plan_summary()["by_formulation_phase"] == {
        "M1_final": 1575, "M1_inner": 4725,
        "S1_final": 6300, "S1_inner": 18900,
        "S2_final": 6300, "S2_inner": 18900,
    }


def test_plan_has_no_pilot_collision():
    assert execution.plan_summary()["pilot_scientific_collisions"] == 0


def test_inner_completion_records_no_outer_access(tmp_path):
    expected = identity()
    history = artifact(tmp_path, "history.json")
    target = tmp_path / "completion.json"
    payload = execution.write_successful_completion(
        target, expected, {"history": history}, training_finished=True, base=tmp_path
    )
    assert payload["outer_test_accessed"] is False
    assert execution.completion_is_reusable(target, expected, base=tmp_path)


def test_successful_final_records_outer_access(tmp_path):
    expected = identity(phase="final", context_length=4, selected_epoch=3)
    artifacts = {name: artifact(tmp_path, f"{name}.bin") for name in ("model", "prediction", "metrics")}
    target = tmp_path / "completion.json"
    payload = execution.write_successful_completion(
        target, expected, artifacts, training_finished=True,
        evaluation_completed=True, evaluation_count=1, base=tmp_path,
    )
    assert payload["outer_test_accessed"] is True
    assert execution.completion_is_reusable(target, expected, base=tmp_path)


def test_final_completion_cannot_precede_evaluation(tmp_path):
    expected = identity(phase="final", selected_epoch=2)
    artifacts = {name: artifact(tmp_path, f"{name}.bin") for name in ("model", "prediction", "metrics")}
    with pytest.raises(RuntimeError):
        execution.write_successful_completion(
            tmp_path / "completion.json", expected, artifacts,
            training_finished=True, base=tmp_path,
        )


def test_pretest_failure_records_false(tmp_path):
    payload = execution.write_failure_record(
        tmp_path / "failure.json", identity(phase="final"),
        stage="pre_outer_test", outer_test_accessed=False, error="synthetic",
    )
    assert payload["outer_test_accessed"] is False


def test_posttest_failure_records_true_and_nonreusable(tmp_path):
    expected = identity(phase="final")
    target = tmp_path / "failure.json"
    payload = execution.write_failure_record(
        target, expected, stage="post_outer_test",
        outer_test_accessed=True, error="synthetic",
    )
    assert payload["outer_test_accessed"] is True
    assert payload["reusable"] is False
    assert not execution.completion_is_reusable(target, expected, base=tmp_path)


def test_failed_run_cannot_masquerade_as_completion(tmp_path):
    expected = identity()
    target = tmp_path / "failure.json"
    execution.write_failure_record(
        target, expected, stage="training", outer_test_accessed=False, error="x"
    )
    assert not execution.completion_is_reusable(target, expected, base=tmp_path)


@pytest.mark.parametrize("field,value", [
    ("config_sha256", "bad-config"),
    ("cohort_sha256", "bad-cohort"),
    ("support_sha256", "bad-support"),
])
def test_identity_mismatch_prevents_reuse(tmp_path, field, value):
    expected = identity()
    history = artifact(tmp_path, "history.json")
    target = tmp_path / "completion.json"
    execution.write_successful_completion(
        target, expected, {"history": history}, training_finished=True, base=tmp_path
    )
    kwargs = {field: value}
    changed = identity(**kwargs)
    assert not execution.completion_is_reusable(target, changed, base=tmp_path)


def test_pilot_copied_to_scientific_directory_is_not_reusable(tmp_path):
    pilot = execution.pilot_identity()
    target = tmp_path / "looks-scientific.json"
    target.write_text(json.dumps({
        "status": "complete", "identity": pilot, "phase": "inner",
        "outer_test_accessed": False, "outer_test_evaluations": 0,
        "atomic_completion": True, "artifacts": {},
    }))
    assert not execution.completion_is_reusable(target, identity(), base=tmp_path)


@pytest.mark.parametrize("missing", ["prediction", "metrics"])
def test_missing_final_artifact_prevents_completion(tmp_path, missing):
    expected = identity(phase="final", selected_epoch=2)
    artifacts = {name: artifact(tmp_path, f"{name}.bin") for name in ("model", "prediction", "metrics") if name != missing}
    with pytest.raises(RuntimeError):
        execution.write_successful_completion(
            tmp_path / "completion.json", expected, artifacts,
            training_finished=True, evaluation_completed=True,
            evaluation_count=1, base=tmp_path,
        )


def test_artifact_hash_mismatch_prevents_reuse(tmp_path):
    expected = identity()
    history = artifact(tmp_path, "history.json")
    target = tmp_path / "completion.json"
    execution.write_successful_completion(
        target, expected, {"history": history}, training_finished=True, base=tmp_path
    )
    history.write_text("mutated")
    assert not execution.completion_is_reusable(target, expected, base=tmp_path)


def test_trace_mismatch_prevents_reuse(tmp_path):
    expected = identity()
    history = artifact(tmp_path, "history.json")
    target = tmp_path / "completion.json"
    execution.write_successful_completion(
        target, expected, {"history": history}, training_finished=True, base=tmp_path
    )
    assert not execution.completion_is_reusable(
        target, identity(trace="Materna-T2"), base=tmp_path
    )


def test_inner_run_cannot_claim_outer_access(tmp_path):
    with pytest.raises(RuntimeError):
        execution.write_successful_completion(
            tmp_path / "completion.json", identity(),
            {"history": artifact(tmp_path, "history.json")},
            training_finished=True, evaluation_completed=True,
            evaluation_count=1, base=tmp_path,
        )


def test_context_selection_api_has_no_outer_test_argument():
    assert "outer" not in " ".join(inspect.signature(select_context).parameters)


def test_inner_training_api_has_no_outer_test_argument():
    assert "outer" not in " ".join(inspect.signature(fit_inner).parameters)


def test_final_refit_requires_fixed_epoch_and_has_no_test_argument():
    parameters = inspect.signature(fit_final_fixed_epochs).parameters
    assert "epoch_count" in parameters
    assert not any("test" in name for name in parameters)


def test_scientific_config_sha_is_unchanged():
    assert execution.sha256_file(BASE / "configs/materna_replication_v1.json") == execution.CONFIG_SHA256


def test_cohort_sha_is_unchanged():
    summary = json.loads((BASE / "manifests/CANDIDATE_35_VM_COHORT_SUMMARY.json").read_text())
    assert summary["candidate_id_list_sha256"] == execution.COHORT_SHA256


def test_archive_sha_is_unchanged():
    archive = ROOT / "data/external/raw/gwa_t_13_materna.zip"
    assert execution.sha256_file(archive) == execution.ARCHIVE_SHA256


def test_planner_invokes_no_optimizer(monkeypatch):
    import torch
    monkeypatch.setattr(torch.optim, "Adam", lambda *args, **kwargs: pytest.fail("optimizer invoked"))
    assert execution.plan_summary()["optimizer_executions"] == 0


def test_atomic_completion_leaves_no_temporary_file(tmp_path):
    expected = identity()
    history = artifact(tmp_path, "history.json")
    target = tmp_path / "completion.json"
    execution.write_successful_completion(
        target, expected, {"history": history}, training_finished=True, base=tmp_path
    )
    assert target.is_file()
    assert not list(tmp_path.glob("*.tmp"))


def test_invalid_resource_is_rejected():
    with pytest.raises(ValueError):
        identity(resource="NOT_A_RESOURCE")


def test_noncohort_vm_is_rejected():
    with pytest.raises(ValueError):
        identity(vm_id="999999")
