"""Tests for pack-based final execution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from timetrack.final_packs import (
    WallClockGuard,
    dependencies_satisfied,
    list_pack_rows,
    load_packs_config,
    pack_by_id,
    pack_output_dir,
    read_pack_status,
)

ROOT = Path(__file__).resolve().parents[1]


def test_packs_config_loads_and_hpo_budget():
    cfg = load_packs_config(ROOT / "configs" / "final_fgcs_packs.yaml")
    assert cfg["execution_mode"] == "manual_packs"
    assert int(cfg["max_required_hpo_trials"]) == 16
    assert int(cfg["lightgbm_max_trials_memory"]) + int(cfg["lightgbm_max_trials_cpu"]) <= 16
    assert "implementation_commit" in cfg
    required = [p for p in cfg["packs"] if p.get("required")]
    assert any(p["id"] == "shared_tuning" for p in required)
    for p in cfg["packs"]:
        assert float(p["estimated_runtime_minutes"]) <= 45
        assert float(p["hard_wall_clock_minutes"]) <= 45


def test_packs_validator_accepts_pre_v2_pending():
    from timetrack.final_config import validate_packs_config

    cfg = load_packs_config(ROOT / "configs" / "final_fgcs_packs.yaml")
    errs = validate_packs_config(cfg, require_frozen=False)
    assert errs == [], errs
    errs_f = validate_packs_config(cfg, require_frozen=True)
    assert errs_f  # pending until experiment-freeze-v2


def test_full_config_marked_optional():
    cfg = yaml.safe_load((ROOT / "configs" / "final_fgcs_full.yaml").read_text())
    assert cfg.get("execution_status") == "optional_extended"
    assert cfg.get("default_execution") is False


def test_wall_clock_guard_stops_launch():
    g = WallClockGuard(hard_minutes=45, stop_launch_minutes=0.0001)
    import time

    time.sleep(0.01)
    assert g.may_launch_new_run() is False


def test_aggregator_rejects_incomplete(tmp_path):
    import importlib.util

    cfg = load_packs_config(ROOT / "configs" / "final_fgcs_packs.yaml")
    cfg = dict(cfg)
    cfg["artifact_root"] = str(tmp_path / "packs")
    path = ROOT / "scripts" / "aggregate_final_packs.py"
    spec = importlib.util.spec_from_file_location("aggregate_final_packs", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    with pytest.raises(SystemExit) as ei:
        mod.aggregate(cfg)
    assert "REFUSING" in str(ei.value)


def test_list_packs_shows_blocked_dependencies(tmp_path):
    cfg = load_packs_config(ROOT / "configs" / "final_fgcs_packs.yaml")
    cfg = dict(cfg)
    cfg["artifact_root"] = str(tmp_path / "packs")
    rows = list_pack_rows(cfg)
    by_id = {r["pack_id"]: r for r in rows}
    assert by_id["shared_tuning"]["status"] == "pending"
    assert by_id["memory_classical"]["status"] == "blocked"
    assert by_id["supporting_statistics"]["status"] == "blocked"


def test_pack_resume_and_partial_marker(tmp_path):
    from timetrack.final_packs import RunStatus

    out = tmp_path / "01_memory_classical"
    out.mkdir()
    st = RunStatus(pack_id="memory_classical", status="partial", completed_runs=["a", "b"], total_runs=5)
    st.save(out / "RUN_STATUS.json")
    loaded = RunStatus.load(out / "RUN_STATUS.json")
    assert loaded.status == "partial"
    assert len(loaded.completed_runs) == 2
    assert "COMPLETE" not in [p.name for p in out.iterdir()] or not (out / "COMPLETE").exists()
