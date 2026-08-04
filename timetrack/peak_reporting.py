"""Frozen peak analysis for experiment-freeze-v2 predictions.

Consumes stored outer NPZs only. Reconstructs reconciliation, verifies against
accepted pack metrics, then scores exact-timestamp peak metrics. Never trains.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

from models.hybrid.reconciliation import (
    coherence_error,
    core_weighted_cpu_hierarchy,
    estimate_residual_covariance,
    machine_core_counts,
    memory_hierarchy,
    reconcile,
)
from timetrack.hierarchy_registry import summing_matrix_hash
from timetrack.metrics import mae

ROOT = Path(__file__).resolve().parents[1]


class PeakProvenanceError(ValueError):
    pass


class ReconstructionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_array(arr: np.ndarray) -> str:
    a = np.ascontiguousarray(np.asarray(arr, dtype=np.float64))
    return hashlib.sha256(a.tobytes()).hexdigest()


def config_hash(cfg: dict[str, Any]) -> str:
    return hashlib.sha256(yaml.safe_dump(cfg, sort_keys=True).encode()).hexdigest()[:16]


def load_peak_config(path: Path | None = None) -> dict[str, Any]:
    path = path or (ROOT / "configs" / "final_peak_analysis.yaml")
    return yaml.safe_load(path.read_text())


def validate_peak_config(cfg: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    required = {
        "peak_analysis_freeze_tag",
        "source_experiment_freeze_tag",
        "source_frozen_implementation_commit",
        "dataset_fingerprint",
        "source_packs",
        "models",
        "horizons",
        "folds",
        "methods",
        "thresholds",
        "peak_matching",
        "threshold_policy",
        "reconstruction",
        "expected_atomic_rows",
        "cpu_core_total",
    }
    missing = required - set(cfg)
    if missing:
        errs.append(f"missing keys: {sorted(missing)}")
    if cfg.get("peak_matching") != "exact_timestamp":
        errs.append("peak_matching must be exact_timestamp")
    if cfg.get("threshold_policy") != "outer_train_quantile_only":
        errs.append("threshold_policy must be outer_train_quantile_only")
    if list(cfg.get("thresholds") or []) != ["q90", "q95"]:
        errs.append("thresholds must be [q90, q95]")
    if list(cfg.get("methods") or []) != ["independent", "bottom_up", "wls", "mint"]:
        errs.append("methods must be [independent, bottom_up, wls, mint]")
    if int(cfg.get("expected_atomic_rows", 0)) != 576:
        errs.append("expected_atomic_rows must be 576")
    if int(cfg.get("cpu_core_total", 0)) != 236:
        errs.append("cpu_core_total must be 236")
    if cfg.get("source_experiment_freeze_tag") != "experiment-freeze-v2":
        errs.append("source freeze must be experiment-freeze-v2")
    cores = list(cfg.get("cpu_cores_verified") or [])
    if cores and cores != [36, 48, 36, 36, 20, 36, 24]:
        errs.append("cpu_cores_verified must match verified mapping")
    return errs


def _git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def train_quantile_threshold(y_train: np.ndarray, mode: str) -> float:
    if mode not in {"q90", "q95"}:
        raise PeakProvenanceError(f"forbidden threshold mode: {mode}")
    tr = np.asarray(y_train, dtype=float).reshape(-1)
    tr = tr[np.isfinite(tr)]
    if len(tr) == 0:
        raise PeakProvenanceError("empty training target for threshold")
    q = 0.90 if mode == "q90" else 0.95
    return float(np.quantile(tr, q))


def refuse_outer_threshold(y_test: np.ndarray, mode: str) -> None:
    """Guard: never derive publication thresholds from outer labels."""
    raise PeakProvenanceError(f"outer-derived threshold refused for {mode}; use train only")


def metric_close(a: float, b: float, *, abs_tol: float, rel_tol: float) -> bool:
    if not np.isfinite(a) or not np.isfinite(b):
        return bool(np.isnan(a) and np.isnan(b))
    diff = abs(float(a) - float(b))
    if diff <= abs_tol:
        return True
    scale = max(abs(float(a)), abs(float(b)), 1e-18)
    return (diff / scale) <= rel_tol


def peak_confusion(y: np.ndarray, yhat: np.ndarray, thr: float) -> dict[str, Any]:
    y = np.asarray(y, dtype=float).reshape(-1)
    yhat = np.asarray(yhat, dtype=float).reshape(-1)
    if y.shape != yhat.shape:
        raise PeakProvenanceError("timestamp length mismatch")
    actual = y >= thr
    pred = yhat >= thr
    tp = int(np.sum(actual & pred))
    fp = int(np.sum(~actual & pred))
    fn = int(np.sum(actual & ~pred))
    tn = int(np.sum(~actual & ~pred))
    n_actual = int(np.sum(actual))
    n_pred = int(np.sum(pred))
    precision_valid = n_pred > 0
    recall_valid = n_actual > 0
    precision = float(tp / n_pred) if precision_valid else float("nan")
    recall = float(tp / n_actual) if recall_valid else float("nan")
    if precision_valid and recall_valid and (precision + recall) > 0:
        f1 = float(2 * precision * recall / (precision + recall))
        f1_valid = True
    else:
        f1 = float("nan")
        f1_valid = False
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else float("nan")
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else float("nan")
    high = actual
    low = ~actual
    high_mae = float(np.mean(np.abs(y[high] - yhat[high]))) if high.any() else float("nan")
    low_mae = float(np.mean(np.abs(y[low] - yhat[low]))) if low.any() else float("nan")
    if high.any():
        err = yhat[high] - y[high]
        mag_mae = float(np.mean(np.abs(err)))
        bias = float(np.mean(err))
        max_under = float(np.min(err))  # most negative = underprediction
        max_over = float(np.max(err))
        ratio = float(np.mean(yhat[high] / np.maximum(y[high], 1e-18)))
    else:
        mag_mae = bias = max_under = max_over = ratio = float("nan")
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "n_actual_peaks": n_actual,
        "n_predicted_peaks": n_pred,
        "precision": precision,
        "precision_valid": precision_valid,
        "recall": recall,
        "recall_valid": recall_valid,
        "f1": f1,
        "f1_valid": f1_valid,
        "specificity": specificity,
        "false_positive_rate": fpr,
        "high_load_mae": high_mae,
        "low_load_mae": low_mae,
        "peak_magnitude_mae": mag_mae,
        "signed_peak_bias": bias,
        "max_underprediction": max_under,
        "max_overprediction": max_over,
        "predicted_actual_peak_ratio": ratio,
        "invalid_reason": (
            None
            if (precision_valid and recall_valid)
            else (
                "no_actual_positives"
                if not recall_valid
                else ("no_predicted_positives" if not precision_valid else None)
            )
        ),
    }


def operational_class(
    *,
    d_high_rel: float,
    d_recall: float,
    d_precision: float,
    d_fa_rel: float,
    coherence_improved: bool,
) -> str:
    """Classify recon vs independent peak trade-off (negative d_high_rel = MAE improvement)."""
    mae_imp = d_high_rel < -0.02
    mae_deg = d_high_rel > 0.02
    mae_neu = abs(d_high_rel) <= 0.02
    rec_imp = d_recall > 0.02
    rec_deg = d_recall < -0.02
    rec_neu = abs(d_recall) <= 0.02
    prec_deg = d_precision < -0.02
    fa_inc = d_fa_rel > 0.05
    fa_neu = abs(d_fa_rel) <= 0.05 if np.isfinite(d_fa_rel) else True

    if mae_imp and (not rec_deg) and (not fa_inc) and coherence_improved:
        return "operational_improvement"
    if rec_imp and (fa_inc or prec_deg):
        return "recall_focused_tradeoff"
    if mae_imp and rec_deg:
        return "accuracy_focused_tradeoff"
    if mae_neu and rec_neu and abs(d_precision) <= 0.02 and coherence_improved:
        return "coherence_only"
    if mae_deg or rec_deg or (fa_inc and not mae_imp and not rec_imp):
        return "operationally_harmful"
    if mae_imp and coherence_improved:
        return "operational_improvement"
    return "operationally_harmful"


def classify_claim(
    n_sup: int, n_unc: int, n_con: int, *, horizon_ok: bool, fold_ok: bool, substantial_contradiction: bool
) -> str:
    n = n_sup + n_unc + n_con
    if n == 0:
        return "unsupported"
    if n_con > n_sup and (substantial_contradiction or n_con >= max(1, n // 2)):
        return "contradicted"
    frac = n_sup / n
    if frac >= 0.80 and n_con == 0 and horizon_ok and fold_ok and not substantial_contradiction:
        return "supported"
    if n_sup > (n_unc + n_con) or frac > 0.5:
        return "partially_supported"
    if n_con > n_sup:
        return "contradicted"
    return "unsupported"


def _verify_recon_source_unchanged() -> None:
    diff = _git(["diff", "9f1bebb", "HEAD", "--", "models/hybrid/reconciliation.py"])
    if diff.strip():
        raise PeakProvenanceError("reconciliation.py differs from experiment-freeze-v2 implementation commit")


def _load_manifest(pack_dir: Path) -> dict[str, Any]:
    path = pack_dir / "MANIFEST.json"
    if not path.exists():
        raise PeakProvenanceError(f"missing MANIFEST: {pack_dir}")
    return json.loads(path.read_text())


def verify_source_pack(man: dict[str, Any], cfg: dict[str, Any], pack_id: str) -> None:
    impl = man.get("frozen_implementation_commit") or man.get("implementation_commit") or man.get("freeze_commit")
    if impl != cfg["source_frozen_implementation_commit"]:
        raise PeakProvenanceError(f"{pack_id}: implementation mismatch")
    if man.get("freeze_tag") != "experiment-freeze-v2":
        raise PeakProvenanceError(f"{pack_id}: freeze_tag")
    if man.get("dataset_fingerprint") != cfg["dataset_fingerprint"]:
        raise PeakProvenanceError(f"{pack_id}: fingerprint")
    if man.get("experiment_stage") != "final" or not bool(man.get("eligible_for_final_claims")):
        raise PeakProvenanceError(f"{pack_id}: not final-eligible")
    if man.get("evaluation_role") != "outer_evaluation":
        raise PeakProvenanceError(f"{pack_id}: evaluation_role")
    if man.get("config_hash") != cfg.get("source_config_hash"):
        raise PeakProvenanceError(f"{pack_id}: config_hash")
    out = str(man.get("output_dir") or "")
    if "results/development" in out or "results/pilot" in out:
        raise PeakProvenanceError(f"{pack_id}: development/pilot path")


def load_npz(pack_dirs: list[Path], model: str, fold: int, horizon: int) -> tuple[Any, Path]:
    for p in pack_dirs:
        pred = p / "metrics" / "predictions"
        if not pred.exists():
            continue
        matches = sorted(pred.glob(f"base__*__f{fold}__h{horizon}__{model}__s0.npz"))
        if matches:
            return np.load(matches[0]), matches[0]
    raise PeakProvenanceError(f"missing NPZ model={model} fold={fold} h={horizon}")


def reconstruct(h, data, method: str, *, shrink_diag: float = 0.1) -> dict[str, Any]:
    yb, pb = data["yb_test"], data["pb_test"]
    yt, pt = data["yt_test"], data["pt_test"]
    y_full = np.concatenate([data["yb_val"], np.asarray(data["yt_val"]).reshape(-1, 1)], 1)
    p_full = np.concatenate([data["pb_val"], np.asarray(data["pt_val"]).reshape(-1, 1)], 1)
    cov = estimate_residual_covariance(y_full, p_full, shrink_diag=shrink_diag)
    series_var = np.maximum(np.diag(cov), 1e-12)
    out = reconcile(
        method,
        h,
        pb,
        pt,
        series_var=series_var if method == "wls" else None,
        residual_cov=cov if method == "mint" else None,
        nonnegative=False,
    )
    bottom_mae_mean = float(
        np.mean([mae(yb[:, j], out["bottom"][:, j]) for j in range(yb.shape[1])])
    )
    adj = float(np.mean(np.abs(np.asarray(out["top"]).reshape(-1) - np.asarray(pt).reshape(-1))))
    return {
        "yt": np.asarray(yt, dtype=float).reshape(-1),
        "pt": np.asarray(out["top"], dtype=float).reshape(-1),
        "yb": np.asarray(yb, dtype=float),
        "pb": np.asarray(out["bottom"], dtype=float),
        "pt_ind": np.asarray(pt, dtype=float).reshape(-1),
        "pb_ind": np.asarray(pb, dtype=float),
        "top_mae": float(mae(yt, out["top"])),
        "bottom_mae_mean": bottom_mae_mean,
        "coherence_before": float(coherence_error(pb, pt)),
        "coherence_after": float(coherence_error(out["bottom"], out["top"])),
        "adjustment_magnitude": adj,
        "series_var": series_var,
        "cov": cov,
        "nonnegative": False,
    }


def run_final_peak_analysis(
    *,
    peak_cfg: dict[str, Any],
    source_cfg: dict[str, Any],
    output_dir: Path,
    smoke: bool = False,
    smoke_pred_root: Path | None = None,
) -> dict[str, Any]:
    errs = validate_peak_config(peak_cfg)
    if errs and not smoke:
        raise ValueError("invalid final_peak_analysis config: " + "; ".join(errs))
    if not smoke:
        _verify_recon_source_unchanged()

    t0 = time.perf_counter()
    cpu0 = time.process_time()
    start_iso = datetime.now(timezone.utc).isoformat()

    artifact_root = ROOT / (source_cfg.get("artifact_root") or "results/final/packs")
    pack_dirs_map = {p["id"]: p["pack_dir"] for p in source_cfg["packs"]}
    source_pack_ids = list(peak_cfg["source_packs"])
    abs_tol = float(peak_cfg["reconstruction"]["abs_tol"])
    rel_tol = float(peak_cfg["reconstruction"]["rel_tol"])
    sampling = float(peak_cfg.get("sampling_seconds", 42.285166))
    core_total = float(peak_cfg["cpu_core_total"])
    shrink = float(peak_cfg.get("mint_shrink_diag", 0.1))

    # Provenance + hashes
    source_pack_hashes: dict[str, str] = {}
    hash_rows = []
    pred_before: dict[str, str] = {}
    accepted_recon: dict[str, pd.DataFrame] = {}

    for pid in source_pack_ids:
        if smoke and smoke_pred_root is not None:
            pdir = smoke_pred_root / pid
        else:
            pdir = artifact_root / pack_dirs_map[pid]
        man = _load_manifest(pdir)
        if not smoke:
            verify_source_pack(man, peak_cfg, pid)
            source_pack_hashes[pid] = man.get("pack_hash")
        recon_path = pdir / "metrics" / "reconciliation_results.csv"
        if recon_path.exists():
            accepted_recon[pid] = pd.read_csv(recon_path)
        pred_dir = pdir / "metrics" / "predictions"
        if not pred_dir.exists():
            raise PeakProvenanceError(f"{pid}: missing predictions")
        for npz in sorted(pred_dir.glob("*.npz")):
            dig = sha256_file(npz)
            pred_before[str(npz.resolve())] = dig
            hash_rows.append(
                {
                    "source_pack": pid,
                    "path": str(npz.relative_to(ROOT)) if str(npz).startswith(str(ROOT)) else str(npz),
                    "sha256": dig,
                    "bytes": npz.stat().st_size,
                }
            )

    cores = machine_core_counts()
    verified = [cores[f"machine0{i}"] for i in range(1, 8)]
    if verified != [36, 48, 36, 36, 20, 36, 24]:
        raise PeakProvenanceError(f"core mapping mismatch: {verified}")
    if abs(sum(verified) - core_total) > 1e-9:
        raise PeakProvenanceError("cpu_core_total mismatch vs verified cores")

    hier_specs = {
        "memory_um": {
            "hierarchy": memory_hierarchy(),
            "packs": ["memory_classical", "memory_dlinear"],
            "scale": 1.0,
            "unit": "memory_bytes",
        },
        "cpu_core_weighted": {
            "hierarchy": core_weighted_cpu_hierarchy(),
            "packs": ["cpu_classical", "cpu_dlinear"],
            "scale": core_total,
            "unit": "cpu_weighted_mean_pct",
        },
    }
    for name, spec in hier_specs.items():
        smh = summing_matrix_hash(spec["hierarchy"])
        spec["summing_matrix_hash"] = smh

    def paths_for(pack_ids: list[str]) -> list[Path]:
        if smoke and smoke_pred_root is not None:
            return [smoke_pred_root / pid for pid in pack_ids]
        return [artifact_root / pack_dirs_map[pid] for pid in pack_ids]

    models = list(peak_cfg["models"])
    horizons = [int(h) for h in peak_cfg["horizons"]]
    folds = [int(f) for f in peak_cfg["folds"]]
    methods = list(peak_cfg["methods"])
    thresholds = list(peak_cfg["thresholds"])

    recon_rows = []
    thr_rows = []
    metric_rows = []
    # cache thresholds per hierarchy×fold (train target shared across models for same fold — use persistence train)
    thr_cache: dict[tuple[str, int, str], float] = {}
    thr_meta: dict[tuple[str, int], dict[str, Any]] = {}

    # First pass: reconstruction verification for all cells
    for hier_name, spec in hier_specs.items():
        h = spec["hierarchy"]
        scale = float(spec["scale"])
        for model in models:
            for horizon in horizons:
                for fold in folds:
                    data, npz_path = load_npz(paths_for(spec["packs"]), model, fold, horizon)
                    # matrix hash check vs accepted row
                    for method in methods:
                        rec = reconstruct(h, data, method, shrink_diag=shrink)
                        # find accepted row
                        accepted = None
                        for pid in spec["packs"]:
                            adf = accepted_recon.get(pid)
                            if adf is None:
                                continue
                            sub = adf[
                                (adf.hierarchy == hier_name)
                                & (adf.base_model == model)
                                & (adf.fold == fold)
                                & (adf.horizon == horizon)
                                & (adf.reconciliation_method == method)
                                & (adf.nonnegative == False)  # noqa: E712
                            ]
                            if not sub.empty:
                                accepted = sub.iloc[0]
                                break
                        if accepted is None and not smoke:
                            raise ReconstructionError(
                                f"missing accepted recon row {hier_name} {model} f{fold} h{horizon} {method}"
                            )
                        diffs = {}
                        ok = True
                        if accepted is not None:
                            for key, col in [
                                ("top_mae", "top_mae"),
                                ("bottom_mae_mean", "bottom_mae_mean"),
                                ("coherence_before", "coherence_error_before"),
                                ("coherence_after", "coherence_error_after"),
                            ]:
                                a = float(rec[key])
                                b = float(accepted[col])
                                close = metric_close(a, b, abs_tol=abs_tol, rel_tol=rel_tol)
                                diffs[f"diff_{key}"] = a - b
                                diffs[f"ok_{key}"] = close
                                ok = ok and close
                            # summing matrix hash
                            if str(accepted.get("summing_matrix_hash")) != str(spec["summing_matrix_hash"]):
                                # classical packs use same hash abe0cd1cb9555ccb for sum hierarchies
                                if not smoke:
                                    raise ReconstructionError(
                                        f"summing_matrix_hash mismatch {accepted.get('summing_matrix_hash')} "
                                        f"vs {spec['summing_matrix_hash']}"
                                    )
                            if bool(accepted.get("nonnegative")):
                                raise ReconstructionError("accepted row has nonnegative=True; refused")
                        if not ok and peak_cfg["reconstruction"].get("require_match", True) and not smoke:
                            raise ReconstructionError(
                                f"reconstruction mismatch {hier_name} {model} f{fold} h{horizon} {method}: {diffs}"
                            )
                        recon_rows.append(
                            {
                                "hierarchy": hier_name,
                                "base_model": model,
                                "horizon": horizon,
                                "fold": fold,
                                "method": method,
                                "npz_path": str(npz_path),
                                "summing_matrix_hash": spec["summing_matrix_hash"],
                                "top_mae_recon": rec["top_mae"],
                                "bottom_mae_mean_recon": rec["bottom_mae_mean"],
                                "coherence_before_recon": rec["coherence_before"],
                                "coherence_after_recon": rec["coherence_after"],
                                "adjustment_magnitude": rec["adjustment_magnitude"],
                                "nonnegative": False,
                                "match_ok": ok if accepted is not None else True,
                                **diffs,
                            }
                        )

                    # thresholds from train (weighted-mean for CPU)
                    yt_train = np.asarray(data["yt_train"], dtype=float).reshape(-1) / scale
                    key_meta = (hier_name, fold)
                    if key_meta not in thr_meta:
                        thr_meta[key_meta] = {
                            "training_n": int(len(yt_train)),
                            "training_target_hash": sha256_array(yt_train),
                            "training_start_timestamp": "not_stored_in_npz",
                            "training_end_timestamp": "not_stored_in_npz",
                        }
                    for mode in thresholds:
                        tk = (hier_name, fold, mode)
                        if tk not in thr_cache:
                            thr_cache[tk] = train_quantile_threshold(yt_train, mode)
                            thr_rows.append(
                                {
                                    "hierarchy": hier_name,
                                    "fold": fold,
                                    "threshold_type": mode,
                                    "threshold_value": thr_cache[tk],
                                    "training_sample_count": thr_meta[key_meta]["training_n"],
                                    "training_start_timestamp": thr_meta[key_meta]["training_start_timestamp"],
                                    "training_end_timestamp": thr_meta[key_meta]["training_end_timestamp"],
                                    "training_target_hash": thr_meta[key_meta]["training_target_hash"],
                                    "unit": spec["unit"],
                                }
                            )

    # Second pass: peak metrics (reuse reconstruct)
    for hier_name, spec in hier_specs.items():
        h = spec["hierarchy"]
        scale = float(spec["scale"])
        for model in models:
            for horizon in horizons:
                for fold in folds:
                    data, npz_path = load_npz(paths_for(spec["packs"]), model, fold, horizon)
                    ind = reconstruct(h, data, "independent", shrink_diag=shrink)
                    for method in methods:
                        rec = reconstruct(h, data, method, shrink_diag=shrink) if method != "independent" else ind
                        # peak on scaled tops
                        yt = rec["yt"] / scale
                        pt = rec["pt"] / scale
                        days = max((len(yt) * sampling) / 86400.0, 1e-9)
                        for mode in thresholds:
                            thr = thr_cache[(hier_name, fold, mode)]
                            cm = peak_confusion(yt, pt, thr)
                            fa_day = float(cm["fp"] / days)
                            metric_rows.append(
                                {
                                    "hierarchy": hier_name,
                                    "unit": spec["unit"],
                                    "base_model": model,
                                    "horizon": horizon,
                                    "fold": fold,
                                    "method": method,
                                    "threshold": mode,
                                    "threshold_value": thr,
                                    "n_paired": int(len(yt)),
                                    "eval_days": days,
                                    "y_min": float(np.min(yt)),
                                    "y_max": float(np.max(yt)),
                                    "yhat_min": float(np.min(pt)),
                                    "yhat_max": float(np.max(pt)),
                                    "coherence_error": rec["coherence_after"],
                                    "false_alarms_per_day": fa_day,
                                    "npz_path": str(npz_path),
                                    **cm,
                                }
                            )

    recon_df = pd.DataFrame(recon_rows)
    thr_df = pd.DataFrame(thr_rows).drop_duplicates(["hierarchy", "fold", "threshold_type"])
    met_df = pd.DataFrame(metric_rows)
    expected = int(peak_cfg.get("expected_atomic_rows", 576))
    if not smoke and len(met_df) != expected:
        raise RuntimeError(f"expected {expected} atomic rows, got {len(met_df)}")

    # Method comparisons vs independent
    comp_rows = []
    for (hier, model, horizon, fold, mode), g in met_df.groupby(
        ["hierarchy", "base_model", "horizon", "fold", "threshold"]
    ):
        base = g[g.method == "independent"]
        if base.empty:
            continue
        b = base.iloc[0]
        for method in ["bottom_up", "wls", "mint"]:
            sub = g[g.method == method]
            if sub.empty:
                continue
            r = sub.iloc[0]
            d_high = float(r.high_load_mae - b.high_load_mae) if np.isfinite(r.high_load_mae) and np.isfinite(b.high_load_mae) else float("nan")
            d_high_rel = d_high / b.high_load_mae if np.isfinite(d_high) and abs(b.high_load_mae) > 1e-18 else float("nan")
            d_prec = float(r.precision - b.precision) if r.precision_valid and b.precision_valid else float("nan")
            d_rec = float(r.recall - b.recall) if r.recall_valid and b.recall_valid else float("nan")
            d_f1 = float(r.f1 - b.f1) if r.f1_valid and b.f1_valid else float("nan")
            d_fa = float(r.false_alarms_per_day - b.false_alarms_per_day)
            d_fa_rel = d_fa / b.false_alarms_per_day if abs(b.false_alarms_per_day) > 1e-18 else (0.0 if abs(d_fa) < 1e-18 else float("inf"))
            d_bias = float(r.signed_peak_bias - b.signed_peak_bias) if np.isfinite(r.signed_peak_bias) and np.isfinite(b.signed_peak_bias) else float("nan")
            d_mag = float(r.peak_magnitude_mae - b.peak_magnitude_mae) if np.isfinite(r.peak_magnitude_mae) and np.isfinite(b.peak_magnitude_mae) else float("nan")
            coh_imp = float(r.coherence_error) < float(b.coherence_error) - 1e-12 or (
                float(r.coherence_error) < 1e-6 and float(b.coherence_error) >= 1e-6
            )
            # also treat exact coherence after recon as improved if before was incoherent
            if float(r.coherence_error) < 1e-6:
                coh_imp = True
            ocls = operational_class(
                d_high_rel=d_high_rel if np.isfinite(d_high_rel) else 0.0,
                d_recall=d_rec if np.isfinite(d_rec) else 0.0,
                d_precision=d_prec if np.isfinite(d_prec) else 0.0,
                d_fa_rel=d_fa_rel if np.isfinite(d_fa_rel) else 0.0,
                coherence_improved=bool(coh_imp),
            )
            comp_rows.append(
                {
                    "hierarchy": hier,
                    "base_model": model,
                    "horizon": horizon,
                    "fold": fold,
                    "threshold": mode,
                    "method": method,
                    "delta_high_load_mae": d_high,
                    "rel_delta_high_load_mae": d_high_rel,
                    "delta_precision": d_prec,
                    "delta_recall": d_rec,
                    "delta_f1": d_f1,
                    "delta_false_alarms_per_day": d_fa,
                    "rel_delta_false_alarms_per_day": d_fa_rel,
                    "delta_signed_peak_bias": d_bias,
                    "delta_peak_magnitude_mae": d_mag,
                    "coherence_independent": float(b.coherence_error),
                    "coherence_method": float(r.coherence_error),
                    "coherence_improved": bool(coh_imp),
                    "operational_class": ocls,
                }
            )
    comp_df = pd.DataFrame(comp_rows)

    # Fold/horizon consistency summaries
    fc_rows = []
    for (hier, model, method, mode), g in comp_df.groupby(["hierarchy", "base_model", "method", "threshold"]):
        def wtl(series_imp, series_deg, series_tie):
            return int(series_imp.sum()), int(series_tie.sum()), int(series_deg.sum())

        mae_imp = g.rel_delta_high_load_mae < -0.02
        mae_deg = g.rel_delta_high_load_mae > 0.02
        mae_tie = (~mae_imp) & (~mae_deg)
        rec_imp = g.delta_recall > 0.02
        rec_deg = g.delta_recall < -0.02
        rec_tie = (~rec_imp) & (~rec_deg) | g.delta_recall.isna()
        # fix rec_tie
        rec_tie = g.delta_recall.apply(lambda x: abs(x) <= 0.02 if np.isfinite(x) else True)
        rec_imp = g.delta_recall.apply(lambda x: x > 0.02 if np.isfinite(x) else False)
        rec_deg = g.delta_recall.apply(lambda x: x < -0.02 if np.isfinite(x) else False)
        prec_imp = g.delta_precision.apply(lambda x: x > 0.02 if np.isfinite(x) else False)
        prec_deg = g.delta_precision.apply(lambda x: x < -0.02 if np.isfinite(x) else False)
        prec_tie = g.delta_precision.apply(lambda x: abs(x) <= 0.02 if np.isfinite(x) else True)
        fa_imp = g.rel_delta_false_alarms_per_day.apply(lambda x: x < -0.05 if np.isfinite(x) else False)  # fewer FA = win
        fa_deg = g.rel_delta_false_alarms_per_day.apply(lambda x: x > 0.05 if np.isfinite(x) else False)
        fa_tie = g.rel_delta_false_alarms_per_day.apply(lambda x: abs(x) <= 0.05 if np.isfinite(x) else True)
        mode_class = g.operational_class.mode().iloc[0] if len(g) else "operationally_harmful"
        fc_rows.append(
            {
                "hierarchy": hier,
                "base_model": model,
                "method": method,
                "threshold": mode,
                "n_cells": len(g),
                "high_load_wins": int(mae_imp.sum()),
                "high_load_ties": int(mae_tie.sum()),
                "high_load_losses": int(mae_deg.sum()),
                "recall_wins": int(rec_imp.sum()),
                "recall_ties": int(rec_tie.sum()),
                "recall_losses": int(rec_deg.sum()),
                "precision_wins": int(prec_imp.sum()),
                "precision_ties": int(prec_tie.sum()),
                "precision_losses": int(prec_deg.sum()),
                "false_alarm_wins": int(fa_imp.sum()),
                "false_alarm_ties": int(fa_tie.sum()),
                "false_alarm_losses": int(fa_deg.sum()),
                "best_rel_high_load": float(g.rel_delta_high_load_mae.min()),
                "worst_rel_high_load": float(g.rel_delta_high_load_mae.max()),
                "median_rel_high_load": float(g.rel_delta_high_load_mae.median()) if g.rel_delta_high_load_mae.notna().any() else float("nan"),
                "median_delta_recall": float(g.delta_recall.dropna().median()) if g.delta_recall.notna().any() else float("nan"),
                "operational_class_mode": mode_class,
                "recurring_fail_fold": int(g.loc[g.rel_delta_high_load_mae.fillna(0).idxmax(), "fold"]) if len(g) else -1,
                "recurring_fail_horizon": int(g.loc[g.rel_delta_high_load_mae.fillna(0).idxmax(), "horizon"]) if len(g) else -1,
            }
        )
    fc_df = pd.DataFrame(fc_rows)

    # Claims P1–P5
    atomic = []

    def add_atoms(claim: str, mask: pd.Series, effect_col: str, improve_if_negative: bool) -> None:
        sub = comp_df[mask] if effect_col.startswith("rel_") or effect_col.startswith("delta_") else met_df[mask]
        src = comp_df if claim != "P3" else met_df
        sub = src[mask]
        for _, r in sub.iterrows():
            if claim == "P3":
                # handled separately
                continue
            val = float(r[effect_col])
            if not np.isfinite(val):
                verdict = "uncertain"
            elif improve_if_negative:
                if val < -0.02:
                    verdict = "support"
                elif val > 0.02:
                    verdict = "contradict"
                else:
                    verdict = "uncertain"
            else:
                # positive effect desired (e.g. recall increase)
                if val > 0.02:
                    verdict = "support"
                elif val < -0.02:
                    verdict = "contradict"
                else:
                    verdict = "uncertain"
            # P2 also requires FA not materially up
            if claim == "P2" and verdict == "support":
                fa = float(r.rel_delta_false_alarms_per_day)
                if np.isfinite(fa) and fa > 0.05:
                    verdict = "uncertain"
            atomic.append(
                {
                    "claim": claim,
                    "hierarchy": r.hierarchy,
                    "base_model": r.base_model,
                    "horizon": int(r.horizon),
                    "fold": int(r.fold),
                    "method": r.method if hasattr(r, "method") else r.get("method"),
                    "threshold": r.threshold,
                    "effect": val,
                    "verdict": verdict,
                }
            )

    # P1: CPU high-load MAE reduction for learned models
    add_atoms(
        "P1",
        (comp_df.hierarchy == "cpu_core_weighted")
        & (comp_df.base_model.isin(["ridge", "lightgbm", "dlinear"]))
        & (comp_df.method.isin(["bottom_up", "wls", "mint"])),
        "rel_delta_high_load_mae",
        True,
    )
    # P2: CPU recall preserve/improve without FA increase
    add_atoms(
        "P2",
        (comp_df.hierarchy == "cpu_core_weighted")
        & (comp_df.base_model.isin(["ridge", "lightgbm", "dlinear"]))
        & (comp_df.method.isin(["bottom_up", "wls", "mint"])),
        "delta_recall",
        False,
    )
    # P3: LightGBM strongest CPU high-load among independent models
    for thr in thresholds:
        for horizon in horizons:
            for fold in folds:
                sub = met_df[
                    (met_df.hierarchy == "cpu_core_weighted")
                    & (met_df.method == "independent")
                    & (met_df.threshold == thr)
                    & (met_df.horizon == horizon)
                    & (met_df.fold == fold)
                    & (met_df.base_model.isin(["persistence", "ridge", "lightgbm", "dlinear"]))
                ]
                if sub.empty or sub.high_load_mae.isna().all():
                    continue
                best = sub.loc[sub.high_load_mae.idxmin()]
                lgbm = sub[sub.base_model == "lightgbm"]
                if lgbm.empty:
                    continue
                lg = lgbm.iloc[0]
                # support if lightgbm has lowest (or within 2%) high-load MAE
                min_mae = float(sub.high_load_mae.min())
                rel = (float(lg.high_load_mae) - min_mae) / max(min_mae, 1e-18)
                verdict = "support" if rel <= 0.02 else "contradict"
                atomic.append(
                    {
                        "claim": "P3",
                        "hierarchy": "cpu_core_weighted",
                        "base_model": "lightgbm",
                        "horizon": horizon,
                        "fold": fold,
                        "method": "independent",
                        "threshold": thr,
                        "effect": -rel,  # negative = closer to best
                        "verdict": verdict,
                        "best_model": best.base_model,
                        "lgbm_high_load_mae": float(lg.high_load_mae),
                        "best_high_load_mae": min_mae,
                    }
                )
    # P4: memory WLS/MinT high-load for ridge/dlinear
    add_atoms(
        "P4",
        (comp_df.hierarchy == "memory_um")
        & (comp_df.base_model.isin(["ridge", "dlinear"]))
        & (comp_df.method.isin(["wls", "mint"])),
        "rel_delta_high_load_mae",
        True,
    )
    # P5: DLinear memory peak underprediction; recon mitigates or preserves bias
    for thr in thresholds:
        for horizon in horizons:
            for fold in folds:
                for method in methods:
                    sub = met_df[
                        (met_df.hierarchy == "memory_um")
                        & (met_df.base_model == "dlinear")
                        & (met_df.threshold == thr)
                        & (met_df.horizon == horizon)
                        & (met_df.fold == fold)
                        & (met_df.method == method)
                    ]
                    if sub.empty:
                        continue
                    r = sub.iloc[0]
                    bias = float(r.signed_peak_bias)
                    # underpredict => bias < 0
                    if method == "independent":
                        verdict = "support" if bias < 0 else ("contradict" if bias > 0 else "uncertain")
                        atomic.append(
                            {
                                "claim": "P5",
                                "hierarchy": "memory_um",
                                "base_model": "dlinear",
                                "horizon": horizon,
                                "fold": fold,
                                "method": method,
                                "threshold": thr,
                                "effect": bias,
                                "verdict": verdict,
                                "aspect": "independent_underprediction",
                            }
                        )
                    else:
                        ind = met_df[
                            (met_df.hierarchy == "memory_um")
                            & (met_df.base_model == "dlinear")
                            & (met_df.threshold == thr)
                            & (met_df.horizon == horizon)
                            & (met_df.fold == fold)
                            & (met_df.method == "independent")
                        ].iloc[0]
                        # mitigate if bias less negative (closer to 0 from below) or preserve if still negative and not worse by >10% of |ind|
                        ib = float(ind.signed_peak_bias)
                        if ib >= 0:
                            verdict = "uncertain"
                        elif bias >= ib - 0.1 * abs(ib):  # not substantially more underpredictive
                            verdict = "support"
                        else:
                            verdict = "contradict"
                        atomic.append(
                            {
                                "claim": "P5",
                                "hierarchy": "memory_um",
                                "base_model": "dlinear",
                                "horizon": horizon,
                                "fold": fold,
                                "method": method,
                                "threshold": thr,
                                "effect": bias - ib,
                                "verdict": verdict,
                                "aspect": "recon_vs_independent_bias",
                            }
                        )

    atom_df = pd.DataFrame(atomic)

    def summarize_claim(cid: str, title: str, qualification: str) -> dict[str, Any]:
        sub = atom_df[atom_df.claim == cid]
        n_sup = int((sub.verdict == "support").sum())
        n_unc = int((sub.verdict == "uncertain").sum())
        n_con = int((sub.verdict == "contradict").sum())
        effects = sub.effect.astype(float)
        horizon_ok = True
        fold_ok = True
        for _, hg in sub.groupby("horizon"):
            if (hg.verdict == "support").mean() < 0.5:
                horizon_ok = False
        fold_maj = sub.groupby("fold").apply(lambda x: (x.verdict == "support").mean() >= 0.5)
        if int(fold_maj.sum()) < min(2, len(fold_maj)):
            fold_ok = False
        substantial = bool(((sub.verdict == "contradict") & (sub.effect.abs() >= 0.05)).any())
        return {
            "claim": cid,
            "title": title,
            "support": classify_claim(
                n_sup, n_unc, n_con, horizon_ok=horizon_ok, fold_ok=fold_ok, substantial_contradiction=substantial
            ),
            "n_atomic": len(sub),
            "n_support": n_sup,
            "n_uncertain": n_unc,
            "n_contradict": n_con,
            "median_effect": float(effects.median()) if len(sub) else float("nan"),
            "min_effect": float(effects.min()) if len(sub) else float("nan"),
            "max_effect": float(effects.max()) if len(sub) else float("nan"),
            "fold_consistency": "ok" if fold_ok else "inconsistent",
            "horizon_consistency": "ok" if horizon_ok else "inconsistent",
            "qualification": qualification,
        }

    claim_df = pd.DataFrame(
        [
            summarize_claim("P1", "CPU recon reduces high-load MAE for learned models", "Persistence excluded from positive claim."),
            summarize_claim("P2", "CPU recon preserves/improves recall without FA increase", "FA materiality threshold +5%."),
            summarize_claim("P3", "LightGBM strongest CPU high-load among independents", "Within 2% of best high-load MAE counts as support."),
            summarize_claim("P4", "Memory WLS/MinT reduce high-load MAE for Ridge/DLinear", "LightGBM not in claim scope."),
            summarize_claim("P5", "DLinear memory peak underprediction; recon mitigates/preserves", "Independent bias must be negative."),
        ]
    )

    # Write outputs
    out = Path(output_dir)
    met = out / "metrics"
    tab = out / "tables"
    fig = out / "figures"
    for d in (met, tab, fig):
        d.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(hash_rows).to_csv(met / "source_prediction_hashes.csv", index=False)
    recon_df.to_csv(met / "reconstruction_verification.csv", index=False)
    thr_df.to_csv(met / "peak_thresholds.csv", index=False)
    met_df.to_csv(met / "peak_metrics.csv", index=False)
    comp_df.to_csv(met / "peak_method_comparisons.csv", index=False)
    fc_df.to_csv(met / "peak_fold_consistency.csv", index=False)
    claim_df.to_csv(met / "peak_claim_support.csv", index=False)
    atom_df.to_csv(met / "peak_claim_atomic.csv", index=False)

    # tables
    main = (
        met_df.groupby(["hierarchy", "base_model", "method", "threshold"], as_index=False)
        .agg(
            high_load_mae=("high_load_mae", "mean"),
            precision=("precision", "mean"),
            recall=("recall", "mean"),
            f1=("f1", "mean"),
            false_alarms_per_day=("false_alarms_per_day", "mean"),
            peak_magnitude_mae=("peak_magnitude_mae", "mean"),
            signed_peak_bias=("signed_peak_bias", "mean"),
        )
    )
    main.to_csv(tab / "peak_main_comparison.csv", index=False)
    fc_df.to_csv(tab / "peak_operational_classification.csv", index=False)
    claim_df.to_csv(tab / "peak_claim_support.csv", index=False)

    # figures
    def scatter_pr(ax, hier, title):
        sub = met_df[(met_df.hierarchy == hier) & (met_df.base_model != "persistence")]
        for method, marker in [("independent", "o"), ("bottom_up", "s"), ("wls", "^"), ("mint", "D")]:
            s = sub[sub.method == method]
            ax.scatter(s.recall, s.precision, label=method, alpha=0.6, marker=marker)
        ax.set_xlabel("recall")
        ax.set_ylabel("precision")
        ax.set_title(title)
        ax.legend(fontsize=7)
        ax.set_xlim(0, 1.05)
        ax.set_ylim(0, 1.05)

    for hier, name in [("cpu_core_weighted", "cpu_peak_precision_recall"), ("memory_um", "memory_peak_precision_recall")]:
        fig_p, ax = plt.subplots(figsize=(6, 5))
        scatter_pr(ax, hier, name)
        fig_p.tight_layout()
        fig_p.savefig(fig / f"{name}.pdf")
        fig_p.savefig(fig / f"{name}.png")
        plt.close(fig_p)

    fig_p, ax = plt.subplots(figsize=(8, 5))
    for hier, marker in [("cpu_core_weighted", "o"), ("memory_um", "s")]:
        s = comp_df[comp_df.hierarchy == hier]
        ax.scatter(s.method, s.rel_delta_high_load_mae, alpha=0.5, marker=marker, label=hier)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylabel("rel Δ high-load MAE (recon−ind)/ind")
    ax.set_title("Peak high-load MAE change")
    ax.legend(fontsize=8)
    fig_p.tight_layout()
    fig_p.savefig(fig / "peak_high_load_mae.pdf")
    fig_p.savefig(fig / "peak_high_load_mae.png")
    plt.close(fig_p)

    fig_p, ax = plt.subplots(figsize=(8, 5))
    for hier, marker in [("cpu_core_weighted", "o"), ("memory_um", "s")]:
        s = comp_df[comp_df.hierarchy == hier]
        ax.scatter(s.method, s.delta_false_alarms_per_day, alpha=0.5, marker=marker, label=hier)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylabel("Δ false alarms / day")
    ax.set_title("False-alarm change vs independent")
    ax.legend(fontsize=8)
    fig_p.tight_layout()
    fig_p.savefig(fig / "peak_false_alarms.pdf")
    fig_p.savefig(fig / "peak_false_alarms.png")
    plt.close(fig_p)

    fig_p, ax = plt.subplots(figsize=(8, 5))
    s = met_df[met_df.base_model != "persistence"]
    ax.scatter(s.base_model + "/" + s.method, s.signed_peak_bias, alpha=0.35)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylabel("signed peak bias (pred−actual)")
    ax.set_title("Peak magnitude bias")
    ax.tick_params(axis="x", labelrotation=90, labelsize=6)
    fig_p.tight_layout()
    fig_p.savefig(fig / "peak_magnitude_bias.pdf")
    fig_p.savefig(fig / "peak_magnitude_bias.png")
    plt.close(fig_p)

    # hash unchanged
    changed = [p for p, d in pred_before.items() if sha256_file(Path(p)) != d]
    if changed:
        raise RuntimeError(f"source predictions modified: {changed[:3]}")

    end_iso = datetime.now(timezone.utc).isoformat()
    wall = time.perf_counter() - t0
    cpu = time.process_time() - cpu0
    try:
        exec_commit = _git(["rev-parse", "HEAD"])
    except Exception:
        exec_commit = "UNKNOWN"
    try:
        peak_tag_commit = _git(["rev-parse", "final-peak-analysis-freeze-v1^{commit}"])
    except Exception:
        try:
            peak_tag_commit = _git(["rev-parse", "final-peak-analysis-freeze-v1"])
        except Exception:
            peak_tag_commit = peak_cfg.get("peak_analysis_freeze_tag_commit") or "PENDING_UNTIL_TAG"
    try:
        src_tag = _git(["rev-parse", "experiment-freeze-v2^{commit}"])
    except Exception:
        src_tag = peak_cfg.get("source_experiment_freeze_tag_commit")

    pch = config_hash(peak_cfg)
    manifest = {
        "pack_id": "peak_analysis",
        "required": True,
        "dependencies": source_pack_ids,
        "experiment_stage": "final",
        "eligible_for_final_claims": True,
        "evaluation_role": "final_peak_analysis",
        "source_experiment_freeze_tag": peak_cfg["source_experiment_freeze_tag"],
        "source_experiment_freeze_tag_commit": src_tag,
        "source_frozen_implementation_commit": peak_cfg["source_frozen_implementation_commit"],
        "peak_analysis_freeze_tag": peak_cfg.get("peak_analysis_freeze_tag", "final-peak-analysis-freeze-v1"),
        "peak_analysis_freeze_tag_commit": peak_tag_commit,
        "peak_analysis_implementation_commit": peak_cfg.get("peak_analysis_implementation_commit") or exec_commit,
        "execution_commit": exec_commit,
        "freeze_tag": peak_cfg["source_experiment_freeze_tag"],
        "freeze_commit": peak_cfg["source_frozen_implementation_commit"],
        "implementation_commit": peak_cfg["source_frozen_implementation_commit"],
        "frozen_implementation_commit": peak_cfg["source_frozen_implementation_commit"],
        "dataset_fingerprint": peak_cfg["dataset_fingerprint"],
        "config_hash": peak_cfg.get("source_config_hash"),
        "peak_config_hash": pch,
        "source_pack_hashes": source_pack_hashes,
        "start_time": start_iso,
        "end_time": end_iso,
        "actual_wall_seconds": wall,
        "cpu_seconds": cpu,
        "atomic_rows_expected": expected,
        "atomic_rows_completed": int(len(met_df)),
        "atomic_rows_failed": 0,
        "reconstruction_max_abs_top_mae_diff": float(recon_df["diff_top_mae"].abs().max()) if "diff_top_mae" in recon_df else 0.0,
        "status": "complete",
        "output_dir": str(out.resolve()),
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "RUN_STATUS.json").write_text(
        json.dumps(
            {
                "pack_id": "peak_analysis",
                "status": "complete",
                "completed_runs": ["peak_analysis"],
                "failed_runs": [],
                "total_runs": 1,
                "wall_seconds": wall,
                "cpu_seconds": cpu,
                "start_time": start_iso,
                "end_time": end_iso,
            },
            indent=2,
        )
        + "\n"
    )
    (out / "COMPLETE").write_text(end_iso + "\n")

    return {
        "manifest": manifest,
        "claims": claim_df,
        "n_rows": len(met_df),
        "wall_seconds": wall,
        "reconstruction_max_abs_top_mae_diff": manifest["reconstruction_max_abs_top_mae_diff"],
        "source_hashes_unchanged": True,
    }
