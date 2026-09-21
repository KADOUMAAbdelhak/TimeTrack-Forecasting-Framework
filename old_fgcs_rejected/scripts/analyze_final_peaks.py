#!/usr/bin/env python3
"""Run frozen peak analysis on experiment-freeze-v2 predictions (no training)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml

from timetrack.peak_reporting import load_peak_config, run_final_peak_analysis, validate_peak_config


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "final_peak_analysis.yaml")
    ap.add_argument("--source-config", type=Path, default=ROOT / "configs" / "final_fgcs_packs.yaml")
    ap.add_argument("--output", type=Path, default=ROOT / "results" / "final" / "packs" / "07_peak_analysis")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--smoke-pred-root", type=Path, default=None)
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    cfg = load_peak_config(args.config)
    errs = validate_peak_config(cfg)
    if errs:
        raise SystemExit("invalid final_peak_analysis.yaml:\n- " + "\n- ".join(errs))
    if args.validate_only:
        print("OK", args.config)
        return

    source_cfg = yaml.safe_load(args.source_config.read_text())
    result = run_final_peak_analysis(
        peak_cfg=cfg,
        source_cfg=source_cfg,
        output_dir=args.output,
        smoke=args.smoke,
        smoke_pred_root=args.smoke_pred_root,
    )
    print(
        f"complete rows={result['n_rows']} wall_s={result['wall_seconds']:.2f} "
        f"recon_max_abs_diff={result['reconstruction_max_abs_top_mae_diff']:.3g} "
        f"hashes_unchanged={result['source_hashes_unchanged']}"
    )
    print(result["claims"].to_string(index=False))


if __name__ == "__main__":
    main()
