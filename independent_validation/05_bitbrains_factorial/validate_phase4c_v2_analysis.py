#!/usr/bin/env python3
"""Independent recomputation gate for Phase 4C V2 scientific analysis."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / "outputs/scientific_v2"
ANALYSIS = OUT / "analysis"
COMPARISONS = OUT / "comparisons"
SYNTHESIS = OUT / "synthesis"
ENVIRONMENTS = ("fastStorage", "Rnd")
RESOURCES = ("CPU", "THROUGHPUT", "MEMORY", "DISK_WRITE")
LEADS = (1, 2, 4, 9, 18)
DEFINITIONS = {"S2_vs_S1": ("S1", "S2"), "M1_vs_S2": ("S2", "M1"), "M1_vs_S1": ("S1", "M1")}
HEAD = "549020a1a0b19d3c633d21cd13d2c8ff007225f1"
TAG = "phase4c-v2-dual-environment-execution-freeze-v1"
EXPECTED_HASHES = {
    "configs/bitbrains_lstm_factorial_phase4c_v2.json": "627391b84887411d8b930fd5d00cdd9a1f90f3990f958d582f4329424353fa4e",
    "EXTERNAL_SCIENTIFIC_DECISION_CRITERIA.md": "79df6a168d7021dbafd6080640a506d22699e9d4989d422f924b178600465f12",
    "protocol_amendment/PHASE4C_V2_EXECUTION_CORRECTION_DECISION.md": "bd0a51380409290dd9deefd2cf25bbc783b018b559121bd21ba37fdfcb07e86d",
    "outputs/scientific_v2/fastStorage/metrics.parquet": "3edbbe0d74a76b4a99ee110ef9f42919700cf4b88273b568924816e828a05309",
    "outputs/scientific_v2/Rnd/metrics.parquet": "4072332fde01457e7d1fc89086d840a730844d8a25366c0abaaf6d69c472de4c",
    "outputs/scientific_v2/fastStorage/persistence_metrics.parquet": "729d66bff8f16160968270d35e7908f62eaa3ff654d00ba72311621b4628b8ef",
    "outputs/scientific_v2/Rnd/persistence_metrics.parquet": "151d3f12030c31ab42c2fad068ac1d9de6fd8d8afb2303ec1934e768f7bd1d59",
}
BOOTSTRAP_SEED = 20261007
BOOTSTRAP_REPLICATES = 10_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_inventory(path: Path) -> tuple[int, list[str]]:
    rows = list(csv.DictReader(path.open(newline="")))
    failures = []
    for row in rows:
        artifact = ROOT / row["relative_path"]
        if not artifact.is_file() or artifact.stat().st_size != int(row["byte_size"]) or sha256(artifact) != row["sha256"]:
            failures.append(row["relative_path"])
    return len(rows), failures


def close(left: pd.Series, right: pd.Series, tolerance: float = 1e-10) -> bool:
    return bool(np.allclose(left.astype(float), right.astype(float), rtol=tolerance, atol=tolerance, equal_nan=True))


def classify(gain_value: float, horizons: int, vms: int, folds: int, seeds: int) -> str:
    if gain_value >= 1 and horizons >= 4 and vms >= 25 and folds >= 4 and seeds >= 2:
        return "BROAD_POSITIVE"
    if gain_value > 0 and horizons >= 3 and vms >= 15 and folds >= 3 and seeds >= 2:
        return "CONDITIONALLY_POSITIVE"
    if gain_value <= -1 and horizons <= 1 and vms <= 10 and folds <= 1 and seeds <= 1:
        return "BROAD_NEGATIVE"
    return "NEUTRAL_OR_MIXED"


def main() -> None:
    failures: list[str] = []
    checks: dict[str, object] = {}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    tag_target = subprocess.check_output(["git", "rev-parse", f"{TAG}^{{}}"], cwd=ROOT, text=True).strip()
    if head != HEAD or tag_target != HEAD:
        failures.append("checkpoint_identity")
    checks["checkpoint"] = {"head": head, "tag_target": tag_target}

    observed_hashes = {relative: sha256(BASE / relative) for relative in EXPECTED_HASHES}
    if observed_hashes != EXPECTED_HASHES:
        failures.append("input_hashes")
    checks["input_hashes"] = observed_hashes
    compact_count, compact_bad = verify_inventory(BASE / "PHASE4C_V2_EXECUTION_CHECKPOINT_SHA256.csv")
    heavy_count, heavy_bad = verify_inventory(OUT / "runtime/PHASE4C_V2_EXECUTION_ARTIFACT_SHA256.csv")
    if compact_count != 35 or compact_bad or heavy_count != 56723 or heavy_bad:
        failures.append("execution_inventory")
    checks["execution_inventory"] = {"compact_entries": compact_count, "compact_failures": compact_bad, "heavy_entries": heavy_count, "heavy_failures": heavy_bad}

    metrics = []
    for environment in ENVIRONMENTS:
        frame = pd.read_parquet(OUT / environment / "metrics.parquet")
        frame["vm_id"] = frame.vm_id.astype(str)
        metrics.append(frame)
    raw = pd.concat(metrics, ignore_index=True)
    if len(raw) != 63000:
        failures.append("metric_count")
    cell = raw.groupby(["environment_key", "formulation", "resource", "lead", "horizon_minutes", "vm_id", "fold"], as_index=False).mae.mean().rename(columns={"mae": "value"})
    if len(cell) != 21000:
        failures.append("seed_averaging")

    stored_primary = pd.read_csv(ANALYSIS / "primary_macro_mae.csv")
    expected_primary = cell.groupby(["environment_key", "formulation", "resource", "lead", "horizon_minutes"], as_index=False).value.mean()
    lead_rows = stored_primary[stored_primary.scope == "lead"].sort_values(["environment_key", "formulation", "resource", "lead"])
    expected_primary = expected_primary.sort_values(["environment_key", "formulation", "resource", "lead"])
    if len(lead_rows) != 120 or not close(lead_rows.macro_mae, expected_primary.value):
        failures.append("primary_macro_aggregation")
    stored_overall = stored_primary[stored_primary.scope == "overall_equal_horizon"].sort_values(["environment_key", "formulation", "resource"])
    expected_overall = expected_primary.groupby(["environment_key", "formulation", "resource"], as_index=False).value.mean().sort_values(["environment_key", "formulation", "resource"])
    if len(stored_overall) != 24 or not close(stored_overall.macro_mae, expected_overall.value):
        failures.append("equal_horizon_aggregation")

    stored_comparisons = pd.read_csv(COMPARISONS / "secondary_aggregation_diagnostics.csv")
    vm_expected = []
    fold_expected = []
    seed_expected = []
    classification_expected = []
    gain_lookup: dict[tuple[str, str, str], float] = {}
    for environment in ENVIRONMENTS:
        for comparison, (reference, candidate) in DEFINITIONS.items():
            for resource in RESOURCES:
                subset = cell[(cell.environment_key == environment) & (cell.resource == resource)]
                lead_gains = []
                for lead in LEADS:
                    values = subset[subset.lead == lead].groupby("formulation").value.mean()
                    expected_gain = 100 * (values[reference] - values[candidate]) / values[reference]
                    observed = stored_comparisons[(stored_comparisons.environment == environment) & (stored_comparisons.comparison == comparison) & (stored_comparisons.resource == resource) & (stored_comparisons.lead == lead)]
                    if len(observed) != 1 or not np.isclose(float(observed.primary_macro_gain_percent.iloc[0]), expected_gain, rtol=1e-10, atol=1e-10):
                        failures.append(f"lead_gain:{environment}:{comparison}:{resource}:{lead}")
                    lead_gains.append(expected_gain)
                by_cell = subset.groupby(["formulation", "vm_id", "fold"], as_index=False).value.mean().pivot(index=["vm_id", "fold"], columns="formulation", values="value")
                overall_gain = float(100 * (by_cell[reference].mean() - by_cell[candidate].mean()) / by_cell[reference].mean())
                gain_lookup[(environment, comparison, resource)] = overall_gain
                observed = stored_comparisons[(stored_comparisons.environment == environment) & (stored_comparisons.comparison == comparison) & (stored_comparisons.resource == resource) & (stored_comparisons.scope == "overall")]
                relative = 100 * (by_cell[reference] - by_cell[candidate]) / by_cell[reference]
                if len(observed) != 1 or not np.isclose(float(observed.primary_macro_gain_percent.iloc[0]), overall_gain) or not np.isclose(float(observed.mean_cell_relative_gain_percent.iloc[0]), relative.mean()) or not np.isclose(float(observed.median_cell_relative_gain_percent.iloc[0]), relative.median()):
                    failures.append(f"overall_or_cell_gain:{environment}:{comparison}:{resource}")

                vm = by_cell.groupby("vm_id")[[reference, candidate]].mean()
                vm_gain = 100 * (vm[reference] - vm[candidate]) / vm[reference]
                fold = by_cell.groupby("fold")[[reference, candidate]].mean()
                fold_gain = 100 * (fold[reference] - fold[candidate]) / fold[reference]
                seed = raw[(raw.environment_key == environment) & (raw.resource == resource)].groupby(["formulation", "seed"]).mae.mean().unstack("formulation")
                seed_gain = 100 * (seed[reference] - seed[candidate]) / seed[reference]
                vm_expected.extend(vm_gain.tolist()); fold_expected.extend(fold_gain.tolist()); seed_expected.extend(seed_gain.tolist())
                counts = (sum(value > 0 for value in lead_gains), int((vm_gain > 0).sum()), int((fold_gain > 0).sum()), int((seed_gain > 0).sum()))
                classification_expected.append({"environment": environment, "comparison": comparison, "resource": resource, "overall_primary_gain_percent": overall_gain, "positive_horizons": counts[0], "positive_vms": counts[1], "positive_folds": counts[2], "positive_seed_aggregates": counts[3], "classification": classify(overall_gain, *counts)})

    for filename, values in [("positive_vm_signs.csv", vm_expected), ("positive_fold_signs.csv", fold_expected), ("positive_seed_signs.csv", seed_expected)]:
        observed = pd.read_csv(ANALYSIS / filename)
        if len(observed) != len(values) or not np.allclose(np.sort(observed.gain_percent), np.sort(values)):
            failures.append(filename)
    expected_class = pd.DataFrame(classification_expected).sort_values(["environment", "comparison", "resource"]).reset_index(drop=True)
    observed_class = pd.read_csv(COMPARISONS / "resource_classifications.csv").sort_values(["environment", "comparison", "resource"]).reset_index(drop=True)
    classification_keys = ["environment", "comparison", "resource", "positive_horizons", "positive_vms", "positive_folds", "positive_seed_aggregates", "classification"]
    if (
        not expected_class[classification_keys].equals(observed_class[classification_keys])
        or not close(expected_class.overall_primary_gain_percent, observed_class.overall_primary_gain_percent)
    ):
        failures.append("resource_classifications")

    environment_decisions = json.loads((ANALYSIS / "environment_decisions.json").read_text())
    expected_environment_labels = {
        "fastStorage": {"S2_vs_S1": "CROSS_RESOURCE_INPUT_MIXED", "M1_vs_S2": "SHARED_REPRESENTATION_NEGATIVE_TRANSFER"},
        "Rnd": {"S2_vs_S1": "CROSS_RESOURCE_INPUT_MIXED", "M1_vs_S2": "SHARED_REPRESENTATION_NOT_SUPPORTED"},
    }
    for environment, labels in expected_environment_labels.items():
        for comparison, label in labels.items():
            if environment_decisions[environment][comparison]["label"] != label:
                failures.append(f"environment_decision:{environment}:{comparison}")

    stored_bootstrap = pd.read_csv(COMPARISONS / "bootstrap_uncertainty.csv")
    for environment in ENVIRONMENTS:
        vms = sorted(cell[cell.environment_key == environment].vm_id.unique())
        samples = np.random.default_rng(BOOTSTRAP_SEED).integers(0, len(vms), size=(BOOTSTRAP_REPLICATES, len(vms)))
        for comparison, (reference, candidate) in DEFINITIONS.items():
            for resource in RESOURCES:
                for lead in (*LEADS, 0):
                    subset = cell[(cell.environment_key == environment) & (cell.resource == resource)]
                    if lead:
                        subset = subset[subset.lead == lead]
                    by_vm = subset.groupby(["formulation", "vm_id"], as_index=False).value.mean().pivot(index="vm_id", columns="formulation", values="value").reindex(vms)
                    ref = by_vm[reference].to_numpy(); cand = by_vm[candidate].to_numpy()
                    values = 100 * (ref[samples].mean(axis=1) - cand[samples].mean(axis=1)) / ref[samples].mean(axis=1)
                    expected = np.percentile(values, [2.5, 50, 97.5])
                    observed = stored_bootstrap[(stored_bootstrap.environment == environment) & (stored_bootstrap.comparison == comparison) & (stored_bootstrap.resource == resource) & (stored_bootstrap.lead == lead)]
                    if len(observed) != 1 or int(observed.replicates.iloc[0]) != 10000 or int(observed.rng_seed.iloc[0]) != BOOTSTRAP_SEED or not np.allclose(observed[["lower_2_5_percent", "median_percent", "upper_97_5_percent"]].iloc[0], expected):
                        failures.append(f"bootstrap:{environment}:{comparison}:{resource}:{lead}")

    synthesis = pd.read_csv(SYNTHESIS / "equal_environment_synthesis.csv")
    for row in synthesis.itertuples(index=False):
        expected = (row.fastStorage + row.Rnd) / 2
        if not np.isclose(row.synthesized_gain_percent, expected):
            failures.append("equal_environment_synthesis")
            break
    decisions = json.loads((ANALYSIS / "scientific_decisions.json").read_text())
    expected_decisions = {
        "H1": "H1_BOUNDARY_PARTIALLY_REPLICATED",
        "H2": "H2_BOUNDARY_CONFIRMED",
        "H3": "HETEROGENEITY_CONFIRMED",
        "final_phase4c_outcome": "BOUNDARY_PARTIALLY_REPLICATED",
        "publication_scope_gate": "MULTIDATASET_BOUNDARY_STUDY_SUPPORTED_WITH_MIXED_REPLICATION",
        "materna_gate": "MATERNA_USEFUL_SECONDARY_REPLICATION",
        "new_architecture_gate": "NO",
        "model_training_during_analysis": 0,
    }
    for key, expected in expected_decisions.items():
        if decisions.get(key) != expected:
            failures.append(f"decision:{key}")

    figures = sorted((OUT / "figures").glob("*.png"))
    if len(figures) != 12 or [int(path.name[:2]) for path in figures] != list(range(1, 13)):
        failures.append("figure_count")
    analysis_source = (BASE / "analyze_phase4c_v2_scientific.py").read_text()
    forbidden = [token for token in ("model.fit(", "optimizer.step(", "torch.optim", "fit_inner(", "fit_final") if token in analysis_source]
    if forbidden:
        failures.append("training_code_present")
    report = (BASE / "PHASE4C_V2_EXTERNAL_CONFIRMATION_REPORT.md").read_text()
    if "no pooled cross-dataset score was calculated" not in report or "Materna was not executed" not in report:
        failures.append("scope_guards")
    checks.update({
        "metric_rows": len(raw), "seed_averaged_cells": len(cell), "primary_lead_cells": len(lead_rows),
        "bootstrap_rows": len(stored_bootstrap), "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "figure_count": len(figures), "forbidden_training_tokens": forbidden,
        "no_timetrack_bitbrains_pooling": "no pooled cross-dataset score was calculated" in report,
        "model_training_during_analysis": 0,
    })
    result = {"status": "PASS" if not failures else "FAIL", "failures": failures, "checks": checks, "validated_decisions": expected_decisions}
    (ANALYSIS / "PHASE4C_V2_ANALYSIS_VALIDATION.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
