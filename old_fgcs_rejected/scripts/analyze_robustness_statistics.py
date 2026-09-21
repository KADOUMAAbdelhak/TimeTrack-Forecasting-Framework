"""Frozen multi-seed robustness statistics (no model training)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "final_robustness_statistics.yaml")
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--require-frozen", action="store_true")
    args = ap.parse_args()
    from timetrack.robustness_reporting import (
        load_stats_config,
        run_robustness_statistics,
        validate_stats_config,
    )

    cfg = load_stats_config(args.config)
    errs = validate_stats_config(cfg, require_frozen=args.require_frozen)
    if errs:
        raise SystemExit(f"config invalid: {errs}")
    manifest = run_robustness_statistics(
        cfg,
        output_dir=args.output,
        smoke=args.smoke,
        require_frozen=args.require_frozen,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
