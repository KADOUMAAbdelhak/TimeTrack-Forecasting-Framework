#!/usr/bin/env python3
"""Build post-audit cross-model F1-vs-F0 reporting tables without fitting models."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "benchmark/neural_v2"
CSV_PATH = BASE / "CROSS_MODEL_CONTEXT_SUMMARY.csv"
MD_PATH = BASE / "CROSS_MODEL_CONTEXT_SUMMARY.md"
LEADS = (1, 2, 4, 8, 16, 32, 64, 128)

EXPECTED = {
    "Ridge": (-1.7167271302399294, -3.8380483670030636, -3.631815130579816),
    "LightGBM": (0.7192049773495687, 0.01493478881284387, -0.08651501027420949),
    "DLinear": (-2.867954122384713, -2.604757074711472, -2.589274706814629),
    "LSTM": (3.0873780755251907, 1.2522065427725717, 0.849314402675976),
}


def summarize(model: str, cells: pd.DataFrame, macro_keys: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    scopes: list[tuple[object, pd.DataFrame]] = [(lead, cells[cells.lead.eq(lead)]) for lead in LEADS]
    scopes.append(("OVERALL", cells))
    for lead, part in scopes:
        macro = part.groupby(macro_keys, as_index=False).agg(
            f0_mae=("f0_mae", "mean"),
            f1_mae=("f1_mae", "mean"),
        )
        macro_f0 = float(macro.f0_mae.mean())
        macro_f1 = float(macro.f1_mae.mean())
        pooled_f0 = float(np.average(part.f0_mae, weights=part.n_predictions))
        pooled_f1 = float(np.average(part.f1_mae, weights=part.n_predictions))
        rows.append({
            "model": model,
            "lead": lead,
            "macro_f0_mae": macro_f0,
            "macro_f1_mae": macro_f1,
            "primary_ratio_macro_mae_gain_pct": 100.0 * (macro_f0 - macro_f1) / macro_f0,
            "pooled_f0_mae": pooled_f0,
            "pooled_f1_mae": pooled_f1,
            "pooled_gain_pct": 100.0 * (pooled_f0 - pooled_f1) / pooled_f0,
            "mean_cell_relative_gain_pct": float(part.cell_gain_pct.mean()),
            "median_cell_relative_gain_pct": float(part.cell_gain_pct.median()),
            "positive_cell_fraction": float((part.cell_gain_pct > 0).mean()),
            "n_macro_cells": len(macro),
            "n_relative_cells": len(part),
            "n_predictions": int(part.n_predictions.sum()),
        })
    return rows


def deterministic_cells(model: str) -> pd.DataFrame:
    detail = pd.read_csv(
        ROOT / "benchmark/phase2b1_corrected/outputs/corrected_deterministic_context_ablation.csv"
    )
    part = detail[
        detail.model.eq(model) & detail.candidate_feature_set.eq("F1_THROUGHPUT")
    ].copy()
    return part.rename(columns={
        "outer_fold": "fold",
        "matched_f0_mae": "f0_mae",
        "candidate_mae": "f1_mae",
        "corrected_context_mae_gain_pct": "cell_gain_pct",
        "n_samples": "n_predictions",
    })


def neural_cells(model: str) -> pd.DataFrame:
    out = ROOT / f"benchmark/neural_v2/outputs/{model.lower()}"
    matched = pd.read_parquet(out / "f0_f1_matched_metrics.parquet")
    registry = pd.read_csv(out / "run_registry.csv")
    counts = registry[registry.feature_set.eq("F0_LOCAL")][
        ["machine", "fold", "seed", "test_sample_count"]
    ]
    cells = matched.merge(counts, on=["machine", "fold", "seed"], validate="many_to_one")
    return cells.rename(columns={
        "mae_f0": "f0_mae",
        "mae_f1": "f1_mae",
        "mae_gain_pct": "cell_gain_pct",
        "test_sample_count": "n_predictions",
    })


def markdown_table(frame: pd.DataFrame) -> str:
    shown = frame.copy()
    for column in shown.select_dtypes(include=[np.number]).columns:
        shown[column] = shown[column].map(lambda value: f"{value:.6f}")
    header = "| " + " | ".join(shown.columns) + " |"
    rule = "|" + "|".join("---" for _ in shown.columns) + "|"
    body = ["| " + " | ".join(map(str, row)) + " |" for row in shown.itertuples(index=False, name=None)]
    return "\n".join([header, rule, *body])


def main() -> None:
    rows: list[dict[str, object]] = []
    for model in ("Ridge", "LightGBM"):
        rows.extend(summarize(model, deterministic_cells(model), ["machine", "fold", "lead"]))
    neural_models = ["DLinear", "LSTM"]
    if (ROOT / "benchmark/neural_v2/outputs/patchtst/metrics.parquet").exists():
        neural_models.append("PatchTST")
    for model in neural_models:
        rows.extend(summarize(model, neural_cells(model), ["machine", "fold", "lead"]))
    summary = pd.DataFrame(rows)
    # PatchTST prospectively defines pooled MAE on the stored predictions
    # themselves.  Use its independently generated direct-pooling table rather
    # than reconstructing pooled values from rounded per-run MAEs.
    patch_aggregation = ROOT / "benchmark/neural_v2/outputs/patchtst/aggregation_summary.csv"
    if patch_aggregation.exists():
        direct = pd.read_csv(patch_aggregation, dtype={"lead": str})
        summary["lead_key"] = summary.lead.astype(str)
        for row in direct.itertuples(index=False):
            mask = summary.model.eq("PatchTST") & summary.lead_key.eq(str(row.lead))
            summary.loc[mask, ["pooled_f0_mae", "pooled_f1_mae", "pooled_gain_pct"]] = [
                row.pooled_f0_mae, row.pooled_f1_mae, row.pooled_gain_pct
            ]
        summary = summary.drop(columns="lead_key")
    overall = summary[summary.lead.eq("OVERALL")].set_index("model")
    for model, expected in EXPECTED.items():
        actual = (
            float(overall.loc[model, "mean_cell_relative_gain_pct"]),
            float(overall.loc[model, "primary_ratio_macro_mae_gain_pct"]),
            float(overall.loc[model, "pooled_gain_pct"]),
        )
        if not np.allclose(actual, expected, atol=5e-12, rtol=0):
            raise RuntimeError(f"{model} audit summaries differ: {actual} != {expected}")
    summary.to_csv(CSV_PATH, index=False)

    display_columns = [
        "model", "lead", "macro_f0_mae", "macro_f1_mae",
        "primary_ratio_macro_mae_gain_pct", "pooled_f0_mae", "pooled_f1_mae",
        "pooled_gain_pct", "mean_cell_relative_gain_pct",
        "median_cell_relative_gain_pct", "positive_cell_fraction",
    ]
    overall_display = summary[summary.lead.eq("OVERALL")][display_columns]
    lstm_display = summary[summary.model.eq("LSTM") & ~summary.lead.eq("OVERALL")][display_columns]
    patchtst_lines: list[str] = []
    if "PatchTST" in set(summary.model):
        patch = summary[summary.model.eq("PatchTST") & ~summary.lead.eq("OVERALL")][display_columns]
        patchtst_lines = [
            "## PatchTST lead-level aggregation semantics", "", markdown_table(patch), "",
            "PatchTST was executed after this reporting convention was frozen; its",
            "prospective primary decision statistic is therefore the ratio of macro MAEs.", "",
        ]
    report = [
        "# Cross-Model Context Summary", "",
        "**POST-AUDIT REPORTING STANDARD.** This table is descriptive reporting, not a",
        "prospective hypothesis-test, selection, or decision criterion. Previously frozen",
        "decision labels are unchanged.", "",
        "The primary statistic is the ratio of separately macro-aggregated matched F0 and",
        "F1 MAEs. For stochastic neural models, seed MAEs are first averaged within each",
        "machine-fold-lead cell; machine-fold-lead cells then receive equal weight. The",
        "OVERALL macro F0 and F1 values are equal-weight means of the 8 lead-specific macro",
        "MAEs, and the overall primary percentage is calculated from those MAEs rather than",
        "by averaging lead percentages. Pooled values weight every stored prediction equally.",
        "Cell-relative summaries retain the original matched-cell percentage definition.", "",
        "## Overall standardized context summary", "", markdown_table(overall_display), "",
        "## LSTM lead-level aggregation semantics", "", markdown_table(lstm_display), "",
        "LSTM lead 1 is positive under the prospective mean cell-relative metric",
        "(+2.3506%) but negative under both the primary macro-MAE ratio (-2.4070%) and",
        "pooled-prediction gain (-2.8834%). Leads 2 through 128 are positive under all",
        "three summaries.", "",
        *patchtst_lines,
        "## Interpretation", "",
        "- Ridge: throughput is detrimental.",
        "- DLinear: throughput is detrimental.",
        "- LightGBM: the mean cell-relative effect is small and positive, but the macro-MAE",
        "  result is effectively neutral and the pooled result is slightly negative.",
        "- LSTM: throughput is positive overall under all three definitions, with smaller",
        "  magnitude under macro-MAE and pooled reporting than under cell percentages.", "",
        "Throughput usefulness is therefore architecture-dependent. Absolute CPU forecast",
        "performance is a separate question: LSTM did not beat accepted LightGBM absolute",
        "performance at any of the eight evaluated leads, and is not claimed to be the best",
        "forecasting model.", "",
        f"The complete {len(summary)}-row machine-readable table is `CROSS_MODEL_CONTEXT_SUMMARY.csv`.",
    ]
    MD_PATH.write_text("\n".join(report) + "\n")
    print(f"rows={len(summary)}")
    print(overall_display.to_string(index=False))


if __name__ == "__main__":
    main()
