"""Optuna HPO with time-series validation objective (MASE preferred)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import optuna
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.runner import prepare_split_windows, run_id
from models import forecasting as F
from timetrack.data import build_analysis_panel
from timetrack.metrics import mase
from timetrack.splits import post_outage_split


SEARCH_SPACES = {
    "lightgbm": lambda t: {
        "n_estimators": t.suggest_int("n_estimators", 50, 400),
        "learning_rate": t.suggest_float("learning_rate", 1e-3, 0.2, log=True),
        "num_leaves": t.suggest_int("num_leaves", 16, 128),
        "max_depth": t.suggest_int("max_depth", 3, 12),
    },
    "xgboost": lambda t: {
        "n_estimators": t.suggest_int("n_estimators", 50, 400),
        "learning_rate": t.suggest_float("learning_rate", 1e-3, 0.2, log=True),
        "max_depth": t.suggest_int("max_depth", 3, 10),
    },
    "ridge": lambda t: {"alpha": t.suggest_float("alpha", 1e-4, 100.0, log=True)},
    "lstm": lambda t: {
        "hidden_size": t.suggest_categorical("hidden_size", [32, 64, 128]),
        "lr": t.suggest_float("lr", 1e-4, 1e-2, log=True),
        "epochs": t.suggest_int("epochs", 10, 40),
        "dropout": t.suggest_float("dropout", 0.0, 0.3),
    },
    "dlinear": lambda t: {
        "epochs": t.suggest_int("epochs", 10, 60),
        "lr": t.suggest_float("lr", 1e-4, 1e-2, log=True),
        "kernel_size": t.suggest_categorical("kernel_size", [13, 25, 49]),
    },
}


def objective_factory(panel, split, target, model_name, horizon, context, seed):
    y_train = panel.loc[split.train_idx, target].to_numpy(dtype=float)
    flat = model_name in {"ridge", "lasso", "elasticnet", "lightgbm", "xgboost", "random_forest"}
    windows = prepare_split_windows(panel, split, target, horizon, context, flat=flat)

    def objective(trial: optuna.Trial) -> float:
        kwargs = SEARCH_SPACES[model_name](trial)
        model = F.build_model(model_name, horizon=horizon, context_length=context, seed=seed, **kwargs)
        model.fit(windows["train"].X, windows["train"].y, windows["val"].X, windows["val"].y)
        pred = model.predict(windows["val"].X)
        y_true = windows["val"].y
        if y_true.ndim > 1:
            y_true = y_true.reshape(-1)
            pred = pred.reshape(-1)
        score = mase(y_true, pred, y_train)
        if score != score:  # NaN -> fall back to MAE
            import numpy as np

            score = float(np.mean(np.abs(y_true - pred)))
        return float(score)

    return objective


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--target", required=True)
    p.add_argument("--model", required=True, choices=sorted(SEARCH_SPACES))
    p.add_argument("--horizon", type=int, default=1)
    p.add_argument("--context", type=int, default=32)
    p.add_argument("--trials", type=int, default=20)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--storage", default="results/tuning/optuna.db")
    args = p.parse_args()

    panel = build_analysis_panel()
    split = post_outage_split(panel)
    storage = f"sqlite:///{ROOT / args.storage}"
    Path(ROOT / args.storage).parent.mkdir(parents=True, exist_ok=True)
    study_name = run_id("hpo", args.target, args.horizon, args.context, args.model, args.seed)
    study = optuna.create_study(
        direction="minimize",
        study_name=study_name,
        storage=storage,
        load_if_exists=True,
        sampler=optuna.samplers.TPESampler(seed=args.seed),
        pruner=optuna.pruners.MedianPruner(),
    )
    study.optimize(
        objective_factory(panel, split, args.target, args.model, args.horizon, args.context, args.seed),
        n_trials=args.trials,
        timeout=args.timeout,
    )
    out = {
        "study_name": study_name,
        "best_value": study.best_value,
        "best_params": study.best_params,
        "n_trials": len(study.trials),
    }
    out_path = ROOT / "results" / "tuning" / f"{study_name}.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
