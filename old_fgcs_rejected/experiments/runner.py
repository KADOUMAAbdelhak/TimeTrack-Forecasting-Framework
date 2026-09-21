"""Experiment runner: leakage-safe train/eval loops with pilot/final stage isolation."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from models import forecasting as F
from timetrack.constants import MAPE_ZERO_EPS, SAMPLING_SECONDS
from timetrack.data import build_analysis_panel, dataset_fingerprint
from timetrack.evaluation_stage import (
    ExperimentStage,
    annotate_run_result,
    assert_eligible_for_final_leaderboard,
    filter_final_eligible,
    parse_stage,
    results_root_for_stage,
    stage_metadata,
)
from timetrack.metrics import compute_metrics
from timetrack.splits import SplitSpec, build_windows, origins_for_split, post_outage_split

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS = PROJECT_ROOT / "results"  # legacy alias; prefer stage roots


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def config_hash(cfg: dict[str, Any]) -> str:
    blob = json.dumps(cfg, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:12]


def run_id(scope: str, target: str, horizon: int, context: int, model: str, seed: int) -> str:
    return f"{scope}__{target}__h{horizon}__c{context}__{model}__seed{seed}"


def _software_versions() -> dict[str, str]:
    vers = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    for mod in ("numpy", "pandas", "sklearn", "lightgbm", "xgboost", "torch", "optuna"):
        try:
            m = __import__(mod if mod != "sklearn" else "sklearn")
            vers[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            vers[mod] = "not_installed"
    return vers


def _series_matrix(panel: pd.DataFrame, target: str, exog: list[str] | None) -> tuple[np.ndarray, list[str]]:
    cols = [target] + (exog or [])
    missing = [c for c in cols if c not in panel.columns]
    if missing:
        raise KeyError(f"missing columns: {missing}")
    return panel[cols].to_numpy(dtype=float), cols


def prepare_split_windows(
    panel: pd.DataFrame,
    split: SplitSpec,
    target: str,
    horizon: int,
    context: int,
    exog: list[str] | None = None,
    flat: bool = False,
) -> dict[str, Any]:
    values, names = _series_matrix(panel, target, exog)
    out = {}
    for part, idx in ("train", split.train_idx), ("val", split.val_idx), ("test", split.test_idx):
        origins = origins_for_split(idx, context, horizon, len(panel))
        ds = build_windows(
            values,
            origins,
            context=context,
            horizon=horizon,
            feature_names=names,
            flat=flat,
            panel_for_gap_check=panel,
        )
        out[part] = ds
    return out


def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_train_series: np.ndarray,
    horizon: int,
) -> dict[str, Any]:
    """If multi-horizon, aggregate metrics over flattened steps and per-step."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if y_true.ndim == 1 or horizon == 1:
        return compute_metrics(y_true, y_pred, y_train=y_train_series)
    metrics = compute_metrics(y_true.reshape(-1), y_pred.reshape(-1), y_train=y_train_series)
    per_h = []
    for h in range(horizon):
        per_h.append(compute_metrics(y_true[:, h], y_pred[:, h], y_train=y_train_series))
    metrics["per_horizon"] = per_h
    return metrics


def _row_from_result(r: dict[str, Any]) -> dict[str, Any]:
    mt = r["metrics_test"]
    return {
        "run_id": r["run_id"],
        "experiment_stage": r.get("experiment_stage", ExperimentStage.PILOT.value),
        "eligible_for_final_claims": bool(r.get("eligible_for_final_claims", False)),
        "evaluation_role": r.get("evaluation_role", "development_benchmark"),
        "scope": r["scope"],
        "target": r["target"],
        "model": r["model"],
        "horizon": r["horizon"],
        "context": r["context"],
        "seed": r["seed"],
        "mae": mt.get("mae"),
        "rmse": mt.get("rmse"),
        "mse": mt.get("mse"),
        "smape": mt.get("smape"),
        "mape": mt.get("mape"),
        "mape_fraction_excluded": mt.get("mape_fraction_excluded"),
        "mase": mt.get("mase"),
        "r2": mt.get("r2"),
        "nrmse": mt.get("nrmse"),
        "medae": mt.get("medae"),
        "maxae": mt.get("maxae"),
        "peak_recall": mt.get("peak_recall"),
        "peak_precision": mt.get("peak_precision"),
        "training_time_sec": r["model_metadata"].get("training_time_sec"),
        "inference_time_sec": r["model_metadata"].get("inference_time_sec"),
        "n_parameters": r["model_metadata"].get("n_parameters"),
        "runtime_sec": r["runtime_sec"],
        "n_test_windows": r["n_test_windows"],
    }


def run_single_experiment(
    panel: pd.DataFrame,
    split: SplitSpec,
    *,
    target: str,
    model_name: str,
    horizon: int,
    context: int,
    seed: int = 0,
    exog: list[str] | None = None,
    scope: str = "local",
    model_kwargs: dict[str, Any] | None = None,
    save_artifacts: bool = True,
    cfg_meta: dict[str, Any] | None = None,
    experiment_stage: str | ExperimentStage = ExperimentStage.PILOT,
) -> dict[str, Any]:
    stage = parse_stage(experiment_stage)
    model_kwargs = dict(model_kwargs or {})
    rid = run_id(scope, target, horizon, context, model_name, seed)
    start = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()

    flat = model_name in {
        "ridge",
        "lasso",
        "elasticnet",
        "random_forest",
        "extra_trees",
        "lightgbm",
        "xgboost",
        "catboost",
    }
    if model_name in {"persistence", "seasonal_persistence", "historical_mean", "moving_average", "ewma", "drift"}:
        flat = False

    windows = prepare_split_windows(panel, split, target, horizon, context, exog=exog, flat=flat)
    y_train_series = panel.loc[split.train_idx, target].to_numpy(dtype=float)

    model = F.build_model(
        model_name,
        horizon=horizon,
        context_length=context,
        seed=seed,
        **model_kwargs,
    )
    model.metadata.target = target
    model.metadata.software_versions = _software_versions()

    model.fit(
        windows["train"].X,
        windows["train"].y,
        X_val=windows["val"].X,
        y_val=windows["val"].y,
    )
    pred_test = model.predict(windows["test"].X)
    pred_val = model.predict(windows["val"].X)

    test_metrics = evaluate_predictions(windows["test"].y, pred_test, y_train_series, horizon)
    val_metrics = evaluate_predictions(windows["val"].y, pred_val, y_train_series, horizon)

    elapsed = time.perf_counter() - t0
    result = {
        "run_id": rid,
        "scope": scope,
        "target": target,
        "model": model_name,
        "horizon": horizon,
        "context": context,
        "seed": seed,
        "exog": exog or [],
        "split": split.meta,
        "metrics_test": test_metrics,
        "metrics_val": val_metrics,
        "model_metadata": model.metadata.to_dict(),
        "sampling_seconds": SAMPLING_SECONDS,
        "mape_eps": MAPE_ZERO_EPS,
        "start_time_utc": start,
        "end_time_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_sec": elapsed,
        "n_train_windows": int(len(windows["train"].y)),
        "n_val_windows": int(len(windows["val"].y)),
        "n_test_windows": int(len(windows["test"].y)),
        "config_meta": dict(cfg_meta or {}),
    }
    annotate_run_result(result, stage)

    if save_artifacts:
        _persist_run(result, model, windows, pred_test, stage=stage)
    return result


def _persist_run(result: dict[str, Any], model, windows, pred_test, stage: ExperimentStage) -> None:
    rid = result["run_id"]
    root = results_root_for_stage(stage)
    raw_dir = root / "metrics" / "raw_runs"
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_json = raw_dir / f"{rid}.json"
    if out_json.exists():
        raise FileExistsError(f"Refusing to overwrite existing run: {out_json}")
    out_json.write_text(json.dumps(result, indent=2, default=str))

    pred_dir = root / "predictions"
    pred_dir.mkdir(parents=True, exist_ok=True)
    y_true = np.asarray(windows["test"].y)
    pred = np.asarray(pred_test)
    df = pd.DataFrame(
        {
            "origin_idx": windows["test"].origin_idx,
            "target_idx": windows["test"].target_idx,
        }
    )
    if y_true.ndim == 1:
        df["y_true"] = y_true
        df["y_pred"] = pred
    else:
        for h in range(y_true.shape[1]):
            df[f"y_true_h{h+1}"] = y_true[:, h]
            df[f"y_pred_h{h+1}"] = pred[:, h]
    df.to_csv(pred_dir / f"{rid}.csv", index=False)

    model_dir = root / "models" / rid
    model.save(model_dir)


def append_all_runs(
    results: list[dict[str, Any]],
    *,
    stage: str | ExperimentStage | None = None,
) -> Path:
    if not results:
        raise ValueError("no results to append")
    if stage is None:
        stage = parse_stage(results[0].get("experiment_stage", ExperimentStage.PILOT))
    else:
        stage = parse_stage(stage)

    # Refuse mixing stages in one append
    stages = {parse_stage(r.get("experiment_stage", ExperimentStage.PILOT)) for r in results}
    if len(stages) != 1 or stage not in stages:
        raise AssertionError(f"append_all_runs refuses mixed or mismatched stages: {stages} vs {stage}")

    rows = [_row_from_result(r) for r in results]
    root = results_root_for_stage(stage)
    path = root / "metrics" / "all_runs.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    if path.exists():
        prev = pd.read_csv(path)
        df = pd.concat([prev[~prev["run_id"].isin(df["run_id"])], df], ignore_index=True)
    df.to_csv(path, index=False)
    return path


def build_leaderboards(
    all_runs_csv: Path | None = None,
    *,
    stage: str | ExperimentStage = ExperimentStage.PILOT,
    require_final_eligible: bool | None = None,
) -> dict[str, Path]:
    stage = parse_stage(stage)
    root = results_root_for_stage(stage)
    path = all_runs_csv or (root / "metrics" / "all_runs.csv")
    df = pd.read_csv(path)

    if require_final_eligible is None:
        require_final_eligible = stage == ExperimentStage.FINAL

    if require_final_eligible:
        assert_eligible_for_final_leaderboard(df)
        df = filter_final_eligible(df)
        if df.empty:
            raise AssertionError("Final leaderboard would be empty after eligibility filter")
    else:
        # Pilot/development leaderboards must not silently include final-only claims metadata incorrectly,
        # but may include any non-final rows present in the stage file.
        if "experiment_stage" in df.columns:
            unexpected = df[df["experiment_stage"] == ExperimentStage.FINAL.value]
            if len(unexpected) and stage != ExperimentStage.FINAL:
                raise AssertionError("Pilot/development aggregation found final-stage rows; refusing mix")

    out_paths: dict[str, Path] = {}
    metrics_dir = root / "metrics"
    tables_md = root / "tables" / "markdown"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    tables_md.mkdir(parents=True, exist_ok=True)

    def _write(frame: pd.DataFrame, name: str) -> Path:
        p = metrics_dir / name
        frame.to_csv(p, index=False)
        out_paths[name] = p
        md = tables_md / name.replace(".csv", ".md")
        md.write_text(frame.head(50).to_markdown(index=False))
        return p

    lb = df.sort_values(["target", "horizon", "mae"])
    _write(lb, "leaderboard.csv")
    _write(df.sort_values(["target", "mae"]), "per_target_leaderboard.csv")
    _write(df.sort_values(["horizon", "mae"]), "per_horizon_leaderboard.csv")

    gcols = ["target", "model", "horizon", "context"]
    summary = (
        df.groupby(gcols, dropna=False)
        .agg(
            n_seeds=("seed", "count"),
            mae_mean=("mae", "mean"),
            mae_std=("mae", "std"),
            rmse_mean=("rmse", "mean"),
            rmse_std=("rmse", "std"),
            mase_mean=("mase", "mean"),
            mase_std=("mase", "std"),
            r2_mean=("r2", "mean"),
            r2_std=("r2", "std"),
            train_time_mean=("training_time_sec", "mean"),
            infer_time_mean=("inference_time_sec", "mean"),
        )
        .reset_index()
    )
    _write(summary, "statistical_summary.csv")
    return out_paths


def build_final_leaderboards(all_runs_csv: Path | None = None) -> dict[str, Path]:
    """Explicit final-only entry point; raises if pilot/ineligible rows are present."""
    root = results_root_for_stage(ExperimentStage.FINAL)
    path = all_runs_csv or (root / "metrics" / "all_runs.csv")
    if not path.exists():
        raise FileNotFoundError(
            f"No final all_runs.csv at {path}. "
            "Final experiments have not been executed yet (pilot runs are ineligible)."
        )
    return build_leaderboards(path, stage=ExperimentStage.FINAL, require_final_eligible=True)


def run_from_config(config_path: str | Path) -> list[dict[str, Any]]:
    cfg = load_config(config_path)
    stage = parse_stage(cfg.get("experiment_stage", ExperimentStage.PILOT))
    # Safety: publication configs cannot silently default to final until freeze
    if cfg.get("tier") == "publication" and stage != ExperimentStage.FINAL:
        print(
            "WARNING: publication tier without experiment_stage=final; treating as pilot/development",
            flush=True,
        )

    fp = dataset_fingerprint()
    panel = build_analysis_panel()
    split = post_outage_split(
        panel,
        train_frac=cfg.get("train_frac", 0.70),
        val_frac=cfg.get("val_frac", 0.15),
    )
    results = []
    cfg_meta = {
        "config_path": str(config_path),
        "config_hash": config_hash(cfg),
        "dataset_fingerprint": fp["fingerprint"],
        "tier": cfg.get("tier", "custom"),
        **stage_metadata(stage),
    }
    stage_root = results_root_for_stage(stage)
    for target in cfg["targets"]:
        exog = cfg.get("exog", {}).get(target)
        for horizon in cfg["horizons"]:
            for context in cfg["contexts"]:
                for model_name in cfg["models"]:
                    for seed in cfg.get("seeds", [0]):
                        mk = cfg.get("model_kwargs", {}).get(model_name, {})
                        print(
                            f"RUN[{stage.value}] {target} h={horizon} c={context} "
                            f"model={model_name} seed={seed}",
                            flush=True,
                        )
                        try:
                            r = run_single_experiment(
                                panel,
                                split,
                                target=target,
                                model_name=model_name,
                                horizon=horizon,
                                context=context,
                                seed=seed,
                                exog=exog,
                                scope=cfg.get("scope", "local"),
                                model_kwargs=mk,
                                save_artifacts=True,
                                cfg_meta=cfg_meta,
                                experiment_stage=stage,
                            )
                            results.append(r)
                            print(
                                f"  MAE={r['metrics_test']['mae']:.6g} MASE={r['metrics_test'].get('mase')} "
                                f"R2={r['metrics_test']['r2']:.4f}",
                                flush=True,
                            )
                        except FileExistsError as e:
                            print(f"  skip existing: {e}", flush=True)
                        except Exception as e:
                            print(f"  FAILED: {e}", flush=True)
                            fail_path = stage_root / "logs" / "failures.jsonl"
                            fail_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(fail_path, "a") as f:
                                f.write(
                                    json.dumps(
                                        {
                                            "target": target,
                                            "model": model_name,
                                            "error": str(e),
                                            "experiment_stage": stage.value,
                                        }
                                    )
                                    + "\n"
                                )
    if results:
        append_all_runs(results, stage=stage)
        build_leaderboards(stage=stage)
    return results
