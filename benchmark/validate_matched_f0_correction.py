#!/usr/bin/env python3
"""Independent validation of the Phase 2B-1 matched-F0 correction."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark.run_matched_f0_correction import arrays, index_hash, support_sets
from benchmark.src.data import PANEL_PATH, load_canonical_panel, sha256_file, verify_raw_hashes
from benchmark.src.metrics import per_lead_metrics, relative_mae_change
from benchmark.src.models.ridge import RidgeForecaster
from benchmark.src.selection import select_from_inner_validation
from benchmark.src.windows import FUTURE_LEADS


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmark" / "phase2b1_corrected"
OUTPUTS = BASE / "outputs"
ORIGINAL = ROOT / "benchmark" / "outputs"
ORIGINAL_AUDIT = ROOT / "benchmark" / "phase2b1_original"
MANIFEST = ROOT / "benchmark" / "PHASE2A_FREEZE_MANIFEST.md"
DECISION_SHA256 = "72b5bf5b984c5eeb5b8d4b21b83f9b2fa9807f6fc944c79ee5edc89aeb33dd8e"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def frozen_hashes() -> tuple[int, list[dict[str, str]]]:
    rows = re.findall(r"\| `([^`]+)`(?: \([^)]*\))? \|(?: [\d,]+ \|)? `([0-9a-f]{64})` \|", MANIFEST.read_text())
    selected = []
    for relative, expected in rows:
        if relative.startswith(("benchmark/src/", "benchmark/tests/", "data/raw/")) or relative in {
            "benchmark/PROTOCOL.md", "benchmark/configs/benchmark.json",
            "discovery/02_dependency_analysis/outputs/canonical_panel.parquet",
            "discovery/02_dependency_analysis/outputs/canonical_signal_registry.csv",
            "discovery/02_dependency_analysis/PROTOCOL.md",
            "discovery/03_rolling_robustness/ROLLING_PROTOCOL.md",
        }:
            selected.append((relative, expected))
    failures = []
    for relative, expected in selected:
        actual = sha(ROOT / relative)
        if actual != expected:
            failures.append({"path": relative, "expected": expected, "actual": actual})
    return len(selected), failures


def original_integrity() -> tuple[int, list[dict[str, str]]]:
    inventory = pd.read_csv(ORIGINAL_AUDIT / "HEAVY_ARTIFACT_SHA256.csv")
    failures = []
    for row in inventory.itertuples(index=False):
        path = ROOT / row.path
        if not path.exists() or path.stat().st_size != int(row.size_bytes) or sha(path) != row.sha256:
            failures.append({"path": row.path})
    return len(inventory), failures


def main() -> None:
    failures = []
    maxima = {"metric_abs_difference": 0.0, "ridge_prediction_abs_difference": 0.0, "gain_abs_difference": 0.0}
    panel = load_canonical_panel()
    support = pd.read_parquet(BASE / "matched_support_manifest.parquet")
    registry = pd.read_csv(OUTPUTS / "matched_f0_run_registry.csv")
    selected = pd.read_csv(OUTPUTS / "matched_f0_selected_configs.csv")
    metrics = pd.read_parquet(OUTPUTS / "matched_f0_metrics.parquet")
    corrected = pd.read_parquet(OUTPUTS / "corrected_context_matched_metrics.parquet")
    original_registry = pd.read_csv(ORIGINAL / "run_registry.csv").set_index("run_id")
    runtime = json.loads((OUTPUTS / "runtime_accounting.json").read_text())
    support_index = support.set_index(["model", "candidate_feature_set", "machine", "fold"])
    selected_index = selected.set_index(["model", "candidate_feature_set", "machine", "outer_fold"])
    if sha(BASE / "PROSPECTIVE_MATCHED_F0_DECISION.md") != DECISION_SHA256:
        failures.append("prospective decision hash")
    if len(support) != 350 or len(registry) != 350 or len(selected) != 350 or len(metrics) != 2800 or len(corrected) != 2800:
        failures.append("output row counts")
    if registry.run_id.duplicated().any() or set(registry.status) != {"completed"}:
        failures.append("registry identity/status")
    if len(list((OUTPUTS / "matched_f0_predictions").glob("*.parquet"))) != 350:
        failures.append("prediction file count")
    if runtime["completed_comparators"] != 350 or runtime["failed_or_missing_comparators"] != 0:
        failures.append("runtime completion state")
    if runtime["inner_candidate_fits"] != 6825 or runtime["inner_lead_models"] != 33600 or runtime["final_models"] != 1575:
        failures.append("fit accounting")

    for run in registry.itertuples(index=False):
        key = (run.model, run.candidate_feature_set, run.machine, int(run.outer_fold))
        row = support_index.loc[key]
        sets = support_sets(panel, run.machine, run.candidate_feature_set, int(run.outer_fold), int(row.candidate_context_length))
        for name in ["inner_train", "inner_validation", "final_train", "test"]:
            expected = row[f"{name}_hash"]
            if index_hash(sets[name]) != expected or getattr(run, f"{name}_hash") != expected:
                failures.append(f"support hash {run.run_id}/{name}")
        progress_path = OUTPUTS / "selection_progress" / run.model / f"{run.machine}_{run.candidate_feature_set}_fold{int(run.outer_fold)}.json"
        progress = json.loads(progress_path.read_text())
        scores = pd.DataFrame(progress["scores"])
        expected_count = 15 if run.model == "Ridge" else 24
        if len(scores) != expected_count:
            failures.append(f"selection grid count {run.run_id}")
        if set(scores.context_length) != {32, 64, 128}:
            failures.append(f"selection lengths {run.run_id}")
        if run.model == "Ridge":
            if set(scores.alpha) != {0.01, 0.1, 1.0, 10.0, 100.0}:
                failures.append(f"Ridge grid {run.run_id}")
        else:
            grid = set(zip(scores.num_leaves, scores.learning_rate, scores.n_estimators))
            expected_grid = {(nl, lr, ne) for nl in [15, 31] for lr in [0.03, 0.05] for ne in [200, 400]}
            if grid != expected_grid:
                failures.append(f"LightGBM grid {run.run_id}")
        chosen = select_from_inner_validation(scores, run.model)
        stored = selected_index.loc[key]
        if int(chosen.context_length) != int(stored.context_length) or abs(float(chosen.inner_validation_mae) - float(stored.inner_validation_mae)) > 1e-12:
            failures.append(f"selection reproduction {run.run_id}")
        if bool(stored.outer_test_columns_available_to_selector):
            failures.append(f"outer test selection {run.run_id}")

        prediction = pd.read_parquet(ROOT / run.prediction_path)
        candidate_run = original_registry.loc[run.candidate_run_id]
        candidate = pd.read_parquet(ROOT / candidate_run.prediction_path)
        if not np.array_equal(prediction.sample_id.to_numpy(), candidate.sample_id.to_numpy()):
            failures.append(f"sample IDs {run.run_id}")
        if not np.array_equal(prediction.y_true.to_numpy(), candidate.y_true.to_numpy()):
            failures.append(f"targets {run.run_id}")
        if not np.array_equal(prediction.target_timestamp.to_numpy(), candidate.target_timestamp.to_numpy()):
            failures.append(f"target timestamps {run.run_id}")
        pivot_t = prediction.pivot(index="origin_index", columns="lead", values="y_true").reindex(columns=FUTURE_LEADS)
        pivot_p = prediction.pivot(index="origin_index", columns="lead", values="y_pred").reindex(columns=FUTURE_LEADS)
        computed = per_lead_metrics(pivot_t.to_numpy(), pivot_p.to_numpy()).set_index("lead")
        saved = metrics[metrics.run_id == run.run_id].set_index("lead")
        maxima["metric_abs_difference"] = max(maxima["metric_abs_difference"], float(np.nanmax(np.abs(computed[["mae", "rmse", "r2"]].to_numpy() - saved[["mae", "rmse", "r2"]].to_numpy()))))
        if run.model == "Ridge":
            X_train, y_train = arrays(panel, run.machine, int(run.context_length), sets["final_train"])
            X_test, _ = arrays(panel, run.machine, int(run.context_length), sets["test"])
            model = RidgeForecaster(alpha=json.loads(run.config_json)["alpha"]).fit(X_train, y_train)
            reproduced = model.predict(X_test)
            maxima["ridge_prediction_abs_difference"] = max(maxima["ridge_prediction_abs_difference"], float(np.max(np.abs(reproduced - pivot_p.to_numpy()))))

    for row in corrected.itertuples(index=False):
        expected = relative_mae_change(row.matched_f0_mae, row.candidate_mae)
        maxima["gain_abs_difference"] = max(maxima["gain_abs_difference"], abs(expected - row.corrected_context_mae_gain_pct))
        if not row.sample_ids_exact_match or not row.targets_exact_match:
            failures.append(f"corrected alignment {row.matched_f0_run_id}")
    if maxima["metric_abs_difference"] > 1e-4: failures.append("metric recomputation")
    if maxima["ridge_prediction_abs_difference"] > 1e-10: failures.append("Ridge reproduction")
    if maxima["gain_abs_difference"] > 1e-10: failures.append("gain recomputation")

    frozen_count, frozen_failures = frozen_hashes()
    original_count, original_failures = original_integrity()
    if frozen_failures: failures.append("frozen hash integrity")
    if original_failures: failures.append("original artifact integrity")
    if not verify_raw_hashes(): failures.append("raw hashes")
    validation = {
        "status": "PASS" if not failures else "FAIL",
        "decision_sha256": DECISION_SHA256,
        "support_comparisons": len(support), "support_hash_failures": sum(x.startswith("support hash") for x in failures),
        "completed_comparators": len(registry), "failed_comparators": runtime["failed_or_missing_comparators"],
        "ridge_comparators": int((registry.model == "Ridge").sum()), "lightgbm_comparators": int((registry.model == "LightGBM").sum()),
        "inner_ridge_fits": 2625, "final_ridge_fits": 175,
        "inner_lightgbm_lead_models": 33600, "final_lightgbm_lead_models": 1400,
        "candidate_reruns": 0, "outer_test_controlled_selection": False,
        "prediction_files": len(list((OUTPUTS / "matched_f0_predictions").glob("*.parquet"))),
        "sample_id_mismatches": sum(x.startswith("sample IDs") for x in failures),
        "target_mismatches": sum(x.startswith("targets") for x in failures),
        "maximum_differences": maxima,
        "frozen_hashes_checked": frozen_count, "frozen_hash_failures": frozen_failures,
        "raw_hashes_unchanged": verify_raw_hashes(), "canonical_panel_sha256": sha256_file(PANEL_PATH),
        "original_heavy_artifacts_checked": original_count, "original_heavy_artifact_failures": original_failures,
        "failures": failures,
    }
    (OUTPUTS / "correction_validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps(validation, indent=2))
    if failures:
        raise RuntimeError("Matched-F0 correction validation failed")


if __name__ == "__main__":
    main()
