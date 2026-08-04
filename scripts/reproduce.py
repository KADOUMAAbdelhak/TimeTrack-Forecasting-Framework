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
    from experiments.final_hierarchy_runner import load_final_config, run_smoke
    from timetrack.final_config import validate_final_config

    cfg = load_final_config(config)
    errs = validate_final_config(cfg, require_frozen=False)
    if errs:
        raise SystemExit("Config invalid:\n" + "\n".join(errs))
    from timetrack.data import dataset_fingerprint
    from timetrack.splits import make_outer_chronological_folds
    from timetrack.data import build_analysis_panel

    fp = dataset_fingerprint()
    print("dataset_fingerprint", fp["fingerprint"])
    panel = build_analysis_panel()
    folds = make_outer_chronological_folds(panel, n_folds=int(cfg["folds"]["n_outer"]))
    print("n_outer_folds", len(folds), "n_rows", len(panel))
    manifest = run_smoke(cfg, resume=resume)
    print(json.dumps(manifest, indent=2))


def tier_final(config: Path, resume: bool) -> None:
    from timetrack.final_config import validate_final_config

    cfg = yaml.safe_load(config.read_text())
    errs = validate_final_config(cfg, require_frozen=True)
    if errs:
        raise SystemExit(
            "Final tier requires a frozen config:\n"
            + "\n".join(errs)
            + "\nComplete freeze procedure before --tier final."
        )
    # Placeholder: full grid runner invoked after freeze
    from experiments.final_hierarchy_runner import run_smoke

    print("Freeze validated. Launching final hierarchy grid (resume=", resume, ")")
    # Full final execution will expand beyond smoke; for now require explicit plan approval
    # via configs and run progressive hierarchy jobs.
    raise SystemExit(
        "Final grid launcher is gated until experiment-freeze-v1 exists. "
        "Pre-freeze checkpoint: use --tier smoke. "
        "After freeze, re-run this command; the freeze commit fills freeze_commit/tag."
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
