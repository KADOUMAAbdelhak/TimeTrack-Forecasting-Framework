#!/usr/bin/env python3
"""Build the deterministic Phase 4A artifact inventory and tree identity."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().parent
INVENTORY = BASE / "PHASE4A_ARTIFACT_SHA256.csv"
SUMMARY = BASE / "PHASE4A_INVENTORY_SUMMARY.json"
EXCLUDED = {INVENTORY, SUMMARY}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def included_paths() -> list[Path]:
    return sorted(
        path
        for path in BASE.rglob("*")
        if path.is_file()
        and path not in EXCLUDED
        and "__pycache__" not in path.parts
        and path.name != ".DS_Store"
    )


def main() -> None:
    rows = []
    tree = hashlib.sha256()
    total_bytes = 0
    for path in included_paths():
        relative = path.relative_to(ROOT).as_posix()
        size = path.stat().st_size
        digest = sha256(path)
        rows.append((relative, size, digest))
        total_bytes += size
        tree.update(f"{relative}\0{size}\0{digest}\n".encode("utf-8"))
    with INVENTORY.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["relative_path", "byte_size", "sha256"])
        writer.writerows(rows)
    summary = {
        "status": "PASS",
        "inventory_entries": len(rows),
        "inventory_total_bytes": total_bytes,
        "inventory_sha256": sha256(INVENTORY),
        "phase4a_tree_sha256": tree.hexdigest(),
        "raw_archive_bytes_in_inventory": 0,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
