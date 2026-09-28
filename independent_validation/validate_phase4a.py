#!/usr/bin/env python3
"""Validate Phase 4A structural/design artifacts without model execution."""

from __future__ import annotations

import hashlib
import json
import subprocess
import csv
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().parent
RAW = ROOT / "data/external/raw"
AUDIT = BASE / "01_dataset_audit"

EXPECTED_HEAD = "f9b11adb5dc3a0c2802703ceb1cbafb060c6f341"
EXPECTED_ARCHIVES = {
    "gwa_t_12_fastStorage.zip": "11313f528a0cbcbe57e63162f8ae5a41a9c7e7c1a79872e294ff3c5bbaa2e671",
    "gwa_t_12_rnd.zip": "d3d9ddebb689c0b5463f2e4cfd8956e84bdcdf138b4476320855393e2b229a06",
    "gwa_t_13_materna.zip": "1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4",
}
REQUIRED = [
    BASE / "PHASE4A_INDEPENDENT_DATA_SCOPE_REPORT.md",
    BASE / "PHASE4A_FREEZE_MANIFEST.md",
    BASE / "PHASE4A_ARTIFACT_SHA256.csv",
    BASE / "PHASE4A_INVENTORY_SUMMARY.json",
    AUDIT / "INDEPENDENCE_LEDGER.md",
    AUDIT / "SOURCE_AND_ACQUISITION_RECORD.md",
    AUDIT / "EXTERNAL_DATASET_STRUCTURAL_AUDIT.csv",
    BASE / "02_harmonization/TARGET_HARMONIZATION_MATRIX.csv",
    BASE / "02_harmonization/DATASET_COMPATIBILITY_SCORECARD.csv",
    BASE / "02_harmonization/REAL_TIME_HORIZON_HARMONIZATION.csv",
    BASE / "02_harmonization/CONTEXT_WINDOW_HARMONIZATION.csv",
    BASE / "02_harmonization/TRANSFORMATION_COMPATIBILITY.csv",
    BASE / "03_evaluation_design/ENTITY_SELECTION_POLICY.md",
    BASE / "03_evaluation_design/EXTERNAL_REPLICATION_DESIGN.md",
    BASE / "03_evaluation_design/SELECTED_ENTITY_COHORTS.csv",
    BASE / "03_evaluation_design/SELECTED_ENTITY_COHORTS_SUMMARY.json",
    BASE / "04_research_scope/NEW_TIMETRACK_DATA_FEASIBILITY.md",
    BASE / "04_research_scope/PUBLICATION_SCOPE_AND_NOVELTY_AUDIT.md",
    BASE / "04_research_scope/DATASET_ROLE_DECISION.csv",
    BASE / "04_research_scope/PHASE4A_DECISION.md",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def expected_selection(entities: pd.DataFrame) -> pd.DataFrame:
    eligible = entities[entities.structurally_eligible.astype(bool)].copy()
    rows = []
    specifications = [
        ("GWA-T-12_Bitbrains_fastStorage", "PRIMARY_EXTERNAL_CONFIRMATION", None),
        ("GWA-T-12_Bitbrains_Rnd", "PRIMARY_EXTERNAL_CONFIRMATION", None),
    ]
    for environment, role, token in specifications:
        ids = set(eligible.loc[eligible.dataset.eq(environment), "entity"])
        ranked = []
        for entity_id in ids:
            key = f"phase4a-v1|{token or environment}|{entity_id}"
            ranked.append((text_digest(key), entity_id, key))
        for rank, (digest, entity_id, key) in enumerate(sorted(ranked)[:35], start=1):
            rows.append([role, environment, rank, entity_id, key, digest])
    materna = [
        set(eligible.loc[eligible.dataset.eq(f"GWA-T-13_Materna_trace_{trace}"), "entity"])
        for trace in (1, 2, 3)
    ]
    ranked = []
    for entity_id in set.intersection(*materna):
        key = f"phase4a-v1|Materna-shared|{entity_id}"
        ranked.append((text_digest(key), entity_id, key))
    for rank, (digest, entity_id, key) in enumerate(sorted(ranked)[:35], start=1):
        rows.append([
            "SECONDARY_EXTERNAL_REPLICATION_NOT_PRIMARY_EXECUTION",
            "GWA-T-13_Materna_shared_all_three",
            rank,
            entity_id,
            key,
            digest,
        ])
    return pd.DataFrame(rows, columns=[
        "cohort_role", "environment", "rank", "entity_id", "selection_key", "selection_sha256"
    ])


def verify_inventory() -> tuple[dict[str, object], list[str]]:
    failures = []
    inventory = BASE / "PHASE4A_ARTIFACT_SHA256.csv"
    summary_path = BASE / "PHASE4A_INVENTORY_SUMMARY.json"
    if not inventory.exists() or not summary_path.exists():
        return {}, ["inventory_missing"]
    summary = json.loads(summary_path.read_text())
    tree = hashlib.sha256()
    total = 0
    entries = 0
    with inventory.open(newline="") as stream:
        for row in csv.DictReader(stream):
            path = ROOT / row["relative_path"]
            size = int(row["byte_size"])
            digest = row["sha256"]
            if not path.is_file() or path.stat().st_size != size or sha256(path) != digest:
                failures.append(f"inventory_entry:{row['relative_path']}")
            tree.update(f"{row['relative_path']}\0{size}\0{digest}\n".encode("utf-8"))
            total += size
            entries += 1
    expected = {
        "inventory_entries": entries,
        "inventory_total_bytes": total,
        "inventory_sha256": sha256(inventory),
        "phase4a_tree_sha256": tree.hexdigest(),
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            failures.append(f"inventory_summary:{key}")
    return summary, failures


def main() -> None:
    failures: list[str] = []
    actual_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tag_target = subprocess.check_output(
        ["git", "rev-parse", "phase3d-posthoc-research-boundary-freeze-v1^{}"],
        cwd=ROOT,
        text=True,
    ).strip()
    if actual_head != EXPECTED_HEAD or tag_target != EXPECTED_HEAD:
        failures.append(f"frozen_head_or_tag:{actual_head}:{tag_target}")
    phase3d = json.loads((ROOT / "multiresource/05_posthoc_audit/validation.json").read_text())
    if phase3d.get("status") != "PASS":
        failures.append("phase3d_validation")
    for path in REQUIRED:
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(f"missing_or_empty:{path.relative_to(ROOT)}")
    for name, expected in EXPECTED_ARCHIVES.items():
        path = RAW / name
        if not path.is_file() or sha256(path) != expected:
            failures.append(f"archive_identity:{name}")

    structural = pd.read_csv(AUDIT / "EXTERNAL_DATASET_STRUCTURAL_AUDIT.csv")
    entities = pd.read_csv(AUDIT / "ENTITY_STRUCTURAL_ELIGIBILITY.csv", dtype={"entity": str})
    horizons = pd.read_csv(BASE / "02_harmonization/REAL_TIME_HORIZON_HARMONIZATION.csv")
    contexts = pd.read_csv(BASE / "02_harmonization/CONTEXT_WINDOW_HARMONIZATION.csv")
    roles = pd.read_csv(BASE / "04_research_scope/DATASET_ROLE_DECISION.csv")
    expected_eligible = {
        "GWA-T-12_Bitbrains_fastStorage": 916,
        "GWA-T-12_Bitbrains_Rnd": 416,
        "GWA-T-13_Materna_trace_1": 475,
        "GWA-T-13_Materna_trace_2": 483,
        "GWA-T-13_Materna_trace_3": 495,
    }
    actual_eligible = entities.groupby("dataset").structurally_eligible.sum().astype(int).to_dict()
    if actual_eligible != expected_eligible:
        failures.append(f"eligible_counts:{actual_eligible}")
    if int(structural.audit_basis.eq("OFFICIAL_RAW_ARCHIVE").sum()) != 5:
        failures.append("raw_partition_count")
    if len(entities) != 3343:
        failures.append("entity_record_count")
    if not horizons.acceptable.eq("YES").all() or len(horizons) != 30:
        failures.append("horizon_mapping")
    if not contexts.acceptable.eq("YES").all() or len(contexts) != 6:
        failures.append("context_mapping")
    if roles.role.eq("PRIMARY_EXTERNAL_CONFIRMATION").sum() != 2:
        failures.append("primary_role_count")
    selected = pd.read_csv(
        BASE / "03_evaluation_design/SELECTED_ENTITY_COHORTS.csv", dtype={"entity_id": str}
    )
    reproducible = expected_selection(entities)
    if not selected.equals(reproducible):
        failures.append("selected_entity_reproduction")
    if selected.groupby("environment").size().to_dict() != {
        "GWA-T-12_Bitbrains_Rnd": 35,
        "GWA-T-12_Bitbrains_fastStorage": 35,
        "GWA-T-13_Materna_shared_all_three": 35,
    }:
        failures.append("selected_entity_counts")
    inventory_summary, inventory_failures = verify_inventory()
    failures.extend(inventory_failures)
    forbidden = [
        path.relative_to(ROOT).as_posix()
        for path in BASE.rglob("*")
        if path.is_file()
        and (path.suffix.lower() in {".pt", ".pth", ".ckpt", ".parquet"} or "prediction" in path.name.lower())
    ]
    if forbidden:
        failures.append(f"external_predictive_artifacts:{forbidden}")

    report = (BASE / "PHASE4A_INDEPENDENT_DATA_SCOPE_REPORT.md").read_text()
    for phrase in [
        "EXTERNAL_CONFIRMATION_FEASIBLE_WITH_PROTOCOL_ADAPTATION",
        "trained zero forecasting models",
        "No commit or push was performed",
    ]:
        if phrase not in report:
            failures.append(f"report_phrase:{phrase}")

    result = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "expected_prefreeze_head": EXPECTED_HEAD,
        "actual_head": actual_head,
        "phase3d_tag_target": tag_target,
        "frozen_history_validation": phase3d.get("status"),
        "canonical_panel_sha256": phase3d.get("checks", {}).get("canonical_panel_sha256"),
        "raw_hashes_unchanged": phase3d.get("checks", {}).get("raw_hashes_unchanged"),
        "official_archives_verified": len(EXPECTED_ARCHIVES),
        "raw_dataset_partitions": 5,
        "entity_records": len(entities),
        "eligible_entities": expected_eligible,
        "selected_entities": selected.groupby("environment").size().astype(int).to_dict(),
        "selected_entity_reproduction": True,
        "forecasting_models_trained": 0,
        "external_predictive_performance_inspected": False,
        "new_architectures_implemented": 0,
        "decision": "EXTERNAL_CONFIRMATION_FEASIBLE_WITH_PROTOCOL_ADAPTATION",
    }
    (BASE / "PHASE4A_VALIDATION.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
