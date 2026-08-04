"""Validate configs/final_robustness_statistics.yaml."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "final_robustness_statistics.yaml",
    )
    ap.add_argument("--require-frozen", action="store_true")
    args = ap.parse_args()
    from timetrack.robustness_reporting import (
        load_stats_config,
        scientific_config_hash,
        validate_stats_config,
    )

    cfg = load_stats_config(args.config)
    errs = validate_stats_config(cfg, require_frozen=args.require_frozen)
    computed = scientific_config_hash(cfg)
    payload = {
        "ok": not errs,
        "errors": errs,
        "freeze_tag": cfg.get("freeze_tag"),
        "scientific_config_hash": computed,
        "frozen_scientific_config_hash": cfg.get("frozen_scientific_config_hash"),
        "hashes_match": computed == cfg.get("frozen_scientific_config_hash"),
    }
    print(json.dumps(payload, indent=2))
    raise SystemExit(0 if not errs else 1)


if __name__ == "__main__":
    main()
