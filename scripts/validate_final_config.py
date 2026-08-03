"""Validate a final/publication config without executing publication.yaml."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REQUIRED_TOP = {
    "experiment_stage",
    "targets",
    "horizons",
    "models",
    "seeds",
    "context_length",
}


def validate(cfg: dict) -> list[str]:
    errs = []
    for k in REQUIRED_TOP:
        if k not in cfg:
            errs.append(f"missing key: {k}")
    if cfg.get("experiment_stage") == "final" and cfg.get("eligible_for_final_claims") is not True:
        errs.append("final stage requires eligible_for_final_claims: true only after freeze")
    if cfg.get("experiment_stage") == "publication" and not cfg.get("frozen_config_hash"):
        errs.append("publication stage requires frozen_config_hash")
    if "horizons" in cfg and any(h < 1 for h in cfg["horizons"]):
        errs.append("horizons must be >= 1")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    args = ap.parse_args()
    cfg = yaml.safe_load(args.config.read_text())
    errs = validate(cfg or {})
    if errs:
        print("INVALID")
        for e in errs:
            print("-", e)
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
