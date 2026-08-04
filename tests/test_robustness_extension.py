"""Tests for the FGCS robustness extension (freeze v2)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pytest

from timetrack.robustness_extension import (
    EXPECTED_ALPHA_GRID,
    assert_config_hashes_agree,
    lightgbm_execution_fingerprint,
    load_robustness_config,
    scientific_config_hash,
    seed_claim_supported,
    validate_robustness_config,
)

ROOT = Path(__file__).resolve().parents[1]


def test_robustness_config_valid_v2():
    cfg = load_robustness_config(ROOT / "configs" / "final_robustness_extension.yaml")
    errs = validate_robustness_config(cfg, require_frozen=False)
    assert errs == [], errs
    assert cfg["freeze_tag"] == "final-robustness-extension-freeze-v2"
    assert int(cfg["lightgbm_n_jobs"]) == -1
    assert cfg["source_experiment_freeze_tag"] == "experiment-freeze-v2"
    assert list(cfg["ewma_alpha_grid"]) == EXPECTED_ALPHA_GRID or [
        float(x) for x in cfg["ewma_alpha_grid"]
    ] == EXPECTED_ALPHA_GRID
    packs = {p["id"]: p for p in cfg["packs"]}
    assert packs["lightgbm_seed_robustness"]["seeds"] == [1, 2]
    assert packs["lightgbm_seed_robustness"]["stop_launching_new_runs_minutes"] == 27
    assert packs["lightgbm_seed_robustness"]["hard_wall_clock_minutes"] == 30
    assert "disk_ud" not in packs["lightgbm_seed_robustness"]["hierarchies"]


def test_scientific_config_hash_stable_across_commit_stamps():
    cfg = load_robustness_config()
    h1 = scientific_config_hash(cfg)
    cfg2 = dict(cfg)
    cfg2["implementation_commit"] = "a" * 40
    cfg2["freeze_commit"] = "b" * 40
    cfg2["freeze_tag_commit"] = "c" * 40
    assert scientific_config_hash(cfg2) == h1
    # Changing a scientific field must change the hash
    cfg3 = dict(cfg)
    cfg3["lightgbm_n_jobs"] = 1
    assert scientific_config_hash(cfg3) != h1


def test_config_hash_agreement_helper():
    cfg = load_robustness_config()
    h = scientific_config_hash(cfg)
    cfg = dict(cfg)
    cfg["frozen_scientific_config_hash"] = h
    assert assert_config_hashes_agree(cfg, executed_hash=h, manifest_hash=h) == []
    assert assert_config_hashes_agree(cfg, executed_hash="deadbeef", manifest_hash=h)


def test_lightgbm_wrapper_matches_seed0_n_jobs():
    from models import forecasting as F

    model = F.build_model("lightgbm", horizon=1, context_length=8, seed=7, n_estimators=10, num_leaves=7)
    est = model._make_estimator()
    params = est.get_params()
    assert params["random_state"] == 7
    assert params["n_jobs"] == -1
    # Must not introduce explicit bagging/feature subsample beyond defaults
    assert params.get("subsample", 1.0) == 1.0
    assert params.get("subsample_freq", 0) == 0
    assert params.get("colsample_bytree", 1.0) == 1.0


def test_seed_only_difference_in_fingerprint():
    cfg = load_robustness_config()
    a = lightgbm_execution_fingerprint(0, family="cpu", cfg=cfg)
    b = lightgbm_execution_fingerprint(1, family="cpu", cfg=cfg)
    diffs = [k for k in a if a[k] != b[k]]
    assert diffs == ["random_state"]
    assert a["n_jobs"] == b["n_jobs"] == -1


def test_seed_claim_rules():
    assert seed_claim_supported([-0.1, -0.12, -0.08])
    assert seed_claim_supported([-0.1, -0.05, 0.01])
    assert not seed_claim_supported([-0.1, -0.05, 0.1])


def test_protocol_and_correction_docs():
    assert (ROOT / "docs" / "FINAL_ROBUSTNESS_EXTENSION_PROTOCOL.md").exists()
    assert (ROOT / "docs" / "PUBLICATION_GATE_CORRECTION.md").exists()
    proto = (ROOT / "docs" / "FINAL_ROBUSTNESS_EXTENSION_PROTOCOL.md").read_text()
    assert "final-robustness-extension-freeze-v2" in proto
    assert "scientific_config_hash" in proto
    assert "n_jobs = -1" in proto or "n_jobs=-1" in proto


def test_source_seed0_hashes_stable_when_packs_present():
    from experiments.robustness_extension import source_seed0_prediction_hashes

    cfg = load_robustness_config()
    h1 = source_seed0_prediction_hashes(cfg)
    h2 = source_seed0_prediction_hashes(cfg)
    assert h1 == h2
    if (ROOT / "results/final/packs/03_cpu_classical/COMPLETE").exists():
        assert h1.get("cpu_classical") not in (None, "missing")
        assert h1 == cfg.get("source_seed0_pack_hashes")


def test_no_impl_diff_from_extension_tag_when_on_freeze_commit():
    """When HEAD is the freeze peel, working tree tracked files must match."""
    try:
        peel = subprocess.check_output(
            ["git", "rev-parse", "final-robustness-extension-freeze-v2^{}"],
            cwd=str(ROOT),
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        pytest.skip("freeze-v2 tag not created yet")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True).strip()
    if head != peel:
        pytest.skip("not currently on freeze-v2 peel; checked at acceptance")
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=str(ROOT),
        text=True,
    ).strip()
    assert dirty == "", dirty
    cfg = load_robustness_config()
    assert cfg["frozen_scientific_config_hash"] == scientific_config_hash(cfg)
    assert validate_robustness_config(cfg, require_frozen=True) == []


def test_ewma_registered_and_predicts():
    from models import forecasting as F

    model = F.build_model("ewma", horizon=1, context_length=8, seed=0, alpha=0.3)
    X = np.random.randn(20, 8, 1)
    y = np.random.randn(20, 1)
    model.fit(X, y)
    pred = model.predict(X)
    assert pred.shape[0] == 20
    assert np.all(np.isfinite(pred))
