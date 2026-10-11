#!/usr/bin/env python3
"""Build or verify the compact Phase 4D execution-conformance inventory."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from phase4d_execution import BASE, ROOT, sha256_file


INVENTORY = BASE / "PHASE4D_EXECUTION_CONFORMANCE_SHA256.csv"
SUMMARY = BASE / "PHASE4D_EXECUTION_CONFORMANCE_INVENTORY_SUMMARY.json"
FILES = (
    "PHASE4D_EXECUTION_CONFORMANCE_DECISION.md",
    "PHASE4D_EXECUTION_CONFORMANCE_FREEZE_MANIFEST.md",
    "PHASE4D_EXECUTION_CONFORMANCE_VALIDATION.json",
    "PHASE4D_EXECUTION_CONFORMANCE_DIFF_AUDIT.json",
    "PHASE4D_DRY_RUN_PLAN_SUMMARY.json",
    "PHASE4D_MATERNA_PREFLIGHT_VALIDATION.json",
    "audit_phase4d_execution_conformance_diff.py",
    "build_phase4d_execution_conformance_inventory.py",
    "phase4d_execution.py",
    "run_phase4d_scientific.py",
    "tests/test_phase4d_execution_conformance.py",
    "validate_phase4d_combined.py",
    "validate_phase4d_execution_conformance.py",
    "validate_phase4d_preflight.py",
    "validate_phase4d_trace.py",
)


def rows() -> list[tuple[str, int, str]]:
    result = []
    for name in FILES:
        path = BASE / name
        if not path.is_file():
            raise FileNotFoundError(path)
        result.append((path.relative_to(ROOT).as_posix(), path.stat().st_size, sha256_file(path)))
    return sorted(result)


def tree_hash(values: list[tuple[str, int, str]]) -> str:
    payload = "".join(f"{path},{size},{digest}\n" for path, size, digest in values)
    return hashlib.sha256(payload.encode()).hexdigest()


def build() -> dict[str, object]:
    values = rows()
    with INVENTORY.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("relative_path", "byte_size", "sha256"))
        writer.writerows(values)
    summary = {
        "entry_count": len(values), "total_bytes": sum(row[1] for row in values),
        "inventory_sha256": sha256_file(INVENTORY),
        "execution_conformance_tree_sha256": tree_hash(values),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def verify() -> dict[str, object]:
    expected = rows()
    with INVENTORY.open(newline="") as stream:
        observed = [(row["relative_path"], int(row["byte_size"]), row["sha256"]) for row in csv.DictReader(stream)]
    if observed != expected:
        raise SystemExit("inventory content mismatch")
    summary = json.loads(SUMMARY.read_text())
    actual = {
        "entry_count": len(expected), "total_bytes": sum(row[1] for row in expected),
        "inventory_sha256": sha256_file(INVENTORY),
        "execution_conformance_tree_sha256": tree_hash(expected),
    }
    if summary != actual:
        raise SystemExit("inventory summary mismatch")
    return actual


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify() if args.verify else build(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
