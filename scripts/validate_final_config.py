"""Validate configs/final_fgcs.yaml (and schema companions)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from timetrack.final_config import validate_final_config


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "final_fgcs.yaml")
    ap.add_argument(
        "--require-frozen",
        action="store_true",
        help="Reject PENDING freeze_commit/freeze_tag (post-freeze / final tier).",
    )
    args = ap.parse_args()
    cfg = yaml.safe_load(args.config.read_text()) or {}
    errs = validate_final_config(cfg, require_frozen=args.require_frozen)
    if errs:
        print("INVALID")
        for e in errs:
            print("-", e)
        sys.exit(1)
    pending = str(cfg.get("freeze_commit", "")).upper().startswith("PENDING")
    print("OK")
    if pending and not args.require_frozen:
        print("NOTE: freeze markers are PENDING (allowed for pre-freeze dry run).")


if __name__ == "__main__":
    main()
