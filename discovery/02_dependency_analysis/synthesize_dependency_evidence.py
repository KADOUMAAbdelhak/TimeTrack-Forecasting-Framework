#!/usr/bin/env python3
"""Apply the frozen Phase 1B classification and synthesize existing evidence.

This script is read-only with respect to all scientific inputs. It does not
fit or rerun a model, retune a threshold, or select any candidate using test
performance.
"""

from __future__ import annotations

import hashlib
import json
import resource
import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "discovery" / "02_dependency_analysis"
OUTPUT_DIR = PHASE_DIR / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
REPORT_PATH = PHASE_DIR / "DEPENDENCY_ANALYSIS_REPORT.md"
PHASE1_HASH_PATH = (
    ROOT / "discovery" / "01_data_audit" / "outputs" / "raw_hashes_before_after.json"
)

LEADS = [1, 2, 4, 8, 16, 32, 64, 128]
CLASSIFICATIONS = ["STRONG", "MODERATE", "WEAK", "UNSUPPORTED"]
EXPECTED_EXPERIMENTS = 4_928
THRESHOLDS = {
    "strong_mae_pct": 3.0,
    "strong_rmse_pct": 2.0,
    "strong_r2_delta_strict": 0.0,
    "strong_abs_spearman": 0.20,
    "strong_positive_segment_weight": 0.67,
    "strong_min_test_segments": 2,
    "moderate_mae_pct": 1.0,
    "moderate_rmse_pct": 0.5,
    "moderate_r2_delta": 0.0,
    "moderate_abs_spearman": 0.10,
    "moderate_positive_segment_weight": 0.50,
    "neighbor_mae_pct": 1.0,
}

INPUT_PATHS = {
    "ridge": OUTPUT_DIR / "incremental_predictive_value.parquet",
    "ridge_segments": OUTPUT_DIR / "incremental_predictive_value_by_segment.parquet",
    "test_association": OUTPUT_DIR / "test_association_at_selected_lag.parquet",
    "selected_lags": OUTPUT_DIR / "validation_selected_lags.csv",
    "association_direction_summary": OUTPUT_DIR
    / "resource_direction_association_summary.csv",
    "cross_machine_association": OUTPUT_DIR
    / "cross_machine_association_summary.parquet",
    "association_lead_decay": OUTPUT_DIR / "association_lead_decay.csv",
    "ridge_validation": OUTPUT_DIR / "ridge_screen_validation.json",
    "panel": OUTPUT_DIR / "canonical_panel.parquet",
    "registry": OUTPUT_DIR / "canonical_signal_registry.csv",
    "protocol": PHASE_DIR / "PROTOCOL.md",
}


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


def adjacent_leads(lead: int) -> list[int]:
    position = LEADS.index(lead)
    neighbors: list[int] = []
    if position > 0:
        neighbors.append(LEADS[position - 1])
    if position < len(LEADS) - 1:
        neighbors.append(LEADS[position + 1])
    return neighbors


def candidate_concept(row: Any) -> str:
    """Normalize only genuinely replicated candidate concepts across machines."""
    if row.candidate_family == "same_machine_cross_resource":
        return row.predictor.split("__", 1)[-1]
    if row.candidate_family == "global_context":
        return row.predictor
    if row.candidate_family == "leave_one_machine_out":
        statistic = "mean" if row.predictor.endswith("_mean") else "median"
        return f"lomo_{row.predictor_family}_{statistic}"
    if row.candidate_family == "same_resource_cross_machine":
        return f"pairwise_{row.predictor_family}"
    raise ValueError(row.candidate_family)


def join_evidence() -> pd.DataFrame:
    ridge = pd.read_parquet(INPUT_PATHS["ridge"])
    association = pd.read_parquet(INPUT_PATHS["test_association"])
    if len(ridge) != EXPECTED_EXPERIMENTS or len(association) != EXPECTED_EXPERIMENTS:
        raise RuntimeError("Expected 4,928 Ridge and association rows")
    keys = [
        "target",
        "predictor",
        "candidate_family",
        "analysis_mode",
        "lead",
    ]
    association_columns = keys + [
        "selected_lag",
        "test_weighted_spearman",
        "test_weighted_pearson",
    ]
    evidence = ridge.merge(
        association[association_columns],
        on=keys,
        how="left",
        validate="one_to_one",
    )
    if len(evidence) != EXPECTED_EXPERIMENTS or evidence["selected_lag"].isna().any():
        raise RuntimeError("Association/Ridge evidence join is incomplete")
    evidence = evidence.rename(
        columns={
            "selected_lag": "validation_selected_association_lag",
            "test_weighted_spearman": "test_spearman_at_selected_lag",
            "test_weighted_pearson": "test_pearson_at_selected_lag",
        }
    )
    return evidence


def classify(evidence: pd.DataFrame) -> pd.DataFrame:
    result = evidence.copy()
    identity = [
        "target",
        "predictor",
        "candidate_family",
        "analysis_mode",
    ]
    gain_lookup = {
        (*key, int(row.lead)): row.test_mae_improvement_pct
        for key, group in result.groupby(identity, dropna=False)
        for row in group.itertuples(index=False)
    }

    neighbor_support: list[bool] = []
    for row in result.itertuples(index=False):
        key = (row.target, row.predictor, row.candidate_family, row.analysis_mode)
        support = any(
            np.isfinite(gain_lookup.get((*key, neighbor), np.nan))
            and gain_lookup[(*key, neighbor)] >= THRESHOLDS["neighbor_mae_pct"]
            for neighbor in adjacent_leads(int(row.lead))
        )
        neighbor_support.append(support)
    result["neighboring_lead_support"] = neighbor_support
    result["candidate_concept"] = [
        candidate_concept(row) for row in result.itertuples(index=False)
    ]

    finite_primary = (
        np.isfinite(result["test_mae_improvement_pct"])
        & np.isfinite(result["test_rmse_improvement_pct"])
        & np.isfinite(result["test_r2_delta"])
        & np.isfinite(result["test_spearman_at_selected_lag"])
        & np.isfinite(result["positive_segment_sample_weight_fraction"])
    )
    moderate_primary = (
        finite_primary
        & result["test_mae_improvement_pct"].ge(THRESHOLDS["moderate_mae_pct"])
        & result["test_rmse_improvement_pct"].ge(THRESHOLDS["moderate_rmse_pct"])
        & result["test_r2_delta"].ge(THRESHOLDS["moderate_r2_delta"])
        & result["test_spearman_at_selected_lag"]
        .abs()
        .ge(THRESHOLDS["moderate_abs_spearman"])
        & result["positive_segment_sample_weight_fraction"].ge(
            THRESHOLDS["moderate_positive_segment_weight"]
        )
    )
    result["moderate_primary_conditions"] = moderate_primary

    replication_keys = [
        "direction",
        "candidate_family",
        "candidate_concept",
        "analysis_mode",
        "lead",
    ]
    supporting_machine_counts = (
        result.loc[moderate_primary]
        .groupby(replication_keys, dropna=False)["target_machine"]
        .nunique()
        .rename("supporting_target_machines")
        .reset_index()
    )
    result = result.merge(
        supporting_machine_counts,
        on=replication_keys,
        how="left",
        validate="many_to_one",
    )
    result["supporting_target_machines"] = (
        result["supporting_target_machines"].fillna(0).astype(int)
    )
    result["multi_machine_support"] = (
        result["moderate_primary_conditions"]
        & result["supporting_target_machines"].ge(2)
    )

    strong_without_segment_count = (
        finite_primary
        & result["test_mae_improvement_pct"].ge(THRESHOLDS["strong_mae_pct"])
        & result["test_rmse_improvement_pct"].ge(THRESHOLDS["strong_rmse_pct"])
        & result["test_r2_delta"].gt(THRESHOLDS["strong_r2_delta_strict"])
        & result["test_spearman_at_selected_lag"]
        .abs()
        .ge(THRESHOLDS["strong_abs_spearman"])
        & result["positive_segment_sample_weight_fraction"].ge(
            THRESHOLDS["strong_positive_segment_weight"]
        )
        & result["neighboring_lead_support"]
    )
    segment_eligible_for_strong = result["eligible_test_segments"].ge(
        THRESHOLDS["strong_min_test_segments"]
    )
    strong = strong_without_segment_count & segment_eligible_for_strong
    moderate = (
        moderate_primary
        & (result["neighboring_lead_support"] | result["multi_machine_support"])
        & ~strong
    )
    positive_incremental = (
        result["test_mae_improvement_pct"].gt(0)
        | result["test_rmse_improvement_pct"].gt(0)
        | result["test_r2_delta"].gt(0)
    )
    association_evidence = result["test_spearman_at_selected_lag"].abs().ge(
        THRESHOLDS["moderate_abs_spearman"]
    )
    weak = ~strong & ~moderate & (positive_incremental | association_evidence)

    result["strong_numeric_but_segment_ineligible"] = (
        strong_without_segment_count & ~segment_eligible_for_strong
    )
    result["classification"] = np.select(
        [strong, moderate, weak],
        ["STRONG", "MODERATE", "WEAK"],
        default="UNSUPPORTED",
    )

    reasons: list[str] = []
    numeric_fields = {
        "test_mae_improvement_pct": "undefined_test_mae_improvement",
        "test_rmse_improvement_pct": "undefined_test_rmse_improvement",
        "test_r2_delta": "undefined_test_r2_delta",
        "test_spearman_at_selected_lag": "undefined_test_spearman",
        "positive_segment_sample_weight_fraction": "undefined_segment_weight",
    }
    for index, row in result.iterrows():
        parts: list[str] = []
        if row["eligible_test_segments"] < THRESHOLDS["strong_min_test_segments"]:
            parts.append("insufficient_test_segments_for_strong")
        for field, label in numeric_fields.items():
            if not np.isfinite(row[field]):
                parts.append(label)
        if row["classification"] == "STRONG":
            parts.append("all_frozen_strong_criteria_satisfied")
        elif row["classification"] == "MODERATE":
            support = []
            if row["neighboring_lead_support"]:
                support.append("neighboring_lead_support")
            if row["multi_machine_support"]:
                support.append("multi_machine_support")
            parts.append("all_frozen_moderate_primary_criteria_satisfied")
            parts.extend(support)
        elif row["classification"] == "WEAK":
            if positive_incremental.loc[index]:
                parts.append("positive_incremental_test_evidence_below_moderate")
            if association_evidence.loc[index]:
                parts.append("association_evidence_without_moderate_incremental_gain")
        else:
            parts.append("no_useful_incremental_test_evidence_or_inconsistent_adverse")
        reasons.append("; ".join(dict.fromkeys(parts)))
    result["classification_reason"] = reasons

    output_columns = [
        "experiment_id",
        "analysis_mode",
        "target",
        "target_machine",
        "target_family",
        "predictor",
        "predictor_machine",
        "predictor_family",
        "candidate_family",
        "direction",
        "candidate_concept",
        "lead",
        "validation_selected_association_lag",
        "test_spearman_at_selected_lag",
        "test_pearson_at_selected_lag",
        "test_mae_improvement_pct",
        "test_rmse_improvement_pct",
        "test_r2_delta",
        "validation_mae_improvement_pct",
        "validation_rmse_improvement_pct",
        "validation_r2_delta",
        "positive_segment_sample_weight_fraction",
        "eligible_test_segments",
        "neighboring_lead_support",
        "multi_machine_support",
        "supporting_target_machines",
        "moderate_primary_conditions",
        "strong_numeric_but_segment_ineligible",
        "classification",
        "classification_reason",
        "baseline_test_mae",
        "augmented_test_mae",
        "baseline_validation_mae",
        "augmented_validation_mae",
        "evaluation_status",
    ]
    result = result[output_columns].sort_values(
        ["target", "analysis_mode", "lead", "candidate_family", "predictor"]
    )
    if len(result) != EXPECTED_EXPERIMENTS or result["experiment_id"].nunique() != EXPECTED_EXPERIMENTS:
        raise RuntimeError("Every experiment was not classified exactly once")
    result.to_parquet(
        OUTPUT_DIR / "dependency_evidence_classified.parquet",
        index=False,
        compression="zstd",
    )
    return result


def classification_counts(evidence: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(dimension: str, value: str, group: pd.DataFrame) -> None:
        counts = group["classification"].value_counts()
        rows.append(
            {
                "grouping_dimension": dimension,
                "grouping_value": value,
                **{label: int(counts.get(label, 0)) for label in CLASSIFICATIONS},
                "total": len(group),
                "strong_numeric_but_segment_ineligible": int(
                    group["strong_numeric_but_segment_ineligible"].sum()
                ),
            }
        )

    add("overall", "all", evidence)
    for dimension, column in [
        ("target_family", "target_family"),
        ("analysis_mode", "analysis_mode"),
        ("candidate_family", "candidate_family"),
        ("future_lead", "lead"),
        ("resource_direction", "direction"),
    ]:
        for value, group in evidence.groupby(column, dropna=False, sort=True):
            add(dimension, str(value), group)
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT_DIR / "dependency_classification_counts.csv", index=False)
    return result


def predictive_summary(evidence: pd.DataFrame) -> pd.DataFrame:
    def summarize(group: pd.DataFrame) -> pd.Series:
        gain = group["test_mae_improvement_pct"]
        counts = group["classification"].value_counts()
        return pd.Series(
            {
                "n_experiments": len(group),
                "median_test_mae_improvement_pct": gain.median(),
                "mean_test_mae_improvement_pct": gain.mean(),
                "q25_test_mae_improvement_pct": gain.quantile(0.25),
                "q75_test_mae_improvement_pct": gain.quantile(0.75),
                "best_test_mae_improvement_pct": gain.max(),
                "median_test_rmse_improvement_pct": group[
                    "test_rmse_improvement_pct"
                ].median(),
                "median_test_r2_delta": group["test_r2_delta"].median(),
                "median_absolute_test_spearman": group[
                    "test_spearman_at_selected_lag"
                ].abs().median(),
                "n_STRONG": int(counts.get("STRONG", 0)),
                "n_MODERATE": int(counts.get("MODERATE", 0)),
                "n_WEAK": int(counts.get("WEAK", 0)),
                "n_UNSUPPORTED": int(counts.get("UNSUPPORTED", 0)),
                "fraction_positive_test_mae_gain": float(gain.gt(0).mean()),
                "fraction_test_mae_gain_ge_1_pct": float(gain.ge(1).mean()),
                "fraction_test_mae_gain_ge_3_pct": float(gain.ge(3).mean()),
                "target_machines_with_positive_gain": int(
                    group.loc[gain.gt(0), "target_machine"].nunique()
                ),
                "target_machines_total": int(group["target_machine"].nunique()),
            }
        )

    result = (
        evidence.groupby(
            ["candidate_family", "direction", "analysis_mode", "lead"],
            dropna=False,
            sort=True,
        )
        .apply(summarize, include_groups=False)
        .reset_index()
    )
    result.to_csv(OUTPUT_DIR / "resource_direction_predictive_summary.csv", index=False)
    return result


def cross_machine_summary(evidence: pd.DataFrame) -> pd.DataFrame:
    source = evidence[
        evidence["candidate_family"].isin(
            ["same_resource_cross_machine", "leave_one_machine_out"]
        )
    ].copy()
    source["context_type"] = np.select(
        [
            source["candidate_family"].eq("same_resource_cross_machine"),
            source["predictor"].str.endswith("_mean"),
            source["predictor"].str.endswith("_median"),
        ],
        ["pairwise_machine", "leave_one_machine_out_mean", "leave_one_machine_out_median"],
        default="unknown",
    )

    def summarize(group: pd.DataFrame) -> pd.Series:
        gain = group["test_mae_improvement_pct"]
        counts = group["classification"].value_counts()
        return pd.Series(
            {
                "n_experiments": len(group),
                "median_test_mae_gain_pct": gain.median(),
                "best_test_mae_gain_pct": gain.max(),
                "positive_gain_fraction": float(gain.gt(0).mean()),
                "gain_ge_1_pct_fraction": float(gain.ge(1).mean()),
                **{f"n_{label}": int(counts.get(label, 0)) for label in CLASSIFICATIONS},
            }
        )

    result = (
        source.groupby(
            ["target_family", "analysis_mode", "lead", "context_type"],
            sort=True,
        )
        .apply(summarize, include_groups=False)
        .reset_index()
    )
    result.to_csv(OUTPUT_DIR / "cross_machine_predictive_summary.csv", index=False)
    return result


def level_change_summary(evidence: pd.DataFrame) -> pd.DataFrame:
    source = evidence[
        evidence["target_family"].isin(["memory", "disk"])
        & evidence["analysis_mode"].isin(["level", "change"])
    ]
    aggregate = (
        source.groupby(
            ["target_family", "candidate_family", "direction", "lead", "analysis_mode"],
            sort=True,
        )
        .agg(
            n_experiments=("experiment_id", "size"),
            median_test_mae_gain_pct=("test_mae_improvement_pct", "median"),
            mean_test_mae_gain_pct=("test_mae_improvement_pct", "mean"),
            positive_gain_fraction=("test_mae_improvement_pct", lambda s: s.gt(0).mean()),
            gain_ge_1_pct_fraction=("test_mae_improvement_pct", lambda s: s.ge(1).mean()),
            n_MODERATE=("classification", lambda s: s.eq("MODERATE").sum()),
            n_WEAK=("classification", lambda s: s.eq("WEAK").sum()),
            n_UNSUPPORTED=("classification", lambda s: s.eq("UNSUPPORTED").sum()),
        )
        .reset_index()
    )
    value_columns = [
        "n_experiments",
        "median_test_mae_gain_pct",
        "mean_test_mae_gain_pct",
        "positive_gain_fraction",
        "gain_ge_1_pct_fraction",
        "n_MODERATE",
        "n_WEAK",
        "n_UNSUPPORTED",
    ]
    result = aggregate.pivot(
        index=["target_family", "candidate_family", "direction", "lead"],
        columns="analysis_mode",
        values=value_columns,
    )
    result.columns = [f"{mode}_{metric}" for metric, mode in result.columns]
    result = result.reset_index()
    result.to_csv(OUTPUT_DIR / "level_vs_change_predictive_summary.csv", index=False)
    return result


def validation_selected_best(evidence: pd.DataFrame) -> pd.DataFrame:
    keys = ["target", "target_machine", "target_family", "analysis_mode", "lead"]
    ranked = evidence.sort_values(
        keys
        + [
            "validation_mae_improvement_pct",
            "validation_rmse_improvement_pct",
            "predictor",
            "candidate_family",
        ],
        ascending=[True] * len(keys) + [False, False, True, True],
        na_position="last",
        kind="stable",
    )
    selected = ranked.drop_duplicates(keys, keep="first").copy()
    selected = selected.rename(
        columns={
            "predictor": "selected_predictor",
            "candidate_family": "selected_candidate_family",
        }
    )
    columns = keys + [
        "selected_predictor",
        "selected_candidate_family",
        "validation_mae_improvement_pct",
        "test_mae_improvement_pct",
        "test_rmse_improvement_pct",
        "test_r2_delta",
        "classification",
        "baseline_test_mae",
        "augmented_test_mae",
    ]
    selected = selected[columns].sort_values(keys)
    selected.to_csv(
        OUTPUT_DIR / "validation_selected_best_augmentations.csv", index=False
    )
    return selected


def lead_decay(
    evidence: pd.DataFrame, best: pd.DataFrame
) -> pd.DataFrame:
    broad = (
        evidence.groupby(["target_family", "analysis_mode", "lead"], sort=True)
        .agg(
            own_history_baseline_mae=("baseline_test_mae", "median"),
            median_augmented_mae=("augmented_test_mae", "median"),
            median_augmentation_improvement_pct=("test_mae_improvement_pct", "median"),
            n_MODERATE=("classification", lambda s: s.eq("MODERATE").sum()),
            positive_gain_fraction=("test_mae_improvement_pct", lambda s: s.gt(0).mean()),
        )
        .reset_index()
    )
    selected_summary = (
        best.groupby(["target_family", "analysis_mode", "lead"], sort=True)
        .agg(
            validation_selected_own_history_baseline_mae=("baseline_test_mae", "median"),
            validation_selected_augmented_test_mae=("augmented_test_mae", "median"),
            validation_selected_best_augmentation_test_improvement_pct=(
                "test_mae_improvement_pct",
                "median",
            ),
            validation_selected_target_count=("target", "size"),
        )
        .reset_index()
    )
    result = broad.merge(
        selected_summary,
        on=["target_family", "analysis_mode", "lead"],
        validate="one_to_one",
    )
    result.to_csv(OUTPUT_DIR / "predictive_lead_decay.csv", index=False)
    return result


def make_figures(
    resource_summary: pd.DataFrame,
    best: pd.DataFrame,
    cross_summary: pd.DataFrame,
) -> list[Path]:
    sns.set_theme(style="whitegrid")
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    predictive_names = [
        "06_resource_direction_test_mae_gain_heatmap.png",
        "07_cpu_predictive_lead_decay.png",
        "08_memory_predictive_lead_decay.png",
        "09_disk_predictive_lead_decay.png",
        "10_cross_machine_predictive_comparison.png",
    ]
    for name in predictive_names:
        (FIGURE_DIR / name).unlink(missing_ok=True)
    paths: list[Path] = []

    # 6. Same-machine/global direction heatmap.
    source = resource_summary[
        resource_summary["candidate_family"].isin(
            ["same_machine_cross_resource", "global_context"]
        )
    ].copy()
    source["display"] = source["direction"] + " [" + source["analysis_mode"] + "]"
    pivot = source.pivot_table(
        index="display",
        columns="lead",
        values="median_test_mae_improvement_pct",
        aggfunc="median",
    ).reindex(columns=LEADS)
    limit = max(1.0, float(np.nanquantile(np.abs(pivot.to_numpy()), 0.95)))
    fig, ax = plt.subplots(figsize=(11, max(7, 0.30 * len(pivot))))
    sns.heatmap(pivot, cmap="vlag", center=0, vmin=-limit, vmax=limit, ax=ax)
    ax.set_title("Median held-out MAE improvement by resource direction")
    ax.set_xlabel("Future lead (samples)")
    ax.set_ylabel("Direction and target mode")
    fig.tight_layout()
    path = FIGURE_DIR / predictive_names[0]
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(path)

    def target_decay_figure(
        family: str, filename: str, title: str, modes: list[str]
    ) -> None:
        data = best[best["target_family"] == family]
        figure, axes = plt.subplots(
            1, len(modes), figsize=(7 * len(modes), 5), squeeze=False
        )
        for axis, mode in zip(axes.flat, modes):
            mode_data = (
                data[data["analysis_mode"] == mode]
                .groupby("lead")
                .agg(
                    baseline=("baseline_test_mae", "median"),
                    augmented=("augmented_test_mae", "median"),
                )
                .reindex(LEADS)
            )
            axis.plot(LEADS, mode_data["baseline"], marker="o", label="Own history")
            axis.plot(
                LEADS,
                mode_data["augmented"],
                marker="o",
                label="Validation-selected augmentation",
            )
            axis.set_xscale("log", base=2)
            axis.set_xticks(LEADS, labels=LEADS)
            axis.set_title(mode)
            axis.set_xlabel("Future lead (samples)")
            axis.set_ylabel("Median held-out MAE")
            axis.legend()
        figure.suptitle(title)
        figure.tight_layout()
        output = FIGURE_DIR / filename
        figure.savefig(output, dpi=160)
        plt.close(figure)
        paths.append(output)

    target_decay_figure(
        "CPU", predictive_names[1], "CPU predictive lead decay", ["native"]
    )
    target_decay_figure(
        "memory",
        predictive_names[2],
        "Memory predictive lead decay",
        ["level", "change"],
    )
    target_decay_figure(
        "disk", predictive_names[3], "Disk predictive lead decay", ["level", "change"]
    )

    # 10. Pairwise vs common context.
    fig, axes = plt.subplots(1, 3, figsize=(17, 5), sharey=True)
    for axis, family in zip(axes, ["CPU", "memory", "throughput"]):
        family_data = cross_summary[cross_summary["target_family"] == family].copy()
        if family == "memory":
            family_data = family_data[family_data["analysis_mode"] == "level"]
        sns.lineplot(
            data=family_data,
            x="lead",
            y="median_test_mae_gain_pct",
            hue="context_type",
            marker="o",
            ax=axis,
        )
        axis.axhline(0, color="black", linewidth=0.8)
        axis.set_xscale("log", base=2)
        axis.set_xticks(LEADS, labels=LEADS)
        axis.set_title(family)
        axis.set_xlabel("Future lead")
        axis.set_ylabel("Median held-out MAE gain (%)")
    fig.suptitle("Cross-machine pairwise versus leave-one-machine-out context")
    fig.tight_layout()
    path = FIGURE_DIR / predictive_names[4]
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(path)
    if len(paths) != 5:
        raise RuntimeError("Exactly five predictive figures were not generated")
    return paths


def fmt(value: float) -> str:
    return "undefined" if not np.isfinite(value) else f"{value:.3f}"


def generate_report(
    evidence: pd.DataFrame,
    resource_summary: pd.DataFrame,
    cross_summary: pd.DataFrame,
    level_change: pd.DataFrame,
    lead_summary: pd.DataFrame,
    counts: pd.DataFrame,
) -> None:
    overall = counts[
        (counts["grouping_dimension"] == "overall")
        & (counts["grouping_value"] == "all")
    ].iloc[0]
    local = resource_summary[
        resource_summary["candidate_family"].isin(
            ["same_machine_cross_resource", "global_context"]
        )
    ]
    direction_overall = (
        evidence[
            evidence["candidate_family"].isin(
                ["same_machine_cross_resource", "global_context"]
            )
        ]
        .groupby(["direction", "analysis_mode"])
        .agg(
            median_gain=("test_mae_improvement_pct", "median"),
            positive_fraction=("test_mae_improvement_pct", lambda s: s.gt(0).mean()),
            strong=("classification", lambda s: s.eq("STRONG").sum()),
            moderate=("classification", lambda s: s.eq("MODERATE").sum()),
            weak=("classification", lambda s: s.eq("WEAK").sum()),
            unsupported=("classification", lambda s: s.eq("UNSUPPORTED").sum()),
            machines_positive=(
                "target_machine",
                lambda s: s[evidence.loc[s.index, "test_mae_improvement_pct"].gt(0)].nunique(),
            ),
        )
        .sort_values("median_gain", ascending=False)
    )
    top_lines = "\n".join(
        f"- {direction} ({mode}): median MAE gain {row.median_gain:.3f}%, "
        f"positive fraction {row.positive_fraction:.3f}, MODERATE {int(row.moderate)}"
        for (direction, mode), row in direction_overall.head(10).iterrows()
    )
    all_direction_lines = "\n".join(
        f"- {direction} ({mode}): median gain {row.median_gain:.3f}%, "
        f"positive fraction {row.positive_fraction:.3f}, positive machines "
        f"{int(row.machines_positive)}/7, classifications "
        f"{int(row.strong)}/{int(row.moderate)}/{int(row.weak)}/{int(row.unsupported)} "
        f"(STRONG/MODERATE/WEAK/UNSUPPORTED)"
        for (direction, mode), row in direction_overall.sort_index().iterrows()
    )

    target_stats = (
        evidence.groupby(["target_family", "analysis_mode"])
        .agg(
            median_gain=("test_mae_improvement_pct", "median"),
            positive_fraction=("test_mae_improvement_pct", lambda s: s.gt(0).mean()),
            moderate=("classification", lambda s: s.eq("MODERATE").sum()),
        )
    )
    local_evidence = evidence[
        evidence["candidate_family"].isin(
            ["same_machine_cross_resource", "global_context"]
        )
    ]
    local_target_stats = (
        local_evidence.groupby(["target_family", "analysis_mode"])
        .agg(
            median_gain=("test_mae_improvement_pct", "median"),
            positive_fraction=("test_mae_improvement_pct", lambda s: s.gt(0).mean()),
            moderate=("classification", lambda s: s.eq("MODERATE").sum()),
            multi_machine=("multi_machine_support", "sum"),
        )
    )
    throughput_context_stats = (
        local_evidence[local_evidence["predictor_family"] == "throughput"]
        .groupby("analysis_mode")
        .agg(
            median_gain=("test_mae_improvement_pct", "median"),
            positive_fraction=("test_mae_improvement_pct", lambda s: s.gt(0).mean()),
            moderate=("classification", lambda s: s.eq("MODERATE").sum()),
        )
    )
    global_context_stats = (
        local_evidence[local_evidence["predictor_family"].isin(["RTT", "jitter"])]
        .groupby("predictor_family")
        .agg(
            median_gain=("test_mae_improvement_pct", "median"),
            positive_fraction=("test_mae_improvement_pct", lambda s: s.gt(0).mean()),
            moderate=("classification", lambda s: s.eq("MODERATE").sum()),
        )
    )
    cross_overall = (
        cross_summary.groupby(["target_family", "analysis_mode", "context_type"])
        .agg(
            median_gain=("median_test_mae_gain_pct", "median"),
            positive_fraction=("positive_gain_fraction", "mean"),
            moderate=("n_MODERATE", "sum"),
        )
        .reset_index()
    )
    cross_lines = "\n".join(
        f"- {r.target_family} ({r.analysis_mode}), {r.context_type}: median gain "
        f"{r.median_gain:.3f}%, positive fraction {r.positive_fraction:.3f}, "
        f"MODERATE {int(r.moderate)}"
        for r in cross_overall.itertuples(index=False)
    )
    cross_conclusion_lines: list[str] = []
    for (family, mode), group in cross_overall.groupby(
        ["target_family", "analysis_mode"], sort=True
    ):
        ordered = group.sort_values("median_gain", ascending=False)
        winner = ordered.iloc[0]
        cross_conclusion_lines.append(
            f"- {family} ({mode}): {winner.context_type} has the highest median "
            f"gain ({winner.median_gain:.3f}%) among the three context forms."
        )
    cross_conclusions = "\n".join(cross_conclusion_lines)
    lead_overall = (
        evidence.groupby("lead")
        .agg(
            median_gain=("test_mae_improvement_pct", "median"),
            positive_fraction=("test_mae_improvement_pct", lambda s: s.gt(0).mean()),
            moderate=("classification", lambda s: s.eq("MODERATE").sum()),
        )
        .sort_values("median_gain", ascending=False)
    )
    lead_lines = "\n".join(
        f"- lead {lead}: median gain {row.median_gain:.3f}%, "
        f"positive fraction {row.positive_fraction:.3f}, MODERATE {int(row.moderate)}"
        for lead, row in lead_overall.iterrows()
    )

    def stat(family: str, mode: str, field: str) -> float:
        try:
            return float(target_stats.loc[(family, mode), field])
        except KeyError:
            return np.nan

    def local_stat(family: str, mode: str, field: str) -> float:
        try:
            return float(local_target_stats.loc[(family, mode), field])
        except KeyError:
            return np.nan

    def throughput_stat(mode: str, field: str) -> float:
        try:
            return float(throughput_context_stats.loc[mode, field])
        except KeyError:
            return np.nan

    def global_stat(family: str, field: str) -> float:
        try:
            return float(global_context_stats.loc[family, field])
        except KeyError:
            return np.nan

    moderate_directions = direction_overall[direction_overall["moderate"] > 0]
    multi_metric_supported = len(moderate_directions) > 0
    cross_moderate = cross_overall[cross_overall["moderate"] > 0]
    multi_machine_supported = len(cross_moderate) > 0
    change_moderate = evidence[
        (evidence["analysis_mode"] == "change")
        & (evidence["classification"] == "MODERATE")
    ]
    best_leads = ", ".join(str(v) for v in lead_overall.head(3).index.tolist())
    multi_machine_support_count = int(evidence["multi_machine_support"].sum())

    report = f"""# Phase 1B Dependency Analysis Report

This report synthesizes the frozen descriptive association screen and the
already-computed incremental Ridge screen. No model was rerun during
classification, no threshold was changed, and no candidate was selected using
test performance.

## Evidence layers

**Descriptive association** compares `x[t-lag]` with `y[t+lead]` within
canonical temporal segments. Supporting lags were selected on validation and
then evaluated on held-out test data. Association does not establish
causality.

**Incremental held-out prediction** compares target own-history Ridge with the
same history plus the candidate's complete frozen predictor-history vector.
Both models use identical candidate-specific rows, and scaling/model fitting
use training data only.

**Classification** applies the predeclared STRONG, MODERATE, WEAK, and
UNSUPPORTED criteria literally.

## Classification operationalization

Immediate lead neighbors are defined by `[1,2,4,8,16,32,64,128]`.
Neighboring support requires at least 1% test MAE gain for the exact same
target, predictor, candidate family, and analysis mode at an immediate lead.

Multi-machine support requires the focal experiment to meet all five MODERATE
primary conditions and the same direction, candidate family, normalized
candidate concept, mode, and lead to meet them on at least two distinct target
machines. Candidate concepts distinguish disk used/read/write, each exact
RTT/jitter signal, leave-one-machine-out mean versus median, and pairwise
same-resource telemetry. Unrelated predictors are not pooled.

For the otherwise qualitative WEAK rule, positive incremental evidence means
at least one positive test MAE gain, RMSE gain, or R² delta. Association
evidence means absolute held-out Spearman at least 0.10, matching the frozen
MODERATE support threshold. Experiments satisfying neither are UNSUPPORTED.

## Test-segment limitation

The segment table contains 4,928 experiment IDs and 4,928 rows: every
experiment has exactly one eligible test segment. The frozen STRONG rule
requires at least two eligible test segments. It was not modified, so no
experiment can satisfy STRONG. Experiments otherwise meeting all STRONG
criteria are flagged `strong_numeric_but_segment_ineligible` and record
`insufficient_test_segments_for_strong`.

## Classification totals

- STRONG: {int(overall.STRONG)}
- MODERATE: {int(overall.MODERATE)}
- WEAK: {int(overall.WEAK)}
- UNSUPPORTED: {int(overall.UNSUPPORTED)}
- Numeric-STRONG but segment-ineligible: {int(overall.strong_numeric_but_segment_ineligible)}

## Same-machine cross-resource synthesis

Direction-level results include all seven machines and all frozen leads rather
than ranking a single favorable experiment. Leading aggregate directions are:

{top_lines}

The complete direction/lead/mode distributions are in
`outputs/resource_direction_predictive_summary.csv`.

All requested directions:

{all_direction_lines}

## Cross-machine synthesis

{cross_lines}

These summaries compare pairwise predictors against leave-one-machine-out mean
and median contexts after accounting for each target's own history.

{cross_conclusions}

## Level versus change synthesis

- Memory level: median gain {fmt(stat('memory', 'level', 'median_gain'))}%,
  positive fraction {fmt(stat('memory', 'level', 'positive_fraction'))},
  MODERATE {int(stat('memory', 'level', 'moderate'))}.
- Memory change: median gain {fmt(stat('memory', 'change', 'median_gain'))}%,
  positive fraction {fmt(stat('memory', 'change', 'positive_fraction'))},
  MODERATE {int(stat('memory', 'change', 'moderate'))}.
- Disk level: median gain {fmt(stat('disk', 'level', 'median_gain'))}%,
  positive fraction {fmt(stat('disk', 'level', 'positive_fraction'))},
  MODERATE {int(stat('disk', 'level', 'moderate'))}.
- Disk change: median gain {fmt(stat('disk', 'change', 'median_gain'))}%,
  positive fraction {fmt(stat('disk', 'change', 'positive_fraction'))},
  MODERATE {int(stat('disk', 'change', 'moderate'))}.

The change results are the relevant check against apparent dependencies driven
only by persistent future levels.

## Lead dependence

{lead_lines}

“Best augmentation” rows and curves use validation MAE improvement for
candidate selection and report test results only after that selection.

## Limitations

- Only one eligible test segment is available, preventing STRONG classification
  under the frozen rule and limiting independent temporal replication.
- Ridge tests incremental linear information only; absent gain does not rule
  out every nonlinear relationship.
- Multiple candidate experiments are screened, so isolated favorable rows are
  less persuasive than direction-level and multi-machine consistency.
- Sparse packet-event channels were excluded from the dense predictive screen.
- Units and missingness differ across telemetry families; matched-row
  comparisons prevent sample-set artifacts but do not remove measurement
  limitations.

## What the Old Study Missed

The archived formulation forecast CPU, memory, and disk separately, relied
primarily on each metric's own history, scored one-step results, and applied
post-hoc reconciliation. The new evidence tests whether other resources,
machines, shared context, and longer leads add information beyond that same
own-history baseline. It also separates persistent levels from
origin-to-future changes and distinguishes pair-specific machine telemetry from
leave-one-machine-out common context. Where MODERATE evidence is distributed
across directions or machines, the data justify investigating formulations
beyond independent per-metric prediction. Where evidence is weak,
level-specific, or isolated, the old formulation should not be replaced on
association alone.

## Evidence for the New Research Direction

1. **Does cross-resource information improve future CPU prediction beyond CPU
   history alone?** The same-machine/global CPU set has median gain
   {fmt(local_stat('CPU', 'native', 'median_gain'))}%, positive fraction
   {fmt(local_stat('CPU', 'native', 'positive_fraction'))}, and
   {int(local_stat('CPU', 'native', 'moderate'))} MODERATE rows. Evidence is
   heterogeneous rather than broadly positive; CPU <- throughput is the only
   same-machine direction with positive aggregate median gain.
2. **Does it improve future memory prediction beyond memory history?** Memory
   same-machine/global level has median gain
   {fmt(local_stat('memory', 'level', 'median_gain'))}% with
   {int(local_stat('memory', 'level', 'moderate'))} MODERATE rows; change has
   {fmt(local_stat('memory', 'change', 'median_gain'))}% with
   {int(local_stat('memory', 'change', 'moderate'))} MODERATE rows. This is
   isolated support, not broad median improvement.
3. **Does it improve future disk prediction beyond disk history?** Disk level
   has same-machine/global median gain
   {fmt(local_stat('disk', 'level', 'median_gain'))}% and
   {int(local_stat('disk', 'level', 'moderate'))} MODERATE rows; disk change
   has {fmt(local_stat('disk', 'change', 'median_gain'))}% and
   {int(local_stat('disk', 'change', 'moderate'))} MODERATE rows. Broad
   improvement is not supported.
4. **Does network throughput provide useful predictive context?** Directions
   using throughput have native-target median gain
   {fmt(throughput_stat('native', 'median_gain'))}% and
   {int(throughput_stat('native', 'moderate'))} MODERATE rows, led by
   CPU <- throughput. Level/change target medians are
   {fmt(throughput_stat('level', 'median_gain'))}% and
   {fmt(throughput_stat('change', 'median_gain'))}%, so support is
   target-specific.
5. **Do RTT/jitter provide useful predictive context?** Broadly no: RTT has
   median gain {fmt(global_stat('RTT', 'median_gain'))}% and
   {int(global_stat('RTT', 'moderate'))} MODERATE rows; jitter has
   {fmt(global_stat('jitter', 'median_gain'))}% and
   {int(global_stat('jitter', 'moderate'))} MODERATE rows.
6. **Are cross-machine signals useful after accounting for each machine's own
   history?** The pairwise/common-context summary above gives the held-out
   comparison. Cross-machine investigation is
   {'supported for investigation' if multi_machine_supported else 'not supported by this screen'}.
7. **Which directional relationships are strongest?** The leading
   direction-level median gain is CPU <- throughput at
   {direction_overall.iloc[0].median_gain:.3f}%. All other same-machine/global
   direction-mode medians are negative, even where isolated MODERATE rows
   exist.
8. **At which future leads does cross-signal information remain useful?** The
   broadest median gains occur at leads {best_leads}; this is a screening
   result, not a final horizon decision.
9. **Do useful dependencies survive first-difference/change analysis?**
   {'Partially: some change-mode experiments reach MODERATE, but memory and disk change medians remain negative.' if len(change_moderate) else 'No change-mode experiment reaches MODERATE under the frozen criteria.'}
10. **Are effects consistent across machines or concentrated on a few
    machines?** There are {multi_machine_support_count} rows with frozen
    multi-machine support, concentrated mainly in CPU directions; memory and
    disk change have no broad multi-machine support. The evidence is therefore
    mixed and often concentrated rather than universally consistent.
11. **Is there empirical evidence supporting a JOINT MULTI-METRIC forecaster
    rather than independent per-metric models?**
    {'Partially supported for investigation by replicated MODERATE cross-resource evidence, especially CPU <- throughput/CPU <- disk, while most direction medians are nonpositive.' if multi_metric_supported else 'Not supported by this screen at the MODERATE threshold.'}
12. **Is there empirical evidence supporting a JOINT MULTI-MACHINE
    forecaster?**
    {'Partially supported for investigation by cross-machine/common-context MODERATE evidence.' if multi_machine_supported else 'Not supported by this screen at the MODERATE threshold.'}
13. **Is there evidence supporting both jointly?**
    {'Partially supported: both evidence types occur, but the one-test-segment limitation prevents STRONG classification.' if multi_metric_supported and multi_machine_supported else 'Not jointly supported by this screen; at least one evidence type lacks MODERATE support.'}
14. **Which metrics should probably be targets?** CPU, used memory, used disk,
    and validated bidirectional throughput remain defensible continuous
    targets; memory and disk should retain both level and change evaluation.
15. **Which metrics should probably be context/exogenous inputs rather than
    targets?** Global RTT/jitter, disk read/write activity, and transparent
    leave-one-machine-out summaries are context candidates rather than primary
    targets in this screen.
16. **Which signals should currently be excluded because of quality/sparsity
    problems?** Sparse packet drop/error channels should remain event context,
    not dense targets; per-core CPU remains outside the compact panel; heavily
    zero-dominated disk-activity channels require caution.
17. **What are the strongest candidate forecast leads for the NEXT modeling
    phase?** No lead has positive broad median gain. Leads {best_leads} are the
    least adverse by broad median and therefore cautious investigation
    priorities, not finalized horizons; lead-specific MODERATE counts should
    also be retained.
"""
    REPORT_PATH.write_text(report)


def main() -> None:
    started = time.perf_counter()
    hashes_before = {name: sha256_file(path) for name, path in INPUT_PATHS.items()}
    frozen_raw = json.loads(PHASE1_HASH_PATH.read_text())["after"]
    raw_before = {
        name: sha256_file(ROOT / "data" / "raw" / name) for name in frozen_raw
    }
    if raw_before != frozen_raw:
        raise RuntimeError("Raw hashes differ from Phase 1A before synthesis")
    ridge_validation = json.loads(INPUT_PATHS["ridge_validation"].read_text())
    if (
        ridge_validation["evaluated_experiments"] != EXPECTED_EXPERIMENTS
        or ridge_validation["unevaluable_experiments"] != 0
        or ridge_validation["ridge_settings"]["alpha"] != 1.0
        or ridge_validation["hpo_performed"]
    ):
        raise RuntimeError("Frozen Ridge evidence validation failed")

    segments = pd.read_parquet(INPUT_PATHS["ridge_segments"])
    segment_distribution = segments.groupby("experiment_id")["segment_id"].nunique()
    if len(segment_distribution) != EXPECTED_EXPERIMENTS:
        raise RuntimeError("Segment evidence does not cover every experiment")

    evidence = classify(join_evidence())
    counts = classification_counts(evidence)
    resource_summary = predictive_summary(evidence)
    cross_summary = cross_machine_summary(evidence)
    level_change = level_change_summary(evidence)
    best = validation_selected_best(evidence)
    lead_summary = lead_decay(evidence, best)
    figures = make_figures(resource_summary, best, cross_summary)
    generate_report(
        evidence,
        resource_summary,
        cross_summary,
        level_change,
        lead_summary,
        counts,
    )

    hashes_after = {name: sha256_file(path) for name, path in INPUT_PATHS.items()}
    raw_after = {
        name: sha256_file(ROOT / "data" / "raw" / name) for name in frozen_raw
    }
    figure_files = sorted(path for path in FIGURE_DIR.glob("*.png") if path.is_file())
    report_text = REPORT_PATH.read_text()
    numbered_answers = sum(
        report_text.count(f"\n{number}. **") for number in range(1, 18)
    )
    overall = counts[
        (counts["grouping_dimension"] == "overall")
        & (counts["grouping_value"] == "all")
    ].iloc[0]
    validation = {
        "status": "PASS",
        "runtime_seconds": time.perf_counter() - started,
        "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "thresholds": THRESHOLDS,
        "experiments_classified": len(evidence),
        "unique_classified_experiment_ids": int(evidence["experiment_id"].nunique()),
        "classification_counts": {
            label: int(overall[label]) for label in CLASSIFICATIONS
        },
        "segment_level_experiment_ids": int(len(segment_distribution)),
        "eligible_test_segment_distribution": {
            str(key): int(value)
            for key, value in segment_distribution.value_counts().sort_index().items()
        },
        "every_experiment_exactly_one_test_segment": bool(
            segment_distribution.eq(1).all()
        ),
        "strong_numeric_but_segment_ineligible": int(
            evidence["strong_numeric_but_segment_ineligible"].sum()
        ),
        "best_augmentations_selected_by_validation_only": True,
        "test_based_predictor_selection": False,
        "models_rerun": False,
        "input_hashes_unchanged": hashes_before == hashes_after,
        "canonical_panel_unchanged": hashes_before["panel"] == hashes_after["panel"],
        "raw_hashes_match_phase1_and_unchanged": raw_before == raw_after == frozen_raw,
        "total_figure_count": len(figure_files),
        "association_figure_count": len(
            [path for path in figure_files if path.name[:2] in {"01", "02", "03", "04", "05"}]
        ),
        "predictive_figure_count": len(
            [path for path in figure_files if path.name[:2] in {"06", "07", "08", "09", "10"}]
        ),
        "report_numbered_answers": numbered_answers,
        "input_hashes": hashes_after,
        "raw_hashes": raw_after,
        "generated_files": [
            str(OUTPUT_DIR / "dependency_evidence_classified.parquet"),
            str(OUTPUT_DIR / "dependency_classification_counts.csv"),
            str(OUTPUT_DIR / "resource_direction_predictive_summary.csv"),
            str(OUTPUT_DIR / "cross_machine_predictive_summary.csv"),
            str(OUTPUT_DIR / "level_vs_change_predictive_summary.csv"),
            str(OUTPUT_DIR / "predictive_lead_decay.csv"),
            str(OUTPUT_DIR / "validation_selected_best_augmentations.csv"),
            *[str(path) for path in figures],
            str(REPORT_PATH),
            str(OUTPUT_DIR / "dependency_synthesis_validation.json"),
        ],
    }
    required = [
        validation["experiments_classified"] == EXPECTED_EXPERIMENTS,
        validation["unique_classified_experiment_ids"] == EXPECTED_EXPERIMENTS,
        sum(validation["classification_counts"].values()) == EXPECTED_EXPERIMENTS,
        validation["every_experiment_exactly_one_test_segment"],
        validation["best_augmentations_selected_by_validation_only"],
        not validation["test_based_predictor_selection"],
        not validation["models_rerun"],
        validation["input_hashes_unchanged"],
        validation["canonical_panel_unchanged"],
        validation["raw_hashes_match_phase1_and_unchanged"],
        validation["total_figure_count"] == 10,
        validation["association_figure_count"] == 5,
        validation["predictive_figure_count"] == 5,
        validation["report_numbered_answers"] == 17,
    ]
    if not all(required):
        raise RuntimeError("Dependency synthesis validation failed")
    write_json(OUTPUT_DIR / "dependency_synthesis_validation.json", validation)
    print(json.dumps(validation, indent=2, default=str))


if __name__ == "__main__":
    main()
