#!/usr/bin/env python3
"""Run the frozen Phase 1B-2A incremental Ridge predictive screen.

Each experiment compares an own-history baseline with the same baseline plus
the candidate's complete frozen history vector. Association-selected lags are
not used as model features. No classification or hyperparameter search occurs.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from joblib import Parallel, delayed
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "discovery" / "02_dependency_analysis"
OUTPUT_DIR = PHASE_DIR / "outputs"
PANEL_PATH = OUTPUT_DIR / "canonical_panel.parquet"
REGISTRY_PATH = OUTPUT_DIR / "canonical_signal_registry.csv"
SPLIT_PATH = OUTPUT_DIR / "split_boundaries_by_target_lead.csv"
CANDIDATE_MANIFEST_PATH = OUTPUT_DIR / "validation_selected_lags.csv"
ASSOCIATION_TEST_PATH = OUTPUT_DIR / "test_association_at_selected_lag.parquet"
PHASE1_HASH_PATH = (
    ROOT / "discovery" / "01_data_audit" / "outputs" / "raw_hashes_before_after.json"
)

LEADS = [1, 2, 4, 8, 16, 32, 64, 128]
FEATURE_LAGS = [0, 1, 2, 4, 8, 16, 32]
RIDGE_SETTINGS = {
    "alpha": 1.0,
    "fit_intercept": True,
    "copy_X": True,
    "max_iter": None,
    "tol": 1e-4,
    "solver": "auto",
    "positive": False,
    "random_state": None,
}
MIN_TRAIN_ROWS = 30
MIN_EVALUATION_ROWS = 2
MIN_ELIGIBLE_SEGMENT_ROWS = 30
EXPECTED_CANDIDATES = 434
EXPECTED_MODE_COMBINATIONS = 616
EXPECTED_EXPERIMENTS = 4_928
SPLITS = ["train", "validation", "test"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    def convert(value: Any) -> Any:
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return None if not np.isfinite(value) else float(value)
        if isinstance(value, (pd.Timestamp, Path)):
            return str(value)
        raise TypeError(type(value).__name__)

    path.write_text(json.dumps(payload, indent=2, default=convert) + "\n")


def load_experiment_manifest() -> pd.DataFrame:
    """Use association rows only as a complete frozen candidate manifest.

    Selected association lags and coefficient values are deliberately excluded.
    """
    association = pd.read_csv(CANDIDATE_MANIFEST_PATH)
    columns = [
        "target",
        "target_machine",
        "target_family",
        "predictor",
        "predictor_machine",
        "predictor_family",
        "candidate_family",
        "direction",
        "analysis_mode",
        "lead",
    ]
    manifest = association[columns].copy()
    if manifest.duplicated().any():
        raise RuntimeError("Duplicate candidate/mode/lead experiments")
    if len(manifest) != EXPECTED_EXPERIMENTS:
        raise RuntimeError(f"Expected {EXPECTED_EXPERIMENTS} experiments, got {len(manifest)}")
    if sorted(manifest["lead"].unique().tolist()) != LEADS:
        raise RuntimeError("Frozen future-lead grid changed")
    relationships = manifest[
        ["target", "predictor", "candidate_family"]
    ].drop_duplicates()
    expected_families = {
        "global_context": 140,
        "same_machine_cross_resource": 126,
        "same_resource_cross_machine": 126,
        "leave_one_machine_out": 42,
    }
    if relationships["candidate_family"].value_counts().to_dict() != expected_families:
        raise RuntimeError("Frozen candidate families changed")
    mode_combinations = manifest[columns[:-1]].drop_duplicates()
    if len(relationships) != EXPECTED_CANDIDATES or len(mode_combinations) != EXPECTED_MODE_COMBINATIONS:
        raise RuntimeError("Frozen candidate or analysis-mode count changed")
    return manifest.sort_values(columns, kind="stable").reset_index(drop=True)


def build_master_masks(
    panel: pd.DataFrame, split_rows: pd.DataFrame
) -> dict[tuple[str, int], dict[str, np.ndarray]]:
    timestamps = panel["timestamp"]
    segments = panel["segment_id"]
    result: dict[tuple[str, int], dict[str, np.ndarray]] = {}
    for row in split_rows.itertuples(index=False):
        y = panel[row.target]
        lead = int(row.lead)
        eligible = pd.Series(True, index=panel.index)
        for lag in FEATURE_LAGS:
            eligible &= y.shift(lag).notna()
        eligible &= y.shift(-lead).notna()
        eligible &= segments.eq(segments.shift(max(FEATURE_LAGS)))
        eligible &= segments.eq(segments.shift(-lead))
        target_time = timestamps.shift(-lead)
        masks = {
            "eligible": eligible.to_numpy(),
            "train": (eligible & target_time.le(row.train_cut_timestamp)).to_numpy(),
            "validation": (
                eligible
                & timestamps.gt(row.train_cut_timestamp)
                & target_time.le(row.validation_cut_timestamp)
            ).to_numpy(),
            "test": (
                eligible & timestamps.gt(row.validation_cut_timestamp)
            ).to_numpy(),
        }
        expected = {
            "eligible": row.eligible_origin_count_before_purge,
            "train": row.train_count,
            "validation": row.validation_count,
            "test": row.test_count,
        }
        for name, expected_count in expected.items():
            if int(masks[name].sum()) != int(expected_count):
                raise RuntimeError(f"Frozen split mismatch for {row.target}, {lead}, {name}")
        result[(row.target, lead)] = masks
    return result


def build_target_history_cache(
    panel: pd.DataFrame, targets: list[str]
) -> dict[str, np.ndarray]:
    return {
        target: np.column_stack(
            [panel[target].shift(lag).to_numpy(dtype=float) for lag in FEATURE_LAGS]
        )
        for target in targets
    }


def target_values(
    panel: pd.DataFrame, target: str, analysis_mode: str, lead: int
) -> np.ndarray:
    future = panel[target].shift(-lead)
    if analysis_mode == "change":
        future = future - panel[target]
    return future.to_numpy(dtype=float)


def predictor_is_level_like(row: Any) -> bool:
    if row.predictor_family == "memory":
        return True
    return row.predictor_family == "disk" and row.predictor.endswith("__disk_used")


def predictor_history(
    panel: pd.DataFrame, row: Any
) -> tuple[np.ndarray, np.ndarray]:
    source = panel[row.predictor]
    segments = panel["segment_id"]
    columns: list[np.ndarray] = []
    safe = np.ones(len(panel), dtype=bool)
    historical_change = row.analysis_mode == "change" and predictor_is_level_like(row)
    for lag in FEATURE_LAGS:
        if historical_change:
            values = source.shift(lag) - source.shift(lag + 1)
            lag_safe = segments.eq(segments.shift(lag)) & segments.eq(
                segments.shift(lag + 1)
            )
        else:
            values = source.shift(lag)
            lag_safe = segments.eq(segments.shift(lag))
        columns.append(values.to_numpy(dtype=float))
        safe &= lag_safe.to_numpy()
    return np.column_stack(columns), safe


def row_hash(indices: np.ndarray) -> str:
    return hashlib.sha256(indices.astype(np.int64, copy=False).tobytes()).hexdigest()


def regression_metrics(
    truth: np.ndarray, prediction: np.ndarray
) -> tuple[dict[str, float], str]:
    if len(truth) == 0:
        return {"mae": np.nan, "rmse": np.nan, "r2": np.nan}, "no rows"
    residual = truth - prediction
    mae = float(np.mean(np.abs(residual)))
    rmse = float(np.sqrt(np.mean(residual**2)))
    if len(truth) < 2:
        r2 = np.nan
        reason = "R2 undefined: fewer than 2 samples"
    else:
        total = float(np.sum((truth - truth.mean()) ** 2))
        if total == 0 or not np.isfinite(total):
            r2 = np.nan
            reason = "R2 undefined: constant or non-finite target"
        else:
            r2 = float(1.0 - np.sum(residual**2) / total)
            reason = ""
    return {"mae": mae, "rmse": rmse, "r2": r2}, reason


def improvement_pct(baseline: float, augmented: float) -> tuple[float, str]:
    if not np.isfinite(baseline) or not np.isfinite(augmented):
        return np.nan, "improvement undefined: non-finite metric"
    if baseline == 0:
        return np.nan, "improvement undefined: baseline metric is zero"
    return float(100.0 * (baseline - augmented) / baseline), ""


def evaluate_experiment_group(
    group: pd.DataFrame,
    panel: pd.DataFrame,
    target_history: dict[str, np.ndarray],
    master_masks: dict[tuple[str, int], dict[str, np.ndarray]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Evaluate all eight leads for one candidate/analysis-mode combination."""
    first = next(group.itertuples(index=False))
    baseline_x = target_history[first.target]
    predictor_x, predictor_safe = predictor_history(panel, first)
    augmented_x = np.column_stack([baseline_x, predictor_x])
    finite_features = (
        np.isfinite(baseline_x).all(axis=1)
        & np.isfinite(predictor_x).all(axis=1)
        & predictor_safe
    )
    segments = panel["segment_id"].to_numpy()
    result_rows: list[dict[str, Any]] = []
    segment_rows: list[dict[str, Any]] = []

    for row in group.sort_values("lead").itertuples(index=False):
        lead = int(row.lead)
        experiment_id = hashlib.sha256(
            (
                f"{row.target}|{row.predictor}|{row.candidate_family}|"
                f"{row.analysis_mode}|{lead}"
            ).encode()
        ).hexdigest()[:20]
        y = target_values(panel, row.target, row.analysis_mode, lead)
        finite = finite_features & np.isfinite(y)
        split_indices = {
            split: np.flatnonzero(master_masks[(row.target, lead)][split] & finite)
            for split in SPLITS
        }
        counts = {split: len(indices) for split, indices in split_indices.items()}
        status = "evaluated"
        reasons: list[str] = []
        if counts["train"] < MIN_TRAIN_ROWS:
            reasons.append(f"train_n<{MIN_TRAIN_ROWS}")
        if counts["validation"] < MIN_EVALUATION_ROWS:
            reasons.append(f"validation_n<{MIN_EVALUATION_ROWS}")
        if counts["test"] < MIN_EVALUATION_ROWS:
            reasons.append(f"test_n<{MIN_EVALUATION_ROWS}")
        if reasons:
            status = "unevaluable"

        metadata = {
            "experiment_id": experiment_id,
            "analysis_mode": row.analysis_mode,
            "candidate_family": row.candidate_family,
            "direction": row.direction,
            "target": row.target,
            "target_machine": row.target_machine,
            "target_family": row.target_family,
            "predictor": row.predictor,
            "predictor_machine": row.predictor_machine,
            "predictor_family": row.predictor_family,
            "lead": lead,
            "train_n": counts["train"],
            "validation_n": counts["validation"],
            "test_n": counts["test"],
            "train_row_hash": row_hash(split_indices["train"]),
            "validation_row_hash": row_hash(split_indices["validation"]),
            "test_row_hash": row_hash(split_indices["test"]),
            "baseline_augmented_train_rows_matched": True,
            "baseline_augmented_validation_rows_matched": True,
            "baseline_augmented_test_rows_matched": True,
            "evaluation_status": status,
            "unevaluable_reason": "; ".join(reasons),
        }
        metric_values: dict[str, Any] = {}
        eligible_segments = 0
        positive_weight = 0
        eligible_weight = 0

        if status == "evaluated":
            train_idx = split_indices["train"]
            baseline_scaler = StandardScaler()
            augmented_scaler = StandardScaler()
            baseline_train = baseline_scaler.fit_transform(baseline_x[train_idx])
            augmented_train = augmented_scaler.fit_transform(augmented_x[train_idx])
            baseline_model = Ridge(**RIDGE_SETTINGS)
            augmented_model = Ridge(**RIDGE_SETTINGS)
            baseline_model.fit(baseline_train, y[train_idx])
            augmented_model.fit(augmented_train, y[train_idx])

            predictions: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
            for split in ("validation", "test"):
                indices = split_indices[split]
                baseline_prediction = baseline_model.predict(
                    baseline_scaler.transform(baseline_x[indices])
                )
                augmented_prediction = augmented_model.predict(
                    augmented_scaler.transform(augmented_x[indices])
                )
                predictions[split] = (indices, baseline_prediction, augmented_prediction)
                baseline_metrics, baseline_reason = regression_metrics(
                    y[indices], baseline_prediction
                )
                augmented_metrics, augmented_reason = regression_metrics(
                    y[indices], augmented_prediction
                )
                mae_gain, mae_reason = improvement_pct(
                    baseline_metrics["mae"], augmented_metrics["mae"]
                )
                rmse_gain, rmse_reason = improvement_pct(
                    baseline_metrics["rmse"], augmented_metrics["rmse"]
                )
                prefix = f"{split}_"
                metric_values.update(
                    {
                        f"baseline_{prefix}mae": baseline_metrics["mae"],
                        f"augmented_{prefix}mae": augmented_metrics["mae"],
                        f"{prefix}mae_improvement_pct": mae_gain,
                        f"baseline_{prefix}rmse": baseline_metrics["rmse"],
                        f"augmented_{prefix}rmse": augmented_metrics["rmse"],
                        f"{prefix}rmse_improvement_pct": rmse_gain,
                        f"baseline_{prefix}r2": baseline_metrics["r2"],
                        f"augmented_{prefix}r2": augmented_metrics["r2"],
                        f"{prefix}r2_delta": (
                            augmented_metrics["r2"] - baseline_metrics["r2"]
                            if np.isfinite(baseline_metrics["r2"])
                            and np.isfinite(augmented_metrics["r2"])
                            else np.nan
                        ),
                        f"{prefix}metric_undefined_reason": "; ".join(
                            reason
                            for reason in [
                                baseline_reason,
                                augmented_reason,
                                mae_reason,
                                rmse_reason,
                            ]
                            if reason
                        ),
                    }
                )

            test_idx, baseline_test_prediction, augmented_test_prediction = predictions["test"]
            test_segments = segments[test_idx]
            for segment_id in sorted(np.unique(test_segments)):
                within = np.flatnonzero(test_segments == segment_id)
                n = len(within)
                if n < MIN_ELIGIBLE_SEGMENT_ROWS:
                    continue
                truth = y[test_idx[within]]
                baseline_metrics, baseline_reason = regression_metrics(
                    truth, baseline_test_prediction[within]
                )
                augmented_metrics, augmented_reason = regression_metrics(
                    truth, augmented_test_prediction[within]
                )
                mae_gain, mae_reason = improvement_pct(
                    baseline_metrics["mae"], augmented_metrics["mae"]
                )
                rmse_gain, rmse_reason = improvement_pct(
                    baseline_metrics["rmse"], augmented_metrics["rmse"]
                )
                r2_delta = (
                    augmented_metrics["r2"] - baseline_metrics["r2"]
                    if np.isfinite(baseline_metrics["r2"])
                    and np.isfinite(augmented_metrics["r2"])
                    else np.nan
                )
                segment_rows.append(
                    {
                        "experiment_id": experiment_id,
                        "segment_id": int(segment_id),
                        "n_samples": n,
                        "baseline_mae": baseline_metrics["mae"],
                        "augmented_mae": augmented_metrics["mae"],
                        "mae_improvement_pct": mae_gain,
                        "baseline_rmse": baseline_metrics["rmse"],
                        "augmented_rmse": augmented_metrics["rmse"],
                        "rmse_improvement_pct": rmse_gain,
                        "baseline_r2": baseline_metrics["r2"],
                        "augmented_r2": augmented_metrics["r2"],
                        "r2_delta": r2_delta,
                        "metric_undefined_reason": "; ".join(
                            reason
                            for reason in [
                                baseline_reason,
                                augmented_reason,
                                mae_reason,
                                rmse_reason,
                            ]
                            if reason
                        ),
                    }
                )
                eligible_segments += 1
                eligible_weight += n
                if augmented_metrics["mae"] < baseline_metrics["mae"]:
                    positive_weight += n
        else:
            for split in ("validation", "test"):
                prefix = f"{split}_"
                metric_values.update(
                    {
                        f"baseline_{prefix}mae": np.nan,
                        f"augmented_{prefix}mae": np.nan,
                        f"{prefix}mae_improvement_pct": np.nan,
                        f"baseline_{prefix}rmse": np.nan,
                        f"augmented_{prefix}rmse": np.nan,
                        f"{prefix}rmse_improvement_pct": np.nan,
                        f"baseline_{prefix}r2": np.nan,
                        f"augmented_{prefix}r2": np.nan,
                        f"{prefix}r2_delta": np.nan,
                        f"{prefix}metric_undefined_reason": "experiment unevaluable",
                    }
                )

        result_rows.append(
            {
                **metadata,
                **metric_values,
                "positive_segment_sample_weight_fraction": (
                    float(positive_weight / eligible_weight)
                    if eligible_weight
                    else np.nan
                ),
                "eligible_test_segments": eligible_segments,
            }
        )
    return result_rows, segment_rows


def baseline_consistency(experiments: pd.DataFrame) -> pd.DataFrame:
    metric_columns = [
        "baseline_validation_mae",
        "baseline_validation_rmse",
        "baseline_validation_r2",
        "baseline_test_mae",
        "baseline_test_rmse",
        "baseline_test_r2",
    ]
    rows: list[dict[str, Any]] = []
    for (target, mode, lead), group in experiments.groupby(
        ["target", "analysis_mode", "lead"], sort=True
    ):
        evaluated = group[group["evaluation_status"] == "evaluated"]
        row_set_columns = ["train_row_hash", "validation_row_hash", "test_row_hash"]
        unique_sets = evaluated[row_set_columns].drop_duplicates()
        inconsistent_groups = 0
        maximum_matched_set_difference = 0.0
        for _, matched in evaluated.groupby(row_set_columns, dropna=False):
            if len(matched) <= 1:
                continue
            for metric in metric_columns:
                finite = matched[metric].dropna()
                difference = float(finite.max() - finite.min()) if len(finite) else 0.0
                maximum_matched_set_difference = max(
                    maximum_matched_set_difference, difference
                )
                if difference != 0.0:
                    inconsistent_groups += 1
        overall_differs = any(
            group[metric].dropna().nunique() > 1 for metric in metric_columns
        )
        consistent = inconsistent_groups == 0
        if not consistent:
            reason = "unexpected baseline difference for identical matched row hashes"
        elif len(unique_sets) > 1 and overall_differs:
            reason = "candidate-specific missingness produced different matched row sets"
        elif len(unique_sets) > 1:
            reason = "matched row sets differ, but recorded baseline metrics coincide"
        else:
            reason = "all evaluated candidates use the same matched row set"
        rows.append(
            {
                "target": target,
                "analysis_mode": mode,
                "lead": lead,
                "candidate_experiments": len(group),
                "evaluated_experiments": len(evaluated),
                "unique_matched_row_sets": len(unique_sets),
                "baseline_metrics_differ_across_candidates": overall_differs,
                "inconsistent_identical_matched_row_groups": inconsistent_groups,
                "maximum_identical_matched_set_metric_difference": maximum_matched_set_difference,
                "baseline_consistent_for_identical_rows": consistent,
                "difference_reason": reason,
            }
        )
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT_DIR / "baseline_consistency.csv", index=False)
    return result


def main() -> None:
    started = time.perf_counter()
    frozen_raw = json.loads(PHASE1_HASH_PATH.read_text())["after"]
    immutable_paths = {
        "panel": PANEL_PATH,
        "registry": REGISTRY_PATH,
        "protocol": PHASE_DIR / "PROTOCOL.md",
        "splits": SPLIT_PATH,
        "association_manifest": CANDIDATE_MANIFEST_PATH,
        "association_test": ASSOCIATION_TEST_PATH,
    }
    hashes_before = {name: sha256_file(path) for name, path in immutable_paths.items()}
    raw_before = {
        name: sha256_file(ROOT / "data" / "raw" / name) for name in frozen_raw
    }
    if raw_before != frozen_raw:
        raise RuntimeError("Raw SHA-256 values do not match Phase 1A")

    panel = pd.read_parquet(PANEL_PATH)
    panel["timestamp"] = pd.to_datetime(panel["timestamp"])
    registry = pd.read_csv(REGISTRY_PATH)
    split_rows = pd.read_csv(
        SPLIT_PATH,
        parse_dates=["train_cut_timestamp", "validation_cut_timestamp"],
    )
    manifest = load_experiment_manifest()
    if not set(manifest["target"]).union(manifest["predictor"]).issubset(
        set(registry["canonical_name"])
    ):
        raise RuntimeError("Experiment manifest contains a noncanonical signal")
    if len(split_rows) != 224 or sorted(split_rows["lead"].unique().tolist()) != LEADS:
        raise RuntimeError("Purged split definitions changed")
    if (
        not split_rows["leakage_check_train_validation"].all()
        or not split_rows["leakage_check_validation_test"].all()
        or int(split_rows["segment_crossing_count"].sum()) != 0
    ):
        raise RuntimeError("Frozen temporal split validation failed")

    master_masks = build_master_masks(panel, split_rows)
    target_history = build_target_history_cache(
        panel, sorted(manifest["target"].unique().tolist())
    )
    group_columns = [
        "target",
        "target_machine",
        "target_family",
        "predictor",
        "predictor_machine",
        "predictor_family",
        "candidate_family",
        "direction",
        "analysis_mode",
    ]
    groups = [group for _, group in manifest.groupby(group_columns, sort=True, dropna=False)]
    if len(groups) != EXPECTED_MODE_COMBINATIONS:
        raise RuntimeError("Unexpected candidate/mode group count")

    workers = max(1, min(8, os.cpu_count() or 1))
    with threadpool_limits(limits=1):
        evaluated_groups = Parallel(n_jobs=workers, prefer="threads", verbose=5)(
            delayed(evaluate_experiment_group)(group, panel, target_history, master_masks)
            for group in groups
        )
    experiment_rows = [row for group_rows, _ in evaluated_groups for row in group_rows]
    segment_rows = [row for _, group_segments in evaluated_groups for row in group_segments]
    experiments = pd.DataFrame(experiment_rows).sort_values(
        ["target", "analysis_mode", "lead", "candidate_family", "predictor"]
    )
    segments = pd.DataFrame(segment_rows).sort_values(["experiment_id", "segment_id"])
    if len(experiments) != EXPECTED_EXPERIMENTS:
        raise RuntimeError("Incomplete experiment output")
    experiments.to_parquet(
        OUTPUT_DIR / "incremental_predictive_value.parquet",
        index=False,
        compression="zstd",
    )
    segments.to_parquet(
        OUTPUT_DIR / "incremental_predictive_value_by_segment.parquet",
        index=False,
        compression="zstd",
    )
    consistency = baseline_consistency(experiments)

    hashes_after = {name: sha256_file(path) for name, path in immutable_paths.items()}
    raw_after = {
        name: sha256_file(ROOT / "data" / "raw" / name) for name in frozen_raw
    }
    evaluated = experiments[experiments["evaluation_status"] == "evaluated"]
    unevaluable = experiments[experiments["evaluation_status"] != "evaluated"]
    runtime = time.perf_counter() - started
    validation = {
        "status": "PASS",
        "runtime_seconds": runtime,
        "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "sklearn_version": sklearn.__version__,
        "ridge_constructor": f"Ridge({', '.join(f'{k}={v!r}' for k, v in RIDGE_SETTINGS.items())})",
        "ridge_settings": RIDGE_SETTINGS,
        "standard_scaler_settings": StandardScaler().get_params(),
        "future_leads": LEADS,
        "target_history_lags": FEATURE_LAGS,
        "predictor_history_lags": FEATURE_LAGS,
        "ridge_alpha_exactly_1": RIDGE_SETTINGS["alpha"] == 1.0,
        "hpo_performed": False,
        "association_selected_lag_used_as_ridge_feature": False,
        "expected_experiments": EXPECTED_EXPERIMENTS,
        "evaluated_experiments": len(evaluated),
        "unevaluable_experiments": len(unevaluable),
        "counts_by_target_family": experiments["target_family"].value_counts().to_dict(),
        "counts_by_analysis_mode": experiments["analysis_mode"].value_counts().to_dict(),
        "sample_count_ranges": {
            split: {
                "min": int(experiments[f"{split}_n"].min()),
                "max": int(experiments[f"{split}_n"].max()),
            }
            for split in SPLITS
        },
        "segment_level_result_rows": len(segments),
        "feature_window_crossings": 0,
        "target_window_crossings": int(split_rows["segment_crossing_count"].sum()),
        "train_validation_target_time_leakage_failures": int(
            (~split_rows["leakage_check_train_validation"]).sum()
        ),
        "validation_test_target_time_leakage_failures": int(
            (~split_rows["leakage_check_validation_test"]).sum()
        ),
        "baseline_augmented_row_mismatch_experiments": int(
            (
                ~experiments[
                    [
                        "baseline_augmented_train_rows_matched",
                        "baseline_augmented_validation_rows_matched",
                        "baseline_augmented_test_rows_matched",
                    ]
                ].all(axis=1)
            ).sum()
        ),
        "same_target_labels_for_baseline_and_augmentation": True,
        "scaling_fit_on_train_only": True,
        "test_used_for_model_fitting": False,
        "test_used_for_scaling": False,
        "test_used_for_candidate_selection": False,
        "baseline_consistency_rows": len(consistency),
        "baseline_consistency_failures": int(
            (~consistency["baseline_consistent_for_identical_rows"]).sum()
        ),
        "canonical_panel_unchanged": hashes_before["panel"] == hashes_after["panel"],
        "canonical_registry_unchanged": hashes_before["registry"] == hashes_after["registry"],
        "all_immutable_inputs_unchanged": hashes_before == hashes_after,
        "raw_hashes_match_phase1_and_unchanged": raw_before == raw_after == frozen_raw,
        "immutable_input_hashes": hashes_after,
        "raw_hashes": raw_after,
        "generated_files": [
            str(OUTPUT_DIR / "incremental_predictive_value.parquet"),
            str(OUTPUT_DIR / "incremental_predictive_value_by_segment.parquet"),
            str(OUTPUT_DIR / "baseline_consistency.csv"),
            str(OUTPUT_DIR / "ridge_screen_validation.json"),
        ],
    }
    required_zero = [
        validation["feature_window_crossings"],
        validation["target_window_crossings"],
        validation["train_validation_target_time_leakage_failures"],
        validation["validation_test_target_time_leakage_failures"],
        validation["baseline_augmented_row_mismatch_experiments"],
        validation["baseline_consistency_failures"],
    ]
    required_true = [
        validation["ridge_alpha_exactly_1"],
        validation["same_target_labels_for_baseline_and_augmentation"],
        validation["scaling_fit_on_train_only"],
        validation["canonical_panel_unchanged"],
        validation["canonical_registry_unchanged"],
        validation["all_immutable_inputs_unchanged"],
        validation["raw_hashes_match_phase1_and_unchanged"],
    ]
    if any(required_zero) or not all(required_true):
        raise RuntimeError("Ridge screen invariant validation failed")
    write_json(OUTPUT_DIR / "ridge_screen_validation.json", validation)
    print(json.dumps(validation, indent=2, default=str))


if __name__ == "__main__":
    main()
