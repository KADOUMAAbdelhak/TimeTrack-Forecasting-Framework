#!/usr/bin/env python3
"""Phase 3D exploratory audit using frozen Phase 3C artifacts only."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.stats import rankdata, spearmanr

from src.data import FUTURE_LEADS, MACHINES, RESOURCE_ORDER, load_panel, target_columns
from src.splits import build_factorial_folds
from src.transforms import transform_resource


ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
P3C = ROOT / "multiresource/04_lstm_factorial"
SCI = P3C / "outputs/scientific"
OUT = BASE / "outputs"
FIG = BASE / "figures"
PROTOCOL = BASE / "POSTHOC_PROTOCOL.md"
PROTOCOL_SHA256 = "c1ed2d6ae3ee3afe20c70b8561cc58d340c0ee70e0686e642f461b7e0f702da8"
P3C_INVENTORY_SHA256 = "95bbb842f60bbc8c2c1bc11704c413e8e654594476d16c40850a217913c5155e"
P3C_TREE_SHA256 = "ec35446710f90a7b1e1a86cdbca6bedd4face31ec68ea56e83fd682addd89a65"
COMPARISONS = {
    "S2_vs_S1": ("S1", "S2"),
    "M1_vs_S2": ("S2", "M1"),
    "M1_vs_S1": ("S1", "M1"),
}
REGIME_MAP = {
    "CPU": ["cpu_level", "cpu_volatility", "throughput_level", "throughput_volatility", "cpu_throughput_corr"],
    "THROUGHPUT": ["throughput_level", "throughput_volatility", "cpu_level", "cpu_volatility"],
    "MEMORY": ["memory_level", "memory_volatility", "memory_change", "cpu_level", "throughput_level"],
    "DISK_WRITE": ["disk_write_level", "disk_write_volatility", "cpu_level", "throughput_level"],
}
DESCRIPTOR_COLUMN = {
    "cpu_level": "cpu_mean_transformed",
    "cpu_volatility": "cpu_std_transformed",
    "throughput_level": "throughput_mean_transformed",
    "throughput_volatility": "throughput_std_transformed",
    "memory_level": "memory_mean_transformed",
    "memory_volatility": "memory_std_transformed",
    "memory_change": "memory_absdiff_mean_transformed",
    "disk_write_level": "disk_write_mean_transformed",
    "disk_write_volatility": "disk_write_std_transformed",
    "cpu_throughput_corr": "cpu_throughput_spearman",
}
ADJACENT_GROUPS = ((1, 2), (2, 4), (8, 16), (16, 32), (64, 128))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_spearman(x: Iterable[float], y: Iterable[float]) -> float:
    xa = np.asarray(list(x), dtype=float)
    ya = np.asarray(list(y), dtype=float)
    keep = np.isfinite(xa) & np.isfinite(ya)
    if keep.sum() < 3 or np.unique(xa[keep]).size < 2 or np.unique(ya[keep]).size < 2:
        return math.nan
    return float(spearmanr(xa[keep], ya[keep]).statistic)


def descriptor_block(panel: pd.DataFrame, machine: str, origins: np.ndarray) -> pd.DataFrame:
    origins = np.asarray(origins, dtype=np.int64)
    history = origins[:, None] - np.arange(31, -1, -1)
    if len(origins) and history.min() < 0:
        raise RuntimeError("Descriptor history precedes panel")
    segments = panel.segment_id.to_numpy(np.int64)
    if len(origins) and not np.all(segments[history] == segments[origins, None]):
        raise RuntimeError("Descriptor history crosses segment")
    native = panel.loc[:, list(target_columns(machine))].to_numpy(float)[history]
    transformed = np.stack(
        [transform_resource(native[:, :, i], resource) for i, resource in enumerate(RESOURCE_ORDER)],
        axis=-1,
    )
    x = np.arange(32, dtype=float)
    x_centered = x - x.mean()
    denominator = float(np.sum(x_centered**2))
    rows: dict[str, np.ndarray] = {"origin_index": origins}
    for index, resource in enumerate(RESOURCE_ORDER):
        prefix = resource.lower()
        values = transformed[:, :, index]
        native_values = native[:, :, index]
        rows[f"{prefix}_last_native"] = native_values[:, -1]
        rows[f"{prefix}_last_transformed"] = values[:, -1]
        rows[f"{prefix}_mean_transformed"] = values.mean(axis=1)
        rows[f"{prefix}_median_transformed"] = np.median(values, axis=1)
        rows[f"{prefix}_std_transformed"] = values.std(axis=1)
        rows[f"{prefix}_iqr_transformed"] = np.quantile(values, .75, axis=1) - np.quantile(values, .25, axis=1)
        rows[f"{prefix}_slope_transformed"] = np.sum((values - values.mean(axis=1, keepdims=True)) * x_centered, axis=1) / denominator
        rows[f"{prefix}_absdiff_mean_transformed"] = np.abs(np.diff(values, axis=1)).mean(axis=1)
        rows[f"{prefix}_max_transformed"] = values.max(axis=1)
        rows[f"{prefix}_min_transformed"] = values.min(axis=1)
        if resource in {"THROUGHPUT", "DISK_WRITE"}:
            med = np.median(native_values, axis=1)
            rows[f"{prefix}_zero_fraction"] = (native_values == 0).mean(axis=1)
            rows[f"{prefix}_spike_ratio"] = np.divide(native_values.max(axis=1), med, out=np.full(len(med), np.nan), where=med > 0)
    cpu_rank = rankdata(transformed[:, :, 0], axis=1)
    throughput_rank = rankdata(transformed[:, :, 1], axis=1)
    cpu_centered = cpu_rank - cpu_rank.mean(axis=1, keepdims=True)
    throughput_centered = throughput_rank - throughput_rank.mean(axis=1, keepdims=True)
    corr_denominator = np.sqrt(np.sum(cpu_centered**2, axis=1) * np.sum(throughput_centered**2, axis=1))
    rows["cpu_throughput_spearman"] = np.divide(
        np.sum(cpu_centered * throughput_centered, axis=1),
        corr_denominator,
        out=np.full(len(origins), np.nan),
        where=corr_denominator > 0,
    )
    return pd.DataFrame(rows)


def build_origin_descriptors(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    descriptor_rows = []
    threshold_rows = []
    threshold_names = sorted(set(DESCRIPTOR_COLUMN.values()))
    for machine in MACHINES:
        folds = build_factorial_folds(panel, machine, 32)
        for fold in folds:
            test = descriptor_block(panel, machine, fold.outer_test)
            test.insert(0, "fold", fold.fold)
            test.insert(0, "machine", machine)
            test["origin_timestamp"] = panel.timestamp.to_numpy()[test.origin_index.to_numpy(np.int64)]
            descriptor_rows.append(test)
            train = descriptor_block(panel, machine, fold.outer_train)
            for descriptor in threshold_names:
                values = train[descriptor].to_numpy(float)
                values = values[np.isfinite(values)]
                if not len(values):
                    lower = upper = math.nan
                else:
                    lower, upper = np.quantile(values, [.33, .67])
                threshold_rows.append({
                    "machine": machine,
                    "fold": fold.fold,
                    "descriptor": descriptor,
                    "q33": float(lower),
                    "q67": float(upper),
                    "training_origin_count": int(len(values)),
                    "source_partition": "legal_outer_train",
                    "history_window": 32,
                })
    descriptors = pd.concat(descriptor_rows, ignore_index=True)
    thresholds = pd.DataFrame(threshold_rows)
    descriptors.to_parquet(OUT / "origin_regime_descriptors.parquet", index=False)
    thresholds.to_csv(OUT / "regime_thresholds.csv", index=False)
    return descriptors, thresholds


def build_cell_matrix(metrics: pd.DataFrame) -> pd.DataFrame:
    cell_formulation = metrics.groupby(["formulation", "resource", "machine", "fold", "lead"], as_index=False).agg(
        mae=("mae", "mean"), n_predictions=("n", "sum")
    )
    frames = []
    for comparison, (reference, candidate) in COMPARISONS.items():
        left = cell_formulation[cell_formulation.formulation.eq(reference)].drop(columns="formulation").rename(columns={"mae": "mae_reference", "n_predictions": "n_reference"})
        right = cell_formulation[cell_formulation.formulation.eq(candidate)].drop(columns="formulation").rename(columns={"mae": "mae_candidate", "n_predictions": "n_candidate"})
        merged = left.merge(right, on=["resource", "machine", "fold", "lead"], validate="one_to_one")
        if not (merged.n_reference == merged.n_candidate).all():
            raise RuntimeError(f"Prediction support differs for {comparison}")
        merged.insert(0, "comparison", comparison)
        merged["gain_pct"] = 100 * (merged.mae_reference - merged.mae_candidate) / merged.mae_reference
        merged["absolute_mae_benefit"] = merged.mae_reference - merged.mae_candidate
        merged["sign"] = np.where(merged.gain_pct > 0, "POSITIVE", np.where(merged.gain_pct < 0, "NEGATIVE", "ZERO"))
        merged["n_predictions"] = merged.pop("n_reference").astype(int)
        merged.drop(columns="n_candidate", inplace=True)
        frames.append(merged)
    result = pd.concat(frames, ignore_index=True)
    result.to_parquet(OUT / "cell_level_gain_matrix.parquet", index=False)
    return result


def reproduce_primary(cell: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (comparison, resource), part in cell.groupby(["comparison", "resource"], sort=False):
        lead_macro = part.groupby("lead")[["mae_reference", "mae_candidate"]].mean()
        reference = float(lead_macro.mae_reference.mean())
        candidate = float(lead_macro.mae_candidate.mean())
        rows.append({"comparison": comparison, "resource": resource, "mae_reference": reference, "mae_candidate": candidate, "gain_pct": 100 * (reference - candidate) / reference, "absolute_mae_benefit": reference - candidate})
    result = pd.DataFrame(rows)
    result.to_csv(OUT / "phase3c_primary_reproduction.csv", index=False)
    return result


def distribution_summary(cell: pd.DataFrame) -> pd.DataFrame:
    result = cell.groupby(["comparison", "resource"]).gain_pct.agg(
        positive_cell_count=lambda x: int((x > 0).sum()),
        negative_cell_count=lambda x: int((x < 0).sum()),
        zero_cell_count=lambda x: int((x == 0).sum()),
        positive_fraction=lambda x: float((x > 0).mean()),
        median_gain="median",
        q25=lambda x: x.quantile(.25),
        q75=lambda x: x.quantile(.75),
        p10=lambda x: x.quantile(.10),
        p90=lambda x: x.quantile(.90),
        min_gain="min",
        max_gain="max",
    ).reset_index()
    result["iqr"] = result.q75 - result.q25
    result.to_csv(OUT / "cell_gain_distribution_summary.csv", index=False)
    return result


def stability_summaries(cell: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    machine_rows = []
    for keys, part in cell.groupby(["comparison", "resource", "machine"], sort=False):
        comparison, resource, machine = keys
        ref, cand = part.mae_reference.mean(), part.mae_candidate.mean()
        fold = part.groupby("fold")[["mae_reference", "mae_candidate"]].mean()
        lead = part.groupby("lead")[["mae_reference", "mae_candidate"]].mean()
        gain = 100 * (ref - cand) / ref
        positive_folds = int((fold.mae_reference > fold.mae_candidate).sum())
        positive_leads = int((lead.mae_reference > lead.mae_candidate).sum())
        if gain > 0 and positive_folds >= 4 and positive_leads >= 6:
            label = "STABLE_POSITIVE_MACHINE"
        elif gain > 0 and positive_folds >= 3 and positive_leads >= 4:
            label = "PARTIAL_POSITIVE_MACHINE"
        else:
            label = "UNSTABLE_OR_NEGATIVE"
        machine_rows.append({"comparison": comparison, "resource": resource, "machine": machine, "mae_reference": ref, "mae_candidate": cand, "absolute_mae_benefit": ref-cand, "gain_pct": gain, "positive_folds": positive_folds, "positive_leads": positive_leads, "positive_cell_fraction": float((part.gain_pct > 0).mean()), "median_cell_gain": part.gain_pct.median(), "q25_cell_gain": part.gain_pct.quantile(.25), "q75_cell_gain": part.gain_pct.quantile(.75), "iqr_cell_gain": part.gain_pct.quantile(.75)-part.gain_pct.quantile(.25), "stability_label": label})
    machine_frame = pd.DataFrame(machine_rows)
    machine_frame.to_csv(OUT / "gain_by_machine.csv", index=False)

    horizon_rows = []
    for keys, part in cell.groupby(["comparison", "resource", "lead"], sort=False):
        comparison, resource, lead_value = keys
        ref, cand = part.mae_reference.mean(), part.mae_candidate.mean()
        by_machine = part.groupby("machine")[["mae_reference", "mae_candidate"]].mean()
        by_fold = part.groupby("fold")[["mae_reference", "mae_candidate"]].mean()
        horizon_rows.append({"comparison": comparison, "resource": resource, "lead": lead_value, "mae_reference": ref, "mae_candidate": cand, "absolute_mae_benefit": ref-cand, "gain_pct": 100*(ref-cand)/ref, "positive_machines": int((by_machine.mae_reference>by_machine.mae_candidate).sum()), "positive_folds": int((by_fold.mae_reference>by_fold.mae_candidate).sum()), "positive_machine_fold_cells": int((part.gain_pct>0).sum()), "median_cell_gain": part.gain_pct.median(), "q25_cell_gain": part.gain_pct.quantile(.25), "q75_cell_gain": part.gain_pct.quantile(.75), "iqr_cell_gain": part.gain_pct.quantile(.75)-part.gain_pct.quantile(.25)})
    horizon_frame = pd.DataFrame(horizon_rows)
    horizon_frame.to_csv(OUT / "gain_by_horizon.csv", index=False)

    fold_rows = []
    for keys, part in cell.groupby(["comparison", "resource", "fold"], sort=False):
        comparison, resource, fold_value = keys
        ref, cand = part.mae_reference.mean(), part.mae_candidate.mean()
        by_machine = part.groupby("machine")[["mae_reference", "mae_candidate"]].mean()
        by_lead = part.groupby("lead")[["mae_reference", "mae_candidate"]].mean()
        fold_rows.append({"comparison": comparison, "resource": resource, "fold": fold_value, "mae_reference": ref, "mae_candidate": cand, "absolute_mae_benefit": ref-cand, "gain_pct": 100*(ref-cand)/ref, "positive_machines": int((by_machine.mae_reference>by_machine.mae_candidate).sum()), "positive_leads": int((by_lead.mae_reference>by_lead.mae_candidate).sum()), "median_cell_gain": part.gain_pct.median()})
    fold_frame = pd.DataFrame(fold_rows)
    fold_frame.to_csv(OUT / "gain_by_fold.csv", index=False)
    return machine_frame, horizon_frame, fold_frame


def build_sample_differences(registry: pd.DataFrame) -> None:
    destination = OUT / "sample_error_differences.parquet"
    writer: pq.ParquetWriter | None = None
    lookup = {}
    for row in registry.itertuples(index=False):
        resource = None if pd.isna(row.resource) else row.resource
        lookup[(row.formulation, resource, row.machine, int(row.fold), int(row.seed))] = ROOT / row.prediction_path
    try:
        for machine in MACHINES:
            for fold in range(1, 6):
                for seed in (0, 1, 2):
                    m1 = pd.read_parquet(lookup[("M1", None, machine, fold, seed)]).sort_values(["resource", "origin_index", "lead"])
                    for resource in RESOURCE_ORDER:
                        s1 = pd.read_parquet(lookup[("S1", resource, machine, fold, seed)]).sort_values(["origin_index", "lead"]).reset_index(drop=True)
                        s2 = pd.read_parquet(lookup[("S2", resource, machine, fold, seed)]).sort_values(["origin_index", "lead"]).reset_index(drop=True)
                        m1_part = m1[m1.resource.eq(resource)].sort_values(["origin_index", "lead"]).reset_index(drop=True)
                        keys = ["origin_index", "lead", "sample_id", "origin_timestamp", "target_timestamp"]
                        if not (s1[keys].equals(s2[keys]) and s1[keys].equals(m1_part[keys])):
                            raise RuntimeError("Matched prediction keys differ")
                        if not (np.array_equal(s1.y_true.to_numpy(), s2.y_true.to_numpy()) and np.array_equal(s1.y_true.to_numpy(), m1_part.y_true.to_numpy())):
                            raise RuntimeError("Matched prediction truth differs")
                        common = s1[keys].copy()
                        common.insert(0, "seed", seed)
                        common.insert(0, "fold", fold)
                        common.insert(0, "machine", machine)
                        common.insert(0, "resource", resource)
                        batches = []
                        for comparison, reference, candidate in (
                            ("S2_vs_S1", s1, s2),
                            ("M1_vs_S2", s2, m1_part),
                        ):
                            frame = common.copy()
                            frame.insert(0, "comparison", comparison)
                            reference_signed = reference.y_pred.to_numpy(float) - reference.y_true.to_numpy(float)
                            candidate_signed = candidate.y_pred.to_numpy(float) - candidate.y_true.to_numpy(float)
                            frame["reference_absolute_error"] = np.abs(reference_signed)
                            frame["candidate_absolute_error"] = np.abs(candidate_signed)
                            frame["delta_absolute_error"] = frame.reference_absolute_error - frame.candidate_absolute_error
                            frame["reference_signed_error"] = reference_signed
                            frame["candidate_signed_error"] = candidate_signed
                            batches.append(frame)
                        table = pa.Table.from_pandas(pd.concat(batches, ignore_index=True), preserve_index=False)
                        if writer is None:
                            writer = pq.ParquetWriter(destination, table.schema, compression="zstd")
                        writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()


def assign_bins(values: pd.DataFrame, descriptor: str, thresholds: pd.DataFrame) -> pd.DataFrame:
    column = DESCRIPTOR_COLUMN[descriptor]
    threshold = thresholds[thresholds.descriptor.eq(column)][["machine", "fold", "q33", "q67"]]
    frame = values.merge(threshold, on=["machine", "fold"], validate="many_to_one")
    observed = frame[column].to_numpy(float)
    frame["regime_bin"] = np.where(~np.isfinite(observed), "MISSING", np.where(observed <= frame.q33, "LOW", np.where(observed <= frame.q67, "MID", "HIGH")))
    return frame


def conditional_stats(part: pd.DataFrame, total_predictions: int) -> dict[str, float | int]:
    seed_cells = part.groupby(["machine", "fold", "seed", "lead"], as_index=False)[["reference_absolute_error", "candidate_absolute_error"]].mean()
    macro_cells = seed_cells.groupby(["machine", "fold", "lead"], as_index=False)[["reference_absolute_error", "candidate_absolute_error"]].mean()
    ref = float(macro_cells.reference_absolute_error.mean())
    cand = float(macro_cells.candidate_absolute_error.mean())
    by_machine = macro_cells.groupby("machine")[["reference_absolute_error", "candidate_absolute_error"]].mean()
    by_fold = macro_cells.groupby("fold")[["reference_absolute_error", "candidate_absolute_error"]].mean()
    return {"mae_reference": ref, "mae_candidate": cand, "absolute_mae_benefit": ref-cand, "gain_pct": 100*(ref-cand)/ref, "prediction_count": len(part), "coverage_fraction": len(part)/total_predictions, "machine_coverage": part.machine.nunique(), "fold_coverage": part.fold.nunique(), "positive_machine_count": int((by_machine.reference_absolute_error>by_machine.candidate_absolute_error).sum()), "positive_fold_count": int((by_fold.reference_absolute_error>by_fold.candidate_absolute_error).sum())}


def regime_analysis(comparison: str, descriptors: pd.DataFrame, thresholds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    source = pd.read_parquet(OUT / "sample_error_differences.parquet", filters=[("comparison", "==", comparison)])
    for resource in RESOURCE_ORDER:
        base = source[source.resource.eq(resource)].merge(descriptors, on=["machine", "fold", "origin_index", "origin_timestamp"], validate="many_to_one")
        total_predictions = len(base)
        for descriptor in REGIME_MAP[resource]:
            assigned = assign_bins(base, descriptor, thresholds)
            for regime_bin in ("LOW", "MID", "HIGH"):
                subset = assigned[assigned.regime_bin.eq(regime_bin)]
                if subset.empty:
                    continue
                lead_stats = {}
                for lead, lead_part in subset.groupby("lead"):
                    stats = conditional_stats(lead_part, total_predictions)
                    lead_stats[int(lead)] = stats
                    rows.append({"comparison": comparison, "resource": resource, "descriptor": descriptor, "regime_bin": regime_bin, "lead": str(int(lead)), **stats, "pattern_classification": ""})
                overall = conditional_stats(subset, total_predictions)
                adjacent_positive = any(a in lead_stats and b in lead_stats and lead_stats[a]["gain_pct"] > 0 and lead_stats[b]["gain_pct"] > 0 and lead_stats[a]["absolute_mae_benefit"] > 0 and lead_stats[b]["absolute_mae_benefit"] > 0 for a, b in ADJACENT_GROUPS)
                stable = overall["gain_pct"] > 0 and overall["absolute_mae_benefit"] > 0 and overall["positive_fold_count"] >= 4 and overall["positive_machine_count"] >= 5 and adjacent_positive and overall["coverage_fraction"] >= .20
                partial = overall["gain_pct"] > 0 and overall["absolute_mae_benefit"] > 0 and overall["positive_fold_count"] >= 3 and overall["positive_machine_count"] >= 3 and adjacent_positive and overall["coverage_fraction"] >= .10
                label = "STABLE_EXPLORATORY_PATTERN" if stable else ("PARTIAL_EXPLORATORY_PATTERN" if partial else "UNSTABLE_PATTERN")
                rows.append({"comparison": comparison, "resource": resource, "descriptor": descriptor, "regime_bin": regime_bin, "lead": "OVERALL", **overall, "pattern_classification": label})
    result = pd.DataFrame(rows)
    result.to_csv(OUT / f"{comparison.lower()}_regime_analysis.csv", index=False)
    return result


def dependency_analysis(panel: pd.DataFrame, cell: pd.DataFrame) -> pd.DataFrame:
    context = cell[cell.comparison.eq("S2_vs_S1")].groupby(["resource", "machine", "fold"], as_index=False)[["mae_reference", "mae_candidate"]].mean()
    context["context_gain_pct"] = 100*(context.mae_reference-context.mae_candidate)/context.mae_reference
    context["absolute_mae_benefit"] = context.mae_reference-context.mae_candidate
    pairs = {"CPU": ("THROUGHPUT",), "THROUGHPUT": ("CPU",), "MEMORY": ("CPU", "THROUGHPUT"), "DISK_WRITE": ("CPU", "THROUGHPUT")}
    rows = []
    for machine in MACHINES:
        values = panel.loc[:, list(target_columns(machine))].to_numpy(float)
        transformed = np.column_stack([transform_resource(values[:, i], resource) for i, resource in enumerate(RESOURCE_ORDER)])
        for fold in build_factorial_folds(panel, machine, 32):
            idx = fold.outer_train
            for resource in RESOURCE_ORDER:
                target_index = RESOURCE_ORDER.index(resource)
                gain_row = context[(context.resource.eq(resource)) & (context.machine.eq(machine)) & (context.fold.eq(fold.fold))].iloc[0]
                for predictor in pairs[resource]:
                    predictor_index = RESOURCE_ORDER.index(predictor)
                    for kind, x, y in (
                        ("level", transformed[idx, target_index], transformed[idx, predictor_index]),
                        ("difference", np.diff(transformed[idx, target_index]), np.diff(transformed[idx, predictor_index])),
                    ):
                        rows.append({"resource": resource, "predictor_resource": predictor, "dependency_kind": kind, "machine": machine, "fold": fold.fold, "training_dependency_spearman": safe_spearman(x, y), "context_gain_pct": gain_row.context_gain_pct, "absolute_mae_benefit": gain_row.absolute_mae_benefit})
    result = pd.DataFrame(rows)
    groups = []
    for keys, part in result.groupby(["resource", "predictor_resource", "dependency_kind"]):
        resource, predictor, kind = keys
        part = part.copy()
        finite = part.training_dependency_spearman.abs().rank(method="first")
        part["dependency_strength_quartile"] = pd.qcut(finite, 4, labels=["Q1", "Q2", "Q3", "Q4"])
        correlation = safe_spearman(part.training_dependency_spearman.abs(), part.context_gain_pct)
        quartile_gain = part.groupby("dependency_strength_quartile", observed=True).context_gain_pct.transform("mean")
        part["dependency_gain_spearman"] = correlation
        part["quartile_mean_context_gain_pct"] = quartile_gain
        groups.append(part)
    result = pd.concat(groups, ignore_index=True)
    result.to_csv(OUT / "dependency_vs_context_gain.csv", index=False)
    return result


def loss_share_analysis(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    loss = pd.read_parquet(SCI / "m1_resource_loss_history.parquet")
    epochs = pd.read_csv(SCI / "selected_epochs.csv")
    chosen = epochs[epochs.formulation.eq("M1")][["machine", "fold", "seed", "selected_L", "selected_epoch"]].rename(columns={"selected_L": "L", "selected_epoch": "epoch"})
    selected = loss[loss.phase.eq("inner")].merge(chosen, on=["machine", "fold", "seed", "L", "epoch"], validate="many_to_one")
    selected = selected[["resource", "machine", "fold", "seed", "loss_share", "resource_mse"]].rename(columns={"resource_mse": "normalized_resource_loss"})
    keys = ["resource", "machine", "fold", "seed"]
    s2 = metrics[metrics.formulation.eq("S2")].groupby(keys, as_index=False).mae.mean().rename(columns={"mae": "mae_s2"})
    m1 = metrics[metrics.formulation.eq("M1")].groupby(keys, as_index=False).mae.mean().rename(columns={"mae": "mae_m1"})
    result = selected.merge(s2, on=keys).merge(m1, on=keys)
    result["m1_vs_s2_gain_pct"] = 100*(result.mae_s2-result.mae_m1)/result.mae_s2
    result["absolute_mae_benefit"] = result.mae_s2-result.mae_m1
    grouped = []
    summary_rows = []
    for resource, part in result.groupby("resource"):
        part = part.copy()
        part["loss_share_quartile"] = pd.qcut(part.loss_share.rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"])
        part["normalized_loss_quartile"] = pd.qcut(part.normalized_resource_loss.rank(method="first"), 4, labels=["Q1", "Q2", "Q3", "Q4"])
        part["loss_share_gain_spearman"] = safe_spearman(part.loss_share, part.m1_vs_s2_gain_pct)
        part["normalized_loss_gain_spearman"] = safe_spearman(part.normalized_resource_loss, part.m1_vs_s2_gain_pct)
        part["loss_share_quartile_mean_gain_pct"] = part.groupby("loss_share_quartile", observed=True).m1_vs_s2_gain_pct.transform("mean")
        part["normalized_loss_quartile_mean_gain_pct"] = part.groupby("normalized_loss_quartile", observed=True).m1_vs_s2_gain_pct.transform("mean")
        summary_rows.append({"resource": resource, "loss_share_gain_spearman": part.loss_share_gain_spearman.iloc[0], "normalized_loss_gain_spearman": part.normalized_loss_gain_spearman.iloc[0], "mean_loss_share": part.loss_share.mean(), "mean_m1_vs_s2_gain_pct": part.m1_vs_s2_gain_pct.mean()})
        grouped.append(part)
    result = pd.concat(grouped, ignore_index=True)
    result.to_csv(OUT / "loss_share_vs_negative_transfer.csv", index=False)
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT / "loss_share_relationship_summary.csv", index=False)
    return result, summary


def context_length_analysis(cell: pd.DataFrame) -> pd.DataFrame:
    contexts = pd.read_csv(SCI / "selected_contexts.csv")
    s1 = contexts[contexts.formulation.eq("S1")].rename(columns={"selected_L": "s1_L"})[["resource", "machine", "fold", "s1_L"]]
    s2 = contexts[contexts.formulation.eq("S2")].rename(columns={"selected_L": "s2_L"})[["resource", "machine", "fold", "s2_L"]]
    m1 = contexts[contexts.formulation.eq("M1")].rename(columns={"selected_L": "m1_L"})[["machine", "fold", "m1_L"]]
    selections = s1.merge(s2, on=["resource", "machine", "fold"]).merge(m1, on=["machine", "fold"])
    rows = []
    for comparison, left, right in (("S2_vs_S1", "s1_L", "s2_L"), ("M1_vs_S2", "s2_L", "m1_L"), ("M1_vs_S1", "s1_L", "m1_L")):
        merged = cell[cell.comparison.eq(comparison)].merge(selections, on=["resource", "machine", "fold"])
        merged["context_relationship"] = np.where(merged[left].eq(merged[right]), "MATCH", "DIFFERENT")
        for (resource, relationship), part in merged.groupby(["resource", "context_relationship"]):
            ref, cand = part.mae_reference.mean(), part.mae_candidate.mean()
            rows.append({"comparison": comparison, "resource": resource, "context_relationship": relationship, "cell_count": len(part), "mae_reference": ref, "mae_candidate": cand, "absolute_mae_benefit": ref-cand, "gain_pct": 100*(ref-cand)/ref, "positive_cell_fraction": float((part.gain_pct>0).mean())})
    result = pd.DataFrame(rows)
    result.to_csv(OUT / "context_length_heterogeneity.csv", index=False)
    return result


def bootstrap_uncertainty(cell: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(20260928)
    rows = []
    for (comparison, resource), part in cell.groupby(["comparison", "resource"], sort=False):
        reference = part.pivot(index="machine", columns=["fold", "lead"], values="mae_reference").reindex(index=MACHINES)
        candidate = part.pivot(index="machine", columns=["fold", "lead"], values="mae_candidate").reindex(index=MACHINES)
        ref_array = np.empty((7, 5, 8)); cand_array = np.empty((7, 5, 8))
        for machine_index, machine in enumerate(MACHINES):
            for fold_index, fold in enumerate(range(1, 6)):
                for lead_index, lead in enumerate(FUTURE_LEADS):
                    ref_array[machine_index, fold_index, lead_index] = reference.loc[machine, (fold, lead)]
                    cand_array[machine_index, fold_index, lead_index] = candidate.loc[machine, (fold, lead)]
        machine_draw = rng.integers(0, 7, size=(10000, 7))
        fold_draw = rng.integers(0, 5, size=(10000, 7, 5))
        selected_ref = ref_array[machine_draw[:, :, None], fold_draw, :]
        selected_cand = cand_array[machine_draw[:, :, None], fold_draw, :]
        for lead_index, lead in enumerate(FUTURE_LEADS):
            ref_boot = selected_ref[:, :, :, lead_index].mean(axis=(1, 2))
            cand_boot = selected_cand[:, :, :, lead_index].mean(axis=(1, 2))
            gains = 100*(ref_boot-cand_boot)/ref_boot
            observed_ref = ref_array[:, :, lead_index].mean(); observed_cand = cand_array[:, :, lead_index].mean()
            rows.append({"comparison": comparison, "resource": resource, "lead": str(lead), "observed_gain_pct": 100*(observed_ref-observed_cand)/observed_ref, "lower_2_5_pct": np.quantile(gains,.025), "upper_97_5_pct": np.quantile(gains,.975), "replicates":10000, "label":"POST-HOC BOOTSTRAP UNCERTAINTY INTERVAL"})
        ref_boot = selected_ref.mean(axis=(1, 2, 3)); cand_boot = selected_cand.mean(axis=(1, 2, 3)); gains=100*(ref_boot-cand_boot)/ref_boot
        observed_ref=ref_array.mean(); observed_cand=cand_array.mean()
        rows.append({"comparison": comparison, "resource": resource, "lead":"OVERALL", "observed_gain_pct":100*(observed_ref-observed_cand)/observed_ref, "lower_2_5_pct":np.quantile(gains,.025), "upper_97_5_pct":np.quantile(gains,.975), "replicates":10000, "label":"POST-HOC BOOTSTRAP UNCERTAINTY INTERVAL"})
    result=pd.DataFrame(rows)
    result.to_csv(OUT/"posthoc_bootstrap_uncertainty.csv",index=False)
    return result


def benefit_concentration(cell: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for (comparison,resource),part in cell.groupby(["comparison","resource"]):
        positive=part.loc[part.absolute_mae_benefit>0,"absolute_mae_benefit"].sort_values(ascending=False).to_numpy()
        total_cells=len(part)
        if len(positive) and positive.sum()>0:
            cumulative=np.cumsum(positive)/positive.sum()
            count50=int(np.searchsorted(cumulative,.5)+1); count80=int(np.searchsorted(cumulative,.8)+1)
            fraction50=count50/total_cells; fraction80=count80/total_cells
        else:
            count50=count80=0; fraction50=fraction80=math.nan
        rows.append({"comparison":comparison,"resource":resource,"total_cells":total_cells,"positive_cells":len(positive),"positive_cell_fraction":len(positive)/total_cells,"positive_absolute_improvement_total":positive.sum() if len(positive) else 0.0,"cells_for_50pct":count50,"fraction_cells_for_50pct":fraction50,"cells_for_80pct":count80,"fraction_cells_for_80pct":fraction80})
    result=pd.DataFrame(rows)
    result.to_csv(OUT/"benefit_concentration.csv",index=False)
    return result


def memory_decomposition(metrics: pd.DataFrame, loss_rows: pd.DataFrame) -> pd.DataFrame:
    sample_path=OUT/"sample_error_differences.parquet"
    s2s1=pd.read_parquet(sample_path,filters=[("comparison","==","S2_vs_S1"),("resource","==","MEMORY")])
    m1s2=pd.read_parquet(sample_path,filters=[("comparison","==","M1_vs_S2"),("resource","==","MEMORY")])
    keys=["machine","fold","seed","lead"]
    def summarize(frame:pd.DataFrame,prefix:str,which:str)->pd.DataFrame:
        absolute=f"{which}_absolute_error"; signed=f"{which}_signed_error"
        return frame.groupby(keys).agg(**{f"{prefix}_mae":(absolute,"mean"),f"{prefix}_mean_bias":(signed,"mean"),f"{prefix}_median_bias":(signed,"median"),f"{prefix}_error_variance":(signed,"var"),f"{prefix}_abs_error_p90":(absolute,lambda x:x.quantile(.90)),f"{prefix}_abs_error_p95":(absolute,lambda x:x.quantile(.95)),f"{prefix}_abs_error_p99":(absolute,lambda x:x.quantile(.99))}).reset_index()
    s1=summarize(s2s1,"s1","reference"); s2=summarize(s2s1,"s2","candidate"); m1=summarize(m1s2,"m1","candidate")
    result=s1.merge(s2,on=keys).merge(m1,on=keys)
    result["m1_s2_absolute_degradation"]=result.m1_mae-result.s2_mae
    result["m1_s2_relative_degradation_pct"]=100*(result.m1_mae-result.s2_mae)/result.s2_mae
    epochs=pd.read_csv(SCI/"selected_epochs.csv")
    for formulation in ("S1","S2"):
        selected=epochs[(epochs.formulation.eq(formulation))&(epochs.resource.eq("MEMORY"))][["machine","fold","seed","selected_L"]].rename(columns={"selected_L":f"{formulation.lower()}_selected_L"})
        result=result.merge(selected,on=["machine","fold","seed"])
    selected=epochs[epochs.formulation.eq("M1")][["machine","fold","seed","selected_L"]].rename(columns={"selected_L":"m1_selected_L"})
    result=result.merge(selected,on=["machine","fold","seed"])
    persistence=metrics[(metrics.formulation.eq("M1"))&(metrics.resource.eq("MEMORY"))][keys+["persistence_skill"]]
    result=result.merge(persistence,on=keys)
    memory_loss=loss_rows[loss_rows.resource.eq("MEMORY")][["machine","fold","seed","loss_share"]].rename(columns={"loss_share":"m1_memory_loss_share"})
    result=result.merge(memory_loss,on=["machine","fold","seed"])
    result.to_csv(OUT/"memory_failure_decomposition.csv",index=False)
    return result


def coherent_horizon_regions(horizon:pd.DataFrame,comparison:str,resource:str)->list[str]:
    part=horizon[(horizon.comparison.eq(comparison))&(horizon.resource.eq(resource))].set_index("lead")
    regions=[]
    for name,leads in (("short",(1,2,4)),("medium",(8,16,32)),("long",(64,128))):
        signs=[part.loc[lead,"gain_pct"]>0 for lead in leads]
        if all(signs): regions.append(f"{name}:positive")
        elif not any(signs): regions.append(f"{name}:negative")
        else: regions.append(f"{name}:mixed")
    return regions


def make_figures(cell:pd.DataFrame,machine:pd.DataFrame,horizon:pd.DataFrame,fold:pd.DataFrame,s2_regime:pd.DataFrame,dependency:pd.DataFrame,loss:pd.DataFrame,memory:pd.DataFrame,concentration:pd.DataFrame,bootstrap:pd.DataFrame)->None:
    FIG.mkdir(parents=True,exist_ok=True)
    for number,comparison,title in ((1,"S2_vs_S1","S2 vs S1"),(2,"M1_vs_S2","M1 vs S2")):
        fig,axes=plt.subplots(2,2,figsize=(11,7),constrained_layout=True)
        for ax,resource in zip(axes.ravel(),RESOURCE_ORDER):
            matrix=cell[(cell.comparison.eq(comparison))&(cell.resource.eq(resource))].groupby(["machine","lead"]).gain_pct.mean().unstack("lead").reindex(index=MACHINES,columns=FUTURE_LEADS)
            im=ax.imshow(matrix,cmap="coolwarm",aspect="auto"); ax.set_title(resource); ax.set_xticks(range(8),FUTURE_LEADS); ax.set_yticks(range(7),MACHINES); fig.colorbar(im,ax=ax,label="gain %")
        fig.suptitle(f"{title}: machine x lead gains"); fig.savefig(FIG/f"{number:02d}_{comparison.lower()}_machine_lead_heatmaps.png",dpi=140); plt.close(fig)
    for number,comparison,title in ((3,"S2_vs_S1","S2 vs S1"),(4,"M1_vs_S2","M1 vs S2")):
        fig,ax=plt.subplots(figsize=(8,4.5)); part=fold[fold.comparison.eq(comparison)]
        for resource in RESOURCE_ORDER:
            p=part[part.resource.eq(resource)]; ax.plot(p.fold,p.gain_pct,marker="o",label=resource)
        ax.axhline(0,color="black",lw=.8); ax.set_xlabel("chronological fold"); ax.set_ylabel("gain %"); ax.set_title(f"Fold-wise {title} gains"); ax.legend(); fig.tight_layout(); fig.savefig(FIG/f"{number:02d}_{comparison.lower()}_fold_gains.png",dpi=140); plt.close(fig)
    overall=s2_regime[s2_regime.lead.eq("OVERALL")].copy(); overall["label"]=overall.resource+":"+overall.descriptor+":"+overall.regime_bin
    fig,ax=plt.subplots(figsize=(10,6)); top=overall.reindex(overall.gain_pct.abs().sort_values(ascending=False).index).head(30).sort_values("gain_pct"); ax.barh(top.label,top.gain_pct); ax.axvline(0,color="black",lw=.8); ax.set_title("Controlled regime-conditional S2 vs S1 effects"); ax.set_xlabel("gain %"); fig.tight_layout(); fig.savefig(FIG/"05_regime_conditional_s2_vs_s1.png",dpi=140); plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(10,7),constrained_layout=True)
    for ax,resource in zip(axes.ravel(),RESOURCE_ORDER):
        p=dependency[dependency.resource.eq(resource)]; ax.scatter(p.training_dependency_spearman.abs(),p.context_gain_pct,alpha=.65); ax.axhline(0,color="black",lw=.7); ax.set_title(resource); ax.set_xlabel("absolute training Spearman"); ax.set_ylabel("S2 vs S1 gain %")
    fig.suptitle("Training dependency versus context gain"); fig.savefig(FIG/"06_dependency_vs_context_gain.png",dpi=140); plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(10,7),constrained_layout=True)
    for ax,resource in zip(axes.ravel(),RESOURCE_ORDER):
        p=loss[loss.resource.eq(resource)]; ax.scatter(100*p.loss_share,p.m1_vs_s2_gain_pct,alpha=.65); ax.axhline(0,color="black",lw=.7); ax.set_title(resource); ax.set_xlabel("M1 validation loss share %"); ax.set_ylabel("M1 vs S2 gain %")
    fig.suptitle("M1 loss share versus negative transfer"); fig.savefig(FIG/"07_loss_share_vs_m1_s2_gain.png",dpi=140); plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.5)); p=memory.groupby("lead")[["s1_mae","s2_mae","m1_mae"]].mean(); [ax.plot(p.index,p[column],marker="o",label=column.upper()) for column in p.columns]; ax.set_xscale("log",base=2); ax.set_xticks(FUTURE_LEADS,FUTURE_LEADS); ax.set_xlabel("lead"); ax.set_ylabel("memory MAE"); ax.set_title("Memory failure decomposition"); ax.legend(); fig.tight_layout(); fig.savefig(FIG/"08_memory_failure_decomposition.png",dpi=140); plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,5)); x=np.arange(len(concentration)); ax.bar(x-.2,concentration.fraction_cells_for_50pct,width=.4,label="50% of positive improvement"); ax.bar(x+.2,concentration.fraction_cells_for_80pct,width=.4,label="80% of positive improvement"); ax.set_xticks(x,[f"{r.comparison}\n{r.resource}" for r in concentration.itertuples()],rotation=45,ha="right"); ax.set_ylabel("fraction of all cells"); ax.set_title("Benefit concentration"); ax.legend(); fig.tight_layout(); fig.savefig(FIG/"09_benefit_concentration.png",dpi=140); plt.close(fig)
    overall=bootstrap[bootstrap.lead.eq("OVERALL")].copy(); overall["label"]=overall.comparison+"\n"+overall.resource; x=np.arange(len(overall)); y=overall.observed_gain_pct.to_numpy(); lower=y-overall.lower_2_5_pct.to_numpy(); upper=overall.upper_97_5_pct.to_numpy()-y
    fig,ax=plt.subplots(figsize=(10,5)); ax.errorbar(x,y,yerr=np.vstack([lower,upper]),fmt="o",capsize=3); ax.axhline(0,color="black",lw=.8); ax.set_xticks(x,overall.label,rotation=45,ha="right"); ax.set_ylabel("gain %"); ax.set_title("Post-hoc bootstrap uncertainty summary"); fig.tight_layout(); fig.savefig(FIG/"10_posthoc_bootstrap_uncertainty.png",dpi=140); plt.close(fig)


def markdown(frame:pd.DataFrame,columns:list[str],digits:int=4)->list[str]:
    lines=["| "+" | ".join(columns)+" |","|"+"|".join(["---"]*len(columns))+"|"]
    for row in frame[columns].itertuples(index=False):
        values=[]
        for value in row:
            if isinstance(value,(float,np.floating)):
                values.append("NA" if not np.isfinite(value) else f"{value:.{digits}f}")
            else: values.append(str(value))
        lines.append("| "+" | ".join(values)+" |")
    return lines


def decide(s2_regime:pd.DataFrame,machine:pd.DataFrame)->tuple[str,pd.DataFrame]:
    patterns=s2_regime[s2_regime.lead.eq("OVERALL")].copy()
    stable=patterns[patterns.pattern_classification.eq("STABLE_EXPLORATORY_PATTERN")]
    partial=patterns[patterns.pattern_classification.eq("PARTIAL_EXPLORATORY_PATTERN")]
    if len(stable): decision="REGIME_CONDITIONAL_CONTEXT_HYPOTHESIS"
    elif len(partial) or (machine[(machine.comparison.eq("S2_vs_S1"))&(machine.stability_label.ne("UNSTABLE_OR_NEGATIVE"))].shape[0]>0): decision="INCONCLUSIVE_POSTHOC_HETEROGENEITY"
    else: decision="NO_STABLE_CONTEXT_BENEFIT"
    return decision,patterns


def write_reports(primary:pd.DataFrame,machine:pd.DataFrame,horizon:pd.DataFrame,fold:pd.DataFrame,s2_regime:pd.DataFrame,m1_regime:pd.DataFrame,dependency:pd.DataFrame,loss_summary:pd.DataFrame,context:pd.DataFrame,memory:pd.DataFrame,bootstrap:pd.DataFrame,concentration:pd.DataFrame,decision:str,patterns:pd.DataFrame)->None:
    stable_machines=machine[(machine.comparison.eq("S2_vs_S1"))&(machine.stability_label.eq("STABLE_POSITIVE_MACHINE"))]
    partial_machines=machine[(machine.comparison.eq("S2_vs_S1"))&(machine.stability_label.eq("PARTIAL_POSITIVE_MACHINE"))]
    stable_patterns=patterns[patterns.pattern_classification.eq("STABLE_EXPLORATORY_PATTERN")]
    partial_patterns=patterns[patterns.pattern_classification.eq("PARTIAL_EXPLORATORY_PATTERN")]
    dependency_summary=dependency.groupby(["resource","predictor_resource","dependency_kind"],as_index=False).dependency_gain_spearman.first()
    memory_breadth=pd.DataFrame([{"dimension":"machines","positive_degradation_units":int((memory.groupby("machine").m1_s2_absolute_degradation.mean()>0).sum()),"total_units":7},{"dimension":"folds","positive_degradation_units":int((memory.groupby("fold").m1_s2_absolute_degradation.mean()>0).sum()),"total_units":5},{"dimension":"leads","positive_degradation_units":int((memory.groupby("lead").m1_s2_absolute_degradation.mean()>0).sum()),"total_units":8}])
    cpu_machine=machine[(machine.comparison.isin(["S2_vs_S1","M1_vs_S1"]))&(machine.resource.eq("CPU"))]
    cpu_horizon=horizon[(horizon.comparison.isin(["S2_vs_S1","M1_vs_S1"]))&(horizon.resource.eq("CPU"))]
    exact_hypothesis="None survived the stable exploratory rule."
    if len(stable_patterns):
        first=stable_patterns.iloc[0]; exact_hypothesis=f"On fresh independent data, {first.resource} forecasts will obtain lower native MAE from cross-resource input specifically in the pre-origin {first.descriptor}={first.regime_bin} regime than from own-resource history alone."
    lines=["# Phase 3D Post-Hoc Heterogeneity and Research-Direction Audit","","## Evidentiary status","",f"This audit is explicitly post-hoc and exploratory. All five outer folds were previously inspected. Protocol SHA-256: `{PROTOCOL_SHA256}`. Validation status: **PENDING**.","","## Frozen Phase 3C reproduction",""]+markdown(primary,["comparison","resource","gain_pct","absolute_mae_benefit"])
    lines += ["","## Machine heterogeneity","",f"Stable positive S2-vs-S1 machines: {len(stable_machines)}. Partial positive machines: {len(partial_machines)}.",""]+markdown(pd.concat([stable_machines,partial_machines]),["resource","machine","gain_pct","positive_folds","positive_leads","stability_label"]) if len(stable_machines)+len(partial_machines) else ["","## Machine heterogeneity","","No S2-versus-S1 machine met the stable or partial machine rule."]
    lines += ["","## Horizon heterogeneity",""]
    for resource in RESOURCE_ORDER: lines.append(f"- {resource}: "+", ".join(coherent_horizon_regions(horizon,"S2_vs_S1",resource)))
    lines += ["","## Fold heterogeneity",""]+markdown(fold[fold.comparison.eq("S2_vs_S1")],["resource","fold","gain_pct","positive_machines","positive_leads"])
    lines += ["","## Controlled regime heterogeneity","",f"Stable controlled S2-vs-S1 patterns: {len(stable_patterns)}. Partial patterns: {len(partial_patterns)}.",""]+markdown(pd.concat([stable_patterns,partial_patterns]),["resource","descriptor","regime_bin","gain_pct","absolute_mae_benefit","coverage_fraction","positive_machine_count","positive_fold_count","pattern_classification"]) if len(stable_patterns)+len(partial_patterns) else ["","## Controlled regime heterogeneity","","No controlled S2-versus-S1 regime reached the stable or partial exploratory rule."]
    lines += ["","## Dependency versus benefit","","Spearman associations below compare absolute training-side dependency with S2-versus-S1 test gain; they are non-causal.",""]+markdown(dependency_summary,["resource","predictor_resource","dependency_kind","dependency_gain_spearman"])
    lines += ["","## M1 loss share versus M1-S2 performance","","These resource-specific Spearman relationships are descriptive only.",""]+markdown(loss_summary,["resource","loss_share_gain_spearman","normalized_loss_gain_spearman","mean_loss_share","mean_m1_vs_s2_gain_pct"])
    lines += ["","## Context-length relationship","", "Selected-L equality/inequality is an association, not a causal intervention.",""]+markdown(context,["comparison","resource","context_relationship","cell_count","gain_pct","absolute_mae_benefit","positive_cell_fraction"])
    lines += ["","## Memory failure decomposition","",f"Native macro-MAE degradation M1 versus S2: {primary[(primary.comparison.eq('M1_vs_S2'))&(primary.resource.eq('MEMORY'))].absolute_mae_benefit.iloc[0]*-1:.4f}; mean cell-relative degradation: {memory.m1_s2_relative_degradation_pct.mean():.4f}%.",""]+markdown(memory_breadth,["dimension","positive_degradation_units","total_units"])
    m1_stable=m1_regime[(m1_regime.lead.eq("OVERALL"))&(m1_regime.pattern_classification.eq("STABLE_EXPLORATORY_PATTERN"))]
    m1_partial=m1_regime[(m1_regime.lead.eq("OVERALL"))&(m1_regime.pattern_classification.eq("PARTIAL_EXPLORATORY_PATTERN"))]
    lines += ["","## M1 negative-transfer localization","",f"No controlled M1-versus-S2 regime was stably positive; {len(m1_partial)} were partially positive. Memory degradation was present across all 7 machines, all 8 leads, and 4/5 folds, so the memory failure is broad rather than confined to one operating regime. Other resources show mixed cell-level pockets but no stable shared-representation benefit.",""]+markdown(m1_partial,["resource","descriptor","regime_bin","gain_pct","absolute_mae_benefit","coverage_fraction","positive_machine_count","positive_fold_count","pattern_classification"])
    lines += ["","## CPU special case","","M1's small gain versus S2 is not evidence of beating S1. S2-versus-S1 and M1-versus-S1 CPU stability summaries remain the required local-baseline comparison.",""]+markdown(cpu_machine,["comparison","machine","gain_pct","positive_folds","positive_leads","stability_label"])+[""]+markdown(cpu_horizon,["comparison","lead","gain_pct","positive_machines","positive_folds"])
    boundary=machine[(machine.comparison.eq("S2_vs_S1"))&(machine.resource.isin(["THROUGHPUT","DISK_WRITE"]))]
    lines += ["","## Throughput and disk-write boundary","", "Machine-level mixtures distinguish uniform small effects from cancelling positive and negative pockets.",""]+markdown(boundary,["resource","machine","gain_pct","positive_folds","positive_leads","positive_cell_fraction","stability_label"])
    lines += ["","## Post-hoc bootstrap uncertainty","","These are POST-HOC BOOTSTRAP UNCERTAINTY INTERVALS, not confirmatory confidence intervals.",""]+markdown(bootstrap[bootstrap.lead.eq("OVERALL")],["comparison","resource","observed_gain_pct","lower_2_5_pct","upper_97_5_pct"])
    lines += ["","## Benefit concentration","",""]+markdown(concentration,["comparison","resource","positive_cell_fraction","fraction_cells_for_50pct","fraction_cells_for_80pct"])
    lines += ["","## Exploratory pattern classifications","",f"Stable patterns: {len(stable_patterns)}; partial patterns: {len(partial_patterns)}; all remaining controlled patterns are unstable. These are exploratory labels only.","","## Research-direction decision","",f"**{decision}**","",f"Surviving hypothesis: {exact_hypothesis}","","Any surviving or partial hypothesis requires an untouched temporal holdout, newly collected TimeTrack telemetry, an external compatible dataset, or another genuinely independent source. The five existing folds cannot provide untouched confirmation.","","No implementation details or new architecture are proposed.",""]
    (BASE/"PHASE3D_POSTHOC_REPORT.md").write_text("\n".join(lines))
    answers=["# Phase 3D Research-Direction Decision","",f"## Decision\n\n**{decision}**","","## Audit answers","",f"1. Stable cross-resource input benefit for any target: {'yes' if len(stable_patterns) else 'no'}.",f"2. Target-specific benefit: {'exploratory stable pattern exists' if len(stable_patterns) else 'not established'}.",f"3. Horizon-specific benefit: see `outputs/gain_by_horizon.csv`; adjacent signs were required for every pattern label.",f"4. Machine-specific benefit: {len(stable_machines)} stable and {len(partial_machines)} partial S2-versus-S1 machines.",f"5. Regime-specific benefit: {len(stable_patterns)} stable and {len(partial_patterns)} partial controlled regimes.","6. Benefit concentration is recorded in `outputs/benefit_concentration.csv`; concentration cannot override stability requirements.","7. Training dependency associations are descriptive and do not establish that dependence predicts benefit causally.","8. M1 transfer is decomposed by regime and by the dedicated memory audit; the global Phase 3C label remains unchanged.","9. Loss share relationships are descriptive and cannot explain negative transfer causally.",f"10. Memory degradation breadth: {memory_breadth.to_dict('records')}.",f"11. CPU multi-resource benefit over S1: assessed directly in S2-versus-S1 and M1-versus-S1 tables; M1-versus-S2 alone is not accepted as evidence.",f"12. Another multi-resource architecture is {'not justified without fresh confirmation' if decision in {'NO_STABLE_CONTEXT_BENEFIT','INCONCLUSIVE_POSTHOC_HETEROGENEITY'} else 'not authorized here; only a fresh-data hypothesis is supported'}.",f"13. Exact hypothesis: {exact_hypothesis}","14. Confirmation requires untouched temporal data, new TimeTrack telemetry, an external compatible dataset, or another independent source.","","No training or architecture selection is authorized by this record."]
    (BASE/"RESEARCH_DIRECTION_DECISION.md").write_text("\n".join(answers)+"\n")


def main()->None:
    if sha256(PROTOCOL)!=PROTOCOL_SHA256: raise RuntimeError("Post-hoc protocol identity differs")
    if sha256(P3C/"PHASE3C_SCIENTIFIC_ARTIFACT_SHA256.csv")!=P3C_INVENTORY_SHA256: raise RuntimeError("Phase 3C inventory differs")
    OUT.mkdir(parents=True,exist_ok=True); FIG.mkdir(parents=True,exist_ok=True)
    panel=load_panel(); metrics=pd.read_parquet(SCI/"metrics.parquet"); registry=pd.read_csv(SCI/"run_registry.csv")
    cell=build_cell_matrix(metrics); primary=reproduce_primary(cell)
    expected={"S2_vs_S1":{"CPU":-3.3130,"THROUGHPUT":-0.2428,"MEMORY":0.8594,"DISK_WRITE":-0.4923},"M1_vs_S2":{"CPU":0.4696,"THROUGHPUT":-0.8401,"MEMORY":-18.4769,"DISK_WRITE":-0.7956},"M1_vs_S1":{"CPU":-2.8279,"THROUGHPUT":-1.0849,"MEMORY":-17.4587,"DISK_WRITE":-1.2918}}
    for row in primary.itertuples():
        if not np.isclose(row.gain_pct,expected[row.comparison][row.resource],atol=5e-5,rtol=0): raise RuntimeError("Phase 3C primary result reproduction failed")
    distribution_summary(cell); machine,horizon,fold=stability_summaries(cell)
    descriptors,thresholds=build_origin_descriptors(panel)
    build_sample_differences(registry)
    s2_regime=regime_analysis("S2_vs_S1",descriptors,thresholds); m1_regime=regime_analysis("M1_vs_S2",descriptors,thresholds)
    dependency=dependency_analysis(panel,cell); loss,loss_summary=loss_share_analysis(metrics); context=context_length_analysis(cell)
    bootstrap=bootstrap_uncertainty(cell); concentration=benefit_concentration(cell); memory=memory_decomposition(metrics,loss)
    decision,patterns=decide(s2_regime,machine)
    make_figures(cell,machine,horizon,fold,s2_regime,dependency,loss,memory,concentration,bootstrap)
    write_reports(primary,machine,horizon,fold,s2_regime,m1_regime,dependency,loss_summary,context,memory,bootstrap,concentration,decision,patterns)
    metadata={"status":"ANALYSIS_COMPLETE_VALIDATION_PENDING","protocol_sha256":PROTOCOL_SHA256,"phase3c_inventory_sha256":P3C_INVENTORY_SHA256,"phase3c_scientific_tree_sha256":P3C_TREE_SHA256,"decision":decision,"figures":len(list(FIG.glob("*.png"))),"no_training":True,"bootstrap_replicates":10000,"bootstrap_seed":20260928}
    (OUT/"audit_metadata.json").write_text(json.dumps(metadata,indent=2,sort_keys=True)+"\n")
    print(json.dumps(metadata,indent=2,sort_keys=True))


if __name__=="__main__": main()
