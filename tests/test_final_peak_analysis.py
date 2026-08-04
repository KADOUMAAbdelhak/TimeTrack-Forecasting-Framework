"""Tests for frozen final peak-analysis reporting."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from timetrack.peak_reporting import (
    PeakProvenanceError,
    classify_claim,
    load_peak_config,
    metric_close,
    operational_class,
    peak_confusion,
    refuse_outer_threshold,
    run_final_peak_analysis,
    sha256_file,
    train_quantile_threshold,
    validate_peak_config,
    verify_source_pack,
)

ROOT = Path(__file__).resolve().parents[1]


def test_peak_config_validates():
    cfg = load_peak_config()
    assert validate_peak_config(cfg) == []


def test_train_only_threshold_and_refuse_outer():
    rng = np.random.default_rng(0)
    train = rng.normal(size=500)
    test = rng.normal(loc=5.0, size=200)  # shifted — must not be used
    q90 = train_quantile_threshold(train, "q90")
    q95 = train_quantile_threshold(train, "q95")
    assert q90 < q95
    # outer quantile would differ; ensure helper refuses
    with pytest.raises(PeakProvenanceError):
        refuse_outer_threshold(test, "q90")
    with pytest.raises(PeakProvenanceError):
        train_quantile_threshold(train, "outer_q90")


def test_cpu_core_conversion_constant():
    cfg = load_peak_config()
    assert cfg["cpu_core_total"] == 236
    assert cfg["cpu_cores_verified"] == [36, 48, 36, 36, 20, 36, 24]
    assert sum(cfg["cpu_cores_verified"]) == 236


def test_peak_confusion_zero_pred_and_zero_actual():
    y = np.array([0.0, 0.0, 0.0, 1.0])
    yhat = np.array([0.0, 0.0, 0.0, 0.0])
    r = peak_confusion(y, yhat, thr=0.5)
    assert r["precision_valid"] is False
    assert r["recall_valid"] is True
    assert np.isnan(r["precision"])
    assert r["invalid_reason"] == "no_predicted_positives"

    y2 = np.array([0.0, 0.0, 0.0, 0.0])
    yhat2 = np.array([1.0, 0.0, 0.0, 0.0])
    r2 = peak_confusion(y2, yhat2, thr=0.5)
    assert r2["recall_valid"] is False
    assert r2["invalid_reason"] == "no_actual_positives"


def test_timestamp_alignment_required():
    with pytest.raises(PeakProvenanceError, match="timestamp"):
        peak_confusion(np.ones(5), np.ones(4), thr=0.5)


def test_operational_and_claim_classes():
    assert (
        operational_class(d_high_rel=-0.05, d_recall=0.0, d_precision=0.0, d_fa_rel=0.0, coherence_improved=True)
        == "operational_improvement"
    )
    assert (
        operational_class(d_high_rel=-0.05, d_recall=-0.05, d_precision=0.0, d_fa_rel=0.0, coherence_improved=True)
        == "accuracy_focused_tradeoff"
    )
    assert (
        operational_class(d_high_rel=0.0, d_recall=0.05, d_precision=-0.05, d_fa_rel=0.1, coherence_improved=True)
        == "recall_focused_tradeoff"
    )
    assert (
        operational_class(d_high_rel=0.0, d_recall=0.0, d_precision=0.0, d_fa_rel=0.0, coherence_improved=True)
        == "coherence_only"
    )
    assert (
        operational_class(d_high_rel=0.05, d_recall=0.0, d_precision=0.0, d_fa_rel=0.0, coherence_improved=True)
        == "operationally_harmful"
    )
    assert (
        classify_claim(9, 0, 0, horizon_ok=True, fold_ok=True, substantial_contradiction=False) == "supported"
    )
    assert (
        classify_claim(1, 1, 7, horizon_ok=False, fold_ok=False, substantial_contradiction=True) == "contradicted"
    )


def test_metric_close_tolerances():
    assert metric_close(1.0, 1.0 + 1e-12, abs_tol=1e-9, rel_tol=1e-8)
    assert not metric_close(1.0, 1.1, abs_tol=1e-9, rel_tol=1e-8)


def test_provenance_rejects_mixed_and_development():
    cfg = load_peak_config()
    good = {
        "freeze_tag": "experiment-freeze-v2",
        "frozen_implementation_commit": cfg["source_frozen_implementation_commit"],
        "dataset_fingerprint": cfg["dataset_fingerprint"],
        "experiment_stage": "final",
        "eligible_for_final_claims": True,
        "evaluation_role": "outer_evaluation",
        "config_hash": cfg["source_config_hash"],
        "output_dir": "/tmp/results/final/packs/x",
    }
    verify_source_pack(good, cfg, "x")
    bad = dict(good)
    bad["freeze_tag"] = "experiment-freeze-v1"
    with pytest.raises(PeakProvenanceError):
        verify_source_pack(bad, cfg, "x")
    bad2 = dict(good)
    bad2["output_dir"] = "/tmp/results/pilot/x"
    with pytest.raises(PeakProvenanceError):
        verify_source_pack(bad2, cfg, "x")


def _write_smoke_packs(root: Path) -> None:
    from models.hybrid.reconciliation import (
        coherence_error,
        core_weighted_cpu_hierarchy,
        estimate_residual_covariance,
        memory_hierarchy,
        reconcile,
    )
    from timetrack.hierarchy_registry import summing_matrix_hash
    from timetrack.metrics import mae

    cfg = load_peak_config()
    specs = [
        ("memory_classical", "memory_um", memory_hierarchy(), ["persistence", "ridge", "lightgbm"]),
        ("memory_dlinear", "memory_um", memory_hierarchy(), ["dlinear"]),
        ("cpu_classical", "cpu_core_weighted", core_weighted_cpu_hierarchy(), ["persistence", "ridge", "lightgbm"]),
        ("cpu_dlinear", "cpu_core_weighted", core_weighted_cpu_hierarchy(), ["dlinear"]),
    ]
    rng = np.random.default_rng(0)
    for pack_id, hier_name, h, models in specs:
        pred = root / pack_id / "metrics" / "predictions"
        pred.mkdir(parents=True, exist_ok=True)
        man = {
            "pack_id": pack_id,
            "pack_hash": "smoke",
            "freeze_tag": "experiment-freeze-v2",
            "frozen_implementation_commit": cfg["source_frozen_implementation_commit"],
            "implementation_commit": cfg["source_frozen_implementation_commit"],
            "dataset_fingerprint": cfg["dataset_fingerprint"],
            "config_hash": cfg["source_config_hash"],
            "experiment_stage": "final",
            "eligible_for_final_claims": True,
            "evaluation_role": "outer_evaluation",
            "output_dir": str(root / pack_id),
        }
        (root / pack_id / "MANIFEST.json").write_text(json.dumps(man))
        (root / pack_id / "COMPLETE").write_text("smoke\n")
        recon_rows = []
        n_b = h.n_bottom
        smh = summing_matrix_hash(h)
        for model in models:
            for fold in (0, 1, 2):
                for horizon in (1, 8, 16):
                    n = 48
                    yb = rng.normal(10, 1, size=(n, n_b))
                    yt = yb.sum(axis=1)
                    noise = 0.05 if model != "persistence" else 0.0
                    pb = yb + rng.normal(0, noise, size=yb.shape)
                    pt = yt + rng.normal(0, noise, size=yt.shape)
                    yb_val, pb_val = yb[:16], pb[:16]
                    yt_val, pt_val = yt[:16], pt[:16]
                    np.savez_compressed(
                        pred / f"base__{hier_name}__f{fold}__h{horizon}__{model}__s0.npz",
                        yb_test=yb,
                        pb_test=pb,
                        yt_test=yt,
                        pt_test=pt,
                        yb_val=yb_val,
                        pb_val=pb_val,
                        yt_val=yt_val,
                        pt_val=pt_val,
                        yt_train=yt,
                    )
                    cov = estimate_residual_covariance(
                        np.concatenate([yb_val, yt_val.reshape(-1, 1)], 1),
                        np.concatenate([pb_val, pt_val.reshape(-1, 1)], 1),
                        shrink_diag=0.1,
                    )
                    sv = np.maximum(np.diag(cov), 1e-12)
                    for method in ("independent", "bottom_up", "wls", "mint"):
                        out = reconcile(
                            method,
                            h,
                            pb,
                            pt,
                            series_var=sv if method == "wls" else None,
                            residual_cov=cov if method == "mint" else None,
                            nonnegative=False,
                        )
                        recon_rows.append(
                            {
                                "hierarchy": hier_name,
                                "fold": fold,
                                "horizon": horizon,
                                "base_model": model,
                                "reconciliation_method": method,
                                "nonnegative": False,
                                "summing_matrix_hash": smh,
                                "top_mae": float(mae(yt, out["top"])),
                                "bottom_mae_mean": float(
                                    np.mean([mae(yb[:, j], out["bottom"][:, j]) for j in range(n_b)])
                                ),
                                "coherence_error_before": float(coherence_error(pb, pt)),
                                "coherence_error_after": float(coherence_error(out["bottom"], out["top"])),
                            }
                        )
        pd.DataFrame(recon_rows).to_csv(root / pack_id / "metrics" / "reconciliation_results.csv", index=False)


def test_smoke_peak_analysis_and_hashes(tmp_path: Path):
    root = tmp_path / "packs"
    _write_smoke_packs(root)
    before = {str(p): sha256_file(p) for p in root.rglob("*.npz")}
    peak_cfg = load_peak_config()
    source_cfg = {
        "artifact_root": "results/final/packs",
        "context": 32,
        "packs": [
            {"id": "memory_classical", "pack_dir": "01_memory_classical"},
            {"id": "memory_dlinear", "pack_dir": "02_memory_dlinear"},
            {"id": "cpu_classical", "pack_dir": "03_cpu_classical"},
            {"id": "cpu_dlinear", "pack_dir": "04_cpu_dlinear"},
            {"id": "peak_analysis", "pack_dir": "07_peak_analysis"},
        ],
    }
    out = tmp_path / "out"
    result = run_final_peak_analysis(
        peak_cfg=peak_cfg,
        source_cfg=source_cfg,
        output_dir=out,
        smoke=True,
        smoke_pred_root=root,
    )
    assert result["n_rows"] == 576
    assert result["source_hashes_unchanged"] is True
    assert (out / "COMPLETE").exists()
    assert (out / "metrics" / "reconstruction_verification.csv").exists()
    man = json.loads((out / "MANIFEST.json").read_text())
    assert man["evaluation_role"] == "final_peak_analysis"
    assert man["eligible_for_final_claims"] is True
    for p, dig in before.items():
        assert sha256_file(Path(p)) == dig


def test_peak_reporting_no_training_imports():
    path = ROOT / "timetrack" / "peak_reporting.py"
    tree = ast.parse(path.read_text())
    forbidden = {"lightgbm", "torch", "sklearn"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in forbidden
            assert not node.module.startswith("models.baselines")
            assert not node.module.startswith("models.dlinear")


def test_reconstruction_subset_against_accepted_if_present():
    """Spot-check real pack reconstruction when artifacts exist locally."""
    npz = ROOT / "results/final/packs/01_memory_classical/metrics/predictions/base__memory_um__f0__h1__ridge__s0.npz"
    if not npz.exists():
        pytest.skip("accepted predictions not present")
    from models.hybrid.reconciliation import memory_hierarchy
    from timetrack.peak_reporting import reconstruct

    data = np.load(npz)
    h = memory_hierarchy()
    recon_csv = pd.read_csv(ROOT / "results/final/packs/01_memory_classical/metrics/reconciliation_results.csv")
    for method in ("independent", "bottom_up", "wls", "mint"):
        rec = reconstruct(h, data, method)
        row = recon_csv[
            (recon_csv.base_model == "ridge")
            & (recon_csv.fold == 0)
            & (recon_csv.horizon == 1)
            & (recon_csv.reconciliation_method == method)
            & (recon_csv.nonnegative == False)  # noqa: E712
        ].iloc[0]
        assert metric_close(rec["top_mae"], float(row.top_mae), abs_tol=1e-9, rel_tol=1e-8)
        assert metric_close(rec["bottom_mae_mean"], float(row.bottom_mae_mean), abs_tol=1e-9, rel_tol=1e-8)
