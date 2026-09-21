#!/usr/bin/env python3
"""Materialize deterministic Phase 2A split and output-schema artifacts."""

from pathlib import Path

from benchmark.src.data import load_canonical_panel
from benchmark.src.splits import (
    joint_eligibility_comparison,
    joint_fold_boundary_table,
)
from benchmark.src.validation import prepare_output_schemas


def main() -> None:
    panel = load_canonical_panel()
    prepare_output_schemas(Path("benchmark/outputs"))
    boundaries = joint_fold_boundary_table(panel)
    comparison = joint_eligibility_comparison(panel)
    boundaries.to_csv("benchmark/outputs/joint_fold_boundaries.csv", index=False)
    comparison.to_csv(
        "benchmark/outputs/joint_eligibility_comparison.csv", index=False
    )
    if len(boundaries) != 35 or not boundaries["leakage_check"].all():
        raise RuntimeError("Joint fold artifact validation failed")
    print(
        {
            "joint_fold_rows": len(boundaries),
            "eligibility_comparison_rows": len(comparison),
            "joint_eligible_range": [
                int(boundaries["joint_eligible_n"].min()),
                int(boundaries["joint_eligible_n"].max()),
            ],
        }
    )


if __name__ == "__main__":
    main()
