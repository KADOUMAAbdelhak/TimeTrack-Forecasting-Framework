#!/usr/bin/env python3
"""Build the compact Phase 4C V2 scientific-analysis checkpoint inventory."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / "outputs/scientific_v2"
ANALYSIS = OUT / "analysis"
ANALYSIS_INVENTORY = ANALYSIS / "PHASE4C_V2_ANALYSIS_ARTIFACT_SHA256.csv"
ANALYSIS_SUMMARY = ANALYSIS / "PHASE4C_V2_ANALYSIS_INVENTORY_SUMMARY.json"
INVENTORY = BASE / "PHASE4C_V2_SCIENTIFIC_CHECKPOINT_SHA256.csv"
SUMMARY = BASE / "PHASE4C_V2_SCIENTIFIC_CHECKPOINT_SUMMARY.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def category(path: Path) -> str:
    if path == BASE / "PHASE4C_V2_SCIENTIFIC_ANALYSIS_FREEZE_MANIFEST.md":
        return "freeze_manifest"
    if path == Path(__file__).resolve():
        return "checkpoint_builder"
    if path in {ANALYSIS_INVENTORY, ANALYSIS_SUMMARY}:
        return "analysis_inventory"
    return "analysis_artifact"


def main() -> None:
    analysis_rows = list(csv.DictReader(ANALYSIS_INVENTORY.open(newline="")))
    artifacts = [ROOT / row["relative_path"] for row in analysis_rows]
    artifacts.extend(
        [
            ANALYSIS_INVENTORY,
            ANALYSIS_SUMMARY,
            BASE / "PHASE4C_V2_SCIENTIFIC_ANALYSIS_FREEZE_MANIFEST.md",
            Path(__file__).resolve(),
        ]
    )
    unique = sorted(set(artifacts))
    rows: list[tuple[str, int, str, str]] = []
    for path in unique:
        if not path.is_file():
            raise FileNotFoundError(path)
        rows.append(
            (
                path.relative_to(ROOT).as_posix(),
                path.stat().st_size,
                sha256(path),
                category(path),
            )
        )

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
    result = {
        "scope": "compact Phase 4C V2 scientific-analysis checkpoint; inventory and summary excluded from their own scope",
        "entry_count": len(rows),
        "total_bytes": sum(row[1] for row in rows),
        "inventory_sha256": sha256(INVENTORY),
        "scientific_checkpoint_tree_sha256": hashlib.sha256(tree_payload.encode()).hexdigest(),
        "analysis_inventory_sha256": sha256(ANALYSIS_INVENTORY),
        "analysis_artifact_count": len(analysis_rows),
        "scientific_figures": sum(Path(row["relative_path"]).suffix == ".png" for row in analysis_rows),
        "model_training_during_analysis": 0,
        "heavy_models_and_predictions_included": False,
    }
    temporary_summary = SUMMARY.with_suffix(".json.tmp")
    temporary_summary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    temporary_summary.replace(SUMMARY)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
