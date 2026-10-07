#!/usr/bin/env python3
"""Build the Phase 4C V2 scientific-analysis artifact inventory."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / "outputs/scientific_v2"
ANALYSIS = OUT / "analysis"
INVENTORY = ANALYSIS / "PHASE4C_V2_ANALYSIS_ARTIFACT_SHA256.csv"
SUMMARY = ANALYSIS / "PHASE4C_V2_ANALYSIS_INVENTORY_SUMMARY.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def category(path: Path) -> str:
    if path.suffix == ".png":
        return "figure"
    if "comparisons" in path.parts:
        return "comparison"
    if "synthesis" in path.parts:
        return "synthesis"
    if path.name.endswith("VALIDATION.json"):
        return "validation"
    if "PROVENANCE" in path.name:
        return "provenance"
    if "REPORT" in path.name:
        return "report"
    if path.suffix == ".py":
        return "analysis_source"
    return "analysis_table"


def main() -> None:
    artifacts = [
        BASE / "PHASE4C_V2_SCIENTIFIC_ANALYSIS_PROVENANCE.md",
        BASE / "PHASE4C_V2_EXTERNAL_CONFIRMATION_REPORT.md",
        BASE / "analyze_phase4c_v2_scientific.py",
        BASE / "validate_phase4c_v2_analysis.py",
        BASE / "build_phase4c_v2_analysis_inventory.py",
    ]
    artifacts.extend(sorted((OUT / "comparisons").glob("*.csv")))
    artifacts.extend(sorted((OUT / "synthesis").glob("*.csv")))
    artifacts.extend(sorted(path for path in ANALYSIS.iterdir() if path.is_file() and path not in {INVENTORY, SUMMARY}))
    artifacts.extend(sorted((OUT / "figures").glob("*.png")))
    unique = sorted(set(artifacts))
    rows = []
    for path in unique:
        if not path.is_file():
            raise FileNotFoundError(path)
        rows.append((path.relative_to(ROOT).as_posix(), path.stat().st_size, sha256(path), category(path)))
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    temporary = INVENTORY.with_suffix(".csv.tmp")
    with temporary.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["relative_path", "byte_size", "sha256", "category"])
        writer.writerows(rows)
    temporary.replace(INVENTORY)
    tree_payload = "".join(f"{path},{size},{digest}\n" for path, size, digest, _ in rows)
    result = {
        "scope": "Phase 4C V2 analysis tables, figures, report, provenance, validation, and source; inventory and summary excluded from their own scope",
        "file_count": len(rows),
        "total_bytes": sum(row[1] for row in rows),
        "inventory_sha256": sha256(INVENTORY),
        "analysis_tree_sha256": hashlib.sha256(tree_payload.encode()).hexdigest(),
        "figure_count": sum(row[3] == "figure" for row in rows),
        "model_training_during_analysis": 0,
    }
    temporary_summary = SUMMARY.with_suffix(".json.tmp")
    temporary_summary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    temporary_summary.replace(SUMMARY)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
