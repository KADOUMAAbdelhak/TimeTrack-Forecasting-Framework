"""List final experiment packs and their status."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from timetrack.final_packs import list_pack_rows, load_packs_config


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "final_fgcs_packs.yaml")
    args = ap.parse_args()
    cfg = load_packs_config(args.config)
    rows = list_pack_rows(cfg)
    print(f"{'PACK':<24} {'REQUIRED':<9} {'ESTIMATE':<10} {'STATUS':<10} {'REMAINING':<10} OUTPUT")
    for r in rows:
        req = "yes" if r["required"] else "no"
        est = f"{r['estimated_minutes']} min" if r["estimated_minutes"] is not None else "?"
        rem = "-" if r["remaining_runs"] is None else str(r["remaining_runs"])
        print(
            f"{r['pack_id']:<24} {req:<9} {est:<10} {r['status']:<10} {rem:<10} {r['output_path']}"
        )


if __name__ == "__main__":
    main()
