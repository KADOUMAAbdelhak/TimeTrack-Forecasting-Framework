#!/usr/bin/env python3
"""Independent invariant validation for the Phase 2B-1 deterministic run."""

from __future__ import annotations

import hashlib
import json
import re
import resource
import time
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark.run_deterministic_benchmark import arrays, index_hash
from benchmark.src.data import PANEL_PATH, load_canonical_panel
from benchmark.src.models.ridge import RidgeForecaster
from benchmark.src.splits import build_inner_split, build_outer_folds
from benchmark.src.validation import deterministic_run_id
from benchmark.src.windows import (
    FUTURE_LEADS,
    finite_feature_origins,
    joint_eligible_origins,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "benchmark" / "outputs"
MANIFEST = ROOT / "benchmark" / "PHASE2A_FREEZE_MANIFEST.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def frozen_hash_failures() -> tuple[int, list[dict[str, str]]]:
    text = MANIFEST.read_text()
    rows = re.findall(
        r"\| `([^`]+)`(?: \([^)]*\))? \|(?: [\d,]+ \|)? `([0-9a-f]{64})` \|",
        text,
    )
    checked = []
    for relative, expected in rows:
        if relative.startswith(
            ("benchmark/src/", "benchmark/tests/", "data/raw/")
        ) or relative in {
            "benchmark/PROTOCOL.md",
            "benchmark/configs/benchmark.json",
            "discovery/02_dependency_analysis/outputs/canonical_panel.parquet",
            "discovery/02_dependency_analysis/outputs/canonical_signal_registry.csv",
            "discovery/02_dependency_analysis/PROTOCOL.md",
            "discovery/03_rolling_robustness/ROLLING_PROTOCOL.md",
        }:
            checked.append((relative, expected))
    failures = []
    for relative, expected in checked:
        actual = sha256(ROOT / relative)
        if actual != expected:
            failures.append(
                {"path": relative, "expected": expected, "actual": actual}
            )
    return len(checked), failures


def scalar_metrics(truth: np.ndarray, prediction: np.ndarray) -> tuple[float, float, float]:
    residual = truth.astype(float) - prediction.astype(float)
    mae = float(np.mean(np.abs(residual)))
    rmse = float(np.sqrt(np.mean(residual**2)))
    total = float(np.sum((truth - truth.mean()) ** 2))
    r2 = (
        float(1.0 - np.sum(residual**2) / total)
        if len(truth) >= 2 and total > 0
        else np.nan
    )
    return mae, rmse, r2


def main() -> None:
    started = time.perf_counter()
    panel = load_canonical_panel()
    timestamps = panel["timestamp"].to_numpy()
    segments = panel["segment_id"].to_numpy()
    registry = pd.read_csv(OUTPUTS / "run_registry.csv")
    metrics = pd.read_parquet(OUTPUTS / "metrics.parquet")
    selected = pd.read_csv(OUTPUTS / "selected_configs.csv")
    context = pd.read_parquet(OUTPUTS / "context_matched_metrics.parquet")
    runtime = json.loads((OUTPUTS / "deterministic_runtime.json").read_text())
    hash_count, hash_failures = frozen_hash_failures()
    failures: list[str] = []
    maxima = {
        "metric_absolute_difference": 0.0,
        "ridge_prediction_absolute_difference": 0.0,
        "relative_gain_formula_absolute_difference": 0.0,
    }

    if len(registry) != 630:
        failures.append(f"run count {len(registry)} != 630")
    if len(metrics) != 5040:
        failures.append(f"metric count {len(metrics)} != 5040")
    if set(metrics["run_id"]) != set(registry["run_id"]):
        failures.append("metric and registry run ID sets differ")
    if registry["run_id"].isna().any() or not registry["run_id"].is_unique:
        failures.append("run IDs missing or duplicated")
    if set(registry["model"]) != {"Persistence", "Ridge", "LightGBM"}:
        failures.append("unexpected model family")
    lead_counts = metrics.groupby("run_id")["lead"].agg(["nunique", "count"])
    if not ((lead_counts["nunique"] == 8) & (lead_counts["count"] == 8)).all():
        failures.append("not every run has exactly eight unique leads")
    if set(metrics["lead"]) != set(FUTURE_LEADS):
        failures.append("real future lead set differs")
    if len(selected) != 420:
        failures.append(f"selected config count {len(selected)} != 420")
    if len(context) != 4200:
        failures.append(f"context matched count {len(context)} != 4200")
    if not selected["exact_minimum_tie_count"].ge(1).all():
        failures.append("invalid exact tie-count audit")
    if selected["outer_test_columns_available_to_selector"].astype(bool).any():
        failures.append("selector reports outer-test access")
    expected_candidates = selected["model"].map({"Ridge": 15, "LightGBM": 24})
    if not selected["candidate_configuration_count"].eq(expected_candidates).all():
        failures.append("candidate configuration count differs")

    fold_cache: dict[str, list] = {}
    registry_index = registry.set_index(
        ["model", "feature_set", "machine", "outer_fold"]
    )
    prediction_files = sorted((OUTPUTS / "predictions").glob("*.parquet"))
    if len(prediction_files) != 630:
        failures.append(f"prediction file count {len(prediction_files)} != 630")
    figure_files = sorted(
        (OUTPUTS / "figures" / "deterministic").glob("*.png")
    )
    if len(figure_files) != 6:
        failures.append(f"deterministic figure count {len(figure_files)} != 6")

    for run in registry.itertuples(index=False):
        config = json.loads(run.config_json)
        expected_run_id = deterministic_run_id(
            run.model,
            run.feature_set,
            run.machine,
            int(run.outer_fold),
            int(run.context_length),
            config,
            None,
        )
        if expected_run_id != run.run_id:
            failures.append(f"run ID mismatch {run.run_id}")
        prediction = pd.read_parquet(ROOT / run.prediction_path)
        if len(prediction) % 8 or prediction["lead"].nunique() != 8:
            failures.append(f"prediction lead shape {run.run_id}")
            continue
        origins = np.sort(prediction["origin_index"].unique())
        if index_hash(origins) != run.test_sample_set_hash:
            failures.append(f"registry sample hash {run.run_id}")
        if not prediction["sample_id"].eq(
            prediction["machine"]
            + ":"
            + prediction["origin_index"].astype(str)
        ).all():
            failures.append(f"sample IDs {run.run_id}")
        expected_target_indices = (
            prediction["origin_index"].to_numpy()
            + prediction["lead"].to_numpy()
        )
        if not np.array_equal(
            prediction["target_index"].to_numpy(), expected_target_indices
        ):
            failures.append(f"target indices {run.run_id}")
        if not np.array_equal(
            prediction["target_timestamp"].to_numpy(),
            timestamps[expected_target_indices],
        ):
            failures.append(f"target timestamps {run.run_id}")
        target = panel[f"{run.machine}__cpu_utilization"].to_numpy()
        if not np.array_equal(
            prediction["y_true"].to_numpy(),
            target[expected_target_indices].astype(np.float32),
        ):
            failures.append(f"target values {run.run_id}")
        check_length = int(run.context_length) if run.context_length else 128
        if np.any(segments[origins - check_length + 1] != segments[origins]):
            failures.append(f"history segment crossing {run.run_id}")
        for lead in FUTURE_LEADS:
            if np.any(segments[origins + lead] != segments[origins]):
                failures.append(f"target segment crossing {run.run_id}/{lead}")
        if run.model == "Persistence":
            expected = target[
                prediction["origin_index"].to_numpy()
            ].astype(np.float32)
            if not np.array_equal(prediction["y_pred"].to_numpy(), expected):
                failures.append(f"persistence values {run.run_id}")
        stored = metrics[metrics["run_id"].eq(run.run_id)].set_index("lead")
        for lead in FUTURE_LEADS:
            rows = prediction[prediction["lead"].eq(lead)]
            computed = scalar_metrics(
                rows["y_true"].to_numpy(), rows["y_pred"].to_numpy()
            )
            saved = stored.loc[lead, ["mae", "rmse", "r2"]].to_numpy(dtype=float)
            difference = np.nanmax(np.abs(np.asarray(computed) - saved))
            maxima["metric_absolute_difference"] = max(
                maxima["metric_absolute_difference"], float(difference)
            )

    for machine in sorted(registry["machine"].unique()):
        eligible = joint_eligible_origins(panel, machine)
        folds = build_outer_folds(panel, eligible)
        fold_cache[machine] = folds
        for fold in folds:
            if not np.all(
                timestamps[fold.train_indices + 128]
                < fold.first_test_origin_timestamp
            ):
                failures.append(f"outer purge {machine}/{fold.fold}")
            inner = build_inner_split(panel, fold.train_indices)
            if not np.all(
                timestamps[inner.train_indices + 128]
                < inner.first_validation_origin_timestamp
            ):
                failures.append(f"inner purge {machine}/{fold.fold}")

    for choice in selected.itertuples(index=False):
        outer = fold_cache[choice.machine][int(choice.outer_fold) - 1]
        inner = build_inner_split(panel, outer.train_indices)
        selected_train = finite_feature_origins(
            panel,
            choice.machine,
            choice.feature_set,
            int(choice.context_length),
            inner.train_indices,
        )
        selected_validation = finite_feature_origins(
            panel,
            choice.machine,
            choice.feature_set,
            int(choice.context_length),
            inner.validation_indices,
        )
        if (
            index_hash(selected_train) != choice.inner_train_sample_set_hash
            or index_hash(selected_validation)
            != choice.inner_validation_sample_set_hash
        ):
            failures.append(
                f"inner selection sample hash {choice.model}/{choice.machine}/"
                f"{choice.outer_fold}/{choice.feature_set}"
            )
        if (
            len(selected_train) != choice.inner_train_n
            or len(selected_validation) != choice.inner_validation_n
        ):
            failures.append("inner selection sample count")

    ridge_registry = registry[registry["model"].eq("Ridge")]
    for run in ridge_registry.itertuples(index=False):
        outer = fold_cache[run.machine][int(run.outer_fold) - 1]
        length = int(run.context_length)
        train_indices = finite_feature_origins(
            panel, run.machine, run.feature_set, length, outer.train_indices
        )
        test_indices = finite_feature_origins(
            panel, run.machine, run.feature_set, length, outer.test_indices
        )
        X_train, y_train = arrays(
            panel, run.machine, run.feature_set, length, train_indices
        )
        X_test, _ = arrays(
            panel, run.machine, run.feature_set, length, test_indices
        )
        model = RidgeForecaster(alpha=json.loads(run.config_json)["alpha"])
        model.fit(X_train, y_train)
        reproduced = model.predict(X_test)
        saved = (
            pd.read_parquet(ROOT / run.prediction_path)
            .pivot(index="origin_index", columns="lead", values="y_pred")
            .reindex(index=test_indices, columns=FUTURE_LEADS)
            .to_numpy()
        )
        maxima["ridge_prediction_absolute_difference"] = max(
            maxima["ridge_prediction_absolute_difference"],
            float(np.max(np.abs(reproduced - saved))),
        )

    for row in context.itertuples(index=False):
        if (
            row.candidate_sample_set_hash != row.matched_f0_sample_set_hash
            or not row.target_rows_exact_match
        ):
            failures.append(f"context row mismatch {row.run_id}/{row.lead}")
        expected_gain = (
            100.0
            * (row.matched_f0_mae - row.candidate_mae)
            / row.matched_f0_mae
            if row.matched_f0_mae
            else np.nan
        )
        maxima["relative_gain_formula_absolute_difference"] = max(
            maxima["relative_gain_formula_absolute_difference"],
            float(abs(expected_gain - row.relative_context_mae_gain_pct)),
        )

    if maxima["metric_absolute_difference"] > 1e-4:
        failures.append("stored metrics differ from prediction recomputation")
    if maxima["ridge_prediction_absolute_difference"] > 1e-10:
        failures.append("Ridge train-only refit reproduction differs")
    if maxima["relative_gain_formula_absolute_difference"] > 1e-10:
        failures.append("context gain formula differs")
    if hash_failures:
        failures.append("frozen hash mismatch")
    if runtime["families"]["Ridge"]["candidate_fits"] != 3150:
        failures.append("Ridge candidate fit accounting")
    if (
        runtime["families"]["LightGBM"]["candidate_fits"] != 40320
        or runtime["families"]["LightGBM"]["final_models"] != 1680
    ):
        failures.append("LightGBM fit accounting")

    prediction_bytes = sum(path.stat().st_size for path in prediction_files)
    validation = {
        "status": "PASS" if not failures else "FAIL",
        "registered_runs": len(registry),
        "lead_metric_rows": len(metrics),
        "selected_config_rows": len(selected),
        "context_matched_rows": len(context),
        "prediction_files": len(prediction_files),
        "deterministic_figures": len(figure_files),
        "prediction_artifact_bytes": prediction_bytes,
        "all_eight_real_leads_per_run": bool(
            ((lead_counts["nunique"] == 8) & (lead_counts["count"] == 8)).all()
        ),
        "duplicate_run_ids": int(registry["run_id"].duplicated().sum()),
        "missing_run_ids": int(registry["run_id"].isna().sum()),
        "segment_crossing_histories": sum(
            "history segment crossing" in failure for failure in failures
        ),
        "segment_crossing_targets": sum(
            "target segment crossing" in failure for failure in failures
        ),
        "outer_target_time_leakage": sum(
            failure.startswith("outer purge") for failure in failures
        ),
        "inner_target_time_leakage": sum(
            failure.startswith("inner purge") for failure in failures
        ),
        "outer_test_controlled_selection": bool(
            selected["outer_test_columns_available_to_selector"].astype(bool).any()
        ),
        "train_only_ridge_preprocessing_reproduced": (
            maxima["ridge_prediction_absolute_difference"] <= 1e-10
        ),
        "candidate_matched_f0_rows_equal": not any(
            "context row mismatch" in failure for failure in failures
        ),
        "persistence_exact": not any(
            "persistence values" in failure for failure in failures
        ),
        "target_timestamps_exact": not any(
            "target timestamps" in failure for failure in failures
        ),
        "metrics_recomputed": maxima["metric_absolute_difference"] <= 1e-4,
        "metric_recomputation_absolute_tolerance": 1e-4,
        "maximum_differences": maxima,
        "frozen_hashes_checked": hash_count,
        "frozen_hash_failures": hash_failures,
        "canonical_panel_sha256": sha256(PANEL_PATH),
        "raw_and_canonical_hashes_unchanged": not hash_failures,
        "ridge_candidate_configurations_fitted": runtime["families"]["Ridge"][
            "candidate_fits"
        ],
        "lightgbm_inner_models_fitted": runtime["families"]["LightGBM"][
            "candidate_fits"
        ],
        "lightgbm_final_models_fitted": runtime["families"]["LightGBM"][
            "final_models"
        ],
        "validation_runtime_seconds": time.perf_counter() - started,
        "validation_peak_rss_bytes": int(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        ),
        "failures": failures,
    }
    (OUTPUTS / "deterministic_run_validation.json").write_text(
        json.dumps(validation, indent=2) + "\n"
    )
    print(json.dumps(validation, indent=2))
    if failures:
        raise RuntimeError("Deterministic benchmark validation failed")


if __name__ == "__main__":
    main()
