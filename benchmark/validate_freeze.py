#!/usr/bin/env python3
"""Validate the Phase 2A freeze without executing the full benchmark."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

from benchmark.src.data import (
    EXPECTED_PANEL_SHA256,
    PANEL_PATH,
    sha256_file,
    verify_raw_hashes,
)
from benchmark.src.features import FEATURE_SET_IDS


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmark"
OUTPUTS = BENCHMARK / "outputs"
FORBIDDEN_NAMES = [
    "proposed_model",
    "novel_model",
    "our_model",
    "context_fusion_model",
    "attention_fusion",
    "adaptive_gate",
]


def main() -> None:
    smoke = json.loads((OUTPUTS / "smoke" / "smoke_validation.json").read_text())
    boundaries = pd.read_csv(OUTPUTS / "joint_fold_boundaries.csv")
    comparison = pd.read_csv(OUTPUTS / "joint_eligibility_comparison.csv")
    registry = pd.read_csv(OUTPUTS / "run_registry.csv")
    metrics = pd.read_parquet(OUTPUTS / "metrics.parquet")
    selected = pd.read_csv(OUTPUTS / "selected_configs.csv")
    xml_root = ET.parse(OUTPUTS / "pytest.xml").getroot()
    suites = (
        [xml_root]
        if xml_root.tag == "testsuite"
        else list(xml_root.findall("testsuite"))
    )
    tests = sum(int(suite.attrib.get("tests", 0)) for suite in suites)
    failures = sum(int(suite.attrib.get("failures", 0)) for suite in suites)
    errors = sum(int(suite.attrib.get("errors", 0)) for suite in suites)
    benchmark_paths = [str(path.relative_to(BENCHMARK)).lower() for path in BENCHMARK.rglob("*")]
    forbidden = [
        name for name in FORBIDDEN_NAMES if any(name in path for path in benchmark_paths)
    ]
    validation = {
        "status": "PASS",
        "scientific_task": "seven machine CPU targets; eight real future leads jointly",
        "feature_sets": FEATURE_SET_IDS,
        "model_families": [
            "Persistence",
            "Ridge",
            "LightGBM",
            "DLinear",
            "TCN",
        ],
        "expected_outer_run_records": 1890,
        "expected_lead_metric_rows": 15120,
        "full_benchmark_executed": False,
        "empty_run_registry_rows": len(registry),
        "empty_metric_rows": len(metrics),
        "empty_selected_config_rows": len(selected),
        "joint_fold_rows": len(boundaries),
        "joint_fold_leakage_failures": int((~boundaries["leakage_check"]).sum()),
        "joint_eligible_range": [
            int(boundaries["joint_eligible_n"].min()),
            int(boundaries["joint_eligible_n"].max()),
        ],
        "eligibility_comparison_rows": len(comparison),
        "unit_tests": tests,
        "unit_test_failures": failures,
        "unit_test_errors": errors,
        "smoke_status": smoke["status"],
        "smoke_model_feature_executions": smoke["model_feature_executions"],
        "smoke_outputs_all_n_by_8": smoke["all_output_shapes_n_by_8"],
        "phase1c_boundary_equivalence": smoke["phase1c_boundary_equivalence"],
        "outer_target_time_leakage": smoke["outer_target_time_leakage"],
        "inner_target_time_leakage": smoke["inner_target_time_leakage"],
        "segment_crossings": smoke["segment_crossings"],
        "outer_test_used_for_selection": smoke["outer_test_used_for_selection"],
        "canonical_panel_unchanged": sha256_file(PANEL_PATH)
        == EXPECTED_PANEL_SHA256,
        "raw_hashes_match_phase1": verify_raw_hashes(),
        "forbidden_model_names": forbidden,
    }
    required = [
        not validation["full_benchmark_executed"],
        validation["empty_run_registry_rows"] == 0,
        validation["empty_metric_rows"] == 0,
        validation["empty_selected_config_rows"] == 0,
        validation["joint_fold_rows"] == 35,
        validation["joint_fold_leakage_failures"] == 0,
        validation["eligibility_comparison_rows"] == 56,
        validation["unit_tests"] >= 18,
        validation["unit_test_failures"] == 0,
        validation["unit_test_errors"] == 0,
        validation["smoke_status"] == "PASS",
        validation["smoke_model_feature_executions"] == 10,
        validation["smoke_outputs_all_n_by_8"],
        validation["phase1c_boundary_equivalence"]["pass"],
        validation["outer_target_time_leakage"] == 0,
        validation["inner_target_time_leakage"] == 0,
        validation["segment_crossings"] == 0,
        not validation["outer_test_used_for_selection"],
        validation["canonical_panel_unchanged"],
        validation["raw_hashes_match_phase1"],
        not validation["forbidden_model_names"],
    ]
    if not all(required):
        validation["status"] = "FAIL"
        raise RuntimeError(json.dumps(validation, indent=2))
    (OUTPUTS / "phase2a_validation.json").write_text(
        json.dumps(validation, indent=2) + "\n"
    )
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
