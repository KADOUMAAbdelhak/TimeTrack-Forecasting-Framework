"""Profile DLinear runtime on a single development series."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.runner import prepare_split_windows
from models import forecasting as F
from timetrack.data import build_analysis_panel
from timetrack.splits import fold_to_split_spec, make_outer_chronological_folds


def main():
    panel = build_analysis_panel()
    fold = make_outer_chronological_folds(panel, n_folds=3)[0]
    split = fold_to_split_spec(fold)
    target = "cluster_mean_CU"
    horizon, context = 1, 32

    t0 = time.perf_counter()
    windows = prepare_split_windows(panel, split, target, horizon, context, flat=False)
    window_s = time.perf_counter() - t0

    results = {"window_construction_sec": window_s, "n_train": len(windows["train"].X)}
    for epochs, timeout, max_batches in [(5, 60, None), (30, 120, 50), (30, 30, 20)]:
        model = F.build_model(
            "dlinear",
            horizon=horizon,
            context_length=context,
            seed=0,
            epochs=epochs,
            timeout_sec=timeout,
            max_batches_per_epoch=max_batches,
            num_threads=1,
            patience=3,
        )
        t1 = time.perf_counter()
        model.fit(windows["train"].X, windows["train"].y, windows["val"].X, windows["val"].y)
        fit_s = time.perf_counter() - t1
        t2 = time.perf_counter()
        pred = model.predict(windows["test"].X)
        pred_s = time.perf_counter() - t2
        key = f"epochs{epochs}_timeout{timeout}_maxb{max_batches}"
        results[key] = {
            "fit_sec": fit_s,
            "predict_sec": pred_s,
            "n_pred": len(pred),
            "runtime": getattr(model, "runtime_meta_", {}),
            "train_time_meta": model.metadata.training_time_sec,
        }
        print(key, "fit", round(fit_s, 2), "pred", round(pred_s, 3), model.runtime_meta_)

    out = ROOT / "results" / "development" / "metrics" / "dlinear_runtime_profile.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print("wrote", out)


if __name__ == "__main__":
    main()
