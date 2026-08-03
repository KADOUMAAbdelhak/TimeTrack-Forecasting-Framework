"""Paired bootstrap comparison of absolute errors for selected run pairs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def paired_bootstrap_mae_diff(y, a, b, n_boot: int = 2000, seed: int = 0):
    rng = np.random.default_rng(seed)
    ea = np.abs(y - a)
    eb = np.abs(y - b)
    n = len(y)
    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        diffs.append(ea[idx].mean() - eb[idx].mean())
    diffs = np.asarray(diffs)
    return {
        "mae_a": float(ea.mean()),
        "mae_b": float(eb.mean()),
        "diff_mae_a_minus_b": float(ea.mean() - eb.mean()),
        "ci95": [float(np.quantile(diffs, 0.025)), float(np.quantile(diffs, 0.975))],
        "p_two_sided_bootstrap": float(2 * min((diffs <= 0).mean(), (diffs >= 0).mean())),
        "n": int(n),
        "n_boot": n_boot,
    }


def load_pred(run_id: str) -> pd.DataFrame:
    path = ROOT / "results" / "predictions" / f"{run_id}.csv"
    return pd.read_csv(path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-a", required=True, help="run_id A")
    p.add_argument("--run-b", required=True, help="run_id B")
    p.add_argument("--n-boot", type=int, default=2000)
    args = p.parse_args()
    da = load_pred(args.run_a)
    db = load_pred(args.run_b)
    if "y_true" in da.columns:
        y, a, b = da["y_true"].values, da["y_pred"].values, db["y_pred"].values
    else:
        # multi-horizon: flatten matching columns
        yt = [c for c in da.columns if c.startswith("y_true")]
        yp = [c for c in da.columns if c.startswith("y_pred")]
        y = da[yt].values.reshape(-1)
        a = da[yp].values.reshape(-1)
        b = db[yp].values.reshape(-1)
    out = paired_bootstrap_mae_diff(y, a, b, n_boot=args.n_boot)
    out["run_a"] = args.run_a
    out["run_b"] = args.run_b
    out_dir = ROOT / "results" / "metrics" / "statistical_tests"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"bootstrap__{args.run_a}__vs__{args.run_b}.json"
    path.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
