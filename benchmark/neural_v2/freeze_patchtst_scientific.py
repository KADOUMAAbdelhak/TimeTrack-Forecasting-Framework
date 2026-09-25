#!/usr/bin/env python3
"""Create the committed inventory for immutable local PatchTST outputs."""

from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = ROOT / "benchmark/neural_v2/outputs/patchtst"
INVENTORY = ROOT / "benchmark/neural_v2/PATCHTST_SCIENTIFIC_ARTIFACT_SHA256.csv"
EXPECTED_FILE_COUNT = 1352
EXPECTED_BYTE_COUNT = 53_994_678
EXPECTED_TREE_SHA256 = "8eb7fbe338660fb07a6ef58df0670c29318812c844c895d5af18eeb4250f4e52"


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
    for path, (_relative, _size, digest) in zip(paths, records):
        # The accepted PatchTST tree identity was prospectively recorded with
        # paths relative to the PatchTST output root.
        output_relative = str(path.relative_to(OUTPUTS))
        tree_digest.update(output_relative.encode() + b"\0" + digest.encode() + b"\n")
    actual_tree = tree_digest.hexdigest()
    actual_bytes = sum(record[1] for record in records)
    if len(records) != EXPECTED_FILE_COUNT:
        raise RuntimeError(f"PatchTST artifact count changed: {len(records)} != {EXPECTED_FILE_COUNT}")
    if actual_bytes != EXPECTED_BYTE_COUNT:
        raise RuntimeError(f"PatchTST artifact bytes changed: {actual_bytes} != {EXPECTED_BYTE_COUNT}")
    if actual_tree != EXPECTED_TREE_SHA256:
        raise RuntimeError(f"PatchTST artifact tree changed: {actual_tree} != {EXPECTED_TREE_SHA256}")
    temporary = INVENTORY.with_suffix(INVENTORY.suffix + ".tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("path", "size_bytes", "sha256"))
        writer.writerows(records)
    os.replace(temporary, INVENTORY)
    print(f"files={len(records)}")
    print(f"bytes={actual_bytes}")
    print(f"tree_sha256={actual_tree}")
    print(f"inventory_sha256={sha256_file(INVENTORY)}")


if __name__ == "__main__":
    main()
