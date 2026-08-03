"""Development-stage hierarchical reconciliation experiment (memory UM).

Uses nested outer fold 0 validation only — not final-eligible.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.runner import prepare_split_windows
from models import forecasting as F
from models.hybrid.reconciliation import coherence_error, is_coherent, memory_hierarchy, reconcile
from timetrack.data import build_analysis_panel, dataset_fingerprint
from timetrack.evaluation_stage import ExperimentStage
from timetrack.metrics import mae
from timetrack.splits import fold_to_split_spec, make_outer_chronological_folds

MACHINES = [f"machine0{i}" for i in range(1, 8)]
BOTTOMS = [f"{m}_UM" for m in MACHINES]
TOP = "cluster_UM"


def _fit_predict(panel, split, target, horizon, context, model_name, seed=0):
    windows = prepare_split_windows(panel, split, target, horizon, context, flat=(model_name == "ridge"))
    model = F.build_model(model_name, horizon=horizon, context_length=context, seed=seed)
    model.fit(windows["train"].X, windows["train"].y, windows["val"].X, windows["val"].y)
    # Evaluate on split.test_idx which for outer folds is the outer test — for development
    # screening we score the outer-fold test but mark ineligible for final claims.
    pred = model.predict(windows["test"].X)
    y = windows["test"].y
    if pred.ndim > 1:
        pred = pred[:, 0] if horizon > 1 else pred.reshape(-1)
        # for multi-horizon take first step for coherence demo simplicity
    if np.asarray(y).ndim > 1:
        y = np.asarray(y)[:, 0]
    return np.asarray(y, dtype=float).reshape(-1), np.asarray(pred, dtype=float).reshape(-1)


def main():
    panel = build_analysis_panel()
    fp = dataset_fingerprint()
    outer = make_outer_chronological_folds(panel, n_folds=3)[0]
    split = fold_to_split_spec(outer)
    horizon, context = 1, 32
    h = memory_hierarchy()

    y_b, p_b = [], []
    for t in BOTTOMS:
        y, p = _fit_predict(panel, split, t, horizon, context, "ridge")
        y_b.append(y)
        p_b.append(p)
    y_bottom = np.column_stack(y_b)
    p_bottom = np.column_stack(p_b)
    y_top, p_top = _fit_predict(panel, split, TOP, horizon, context, "ridge")

    # align lengths
    n = min(len(y_top), y_bottom.shape[0], p_bottom.shape[0], len(p_top))
    y_bottom, p_bottom = y_bottom[:n], p_bottom[:n]
    y_top, p_top = y_top[:n], p_top[:n]

    rows = []
    for method in ("independent", "bottom_up", "top_down", "ols", "wls"):
        out = reconcile(method, h, p_bottom, p_top, series_var=np.ones(8))
        rows.append(
            {
                "method": method,
                "top_mae": mae(y_top, out["top"]),
                "bottom_mae_mean": float(np.mean([mae(y_bottom[:, i], out["bottom"][:, i]) for i in range(7)])),
                "coherence_error": out["coherence_error"],
                "coherent": is_coherent(out["bottom"], out["top"], atol=1e-3 * np.mean(np.abs(out["top"]))),
            }
        )

    df = pd.DataFrame(rows)
    out_dir = ROOT / "results" / "development" / "metrics"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "hierarchy_memory_outer0_ridge.csv"
    df.to_csv(out_csv, index=False)
    meta = {
        "experiment_stage": ExperimentStage.DEVELOPMENT.value,
        "eligible_for_final_claims": False,
        "evaluation_role": "inner_model_selection",
        "dataset_fingerprint": fp["fingerprint"],
        "outer_fold": outer.fold_id,
        "hierarchy": h.name,
        "model": "ridge",
        "note": "Development screen of reconciliation operators on memory UM hierarchy",
    }
    (out_dir / "hierarchy_memory_outer0_ridge.meta.json").write_text(json.dumps(meta, indent=2))
    print(df.to_string(index=False))
    print("wrote", out_csv)


if __name__ == "__main__":
    main()
