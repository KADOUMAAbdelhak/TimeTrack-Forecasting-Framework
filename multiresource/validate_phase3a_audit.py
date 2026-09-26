#!/usr/bin/env python3
"""Validate Phase 3A discovery artifacts without fitting a model."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark.neural_v2.src.data import EXPECTED_PANEL_SHA256


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "multiresource"
AUDIT = BASE / "01_target_audit"
PANEL = ROOT / "discovery/02_dependency_analysis/outputs/canonical_panel.parquet"
REGISTRY = ROOT / "discovery/02_dependency_analysis/outputs/canonical_signal_registry.csv"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    failures: list[str] = []
    panel = pd.read_parquet(PANEL)
    design = json.loads((AUDIT / "MULTIRESOURCE_DESIGN_REGION.json").read_text())
    indices = np.arange(design["row_count"], dtype="<i8")
    timestamps = pd.to_datetime(panel.timestamp.iloc[indices]).astype("int64").to_numpy(dtype="<i8")
    segments = panel.segment_id.iloc[indices].to_numpy(dtype="<i8")
    membership = hashlib.sha256(indices.tobytes() + timestamps.tobytes() + segments.tobytes()).hexdigest()
    if membership != design["membership_sha256"]:
        failures.append("design membership hash")
    if design["end_index_inclusive"] + 1 != design["excluded_first_test_or_later_start_index"]:
        failures.append("design boundary")
    if min(item["first_test_origin_index"] for item in design["frozen_machine_first_test_boundaries"].values()) != design["excluded_first_test_or_later_start_index"]:
        failures.append("earliest frozen test boundary")

    candidates = pd.read_csv(AUDIT / "TARGET_CANDIDATE_REGISTRY.csv")
    required = {
        "resource_family","candidate_name","machine","canonical_column","raw_source_file",
        "raw_source_columns","units_if_known","semantic_description","aggregation_formula_if_any",
        "finite_count","missing_count","zero_fraction","constant_flag","near_constant_flag",
        "negative_value_count","min","max","median","mean","std","q01","q05","q25",
        "q75","q95","q99","duplicate_or_identity_notes","prior_quality_notes","recommendation_status",
    }
    if len(candidates) != 91 or not required.issubset(candidates.columns):
        failures.append("candidate registry")
    allowed = {"PRIMARY_TARGET_CANDIDATE","SECONDARY_TARGET_CANDIDATE","AUXILIARY_ONLY","REJECT_FOR_MULTI_TARGET"}
    if not set(candidates.recommendation_status).issubset(allowed):
        failures.append("candidate labels")

    support = pd.read_csv(AUDIT / "JOINT_SUPPORT_AUDIT.csv")
    dependencies = pd.read_csv(BASE / "02_dependency_design/LAGGED_SPEARMAN_DEPENDENCIES.csv")
    if len(support) != 630 or len(dependencies) != 1512:
        failures.append("audit coverage")
    figures = sorted((AUDIT / "figures").glob("*.png"))
    if len(figures) != 6 or any(path.stat().st_size == 0 for path in figures):
        failures.append("figure coverage")

    log_inverse_max = 0.0
    for suffix in ("throughput_total", "disk_write"):
        for machine in (f"machine{i:02d}" for i in range(1, 8)):
            values = panel[f"{machine}__{suffix}"].dropna().to_numpy(dtype=float)
            if np.any(values < 0):
                failures.append(f"negative {suffix}")
            log_inverse_max = max(log_inverse_max, float(np.max(np.abs(np.expm1(np.log1p(values)) - values))))

    result = {
        "status":"PASS" if not failures else "FAIL",
        "scientific_execution":"NONE",
        "model_implementation":"NONE",
        "canonical_panel_sha256":digest(PANEL),
        "canonical_panel_expected":EXPECTED_PANEL_SHA256,
        "canonical_registry_sha256":digest(REGISTRY),
        "design_region_membership_sha256":membership,
        "design_region_json_sha256":digest(AUDIT / "MULTIRESOURCE_DESIGN_REGION.json"),
        "candidate_rows":len(candidates),"support_rows":len(support),"dependency_rows":len(dependencies),
        "figure_count":len(figures),"log1p_inverse_max_abs_error":log_inverse_max,
        "failures":failures,
    }
    (BASE / "PHASE3A_AUDIT_VALIDATION.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures or digest(PANEL) != EXPECTED_PANEL_SHA256:
        raise RuntimeError("Phase 3A audit validation failed")


if __name__ == "__main__":
    main()
