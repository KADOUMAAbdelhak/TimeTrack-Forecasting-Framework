"""Prospectively frozen PatchTST aggregation and decision helpers."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from benchmark.neural_v2.analyze_dlinear_scientific import matched_metrics
from benchmark.neural_v2.src.data import FUTURE_LEADS


ROOT = Path(__file__).resolve().parents[2]


def aggregation_summary(
    metrics: pd.DataFrame, registry: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return lead/overall summaries and exact matched seed-level cells."""
    matched = matched_metrics(metrics)
    counts = registry[registry.feature_set.eq("F0_LOCAL")][
        ["machine", "fold", "seed", "test_sample_count"]
    ]
    matched = matched.merge(counts, on=["machine", "fold", "seed"], validate="many_to_one")
    pooled: dict[tuple[str, int], list[float | int]] = {
        (feature, lead): [0.0, 0]
        for feature in ("F0_LOCAL", "F1_THROUGHPUT") for lead in FUTURE_LEADS
    }
    for record in registry.itertuples(index=False):
        prediction = pd.read_parquet(ROOT / record.prediction_path)
        for lead, part in prediction.groupby("lead", sort=False):
            item = pooled[(record.feature_set, int(lead))]
            item[0] = float(item[0]) + float(np.abs(part.y_true - part.y_pred).sum())
            item[1] = int(item[1]) + len(part)
    rows: list[dict[str, object]] = []
    scopes: list[tuple[object, pd.DataFrame]] = [
        (lead, matched[matched.lead.eq(lead)]) for lead in FUTURE_LEADS
    ]
    scopes.append(("OVERALL", matched))
    for lead, part in scopes:
        macro = part.groupby(["machine", "fold", "lead"], as_index=False).agg(
            f0_mae=("mae_f0", "mean"), f1_mae=("mae_f1", "mean")
        )
        macro_f0 = float(macro.f0_mae.mean())
        macro_f1 = float(macro.f1_mae.mean())
        selected_leads = FUTURE_LEADS if lead == "OVERALL" else (lead,)
        pooled_f0 = sum(float(pooled[("F0_LOCAL", item)][0]) for item in selected_leads) / sum(int(pooled[("F0_LOCAL", item)][1]) for item in selected_leads)
        pooled_f1 = sum(float(pooled[("F1_THROUGHPUT", item)][0]) for item in selected_leads) / sum(int(pooled[("F1_THROUGHPUT", item)][1]) for item in selected_leads)
        rows.append({
            "lead": lead,
            "macro_f0_mae": macro_f0,
            "macro_f1_mae": macro_f1,
            "primary_gain_pct": 100.0 * (macro_f0 - macro_f1) / macro_f0,
            "pooled_f0_mae": pooled_f0,
            "pooled_f1_mae": pooled_f1,
            "pooled_gain_pct": 100.0 * (pooled_f0 - pooled_f1) / pooled_f0,
            "mean_cell_relative_gain_pct": float(part.mae_gain_pct.mean()),
            "median_cell_relative_gain_pct": float(part.mae_gain_pct.median()),
            "positive_cell_fraction": float((part.mae_gain_pct > 0).mean()),
            "n_macro_cells": len(macro),
            "n_relative_cells": len(part),
            "n_predictions": int(part.test_sample_count.sum()),
        })
    return pd.DataFrame(rows), matched


def ratio_gain(frame: pd.DataFrame) -> float:
    f0 = float(frame.mae_f0.mean())
    f1 = float(frame.mae_f1.mean())
    return 100.0 * (f0 - f1) / f0


def subgroup_gains(matched: pd.DataFrame, column: str) -> pd.Series:
    return matched.groupby(column, sort=True).apply(ratio_gain, include_groups=False)


def prospective_decision(
    summary: pd.DataFrame, matched: pd.DataFrame
) -> tuple[str, dict[str, object], dict[str, pd.Series]]:
    lead_rows = summary[~summary.lead.eq("OVERALL")].copy()
    overall = float(summary[summary.lead.eq("OVERALL")].iloc[0].primary_gain_pct)
    machine = subgroup_gains(matched, "machine")
    fold = subgroup_gains(matched, "fold")
    seed = subgroup_gains(matched, "seed")
    counts: dict[str, object] = {
        "overall_primary_gain_pct": overall,
        "positive_leads": int((lead_rows.primary_gain_pct > 0).sum()),
        "positive_machines": int((machine > 0).sum()),
        "positive_folds": int((fold > 0).sum()),
        "positive_seeds": int((seed > 0).sum()),
        "negative_leads": int((lead_rows.primary_gain_pct < 0).sum()),
        "negative_machines": int((machine < 0).sum()),
        "negative_folds": int((fold < 0).sum()),
        "negative_seeds": int((seed < 0).sum()),
    }
    if (
        overall > 0
        and counts["positive_leads"] == 8
        and counts["positive_machines"] >= 5
        and counts["positive_folds"] >= 4
        and counts["positive_seeds"] == 3
    ):
        label = "BROAD_POSITIVE"
    elif (
        overall > 0
        and counts["positive_leads"] >= 4
        and counts["positive_machines"] >= 4
        and counts["positive_folds"] >= 3
        and counts["positive_seeds"] >= 2
    ):
        label = "CONDITIONALLY_POSITIVE"
    elif (
        overall < 0
        and counts["negative_leads"] >= 6
        and counts["negative_machines"] >= 5
        and counts["negative_folds"] >= 4
        and counts["negative_seeds"] == 3
    ):
        label = "BROAD_NEGATIVE"
    else:
        label = "NEUTRAL"
    return label, counts, {"machine": machine, "fold": fold, "seed": seed}
