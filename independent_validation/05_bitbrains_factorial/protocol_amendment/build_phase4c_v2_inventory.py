#!/usr/bin/env python3
"""Build the non-circular Phase 4C V2 amendment artifact inventory."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
OUT = HERE / "PHASE4C_V2_ARTIFACT_SHA256.csv"

ARTIFACTS = [
    BASE / "EXTERNAL_SCIENTIFIC_DECISION_CRITERIA.md",
    BASE / "PHASE4C_EXECUTION_BLOCKER_REPORT.md",
    BASE / "audit_phase4c_iqr_gate.py",
    BASE / "configs/bitbrains_lstm_factorial_phase4c_v2.json",
    BASE / "run_phase4c_scientific.py",
    BASE / "validate_phase4c_environment.py",
    HERE / "ABORTED_PRE_AMENDMENT_PROVENANCE.json",
    HERE / "ABORTED_PRE_AMENDMENT_RUNS.csv",
    HERE / "CANDIDATE_V2_COHORTS.csv",
    HERE / "CANDIDATE_V2_COHORTS_SUMMARY.json",
    HERE / "CANDIDATE_V2_SUPPORT_MANIFEST.parquet",
    HERE / "CANDIDATE_V2_SUPPORT_SUMMARY.csv",
    HERE / "CANDIDATE_V2_SUPPORT_VALIDATION.json",
    HERE / "PHASE4C_PROTOCOL_AMENDMENT_DECISION.md",
    HERE / "PHASE4C_TRAINING_SCALE_ELIGIBILITY_AUDIT_REPORT.md",
    HERE / "PHASE4C_V2_PROTOCOL_VALIDATION.json",
    HERE / "PHASE4C_V2_SCALER_PARTITIONS.csv",
    HERE / "PHASE4C_V2_SELECTED_COHORTS.csv",
    HERE / "PHASE4C_V2_SUPPORT_MANIFEST.parquet",
    HERE / "PHASE4C_V2_SUPPORT_SUMMARY.csv",
    HERE / "PHASE4C_V2_SUPPORT_VALIDATION.json",
    HERE / "TRAINING_SCALE_ELIGIBILITY.csv",
    HERE / "TRAINING_SCALE_ELIGIBILITY_SUMMARY.json",
    HERE / "TRAINING_SCALE_ELIGIBILITY_VALIDATION.json",
    HERE / "ZERO_IQR_PREVALENCE.csv",
    HERE / "audit_training_scale_eligibility.py",
    HERE / "materialize_phase4c_v2.py",
    HERE / "validate_phase4c_v2_protocol.py",
    HERE / "validate_training_scale_eligibility.py",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    rows = []
    for path in sorted(ARTIFACTS):
        if not path.is_file():
            raise FileNotFoundError(path)
        rows.append({
            "relative_path": path.relative_to(ROOT).as_posix(),
            "byte_size": path.stat().st_size,
            "sha256": sha256(path),
        })
    frame = pd.DataFrame(rows).sort_values("relative_path")
    frame.to_csv(OUT, index=False)
    tree_payload = "".join(
        f"{row.relative_path},{row.byte_size},{row.sha256}\n"
        for row in frame.itertuples(index=False)
    )
    print(f"entries={len(frame)}")
    print(f"total_bytes={int(frame.byte_size.sum())}")
    print(f"inventory_sha256={sha256(OUT)}")
    print(f"amendment_tree_sha256={hashlib.sha256(tree_payload.encode()).hexdigest()}")


if __name__ == "__main__":
    main()
