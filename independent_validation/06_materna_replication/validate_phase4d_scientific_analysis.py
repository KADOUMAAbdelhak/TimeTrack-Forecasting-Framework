#!/usr/bin/env python3
"""Independent validator for the frozen Phase 4D Materna scientific analysis."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / "outputs/scientific_v1"
ANALYSIS = OUT / "analysis"
COMPARISONS = OUT / "comparisons"
SYNTHESIS = OUT / "synthesis"
FIGURES = OUT / "figures"
OUTPUT = BASE / "PHASE4D_MATERNA_SCIENTIFIC_ANALYSIS_VALIDATION.json"
TRACES = ("Materna-T1", "Materna-T2", "Materna-T3")
RESOURCES = ("CPU", "THROUGHPUT", "MEMORY", "DISK_WRITE")
LEADS = (1, 2, 4, 9, 18)
FORMULATIONS = ("S1", "S2", "M1")
COMPARISONS_DEF = {"S2_vs_S1": ("S1", "S2"), "M1_vs_S2": ("S2", "M1"), "M1_vs_S1": ("S1", "M1")}
POSITIVE = {"BROAD_POSITIVE", "CONDITIONALLY_POSITIVE"}
SEED = 20261007
REPLICATES = 10_000
HEAVY_SHA = "8484e62b2dae596ece90308c18ea617ec904ea55ceb4fbfc76e2fcaa55dd1718"
HEAVY_TREE = "3d9a6ffe1b7d520bc5ca0e3f36e147f39e87590c88f8289a26c962a09e6756e1"
SOURCE_HASHES = {
    "Materna-T1/metrics.parquet": "f4ed6252ce72c3bb0b05b78cd471331c86ac9701a72756968207088c7f36d370",
    "Materna-T1/persistence_metrics.parquet": "b151fc44a962270c42ed811d7ab06e702a622fdddaeeafaa937bb2c429731989",
    "Materna-T1/selected_contexts.csv": "1f67fbfed25e34b29d0f2e28a220a3f73e8cd795b746c0d8ef08a8794997cfea",
    "Materna-T1/selected_epochs.csv": "8ae73a05e7b1128171af6f5aabf023c20cde17c0baf156eae0761183ff432ec9",
    "Materna-T1/m1_resource_loss_history.parquet": "a1e95c096b3341317e0bce8ac09b1161567923f43c4069e1a06371088cbc6c36",
    "Materna-T2/metrics.parquet": "24b670e03c152018cccf9fc23a6d2b7fe1d9a693783d53b2290c167144b4720d",
    "Materna-T2/persistence_metrics.parquet": "8b37b0e986886f40e7d177f95f846c95e1a60806bdddf335a7bf57df94eacbbc",
    "Materna-T2/selected_contexts.csv": "caf446c19e319c47d3ad345fe3110f0e804a01b051473ec408819edeab422f06",
    "Materna-T2/selected_epochs.csv": "11afe345f78f4378356ba3210dfa3ad785c0b6ec3939f05c52e1d9ef561582da",
    "Materna-T2/m1_resource_loss_history.parquet": "9f049f1724b30dfc4dc70b01c1f52523c56a5b2182bd1543da3068b31ced39de",
    "Materna-T3/metrics.parquet": "50767c5f371a6dc5c528b6c5bd777a7660faa8176d7c1f8d2a7a443f18e8b843",
    "Materna-T3/persistence_metrics.parquet": "f06a77a33b2056f74b423b054c7b4f2aa75dc28c30d1cc10f966e46015aae5eb",
    "Materna-T3/selected_contexts.csv": "dc2f5d1772e039f6a9a0748ad2ae428fb4592b349282512d1d09ea3b2aaf067d",
    "Materna-T3/selected_epochs.csv": "895d228f17d3d70f5a3896b1737267ebb60814d9340c98487eaf8aa21bb2dc8d",
    "Materna-T3/m1_resource_loss_history.parquet": "48b3666ab1955713f1d97194fe452db9ceeb8743a06b81b5c51dadb288d52404",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gain(reference, candidate):
    return 100.0 * (reference - candidate) / reference


def frame_close(left: pd.DataFrame, right: pd.DataFrame, keys: list[str], columns: list[str], tolerance: float = 1e-10) -> bool:
    a = left.sort_values(keys).reset_index(drop=True)
    b = right.sort_values(keys).reset_index(drop=True)
    if len(a) != len(b) or any(not a[key].astype(str).equals(b[key].astype(str)) for key in keys):
        return False
    return all(np.allclose(a[column].astype(float), b[column].astype(float), rtol=tolerance, atol=tolerance, equal_nan=True) for column in columns)


def verify_heavy() -> dict:
    inventory = OUT / "runtime/PHASE4D_EXECUTION_ARTIFACT_SHA256.csv"
    rows = list(csv.DictReader(inventory.open(newline="")))
    failures = []
    tree = hashlib.sha256()
    for row in rows:
        path = ROOT / row["relative_path"]
        tree.update(f"{row['relative_path']},{row['byte_size']},{row['sha256']}\n".encode())
        if not path.is_file() or path.stat().st_size != int(row["byte_size"]) or sha256_file(path) != row["sha256"]:
            failures.append(row["relative_path"])
    status = len(rows) == 141785 and not failures and sha256_file(inventory) == HEAVY_SHA and tree.hexdigest() == HEAVY_TREE
    return {"status": "PASS" if status else "FAIL", "entries": len(rows), "verified": len(rows) - len(failures), "failures": failures, "inventory_sha256": sha256_file(inventory), "execution_tree_sha256": tree.hexdigest()}


def load_and_recompute() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    metrics = []
    for trace in TRACES:
        frame = pd.read_parquet(OUT / trace / "metrics.parquet")
        frame["vm_id"] = frame.vm_id.astype(str)
        metrics.append(frame)
    metrics = pd.concat(metrics, ignore_index=True)
    keys = ["environment_key", "formulation", "resource", "lead", "horizon_minutes", "vm_id", "fold"]
    cells = metrics.groupby(keys, as_index=False).mae.mean().rename(columns={"mae": "seed_mean_mae"})
    lead = cells.groupby(keys[:5], as_index=False).seed_mean_mae.mean().rename(columns={"seed_mean_mae": "macro_mae"})
    lead["scope"] = "lead"
    overall = lead.groupby(["environment_key", "formulation", "resource"], as_index=False).macro_mae.mean()
    overall["lead"] = 0; overall["horizon_minutes"] = 0; overall["scope"] = "overall_equal_horizon"
    primary = pd.concat([lead, overall], ignore_index=True)
    return metrics, cells, primary


def recompute_comparisons(metrics: pd.DataFrame, cells: pd.DataFrame, primary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pooled_lead = metrics.assign(wx=metrics.mae * metrics.n).groupby(["environment_key", "formulation", "resource", "lead"], as_index=False).agg(wx=("wx", "sum"), n=("n", "sum"))
    pooled_lead["pooled_mae"] = pooled_lead.wx / pooled_lead.n
    pooled_all = metrics.assign(wx=metrics.mae * metrics.n).groupby(["environment_key", "formulation", "resource"], as_index=False).agg(wx=("wx", "sum"), n=("n", "sum"))
    pooled_all["pooled_mae"] = pooled_all.wx / pooled_all.n; pooled_all["lead"] = 0
    pooled = pd.concat([pooled_lead, pooled_all], ignore_index=True)
    rows, vm_rows, fold_rows, seed_rows = [], [], [], []
    for trace in TRACES:
        for comparison, (reference, candidate) in COMPARISONS_DEF.items():
            for resource in RESOURCES:
                for lead in (*LEADS, 0):
                    p = primary[(primary.environment_key == trace) & (primary.resource == resource) & (primary.lead == lead)].set_index("formulation").macro_mae
                    q = pooled[(pooled.environment_key == trace) & (pooled.resource == resource) & (pooled.lead == lead)].set_index("formulation").pooled_mae
                    subset = cells[(cells.environment_key == trace) & (cells.resource == resource)]
                    if lead:
                        subset = subset[subset.lead == lead]
                    else:
                        subset = subset.groupby(["formulation", "vm_id", "fold"], as_index=False).seed_mean_mae.mean()
                    pivot = subset.pivot(index=["vm_id", "fold"], columns="formulation", values="seed_mean_mae")
                    rel = gain(pivot[reference], pivot[candidate])
                    rows.append({"trace": trace, "comparison": comparison, "resource": resource, "scope": "lead" if lead else "overall", "lead": lead, "primary_macro_gain_percent": float(gain(p[reference], p[candidate])), "pooled_gain_percent": float(gain(q[reference], q[candidate])), "mean_cell_relative_gain_percent": float(rel.mean()), "median_cell_relative_gain_percent": float(rel.median()), "positive_cell_fraction": float((rel > 0).mean())})
                base = cells[(cells.environment_key == trace) & (cells.resource == resource)]
                v = base.groupby(["formulation", "vm_id"], as_index=False).seed_mean_mae.mean().pivot(index="vm_id", columns="formulation", values="seed_mean_mae")
                for key, value in gain(v[reference], v[candidate]).items(): vm_rows.append({"trace": trace, "comparison": comparison, "resource": resource, "vm_id": key, "gain_percent": value, "positive": value > 0})
                f = base.groupby(["formulation", "fold"], as_index=False).seed_mean_mae.mean().pivot(index="fold", columns="formulation", values="seed_mean_mae")
                for key, value in gain(f[reference], f[candidate]).items(): fold_rows.append({"trace": trace, "comparison": comparison, "resource": resource, "fold": key, "gain_percent": value, "positive": value > 0})
                s = metrics[(metrics.environment_key == trace) & (metrics.resource == resource)].groupby(["formulation", "seed"], as_index=False).mae.mean().pivot(index="seed", columns="formulation", values="mae")
                for key, value in gain(s[reference], s[candidate]).items(): seed_rows.append({"trace": trace, "comparison": comparison, "resource": resource, "seed": key, "gain_percent": value, "positive": value > 0})
    return pd.DataFrame(rows), pd.DataFrame(vm_rows), pd.DataFrame(fold_rows), pd.DataFrame(seed_rows)


def recompute_classes(comparisons: pd.DataFrame, vm: pd.DataFrame, fold: pd.DataFrame, seed: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for trace in TRACES:
        for comparison in COMPARISONS_DEF:
            for resource in RESOURCES:
                q = comparisons[(comparisons.trace == trace) & (comparisons.comparison == comparison) & (comparisons.resource == resource)]
                overall = float(q[q.scope == "overall"].primary_macro_gain_percent.iloc[0])
                horizons = int((q[q.scope == "lead"].primary_macro_gain_percent > 0).sum())
                vms = int(vm[(vm.trace == trace) & (vm.comparison == comparison) & (vm.resource == resource)].positive.sum())
                folds = int(fold[(fold.trace == trace) & (fold.comparison == comparison) & (fold.resource == resource)].positive.sum())
                seeds = int(seed[(seed.trace == trace) & (seed.comparison == comparison) & (seed.resource == resource)].positive.sum())
                if overall >= 1 and horizons >= 4 and vms >= 25 and folds >= 4 and seeds >= 2: label = "BROAD_POSITIVE"
                elif overall > 0 and horizons >= 3 and vms >= 15 and folds >= 3 and seeds >= 2: label = "CONDITIONALLY_POSITIVE"
                elif overall <= -1 and horizons <= 1 and vms <= 10 and folds <= 1 and seeds <= 1: label = "BROAD_NEGATIVE"
                else: label = "NEUTRAL_OR_MIXED"
                rows.append({"trace": trace, "comparison": comparison, "resource": resource, "overall_primary_gain_percent": overall, "positive_horizons": horizons, "positive_vms": vms, "positive_folds": folds, "positive_seed_aggregates": seeds, "classification": label})
    return pd.DataFrame(rows)


def recompute_trace_decisions(classes: pd.DataFrame) -> dict:
    result = {}
    for trace in TRACES:
        result[trace] = {}
        s2 = classes[(classes.trace == trace) & (classes.comparison == "S2_vs_S1")]
        pos = int(s2.classification.isin(POSITIVE).sum()); neg = int((s2.classification == "BROAD_NEGATIVE").sum()); mean = float(s2.overall_primary_gain_percent.mean())
        label = "CROSS_RESOURCE_INPUT_SUPPORTED" if pos >= 3 and mean > 0 and neg <= 1 else ("CROSS_RESOURCE_INPUT_NOT_SUPPORTED" if ((pos <= 1 and mean <= 0) or neg >= 2) else "CROSS_RESOURCE_INPUT_MIXED")
        result[trace]["S2_vs_S1"] = label
        m1 = classes[(classes.trace == trace) & (classes.comparison == "M1_vs_S2")]
        pos = int(m1.classification.isin(POSITIVE).sum()); broad_neg = int((m1.classification == "BROAD_NEGATIVE").sum()); material = int((m1.overall_primary_gain_percent <= -1).sum()); mean = float(m1.overall_primary_gain_percent.mean()); trade = bool(m1.overall_primary_gain_percent.max() >= 1 and m1.overall_primary_gain_percent.min() <= -1)
        if (pos >= 1 and material >= 2) or trade: label = "SHARED_REPRESENTATION_NEGATIVE_TRANSFER"
        elif pos <= 1 and mean <= 0: label = "SHARED_REPRESENTATION_NOT_SUPPORTED"
        elif pos >= 3 and mean > 0 and broad_neg == 0: label = "SHARED_REPRESENTATION_SUPPORTED"
        elif mean > 0 and pos >= 2: label = "SHARED_REPRESENTATION_CONDITIONALLY_SUPPORTED"
        else: label = "SHARED_REPRESENTATION_NOT_SUPPORTED"
        result[trace]["M1_vs_S2"] = label
        j = classes[(classes.trace == trace) & (classes.comparison == "M1_vs_S1")]
        pos = int((j.overall_primary_gain_percent > 0).sum()); neg = int((j.overall_primary_gain_percent < 0).sum()); mean = float(j.overall_primary_gain_percent.mean())
        result[trace]["M1_vs_S1"] = "JOINT_SYSTEM_BROADLY_BENEFICIAL" if pos >= 3 and mean > 0 else ("JOINT_SYSTEM_BROADLY_HARMFUL" if neg >= 3 and mean < 0 else "JOINT_SYSTEM_MIXED")
    return result


def recompute_bootstrap(cells: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for trace in TRACES:
        vms = sorted(cells[cells.environment_key == trace].vm_id.unique())
        rng = np.random.default_rng(SEED)
        samples = rng.integers(0, len(vms), size=(REPLICATES, len(vms)))
        for comparison, (reference, candidate) in COMPARISONS_DEF.items():
            for resource in RESOURCES:
                for lead in (*LEADS, 0):
                    q = cells[(cells.environment_key == trace) & (cells.resource == resource)]
                    if lead: q = q[q.lead == lead]
                    p = q.groupby(["formulation", "vm_id"], as_index=False).seed_mean_mae.mean().pivot(index="vm_id", columns="formulation", values="seed_mean_mae").reindex(vms)
                    values = gain(p[reference].to_numpy()[samples].mean(axis=1), p[candidate].to_numpy()[samples].mean(axis=1))
                    rows.append({"trace": trace, "comparison": comparison, "resource": resource, "lead": lead, "lower_2_5_percent": np.percentile(values, 2.5), "median_percent": np.percentile(values, 50), "upper_97_5_percent": np.percentile(values, 97.5)})
    return pd.DataFrame(rows)


def main() -> None:
    checks = {}
    source_failures = [name for name, expected in SOURCE_HASHES.items() if sha256_file(OUT / name) != expected]
    checks["exact_source_hashes"] = {"status": "PASS" if not source_failures else "FAIL", "failures": source_failures, "source_count": len(SOURCE_HASHES)}
    metrics, cells, primary = load_and_recompute()
    stored_cells = pd.read_csv(ANALYSIS / "matched_vm_fold_cells.csv", dtype={"vm_id": str})
    stored_primary = pd.read_csv(ANALYSIS / "primary_macro_mae.csv")
    checks["seed_averaging"] = {"status": "PASS" if frame_close(cells, stored_cells, ["environment_key", "formulation", "resource", "lead", "vm_id", "fold"], ["seed_mean_mae"]) else "FAIL"}
    checks["VM_fold_MacroMAE_and_equal_horizon"] = {"status": "PASS" if frame_close(primary, stored_primary, ["environment_key", "formulation", "resource", "scope", "lead"], ["macro_mae"]) else "FAIL"}

    comp, vm, fold, seed = recompute_comparisons(metrics, cells, primary)
    stored_comp = pd.read_csv(COMPARISONS / "secondary_aggregation_diagnostics.csv")
    comp_ok = frame_close(comp, stored_comp, ["trace", "comparison", "resource", "scope", "lead"], ["primary_macro_gain_percent", "pooled_gain_percent", "mean_cell_relative_gain_percent", "median_cell_relative_gain_percent", "positive_cell_fraction"])
    checks["three_primary_gains_and_secondary_diagnostics"] = {"status": "PASS" if comp_ok else "FAIL", "rows": len(comp)}

    classes = recompute_classes(comp, vm, fold, seed)
    stored_classes = pd.read_csv(COMPARISONS / "resource_classifications.csv")
    class_numeric = frame_close(classes, stored_classes, ["trace", "comparison", "resource"], ["overall_primary_gain_percent", "positive_horizons", "positive_vms", "positive_folds", "positive_seed_aggregates"])
    class_labels = classes.sort_values(["trace", "comparison", "resource"]).classification.reset_index(drop=True).equals(stored_classes.sort_values(["trace", "comparison", "resource"]).classification.reset_index(drop=True))
    checks["positive_counts_and_resource_classifications"] = {"status": "PASS" if class_numeric and class_labels else "FAIL", "rows": len(classes)}

    expected_trace = recompute_trace_decisions(classes)
    stored_trace = json.loads((ANALYSIS / "trace_decisions.json").read_text())
    trace_ok = all(stored_trace[t][c]["label"] == expected_trace[t][c] for t in TRACES for c in COMPARISONS_DEF)
    checks["trace_level_decisions"] = {"status": "PASS" if trace_ok else "FAIL", "expected": expected_trace}

    boot = recompute_bootstrap(cells)
    stored_boot = pd.read_csv(COMPARISONS / "bootstrap_uncertainty.csv")
    boot_numeric = frame_close(boot, stored_boot, ["trace", "comparison", "resource", "lead"], ["lower_2_5_percent", "median_percent", "upper_97_5_percent"], 1e-9)
    boot_metadata = bool((stored_boot.replicates == REPLICATES).all() and (stored_boot.rng_seed == SEED).all() and (stored_boot.VM_draws == 35).all() and (stored_boot.folds_retained_per_VM == 5).all())
    checks["bootstrap_pairing_VM_resampling_replicates_seed"] = {"status": "PASS" if boot_numeric and boot_metadata else "FAIL", "rows": len(boot), "replicates": REPLICATES, "seed": SEED}

    stored_syn = pd.read_csv(SYNTHESIS / "equal_temporal_block_synthesis.csv")
    syn_ok = np.allclose(stored_syn.equal_temporal_block_gain_percent, stored_syn[list(TRACES)].mean(axis=1), rtol=1e-12, atol=1e-12)
    checks["equal_temporal_block_synthesis"] = {"status": "PASS" if syn_ok else "FAIL", "rows": len(stored_syn)}

    scientific = json.loads((ANALYSIS / "scientific_decisions.json").read_text())
    expected_labels = {
        "R1": "R1_RESOURCE_TEMPORAL_DEPENDENCE_CONFIRMED",
        "R2": "R2_NEGATIVE_SHARING_REPLICATED",
        "R3": "R3_JOINT_SYSTEM_UNDERPERFORMANCE_REPLICATED",
        "R4": "R4_TEMPORAL_HETEROGENEITY_CONFIRMED",
        "cross_resource_boundary": "CROSS_RESOURCE_BOUNDARY_STRENGTHENED",
        "shared_representation_boundary": "SHARED_REPRESENTATION_BOUNDARY_STRENGTHENED",
        "joint_system_boundary": "JOINT_SYSTEM_UNDERPERFORMANCE_STRENGTHENED",
        "paper_scope_gate": "MULTIDATASET_TEMPORAL_BOUNDARY_STUDY_STRONGLY_SUPPORTED",
        "stop_experimentation_gate": "STOP_EXPERIMENTATION_AND_WRITE",
    }
    checks["R1_R2_R3_R4_and_final_gates"] = {"status": "PASS" if all(scientific.get(k) == v for k, v in expected_labels.items()) else "FAIL", "expected": expected_labels}

    cross = pd.read_csv(SYNTHESIS / "cross_study_synthesis.csv")
    forbidden = [c for c in cross.columns if "pooled_global" in c.lower() or "global_score" in c.lower()]
    checks["cross_study_no_pooled_global_score"] = {"status": "PASS" if len(cross) == 12 and not forbidden else "FAIL", "rows": len(cross), "forbidden_columns": forbidden}
    figures = sorted(FIGURES.glob("*.png"))
    checks["diagnostic_figures"] = {"status": "PASS" if len(figures) == 12 else "FAIL", "count": len(figures), "files": [p.name for p in figures]}

    source = (BASE / "analyze_phase4d_materna_scientific.py").read_text().lower()
    forbidden_training = [token for token in ("import torch", "optimizer.step", ".backward(", "model.fit(") if token in source]
    checks["model_training_during_analysis"] = {"status": "PASS" if scientific.get("model_training_during_analysis") == 0 and not forbidden_training else "FAIL", "count": scientific.get("model_training_during_analysis"), "forbidden_tokens": forbidden_training}
    checks["frozen_execution_artifacts_unchanged"] = verify_heavy()

    failures = [name for name, value in checks.items() if value["status"] != "PASS"]
    output = {"status": "PASS" if not failures else "FAIL", "failures": failures, "checks": checks}
    OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
