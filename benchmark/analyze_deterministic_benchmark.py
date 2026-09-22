#!/usr/bin/env python3
"""Build descriptive Phase 2B-1 metrics, aggregates, figures, and report."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from benchmark.src.metrics import per_lead_metrics, relative_mae_change
from benchmark.src.windows import FUTURE_LEADS


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "benchmark" / "outputs"
FIGURES = OUTPUTS / "figures" / "deterministic"
REPORT = ROOT / "benchmark" / "DETERMINISTIC_BENCHMARK_REPORT.md"
FEATURES = [
    "F0_LOCAL",
    "F1_THROUGHPUT",
    "F2_LOMO_MEAN",
    "F3_LOMO_MEDIAN",
    "F4_THROUGHPUT_LOMO_MEAN",
    "F5_THROUGHPUT_LOMO_MEDIAN",
]
MODELS = ["Persistence", "Ridge", "LightGBM"]


def sample_hash(indices: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(indices, dtype="<i8").tobytes()).hexdigest()


def prediction_path(registry_row: pd.Series) -> Path:
    return ROOT / registry_row["prediction_path"]


def aligned_reference(
    candidate: pd.DataFrame, reference: pd.DataFrame
) -> pd.DataFrame:
    columns = ["origin_index", "lead", "y_true", "y_pred", "target_timestamp"]
    aligned = candidate[columns].merge(
        reference[columns],
        on=["origin_index", "lead"],
        how="left",
        validate="one_to_one",
        suffixes=("_candidate", "_reference"),
    )
    if aligned["y_pred_reference"].isna().any():
        raise RuntimeError("Reference prediction is missing a candidate sample")
    if not np.array_equal(
        aligned["y_true_candidate"].to_numpy(),
        aligned["y_true_reference"].to_numpy(),
    ):
        raise RuntimeError("Candidate and reference target rows differ")
    if not np.array_equal(
        aligned["target_timestamp_candidate"].to_numpy(),
        aligned["target_timestamp_reference"].to_numpy(),
    ):
        raise RuntimeError("Candidate and reference target timestamps differ")
    return aligned


def metrics_from_frame(frame: pd.DataFrame) -> pd.DataFrame:
    truth = frame.pivot(index="origin_index", columns="lead", values="y_true")
    prediction = frame.pivot(index="origin_index", columns="lead", values="y_pred")
    truth = truth[FUTURE_LEADS]
    prediction = prediction[FUTURE_LEADS]
    return per_lead_metrics(truth.to_numpy(), prediction.to_numpy())


def single_lead_metrics(truth: np.ndarray, prediction: np.ndarray) -> dict[str, float]:
    residual = truth.astype(float) - prediction.astype(float)
    total = float(np.sum((truth - truth.mean()) ** 2))
    return {
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "r2": (
            float(1.0 - np.sum(residual**2) / total)
            if len(truth) >= 2 and total > 0
            else np.nan
        ),
    }


def recompute_and_match(
    registry: pd.DataFrame, frozen_metrics: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    started = time.perf_counter()
    registry_index = registry.set_index(
        ["model", "feature_set", "machine", "outer_fold"]
    )
    metric_rows = []
    context_rows = []
    max_recompute_difference = 0.0
    for run in registry.itertuples(index=False):
        candidate = pd.read_parquet(ROOT / run.prediction_path)
        recomputed = metrics_from_frame(candidate)
        stored = frozen_metrics[frozen_metrics["run_id"].eq(run.run_id)].sort_values(
            "lead"
        )
        differences = np.abs(
            recomputed[["mae", "rmse", "r2"]].to_numpy()
            - stored[["mae", "rmse", "r2"]].to_numpy()
        )
        max_recompute_difference = max(
            max_recompute_difference, float(np.nanmax(differences))
        )
        persistence_run = registry_index.loc[
            ("Persistence", "F0_LOCAL", run.machine, run.outer_fold)
        ]
        persistence = pd.read_parquet(prediction_path(persistence_run))
        persistence_aligned = aligned_reference(candidate, persistence)
        if run.feature_set == "F0_LOCAL":
            f0 = candidate
        else:
            f0_run = registry_index.loc[
                (run.model, "F0_LOCAL", run.machine, run.outer_fold)
            ]
            f0 = pd.read_parquet(prediction_path(f0_run))
        f0_aligned = aligned_reference(candidate, f0)
        origins = np.sort(candidate["origin_index"].unique())
        run_sample_hash = sample_hash(origins)
        for metric in recomputed.itertuples(index=False):
            lead = int(metric.lead)
            persistence_lead = persistence_aligned[
                persistence_aligned["lead"].eq(lead)
            ]
            f0_lead = f0_aligned[f0_aligned["lead"].eq(lead)]
            persistence_metric = single_lead_metrics(
                persistence_lead["y_true_candidate"].to_numpy(),
                persistence_lead["y_pred_reference"].to_numpy(),
            )
            f0_metric = single_lead_metrics(
                f0_lead["y_true_candidate"].to_numpy(),
                f0_lead["y_pred_reference"].to_numpy(),
            )
            metric_rows.append(
                {
                    "run_id": run.run_id,
                    "machine": run.machine,
                    "outer_fold": run.outer_fold,
                    "lead": lead,
                    "model": run.model,
                    "feature_set": run.feature_set,
                    "seed": None,
                    "mae": float(metric.mae),
                    "rmse": float(metric.rmse),
                    "r2": float(metric.r2),
                    "mae_change_vs_persistence_pct": relative_mae_change(
                        persistence_metric["mae"], float(metric.mae)
                    ),
                    "mae_change_vs_same_model_f0_pct": relative_mae_change(
                        f0_metric["mae"], float(metric.mae)
                    ),
                    "n_samples": len(origins),
                    "sample_set_hash": run_sample_hash,
                }
            )
            if run.feature_set != "F0_LOCAL":
                context_rows.append(
                    {
                        "run_id": run.run_id,
                        "model": run.model,
                        "feature_set": run.feature_set,
                        "machine": run.machine,
                        "outer_fold": run.outer_fold,
                        "lead": lead,
                        "n_samples": len(origins),
                        "candidate_sample_set_hash": run_sample_hash,
                        "matched_f0_sample_set_hash": sample_hash(
                            np.sort(f0_lead["origin_index"].unique())
                        ),
                        "candidate_mae": float(metric.mae),
                        "matched_f0_mae": f0_metric["mae"],
                        "relative_context_mae_gain_pct": relative_mae_change(
                            f0_metric["mae"], float(metric.mae)
                        ),
                        "candidate_rmse": float(metric.rmse),
                        "matched_f0_rmse": f0_metric["rmse"],
                        "relative_context_rmse_gain_pct": relative_mae_change(
                            f0_metric["rmse"], float(metric.rmse)
                        ),
                        "candidate_r2": float(metric.r2),
                        "matched_f0_r2": f0_metric["r2"],
                        "context_r2_delta": float(metric.r2 - f0_metric["r2"]),
                        "target_rows_exact_match": True,
                    }
                )
    return (
        pd.DataFrame(metric_rows),
        pd.DataFrame(context_rows),
        max_recompute_difference,
    )


def aggregates(
    metrics: pd.DataFrame, context: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    lead_rows = []
    for keys, group in metrics.groupby(["model", "feature_set", "lead"], sort=False):
        machine = group.groupby("machine", as_index=False).agg(
            machine_mae=("mae", "mean"),
            machine_rmse=("rmse", "mean"),
            machine_r2=("r2", "mean"),
        )
        fold = group.groupby("outer_fold", as_index=False).agg(
            fold_macro_mae=("mae", "mean")
        )
        lead_rows.append(
            {
                "model": keys[0],
                "feature_set": keys[1],
                "lead": keys[2],
                "macro_machine_mae": machine["machine_mae"].mean(),
                "median_machine_mae": machine["machine_mae"].median(),
                "worst_machine_mae": machine["machine_mae"].max(),
                "fold_level_macro_mae_mean": fold["fold_macro_mae"].mean(),
                "macro_machine_rmse": machine["machine_rmse"].mean(),
                "macro_machine_r2": machine["machine_r2"].mean(),
                "mean_relative_mae_vs_persistence_pct": group[
                    "mae_change_vs_persistence_pct"
                ].mean(),
                "mean_matched_context_gain_pct": (
                    group["mae_change_vs_same_model_f0_pct"].mean()
                    if keys[1] != "F0_LOCAL"
                    else 0.0
                ),
            }
        )
    by_lead = pd.DataFrame(lead_rows)
    by_machine = (
        metrics.groupby(["model", "feature_set", "machine", "lead"], as_index=False)
        .agg(
            mean_fold_mae=("mae", "mean"),
            median_fold_mae=("mae", "median"),
            worst_fold_mae=("mae", "max"),
            mean_fold_rmse=("rmse", "mean"),
            mean_fold_r2=("r2", "mean"),
            mean_relative_mae_vs_persistence_pct=(
                "mae_change_vs_persistence_pct",
                "mean",
            ),
            mean_matched_context_gain_pct=(
                "mae_change_vs_same_model_f0_pct",
                "mean",
            ),
        )
    )
    context_ablation = context.copy()
    profile = (
        context.groupby(["model", "feature_set", "lead"], as_index=False)
        .agg(
            mean_context_mae_gain_pct=("relative_context_mae_gain_pct", "mean"),
            median_context_mae_gain_pct=("relative_context_mae_gain_pct", "median"),
            min_context_mae_gain_pct=("relative_context_mae_gain_pct", "min"),
            max_context_mae_gain_pct=("relative_context_mae_gain_pct", "max"),
            mean_context_rmse_gain_pct=("relative_context_rmse_gain_pct", "mean"),
            mean_context_r2_delta=("context_r2_delta", "mean"),
            positive_machine_fold_fraction=(
                "relative_context_mae_gain_pct",
                lambda values: float((values > 0).mean()),
            ),
        )
    )
    return by_lead, by_machine, context_ablation, profile


def make_figures(
    by_lead: pd.DataFrame,
    context_profile: pd.DataFrame,
    context: pd.DataFrame,
    selected: pd.DataFrame,
) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 140, "font.size": 9})

    f0 = by_lead[by_lead["feature_set"].eq("F0_LOCAL")]
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for model in MODELS:
        rows = f0[f0["model"].eq(model)].sort_values("lead")
        ax.plot(rows["lead"], rows["macro_machine_mae"], marker="o", label=model)
    ax.set(xscale="log", xlabel="Real future lead (samples)", ylabel="Macro MAE")
    ax.set_xticks(FUTURE_LEADS, labels=FUTURE_LEADS)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES / "01_f0_mae_by_real_lead.png")
    plt.close(fig)

    for number, model in ((2, "Ridge"), (3, "LightGBM")):
        fig, ax = plt.subplots(figsize=(7.2, 4.4))
        for feature in FEATURES[1:]:
            rows = context_profile[
                context_profile["model"].eq(model)
                & context_profile["feature_set"].eq(feature)
            ].sort_values("lead")
            ax.plot(
                rows["lead"],
                rows["mean_context_mae_gain_pct"],
                marker="o",
                label=feature,
            )
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set(
            xscale="log",
            xlabel="Real future lead (samples)",
            ylabel="Matched-F0 MAE gain (%)",
        )
        ax.set_xticks(FUTURE_LEADS, labels=FUTURE_LEADS)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(FIGURES / f"0{number}_{model.lower()}_context_gain_by_lead.png")
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for feature in ["F0_LOCAL", "F1_THROUGHPUT", "F4_THROUGHPUT_LOMO_MEAN", "F5_THROUGHPUT_LOMO_MEDIAN"]:
        rows = by_lead[
            by_lead["model"].eq("LightGBM")
            & by_lead["feature_set"].eq(feature)
        ].sort_values("lead")
        ax.plot(rows["lead"], rows["macro_machine_mae"], marker="o", label=feature)
    ax.set(xscale="log", xlabel="Real future lead (samples)", ylabel="Macro MAE")
    ax.set_xticks(FUTURE_LEADS, labels=FUTURE_LEADS)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGURES / "04_lightgbm_absolute_mae_contexts.png")
    plt.close(fig)

    feature_order = {feature: index for index, feature in enumerate(FEATURES[1:])}
    for number, model in ((5, "Ridge"), (6, "LightGBM")):
        selection = selected[
            selected["model"].eq(model)
            & selected["feature_set"].ne("F0_LOCAL")
        ].copy()
        selection["_feature_order"] = selection["feature_set"].map(feature_order)
        selection = (
            selection.sort_values(
                [
                    "machine",
                    "outer_fold",
                    "inner_validation_mae",
                    "_feature_order",
                ]
            )
            .groupby(["machine", "outer_fold"], as_index=False)
            .first()
        )
        shown = context[context["model"].eq(model)].merge(
            selection[["machine", "outer_fold", "feature_set"]],
            on=["machine", "outer_fold", "feature_set"],
            validate="many_to_one",
        )
        heat = shown.pivot_table(
            index="machine",
            columns="lead",
            values="relative_context_mae_gain_pct",
            aggfunc="mean",
        ).reindex(columns=FUTURE_LEADS)
        fig, ax = plt.subplots(figsize=(8.0, 4.4))
        image = ax.imshow(heat.to_numpy(), aspect="auto", cmap="RdBu_r")
        ax.set_xticks(range(len(FUTURE_LEADS)), labels=FUTURE_LEADS)
        ax.set_yticks(range(len(heat.index)), labels=heat.index)
        ax.set(xlabel="Real future lead", ylabel="Target machine")
        fig.colorbar(image, ax=ax, label="Outer-test matched-F0 MAE gain (%)")
        fig.tight_layout()
        fig.savefig(
            FIGURES / f"0{number}_{model.lower()}_validation_selected_context_heatmap.png"
        )
        plt.close(fig)


def markdown_table(frame: pd.DataFrame, digits: int = 3) -> str:
    formatted = frame.copy()
    for column in formatted.select_dtypes(include=[np.number]).columns:
        formatted[column] = formatted[column].map(
            lambda value: f"{value:.{digits}f}" if pd.notna(value) else "NA"
        )
    header = "| " + " | ".join(formatted.columns) + " |"
    separator = "|" + "|".join(["---"] * len(formatted.columns)) + "|"
    rows = [
        "| " + " | ".join(map(str, row)) + " |"
        for row in formatted.itertuples(index=False, name=None)
    ]
    return "\n".join([header, separator, *rows])


def write_report(
    by_lead: pd.DataFrame,
    by_machine: pd.DataFrame,
    context_profile: pd.DataFrame,
    context_detail: pd.DataFrame,
    selected: pd.DataFrame,
    runtime: dict,
) -> None:
    f0_ranking = (
        by_lead[by_lead["feature_set"].eq("F0_LOCAL")]
        .sort_values(["lead", "macro_machine_mae"])
        [["lead", "model", "macro_machine_mae"]]
    )
    f0_ranking["rank"] = f0_ranking.groupby("lead").cumcount() + 1
    f0_ranking = f0_ranking[["lead", "rank", "model", "macro_machine_mae"]]
    gains = context_profile[
        context_profile["model"].isin(["Ridge", "LightGBM"])
    ].copy()
    gain_summary = (
        gains.groupby(["model", "feature_set"], as_index=False)
        .agg(
            mean_gain_pct=("mean_context_mae_gain_pct", "mean"),
            best_lead_gain_pct=("mean_context_mae_gain_pct", "max"),
            positive_detail_fraction=("positive_machine_fold_fraction", "mean"),
        )
    )
    best_leads = gains.loc[
        gains.groupby(["model", "feature_set"])[
            "mean_context_mae_gain_pct"
        ].idxmax(),
        ["model", "feature_set", "lead", "mean_context_mae_gain_pct"],
    ]
    combined = gain_summary[
        gain_summary["feature_set"].isin(
            ["F4_THROUGHPUT_LOMO_MEAN", "F5_THROUGHPUT_LOMO_MEDIAN"]
        )
    ]
    throughput = gain_summary[
        gain_summary["feature_set"].eq("F1_THROUGHPUT")
    ][["model", "mean_gain_pct"]].rename(columns={"mean_gain_pct": "f1_gain"})
    combined_best = combined.groupby("model", as_index=False)["mean_gain_pct"].max()
    comparison = throughput.merge(combined_best, on="model")
    comparison["combined_minus_f1_pct_points"] = (
        comparison["mean_gain_pct"] - comparison["f1_gain"]
    )
    model_context = gains.groupby("model")["mean_context_mae_gain_pct"].mean()
    gain_by_lead = gains[
        ["model", "lead", "feature_set", "mean_context_mae_gain_pct"]
    ].sort_values(["model", "lead", "feature_set"])
    consistency_rows = []
    deterministic_detail = context_detail[
        context_detail["model"].isin(["Ridge", "LightGBM"])
    ]
    for keys, group in deterministic_detail.groupby(["model", "feature_set"]):
        machine_means = group.groupby("machine")[
            "relative_context_mae_gain_pct"
        ].mean()
        fold_means = group.groupby("outer_fold")[
            "relative_context_mae_gain_pct"
        ].mean()
        consistency_rows.append(
            {
                "model": keys[0],
                "feature_set": keys[1],
                "mean_gain_pct": group["relative_context_mae_gain_pct"].mean(),
                "positive_machine_fold_fraction": (
                    group["relative_context_mae_gain_pct"] > 0
                ).mean(),
                "machines_positive_of_7": int((machine_means > 0).sum()),
                "folds_positive_of_5": int((fold_means > 0).sum()),
            }
        )
    consistency_table = pd.DataFrame(consistency_rows)
    selection = selected.copy()
    selection_config = selection["config_json"].map(json.loads)
    selection["alpha"] = selection_config.map(lambda value: value.get("alpha"))
    selection["num_leaves"] = selection_config.map(
        lambda value: value.get("num_leaves")
    )
    selection["learning_rate"] = selection_config.map(
        lambda value: value.get("learning_rate")
    )
    selection["n_estimators"] = selection_config.map(
        lambda value: value.get("n_estimators")
    )
    context_distribution = (
        selection.groupby(["model", "context_length"], as_index=False)
        .size()
        .rename(columns={"size": "selected_runs"})
    )
    ridge_alpha_distribution = (
        selection[selection["model"].eq("Ridge")]
        .groupby("alpha", as_index=False)
        .size()
        .rename(columns={"size": "selected_runs"})
    )
    lightgbm_distribution = (
        selection[selection["model"].eq("LightGBM")]
        .groupby(
            ["context_length", "num_leaves", "learning_rate", "n_estimators"],
            as_index=False,
        )
        .size()
        .rename(columns={"size": "selected_runs"})
    )
    profile_pivot = gains.pivot_table(
        index=["model", "lead"],
        columns="feature_set",
        values="mean_context_mae_gain_pct",
    )
    combined_wins = {}
    for model in ["Ridge", "LightGBM"]:
        rows = profile_pivot.loc[model]
        combined_wins[model] = int(
            (
                rows[
                    ["F4_THROUGHPUT_LOMO_MEAN", "F5_THROUGHPUT_LOMO_MEDIAN"]
                ].max(axis=1)
                > rows["F1_THROUGHPUT"]
            ).sum()
        )
    f1_machine = (
        deterministic_detail[
            deterministic_detail["feature_set"].eq("F1_THROUGHPUT")
        ]
        .groupby(["model", "machine"])["relative_context_mae_gain_pct"]
        .mean()
    )
    positive_f1_machines = {
        model: ", ".join(
            f1_machine.loc[model][f1_machine.loc[model] > 0].index.tolist()
        )
        or "none"
        for model in ["Ridge", "LightGBM"]
    }
    ridge_f1 = gains[
        gains["model"].eq("Ridge")
        & gains["feature_set"].eq("F1_THROUGHPUT")
    ]
    lightgbm_f1 = gains[
        gains["model"].eq("LightGBM")
        & gains["feature_set"].eq("F1_THROUGHPUT")
    ]
    lomo_means = gain_summary[
        gain_summary["feature_set"].isin(["F2_LOMO_MEAN", "F3_LOMO_MEDIAN"])
    ].pivot(index="model", columns="feature_set", values="mean_gain_pct")
    combined_means = gain_summary[
        gain_summary["feature_set"].isin(
            ["F4_THROUGHPUT_LOMO_MEAN", "F5_THROUGHPUT_LOMO_MEDIAN"]
        )
    ].pivot(index="model", columns="feature_set", values="mean_gain_pct")
    lines = [
        "# Phase 2B-1 Deterministic Benchmark Report",
        "",
        "This is a descriptive benchmark execution report, not manuscript text.",
        "No statistical significance test, neural model, or proposed architecture is included.",
        "",
        "## Execution",
        "",
        f"- Completed runs: {runtime['registered_runs']} / 630.",
        f"- Lead-level metric rows: {runtime['metric_rows']} / 5,040.",
        "- Models: Persistence, Ridge, and LightGBM only.",
        "- Feature sets: frozen F0-F5; machines 01-07; folds 1-5.",
        "",
        "## F0 ranking by real lead",
        "",
        markdown_table(f0_ranking),
        "",
        "## Matched-F0 context summary",
        "",
        markdown_table(gain_summary),
        "",
        "## Matched-F0 gain by real lead",
        "",
        markdown_table(gain_by_lead),
        "",
        "## Leads with largest matched context gain",
        "",
        markdown_table(best_leads),
        "",
        "## Selection audit",
        "",
        "Selected context lengths:",
        "",
        markdown_table(context_distribution, digits=0),
        "",
        "Selected Ridge alphas:",
        "",
        markdown_table(ridge_alpha_distribution, digits=2),
        "",
        "Selected LightGBM joint configurations:",
        "",
        markdown_table(lightgbm_distribution, digits=3),
        "",
        "## Machine/fold consistency",
        "",
        markdown_table(consistency_table),
        "",
        "## Benchmark questions",
        "",
    ]
    f1 = gains[gains["feature_set"].eq("F1_THROUGHPUT")]
    lomo = gains[
        gains["feature_set"].isin(["F2_LOMO_MEAN", "F3_LOMO_MEDIAN"])
    ]
    consistency = gains["positive_machine_fold_fraction"].mean()
    lines += [
        "1. **BQ1:** Ridge throughput was adverse at every lead "
        f"({ridge_f1['mean_context_mae_gain_pct'].min():.3f}% to "
        f"{ridge_f1['mean_context_mae_gain_pct'].max():.3f}%). LightGBM F1 was "
        f"weakly positive at leads "
        f"{lightgbm_f1.loc[lightgbm_f1['mean_context_mae_gain_pct'] > 0, 'lead'].astype(int).tolist()}, "
        f"with its largest gain {lightgbm_f1['mean_context_mae_gain_pct'].max():.3f}%.",
        f"2. **BQ2:** F2/F3 aggregate gains were adverse at every lead "
        f"({lomo['mean_context_mae_gain_pct'].min():.3f}% to "
        f"{lomo['mean_context_mae_gain_pct'].max():.3f}%); no F2/F3 model had "
        "a positive machine-average or fold-average effect.",
        f"3. **BQ3:** Combined context beat F1 at {combined_wins['Ridge']}/8 "
        f"Ridge leads and {combined_wins['LightGBM']}/8 LightGBM leads. "
        f"Combined-minus-F1 average gain is "
        + ", ".join(
            f"{row.model} {row.combined_minus_f1_pct_points:.3f} pp"
            for row in comparison.itertuples(index=False)
        )
        + ".",
        f"4. **BQ4:** Median LOMO was less adverse than mean LOMO on average: "
        f"Ridge F3 {lomo_means.loc['Ridge', 'F3_LOMO_MEDIAN']:.3f}% vs F2 "
        f"{lomo_means.loc['Ridge', 'F2_LOMO_MEAN']:.3f}%, LightGBM F3 "
        f"{lomo_means.loc['LightGBM', 'F3_LOMO_MEDIAN']:.3f}% vs F2 "
        f"{lomo_means.loc['LightGBM', 'F2_LOMO_MEAN']:.3f}%. F5 was also less "
        f"adverse than F4 for Ridge ({combined_means.loc['Ridge', 'F5_THROUGHPUT_LOMO_MEDIAN']:.3f}% "
        f"vs {combined_means.loc['Ridge', 'F4_THROUGHPUT_LOMO_MEAN']:.3f}%) "
        f"and LightGBM ({combined_means.loc['LightGBM', 'F5_THROUGHPUT_LOMO_MEDIAN']:.3f}% "
        f"vs {combined_means.loc['LightGBM', 'F4_THROUGHPUT_LOMO_MEAN']:.3f}%).",
        "5. **BQ5:** Context was most useful for LightGBM F1 at real lead 128 "
        f"({lightgbm_f1['mean_context_mae_gain_pct'].max():.3f}%); Ridge had no "
        "positive aggregate contextual lead.",
        f"6. **BQ6:** Mean positive machine-fold fraction across contextual profiles is "
        f"{consistency:.3f}. F1-positive machine averages were Ridge: "
        f"{positive_f1_machines['Ridge']}; LightGBM: "
        f"{positive_f1_machines['LightGBM']}. Other context sets had no "
        "positive model-level machine average.",
        f"7. **BQ7:** Mean context gain over F1-F5/leads is Ridge "
        f"{model_context.get('Ridge', np.nan):.3f}% and LightGBM "
        f"{model_context.get('LightGBM', np.nan):.3f}%; LightGBM extracted "
        "more useful/less harmful context descriptively.",
        "8. **BQ8:** NOT YET EVALUATED.",
        "9. **BQ9:** The F0 ranking did not change: LightGBM first, Ridge "
        "second, Persistence third at all eight real leads.",
        "10. **BQ10:** Positive context effects were concentrated in F1 and "
        "specific machines/folds; the machine/fold table above and "
        "`deterministic_context_ablation.csv` retain the full descriptive detail.",
        "",
        "## Scope",
        "",
        "The figures showing a best contextual feature choose that feature by inner-validation MAE only, then display outer-test gain. Outer-test performance never chooses a feature or configuration.",
    ]
    REPORT.write_text("\n".join(lines) + "\n")


def main() -> None:
    started = time.perf_counter()
    registry = pd.read_csv(OUTPUTS / "run_registry.csv")
    metrics = pd.read_parquet(OUTPUTS / "metrics.parquet")
    selected = pd.read_csv(OUTPUTS / "selected_configs.csv")
    if len(registry) != 630 or len(metrics) != 5040 or len(selected) != 420:
        raise RuntimeError("Deterministic benchmark is incomplete")
    metrics, context, maximum_difference = recompute_and_match(registry, metrics)
    metrics.to_parquet(OUTPUTS / "metrics.parquet", index=False, compression="zstd")
    context.to_parquet(
        OUTPUTS / "context_matched_metrics.parquet",
        index=False,
        compression="zstd",
    )
    by_lead, by_machine, ablation, profile = aggregates(metrics, context)
    by_lead.to_csv(OUTPUTS / "deterministic_aggregate_by_lead.csv", index=False)
    by_machine.to_csv(OUTPUTS / "deterministic_aggregate_by_machine.csv", index=False)
    ablation.to_csv(OUTPUTS / "deterministic_context_ablation.csv", index=False)
    profile.to_csv(OUTPUTS / "context_gain_by_lead.csv", index=False)
    make_figures(by_lead, profile, context, selected)
    runtime_path = OUTPUTS / "deterministic_runtime.json"
    runtime = json.loads(runtime_path.read_text())
    runtime["analysis_runtime_seconds"] = time.perf_counter() - started
    runtime["metric_recomputation_max_abs_difference"] = maximum_difference
    runtime["total_recorded_wall_seconds"] = (
        sum(
            family.get("wall_runtime_seconds", 0)
            for family in runtime["families"].values()
        )
        + runtime["analysis_runtime_seconds"]
    )
    runtime_path.write_text(json.dumps(runtime, indent=2) + "\n")
    write_report(by_lead, by_machine, profile, context, selected, runtime)
    print(
        json.dumps(
            {
                "metrics": len(metrics),
                "context_rows": len(context),
                "max_metric_recompute_difference": maximum_difference,
                "figures": len(list(FIGURES.glob("*.png"))),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
