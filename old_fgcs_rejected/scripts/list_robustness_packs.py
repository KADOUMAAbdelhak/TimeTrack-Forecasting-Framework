"""List robustness-extension pack statuses."""

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
    from timetrack.final_packs import pack_output_dir, read_pack_status
    from timetrack.robustness_extension import load_robustness_config

    cfg = load_robustness_config(args.config)
    rows = []
    for pack in cfg.get("packs") or []:
        out = pack_output_dir(cfg, pack)
        status = read_pack_status(cfg, pack)
        deps = list(pack.get("dependencies") or [])
        dep_ok = True
        for d in deps:
            dep = next(p for p in cfg["packs"] if p["id"] == d)
            if read_pack_status(cfg, dep) != "complete":
                dep_ok = False
                break
        if status == "pending" and deps and not dep_ok:
            status = "blocked"
        rows.append(
            {
                "pack_id": pack["id"],
                "status": status,
                "dependencies": deps,
                "dependencies_satisfied": dep_ok,
                "seeds": pack.get("seeds"),
                "hierarchies": pack.get("hierarchies"),
                "estimated_base_fits": pack.get("estimated_base_fits"),
                "output_dir": str(out),
                "reuse_seed0_from": pack.get("reuse_seed0_from"),
            }
        )
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
