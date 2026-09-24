#!/usr/bin/env python3
"""Independent validation for Phase 2B-2A1 DLinear scientific outputs."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark.neural_v2.src.data import (
    CONTEXT_LENGTHS,
    EXPECTED_PANEL_SHA256,
    FUTURE_LEADS,
    load_canonical_panel,
    sample_set_hash,
)
from benchmark.neural_v2.src.metrics import per_lead_metrics
from benchmark.neural_v2.src.splits import build_supported_folds
from benchmark.neural_v2.src.training import (
    FeatureStandardizer,
    fit_final_fixed_epochs,
)
from benchmark.neural_v2.src.validation import atomic_json_write, run_id
from benchmark.src.data import PANEL_PATH, verify_raw_hashes


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "benchmark/neural_v2/outputs/dlinear"
PHASE2A_MANIFEST = ROOT / "benchmark/PHASE2A_FREEZE_MANIFEST.md"
NEURAL_INVENTORY = ROOT / "benchmark/neural_v2/NEURAL_V2_ARTIFACT_SHA256.csv"
ORIGINAL_INVENTORY = ROOT / "benchmark/phase2b1_original/HEAVY_ARTIFACT_SHA256.csv"
CORRECTED_INVENTORY = ROOT / "benchmark/phase2b1_corrected/CORRECTION_ARTIFACT_SHA256.csv"
EXPECTED_DECISION_HASH = "9cec1dc25dc20dd1bf20ac3d7d495f731d41106935a66726d79a182fd058a08c"
EXPECTED_NEURAL_COMMIT = "08697069cf54f4c94cbd2a449b3e2050405328fb"
EXPECTED_DETERMINISTIC_COMMIT = "bdc7c9243cb33cbb3fadee7b911810a164d8da43"
FEATURES = ("F0_LOCAL", "F1_THROUGHPUT")
MACHINES = tuple(f"machine{number:02d}" for number in range(1, 8))
SEEDS = (0, 1, 2)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_inventory(path: Path) -> tuple[int, list[str]]:
    inventory = pd.read_csv(path)
    failures: list[str] = []
    for row in inventory.itertuples(index=False):
        artifact = ROOT / row.path
        if (
            not artifact.exists()
            or artifact.stat().st_size != int(row.size_bytes)
            or sha256(artifact) != row.sha256
        ):
            failures.append(str(row.path))
    return len(inventory), failures


def phase2a_hashes() -> tuple[int, list[str]]:
    rows = re.findall(
        r"\| `([^`]+)`(?: \([^)]*\))? \|(?: [\d,]+ \|)? `([0-9a-f]{64})` \|",
        PHASE2A_MANIFEST.read_text(),
    )
    selected = []
    for relative, expected in rows:
        if relative.startswith(("benchmark/src/", "benchmark/tests/", "data/raw/")) or relative in {
            "benchmark/PROTOCOL.md",
            "benchmark/configs/benchmark.json",
            "discovery/02_dependency_analysis/outputs/canonical_panel.parquet",
            "discovery/02_dependency_analysis/outputs/canonical_signal_registry.csv",
            "discovery/02_dependency_analysis/PROTOCOL.md",
            "discovery/03_rolling_robustness/ROLLING_PROTOCOL.md",
        }:
            selected.append((relative, expected))
    failures = [relative for relative, expected in selected if not (ROOT / relative).exists() or sha256(ROOT / relative) != expected]
    return len(selected), failures


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    started = time.perf_counter()
    failures: list[str] = []
    maxima = {
        "metric_abs_difference": 0.0,
        "target_abs_difference": 0.0,
        "inner_mean_mae_abs_difference": 0.0,
    }
    counts = {
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

    panel = load_canonical_panel()
    timestamps = panel.timestamp.to_numpy()
    segments = panel.segment_id.to_numpy()
    registry = pd.read_csv(OUT / "run_registry.csv")
    inner = pd.read_parquet(OUT / "inner_selection_runs.parquet")
    selected = pd.read_csv(OUT / "selected_contexts.csv")
    selected_epochs = pd.read_csv(OUT / "selected_epochs.csv")
    metrics = pd.read_parquet(OUT / "metrics.parquet")

    expected_run_keys = {
        (feature, machine, fold, seed)
        for feature in FEATURES
        for machine in MACHINES
        for fold in range(1, 6)
        for seed in SEEDS
    }
    observed_run_keys = set(
        zip(registry.feature_set, registry.machine, registry.fold, registry.seed)
    )
    expected_metric_keys = {
        (*key, lead) for key in expected_run_keys for lead in FUTURE_LEADS
    }
    observed_metric_keys = set(
        zip(metrics.feature_set, metrics.machine, metrics.fold, metrics.seed, metrics.lead)
    )
    if len(inner) != 630:
        failures.append("inner fit count")
    if len(registry) != 210:
        failures.append("final run count")
    if len(metrics) != 1680:
        failures.append("metric row count")
    if len(selected) != 70:
        failures.append("selected-context count")
    if observed_run_keys != expected_run_keys:
        failures.append("missing or unexpected final run keys")
    if observed_metric_keys != expected_metric_keys:
        failures.append("missing or unexpected metric keys")
    if registry.run_id.duplicated().any() or len(set(registry.run_id)) != 210:
        failures.append("duplicate run IDs")
    prediction_paths = sorted((OUT / "predictions").glob("*.parquet"))
    if len(prediction_paths) != 210:
        failures.append("prediction file count")

    # Rebuild every supported split and independently check hashes and purges.
    fold_cache = {}
    for machine in MACHINES:
        for length in CONTEXT_LENGTHS:
            supported = build_supported_folds(panel, machine, length)
            fold_cache[(machine, length)] = supported
            for fold in supported:
                supports = {
                    "inner_train": fold.inner_train_indices,
                    "inner_validation": fold.inner_validation_indices,
                    "final_train": fold.outer_train_indices,
                    "test": fold.outer_test_indices,
                }
                for origins in supports.values():
                    histories = origins[:, None] - np.arange(length - 1, -1, -1)
                    targets = origins[:, None] + np.asarray(FUTURE_LEADS)
                    counts["segment_crossing_histories"] += int(
                        np.sum(~np.all(segments[histories] == segments[origins, None], axis=1))
                    )
                    counts["segment_crossing_targets"] += int(
                        np.sum(~np.all(segments[targets] == segments[origins, None], axis=1))
                    )
                if fold.outer_train_indices[-1] + max(FUTURE_LEADS) >= fold.outer_test_indices[0]:
                    counts["outer_target_time_leakage"] += 1
                if fold.inner_train_indices[-1] + max(FUTURE_LEADS) >= fold.inner_validation_indices[0]:
                    counts["inner_target_time_leakage"] += 1

    # F0/F1 support records must match for every L, fold, machine, and seed.
    support_columns = ["inner_train_hash", "inner_validation_hash", "final_train_hash", "test_hash"]
    for key, group in inner.groupby(["machine", "fold", "context_length", "seed"]):
        if set(group.feature_set) != set(FEATURES) or len(group) != 2:
            counts["support_hash_mismatches"] += 1
            continue
        for column in support_columns:
            if group[column].nunique() != 1:
                counts["support_hash_mismatches"] += 1
        machine, fold_number, length, _seed = key
        fold = fold_cache[(machine, int(length))][int(fold_number) - 1]
        expected_hashes = {
            "inner_train_hash": sample_set_hash(fold.inner_train_indices),
            "inner_validation_hash": sample_set_hash(fold.inner_validation_indices),
            "final_train_hash": sample_set_hash(fold.outer_train_indices),
            "test_hash": sample_set_hash(fold.outer_test_indices),
        }
        for column, expected in expected_hashes.items():
            if not (group[column] == expected).all():
                counts["support_hash_mismatches"] += 1

    # Recompute the seed-mean context choice with the smaller-L tie break.
    for key, group in inner.groupby(["feature_set", "machine", "fold"]):
        for row in group.itertuples(index=False):
            maxima["inner_mean_mae_abs_difference"] = max(
                maxima["inner_mean_mae_abs_difference"],
                abs(float(row.mean_validation_mae) - float(np.mean(row.validation_mae_by_lead))),
            )
        scores = []
        for length, length_group in group.groupby("context_length"):
            per_lead_values = np.asarray(length_group.validation_mae_by_lead.tolist(), dtype=float)
            scores.append((float(per_lead_values.mean()), int(length)))
        expected_L = min(scores)[1]
        stored = selected[
            (selected.feature_set == key[0])
            & (selected.machine == key[1])
            & (selected.fold == key[2])
        ]
        if len(stored) != 1 or int(stored.iloc[0].selected_L) != expected_L:
            counts["selected_L_mismatches"] += 1

    selected_index = selected.set_index(["feature_set", "machine", "fold"])
    inner_index = inner.set_index(["feature_set", "machine", "fold", "context_length", "seed"])
    for row in selected_epochs.itertuples(index=False):
        expected_L = int(selected_index.loc[(row.feature_set, row.machine, row.fold)].selected_L)
        expected_epoch = int(inner_index.loc[(row.feature_set, row.machine, row.fold, expected_L, row.seed)].best_epoch)
        if row.selected_L != expected_L or row.selected_epoch != expected_epoch:
            counts["selected_epoch_mismatches"] += 1

    # Recompute every final artifact from its immutable identifiers and predictions.
    metric_index = metrics.set_index(["run_id", "lead"])
    prediction_schema = {
        "run_id", "model", "feature_set", "machine", "fold", "seed",
        "selected_L", "selected_epoch", "lead", "origin_timestamp",
        "target_timestamp", "sample_id", "y_true", "y_pred",
    }
    for row in registry.itertuples(index=False):
        payload = {
            "model": row.model,
            "feature_set": row.feature_set,
            "machine": row.machine,
            "fold": int(row.fold),
            "seed": int(row.seed),
            "selected_L": int(row.selected_L),
            "selected_epoch": int(row.selected_epoch),
        }
        if run_id(payload) != row.run_id:
            counts["run_id_mismatches"] += 1
        path = ROOT / row.prediction_path
        if not path.exists() or sha256(path) != row.prediction_sha256:
            counts["prediction_hash_mismatches"] += 1
            continue
        prediction = pd.read_parquet(path)
        if not prediction_schema.issubset(prediction.columns):
            failures.append(f"prediction schema {row.run_id}")
            continue
        if set(prediction.run_id) != {row.run_id} or set(prediction.lead) != set(FUTURE_LEADS):
            failures.append(f"prediction identity {row.run_id}")
        if prediction.duplicated(["sample_id", "lead"]).any():
            counts["sample_id_mismatches"] += 1
        origin = prediction.origin_index.to_numpy(dtype=np.int64)
        lead = prediction.lead.to_numpy(dtype=np.int64)
        target = prediction.target_index.to_numpy(dtype=np.int64)
        if not np.array_equal(target, origin + lead):
            counts["timestamp_mismatches"] += 1
        if not np.array_equal(prediction.origin_timestamp.to_numpy(), timestamps[origin]):
            counts["timestamp_mismatches"] += 1
        if not np.array_equal(prediction.target_timestamp.to_numpy(), timestamps[target]):
            counts["timestamp_mismatches"] += 1
        expected_true = panel[f"{row.machine}__cpu_utilization"].to_numpy(dtype=np.float32)[target]
        maxima["target_abs_difference"] = max(
            maxima["target_abs_difference"],
            float(np.max(np.abs(prediction.y_true.to_numpy(dtype=np.float32) - expected_true))),
        )
        expected_fold = fold_cache[(row.machine, int(row.selected_L))][int(row.fold) - 1]
        if row.test_hash != sample_set_hash(expected_fold.outer_test_indices):
            counts["support_hash_mismatches"] += 1
        expected_ids = {f"{row.machine}:{origin_value}" for origin_value in expected_fold.outer_test_indices}
        if set(prediction.sample_id) != expected_ids:
            counts["sample_id_mismatches"] += 1
        true_pivot = prediction.pivot(index="origin_index", columns="lead", values="y_true").reindex(columns=FUTURE_LEADS)
        pred_pivot = prediction.pivot(index="origin_index", columns="lead", values="y_pred").reindex(columns=FUTURE_LEADS)
        computed = per_lead_metrics(true_pivot.to_numpy(), pred_pivot.to_numpy())
        for position, lead_value in enumerate(FUTURE_LEADS):
            saved = metric_index.loc[(row.run_id, lead_value)]
            differences = np.abs(
                np.asarray([computed["mae"][position], computed["rmse"][position], computed["r2"][position]])
                - saved[["mae", "rmse", "r2"]].to_numpy(dtype=float)
            )
            maxima["metric_abs_difference"] = max(
                maxima["metric_abs_difference"], float(np.nanmax(differences))
            )

    # Direct paired F0/F1 prediction support check, independent of stored hashes.
    for key, group in registry.groupby(["machine", "fold", "seed"]):
        if set(group.feature_set) != set(FEATURES):
            counts["sample_id_mismatches"] += 1
            continue
        frames = {
            row.feature_set: pd.read_parquet(ROOT / row.prediction_path, columns=["sample_id", "lead", "target_timestamp", "y_true"])
            for row in group.itertuples(index=False)
        }
        columns = ["sample_id", "lead", "target_timestamp", "y_true"]
        left = frames["F0_LOCAL"].sort_values(["sample_id", "lead"])[columns].reset_index(drop=True)
        right = frames["F1_THROUGHPUT"].sort_values(["sample_id", "lead"])[columns].reset_index(drop=True)
        if not left.equals(right):
            counts["sample_id_mismatches"] += 1

    # Train-only transforms and final-refit API/ordering are verified independently.
    synthetic_train = np.arange(24, dtype=np.float32).reshape(4, 3, 2)
    synthetic_test = synthetic_train + 10_000
    scaler = FeatureStandardizer.fit(synthetic_train)
    train_only_transform = bool(
        np.allclose(scaler.mean, synthetic_train.mean(axis=(0, 1), keepdims=True))
        and not np.allclose(scaler.mean, np.concatenate([synthetic_train, synthetic_test]).mean(axis=(0, 1), keepdims=True))
    )
    final_signature = inspect.signature(fit_final_fixed_epochs)
    no_test_or_validation_api = not any(
        "test" in name or "validation" in name for name in final_signature.parameters
    )
    runner_source = (ROOT / "benchmark/neural_v2/run_dlinear_scientific.py").read_text()
    fit_position = runner_source.index("result = fit_final_fixed_epochs(")
    test_position = runner_source.index("outer_test = build_windows(", fit_position)
    test_loaded_after_fit = test_position > fit_position

    neural_count, neural_failures = verify_inventory(NEURAL_INVENTORY)
    phase2a_count, phase2a_failures = phase2a_hashes()
    original_count, original_failures = verify_inventory(ORIGINAL_INVENTORY)
    corrected_count, corrected_failures = verify_inventory(CORRECTED_INVENTORY)
    raw_unchanged = verify_raw_hashes()
    canonical_hash = sha256(PANEL_PATH)
    neural_tag = git_output("rev-list", "-n", "1", "neural-v2-protocol-freeze-v1")
    deterministic_tag = git_output("rev-list", "-n", "1", "phase2b1-corrected-deterministic-freeze-v1")
    head_contains_freeze = subprocess.run(
        ["git", "merge-base", "--is-ancestor", EXPECTED_NEURAL_COMMIT, "HEAD"], cwd=ROOT
    ).returncode == 0

    comparison = pd.read_csv(OUT / "dlinear_vs_lightgbm.csv")
    compatible_relations = {"EXACT_IDENTICAL", "EXACT_INTERSECTION_NO_RETRAIN"}
    comparison_ok = bool(
        len(comparison[comparison.aggregation_level == "machine_fold"]) == 280
        and len(comparison[comparison.aggregation_level == "lead_macro"]) == 8
        and set(comparison[comparison.aggregation_level == "machine_fold"].support_relation).issubset(compatible_relations)
        and (comparison[comparison.aggregation_level == "machine_fold"].common_test_n > 0).all()
    )
    figures = sorted((OUT / "figures").glob("*.png"))
    other_model_outputs = [path.name for path in (OUT.parent).iterdir() if path.is_dir() and path.name != "dlinear"]

    if any(counts.values()):
        failures.append("nonzero structural validation count")
    if maxima["metric_abs_difference"] > 1e-12:
        failures.append("metric recomputation")
    if maxima["target_abs_difference"] != 0:
        failures.append("target recomputation")
    # The cached scalar was produced from float32 arrays; the persisted per-lead
    # values are JSON/Python floats, so sub-micro-unit recasting is expected.
    if maxima["inner_mean_mae_abs_difference"] > 1e-6:
        failures.append("inner mean MAE recomputation")
    if not train_only_transform:
        failures.append("train-only transformation")
    if not (no_test_or_validation_api and test_loaded_after_fit):
        failures.append("outer-test isolation")
    if neural_count != 29 or neural_failures:
        failures.append("Neural-v2 frozen inventory")
    if phase2a_count != 33 or phase2a_failures:
        failures.append("Phase 2A frozen hashes")
    if original_count != 632 or original_failures:
        failures.append("original deterministic inventory")
    if corrected_count != 1070 or corrected_failures:
        failures.append("corrected deterministic inventory")
    if not raw_unchanged or canonical_hash != EXPECTED_PANEL_SHA256:
        failures.append("raw/canonical integrity")
    if neural_tag != EXPECTED_NEURAL_COMMIT or deterministic_tag != EXPECTED_DETERMINISTIC_COMMIT or not head_contains_freeze:
        failures.append("checkpoint ancestry/tag integrity")
    if not comparison_ok:
        failures.append("LightGBM compatible-support comparison")
    if len(figures) != 4:
        failures.append("figure count")
    if other_model_outputs:
        failures.append("non-DLinear scientific outputs exist")

    runtime_path = OUT / "runtime_accounting.json"
    runtime = json.loads(runtime_path.read_text())
    validation_wall = time.perf_counter() - started
    epoch_distribution = (
        selected_epochs.groupby("selected_epoch").size().rename("count").reset_index().to_dict(orient="records")
    )
    pilot_seconds = float(runtime["pilot_central_dlinear_projection_hours"]) * 3600
    runtime.update(
        {
            "validation_wall_seconds": validation_wall,
            "total_recorded_wall_seconds": float(runtime["execution_wall_seconds"]) + float(runtime["analysis_wall_seconds"]) + validation_wall,
            "selected_epoch_distribution": epoch_distribution,
            "actual_to_pilot_runtime_ratio": float(runtime["execution_wall_seconds"]) / pilot_seconds,
            "actual_minus_pilot_seconds": float(runtime["execution_wall_seconds"]) - pilot_seconds,
            "status": "COMPLETE" if not failures else "VALIDATION_FAILED",
        }
    )
    atomic_json_write(runtime_path, runtime)

    validation = {
        "status": "PASS" if not failures else "FAIL",
        "scientific_scope": "DLinear only",
        "decision_sha256": EXPECTED_DECISION_HASH,
        "checkpoint_integrity": {
            "head_contains_neural_freeze": bool(head_contains_freeze),
            "neural_tag_target": neural_tag,
            "deterministic_tag_target": deterministic_tag,
        },
        "artifact_counts": {
            "inner_fits": len(inner),
            "final_runs": len(registry),
            "metric_rows": len(metrics),
            "selected_context_records": len(selected),
            "prediction_files": len(prediction_paths),
            "figures": len(figures),
        },
        "identity_coverage": {
            "all_seeds_present": bool(set(registry.seed) == set(SEEDS)),
            "all_leads_present": bool(set(metrics.lead) == set(FUTURE_LEADS)),
            "duplicate_run_ids": int(registry.run_id.duplicated().sum()),
            "missing_run_keys": len(expected_run_keys - observed_run_keys),
            "missing_metric_keys": len(expected_metric_keys - observed_metric_keys),
        },
        "structural_counts": counts,
        "maximum_differences": maxima,
        "selection_and_fit": {
            "selected_L_from_inner_validation_only": bool(counts["selected_L_mismatches"] == 0),
            "smaller_L_tie_break_reproduced": bool(counts["selected_L_mismatches"] == 0),
            "per_seed_epoch_reproduced": bool(counts["selected_epoch_mismatches"] == 0),
            "final_refit_has_no_test_or_validation_api": bool(no_test_or_validation_api),
            "outer_test_loaded_after_fit": bool(test_loaded_after_fit),
            "train_only_transformation": bool(train_only_transform),
        },
        "comparison": {
            "compatible_support_only": bool(comparison_ok),
            "machine_fold_rows": int((comparison.aggregation_level == "machine_fold").sum()),
            "lead_macro_rows": int((comparison.aggregation_level == "lead_macro").sum()),
        },
        "frozen_integrity": {
            "neural_v2_checked": neural_count,
            "neural_v2_failures": neural_failures,
            "phase2a_checked": phase2a_count,
            "phase2a_failures": phase2a_failures,
            "original_deterministic_checked": original_count,
            "original_deterministic_failures": original_failures,
            "corrected_deterministic_checked": corrected_count,
            "corrected_deterministic_failures": corrected_failures,
            "raw_hashes_unchanged": raw_unchanged,
            "canonical_panel_sha256": canonical_hash,
        },
        "other_model_output_directories": other_model_outputs,
        "failures": failures,
    }
    atomic_json_write(OUT / "validation.json", validation)
    print(json.dumps(validation, indent=2))
    if failures:
        raise RuntimeError("DLinear scientific validation failed")


if __name__ == "__main__":
    main()
