"""Manually launch a single final experiment pack (resumable)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    ap = argparse.ArgumentParser(description="Run one FGCS final pack (manual launch only).")
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "final_fgcs_packs.yaml")
    ap.add_argument("--pack", required=True, help="Pack ID from configs/final_fgcs_packs.yaml")
    ap.add_argument("--resume", action="store_true", default=True)
    ap.add_argument("--no-resume", action="store_true", help="Ignore prior RUN_STATUS and restart bookkeeping")
    args = ap.parse_args()
    resume = not args.no_resume
    from experiments.pack_runner import run_pack

    manifest = run_pack(args.pack, args.config, resume=resume)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
