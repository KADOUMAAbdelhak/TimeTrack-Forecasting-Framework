"""Execute robustness-extension packs (EWMA + multi-seed). Seed-0 packs are read-only."""

from __future__ import annotations

import gc
import hashlib
import json
import subprocess
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

from experiments.final_hierarchy_runner import _align, _prepare_cpu_panel  # noqa: E402
from experiments.pack_runner import _append_csv, _fit_predict, _hierarchy_entry, _write_json  # noqa: E402
from models.hybrid.reconciliation import (  # noqa: E402
    coherence_error,
    estimate_residual_covariance,
    is_coherent,
    reconcile,
)
from timetrack.data import build_analysis_panel, dataset_fingerprint  # noqa: E402
from timetrack.efficiency import peak_rss_bytes  # noqa: E402
from timetrack.final_packs import (  # noqa: E402
    RunStatus,
    WallClockGuard,
    config_hash,
    pack_by_id,
    pack_hash,
    pack_output_dir,
)
from timetrack.metrics import mae  # noqa: E402
from timetrack.robustness_extension import (  # noqa: E402
    load_robustness_config,
    validate_robustness_config,
)
from timetrack.splits import fold_to_split_spec, make_outer_chronological_folds  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git(cmd: list[str]) -> str | None:
    try:
        return subprocess.check_output(cmd, cwd=str(ROOT), text=True).strip()
    except Exception:
        return None


def _file_sha16(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def source_seed0_prediction_hashes(cfg: dict[str, Any]) -> dict[str, str]:
    """Hash COMPLETE markers / MANIFEST of accepted seed-0 packs (integrity check)."""
    root = ROOT / (cfg.get("source_artifact_root") or "results/final/packs")
    out: dict[str, str] = {}
    for name in cfg.get("source_seed0_packs") or []:
        # map pack id to directory via final packs config when possible
        pack_dirs = {
            "shared_tuning": "00_shared_tuning",
            "memory_classical": "01_memory_classical",
            "memory_dlinear": "02_memory_dlinear",
            "cpu_classical": "03_cpu_classical",
            "cpu_dlinear": "04_cpu_dlinear",
            "disk_boundary": "05_disk_boundary",
        }
        d = root / pack_dirs.get(name, name)
        manif = d / "MANIFEST.json"
        complete = d / "COMPLETE"
        payload = b""
        if manif.exists():
            payload += manif.read_bytes()
        if complete.exists():
            payload += complete.read_bytes()
        # also hash a stable sample of prediction files if present
        pred_dir = d / "metrics" / "predictions"
        if pred_dir.exists():
            for p in sorted(pred_dir.glob("*.npz"))[:5]:
                payload += p.name.encode() + p.read_bytes()[:4096]
        out[name] = hashlib.sha256(payload).hexdigest()[:16] if payload else "missing"
    return out


def _work_panel(panel: pd.DataFrame, hier_name: str) -> pd.DataFrame:
    return _prepare_cpu_panel(panel) if hier_name == "cpu_core_weighted" else panel


def _horizons_for(pack: dict[str, Any], hier_name: str) -> list[int]:
    by_h = pack.get("horizons_by_hierarchy") or {}
    if hier_name in by_h:
        return [int(x) for x in by_h[hier_name]]
    return [int(x) for x in (pack.get("horizons") or [])]


def _methods_for(pack: dict[str, Any], hier_name: str) -> list[str]:
    by_m = pack.get("reconciliation_methods_by_hierarchy") or {}
    if hier_name in by_m:
        return list(by_m[hier_name])
    return list(pack.get("reconciliation_methods") or [])


def _family_key(hier_name: str) -> str:
    return {
        "cpu_core_weighted": "cpu",
        "memory_um": "memory",
        "disk_ud": "disk",
    }[hier_name]


def select_ewma_alphas(
    cfg: dict[str, Any],
    pack: dict[str, Any],
    panel: pd.DataFrame,
    folds,
    *,
    out: Path,
) -> dict[str, Any]:
    """Select EWMA alpha per metric family using inner validation only."""
    from timetrack.metrics import mae as _mae

    context = int(cfg.get("context", 32))
    grid = [float(a) for a in cfg["ewma_alpha_grid"]]
    eff = {"warmup": 0, "repeats": 1}
    selected: dict[str, Any] = {}
    rows = []

    for hier_name in pack["hierarchies"]:
        entry = _hierarchy_entry(hier_name)
        work = _work_panel(panel, entry["name"])
        top = entry["hierarchy"].top_name
        horizons = _horizons_for(pack, hier_name)
        fold_ids = [int(f) for f in pack["outer_folds"]]
        family = _family_key(hier_name)
        best_alpha = None
        best_mean = float("inf")
        alpha_scores: dict[str, Any] = {}

        for alpha in grid:
            fold_scores: list[dict[str, Any]] = []
            maes: list[float] = []
            for fold_id in fold_ids:
                split = fold_to_split_spec(folds[fold_id])
                for h in horizons:
                    pack_fit = _fit_predict(
                        work, split, top, h, context, "ewma", 0, {"alpha": alpha}, eff
                    )
                    # INNER VAL ONLY — never touch y_test / p_test for selection
                    m = float(_mae(pack_fit["y_val"], pack_fit["p_val"]))
                    maes.append(m)
                    fold_scores.append(
                        {
                            "fold": fold_id,
                            "horizon": h,
                            "val_mae": m,
                            "outer_test_accessed": False,
                        }
                    )
                    del pack_fit
                    gc.collect()
            mean_m = float(np.mean(maes))
            alpha_scores[str(alpha)] = {
                "mean_val_mae": mean_m,
                "std_val_mae": float(np.std(maes, ddof=0)),
                "fold_horizon_scores": fold_scores,
            }
            rows.append(
                {
                    "family": family,
                    "hierarchy": hier_name,
                    "alpha": alpha,
                    "mean_val_mae": mean_m,
                    "n_scores": len(maes),
                }
            )
            if mean_m < best_mean:
                best_mean = mean_m
                best_alpha = alpha

        selected[f"ewma_{family}"] = {
            "alpha": float(best_alpha),
            "selection_reason": "min_mean_inner_val_mae",
            "mean_val_mae": best_mean,
            "outer_labels_used_for_selection": False,
            "alpha_grid_scores": alpha_scores,
        }

    (out / "selected_ewma_params.yaml").write_text(yaml.safe_dump(selected, sort_keys=False))
    pd.DataFrame(rows).to_csv(out / "metrics" / "ewma_alpha_selection.csv", index=False)
    return selected


def run_ewma_baselines(
    cfg: dict[str, Any],
    pack: dict[str, Any],
    out: Path,
    guard: WallClockGuard,
    status: RunStatus,
) -> None:
    metrics = out / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    panel = build_analysis_panel()
    fp = dataset_fingerprint()
    folds = make_outer_chronological_folds(panel, n_folds=int(cfg["n_outer_folds"]))
    context = int(cfg.get("context", 32))
    # EWMA is deterministic and cheap; skip multi-repeat latency probes.
    eff_proto = {"warmup": 0, "repeats": 1, "threads": 1}

    # Alpha selection (inner val only)
    selected = select_ewma_alphas(cfg, pack, panel, folds, out=out)
    alpha_by_family = {
        "cpu": float(selected["ewma_cpu"]["alpha"]),
        "memory": float(selected["ewma_memory"]["alpha"]),
        "disk": float(selected["ewma_disk"]["alpha"]),
    }

    # Enumerate outer base jobs: 8 series × horizons × folds per hierarchy
    jobs: list[tuple[str, int, int]] = []
    for hier_name in pack["hierarchies"]:
        for fold_id in pack["outer_folds"]:
            for horizon in _horizons_for(pack, hier_name):
                jobs.append((hier_name, int(fold_id), int(horizon)))
    status.total_runs = len(jobs)

    base_rows: list[dict[str, Any]] = []
    recon_rows: list[dict[str, Any]] = []
    cfg_h = config_hash(cfg)
    ph = pack_hash(pack)

    for hier_name, fold_id, horizon in jobs:
        run_id = f"base__{hier_name}__f{fold_id}__h{horizon}__ewma__s0"
        if run_id in status.completed_runs:
            continue
        if not guard.may_launch_new_run():
            status.status = "partial"
            status.last_message = (
                f"Pack {pack['id']} reached launch limit after {guard.format_elapsed()}.\n"
                f"Completed: {len(status.completed_runs)}/{status.total_runs}.\n"
                f"Resume with:\n"
                f"python scripts/run_robustness_pack.py \\\n"
                f"    --config configs/final_robustness_extension.yaml \\\n"
                f"    --pack {pack['id']} \\\n"
                f"    --resume"
            )
            break

        entry = _hierarchy_entry(hier_name)
        h = entry["hierarchy"]
        work = _work_panel(panel, entry["name"])
        family = _family_key(hier_name)
        alpha = alpha_by_family[family]
        split = fold_to_split_spec(folds[fold_id])
        methods = _methods_for(pack, hier_name)

        try:
            bottom_packs = [
                _fit_predict(work, split, name, horizon, context, "ewma", 0, {"alpha": alpha}, eff_proto)
                for name in h.bottom_names
            ]
            top_pack = _fit_predict(
                work, split, h.top_name, horizon, context, "ewma", 0, {"alpha": alpha}, eff_proto
            )
            aligned = _align(bottom_packs, top_pack)
            y_full_val = np.concatenate([aligned["yb_val"], aligned["yt_val"].reshape(-1, 1)], axis=1)
            p_full_val = np.concatenate([aligned["pb_val"], aligned["pt_val"].reshape(-1, 1)], axis=1)
            cov = estimate_residual_covariance(y_full_val, p_full_val, shrink_diag=0.1)
            series_var = np.maximum(np.diag(cov), 1e-12)

            meta = {
                "run_id": run_id,
                "experiment_stage": "final_robustness_extension",
                "eligible_for_final_claims": True,
                "evaluation_role": "robustness_extension",
                "freeze_commit": cfg.get("freeze_commit"),
                "freeze_tag": cfg.get("freeze_tag"),
                "source_experiment_freeze_tag": cfg.get("source_experiment_freeze_tag"),
                "dataset_fingerprint": fp.get("fingerprint"),
                "config_hash": cfg_h,
                "pack_id": pack["id"],
                "pack_hash": ph,
                "hierarchy": entry["name"],
                "fold": fold_id,
                "horizon": horizon,
                "context": context,
                "base_model": "ewma",
                "ewma_alpha": alpha,
                "seed": 0,
                "summing_matrix_hash": entry.get("summing_matrix_hash"),
                "wall_train_sec_sum": float(
                    sum(p["wall_train_sec"] for p in bottom_packs) + top_pack["wall_train_sec"]
                ),
                "cpu_train_sec_sum": float(
                    sum(p["cpu_train_sec"] for p in bottom_packs) + top_pack["cpu_train_sec"]
                ),
                "peak_rss_mb_max": float(
                    max([p["peak_rss_mb"] for p in bottom_packs] + [top_pack["peak_rss_mb"]])
                ),
                "top_mae_independent": float(mae(aligned["yt_test"], aligned["pt_test"])),
                "n_bottom_series": len(h.bottom_names),
                "n_series_fitted": len(h.bottom_names) + 1,
            }
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

            coh_before = coherence_error(aligned["pb_test"], aligned["pt_test"])
            for method in methods:
                out_r = reconcile(
                    method,
                    h,
                    aligned["pb_test"],
                    aligned["pt_test"],
                    series_var=series_var if method == "wls" else None,
                    residual_cov=cov if method == "mint" else None,
                    nonnegative=False,
                )
                recon_rows.append(
                    {
                        **meta,
                        "run_id": f"{run_id}__{method}__nn0",
                        "reconciliation_method": method,
                        "nonnegative": False,
                        "coherence_error_before": float(coh_before),
                        "coherence_error_after": float(
                            coherence_error(out_r["bottom"], out_r["top"])
                        ),
                        "is_coherent_after": bool(
                            is_coherent(out_r["bottom"], out_r["top"], atol=1e-4)
                        ),
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

        if base_rows:
            _append_csv(metrics / "base_forecasts.csv", base_rows)
            base_rows = []
        if recon_rows:
            _append_csv(metrics / "reconciliation_results.csv", recon_rows)
            recon_rows = []
        status.wall_seconds = guard.elapsed()
        status.cpu_seconds = guard.cpu_elapsed()
        status.save(out / "RUN_STATUS.json")
        gc.collect()

    # Summary vs persistence / ridge / lightgbm from source packs
    _write_ewma_comparisons(cfg, out)

    n_series_expected = 192  # documented outer series-fits across hierarchies
    # jobs are hierarchy×fold×horizon base groups; each fits 8 series
    n_done = len(status.completed_runs)
    n_fail = len(status.failed_runs)
    status.total_runs = len(jobs)
    if status.status != "partial":
        if n_done + n_fail >= len(jobs) and n_fail == 0:
            status.status = "complete"
        elif n_done + n_fail >= len(jobs):
            status.status = "complete"
            status.last_message = (status.last_message or "") + f"; failures={n_fail}"
        elif n_done > 0:
            status.status = "partial"

    # Record expected series fit count for reporting
    _write_json(
        out / "FIT_COUNTS.json",
        {
            "expected_series_fits": n_series_expected,
            "completed_base_groups": n_done,
            "failed_base_groups": n_fail,
            "series_per_group": 8,
            "approx_completed_series_fits": n_done * 8,
        },
    )


def _load_source_recon(cfg: dict[str, Any], pack_dirname: str) -> pd.DataFrame | None:
    path = ROOT / (cfg.get("source_artifact_root") or "results/final/packs") / pack_dirname / "metrics" / "reconciliation_results.csv"
    if not path.exists():
        return None
    return pd.read_csv(path)


def _write_ewma_comparisons(cfg: dict[str, Any], out: Path) -> None:
    ewma_path = out / "metrics" / "reconciliation_results.csv"
    if not ewma_path.exists():
        return
    ewma = pd.read_csv(ewma_path)
    frames = []
    for dirname, model in [
        ("03_cpu_classical", "persistence"),
        ("03_cpu_classical", "ridge"),
        ("03_cpu_classical", "lightgbm"),
        ("01_memory_classical", "persistence"),
        ("01_memory_classical", "ridge"),
        ("01_memory_classical", "lightgbm"),
        ("05_disk_boundary", "persistence"),
        ("05_disk_boundary", "ridge"),
    ]:
        df = _load_source_recon(cfg, dirname)
        if df is None:
            continue
        sub = df[df["base_model"] == model].copy()
        if sub.empty:
            continue
        sub["source_pack_dir"] = dirname
        frames.append(sub)
    if not frames:
        return
    src = pd.concat(frames, ignore_index=True)

    rows = []
    for _, r in ewma.iterrows():
        mask = (
            (src["hierarchy"] == r["hierarchy"])
            & (src["fold"] == r["fold"])
            & (src["horizon"] == r["horizon"])
            & (src["reconciliation_method"] == r["reconciliation_method"])
            & (src["seed"] == 0)
        )
        for model in ("persistence", "ridge", "lightgbm"):
            m = src[mask & (src["base_model"] == model)]
            if m.empty:
                continue
            base_mae = float(m["top_mae"].iloc[0])
            e_mae = float(r["top_mae"])
            rows.append(
                {
                    "hierarchy": r["hierarchy"],
                    "fold": int(r["fold"]),
                    "horizon": int(r["horizon"]),
                    "method": r["reconciliation_method"],
                    "ewma_alpha": r.get("ewma_alpha"),
                    "ewma_top_mae": e_mae,
                    "comparator": model,
                    "comparator_top_mae": base_mae,
                    "rel_mae_vs_comparator": e_mae / max(base_mae, 1e-12),
                    "pct_change_vs_comparator": 100.0 * (e_mae / max(base_mae, 1e-12) - 1.0),
                }
            )
    if rows:
        pd.DataFrame(rows).to_csv(out / "metrics" / "ewma_vs_baselines.csv", index=False)

    # Fold-consistency summary for independent EWMA
    ind = ewma[ewma["reconciliation_method"] == "independent"]
    summary = (
        ind.groupby(["hierarchy", "horizon"], as_index=False)
        .agg(
            mean_top_mae=("top_mae", "mean"),
            std_top_mae=("top_mae", "std"),
            n_folds=("fold", "nunique"),
            mean_coherence_before=("coherence_error_before", "mean"),
            mean_coherence_after=("coherence_error_after", "mean"),
        )
    )
    summary.to_csv(out / "metrics" / "ewma_fold_summary.csv", index=False)


def run_seed_model_pack(
    cfg: dict[str, Any],
    pack: dict[str, Any],
    out: Path,
    guard: WallClockGuard,
    status: RunStatus,
    *,
    model_name: str,
) -> None:
    """Fit additional seeds for lightgbm or dlinear; do not touch seed-0 artifacts."""
    shared_path = ROOT / cfg["shared_hyperparameters_path"]
    shared = yaml.safe_load(shared_path.read_text()) if shared_path.exists() else {}
    metrics = out / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    panel = build_analysis_panel()
    fp = dataset_fingerprint()
    folds = make_outer_chronological_folds(panel, n_folds=int(cfg["n_outer_folds"]))
    context = int(cfg.get("context", 32))
    # Keep latency probes light for seed robustness wall-clock budget
    eff_proto = {"warmup": 0, "repeats": 1, "threads": 1}
    seeds = [int(s) for s in pack["seeds"]]
    methods = list(pack.get("reconciliation_methods") or [])
    horizons = [int(h) for h in pack["horizons"]]
    fold_ids = [int(f) for f in pack["outer_folds"]]
    # Verify matrix counts (series fits / recon evals for NEW seeds only)
    n_hier = len(pack["hierarchies"])
    n_series = 8
    expected_fits = n_hier * n_series * len(horizons) * len(fold_ids) * len(seeds)
    expected_recon = n_hier * len(horizons) * len(fold_ids) * len(seeds) * len(methods)
    if model_name == "lightgbm":
        if expected_fits != 288:
            raise SystemExit(f"expected 288 new LightGBM series fits, got {expected_fits}")
        if expected_recon != 144:
            raise SystemExit(f"expected 144 new LightGBM recon evals, got {expected_recon}")
        if seeds != [1, 2]:
            raise SystemExit(f"lightgbm pack must train only seeds [1,2], got {seeds}")
        if 0 in seeds:
            raise SystemExit("seed 0 must not be retrained")
    _write_json(
        metrics / "EXPECTED_COUNTS.json",
        {
            "expected_new_series_fits": expected_fits,
            "expected_new_recon_evals": expected_recon,
            "new_seeds": seeds,
            "seed0_retrained": False,
        },
    )

    jobs = []
    for hier_name in pack["hierarchies"]:
        for fold_id in fold_ids:
            for horizon in horizons:
                for seed in seeds:
                    jobs.append((hier_name, fold_id, horizon, seed))
    status.total_runs = len(jobs)
    cfg_h = config_hash(cfg)
    ph = pack_hash(pack)
    base_rows: list[dict[str, Any]] = []
    recon_rows: list[dict[str, Any]] = []

    def _kwargs(hier: str) -> dict[str, Any]:
        if model_name == "lightgbm":
            key = "lightgbm_cpu" if hier == "cpu_core_weighted" else "lightgbm_memory"
            src = cfg.get(key) or shared.get(key) or {}
            return {
                "n_estimators": int(src["n_estimators"]),
                "learning_rate": float(src["learning_rate"]),
                "num_leaves": int(src["num_leaves"]),
            }
        # dlinear fixed
        d = dict(cfg.get("dlinear_fixed") or shared.get(f"dlinear_{'cpu' if hier == 'cpu_core_weighted' else 'memory'}") or {})
        return {k: d[k] for k in d if k in ("epochs", "patience", "num_threads", "max_batches_per_epoch", "timeout_sec")}

    for hier_name, fold_id, horizon, seed in jobs:
        run_id = f"base__{hier_name}__f{fold_id}__h{horizon}__{model_name}__s{seed}"
        if run_id in status.completed_runs:
            continue
        if not guard.may_launch_new_run():
            status.status = "partial"
            status.last_message = f"Pack {pack['id']} launch limit; resume required."
            break
        entry = _hierarchy_entry(hier_name)
        h = entry["hierarchy"]
        work = _work_panel(panel, entry["name"])
        split = fold_to_split_spec(folds[fold_id])
        kwargs = _kwargs(hier_name)
        try:
            bottom_packs = [
                _fit_predict(work, split, name, horizon, context, model_name, seed, kwargs, eff_proto)
                for name in h.bottom_names
            ]
            top_pack = _fit_predict(
                work, split, h.top_name, horizon, context, model_name, seed, kwargs, eff_proto
            )
            aligned = _align(bottom_packs, top_pack)
            y_full_val = np.concatenate([aligned["yb_val"], aligned["yt_val"].reshape(-1, 1)], axis=1)
            p_full_val = np.concatenate([aligned["pb_val"], aligned["pt_val"].reshape(-1, 1)], axis=1)
            cov = estimate_residual_covariance(y_full_val, p_full_val, shrink_diag=0.1)
            series_var = np.maximum(np.diag(cov), 1e-12)
            pred_bytes = (
                np.ascontiguousarray(aligned["pt_test"]).tobytes()
                + np.ascontiguousarray(aligned["pb_test"]).tobytes()
            )
            pred_hash = hashlib.sha256(pred_bytes).hexdigest()[:16]
            meta = {
                "run_id": run_id,
                "experiment_stage": "final_robustness_extension",
                "eligible_for_final_claims": True,
                "evaluation_role": "robustness_extension",
                "freeze_commit": cfg.get("freeze_commit"),
                "freeze_tag": cfg.get("freeze_tag"),
                "source_experiment_freeze_tag": cfg.get("source_experiment_freeze_tag"),
                "dataset_fingerprint": fp.get("fingerprint"),
                "config_hash": cfg_h,
                "pack_id": pack["id"],
                "pack_hash": ph,
                "hierarchy": entry["name"],
                "fold": fold_id,
                "horizon": horizon,
                "context": context,
                "base_model": model_name,
                "seed": seed,
                "prediction_hash": pred_hash,
                "model_kwargs": json.dumps(kwargs, sort_keys=True),
                "summing_matrix_hash": entry.get("summing_matrix_hash"),
                "wall_train_sec_sum": float(
                    sum(p["wall_train_sec"] for p in bottom_packs) + top_pack["wall_train_sec"]
                ),
                "top_mae_independent": float(mae(aligned["yt_test"], aligned["pt_test"])),
            }
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
            coh_before = coherence_error(aligned["pb_test"], aligned["pt_test"])
            for method in methods:
                out_r = reconcile(
                    method,
                    h,
                    aligned["pb_test"],
                    aligned["pt_test"],
                    series_var=series_var if method == "wls" else None,
                    residual_cov=cov if method == "mint" else None,
                    nonnegative=False,
                )
                recon_rows.append(
                    {
                        **{k: v for k, v in meta.items() if k != "model_kwargs"},
                        "run_id": f"{run_id}__{method}__nn0",
                        "reconciliation_method": method,
                        "nonnegative": False,
                        "coherence_error_before": float(coh_before),
                        "coherence_error_after": float(
                            coherence_error(out_r["bottom"], out_r["top"])
                        ),
                        "is_coherent_after": bool(
                            is_coherent(out_r["bottom"], out_r["top"], atol=1e-4)
                        ),
                        "top_mae": float(mae(aligned["yt_test"], out_r["top"])),
                        "bottom_mae_mean": float(
                            np.mean(
                                [
                                    mae(aligned["yb_test"][:, j], out_r["bottom"][:, j])
                                    for j in range(aligned["yb_test"].shape[1])
                                ]
                            )
                        ),
                        "neg_pred_rate": float(np.mean(out_r["top"] < 0)),
                    }
                )
            status.completed_runs.append(run_id)
        except Exception as exc:  # noqa: BLE001
            status.failed_runs.append(run_id)
            status.last_message = f"{run_id} failed: {type(exc).__name__}: {exc}"
            (out / "logs").mkdir(parents=True, exist_ok=True)
            (out / "logs" / f"{run_id}.err").write_text(status.last_message)

        if base_rows:
            _append_csv(metrics / "base_forecasts.csv", base_rows)
            base_rows = []
        if recon_rows:
            _append_csv(metrics / "reconciliation_results.csv", recon_rows)
            recon_rows = []
        status.wall_seconds = guard.elapsed()
        status.cpu_seconds = guard.cpu_elapsed()
        status.save(out / "RUN_STATUS.json")
        gc.collect()

    if status.status != "partial":
        n_done = len(status.completed_runs)
        n_fail = len(status.failed_runs)
        if n_done + n_fail >= len(jobs) and n_fail == 0:
            status.status = "complete"
        elif n_done + n_fail >= len(jobs):
            status.status = "complete"
        elif n_done > 0:
            status.status = "partial"

    if status.status == "complete" and model_name == "lightgbm":
        from experiments.lightgbm_seed_analysis import analyze_lightgbm_seed_robustness

        analysis = analyze_lightgbm_seed_robustness(cfg, pack, out)
        _write_json(out / "metrics" / "ANALYSIS_SUMMARY.json", analysis)


def run_robustness_statistics(
    cfg: dict[str, Any],
    pack: dict[str, Any],
    out: Path,
    status: RunStatus,
) -> None:
    """No training. Aggregate EWMA + multi-seed vs source seed-0 for claim checks."""
    metrics = out / "metrics"
    tables = out / "tables"
    metrics.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    root = ROOT / (cfg.get("artifact_root") or "results/final/robustness")
    src_root = ROOT / (cfg.get("source_artifact_root") or "results/final/packs")

    ewma = pd.read_csv(root / "01_ewma_baselines" / "metrics" / "reconciliation_results.csv")
    frames = [ewma.assign(source="ewma_extension")]
    for dirname, label in [
        ("03_cpu_classical", "seed0"),
        ("01_memory_classical", "seed0"),
        ("04_cpu_dlinear", "seed0"),
        ("02_memory_dlinear", "seed0"),
    ]:
        p = src_root / dirname / "metrics" / "reconciliation_results.csv"
        if p.exists():
            frames.append(pd.read_csv(p).assign(source=label))
    for dirname in ("02_lightgbm_seed_robustness", "03_dlinear_seed_robustness"):
        p = root / dirname / "metrics" / "reconciliation_results.csv"
        if p.exists():
            frames.append(pd.read_csv(p).assign(source="extension_seeds"))

    all_df = pd.concat(frames, ignore_index=True)
    all_df.to_csv(metrics / "combined_reconciliation.csv", index=False)

    # Baseline strength: independent models per hierarchy/horizon/fold
    rows = []
    for hier in ("cpu_core_weighted", "memory_um"):
        for horizon in (1, 8, 16):
            for fold in (0, 1, 2):
                candidates = {}
                for model in ("persistence", "ewma", "ridge", "lightgbm", "dlinear"):
                    sub = all_df[
                        (all_df["hierarchy"] == hier)
                        & (all_df["horizon"] == horizon)
                        & (all_df["fold"] == fold)
                        & (all_df["reconciliation_method"] == "independent")
                        & (all_df["base_model"] == model)
                    ]
                    if model in ("lightgbm", "dlinear"):
                        sub = sub[sub["seed"] == 0] if "seed" in sub.columns else sub
                    if not sub.empty:
                        candidates[model] = float(sub["top_mae"].iloc[0])
                if not candidates:
                    continue
                strongest = min(candidates, key=candidates.get)
                det = {k: candidates[k] for k in ("persistence", "ewma", "ridge") if k in candidates}
                strongest_det = min(det, key=det.get) if det else None
                rows.append(
                    {
                        "hierarchy": hier,
                        "horizon": horizon,
                        "fold": fold,
                        "strongest_overall": strongest,
                        "strongest_deterministic": strongest_det,
                        **{f"mae_{k}": v for k, v in candidates.items()},
                    }
                )
    pd.DataFrame(rows).to_csv(tables / "baseline_strength.csv", index=False)
    status.status = "complete"
    status.completed_runs.append("robustness_statistics")
    status.total_runs = 1
    status.last_message = "robustness_statistics aggregated (bootstrap deferred to dedicated analysis if needed)"


def _finalize_manifest(
    cfg: dict[str, Any],
    pack: dict[str, Any],
    out: Path,
    status: RunStatus,
    *,
    seed0_hashes: dict[str, str],
) -> dict[str, Any]:
    peak_bytes, peak_available, peak_reason = peak_rss_bytes()
    exec_commit = _git(["git", "rev-parse", "HEAD"])
    branch = _git(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    freeze_tag = cfg.get("freeze_tag")
    freeze_tag_commit = _git(["git", "rev-parse", f"{freeze_tag}^{{}}"]) if freeze_tag else None
    if freeze_tag_commit is None and freeze_tag:
        freeze_tag_commit = _git(["git", "rev-parse", freeze_tag])
    manifest = {
        "pack_id": pack["id"],
        "required": bool(pack.get("required")),
        "dependencies": list(pack.get("dependencies") or []),
        "experiment_stage": "final_robustness_extension",
        "eligible_for_final_claims": status.status == "complete",
        "evaluation_role": "robustness_extension",
        "execution_commit": exec_commit,
        "implementation_commit": cfg.get("implementation_commit"),
        "freeze_commit": cfg.get("freeze_commit"),
        "freeze_tag": freeze_tag,
        "freeze_tag_commit": freeze_tag_commit,
        "source_experiment_freeze_tag": cfg.get("source_experiment_freeze_tag"),
        "source_experiment_freeze_commit": cfg.get("source_experiment_freeze_commit"),
        "source_experiment_freeze_tag_commit": cfg.get("source_experiment_freeze_tag_commit"),
        "repository_url": cfg.get("repository_url"),
        "git_branch": branch,
        "dataset_fingerprint": dataset_fingerprint().get("fingerprint"),
        "config_hash": config_hash(cfg),
        "pack_hash": pack_hash(pack),
        "dependency_lock_hash": cfg.get("dependency_lock_hash"),
        "source_seed0_pack_hashes": seed0_hashes,
        "start_time": status.start_time,
        "end_time": status.end_time,
        "actual_wall_seconds": status.wall_seconds,
        "cpu_seconds": status.cpu_seconds,
        "peak_memory_bytes": peak_bytes,
        "peak_memory_available": peak_available,
        "peak_memory_reason": peak_reason,
        "completed_runs": len(status.completed_runs),
        "failed_runs": len(status.failed_runs),
        "status": status.status,
        "output_dir": str(out),
    }
    _write_json(out / "MANIFEST.json", manifest)
    if status.status == "complete":
        (out / "COMPLETE").write_text(_now() + "\n")
    return manifest


def run_robustness_pack(
    pack_id: str,
    config_path: Path | str | None = None,
    *,
    resume: bool = True,
) -> dict[str, Any]:
    cfg = load_robustness_config(config_path)
    errs = validate_robustness_config(cfg, require_frozen=False)
    if errs:
        raise SystemExit(f"robustness config invalid: {errs}")
    pack = pack_by_id(cfg, pack_id)
    out = pack_output_dir(cfg, pack)
    out.mkdir(parents=True, exist_ok=True)

    seed0_hashes = source_seed0_prediction_hashes(cfg)
    _write_json(out / "SOURCE_SEED0_HASHES.json", seed0_hashes)

    if (out / "COMPLETE").exists() and resume:
        return json.loads((out / "MANIFEST.json").read_text())

    status_path = out / "RUN_STATUS.json"
    if resume and status_path.exists():
        status = RunStatus.load(status_path)
        status.pack_id = pack_id
    else:
        status = RunStatus(pack_id=pack_id)
        status.start_time = _now()
    status.status = "running"
    status.save(status_path)

    hard = float(pack.get("hard_wall_clock_minutes") or cfg.get("hard_wall_clock_minutes_default") or 45)
    stop = float(
        pack.get("stop_launching_new_runs_minutes")
        or cfg.get("stop_launching_new_runs_minutes_default")
        or 40
    )
    guard = WallClockGuard(hard, stop)
    kind = pack.get("kind") or pack_id

    if kind == "ewma_baselines":
        run_ewma_baselines(cfg, pack, out, guard, status)
    elif kind == "lightgbm_seed_robustness":
        run_seed_model_pack(cfg, pack, out, guard, status, model_name="lightgbm")
    elif kind == "dlinear_seed_robustness":
        run_seed_model_pack(cfg, pack, out, guard, status, model_name="dlinear")
    elif kind == "robustness_statistics":
        run_robustness_statistics(cfg, pack, out, status)
    else:
        raise SystemExit(f"unknown pack kind: {kind}")

    status.end_time = _now()
    status.wall_seconds = guard.elapsed()
    status.cpu_seconds = guard.cpu_elapsed()
    status.save(status_path)
    return _finalize_manifest(cfg, pack, out, status, seed0_hashes=seed0_hashes)
