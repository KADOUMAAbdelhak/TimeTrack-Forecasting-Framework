#!/usr/bin/env python3
"""Build the compact Phase 4D Materna scientific-analysis inventory."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / "outputs/scientific_v1"
INVENTORY = BASE / "PHASE4D_MATERNA_SCIENTIFIC_ANALYSIS_ARTIFACT_SHA256.csv"
SUMMARY = BASE / "PHASE4D_MATERNA_SCIENTIFIC_ANALYSIS_INVENTORY_SUMMARY.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifacts() -> dict[str, list[Path]]:
    return {
        "provenance": [BASE / "PHASE4D_MATERNA_SCIENTIFIC_ANALYSIS_PROVENANCE.md"],
        "report": [BASE / "PHASE4D_MATERNA_SCIENTIFIC_REPORT.md"],
        "analysis_code": [
            BASE / "analyze_phase4d_materna_scientific.py",
            BASE / "validate_phase4d_scientific_analysis.py",
            BASE / "build_phase4d_analysis_inventory.py",
        ],
        "validation": [BASE / "PHASE4D_MATERNA_SCIENTIFIC_ANALYSIS_VALIDATION.json"],
        "analysis_table": sorted((OUT / "analysis").glob("*")),
        "comparison_table": sorted((OUT / "comparisons").glob("*")),
        "synthesis_table": sorted((OUT / "synthesis").glob("*")),
        "figure": sorted((OUT / "figures").glob("*.png")),
    }


def main() -> None:
    rows = []
    for category, paths in artifacts().items():
        for path in paths:
            if not path.is_file():
                raise FileNotFoundError(path)
            rows.append((path.relative_to(ROOT).as_posix(), path.stat().st_size, sha256_file(path), category))
    rows.sort(key=lambda row: row[0])
    temporary = INVENTORY.with_suffix(".csv.tmp")
    with temporary.open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["relative_path", "byte_size", "sha256", "category"])
        writer.writerows(rows)
    temporary.replace(INVENTORY)
    payload = "".join(f"{path},{size},{digest}\n" for path, size, digest, _ in rows)
    summary = {
        "scope": "Phase 4D scientific-analysis provenance, code, validation, report, tables, synthesis, and figures; inventory and summary excluded from their own scope",
        "file_count": len(rows),
        "total_bytes": sum(row[1] for row in rows),
        "inventory_sha256": sha256_file(INVENTORY),
        "analysis_tree_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "figure_count": sum(row[3] == "figure" for row in rows),
        "model_training_during_analysis": 0,
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
