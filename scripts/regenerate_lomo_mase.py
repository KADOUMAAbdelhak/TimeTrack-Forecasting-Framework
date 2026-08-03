"""Regenerate LOMO MASE fields without retraining.

Uses stored MAE + outer-train naive scales (held-out machine, per fold).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from timetrack.data import build_analysis_panel
from timetrack.metrics import naive_scale, nanmean_valid
from timetrack.splits import fold_to_split_spec, make_outer_chronological_folds

MACHINES = [f"machine0{i}" for i in range(1, 8)]


def main():
    panel = build_analysis_panel()
    folds = {f.fold_id: fold_to_split_spec(f) for f in make_outer_chronological_folds(panel, n_folds=3)}
    path = ROOT / "results" / "development" / "metrics" / "lomo_all_runs.csv"
    df = pd.read_csv(path)

    scales = {}
    for fold_id, split in folds.items():
        for fam, suffix in ("CU", "_CU"), ("UM", "_UM"):
            for m in MACHINES:
                col = f"{m}{suffix}"
                y = panel.loc[split.train_idx, col].to_numpy(dtype=float)
                scales[(fold_id, fam, m)] = naive_scale(y)

    mases, valid, reasons, nmae, rmsse_approx = [], [], [], [], []
    for _, r in df.iterrows():
        info = scales[(r["outer_fold"], r["family"], r["held_out_machine"])]
        mae = float(r["mae"])
        if info["valid"] and np.isfinite(mae):
            m = mae / info["scale"]
            mases.append(m)
            valid.append(True)
            reasons.append("")
            # RMSSE unavailable without residuals; leave nan
            rmsse_approx.append(np.nan)
        else:
            mases.append(np.nan)
            valid.append(False)
            reasons.append(info["reason"] or "undefined")
            rmsse_approx.append(np.nan)
        # train-range nMAE
        split = folds[r["outer_fold"]]
        col = f"{r['held_out_machine']}_{'CU' if r['family']=='CU' else 'UM'}"
        yt = panel.loc[split.train_idx, col].to_numpy(dtype=float)
        yt = yt[np.isfinite(yt)]
        rng = float(np.max(yt) - np.min(yt)) if len(yt) else np.nan
        nmae.append(mae / rng if np.isfinite(mae) and np.isfinite(rng) and rng > 0 else np.nan)

    df["mase"] = mases
    df["mase_valid"] = valid
    df["mase_invalid_reason"] = reasons
    df["nmae_train_range"] = nmae
    df["mase_scale"] = [
        scales[(r["outer_fold"], r["family"], r["held_out_machine"])]["scale"] for _, r in df.iterrows()
    ]
    df.to_csv(path, index=False)

    # summaries: never average invalid MASE
    rows = []
    for keys, g in df.groupby(["family", "method", "horizon"]):
        rows.append(
            {
                "family": keys[0],
                "method": keys[1],
                "horizon": keys[2],
                "mae_macro": float(g["mae"].mean()),
                "mae_std": float(g["mae"].std()),
                "mae_worst_machine": float(g["mae"].max()),
                "mase_macro": nanmean_valid(g["mase"].to_numpy(), g["mase_valid"].to_numpy()),
                "mase_n_valid": int(g["mase_valid"].sum()),
                "mase_n_invalid": int((~g["mase_valid"]).sum()),
                "nmae_train_range_macro": float(np.nanmean(g["nmae_train_range"])),
                "n": len(g),
            }
        )
    summary = pd.DataFrame(rows)
    summary.to_csv(ROOT / "results" / "development" / "metrics" / "lomo_summary.csv", index=False)

    per_m = (
        df.groupby(["family", "held_out_machine", "method", "horizon"], as_index=False)
        .agg(
            mae=("mae", "mean"),
            mase=("mase", "mean"),  # per cell usually single fold-agg; use nanmean via apply
            mase_valid=("mase_valid", "all"),
            nmae_train_range=("nmae_train_range", "mean"),
        )
    )
    # fix mase mean with validity
    fixed = []
    for _, r in per_m.iterrows():
        sub = df[
            (df.family == r.family)
            & (df.held_out_machine == r.held_out_machine)
            & (df.method == r.method)
            & (df.horizon == r.horizon)
        ]
        r = r.copy()
        r["mase"] = nanmean_valid(sub["mase"].to_numpy(), sub["mase_valid"].to_numpy())
        fixed.append(r)
    pd.DataFrame(fixed).to_csv(ROOT / "results" / "development" / "tables" / "lomo_per_machine.csv", index=False)

    cal = df[df["method"].str.startswith("global_residual_cal")].copy()
    cal_curve = []
    for keys, g in cal.groupby(["family", "horizon", "calibration_n"]):
        cal_curve.append(
            {
                "family": keys[0],
                "horizon": keys[1],
                "calibration_n": keys[2],
                "mae_macro": float(g["mae"].mean()),
                "mae_worst": float(g["mae"].max()),
                "mase_macro": nanmean_valid(g["mase"].to_numpy(), g["mase_valid"].to_numpy()),
                "nmae_train_range_macro": float(np.nanmean(g["nmae_train_range"])),
            }
        )
    pd.DataFrame(cal_curve).to_csv(
        ROOT / "results" / "development" / "tables" / "lomo_calibration_curve.csv", index=False
    )

    meta_path = ROOT / "results" / "development" / "metrics" / "lomo_all_runs.meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta["mase_policy"] = "finite_lag1_pairs_on_outer_train; invalid excluded from averages"
    meta["mase_regenerated"] = True
    meta_path.write_text(json.dumps(meta, indent=2))
    print(summary[summary.family == "CU"][["method", "horizon", "mase_macro", "mase_n_valid", "nmae_train_range_macro"]].head(20))
    print("regenerated LOMO MASE fields", path)


if __name__ == "__main__":
    main()
