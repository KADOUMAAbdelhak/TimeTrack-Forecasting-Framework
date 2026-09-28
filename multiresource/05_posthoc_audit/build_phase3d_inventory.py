#!/usr/bin/env python3
"""Build or verify the Phase 3D artifact inventory without circular hashes."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
INVENTORY = BASE / "PHASE3D_ARTIFACT_SHA256.csv"
BOUNDARY = ROOT / "multiresource/MULTIRESOURCE_RESEARCH_BOUNDARY.md"
EXCLUDED = {INVENTORY, BASE / "PHASE3D_FREEZE_MANIFEST.md"}


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def artifact_paths() -> list[Path]:
    paths = [path for path in BASE.rglob("*") if path.is_file()]
    paths.append(BOUNDARY)
    return sorted(
        {
            path.resolve()
            for path in paths
            if path.resolve() not in {item.resolve() for item in EXCLUDED}
            and "__pycache__" not in path.parts
            and path.suffix not in {".pyc", ".pyo"}
        },
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def records() -> list[tuple[str, int, str]]:
    return [
        (path.relative_to(ROOT).as_posix(), path.stat().st_size, sha256(path))
        for path in artifact_paths()
    ]


def tree_sha256(rows: list[tuple[str, int, str]]) -> str:
    value = hashlib.sha256()
    for relative_path, byte_size, digest in rows:
        value.update(f"{relative_path},{byte_size},{digest}\n".encode("utf-8"))
    return value.hexdigest()


def write_inventory(rows: list[tuple[str, int, str]]) -> None:
    with INVENTORY.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["relative_path", "byte_size", "sha256"])
        writer.writerows(rows)


def read_inventory() -> list[tuple[str, int, str]]:
    with INVENTORY.open(newline="") as stream:
        return [
            (row["relative_path"], int(row["byte_size"]), row["sha256"])
            for row in csv.DictReader(stream)
        ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    current = records()
    if args.verify:
        recorded = read_inventory()
        if recorded != current:
            raise SystemExit("Phase 3D artifact inventory mismatch")
    else:
        write_inventory(current)
    print(f"entries={len(current)}")
    print(f"total_bytes={sum(row[1] for row in current)}")
    print(f"inventory_sha256={sha256(INVENTORY)}")
    print(f"tree_sha256={tree_sha256(current)}")


if __name__ == "__main__":
    main()
