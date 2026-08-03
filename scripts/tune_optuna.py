"""Optuna HPO with nested inner-fold validation (no outer/final evaluation access)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import optuna
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.runner import config_hash, prepare_split_windows, run_id
from models import forecasting as F
from timetrack.data import build_analysis_panel, dataset_fingerprint
from timetrack.evaluation_stage import ExperimentStage
from timetrack.metrics import mase
from timetrack.splits import fold_to_split_spec, make_inner_rolling_folds, make_outer_chronological_folds

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


def _score(y_true, y_pred, y_train) -> float:
    y_true = np.asarray(y_true, dtype=float).reshape(-1)
    y_pred = np.asarray(y_pred, dtype=float).reshape(-1)
    s = mase(y_true, y_pred, y_train)
    if s != s:
        return float(np.mean(np.abs(y_true - y_pred)))
    return float(s)


def objective_factory(
    panel,
    inner_folds,
    target: str,
    model_name: str,
    horizon: int,
    context: int,
    seed: int,
    exog: list[str] | None,
):
    flat = model_name in {"ridge", "lasso", "elasticnet", "lightgbm", "xgboost", "random_forest"}

    def objective(trial: optuna.Trial) -> float:
        kwargs = SEARCH_SPACES[model_name](trial)
        scores = []
        for fold in inner_folds:
            split = fold_to_split_spec(fold)
            # Critical: use val as evaluation; do not touch any outer test indices
            windows = prepare_split_windows(
                panel, split, target, horizon, context, exog=exog, flat=flat
            )
            y_train = panel.loc[split.train_idx, target].to_numpy(dtype=float)
            model = F.build_model(
                model_name, horizon=horizon, context_length=context, seed=seed, **kwargs
            )
            try:
                model.fit(windows["train"].X, windows["train"].y, windows["val"].X, windows["val"].y)
                pred = model.predict(windows["val"].X)
                scores.append(_score(windows["val"].y, pred, y_train))
            except Exception as exc:  # trial failure handling
                raise optuna.TrialPruned(f"fit/predict failed: {exc}") from exc
            trial.report(float(np.mean(scores)), step=len(scores))
            if trial.should_prune():
                raise optuna.TrialPruned()
        return float(np.mean(scores))

    return objective


def export_study_artifacts(study: optuna.Study, out_dir: Path, meta: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    # history CSV
    rows = []
    for t in study.trials:
        rows.append(
            {
                "number": t.number,
                "state": str(t.state),
                "value": t.value,
                **{f"param_{k}": v for k, v in t.params.items()},
            }
        )
    pd.DataFrame(rows).to_csv(out_dir / "trial_history.csv", index=False)
    (out_dir / "best_config.json").write_text(
        json.dumps({"best_value": study.best_value, "best_params": study.best_params, **meta}, indent=2)
    )
    (out_dir / "search_space.json").write_text(
        json.dumps({"models": list(SEARCH_SPACES), "note": "see tune_optuna.SEARCH_SPACES"}, indent=2)
    )
    (out_dir / "study_meta.json").write_text(json.dumps(meta, indent=2))
    # plots
    try:
        from optuna.visualization.matplotlib import (
            plot_optimization_history,
            plot_param_importances,
        )
        import matplotlib.pyplot as plt

        ax = plot_optimization_history(study)
        fig = ax.figure if hasattr(ax, "figure") else plt.gcf()
        fig.savefig(out_dir / "optimization_history.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        try:
            ax2 = plot_param_importances(study)
            fig2 = ax2.figure if hasattr(ax2, "figure") else plt.gcf()
            fig2.savefig(out_dir / "param_importance.png", dpi=150, bbox_inches="tight")
            plt.close(fig2)
        except Exception:
            pass
    except Exception as exc:
        (out_dir / "plot_warning.txt").write_text(str(exc))


def main():
    p = argparse.ArgumentParser(description="Fold-aware Optuna HPO (development stage only)")
    p.add_argument("--target", required=True)
    p.add_argument("--model", required=True, choices=sorted(SEARCH_SPACES))
    p.add_argument("--horizon", type=int, default=1)
    p.add_argument("--context", type=int, default=32)
    p.add_argument("--trials", type=int, default=20)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--outer-fold", type=int, default=0, help="Which outer fold's train span to use for inner HPO")
    p.add_argument("--n-outer", type=int, default=3)
    p.add_argument("--n-inner", type=int, default=3)
    p.add_argument("--storage", default="results/development/tuning/optuna.db")
    p.add_argument("--exog", nargs="*", default=None)
    args = p.parse_args()

    panel = build_analysis_panel()
    fp = dataset_fingerprint()
    outer_folds = make_outer_chronological_folds(panel, n_folds=args.n_outer)
    of = outer_folds[args.outer_fold]
    # Inner HPO uses only data before outer test
    fit_span = np.concatenate([of.train_idx, of.val_idx])
    # Ensure no outer test leakage
    assert not set(fit_span).intersection(of.test_idx)
    inner = make_inner_rolling_folds(panel, fit_span, n_inner=args.n_inner, mode="expanding")

    storage_path = ROOT / args.storage
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage = f"sqlite:///{storage_path}"
    study_name = (
        f"hpo__{args.target}__h{args.horizon}__c{args.context}__{args.model}"
        f"__outer{args.outer_fold}__seed{args.seed}"
    )
    meta = {
        "experiment_stage": ExperimentStage.DEVELOPMENT.value,
        "eligible_for_final_claims": False,
        "evaluation_role": "inner_model_selection",
        "study_name": study_name,
        "target": args.target,
        "model": args.model,
        "horizon": args.horizon,
        "context": args.context,
        "seed": args.seed,
        "outer_fold": args.outer_fold,
        "n_inner_folds": len(inner),
        "dataset_fingerprint": fp["fingerprint"],
        "outer_meta": of.meta,
        "trials_budget": args.trials,
        "timeout_sec": args.timeout,
    }
    meta["config_hash"] = config_hash(meta)

    study = optuna.create_study(
        direction="minimize",
        study_name=study_name,
        storage=storage,
        load_if_exists=True,
        sampler=optuna.samplers.TPESampler(seed=args.seed),
        pruner=optuna.pruners.MedianPruner(),
    )
    study.optimize(
        objective_factory(
            panel, inner, args.target, args.model, args.horizon, args.context, args.seed, args.exog
        ),
        n_trials=args.trials,
        timeout=args.timeout,
        catch=(Exception,),
    )
    out_dir = ROOT / "results" / "development" / "tuning" / study_name
    export_study_artifacts(study, out_dir, meta)
    print(json.dumps({"best_value": study.best_value, "best_params": study.best_params, "out": str(out_dir)}, indent=2))


if __name__ == "__main__":
    main()
