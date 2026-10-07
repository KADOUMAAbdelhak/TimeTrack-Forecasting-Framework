#!/usr/bin/env python3
"""Build the compact Phase 4C V2 execution checkpoint inventory."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
INVENTORY = BASE / "PHASE4C_V2_EXECUTION_CHECKPOINT_SHA256.csv"
SUMMARY = BASE / "PHASE4C_V2_EXECUTION_CHECKPOINT_SUMMARY.json"

COMPACT_ARTIFACTS = {
    "manifest": [
        BASE / "PHASE4C_V2_EXECUTION_FREEZE_MANIFEST.md",
    ],
    "identity": [
        BASE / "configs/bitbrains_lstm_factorial_phase4c_v2.json",
        BASE / "EXTERNAL_SCIENTIFIC_DECISION_CRITERIA.md",
        BASE / "protocol_amendment/PHASE4C_V2_EXECUTION_CORRECTION_DECISION.md",
        BASE / "protocol_amendment/PHASE4C_V2_EXECUTION_CORRECTION_FREEZE_MANIFEST.md",
        BASE / "protocol_amendment/PHASE4C_V2_EXECUTION_CORRECTION_SHA256.csv",
        BASE / "protocol_amendment/PHASE4C_V2_SELECTED_COHORTS.csv",
        BASE / "protocol_amendment/PHASE4C_V2_SUPPORT_VALIDATION.json",
        BASE / "protocol_amendment/ABORTED_PRE_AMENDMENT_PROVENANCE.json",
        BASE / "protocol_amendment/ABORTED_PRE_AMENDMENT_RUNS.csv",
        BASE / "protocol_amendment/PHASE4C_V2_PROTOCOL_VALIDATION.json",
    ],
    "validator": [
        BASE / "build_phase4c_v2_execution_checkpoint.py",
        BASE / "run_phase4c_scientific.py",
        BASE / "validate_phase4c_environment.py",
        BASE / "validate_phase4c_v2_combined.py",
        BASE / "protocol_amendment/validate_phase4c_v2_protocol.py",
        BASE / "tests/test_phase4c_v2_execution_conformance.py",
    ],
    "technical_validation": [
        BASE / "outputs/scientific_v2/fastStorage/validation/technical_validation.json",
        BASE / "outputs/scientific_v2/Rnd/validation/technical_validation.json",
        BASE / "outputs/scientific_v2/validation/combined_technical_validation.json",
    ],
    "runtime": [
        BASE / "outputs/scientific_v2/fastStorage/runtime/runtime_accounting.json",
        BASE / "outputs/scientific_v2/Rnd/runtime/runtime_accounting.json",
        BASE / "outputs/scientific_v2/runtime/combined_runtime_storage_accounting.json",
    ],
    "heavy_artifact_identity": [
        BASE / "outputs/scientific_v2/runtime/PHASE4C_V2_EXECUTION_ARTIFACT_SHA256.csv",
        BASE / "outputs/scientific_v2/runtime/PHASE4C_V2_EXECUTION_INVENTORY_SUMMARY.json",
    ],
    "selection": [
        BASE / "outputs/scientific_v2/fastStorage/selected_contexts.csv",
        BASE / "outputs/scientific_v2/fastStorage/selected_epochs.csv",
        BASE / "outputs/scientific_v2/Rnd/selected_contexts.csv",
        BASE / "outputs/scientific_v2/Rnd/selected_epochs.csv",
    ],
    "metrics": [
        BASE / "outputs/scientific_v2/fastStorage/metrics.parquet",
        BASE / "outputs/scientific_v2/Rnd/metrics.parquet",
    ],
    "persistence": [
        BASE / "outputs/scientific_v2/fastStorage/persistence_metrics.parquet",
        BASE / "outputs/scientific_v2/Rnd/persistence_metrics.parquet",
    ],
    "loss_history": [
        BASE / "outputs/scientific_v2/fastStorage/m1_resource_loss_history.parquet",
        BASE / "outputs/scientific_v2/Rnd/m1_resource_loss_history.parquet",
    ],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    rows: list[tuple[str, int, str, str]] = []
    for category, artifacts in COMPACT_ARTIFACTS.items():
        for path in artifacts:
            if not path.is_file():
                raise FileNotFoundError(path)
            rows.append(
                (
                    path.relative_to(ROOT).as_posix(),
                    path.stat().st_size,
                    sha256(path),
                    category,
                )
            )
    rows.sort(key=lambda row: row[0])

    temporary = INVENTORY.with_suffix(".csv.tmp")
    with temporary.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["relative_path", "byte_size", "sha256", "category"])
        writer.writerows(rows)
    temporary.replace(INVENTORY)

    tree_payload = "".join(
        f"{relative_path},{byte_size},{digest}\n"
        for relative_path, byte_size, digest, _category in rows
    )
    summary = {
        "scope": "explicit compact checkpoint artifacts; inventory and summary excluded from their own scope",
        "entry_count": len(rows),
        "total_compact_bytes": sum(row[1] for row in rows),
        "compact_inventory_sha256": sha256(INVENTORY),
        "checkpoint_tree_sha256": hashlib.sha256(tree_payload.encode()).hexdigest(),
        "heavy_models_and_predictions_included": False,
    }
    temporary_summary = SUMMARY.with_suffix(".json.tmp")
    temporary_summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    temporary_summary.replace(SUMMARY)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
