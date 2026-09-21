#!/usr/bin/env python3
"""Copy lightweight frozen aggregate assets into fgcs/ (no NPZ/models)."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FGCS = Path(__file__).resolve().parents[1]
AGG = ROOT / "results" / "final" / "aggregate"


def main() -> None:
    (FGCS / "figs").mkdir(exist_ok=True)
    (FGCS / "results" / "main").mkdir(parents=True, exist_ok=True)
    (FGCS / "results" / "provenance").mkdir(parents=True, exist_ok=True)

    fig_map = {
        "cpu_accuracy_vs_horizon.pdf": "cpu_accuracy_vs_horizon.pdf",
        "cpu_reconciliation_effect_by_seed.pdf": "cpu_reconciliation_effect_by_seed.pdf",
        "cpu_coherence_before_after.pdf": "coherence_before_after.pdf",
        "memory_accuracy_vs_horizon.pdf": "memory_accuracy_vs_horizon.pdf",
        "memory_reconciliation_vs_ewma.pdf": "memory_reconciliation_vs_ewma.pdf",
        "disk_boundary.pdf": "disk_boundary.pdf",
        "bootstrap_relative_effects.pdf": "bootstrap_relative_effects.pdf",
        "top_bottom_tradeoff.pdf": "top_bottom_tradeoff.pdf",
        "cpu_peak_results.pdf": "cpu_peak_results.pdf",
        "dlinear_memory_peak_bias_by_seed.pdf": "dlinear_memory_peak_bias_by_seed.pdf",
        "method_selection_map.pdf": "method_selection_map.pdf",
    }
    for src_name, dst_name in fig_map.items():
        src = AGG / "figures" / src_name
        if not src.exists():
            raise FileNotFoundError(src)
        shutil.copy2(src, FGCS / "figs" / dst_name)

    for name in sorted((AGG / "tables").glob("*.csv")):
        shutil.copy2(name, FGCS / "results" / "main" / name.name)

    for name in [
        "SOURCE_ARTIFACT_HASHES.csv",
        "MANIFEST.json",
        "SAFE_CLAIMS_V2.md",
        "UNSUPPORTED_CLAIMS_V2.md",
        "FINAL_EVIDENCE_SUMMARY_V2.md",
    ]:
        src = AGG / name
        if src.exists():
            shutil.copy2(src, FGCS / "results" / "provenance" / name)

    print("prepare_manuscript_assets: OK")


if __name__ == "__main__":
    main()
