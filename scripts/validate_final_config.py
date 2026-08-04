"""Validate final FGCS configs (monolithic optional or pack-based default)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from timetrack.final_config import freeze_metadata, validate_final_config


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "final_fgcs_packs.yaml")
    ap.add_argument(
        "--require-frozen",
        action="store_true",
        help="Reject PENDING freeze markers and require resolvable freeze tag.",
    )
    args = ap.parse_args()
    cfg = yaml.safe_load(args.config.read_text()) or {}
    # Pointer configs redirect to packs
    if cfg.get("redirect"):
        redirected = ROOT / cfg["redirect"]
        cfg = yaml.safe_load(redirected.read_text()) or {}
        print(f"NOTE: redirected to {cfg.get('execution_mode', redirected)}")
    errs = validate_final_config(cfg, require_frozen=args.require_frozen)
    if errs:
        print("INVALID")
        for e in errs:
            print("-", e)
        sys.exit(1)
    print("OK")
    meta = freeze_metadata(cfg)
    pending = str(cfg.get("freeze_commit", "")).upper().startswith("PENDING")
    if pending and not args.require_frozen:
        print("NOTE: freeze markers are PENDING (allowed for pre-freeze dry run).")
    if args.require_frozen:
        print("freeze_metadata:")
        for k, v in meta.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
