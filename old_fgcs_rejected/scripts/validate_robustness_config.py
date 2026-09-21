"""Validate configs/final_robustness_extension.yaml."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "final_robustness_extension.yaml")
    ap.add_argument("--require-frozen", action="store_true")
    args = ap.parse_args()
    from timetrack.robustness_extension import load_robustness_config, validate_robustness_config

    cfg = load_robustness_config(args.config)
    errs = validate_robustness_config(cfg, require_frozen=args.require_frozen)
    print(json.dumps({"ok": not errs, "errors": errs, "freeze_tag": cfg.get("freeze_tag")}, indent=2))
    raise SystemExit(0 if not errs else 1)


if __name__ == "__main__":
    main()
