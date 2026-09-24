#!/usr/bin/env python3
"""Create the committed inventory for the immutable local DLinear outputs."""

from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = ROOT / "benchmark/neural_v2/outputs/dlinear"
INVENTORY = ROOT / "benchmark/neural_v2/DLINEAR_SCIENTIFIC_ARTIFACT_SHA256.csv"
EXPECTED_TREE_SHA256 = "f36561563c8b4b541edea0d930d0eb7e4ffdfe5cd4d546ee56041fe23ffb4371"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    paths = sorted(path for path in OUTPUTS.rglob("*") if path.is_file())
    records = [
        (str(path.relative_to(ROOT)), path.stat().st_size, sha256_file(path))
        for path in paths
    ]
    tree_digest = hashlib.sha256()
    for relative, _size, digest in records:
        tree_digest.update(relative.encode() + b"\0" + digest.encode() + b"\n")
    actual_tree_sha256 = tree_digest.hexdigest()
    if actual_tree_sha256 != EXPECTED_TREE_SHA256:
        raise RuntimeError(
            f"DLinear artifact tree changed: {actual_tree_sha256} != {EXPECTED_TREE_SHA256}"
        )
    temporary = INVENTORY.with_suffix(INVENTORY.suffix + ".tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("path", "size_bytes", "sha256"))
        writer.writerows(records)
    os.replace(temporary, INVENTORY)
    print(f"files={len(records)}")
    print(f"bytes={sum(record[1] for record in records)}")
    print(f"tree_sha256={actual_tree_sha256}")
    print(f"inventory_sha256={sha256_file(INVENTORY)}")


if __name__ == "__main__":
    main()
