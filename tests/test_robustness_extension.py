"""Tests for the FGCS robustness extension (EWMA + multi-seed)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from timetrack.robustness_extension import (
    EXPECTED_ALPHA_GRID,
    seed_claim_supported,
    validate_robustness_config,
    load_robustness_config,
)

ROOT = Path(__file__).resolve().parents[1]


def test_robustness_config_valid():
    cfg = load_robustness_config(ROOT / "configs" / "final_robustness_extension.yaml")
    errs = validate_robustness_config(cfg, require_frozen=False)
    assert errs == [], errs
    assert cfg["source_experiment_freeze_tag"] == "experiment-freeze-v2"
    assert cfg["dataset_fingerprint"] == "bf06dc0e7fe6ff5e"
    assert list(cfg["ewma_alpha_grid"]) == EXPECTED_ALPHA_GRID
    packs = {p["id"]: p for p in cfg["packs"]}
    assert packs["ewma_baselines"]["estimated_base_fits"] == 192
    assert packs["lightgbm_seed_robustness"]["seeds"] == [1, 2]
    assert "disk_ud" not in packs["lightgbm_seed_robustness"]["hierarchies"]
    assert packs["dlinear_seed_robustness"]["estimated_base_fits"] == 288


def test_ewma_registered_and_predicts():
    from models import forecasting as F

    model = F.build_model("ewma", horizon=1, context_length=8, seed=0, alpha=0.3)
    X = np.random.randn(20, 8, 1)
    y = np.random.randn(20, 1)
    model.fit(X, y)
    pred = model.predict(X)
    assert pred.shape[0] == 20
    assert np.all(np.isfinite(pred))


def test_seed_claim_rules():
    # all improve
    assert seed_claim_supported([-0.1, -0.12, -0.08])
    # two improve, one neutral
    assert seed_claim_supported([-0.1, -0.05, 0.01])
    # one opposing
    assert not seed_claim_supported([-0.1, -0.05, 0.1])
    # all neutral
    assert not seed_claim_supported([0.0, 0.01, -0.01])


def test_protocol_docs_exist():
    assert (ROOT / "docs" / "FINAL_ROBUSTNESS_EXTENSION_PROTOCOL.md").exists()
    assert (ROOT / "docs" / "PUBLICATION_GATE_CORRECTION.md").exists()
    assert (ROOT / "docs" / "FGCS_PUBLICATION_READINESS_PRE_ROBUSTNESS.md").exists()
    pre = (ROOT / "docs" / "FGCS_PUBLICATION_READINESS_PRE_ROBUSTNESS.md").read_text()
    assert "# GO" in pre or "\n# GO\n" in pre or "## Decision\n\n# GO" in pre
    corr = (ROOT / "docs" / "PUBLICATION_GATE_CORRECTION.md").read_text()
    assert "CONDITIONAL GO" in corr
    assert "Gate 2" in corr and "Gate 3" in corr and "Gate 4" in corr


def test_source_seed0_hashes_stable_when_packs_present():
    from experiments.robustness_extension import source_seed0_prediction_hashes

    cfg = load_robustness_config()
    h1 = source_seed0_prediction_hashes(cfg)
    h2 = source_seed0_prediction_hashes(cfg)
    assert h1 == h2
    # accepted packs should not be missing if present in workspace
    if (ROOT / "results/final/packs/03_cpu_classical/COMPLETE").exists():
        assert h1.get("cpu_classical") not in (None, "missing")
