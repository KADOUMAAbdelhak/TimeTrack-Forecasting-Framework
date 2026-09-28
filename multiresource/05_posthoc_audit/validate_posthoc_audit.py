#!/usr/bin/env python3
"""Independent validation for the Phase 3D post-hoc audit."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import rankdata

from benchmark.neural_v2.validate_dlinear_scientific import phase2a_hashes, sha256 as file_sha256, verify_inventory
from benchmark.src.data import PANEL_PATH, verify_raw_hashes
from src.data import MACHINES, RESOURCE_ORDER, load_panel, target_columns
from src.splits import build_factorial_folds
from src.transforms import transform_resource


ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
P3C = ROOT / "multiresource/04_lstm_factorial"
SCI = P3C / "outputs/scientific"
OUT = BASE / "outputs"
FIG = BASE / "figures"
EXPECTED_PROTOCOL = "c1ed2d6ae3ee3afe20c70b8561cc58d340c0ee70e0686e642f461b7e0f702da8"
EXPECTED_INVENTORY = "95bbb842f60bbc8c2c1bc11704c413e8e654594476d16c40850a217913c5155e"
EXPECTED_TREE = "ec35446710f90a7b1e1a86cdbca6bedd4face31ec68ea56e83fd682addd89a65"
EXPECTED_PANEL = "c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a"
EXPECTED_PRIMARY = {
    ("S2_vs_S1", "CPU"): -3.3130,
    ("S2_vs_S1", "THROUGHPUT"): -0.2428,
    ("S2_vs_S1", "MEMORY"): 0.8594,
    ("S2_vs_S1", "DISK_WRITE"): -0.4923,
    ("M1_vs_S2", "CPU"): 0.4696,
    ("M1_vs_S2", "THROUGHPUT"): -0.8401,
    ("M1_vs_S2", "MEMORY"): -18.4769,
    ("M1_vs_S2", "DISK_WRITE"): -0.7956,
    ("M1_vs_S1", "CPU"): -2.8279,
    ("M1_vs_S1", "THROUGHPUT"): -1.0849,
    ("M1_vs_S1", "MEMORY"): -17.4587,
    ("M1_vs_S1", "DISK_WRITE"): -1.2918,
}
EXPECTED_FIGURES = {
    "01_s2_vs_s1_machine_lead_heatmaps.png",
    "02_m1_vs_s2_machine_lead_heatmaps.png",
    "03_s2_vs_s1_fold_gains.png",
    "04_m1_vs_s2_fold_gains.png",
    "05_regime_conditional_s2_vs_s1.png",
    "06_dependency_vs_context_gain.png",
    "07_loss_share_vs_m1_s2_gain.png",
    "08_memory_failure_decomposition.png",
    "09_benefit_concentration.png",
    "10_posthoc_bootstrap_uncertainty.png",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def verify_phase3c_tree() -> tuple[int, int, str, list[str]]:
    inventory = P3C / "PHASE3C_SCIENTIFIC_ARTIFACT_SHA256.csv"
    failures = []
    tree = hashlib.sha256()
    entries = 0
    total_bytes = 0
    with inventory.open(newline="") as stream:
        for row in csv.DictReader(stream):
            path = ROOT / row["relative_path"]
            size = int(row["byte_size"])
            expected = row["sha256"]
            entries += 1
            total_bytes += size
            if not path.exists() or path.stat().st_size != size or digest(path) != expected:
                failures.append(row["relative_path"])
            tree.update(f"{row['relative_path']},{size},{expected}\n".encode())
    return entries, total_bytes, tree.hexdigest(), failures


def descriptor_values(panel: pd.DataFrame, machine: str, origins: np.ndarray) -> dict[str, np.ndarray]:
    origins = np.asarray(origins, dtype=np.int64)
    history = origins[:, None] - np.arange(31, -1, -1)
    native = panel.loc[:, list(target_columns(machine))].to_numpy(float)[history]
    transformed = np.stack([transform_resource(native[:, :, i], resource) for i, resource in enumerate(RESOURCE_ORDER)], axis=-1)
    values = {
        "cpu_mean_transformed": transformed[:, :, 0].mean(axis=1),
        "cpu_std_transformed": transformed[:, :, 0].std(axis=1),
        "throughput_mean_transformed": transformed[:, :, 1].mean(axis=1),
        "throughput_std_transformed": transformed[:, :, 1].std(axis=1),
        "memory_mean_transformed": transformed[:, :, 2].mean(axis=1),
        "memory_std_transformed": transformed[:, :, 2].std(axis=1),
        "memory_absdiff_mean_transformed": np.abs(np.diff(transformed[:, :, 2], axis=1)).mean(axis=1),
        "disk_write_mean_transformed": transformed[:, :, 3].mean(axis=1),
        "disk_write_std_transformed": transformed[:, :, 3].std(axis=1),
    }
    cpu_rank = rankdata(transformed[:, :, 0], axis=1)
    throughput_rank = rankdata(transformed[:, :, 1], axis=1)
    cpu = cpu_rank - cpu_rank.mean(axis=1, keepdims=True)
    throughput = throughput_rank - throughput_rank.mean(axis=1, keepdims=True)
    denominator = np.sqrt(np.sum(cpu**2, axis=1) * np.sum(throughput**2, axis=1))
    values["cpu_throughput_spearman"] = np.divide(np.sum(cpu*throughput, axis=1), denominator, out=np.full(len(origins), np.nan), where=denominator>0)
    return values


def validate_sources_no_training() -> tuple[list[str], int]:
    violations = []
    architecture_definitions = 0
    for source in sorted(BASE.glob("*.py")):
        tree = ast.parse(source.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                if any(module.split(".")[0] in {"torch", "tensorflow", "keras", "jax"} for module in modules):
                    violations.append(f"{source.name}: training framework import")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"fit", "step", "backward", "train"}:
                violations.append(f"{source.name}: training call {node.func.attr}")
            if isinstance(node, ast.ClassDef):
                architecture_definitions += 1
    return violations, architecture_definitions


def main() -> None:
    failures: list[str] = []
    checks: dict[str, object] = {}
    checks["protocol_sha256"] = digest(BASE / "POSTHOC_PROTOCOL.md")
    if checks["protocol_sha256"] != EXPECTED_PROTOCOL:
        failures.append("protocol identity")
    checks["phase3c_inventory_sha256"] = digest(P3C / "PHASE3C_SCIENTIFIC_ARTIFACT_SHA256.csv")
    if checks["phase3c_inventory_sha256"] != EXPECTED_INVENTORY:
        failures.append("Phase 3C inventory identity")
    entries, total_bytes, tree_hash, artifact_failures = verify_phase3c_tree()
    checks.update({"phase3c_inventory_entries": entries, "phase3c_inventory_bytes": total_bytes, "phase3c_scientific_tree_sha256": tree_hash, "phase3c_artifact_mismatches": len(artifact_failures)})
    if tree_hash != EXPECTED_TREE or artifact_failures:
        failures.append("Phase 3C scientific tree")
    prediction_inventory = pd.read_csv(P3C / "PHASE3C_SCIENTIFIC_ARTIFACT_SHA256.csv")
    prediction_rows = prediction_inventory.relative_path.str.contains("/predictions/")
    checks["frozen_prediction_files_verified"] = int(prediction_rows.sum())
    if prediction_rows.sum() != 945:
        failures.append("prediction inventory count")

    primary = pd.read_csv(OUT / "phase3c_primary_reproduction.csv")
    primary_errors = []
    for row in primary.itertuples(index=False):
        expected = EXPECTED_PRIMARY[(row.comparison, row.resource)]
        if not np.isclose(row.gain_pct, expected, atol=5e-5, rtol=0):
            primary_errors.append((row.comparison, row.resource))
    checks["primary_reproduction_rows"] = len(primary)
    checks["primary_reproduction_mismatches"] = len(primary_errors)
    if len(primary) != 12 or primary_errors:
        failures.append("Phase 3C primary reproduction")

    cell = pd.read_parquet(OUT / "cell_level_gain_matrix.parquet")
    checks["cell_matrix_rows"] = len(cell)
    if len(cell) != 3*4*7*5*8 or cell[["comparison","resource","machine","fold","lead"]].duplicated().any():
        failures.append("cell matrix shape/uniqueness")
    if not np.allclose(cell.gain_pct, 100*(cell.mae_reference-cell.mae_candidate)/cell.mae_reference, rtol=0, atol=1e-12):
        failures.append("cell gain recomputation")

    sample_file = pq.ParquetFile(OUT / "sample_error_differences.parquet")
    checks["sample_error_rows"] = sample_file.metadata.num_rows
    required = {"comparison","resource","machine","fold","seed","lead","origin_index","sample_id","origin_timestamp","target_timestamp","reference_absolute_error","candidate_absolute_error","delta_absolute_error","reference_signed_error","candidate_signed_error"}
    if not required.issubset(set(sample_file.schema.names)):
        failures.append("sample error schema")
    delta_error = 0.0
    for batch in sample_file.iter_batches(columns=["reference_absolute_error","candidate_absolute_error","delta_absolute_error"], batch_size=250000):
        frame = batch.to_pandas()
        delta_error = max(delta_error, float(np.max(np.abs(frame.reference_absolute_error-frame.candidate_absolute_error-frame.delta_absolute_error))))
    checks["sample_delta_max_abs_error"] = delta_error
    if delta_error > 1e-12:
        failures.append("sample delta recomputation")

    panel = load_panel()
    descriptors = pd.read_parquet(OUT / "origin_regime_descriptors.parquet")
    thresholds = pd.read_csv(OUT / "regime_thresholds.csv")
    threshold_mismatch = 0
    descriptor_origin_mismatch = 0
    segment_crossing = 0
    future_descriptor_access = 0
    timestamps = panel.timestamp.to_numpy()
    segments = panel.segment_id.to_numpy(np.int64)
    for machine in MACHINES:
        for fold in build_factorial_folds(panel, machine, 32):
            observed = descriptors[(descriptors.machine.eq(machine)) & (descriptors.fold.eq(fold.fold))]
            if not np.array_equal(np.sort(observed.origin_index.to_numpy(np.int64)), fold.outer_test):
                descriptor_origin_mismatch += 1
            if not np.array_equal(observed.sort_values("origin_index").origin_timestamp.to_numpy(), timestamps[fold.outer_test]):
                descriptor_origin_mismatch += 1
            history = fold.outer_test[:, None] - np.arange(31, -1, -1)
            segment_crossing += int(np.sum(~np.all(segments[history] == segments[fold.outer_test, None], axis=1)))
            future_descriptor_access += int(history.max(axis=1).max() > fold.outer_test.max())
            train_values = descriptor_values(panel, machine, fold.outer_train)
            for descriptor, values in train_values.items():
                finite = values[np.isfinite(values)]
                expected_q33, expected_q67 = np.quantile(finite, [.33, .67])
                row = thresholds[(thresholds.machine.eq(machine)) & (thresholds.fold.eq(fold.fold)) & (thresholds.descriptor.eq(descriptor))].iloc[0]
                threshold_mismatch += int(not np.isclose(row.q33, expected_q33, rtol=1e-14, atol=1e-12) or not np.isclose(row.q67, expected_q67, rtol=1e-14, atol=1e-12) or row.source_partition != "legal_outer_train" or row.history_window != 32)
    checks.update({"descriptor_origin_mismatches": descriptor_origin_mismatch, "descriptor_segment_crossings": segment_crossing, "future_descriptor_access": future_descriptor_access, "training_threshold_mismatches": threshold_mismatch})
    if descriptor_origin_mismatch or segment_crossing or future_descriptor_access or threshold_mismatch:
        failures.append("origin-time regime legality")

    regime_expected = {"CPU":5,"THROUGHPUT":4,"MEMORY":5,"DISK_WRITE":4}
    for comparison in ("s2_vs_s1","m1_vs_s2"):
        regime = pd.read_csv(OUT / f"{comparison}_regime_analysis.csv", dtype={"lead":str})
        observed = regime[regime.lead.eq("OVERALL")].groupby("resource").descriptor.nunique().to_dict()
        if observed != regime_expected or set(regime.regime_bin) != {"LOW","MID","HIGH"}:
            failures.append(f"controlled regime inventory {comparison}")
    source_violations, architecture_definitions = validate_sources_no_training()
    checks["training_source_violations"] = source_violations
    checks["phase3d_forecasting_fits"] = 0
    checks["post_phase3c_architecture_implementations"] = architecture_definitions
    if source_violations:
        failures.append("training code present")
    if architecture_definitions:
        failures.append("Phase 3D architecture definition present")

    bootstrap = pd.read_csv(OUT / "posthoc_bootstrap_uncertainty.csv", dtype={"lead":str})
    checks["bootstrap_rows"] = len(bootstrap)
    if len(bootstrap) != 3*4*9 or set(bootstrap.replicates) != {10000} or not bootstrap.label.eq("POST-HOC BOOTSTRAP UNCERTAINTY INTERVAL").all():
        failures.append("bootstrap output")
    memory = pd.read_csv(OUT / "memory_failure_decomposition.csv")
    checks["memory_decomposition_rows"] = len(memory)
    if len(memory) != 7*5*3*8:
        failures.append("memory decomposition shape")
    figure_names = {path.name for path in FIG.glob("*.png") if path.stat().st_size > 0}
    checks["figure_count"] = len(figure_names)
    if figure_names != EXPECTED_FIGURES:
        failures.append("figure inventory")

    histories = {
        "phase3b": (P3C / "PHASE3B_ARTIFACT_SHA256.csv", 31),
        "phase3a": (ROOT / "multiresource/PHASE3A_ARTIFACT_SHA256.csv", 25),
        "neural_v2": (ROOT / "benchmark/neural_v2/NEURAL_V2_ARTIFACT_SHA256.csv", 29),
        "dlinear": (ROOT / "benchmark/neural_v2/DLINEAR_SCIENTIFIC_ARTIFACT_SHA256.csv", 1347),
        "lstm": (ROOT / "benchmark/neural_v2/LSTM_SCIENTIFIC_ARTIFACT_SHA256.csv", 1349),
        "patchtst": (ROOT / "benchmark/neural_v2/PATCHTST_SCIENTIFIC_ARTIFACT_SHA256.csv", 1352),
        "original": (ROOT / "benchmark/phase2b1_original/HEAVY_ARTIFACT_SHA256.csv", 632),
        "corrected": (ROOT / "benchmark/phase2b1_corrected/CORRECTION_ARTIFACT_SHA256.csv", 1070),
    }
    frozen = {}
    for name, (path, expected) in histories.items():
        count, bad = verify_inventory(path)
        frozen[name] = {"count": count, "expected": expected, "pass": count == expected and not bad}
        if not frozen[name]["pass"]:
            failures.append(f"frozen {name}")
    phase2a_count, phase2a_bad = phase2a_hashes()
    frozen["phase2a"] = {"count": phase2a_count, "expected": 33, "pass": phase2a_count == 33 and not phase2a_bad}
    if not frozen["phase2a"]["pass"]:
        failures.append("frozen phase2a")
    raw = verify_raw_hashes()
    canonical = file_sha256(PANEL_PATH)
    if not raw or canonical != EXPECTED_PANEL:
        failures.append("raw/canonical integrity")
    checks.update({"frozen_history": frozen, "raw_hashes_unchanged": raw, "canonical_panel_sha256": canonical})

    result = {"status": "PASS" if not failures else "FAIL", "failures": failures, "checks": checks, "posthoc_only": True, "no_model_execution": not source_violations, "phase3c_artifacts_unchanged": not artifact_failures and tree_hash == EXPECTED_TREE, "figure_count": len(figure_names)}
    (BASE / "validation.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if not failures:
        report = (BASE / "PHASE3D_POSTHOC_REPORT.md").read_text().replace("Validation status: **PENDING**.", "Validation status: **PASS**.")
        (BASE / "PHASE3D_POSTHOC_REPORT.md").write_text(report)
        metadata_path = OUT / "audit_metadata.json"
        metadata = json.loads(metadata_path.read_text())
        metadata["status"] = "VALIDATED_PASS"
        metadata["validation_path"] = "multiresource/05_posthoc_audit/validation.json"
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures:
        raise RuntimeError("Phase 3D validation failed")


if __name__ == "__main__":
    main()
