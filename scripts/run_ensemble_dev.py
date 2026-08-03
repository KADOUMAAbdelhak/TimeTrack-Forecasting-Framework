"""Validation-only ensembles on frozen constituent forecasts (development).

Constituents: persistence, ridge, lightgbm (fixed defaults — not re-tuned here).
Weights from val only; outer test scored after weight freeze.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.runner import prepare_split_windows
from models import forecasting as F
from models.ensembles.strategies import ensemble_predict
from timetrack.data import build_analysis_panel, dataset_fingerprint
from timetrack.evaluation_stage import ExperimentStage
from timetrack.metrics import mae, mase
from timetrack.splits import fold_to_split_spec, make_outer_chronological_folds

TARGETS = ("cluster_mean_CU", "cluster_UM", "averageRttWithGoogleDns")
CONSTITUENTS = ("persistence", "ridge", "lightgbm")
METHODS = ("mean", "inverse_mae", "nonnegative", "stacking")
HORIZONS = (1, 8)
CONTEXT = 32
SEED = 0


def _flat(name: str) -> bool:
    return name in {"ridge", "lightgbm"}


def _fit_predict(panel, split, target, model_name, horizon):
    windows = prepare_split_windows(panel, split, target, horizon, CONTEXT, flat=_flat(model_name))
    model = F.build_model(model_name, horizon=horizon, context_length=CONTEXT, seed=SEED)
    t0 = time.perf_counter()
    model.fit(windows["train"].X, windows["train"].y, windows["val"].X, windows["val"].y)
    train_s = time.perf_counter() - t0
    pv = model.predict(windows["val"].X)
    pt = model.predict(windows["test"].X)
    yv, yt = windows["val"].y, windows["test"].y
    if np.asarray(yv).ndim > 1:
        yv, yt = np.asarray(yv)[:, 0], np.asarray(yt)[:, 0]
        pv = np.asarray(pv)[:, 0] if np.asarray(pv).ndim > 1 else pv
        pt = np.asarray(pt)[:, 0] if np.asarray(pt).ndim > 1 else pt
    return np.asarray(yv), np.asarray(pv), np.asarray(yt), np.asarray(pt), train_s


def main():
    panel = build_analysis_panel()
    fp = dataset_fingerprint()
    folds = make_outer_chronological_folds(panel, n_folds=3)
    rows = []
    for fold in folds:
        split = fold_to_split_spec(fold)
        for target in TARGETS:
            if target not in panel.columns:
                continue
            for horizon in HORIZONS:
                packs = {}
                train_s = 0.0
                for m in CONSTITUENTS:
                    yv, pv, yt, pt, ts = _fit_predict(panel, split, target, m, horizon)
                    packs[m] = (yv, pv, yt, pt)
                    train_s += ts
                # align lengths
                n_val = min(len(packs[m][0]) for m in CONSTITUENTS)
                n_test = min(len(packs[m][2]) for m in CONSTITUENTS)
                y_val = packs[CONSTITUENTS[0]][0][:n_val]
                y_test = packs[CONSTITUENTS[0]][2][:n_test]
                preds_val = [packs[m][1][:n_val] for m in CONSTITUENTS]
                preds_test = [packs[m][3][:n_test] for m in CONSTITUENTS]
                y_train = panel.loc[split.train_idx, target].to_numpy(dtype=float)

                # constituents
                for i, m in enumerate(CONSTITUENTS):
                    rows.append(
                        {
                            "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                            "eligible_for_final_claims": False,
                            "target": target,
                            "horizon": horizon,
                            "outer_fold": fold.fold_id,
                            "method": m,
                            "mae": mae(y_test, preds_test[i]),
                            "mase": mase(y_test, preds_test[i], y_train),
                            "beats_best_constituent": False,
                            "train_seconds": train_s,
                        }
                    )
                best_c = min(mae(y_test, p) for p in preds_test)
                for method in METHODS:
                    out = ensemble_predict(method, preds_test, y_val=y_val, preds_val=preds_val)
                    em = mae(y_test, out["pred"])
                    rows.append(
                        {
                            "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                            "eligible_for_final_claims": False,
                            "target": target,
                            "horizon": horizon,
                            "outer_fold": fold.fold_id,
                            "method": f"ens_{method}",
                            "mae": em,
                            "mase": mase(y_test, out["pred"], y_train),
                            "beats_best_constituent": bool(em < best_c - 1e-12),
                            "best_constituent_mae": best_c,
                            "weights": ";".join(f"{w:.4f}" for w in np.asarray(out["weights"]).ravel()),
                            "stacking_accepted": out.get("accepted", True),
                            "train_seconds": train_s,
                        }
                    )

    df = pd.DataFrame(rows)
    out = ROOT / "results" / "development" / "metrics"
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "ensemble_all_runs.csv", index=False)
    summary = (
        df.groupby(["target", "horizon", "method"], as_index=False)
        .agg(mae_mean=("mae", "mean"), mae_std=("mae", "std"), beat_rate=("beats_best_constituent", "mean"))
    )
    summary.to_csv(out / "ensemble_summary.csv", index=False)
    (out / "ensemble_all_runs.meta.json").write_text(
        json.dumps(
            {
                "experiment_stage": ExperimentStage.DEVELOPMENT.value,
                "eligible_for_final_claims": False,
                "dataset_fingerprint": fp["fingerprint"],
                "constituents": list(CONSTITUENTS),
                "n_rows": len(df),
            },
            indent=2,
        )
    )
    print(summary.to_string(index=False))
    print("wrote ensemble metrics", len(df))


if __name__ == "__main__":
    main()
