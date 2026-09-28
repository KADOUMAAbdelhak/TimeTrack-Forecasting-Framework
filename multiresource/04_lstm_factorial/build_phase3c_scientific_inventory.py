#!/usr/bin/env python3
"""Build the canonical Phase 3C scientific artifact inventory."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "PHASE3C_SCIENTIFIC_ARTIFACT_SHA256.csv"
TOP_LEVEL = (
    "FACTORIAL_SCIENTIFIC_DECISION_CRITERIA.md",
    "PHASE3C_FACTORIAL_SCIENTIFIC_REPORT.md",
    "run_factorial_scientific.py",
    "analyze_factorial_scientific.py",
    "validate_factorial_scientific.py",
    "build_phase3c_scientific_inventory.py",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    paths = [BASE / name for name in TOP_LEVEL]
    paths.extend(path for path in (BASE / "outputs/scientific").rglob("*") if path.is_file())
    paths = sorted(set(paths), key=lambda path: path.relative_to(ROOT).as_posix())
    rows = []
    tree_digest = hashlib.sha256()
    total_bytes = 0
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        size = path.stat().st_size
        digest = sha256(path)
        rows.append((relative, size, digest))
        total_bytes += size
        tree_digest.update(f"{relative},{size},{digest}\n".encode())
    with OUTPUT.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("relative_path", "byte_size", "sha256"))
        writer.writerows(rows)
    result = {
        "inventory_entries": len(rows),
        "inventory_sha256": sha256(OUTPUT),
        "scientific_tree_sha256": tree_digest.hexdigest(),
        "total_bytes": total_bytes,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
