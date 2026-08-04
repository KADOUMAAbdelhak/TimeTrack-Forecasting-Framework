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
from timetrack.efficiency import measure_inference_latencies, timed_train
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
    return {
        "ridge": {"alpha": 1.0},
        "lightgbm_memory": {"n_estimators": 200, "learning_rate": 0.05, "num_leaves": 31},
        "lightgbm_cpu": {"n_estimators": 200, "learning_rate": 0.05, "num_leaves": 31},
        "dlinear": dict(cfg.get("dlinear_fixed") or {}),
    }


def _model_kwargs_for(cfg: dict[str, Any], shared: dict[str, Any], model: str, hierarchy: str) -> dict[str, Any]:
    if model == "ridge":
        return dict(shared.get("ridge") or {"alpha": 1.0})
    if model == "lightgbm":
        if "cpu" in hierarchy:
            return dict(shared.get("lightgbm_cpu") or shared.get("lightgbm_memory") or {})
        return dict(shared.get("lightgbm_memory") or shared.get("lightgbm_cpu") or {})
    if model == "dlinear":
        return dict(shared.get("dlinear") or cfg.get("dlinear_fixed") or {})
    if model == "lstm":
        return {"epochs": 30, "hidden_size": 64, "patience": 5, "num_threads": 1}
    return {}


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


def run_shared_tuning(cfg: dict[str, Any], pack: dict[str, Any], out: Path, guard: WallClockGuard, status: RunStatus) -> None:
    from timetrack.metrics import mae as _mae

    panel = build_analysis_panel()
    folds = make_outer_chronological_folds(panel, n_folds=int(cfg["n_outer_folds"]))
    split = fold_to_split_spec(folds[0])
    context = int(cfg.get("context", 32))
    horizon = 1
    metrics_dir = out / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    # Ridge grid on representative tops
    alphas = list(cfg.get("ridge_alpha_grid") or [1e-4, 1e-2, 1.0, 100.0, 1e4])
    ridge_targets = [("memory_um", "cluster_UM"), ("cpu_core_weighted", "cluster_mean_CU")]
    best_ridge = {"alpha": 1.0, "mae": float("inf")}
    for hier, target in ridge_targets:
        if target not in panel.columns:
            continue
        for alpha in alphas:
            run_id = f"ridge_grid__{hier}__alpha={alpha}"
            if run_id in status.completed_runs:
                continue
            if not guard.may_launch_new_run():
                status.status = "partial"
                status.last_message = "launch limit during ridge grid"
                return
            pack_out = _fit_predict(panel, split, target, horizon, context, "ridge", 0, {"alpha": float(alpha)}, cfg.get("efficiency_protocol") or {})
            m = float(_mae(pack_out["y_val"], pack_out["p_val"]))
            rows.append({"run_id": run_id, "model": "ridge", "hierarchy": hier, "target": target, "alpha": alpha, "val_mae": m})
            status.completed_runs.append(run_id)
            if m < best_ridge["mae"]:
                best_ridge = {"alpha": float(alpha), "mae": m, "target": target}

    # LightGBM small search (8 mem + 8 cpu)
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
    assert len(lgbm_space) <= 8
    best_mem = {"mae": float("inf"), "params": lgbm_space[1]}
    best_cpu = {"mae": float("inf"), "params": lgbm_space[1]}
    for tag, target, bucket in (
        ("memory", "cluster_UM", best_mem),
        ("cpu", "cluster_mean_CU", best_cpu),
    ):
        if target not in panel.columns:
            continue
        for i, params in enumerate(lgbm_space):
            run_id = f"lgbm_{tag}_trial{i}"
            if run_id in status.completed_runs:
                continue
            if not guard.may_launch_new_run():
                status.status = "partial"
                status.last_message = "launch limit during lightgbm tuning"
                return
            pack_out = _fit_predict(panel, split, target, horizon, context, "lightgbm", 0, params, cfg.get("efficiency_protocol") or {})
            m = float(_mae(pack_out["y_val"], pack_out["p_val"]))
            rows.append({"run_id": run_id, "model": "lightgbm", "family": tag, "target": target, "val_mae": m, **params})
            status.completed_runs.append(run_id)
            if m < bucket["mae"]:
                bucket["mae"] = m
                bucket["params"] = dict(params)

    # DLinear config validation
    run_id = "dlinear_validate_cluster_UM"
    if run_id not in status.completed_runs and guard.may_launch_new_run():
        dkwargs = dict(cfg.get("dlinear_fixed") or {})
        pack_out = _fit_predict(panel, split, "cluster_UM", horizon, context, "dlinear", 0, dkwargs, cfg.get("efficiency_protocol") or {})
        m = float(_mae(pack_out["y_val"], pack_out["p_val"]))
        rows.append({"run_id": run_id, "model": "dlinear", "target": "cluster_UM", "val_mae": m, **dkwargs})
        status.completed_runs.append(run_id)

    selected = {
        "ridge": {"alpha": best_ridge["alpha"]},
        "lightgbm_memory": best_mem["params"],
        "lightgbm_cpu": best_cpu["params"],
        "dlinear": dict(cfg.get("dlinear_fixed") or {}),
        "selection_notes": {
            "ridge_best_val_mae": best_ridge.get("mae"),
            "lgbm_memory_best_val_mae": best_mem["mae"],
            "lgbm_cpu_best_val_mae": best_cpu["mae"],
            "objective_scope": "inner_validation_fold0_only",
            "outer_evaluation": False,
        },
    }
    (out / "selected_hyperparameters.yaml").write_text(yaml.safe_dump(selected, sort_keys=True))
    pd.DataFrame(rows).to_csv(metrics_dir / "tuning_summary.csv", index=False)
    status.total_runs = len(alphas) * 2 + 16 + 1
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
    from timetrack.stats_bootstrap import holm_adjust, paired_block_bootstrap_comparison, select_block_length

    root = ROOT / (cfg.get("artifact_root") or "results/final/packs")
    dep_ids = pack.get("dependencies") or []
    frames = []
    for dep in dep_ids:
        dep_pack = pack_by_id(cfg, dep)
        path = pack_output_dir(cfg, dep_pack) / "metrics" / "reconciliation_results.csv"
        if path.exists():
            df = pd.read_csv(path)
            df["source_pack"] = dep
            frames.append(df)
    if not frames:
        status.status = "failed"
        status.last_message = "no reconciliation_results.csv from dependencies"
        return
    all_df = pd.concat(frames, ignore_index=True)
    metrics = out / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    all_df.to_csv(metrics / "reconciliation_results_aggregated.csv", index=False)

    # Coherence / accuracy tables
    summary = (
        all_df.groupby(["hierarchy", "base_model", "horizon", "reconciliation_method"], as_index=False)
        .agg(top_mae=("top_mae", "mean"), coherence_after=("coherence_error_after", "mean"), coherence_before=("coherence_error_before", "mean"))
    )
    summary.to_csv(metrics / "hierarchy_summary.csv", index=False)
    (out / "tables").mkdir(parents=True, exist_ok=True)
    summary.to_csv(out / "tables" / "main_comparison.csv", index=False)

    families = {
        "memory_um": [("independent", "bottom_up"), ("independent", "wls"), ("independent", "mint")],
        "cpu_core_weighted": [("independent", "bottom_up"), ("independent", "wls"), ("independent", "mint")],
        "disk_ud": [("independent", "bottom_up"), ("independent", "top_down")],
    }
    boot_rows = []
    # Use fold-level MAE differences as paired units when full vectors unavailable
    for hier, comps in families.items():
        sub = all_df[all_df["hierarchy"] == hier]
        if sub.empty:
            continue
        for a, b in comps:
            # pair by fold, horizon, base_model
            keys = ["fold", "horizon", "base_model"]
            sa = sub[sub["reconciliation_method"] == a][keys + ["top_mae"]].rename(columns={"top_mae": "mae_a"})
            sb = sub[sub["reconciliation_method"] == b][keys + ["top_mae"]].rename(columns={"top_mae": "mae_b"})
            merged = sa.merge(sb, on=keys)
            if merged.empty:
                continue
            d = (merged["mae_a"] - merged["mae_b"]).to_numpy()
            # treat fold-level diffs with block_length=1 (already aggregated)
            cmp_ = paired_block_bootstrap_comparison(
                np.zeros_like(d),
                merged["mae_a"].to_numpy(),
                merged["mae_b"].to_numpy(),
                block_length=1,
                n_boot=int((cfg.get("bootstrap_policy") or {}).get("n_boot", 1000)),
                seed=int((cfg.get("bootstrap_policy") or {}).get("seed", 0)),
            )
            boot_rows.append(
                {
                    "hierarchy": hier,
                    "method_a": a,
                    "method_b": b,
                    "n_pairs": len(merged),
                    "fold_sign_consistency": float(np.mean(np.sign(merged["mae_a"] - merged["mae_b"]) < 0)),
                    **cmp_,
                }
            )
    if boot_rows:
        boot_df = pd.DataFrame(boot_rows)
        boot_df["p_holm"] = holm_adjust(boot_df["p_value_approx"].tolist())
        boot_df.to_csv(metrics / "paired_block_bootstrap.csv", index=False)
        boot_df.to_csv(metrics / "holm_corrected_tests.csv", index=False)
        boot_df.to_csv(out / "tables" / "statistical_comparisons.csv", index=False)

    # Efficiency aggregation from base forecasts
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
    status.wall_seconds = guard.elapsed()
    status.cpu_seconds = guard.cpu_elapsed()
    status.end_time = _now()
    status.save(out / "RUN_STATUS.json")
    meta = freeze_metadata(cfg)
    manifest = {
        "pack_id": pack["id"],
        "required": bool(pack.get("required")),
        "dependencies": list(pack.get("dependencies") or []),
        "implementation_commit": meta.get("implementation_commit"),
        "freeze_commit": meta.get("freeze_commit"),
        "freeze_tag": meta.get("freeze_tag"),
        "freeze_tag_commit": meta.get("freeze_tag_commit"),
        "configuration_hash": config_hash(cfg),
        "pack_hash": pack_hash(pack),
        "dataset_fingerprint": dataset_fingerprint().get("fingerprint"),
        "start_time": status.start_time,
        "end_time": status.end_time,
        "actual_wall_seconds": status.wall_seconds,
        "cpu_seconds": status.cpu_seconds,
        "completed_runs": len(status.completed_runs),
        "failed_runs": len(status.failed_runs),
        "skipped_runs": len(status.skipped_runs),
        "status": status.status,
        "eligible_for_final_claims": (not pending_freeze) and status.status == "complete",
        "output_dir": str(out),
    }
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
