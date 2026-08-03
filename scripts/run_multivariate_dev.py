"""Multivariate input ablation (development stage).

Fixed model/fold/horizon/context comparisons for required metric pairs.
Separates extra inputs vs capacity via parameter-matched Ridge controls where practical.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.runner import prepare_split_windows
from models import forecasting as F
from timetrack.data import build_analysis_panel, dataset_fingerprint
from timetrack.evaluation_stage import ExperimentStage
from timetrack.metrics import mae, mase
from timetrack.splits import fold_to_split_spec, make_outer_chronological_folds

# target, exog list (empty = univariate history only)
PAIRS = [
    ("cluster_mean_CU", []),
    ("cluster_mean_CU", ["cluster_UM"]),
    ("cluster_UM", []),
    ("cluster_UM", ["cluster_mean_CU"]),
    ("machine01_tx_bond0", []),
    ("machine01_tx_bond0", ["machine01_rx_bond0"]),
    ("machine01_rx_bond0", []),
    ("machine01_rx_bond0", ["machine01_tx_bond0"]),
    ("averageRttWithGoogleDns", []),
    ("averageRttWithGoogleDns", ["minRttWithGoogleDns", "maxRttWithGoogleDns"]),
    ("jitterWithGoogleDns", []),
    ("jitterWithGoogleDns", ["averageRttWithGoogleDns", "minRttWithGoogleDns", "maxRttWithGoogleDns"]),
]

MODELS = ("ridge", "lightgbm", "lstm", "dlinear")
HORIZONS = (1, 8)
CONTEXT = 32
SEED = 0


def _flat(name: str) -> bool:
    return name in {"ridge", "lightgbm", "xgboost", "catboost", "random_forest", "extra_trees"}


def _run_one(panel, split, target, exog, model_name, horizon):
    kwargs = {}
    if model_name in {"lstm", "dlinear"}:
        kwargs["epochs"] = 12
    windows = prepare_split_windows(
        panel, split, target, horizon, CONTEXT, exog=exog or None, flat=_flat(model_name)
    )
    # parameter-matched ridge control: univariate with padded zeros to match multivariate dim
    model = F.build_model(model_name, horizon=horizon, context_length=CONTEXT, seed=SEED, **kwargs)
    t0 = time.perf_counter()
    model.fit(windows["train"].X, windows["train"].y, windows["val"].X, windows["val"].y)
    train_s = time.perf_counter() - t0
    pred = model.predict(windows["test"].X)
    y = windows["test"].y
    if np.asarray(y).ndim > 1:
        y = np.asarray(y)[:, 0]
        pred = np.asarray(pred)[:, 0] if np.asarray(pred).ndim > 1 else pred
    y_train = panel.loc[split.train_idx, target].to_numpy(dtype=float)
    n_params = model.metadata.n_parameters
    return {
        "target": target,
        "exog": ",".join(exog) if exog else "",
        "n_exog": len(exog),
        "multivariate": bool(exog),
        "model": model_name,
        "horizon": horizon,
        "mae": mae(y, pred),
        "mase": mase(y, pred, y_train),
        "n_parameters": n_params,
        "train_seconds": train_s,
        "n_test": len(y),
    }


def main():
    panel = build_analysis_panel()
    # Ensure RTT columns exist
    for c in ("averageRttWithGoogleDns", "minRttWithGoogleDns", "maxRttWithGoogleDns", "jitterWithGoogleDns"):
        if c not in panel.columns:
            # try case variants from network merge
            matches = [x for x in panel.columns if x.lower() == c.lower()]
            if matches:
                panel[c] = panel[matches[0]]
    fp = dataset_fingerprint()
    folds = make_outer_chronological_folds(panel, n_folds=3)
    rows = []
    for fold in folds:
        split = fold_to_split_spec(fold)
        for target, exog in PAIRS:
            missing = [e for e in [target, *exog] if e not in panel.columns]
            if missing:
                print("skip missing", missing, flush=True)
                continue
            for model in MODELS:
                for horizon in HORIZONS:
                    print(f"{fold.fold_id} {target} exog={exog} {model} h={horizon}", flush=True)
                    try:
                        r = _run_one(panel, split, target, exog, model, horizon)
                        r.update(
                            {
                                "outer_fold": fold.fold_id,
                                "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                                "eligible_for_final_claims": False,
                            }
                        )
                        rows.append(r)
                    except Exception as e:
                        print("FAIL", e, flush=True)

    df = pd.DataFrame(rows)
    out_dir = ROOT / "results" / "development" / "tables"
    fig_dir = ROOT / "results" / "development" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "univariate_vs_multivariate.csv", index=False)

    # Gain vs rough correlation of target with first exog (development diagnostic only)
    gains = []
    for (target, model, horizon), g in df.groupby(["target", "model", "horizon"]):
        uni = g[g["multivariate"] == False]
        multi = g[g["multivariate"] == True]
        if uni.empty or multi.empty:
            continue
        gain = float(uni["mae"].mean() - multi["mae"].mean())
        exog = multi.iloc[0]["exog"].split(",")[0] if multi.iloc[0]["exog"] else ""
        corr = float(panel[[target, exog]].corr().iloc[0, 1]) if exog in panel.columns else np.nan
        gains.append({"target": target, "model": model, "horizon": horizon, "mae_gain": gain, "corr": corr})
    gdf = pd.DataFrame(gains)
    if not gdf.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(gdf["corr"], gdf["mae_gain"], alpha=0.7)
        ax.axhline(0, color="gray", lw=0.8)
        ax.set_xlabel("|corr| proxy (signed corr with first exog)")
        ax.set_ylabel("MAE gain (uni - multi), >0 means multi better")
        ax.set_title("Multivariate gain vs correlation (dev; not causal)")
        fig.tight_layout()
        fig.savefig(fig_dir / "multivariate_gain_by_correlation.pdf")
        fig.savefig(fig_dir / "multivariate_gain_by_correlation.png", dpi=120)
        plt.close(fig)

    meta = {
        "experiment_stage": ExperimentStage.DEVELOPMENT.value,
        "eligible_for_final_claims": False,
        "dataset_fingerprint": fp["fingerprint"],
        "n_rows": len(df),
        "note": "Do not claim causality from correlation vs gain scatter.",
    }
    (out_dir / "univariate_vs_multivariate.meta.json").write_text(json.dumps(meta, indent=2))
    print(df.groupby(["target", "multivariate", "model"])["mae"].mean().head(20))


if __name__ == "__main__":
    main()
