#!/usr/bin/env python3
"""Independent validation for Phase 2B-2A3 PatchTST scientific outputs."""

from __future__ import annotations

import inspect
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark.neural_v2.src.data import CONTEXT_LENGTHS, EXPECTED_PANEL_SHA256, FUTURE_LEADS, load_canonical_panel, sample_set_hash
from benchmark.neural_v2.src.metrics import per_lead_metrics
from benchmark.neural_v2.src.splits import build_supported_folds
from benchmark.neural_v2.src.training import FeatureStandardizer, fit_final_fixed_epochs
from benchmark.neural_v2.src.validation import atomic_json_write, run_id
from benchmark.neural_v2.patchtst_aggregation import aggregation_summary
from benchmark.neural_v2.validate_dlinear_scientific import phase2a_hashes, sha256, verify_inventory
from benchmark.src.data import PANEL_PATH, verify_raw_hashes


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "benchmark/neural_v2/outputs/patchtst"
NEURAL_INVENTORY = ROOT / "benchmark/neural_v2/NEURAL_V2_ARTIFACT_SHA256.csv"
DLINEAR_INVENTORY = ROOT / "benchmark/neural_v2/DLINEAR_SCIENTIFIC_ARTIFACT_SHA256.csv"
LSTM_INVENTORY = ROOT / "benchmark/neural_v2/LSTM_SCIENTIFIC_ARTIFACT_SHA256.csv"
ORIGINAL_INVENTORY = ROOT / "benchmark/phase2b1_original/HEAVY_ARTIFACT_SHA256.csv"
CORRECTED_INVENTORY = ROOT / "benchmark/phase2b1_corrected/CORRECTION_ARTIFACT_SHA256.csv"
CRITERIA = ROOT / "benchmark/neural_v2/PATCHTST_DECISION_CRITERIA.md"
EXPECTED_CRITERIA_HASH = "c431f575706dd013a43ebedbd5ac695a6c615d3855b5bba709372afb82273203"
FEATURES = ("F0_LOCAL", "F1_THROUGHPUT")
MACHINES = tuple(f"machine{number:02d}" for number in range(1, 8))
SEEDS = (0, 1, 2)


def main() -> None:
    started = time.perf_counter()
    failures: list[str] = []
    structural = {
        "segment_crossing_histories": 0,
        "segment_crossing_targets": 0,
        "outer_target_time_leakage": 0,
        "inner_target_time_leakage": 0,
        "support_hash_mismatches": 0,
        "sample_id_mismatches": 0,
        "timestamp_mismatches": 0,
        "selected_L_mismatches": 0,
        "selected_epoch_mismatches": 0,
        "run_id_mismatches": 0,
        "prediction_hash_mismatches": 0,
    }
    maxima = {"metric_abs_difference": 0.0, "target_abs_difference": 0.0, "aggregation_abs_difference": 0.0, "pooled_direct_abs_difference": 0.0}
    panel = load_canonical_panel()
    timestamps = panel.timestamp.to_numpy()
    segments = panel.segment_id.to_numpy()
    registry = pd.read_csv(OUT / "run_registry.csv")
    inner = pd.read_parquet(OUT / "inner_selection_runs.parquet")
    selected = pd.read_csv(OUT / "selected_contexts.csv")
    epochs = pd.read_csv(OUT / "selected_epochs.csv")
    metrics = pd.read_parquet(OUT / "metrics.parquet")
    predictions = sorted((OUT / "predictions").glob("*.parquet"))
    figures = sorted((OUT / "figures").glob("*.png"))

    run_keys = {(f, m, fold, seed) for f in FEATURES for m in MACHINES for fold in range(1, 6) for seed in SEEDS}
    metric_keys = {(*key, lead) for key in run_keys for lead in FUTURE_LEADS}
    observed_runs = set(zip(registry.feature_set, registry.machine, registry.fold, registry.seed))
    observed_metrics = set(zip(metrics.feature_set, metrics.machine, metrics.fold, metrics.seed, metrics.lead))
    expected_counts = {"inner": 630, "runs": 210, "metrics": 1680, "selected": 70, "predictions": 210, "figures": 6}
    actual_counts = {"inner": len(inner), "runs": len(registry), "metrics": len(metrics), "selected": len(selected), "predictions": len(predictions), "figures": len(figures)}
    if actual_counts != expected_counts: failures.append("artifact counts")
    if observed_runs != run_keys or observed_metrics != metric_keys: failures.append("run/metric coverage")
    if registry.run_id.duplicated().any(): failures.append("duplicate run IDs")

    fold_cache = {}
    for machine in MACHINES:
        for length in CONTEXT_LENGTHS:
            folds = build_supported_folds(panel, machine, length)
            fold_cache[(machine, length)] = folds
            for fold in folds:
                for origins in (fold.inner_train_indices, fold.inner_validation_indices, fold.outer_train_indices, fold.outer_test_indices):
                    histories = origins[:, None] - np.arange(length - 1, -1, -1)
                    targets = origins[:, None] + np.asarray(FUTURE_LEADS)
                    structural["segment_crossing_histories"] += int(np.sum(~np.all(segments[histories] == segments[origins, None], axis=1)))
                    structural["segment_crossing_targets"] += int(np.sum(~np.all(segments[targets] == segments[origins, None], axis=1)))
                structural["outer_target_time_leakage"] += int(fold.outer_train_indices[-1] + max(FUTURE_LEADS) >= fold.outer_test_indices[0])
                structural["inner_target_time_leakage"] += int(fold.inner_train_indices[-1] + max(FUTURE_LEADS) >= fold.inner_validation_indices[0])

    support_columns = ("inner_train_hash", "inner_validation_hash", "final_train_hash", "test_hash")
    for key, group in inner.groupby(["machine", "fold", "context_length", "seed"]):
        if len(group) != 2 or set(group.feature_set) != set(FEATURES):
            structural["support_hash_mismatches"] += 1
            continue
        structural["support_hash_mismatches"] += sum(group[column].nunique() != 1 for column in support_columns)
        machine, fold_number, length, _seed = key
        fold = fold_cache[(machine, int(length))][int(fold_number) - 1]
        expected = {
            "inner_train_hash": sample_set_hash(fold.inner_train_indices),
            "inner_validation_hash": sample_set_hash(fold.inner_validation_indices),
            "final_train_hash": sample_set_hash(fold.outer_train_indices),
            "test_hash": sample_set_hash(fold.outer_test_indices),
        }
        structural["support_hash_mismatches"] += sum(not (group[column] == value).all() for column, value in expected.items())

    for key, group in inner.groupby(["feature_set", "machine", "fold"]):
        scores = []
        for length, rows in group.groupby("context_length"):
            scores.append((float(np.asarray(rows.validation_mae_by_lead.tolist(), dtype=float).mean()), int(length)))
        expected_L = min(scores)[1]
        stored = selected[(selected.feature_set == key[0]) & (selected.machine == key[1]) & (selected.fold == key[2])]
        structural["selected_L_mismatches"] += int(len(stored) != 1 or int(stored.iloc[0].selected_L) != expected_L)
    selected_index = selected.set_index(["feature_set", "machine", "fold"])
    inner_index = inner.set_index(["feature_set", "machine", "fold", "context_length", "seed"])
    for row in epochs.itertuples(index=False):
        length = int(selected_index.loc[(row.feature_set, row.machine, row.fold)].selected_L)
        epoch = int(inner_index.loc[(row.feature_set, row.machine, row.fold, length, row.seed)].best_epoch)
        structural["selected_epoch_mismatches"] += int(row.selected_L != length or row.selected_epoch != epoch)

    metric_index = metrics.set_index(["run_id", "lead"])
    pooled_sums = {(feature, lead): [0.0, 0] for feature in FEATURES for lead in FUTURE_LEADS}
    required_schema = {"run_id", "model", "feature_set", "machine", "fold", "seed", "selected_L", "selected_epoch", "lead", "origin_timestamp", "target_timestamp", "sample_id", "y_true", "y_pred"}
    for row in registry.itertuples(index=False):
        payload = {"model": row.model, "feature_set": row.feature_set, "machine": row.machine, "fold": int(row.fold), "seed": int(row.seed), "selected_L": int(row.selected_L), "selected_epoch": int(row.selected_epoch)}
        structural["run_id_mismatches"] += int(run_id(payload) != row.run_id)
        path = ROOT / row.prediction_path
        if not path.exists() or sha256(path) != row.prediction_sha256:
            structural["prediction_hash_mismatches"] += 1
            continue
        frame = pd.read_parquet(path)
        if not required_schema.issubset(frame.columns): failures.append(f"prediction schema {row.run_id}")
        if frame.duplicated(["sample_id", "lead"]).any(): structural["sample_id_mismatches"] += 1
        origin = frame.origin_index.to_numpy(dtype=np.int64); lead = frame.lead.to_numpy(dtype=np.int64); target = frame.target_index.to_numpy(dtype=np.int64)
        structural["timestamp_mismatches"] += int(not np.array_equal(target, origin + lead))
        structural["timestamp_mismatches"] += int(not np.array_equal(frame.origin_timestamp.to_numpy(), timestamps[origin]))
        structural["timestamp_mismatches"] += int(not np.array_equal(frame.target_timestamp.to_numpy(), timestamps[target]))
        expected_true = panel[f"{row.machine}__cpu_utilization"].to_numpy(dtype=np.float32)[target]
        maxima["target_abs_difference"] = max(maxima["target_abs_difference"], float(np.max(np.abs(frame.y_true.to_numpy(dtype=np.float32) - expected_true))))
        fold = fold_cache[(row.machine, int(row.selected_L))][int(row.fold) - 1]
        expected_ids = {f"{row.machine}:{origin_value}" for origin_value in fold.outer_test_indices}
        structural["sample_id_mismatches"] += int(set(frame.sample_id) != expected_ids)
        truth = frame.pivot(index="origin_index", columns="lead", values="y_true").reindex(columns=FUTURE_LEADS)
        pred = frame.pivot(index="origin_index", columns="lead", values="y_pred").reindex(columns=FUTURE_LEADS)
        computed = per_lead_metrics(truth.to_numpy(), pred.to_numpy())
        for position, lead_value in enumerate(FUTURE_LEADS):
            saved = metric_index.loc[(row.run_id, lead_value)][["mae", "rmse", "r2"]].to_numpy(dtype=float)
            current = np.asarray([computed["mae"][position], computed["rmse"][position], computed["r2"][position]])
            maxima["metric_abs_difference"] = max(maxima["metric_abs_difference"], float(np.nanmax(np.abs(current - saved))))
            lead_part = frame[frame.lead.eq(lead_value)]
            pooled_sums[(row.feature_set, lead_value)][0] += float(np.abs(lead_part.y_true - lead_part.y_pred).sum())
            pooled_sums[(row.feature_set, lead_value)][1] += len(lead_part)

    recomputed_aggregation, _matched = aggregation_summary(metrics, registry)
    stored_aggregation = pd.read_csv(OUT / "aggregation_summary.csv", dtype={"lead": str})
    expected_aggregation = recomputed_aggregation.copy()
    expected_aggregation["lead"] = expected_aggregation.lead.astype(str)
    stored_aggregation = stored_aggregation.sort_values("lead").reset_index(drop=True)
    expected_aggregation = expected_aggregation.sort_values("lead").reset_index(drop=True)
    aggregation_columns = [column for column in expected_aggregation.columns if column != "lead"]
    maxima["aggregation_abs_difference"] = float(np.max(np.abs(
        stored_aggregation[aggregation_columns].to_numpy(dtype=float)
        - expected_aggregation[aggregation_columns].to_numpy(dtype=float)
    )))
    for lead in [*FUTURE_LEADS, "OVERALL"]:
        selected_leads = FUTURE_LEADS if lead == "OVERALL" else (lead,)
        direct = {}
        for feature in FEATURES:
            error_sum = sum(pooled_sums[(feature, item)][0] for item in selected_leads)
            count = sum(pooled_sums[(feature, item)][1] for item in selected_leads)
            direct[feature] = error_sum / count
        stored_row = stored_aggregation[stored_aggregation.lead.eq(str(lead))].iloc[0]
        direct_gain = 100.0 * (direct["F0_LOCAL"] - direct["F1_THROUGHPUT"]) / direct["F0_LOCAL"]
        maxima["pooled_direct_abs_difference"] = max(
            maxima["pooled_direct_abs_difference"],
            abs(direct["F0_LOCAL"] - float(stored_row.pooled_f0_mae)),
            abs(direct["F1_THROUGHPUT"] - float(stored_row.pooled_f1_mae)),
            abs(direct_gain - float(stored_row.pooled_gain_pct)),
        )

    for _key, group in registry.groupby(["machine", "fold", "seed"]):
        frames = {row.feature_set: pd.read_parquet(ROOT / row.prediction_path, columns=["sample_id", "lead", "target_timestamp", "y_true"]) for row in group.itertuples(index=False)}
        columns = ["sample_id", "lead", "target_timestamp", "y_true"]
        left = frames["F0_LOCAL"].sort_values(["sample_id", "lead"])[columns].reset_index(drop=True)
        right = frames["F1_THROUGHPUT"].sort_values(["sample_id", "lead"])[columns].reset_index(drop=True)
        structural["sample_id_mismatches"] += int(not left.equals(right))

    synthetic_train = np.arange(24, dtype=np.float32).reshape(4, 3, 2); synthetic_test = synthetic_train + 10_000
    scaler = FeatureStandardizer.fit(synthetic_train)
    train_only = bool(np.allclose(scaler.mean, synthetic_train.mean(axis=(0, 1), keepdims=True)) and not np.allclose(scaler.mean, np.concatenate([synthetic_train, synthetic_test]).mean(axis=(0, 1), keepdims=True)))
    no_test_api = not any("test" in name or "validation" in name for name in inspect.signature(fit_final_fixed_epochs).parameters)
    source = (ROOT / "benchmark/neural_v2/run_patchtst_scientific.py").read_text()
    fit_position = source.index("result = fit_final_fixed_epochs("); test_after_fit = source.index("outer_test = build_windows(", fit_position) > fit_position

    neural_count, neural_bad = verify_inventory(NEURAL_INVENTORY)
    dlinear_count, dlinear_bad = verify_inventory(DLINEAR_INVENTORY)
    lstm_count, lstm_bad = verify_inventory(LSTM_INVENTORY)
    phase2a_count, phase2a_bad = phase2a_hashes()
    original_count, original_bad = verify_inventory(ORIGINAL_INVENTORY)
    corrected_count, corrected_bad = verify_inventory(CORRECTED_INVENTORY)
    raw_ok = verify_raw_hashes(); canonical_hash = sha256(PANEL_PATH)
    vs_dlinear = pd.read_csv(OUT / "patchtst_vs_dlinear.csv")
    vs_lightgbm = pd.read_csv(OUT / "patchtst_vs_lightgbm.csv")
    vs_lstm = pd.read_csv(OUT / "patchtst_vs_lstm.csv")
    comparison_ok = bool(
        len(vs_dlinear[vs_dlinear.aggregation_level.eq("machine_fold")]) == 280
        and len(vs_lightgbm[vs_lightgbm.aggregation_level.eq("machine_fold")]) == 280
        and len(vs_lstm[vs_lstm.aggregation_level.eq("machine_fold")]) == 280
        and set(vs_dlinear[vs_dlinear.aggregation_level.eq("machine_fold")].support_relation).issubset({"EXACT_IDENTICAL", "EXACT_INTERSECTION_NO_RETRAIN"})
        and set(vs_lightgbm[vs_lightgbm.aggregation_level.eq("machine_fold")].support_relation).issubset({"EXACT_IDENTICAL", "EXACT_INTERSECTION_NO_RETRAIN"})
        and set(vs_lstm[vs_lstm.aggregation_level.eq("machine_fold")].support_relation).issubset({"EXACT_IDENTICAL", "EXACT_INTERSECTION_NO_RETRAIN"})
    )
    unexpected_dirs = [p.name for p in OUT.parent.iterdir() if p.is_dir() and p.name not in {"dlinear", "lstm", "patchtst"}]
    if any(structural.values()): failures.append("nonzero structural count")
    if maxima["metric_abs_difference"] > 1e-12 or maxima["target_abs_difference"] != 0: failures.append("prediction recomputation")
    if maxima["aggregation_abs_difference"] > 1e-12: failures.append("primary/cell aggregation recomputation")
    if maxima["pooled_direct_abs_difference"] > 1e-6: failures.append("pooled aggregation recomputation")
    if not (train_only and no_test_api and test_after_fit): failures.append("train/test isolation")
    if sha256(CRITERIA) != EXPECTED_CRITERIA_HASH: failures.append("prospective criteria hash")
    if neural_count != 29 or neural_bad: failures.append("Neural-v2 inventory")
    if dlinear_count != 1347 or dlinear_bad: failures.append("DLinear inventory")
    if lstm_count != 1349 or lstm_bad: failures.append("LSTM inventory")
    if phase2a_count != 33 or phase2a_bad: failures.append("Phase 2A hashes")
    if original_count != 632 or original_bad: failures.append("original deterministic inventory")
    if corrected_count != 1070 or corrected_bad: failures.append("corrected deterministic inventory")
    if not raw_ok or canonical_hash != EXPECTED_PANEL_SHA256: failures.append("raw/canonical integrity")
    if not comparison_ok: failures.append("comparison support")
    if unexpected_dirs: failures.append("unauthorized model outputs")

    runtime_path = OUT / "runtime_accounting.json"; runtime = json.loads(runtime_path.read_text())
    validation_wall = time.perf_counter() - started
    runtime["validation_wall_seconds"] = validation_wall
    runtime["total_recorded_wall_seconds"] = float(runtime["execution_wall_seconds"]) + float(runtime["analysis_wall_seconds"]) + validation_wall
    runtime["status"] = "COMPLETE" if not failures else "VALIDATION_FAILED"
    atomic_json_write(runtime_path, runtime)
    validation = {
        "status": "PASS" if not failures else "FAIL",
        "scientific_scope": "PatchTST only",
        "artifact_counts": actual_counts,
        "all_seeds_present": bool(set(registry.seed) == set(SEEDS)),
        "all_leads_present": bool(set(metrics.lead) == set(FUTURE_LEADS)),
        "missing_run_keys": len(run_keys - observed_runs),
        "missing_metric_keys": len(metric_keys - observed_metrics),
        "duplicate_run_ids": int(registry.run_id.duplicated().sum()),
        "structural_counts": structural,
        "maximum_differences": maxima,
        "selection_and_fit": {"selected_L_inner_only": structural["selected_L_mismatches"] == 0, "smaller_L_tie_break": structural["selected_L_mismatches"] == 0, "per_seed_fixed_epoch": structural["selected_epoch_mismatches"] == 0, "train_only_preprocessing": train_only, "final_refit_no_test_api": no_test_api, "outer_test_loaded_after_fit": test_after_fit},
        "comparison_support_valid": comparison_ok,
        "aggregation_recomputation": {"primary_exact": maxima["aggregation_abs_difference"] <= 1e-12, "pooled_exact_with_float_tolerance": maxima["pooled_direct_abs_difference"] <= 1e-6, "cell_relative_exact": maxima["aggregation_abs_difference"] <= 1e-12},
        "frozen_integrity": {"neural_v2": [neural_count, len(neural_bad)], "dlinear": [dlinear_count, len(dlinear_bad)], "lstm": [lstm_count, len(lstm_bad)], "phase2a": [phase2a_count, len(phase2a_bad)], "original_deterministic": [original_count, len(original_bad)], "corrected_deterministic": [corrected_count, len(corrected_bad)], "raw_hashes_unchanged": raw_ok, "canonical_panel_sha256": canonical_hash},
        "unexpected_model_output_directories": unexpected_dirs,
        "failures": failures,
    }
    atomic_json_write(OUT / "validation.json", validation)
    print(json.dumps(validation, indent=2))
    if failures: raise RuntimeError("PatchTST scientific validation failed")


if __name__ == "__main__":
    main()
