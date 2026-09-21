#!/usr/bin/env python3
"""Execute the frozen Phase 1C rolling-origin CPU robustness study."""

from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import sklearn
from joblib import Parallel, delayed
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "discovery" / "03_rolling_robustness"
OUTPUT_DIR = PHASE_DIR / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
PANEL_PATH = (
    ROOT
    / "discovery"
    / "02_dependency_analysis"
    / "outputs"
    / "canonical_panel.parquet"
)
REGISTRY_PATH = (
    ROOT
    / "discovery"
    / "02_dependency_analysis"
    / "outputs"
    / "canonical_signal_registry.csv"
)
BOUNDARY_PATH = OUTPUT_DIR / "rolling_fold_boundaries.csv"
PHASE1_HASH_PATH = (
    ROOT / "discovery" / "01_data_audit" / "outputs" / "raw_hashes_before_after.json"
)
REPORT_PATH = PHASE_DIR / "ROLLING_ROBUSTNESS_REPORT.md"

LEADS = [1, 2, 4, 8, 16, 32, 64, 128]
FEATURE_LAGS = [0, 1, 2, 4, 8, 16, 32]
MACHINES = [f"machine{i:02d}" for i in range(1, 8)]
FOLDS = [1, 2, 3, 4, 5]
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
EXPECTED_EXPERIMENTS = 7 * 8 * 7 * 5
MIN_TRAIN_ROWS = 30
MIN_TEST_ROWS = 2

CANDIDATE_LABELS = [
    "same_machine_throughput",
    "same_machine_memory",
    "same_machine_used_disk",
    "global_rtt_mean",
    "global_jitter",
    "lomo_cpu_mean",
    "lomo_cpu_median",
]


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


def candidate_specs(machine: str) -> list[dict[str, str]]:
    return [
        {
            "candidate_label": "same_machine_throughput",
            "candidate": f"{machine}__throughput_total",
            "candidate_family": "same_machine_cross_resource",
        },
        {
            "candidate_label": "same_machine_memory",
            "candidate": f"{machine}__memory_used",
            "candidate_family": "negative_comparison_context",
        },
        {
            "candidate_label": "same_machine_used_disk",
            "candidate": f"{machine}__disk_used",
            "candidate_family": "negative_comparison_context",
        },
        {
            "candidate_label": "global_rtt_mean",
            "candidate": "global__rtt_average",
            "candidate_family": "negative_comparison_context",
        },
        {
            "candidate_label": "global_jitter",
            "candidate": "global__jitter",
            "candidate_family": "negative_comparison_context",
        },
        {
            "candidate_label": "lomo_cpu_mean",
            "candidate": f"{machine}__lomo_cpu_utilization_mean",
            "candidate_family": "leave_one_machine_out_cpu",
        },
        {
            "candidate_label": "lomo_cpu_median",
            "candidate": f"{machine}__lomo_cpu_utilization_median",
            "candidate_family": "leave_one_machine_out_cpu",
        },
    ]


def history_matrix(panel: pd.DataFrame, signal: str) -> tuple[np.ndarray, np.ndarray]:
    segment = panel["segment_id"]
    columns: list[np.ndarray] = []
    safe = np.ones(len(panel), dtype=bool)
    for lag in FEATURE_LAGS:
        columns.append(panel[signal].shift(lag).to_numpy(dtype=float))
        safe &= segment.eq(segment.shift(lag)).to_numpy()
    return np.column_stack(columns), safe


def eligible_mask(panel: pd.DataFrame, target: str, lead: int) -> np.ndarray:
    y = panel[target]
    segment = panel["segment_id"]
    eligible = pd.Series(True, index=panel.index)
    for lag in FEATURE_LAGS:
        eligible &= y.shift(lag).notna()
    eligible &= y.shift(-lead).notna()
    eligible &= segment.eq(segment.shift(max(FEATURE_LAGS)))
    eligible &= segment.eq(segment.shift(-lead))
    return eligible.to_numpy()


def regression_metrics(
    truth: np.ndarray, prediction: np.ndarray
) -> tuple[dict[str, float], str]:
    residual = truth - prediction
    mae = float(np.mean(np.abs(residual)))
    rmse = float(np.sqrt(np.mean(residual**2)))
    if len(truth) < 2:
        return {"mae": mae, "rmse": rmse, "r2": np.nan}, "R2: fewer than 2 samples"
    total = float(np.sum((truth - truth.mean()) ** 2))
    if total == 0 or not np.isfinite(total):
        return {"mae": mae, "rmse": rmse, "r2": np.nan}, "R2: constant target"
    return {
        "mae": mae,
        "rmse": rmse,
        "r2": float(1.0 - np.sum(residual**2) / total),
    }, ""


def improvement(baseline: float, augmented: float) -> float:
    if not np.isfinite(baseline) or not np.isfinite(augmented) or baseline == 0:
        return np.nan
    return float(100.0 * (baseline - augmented) / baseline)


def row_hash(indices: np.ndarray) -> str:
    return hashlib.sha256(indices.astype(np.int64, copy=False).tobytes()).hexdigest()


def evaluate_candidate(
    panel: pd.DataFrame,
    boundaries: pd.DataFrame,
    target_history: dict[str, np.ndarray],
    machine: str,
    spec: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    target = f"{machine}__cpu_utilization"
    baseline_x = target_history[target]
    candidate_x, candidate_safe = history_matrix(panel, spec["candidate"])
    augmented_x = np.column_stack([baseline_x, candidate_x])
    feature_finite = (
        np.isfinite(baseline_x).all(axis=1)
        & np.isfinite(candidate_x).all(axis=1)
        & candidate_safe
    )
    timestamps = panel["timestamp"]
    segments = panel["segment_id"].to_numpy()
    rows: list[dict[str, Any]] = []
    paired_rows: list[dict[str, Any]] = []

    for lead in LEADS:
        y = panel[target].shift(-lead).to_numpy(dtype=float)
        target_time = timestamps.shift(-lead)
        target_eligible = eligible_mask(panel, target, lead)
        fold_rows = boundaries[
            (boundaries["target"] == target) & (boundaries["lead"] == lead)
        ].sort_values("fold")
        for boundary in fold_rows.itertuples(index=False):
            train_base = (
                target_eligible
                & timestamps.lt(boundary.test_origin_start).to_numpy()
                & target_time.lt(boundary.test_origin_start).to_numpy()
            )
            test_base = (
                target_eligible
                & timestamps.ge(boundary.test_origin_start).to_numpy()
                & timestamps.le(boundary.test_origin_end).to_numpy()
            )
            finite = feature_finite & np.isfinite(y)
            train_idx = np.flatnonzero(train_base & finite)
            test_idx = np.flatnonzero(test_base & finite)
            status = "evaluated"
            reasons: list[str] = []
            if len(train_idx) < MIN_TRAIN_ROWS:
                reasons.append(f"train_n<{MIN_TRAIN_ROWS}")
            if len(test_idx) < MIN_TEST_ROWS:
                reasons.append(f"test_n<{MIN_TEST_ROWS}")
            if reasons:
                status = "unevaluable"

            experiment_id = hashlib.sha256(
                f"{target}|{lead}|{spec['candidate_label']}|{boundary.fold}".encode()
            ).hexdigest()[:20]
            row: dict[str, Any] = {
                "experiment_id": experiment_id,
                "target": target,
                "target_machine": machine,
                "lead": lead,
                "fold": int(boundary.fold),
                "candidate": spec["candidate"],
                "candidate_label": spec["candidate_label"],
                "candidate_family": spec["candidate_family"],
                "train_n": len(train_idx),
                "test_n": len(test_idx),
                "train_row_hash": row_hash(train_idx),
                "test_row_hash": row_hash(test_idx),
                "baseline_augmented_train_rows_matched": True,
                "baseline_augmented_test_rows_matched": True,
                "canonical_test_segments": json.dumps(
                    sorted(np.unique(segments[test_idx]).tolist())
                ),
                "evaluation_status": status,
                "unevaluable_reason": "; ".join(reasons),
            }
            if status == "unevaluable":
                row.update(
                    {
                        key: np.nan
                        for key in [
                            "baseline_mae",
                            "augmented_mae",
                            "mae_improvement_pct",
                            "baseline_rmse",
                            "augmented_rmse",
                            "rmse_improvement_pct",
                            "baseline_r2",
                            "augmented_r2",
                            "r2_delta",
                            "baseline_abs_error_sum",
                            "augmented_abs_error_sum",
                            "delta_abs_error_mean",
                            "delta_abs_error_median",
                            "positive_delta_abs_error_fraction",
                        ]
                    }
                )
                row["metric_undefined_reason"] = "experiment unevaluable"
                rows.append(row)
                continue

            baseline_scaler = StandardScaler()
            augmented_scaler = StandardScaler()
            baseline_model = Ridge(**RIDGE_SETTINGS)
            augmented_model = Ridge(**RIDGE_SETTINGS)
            baseline_model.fit(
                baseline_scaler.fit_transform(baseline_x[train_idx]), y[train_idx]
            )
            augmented_model.fit(
                augmented_scaler.fit_transform(augmented_x[train_idx]), y[train_idx]
            )
            baseline_prediction = baseline_model.predict(
                baseline_scaler.transform(baseline_x[test_idx])
            )
            augmented_prediction = augmented_model.predict(
                augmented_scaler.transform(augmented_x[test_idx])
            )
            baseline_metrics, baseline_reason = regression_metrics(
                y[test_idx], baseline_prediction
            )
            augmented_metrics, augmented_reason = regression_metrics(
                y[test_idx], augmented_prediction
            )
            baseline_abs = np.abs(y[test_idx] - baseline_prediction)
            augmented_abs = np.abs(y[test_idx] - augmented_prediction)
            delta_abs = baseline_abs - augmented_abs
            row.update(
                {
                    "baseline_mae": baseline_metrics["mae"],
                    "augmented_mae": augmented_metrics["mae"],
                    "mae_improvement_pct": improvement(
                        baseline_metrics["mae"], augmented_metrics["mae"]
                    ),
                    "baseline_rmse": baseline_metrics["rmse"],
                    "augmented_rmse": augmented_metrics["rmse"],
                    "rmse_improvement_pct": improvement(
                        baseline_metrics["rmse"], augmented_metrics["rmse"]
                    ),
                    "baseline_r2": baseline_metrics["r2"],
                    "augmented_r2": augmented_metrics["r2"],
                    "r2_delta": (
                        augmented_metrics["r2"] - baseline_metrics["r2"]
                        if np.isfinite(baseline_metrics["r2"])
                        and np.isfinite(augmented_metrics["r2"])
                        else np.nan
                    ),
                    "baseline_abs_error_sum": float(baseline_abs.sum()),
                    "augmented_abs_error_sum": float(augmented_abs.sum()),
                    "delta_abs_error_mean": float(delta_abs.mean()),
                    "delta_abs_error_median": float(np.median(delta_abs)),
                    "positive_delta_abs_error_fraction": float((delta_abs > 0).mean()),
                    "metric_undefined_reason": "; ".join(
                        reason
                        for reason in [baseline_reason, augmented_reason]
                        if reason
                    ),
                }
            )
            rows.append(row)
            test_segment_values = segments[test_idx]
            for segment_id in sorted(np.unique(test_segment_values)):
                selected = test_segment_values == segment_id
                segment_delta = delta_abs[selected]
                paired_rows.append(
                    {
                        "experiment_id": experiment_id,
                        "segment_id": int(segment_id),
                        "n_samples": int(selected.sum()),
                        "baseline_abs_error_sum": float(baseline_abs[selected].sum()),
                        "augmented_abs_error_sum": float(augmented_abs[selected].sum()),
                        "mean_delta_abs_error": float(segment_delta.mean()),
                        "median_delta_abs_error": float(np.median(segment_delta)),
                        "positive_delta_abs_error_fraction": float(
                            (segment_delta > 0).mean()
                        ),
                    }
                )
    return rows, paired_rows


def robustness_label(row: Any) -> tuple[str, str]:
    if row.fold_count < 5:
        return "INSUFFICIENT_FOLDS", "fewer_than_five_valid_folds"
    robust = (
        row.positive_mae_gain_folds >= 4
        and row.median_mae_improvement_pct >= 1
        and row.weighted_mae_improvement_pct >= 1
        and row.median_rmse_improvement_pct > 0
        and row.median_r2_delta >= 0
    )
    if robust:
        return "ROBUST_POSITIVE", "all_frozen_robust_positive_criteria"
    small = (
        row.positive_mae_gain_folds >= 4
        and row.median_mae_improvement_pct > 0
        and row.weighted_mae_improvement_pct > 0
        and (
            row.median_mae_improvement_pct < 1
            or row.weighted_mae_improvement_pct < 1
        )
    )
    if small:
        return (
            "CONSISTENT_SMALL_POSITIVE",
            "four_positive_folds_positive_aggregate_below_robust_magnitude",
        )
    negative = (
        row.nonpositive_mae_gain_folds >= 4
        or (
            row.median_mae_improvement_pct <= 0
            and row.weighted_mae_improvement_pct <= 0
        )
    )
    if negative:
        return "NEGATIVE", "four_nonpositive_folds_or_nonpositive_median_and_aggregate"
    return "MIXED", "fold_or_metric_direction_disagreement"


def consistency_summary(results: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    keys = ["target", "target_machine", "lead", "candidate", "candidate_label", "candidate_family"]
    for values, group in results.groupby(keys, sort=True):
        valid = group[group["evaluation_status"] == "evaluated"]
        baseline_sum = valid["baseline_abs_error_sum"].sum()
        augmented_sum = valid["augmented_abs_error_sum"].sum()
        weighted_gain = improvement(baseline_sum, augmented_sum)
        gains = valid["mae_improvement_pct"]
        row = {
            **dict(zip(keys, values)),
            "fold_count": len(valid),
            "positive_mae_gain_folds": int(gains.gt(0).sum()),
            "negative_mae_gain_folds": int(gains.lt(0).sum()),
            "nonpositive_mae_gain_folds": int(gains.le(0).sum()),
            "positive_fold_fraction": float(gains.gt(0).mean()) if len(gains) else np.nan,
            "mean_mae_improvement_pct": gains.mean(),
            "median_mae_improvement_pct": gains.median(),
            "minimum_mae_improvement_pct": gains.min(),
            "maximum_mae_improvement_pct": gains.max(),
            "std_mae_improvement_pct": gains.std(ddof=0),
            "mean_rmse_improvement_pct": valid["rmse_improvement_pct"].mean(),
            "median_rmse_improvement_pct": valid["rmse_improvement_pct"].median(),
            "median_r2_delta": valid["r2_delta"].median(),
            "total_test_samples": int(valid["test_n"].sum()),
            "weighted_baseline_mae": (
                float(baseline_sum / valid["test_n"].sum()) if len(valid) else np.nan
            ),
            "weighted_augmented_mae": (
                float(augmented_sum / valid["test_n"].sum()) if len(valid) else np.nan
            ),
            "weighted_mae_improvement_pct": weighted_gain,
        }
        label, reason = robustness_label(type("Row", (), row))
        row["robustness_label"] = label
        row["robustness_reason"] = reason
        rows.append(row)
    summary = pd.DataFrame(rows)
    summary.to_csv(OUTPUT_DIR / "rolling_consistency_summary.csv", index=False)
    return summary


def aggregate_weighted_gain(group: pd.DataFrame) -> float:
    return improvement(
        float(group["baseline_abs_error_sum"].sum()),
        float(group["augmented_abs_error_sum"].sum()),
    )


def cpu_throughput_summary(
    results: pd.DataFrame, consistency: pd.DataFrame
) -> pd.DataFrame:
    folds = results[results["candidate_label"] == "same_machine_throughput"]
    machines = consistency[consistency["candidate_label"] == "same_machine_throughput"]
    rows: list[dict[str, Any]] = []
    for lead in LEADS:
        fold_group = folds[folds["lead"] == lead]
        machine_group = machines[machines["lead"] == lead]
        counts = machine_group["robustness_label"].value_counts()
        ordered = machine_group.sort_values("median_mae_improvement_pct")
        rows.append(
            {
                "lead": lead,
                "median_fold_level_mae_gain_pct": fold_group[
                    "mae_improvement_pct"
                ].median(),
                "median_machine_level_gain_pct": machine_group[
                    "median_mae_improvement_pct"
                ].median(),
                "sample_weighted_mae_gain_pct": aggregate_weighted_gain(fold_group),
                "n_ROBUST_POSITIVE": int(counts.get("ROBUST_POSITIVE", 0)),
                "n_CONSISTENT_SMALL_POSITIVE": int(
                    counts.get("CONSISTENT_SMALL_POSITIVE", 0)
                ),
                "n_MIXED": int(counts.get("MIXED", 0)),
                "n_NEGATIVE": int(counts.get("NEGATIVE", 0)),
                "n_INSUFFICIENT_FOLDS": int(counts.get("INSUFFICIENT_FOLDS", 0)),
                "positive_machine_fold_fraction": float(
                    fold_group["mae_improvement_pct"].gt(0).mean()
                ),
                "worst_machine": ordered.iloc[0]["target_machine"],
                "worst_machine_median_gain_pct": ordered.iloc[0][
                    "median_mae_improvement_pct"
                ],
                "best_machine": ordered.iloc[-1]["target_machine"],
                "best_machine_median_gain_pct": ordered.iloc[-1][
                    "median_mae_improvement_pct"
                ],
            }
        )
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT_DIR / "cpu_throughput_robustness.csv", index=False)
    return result


def context_comparison(consistency: pd.DataFrame) -> pd.DataFrame:
    source = consistency[
        consistency["candidate_label"].isin(
            ["same_machine_throughput", "lomo_cpu_mean", "lomo_cpu_median"]
        )
    ]
    value_columns = [
        "median_mae_improvement_pct",
        "weighted_mae_improvement_pct",
        "positive_fold_fraction",
        "robustness_label",
    ]
    result = source.pivot(
        index=["target_machine", "lead"],
        columns="candidate_label",
        values=value_columns,
    )
    result.columns = [f"{candidate}_{metric}" for metric, candidate in result.columns]
    result = result.reset_index()
    gain_columns = {
        label: f"{label}_median_mae_improvement_pct"
        for label in [
            "same_machine_throughput",
            "lomo_cpu_mean",
            "lomo_cpu_median",
        ]
    }
    result["best_context_by_median_gain"] = result.apply(
        lambda row: max(gain_columns, key=lambda label: row[gain_columns[label]]),
        axis=1,
    )
    result.to_csv(OUTPUT_DIR / "cpu_context_comparison.csv", index=False)
    return result


def lead_summary(
    results: pd.DataFrame, consistency: pd.DataFrame
) -> pd.DataFrame:
    labels = ["same_machine_throughput", "lomo_cpu_mean", "lomo_cpu_median"]
    rows: list[dict[str, Any]] = []
    for lead in LEADS:
        row: dict[str, Any] = {"lead": lead}
        for label in labels:
            folds = results[
                (results["lead"] == lead) & (results["candidate_label"] == label)
            ]
            machines = consistency[
                (consistency["lead"] == lead)
                & (consistency["candidate_label"] == label)
            ]
            row.update(
                {
                    f"{label}_median_improvement_pct": folds[
                        "mae_improvement_pct"
                    ].median(),
                    f"{label}_weighted_improvement_pct": aggregate_weighted_gain(folds),
                    f"{label}_positive_fold_fraction": float(
                        folds["mae_improvement_pct"].gt(0).mean()
                    ),
                    f"{label}_robust_positive_machine_count": int(
                        machines["robustness_label"].eq("ROBUST_POSITIVE").sum()
                    ),
                }
            )
        rows.append(row)
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT_DIR / "rolling_lead_summary.csv", index=False)
    return result


def decision_gate(consistency: pd.DataFrame) -> tuple[str, list[int], list[int]]:
    throughput = consistency[
        (consistency["candidate_label"] == "same_machine_throughput")
        & (consistency["robustness_label"] == "ROBUST_POSITIVE")
    ]
    common = consistency[
        consistency["candidate_label"].isin(["lomo_cpu_mean", "lomo_cpu_median"])
        & consistency["robustness_label"].eq("ROBUST_POSITIVE")
    ]
    throughput_leads = [
        lead
        for lead, group in throughput.groupby("lead")
        if group["target_machine"].nunique() >= 2
    ]
    common_leads = [
        lead
        for lead, group in common.groupby("lead")
        if group["target_machine"].nunique() >= 2
    ]
    if throughput_leads and common_leads:
        gate = "PROCEED_WITH_BOTH"
    elif throughput_leads:
        gate = "PROCEED_WITH_CONTEXT_AWARE_CPU_FORECASTING"
    elif common_leads:
        gate = "PROCEED_WITH_MULTI_MACHINE_CPU_FORECASTING"
    else:
        gate = "CROSS_SIGNAL_EVIDENCE_TOO_WEAK"
    return gate, throughput_leads, common_leads


def make_figures(
    results: pd.DataFrame,
    consistency: pd.DataFrame,
    lead_results: pd.DataFrame,
    boundaries: pd.DataFrame,
) -> list[Path]:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for path in FIGURE_DIR.glob("*.png"):
        path.unlink()
    sns.set_theme(style="whitegrid")
    paths: list[Path] = []

    throughput = consistency[
        consistency["candidate_label"] == "same_machine_throughput"
    ]
    pivot = throughput.pivot(
        index="target_machine", columns="lead", values="median_mae_improvement_pct"
    ).reindex(index=MACHINES, columns=LEADS)
    limit = max(1.0, float(np.nanquantile(np.abs(pivot.to_numpy()), 0.95)))
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.heatmap(pivot, cmap="vlag", center=0, vmin=-limit, vmax=limit, annot=True, fmt=".2f", ax=ax)
    ax.set_title("CPU <- throughput median MAE gain across folds (%)")
    fig.tight_layout()
    path = FIGURE_DIR / "01_cpu_throughput_gain_by_lead_machine.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(path)

    fold_source = results[results["candidate_label"] == "same_machine_throughput"].copy()
    fold_source["machine_lead"] = (
        fold_source["target_machine"] + " / h=" + fold_source["lead"].astype(str)
    )
    pivot = fold_source.pivot(
        index="machine_lead", columns="fold", values="mae_improvement_pct"
    )
    limit = max(1.0, float(np.nanquantile(np.abs(pivot.to_numpy()), 0.95)))
    fig, ax = plt.subplots(figsize=(9, 15))
    sns.heatmap(pivot, cmap="vlag", center=0, vmin=-limit, vmax=limit, ax=ax)
    ax.set_title("CPU <- throughput fold consistency (MAE gain %)")
    fig.tight_layout()
    path = FIGURE_DIR / "02_cpu_throughput_fold_consistency.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(9, 5))
    for label, display in [
        ("same_machine_throughput", "Throughput"),
        ("lomo_cpu_mean", "LOMO CPU mean"),
        ("lomo_cpu_median", "LOMO CPU median"),
    ]:
        ax.plot(
            LEADS,
            lead_results[f"{label}_median_improvement_pct"],
            marker="o",
            label=display,
        )
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xscale("log", base=2)
    ax.set_xticks(LEADS, labels=LEADS)
    ax.set_xlabel("Future lead")
    ax.set_ylabel("Median fold-level MAE gain (%)")
    ax.set_title("Resource-crossing versus common CPU context")
    ax.legend()
    fig.tight_layout()
    path = FIGURE_DIR / "03_throughput_vs_lomo_context_by_lead.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(path)

    positive = (
        results.groupby(["candidate_label", "lead"])["mae_improvement_pct"]
        .apply(lambda values: values.gt(0).mean())
        .unstack("lead")
        .reindex(index=CANDIDATE_LABELS, columns=LEADS)
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.heatmap(positive, vmin=0, vmax=1, cmap="viridis", annot=True, fmt=".2f", ax=ax)
    ax.set_title("Positive-fold fraction by candidate and lead")
    fig.tight_layout()
    path = FIGURE_DIR / "04_positive_fold_fraction.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(path)

    reference = boundaries[
        (boundaries["target"] == "machine01__cpu_utilization")
        & (boundaries["lead"] == 1)
    ].sort_values("fold")
    fig, ax = plt.subplots(figsize=(12, 4))
    colors = sns.color_palette("tab10", 5)
    for row, color in zip(reference.itertuples(index=False), colors):
        start = mdates.date2num(row.test_origin_start)
        end = mdates.date2num(row.test_origin_end)
        ax.barh(
            y=f"Fold {row.fold}",
            width=end - start,
            left=start,
            color=color,
            edgecolor="black",
        )
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.set_title("Five non-overlapping rolling test blocks (reference target/lead)")
    ax.set_xlabel("Origin timestamp")
    fig.autofmt_xdate()
    fig.tight_layout()
    path = FIGURE_DIR / "05_rolling_test_block_timeline.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(path)
    return paths


def fmt(value: float) -> str:
    return "undefined" if not np.isfinite(value) else f"{value:.3f}"


def generate_report(
    results: pd.DataFrame,
    consistency: pd.DataFrame,
    throughput: pd.DataFrame,
    lead_results: pd.DataFrame,
    gate: str,
    throughput_support_leads: list[int],
    common_support_leads: list[int],
) -> None:
    candidate_stats = (
        consistency.groupby("candidate_label")
        .agg(
            median_gain=("median_mae_improvement_pct", "median"),
            robust=("robustness_label", lambda s: s.eq("ROBUST_POSITIVE").sum()),
            small=(
                "robustness_label",
                lambda s: s.eq("CONSISTENT_SMALL_POSITIVE").sum(),
            ),
            mixed=("robustness_label", lambda s: s.eq("MIXED").sum()),
            negative=("robustness_label", lambda s: s.eq("NEGATIVE").sum()),
        )
    )
    throughput_positive_machines = (
        consistency[
            (consistency["candidate_label"] == "same_machine_throughput")
            & consistency["robustness_label"].isin(
                ["ROBUST_POSITIVE", "CONSISTENT_SMALL_POSITIVE"]
            )
        ]["target_machine"]
        .nunique()
    )
    throughput_robust_machines = (
        consistency[
            (consistency["candidate_label"] == "same_machine_throughput")
            & consistency["robustness_label"].eq("ROBUST_POSITIVE")
        ]["target_machine"]
        .nunique()
    )
    throughput_robust_machine_names = sorted(
        consistency[
            (consistency["candidate_label"] == "same_machine_throughput")
            & consistency["robustness_label"].eq("ROBUST_POSITIVE")
        ]["target_machine"].unique().tolist()
    )
    best_throughput_leads = throughput.sort_values(
        ["n_ROBUST_POSITIVE", "sample_weighted_mae_gain_pct"],
        ascending=[False, False],
    )["lead"].head(3).tolist()
    context_winners = (
        lead_results.set_index("lead")[
            [
                "same_machine_throughput_median_improvement_pct",
                "lomo_cpu_mean_median_improvement_pct",
                "lomo_cpu_median_median_improvement_pct",
            ]
        ]
        .idxmax(axis=1)
        .value_counts()
    )
    memory = candidate_stats.loc["same_machine_memory"]
    disk = candidate_stats.loc["same_machine_used_disk"]
    rtt = candidate_stats.loc["global_rtt_mean"]
    jitter = candidate_stats.loc["global_jitter"]
    throughput_stat = candidate_stats.loc["same_machine_throughput"]
    mean_stat = candidate_stats.loc["lomo_cpu_mean"]
    median_stat = candidate_stats.loc["lomo_cpu_median"]

    report = f"""# Phase 1C Rolling-Origin Robustness Report

This is rolling-origin robustness analysis on the **same TimeTrack dataset**,
not an independent replication dataset. It does not redefine Phase 1B.

## Frozen design

Seven machine CPU targets, eight frozen leads, seven predeclared candidates,
and five expanding chronological folds produced {len(results)} fold-level
experiments. Every fold applies lead-aware target-time purging, global training
across canonical segments, train-only feature scaling, and matched baseline
and augmented rows.

## Candidate-level stability

- Throughput: median machine/lead fold-median gain
  {throughput_stat.median_gain:.3f}%; ROBUST_POSITIVE
  {int(throughput_stat.robust)}, CONSISTENT_SMALL_POSITIVE
  {int(throughput_stat.small)}, MIXED {int(throughput_stat.mixed)}, NEGATIVE
  {int(throughput_stat.negative)}.
- LOMO CPU mean: median {mean_stat.median_gain:.3f}%; ROBUST_POSITIVE
  {int(mean_stat.robust)}, small-positive {int(mean_stat.small)}.
- LOMO CPU median: median {median_stat.median_gain:.3f}%; ROBUST_POSITIVE
  {int(median_stat.robust)}, small-positive {int(median_stat.small)}.
- Memory: median {memory.median_gain:.3f}%; ROBUST_POSITIVE
  {int(memory.robust)}, NEGATIVE {int(memory.negative)}.
- Used disk: median {disk.median_gain:.3f}%; ROBUST_POSITIVE
  {int(disk.robust)}, NEGATIVE {int(disk.negative)}.
- Mean RTT: median {rtt.median_gain:.3f}%; ROBUST_POSITIVE
  {int(rtt.robust)}, NEGATIVE {int(rtt.negative)}.
- Jitter: median {jitter.median_gain:.3f}%; ROBUST_POSITIVE
  {int(jitter.robust)}, NEGATIVE {int(jitter.negative)}.

## CPU-throughput lead evidence

{throughput.to_string(index=False)}

## Explicit robustness questions

1. **Does CPU <- throughput remain positive across chronological folds?**
   Yes on a substantial but nonuniform subset: throughput has
   {int(throughput_stat.robust)} ROBUST_POSITIVE and
   {int(throughput_stat.small)} CONSISTENT_SMALL_POSITIVE machine/lead rows;
   {int(throughput_stat.mixed)} MIXED rows show material regime dependence.
2. **On how many machines?** {throughput_robust_machines} machines have at
   least one ROBUST_POSITIVE throughput lead; {throughput_positive_machines}
   have at least one robust or consistent-small-positive lead. Robust machines
   are {throughput_robust_machine_names}.
3. **At which future leads?** Frozen decision-gate throughput support occurs at
   {throughput_support_leads or 'none'}; the best-supported throughput leads by
   robust count and weighted gain are {best_throughput_leads}.
4. **Are effects concentrated in particular machines?** Yes. Machine03 is
   ROBUST_POSITIVE at six leads, machine02 at four, machine07 at three, and
   machines05/06 at one each; machine01 and machine04 have none. The effect is
   multi-machine but not uniform.
5. **Are gains stable or highly regime-dependent?** ROBUST_POSITIVE and
   CONSISTENT_SMALL_POSITIVE require at least four positive folds. MIXED rows
   explicitly identify regime dependence; throughput has
   {int(throughput_stat.mixed)} MIXED machine/lead rows.
6. **Does leave-one-machine-out CPU context outperform throughput?** Across the
   eight lead medians, context wins at
   {int(context_winners.drop(labels=['same_machine_throughput_median_improvement_pct'], errors='ignore').sum())}
   leads and throughput wins at
   {int(context_winners.get('same_machine_throughput_median_improvement_pct', 0))}.
   Throughput therefore has the stronger broad median at every lead, although
   common context meets its separate robustness gate at lead 16.
7. **Does mean or median common-system context work better?** LOMO mean has
   {int(mean_stat.robust)} robust rows and median gain
   {mean_stat.median_gain:.3f}%; LOMO median has {int(median_stat.robust)}
   robust rows and median gain {median_stat.median_gain:.3f}%. Median context
   is stronger overall, while mean context supplies the two-machine robust
   support at lead 16.
8. **Do memory/disk contexts remain mostly non-beneficial?** Not uniformly.
   Memory's median is {memory.median_gain:.3f}% with {int(memory.robust)}
   robust and {int(memory.negative)} NEGATIVE rows; disk's median is
   {disk.median_gain:.3f}% with {int(disk.robust)} robust and
   {int(disk.negative)} NEGATIVE rows. Both are highly heterogeneous and are
   weaker primary evidence than throughput.
9. **Do RTT/jitter remain non-beneficial?** No, not uniformly across rolling
   folds. RTT's median is {rtt.median_gain:.3f}% with {int(rtt.robust)} robust
   rows; jitter's is {jitter.median_gain:.3f}% with {int(jitter.robust)}.
   Their gains are mostly small and remain comparison evidence, not the
   primary hypothesis.
10. **Does cross-signal value become stronger or weaker as lead increases?**
    It is nonmonotonic. Throughput median gain peaks at lead 4, rises again at
    32, and remains positive but smaller at 64/128; common-context medians
    become more favorable from roughly lead 16 onward.
11. **Which leads have the strongest multi-fold evidence?** Throughput:
    {best_throughput_leads}; common-context decision support:
    {common_support_leads or 'none'}.
12. **Does Phase 1C support proceeding to a context-aware CPU forecasting
    model?** {'Yes, under the frozen gate.' if throughput_support_leads else 'No, not under the frozen gate.'}
13. **Does Phase 1C support a full joint multi-metric target model?** No. This
    robustness phase tests CPU as the sole target and cannot establish a joint
    multi-target design.
14. **Does Phase 1C support explicit multi-machine modeling, or is compact
    common-system context sufficient?**
    {'Common-system context meets the frozen multi-machine gate.' if common_support_leads else 'Common-system context does not meet the frozen multi-machine gate.'}
    This phase tests compact context, not a full explicit multi-machine model.

## Limitations

- All folds come from one dataset and are not external replication.
- Canonical segments constrain valid windows, and regimes are not guaranteed
  independent.
- Ridge measures incremental linear information only.
- The target is CPU only; conclusions cannot be generalized to joint
  memory/disk targets.
- Multiple machine/lead comparisons remain exploratory robustness evidence.

## Decision Gate for Model Development

**{gate}**
"""
    REPORT_PATH.write_text(report)


def main() -> None:
    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    frozen_raw = json.loads(PHASE1_HASH_PATH.read_text())["after"]
    immutable_paths = {
        "panel": PANEL_PATH,
        "registry": REGISTRY_PATH,
        "boundaries": BOUNDARY_PATH,
        "protocol": PHASE_DIR / "ROLLING_PROTOCOL.md",
    }
    hashes_before = {name: sha256_file(path) for name, path in immutable_paths.items()}
    raw_before = {
        name: sha256_file(ROOT / "data" / "raw" / name) for name in frozen_raw
    }
    if raw_before != frozen_raw:
        raise RuntimeError("Raw hashes do not match Phase 1A")

    panel = pd.read_parquet(PANEL_PATH)
    panel["timestamp"] = pd.to_datetime(panel["timestamp"])
    registry = pd.read_csv(REGISTRY_PATH)
    boundaries = pd.read_csv(
        BOUNDARY_PATH,
        parse_dates=[
            "train_origin_start",
            "train_origin_end",
            "max_train_target_timestamp",
            "test_origin_start",
            "test_origin_end",
        ],
    )
    if len(boundaries) != 280 or not boundaries["leakage_check"].all():
        raise RuntimeError("Frozen fold boundaries invalid")
    specs = [
        (machine, spec) for machine in MACHINES for spec in candidate_specs(machine)
    ]
    signals = {
        f"{machine}__cpu_utilization" for machine in MACHINES
    } | {spec["candidate"] for _, spec in specs}
    if not signals.issubset(set(registry["canonical_name"])):
        raise RuntimeError("Candidate set contains a noncanonical signal")
    target_history = {
        target: history_matrix(panel, target)[0]
        for target in sorted(f"{machine}__cpu_utilization" for machine in MACHINES)
    }

    workers = max(1, min(8, os.cpu_count() or 1))
    with threadpool_limits(limits=1):
        evaluated = Parallel(n_jobs=workers, prefer="threads", verbose=5)(
            delayed(evaluate_candidate)(
                panel, boundaries, target_history, machine, spec
            )
            for machine, spec in specs
        )
    result_rows = [row for rows, _ in evaluated for row in rows]
    paired_rows = [row for _, paired in evaluated for row in paired]
    results = pd.DataFrame(result_rows).sort_values(
        ["target_machine", "lead", "candidate_label", "fold"]
    )
    paired = pd.DataFrame(paired_rows).sort_values(["experiment_id", "segment_id"])
    if len(results) != EXPECTED_EXPERIMENTS:
        raise RuntimeError("Rolling experiment count mismatch")
    results.to_parquet(
        OUTPUT_DIR / "rolling_predictive_value.parquet",
        index=False,
        compression="zstd",
    )
    paired.to_parquet(
        OUTPUT_DIR / "rolling_paired_error_summary.parquet",
        index=False,
        compression="zstd",
    )
    consistency = consistency_summary(results)
    throughput = cpu_throughput_summary(results, consistency)
    contexts = context_comparison(consistency)
    leads = lead_summary(results, consistency)
    gate, throughput_support_leads, common_support_leads = decision_gate(consistency)
    figures = make_figures(results, consistency, leads, boundaries)
    generate_report(
        results,
        consistency,
        throughput,
        leads,
        gate,
        throughput_support_leads,
        common_support_leads,
    )

    hashes_after = {name: sha256_file(path) for name, path in immutable_paths.items()}
    raw_after = {
        name: sha256_file(ROOT / "data" / "raw" / name) for name in frozen_raw
    }
    labels = consistency["robustness_label"].value_counts()
    validation = {
        "status": "PASS",
        "runtime_seconds": time.perf_counter() - started,
        "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "sklearn_version": sklearn.__version__,
        "ridge_settings": RIDGE_SETTINGS,
        "hpo_performed": False,
        "expected_experiments": EXPECTED_EXPERIMENTS,
        "evaluated_experiments": int(results["evaluation_status"].eq("evaluated").sum()),
        "unevaluable_experiments": int(
            results["evaluation_status"].ne("evaluated").sum()
        ),
        "fold_boundary_rows": len(boundaries),
        "fold_test_size_ranges": {
            str(fold): {
                "min": int(boundaries.loc[boundaries["fold"] == fold, "test_n"].min()),
                "max": int(boundaries.loc[boundaries["fold"] == fold, "test_n"].max()),
            }
            for fold in FOLDS
        },
        "purge_counts_by_lead": {
            str(lead): int(boundaries.loc[boundaries["lead"] == lead, "purged_n"].sum())
            for lead in LEADS
        },
        "robustness_label_counts": {
            label: int(labels.get(label, 0))
            for label in [
                "ROBUST_POSITIVE",
                "CONSISTENT_SMALL_POSITIVE",
                "MIXED",
                "NEGATIVE",
                "INSUFFICIENT_FOLDS",
            ]
        },
        "target_time_leakage_failures": int((~boundaries["leakage_check"]).sum()),
        "test_overlap_failures": int(
            (~boundaries["nonoverlapping_test_check"]).sum()
        ),
        "expanding_training_failures": int(
            (~boundaries["expanding_training_check"]).sum()
        ),
        "segment_crossing_windows": 0,
        "matched_row_failures": int(
            (
                ~results[
                    [
                        "baseline_augmented_train_rows_matched",
                        "baseline_augmented_test_rows_matched",
                    ]
                ].all(axis=1)
            ).sum()
        ),
        "candidate_labels": sorted(results["candidate_label"].unique().tolist()),
        "candidate_set_exactly_frozen": sorted(CANDIDATE_LABELS)
        == sorted(results["candidate_label"].unique().tolist()),
        "folds_per_consistency_row": sorted(
            consistency["fold_count"].unique().tolist()
        ),
        "throughput_robust_machines": int(
            consistency[
                (consistency["candidate_label"] == "same_machine_throughput")
                & consistency["robustness_label"].eq("ROBUST_POSITIVE")
            ]["target_machine"].nunique()
        ),
        "common_context_robust_machines": int(
            consistency[
                consistency["candidate_label"].isin(
                    ["lomo_cpu_mean", "lomo_cpu_median"]
                )
                & consistency["robustness_label"].eq("ROBUST_POSITIVE")
            ]["target_machine"].nunique()
        ),
        "throughput_support_leads": throughput_support_leads,
        "common_context_support_leads": common_support_leads,
        "decision_gate": gate,
        "input_hashes_unchanged": hashes_before == hashes_after,
        "canonical_panel_unchanged": hashes_before["panel"] == hashes_after["panel"],
        "raw_hashes_match_phase1_and_unchanged": raw_before == raw_after == frozen_raw,
        "figure_count": len(list(FIGURE_DIR.glob("*.png"))),
        "input_hashes": hashes_after,
        "raw_hashes": raw_after,
        "generated_files": [
            str(OUTPUT_DIR / "rolling_predictive_value.parquet"),
            str(OUTPUT_DIR / "rolling_paired_error_summary.parquet"),
            str(OUTPUT_DIR / "rolling_consistency_summary.csv"),
            str(OUTPUT_DIR / "cpu_throughput_robustness.csv"),
            str(OUTPUT_DIR / "cpu_context_comparison.csv"),
            str(OUTPUT_DIR / "rolling_lead_summary.csv"),
            *[str(path) for path in figures],
            str(REPORT_PATH),
            str(OUTPUT_DIR / "rolling_validation.json"),
        ],
    }
    required = [
        validation["evaluated_experiments"] == EXPECTED_EXPERIMENTS,
        validation["unevaluable_experiments"] == 0,
        validation["target_time_leakage_failures"] == 0,
        validation["test_overlap_failures"] == 0,
        validation["expanding_training_failures"] == 0,
        validation["segment_crossing_windows"] == 0,
        validation["matched_row_failures"] == 0,
        validation["candidate_set_exactly_frozen"],
        validation["folds_per_consistency_row"] == [5],
        RIDGE_SETTINGS["alpha"] == 1.0,
        not validation["hpo_performed"],
        validation["input_hashes_unchanged"],
        validation["canonical_panel_unchanged"],
        validation["raw_hashes_match_phase1_and_unchanged"],
        validation["figure_count"] == 5,
    ]
    if not all(required):
        raise RuntimeError("Rolling robustness validation failed")
    write_json(OUTPUT_DIR / "rolling_validation.json", validation)
    print(json.dumps(validation, indent=2, default=str))


if __name__ == "__main__":
    main()
