#!/usr/bin/env python3
"""Frozen, no-training scientific analysis for Phase 4C V2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parent
OUT = BASE / "outputs/scientific_v2"
COMPARISONS = OUT / "comparisons"
SYNTHESIS = OUT / "synthesis"
ANALYSIS = OUT / "analysis"
FIGURES = OUT / "figures"
REPORT = BASE / "PHASE4C_V2_EXTERNAL_CONFIRMATION_REPORT.md"
ENVIRONMENTS = ("fastStorage", "Rnd")
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
TIMETRACK = {
    "S2_vs_S1": {"CPU": -3.3130, "THROUGHPUT": -0.2428, "MEMORY": 0.8594, "DISK_WRITE": -0.4923},
    "M1_vs_S2": {"CPU": 0.4696, "THROUGHPUT": -0.8401, "MEMORY": -18.4769, "DISK_WRITE": -0.7956},
    "M1_vs_S1": {"CPU": -2.8279, "THROUGHPUT": -1.0849, "MEMORY": -17.4587, "DISK_WRITE": -1.2918},
}


def gain(reference: np.ndarray | float, candidate: np.ndarray | float) -> np.ndarray | float:
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
        values[column] = values[column].map(lambda value: f"{value:.4f}")
    header = "| " + " | ".join(map(str, values.columns)) + " |"
    divider = "|" + "|".join("---" for _ in values.columns) + "|"
    rows = ["| " + " | ".join(map(str, row)) + " |" for row in values.itertuples(index=False, name=None)]
    return "\n".join([header, divider, *rows])


def load_metrics() -> pd.DataFrame:
    frames = []
    for environment in ENVIRONMENTS:
        frame = pd.read_parquet(OUT / environment / "metrics.parquet")
        frame["vm_id"] = frame["vm_id"].astype(str)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def primary_tables(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    keys = ["environment_key", "formulation", "resource", "lead", "horizon_minutes", "vm_id", "fold"]
    cells = metrics.groupby(keys, as_index=False, sort=True)["mae"].mean().rename(columns={"mae": "seed_mean_mae"})
    macro = cells.groupby(keys[:5], as_index=False, sort=True)["seed_mean_mae"].mean().rename(columns={"seed_mean_mae": "macro_mae"})
    macro["scope"] = "lead"
    overall = macro.groupby(["environment_key", "formulation", "resource"], as_index=False, sort=True)["macro_mae"].mean()
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


def comparison_tables(metrics: pd.DataFrame, cells: pd.DataFrame, primary: pd.DataFrame, pooled: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    all_rows = []
    vm_rows = []
    fold_rows = []
    seed_rows = []
    for environment in ENVIRONMENTS:
        for comparison, (reference, candidate) in COMPARISON_DEFS.items():
            environment_rows = []
            for resource in RESOURCES:
                for lead in (*LEADS, 0):
                    scope = "lead" if lead else "overall"
                    p = primary[(primary.environment_key == environment) & (primary.resource == resource)]
                    if lead:
                        p = p[(p.lead == lead) & (p.scope == "lead")]
                    else:
                        p = p[p.scope == "overall_equal_horizon"]
                    values = p.set_index("formulation").macro_mae
                    primary_gain = float(gain(values[reference], values[candidate]))

                    q = pooled[(pooled.environment_key == environment) & (pooled.resource == resource)]
                    q = q[(q.lead == lead)]
                    pool_values = q.set_index("formulation").pooled_mae
                    pooled_gain = float(gain(pool_values[reference], pool_values[candidate]))

                    c = cells[(cells.environment_key == environment) & (cells.resource == resource)]
                    if lead:
                        c = c[c.lead == lead]
                    else:
                        c = c.groupby(["formulation", "vm_id", "fold"], as_index=False).seed_mean_mae.mean()
                    pivot = c.pivot(index=["vm_id", "fold"], columns="formulation", values="seed_mean_mae")
                    relative = gain(pivot[reference], pivot[candidate])
                    row = {
                        "environment": environment,
                        "comparison": comparison,
                        "reference": reference,
                        "candidate": candidate,
                        "resource": resource,
                        "scope": scope,
                        "lead": lead,
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
                    }
                    environment_rows.append(row)
                    all_rows.append(row)

                base = cells[(cells.environment_key == environment) & (cells.resource == resource)]
                vm = base.groupby(["formulation", "vm_id"], as_index=False).seed_mean_mae.mean().pivot(index="vm_id", columns="formulation", values="seed_mean_mae")
                for vm_id, value in gain(vm[reference], vm[candidate]).items():
                    vm_rows.append({"environment": environment, "comparison": comparison, "resource": resource, "vm_id": vm_id, "gain_percent": value, "positive": value > 0})
                fold = base.groupby(["formulation", "fold"], as_index=False).seed_mean_mae.mean().pivot(index="fold", columns="formulation", values="seed_mean_mae")
                for fold_id, value in gain(fold[reference], fold[candidate]).items():
                    fold_rows.append({"environment": environment, "comparison": comparison, "resource": resource, "fold": fold_id, "gain_percent": value, "positive": value > 0})
                seed = metrics[(metrics.environment_key == environment) & (metrics.resource == resource)].groupby(
                    ["formulation", "seed"], as_index=False
                ).mae.mean().pivot(index="seed", columns="formulation", values="mae")
                for seed_id, value in gain(seed[reference], seed[candidate]).items():
                    seed_rows.append({"environment": environment, "comparison": comparison, "resource": resource, "seed": seed_id, "gain_percent": value, "positive": value > 0})

            write_csv(pd.DataFrame(environment_rows), COMPARISONS / f"{environment}_{comparison.lower()}.csv")
    return pd.DataFrame(all_rows), pd.DataFrame(vm_rows), pd.DataFrame(fold_rows), pd.DataFrame(seed_rows)


def classify_resources(comparisons: pd.DataFrame, vm: pd.DataFrame, fold: pd.DataFrame, seed: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for environment in ENVIRONMENTS:
        for comparison in COMPARISON_DEFS:
            for resource in RESOURCES:
                subset = comparisons[(comparisons.environment == environment) & (comparisons.comparison == comparison) & (comparisons.resource == resource)]
                overall_gain = float(subset[subset.scope == "overall"].primary_macro_gain_percent.iloc[0])
                positive_horizons = int((subset[subset.scope == "lead"].primary_macro_gain_percent > 0).sum())
                positive_vms = int(vm[(vm.environment == environment) & (vm.comparison == comparison) & (vm.resource == resource)].positive.sum())
                positive_folds = int(fold[(fold.environment == environment) & (fold.comparison == comparison) & (fold.resource == resource)].positive.sum())
                positive_seeds = int(seed[(seed.environment == environment) & (seed.comparison == comparison) & (seed.resource == resource)].positive.sum())
                if overall_gain >= 1 and positive_horizons >= 4 and positive_vms >= 25 and positive_folds >= 4 and positive_seeds >= 2:
                    label = "BROAD_POSITIVE"
                elif overall_gain > 0 and positive_horizons >= 3 and positive_vms >= 15 and positive_folds >= 3 and positive_seeds >= 2:
                    label = "CONDITIONALLY_POSITIVE"
                elif overall_gain <= -1 and positive_horizons <= 1 and positive_vms <= 10 and positive_folds <= 1 and positive_seeds <= 1:
                    label = "BROAD_NEGATIVE"
                else:
                    label = "NEUTRAL_OR_MIXED"
                rows.append({
                    "environment": environment, "comparison": comparison, "resource": resource,
                    "overall_primary_gain_percent": overall_gain, "positive_horizons": positive_horizons,
                    "positive_vms": positive_vms, "positive_folds": positive_folds,
                    "positive_seed_aggregates": positive_seeds, "classification": label,
                })
    return pd.DataFrame(rows)


def environment_decisions(classifications: pd.DataFrame) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    positive_labels = {"BROAD_POSITIVE", "CONDITIONALLY_POSITIVE"}
    for environment in ENVIRONMENTS:
        result[environment] = {}
        s2 = classifications[(classifications.environment == environment) & (classifications.comparison == "S2_vs_S1")]
        positive = int(s2.classification.isin(positive_labels).sum())
        negative = int((s2.classification == "BROAD_NEGATIVE").sum())
        mean_gain = float(s2.overall_primary_gain_percent.mean())
        if positive >= 3 and mean_gain > 0 and negative <= 1:
            label = "CROSS_RESOURCE_INPUT_SUPPORTED"
        elif (positive <= 1 and mean_gain <= 0) or negative >= 2:
            label = "CROSS_RESOURCE_INPUT_NOT_SUPPORTED"
        else:
            label = "CROSS_RESOURCE_INPUT_MIXED"
        result[environment]["S2_vs_S1"] = {"label": label, "positive_resources": positive, "broad_negative_resources": negative, "equal_resource_mean_gain_percent": mean_gain}

        m1 = classifications[(classifications.environment == environment) & (classifications.comparison == "M1_vs_S2")]
        positive = int(m1.classification.isin(positive_labels).sum())
        negative = int((m1.classification == "BROAD_NEGATIVE").sum())
        mean_gain = float(m1.overall_primary_gain_percent.mean())
        raw_positive = int((m1.overall_primary_gain_percent > 0).sum())
        strong_tradeoff = bool(m1.overall_primary_gain_percent.max() >= 1 and m1.overall_primary_gain_percent.min() <= -1)
        if raw_positive >= 1 and (negative >= 2 or strong_tradeoff):
            label = "SHARED_REPRESENTATION_NEGATIVE_TRANSFER"
            reason = "conservative overlap rule: positive target evidence coexists with at least two broad negatives or strong trade-offs"
        elif positive <= 1 and mean_gain <= 0:
            label = "SHARED_REPRESENTATION_NOT_SUPPORTED"
            reason = "at most one positive resource and nonpositive equal-resource mean"
        elif positive >= 3 and mean_gain > 0 and negative == 0:
            label = "SHARED_REPRESENTATION_SUPPORTED"
            reason = "full frozen support criteria"
        elif mean_gain > 0 and positive >= 2:
            label = "SHARED_REPRESENTATION_CONDITIONALLY_SUPPORTED"
            reason = "positive mean and at least two positive resources"
        else:
            label = "SHARED_REPRESENTATION_NOT_SUPPORTED"
            reason = "no frozen positive-sharing rule applies"
        result[environment]["M1_vs_S2"] = {"label": label, "positive_resources": positive, "raw_positive_resources": raw_positive, "broad_negative_resources": negative, "equal_resource_mean_gain_percent": mean_gain, "reason": reason}
    return result


def bootstrap(cells: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for environment in ENVIRONMENTS:
        vms = sorted(cells[cells.environment_key == environment].vm_id.unique())
        rng = np.random.default_rng(BOOTSTRAP_SEED)
        samples = rng.integers(0, len(vms), size=(BOOTSTRAP_REPLICATES, len(vms)))
        for comparison, (reference, candidate) in COMPARISON_DEFS.items():
            for resource in RESOURCES:
                for lead in (*LEADS, 0):
                    subset = cells[(cells.environment_key == environment) & (cells.resource == resource)]
                    if lead:
                        subset = subset[subset.lead == lead]
                    by_vm = subset.groupby(["formulation", "vm_id"], as_index=False).seed_mean_mae.mean().pivot(index="vm_id", columns="formulation", values="seed_mean_mae").reindex(vms)
                    ref_values = by_vm[reference].to_numpy()
                    cand_values = by_vm[candidate].to_numpy()
                    boot = gain(ref_values[samples].mean(axis=1), cand_values[samples].mean(axis=1))
                    rows.append({
                        "interval_label": "PROSPECTIVELY DEFINED EXTERNAL CONFIRMATION UNCERTAINTY INTERVALS",
                        "environment": environment, "comparison": comparison, "resource": resource,
                        "scope": "lead" if lead else "overall_equal_horizon", "lead": lead,
                        "horizon_minutes": HORIZONS.get(lead, 0), "replicates": BOOTSTRAP_REPLICATES,
                        "rng_seed": BOOTSTRAP_SEED, "lower_2_5_percent": float(np.percentile(boot, 2.5)),
                        "median_percent": float(np.percentile(boot, 50)), "upper_97_5_percent": float(np.percentile(boot, 97.5)),
                    })
    return pd.DataFrame(rows)


def persistence_tables(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    persistence_rows = []
    skill_rows = []
    for environment in ENVIRONMENTS:
        p = pd.read_parquet(OUT / environment / "persistence_metrics.parquet")
        p["vm_id"] = p.vm_id.astype(str)
        cell = p.groupby(["resource", "lead", "horizon_minutes", "vm_id", "fold"], as_index=False)[["mae", "rmse", "r2", "nmae"]].mean()
        summary = cell.groupby(["resource", "lead", "horizon_minutes"], as_index=False)[["mae", "rmse", "r2", "nmae"]].mean()
        summary.insert(0, "environment", environment)
        persistence_rows.append(summary)

        skill_cell = metrics[metrics.environment_key == environment].groupby(
            ["formulation", "resource", "lead", "horizon_minutes", "vm_id", "fold"], as_index=False
        ).persistence_skill.mean()
        skill = skill_cell.groupby(["formulation", "resource", "lead", "horizon_minutes"], as_index=False).persistence_skill.mean()
        skill.insert(0, "environment", environment)
        overall = skill.groupby(["environment", "formulation", "resource"], as_index=False).persistence_skill.mean()
        overall["lead"] = 0
        overall["horizon_minutes"] = 0
        skill_rows.append(pd.concat([skill, overall], ignore_index=True))
    return pd.concat(persistence_rows, ignore_index=True), pd.concat(skill_rows, ignore_index=True)


def loss_and_context_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    selected_loss_rows = []
    context_rows = []
    for environment in ENVIRONMENTS:
        epochs = pd.read_csv(OUT / environment / "selected_epochs.csv", dtype={"vm_id": str})
        selected = epochs[epochs.formulation == "M1"][["vm_id", "fold", "seed", "selected_L", "selected_epoch"]]
        history = pd.read_parquet(OUT / environment / "m1_resource_loss_history.parquet")
        history["vm_id"] = history.vm_id.astype(str)
        merged = history.merge(selected, left_on=["vm_id", "fold", "seed", "L", "epoch"], right_on=["vm_id", "fold", "seed", "selected_L", "selected_epoch"], how="inner")
        merged.insert(0, "environment_key", environment)
        selected_loss_rows.append(merged[["environment_key", "vm_id", "fold", "seed", "L", "epoch", "resource", "validation_loss_share"]])

        contexts = pd.read_csv(OUT / environment / "selected_contexts.csv", dtype={"vm_id": str})
        contexts["resource"] = contexts.resource.fillna("ALL")
        counts = contexts.groupby(["formulation", "resource", "selected_L"], as_index=False).size().rename(columns={"size": "count", "selected_L": "L"})
        counts.insert(0, "environment", environment)
        context_rows.append(counts)
    selected_loss = pd.concat(selected_loss_rows, ignore_index=True)
    loss_summary = selected_loss.groupby(["environment_key", "resource"]).validation_loss_share.agg(["mean", "median"]).reset_index()
    loss_summary["mean_percent"] = 100 * loss_summary["mean"]
    loss_summary["median_percent"] = 100 * loss_summary["median"]
    loss_summary = loss_summary.drop(columns=["mean", "median"])
    return selected_loss, loss_summary, pd.concat(context_rows, ignore_index=True)


def synthesis_table(comparisons: pd.DataFrame) -> pd.DataFrame:
    overall = comparisons[comparisons.scope == "overall"]
    lead = comparisons[comparisons.scope == "lead"]
    frame = pd.concat([lead, overall], ignore_index=True)
    pivot = frame.pivot_table(index=["comparison", "resource", "scope", "lead", "horizon_minutes"], columns="environment", values="primary_macro_gain_percent").reset_index()
    pivot["synthesized_gain_percent"] = (pivot.fastStorage + pivot.Rnd) / 2
    pivot["sign_agreement"] = [sign(a) == sign(b) for a, b in zip(pivot.fastStorage, pivot.Rnd)]
    pivot["absolute_environment_disagreement_percent"] = (pivot.fastStorage - pivot.Rnd).abs()
    return pivot


def heterogeneity_table(comparisons: pd.DataFrame, vm: pd.DataFrame, fold: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for environment in ENVIRONMENTS:
        for comparison in COMPARISON_DEFS:
            for resource in RESOURCES:
                v = vm[(vm.environment == environment) & (vm.comparison == comparison) & (vm.resource == resource)].gain_percent
                f = fold[(fold.environment == environment) & (fold.comparison == comparison) & (fold.resource == resource)].gain_percent
                l = comparisons[(comparisons.environment == environment) & (comparisons.comparison == comparison) & (comparisons.resource == resource) & (comparisons.scope == "lead")].primary_macro_gain_percent
                rows.append({
                    "environment": environment, "comparison": comparison, "resource": resource,
                    "positive_vm_fraction": float((v > 0).mean()), "positive_horizon_fraction": float((l > 0).mean()),
                    "positive_fold_fraction": float((f > 0).mean()), "vm_gain_iqr_percent": float(v.quantile(.75) - v.quantile(.25)),
                    "fold_gain_range_percent": float(f.max() - f.min()), "lead_gain_range_percent": float(l.max() - l.min()),
                })
    return pd.DataFrame(rows)


def scientific_decisions(classifications: pd.DataFrame, environment: dict[str, dict[str, object]], synthesis: pd.DataFrame, heterogeneity: pd.DataFrame) -> dict[str, object]:
    overall = synthesis[synthesis.scope == "overall"]
    h1_values = overall[overall.comparison == "S2_vs_S1"].synthesized_gain_percent
    h1_supported = any(environment[e]["S2_vs_S1"]["label"] == "CROSS_RESOURCE_INPUT_SUPPORTED" for e in ENVIRONMENTS)
    if not h1_supported and h1_values.mean() <= 0 and int((h1_values > 0).sum()) <= 1:
        h1 = "H1_BOUNDARY_CONFIRMED"
        h1_reason = "neither environment supported S2, synthesis mean was nonpositive, and no more than one resource was positive"
    elif not h1_supported:
        h1 = "H1_BOUNDARY_PARTIALLY_REPLICATED"
        h1_reason = "neither environment supported S2, but synthesized resource evidence remained mixed"
    else:
        h1 = "H1_BOUNDARY_NOT_REPLICATED"
        h1_reason = "at least one environment supported S2 and synthesis was broadly positive"

    h2_values = overall[overall.comparison == "M1_vs_S2"].synthesized_gain_percent
    h2_supported = any(environment[e]["M1_vs_S2"]["label"] == "SHARED_REPRESENTATION_SUPPORTED" for e in ENVIRONMENTS)
    if not h2_supported and h2_values.mean() <= 0 and int((h2_values > 0).sum()) <= 1:
        h2 = "H2_BOUNDARY_CONFIRMED"
        h2_reason = "neither environment supported M1 sharing, synthesis mean was nonpositive, and no more than one resource was positive"
    elif not h2_supported:
        h2 = "H2_BOUNDARY_PARTIALLY_REPLICATED"
        h2_reason = "neither environment fully supported M1, but synthesized evidence was mixed"
    else:
        h2 = "H2_BOUNDARY_NOT_REPLICATED"
        h2_reason = "at least one environment supported M1 and synthesis was broadly positive"

    cross_sign_disagreement = bool((~overall.sign_agreement).any())
    within_mixed = bool(((heterogeneity.positive_vm_fraction > 0) & (heterogeneity.positive_vm_fraction < 1)).any())
    broad_dominance = all(environment[e]["S2_vs_S1"]["label"] == "CROSS_RESOURCE_INPUT_SUPPORTED" for e in ENVIRONMENTS)
    h3 = "HETEROGENEITY_CONFIRMED" if (cross_sign_disagreement or within_mixed) and not broad_dominance else "HETEROGENEITY_WEAK_OR_MIXED"
    h3_reason = "predefined environment/resource/VM/lead/fold dimensions show sign or magnitude variation, without a broadly positive effect dominating both environments"

    s2_labels = {environment[e]["S2_vs_S1"]["label"] for e in ENVIRONMENTS}
    m1_labels = {environment[e]["M1_vs_S2"]["label"] for e in ENVIRONMENTS}
    materially_conflicting = ("CROSS_RESOURCE_INPUT_SUPPORTED" in s2_labels and "CROSS_RESOURCE_INPUT_NOT_SUPPORTED" in s2_labels) or ("SHARED_REPRESENTATION_SUPPORTED" in m1_labels and any("NOT_SUPPORTED" in value or "NEGATIVE_TRANSFER" in value for value in m1_labels))
    if h1 == "H1_BOUNDARY_CONFIRMED" and h2 == "H2_BOUNDARY_CONFIRMED" and h3 != "HETEROGENEITY_NOT_REPLICATED":
        final = "BOUNDARY_CONFIRMED_ACROSS_BOTH_ENVIRONMENTS"
    elif materially_conflicting:
        final = "ENVIRONMENT_DEPENDENT_BOUNDARY"
    elif h1 == "H1_BOUNDARY_NOT_REPLICATED" or h2 == "H2_BOUNDARY_NOT_REPLICATED":
        final = "EXTERNAL_EVIDENCE_CONTRADICTS_TIMETRACK_BOUNDARY"
    elif "PARTIALLY_REPLICATED" in h1 or "PARTIALLY_REPLICATED" in h2:
        final = "BOUNDARY_PARTIALLY_REPLICATED"
    else:
        final = "EXTERNAL_CONFIRMATION_INCONCLUSIVE"

    if final == "BOUNDARY_CONFIRMED_ACROSS_BOTH_ENVIRONMENTS":
        publication = "MULTIDATASET_BOUNDARY_STUDY_SUPPORTED"
    elif final in {"BOUNDARY_PARTIALLY_REPLICATED", "ENVIRONMENT_DEPENDENT_BOUNDARY"}:
        publication = "MULTIDATASET_BOUNDARY_STUDY_SUPPORTED_WITH_MIXED_REPLICATION"
    elif final == "EXTERNAL_EVIDENCE_CONTRADICTS_TIMETRACK_BOUNDARY":
        publication = "TIMETRACK_BOUNDARY_NOT_EXTERNALLY_SUPPORTED"
    else:
        publication = "EXTERNAL_RESULTS_INCONCLUSIVE"
    materna = "MATERNA_NEEDED_FOR_RESOLUTION" if materially_conflicting else ("MATERNA_USEFUL_SECONDARY_REPLICATION" if h3 == "HETEROGENEITY_CONFIRMED" else "MATERNA_NOT_NEEDED")
    return {
        "H1": h1, "H1_reason": h1_reason, "H2": h2, "H2_reason": h2_reason,
        "H3": h3, "H3_reason": h3_reason, "final_phase4c_outcome": final,
        "publication_scope_gate": publication, "materna_gate": materna,
        "new_architecture_gate": "NO", "new_architecture_reason": "external evidence does not reveal a stable replicated beneficial mechanism unavailable from TimeTrack; heterogeneity and negative naive-sharing results are not an architecture mandate",
        "model_training_during_analysis": 0,
    }


def timetrack_tables(comparisons: pd.DataFrame, synthesis: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    overall = comparisons[comparisons.scope == "overall"]
    synth = synthesis[synthesis.scope == "overall"]
    for comparison in COMPARISON_DEFS:
        for resource in RESOURCES:
            fs = float(overall[(overall.environment == "fastStorage") & (overall.comparison == comparison) & (overall.resource == resource)].primary_macro_gain_percent.iloc[0])
            rnd = float(overall[(overall.environment == "Rnd") & (overall.comparison == comparison) & (overall.resource == resource)].primary_macro_gain_percent.iloc[0])
            syn = float(synth[(synth.comparison == comparison) & (synth.resource == resource)].synthesized_gain_percent.iloc[0])
            tt = TIMETRACK[comparison][resource]
            rows.append({"comparison": comparison, "resource": resource, "TimeTrack_gain_percent": tt, "fastStorage_gain_percent": fs, "Rnd_gain_percent": rnd, "Bitbrains_equal_environment_gain_percent": syn, "all_three_sign_agreement": sign(tt) == sign(fs) == sign(rnd)})
    table = pd.DataFrame(rows)
    consistency = []
    for row in table.itertuples(index=False):
        values = [row.TimeTrack_gain_percent, row.fastStorage_gain_percent, row.Rnd_gain_percent]
        if all(value > 0 for value in values) and min(values) >= 1:
            label = "CONSISTENTLY_BENEFICIAL"
        elif all(value > 0 for value in values):
            label = "DIRECTIONALLY_POSITIVE_BUT_WEAK"
        elif all(value < 0 for value in values):
            label = "CONSISTENTLY_NEGATIVE"
        else:
            label = "INCONSISTENT_OR_ENVIRONMENT_DEPENDENT"
        consistency.append({"comparison": row.comparison, "resource": row.resource, "cross_dataset_consistency": label})
    return table, pd.DataFrame(consistency)


def efficiency_table(runtime: dict[str, object]) -> pd.DataFrame:
    parameter_rows = [
        {"formulation": "S1", "parameters": 203028, "models_per_target_set": 4},
        {"formulation": "S2", "parameters": 206100, "models_per_target_set": 4},
        {"formulation": "M1", "parameters": 52500, "models_per_target_set": 1},
    ]
    frame = pd.DataFrame(parameter_rows)
    frame["parameter_reduction_vs_S2_percent"] = 100 * (206100 - frame.parameters) / 206100
    frame["model_count_reduction_vs_S2_percent"] = 100 * (4 - frame.models_per_target_set) / 4
    fit_hours = {}
    for formulation in FORMULATIONS:
        fit_hours[formulation] = sum(
            runtime["environments"][environment]["stage_fit_runtime"][phase][formulation]["fit_hours"]
            for environment in ENVIRONMENTS for phase in ("inner", "final")
        )
    frame["combined_actual_fit_hours"] = frame.formulation.map(fit_hours)
    return frame


def save_figure(fig: plt.Figure, number: int, slug: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIGURES / f"{number:02d}_{slug}.png", dpi=150)
    plt.close(fig)


def generate_figures(comparisons: pd.DataFrame, synthesis: pd.DataFrame, vm: pd.DataFrame, persistence_skill: pd.DataFrame, loss_summary: pd.DataFrame, efficiency: pd.DataFrame, bootstrap_frame: pd.DataFrame) -> None:
    for path in FIGURES.glob("*.png"):
        path.unlink()
    specs = [(1, "fastStorage", "S2_vs_S1"), (2, "Rnd", "S2_vs_S1"), (3, "fastStorage", "M1_vs_S2"), (4, "Rnd", "M1_vs_S2")]
    for number, environment, comparison in specs:
        fig, ax = plt.subplots(figsize=(7, 4))
        subset = comparisons[(comparisons.environment == environment) & (comparisons.comparison == comparison) & (comparisons.scope == "lead")]
        for resource in RESOURCES:
            row = subset[subset.resource == resource].sort_values("horizon_minutes")
            ax.plot(row.horizon_minutes, row.primary_macro_gain_percent, marker="o", label=resource)
        ax.axhline(0, color="black", linewidth=.8); ax.set(xlabel="Horizon (minutes)", ylabel="Primary gain (%)", title=f"{environment}: {comparison}"); ax.legend(fontsize=8)
        save_figure(fig, number, f"{environment.lower()}_{comparison.lower()}_gain")
    for number, comparison in [(5, "S2_vs_S1"), (6, "M1_vs_S2")]:
        fig, ax = plt.subplots(figsize=(7, 4)); subset = synthesis[(synthesis.comparison == comparison) & (synthesis.scope == "lead")]
        for resource in RESOURCES:
            row = subset[subset.resource == resource].sort_values("horizon_minutes")
            ax.plot(row.horizon_minutes, row.synthesized_gain_percent, marker="o", label=resource)
        ax.axhline(0, color="black", linewidth=.8); ax.set(xlabel="Horizon (minutes)", ylabel="Equal-environment gain (%)", title=f"Synthesis: {comparison}"); ax.legend(fontsize=8)
        save_figure(fig, number, f"equal_environment_{comparison.lower()}")
    for number, comparison in [(7, "S2_vs_S1"), (8, "M1_vs_S2")]:
        fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
        for ax, environment in zip(axes, ENVIRONMENTS):
            data = [vm[(vm.environment == environment) & (vm.comparison == comparison) & (vm.resource == resource)].gain_percent for resource in RESOURCES]
            ax.boxplot(data, tick_labels=RESOURCES, showfliers=False); ax.axhline(0, color="black", linewidth=.8); ax.tick_params(axis="x", rotation=35); ax.set_title(environment)
        axes[0].set_ylabel("VM-level gain (%)"); fig.suptitle(f"VM heterogeneity: {comparison}")
        save_figure(fig, number, f"vm_heterogeneity_{comparison.lower()}")
    fig, ax = plt.subplots(figsize=(9, 4)); ps = persistence_skill[persistence_skill.lead == 0]
    labels=[]; values=[]
    for environment in ENVIRONMENTS:
        for formulation in FORMULATIONS:
            for resource in RESOURCES:
                labels.append(f"{environment[:2]}-{formulation}-{resource[:3]}")
                values.append(float(ps[(ps.environment == environment) & (ps.formulation == formulation) & (ps.resource == resource)].persistence_skill.iloc[0]))
    ax.bar(range(len(values)), values); ax.axhline(0,color="black",linewidth=.8); ax.set_xticks(range(len(labels)), labels, rotation=90, fontsize=6); ax.set_ylabel("Persistence skill"); ax.set_title("Persistence skill by formulation/resource/environment")
    save_figure(fig, 9, "persistence_skill")
    fig, ax = plt.subplots(figsize=(7, 4)); tt={"CPU":48.24,"THROUGHPUT":26.32,"MEMORY":13.67,"DISK_WRITE":11.77}; x=np.arange(4); width=.25
    ax.bar(x-width,[tt[r] for r in RESOURCES],width,label="TimeTrack")
    for offset, environment in [(0,"fastStorage"),(width,"Rnd")]:
        values=[float(loss_summary[(loss_summary.environment_key==environment)&(loss_summary.resource==r)].mean_percent.iloc[0]) for r in RESOURCES]
        ax.bar(x+offset,values,width,label=environment)
    ax.set_xticks(x,RESOURCES,rotation=25); ax.set_ylabel("Mean validation-loss share (%)"); ax.set_title("M1 loss-share comparison"); ax.legend(fontsize=8)
    save_figure(fig, 10, "m1_loss_share")
    fig, ax = plt.subplots(figsize=(6, 4)); x=efficiency.parameters; y=[]
    overall=comparisons[comparisons.scope=="overall"]
    for formulation in FORMULATIONS:
        if formulation=="S1": y.append(0.0)
        elif formulation=="S2": y.append(float(overall[overall.comparison=="S2_vs_S1"].primary_macro_gain_percent.mean()))
        else: y.append(float(overall[overall.comparison=="M1_vs_S1"].primary_macro_gain_percent.mean()))
    ax.scatter(x,y,s=80); [ax.annotate(f,(px,py)) for f,px,py in zip(FORMULATIONS,x,y)]; ax.axhline(0,color="black",linewidth=.8); ax.set(xlabel="Parameters",ylabel="Mean gain vs S1 (%)",title="Accuracy-efficiency diagnostic")
    save_figure(fig, 11, "accuracy_efficiency")
    fig, ax = plt.subplots(figsize=(8, 7)); bo=bootstrap_frame[bootstrap_frame.scope=="overall_equal_horizon"].copy(); bo["label"]=bo.environment+" "+bo.comparison+" "+bo.resource
    y=np.arange(len(bo)); ax.errorbar(bo.median_percent,y,xerr=[bo.median_percent-bo.lower_2_5_percent,bo.upper_97_5_percent-bo.median_percent],fmt="o",markersize=3); ax.axvline(0,color="black",linewidth=.8); ax.set_yticks(y,bo.label,fontsize=6); ax.set_xlabel("Bootstrap gain interval (%)"); ax.set_title("Prospectively defined overall uncertainty")
    save_figure(fig, 12, "bootstrap_uncertainty_summary")


def report_text(primary: pd.DataFrame, comparisons: pd.DataFrame, classifications: pd.DataFrame, environment: dict[str, dict[str, object]], bootstrap_frame: pd.DataFrame, persistence: pd.DataFrame, persistence_skill: pd.DataFrame, heterogeneity: pd.DataFrame, loss_summary: pd.DataFrame, contexts: pd.DataFrame, efficiency: pd.DataFrame, synthesis: pd.DataFrame, decisions: dict[str, object], timetrack: pd.DataFrame, consistency: pd.DataFrame) -> str:
    sections = [
        "# Phase 4C V2 Dual-Environment External Confirmation Report", "",
        "## 1. Analysis provenance", "",
        "Analysis used only the frozen compact metrics, persistence, selection, and M1 loss-history artifacts identified in `PHASE4C_V2_SCIENTIFIC_ANALYSIS_PROVENANCE.md`. Bootstrap seed: `20261007`; replicates: 10,000. No model training occurred.", "",
        "## 2. Primary aggregation semantics", "",
        "Native MAE was averaged across three seeds within each matched environment/VM/fold/resource/lead/formulation cell. VM-fold cells then received equal weight. Overall resource MacroMAE is the equal mean of the five lead-specific MacroMAEs. Pooled prediction-level MAE is secondary only.",
    ]
    for idx, environment_name in enumerate(ENVIRONMENTS, start=3):
        sections.extend(["", f"## {idx}. {environment_name}", ""])
        absolute = primary[(primary.environment_key == environment_name) & (primary.scope == "overall_equal_horizon")][["formulation", "resource", "macro_mae"]]
        sections.extend(["### Absolute overall MacroMAEs", "", md_table(absolute), ""])
        gains = classifications[classifications.environment == environment_name][["comparison", "resource", "overall_primary_gain_percent", "positive_horizons", "positive_vms", "positive_folds", "positive_seed_aggregates", "classification"]]
        sections.extend(["### Gains, classifications, and consistency", "", md_table(gains), "", "### Global decisions", "", f"- S2 vs S1: `{environment[environment_name]['S2_vs_S1']['label']}`", f"- M1 vs S2: `{environment[environment_name]['M1_vs_S2']['label']}` — {environment[environment_name]['M1_vs_S2']['reason']}"])
    bootstrap_overall = bootstrap_frame[bootstrap_frame.scope == "overall_equal_horizon"]
    skill_overall = persistence_skill[persistence_skill.lead == 0]
    synthesis_overall = synthesis[synthesis.scope == "overall"]
    sections.extend([
        "", "## 5. Secondary aggregation diagnostics", "",
        "Primary, pooled, mean/median cell-relative gains, positive-cell fractions, and explicit sign-reversal flags are preserved in the six comparison CSVs and `secondary_aggregation_diagnostics.csv`.",
        "", "## 6. Bootstrap uncertainty", "",
        "Intervals are prospectively defined paired VM-cluster percentile intervals and do not change classifications.", "",
        md_table(bootstrap_overall[["environment", "comparison", "resource", "lower_2_5_percent", "median_percent", "upper_97_5_percent"]]),
        "", "## 7. Persistence", "",
        "Persistence absolute metrics are reported per environment/resource/lead; model persistence skill is reported separately. Positive skill means the formulation beats persistence; nonpositive cells are retained as an absolute-forecasting warning.", "",
        md_table(persistence[["environment", "resource", "lead", "horizon_minutes", "mae", "rmse", "r2", "nmae"]]), "",
        md_table(skill_overall[["environment", "formulation", "resource", "persistence_skill"]]),
        "", "No formulation beats persistence across every resource. All three formulations have negative overall CPU persistence skill in both environments. All three also have negative throughput skill in fastStorage; in Rnd, S2 and M1 remain negative while S1 is only slightly positive. Memory and disk-write are positive for all formulations in both environments.",
        "", "## 8. Heterogeneity", "", md_table(heterogeneity), "",
        f"Frozen H3 label: `{decisions['H3']}`. {decisions['H3_reason']}",
        "", "## 9. M1 loss balance", "", md_table(loss_summary), "",
        "TimeTrack descriptive mean shares were CPU 48.24%, throughput 26.32%, memory 13.67%, and disk-write 11.77%. These differences are descriptive and not causal.",
        "", "## 10. Context selection", "", md_table(contexts), "",
        "Context selections are descriptive and are not causal evidence.",
        "", "## 11. Efficiency", "", md_table(efficiency), "",
        "M1 uses 52,500 parameters versus 206,100 for four S2 models, a 74.5269% reduction, and one model versus four, a 75% model-count reduction. Accuracy conclusions remain separate from efficiency.",
        "", "## 12. Population/generalizability restriction", "",
        "The confirmation population is restricted to structurally valid VMs with nondegenerate four-resource training variability in every scaler partition: fastStorage 596/916 and Rnd 272/416 were scale eligible. Approximately 35% were excluded in each environment for zero-IQR structure. Conclusions do not generalize to idle, quiescent, or resource-constant VMs.",
        "", "## 13. Equal-environment synthesis", "",
        "No weighting by VM count, origin count, prediction count, or duration was used.", "",
        md_table(synthesis_overall[["comparison", "resource", "fastStorage", "Rnd", "synthesized_gain_percent", "sign_agreement", "absolute_environment_disagreement_percent"]]),
        "", "## 14. H1", "", f"`{decisions['H1']}` — {decisions['H1_reason']}",
        "", "## 15. H2", "", f"`{decisions['H2']}` — {decisions['H2_reason']}",
        "", "## 16. H3", "", f"`{decisions['H3']}` — {decisions['H3_reason']}",
        "", "## 17. TimeTrack comparison", "", md_table(timetrack), "",
        "TimeTrack and Bitbrains remain separate evidence environments; no pooled cross-dataset score was calculated.",
        "", "## 18. Cross-dataset resource consistency", "", md_table(consistency),
        "", "## 19. Final Phase 4C outcome", "", f"`{decisions['final_phase4c_outcome']}`",
        "", "## 20. Publication-scope gate", "", f"`{decisions['publication_scope_gate']}`",
        "", "## 21. Materna gate", "", f"`{decisions['materna_gate']}`. Materna was not executed.",
        "", "## 22. New-architecture gate", "", f"`{decisions['new_architecture_gate']}` — {decisions['new_architecture_reason']}", "",
    ])
    return "\n".join(sections)


def main() -> None:
    for directory in (COMPARISONS, SYNTHESIS, ANALYSIS, FIGURES):
        directory.mkdir(parents=True, exist_ok=True)
    metrics = load_metrics()
    cells, primary, pooled = primary_tables(metrics)
    comparisons, vm, fold, seed = comparison_tables(metrics, cells, primary, pooled)
    classifications = classify_resources(comparisons, vm, fold, seed)
    environment = environment_decisions(classifications)
    bootstrap_frame = bootstrap(cells)
    persistence, persistence_skill = persistence_tables(metrics)
    selected_loss, loss_summary, contexts = loss_and_context_tables()
    synthesis = synthesis_table(comparisons)
    heterogeneity = heterogeneity_table(comparisons, vm, fold)
    decisions = scientific_decisions(classifications, environment, synthesis, heterogeneity)
    timetrack, consistency = timetrack_tables(comparisons, synthesis)
    runtime = json.loads((OUT / "runtime/combined_runtime_storage_accounting.json").read_text())
    efficiency = efficiency_table(runtime)

    outputs = {
        ANALYSIS / "primary_macro_mae.csv": primary,
        ANALYSIS / "pooled_mae.csv": pooled,
        ANALYSIS / "matched_vm_fold_cells.csv": cells,
        ANALYSIS / "positive_vm_signs.csv": vm,
        ANALYSIS / "positive_fold_signs.csv": fold,
        ANALYSIS / "positive_seed_signs.csv": seed,
        ANALYSIS / "positive_consistency_counts.csv": classifications.drop(columns=["classification"]),
        COMPARISONS / "secondary_aggregation_diagnostics.csv": comparisons,
        COMPARISONS / "resource_classifications.csv": classifications,
        COMPARISONS / "bootstrap_uncertainty.csv": bootstrap_frame,
        SYNTHESIS / "equal_environment_synthesis.csv": synthesis,
        ANALYSIS / "persistence_summary.csv": persistence,
        ANALYSIS / "persistence_skill_summary.csv": persistence_skill,
        ANALYSIS / "heterogeneity_summary.csv": heterogeneity,
        ANALYSIS / "m1_selected_loss_shares.csv": selected_loss,
        ANALYSIS / "m1_loss_share_summary.csv": loss_summary,
        ANALYSIS / "context_selection_distribution.csv": contexts,
        ANALYSIS / "efficiency.csv": efficiency,
        ANALYSIS / "timetrack_bitbrains_comparison.csv": timetrack,
        ANALYSIS / "cross_dataset_resource_consistency.csv": consistency,
    }
    for path, frame in outputs.items():
        write_csv(frame, path)
    write_json(environment, ANALYSIS / "environment_decisions.json")
    write_json(decisions, ANALYSIS / "scientific_decisions.json")
    generate_figures(comparisons, synthesis, vm, persistence_skill, loss_summary, efficiency, bootstrap_frame)
    REPORT.write_text(report_text(primary, comparisons, classifications, environment, bootstrap_frame, persistence, persistence_skill, heterogeneity, loss_summary, contexts, efficiency, synthesis, decisions, timetrack, consistency) + "\n")
    print(json.dumps({"environment_decisions": environment, "scientific_decisions": decisions, "figure_count": len(list(FIGURES.glob("*.png")))}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
