#!/usr/bin/env python3
"""Run frozen final statistical analysis on experiment-freeze-v2 predictions.

Never trains models. Never modifies source prediction NPZs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml

from timetrack.statistical_reporting import (
    load_statistics_config,
    run_final_statistics,
    validate_statistics_config,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "final_statistics.yaml")
    ap.add_argument("--source-config", type=Path, default=ROOT / "configs" / "final_fgcs_packs.yaml")
    ap.add_argument("--output", type=Path, default=ROOT / "results" / "final" / "packs" / "06_supporting_statistics")
    ap.add_argument("--smoke", action="store_true", help="Synthetic smoke mode (tests only)")
    ap.add_argument("--smoke-pred-root", type=Path, default=None)
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    stats_cfg = load_statistics_config(args.config)
    errs = validate_statistics_config(stats_cfg)
    if errs:
        raise SystemExit("invalid final_statistics.yaml:\n- " + "\n- ".join(errs))
    if args.validate_only:
        print("OK", args.config)
        return

    source_cfg = yaml.safe_load(args.source_config.read_text())
    result = run_final_statistics(
        stats_cfg=stats_cfg,
        source_cfg=source_cfg,
        output_dir=args.output,
        smoke=args.smoke,
        smoke_pred_root=args.smoke_pred_root,
    )
    print(
        f"complete comparisons={result['n_comparisons']} "
        f"wall_s={result['wall_seconds']:.2f} "
        f"hashes_unchanged={result['source_hashes_unchanged']}"
    )
    print(result["claims"].to_string(index=False))


if __name__ == "__main__":
    main()
