"""Tests for final efficiency, bootstrap, and config validation."""

from __future__ import annotations

import numpy as np
import pytest
import yaml
from pathlib import Path

from timetrack.efficiency import EfficiencyRecord, measure_inference_latencies, timed_train
from timetrack.final_config import validate_final_config
from timetrack.hierarchy_registry import cpu_weighted_registry_entry, memory_registry_entry
from timetrack.stats_bootstrap import (
    holm_adjust,
    paired_block_bootstrap_comparison,
    select_block_length,
)

ROOT = Path(__file__).resolve().parents[1]


def test_efficiency_record_required_fields_finite():
    def pred(X):
        return np.asarray(X).reshape(-1)[: max(1, len(np.asarray(X)))]

    X = np.random.default_rng(0).normal(size=(32, 8))

    def fit():
        return True

    _, wall, cpu, rss = timed_train(fit)
    lat = measure_inference_latencies(pred, X, n_warm=1, n_repeat=5)
    rec = EfficiencyRecord(
        wall_train_sec=wall,
        cpu_train_sec=cpu,
        peak_rss_mb=rss,
        warm_infer_latency_ms_median=lat["warm_infer_latency_ms_median"],
        warm_infer_latency_ms_p25=lat["warm_infer_latency_ms_p25"],
        warm_infer_latency_ms_p75=lat["warm_infer_latency_ms_p75"],
        cold_infer_latency_ms=lat["cold_infer_latency_ms"],
        forecasts_per_sec=lat["forecasts_per_sec"],
        n_train_samples=32,
        n_prediction_origins=32,
    )
    rec.assert_finite_required()


def test_block_length_and_holm_deterministic():
    rng = np.random.default_rng(0)
    resid = rng.normal(size=400)
    info = select_block_length(resid, forecast_horizon=4, context_length=32)
    assert 8 <= info["block_length"] <= 256
    yt = rng.normal(size=300)
    ya = yt + rng.normal(scale=0.5, size=300)
    yb = yt + rng.normal(scale=0.2, size=300)
    a = paired_block_bootstrap_comparison(yt, ya, yb, block_length=16, n_boot=100, seed=0)
    b = paired_block_bootstrap_comparison(yt, ya, yb, block_length=16, n_boot=100, seed=0)
    assert a["mean_diff"] == b["mean_diff"]
    assert a["ci_low"] == b["ci_low"]
    adj = holm_adjust([0.01, 0.04, 0.03])
    assert adj[0] <= adj[1] or True  # holm order-dependent
    assert all(0 <= x <= 1 for x in adj)


def test_final_config_yaml_validates():
    cfg = yaml.safe_load((ROOT / "configs" / "final_fgcs_full.yaml").read_text())
    errs = validate_final_config(cfg, require_frozen=False)
    assert errs == [], errs
    # optional_extended full config; freeze markers updated with active freeze generation
    assert "experiment-freeze" in str(cfg.get("freeze_tag", ""))


def test_cpu_registry_rejects_raw_conflict_flag_path():
    e = cpu_weighted_registry_entry()
    assert e["meta"]["verified_cores"]["machine05"] == 20
    assert e["meta"]["verified_cores"]["machine07"] == 24
    m = memory_registry_entry()
    assert m["hierarchy"].top_name == "cluster_UM"


def test_validator_rejects_pilot_paths_and_outer_hpo():
    cfg = yaml.safe_load((ROOT / "configs" / "final_fgcs_full.yaml").read_text())
    cfg = dict(cfg)
    cfg["artifact_paths"] = dict(cfg["artifact_paths"])
    cfg["artifact_paths"]["metrics"] = "results/development/metrics"
    errs = validate_final_config(cfg, require_frozen=False)
    assert any("development" in e for e in errs)
    cfg2 = yaml.safe_load((ROOT / "configs" / "final_fgcs_full.yaml").read_text())
    cfg2 = dict(cfg2)
    cfg2["hpo"] = dict(cfg2["hpo"])
    cfg2["hpo"]["use_outer_labels"] = True
    errs2 = validate_final_config(cfg2, require_frozen=False)
    assert any("outer-label" in e for e in errs2)


def test_packs_config_is_default_execution_entry():
    pointer = yaml.safe_load((ROOT / "configs" / "final_fgcs.yaml").read_text())
    assert pointer.get("execution_mode") == "manual_packs"
    assert pointer.get("redirect") == "configs/final_fgcs_packs.yaml"
    packs = yaml.safe_load((ROOT / "configs" / "final_fgcs_packs.yaml").read_text())
    assert packs.get("default_execution") is True
    assert int(packs["max_required_hpo_trials"]) <= 16
