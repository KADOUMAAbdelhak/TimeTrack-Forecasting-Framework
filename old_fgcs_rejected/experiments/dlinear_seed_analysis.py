"""Post-fit analysis for DLinear multi-seed robustness (no retraining of seed 0).

Analysis-only layer: does not alter DLinear training code from
final-robustness-extension-freeze-v2 / experiment-freeze-v2.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd

from experiments.pack_runner import _hierarchy_entry
from models.hybrid.reconciliation import (
    coherence_error,
    estimate_residual_covariance,
    is_coherent,
    reconcile,
)
from timetrack.hierarchy_registry import machine_core_counts
from timetrack.metrics import mae, mase_result, r2_score, rmse

ROOT = Path(__file__).resolve().parents[1]
CPU_CORE_TOTAL = 236.0
SOURCE_DIRS = {
    "cpu_dlinear": "04_cpu_dlinear",
    "memory_dlinear": "02_memory_dlinear",
    "cpu_classical": "03_cpu_classical",
    "memory_classical": "01_memory_classical",
}


def _sha256(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def _cpu_scale(hierarchy: str) -> float:
    return CPU_CORE_TOTAL if hierarchy == "cpu_core_weighted" else 1.0


def _core_weights(hierarchy: str, n_bottom: int) -> np.ndarray:
    if hierarchy != "cpu_core_weighted":
        return np.ones(n_bottom, dtype=float) / max(n_bottom, 1)
    cores = machine_core_counts()
    entry = _hierarchy_entry(hierarchy)
    w = []
    for name in entry["hierarchy"].bottom_names:
        key = name
        for suffix in ("_CU_wcontrib", "_CU", "_UM", "_UD"):
            if key.endswith(suffix):
                key = key[: -len(suffix)]
                break
        w.append(float(cores.get(key, 1.0)))
    w = np.asarray(w, dtype=float)
    return w / w.sum()


def _load_npz(path: Path) -> dict[str, np.ndarray]:
    data = np.load(path)
    return {k: data[k] for k in data.files}


def dlinear_execution_fingerprint(seed: int, cfg: dict[str, Any]) -> dict[str, Any]:
    """Constructor / training-policy fields for seed comparability (frozen DLinear)."""
    d = dict(cfg.get("dlinear_fixed") or {})
    return {
        "epochs": int(d.get("epochs", 40)),
        "patience": int(d.get("patience", 5)),
        "num_threads": int(d.get("num_threads", 1)),
        "max_batches_per_epoch": int(d.get("max_batches_per_epoch", 200)),
        "timeout_sec": float(d.get("timeout_sec", 180)),
        "batch_size": 256,
        "lr": 1e-3,
        "kernel_size": 25,
        "loss": "MSELoss",
        "optimizer": "Adam",
        "scaling": "train_only_standardize",
        "inverse_before_metrics": True,
        "torch_manual_seed": int(seed),
        "numpy_random_seed_set_in_fit": False,  # seed-0 freeze does not call np.random.seed
        "python_random_seed_set_in_fit": False,  # seed-0 freeze does not call random.seed
        "cuda_manual_seed_set_in_fit": False,
        "dataloader_shuffle": False,  # no DataLoader; uses torch.randperm each epoch
        "batch_order": "torch.randperm(len(Xt))",
        "num_workers": 0,
        "device": "cpu",
        "deterministic_algorithms_mode": False,
    }


def _baseline_indep_mae(
    src_root: Path,
    ewma_root: Path,
    lgbm_root: Path | None,
    hierarchy: str,
    fold: int,
    horizon: int,
    model: str,
) -> float | None:
    if model == "ewma":
        path = ewma_root / "metrics" / "reconciliation_results.csv"
        if not path.exists():
            return None
        df = pd.read_csv(path)
        m = df[
            (df.hierarchy == hierarchy)
            & (df.fold == fold)
            & (df.horizon == horizon)
            & (df.reconciliation_method == "independent")
            & (df.base_model == "ewma")
        ]
        return float(m.top_mae.iloc[0]) if not m.empty else None
    if model == "lightgbm":
        # Prefer multi-seed pack seed0; else classical
        for root, seed in ((lgbm_root, 0), (None, 0)):
            if root is not None:
                path = root / "metrics" / "lightgbm_seed_results.csv"
                if path.exists():
                    df = pd.read_csv(path)
                    m = df[
                        (df.hierarchy == hierarchy)
                        & (df.fold == fold)
                        & (df.horizon == horizon)
                        & (df.reconciliation_method == "independent")
                        & (df.seed == 0)
                    ]
                    if not m.empty:
                        return float(m.top_mae_native.iloc[0])
        dirname = SOURCE_DIRS["cpu_classical" if hierarchy == "cpu_core_weighted" else "memory_classical"]
        path = src_root / dirname / "metrics" / "reconciliation_results.csv"
    else:
        dirname = SOURCE_DIRS["cpu_classical" if hierarchy == "cpu_core_weighted" else "memory_classical"]
        path = src_root / dirname / "metrics" / "reconciliation_results.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    m = df[
        (df.hierarchy == hierarchy)
        & (df.fold == fold)
        & (df.horizon == horizon)
        & (df.reconciliation_method == "independent")
        & (df.base_model == model)
        & (df.seed == 0)
    ]
    return float(m.top_mae.iloc[0]) if not m.empty else None


def _peak_metrics(yt_train: np.ndarray, yt: np.ndarray, pt: np.ndarray, q: float) -> dict[str, float]:
    thr = float(np.nanquantile(yt_train, q))
    mask = yt >= thr
    if not np.any(mask):
        return {
            "threshold": thr,
            "n_peak": 0,
            "peak_mae": float("nan"),
            "signed_bias": float("nan"),
            "max_underpred": float("nan"),
        }
    err = pt[mask] - yt[mask]
    return {
        "threshold": thr,
        "n_peak": int(mask.sum()),
        "peak_mae": float(np.mean(np.abs(err))),
        "signed_bias": float(np.mean(err)),
        "max_underpred": float(np.min(err)),  # most negative = underprediction
    }


def analyze_dlinear_seed_robustness(cfg: dict[str, Any], pack: dict[str, Any], out: Path) -> dict[str, Any]:
    metrics = out / "metrics"
    tables = out / "tables"
    figures = out / "figures"
    metrics.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    src_root = ROOT / (cfg.get("source_artifact_root") or "results/final/packs")
    ewma_root = ROOT / (cfg.get("artifact_root") or "results/final/robustness") / "01_ewma_baselines"
    lgbm_root = ROOT / (cfg.get("artifact_root") or "results/final/robustness") / "02_lightgbm_seed_robustness"
    reuse = pack.get("reuse_seed0_from") or {
        "cpu_core_weighted": "cpu_dlinear",
        "memory_um": "memory_dlinear",
    }
    methods = list(pack.get("reconciliation_methods") or ["independent", "bottom_up", "wls", "mint"])
    horizons = [int(h) for h in pack["horizons"]]
    folds = [int(f) for f in pack["outer_folds"]]
    hierarchies = list(pack["hierarchies"])

    dlin_params = {
        k: (cfg.get("dlinear_fixed") or {}).get(k)
        for k in ("epochs", "patience", "num_threads", "max_batches_per_epoch", "timeout_sec")
    }
    model_cfg_hash = hashlib.sha256(json.dumps(dlin_params, sort_keys=True, default=str).encode()).hexdigest()[:16]

    from experiments.robustness_extension import source_seed0_prediction_hashes

    seed0_hashes = source_seed0_prediction_hashes(cfg)
    pd.DataFrame([{"pack": k, "hash16": v} for k, v in seed0_hashes.items()]).to_csv(
        metrics / "source_seed0_hashes.csv", index=False
    )

    # Seed input diff (hyperparams / policy only; series-level tensors checked via alignment)
    diff_rows = []
    unexpected = 0
    fp0 = dlinear_execution_fingerprint(0, cfg)
    for seed in (1, 2):
        fp = dlinear_execution_fingerprint(seed, cfg)
        for key in sorted(set(fp0) | set(fp)):
            v0, v1 = fp0.get(key), fp.get(key)
            if key == "torch_manual_seed":
                status = "intentional_seed_difference"
            elif v0 == v1:
                status = "equal"
            else:
                status = "unexpected_difference"
                unexpected += 1
            diff_rows.append(
                {
                    "hierarchy": "all",
                    "fold": None,
                    "horizon": None,
                    "series": None,
                    "field": key,
                    "seed0_value": v0,
                    "new_seed": seed,
                    "new_seed_value": v1,
                    "classification": status,
                }
            )
    pd.DataFrame(diff_rows).to_csv(metrics / "dlinear_seed_input_diff.csv", index=False)
    if unexpected:
        raise RuntimeError(f"dlinear_seed_input_diff unexpected_difference={unexpected}")

    result_rows: list[dict[str, Any]] = []
    hash_rows: list[dict[str, Any]] = []
    diag_rows: list[dict[str, Any]] = []
    peak_rows: list[dict[str, Any]] = []
    train_rows: list[dict[str, Any]] = []
    pred_cache: dict[tuple, dict[str, np.ndarray]] = {}
    align_rows: list[dict[str, Any]] = []

    for hier in hierarchies:
        entry = _hierarchy_entry(hier)
        h = entry["hierarchy"]
        scale = _cpu_scale(hier)
        core_w = _core_weights(hier, len(h.bottom_names))
        src_pack = reuse[hier]
        src_dir = src_root / SOURCE_DIRS[src_pack] / "metrics" / "predictions"
        new_dir = metrics / "predictions"

        for fold in folds:
            for horizon in horizons:
                for seed in (0, 1, 2):
                    run_id = f"base__{hier}__f{fold}__h{horizon}__dlinear__s{seed}"
                    if seed == 0:
                        path = src_dir / f"{run_id}.npz"
                        source = f"experiment-freeze-v2:{src_pack}"
                    else:
                        path = new_dir / f"{run_id}.npz"
                        source = "robustness_extension"
                    if not path.exists():
                        raise FileNotFoundError(path)
                    aligned = _load_npz(path)
                    pred_cache[(hier, fold, horizon, seed)] = aligned
                    pred_hash = hashlib.sha256(
                        (_sha256(aligned["pt_test"]) + _sha256(aligned["pb_test"])).encode()
                    ).hexdigest()
                    scaler_payload = np.concatenate(
                        [aligned["yt_train"][: min(32, len(aligned["yt_train"]))]]
                    )
                    # Scaler not stored; proxy hash from train targets (deterministic given split)
                    scaler_hash = _sha256(scaler_payload)[:16]
                    split_hash = hashlib.sha256(
                        f"{hier}|{fold}|{horizon}|{len(aligned['yt_test'])}|{len(aligned['yt_val'])}|{len(aligned['yt_train'])}".encode()
                    ).hexdigest()[:16]

                    for j, name in enumerate(h.bottom_names):
                        hash_rows.append(
                            {
                                "hierarchy": hier,
                                "target": name,
                                "fold": fold,
                                "horizon": horizon,
                                "seed": seed,
                                "split": "test",
                                "prediction_sha256": _sha256(aligned["pb_test"][:, j]),
                                "model_config_hash": model_cfg_hash,
                                "split_hash": split_hash,
                                "scaler_hash": scaler_hash,
                                "source": source,
                            }
                        )
                    hash_rows.append(
                        {
                            "hierarchy": hier,
                            "target": h.top_name,
                            "fold": fold,
                            "horizon": horizon,
                            "seed": seed,
                            "split": "test",
                            "prediction_sha256": _sha256(aligned["pt_test"]),
                            "model_config_hash": model_cfg_hash,
                            "split_hash": split_hash,
                            "scaler_hash": scaler_hash,
                            "source": source,
                        }
                    )

                    yt = aligned["yt_test"]
                    pt_ind = aligned["pt_test"]
                    yb = aligned["yb_test"]
                    yt_train = aligned["yt_train"]
                    finite_pct = float(np.mean(np.isfinite(pt_ind)) * 100)
                    neg_pct = float(np.mean(pt_ind < 0) * 100)
                    # CPU percentage space for >100% check
                    pt_report = pt_ind / scale
                    yt_report = yt / scale
                    above_100 = float(np.mean(pt_report > 100.0) * 100) if hier == "cpu_core_weighted" else float("nan")
                    y_min, y_med, y_max = float(np.nanmin(yt)), float(np.nanmedian(yt)), float(np.nanmax(yt))
                    p_min, p_med, p_max = float(np.nanmin(pt_ind)), float(np.nanmedian(pt_ind)), float(np.nanmax(pt_ind))
                    y_range = y_max - y_min
                    p_range = p_max - p_min
                    range_ratio = float(p_range / max(y_range, 1e-12))
                    diag_rows.append(
                        {
                            "hierarchy": hier,
                            "seed": seed,
                            "fold": fold,
                            "horizon": horizon,
                            "finite_pred_pct": finite_pct,
                            "negative_pred_pct": neg_pct,
                            "pct_above_100_cpu_report": above_100,
                            "y_min": y_min,
                            "y_median": y_med,
                            "y_max": y_max,
                            "p_min": p_min,
                            "p_median": p_med,
                            "p_max": p_max,
                            "y_range": y_range,
                            "p_range": p_range,
                            "pred_to_target_range_ratio": range_ratio,
                            "scaled_space_mae": "unavailable_in_frozen_pack_metrics",
                            "inverse_transformed_mae": float(mae(yt, pt_ind)),
                            "median_pred_over_target": float(p_med / max(abs(y_med), 1e-12)),
                            "q90_mae": _peak_metrics(yt_train, yt, pt_ind, 0.90)["peak_mae"],
                            "q95_mae": _peak_metrics(yt_train, yt, pt_ind, 0.95)["peak_mae"],
                            "early_stop_epoch": "unavailable_in_frozen_pack_metrics",
                            "training_batches_completed": "unavailable_in_frozen_pack_metrics",
                            "timeout_status": "unavailable_in_frozen_pack_metrics",
                        }
                    )
                    for q, qname in ((0.90, "q90"), (0.95, "q95")):
                        pm = _peak_metrics(yt_train, yt, pt_ind, q)
                        peak_rows.append(
                            {
                                "hierarchy": hier,
                                "seed": seed,
                                "fold": fold,
                                "horizon": horizon,
                                "method": "independent",
                                "threshold_name": qname,
                                "threshold_value": pm["threshold"],
                                "n_peak": pm["n_peak"],
                                "peak_mae": pm["peak_mae"],
                                "signed_bias": pm["signed_bias"],
                                "max_underpred": pm["max_underpred"],
                                "pred_to_target_range_ratio": range_ratio,
                            }
                        )
                    train_rows.append(
                        {
                            "hierarchy": hier,
                            "seed": seed,
                            "fold": fold,
                            "horizon": horizon,
                            "requested_epochs": int((cfg.get("dlinear_fixed") or {}).get("epochs", 40)),
                            "completed_epochs": "unavailable_in_frozen_pack_metrics",
                            "best_epoch": "unavailable_in_frozen_pack_metrics",
                            "early_stop_epoch": "unavailable_in_frozen_pack_metrics",
                            "final_train_loss": "unavailable_in_frozen_pack_metrics",
                            "best_validation_loss": "unavailable_in_frozen_pack_metrics",
                            "wall_time": "unavailable_in_frozen_pack_metrics",
                            "timeout": "unavailable_in_frozen_pack_metrics",
                            "failed_run": False,
                            "non_finite_loss": "unavailable_in_frozen_pack_metrics",
                        }
                    )

                    y_full_val = np.concatenate(
                        [aligned["yb_val"], aligned["yt_val"].reshape(-1, 1)], axis=1
                    )
                    p_full_val = np.concatenate(
                        [aligned["pb_val"], aligned["pt_val"].reshape(-1, 1)], axis=1
                    )
                    cov = estimate_residual_covariance(y_full_val, p_full_val, shrink_diag=0.1)
                    series_var = np.maximum(np.diag(cov), 1e-12)
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
                        top = out_r["top"]
                        bottom = out_r["bottom"]
                        per_m = np.array(
                            [mae(yb[:, j], bottom[:, j]) for j in range(yb.shape[1])], dtype=float
                        )
                        per_m_ind = np.array(
                            [mae(yb[:, j], aligned["pb_test"][:, j]) for j in range(yb.shape[1])],
                            dtype=float,
                        )
                        improved = int(np.sum(per_m < per_m_ind - 1e-12))
                        degraded = int(np.sum(per_m > per_m_ind + 1e-12))
                        mase_info = mase_result(yt, top, yt_train)
                        top_mae = float(mae(yt, top))
                        result_rows.append(
                            {
                                "hierarchy": hier,
                                "fold": fold,
                                "horizon": horizon,
                                "seed": seed,
                                "reconciliation_method": method,
                                "base_model": "dlinear",
                                "source": source,
                                "top_mae_native": top_mae,
                                "top_mae_report": top_mae / scale,
                                "top_rmse_report": float(rmse(yt, top)) / scale,
                                "top_r2": float(r2_score(yt, top)),
                                "mase": mase_info["mase"],
                                "mase_valid": mase_info["mase_valid"],
                                "coherence_error_before": float(coh_before),
                                "coherence_error_after": float(coherence_error(bottom, top)),
                                "is_coherent_after": bool(is_coherent(bottom, top, atol=1e-4)),
                                "recon_adjustment_l2": float(
                                    np.sqrt(np.mean((top - pt_ind) ** 2))
                                ),
                                "bottom_mae_mean_native": float(np.mean(per_m)),
                                "bottom_mae_weighted_native": float(np.dot(per_m, core_w)),
                                "worst_machine_mae_native": float(np.max(per_m)),
                                "improved_machine_count": improved,
                                "degraded_machine_count": degraded,
                                "neg_pred_rate": float(np.mean(top < 0)),
                                "prediction_hash": pred_hash[:16],
                                "model_config_hash": model_cfg_hash,
                                "report_unit": (
                                    "weighted_mean_pct" if hier == "cpu_core_weighted" else "native"
                                ),
                            }
                        )
                        if method != "independent":
                            for q, qname in ((0.90, "q90"), (0.95, "q95")):
                                pm = _peak_metrics(yt_train, yt, top, q)
                                peak_rows.append(
                                    {
                                        "hierarchy": hier,
                                        "seed": seed,
                                        "fold": fold,
                                        "horizon": horizon,
                                        "method": method,
                                        "threshold_name": qname,
                                        "threshold_value": pm["threshold"],
                                        "n_peak": pm["n_peak"],
                                        "peak_mae": pm["peak_mae"],
                                        "signed_bias": pm["signed_bias"],
                                        "max_underpred": pm["max_underpred"],
                                        "pred_to_target_range_ratio": float(
                                            (np.nanmax(top) - np.nanmin(top))
                                            / max(y_range, 1e-12)
                                        ),
                                    }
                                )

                # alignment across seeds
                keys = [(hier, fold, horizon, s) for s in (0, 1, 2)]
                yt = [pred_cache[k]["yt_test"] for k in keys]
                yv = [pred_cache[k]["yt_val"] for k in keys]
                ytr = [pred_cache[k]["yt_train"] for k in keys]
                align_rows.append(
                    {
                        "hierarchy": hier,
                        "fold": fold,
                        "horizon": horizon,
                        "n_test_equal": len({len(x) for x in yt}) == 1,
                        "n_val_equal": len({len(x) for x in yv}) == 1,
                        "n_train_equal": len({len(x) for x in ytr}) == 1,
                        "yt_test_equal": all(np.allclose(yt[0], yt[i], equal_nan=True) for i in (1, 2)),
                        "yt_val_equal": all(np.allclose(yv[0], yv[i], equal_nan=True) for i in (1, 2)),
                        "yt_train_equal": all(np.allclose(ytr[0], ytr[i], equal_nan=True) for i in (1, 2)),
                    }
                )

    results = pd.DataFrame(result_rows)
    enriched = []
    for _, r in results.iterrows():
        ind = results[
            (results.hierarchy == r.hierarchy)
            & (results.fold == r.fold)
            & (results.horizon == r.horizon)
            & (results.seed == r.seed)
            & (results.reconciliation_method == "independent")
        ].iloc[0]
        pers = _baseline_indep_mae(
            src_root, ewma_root, lgbm_root, r.hierarchy, int(r.fold), int(r.horizon), "persistence"
        )
        ewma = _baseline_indep_mae(
            src_root, ewma_root, lgbm_root, r.hierarchy, int(r.fold), int(r.horizon), "ewma"
        )
        ridge = _baseline_indep_mae(
            src_root, ewma_root, lgbm_root, r.hierarchy, int(r.fold), int(r.horizon), "ridge"
        )
        lgbm = _baseline_indep_mae(
            src_root, ewma_root, lgbm_root, r.hierarchy, int(r.fold), int(r.horizon), "lightgbm"
        )
        row = dict(r)
        row["rel_mae_vs_independent"] = float(r.top_mae_native / max(ind.top_mae_native, 1e-12))
        row["pct_vs_independent"] = 100.0 * (row["rel_mae_vs_independent"] - 1.0)
        row["persistence_mae_native"] = pers
        row["ewma_mae_native"] = ewma
        row["ridge_mae_native"] = ridge
        row["lightgbm_mae_native"] = lgbm
        row["rel_mae_vs_persistence"] = (
            float(r.top_mae_native / max(pers, 1e-12)) if pers is not None else None
        )
        row["rel_mae_vs_ewma"] = float(r.top_mae_native / max(ewma, 1e-12)) if ewma is not None else None
        row["rel_mae_vs_ridge"] = float(r.top_mae_native / max(ridge, 1e-12)) if ridge is not None else None
        row["rel_mae_vs_lightgbm"] = (
            float(r.top_mae_native / max(lgbm, 1e-12)) if lgbm is not None else None
        )
        enriched.append(row)
    results = pd.DataFrame(enriched)
    results.to_csv(metrics / "dlinear_seed_results.csv", index=False)
    pd.DataFrame(hash_rows).to_csv(metrics / "dlinear_seed_prediction_hashes.csv", index=False)
    pd.DataFrame(diag_rows).to_csv(metrics / "dlinear_seed_numerical_diagnostics.csv", index=False)
    pd.DataFrame(train_rows).to_csv(metrics / "dlinear_seed_training_stability.csv", index=False)
    pd.DataFrame(align_rows).to_csv(metrics / "dlinear_seed_timestamp_alignment.csv", index=False)
    if align_rows and not all(
        r["yt_test_equal"] and r["yt_val_equal"] and r["yt_train_equal"] for r in align_rows
    ):
        raise RuntimeError("timestamp/label arrays do not align across DLinear seeds")

    # Variability
    var_rows = []
    for (hier, horizon, fold, method), g in results.groupby(
        ["hierarchy", "horizon", "fold", "reconciliation_method"]
    ):
        g = g.sort_values("seed")
        maes = g["top_mae_report"].to_numpy()
        hashes = g["prediction_hash"].tolist()
        mean = float(np.mean(maes))
        std = float(np.std(maes, ddof=0))
        cv = float(std / max(abs(mean), 1e-12))
        max_abs = 0.0
        keys = [(hier, int(fold), int(horizon), int(s)) for s in (0, 1, 2)]
        tops = [pred_cache[k]["pt_test"] for k in keys]
        for i in range(3):
            for j in range(i + 1, 3):
                max_abs = max(max_abs, float(np.max(np.abs(tops[i] - tops[j]))))
        identical = len(set(hashes)) == 1
        rel_spread = float((maes.max() - maes.min()) / max(abs(mean), 1e-12))
        pcts = g["pct_vs_independent"].to_numpy()
        # primary direction: for independent use vs persistence; else vs independent
        if method == "independent":
            effects = g["rel_mae_vs_persistence"].to_numpy()
            primary_ok = np.all(effects < 1.0) or np.all(effects > 1.0)
        else:
            primary_ok = np.all(pcts < 0) or np.all(pcts > 0) or np.all(np.abs(pcts) <= 2)
        if identical or (max_abs <= 1e-9 * max(1.0, float(np.nanmax(np.abs(tops[0]))))) or rel_spread <= 1e-9:
            klass = "seed_invariant"
        elif cv <= 0.01 and primary_ok:
            klass = "practically_seed_stable"
        elif cv <= 0.05 and primary_ok:
            klass = "moderately_seed_sensitive"
        else:
            klass = "seed_unstable"
        worst_seed = int(g.loc[g["top_mae_report"].idxmax(), "seed"])
        var_rows.append(
            {
                "hierarchy": hier,
                "horizon": horizon,
                "fold": fold,
                "reconciliation_method": method,
                "mean_mae_report": mean,
                "std_mae_report": std,
                "cv": cv,
                "min_mae_report": float(maes.min()),
                "max_mae_report": float(maes.max()),
                "worst_seed": worst_seed,
                "identical_prediction_hashes": identical,
                "n_unique_hashes": len(set(hashes)),
                "pairwise_max_abs_pred_diff": max_abs,
                "stability_class": klass,
                "seed0_mae": float(maes[0]),
                "seed1_mae": float(maes[1]),
                "seed2_mae": float(maes[2]),
            }
        )
    var_df = pd.DataFrame(var_rows)
    var_df.to_csv(metrics / "dlinear_seed_summary.csv", index=False)

    fold_rows = []
    for (hier, seed, horizon, method), g in results.groupby(
        ["hierarchy", "seed", "horizon", "reconciliation_method"]
    ):
        fold_rows.append(
            {
                "hierarchy": hier,
                "seed": seed,
                "horizon": horizon,
                "reconciliation_method": method,
                "n_folds": g.fold.nunique(),
                "mean_mae_report": float(g.top_mae_report.mean()),
                "std_mae_report": float(g.top_mae_report.std(ddof=0)),
                "mean_pct_vs_independent": float(g.pct_vs_independent.mean()),
                "mean_rel_vs_persistence": float(g.rel_mae_vs_persistence.mean())
                if g.rel_mae_vs_persistence.notna().all()
                else None,
                "mean_rel_vs_ewma": float(g.rel_mae_vs_ewma.mean()) if g.rel_mae_vs_ewma.notna().all() else None,
            }
        )
    pd.DataFrame(fold_rows).to_csv(metrics / "dlinear_seed_fold_consistency.csv", index=False)

    recon_eff = results[results.reconciliation_method != "independent"][
        [
            "hierarchy",
            "seed",
            "fold",
            "horizon",
            "reconciliation_method",
            "top_mae_report",
            "pct_vs_independent",
            "coherence_error_before",
            "coherence_error_after",
            "bottom_mae_mean_native",
            "worst_machine_mae_native",
            "improved_machine_count",
            "degraded_machine_count",
        ]
    ]
    recon_eff.to_csv(metrics / "dlinear_seed_reconciliation_effects.csv", index=False)

    peak_df = pd.DataFrame(peak_rows)
    peak_df.to_csv(tables / "dlinear_peak_compression_by_seed.csv", index=False)

    cpu = results[results.hierarchy == "cpu_core_weighted"]
    mem = results[results.hierarchy == "memory_um"]
    cpu.to_csv(tables / "dlinear_cpu_seed_robustness.csv", index=False)
    mem.to_csv(tables / "dlinear_memory_seed_robustness.csv", index=False)

    conclusions = []
    cpu_ind = cpu[cpu.reconciliation_method == "independent"]
    for seed, g in cpu_ind.groupby("seed"):
        for name, col in (
            ("persistence", "rel_mae_vs_persistence"),
            ("ewma", "rel_mae_vs_ewma"),
            ("ridge", "rel_mae_vs_ridge"),
            ("lightgbm", "rel_mae_vs_lightgbm"),
        ):
            conclusions.append(
                {
                    "check": f"C1_cpu_independent_vs_{name}",
                    "seed": int(seed),
                    "wins": int((g[col] < 1.0).sum()),
                    "losses": int((g[col] > 1.0).sum()),
                    "mean_rel": float(g[col].mean()),
                    "worst_rel": float(g[col].max()),
                    "worst_fold": int(g.loc[g[col].idxmax(), "fold"]),
                    "worst_horizon": int(g.loc[g[col].idxmax(), "horizon"]),
                }
            )
    cpu_bu = cpu[cpu.reconciliation_method == "bottom_up"]
    for seed, g in cpu_bu.groupby("seed"):
        conclusions.append(
            {
                "check": "C2_cpu_bottom_up_vs_independent",
                "seed": int(seed),
                "wins": int((g.pct_vs_independent < 0).sum()),
                "neutral": int((np.abs(g.pct_vs_independent) <= 2).sum()),
                "losses": int((g.pct_vs_independent > 2).sum()),
                "mean_pct": float(g.pct_vs_independent.mean()),
                "worst_pct": float(g.pct_vs_independent.max()),
                "mean_coh_reduction": float(
                    (g.coherence_error_before - g.coherence_error_after).mean()
                ),
            }
        )
    mem_ind = mem[mem.reconciliation_method == "independent"]
    for seed, g in mem_ind.groupby("seed"):
        conclusions.append(
            {
                "check": "memory_independent_vs_ewma",
                "seed": int(seed),
                "wins": int((g.rel_mae_vs_ewma < 1.0).sum()),
                "losses": int((g.rel_mae_vs_ewma > 1.0).sum()),
                "mean_rel": float(g.rel_mae_vs_ewma.mean()),
            }
        )
    for method in ("wls", "mint", "bottom_up"):
        sub = mem[mem.reconciliation_method == method]
        for seed, g in sub.groupby("seed"):
            conclusions.append(
                {
                    "check": f"memory_{method}_vs_independent",
                    "seed": int(seed),
                    "wins": int((g.pct_vs_independent < 0).sum()),
                    "mean_pct": float(g.pct_vs_independent.mean()),
                    "cells_support": int((g.pct_vs_independent < 0).sum()),
                    "n_cells": len(g),
                }
            )
    for hier in hierarchies:
        sub = var_df[var_df.hierarchy == hier]
        conclusions.append(
            {
                "check": "seed_stability",
                "hierarchy": hier,
                "n_seed_invariant": int((sub.stability_class == "seed_invariant").sum()),
                "n_practically_stable": int((sub.stability_class == "practically_seed_stable").sum()),
                "n_moderate": int((sub.stability_class == "moderately_seed_sensitive").sum()),
                "n_unstable": int((sub.stability_class == "seed_unstable").sum()),
                "identical_hash_cells": int(sub.identical_prediction_hashes.sum()),
                "total_cells": len(sub),
            }
        )
    pd.DataFrame(conclusions).to_csv(tables / "dlinear_seed_conclusion.csv", index=False)

    _plot_seed_variability(cpu, figures / "dlinear_cpu_seed_variability.pdf", "CPU DLinear")
    _plot_seed_variability(mem, figures / "dlinear_memory_seed_variability.pdf", "Memory DLinear")
    _plot_recon_by_seed(cpu, figures / "dlinear_reconciliation_effect_by_seed.pdf")
    _plot_peak(peak_df, figures / "dlinear_peak_compression_by_seed.pdf")

    # hash identity
    id_count = material = 0
    for _, g in pd.DataFrame(hash_rows).groupby(["hierarchy", "fold", "horizon", "target"]):
        if len(set(g.prediction_sha256)) == 1:
            id_count += 1
        else:
            material += 1
    summary = {
        "identical_across_three_seeds": id_count,
        "materially_different_hash_groups": material,
        "n_hash_groups": id_count + material,
        "unexpected_input_diffs": unexpected,
        "model_config_hash": model_cfg_hash,
    }
    (metrics / "dlinear_seed_hash_identity.json").write_text(json.dumps(summary, indent=2))
    return summary


def _plot_seed_variability(df: pd.DataFrame, path: Path, title: str) -> None:
    ind = df[df.reconciliation_method == "independent"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for seed, g in ind.groupby("seed"):
        means = g.groupby("horizon")["top_mae_report"].mean()
        ax.plot(means.index, means.values, marker="o", label=f"seed {seed}")
    ax.set_xlabel("Horizon")
    ax.set_ylabel("Top MAE (report units)")
    ax.set_title(title + " — independent MAE by seed")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    fig.savefig(path.with_suffix(".png"))
    plt.close(fig)


def _plot_recon_by_seed(cpu: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for method in ("bottom_up", "wls", "mint"):
        sub = cpu[cpu.reconciliation_method == method]
        means = sub.groupby("seed")["pct_vs_independent"].mean()
        ax.plot(means.index, means.values, marker="o", label=method)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("Seed")
    ax.set_ylabel("% MAE vs independent")
    ax.set_title("CPU DLinear reconciliation effect by seed")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    fig.savefig(path.with_suffix(".png"))
    plt.close(fig)


def _plot_peak(peak_df: pd.DataFrame, path: Path) -> None:
    sub = peak_df[(peak_df.method == "independent") & (peak_df.threshold_name == "q95")]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for ax, hier, title in zip(
        axes,
        ("cpu_core_weighted", "memory_um"),
        ("CPU", "Memory"),
    ):
        g = sub[sub.hierarchy == hier]
        for seed, sg in g.groupby("seed"):
            ax.scatter(
                [seed] * len(sg),
                sg.signed_bias,
                label=f"seed {int(seed)}",
                alpha=0.7,
            )
        ax.axhline(0, color="k", lw=0.8)
        ax.set_title(f"{title} q95 signed peak bias")
        ax.set_xlabel("Seed")
        ax.set_ylabel("mean(pred-true) on peaks")
        ax.grid(True, alpha=0.3)
        if len(g):
            ax.legend()
    fig.tight_layout()
    fig.savefig(path)
    fig.savefig(path.with_suffix(".png"))
    plt.close(fig)
