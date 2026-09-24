#!/usr/bin/env python3
"""Analyze Phase 2B-2A1 DLinear without fitting any model."""

from __future__ import annotations

import json
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from benchmark.neural_v2.src.data import FUTURE_LEADS, sample_set_hash
from benchmark.neural_v2.src.metrics import per_lead_metrics
from benchmark.neural_v2.src.validation import atomic_json_write


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "benchmark/neural_v2/outputs/dlinear"
FIGURES = OUT / "figures"
CRITERIA_PATH = ROOT / "benchmark/neural_v2/DLINEAR_DECISION_CRITERIA.md"
FEATURE_LABELS = {"F0_LOCAL": "DLinear F0", "F1_THROUGHPUT": "DLinear F1"}


def atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def atomic_parquet(path: Path, frame: pd.DataFrame) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(temporary, index=False, engine="pyarrow")
    temporary.replace(path)


def macro_metrics(truth: np.ndarray, prediction: np.ndarray) -> tuple[float, float, float]:
    residual = truth.astype(float) - prediction.astype(float)
    mae = float(np.mean(np.abs(residual)))
    rmse = float(np.sqrt(np.mean(residual**2)))
    total = float(np.sum((truth - truth.mean()) ** 2))
    r2 = float(1.0 - np.sum(residual**2) / total) if total > 0 else float("nan")
    return mae, rmse, r2


def matched_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    keys = ["machine", "fold", "seed", "lead"]
    f0 = metrics[metrics.feature_set.eq("F0_LOCAL")].copy()
    f1 = metrics[metrics.feature_set.eq("F1_THROUGHPUT")].copy()
    joined = f0.merge(f1, on=keys, suffixes=("_f0", "_f1"), validate="one_to_one")
    if not joined["test_hash_f0"].eq(joined["test_hash_f1"]).all():
        raise RuntimeError("DLinear F0/F1 test hashes differ")
    joined["mae_gain_pct"] = 100.0 * (joined.mae_f0 - joined.mae_f1) / joined.mae_f0
    joined["rmse_gain_pct"] = 100.0 * (joined.rmse_f0 - joined.rmse_f1) / joined.rmse_f0
    joined["r2_delta"] = joined.r2_f1 - joined.r2_f0
    return joined[
        keys
        + [
            "run_id_f0",
            "run_id_f1",
            "test_hash_f0",
            "mae_f0",
            "mae_f1",
            "mae_gain_pct",
            "rmse_f0",
            "rmse_f1",
            "rmse_gain_pct",
            "r2_f0",
            "r2_f1",
            "r2_delta",
        ]
    ].rename(columns={"test_hash_f0": "test_hash"})


def build_seed_summary(metrics: pd.DataFrame, matched: pd.DataFrame) -> pd.DataFrame:
    keys = ["feature_set", "machine", "fold", "lead"]
    summary = metrics.groupby(keys).agg(
        mae_mean=("mae", "mean"),
        mae_std=("mae", "std"),
        mae_min=("mae", "min"),
        mae_max=("mae", "max"),
        rmse_mean=("rmse", "mean"),
        rmse_std=("rmse", "std"),
        rmse_min=("rmse", "min"),
        rmse_max=("rmse", "max"),
        r2_mean=("r2", "mean"),
        r2_std=("r2", "std"),
        r2_min=("r2", "min"),
        r2_max=("r2", "max"),
        seed_count=("seed", "nunique"),
    ).reset_index()
    gains = matched.groupby(["machine", "fold", "lead"]).agg(
        gain_mean=("mae_gain_pct", "mean"),
        gain_std=("mae_gain_pct", "std"),
        gain_min=("mae_gain_pct", "min"),
        gain_max=("mae_gain_pct", "max"),
        positive_seed_count=("mae_gain_pct", lambda values: int((values > 0).sum())),
        negative_seed_count=("mae_gain_pct", lambda values: int((values < 0).sum())),
    ).reset_index()
    gains["all_three_seeds_agree_on_sign"] = (
        gains.positive_seed_count.eq(3) | gains.negative_seed_count.eq(3)
    )
    f1_mask = summary.feature_set.eq("F1_THROUGHPUT")
    summary.loc[f1_mask, gains.columns] = gains.to_numpy()
    return summary


def aggregate_tables(metrics: pd.DataFrame, matched: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    by_lead = metrics.groupby(["feature_set", "lead"]).agg(
        mae=("mae", "mean"),
        rmse=("rmse", "mean"),
        r2=("r2", "mean"),
        cells=("run_id", "count"),
    ).reset_index()
    gain_lead = matched.groupby("lead").agg(
        mae_gain_pct=("mae_gain_pct", "mean"),
        mae_gain_std=("mae_gain_pct", "std"),
        rmse_gain_pct=("rmse_gain_pct", "mean"),
        r2_delta=("r2_delta", "mean"),
        positive_fraction=("mae_gain_pct", lambda values: float((values > 0).mean())),
    ).reset_index()
    by_lead = by_lead.merge(
        gain_lead.assign(feature_set="F1_THROUGHPUT"),
        on=["feature_set", "lead"],
        how="left",
    )
    by_machine = metrics.groupby(["feature_set", "machine", "lead"]).agg(
        mae=("mae", "mean"), rmse=("rmse", "mean"), r2=("r2", "mean")
    ).reset_index()
    gain_machine = matched.groupby(["machine", "lead"]).agg(
        mae_gain_pct=("mae_gain_pct", "mean"),
        positive_seed_fold_fraction=("mae_gain_pct", lambda values: float((values > 0).mean())),
    ).reset_index()
    by_machine = by_machine.merge(
        gain_machine.assign(feature_set="F1_THROUGHPUT"),
        on=["feature_set", "machine", "lead"],
        how="left",
    )
    by_fold = metrics.groupby(["feature_set", "fold", "lead"]).agg(
        mae=("mae", "mean"), rmse=("rmse", "mean"), r2=("r2", "mean")
    ).reset_index()
    gain_fold = matched.groupby(["fold", "lead"]).agg(
        mae_gain_pct=("mae_gain_pct", "mean"),
        positive_seed_machine_fraction=("mae_gain_pct", lambda values: float((values > 0).mean())),
    ).reset_index()
    by_fold = by_fold.merge(
        gain_fold.assign(feature_set="F1_THROUGHPUT"),
        on=["feature_set", "fold", "lead"],
        how="left",
    )
    return by_lead, by_machine, by_fold


def compatible_lightgbm_comparison(registry: pd.DataFrame) -> pd.DataFrame:
    deterministic = pd.read_csv(ROOT / "benchmark/outputs/run_registry.csv")
    matched_registry = pd.read_csv(
        ROOT / "benchmark/phase2b1_corrected/outputs/matched_f0_run_registry.csv"
    )
    rows = []
    for machine in sorted(registry.machine.unique()):
        for fold in sorted(registry.fold.unique()):
            neural_rows = registry[
                registry.machine.eq(machine) & registry.fold.eq(fold)
            ]
            neural_predictions = {}
            for feature in ("F0_LOCAL", "F1_THROUGHPUT"):
                for record in neural_rows[neural_rows.feature_set.eq(feature)].itertuples(index=False):
                    neural_predictions[(feature, int(record.seed))] = pd.read_parquet(
                        ROOT / record.prediction_path
                    )
            candidate_record = deterministic[
                deterministic.model.eq("LightGBM")
                & deterministic.feature_set.eq("F1_THROUGHPUT")
                & deterministic.machine.eq(machine)
                & deterministic.outer_fold.eq(fold)
            ].iloc[0]
            matched_record = matched_registry[
                matched_registry.model.eq("LightGBM")
                & matched_registry.candidate_feature_set.eq("F1_THROUGHPUT")
                & matched_registry.machine.eq(machine)
                & matched_registry.outer_fold.eq(fold)
            ].iloc[0]
            lightgbm_f1 = pd.read_parquet(ROOT / candidate_record.prediction_path)
            lightgbm_f0 = pd.read_parquet(ROOT / matched_record.prediction_path)
            dlinear_origins = set(
                neural_predictions[("F0_LOCAL", 0)].origin_index.unique()
            )
            lightgbm_origins = set(lightgbm_f1.origin_index.unique())
            matched_origins = set(lightgbm_f0.origin_index.unique())
            if lightgbm_origins != matched_origins:
                raise RuntimeError(f"LightGBM matched support differs {machine}/{fold}")
            common = np.asarray(sorted(dlinear_origins & lightgbm_origins), dtype=np.int64)
            relation = (
                "EXACT_IDENTICAL"
                if dlinear_origins == lightgbm_origins
                else "EXACT_INTERSECTION_NO_RETRAIN"
            )
            common_hash = sample_set_hash(common)
            for lead in FUTURE_LEADS:
                deterministic_values = {}
                for label, frame in (("f0", lightgbm_f0), ("f1", lightgbm_f1)):
                    subset = frame[
                        frame.lead.eq(lead) & frame.origin_index.isin(common)
                    ].sort_values("origin_index")
                    deterministic_values[label] = subset
                if not np.array_equal(
                    deterministic_values["f0"].y_true.to_numpy(),
                    deterministic_values["f1"].y_true.to_numpy(),
                ):
                    raise RuntimeError("LightGBM target mismatch on common support")
                lb_f0 = macro_metrics(
                    deterministic_values["f0"].y_true.to_numpy(),
                    deterministic_values["f0"].y_pred.to_numpy(),
                )
                lb_f1 = macro_metrics(
                    deterministic_values["f1"].y_true.to_numpy(),
                    deterministic_values["f1"].y_pred.to_numpy(),
                )
                dlinear_values = {feature: [] for feature in ("F0_LOCAL", "F1_THROUGHPUT")}
                for feature in dlinear_values:
                    for seed in (0, 1, 2):
                        subset = neural_predictions[(feature, seed)]
                        subset = subset[
                            subset.lead.eq(lead) & subset.origin_index.isin(common)
                        ].sort_values("origin_index")
                        if not np.array_equal(
                            subset.y_true.to_numpy(),
                            deterministic_values["f0"].y_true.to_numpy(),
                        ):
                            raise RuntimeError("DLinear/LightGBM target mismatch")
                        dlinear_values[feature].append(
                            macro_metrics(subset.y_true.to_numpy(), subset.y_pred.to_numpy())
                        )
                dl_f0 = np.mean(dlinear_values["F0_LOCAL"], axis=0)
                dl_f1 = np.mean(dlinear_values["F1_THROUGHPUT"], axis=0)
                rows.append(
                    {
                        "aggregation_level": "machine_fold",
                        "machine": machine,
                        "fold": fold,
                        "lead": lead,
                        "support_relation": relation,
                        "dlinear_test_n": len(dlinear_origins),
                        "lightgbm_test_n": len(lightgbm_origins),
                        "common_test_n": len(common),
                        "common_test_hash": common_hash,
                        "lightgbm_f0_mae": lb_f0[0],
                        "lightgbm_f1_mae": lb_f1[0],
                        "lightgbm_f1_context_gain_pct": 100.0 * (lb_f0[0] - lb_f1[0]) / lb_f0[0],
                        "dlinear_f0_mean_seed_mae": dl_f0[0],
                        "dlinear_f1_mean_seed_mae": dl_f1[0],
                        "dlinear_f1_context_gain_pct": 100.0 * (dl_f0[0] - dl_f1[0]) / dl_f0[0],
                    }
                )
    cells = pd.DataFrame(rows)
    aggregate = cells.groupby("lead").agg(
        common_test_n=("common_test_n", "sum"),
        lightgbm_f0_mae=("lightgbm_f0_mae", "mean"),
        lightgbm_f1_mae=("lightgbm_f1_mae", "mean"),
        lightgbm_f1_context_gain_pct=("lightgbm_f1_context_gain_pct", "mean"),
        dlinear_f0_mean_seed_mae=("dlinear_f0_mean_seed_mae", "mean"),
        dlinear_f1_mean_seed_mae=("dlinear_f1_mean_seed_mae", "mean"),
        dlinear_f1_context_gain_pct=("dlinear_f1_context_gain_pct", "mean"),
    ).reset_index()
    aggregate.insert(0, "fold", "ALL")
    aggregate.insert(0, "machine", "ALL")
    aggregate.insert(0, "aggregation_level", "lead_macro")
    aggregate["support_relation"] = "EXACT_COMMON_SUBSETS"
    aggregate["dlinear_test_n"] = np.nan
    aggregate["lightgbm_test_n"] = np.nan
    aggregate["common_test_hash"] = "per-cell hashes recorded above"
    return pd.concat([cells, aggregate], ignore_index=True, sort=False)


def decision(matched: pd.DataFrame) -> tuple[str, dict[str, object]]:
    lead_means = matched.groupby("lead").mae_gain_pct.mean()
    machine_means = matched.groupby("machine").mae_gain_pct.mean()
    fold_means = matched.groupby("fold").mae_gain_pct.mean()
    seed_means = matched.groupby("seed").mae_gain_pct.mean()
    overall = float(matched.mae_gain_pct.mean())
    counts = {
        "overall_mean_gain_pct": overall,
        "positive_leads": int((lead_means > 0).sum()),
        "positive_machines": int((machine_means > 0).sum()),
        "positive_folds": int((fold_means > 0).sum()),
        "positive_seeds": int((seed_means > 0).sum()),
        "negative_leads": int((lead_means < 0).sum()),
        "negative_machines": int((machine_means < 0).sum()),
        "negative_folds": int((fold_means < 0).sum()),
        "negative_seeds": int((seed_means < 0).sum()),
    }
    if overall > 0 and counts["positive_leads"] == 8 and counts["positive_machines"] >= 5 and counts["positive_folds"] >= 4 and counts["positive_seeds"] == 3:
        label = "BROAD_POSITIVE"
    elif overall > 0 and counts["positive_leads"] >= 4 and counts["positive_machines"] >= 4 and counts["positive_folds"] >= 3 and counts["positive_seeds"] >= 2:
        label = "CONDITIONALLY_POSITIVE"
    elif overall < 0 and counts["negative_leads"] >= 6 and counts["negative_machines"] >= 5 and counts["negative_folds"] >= 4 and counts["negative_seeds"] == 3:
        label = "BROAD_NEGATIVE"
    else:
        label = "NEUTRAL"
    return label, counts


def make_figures(by_lead: pd.DataFrame, by_machine: pd.DataFrame, comparison: pd.DataFrame) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 5))
    for feature, rows in by_lead.groupby("feature_set"):
        plt.plot(rows.lead, rows.mae, marker="o", label=FEATURE_LABELS[feature])
    plt.xscale("log", base=2)
    plt.xlabel("Real future lead")
    plt.ylabel("MAE")
    plt.title("DLinear CPU MAE by real future lead")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "01_dlinear_f0_f1_mae_by_lead.png", dpi=160)
    plt.close()

    gains = by_lead[by_lead.feature_set.eq("F1_THROUGHPUT")]
    plt.figure(figsize=(8, 5))
    plt.axhline(0, color="black", linewidth=1)
    plt.plot(gains.lead, gains.mae_gain_pct, marker="o")
    plt.xscale("log", base=2)
    plt.xlabel("Real future lead")
    plt.ylabel("Matched F1 MAE gain (%)")
    plt.title("DLinear matched throughput gain")
    plt.tight_layout()
    plt.savefig(FIGURES / "02_dlinear_f1_gain_by_lead.png", dpi=160)
    plt.close()

    heat = by_machine[by_machine.feature_set.eq("F1_THROUGHPUT")].pivot(
        index="machine", columns="lead", values="mae_gain_pct"
    )
    plt.figure(figsize=(10, 5))
    image = plt.imshow(heat.to_numpy(), aspect="auto", cmap="RdBu_r")
    plt.colorbar(image, label="Matched F1 MAE gain (%)")
    plt.xticks(range(len(heat.columns)), heat.columns)
    plt.yticks(range(len(heat.index)), heat.index)
    plt.xlabel("Real future lead")
    plt.ylabel("Machine")
    plt.title("DLinear throughput gain by machine and lead")
    plt.tight_layout()
    plt.savefig(FIGURES / "03_dlinear_machine_lead_gain_heatmap.png", dpi=160)
    plt.close()

    compatible = comparison[comparison.aggregation_level.eq("lead_macro")]
    plt.figure(figsize=(9, 5))
    for column, label in (
        ("lightgbm_f0_mae", "LightGBM matched F0"),
        ("lightgbm_f1_mae", "LightGBM F1"),
        ("dlinear_f0_mean_seed_mae", "DLinear F0"),
        ("dlinear_f1_mean_seed_mae", "DLinear F1"),
    ):
        plt.plot(compatible.lead, compatible[column], marker="o", label=label)
    plt.xscale("log", base=2)
    plt.xlabel("Real future lead")
    plt.ylabel("MAE on exact common evaluation support")
    plt.title("LightGBM versus DLinear on compatible support")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "04_lightgbm_vs_dlinear_compatible_mae.png", dpi=160)
    plt.close()


def write_report(
    by_lead: pd.DataFrame,
    matched: pd.DataFrame,
    selected: pd.DataFrame,
    comparison: pd.DataFrame,
    label: str,
    counts: dict[str, object],
) -> None:
    f0 = by_lead[by_lead.feature_set.eq("F0_LOCAL")].sort_values("lead")
    f1 = by_lead[by_lead.feature_set.eq("F1_THROUGHPUT")].sort_values("lead")
    lead_gains = f1[["lead", "mae_gain_pct"]]
    machine_means = matched.groupby("machine").mae_gain_pct.mean()
    fold_means = matched.groupby("fold").mae_gain_pct.mean()
    seed_means = matched.groupby("seed").mae_gain_pct.mean()
    selected_counts = selected.groupby(["feature_set", "selected_L"]).size()
    compatible = comparison[comparison.aggregation_level.eq("lead_macro")].sort_values("lead")
    dlinear_f0_wins = int((compatible.dlinear_f0_mean_seed_mae < compatible.lightgbm_f0_mae).sum())
    dlinear_f1_wins = int((compatible.dlinear_f1_mean_seed_mae < compatible.lightgbm_f1_mae).sum())
    incremental_wins = int((compatible.dlinear_f1_context_gain_pct > compatible.lightgbm_f1_context_gain_pct).sum())
    lines = [
        "# Phase 2B-2A1 DLinear Scientific Report",
        "",
        "This is a descriptive report; no statistical-significance test is performed.",
        "",
        "## Aggregate lead results",
        "",
        "| Lead | DLinear F0 MAE | DLinear F1 MAE | Matched F1 gain (%) |",
        "|---:|---:|---:|---:|",
    ]
    for f0_row, f1_row in zip(f0.itertuples(), f1.itertuples()):
        lines.append(f"| {int(f0_row.lead)} | {f0_row.mae:.4f} | {f1_row.mae:.4f} | {f1_row.mae_gain_pct:.3f} |")
    lines += [
        "",
        "## Descriptive answers",
        "",
        f"1. DLinear F0 MAE rises across the lead profile from {f0.mae.iloc[0]:.4f} at lead 1 to {f0.mae.iloc[-1]:.4f} at lead 128; the complete eight-lead profile is tabulated above.",
        f"2. F1 throughput has an overall matched cell-mean MAE gain of {counts['overall_mean_gain_pct']:.3f}% versus DLinear F0.",
        f"3. Positive aggregate leads: {lead_gains.loc[lead_gains.mae_gain_pct > 0, 'lead'].astype(int).tolist()} ({counts['positive_leads']}/8).",
        f"4. Positive machine means: {machine_means[machine_means > 0].index.tolist()} ({counts['positive_machines']}/7).",
        f"5. Positive fold means: {fold_means[fold_means > 0].index.astype(int).tolist()} ({counts['positive_folds']}/5).",
        f"6. Seed mean gains are {seed_means.round(3).to_dict()}; {counts['positive_seeds']}/3 seeds are positive overall.",
        f"7. F0 selected-L counts: {selected_counts.get('F0_LOCAL', pd.Series(dtype=int)).to_dict() if isinstance(selected_counts.index, pd.MultiIndex) else {}}.",
        f"8. F1 selected-L counts: {selected_counts.get('F1_THROUGHPUT', pd.Series(dtype=int)).to_dict() if isinstance(selected_counts.index, pd.MultiIndex) else {}}.",
        f"9. Throughput changes the preferred L in {int((selected.pivot(index=['machine','fold'], columns='feature_set', values='selected_L').F0_LOCAL != selected.pivot(index=['machine','fold'], columns='feature_set', values='selected_L').F1_THROUGHPUT).sum())}/35 machine-fold cells.",
        f"10. DLinear F0 beats accepted matched LightGBM F0 at {dlinear_f0_wins}/8 aggregate leads on exact common evaluation subsets.",
        f"11. DLinear F1 beats accepted LightGBM F1 at {dlinear_f1_wins}/8 aggregate leads on exact common evaluation subsets.",
        f"12. DLinear has a larger incremental throughput gain than LightGBM at {incremental_wins}/8 aggregate leads on those subsets.",
        "",
        "All LightGBM comparisons were recomputed on exact per-cell intersections without retraining. Machine/fold support relations and hashes are recorded in `dlinear_vs_lightgbm.csv`; no differently supported aggregate was compared silently.",
        "",
        "## DLinear throughput decision",
        "",
        "Prospective rule: `BROAD_POSITIVE` requires positive overall gain, 8/8 positive leads, at least 5/7 positive machines, at least 4/5 positive folds, and 3/3 positive seeds; `CONDITIONALLY_POSITIVE` requires positive overall gain, at least 4/8 leads, 4/7 machines, 3/5 folds, and 2/3 seeds; `BROAD_NEGATIVE` requires negative overall gain, at least 6/8 negative leads, 5/7 machines, 4/5 folds, and 3/3 seeds; all other patterns are `NEUTRAL`.",
        "",
        f"**{label}**",
        "",
        f"The prospective criteria are frozen in `{CRITERIA_PATH.relative_to(ROOT)}`. Observed consistency counts were {counts}.",
        "",
        "No LSTM, TCN-v2, PatchTST, B4-v1, or multi-target model was executed.",
    ]
    (ROOT / "benchmark/neural_v2/DLINEAR_SCIENTIFIC_REPORT.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    started = time.perf_counter()
    metrics = pd.read_parquet(OUT / "metrics.parquet")
    registry = pd.read_csv(OUT / "run_registry.csv")
    selected = pd.read_csv(OUT / "selected_contexts.csv")
    matched = matched_metrics(metrics)
    atomic_parquet(OUT / "f0_f1_matched_metrics.parquet", matched)
    seed = build_seed_summary(metrics, matched)
    atomic_csv(OUT / "seed_summary.csv", seed)
    by_lead, by_machine, by_fold = aggregate_tables(metrics, matched)
    atomic_csv(OUT / "aggregate_by_lead.csv", by_lead)
    atomic_csv(OUT / "aggregate_by_machine.csv", by_machine)
    atomic_csv(OUT / "aggregate_by_fold.csv", by_fold)
    comparison = compatible_lightgbm_comparison(registry)
    atomic_csv(OUT / "dlinear_vs_lightgbm.csv", comparison)
    label, counts = decision(matched)
    make_figures(by_lead, by_machine, comparison)
    write_report(by_lead, matched, selected, comparison, label, counts)
    runtime_path = OUT / "runtime_accounting.json"
    runtime = json.loads(runtime_path.read_text())
    runtime["analysis_wall_seconds"] = time.perf_counter() - started
    runtime["total_recorded_wall_seconds"] = runtime["execution_wall_seconds"] + runtime["analysis_wall_seconds"]
    runtime["status"] = "ANALYSIS_COMPLETE_VALIDATION_PENDING"
    runtime["dlinear_throughput_decision"] = label
    runtime["decision_counts"] = counts
    atomic_json_write(runtime_path, runtime)
    print(json.dumps({"decision": label, **counts}, indent=2))


if __name__ == "__main__":
    main()
