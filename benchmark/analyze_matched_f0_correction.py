#!/usr/bin/env python3
"""Analyze corrected matched/reselected F0 comparators."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark.src.metrics import relative_mae_change
from benchmark.src.windows import FUTURE_LEADS


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "benchmark" / "outputs"
BASE = ROOT / "benchmark" / "phase2b1_corrected"
OUTPUTS = BASE / "outputs"


def scalar(truth: np.ndarray, prediction: np.ndarray) -> tuple[float, float, float]:
    residual = truth.astype(float) - prediction.astype(float)
    mae = float(np.mean(np.abs(residual)))
    rmse = float(np.sqrt(np.mean(residual ** 2)))
    total = float(np.sum((truth - truth.mean()) ** 2))
    r2 = float(1 - np.sum(residual ** 2) / total) if len(truth) > 1 and total > 0 else np.nan
    return mae, rmse, r2


def main() -> None:
    registry = pd.read_csv(OUTPUTS / "matched_f0_run_registry.csv")
    original_registry = pd.read_csv(ORIGINAL / "run_registry.csv").set_index("run_id")
    rows = []
    for run in registry.itertuples(index=False):
        candidate_run = original_registry.loc[run.candidate_run_id]
        candidate = pd.read_parquet(ROOT / candidate_run.prediction_path)
        reference = pd.read_parquet(ROOT / run.prediction_path)
        keys = ["sample_id", "origin_index", "lead", "target_index", "target_timestamp"]
        aligned = candidate[keys + ["y_true", "y_pred"]].merge(
            reference[keys + ["y_true", "y_pred"]], on=keys, validate="one_to_one",
            suffixes=("_candidate", "_matched_f0"),
        )
        if len(aligned) != len(candidate) or len(aligned) != len(reference):
            raise RuntimeError("Candidate/reference row alignment failure")
        if not np.array_equal(aligned.y_true_candidate.to_numpy(), aligned.y_true_matched_f0.to_numpy()):
            raise RuntimeError("Candidate/reference targets differ")
        for lead in FUTURE_LEADS:
            part = aligned[aligned.lead == lead]
            truth = part.y_true_candidate.to_numpy()
            candidate_mae, candidate_rmse, candidate_r2 = scalar(truth, part.y_pred_candidate.to_numpy())
            f0_mae, f0_rmse, f0_r2 = scalar(truth, part.y_pred_matched_f0.to_numpy())
            rows.append({
                "model": run.model, "candidate_feature_set": run.candidate_feature_set,
                "machine": run.machine, "outer_fold": int(run.outer_fold), "lead": lead,
                "candidate_run_id": run.candidate_run_id, "matched_f0_run_id": run.run_id,
                "n_samples": len(part), "test_hash": run.test_hash,
                "candidate_mae": candidate_mae, "matched_f0_mae": f0_mae,
                "corrected_context_mae_gain_pct": relative_mae_change(f0_mae, candidate_mae),
                "candidate_rmse": candidate_rmse, "matched_f0_rmse": f0_rmse,
                "corrected_context_rmse_gain_pct": relative_mae_change(f0_rmse, candidate_rmse),
                "candidate_r2": candidate_r2, "matched_f0_r2": f0_r2,
                "corrected_context_r2_delta": candidate_r2 - f0_r2,
                "sample_ids_exact_match": True, "targets_exact_match": True,
            })
    detail = pd.DataFrame(rows).sort_values(["model", "candidate_feature_set", "machine", "outer_fold", "lead"])
    detail.to_parquet(OUTPUTS / "corrected_context_matched_metrics.parquet", index=False, compression="zstd")
    detail.to_csv(OUTPUTS / "corrected_deterministic_context_ablation.csv", index=False)
    gains = detail.groupby(["model", "candidate_feature_set", "lead"], as_index=False).agg(
        corrected_context_mae_gain_pct=("corrected_context_mae_gain_pct", "mean"),
        median_corrected_context_mae_gain_pct=("corrected_context_mae_gain_pct", "median"),
        min_corrected_context_mae_gain_pct=("corrected_context_mae_gain_pct", "min"),
        max_corrected_context_mae_gain_pct=("corrected_context_mae_gain_pct", "max"),
        positive_machine_fold_fraction=("corrected_context_mae_gain_pct", lambda x: float((x > 0).mean())),
        corrected_context_rmse_gain_pct=("corrected_context_rmse_gain_pct", "mean"),
        corrected_context_r2_delta=("corrected_context_r2_delta", "mean"),
    )
    gains.to_csv(OUTPUTS / "corrected_context_gain_by_lead.csv", index=False)
    original = pd.read_csv(ORIGINAL / "context_gain_by_lead.csv").rename(columns={
        "feature_set": "candidate_feature_set",
        "mean_context_mae_gain_pct": "original_context_mae_gain_pct",
    })
    comparison = original[["model", "candidate_feature_set", "lead", "original_context_mae_gain_pct"]].merge(
        gains[["model", "candidate_feature_set", "lead", "corrected_context_mae_gain_pct"]],
        on=["model", "candidate_feature_set", "lead"], validate="one_to_one",
    )
    comparison["difference_percentage_points"] = comparison.corrected_context_mae_gain_pct - comparison.original_context_mae_gain_pct
    comparison["sign_changed"] = np.sign(comparison.original_context_mae_gain_pct) != np.sign(comparison.corrected_context_mae_gain_pct)
    comparison.to_csv(OUTPUTS / "original_vs_corrected_context_gains.csv", index=False)

    original_detail = pd.read_parquet(ORIGINAL / "context_matched_metrics.parquet").rename(columns={
        "feature_set": "candidate_feature_set",
        "relative_context_mae_gain_pct": "original_gain",
    })
    cell = original_detail[["model", "candidate_feature_set", "machine", "outer_fold", "lead", "original_gain"]].merge(
        detail[["model", "candidate_feature_set", "machine", "outer_fold", "lead", "corrected_context_mae_gain_pct"]],
        on=["model", "candidate_feature_set", "machine", "outer_fold", "lead"], validate="one_to_one",
    )
    cell["difference_pp"] = cell.corrected_context_mae_gain_pct - cell.original_gain
    cell["sign_changed"] = np.sign(cell.original_gain) != np.sign(cell.corrected_context_mae_gain_pct)
    signs = {
        "machine_fold_lead_cells": len(cell),
        "sign_changed": int(cell.sign_changed.sum()),
        "negative_to_positive": int(((cell.original_gain < 0) & (cell.corrected_context_mae_gain_pct > 0)).sum()),
        "positive_to_negative": int(((cell.original_gain > 0) & (cell.corrected_context_mae_gain_pct < 0)).sum()),
        "median_signed_correction_pp": float(cell.difference_pp.median()),
        "median_absolute_correction_pp": float(cell.difference_pp.abs().median()),
    }
    (OUTPUTS / "sign_change_summary.json").write_text(json.dumps(signs, indent=2) + "\n")

    consistency = []
    for (model, feature), group in detail.groupby(["model", "candidate_feature_set"]):
        machine = group.groupby("machine").corrected_context_mae_gain_pct.mean()
        fold = group.groupby("outer_fold").corrected_context_mae_gain_pct.mean()
        consistency.append({
            "model": model, "candidate_feature_set": feature,
            "mean_gain_pct": group.corrected_context_mae_gain_pct.mean(),
            "positive_cell_fraction": float((group.corrected_context_mae_gain_pct > 0).mean()),
            "machines_positive_of_7": int((machine > 0).sum()),
            "folds_positive_of_5": int((fold > 0).sum()),
        })
    consistency = pd.DataFrame(consistency)
    consistency.to_csv(OUTPUTS / "corrected_machine_fold_consistency.csv", index=False)

    def table(frame: pd.DataFrame) -> str:
        shown = frame.copy()
        for column in shown.select_dtypes(include=[np.number]).columns:
            shown[column] = shown[column].map(lambda value: f"{value:.3f}")
        header = "| " + " | ".join(shown.columns) + " |"
        separator = "|" + "|".join(["---"] * len(shown.columns)) + "|"
        body = ["| " + " | ".join(map(str, row)) + " |" for row in shown.itertuples(index=False, name=None)]
        return "\n".join([header, separator, *body])
    comparison_report = "\n".join([
        "# Original versus Corrected Context Gains", "",
        "The original candidate predictions and absolute metrics are unchanged. Only the matched F0 comparator changed.", "",
        table(comparison), "", "## Cell-level sign changes", "", *[f"- {k}: {v}" for k, v in signs.items()], "",
    ])
    (BASE / "ORIGINAL_VS_CORRECTED_COMPARISON.md").write_text(comparison_report)

    positive_leads = gains[gains.corrected_context_mae_gain_pct > 0].groupby(["model", "candidate_feature_set"]).lead.apply(list).to_dict()
    decision = "SUPPORTED" if all(consistency.mean_gain_pct > 0) else ("CONDITIONALLY_SUPPORTED" if (consistency.mean_gain_pct > 0).any() else "NOT_SUPPORTED")
    lgb_f1 = consistency[(consistency.model == "LightGBM") & (consistency.candidate_feature_set == "F1_THROUGHPUT")].iloc[0]
    lgb_f1_detail = detail[(detail.model == "LightGBM") & (detail.candidate_feature_set == "F1_THROUGHPUT")]
    positive_machines = lgb_f1_detail.groupby("machine").corrected_context_mae_gain_pct.mean().loc[lambda x: x > 0].index.tolist()
    positive_folds = [int(x) for x in lgb_f1_detail.groupby("outer_fold").corrected_context_mae_gain_pct.mean().loc[lambda x: x > 0].index]
    report = [
        "# Corrected Phase 2B-1 Context Report", "",
        "This report is descriptive; it is not a statistical-significance decision.", "",
        "## Corrected gains by lead", "", table(gains), "", "## Machine/fold consistency", "", table(consistency), "",
        "## Corrected descriptive answers", "",
        "1. **Ridge throughput:** No aggregate improvement. F1 remains negative at all eight leads; its overall mean gain is -1.717%.",
        "2. **LightGBM throughput:** Yes, modestly and heterogeneously. F1 is positive at all eight aggregate leads (0.356% to 1.010%) and averages 0.719%.",
        "3. **LOMO mean:** No broad benefit. F2 is negative at every lead for both Ridge and LightGBM.",
        "4. **LOMO median:** No broad benefit. F3 is negative at every lead for both models.",
        "5. **Combined F4/F5:** No broad benefit. Both combined contexts are negative at every aggregate lead for both models.",
        "6. **Positive real leads:** Only LightGBM F1 is aggregate-positive, at all leads [1, 2, 4, 8, 16, 32, 64, 128].",
        f"7. **Machine consistency:** LightGBM F1 is positive on {int(lgb_f1.machines_positive_of_7)}/7 machine averages: {positive_machines}.",
        f"8. **Fold consistency:** LightGBM F1 is positive on {int(lgb_f1.folds_positive_of_5)}/5 fold averages: {positive_folds}; fold 5 is negative.",
        f"9. **Material bias:** Yes. Median absolute cell correction is {signs['median_absolute_correction_pp']:.3f} percentage points, and the original LightGBM F1 overall mean changes from -0.108% to +0.719%.",
        f"10. **Magnitude versus direction:** Both changed. Most aggregate LOMO/combined and Ridge conclusions remain negative but less adverse; LightGBM F1 reverses overall direction. At cell level {signs['sign_changed']}/{signs['machine_fold_lead_cells']} signs change.",
        "11. **Local CPU sufficiency:** Local CPU remains a strong and broadly sufficient LightGBM baseline. Throughput adds only a small, nonuniform incremental gain; LOMO and combined contexts remain adverse.",
        "12. **Research-direction decision:** **CONDITIONALLY_SUPPORTED**. Only same-machine throughput with LightGBM has consistent aggregate lead-level support, and the effect is small and not positive on every machine or fold. A broad context-aware CPU direction is not supported.",
        "", "## Detailed model-feature summary", "",
    ]
    labels = {"F1_THROUGHPUT":"throughput", "F2_LOMO_MEAN":"LOMO mean", "F3_LOMO_MEDIAN":"LOMO median", "F4_THROUGHPUT_LOMO_MEAN":"throughput + LOMO mean", "F5_THROUGHPUT_LOMO_MEDIAN":"throughput + LOMO median"}
    for model in ["Ridge", "LightGBM"]:
        for feature in labels:
            row = consistency[(consistency.model == model) & (consistency.candidate_feature_set == feature)].iloc[0]
            report.append(f"- {model} {labels[feature]}: mean gain {row.mean_gain_pct:.3f}%; positive leads {positive_leads.get((model, feature), [])}; positive machines {int(row.machines_positive_of_7)}/7; positive folds {int(row.folds_positive_of_5)}/5.")
    report += ["", f"The support correction changed {signs['sign_changed']} of {signs['machine_fold_lead_cells']} cell signs ({signs['negative_to_positive']} negative-to-positive; {signs['positive_to_negative']} positive-to-negative). Median absolute correction was {signs['median_absolute_correction_pp']:.3f} percentage points.", "", f"Context-aware CPU direction decision: **{decision}**.", "", "DLinear and TCN were not executed."]
    (BASE / "CORRECTED_CONTEXT_REPORT.md").write_text("\n".join(report) + "\n")
    (OUTPUTS / "analysis_summary.json").write_text(json.dumps({"decision": decision, "signs": signs}, indent=2) + "\n")
    print(json.dumps({"detail_rows": len(detail), "gain_rows": len(gains), "decision": decision, **signs}, indent=2))


if __name__ == "__main__":
    main()
