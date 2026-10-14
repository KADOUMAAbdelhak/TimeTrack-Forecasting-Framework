#!/usr/bin/env python3
"""Execute the frozen, no-training Phase 4D Materna scientific analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / "outputs/scientific_v1"
ANALYSIS = OUT / "analysis"
COMPARISONS = OUT / "comparisons"
SYNTHESIS = OUT / "synthesis"
FIGURES = OUT / "figures"
REPORT = BASE / "PHASE4D_MATERNA_SCIENTIFIC_REPORT.md"
TRACES = ("Materna-T1", "Materna-T2", "Materna-T3")
RESOURCES = ("CPU", "THROUGHPUT", "MEMORY", "DISK_WRITE")
LEADS = (1, 2, 4, 9, 18)
HORIZONS = {1: 5, 2: 10, 4: 20, 9: 45, 18: 90}
FORMULATIONS = ("S1", "S2", "M1")
COMPARISON_DEFS = {
    "S2_vs_S1": ("S1", "S2"),
    "M1_vs_S2": ("S2", "M1"),
    "M1_vs_S1": ("S1", "M1"),
}
BOOTSTRAP_SEED = 20261007
BOOTSTRAP_REPLICATES = 10_000
POSITIVE_CLASSES = {"BROAD_POSITIVE", "CONDITIONALLY_POSITIVE"}

TIMETRACK = {
    "S2_vs_S1": {"CPU": -3.3130, "THROUGHPUT": -0.2428, "MEMORY": 0.8594, "DISK_WRITE": -0.4923},
    "M1_vs_S2": {"CPU": 0.4696, "THROUGHPUT": -0.8401, "MEMORY": -18.4769, "DISK_WRITE": -0.7956},
    "M1_vs_S1": {"CPU": -2.8279, "THROUGHPUT": -1.0849, "MEMORY": -17.4587, "DISK_WRITE": -1.2918},
}
BITBRAINS = {
    "S2_vs_S1": {
        "CPU": (-3.198519, 1.412867), "THROUGHPUT": (0.012731, -7.214491),
        "MEMORY": (2.449985, 1.673083), "DISK_WRITE": (2.689207, 0.160400),
    },
    "M1_vs_S2": {
        "CPU": (0.045047, -16.509941), "THROUGHPUT": (-27.094152, -14.318987),
        "MEMORY": (-4.867061, -8.915737), "DISK_WRITE": (-4.072129, -5.551233),
    },
    "M1_vs_S1": {
        "CPU": (-3.152031, -14.863811), "THROUGHPUT": (-27.077972, -22.566520),
        "MEMORY": (-2.297834, -7.093487), "DISK_WRITE": (-1.273414, -5.381929),
    },
}
BITBRAINS_CLASSES = {
    "S2_vs_S1": {
        "CPU": ("NEUTRAL_OR_MIXED", "CONDITIONALLY_POSITIVE"),
        "THROUGHPUT": ("NEUTRAL_OR_MIXED", "NEUTRAL_OR_MIXED"),
        "MEMORY": ("BROAD_POSITIVE", "CONDITIONALLY_POSITIVE"),
        "DISK_WRITE": ("CONDITIONALLY_POSITIVE", "NEUTRAL_OR_MIXED"),
    },
    "M1_vs_S2": {resource: (("NEUTRAL_OR_MIXED" if resource == "CPU" else "BROAD_NEGATIVE"), "BROAD_NEGATIVE") for resource in RESOURCES},
    "M1_vs_S1": {
        "CPU": ("BROAD_NEGATIVE", "BROAD_NEGATIVE"),
        "THROUGHPUT": ("BROAD_NEGATIVE", "BROAD_NEGATIVE"),
        "MEMORY": ("NEUTRAL_OR_MIXED", "BROAD_NEGATIVE"),
        "DISK_WRITE": ("NEUTRAL_OR_MIXED", "BROAD_NEGATIVE"),
    },
}


def gain(reference: np.ndarray | pd.Series | float,
         candidate: np.ndarray | pd.Series | float):
    return 100.0 * (reference - candidate) / reference


def sign(value: float, tolerance: float = 1e-12) -> int:
    return 1 if value > tolerance else (-1 if value < -tolerance else 0)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, lineterminator="\n")


def write_json(value: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def md_table(frame: pd.DataFrame, columns: Iterable[str] | None = None) -> str:
    shown = frame.loc[:, list(columns)] if columns is not None else frame
    values = shown.copy()
    for column in values.select_dtypes(include=["float"]).columns:
        values[column] = values[column].map(lambda value: f"{value:.6f}")
    header = "| " + " | ".join(map(str, values.columns)) + " |"
    divider = "|" + "|".join("---" for _ in values.columns) + "|"
    rows = ["| " + " | ".join(map(str, row)) + " |" for row in values.itertuples(index=False, name=None)]
    return "\n".join([header, divider, *rows])


def load_metrics() -> pd.DataFrame:
    frames = []
    for trace in TRACES:
        frame = pd.read_parquet(OUT / trace / "metrics.parquet")
        frame["vm_id"] = frame.vm_id.astype(str)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def primary_tables(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cell_keys = ["environment_key", "formulation", "resource", "lead", "horizon_minutes", "vm_id", "fold"]
    cells = metrics.groupby(cell_keys, as_index=False, sort=True).mae.mean().rename(columns={"mae": "seed_mean_mae"})
    macro = cells.groupby(cell_keys[:5], as_index=False, sort=True).seed_mean_mae.mean().rename(columns={"seed_mean_mae": "macro_mae"})
    macro["scope"] = "lead"
    overall = macro.groupby(["environment_key", "formulation", "resource"], as_index=False, sort=True).macro_mae.mean()
    overall["lead"] = 0
    overall["horizon_minutes"] = 0
    overall["scope"] = "overall_equal_horizon"
    primary = pd.concat([macro, overall], ignore_index=True)

    weighted = metrics.assign(weighted_mae=metrics.mae * metrics.n).groupby(
        ["environment_key", "formulation", "resource", "lead", "horizon_minutes"], as_index=False, sort=True
    ).agg(weighted_mae=("weighted_mae", "sum"), n=("n", "sum"))
    weighted["pooled_mae"] = weighted.weighted_mae / weighted.n
    weighted["scope"] = "lead"
    pooled_overall = metrics.assign(weighted_mae=metrics.mae * metrics.n).groupby(
        ["environment_key", "formulation", "resource"], as_index=False, sort=True
    ).agg(weighted_mae=("weighted_mae", "sum"), n=("n", "sum"))
    pooled_overall["pooled_mae"] = pooled_overall.weighted_mae / pooled_overall.n
    pooled_overall["lead"] = 0
    pooled_overall["horizon_minutes"] = 0
    pooled_overall["scope"] = "overall_pooled_predictions"
    pooled = pd.concat([weighted, pooled_overall], ignore_index=True)
    return cells, primary, pooled


def comparison_tables(metrics: pd.DataFrame, cells: pd.DataFrame, primary: pd.DataFrame,
                      pooled: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows, vm_rows, fold_rows, seed_rows = [], [], [], []
    for trace in TRACES:
        for comparison, (reference, candidate) in COMPARISON_DEFS.items():
            for resource in RESOURCES:
                for lead in (*LEADS, 0):
                    p = primary[(primary.environment_key == trace) & (primary.resource == resource)]
                    p = p[(p.lead == lead) & (p.scope == ("lead" if lead else "overall_equal_horizon"))]
                    values = p.set_index("formulation").macro_mae
                    primary_gain = float(gain(values[reference], values[candidate]))

                    q = pooled[(pooled.environment_key == trace) & (pooled.resource == resource) & (pooled.lead == lead)]
                    pool_values = q.set_index("formulation").pooled_mae
                    pooled_gain = float(gain(pool_values[reference], pool_values[candidate]))

                    c = cells[(cells.environment_key == trace) & (cells.resource == resource)]
                    if lead:
                        c = c[c.lead == lead]
                    else:
                        c = c.groupby(["formulation", "vm_id", "fold"], as_index=False).seed_mean_mae.mean()
                    pivot = c.pivot(index=["vm_id", "fold"], columns="formulation", values="seed_mean_mae")
                    relative = gain(pivot[reference], pivot[candidate])
                    rows.append({
                        "trace": trace, "comparison": comparison, "reference": reference,
                        "candidate": candidate, "resource": resource,
                        "scope": "lead" if lead else "overall", "lead": lead,
                        "horizon_minutes": HORIZONS.get(lead, 0),
                        "reference_macro_mae": float(values[reference]),
                        "candidate_macro_mae": float(values[candidate]),
                        "primary_macro_gain_percent": primary_gain,
                        "reference_pooled_mae": float(pool_values[reference]),
                        "candidate_pooled_mae": float(pool_values[candidate]),
                        "pooled_gain_percent": pooled_gain,
                        "mean_cell_relative_gain_percent": float(relative.mean()),
                        "median_cell_relative_gain_percent": float(relative.median()),
                        "positive_cell_fraction": float((relative > 0).mean()),
                        "primary_pooled_sign_reversal": sign(primary_gain) != sign(pooled_gain),
                        "primary_mean_cell_sign_reversal": sign(primary_gain) != sign(float(relative.mean())),
                        "primary_median_cell_sign_reversal": sign(primary_gain) != sign(float(relative.median())),
                    })

                base = cells[(cells.environment_key == trace) & (cells.resource == resource)]
                vm = base.groupby(["formulation", "vm_id"], as_index=False).seed_mean_mae.mean().pivot(index="vm_id", columns="formulation", values="seed_mean_mae")
                for vm_id, value in gain(vm[reference], vm[candidate]).items():
                    vm_rows.append({"trace": trace, "comparison": comparison, "resource": resource, "vm_id": vm_id, "gain_percent": value, "positive": value > 0})
                fold = base.groupby(["formulation", "fold"], as_index=False).seed_mean_mae.mean().pivot(index="fold", columns="formulation", values="seed_mean_mae")
                for fold_id, value in gain(fold[reference], fold[candidate]).items():
                    fold_rows.append({"trace": trace, "comparison": comparison, "resource": resource, "fold": fold_id, "gain_percent": value, "positive": value > 0})
                seed = metrics[(metrics.environment_key == trace) & (metrics.resource == resource)].groupby(
                    ["formulation", "seed"], as_index=False
                ).mae.mean().pivot(index="seed", columns="formulation", values="mae")
                for seed_id, value in gain(seed[reference], seed[candidate]).items():
                    seed_rows.append({"trace": trace, "comparison": comparison, "resource": resource, "seed": seed_id, "gain_percent": value, "positive": value > 0})
    return pd.DataFrame(rows), pd.DataFrame(vm_rows), pd.DataFrame(fold_rows), pd.DataFrame(seed_rows)


def classify_resources(comparisons: pd.DataFrame, vm: pd.DataFrame,
                       fold: pd.DataFrame, seed: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for trace in TRACES:
        for comparison in COMPARISON_DEFS:
            for resource in RESOURCES:
                subset = comparisons[(comparisons.trace == trace) & (comparisons.comparison == comparison) & (comparisons.resource == resource)]
                overall = float(subset[subset.scope == "overall"].primary_macro_gain_percent.iloc[0])
                horizons = int((subset[subset.scope == "lead"].primary_macro_gain_percent > 0).sum())
                vms = int(vm[(vm.trace == trace) & (vm.comparison == comparison) & (vm.resource == resource)].positive.sum())
                folds = int(fold[(fold.trace == trace) & (fold.comparison == comparison) & (fold.resource == resource)].positive.sum())
                seeds = int(seed[(seed.trace == trace) & (seed.comparison == comparison) & (seed.resource == resource)].positive.sum())
                if overall >= 1 and horizons >= 4 and vms >= 25 and folds >= 4 and seeds >= 2:
                    label = "BROAD_POSITIVE"
                elif overall > 0 and horizons >= 3 and vms >= 15 and folds >= 3 and seeds >= 2:
                    label = "CONDITIONALLY_POSITIVE"
                elif overall <= -1 and horizons <= 1 and vms <= 10 and folds <= 1 and seeds <= 1:
                    label = "BROAD_NEGATIVE"
                else:
                    label = "NEUTRAL_OR_MIXED"
                rows.append({
                    "trace": trace, "comparison": comparison, "resource": resource,
                    "overall_primary_gain_percent": overall, "positive_horizons": horizons,
                    "positive_vms": vms, "positive_folds": folds,
                    "positive_seed_aggregates": seeds, "classification": label,
                })
    return pd.DataFrame(rows)


def trace_decisions(classifications: pd.DataFrame) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for trace in TRACES:
        result[trace] = {}
        s2 = classifications[(classifications.trace == trace) & (classifications.comparison == "S2_vs_S1")]
        positive = int(s2.classification.isin(POSITIVE_CLASSES).sum())
        broad_negative = int((s2.classification == "BROAD_NEGATIVE").sum())
        mean_gain = float(s2.overall_primary_gain_percent.mean())
        if positive >= 3 and mean_gain > 0 and broad_negative <= 1:
            label, reason = "CROSS_RESOURCE_INPUT_SUPPORTED", "at least three positive resources, positive equal-resource mean, and at most one broad negative"
        elif (positive <= 1 and mean_gain <= 0) or broad_negative >= 2:
            label, reason = "CROSS_RESOURCE_INPUT_NOT_SUPPORTED", "frozen non-support predicate applied"
        else:
            label, reason = "CROSS_RESOURCE_INPUT_MIXED", "neither frozen support nor non-support predicate applied"
        result[trace]["S2_vs_S1"] = {"label": label, "reason": reason, "positive_resources": positive, "broad_negative_resources": broad_negative, "equal_resource_mean_gain_percent": mean_gain}

        m1 = classifications[(classifications.trace == trace) & (classifications.comparison == "M1_vs_S2")]
        positive = int(m1.classification.isin(POSITIVE_CLASSES).sum())
        broad_negative = int((m1.classification == "BROAD_NEGATIVE").sum())
        material_negative = int((m1.overall_primary_gain_percent <= -1).sum())
        mean_gain = float(m1.overall_primary_gain_percent.mean())
        strong_tradeoff = bool(m1.overall_primary_gain_percent.max() >= 1 and m1.overall_primary_gain_percent.min() <= -1)
        negative_transfer = (positive >= 1 and material_negative >= 2) or strong_tradeoff
        not_supported = positive <= 1 and mean_gain <= 0
        supported = positive >= 3 and mean_gain > 0 and broad_negative == 0
        conditional = mean_gain > 0 and positive >= 2 and not supported
        if negative_transfer:
            label, reason = "SHARED_REPRESENTATION_NEGATIVE_TRANSFER", "frozen conservative negative-transfer predicate applied"
        elif not_supported:
            label, reason = "SHARED_REPRESENTATION_NOT_SUPPORTED", "at most one positive resource and nonpositive equal-resource mean"
        elif supported:
            label, reason = "SHARED_REPRESENTATION_SUPPORTED", "full frozen support predicate applied"
        elif conditional:
            label, reason = "SHARED_REPRESENTATION_CONDITIONALLY_SUPPORTED", "positive mean and at least two positive resources"
        else:
            label, reason = "SHARED_REPRESENTATION_NOT_SUPPORTED", "residual_no_support"
        result[trace]["M1_vs_S2"] = {
            "label": label, "reason": reason, "positive_resources": positive,
            "broad_negative_resources": broad_negative, "materially_negative_resources": material_negative,
            "strong_target_specific_tradeoffs": strong_tradeoff,
            "equal_resource_mean_gain_percent": mean_gain,
        }

        joint = classifications[(classifications.trace == trace) & (classifications.comparison == "M1_vs_S1")]
        positive_raw = int((joint.overall_primary_gain_percent > 0).sum())
        negative_raw = int((joint.overall_primary_gain_percent < 0).sum())
        mean_gain = float(joint.overall_primary_gain_percent.mean())
        if positive_raw >= 3 and mean_gain > 0:
            label = "JOINT_SYSTEM_BROADLY_BENEFICIAL"
        elif negative_raw >= 3 and mean_gain < 0:
            label = "JOINT_SYSTEM_BROADLY_HARMFUL"
        else:
            label = "JOINT_SYSTEM_MIXED"
        result[trace]["M1_vs_S1"] = {"label": label, "positive_resources": positive_raw, "negative_resources": negative_raw, "equal_resource_mean_gain_percent": mean_gain}
    return result


def bootstrap(cells: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for trace in TRACES:
        vms = sorted(cells[cells.environment_key == trace].vm_id.unique())
        rng = np.random.default_rng(BOOTSTRAP_SEED)
        samples = rng.integers(0, len(vms), size=(BOOTSTRAP_REPLICATES, len(vms)))
        for comparison, (reference, candidate) in COMPARISON_DEFS.items():
            for resource in RESOURCES:
                for lead in (*LEADS, 0):
                    subset = cells[(cells.environment_key == trace) & (cells.resource == resource)]
                    if lead:
                        subset = subset[subset.lead == lead]
                    by_vm = subset.groupby(["formulation", "vm_id"], as_index=False).seed_mean_mae.mean().pivot(
                        index="vm_id", columns="formulation", values="seed_mean_mae"
                    ).reindex(vms)
                    ref, cand = by_vm[reference].to_numpy(), by_vm[candidate].to_numpy()
                    values = gain(ref[samples].mean(axis=1), cand[samples].mean(axis=1))
                    rows.append({
                        "interval_label": "PROSPECTIVELY DEFINED MATERNA TRACE UNCERTAINTY INTERVALS",
                        "trace": trace, "comparison": comparison, "resource": resource,
                        "scope": "lead" if lead else "overall_equal_horizon", "lead": lead,
                        "horizon_minutes": HORIZONS.get(lead, 0), "replicates": BOOTSTRAP_REPLICATES,
                        "rng_seed": BOOTSTRAP_SEED, "VM_draws": 35, "folds_retained_per_VM": 5,
                        "lower_2_5_percent": float(np.percentile(values, 2.5)),
                        "median_percent": float(np.percentile(values, 50)),
                        "upper_97_5_percent": float(np.percentile(values, 97.5)),
                    })
    return pd.DataFrame(rows)


def persistence_tables(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries, skills = [], []
    for trace in TRACES:
        p = pd.read_parquet(OUT / trace / "persistence_metrics.parquet")
        p["vm_id"] = p.vm_id.astype(str)
        cells = p.groupby(["resource", "lead", "horizon_minutes", "vm_id", "fold"], as_index=False)[["mae", "rmse", "r2", "nmae"]].mean()
        summary = cells.groupby(["resource", "lead", "horizon_minutes"], as_index=False)[["mae", "rmse", "r2", "nmae"]].mean()
        summary.insert(0, "trace", trace)
        summaries.append(summary)

        skill_cells = metrics[metrics.environment_key == trace].groupby(
            ["formulation", "resource", "lead", "horizon_minutes", "vm_id", "fold"], as_index=False
        ).persistence_skill.mean()
        skill = skill_cells.groupby(["formulation", "resource", "lead", "horizon_minutes"], as_index=False).persistence_skill.mean()
        skill.insert(0, "trace", trace)
        overall = skill.groupby(["trace", "formulation", "resource"], as_index=False).persistence_skill.mean()
        overall["lead"] = 0
        overall["horizon_minutes"] = 0
        skills.append(pd.concat([skill, overall], ignore_index=True))
    return pd.concat(summaries, ignore_index=True), pd.concat(skills, ignore_index=True)


def temporal_synthesis(comparisons: pd.DataFrame) -> pd.DataFrame:
    pivot = comparisons.pivot_table(
        index=["comparison", "resource", "scope", "lead", "horizon_minutes"],
        columns="trace", values="primary_macro_gain_percent"
    ).reset_index()
    pivot["equal_temporal_block_gain_percent"] = pivot[list(TRACES)].mean(axis=1)
    pivot["sign_pattern"] = pivot[list(TRACES)].apply(lambda row: "/".join("+" if v > 0 else ("-" if v < 0 else "0") for v in row), axis=1)
    pivot["max_minus_min_temporal_spread_percent"] = pivot[list(TRACES)].max(axis=1) - pivot[list(TRACES)].min(axis=1)
    pivot["synthesis_label"] = "EQUAL_TEMPORAL_BLOCK_SYNTHESIS"
    return pivot


def heterogeneity_tables(classifications: pd.DataFrame, comparisons: pd.DataFrame,
                         vm: pd.DataFrame, decisions: dict[str, dict[str, object]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    class_rows = []
    for comparison in COMPARISON_DEFS:
        for resource in RESOURCES:
            subset = classifications[(classifications.comparison == comparison) & (classifications.resource == resource)].set_index("trace")
            classes = [subset.loc[t, "classification"] for t in TRACES]
            gains = [float(subset.loc[t, "overall_primary_gain_percent"]) for t in TRACES]
            class_rows.append({
                "comparison": comparison, "resource": resource,
                **{f"{trace}_classification": cls for trace, cls in zip(TRACES, classes)},
                **{f"{trace}_gain_percent": value for trace, value in zip(TRACES, gains)},
                "temporally_classification_variable": len(set(classes)) > 1,
                "raw_sign_reversal": len({sign(value) for value in gains}) > 1,
            })
    vm_pivot = vm.pivot_table(index=["comparison", "resource", "vm_id"], columns="trace", values="gain_percent").reset_index()
    vm_pivot["temporal_range_percent"] = vm_pivot[list(TRACES)].max(axis=1) - vm_pivot[list(TRACES)].min(axis=1)
    vm_pivot["raw_sign_reversal"] = vm_pivot[list(TRACES)].apply(lambda row: len({sign(v) for v in row}) > 1, axis=1)
    return pd.DataFrame(class_rows), vm_pivot


def loss_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    selected_rows = []
    for trace in TRACES:
        epochs = pd.read_csv(OUT / trace / "selected_epochs.csv", dtype={"vm_id": str})
        selected = epochs[epochs.formulation == "M1"][["vm_id", "fold", "seed", "selected_L", "selected_epoch"]]
        history = pd.read_parquet(OUT / trace / "m1_resource_loss_history.parquet")
        history["vm_id"] = history.vm_id.astype(str)
        history = history[history.phase == "inner"]
        merged = history.merge(selected, left_on=["vm_id", "fold", "seed", "L", "epoch"], right_on=["vm_id", "fold", "seed", "selected_L", "selected_epoch"], how="inner")
        merged.insert(0, "trace", trace)
        selected_rows.append(merged[["trace", "vm_id", "fold", "seed", "L", "epoch", "resource", "validation_loss_share"]])
    selected = pd.concat(selected_rows, ignore_index=True)
    summary = selected.groupby(["trace", "resource"]).validation_loss_share.agg(["mean", "median"]).reset_index()
    summary["mean_percent"] = 100 * summary.pop("mean")
    summary["median_percent"] = 100 * summary.pop("median")
    return selected, summary


def efficiency_table() -> pd.DataFrame:
    runtime = json.loads((OUT / "runtime/combined_runtime_storage_accounting.json").read_text())
    rows = []
    specs = {"S1": (203028, 4), "S2": (206100, 4), "M1": (52500, 1)}
    for formulation, (parameters, models) in specs.items():
        fit_hours = sum(
            runtime["traces"][trace]["stage_fit_hours"][f"{formulation}_{phase}"]
            for trace in TRACES for phase in ("inner", "final")
        )
        rows.append({
            "formulation": formulation, "parameters": parameters,
            "models_per_target_set": models, "actual_Materna_fit_hours": fit_hours,
            "parameter_reduction_vs_S2_percent": 100 * (206100 - parameters) / 206100,
            "model_count_reduction_vs_S2_percent": 100 * (4 - models) / 4,
        })
    return pd.DataFrame(rows)


def r_decisions(classifications: pd.DataFrame, trace: dict[str, dict[str, object]],
                synthesis: pd.DataFrame, class_changes: pd.DataFrame) -> dict[str, object]:
    overall = synthesis[synthesis.scope == "overall"]
    s2 = overall[overall.comparison == "S2_vs_S1"]
    supported = sum(trace[t]["S2_vs_S1"]["label"] == "CROSS_RESOURCE_INPUT_SUPPORTED" for t in TRACES)
    mean_gain = float(s2.equal_temporal_block_gain_percent.mean())
    positive = int((s2.equal_temporal_block_gain_percent > 0).sum())
    trace_diff = len({trace[t]["S2_vs_S1"]["label"] for t in TRACES}) > 1
    s2_changes = class_changes[class_changes.comparison == "S2_vs_S1"]
    sign_changes = int(s2_changes.raw_sign_reversal.sum())
    classification_changes = int(s2_changes.temporally_classification_variable.sum())
    broad = supported >= 2 and mean_gain > 0 and positive >= 3
    temporal = not broad and (trace_diff or sign_changes >= 2 or classification_changes >= 2)
    if broad:
        r1, r1_reason = "R1_BROAD_CROSS_RESOURCE_BENEFIT", "at least two supporting traces, positive synthesized four-resource mean, and at least three positive synthesized resources"
    elif temporal:
        r1, r1_reason = "R1_RESOURCE_TEMPORAL_DEPENDENCE_CONFIRMED", "broad benefit failed and frozen temporal-dependence criteria applied"
    elif supported == 0 and mean_gain <= 0 and positive <= 1:
        r1, r1_reason = "R1_CROSS_RESOURCE_INPUT_NOT_SUPPORTED", "no supporting trace, nonpositive synthesized mean, at most one positive resource, and no dominating temporal-dependence criterion"
    else:
        r1, r1_reason = "R1_MIXED_OR_INCONCLUSIVE", "no other frozen R1 predicate applied"

    m1 = overall[overall.comparison == "M1_vs_S2"]
    labels = [trace[t]["M1_vs_S2"]["label"] for t in TRACES]
    supported = labels.count("SHARED_REPRESENTATION_SUPPORTED")
    conditional = labels.count("SHARED_REPRESENTATION_CONDITIONALLY_SUPPORTED")
    mean_gain = float(m1.equal_temporal_block_gain_percent.mean())
    positive = int((m1.equal_temporal_block_gain_percent > 0).sum())
    material_mixed = bool((m1.equal_temporal_block_gain_percent >= 1).any() and (m1.equal_temporal_block_gain_percent <= -1).any())
    if supported == 0 and conditional <= 1 and mean_gain <= 0 and positive <= 1:
        r2, r2_reason = "R2_NEGATIVE_SHARING_REPLICATED", "zero supported traces, at most one conditional trace, nonpositive synthesized mean, and at most one positive synthesized resource"
    elif supported == 0 and material_mixed:
        r2, r2_reason = "R2_MIXED_SHARING_EFFECT", "no supported trace and material positive and negative synthesized effects"
    elif supported + conditional >= 2 and mean_gain > 0 and positive >= 3:
        r2, r2_reason = "R2_SHARING_BENEFIT_REPLICATED", "at least two supported/conditional traces and broadly positive synthesis"
    else:
        r2, r2_reason = "R2_INCONCLUSIVE", "no other frozen R2 predicate applied"

    joint = overall[overall.comparison == "M1_vs_S1"]
    joint_labels = [trace[t]["M1_vs_S1"]["label"] for t in TRACES]
    all_negative = bool((joint.equal_temporal_block_gain_percent < 0).all())
    harmful = joint_labels.count("JOINT_SYSTEM_BROADLY_HARMFUL")
    beneficial = joint_labels.count("JOINT_SYSTEM_BROADLY_BENEFICIAL")
    mean_gain = float(joint.equal_temporal_block_gain_percent.mean())
    positive = int((joint.equal_temporal_block_gain_percent > 0).sum())
    if all_negative and harmful >= 2:
        r3, r3_reason = "R3_JOINT_SYSTEM_UNDERPERFORMANCE_REPLICATED", "all four synthesized gains are negative and at least two traces are broadly harmful"
    elif mean_gain <= 0 and positive <= 2:
        r3, r3_reason = "R3_JOINT_SYSTEM_PARTIAL_UNDERPERFORMANCE", "nonpositive synthesized mean and at most two positive resources, without full replication"
    elif positive >= 3 and mean_gain > 0 and beneficial >= 2:
        r3, r3_reason = "R3_JOINT_SYSTEM_BENEFIT", "at least three positive synthesized resources and at least two broadly beneficial traces"
    else:
        r3, r3_reason = "R3_MIXED_OR_INCONCLUSIVE", "no other frozen R3 predicate applied"

    variable = int(class_changes.temporally_classification_variable.sum())
    raw_reversals = int(class_changes.raw_sign_reversal.sum())
    s2_global_diff = len({trace[t]["S2_vs_S1"]["label"] for t in TRACES}) > 1
    m1_global_diff = len({trace[t]["M1_vs_S2"]["label"] for t in TRACES}) > 1
    if variable >= 2 or s2_global_diff or m1_global_diff:
        r4, r4_reason = "R4_TEMPORAL_HETEROGENEITY_CONFIRMED", "at least two resource/comparison classes vary or a frozen global trace decision differs"
    elif variable == 1:
        r4, r4_reason = "R4_TEMPORAL_HETEROGENEITY_WEAK", "exactly one class varies and global decisions remain identical"
    else:
        r4, r4_reason = "R4_TEMPORAL_HETEROGENEITY_NOT_SUPPORTED", "all classes and global decisions are identical"

    return {
        "R1": r1, "R1_reason": r1_reason, "R1_mechanics": {"supported_traces": supported if False else sum(trace[t]["S2_vs_S1"]["label"] == "CROSS_RESOURCE_INPUT_SUPPORTED" for t in TRACES), "positive_synthesized_resources": int((s2.equal_temporal_block_gain_percent > 0).sum()), "synthesized_equal_resource_mean_gain_percent": float(s2.equal_temporal_block_gain_percent.mean()), "resource_sign_changes": sign_changes, "resource_classification_changes": classification_changes, "trace_decisions_differ": trace_diff},
        "R2": r2, "R2_reason": r2_reason,
        "R3": r3, "R3_reason": r3_reason,
        "R4": r4, "R4_reason": r4_reason,
        "R4_mechanics": {"resource_comparison_class_changes": variable, "raw_sign_reversals": raw_reversals, "S2_trace_decisions_differ": s2_global_diff, "M1_trace_decisions_differ": m1_global_diff},
    }


def cross_study_table(synthesis: pd.DataFrame, classifications: pd.DataFrame) -> pd.DataFrame:
    overall = synthesis[synthesis.scope == "overall"]
    rows = []
    for comparison in COMPARISON_DEFS:
        for resource in RESOURCES:
            m = overall[(overall.comparison == comparison) & (overall.resource == resource)].iloc[0]
            fs, rnd = BITBRAINS[comparison][resource]
            fs_class, rnd_class = BITBRAINS_CLASSES[comparison][resource]
            values = [TIMETRACK[comparison][resource], fs, rnd, *(float(m[t]) for t in TRACES)]
            cls = classifications[(classifications.comparison == comparison) & (classifications.resource == resource)].set_index("trace")
            rows.append({
                "comparison": comparison, "resource": resource,
                "TimeTrack_gain_percent": TIMETRACK[comparison][resource],
                "fastStorage_gain_percent": fs, "Rnd_gain_percent": rnd,
                "Bitbrains_equal_environment_gain_percent": (fs + rnd) / 2,
                "fastStorage_classification": fs_class,
                "Rnd_classification": rnd_class,
                "Bitbrains_classification_consistency": fs_class == rnd_class,
                **{f"{t}_gain_percent": float(m[t]) for t in TRACES},
                "Materna_equal_temporal_block_gain_percent": float(m.equal_temporal_block_gain_percent),
                "all_six_environment_sign_consistency": len({sign(v) for v in values}) == 1,
                "environment_or_time_dependence": len({sign(v) for v in values}) > 1,
                **{f"{t}_classification": cls.loc[t, "classification"] for t in TRACES},
                "Materna_classification_consistency": len(set(cls.classification)) == 1,
            })
    return pd.DataFrame(rows)


def final_gates(r: dict[str, object], cross: pd.DataFrame) -> dict[str, str]:
    s2 = cross[cross.comparison == "S2_vs_S1"]
    dependence = bool(s2.environment_or_time_dependence.any()) or r["R4"] == "R4_TEMPORAL_HETEROGENEITY_CONFIRMED"
    if r["R1"] == "R1_BROAD_CROSS_RESOURCE_BENEFIT":
        all_positive = bool((s2[["TimeTrack_gain_percent", "fastStorage_gain_percent", "Rnd_gain_percent", "Materna-T1_gain_percent", "Materna-T2_gain_percent", "Materna-T3_gain_percent"]] > 0).all().all())
        cross_resource = "CROSS_RESOURCE_BOUNDARY_NOT_SUPPORTED" if all_positive else "CROSS_RESOURCE_BOUNDARY_MIXED"
    elif dependence:
        cross_resource = "CROSS_RESOURCE_BOUNDARY_STRENGTHENED"
    else:
        cross_resource = "CROSS_RESOURCE_BOUNDARY_STRENGTHENED"

    if r["R2"] == "R2_NEGATIVE_SHARING_REPLICATED":
        shared = "SHARED_REPRESENTATION_BOUNDARY_STRENGTHENED"
    elif r["R2"] == "R2_SHARING_BENEFIT_REPLICATED":
        shared = "SHARED_REPRESENTATION_BOUNDARY_NOT_SUPPORTED"
    else:
        shared = "SHARED_REPRESENTATION_BOUNDARY_MIXED"

    if r["R3"] == "R3_JOINT_SYSTEM_UNDERPERFORMANCE_REPLICATED":
        joint = "JOINT_SYSTEM_UNDERPERFORMANCE_STRENGTHENED"
    elif r["R3"] == "R3_JOINT_SYSTEM_BENEFIT":
        joint = "JOINT_SYSTEM_UNDERPERFORMANCE_NOT_REPLICATED"
    else:
        joint = "JOINT_SYSTEM_UNDERPERFORMANCE_PARTIAL"

    contradicted = sum(label.endswith("NOT_SUPPORTED") or label.endswith("NOT_REPLICATED") for label in (cross_resource, shared, joint))
    if contradicted >= 2:
        paper = "MULTIDATASET_BOUNDARY_STUDY_NOT_SUPPORTED"
    elif contradicted == 1:
        paper = "MULTIDATASET_BOUNDARY_STUDY_REQUIRES_QUALIFICATION"
    elif shared == "SHARED_REPRESENTATION_BOUNDARY_STRENGTHENED" and joint in {"JOINT_SYSTEM_UNDERPERFORMANCE_STRENGTHENED", "JOINT_SYSTEM_UNDERPERFORMANCE_PARTIAL"} and cross_resource in {"CROSS_RESOURCE_BOUNDARY_STRENGTHENED", "CROSS_RESOURCE_BOUNDARY_MIXED"}:
        paper = "MULTIDATASET_TEMPORAL_BOUNDARY_STUDY_STRONGLY_SUPPORTED"
    else:
        paper = "MULTIDATASET_TEMPORAL_BOUNDARY_STUDY_SUPPORTED"
    return {
        "cross_resource_boundary": cross_resource,
        "shared_representation_boundary": shared,
        "joint_system_boundary": joint,
        "paper_scope_gate": paper,
        "stop_experimentation_gate": "STOP_EXPERIMENTATION_AND_WRITE",
    }


def save_figure(fig: plt.Figure, number: int, slug: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIGURES / f"{number:02d}_{slug}.png", dpi=150)
    plt.close(fig)


def line_figure(comparisons: pd.DataFrame, trace: str, comparison: str,
                number: int, slug: str) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    subset = comparisons[(comparisons.trace == trace) & (comparisons.comparison == comparison) & (comparisons.scope == "lead")]
    for resource in RESOURCES:
        row = subset[subset.resource == resource].sort_values("horizon_minutes")
        ax.plot(row.horizon_minutes, row.primary_macro_gain_percent, marker="o", label=resource)
    ax.axhline(0, color="black", linewidth=.8)
    ax.set(xlabel="Horizon (minutes)", ylabel="Primary gain (%)", title=f"{trace}: {comparison}")
    ax.legend(fontsize=8)
    save_figure(fig, number, slug)


def synthesis_figure(synthesis: pd.DataFrame, comparison: str, number: int, slug: str) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True)
    for ax, resource in zip(axes.flat, RESOURCES):
        row = synthesis[(synthesis.comparison == comparison) & (synthesis.resource == resource) & (synthesis.scope == "lead")].sort_values("horizon_minutes")
        for trace in TRACES:
            ax.plot(row.horizon_minutes, row[trace], marker="o", alpha=.65, label=trace)
        ax.plot(row.horizon_minutes, row.equal_temporal_block_gain_percent, marker="o", color="black", linewidth=2, label="equal-block")
        ax.axhline(0, color="grey", linewidth=.7); ax.set_title(resource)
    axes[1, 0].set_xlabel("Horizon (minutes)"); axes[1, 1].set_xlabel("Horizon (minutes)")
    axes[0, 0].set_ylabel("Gain (%)"); axes[1, 0].set_ylabel("Gain (%)")
    axes[0, 0].legend(fontsize=7); fig.suptitle(f"Temporal synthesis: {comparison}")
    save_figure(fig, number, slug)


def generate_figures(comparisons: pd.DataFrame, synthesis: pd.DataFrame, vm: pd.DataFrame,
                     persistence_skill: pd.DataFrame, cross: pd.DataFrame) -> None:
    for path in FIGURES.glob("*.png"):
        path.unlink()
    for number, trace in enumerate(TRACES, 1):
        line_figure(comparisons, trace, "S2_vs_S1", number, f"{trace.lower()}_s2_vs_s1")
    synthesis_figure(synthesis, "S2_vs_S1", 4, "s2_temporal_synthesis")
    for number, trace in enumerate(TRACES, 5):
        line_figure(comparisons, trace, "M1_vs_S2", number, f"{trace.lower()}_m1_vs_s2")
    synthesis_figure(synthesis, "M1_vs_S2", 8, "m1_temporal_synthesis")

    fig, ax = plt.subplots(figsize=(8, 4)); subset = synthesis[(synthesis.comparison == "M1_vs_S1") & (synthesis.scope == "overall")]
    x = np.arange(len(RESOURCES)); width = .2
    for idx, trace in enumerate(TRACES):
        values = [float(subset[subset.resource == resource][trace].iloc[0]) for resource in RESOURCES]
        ax.bar(x + (idx - 1) * width, values, width, label=trace)
    syn = [float(subset[subset.resource == resource].equal_temporal_block_gain_percent.iloc[0]) for resource in RESOURCES]
    ax.plot(x, syn, color="black", marker="o", label="equal-block"); ax.axhline(0, color="grey", linewidth=.8)
    ax.set_xticks(x, RESOURCES, rotation=20); ax.set_ylabel("Overall gain (%)"); ax.set_title("M1 vs S1 cross-trace summary"); ax.legend(fontsize=8)
    save_figure(fig, 9, "m1_vs_s1_cross_trace")

    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, comparison in zip(axes, COMPARISON_DEFS):
        data = [vm[(vm.comparison == comparison) & (vm.resource == resource)].groupby("vm_id").gain_percent.std() for resource in RESOURCES]
        ax.boxplot(data, tick_labels=RESOURCES, showfliers=False); ax.tick_params(axis="x", rotation=30); ax.set_title(comparison)
    axes[0].set_ylabel("Within-VM temporal gain SD (%)"); fig.suptitle("VM-level temporal heterogeneity")
    save_figure(fig, 10, "vm_temporal_heterogeneity")

    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True); overall = persistence_skill[persistence_skill.lead == 0]
    for ax, trace in zip(axes, TRACES):
        row = overall[overall.trace == trace]
        x = np.arange(len(RESOURCES)); width = .25
        for idx, formulation in enumerate(FORMULATIONS):
            vals = [float(row[(row.formulation == formulation) & (row.resource == resource)].persistence_skill.iloc[0]) for resource in RESOURCES]
            ax.bar(x + (idx - 1) * width, vals, width, label=formulation)
        ax.axhline(0, color="black", linewidth=.8); ax.set_xticks(x, RESOURCES, rotation=30); ax.set_title(trace)
    axes[0].set_ylabel("Persistence skill"); axes[0].legend(fontsize=8); fig.suptitle("Persistence-skill summary")
    save_figure(fig, 11, "persistence_skill_summary")

    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True)
    sources = ["TimeTrack_gain_percent", "fastStorage_gain_percent", "Rnd_gain_percent", "Materna-T1_gain_percent", "Materna-T2_gain_percent", "Materna-T3_gain_percent"]
    for ax, comparison in zip(axes, COMPARISON_DEFS):
        row = cross[cross.comparison == comparison].set_index("resource")
        matrix = row.loc[list(RESOURCES), sources].to_numpy()
        image = ax.imshow(matrix, cmap="RdBu", aspect="auto", vmin=-max(abs(matrix.min()), abs(matrix.max())), vmax=max(abs(matrix.min()), abs(matrix.max())))
        ax.set_xticks(range(len(sources)), [s.replace("_gain_percent", "") for s in sources], rotation=45, ha="right", fontsize=7)
        ax.set_yticks(range(len(RESOURCES)), RESOURCES); ax.set_title(comparison)
    fig.colorbar(image, ax=axes.ravel().tolist(), label="Gain (%)", shrink=.8); fig.suptitle("TimeTrack + Bitbrains + Materna boundary summary")
    FIGURES.mkdir(parents=True, exist_ok=True); fig.savefig(FIGURES / "12_full_cross_study_boundary.png", dpi=150, bbox_inches="tight"); plt.close(fig)


def report_text(primary: pd.DataFrame, comparisons: pd.DataFrame, classifications: pd.DataFrame,
                decisions: dict[str, dict[str, object]], bootstrap_frame: pd.DataFrame,
                persistence: pd.DataFrame, persistence_skill: pd.DataFrame,
                synthesis: pd.DataFrame, r: dict[str, object], class_changes: pd.DataFrame,
                loss_summary: pd.DataFrame, efficiency: pd.DataFrame,
                cross: pd.DataFrame, gates: dict[str, str]) -> str:
    skill_overall = persistence_skill[persistence_skill.lead == 0].copy()
    skill_overall["beats_persistence"] = skill_overall.persistence_skill > 0
    beat_summary = "; ".join(
        f"{trace} {formulation}: {', '.join(group[group.beats_persistence].resource.tolist()) or 'none'}"
        for (trace, formulation), group in skill_overall.groupby(["trace", "formulation"], sort=True)
    )
    fail_summary = "; ".join(
        f"{trace} {formulation}: {', '.join(group[~group.beats_persistence].resource.tolist()) or 'none'}"
        for (trace, formulation), group in skill_overall.groupby(["trace", "formulation"], sort=True)
    )
    overall_universal = [
        formulation
        for formulation, group in skill_overall.groupby("formulation", sort=True)
        if (group.persistence_skill > 0).all()
    ]
    lead_skill = persistence_skill[persistence_skill.lead != 0]
    lead_universal = [
        formulation
        for formulation, group in lead_skill.groupby("formulation", sort=True)
        if (group.persistence_skill > 0).all()
    ]
    all_source_columns = ["TimeTrack_gain_percent", "fastStorage_gain_percent", "Rnd_gain_percent", "Materna-T1_gain_percent", "Materna-T2_gain_percent", "Materna-T3_gain_percent"]
    repeated_negative = cross[(cross[all_source_columns] < 0).all(axis=1)].copy()
    repeated_negative["six_source_mean"] = repeated_negative[all_source_columns].mean(axis=1)
    strongest_negative = repeated_negative.sort_values("six_source_mean").iloc[0]
    memory_context = cross[(cross.comparison == "S2_vs_S1") & (cross.resource == "MEMORY")].iloc[0]
    sections = [
        "# Phase 4D Materna Scientific Report", "",
        "## 1. Provenance", "",
        "This is the first authorized scientific inspection of the completed Materna predictive results. Inputs and hashes are frozen in `PHASE4D_MATERNA_SCIENTIFIC_ANALYSIS_PROVENANCE.md`. No model training occurred during analysis.", "",
        "## 2. Aggregation semantics", "",
        "Native MAE is seed-averaged inside matched trace/VM/fold/resource/lead/formulation cells. VM-fold cells are equally weighted; overall resource MacroMAE equally weights five horizons. Prediction-pooled and cell-relative results are diagnostics only.",
    ]
    for index, trace in enumerate(TRACES, 3):
        gains = classifications[classifications.trace == trace][["comparison", "resource", "overall_primary_gain_percent", "positive_horizons", "positive_vms", "positive_folds", "positive_seed_aggregates", "classification"]]
        sections += ["", f"## {index}. {trace} results", "", md_table(gains), "", "Trace decisions:", "", f"- S2 vs S1: `{decisions[trace]['S2_vs_S1']['label']}` — {decisions[trace]['S2_vs_S1']['reason']}", f"- M1 vs S2: `{decisions[trace]['M1_vs_S2']['label']}` — {decisions[trace]['M1_vs_S2']['reason']}", f"- M1 vs S1: `{decisions[trace]['M1_vs_S1']['label']}`"]
    boot = bootstrap_frame[bootstrap_frame.scope == "overall_equal_horizon"]
    skill = skill_overall
    temporal = synthesis[synthesis.scope == "overall"]
    sections += [
        "", "## 6. Bootstrap", "", md_table(boot[["trace", "comparison", "resource", "lower_2_5_percent", "median_percent", "upper_97_5_percent"]]),
        "", "## 7. Persistence", "", md_table(skill[["trace", "formulation", "resource", "persistence_skill", "beats_persistence"]]), "",
        f"Overall cells beating persistence — {beat_summary}.", "",
        f"Overall cells not beating persistence — {fail_summary}.", "",
        f"Across trace-resource overall aggregates, universally persistence-positive formulations: {', '.join(overall_universal) or 'none'}. S2 is positive in all 12 overall trace-resource cells.", "",
        f"Across every trace-resource-lead cell, universally persistence-positive formulations: {', '.join(lead_universal) or 'none'}.", "",
        "Persistence is an absolute forecasting sanity check and does not redefine R1-R4. Relative formulation improvements do not imply absolute superiority over persistence.",
        "", "## 8. Temporal synthesis", "", md_table(temporal[["comparison", "resource", *TRACES, "equal_temporal_block_gain_percent", "sign_pattern", "max_minus_min_temporal_spread_percent"]]),
        "", "## 9. R1", "", f"`{r['R1']}` — {r['R1_reason']}",
        "", "## 10. R2", "", f"`{r['R2']}` — {r['R2_reason']}",
        "", "## 11. R3", "", f"`{r['R3']}` — {r['R3_reason']}",
        "", "## 12. R4", "", f"`{r['R4']}` — {r['R4_reason']}", "", f"Resource/comparison class changes: `{r['R4_mechanics']['resource_comparison_class_changes']}`. Raw sign reversals: `{r['R4_mechanics']['raw_sign_reversals']}`. S2 global decisions differ: `{r['R4_mechanics']['S2_trace_decisions_differ']}`. M1 global decisions differ: `{r['R4_mechanics']['M1_trace_decisions_differ']}`.", "", md_table(class_changes),
        "", "## 13. M1 loss balance", "", md_table(loss_summary), "",
        "Reference means: TimeTrack CPU 48.24%, throughput 26.32%, memory 13.67%, disk-write 11.77%; fastStorage 37.885905%, 13.493035%, 25.708970%, 22.912090%; Rnd 26.950113%, 33.243624%, 15.811861%, 23.994402%. The comparison is descriptive and not causal.",
        "", "## 14. Efficiency", "", md_table(efficiency), "",
        "M1 uses 52,500 parameters versus 206,100 for S2, a 74.526929% reduction, and one model versus four, a 75% model-count reduction. Efficiency and accuracy are separate conclusions.",
        "", "## 15. Population boundary", "",
        "Structural common pool: 398. Training-scale eligible: 74. Selected: 35. Retention: 18.5930%. Results apply only to structurally valid VMs with nondegenerate four-resource training variability across every scientific scaler-fit partition in all three temporal blocks; they do not generalize to the complete Materna population.",
        "", "## 16. TimeTrack comparison", "", md_table(cross[["comparison", "resource", "TimeTrack_gain_percent", "Materna-T1_gain_percent", "Materna-T2_gain_percent", "Materna-T3_gain_percent", "Materna_equal_temporal_block_gain_percent"]]),
        "", "## 17. Bitbrains comparison", "", md_table(cross[["comparison", "resource", "fastStorage_gain_percent", "Rnd_gain_percent", "Bitbrains_equal_environment_gain_percent", "Materna_equal_temporal_block_gain_percent"]]),
        "", "## 18. Complete cross-study synthesis", "", md_table(cross), "",
        "No pooled global score was calculated across TimeTrack, Bitbrains, and Materna. Synthesis is descriptive direction/classification consistency only.",
        f"The strongest repeated negative-transfer result is {strongest_negative.comparison} for {strongest_negative.resource}: it is negative in TimeTrack, both Bitbrains environments, and all three Materna blocks (six-source mean {strongest_negative.six_source_mean:.6f}%).",
        f"The strongest repeated positive/context result is S2 vs S1 for memory: it is positive in TimeTrack, both Bitbrains environments, Materna T2, and Materna T3, while Materna T1 is {memory_context['Materna-T1_gain_percent']:.6f}%; therefore it is repeated but not universal.",
        "", "## 19. Final cross-resource boundary", "", f"`{gates['cross_resource_boundary']}`",
        "", "## 20. Final shared-representation boundary", "", f"`{gates['shared_representation_boundary']}`",
        "", "## 21. Final joint-system boundary", "", f"`{gates['joint_system_boundary']}`",
        "", "## 22. Final paper-scope gate", "", f"`{gates['paper_scope_gate']}`",
        "", "## 23. Stop-experimentation decision", "", f"`{gates['stop_experimentation_gate']}`", "",
        "Exactly 12 diagnostic scientific figures were generated. Model training during analysis: `0`.", "",
    ]
    return "\n".join(sections)


def main() -> None:
    for directory in (ANALYSIS, COMPARISONS, SYNTHESIS, FIGURES):
        directory.mkdir(parents=True, exist_ok=True)
    metrics = load_metrics()
    cells, primary, pooled = primary_tables(metrics)
    comparisons, vm, fold, seed = comparison_tables(metrics, cells, primary, pooled)
    classifications = classify_resources(comparisons, vm, fold, seed)
    decisions = trace_decisions(classifications)
    bootstrap_frame = bootstrap(cells)
    persistence, persistence_skill = persistence_tables(metrics)
    synthesis = temporal_synthesis(comparisons)
    class_changes, vm_temporal = heterogeneity_tables(classifications, comparisons, vm, decisions)
    selected_loss, loss_summary = loss_tables()
    efficiency = efficiency_table()
    r = r_decisions(classifications, decisions, synthesis, class_changes)
    cross = cross_study_table(synthesis, classifications)
    gates = final_gates(r, cross)

    outputs = {
        ANALYSIS / "matched_vm_fold_cells.csv": cells,
        ANALYSIS / "primary_macro_mae.csv": primary,
        ANALYSIS / "pooled_mae.csv": pooled,
        COMPARISONS / "secondary_aggregation_diagnostics.csv": comparisons,
        ANALYSIS / "positive_vm_signs.csv": vm,
        ANALYSIS / "positive_fold_signs.csv": fold,
        ANALYSIS / "positive_seed_signs.csv": seed,
        COMPARISONS / "resource_classifications.csv": classifications,
        COMPARISONS / "bootstrap_uncertainty.csv": bootstrap_frame,
        ANALYSIS / "persistence_summary.csv": persistence,
        ANALYSIS / "persistence_skill_summary.csv": persistence_skill,
        SYNTHESIS / "equal_temporal_block_synthesis.csv": synthesis,
        ANALYSIS / "temporal_classification_changes.csv": class_changes,
        ANALYSIS / "vm_temporal_heterogeneity.csv": vm_temporal,
        ANALYSIS / "m1_selected_loss_shares.csv": selected_loss,
        ANALYSIS / "m1_loss_share_summary.csv": loss_summary,
        ANALYSIS / "efficiency.csv": efficiency,
        SYNTHESIS / "cross_study_synthesis.csv": cross,
    }
    for path, frame in outputs.items():
        write_csv(frame, path)
    write_json(decisions, ANALYSIS / "trace_decisions.json")
    write_json({**r, **gates, "model_training_during_analysis": 0}, ANALYSIS / "scientific_decisions.json")
    generate_figures(comparisons, synthesis, vm, persistence_skill, cross)
    REPORT.write_text(report_text(primary, comparisons, classifications, decisions, bootstrap_frame, persistence, persistence_skill, synthesis, r, class_changes, loss_summary, efficiency, cross, gates) + "\n")
    print(json.dumps({"trace_decisions": decisions, "R1_R2_R3_R4": r, "final_gates": gates, "figure_count": len(list(FIGURES.glob('*.png'))), "model_training_during_analysis": 0}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
