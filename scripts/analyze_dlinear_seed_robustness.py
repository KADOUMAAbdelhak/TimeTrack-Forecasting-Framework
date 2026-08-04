"""Analysis-only post-processor for DLinear seed robustness artifacts."""

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
    args = ap.parse_args()
    from experiments.dlinear_seed_analysis import analyze_dlinear_seed_robustness
    from timetrack.final_packs import pack_by_id, pack_output_dir
    from timetrack.robustness_extension import load_robustness_config, scientific_config_hash

    cfg = load_robustness_config(args.config)
    pack = pack_by_id(cfg, "dlinear_seed_robustness")
    out = pack_output_dir(cfg, pack)
    if not (out / "COMPLETE").exists():
        raise SystemExit(f"pack not complete: {out}")
    summary = analyze_dlinear_seed_robustness(cfg, pack, out)
    summary["scientific_config_hash"] = scientific_config_hash(cfg)
    (out / "metrics" / "ANALYSIS_SUMMARY.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
