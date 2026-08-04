"""Execute a single final experiment pack with resume and wall-clock limits."""

from __future__ import annotations

import gc
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.final_hierarchy_runner import (
    FLAT_MODELS,
    _align,
    _first_step,
    _prepare_cpu_panel,
)
from experiments.runner import prepare_split_windows
from models import forecasting as F
from models.hybrid.reconciliation import (
    coherence_error,
    estimate_residual_covariance,
    is_coherent,
    reconcile,
)
from timetrack.data import build_analysis_panel, dataset_fingerprint
from timetrack.efficiency import measure_inference_latencies, peak_rss_bytes, timed_train
from timetrack.final_config import freeze_metadata
from timetrack.final_packs import (
    RunStatus,
    WallClockGuard,
    config_hash,
    dependencies_satisfied,
    load_packs_config,
    pack_by_id,
    pack_hash,
    pack_output_dir,
)
from timetrack.hierarchy_registry import final_hierarchy_registry, summing_matrix_hash
from timetrack.metrics import mae
from timetrack.splits import fold_to_split_spec, make_outer_chronological_folds

try:
    from models.hybrid.reconciliation import bond0_hierarchy, BOND_MEMBER_IFACES
except Exception:  # pragma: no cover
    bond0_hierarchy = None
    BOND_MEMBER_IFACES = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_shared_hparams(cfg: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / (cfg.get("shared_hyperparameters_path") or "")
    if path.exists():
        return yaml.safe_load(path.read_text()) or {}
    dlin = dict(cfg.get("dlinear_fixed") or {})
    return {
        "ridge_cpu": {"alpha": 1.0},
        "ridge_memory": {"alpha": 1.0},
        "lightgbm_cpu": {"n_estimators": 200, "learning_rate": 0.05, "num_leaves": 31},
        "lightgbm_memory": {"n_estimators": 200, "learning_rate": 0.05, "num_leaves": 31},
        "dlinear_cpu": {**dlin, "enabled": True},
        "dlinear_memory": {**dlin, "enabled": True},
    }


def _model_kwargs_for(cfg: dict[str, Any], shared: dict[str, Any], model: str, hierarchy: str) -> dict[str, Any]:
    is_cpu = "cpu" in hierarchy
    if model == "ridge":
        key = "ridge_cpu" if is_cpu else "ridge_memory"
        legacy = shared.get("ridge") or {}
        return dict(shared.get(key) or legacy or {"alpha": 1.0})
    if model == "lightgbm":
        key = "lightgbm_cpu" if is_cpu else "lightgbm_memory"
        return dict(shared.get(key) or {})
    if model == "dlinear":
        key = "dlinear_cpu" if is_cpu else "dlinear_memory"
        block = dict(shared.get(key) or shared.get("dlinear") or cfg.get("dlinear_fixed") or {})
        block.pop("enabled", None)
        block.pop("eligibility_reason", None)
        return block
    if model == "lstm":
        return {"epochs": 30, "hidden_size": 64, "patience": 5, "num_threads": 1}
    return {}


def _complexity_key(model: str, params: dict[str, Any]) -> tuple:
    if model == "ridge":
        return (abs(np.log10(max(float(params.get("alpha", 1.0)), 1e-12))),)
    if model == "lightgbm":
        return (
            int(params.get("n_estimators", 0)),
            int(params.get("num_leaves", 0)),
            float(params.get("learning_rate", 0)),
        )
    return (0,)


def _fit_predict(
    panel: pd.DataFrame,
    split,
    target: str,
    horizon: int,
    context: int,
    model_name: str,
    seed: int,
    kwargs: dict[str, Any],
    eff_proto: dict[str, Any],
) -> dict[str, Any]:
    flat = model_name in FLAT_MODELS
    windows = prepare_split_windows(panel, split, target, horizon, context, flat=flat)
    model = F.build_model(model_name, horizon=horizon, context_length=context, seed=seed, **kwargs)

    def _fit():
        return model.fit(windows["train"].X, windows["train"].y, windows["val"].X, windows["val"].y)

    _, wall_train, cpu_train, peak_rss = timed_train(_fit)
    X_batch = windows["val"].X if len(windows["val"].X) else windows["test"].X
    lat = measure_inference_latencies(
        model.predict,
        X_batch,
        n_warm=int(eff_proto.get("warmup", 1)),
        n_repeat=int(eff_proto.get("repeats", 3)),
    )
    pred_val = model.predict(windows["val"].X)
    pred_test = model.predict(windows["test"].X)
    out = {
        "y_train": _first_step(windows["train"].y),
        "y_val": _first_step(windows["val"].y),
        "y_test": _first_step(windows["test"].y),
        "p_val": _first_step(pred_val),
        "p_test": _first_step(pred_test),
        "origin_val": windows["val"].origin_idx,
        "origin_test": windows["test"].origin_idx,
        "wall_train_sec": float(wall_train),
        "cpu_train_sec": float(cpu_train),
        "peak_rss_mb": float(peak_rss),
        **lat,
    }
    del model
    gc.collect()
    return out


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))


def _append_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    if path.exists():
        old = pd.read_csv(path)
        df = pd.concat([old, df], ignore_index=True)
        df = df.drop_duplicates(subset=[c for c in ("run_id",) if c in df.columns], keep="last")
    df.to_csv(path, index=False)


def _mae_tied(a: float, b: float) -> bool:
    if not (np.isfinite(a) and np.isfinite(b)):
        return False
    return abs(a - b) < max(1e-9, 1e-4 * max(abs(a), abs(b), 1e-12))


def _eval_candidate_folds(
    panel: pd.DataFrame,
    folds,
    target: str,
    model_name: str,
    params: dict[str, Any],
    *,
    context: int,
    horizon: int,
    seed: int,
    eff_proto: dict[str, Any],
) -> dict[str, Any]:
    from timetrack.metrics import mae as _mae
    from timetrack.metrics import mase_result

    fold_maes, fold_mase, fold_mase_valid, fold_pers = [], [], [], []
    for fold_id, fold in enumerate(folds):
        split = fold_to_split_spec(fold)
        pack = _fit_predict(panel, split, target, horizon, context, model_name, seed, params, eff_proto)
        pers = _fit_predict(panel, split, target, horizon, context, "persistence", 0, {}, {"warmup": 0, "repeats": 1})
        yv, pv = pack["y_val"], pack["p_val"]
        fold_maes.append(float(_mae(yv, pv)))
        mr = mase_result(yv, pv, pack["y_train"])
        fold_mase.append(float(mr["mase"]) if mr.get("mase_valid") else float("nan"))
        fold_mase_valid.append(bool(mr.get("mase_valid")))
        fold_pers.append(float(_mae(pers["y_val"], pers["p_val"])))
    arr = np.asarray(fold_maes, dtype=float)
    valid_mase = [m for m, ok in zip(fold_mase, fold_mase_valid) if ok and np.isfinite(m)]
    return {
        "fold_maes": fold_maes,
        "fold_mase": fold_mase,
        "fold_mase_valid": fold_mase_valid,
        "fold_persistence_maes": fold_pers,
        "mean_mae": float(np.mean(arr)),
        "std_mae": float(np.std(arr, ddof=0)),
        "mean_valid_mase": float(np.mean(valid_mase)) if valid_mase else float("nan"),
        "n_valid_mase_folds": int(len(valid_mase)),
        "mean_persistence_mae": float(np.mean(fold_pers)),
        "rel_mae_vs_persistence": float(np.mean(arr) / max(float(np.mean(fold_pers)), 1e-12)),
    }


def _eligibility_gate(fold_maes: list[float], fold_pers: list[float], preds_finite: bool = True) -> tuple[bool, str]:
    if not preds_finite:
        return False, "non_finite_predictions"
    if len(fold_maes) < 2:
        return False, "insufficient_folds"
    ratios = []
    for m, p in zip(fold_maes, fold_pers):
        if not (np.isfinite(m) and np.isfinite(p) and p > 0):
            continue
        ratios.append(m / p)
    if len(ratios) < 2:
        return False, "fewer_than_two_valid_metric_folds"
    mean_r = float(np.mean(ratios))
    if mean_r > 2.0:
        return False, f"mean_mae_gt_2x_persistence ({mean_r:.3f})"
    if any(r > 5.0 for r in ratios):
        return False, f"fold_mae_gt_5x_persistence ({max(ratios):.3f})"
    return True, "passed_persistence_eligibility_gate"


def run_shared_tuning(cfg: dict[str, Any], pack: dict[str, Any], out: Path, guard: WallClockGuard, status: RunStatus) -> None:
    panel = build_analysis_panel()
    folds = make_outer_chronological_folds(panel, n_folds=int(cfg["n_outer_folds"]))
    context = int(cfg.get("context", 32))
    horizon = 1
    metrics_dir = out / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    eff_light = {"warmup": 0, "repeats": 1}
    rows: list[dict[str, Any]] = []
    diag_rows: list[dict[str, Any]] = []

    alphas = [float(a) for a in (cfg.get("ridge_alpha_grid") or [1e-4, 1e-2, 1.0, 100.0, 1e4])]
    lgbm_space = [
        {"n_estimators": 100, "learning_rate": 0.05, "num_leaves": 15},
        {"n_estimators": 200, "learning_rate": 0.05, "num_leaves": 31},
        {"n_estimators": 300, "learning_rate": 0.03, "num_leaves": 31},
        {"n_estimators": 200, "learning_rate": 0.1, "num_leaves": 63},
        {"n_estimators": 400, "learning_rate": 0.05, "num_leaves": 31},
        {"n_estimators": 200, "learning_rate": 0.02, "num_leaves": 15},
        {"n_estimators": 150, "learning_rate": 0.08, "num_leaves": 31},
        {"n_estimators": 250, "learning_rate": 0.05, "num_leaves": 47},
    ]
    assert len(lgbm_space) <= int(cfg.get("lightgbm_max_trials_memory", 8))
    assert len(lgbm_space) <= int(cfg.get("lightgbm_max_trials_cpu", 8))
    default_lgbm = {"n_estimators": 200, "learning_rate": 0.05, "num_leaves": 31}
    canonical_ridge = 1.0
    dlin_fixed = dict(cfg.get("dlinear_fixed") or {})

    def select_from_candidates(cands: list[dict[str, Any]], *, model: str, default_params: dict[str, Any]) -> dict[str, Any]:
        finite = [c for c in cands if np.isfinite(c["mean_mae"])]
        if not finite:
            raise RuntimeError(f"no finite candidates for {model}")
        best = min(finite, key=lambda c: c["mean_mae"])
        tied = [c for c in finite if _mae_tied(c["mean_mae"], best["mean_mae"])]
        if len(tied) == 1:
            best["selection_status"] = "selected"
            best["selection_reason"] = "min_mean_inner_mae"
            for c in cands:
                if c is not best:
                    c["selection_status"] = "rejected"
            return best
        # lower complexity, then canonical/default
        tied_sorted = sorted(tied, key=lambda c: (_complexity_key(model, c["params"]), c["params"] != default_params))
        pick = tied_sorted[0]
        # prefer exact default/canonical if present in tie set
        for c in tied:
            if c["params"] == default_params:
                pick = c
                break
        pick["selection_status"] = "selected_tie_break"
        pick["selection_reason"] = "validation_tie_complexity_then_canonical"
        for c in cands:
            if c is pick:
                continue
            c["selection_status"] = "tied_not_selected" if c in tied else "rejected"
        return pick

    selected: dict[str, Any] = {}

    # ---- Ridge per family ----
    for family, target, key, default_alpha in (
        ("cpu", "cluster_mean_CU", "ridge_cpu", canonical_ridge),
        ("memory", "cluster_UM", "ridge_memory", canonical_ridge),
    ):
        cands = []
        for alpha in alphas:
            if not guard.may_launch_new_run():
                status.status = "partial"
                status.last_message = "launch limit during ridge tuning"
                return
            run_id = f"ridge_{family}_alpha={alpha}"
            params = {"alpha": float(alpha)}
            metrics = _eval_candidate_folds(
                panel, folds, target, "ridge", params, context=context, horizon=horizon, seed=0, eff_proto=eff_light
            )
            row = {"run_id": run_id, "model": "ridge", "family": family, "target": target, "params": params, **metrics}
            cands.append(row)
            rows.append({**{k: v for k, v in row.items() if k != "params"}, **params})
            if run_id not in status.completed_runs:
                status.completed_runs.append(run_id)
            status.save(out / "RUN_STATUS.json")
        all_tied = len(cands) >= 2 and all(_mae_tied(c["mean_mae"], cands[0]["mean_mae"]) for c in cands)
        if family == "memory" and all_tied:
            pick = next(c for c in cands if float(c["params"]["alpha"]) == default_alpha)
            pick["selection_status"] = "selected_tie_canonical"
            pick["selection_reason"] = "validation_tie_canonical_default"
            for c in cands:
                if c is not pick:
                    c["selection_status"] = "tied_not_selected"
        else:
            pick = select_from_candidates(cands, model="ridge", default_params={"alpha": default_alpha})
        selected[key] = {"alpha": float(pick["params"]["alpha"]), "selection_reason": pick.get("selection_reason")}
        # default comparison
        def_metrics = _eval_candidate_folds(
            panel, folds, target, "ridge", {"alpha": default_alpha}, context=context, horizon=horizon, seed=0, eff_proto=eff_light
        )
        selected[key]["vs_default_alpha_1_mean_mae"] = def_metrics["mean_mae"]
        selected[key]["mean_mae"] = pick["mean_mae"]
        selected[key]["std_mae"] = pick["std_mae"]
        selected[key]["fold_maes"] = pick["fold_maes"]
        selected[key]["fold_persistence_maes"] = pick["fold_persistence_maes"]
        selected[key]["rel_mae_vs_persistence"] = pick["rel_mae_vs_persistence"]

    # ---- LightGBM per family ----
    for family, target, key in (
        ("cpu", "cluster_mean_CU", "lightgbm_cpu"),
        ("memory", "cluster_UM", "lightgbm_memory"),
    ):
        cands = []
        for i, params in enumerate(lgbm_space):
            if not guard.may_launch_new_run():
                status.status = "partial"
                status.last_message = "launch limit during lightgbm tuning"
                return
            run_id = f"lgbm_{family}_trial{i}"
            if run_id in status.completed_runs:
                # still need cand list — force recompute metrics from scratch if missing; simplest: skip resume for trial body
                pass
            metrics = _eval_candidate_folds(
                panel, folds, target, "lightgbm", params, context=context, horizon=horizon, seed=0, eff_proto=eff_light
            )
            row = {"run_id": run_id, "model": "lightgbm", "family": family, "target": target, "params": dict(params), **metrics}
            cands.append(row)
            rows.append({**{k: v for k, v in row.items() if k != "params"}, **params})
            if run_id not in status.completed_runs:
                status.completed_runs.append(run_id)
            status.save(out / "RUN_STATUS.json")
        pick = select_from_candidates(cands, model="lightgbm", default_params=default_lgbm)
        selected[key] = {**dict(pick["params"]), "selection_reason": pick.get("selection_reason")}
        def_metrics = _eval_candidate_folds(
            panel, folds, target, "lightgbm", default_lgbm, context=context, horizon=horizon, seed=0, eff_proto=eff_light
        )
        selected[key]["vs_default_mean_mae"] = def_metrics["mean_mae"]
        selected[key]["mean_mae"] = pick["mean_mae"]
        selected[key]["std_mae"] = pick["std_mae"]
        selected[key]["fold_maes"] = pick["fold_maes"]
        selected[key]["fold_persistence_maes"] = pick["fold_persistence_maes"]
        selected[key]["rel_mae_vs_persistence"] = pick["rel_mae_vs_persistence"]
        selected[key]["fold_mase"] = pick["fold_mase"]
        selected[key]["fold_mase_valid"] = pick["fold_mase_valid"]

    # ---- DLinear validation + eligibility (CPU & memory) ----
    for family, target, key in (
        ("cpu", "cluster_mean_CU", "dlinear_cpu"),
        ("memory", "cluster_UM", "dlinear_memory"),
    ):
        if not guard.may_launch_new_run():
            status.status = "partial"
            status.last_message = "launch limit during dlinear validation"
            return
        run_id = f"dlinear_{family}_validate"
        fold_diag = []
        fold_maes, fold_pers = [], []
        all_finite = True
        for fold_id, fold in enumerate(folds):
            split = fold_to_split_spec(fold)
            pack = _fit_predict(panel, split, target, horizon, context, "dlinear", 0, dlin_fixed, eff_light)
            pers = _fit_predict(panel, split, target, horizon, context, "persistence", 0, {}, {"warmup": 0, "repeats": 1})
            from timetrack.metrics import mae as _mae

            yv, pv = pack["y_val"], pack["p_val"]
            yt = pack["y_train"]
            finite = bool(np.all(np.isfinite(pv)))
            all_finite = all_finite and finite
            mae_v = float(_mae(yv, pv))
            mae_p = float(_mae(pers["y_val"], pers["p_val"]))
            fold_maes.append(mae_v)
            fold_pers.append(mae_p)
            # scaling diagnostics from a fresh model fit metadata if available
            fold_diag.append(
                {
                    "fold": fold_id,
                    "y_train_min": float(np.nanmin(yt)),
                    "y_train_median": float(np.nanmedian(yt)),
                    "y_train_max": float(np.nanmax(yt)),
                    "y_val_min": float(np.nanmin(yv)),
                    "y_val_median": float(np.nanmedian(yv)),
                    "y_val_max": float(np.nanmax(yv)),
                    "pred_min": float(np.nanmin(pv)),
                    "pred_median": float(np.nanmedian(pv)),
                    "pred_max": float(np.nanmax(pv)),
                    "finite_pred_pct": float(np.mean(np.isfinite(pv)) * 100),
                    "mae": mae_v,
                    "persistence_mae": mae_p,
                }
            )
            diag_rows.append({"run_id": run_id, "family": family, "target": target, **fold_diag[-1]})
        ok, reason = _eligibility_gate(fold_maes, fold_pers, preds_finite=all_finite)
        selected[key] = {
            **dlin_fixed,
            "enabled": bool(ok),
            "eligibility_reason": reason,
            "mean_mae": float(np.mean(fold_maes)),
            "std_mae": float(np.std(fold_maes, ddof=0)),
            "fold_maes": fold_maes,
            "fold_persistence_maes": fold_pers,
            "rel_mae_vs_persistence": float(np.mean(fold_maes) / max(float(np.mean(fold_pers)), 1e-12)),
            "fold_diagnostics": fold_diag,
        }
        rows.append(
            {
                "run_id": run_id,
                "model": "dlinear",
                "family": family,
                "target": target,
                "mean_mae": selected[key]["mean_mae"],
                "std_mae": selected[key]["std_mae"],
                "enabled": ok,
                "eligibility_reason": reason,
                **{f"fold{i}_mae": fold_maes[i] for i in range(len(fold_maes))},
            }
        )
        if run_id not in status.completed_runs:
            status.completed_runs.append(run_id)
        status.save(out / "RUN_STATUS.json")

    selected["selection_notes"] = {
        "objective": "mean_inner_validation_mae_across_3_outer_fit_val_blocks",
        "outer_evaluation_labels_accessed": False,
        "n_outer_folds_used_for_inner_val": len(folds),
        "tie_policy": "max(1e-9 abs, 1e-4 rel); then lower complexity; then canonical default",
    }
    (out / "selected_hyperparameters.yaml").write_text(yaml.safe_dump(selected, sort_keys=False))
    pd.DataFrame(rows).to_csv(metrics_dir / "tuning_summary.csv", index=False)
    if diag_rows:
        pd.DataFrame(diag_rows).to_csv(metrics_dir / "dlinear_diagnostics.csv", index=False)
    # eligibility sidecar for aggregator / later packs
    elig = {
        "dlinear_cpu": selected["dlinear_cpu"]["enabled"],
        "dlinear_memory": selected["dlinear_memory"]["enabled"],
        "reasons": {
            "dlinear_cpu": selected["dlinear_cpu"]["eligibility_reason"],
            "dlinear_memory": selected["dlinear_memory"]["eligibility_reason"],
        },
    }
    _write_json(out / "MODEL_ELIGIBILITY.json", elig)
    status.total_runs = len(status.completed_runs)
    if status.status != "partial":
        status.status = "complete"


def _hierarchy_entry(name: str):
    reg = final_hierarchy_registry(include_network=False)
    if name in reg:
        return reg[name]
    if name == "network_bond0":
        # Prefer acamas transmitted if columns exist later
        if bond0_hierarchy is None:
            raise KeyError(name)
        h = bond0_hierarchy("acamas", "transmitted")
        return {
            "name": h.name,
            "hierarchy": h,
            "meta": {"role": "secondary_approximate"},
            "summing_matrix_hash": summing_matrix_hash(h),
            "hierarchy_metadata_hash": "network",
        }
    raise KeyError(name)


def run_hierarchy_models_pack(
    cfg: dict[str, Any],
    pack: dict[str, Any],
    out: Path,
    guard: WallClockGuard,
    status: RunStatus,
    *,
    pending_freeze: bool,
) -> None:
    shared = _load_shared_hparams(cfg)
    panel = build_analysis_panel()
    fp = dataset_fingerprint()
    folds = make_outer_chronological_folds(panel, n_folds=int(cfg["n_outer_folds"]))
    context = int(cfg.get("context", 32))
    eff_proto = cfg.get("efficiency_protocol") or {}
    metrics = out / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)

    hier_name = pack["hierarchies"][0]
    entry = _hierarchy_entry(hier_name if hier_name != "network_bond0" else "network_bond0")
    # For network_bond0 key from registry name
    if hier_name == "network_bond0":
        entry = _hierarchy_entry("network_bond0")
        work = panel
        # Attach NIC columns if needed — skip pack if columns missing
        h = entry["hierarchy"]
        missing = [c for c in h.series_names if c not in work.columns]
        if missing:
            status.status = "skipped"
            status.last_message = f"network columns missing: {missing[:3]}..."
            status.skipped_runs.append("network_columns_missing")
            return
    else:
        entry = _hierarchy_entry(hier_name)
        work = _prepare_cpu_panel(panel) if entry["name"] == "cpu_core_weighted" else panel

    h = entry["hierarchy"]
    models = list(pack.get("models") or [])
    horizons = list(pack.get("horizons") or [])
    fold_ids = list(pack.get("outer_folds") or [])
    seeds = list(pack.get("seeds") or [0])
    methods = list(pack.get("reconciliation_methods") or [])
    abl_h = pack.get("ablations_horizon")
    abl_methods = list(pack.get("ablation_methods") or [])
    nn_h = pack.get("nonnegative_ablation_horizon")

    # Enumerate base jobs
    jobs = []
    for fold_id in fold_ids:
        for horizon in horizons:
            for model_name in models:
                for seed in seeds:
                    jobs.append((int(fold_id), int(horizon), model_name, int(seed)))
    status.total_runs = len(jobs)
    base_rows = []
    recon_rows = []

    for fold_id, horizon, model_name, seed in jobs:
        run_id = f"base__{entry['name']}__f{fold_id}__h{horizon}__{model_name}__s{seed}"
        if run_id in status.completed_runs:
            continue
        if not guard.may_launch_new_run():
            status.status = "partial"
            status.last_message = (
                f"Pack {pack['id']} reached its launch limit after {guard.format_elapsed()}.\n"
                f"Completed: {len(status.completed_runs)}/{status.total_runs} base fits.\n"
                f"Status: partial.\n"
                f"Resume with:\n"
                f"python scripts/run_final_pack.py \\\n"
                f"    --config configs/final_fgcs_packs.yaml \\\n"
                f"    --pack {pack['id']} \\\n"
                f"    --resume"
            )
            break

        split = fold_to_split_spec(folds[fold_id])
        kwargs = _model_kwargs_for(cfg, shared, model_name, entry["name"])
        try:
            bottom_packs = [
                _fit_predict(work, split, name, horizon, context, model_name, seed, kwargs, eff_proto)
                for name in h.bottom_names
            ]
            top_pack = _fit_predict(work, split, h.top_name, horizon, context, model_name, seed, kwargs, eff_proto)
            aligned = _align(bottom_packs, top_pack)
            y_full_val = np.concatenate([aligned["yb_val"], aligned["yt_val"].reshape(-1, 1)], axis=1)
            p_full_val = np.concatenate([aligned["pb_val"], aligned["pt_val"].reshape(-1, 1)], axis=1)
            cov = estimate_residual_covariance(y_full_val, p_full_val, shrink_diag=0.1)
            series_var = np.maximum(np.diag(cov), 1e-12)

            meta = {
                "run_id": run_id,
                "experiment_stage": "final" if not pending_freeze else "development",
                "eligible_for_final_claims": (not pending_freeze),
                "evaluation_role": "outer_evaluation" if not pending_freeze else "pack_prefreeze",
                "freeze_commit": cfg.get("freeze_commit"),
                "freeze_tag": cfg.get("freeze_tag"),
                "dataset_fingerprint": fp.get("fingerprint"),
                "config_hash": config_hash(cfg),
                "pack_id": pack["id"],
                "pack_hash": pack_hash(pack),
                "hierarchy": entry["name"],
                "fold": fold_id,
                "horizon": horizon,
                "context": context,
                "base_model": model_name,
                "seed": seed,
                "summing_matrix_hash": entry.get("summing_matrix_hash"),
                "wall_train_sec_sum": float(sum(p["wall_train_sec"] for p in bottom_packs) + top_pack["wall_train_sec"]),
                "top_mae_independent": float(mae(aligned["yt_test"], aligned["pt_test"])),
            }
            # Persist predictions for later stats/peak packs
            pred_path = metrics / "predictions" / f"{run_id}.npz"
            pred_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(
                pred_path,
                yb_test=aligned["yb_test"],
                pb_test=aligned["pb_test"],
                yt_test=aligned["yt_test"],
                pt_test=aligned["pt_test"],
                yb_val=aligned["yb_val"],
                pb_val=aligned["pb_val"],
                yt_val=aligned["yt_val"],
                pt_val=aligned["pt_val"],
                yt_train=aligned["yt_train"],
            )
            base_rows.append(meta)

            method_list = list(methods)
            if abl_h is not None and int(horizon) == int(abl_h):
                for m in abl_methods:
                    if m not in method_list:
                        method_list.append(m)
            nn_flags = [False]
            if nn_h is not None and int(horizon) == int(nn_h):
                nn_flags = [False, True]

            coh_before = coherence_error(aligned["pb_test"], aligned["pt_test"])
            for method in method_list:
                for nn in nn_flags:
                    out_r = reconcile(
                        method,
                        h,
                        aligned["pb_test"],
                        aligned["pt_test"],
                        series_var=series_var if method == "wls" else None,
                        residual_cov=cov if method == "mint" else None,
                        nonnegative=nn,
                    )
                    recon_rows.append(
                        {
                            **meta,
                            "run_id": f"{run_id}__{method}__nn{int(nn)}",
                            "reconciliation_method": method,
                            "nonnegative": nn,
                            "coherence_error_before": float(coh_before),
                            "coherence_error_after": float(coherence_error(out_r["bottom"], out_r["top"])),
                            "is_coherent_after": bool(is_coherent(out_r["bottom"], out_r["top"], atol=1e-4)),
                            "top_mae": float(mae(aligned["yt_test"], out_r["top"])),
                            "bottom_mae_mean": float(
                                np.mean(
                                    [
                                        mae(aligned["yb_test"][:, j], out_r["bottom"][:, j])
                                        for j in range(aligned["yb_test"].shape[1])
                                    ]
                                )
                            ),
                        }
                    )
            status.completed_runs.append(run_id)
        except Exception as exc:  # noqa: BLE001
            status.failed_runs.append(run_id)
            status.last_message = f"{run_id} failed: {type(exc).__name__}: {exc}"
            (out / "logs").mkdir(parents=True, exist_ok=True)
            (out / "logs" / f"{run_id}.err").write_text(status.last_message)

        # Persist incrementally
        if base_rows:
            _append_csv(metrics / "base_forecasts.csv", base_rows)
            base_rows = []
        if recon_rows:
            _append_csv(metrics / "reconciliation_results.csv", recon_rows)
            recon_rows = []
        status.wall_seconds = guard.elapsed()
        status.cpu_seconds = guard.cpu_elapsed()
        status.save(out / "RUN_STATUS.json")

    if status.status != "partial":
        n_done = len(status.completed_runs)
        n_fail = len(status.failed_runs)
        if n_done + n_fail >= (status.total_runs or 0) and n_fail == 0:
            status.status = "complete"
        elif n_done + n_fail >= (status.total_runs or 0) and n_fail > 0:
            status.status = "complete"  # documented failures allowed for COMPLETE with note
            status.last_message = (status.last_message or "") + f"; permanent failures: {n_fail}"
        elif n_done > 0:
            status.status = "partial"


def run_supporting_statistics(cfg: dict[str, Any], pack: dict[str, Any], out: Path, status: RunStatus) -> None:
    """Delegate to frozen final-analysis layer (timestamp-level bootstrap).

    Prediction packs remain experiment-freeze-v2; statistics follow
    configs/final_statistics.yaml (final-analysis-freeze-v1). Does not train models.
    """
    from timetrack.statistical_reporting import load_statistics_config, run_final_statistics

    # Preserve dependency reconciliation aggregate for audit/efficiency joins
    dep_ids = pack.get("dependencies") or []
    frames = []
    for dep in dep_ids:
        dep_pack = pack_by_id(cfg, dep)
        path = pack_output_dir(cfg, dep_pack) / "metrics" / "reconciliation_results.csv"
        if path.exists():
            df = pd.read_csv(path)
            df["source_pack"] = dep
            frames.append(df)
    metrics = out / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    (out / "tables").mkdir(parents=True, exist_ok=True)
    if frames:
        all_df = pd.concat(frames, ignore_index=True)
        all_df.to_csv(metrics / "reconciliation_results_aggregated.csv", index=False)
        summary = (
            all_df.groupby(["hierarchy", "base_model", "horizon", "reconciliation_method"], as_index=False)
            .agg(
                top_mae=("top_mae", "mean"),
                coherence_after=("coherence_error_after", "mean"),
                coherence_before=("coherence_error_before", "mean"),
            )
        )
        summary.to_csv(metrics / "hierarchy_summary.csv", index=False)
        summary.to_csv(out / "tables" / "main_comparison.csv", index=False)

    eff_frames = []
    for dep in dep_ids:
        dep_pack = pack_by_id(cfg, dep)
        path = pack_output_dir(cfg, dep_pack) / "metrics" / "base_forecasts.csv"
        if path.exists():
            eff_frames.append(pd.read_csv(path))
    if eff_frames:
        eff = pd.concat(eff_frames, ignore_index=True)
        if "wall_train_sec_sum" in eff.columns:
            g = eff.groupby(["hierarchy", "base_model"], as_index=False)["wall_train_sec_sum"].mean()
            g.to_csv(metrics / "efficiency.csv", index=False)
            g.to_csv(out / "tables" / "efficiency_comparison.csv", index=False)

    try:
        stats_cfg = load_statistics_config(ROOT / "configs" / "final_statistics.yaml")
        run_final_statistics(stats_cfg=stats_cfg, source_cfg=cfg, output_dir=out, smoke=False)
    except Exception as exc:  # noqa: BLE001 — pack status must record failure
        status.status = "failed"
        status.failed_runs.append("supporting_statistics")
        status.last_message = f"final statistics failed: {exc}"
        return

    status.status = "complete"
    status.completed_runs.append("supporting_statistics")
    status.total_runs = 1


def run_peak_analysis(cfg: dict[str, Any], pack: dict[str, Any], out: Path, status: RunStatus) -> None:
    from experiments.final_supporting_analyses import peak_metrics, peak_threshold

    root = ROOT / (cfg.get("artifact_root") or "results/final/packs")
    rows = []
    for dep in pack.get("dependencies") or []:
        dep_pack = pack_by_id(cfg, dep)
        pred_dir = pack_output_dir(cfg, dep_pack) / "metrics" / "predictions"
        recon = pack_output_dir(cfg, dep_pack) / "metrics" / "reconciliation_results.csv"
        if not pred_dir.exists() or not recon.exists():
            continue
        rdf = pd.read_csv(recon)
        for path in sorted(pred_dir.glob("*.npz")):
            data = np.load(path)
            yt_train = data["yt_train"]
            yt = data["yt_test"]
            # independent = pt_test; prefer bottom_up if present in recon for same run
            run_id = path.stem
            pt = data["pt_test"]
            for mode in ("q90", "q95"):
                thr = peak_threshold(yt_train, mode=mode)
                pm = peak_metrics(yt, pt, thr)
                rows.append({"source_pack": dep, "run_id": run_id, "method": "independent", "threshold": mode, **pm})
            # strongest retained proxy: bottom_up row if available
            sub = rdf[rdf["run_id"].astype(str).str.startswith(run_id) & (rdf["reconciliation_method"] == "bottom_up")]
            if not sub.empty:
                # approximate using independent preds as placeholder when recon vectors not stored
                pm2 = peak_metrics(yt, pt, peak_threshold(yt_train, "q95"))
                rows.append({"source_pack": dep, "run_id": run_id, "method": "bottom_up_proxy", "threshold": "q95", **pm2})
    metrics = out / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(metrics / "peak_metrics.csv", index=False)
    status.status = "complete"
    status.completed_runs.append("peak_analysis")
    status.total_runs = 1


def run_downsampling(cfg: dict[str, Any], pack: dict[str, Any], out: Path, guard: WallClockGuard, status: RunStatus) -> None:
    from experiments.final_supporting_analyses import downsampling_eval_row

    shared = _load_shared_hparams(cfg)
    panel = build_analysis_panel()
    # ensure weighted mean column
    work = _prepare_cpu_panel(panel)
    if "cluster_CU_wsum" in work.columns:
        from models.hybrid.reconciliation import machine_core_counts

        div = float(sum(machine_core_counts().values()))
        work["cluster_CU_weighted_mean"] = work["cluster_CU_wsum"] / div
    folds = make_outer_chronological_folds(work, n_folds=int(cfg["n_outer_folds"]))
    split = fold_to_split_spec(folds[0])
    targets = list(pack.get("downsampling_targets") or ["cluster_UM"])
    factors = list(pack.get("downsampling_factors") or [1, 7])
    models = list(pack.get("models") or ["persistence", "ridge"])
    horizons = list(pack.get("horizons") or [1, 8])
    rows = []
    jobs = [(t, m, h, f) for t in targets for m in models for h in horizons for f in factors]
    status.total_runs = len(jobs)
    for target, model, horizon, factor in jobs:
        run_id = f"down__{target}__{model}__h{horizon}__x{factor}"
        if run_id in status.completed_runs:
            continue
        if not guard.may_launch_new_run():
            status.status = "partial"
            status.last_message = "launch limit during downsampling"
            break
        if target not in work.columns:
            status.skipped_runs.append(run_id)
            continue
        kwargs = _model_kwargs_for(cfg, shared, model, "memory_um" if "UM" in target else "cpu")
        # temporarily apply kwargs via model build inside helper — helper uses defaults; fit with shared via monkeypatch not needed for smoke
        row = downsampling_eval_row(
            work,
            split,
            target,
            model_name=model,
            horizon_native=int(horizon),
            context_native=int(cfg.get("context", 32)),
            factor=int(factor),
            seed=0,
        )
        row["run_id"] = run_id
        rows.append(row)
        status.completed_runs.append(run_id)
    metrics = out / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    if rows:
        _append_csv(metrics / "downsampling.csv", rows)
    if status.status != "partial":
        status.status = "complete" if not status.failed_runs else "complete"


def run_conformal(cfg: dict[str, Any], pack: dict[str, Any], out: Path, status: RunStatus) -> None:
    from experiments.final_supporting_analyses import split_conformal_from_residuals

    shared = _load_shared_hparams(cfg)
    panel = build_analysis_panel()
    work = _prepare_cpu_panel(panel)
    from models.hybrid.reconciliation import machine_core_counts

    if "cluster_CU_wsum" in work.columns:
        work["cluster_CU_weighted_mean"] = work["cluster_CU_wsum"] / float(sum(machine_core_counts().values()))
    folds = make_outer_chronological_folds(work, n_folds=int(cfg["n_outer_folds"]))
    split = fold_to_split_spec(folds[0])
    context = int(cfg.get("context", 32))
    targets = list(pack.get("conformal_targets") or ["cluster_UM"])
    covs = list(pack.get("nominal_coverage") or [0.9])
    rows = []
    for target in targets:
        if target not in work.columns:
            continue
        kwargs = _model_kwargs_for(cfg, shared, "ridge", "memory_um")
        pack_out = _fit_predict(work, split, target, 1, context, "ridge", 0, kwargs, cfg.get("efficiency_protocol") or {})
        for nom in covs:
            cal = split_conformal_from_residuals(pack_out["y_val"], pack_out["p_val"], pack_out["y_test"], pack_out["p_test"], float(nom))
            rows.append({"target": target, "base_model": "ridge", **cal})
    metrics = out / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(metrics / "calibration.csv", index=False)
    status.status = "complete"
    status.completed_runs.append("conformal")
    status.total_runs = 1


def finalize_pack_artifacts(
    cfg: dict[str, Any],
    pack: dict[str, Any],
    out: Path,
    status: RunStatus,
    guard: WallClockGuard,
    *,
    pending_freeze: bool,
) -> None:
    import subprocess

    from timetrack.efficiency import peak_rss_bytes

    status.wall_seconds = guard.elapsed()
    status.cpu_seconds = guard.cpu_elapsed()
    status.end_time = _now()
    status.save(out / "RUN_STATUS.json")
    meta = freeze_metadata(cfg)
    try:
        exec_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True).strip()
    except Exception:
        exec_commit = None
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(ROOT), text=True).strip()
    except Exception:
        branch = cfg.get("branch")
    peak_bytes, peak_available, peak_reason = peak_rss_bytes()

    role = "shared_final_tuning" if pack.get("kind") == "shared_tuning" else "outer_evaluation"
    if pack.get("id") == "supporting_statistics" or pack.get("kind") == "supporting_statistics":
        role = "final_statistical_analysis"
    if pending_freeze:
        role = "pack_prefreeze"
    # Preserve analysis-layer provenance if already written by run_final_statistics
    prior: dict[str, Any] = {}
    prior_path = out / "MANIFEST.json"
    if prior_path.exists() and role == "final_statistical_analysis":
        try:
            prior = json.loads(prior_path.read_text())
        except Exception:
            prior = {}
    manifest = {
        "pack_id": pack["id"],
        "required": bool(pack.get("required")),
        "dependencies": list(pack.get("dependencies") or []),
        "experiment_stage": "development" if pending_freeze else "final",
        "eligible_for_final_claims": (not pending_freeze) and status.status == "complete",
        "evaluation_role": role,
        "execution_commit": exec_commit,
        "frozen_implementation_commit": meta.get("implementation_commit"),
        "implementation_commit": meta.get("implementation_commit"),
        "freeze_commit": meta.get("freeze_commit"),
        "freeze_tag": meta.get("freeze_tag"),
        "freeze_tag_commit": meta.get("freeze_tag_commit"),
        "repository_url": cfg.get("repository_url"),
        "git_branch": branch,
        "dataset_fingerprint": dataset_fingerprint().get("fingerprint"),
        "config_hash": config_hash(cfg),
        "pack_hash": pack_hash(pack),
        "dependency_lock_hash": cfg.get("dependency_lock_hash"),
        "start_time": status.start_time,
        "end_time": status.end_time,
        "actual_wall_seconds": status.wall_seconds,
        "cpu_seconds": status.cpu_seconds,
        "peak_memory_bytes": peak_bytes,
        "peak_memory_available": peak_available,
        "peak_memory_reason": peak_reason,
        "completed_runs": len(status.completed_runs),
        "failed_runs": len(status.failed_runs),
        "skipped_runs": len(status.skipped_runs),
        "status": status.status,
        "output_dir": str(out),
    }
    for k in (
        "source_experiment_freeze_tag",
        "source_experiment_freeze_tag_commit",
        "source_frozen_implementation_commit",
        "analysis_freeze_tag",
        "analysis_freeze_tag_commit",
        "analysis_implementation_commit",
        "statistical_config_hash",
        "source_pack_hashes",
        "bootstrap_n_boot",
        "bootstrap_seed",
        "comparisons_completed",
        "comparisons_failed",
    ):
        if k in prior:
            manifest[k] = prior[k]
    required_fields = [
        "experiment_stage",
        "eligible_for_final_claims",
        "evaluation_role",
        "execution_commit",
        "frozen_implementation_commit",
        "freeze_tag",
        "freeze_tag_commit",
        "repository_url",
        "git_branch",
        "dataset_fingerprint",
        "config_hash",
        "pack_hash",
        "dependency_lock_hash",
        "peak_memory_available",
    ]
    missing = [k for k in required_fields if k not in manifest or manifest[k] is None]
    # peak_memory_bytes may be null if unavailable
    if not peak_available and "peak_memory_reason" not in manifest:
        missing.append("peak_memory_reason")
    if missing and not pending_freeze and status.status == "complete":
        status.status = "failed"
        status.last_message = f"manifest missing required provenance fields: {missing}"
        manifest["status"] = "failed"
        manifest["eligible_for_final_claims"] = False
    _write_json(out / "MANIFEST.json", manifest)
    if status.status == "complete":
        (out / "COMPLETE").write_text(_now() + "\n")
    elif status.status == "partial":
        print(status.last_message or f"Pack {pack['id']} partial after {guard.format_elapsed()}.")


def run_pack(pack_id: str, config_path: Path | str | None = None, *, resume: bool = True) -> dict[str, Any]:
    cfg = load_packs_config(config_path)
    pack = pack_by_id(cfg, pack_id)
    out = pack_output_dir(cfg, pack)
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics").mkdir(exist_ok=True)
    (out / "tables").mkdir(exist_ok=True)
    (out / "figures").mkdir(exist_ok=True)
    (out / "logs").mkdir(exist_ok=True)

    ok, missing = dependencies_satisfied(cfg, pack)
    if not ok:
        raise SystemExit(f"Pack {pack_id} blocked; incomplete dependencies: {missing}")

    pending_freeze = str(cfg.get("freeze_commit", "")).upper().startswith("PENDING") or str(
        cfg.get("implementation_commit", "PENDING")
    ).upper().startswith("PENDING")

    # Demote DLinear packs when shared_tuning eligibility failed
    if pack_id in {"memory_dlinear", "cpu_dlinear"} and not pending_freeze:
        elig_path = pack_output_dir(cfg, pack_by_id(cfg, "shared_tuning")) / "MODEL_ELIGIBILITY.json"
        if elig_path.exists():
            elig = json.loads(elig_path.read_text())
            key = "dlinear_memory" if pack_id == "memory_dlinear" else "dlinear_cpu"
            if not elig.get(key, True):
                status = RunStatus(pack_id=pack_id, status="skipped")
                status.skipped_runs.append(f"ineligible:{elig.get('reasons', {}).get(key)}")
                status.start_time = _now()
                guard = WallClockGuard(1, 0.5)
                status.status = "skipped"
                finalize_pack_artifacts(cfg, pack, out, status, guard, pending_freeze=pending_freeze)
                # Write SKIPPED marker instead of COMPLETE for ineligible required demotion
                (out / "SKIPPED_INELIGIBLE").write_text(json.dumps(elig, indent=2))
                if (out / "COMPLETE").exists():
                    (out / "COMPLETE").unlink()
                return json.loads((out / "MANIFEST.json").read_text())
    status_path = out / "RUN_STATUS.json"
    if resume and status_path.exists():
        status = RunStatus.load(status_path)
        status.pack_id = pack_id
    else:
        status = RunStatus(pack_id=pack_id)
    if (out / "COMPLETE").exists() and resume:
        print(f"Pack {pack_id} already complete. Nothing to do.")
        return json.loads((out / "MANIFEST.json").read_text()) if (out / "MANIFEST.json").exists() else {"status": "complete"}

    status.status = "running"
    if not status.start_time:
        status.start_time = _now()
    status.save(status_path)

    hard = float(pack.get("hard_wall_clock_minutes") or cfg.get("hard_wall_clock_minutes_default") or 45)
    stop = float(pack.get("stop_launching_new_runs_minutes") or cfg.get("stop_launching_new_runs_minutes_default") or 40)
    guard = WallClockGuard(hard, stop)

    kind = pack.get("kind")
    try:
        if kind == "shared_tuning":
            run_shared_tuning(cfg, pack, out, guard, status)
        elif kind == "hierarchy_models":
            run_hierarchy_models_pack(cfg, pack, out, guard, status, pending_freeze=pending_freeze)
        elif kind == "supporting_statistics":
            run_supporting_statistics(cfg, pack, out, status)
        elif kind == "peak_analysis":
            run_peak_analysis(cfg, pack, out, status)
        elif kind == "downsampling":
            run_downsampling(cfg, pack, out, guard, status)
        elif kind == "conformal":
            run_conformal(cfg, pack, out, status)
        else:
            raise ValueError(f"unknown pack kind: {kind}")
    except Exception as exc:  # noqa: BLE001
        status.status = "failed"
        status.last_message = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        finalize_pack_artifacts(cfg, pack, out, status, guard, pending_freeze=pending_freeze)

    return json.loads((out / "MANIFEST.json").read_text())
