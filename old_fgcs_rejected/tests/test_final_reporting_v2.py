"""Tests for robustness-aware final reporting v2."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from timetrack.final_reporting import load_yaml, sha256_file
from timetrack.final_reporting_v2 import (
    EvidenceError,
    provenance_envelope_hash,
    run_final_aggregation_v2,
    scientific_protocol_hash,
    validate_registry_v2,
    validate_reporting_config_v2,
)
from timetrack.freeze_immutability import create_annotated_tag_immutable

ROOT = Path(__file__).resolve().parents[1]


def test_registry_v2_validates():
    reg = load_yaml(ROOT / "configs" / "final_evidence_registry_v2.yaml")
    rep = load_yaml(ROOT / "configs" / "final_reporting_v2.yaml")
    assert validate_registry_v2(reg) == []
    assert validate_reporting_config_v2(rep) == []
    assert reg["required_pack_hashes"]["robustness_statistics"] == "08859b8132f3d605"
    assert any("final-robustness-analysis-freeze-v1" in (m.get("path") or "") for m in reg["exclusions"].values())


def test_scientific_protocol_hash_ignores_archive_paths():
    reg = load_yaml(ROOT / "configs" / "final_evidence_registry_v2.yaml")
    rep = load_yaml(ROOT / "configs" / "final_reporting_v2.yaml")
    h1 = scientific_protocol_hash(reg, rep)
    reg2 = dict(reg)
    reg2["archived_pre_robustness_aggregate"] = "results/final/archive/OTHER"
    rep2 = dict(rep)
    rep2["reporting_freeze_tag_commit"] = "a" * 40
    assert scientific_protocol_hash(reg2, rep2) == h1
    # provenance envelope must change when tag commit changes
    assert provenance_envelope_hash(reg, rep, exec_commit="x") != provenance_envelope_hash(
        reg, rep2, exec_commit="x"
    )


def test_rejects_claim_eligible_exclusions():
    reg = load_yaml(ROOT / "configs" / "final_evidence_registry_v2.yaml")
    reg = dict(reg)
    excl = dict(reg["exclusions"])
    bad = dict(excl["downsampling"])
    bad["claim_eligible"] = True
    excl["downsampling"] = bad
    reg["exclusions"] = excl
    assert any("downsampling" in e for e in validate_registry_v2(reg))


def test_create_tag_refuses_existing(monkeypatch):
    from timetrack import freeze_immutability as fi

    monkeypatch.setattr(fi, "tag_exists_local", lambda tag: True)
    monkeypatch.setattr(fi, "tag_exists_remote", lambda tag, remote="origin": False)
    with pytest.raises(SystemExit, match="already exists locally"):
        create_annotated_tag_immutable("final-reporting-freeze-v2", "msg")


@pytest.mark.skipif(
    not (ROOT / "results/final/robustness/04_robustness_statistics/MANIFEST.json").exists(),
    reason="robustness statistics pack not present",
)
@pytest.mark.skipif(
    not (ROOT / "results/final/archive/pre_robustness_aggregate/MANIFEST.json").exists(),
    reason="pre-robustness archive not present",
)
def test_aggregate_v2_smoke_on_real_artifacts(tmp_path: Path):
    reg = load_yaml(ROOT / "configs" / "final_evidence_registry_v2.yaml")
    rep = load_yaml(ROOT / "configs" / "final_reporting_v2.yaml")
    src = ROOT / "results/final/packs/03_cpu_classical/metrics/reconciliation_results.csv"
    before = sha256_file(src)
    out = tmp_path / "aggregate"
    result = run_final_aggregation_v2(registry=reg, reporting=rep, output_dir=out, smoke=False, require_frozen=False)
    assert (out / "tables" / "table02_cpu_forecasting_results.csv").exists()
    assert (out / "tables" / "table07_final_claim_matrix.csv").exists()
    assert (out / "figures" / "cpu_accuracy_vs_horizon.pdf").exists()
    assert (out / "figures" / "dlinear_memory_peak_bias_by_seed.pdf").exists()
    assert result["manifest"]["source_files_unchanged"] is True
    assert result["manifest"]["models_trained"] is False
    assert sha256_file(src) == before
    claims = pd.read_csv(out / "tables" / "table07_final_claim_matrix.csv")
    assert set(claims.claim) >= {"A1", "A2", "B1", "C2", "D3", "P5"}
    assert claims.set_index("claim").loc["A1", "classification"] == "supported"
    assert claims.set_index("claim").loc["C2", "classification"] in {"contradicted", "unsupported"}
    cpu = pd.read_csv(out / "tables" / "table02_cpu_forecasting_results.csv")
    assert "ewma" in set(cpu.base_model)
    assert set(cpu.unit.unique()) == {"cpu_weighted_mean_pct"}
