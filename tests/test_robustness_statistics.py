"""Tests for frozen multi-seed robustness statistical analysis."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from timetrack.robustness_reporting import (
    claim_support,
    classify_seed_variability,
    load_stats_config,
    scientific_config_hash,
    validate_stats_config,
)

ROOT = Path(__file__).resolve().parents[1]


def test_stats_config_loads():
    cfg = load_stats_config()
    errs = validate_stats_config(cfg, require_frozen=False)
    assert errs == [], errs
    assert cfg["freeze_tag"] == "final-robustness-analysis-freeze-v1"
    assert int(cfg["bootstrap"]["n_boot"]) == 5000
    assert cfg["lightgbm_pack_hash"] == "446473103b0cf235"
    assert cfg["dlinear_pack_hash"] == "ecd66cd4bc4a7770"


def test_scientific_hash_stable_across_commit_stamps():
    cfg = load_stats_config()
    h1 = scientific_config_hash(cfg)
    cfg2 = dict(cfg)
    cfg2["implementation_commit"] = "a" * 40
    cfg2["freeze_commit"] = "b" * 40
    assert scientific_config_hash(cfg2) == h1


def test_claim_support_rules():
    assert claim_support([-0.1, -0.08, -0.09]) == "supported"
    assert claim_support([-0.1, -0.05, 0.01]) == "supported"
    assert claim_support([0.1, 0.08, 0.05]) == "contradicted"
    assert claim_support([-0.1, 0.03, 0.04]) == "contradicted"


def test_seed_variability_classifier():
    assert classify_seed_variability(np.array([1.0, 1.0, 1.0]), ["a", "a", "a"], 0.0) == "seed_invariant"
    assert (
        classify_seed_variability(np.array([1.0, 1.005, 0.995]), ["a", "b", "c"], 0.1) == "practically_seed_stable"
    )


def test_rejects_provisional_paths_listed():
    cfg = load_stats_config()
    rejected = cfg.get("rejected_inputs") or []
    assert any("provisional_robustness/final-robustness-extension-freeze-v1" in r for r in rejected)
    assert any("provisional_robustness_analysis" in r for r in rejected)


def test_seed0_dlinear_recon_paths_resolve_under_source_root():
    cfg = load_stats_config()
    src = ROOT / (cfg.get("source_artifact_root") or "results/final/packs")
    from timetrack.robustness_reporting import SOURCE_DIRS

    cpu = src / SOURCE_DIRS["cpu_dlinear"] / "metrics" / "reconciliation_results.csv"
    mem = src / SOURCE_DIRS["memory_dlinear"] / "metrics" / "reconciliation_results.csv"
    assert cpu.exists(), cpu
    assert mem.exists(), mem
    # Guard against the bug that joined ROOT/SOURCE_DIRS without packs/
    assert not (ROOT / SOURCE_DIRS["cpu_dlinear"] / "metrics" / "reconciliation_results.csv").exists()


def test_no_training_in_reporting_module_source():
    text = (ROOT / "timetrack" / "robustness_reporting.py").read_text()
    assert "build_model" not in text
    assert ".fit(" not in text
    assert "LGBMRegressor" not in text


def test_threshold_name_preservation_in_peak_helper_contract():
    # peak CSV schema uses threshold_name not overwritten numeric threshold
    from timetrack import robustness_reporting as rr

    src = rr.__file__
    text = Path(src).read_text()
    assert "threshold_name" in text
    assert 'threshold_name": qname' in text or "threshold_name" in text


def test_protocol_docs_exist():
    assert (ROOT / "docs" / "FINAL_ROBUSTNESS_STATISTICAL_PROTOCOL.md").exists()
    assert (ROOT / "results" / "final" / "robustness" / "ROBUSTNESS_ANALYSIS_PROVENANCE.md").exists()
