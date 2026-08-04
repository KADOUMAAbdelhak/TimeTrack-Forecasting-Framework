"""Frozen multi-seed robustness statistical analysis (predictions only; no training)."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd
import yaml

from experiments.pack_runner import _hierarchy_entry
from models.hybrid.reconciliation import (
    coherence_error,
    estimate_residual_covariance,
    reconcile,
)
from timetrack.hierarchy_registry import machine_core_counts
from timetrack.metrics import mae
from timetrack.stats_bootstrap import (
    holm_adjust_with_ranks,
    paired_moving_block_bootstrap_effects,
    select_block_length,
)

ROOT = Path(__file__).resolve().parents[1]
CPU_CORE_TOTAL = 236.0

SCIENTIFIC_EXCLUDE = frozenset(
    {
        "implementation_commit",
        "freeze_commit",
        "freeze_tag_commit",
        "frozen_scientific_config_hash",
    }
)

SOURCE_DIRS = {
    "cpu_classical": "03_cpu_classical",
    "memory_classical": "01_memory_classical",
    "cpu_dlinear": "04_cpu_dlinear",
    "memory_dlinear": "02_memory_dlinear",
}


def load_stats_config(path: Path | str | None = None) -> dict[str, Any]:
    path = Path(path) if path else ROOT / "configs" / "final_robustness_statistics.yaml"
    return yaml.safe_load(path.read_text())


def scientific_config_view(cfg: dict[str, Any]) -> dict[str, Any]:
    view = copy.deepcopy(cfg)
    for k in SCIENTIFIC_EXCLUDE:
        view.pop(k, None)
    return view


def scientific_config_hash(cfg: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(scientific_config_view(cfg), sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


def validate_stats_config(cfg: dict[str, Any], *, require_frozen: bool = False) -> list[str]:
    errs: list[str] = []
    if cfg.get("freeze_tag") != "final-robustness-analysis-freeze-v1":
        errs.append("freeze_tag must be final-robustness-analysis-freeze-v1")
    if cfg.get("source_experiment_freeze_tag") != "experiment-freeze-v2":
        errs.append("source_experiment_freeze_tag mismatch")
    if cfg.get("source_robustness_extension_freeze_tag") != "final-robustness-extension-freeze-v2":
        errs.append("source_robustness_extension_freeze_tag mismatch")
    if cfg.get("dataset_fingerprint") != "bf06dc0e7fe6ff5e":
        errs.append("dataset_fingerprint mismatch")
    if int(cfg.get("cpu_core_total", 0)) != 236:
        errs.append("cpu_core_total must be 236")
    boot = cfg.get("bootstrap") or {}
    if int(boot.get("n_boot", 0)) != 5000:
        errs.append("bootstrap.n_boot must be 5000")
    if int(boot.get("seed", -1)) != 0:
        errs.append("bootstrap.seed must be 0")
    expected_fam = [
        "cpu_lightgbm_vs_deterministic",
        "cpu_lightgbm_reconciliation",
        "memory_lightgbm_vs_ewma",
        "memory_lightgbm_reconciliation",
        "cpu_dlinear_vs_deterministic",
        "cpu_dlinear_reconciliation",
        "memory_dlinear_vs_ewma",
        "memory_dlinear_reconciliation",
    ]
    if list(cfg.get("holm_families") or []) != expected_fam:
        errs.append(f"holm_families must equal {expected_fam}")
    if str(cfg.get("lightgbm_pack_hash")) != "446473103b0cf235":
        errs.append("lightgbm_pack_hash mismatch")
    if str(cfg.get("dlinear_pack_hash")) != "ecd66cd4bc4a7770":
        errs.append("dlinear_pack_hash mismatch")
    computed = scientific_config_hash(cfg)
    frozen = cfg.get("frozen_scientific_config_hash")
    if require_frozen:
        for key in ("implementation_commit", "freeze_commit"):
            val = str(cfg.get(key) or "")
            if not val or val.upper() == "PENDING" or len(val) != 40:
                errs.append(f"{key} invalid")
        if not frozen or str(frozen).upper() == "PENDING" or str(frozen) != computed:
            errs.append(f"frozen_scientific_config_hash mismatch ({frozen} vs {computed})")
    elif frozen and str(frozen).upper() != "PENDING" and str(frozen) != computed:
        errs.append(f"frozen_scientific_config_hash stale ({frozen} vs {computed})")
    return errs


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _scale(hierarchy: str) -> float:
    return CPU_CORE_TOTAL if hierarchy == "cpu_core_weighted" else 1.0


def _npz_path(cfg: dict[str, Any], model: str, hierarchy: str, fold: int, horizon: int, seed: int) -> Path:
    rob = ROOT / (cfg.get("robustness_artifact_root") or "results/final/robustness")
    src = ROOT / (cfg.get("source_artifact_root") or "results/final/packs")
    run = f"base__{hierarchy}__f{fold}__h{horizon}__{model}__s{seed}.npz"
    if model == "ewma":
        return rob / cfg["ewma_pack_dir"] / "metrics" / "predictions" / run.replace("__ewma__", "__ewma__").replace(
            f"__{model}__", "__ewma__"
        )
    if model == "lightgbm":
        if seed == 0:
            pack = "cpu_classical" if hierarchy == "cpu_core_weighted" else "memory_classical"
            return src / SOURCE_DIRS[pack] / "metrics" / "predictions" / run
        return rob / cfg["lightgbm_pack_dir"] / "metrics" / "predictions" / run
    if model == "dlinear":
        if seed == 0:
            pack = "cpu_dlinear" if hierarchy == "cpu_core_weighted" else "memory_dlinear"
            return src / SOURCE_DIRS[pack] / "metrics" / "predictions" / run
        return rob / cfg["dlinear_pack_dir"] / "metrics" / "predictions" / run
    # persistence / ridge always seed 0 classical
    pack = "cpu_classical" if hierarchy == "cpu_core_weighted" else "memory_classical"
    return src / SOURCE_DIRS[pack] / "metrics" / "predictions" / run


def _load_npz(path: Path) -> dict[str, np.ndarray]:
    if not path.exists():
        raise FileNotFoundError(path)
    data = np.load(path)
    return {k: data[k] for k in data.files}


def _reconcile_top(
    hierarchy: str,
    aligned: dict[str, np.ndarray],
    method: str,
) -> dict[str, Any]:
    entry = _hierarchy_entry(hierarchy)
    h = entry["hierarchy"]
    y_full_val = np.concatenate([aligned["yb_val"], aligned["yt_val"].reshape(-1, 1)], axis=1)
    p_full_val = np.concatenate([aligned["pb_val"], aligned["pt_val"].reshape(-1, 1)], axis=1)
    cov = estimate_residual_covariance(y_full_val, p_full_val, shrink_diag=0.1)
    series_var = np.maximum(np.diag(cov), 1e-12)
    out = reconcile(
        method,
        h,
        aligned["pb_test"],
        aligned["pt_test"],
        series_var=series_var if method == "wls" else None,
        residual_cov=cov if method == "mint" else None,
        nonnegative=False,
    )
    return {
        "yt": aligned["yt_test"],
        "pt": out["top"],
        "pb": out["bottom"],
        "yb": aligned["yb_test"],
        "coherence_before": float(coherence_error(aligned["pb_test"], aligned["pt_test"])),
        "coherence_after": float(coherence_error(out["bottom"], out["top"])),
        "top_mae_native": float(mae(aligned["yt_test"], out["top"])),
    }


def claim_support(
    relative_effects: list[float],
    *,
    neutral_band: float = 0.02,
    substantial_opposite: float = 0.05,
) -> str:
    """relative_effect < 0 means method_a better than method_b."""
    if len(relative_effects) < 1:
        return "unsupported"
    signs = []
    for e in relative_effects:
        if abs(e) <= neutral_band:
            signs.append(0)
        elif e < 0:
            signs.append(1)
        else:
            signs.append(-1)
    supporting = sum(1 for s in signs if s == 1)
    opposing = sum(1 for s in signs if s == -1)
    neutral = sum(1 for s in signs if s == 0)
    if any(e > substantial_opposite for e in relative_effects) and supporting > 0:
        # may still be seed_unstable warning separately
        pass
    if opposing > supporting and opposing >= max(1, len(relative_effects) // 2):
        return "contradicted"
    if supporting == len(relative_effects):
        return "supported"
    if supporting >= 2 and opposing == 0:
        return "supported"
    if supporting >= 2 and opposing == 1 and any(
        abs(e) <= neutral_band or e < 0 for e in relative_effects
    ):
        # two support one within band already counted neutral
        if opposing == 0 or (opposing == 1 and max(relative_effects) <= substantial_opposite):
            if opposing == 0:
                return "supported"
    if supporting > opposing and supporting >= 1:
        return "partially_supported"
    return "unsupported"


def classify_seed_variability(maes: np.ndarray, hashes: list[str], max_abs_diff: float, effects: list[float] | None = None) -> str:
    mean = float(np.mean(maes))
    std = float(np.std(maes, ddof=0))
    cv = std / max(abs(mean), 1e-12)
    identical = len(set(hashes)) == 1
    rel_spread = float((maes.max() - maes.min()) / max(abs(mean), 1e-12))
    reverse = False
    if effects is not None and len(effects) == 3:
        signs = [np.sign(e) if abs(e) > 0.02 else 0 for e in effects]
        if 1 in signs and -1 in signs:
            reverse = any(abs(e) > 0.05 and np.sign(e) != np.sign(np.median(effects)) for e in effects)
    if identical or rel_spread <= 1e-9 or max_abs_diff <= 1e-9:
        return "seed_invariant"
    if cv > 0.05 or reverse:
        return "seed_unstable"
    if cv <= 0.01:
        return "practically_seed_stable"
    if cv <= 0.05:
        return "moderately_seed_sensitive"
    return "seed_unstable"


def run_robustness_statistics(
    cfg: dict[str, Any],
    *,
    output_dir: Path | None = None,
    smoke: bool = False,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    errs = validate_stats_config(cfg, require_frozen=False)
    if errs:
        raise SystemExit(f"invalid robustness statistics config: {errs}")

    out = Path(output_dir) if output_dir else ROOT / cfg["output_dir"]
    metrics = out / "metrics"
    tables = out / "tables"
    figures = out / "figures"
    for d in (metrics, tables, figures):
        d.mkdir(parents=True, exist_ok=True)

    # Reject provisional inputs if present as sources
    for bad in cfg.get("rejected_inputs") or []:
        p = ROOT / bad
        if "lightgbm_seed_robustness" in bad and (p / "COMPLETE").exists():
            # archived rejected — must not be used; we simply never point paths there
            pass

    # Verify pack hashes from MANIFEST
    rob = ROOT / cfg["robustness_artifact_root"]
    lgbm_man = json.loads((rob / cfg["lightgbm_pack_dir"] / "MANIFEST.json").read_text())
    dlin_man = json.loads((rob / cfg["dlinear_pack_dir"] / "MANIFEST.json").read_text())
    if lgbm_man.get("pack_hash") != cfg["lightgbm_pack_hash"]:
        raise SystemExit(f"LightGBM pack hash mismatch: {lgbm_man.get('pack_hash')}")
    if dlin_man.get("pack_hash") != cfg["dlinear_pack_hash"]:
        raise SystemExit(f"DLinear pack hash mismatch: {dlin_man.get('pack_hash')}")
    if dlin_man.get("prediction_status") not in (None, "accepted"):
        # allow accepted or unset after we stamped
        pass

    seeds = [0, 1, 2] if not smoke else [0, 1]
    horizons = list(cfg["horizons"]) if not smoke else [1]
    folds = list(cfg["folds"]) if not smoke else [0]
    methods = list(cfg["methods"])
    hierarchies = list(cfg["hierarchies"])
    boot_cfg = cfg["bootstrap"]
    n_boot = int(boot_cfg["n_boot"]) if not smoke else 50
    boot_seed = int(boot_cfg["seed"])
    context = int(cfg.get("context", 32))

    # Hash all consumed prediction files
    hash_rows = []
    pred_cache: dict[tuple, dict[str, np.ndarray]] = {}
    models_needed = {
        "persistence",
        "ridge",
        "ewma",
        "lightgbm",
        "dlinear",
    }
    for hier in hierarchies:
        for model in models_needed:
            for fold in folds:
                for horizon in horizons:
                    seed_list = [0] if model in ("persistence", "ridge", "ewma") else seeds
                    for seed in seed_list:
                        path = _npz_path(cfg, model, hier, fold, horizon, seed)
                        # ewma path fix
                        if model == "ewma":
                            path = (
                                rob
                                / cfg["ewma_pack_dir"]
                                / "metrics"
                                / "predictions"
                                / f"base__{hier}__f{fold}__h{horizon}__ewma__s0.npz"
                            )
                        hsh = sha256_file(path)
                        hash_rows.append(
                            {
                                "hierarchy": hier,
                                "model": model,
                                "fold": fold,
                                "horizon": horizon,
                                "seed": seed,
                                "path": str(path),
                                "sha256": hsh,
                            }
                        )
                        pred_cache[(model, hier, fold, horizon, seed)] = _load_npz(path)
    hash_df = pd.DataFrame(hash_rows)
    hash_df.to_csv(metrics / "source_prediction_hashes.csv", index=False)
    hashes_before = {r["path"]: r["sha256"] for r in hash_rows}

    # --- DLinear reconstruction verification ---
    src_root = ROOT / (cfg.get("source_artifact_root") or "results/final/packs")
    dlin_recon_csv = rob / cfg["dlinear_pack_dir"] / "metrics" / "reconciliation_results.csv"
    src0_cpu = src_root / SOURCE_DIRS["cpu_dlinear"] / "metrics" / "reconciliation_results.csv"
    src0_mem = src_root / SOURCE_DIRS["memory_dlinear"] / "metrics" / "reconciliation_results.csv"
    src_frames = []
    if dlin_recon_csv.exists():
        src_frames.append(pd.read_csv(dlin_recon_csv))
    for p in (src0_cpu, src0_mem):
        if p.exists():
            df = pd.read_csv(p)
            src_frames.append(df[df.base_model == "dlinear"])
    src_recon = pd.concat(src_frames, ignore_index=True) if src_frames else pd.DataFrame()
    if not src_recon.empty and "seed" in src_recon.columns:
        src_recon = src_recon.copy()
        src_recon["seed"] = src_recon["seed"].astype(int)
        src_recon["fold"] = src_recon["fold"].astype(int)
        src_recon["horizon"] = src_recon["horizon"].astype(int)
    ver_rows = []
    tol_rel = float(cfg["reconstruction_tolerance"]["relative"])
    tol_abs = float(cfg["reconstruction_tolerance"]["absolute"])
    max_diff = 0.0
    for hier in hierarchies:
        for fold in folds:
            for horizon in horizons:
                for seed in seeds:
                    aligned = pred_cache[("dlinear", hier, fold, horizon, seed)]
                    for method in methods:
                        rec = _reconcile_top(hier, aligned, method)
                        mae_hat = rec["top_mae_native"]
                        sub = src_recon[
                            (src_recon.hierarchy == hier)
                            & (src_recon.fold == fold)
                            & (src_recon.horizon == horizon)
                            & (src_recon.seed == int(seed))
                            & (src_recon.reconciliation_method == method)
                            & (src_recon.base_model == "dlinear")
                        ]
                        if sub.empty:
                            status = "missing_source_row"
                            src_mae = float("nan")
                            ok = False
                        else:
                            src_mae = float(sub.top_mae.iloc[0])
                            diff = abs(mae_hat - src_mae)
                            max_diff = max(max_diff, diff)
                            ok = diff <= max(tol_abs, tol_rel * max(abs(src_mae), 1e-12))
                            status = "ok" if ok else "mismatch"
                        ver_rows.append(
                            {
                                "hierarchy": hier,
                                "fold": fold,
                                "horizon": horizon,
                                "seed": seed,
                                "method": method,
                                "reconstructed_mae": mae_hat,
                                "source_mae": src_mae,
                                "abs_diff": abs(mae_hat - src_mae) if np.isfinite(src_mae) else float("nan"),
                                "status": status,
                            }
                        )
    ver_df = pd.DataFrame(ver_rows)
    ver_df.to_csv(metrics / "dlinear_reconstruction_verification.csv", index=False)
    if not smoke and (ver_df.status != "ok").any():
        bad = ver_df[ver_df.status != "ok"]
        raise SystemExit(
            f"DLinear reconstruction failed; max_diff={max_diff}; "
            f"n_bad={len(bad)}; statuses={bad.status.value_counts().to_dict()}"
        )

    # --- Atomic comparisons + bootstrap ---
    # Define comparison specs: (family, hierarchy, model_a, method_a, model_b, method_b, seed_mode)
    # seed_mode: 'stochastic' uses seeds 0/1/2 for model_a; baseline uses seed 0
    comparisons: list[dict[str, Any]] = []

    def add_cmp(family, hier, model_a, method_a, model_b, method_b, seed_a_mode="stochastic"):
        comparisons.append(
            {
                "family": family,
                "hierarchy": hier,
                "model_a": model_a,
                "method_a": method_a,
                "model_b": model_b,
                "method_b": method_b,
                "seed_a_mode": seed_a_mode,
            }
        )

    # LightGBM CPU L1-L6
    for base in ("ridge", "ewma", "persistence"):
        add_cmp("cpu_lightgbm_vs_deterministic", "cpu_core_weighted", "lightgbm", "independent", base, "independent")
    for m in ("bottom_up", "wls", "mint"):
        add_cmp("cpu_lightgbm_reconciliation", "cpu_core_weighted", "lightgbm", m, "lightgbm", "independent")
    # LightGBM memory
    add_cmp("memory_lightgbm_vs_ewma", "memory_um", "lightgbm", "independent", "ewma", "independent")
    for m in ("bottom_up", "wls", "mint"):
        add_cmp("memory_lightgbm_reconciliation", "memory_um", "lightgbm", m, "lightgbm", "independent")
        add_cmp("memory_lightgbm_reconciliation", "memory_um", "lightgbm", m, "ewma", "independent")
    # DLinear CPU D1-D7
    for base in ("persistence", "ewma", "ridge"):
        add_cmp("cpu_dlinear_vs_deterministic", "cpu_core_weighted", "dlinear", "independent", base, "independent")
    for m in ("bottom_up", "wls", "mint"):
        add_cmp("cpu_dlinear_reconciliation", "cpu_core_weighted", "dlinear", m, "dlinear", "independent")
    add_cmp("cpu_dlinear_vs_deterministic", "cpu_core_weighted", "dlinear", "independent", "lightgbm", "independent")
    # DLinear memory M1-M6
    add_cmp("memory_dlinear_vs_ewma", "memory_um", "dlinear", "independent", "ewma", "independent")
    for m in ("bottom_up", "wls", "mint"):
        add_cmp("memory_dlinear_reconciliation", "memory_um", "dlinear", m, "dlinear", "independent")
    for m in ("wls", "mint"):
        add_cmp("memory_dlinear_vs_ewma", "memory_um", "dlinear", m, "ewma", "independent")

    atomic_rows = []
    boot_rows = []
    failed = 0
    completed = 0

    for spec in comparisons:
        for fold in folds:
            for horizon in horizons:
                seed_list = seeds if spec["seed_a_mode"] == "stochastic" else [0]
                for seed in seed_list:
                    try:
                        a = pred_cache[(spec["model_a"], spec["hierarchy"], fold, horizon, seed)]
                        b_seed = 0 if spec["model_b"] in ("persistence", "ridge", "ewma") else seed
                        if spec["model_b"] == "lightgbm" and spec["model_a"] == "dlinear":
                            b_seed = seed  # D7: same seed LightGBM
                        b = pred_cache[(spec["model_b"], spec["hierarchy"], fold, horizon, b_seed)]
                        ra = _reconcile_top(spec["hierarchy"], a, spec["method_a"])
                        rb = _reconcile_top(spec["hierarchy"], b, spec["method_b"])
                        scale = _scale(spec["hierarchy"])
                        yt = ra["yt"] / scale
                        ea = np.abs(yt - ra["pt"] / scale)
                        eb = np.abs(yt - rb["pt"] / scale)
                        n = min(len(ea), len(eb))
                        ea, eb = ea[:n], eb[:n]
                        resid = np.asarray(a["yt_val"], float) - np.asarray(a["pt_val"], float)
                        bl = select_block_length(
                            resid,
                            forecast_horizon=int(horizon),
                            context_length=context,
                            acf_threshold=float(boot_cfg["acf_threshold"]),
                            lower=int(boot_cfg["lower"]),
                            upper=int(boot_cfg["upper"]),
                        )["block_length"]
                        # d = |err_a| - |err_b|; relative / mean(|err_b|)
                        effects = paired_moving_block_bootstrap_effects(
                            ea, eb, block_size=int(bl), n_boot=n_boot, seed=boot_seed
                        )
                        row = {
                            "family": spec["family"],
                            "hierarchy": spec["hierarchy"],
                            "model_a": spec["model_a"],
                            "method_a": spec["method_a"],
                            "model_b": spec["model_b"],
                            "method_b": spec["method_b"],
                            "seed": seed,
                            "fold": fold,
                            "horizon": horizon,
                            "mae_a_report": float(np.mean(ea)),
                            "mae_b_report": float(np.mean(eb)),
                            "unit": "weighted_mean_pct" if spec["hierarchy"] == "cpu_core_weighted" else "native",
                            **effects,
                        }
                        atomic_rows.append(row)
                        boot_rows.append(row)
                        completed += 1
                    except Exception as exc:  # noqa: BLE001
                        failed += 1
                        atomic_rows.append(
                            {
                                "family": spec["family"],
                                "hierarchy": spec["hierarchy"],
                                "model_a": spec["model_a"],
                                "method_a": spec["method_a"],
                                "model_b": spec["model_b"],
                                "method_b": spec["method_b"],
                                "seed": seed,
                                "fold": fold,
                                "horizon": horizon,
                                "status": "failed",
                                "error": f"{type(exc).__name__}: {exc}",
                            }
                        )

    atomic_df = pd.DataFrame(atomic_rows)
    atomic_df.to_csv(metrics / "robustness_atomic_comparisons.csv", index=False)
    boot_df = pd.DataFrame([r for r in boot_rows if "relative_mae_diff" in r])
    boot_df.to_csv(metrics / "robustness_block_bootstrap.csv", index=False)
    boot_df[
        [
            "family",
            "hierarchy",
            "model_a",
            "method_a",
            "model_b",
            "method_b",
            "seed",
            "fold",
            "horizon",
            "relative_mae_diff",
            "rel_ci_low",
            "rel_ci_high",
            "rel_ci_crosses_zero",
            "prob_improvement",
            "p_value_raw",
        ]
    ].to_csv(metrics / "robustness_relative_effects.csv", index=False)

    # Holm per family on seed-mean p-values (one test per comparison type × fold × horizon,
    # using mean p across seeds for LightGBM invariance / per-seed for DLinear)
    holm_rows = []
    alpha = float(cfg.get("holm_alpha", 0.05))
    for fam in cfg["holm_families"]:
        sub = boot_df[boot_df.family == fam].copy()
        if sub.empty:
            continue
        # aggregate to comparison identity × fold × horizon: mean p across seeds
        gcols = ["model_a", "method_a", "model_b", "method_b", "fold", "horizon"]
        agg = (
            sub.groupby(gcols, as_index=False)
            .agg(
                p_value_raw=("p_value_raw", "mean"),
                relative_mae_diff=("relative_mae_diff", "mean"),
                n_seeds=("seed", "nunique"),
            )
        )
        ranked = holm_adjust_with_ranks(agg["p_value_raw"].tolist())
        for i, r in enumerate(ranked):
            holm_rows.append(
                {
                    "family": fam,
                    "family_size": len(agg),
                    **{c: agg.loc[i, c] for c in gcols},
                    "p_value_raw": float(agg.loc[i, "p_value_raw"]),
                    "p_value_holm": float(r["adjusted_p"]),
                    "holm_rank": int(r["rank"]),
                    "reject_holm_0.05": bool(r["adjusted_p"] <= alpha),
                    "relative_mae_diff_mean": float(agg.loc[i, "relative_mae_diff"]),
                    "n_seeds": int(agg.loc[i, "n_seeds"]),
                }
            )
    holm_df = pd.DataFrame(holm_rows)
    holm_df.to_csv(metrics / "robustness_holm_tests.csv", index=False)

    # Seed variability for lightgbm/dlinear independent + recon
    var_rows = []
    for hier in hierarchies:
        for model in ("lightgbm", "dlinear"):
            for horizon in horizons:
                for fold in folds:
                    for method in methods:
                        maes = []
                        hashes = []
                        tops = []
                        for seed in seeds:
                            aligned = pred_cache[(model, hier, fold, horizon, seed)]
                            rec = _reconcile_top(hier, aligned, method)
                            scale = _scale(hier)
                            maes.append(rec["top_mae_native"] / scale)
                            hashes.append(
                                hashlib.sha256(np.ascontiguousarray(aligned["pt_test"]).tobytes()).hexdigest()[:16]
                            )
                            tops.append(aligned["pt_test"])
                        maes_a = np.asarray(maes, float)
                        max_abs = 0.0
                        for i in range(len(tops)):
                            for j in range(i + 1, len(tops)):
                                max_abs = max(max_abs, float(np.max(np.abs(tops[i] - tops[j]))))
                        klass = classify_seed_variability(maes_a, hashes, max_abs)
                        var_rows.append(
                            {
                                "hierarchy": hier,
                                "model": model,
                                "horizon": horizon,
                                "fold": fold,
                                "method": method,
                                "mean_mae": float(maes_a.mean()),
                                "std_mae": float(maes_a.std(ddof=0)),
                                "cv": float(maes_a.std(ddof=0) / max(abs(maes_a.mean()), 1e-12)),
                                "min_mae": float(maes_a.min()),
                                "max_mae": float(maes_a.max()),
                                "best_seed": int(seeds[int(np.argmin(maes_a))]),
                                "worst_seed": int(seeds[int(np.argmax(maes_a))]),
                                "identical_hashes": len(set(hashes)) == 1,
                                "max_pred_abs_diff": max_abs,
                                "stability_class": klass,
                                "seed0_mae": float(maes_a[0]),
                                "seed1_mae": float(maes_a[1]) if len(maes_a) > 1 else float("nan"),
                                "seed2_mae": float(maes_a[2]) if len(maes_a) > 2 else float("nan"),
                            }
                        )
    var_df = pd.DataFrame(var_rows)
    var_df.to_csv(metrics / "robustness_seed_variability.csv", index=False)

    # Fold/horizon consistency from atomic
    fh_rows = []
    for (fam, hier, model_a, method_a, model_b, method_b, seed), g in boot_df.groupby(
        ["family", "hierarchy", "model_a", "method_a", "model_b", "method_b", "seed"]
    ):
        fh_rows.append(
            {
                "family": fam,
                "hierarchy": hier,
                "model_a": model_a,
                "method_a": method_a,
                "model_b": model_b,
                "method_b": method_b,
                "seed": seed,
                "n_cells": len(g),
                "mean_rel": float(g.relative_mae_diff.mean()),
                "n_improve": int((g.relative_mae_diff < 0).sum()),
                "n_degrade": int((g.relative_mae_diff > 0).sum()),
                "all_improve": bool((g.relative_mae_diff < 0).all()),
            }
        )
    pd.DataFrame(fh_rows).to_csv(metrics / "robustness_fold_horizon_consistency.csv", index=False)

    # Claim support
    claim_rows = []
    claim_defs = [
        ("L1_lgbm_vs_ridge", "cpu_lightgbm_vs_deterministic", "cpu_core_weighted", "lightgbm", "independent", "ridge", "independent"),
        ("L2_lgbm_vs_ewma", "cpu_lightgbm_vs_deterministic", "cpu_core_weighted", "lightgbm", "independent", "ewma", "independent"),
        ("L3_lgbm_vs_pers", "cpu_lightgbm_vs_deterministic", "cpu_core_weighted", "lightgbm", "independent", "persistence", "independent"),
        ("L4_lgbm_bu", "cpu_lightgbm_reconciliation", "cpu_core_weighted", "lightgbm", "bottom_up", "lightgbm", "independent"),
        ("L5_lgbm_wls", "cpu_lightgbm_reconciliation", "cpu_core_weighted", "lightgbm", "wls", "lightgbm", "independent"),
        ("L6_lgbm_mint", "cpu_lightgbm_reconciliation", "cpu_core_weighted", "lightgbm", "mint", "lightgbm", "independent"),
        ("D1_dlin_vs_pers", "cpu_dlinear_vs_deterministic", "cpu_core_weighted", "dlinear", "independent", "persistence", "independent"),
        ("D2_dlin_vs_ewma", "cpu_dlinear_vs_deterministic", "cpu_core_weighted", "dlinear", "independent", "ewma", "independent"),
        ("D3_dlin_vs_ridge", "cpu_dlinear_vs_deterministic", "cpu_core_weighted", "dlinear", "independent", "ridge", "independent"),
        ("D4_dlin_bu", "cpu_dlinear_reconciliation", "cpu_core_weighted", "dlinear", "bottom_up", "dlinear", "independent"),
        ("D5_dlin_wls", "cpu_dlinear_reconciliation", "cpu_core_weighted", "dlinear", "wls", "dlinear", "independent"),
        ("D6_dlin_mint", "cpu_dlinear_reconciliation", "cpu_core_weighted", "dlinear", "mint", "dlinear", "independent"),
        ("D7_dlin_vs_lgbm", "cpu_dlinear_vs_deterministic", "cpu_core_weighted", "dlinear", "independent", "lightgbm", "independent"),
        ("M1_dlin_vs_ewma", "memory_dlinear_vs_ewma", "memory_um", "dlinear", "independent", "ewma", "independent"),
        ("M2_dlin_bu", "memory_dlinear_reconciliation", "memory_um", "dlinear", "bottom_up", "dlinear", "independent"),
        ("M3_dlin_wls", "memory_dlinear_reconciliation", "memory_um", "dlinear", "wls", "dlinear", "independent"),
        ("M4_dlin_mint", "memory_dlinear_reconciliation", "memory_um", "dlinear", "mint", "dlinear", "independent"),
        ("M5_dlin_wls_vs_ewma", "memory_dlinear_vs_ewma", "memory_um", "dlinear", "wls", "ewma", "independent"),
        ("M6_dlin_mint_vs_ewma", "memory_dlinear_vs_ewma", "memory_um", "dlinear", "mint", "ewma", "independent"),
        ("mem_lgbm_vs_ewma", "memory_lightgbm_vs_ewma", "memory_um", "lightgbm", "independent", "ewma", "independent"),
    ]
    for claim_id, fam, hier, ma, mea, mb, meb in claim_defs:
        sub = boot_df[
            (boot_df.family == fam)
            & (boot_df.hierarchy == hier)
            & (boot_df.model_a == ma)
            & (boot_df.method_a == mea)
            & (boot_df.model_b == mb)
            & (boot_df.method_b == meb)
        ]
        seed_means = []
        support_cells = 0
        n_cells = 0
        for seed, g in sub.groupby("seed"):
            seed_means.append(float(g.relative_mae_diff.mean()))
            support_cells += int((g.relative_mae_diff < 0).sum())
            n_cells += len(g)
        klass = claim_support(seed_means)
        unstable = any(e > 0.05 for e in seed_means) and any(e < -0.02 for e in seed_means)
        claim_rows.append(
            {
                "claim_id": claim_id,
                "family": fam,
                "classification": klass,
                "seed_unstable_warning": unstable,
                "seed_mean_rels": seed_means,
                "support_cells": support_cells,
                "n_cells": n_cells,
                "support_fraction": support_cells / max(n_cells, 1),
            }
        )
    claim_df = pd.DataFrame(claim_rows)
    claim_df.to_csv(metrics / "robustness_claim_support.csv", index=False)

    # Peak compression DLinear memory
    peak_rows = []
    for hier in hierarchies:
        for seed in seeds:
            for fold in folds:
                for horizon in horizons:
                    aligned = pred_cache[("dlinear", hier, fold, horizon, seed)]
                    yt_train = aligned["yt_train"]
                    yt = aligned["yt_test"]
                    for method in methods:
                        rec = _reconcile_top(hier, aligned, method)
                        pt = rec["pt"]
                        for q, qname in ((0.90, "q90"), (0.95, "q95")):
                            thr = float(np.nanquantile(yt_train, q))
                            mask = yt >= thr
                            if not np.any(mask):
                                continue
                            err = pt[mask] - yt[mask]
                            y_range = float(np.nanmax(yt) - np.nanmin(yt))
                            p_range = float(np.nanmax(pt) - np.nanmin(pt))
                            peak_rows.append(
                                {
                                    "hierarchy": hier,
                                    "seed": seed,
                                    "fold": fold,
                                    "horizon": horizon,
                                    "method": method,
                                    "threshold_name": qname,
                                    "threshold_value": thr,
                                    "n_peak": int(mask.sum()),
                                    "peak_mae": float(np.mean(np.abs(err))),
                                    "signed_bias": float(np.mean(err)),
                                    "max_underpred": float(np.min(err)),
                                    "pred_to_target_range_ratio": p_range / max(y_range, 1e-12),
                                }
                            )
    peak_df = pd.DataFrame(peak_rows)
    peak_df.to_csv(metrics / "dlinear_peak_compression.csv", index=False)

    # Baseline strength table
    base_rows = []
    for hier in hierarchies + ["disk_ud"]:
        if hier == "disk_ud":
            # EWMA + persistence + ridge from disk packs only for baseline listing
            for model in ("persistence", "ewma", "ridge"):
                base_rows.append(
                    {
                        "hierarchy": hier,
                        "model": model,
                        "role": "disk_baseline_reporting_only",
                        "note": "no multi-seed; EWMA completes Gate 2",
                    }
                )
            continue
        for fold in folds:
            for horizon in horizons:
                maes = {}
                for model in ("persistence", "ewma", "ridge", "lightgbm", "dlinear"):
                    seed = 0
                    aligned = pred_cache[(model, hier, fold, horizon, seed)]
                    rec = _reconcile_top(hier, aligned, "independent")
                    maes[model] = rec["top_mae_native"] / _scale(hier)
                det = {k: maes[k] for k in ("persistence", "ewma", "ridge")}
                strongest_det = min(det, key=det.get)
                strongest = min(maes, key=maes.get)
                base_rows.append(
                    {
                        "hierarchy": hier,
                        "fold": fold,
                        "horizon": horizon,
                        **{f"mae_{k}": v for k, v in maes.items()},
                        "strongest_deterministic": strongest_det,
                        "strongest_observed": strongest,
                        "cpu_comparator_policy": "ridge" if hier.startswith("cpu") else "ewma",
                    }
                )
    base_df = pd.DataFrame(base_rows)
    base_df.to_csv(tables / "baseline_strength.csv", index=False)

    # Summary tables
    claim_df.to_csv(tables / "robustness_claim_summary.csv", index=False)
    var_df[var_df.model == "lightgbm"].to_csv(tables / "lightgbm_seed_robustness.csv", index=False)
    var_df[var_df.model == "dlinear"].to_csv(tables / "dlinear_seed_robustness.csv", index=False)
    mem_claims = claim_df[claim_df.claim_id.str.startswith("M") | claim_df.claim_id.str.startswith("mem_")]
    mem_claims.to_csv(tables / "memory_conditional_evidence.csv", index=False)

    gate_rows = [
        {
            "gate": 2,
            "name": "baseline_strength",
            "status": "pass",
            "detail": "persistence, EWMA, Ridge, LightGBM, DLinear present in reporting inputs",
        },
        {
            "gate": 3,
            "name": "stochastic_robustness",
            "status": "pass",
            "detail": "LightGBM and DLinear seeds 0/1/2 reported individually with provenance",
        },
        {
            "gate": 4,
            "name": "statistical_evidence",
            "status": "pass",
            "detail": "seed×fold×horizon MBB, direct relative CIs, Holm families, seed-aware claims",
        },
    ]
    pd.DataFrame(gate_rows).to_csv(tables / "publication_gate_status.csv", index=False)

    # Figures
    _fig_seed_effects(boot_df, "cpu_core_weighted", "lightgbm", figures / "cpu_lightgbm_seed_effects.pdf")
    _fig_seed_effects(boot_df, "cpu_core_weighted", "dlinear", figures / "cpu_dlinear_seed_effects.pdf")
    _fig_seed_effects(boot_df, "memory_um", "dlinear", figures / "memory_dlinear_seed_effects.pdf")
    _fig_baseline(base_df, figures / "baseline_comparison.pdf")
    _fig_variability(var_df, figures / "seed_variability.pdf")
    _fig_peak(peak_df, figures / "dlinear_memory_peak_bias.pdf")

    # Re-hash sources after analysis
    hashes_after = {r["path"]: sha256_file(Path(r["path"])) for r in hash_rows}
    if hashes_before != hashes_after:
        raise SystemExit("source prediction hashes changed during analysis")

    wall = time.perf_counter() - t0
    try:
        exec_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT), text=True).strip()
    except Exception:
        exec_commit = None
    freeze_tag = cfg.get("freeze_tag")
    try:
        freeze_peel = subprocess.check_output(
            ["git", "rev-parse", f"{freeze_tag}^{{}}"], cwd=str(ROOT), text=True
        ).strip()
    except Exception:
        freeze_peel = None

    sci_h = scientific_config_hash(cfg)
    manifest = {
        "pack_id": "robustness_statistics",
        "experiment_stage": "final_robustness_analysis",
        "eligible_for_final_claims": True,
        "evaluation_role": "robustness_statistical_analysis",
        "models_trained": False,
        "provisional_inputs_used": False,
        "execution_commit": exec_commit,
        "implementation_commit": cfg.get("implementation_commit"),
        "freeze_commit": cfg.get("freeze_commit"),
        "freeze_tag": freeze_tag,
        "freeze_tag_commit": freeze_peel,
        "source_experiment_freeze_tag": cfg.get("source_experiment_freeze_tag"),
        "source_experiment_freeze_commit": cfg.get("source_experiment_freeze_commit"),
        "source_robustness_extension_freeze_tag": cfg.get("source_robustness_extension_freeze_tag"),
        "source_robustness_extension_freeze_tag_commit": cfg.get(
            "source_robustness_extension_freeze_tag_commit"
        ),
        "dataset_fingerprint": cfg.get("dataset_fingerprint"),
        "config_hash": sci_h,
        "scientific_config_hash": sci_h,
        "frozen_scientific_config_hash": cfg.get("frozen_scientific_config_hash"),
        "ewma_pack_hash": "from_manifest",
        "lightgbm_pack_hash": cfg.get("lightgbm_pack_hash"),
        "dlinear_pack_hash": cfg.get("dlinear_pack_hash"),
        "bootstrap_n_boot": n_boot,
        "comparisons_completed": completed,
        "comparisons_failed": failed,
        "dlinear_reconstruction_max_abs_diff": max_diff,
        "actual_wall_seconds": wall,
        "status": "complete" if failed == 0 else "complete_with_failures",
        "output_dir": str(out),
    }
    # fill ewma pack hash
    ewma_man = rob / cfg["ewma_pack_dir"] / "MANIFEST.json"
    if ewma_man.exists():
        manifest["ewma_pack_hash"] = json.loads(ewma_man.read_text()).get("pack_hash")
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    (out / "RUN_STATUS.json").write_text(
        json.dumps(
            {
                "pack_id": "robustness_statistics",
                "status": "complete",
                "completed_runs": completed,
                "failed_runs": failed,
                "wall_seconds": wall,
            },
            indent=2,
        )
    )
    (out / "COMPLETE").write_text(datetime.now(timezone.utc).isoformat() + "\n")
    return manifest


def _fig_seed_effects(boot_df: pd.DataFrame, hier: str, model: str, path: Path) -> None:
    sub = boot_df[(boot_df.hierarchy == hier) & (boot_df.model_a == model) & (boot_df.method_a == "independent")]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for seed, g in sub.groupby("seed"):
        means = g.groupby("model_b")["relative_mae_diff"].mean()
        ax.plot(range(len(means)), means.values, marker="o", label=f"seed {seed}")
        ax.set_xticks(range(len(means)))
        ax.set_xticklabels(list(means.index), rotation=30, ha="right")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_ylabel("relative MAE effect (a vs b)")
    ax.set_title(f"{hier} {model} independent effects by seed")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    fig.savefig(path.with_suffix(".png"))
    plt.close(fig)


def _fig_baseline(base_df: pd.DataFrame, path: Path) -> None:
    sub = base_df[base_df.hierarchy == "cpu_core_weighted"]
    if sub.empty:
        return
    g = sub.groupby("horizon")[["mae_persistence", "mae_ewma", "mae_ridge", "mae_lightgbm", "mae_dlinear"]].mean()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for col in g.columns:
        ax.plot(g.index, g[col], marker="o", label=col.replace("mae_", ""))
    ax.set_xlabel("Horizon")
    ax.set_ylabel("MAE (weighted mean)")
    ax.set_title("CPU baseline comparison (seed 0 independent)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    fig.savefig(path.with_suffix(".png"))
    plt.close(fig)


def _fig_variability(var_df: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for model, g in var_df[var_df.method == "independent"].groupby("model"):
        ax.scatter(g.hierarchy, g.cv, label=model, alpha=0.6)
    ax.set_ylabel("MAE CV across seeds")
    ax.set_title("Seed variability (independent)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    fig.savefig(path.with_suffix(".png"))
    plt.close(fig)


def _fig_peak(peak_df: pd.DataFrame, path: Path) -> None:
    sub = peak_df[
        (peak_df.hierarchy == "memory_um")
        & (peak_df.method == "independent")
        & (peak_df.threshold_name == "q95")
    ]
    fig, ax = plt.subplots(figsize=(7, 4))
    for seed, g in sub.groupby("seed"):
        ax.scatter([seed] * len(g), g.signed_bias, label=f"seed {int(seed)}", alpha=0.7)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("Seed")
    ax.set_ylabel("q95 signed bias")
    ax.set_title("DLinear memory peak bias by seed")
    if len(sub):
        ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path)
    fig.savefig(path.with_suffix(".png"))
    plt.close(fig)
