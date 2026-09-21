"""Tests for frozen final evidence aggregation / reporting."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from timetrack.final_reporting import (
    EvidenceError,
    config_hash,
    load_yaml,
    run_final_aggregation,
    sha256_file,
    validate_registry,
    validate_reporting_config,
    verify_pack_manifest,
)

ROOT = Path(__file__).resolve().parents[1]


def test_registry_and_reporting_validate():
    reg = load_yaml(ROOT / "configs" / "final_evidence_registry.yaml")
    rep = load_yaml(ROOT / "configs" / "final_reporting.yaml")
    assert validate_registry(reg) == []
    assert validate_reporting_config(rep) == []
    assert reg["exclusions"]["downsampling"]["claim_eligible"] is False
    assert "downsampling" not in reg["accepted_prediction_packs"]
    assert "downsampling" not in reg["accepted_analysis_packs"]


def test_rejects_mixed_freeze_and_development():
    reg = load_yaml(ROOT / "configs" / "final_evidence_registry.yaml")
    man = {
        "dataset_fingerprint": reg["dataset_fingerprint"],
        "eligible_for_final_claims": True,
        "experiment_stage": "final",
        "freeze_tag": "experiment-freeze-v1",
        "frozen_implementation_commit": reg["prediction_layer"]["implementation_commit"],
        "evaluation_role": "outer_evaluation",
        "output_dir": "/tmp/results/final/x",
    }
    with pytest.raises(EvidenceError):
        verify_pack_manifest("cpu_classical", man, reg)
    man2 = dict(man)
    man2["freeze_tag"] = "experiment-freeze-v2"
    man2["output_dir"] = "/tmp/results/pilot/x"
    with pytest.raises(EvidenceError):
        verify_pack_manifest("cpu_classical", man2, reg)


def test_exclusion_not_required():
    reg = load_yaml(ROOT / "configs" / "final_evidence_registry.yaml")
    assert "network_secondary" not in reg["accepted_prediction_packs"]
    assert reg["exclusions"]["conformal_intervals"]["claim_eligible"] is False


def test_unit_separation_config():
    rep = load_yaml(ROOT / "configs" / "final_reporting.yaml")
    units = set(rep["unit_separation"])
    assert units == {"cpu_weighted_mean_pct", "memory_bytes", "disk_level"}


def test_deterministic_config_hash():
    reg = load_yaml(ROOT / "configs" / "final_evidence_registry.yaml")
    assert config_hash(reg) == config_hash(reg)


@pytest.mark.skipif(
    not (ROOT / "results/final/packs/03_cpu_classical/MANIFEST.json").exists(),
    reason="final packs not present",
)
def test_aggregate_smoke_on_real_artifacts(tmp_path: Path):
    reg = load_yaml(ROOT / "configs" / "final_evidence_registry.yaml")
    rep = load_yaml(ROOT / "configs" / "final_reporting.yaml")
    # hash a source file before
    src = ROOT / "results/final/packs/03_cpu_classical/metrics/reconciliation_results.csv"
    before = sha256_file(src)
    out = tmp_path / "aggregate"
    result = run_final_aggregation(registry=reg, reporting=rep, output_dir=out, smoke=False)
    assert (out / "tables" / "table02_cpu_main_results.csv").exists()
    assert (out / "tables" / "table06_claim_support_matrix.csv").exists()
    assert (out / "figures" / "cpu_accuracy_vs_horizon.pdf").exists()
    assert result["manifest"]["source_files_unchanged"] is True
    assert sha256_file(src) == before
    # no cross-unit pooling: separate tables exist
    cpu = pd.read_csv(out / "tables" / "table02_cpu_main_results.csv")
    mem = pd.read_csv(out / "tables" / "table03_memory_main_results.csv")
    assert set(cpu.unit.unique()) == {"cpu_weighted_mean_pct"}
    assert set(mem.unit.unique()) == {"memory_bytes"}
    # duplicate claim D1/D2 present
    claims = pd.read_csv(out / "tables" / "table06_claim_support_matrix.csv")
    assert "D1" in set(claims.claim) and "D2" in set(claims.claim)
