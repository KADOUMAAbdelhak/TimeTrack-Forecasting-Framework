#!/usr/bin/env python3
"""Build the correction-checkpoint inventory after all artifacts are final."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parents[1]
OUT = HERE / "PHASE4C_V2_EXECUTION_CORRECTION_SHA256.csv"
ARTIFACTS = [
    BASE / "run_phase4c_scientific.py",
    BASE / "validate_phase4c_environment.py",
    BASE / "tests/test_phase4c_v2_execution_conformance.py",
    HERE / "PHASE4C_V2_EXECUTION_CORRECTION_DECISION.md",
    HERE / "PHASE4C_V2_EXECUTION_CORRECTION_DIFF_AUDIT.json",
    HERE / "PHASE4C_V2_EXECUTION_CORRECTION_FREEZE_MANIFEST.md",
    HERE / "PHASE4C_V2_PROTOCOL_VALIDATION.json",
    HERE / "audit_phase4c_v2_execution_correction_diff.py",
    HERE / "build_phase4c_v2_execution_correction_inventory.py",
    HERE / "validate_phase4c_v2_protocol.py",
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
    print(f"corrected_execution_tree_sha256={hashlib.sha256(tree_payload.encode()).hexdigest()}")


if __name__ == "__main__":
    main()
