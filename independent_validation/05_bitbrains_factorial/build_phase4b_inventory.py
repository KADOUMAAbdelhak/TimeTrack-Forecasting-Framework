#!/usr/bin/env python3
"""Build or verify the deterministic Phase 4B preflight artifact inventory."""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
INVENTORY = BASE / "PHASE4B_ARTIFACT_SHA256.csv"
FREEZE_MANIFEST = BASE / "PHASE4B_PROTOCOL_FREEZE_MANIFEST.md"
EXCLUDED = {INVENTORY.resolve(), FREEZE_MANIFEST.resolve()}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_paths() -> list[Path]:
    return sorted(
        (
            path.resolve()
            for path in BASE.rglob("*")
            if path.is_file()
            and path.resolve() not in EXCLUDED
            and "__pycache__" not in path.parts
            and path.suffix not in {".pyc", ".pyo"}
            and path.name != ".DS_Store"
        ),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def records() -> list[tuple[str, int, str]]:
    return [
        (path.relative_to(ROOT).as_posix(), path.stat().st_size, sha256(path))
        for path in artifact_paths()
    ]


def tree_sha256(rows: list[tuple[str, int, str]]) -> str:
    digest = hashlib.sha256()
    for relative_path, byte_size, artifact_sha256 in rows:
        digest.update(
            f"{relative_path},{byte_size},{artifact_sha256}\n".encode("utf-8")
        )
    return digest.hexdigest()


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
        if read_inventory() != current:
            raise SystemExit("Phase 4B artifact inventory mismatch")
    else:
        write_inventory(current)
    print(f"entries={len(current)}")
    print(f"total_bytes={sum(row[1] for row in current)}")
    print(f"inventory_sha256={sha256(INVENTORY)}")
    print(f"tree_sha256={tree_sha256(current)}")


if __name__ == "__main__":
    main()
