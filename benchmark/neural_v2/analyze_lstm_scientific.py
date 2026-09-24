#!/usr/bin/env python3
"""Analyze Phase 2B-2A2 LSTM without fitting any model."""

from __future__ import annotations

import json
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from benchmark.neural_v2.analyze_dlinear_scientific import (
    aggregate_tables,
    atomic_csv,
    atomic_parquet,
    build_seed_summary,
    compatible_lightgbm_comparison,
    decision,
    macro_metrics,
    matched_metrics,
)
from benchmark.neural_v2.src.data import FUTURE_LEADS, sample_set_hash
from benchmark.neural_v2.src.validation import atomic_json_write


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "benchmark/neural_v2/outputs/lstm"
DLINEAR_OUT = ROOT / "benchmark/neural_v2/outputs/dlinear"
FIGURES = OUT / "figures"
CRITERIA_PATH = ROOT / "benchmark/neural_v2/LSTM_DECISION_CRITERIA.md"
FEATURE_LABELS = {"F0_LOCAL": "LSTM F0", "F1_THROUGHPUT": "LSTM F1"}


def load_predictions(registry: pd.DataFrame, machine: str, fold: int) -> dict[tuple[str, int], pd.DataFrame]:
    rows = registry[registry.machine.eq(machine) & registry.fold.eq(fold)]
    result = {}
    for feature in ("F0_LOCAL", "F1_THROUGHPUT"):
        for record in rows[rows.feature_set.eq(feature)].itertuples(index=False):
            result[(feature, int(record.seed))] = pd.read_parquet(ROOT / record.prediction_path)
    return result


def lstm_dlinear_comparison(lstm_registry: pd.DataFrame) -> pd.DataFrame:
    dlinear_registry = pd.read_csv(DLINEAR_OUT / "run_registry.csv")
    rows = []
    for machine in sorted(lstm_registry.machine.unique()):
        for fold in sorted(lstm_registry.fold.unique()):
            lstm = load_predictions(lstm_registry, machine, int(fold))
            dlinear = load_predictions(dlinear_registry, machine, int(fold))
            origin_sets = []
            for frames in (lstm, dlinear):
                for frame in frames.values():
                    origin_sets.append(set(frame.origin_index.unique()))
            common_set = set.intersection(*origin_sets)
            common = np.asarray(sorted(common_set), dtype=np.int64)
            relation = "EXACT_IDENTICAL" if all(values == origin_sets[0] for values in origin_sets) else "EXACT_INTERSECTION_NO_RETRAIN"
            for lead in FUTURE_LEADS:
                model_values = {}
                reference_truth = None
                for model_name, frames in (("lstm", lstm), ("dlinear", dlinear)):
                    for feature in ("F0_LOCAL", "F1_THROUGHPUT"):
                        seed_metrics = []
                        for seed in (0, 1, 2):
                            subset = frames[(feature, seed)]
                            subset = subset[subset.lead.eq(lead) & subset.origin_index.isin(common)].sort_values("origin_index")
                            truth = subset.y_true.to_numpy()
                            if reference_truth is None:
                                reference_truth = truth
                            elif not np.array_equal(truth, reference_truth):
                                raise RuntimeError(f"LSTM/DLinear target mismatch {machine}/{fold}/{lead}")
                            seed_metrics.append(macro_metrics(truth, subset.y_pred.to_numpy()))
                        model_values[(model_name, feature)] = np.mean(seed_metrics, axis=0)
                dl_f0 = model_values[("dlinear", "F0_LOCAL")]
                dl_f1 = model_values[("dlinear", "F1_THROUGHPUT")]
                ls_f0 = model_values[("lstm", "F0_LOCAL")]
                ls_f1 = model_values[("lstm", "F1_THROUGHPUT")]
                rows.append({
                    "aggregation_level": "machine_fold",
                    "machine": machine,
                    "fold": fold,
                    "lead": lead,
                    "support_relation": relation,
                    "common_test_n": len(common),
                    "common_test_hash": sample_set_hash(common),
                    "dlinear_f0_mae": dl_f0[0],
                    "dlinear_f1_mae": dl_f1[0],
                    "dlinear_f1_context_gain_pct": 100.0 * (dl_f0[0] - dl_f1[0]) / dl_f0[0],
                    "lstm_f0_mae": ls_f0[0],
                    "lstm_f1_mae": ls_f1[0],
                    "lstm_f1_context_gain_pct": 100.0 * (ls_f0[0] - ls_f1[0]) / ls_f0[0],
                })
    cells = pd.DataFrame(rows)
    aggregate = cells.groupby("lead").agg(
        common_test_n=("common_test_n", "sum"),
        dlinear_f0_mae=("dlinear_f0_mae", "mean"),
        dlinear_f1_mae=("dlinear_f1_mae", "mean"),
        dlinear_f1_context_gain_pct=("dlinear_f1_context_gain_pct", "mean"),
        lstm_f0_mae=("lstm_f0_mae", "mean"),
        lstm_f1_mae=("lstm_f1_mae", "mean"),
        lstm_f1_context_gain_pct=("lstm_f1_context_gain_pct", "mean"),
    ).reset_index()
    aggregate.insert(0, "fold", "ALL")
    aggregate.insert(0, "machine", "ALL")
    aggregate.insert(0, "aggregation_level", "lead_macro")
    aggregate["support_relation"] = "EXACT_COMMON_SUBSETS"
    aggregate["common_test_hash"] = "per-cell hashes recorded above"
    return pd.concat([cells, aggregate], ignore_index=True, sort=False)


def lstm_lightgbm_comparison(registry: pd.DataFrame) -> pd.DataFrame:
    comparison = compatible_lightgbm_comparison(registry)
    return comparison.rename(columns={
        "dlinear_test_n": "lstm_test_n",
        "dlinear_f0_mean_seed_mae": "lstm_f0_mean_seed_mae",
        "dlinear_f1_mean_seed_mae": "lstm_f1_mean_seed_mae",
        "dlinear_f1_context_gain_pct": "lstm_f1_context_gain_pct",
    })


def make_figures(
    by_lead: pd.DataFrame,
    by_machine: pd.DataFrame,
    vs_dlinear: pd.DataFrame,
    vs_lightgbm: pd.DataFrame,
) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for old in FIGURES.glob("*.png"):
        old.unlink()
    plt.figure(figsize=(8, 5))
    for feature, rows in by_lead.groupby("feature_set"):
        plt.plot(rows.lead, rows.mae, marker="o", label=FEATURE_LABELS[feature])
    plt.xscale("log", base=2); plt.xlabel("Real future lead"); plt.ylabel("MAE")
    plt.title("LSTM CPU MAE by real future lead"); plt.legend(); plt.tight_layout()
    plt.savefig(FIGURES / "01_lstm_f0_f1_mae_by_lead.png", dpi=160); plt.close()

    gains = by_lead[by_lead.feature_set.eq("F1_THROUGHPUT")]
    plt.figure(figsize=(8, 5)); plt.axhline(0, color="black", linewidth=1)
    plt.plot(gains.lead, gains.mae_gain_pct, marker="o")
    plt.xscale("log", base=2); plt.xlabel("Real future lead"); plt.ylabel("Matched F1 MAE gain (%)")
    plt.title("LSTM matched throughput gain"); plt.tight_layout()
    plt.savefig(FIGURES / "02_lstm_f1_gain_by_lead.png", dpi=160); plt.close()

    heat = by_machine[by_machine.feature_set.eq("F1_THROUGHPUT")].pivot(index="machine", columns="lead", values="mae_gain_pct")
    plt.figure(figsize=(10, 5)); image = plt.imshow(heat.to_numpy(), aspect="auto", cmap="RdBu_r")
    plt.colorbar(image, label="Matched F1 MAE gain (%)")
    plt.xticks(range(len(heat.columns)), heat.columns); plt.yticks(range(len(heat.index)), heat.index)
    plt.xlabel("Real future lead"); plt.ylabel("Machine"); plt.title("LSTM throughput gain by machine and lead")
    plt.tight_layout(); plt.savefig(FIGURES / "03_lstm_machine_lead_gain_heatmap.png", dpi=160); plt.close()

    macro = vs_dlinear[vs_dlinear.aggregation_level.eq("lead_macro")]
    plt.figure(figsize=(9, 5))
    for column, label in (("dlinear_f0_mae", "DLinear F0"), ("dlinear_f1_mae", "DLinear F1"), ("lstm_f0_mae", "LSTM F0"), ("lstm_f1_mae", "LSTM F1")):
        plt.plot(macro.lead, macro[column], marker="o", label=label)
    plt.xscale("log", base=2); plt.xlabel("Real future lead"); plt.ylabel("MAE on compatible support")
    plt.title("LSTM versus DLinear"); plt.legend(); plt.tight_layout()
    plt.savefig(FIGURES / "04_lstm_vs_dlinear_mae.png", dpi=160); plt.close()

    macro = vs_lightgbm[vs_lightgbm.aggregation_level.eq("lead_macro")]
    plt.figure(figsize=(9, 5))
    for column, label in (("lightgbm_f0_mae", "LightGBM matched F0"), ("lightgbm_f1_mae", "LightGBM F1"), ("lstm_f0_mean_seed_mae", "LSTM F0"), ("lstm_f1_mean_seed_mae", "LSTM F1")):
        plt.plot(macro.lead, macro[column], marker="o", label=label)
    plt.xscale("log", base=2); plt.xlabel("Real future lead"); plt.ylabel("MAE on compatible support")
    plt.title("LSTM versus LightGBM"); plt.legend(); plt.tight_layout()
    plt.savefig(FIGURES / "05_lstm_vs_lightgbm_mae.png", dpi=160); plt.close()


def write_report(
    by_lead: pd.DataFrame,
    matched: pd.DataFrame,
    selected: pd.DataFrame,
    vs_dlinear: pd.DataFrame,
    vs_lightgbm: pd.DataFrame,
    label: str,
    counts: dict[str, object],
) -> None:
    f0 = by_lead[by_lead.feature_set.eq("F0_LOCAL")].sort_values("lead")
    f1 = by_lead[by_lead.feature_set.eq("F1_THROUGHPUT")].sort_values("lead")
    lead_gains = matched.groupby("lead", as_index=False).mae_gain_pct.mean()
    machine_means = matched.groupby("machine").mae_gain_pct.mean()
    fold_means = matched.groupby("fold").mae_gain_pct.mean()
    seed_means = matched.groupby("seed").mae_gain_pct.mean()
    selected_counts = selected.groupby(["feature_set", "selected_L"]).size()
    piv = selected.pivot(index=["machine", "fold"], columns="feature_set", values="selected_L")
    dl = vs_dlinear[vs_dlinear.aggregation_level.eq("lead_macro")].sort_values("lead")
    lb = vs_lightgbm[vs_lightgbm.aggregation_level.eq("lead_macro")].sort_values("lead")
    dl_f0_wins = int((dl.lstm_f0_mae < dl.dlinear_f0_mae).sum())
    dl_f1_wins = int((dl.lstm_f1_mae < dl.dlinear_f1_mae).sum())
    dl_context_wins = int((dl.lstm_f1_context_gain_pct > dl.dlinear_f1_context_gain_pct).sum())
    lb_f0_wins = int((lb.lstm_f0_mean_seed_mae < lb.lightgbm_f0_mae).sum())
    lb_f1_wins = int((lb.lstm_f1_mean_seed_mae < lb.lightgbm_f1_mae).sum())
    lb_context_wins = int((lb.lstm_f1_context_gain_pct > lb.lightgbm_f1_context_gain_pct).sum())
    lines = [
        "# Phase 2B-2A2 LSTM Scientific Report", "",
        "This is a descriptive report; no statistical-significance test is performed.", "",
        "## Aggregate lead results", "",
        "| Lead | LSTM F0 MAE | LSTM F1 MAE | Matched F1 gain (%) |", "|---:|---:|---:|---:|",
    ]
    for f0_row, f1_row in zip(f0.itertuples(), f1.itertuples()):
        lines.append(f"| {int(f0_row.lead)} | {f0_row.mae:.4f} | {f1_row.mae:.4f} | {f1_row.mae_gain_pct:.3f} |")
    lines += [
        "", "## Descriptive answers", "",
        f"1. LSTM F0 MAE vector: {f0.mae.tolist()}.",
        f"2. LSTM F1 MAE vector: {f1.mae.tolist()}.",
        f"3. Matched F1 gain vector: {lead_gains.mae_gain_pct.tolist()}%; overall cell-mean gain {counts['overall_mean_gain_pct']:.3f}%.",
        f"4. Positive aggregate leads: {lead_gains.loc[lead_gains.mae_gain_pct > 0, 'lead'].astype(int).tolist()} ({counts['positive_leads']}/8).",
        f"5. Positive machine means: {machine_means[machine_means > 0].index.tolist()} ({counts['positive_machines']}/7).",
        f"6. Positive fold means: {fold_means[fold_means > 0].index.astype(int).tolist()} ({counts['positive_folds']}/5).",
        f"7. Seed mean gains: {seed_means.round(3).to_dict()}; {counts['positive_seeds']}/3 positive seeds.",
        f"8. F0 selected-L counts: {selected_counts.get('F0_LOCAL', pd.Series(dtype=int)).to_dict()}.",
        f"9. F1 selected-L counts: {selected_counts.get('F1_THROUGHPUT', pd.Series(dtype=int)).to_dict()}.",
        f"10. Throughput changes preferred L in {int((piv.F0_LOCAL != piv.F1_THROUGHPUT).sum())}/35 cells.",
        f"11. LSTM beats frozen DLinear F0 at {dl_f0_wins}/8 leads and DLinear F1 at {dl_f1_wins}/8 leads on compatible support.",
        f"12. LSTM beats accepted LightGBM F0 at {lb_f0_wins}/8 leads and LightGBM F1 at {lb_f1_wins}/8 leads on compatible support.",
        f"13. LSTM has larger incremental throughput gain than DLinear at {dl_context_wins}/8 leads.",
        f"14. LSTM has larger incremental throughput gain than LightGBM at {lb_context_wins}/8 leads.",
        f"15. Architecture-dependent interpretation: corrected Ridge throughput was negative at all eight leads; accepted LightGBM throughput was conditionally positive; frozen DLinear was broad negative; LSTM is {label}. This pattern is descriptive evidence that extracted throughput value depends on architecture, not evidence of universal usefulness or uselessness.",
        "", "All cross-model comparisons use exact identical support or exact prediction intersections without retraining. Per-cell support relations and hashes are retained in the comparison CSV files.",
        "", "## LSTM throughput decision", "",
        "Prospective rule: `BROAD_POSITIVE` requires positive overall gain, 8/8 positive leads, at least 5/7 positive machines, at least 4/5 positive folds, and 3/3 positive seeds; `CONDITIONALLY_POSITIVE` requires positive overall gain, at least 4/8 leads, 4/7 machines, 3/5 folds, and 2/3 seeds; `BROAD_NEGATIVE` requires negative overall gain, at least 6/8 negative leads, 5/7 machines, 4/5 folds, and 3/3 seeds; all other patterns are `NEUTRAL`.",
        "", f"**{label}**", "", f"Observed consistency counts: {counts}.", "",
        "No DLinear rerun, PatchTST, TCN-v2, B4-v1, or multi-target model was executed.",
    ]
    (ROOT / "benchmark/neural_v2/LSTM_SCIENTIFIC_REPORT.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    started = time.perf_counter()
    metrics = pd.read_parquet(OUT / "metrics.parquet")
    registry = pd.read_csv(OUT / "run_registry.csv")
    selected = pd.read_csv(OUT / "selected_contexts.csv")
    matched = matched_metrics(metrics)
    atomic_parquet(OUT / "f0_f1_matched_metrics.parquet", matched)
    atomic_csv(OUT / "seed_summary.csv", build_seed_summary(metrics, matched))
    by_lead, by_machine, by_fold = aggregate_tables(metrics, matched)
    atomic_csv(OUT / "aggregate_by_lead.csv", by_lead)
    atomic_csv(OUT / "aggregate_by_machine.csv", by_machine)
    atomic_csv(OUT / "aggregate_by_fold.csv", by_fold)
    vs_dlinear = lstm_dlinear_comparison(registry)
    atomic_csv(OUT / "lstm_vs_dlinear.csv", vs_dlinear)
    vs_lightgbm = lstm_lightgbm_comparison(registry)
    atomic_csv(OUT / "lstm_vs_lightgbm.csv", vs_lightgbm)
    label, counts = decision(matched)
    make_figures(by_lead, by_machine, vs_dlinear, vs_lightgbm)
    write_report(by_lead, matched, selected, vs_dlinear, vs_lightgbm, label, counts)
    runtime_path = OUT / "runtime_accounting.json"
    runtime = json.loads(runtime_path.read_text())
    runtime["analysis_wall_seconds"] = time.perf_counter() - started
    runtime["total_recorded_wall_seconds"] = runtime["execution_wall_seconds"] + runtime["analysis_wall_seconds"]
    runtime["status"] = "ANALYSIS_COMPLETE_VALIDATION_PENDING"
    runtime["lstm_throughput_decision"] = label
    runtime["decision_counts"] = counts
    pilot_seconds = float(runtime["pilot_central_lstm_projection_hours"]) * 3600
    runtime["actual_to_pilot_runtime_ratio"] = float(runtime["execution_wall_seconds"]) / pilot_seconds
    runtime["actual_minus_pilot_seconds"] = float(runtime["execution_wall_seconds"]) - pilot_seconds
    atomic_json_write(runtime_path, runtime)
    print(json.dumps({"decision": label, **counts}, indent=2))


if __name__ == "__main__":
    main()
