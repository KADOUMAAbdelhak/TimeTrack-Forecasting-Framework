"""Clean-environment / staged reproduction entrypoint."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))


def tier_smoke(config: Path, resume: bool) -> None:
    """Pack-based smoke: list packs + run shared_tuning only (no auto-queue)."""
    from timetrack.final_packs import list_pack_rows, load_packs_config
    from experiments.pack_runner import run_pack

    packs_cfg = ROOT / "configs" / "final_fgcs_packs.yaml"
    cfg = load_packs_config(packs_cfg)
    print("packs:")
    for r in list_pack_rows(cfg):
        print(f"  {r['pack_id']}: {r['status']} (required={r['required']})")
    from timetrack.data import dataset_fingerprint

    print("dataset_fingerprint", dataset_fingerprint()["fingerprint"])
    manifest = run_pack("shared_tuning", packs_cfg, resume=resume)
    print(json.dumps(manifest, indent=2))


def tier_final(config: Path, resume: bool) -> None:
    raise SystemExit(
        "Do not auto-run all final packs.\n"
        "After freeze, launch ONE pack at a time:\n"
        "  python scripts/list_final_packs.py --config configs/final_fgcs_packs.yaml\n"
        "  python scripts/run_final_pack.py --config configs/final_fgcs_packs.yaml "
        "--pack <pack_id> --resume\n"
        "Do not execute configs/final_fgcs_full.yaml or publication.yaml for claims."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="TimeTrack reproduction runner")
    ap.add_argument("--tier", choices=["smoke", "final"], required=True)
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "final_fgcs.yaml")
    ap.add_argument("--resume", action="store_true", default=True)
    ap.add_argument("--no-resume", action="store_true")
    args = ap.parse_args()
    resume = not args.no_resume
    if args.tier == "smoke":
        # Ensure tests pass as part of smoke contract when asked via clean env script;
        # reproduce.py smoke focuses on experiment path.
        tier_smoke(args.config, resume=resume)
    else:
        tier_final(args.config, resume=resume)


if __name__ == "__main__":
    main()
