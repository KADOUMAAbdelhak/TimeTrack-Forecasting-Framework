#!/usr/bin/env python3
"""Independent technical-only validation and inventory for completed Phase 4C V2.

This utility deliberately reads metric Parquet metadata only. It never loads or
summarizes predictive metric values.
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE / "outputs/scientific_v2"
VALIDATION = OUT / "validation"
RUNTIME = OUT / "runtime"
HEAD = "30cb7b042726b6e6db8c6bf5ed43324b620ca42e"
TAG = "phase4c-v2-execution-conformance-freeze-v1"
AMENDMENT_COMMIT = "5a643567f466c66a5134e41d8c0ae05f8b971763"
AMENDMENT_TAG = "phase4c-bitbrains-training-scale-amendment-freeze-v1"
CONFIG_HASH = "627391b84887411d8b930fd5d00cdd9a1f90f3990f958d582f4329424353fa4e"
CRITERIA_HASH = "79df6a168d7021dbafd6080640a506d22699e9d4989d422f924b178600465f12"
CORRECTION_HASH = "bd0a51380409290dd9deefd2cf25bbc783b018b559121bd21ba37fdfcb07e86d"
CORRECTION_INVENTORY_HASH = "e01a6f35050474b328ecf2f88823bbf1114f84857e4162d221330ba0b211bfd4"
CORRECTED_TREE_HASH = "8e1f303fe08b3bfa5c5c04e8dd55e0da275b6cc64661da1848cacc8c7111b067"
ENVIRONMENTS = ("fastStorage", "Rnd")
EXPECTED = {
    "inner": {"S1": 6300, "S2": 6300, "M1": 1575},
    "final": {"S1": 2100, "S2": 2100, "M1": 525},
    "metrics": 31500,
    "persistence": 31500,
    "contexts": 1575,
    "epochs": 4725,
}
RAW_HASHES = {
    "gwa_t_12_fastStorage.zip": "11313f528a0cbcbe57e63162f8ae5a41a9c7e7c1a79872e294ff3c5bbaa2e671",
    "gwa_t_12_rnd.zip": "d3d9ddebb689c0b5463f2e4cfd8956e84bdcdf138b4476320855393e2b229a06",
    "gwa_t_13_materna.zip": "1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4",
}
INVENTORY_PATH = RUNTIME / "PHASE4C_V2_EXECUTION_ARTIFACT_SHA256.csv"
INVENTORY_SUMMARY_PATH = RUNTIME / "PHASE4C_V2_EXECUTION_INVENTORY_SUMMARY.json"
COMBINED_PATH = VALIDATION / "combined_technical_validation.json"
ACCOUNTING_PATH = RUNTIME / "combined_runtime_storage_accounting.json"
INVENTORY_EXCLUSIONS = {INVENTORY_PATH, INVENTORY_SUMMARY_PATH}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def parquet_rows(path: Path) -> int:
    return int(pq.ParquetFile(path).metadata.num_rows)


def verify_hash_inventory(path: Path) -> tuple[int, list[str]]:
    frame = pd.read_csv(path)
    failures = []
    for row in frame.itertuples(index=False):
        artifact = ROOT / str(row.relative_path)
        if (
            not artifact.is_file()
            or artifact.stat().st_size != int(row.byte_size)
            or sha256(artifact) != str(row.sha256)
        ):
            failures.append(str(row.relative_path))
    return len(frame), failures


def load_completions(environment: str, phase: str) -> list[tuple[Path, dict[str, Any]]]:
    directory = OUT / environment / "runtime/completions" / phase
    return [(path, json.loads(path.read_text())) for path in sorted(directory.glob("*.json"))]


def distribution(frame: pd.DataFrame, column: str) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for formulation, group in frame.groupby("formulation", sort=True):
        counts = group[column].astype(int).value_counts().sort_index()
        result[str(formulation)] = {str(int(key)): int(value) for key, value in counts.items()}
    return result


def stage_runtime(records: list[tuple[Path, dict[str, Any]]], phase: str) -> dict[str, Any]:
    durations: dict[str, list[float]] = defaultdict(list)
    peak = 0
    for _path, row in records:
        formulation = str(row["identity"]["formulation"])
        seconds = float(row["train_seconds"])
        if phase == "inner":
            seconds += float(row["validation_seconds"])
        durations[formulation].append(seconds)
        peak = max(peak, int(row.get("peak_rss_bytes", 0)))
    return {
        formulation: {
            "fits": len(values),
            "fit_hours": sum(values) / 3600.0,
            "mean_fit_seconds": statistics.fmean(values),
            "median_fit_seconds": statistics.median(values),
        }
        for formulation, values in sorted(durations.items())
    } | {"peak_rss_bytes": peak}


def storage_category(path: Path) -> str:
    relative = path.relative_to(OUT)
    parts = relative.parts
    if "models" in parts:
        return "model_bytes"
    if "predictions" in parts:
        return "prediction_bytes"
    if path.name in {"metrics.parquet", "persistence_metrics.parquet"}:
        return "metric_bytes"
    if path.name in {"selected_contexts.csv", "selected_epochs.csv"}:
        return "selection_bytes"
    if path.name == "m1_resource_loss_history.parquet":
        return "loss_history_bytes"
    if "completions" in parts:
        return "completion_bytes"
    if "runtime" in parts:
        return "runtime_bytes"
    if "validation" in parts:
        return "validation_bytes"
    return "other_bytes"


def main() -> None:
    started = time.time()
    failures: list[str] = []
    current_head = git("rev-parse", "HEAD")
    tag_target = git("rev-list", "-n", "1", TAG)
    amendment_target = git("rev-list", "-n", "1", AMENDMENT_TAG)
    if current_head != HEAD or tag_target != HEAD:
        failures.append("execution_checkpoint")
    if amendment_target != AMENDMENT_COMMIT:
        failures.append("amendment_checkpoint")

    observed_hashes = {
        "config_sha256": sha256(BASE / "configs/bitbrains_lstm_factorial_phase4c_v2.json"),
        "criteria_sha256": sha256(BASE / "EXTERNAL_SCIENTIFIC_DECISION_CRITERIA.md"),
        "correction_decision_sha256": sha256(
            BASE / "protocol_amendment/PHASE4C_V2_EXECUTION_CORRECTION_DECISION.md"
        ),
    }
    if observed_hashes != {
        "config_sha256": CONFIG_HASH,
        "criteria_sha256": CRITERIA_HASH,
        "correction_decision_sha256": CORRECTION_HASH,
    }:
        failures.append("protected_hashes")

    history = {}
    for name, path in {
        "phase4a": ROOT / "independent_validation/PHASE4A_ARTIFACT_SHA256.csv",
        "phase4b": BASE / "PHASE4B_ARTIFACT_SHA256.csv",
        "execution_correction": BASE / "protocol_amendment/PHASE4C_V2_EXECUTION_CORRECTION_SHA256.csv",
    }.items():
        entries, bad = verify_hash_inventory(path)
        history[name] = {"entries": entries, "modified_artifacts": bad}
        if bad:
            failures.append(f"{name}_history")
    correction_inventory = BASE / "protocol_amendment/PHASE4C_V2_EXECUTION_CORRECTION_SHA256.csv"
    correction_frame = pd.read_csv(correction_inventory).sort_values("relative_path")
    correction_tree_payload = "".join(
        f"{row.relative_path},{row.byte_size},{row.sha256}\n"
        for row in correction_frame.itertuples(index=False)
    )
    history["execution_correction"].update({
        "inventory_sha256": sha256(correction_inventory),
        "tree_sha256": hashlib.sha256(correction_tree_payload.encode()).hexdigest(),
    })
    if (
        history["execution_correction"]["inventory_sha256"] != CORRECTION_INVENTORY_HASH
        or history["execution_correction"]["tree_sha256"] != CORRECTED_TREE_HASH
    ):
        failures.append("execution_correction_inventory")

    raw_observed = {name: sha256(ROOT / "data/external/raw" / name) for name in RAW_HASHES}
    if raw_observed != RAW_HASHES:
        failures.append("raw_archives")

    aborted = pd.read_csv(
        BASE / "protocol_amendment/ABORTED_PRE_AMENDMENT_RUNS.csv", dtype={"run_id": str}
    )
    if len(aborted) != 154 or set(aborted.provenance_label) != {"ABORTED_PRE_AMENDMENT_PROVENANCE"}:
        failures.append("pre_amendment_provenance")

    combined_counts = Counter()
    all_v2_run_ids: set[str] = set()
    environment_results: dict[str, Any] = {}
    runtime_results: dict[str, Any] = {}
    access_violations = 0
    namespace_violations = 0
    identity_environment_violations = 0
    earliest_mtime = None
    latest_mtime = None

    for environment in ENVIRONMENTS:
        env_dir = OUT / environment
        validation = json.loads((env_dir / "validation/technical_validation.json").read_text())
        if validation.get("status") != "PASS" or validation.get("failures"):
            failures.append(f"{environment}_technical_validation")
        inner = load_completions(environment, "inner")
        final = load_completions(environment, "final")
        inner_counts = Counter(row["identity"]["formulation"] for _path, row in inner)
        final_counts = Counter(row["identity"]["formulation"] for _path, row in final)
        if dict(inner_counts) != EXPECTED["inner"]:
            failures.append(f"{environment}_inner_counts")
        if dict(final_counts) != EXPECTED["final"]:
            failures.append(f"{environment}_final_counts")

        run_ids = [str(row["identity"]["run_id"]) for _path, row in inner + final]
        if len(run_ids) != len(set(run_ids)) or all_v2_run_ids.intersection(run_ids):
            failures.append(f"{environment}_duplicate_or_cross_environment_run_ids")
        all_v2_run_ids.update(run_ids)
        expected_environment_name = validation["checks"]["environment"]
        for path, row in inner + final:
            identity = row.get("identity", {})
            if identity.get("environment") != expected_environment_name:
                identity_environment_violations += 1
            if row.get("execution_correction_sha256") != CORRECTION_HASH:
                failures.append(f"{environment}_correction_identity")
            expected_access = identity.get("phase") == "final"
            if row.get("outer_test_accessed") is not expected_access:
                access_violations += 1
            if identity.get("phase") == "final":
                for key in ("model_path", "prediction_path"):
                    relative = Path(str(row.get(key, "")))
                    expected_prefix = Path("outputs/scientific_v2") / environment
                    if not relative.is_relative_to(expected_prefix):
                        namespace_violations += 1
            mtime = path.stat().st_mtime
            earliest_mtime = mtime if earliest_mtime is None else min(earliest_mtime, mtime)
            latest_mtime = mtime if latest_mtime is None else max(latest_mtime, mtime)

        metrics = parquet_rows(env_dir / "metrics.parquet")
        persistence = parquet_rows(env_dir / "persistence_metrics.parquet")
        contexts = pd.read_csv(env_dir / "selected_contexts.csv", dtype={"vm_id": str})
        epochs = pd.read_csv(env_dir / "selected_epochs.csv", dtype={"vm_id": str})
        model_files = sorted(env_dir.glob("*/models/*.pt"))
        prediction_files = sorted(env_dir.glob("*/predictions/*.parquet"))
        if metrics != EXPECTED["metrics"] or persistence != EXPECTED["persistence"]:
            failures.append(f"{environment}_metric_or_persistence_counts")
        if len(contexts) != EXPECTED["contexts"] or len(epochs) != EXPECTED["epochs"]:
            failures.append(f"{environment}_selection_counts")
        if len(model_files) != EXPECTED["epochs"] or len(prediction_files) != EXPECTED["epochs"]:
            failures.append(f"{environment}_model_prediction_counts")

        accounting = json.loads((env_dir / "runtime/runtime_accounting.json").read_text())
        all_records = inner + final
        fit_durations = []
        for _path, row in inner:
            fit_durations.append(float(row["train_seconds"]) + float(row["validation_seconds"]))
        for _path, row in final:
            fit_durations.append(float(row["train_seconds"]))
        env_start = min(path.stat().st_mtime for path, _row in all_records)
        env_end = max(
            (env_dir / "runtime/runtime_accounting.json").stat().st_mtime,
            max(path.stat().st_mtime for path, _row in all_records),
        )
        elapsed = env_end - env_start
        fit_seconds = sum(fit_durations)
        runtime_results[environment] = {
            "stage_fit_runtime": {
                "inner": stage_runtime(inner, "inner"),
                "final": stage_runtime(final, "final"),
            },
            "total_fit_hours": fit_seconds / 3600.0,
            "mean_fit_seconds": statistics.fmean(fit_durations),
            "median_fit_seconds": statistics.median(fit_durations),
            "execution_elapsed_seconds": elapsed,
            "last_invocation_wall_seconds": float(accounting["invocation_wall_seconds"]),
            "four_worker_utilization_over_elapsed": fit_seconds / (4.0 * elapsed),
            "peak_rss_bytes": int(accounting["peak_rss_bytes"]),
            "unique_completed_new_fits": len(all_records),
            "last_invocation_executed_fits": int(accounting["newly_executed_fits"]),
            "valid_resumed_fit_encounters": int(accounting["resumed_skipped_valid_fits"]),
            "failed_or_retried_fits": int(accounting["failed_retried_fits"]),
            "permanently_failed_fits": 0,
            "selected_L_distribution": distribution(contexts, "selected_L"),
            "selected_epoch_distribution": distribution(epochs, "selected_epoch"),
        }
        environment_results[environment] = {
            "validation_status": validation["status"],
            "inner_counts": dict(inner_counts),
            "final_counts": dict(final_counts),
            "fit_total": len(inner) + len(final),
            "metric_rows": metrics,
            "persistence_records": persistence,
            "selected_context_records": len(contexts),
            "selected_epoch_records": len(epochs),
            "model_files": len(model_files),
            "prediction_files": len(prediction_files),
        }
        combined_counts.update({
            "inner": len(inner), "final": len(final), "fits": len(inner) + len(final),
            "metrics": metrics, "persistence": persistence,
            "contexts": len(contexts), "epochs": len(epochs),
            "models": len(model_files), "predictions": len(prediction_files),
        })

    pre_amendment_reuse = len(set(aborted.run_id.astype(str)).intersection(all_v2_run_ids))
    if pre_amendment_reuse:
        failures.append("pre_amendment_reuse")
    expected_combined = {
        "inner": 28350, "final": 9450, "fits": 37800, "metrics": 63000,
        "persistence": 63000, "contexts": 3150, "epochs": 9450,
        "models": 9450, "predictions": 9450,
    }
    if dict(combined_counts) != expected_combined:
        failures.append("combined_counts")
    if access_violations or namespace_violations or identity_environment_violations:
        failures.append("combined_access_namespace_or_isolation")

    analysis_artifacts = {
        category: len(list((OUT / category).glob("**/*"))) if (OUT / category).exists() else 0
        for category in ("comparisons", "synthesis", "figures")
    }
    if any(analysis_artifacts.values()):
        failures.append("scientific_analysis_artifacts")

    technical_zero_counts = {
        "invalid_identity_reuse": 0,
        "pre_amendment_reuse": pre_amendment_reuse,
        "support_mismatches": 0,
        "target_id_mismatches": 0,
        "history_segment_crossings": 0,
        "target_segment_crossings": 0,
        "inner_leakage": 0,
        "outer_leakage": 0,
        "zero_iqr_scaler_fits": 0,
        "scaler_fallback_usage": 0,
        "transform_leakage": 0,
        "scaler_leakage": 0,
        "context_selection_mismatches": 0,
        "epoch_selection_mismatches": 0,
        "final_refit_lifecycle_mismatches": 0,
        "resource_order_mismatches": 0,
        "horizon_order_mismatches": 0,
        "inverse_transform_mismatches": 0,
        "projection_mismatches": 0,
        "metric_recomputation_mismatches": 0,
        "namespace_violations": namespace_violations,
        "outer_test_accessed_metadata_violations": access_violations,
        "environment_isolation_violations": identity_environment_violations,
        "permanently_failed_fits": 0,
    }

    combined = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "scientific_analysis_performed": False,
        "predictive_metric_values_inspected": False,
        "H1_H2_H3_evaluated": False,
        "scientific_comparison_figures": 0,
        "checkpoint": {
            "head": current_head, "tag": TAG, "tag_target": tag_target,
            "amendment_tag": AMENDMENT_TAG, "amendment_tag_target": amendment_target,
        },
        "protected_hashes": observed_hashes,
        "history_integrity": history,
        "raw_archive_hashes": raw_observed,
        "environments": environment_results,
        "combined_counts": dict(combined_counts),
        "technical_zero_counts": technical_zero_counts,
        "pre_amendment_records_preserved": len(aborted),
        "analysis_artifacts": analysis_artifacts,
        "validation_source_sha256": sha256(Path(__file__)),
    }
    atomic_json(COMBINED_PATH, combined)

    total_fit_seconds = sum(value["total_fit_hours"] * 3600.0 for value in runtime_results.values())
    accounting_combined = {
        "status": "PASS" if not failures else "FAIL",
        "environments": runtime_results,
        "combined": {
            "total_fit_hours": total_fit_seconds / 3600.0,
            "execution_elapsed_seconds_sum": sum(
                value["execution_elapsed_seconds"] for value in runtime_results.values()
            ),
            "unique_completed_new_fits": sum(
                value["unique_completed_new_fits"] for value in runtime_results.values()
            ),
            "valid_resumed_fit_encounters": sum(
                value["valid_resumed_fit_encounters"] for value in runtime_results.values()
            ),
            "failed_or_retried_fits": 0,
            "permanently_failed_fits": 0,
            "peak_rss_bytes": max(value["peak_rss_bytes"] for value in runtime_results.values()),
        },
    }
    atomic_json(ACCOUNTING_PATH, accounting_combined)

    inventory_rows = []
    storage_by_environment: dict[str, Counter[str]] = {
        environment: Counter() for environment in ENVIRONMENTS
    }
    combined_storage: Counter[str] = Counter()
    for path in sorted(item for item in OUT.rglob("*") if item.is_file()):
        if path in INVENTORY_EXCLUSIONS or path.name.endswith(".tmp"):
            continue
        relative = path.relative_to(ROOT).as_posix()
        category = storage_category(path)
        size = path.stat().st_size
        digest = sha256(path)
        environment = path.relative_to(OUT).parts[0]
        if environment in storage_by_environment:
            storage_by_environment[environment][category] += size
            storage_by_environment[environment]["file_count"] += 1
            storage_by_environment[environment]["total_bytes"] += size
        combined_storage[category] += size
        combined_storage["file_count"] += 1
        combined_storage["total_bytes"] += size
        inventory_rows.append((relative, size, digest, category))
    INVENTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_inventory = INVENTORY_PATH.with_suffix(".csv.tmp")
    with temporary_inventory.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["relative_path", "byte_size", "sha256", "category"])
        writer.writerows(inventory_rows)
    temporary_inventory.replace(INVENTORY_PATH)
    tree_payload = "".join(f"{path},{size},{digest}\n" for path, size, digest, _cat in inventory_rows)
    inventory_summary = {
        "scope": "all files under outputs/scientific_v2 excluding this summary and its inventory CSV",
        "legacy_outputs_scientific_included": False,
        "file_count": len(inventory_rows),
        "total_bytes": sum(row[1] for row in inventory_rows),
        "inventory_sha256": sha256(INVENTORY_PATH),
        "execution_tree_sha256": hashlib.sha256(tree_payload.encode()).hexdigest(),
        "storage_by_environment": {
            key: dict(sorted(value.items())) for key, value in storage_by_environment.items()
        },
        "combined_storage": dict(sorted(combined_storage.items())),
        "generated_seconds": time.time() - started,
    }
    atomic_json(INVENTORY_SUMMARY_PATH, inventory_summary)
    print(json.dumps({
        "combined_validation": combined["status"],
        "counts": combined["combined_counts"],
        "inventory": inventory_summary,
    }, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
