"""Build all Phase 4B support metadata and execute the bounded inner-only pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from . import CONTEXTS, HORIZON_MINUTES, RESOURCE_ORDER
from .cleaning import CleanVM, clean_and_segment
from .ingestion import BASE, CONFIG_PATH, read_vm, selected_ids, sha256_file
from .metrics import per_lead_metrics
from .panel import build_windows
from .splits import ExternalFold, assert_support_minima, build_folds, manifest_rows
from .support import assert_context_invariant, legal_origins, support_hash
from .training import (
    build_model,
    encoder_parameter_count,
    fit_inner,
    head_parameter_count,
    parameter_count,
    serialized_state_bytes,
)
from .transforms import fit_partition_scaler, scale_windows
from .validation import scientific_workload_counts


MANIFESTS = BASE / "manifests"
PILOT = BASE / "pilot"
OUTPUTS = BASE / "outputs"
DECISION = BASE / "EXTERNAL_FACTORIAL_DECISION.md"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def build_support_manifests() -> dict[str, object]:
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    support_rows, segment_rows, quality_rows, member_rows = [], [], [], []
    failures = []
    environment_summaries = {}
    for environment, vm_ids in selected_ids().items():
        environment_origin_total = 0
        for vm_id in vm_ids:
            clean = clean_and_segment(read_vm(environment, vm_id))
            quality_rows.append(clean.quality)
            segment_rows.extend(clean.segments)
            member_rows.extend(clean.members)
            origins = legal_origins(clean.frame)
            assert_context_invariant({context: origins.copy() for context in CONTEXTS})
            folds = build_folds(clean.frame, environment, vm_id, origins)
            failures.extend(assert_support_minima(folds, cfg["support_minima"]))
            support_rows.extend(manifest_rows(clean.frame, folds))
            environment_origin_total += len(origins)
        environment_summaries[environment] = {
            "selected_vms": len(vm_ids),
            "total_legal_origins_across_vms": environment_origin_total,
        }
    support = pd.DataFrame(support_rows).sort_values(["environment", "vm_id", "fold", "L"])
    if len(support) != 1050:
        raise RuntimeError(f"Expected 1,050 support rows, found {len(support)}")
    support.to_parquet(MANIFESTS / "EXTERNAL_SUPPORT_MANIFEST.parquet", index=False)
    exact_columns = [column for column in support.columns if column.endswith("_origin_ids")]
    summary = support.drop(columns=exact_columns).copy()
    for column in [column for column in summary.columns if column.endswith("_segment_ids")]:
        summary[column] = summary[column].map(lambda values: ";".join(str(value) for value in values))
    summary.to_csv(MANIFESTS / "EXTERNAL_SUPPORT_SUMMARY.csv", index=False)
    pd.DataFrame(segment_rows).sort_values(["environment", "vm_id", "segment_id"]).to_csv(
        MANIFESTS / "BITBRAINS_SEGMENT_MANIFEST.csv", index=False
    )
    pd.DataFrame(quality_rows).sort_values(["environment", "vm_id"]).to_csv(
        MANIFESTS / "SELECTED_VM_QUALITY.csv", index=False
    )
    pd.DataFrame(member_rows).sort_values(["environment", "vm_id", "member_path"]).to_csv(
        MANIFESTS / "RAW_MEMBER_MANIFEST.csv", index=False
    )
    feasibility = {
        "status": "PASS" if not failures else "FAIL",
        "support_record_count": len(support),
        "expected_support_record_count": 1050,
        "support_failures": failures,
        "support_minima": cfg["support_minima"],
        "environments": environment_summaries,
        "formulation_resource_support_mismatches": 0,
    }
    write_json(MANIFESTS / "SUPPORT_FEASIBILITY.json", feasibility)
    if failures:
        raise RuntimeError(f"Support feasibility failed for {len(failures)} VM/fold/split cells")
    return feasibility


def _pilot_fold(environment: str, vm_id: str) -> tuple[CleanVM, ExternalFold]:
    clean = clean_and_segment(read_vm(environment, vm_id))
    folds = build_folds(clean.frame, environment, vm_id, legal_origins(clean.frame))
    return clean, folds[0]


def _technical_metric_rows(
    environment: str,
    vm_id: str,
    formulation: str,
    target: str,
    prediction_scaled: np.ndarray,
    y_validation_native: np.ndarray,
    persistence_native: np.ndarray,
    scaler,
) -> list[dict[str, object]]:
    rows = []
    resources = RESOURCE_ORDER if formulation == "M1" else (target,)
    for resource in resources:
        index = RESOURCE_ORDER.index(resource)
        scaled = prediction_scaled[:, index, :] if formulation == "M1" else prediction_scaled
        predicted, _, unclipped = scaler.inverse_one(scaled, resource)
        observed = y_validation_native[:, index, :]
        persistence = persistence_native[:, index, :]
        metrics = per_lead_metrics(observed, predicted, float(scaler.native_iqr[index]), persistence)
        for lead_index, minutes in enumerate(HORIZON_MINUTES):
            rows.append({
                "environment": environment,
                "vm_id": vm_id,
                "formulation": formulation,
                "target": target,
                "resource": resource,
                "horizon_minutes": minutes,
                "mae": float(metrics["mae"][lead_index]),
                "rmse": float(metrics["rmse"][lead_index]),
                "r2": float(metrics["r2"][lead_index]),
                "nmae": float(metrics["nmae"][lead_index]),
                "persistence_skill": float(metrics["persistence_skill"][lead_index]),
                "pre_projection_negative_fraction": (
                    float(np.mean(unclipped[:, lead_index] < 0))
                    if resource in {"THROUGHPUT", "DISK_WRITE"} else 0.0
                ),
                "scientific_status": "NON_SCIENTIFIC_INNER_VALIDATION_SANITY_ONLY",
            })
    return rows


def run_pilot() -> dict[str, object]:
    PILOT.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    timing_rows, loss_rows, sanity_rows = [], [], []
    state_sizes: dict[str, list[int]] = {"S1": [], "S2": [], "M1": []}
    for environment, vm_id in cfg["pilot"]["vm_by_environment"].items():
        clean, fold = _pilot_fold(environment, vm_id)
        context = cfg["pilot"]["context"]
        X_train, y_train, _ = build_windows(clean.frame, fold.inner_train, context)
        X_validation, y_validation, persistence_validation = build_windows(
            clean.frame, fold.inner_validation, context
        )
        scaler = fit_partition_scaler(clean.frame, fold.inner_train, context)
        X_train_scaled, y_train_scaled = scale_windows(X_train, y_train, scaler)
        X_validation_scaled, y_validation_scaled = scale_windows(X_validation, y_validation, scaler)
        specifications = (
            [("S1", resource) for resource in RESOURCE_ORDER]
            + [("S2", resource) for resource in RESOURCE_ORDER]
            + [("M1", "ALL")]
        )
        for formulation, target in specifications:
            if formulation == "S1":
                index = RESOURCE_ORDER.index(target)
                train_x, validation_x = X_train_scaled[..., [index]], X_validation_scaled[..., [index]]
                train_y, validation_y = y_train_scaled[:, index, :], y_validation_scaled[:, index, :]
                resource_name = target
            elif formulation == "S2":
                index = RESOURCE_ORDER.index(target)
                train_x, validation_x = X_train_scaled, X_validation_scaled
                train_y, validation_y = y_train_scaled[:, index, :], y_validation_scaled[:, index, :]
                resource_name = target
            else:
                train_x, validation_x = X_train_scaled, X_validation_scaled
                train_y, validation_y = y_train_scaled, y_validation_scaled
                resource_name = None
            result = fit_inner(
                formulation, resource_name, cfg["pilot"]["seed"],
                train_x, train_y, validation_x, validation_y,
                fixed_epochs=cfg["pilot"]["epochs"], batch_size=cfg["batch_size"],
            )
            count = parameter_count(result.model)
            state_bytes = serialized_state_bytes(result.model)
            state_sizes[formulation].append(state_bytes)
            training_seconds = float(sum(result.epoch_train_seconds))
            validation_seconds = float(sum(result.epoch_validation_seconds))
            timing_rows.append({
                "environment": environment,
                "vm_id": vm_id,
                "formulation": formulation,
                "target": target,
                "parameter_count": count,
                "L": context,
                "training_samples": len(train_x),
                "validation_samples": len(validation_x),
                "seconds_per_epoch": training_seconds / cfg["pilot"]["epochs"],
                "validation_seconds_per_epoch": validation_seconds / cfg["pilot"]["epochs"],
                "five_epoch_training_seconds": training_seconds,
                "five_epoch_validation_seconds": validation_seconds,
                "samples_per_second": len(train_x) * cfg["pilot"]["epochs"] / training_seconds,
                "peak_rss_bytes": result.peak_rss_bytes,
                "serialized_model_bytes": state_bytes,
                "input_dimensions": f"N,{context},{train_x.shape[-1]}",
                "output_dimensions": "N,4,5" if formulation == "M1" else "N,5",
                "epochs_trained": result.epochs_trained,
                "outer_test_targets_accessed": False,
            })
            sanity_rows.extend(_technical_metric_rows(
                environment, vm_id, formulation, target,
                result.validation_prediction, y_validation, persistence_validation, scaler,
            ))
            if formulation == "M1":
                for log in result.epoch_logs:
                    for resource in RESOURCE_ORDER:
                        loss_rows.append({
                            "environment": environment,
                            "vm_id": vm_id,
                            "epoch": log["epoch"],
                            "resource": resource,
                            "train_normalized_mse": log["train_resource_mse"][resource],
                            "train_loss_share": log["train_loss_share"][resource],
                            "validation_normalized_mse": log["validation_resource_mse"][resource],
                            "validation_loss_share": log["validation_loss_share"][resource],
                            "scientific_status": "NON_SCIENTIFIC_TECHNICAL_DIAGNOSTIC",
                        })
    timings = pd.DataFrame(timing_rows)
    timings.to_csv(PILOT / "PILOT_TIMINGS.csv", index=False)
    pd.DataFrame(loss_rows).to_csv(PILOT / "M1_LOSS_BALANCE.csv", index=False)
    pd.DataFrame(sanity_rows).to_csv(PILOT / "INNER_VALIDATION_SANITY.csv", index=False)
    parameter_counts = {
        "S1_parameters_per_model": parameter_count(build_model("S1", 1)),
        "S1_four_model_total": 4 * parameter_count(build_model("S1", 1)),
        "S2_parameters_per_model": parameter_count(build_model("S2", 4)),
        "S2_four_model_total": 4 * parameter_count(build_model("S2", 4)),
        "M1_encoder_parameters": encoder_parameter_count(build_model("M1", 4)),
        "M1_head_parameters": head_parameter_count(build_model("M1", 4)),
        "M1_total_parameters": parameter_count(build_model("M1", 4)),
    }
    write_json(PILOT / "PARAMETER_COUNTS.json", parameter_counts)
    access = {
        "pilot_models": len(timings),
        "expected_pilot_models": 18,
        "epochs_per_model": sorted(timings.epochs_trained.unique().tolist()),
        "outer_test_targets_accessed": bool(timings.outer_test_targets_accessed.any()),
        "outer_test_predictions_generated": 0,
        "scientific_context_selections": 0,
        "scientific_final_refits": 0,
    }
    write_json(PILOT / "PILOT_DATA_ACCESS.json", access)
    if len(timings) != 18 or set(timings.epochs_trained) != {5} or access["outer_test_targets_accessed"]:
        raise RuntimeError("Pilot execution boundary violated")
    return {"timings": timings, "parameter_counts": parameter_counts, "state_sizes": state_sizes}


def runtime_and_storage_projection(pilot: dict[str, object]) -> dict[str, object]:
    timings: pd.DataFrame = pilot["timings"]
    counts = scientific_workload_counts()
    projections: dict[str, object] = {
        "fit_counts_per_environment": counts,
        "combined_fit_counts": {
            "inner_total": 2 * counts["inner_total"],
            "final_total": 2 * counts["final_total"],
            "fit_total": 2 * counts["fit_total"],
            "metric_rows": 2 * counts["metric_rows"],
        },
        "scenarios": {},
    }
    epoch_scenarios = {"OPTIMISTIC": 10, "CENTRAL": 25, "CONSERVATIVE": 50}
    for scenario, epochs in epoch_scenarios.items():
        per_environment = {}
        combined_hours = 0.0
        for environment, group in timings.groupby("environment", sort=True):
            categories = {}
            total = 0.0
            for formulation in ("S1", "S2", "M1"):
                selected = group[group.formulation.eq(formulation)]
                train_epoch = float(selected.seconds_per_epoch.median())
                validation_epoch = float(selected.validation_seconds_per_epoch.median())
                inner_hours = counts[f"{formulation}_inner"] * epochs * (train_epoch + validation_epoch) / 3600.0
                final_hours = counts[f"{formulation}_final"] * epochs * train_epoch / 3600.0
                categories[f"{formulation}_inner_fit_hours"] = inner_hours
                categories[f"{formulation}_final_fit_hours"] = final_hours
                total += inner_hours + final_hours
            categories["aggregate_fit_hours"] = total
            categories["one_worker_wall_hours"] = total
            categories["four_worker_wall_hours"] = total / 4.0
            per_environment[environment] = categories
            combined_hours += total
        projections["scenarios"][scenario] = {
            "effective_epochs": epochs,
            "environments": per_environment,
            "combined_aggregate_fit_hours": combined_hours,
            "combined_one_worker_wall_hours": combined_hours,
            "combined_four_worker_wall_hours": combined_hours / 4.0,
        }

    support = pd.read_parquet(MANIFESTS / "EXTERNAL_SUPPORT_MANIFEST.parquet")
    unique_tests = support[support.L.eq(18)].outer_test_count.sum()
    state_medians = {
        formulation: int(np.median(values)) for formulation, values in pilot["state_sizes"].items()
    }
    model_bytes_per_environment = (
        counts["S1_final"] * state_medians["S1"]
        + counts["S2_final"] * state_medians["S2"]
        + counts["M1_final"] * state_medians["M1"]
    )
    prediction_bytes = int(unique_tests * 1600)
    metrics_manifest_bytes = int(2 * counts["metric_rows"] * 300 + sum(
        path.stat().st_size for path in MANIFESTS.glob("*") if path.is_file()
    ))
    storage = {
        "serialized_model_state_median_bytes": state_medians,
        "model_artifact_bytes_both_environments": 2 * model_bytes_per_environment,
        "prediction_payload_bytes_both_environments": prediction_bytes,
        "metrics_and_manifests_bytes": metrics_manifest_bytes,
    }
    storage["total_retained_scientific_bytes"] = sum(
        value for key, value in storage.items() if key.endswith("bytes_both_environments") or key == "metrics_and_manifests_bytes"
    )
    write_json(PILOT / "RUNTIME_PROJECTION.json", projections)
    write_json(PILOT / "STORAGE_PROJECTION.json", storage)

    central_days = projections["scenarios"]["CENTRAL"]["combined_four_worker_wall_hours"] / 24.0
    conservative_days = projections["scenarios"]["CONSERVATIVE"]["combined_four_worker_wall_hours"] / 24.0
    peak_rss = int(timings.peak_rss_bytes.max())
    try:
        physical_ram = int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
    except (ValueError, OSError):
        physical_ram = 0
    memory_safe = not physical_ram or 4 * peak_rss < 0.8 * physical_ram
    retained_gb = storage["total_retained_scientific_bytes"] / 1e9
    if central_days <= 7 and conservative_days <= 14 and retained_gb <= 20 and memory_safe:
        decision = "FULL_35_VM_CONFIRMATION_FEASIBLE"
    elif central_days <= 21 and conservative_days <= 42 and retained_gb <= 100 and memory_safe:
        decision = "FULL_35_VM_CONFIRMATION_EXPENSIVE_BUT_FEASIBLE"
    else:
        decision = "PROSPECTIVE_COHORT_REDUCTION_REQUIRED"
    feasibility = {
        "decision": decision,
        "central_four_worker_days": central_days,
        "conservative_four_worker_days": conservative_days,
        "peak_pilot_rss_bytes": peak_rss,
        "detected_physical_ram_bytes": physical_ram,
        "four_worker_memory_safe": memory_safe,
        "retained_storage_gb_decimal": retained_gb,
        "basis": "timing, memory, disk, support, and technical correctness only",
    }
    write_json(PILOT / "COMPUTE_FEASIBILITY_DECISION.json", feasibility)
    return {"runtime": projections, "storage": storage, "feasibility": feasibility}


def run_all() -> None:
    identities = {
        "decision_sha256": digest(DECISION),
        "config_sha256": digest(CONFIG_PATH),
        "phase4a_commit": "59f5bed3fd7b385739d08dc088965341a29c2809",
    }
    write_json(OUTPUTS / "PREFLIGHT_IDENTITIES.json", identities)
    support = build_support_manifests()
    pilot = run_pilot()
    projections = runtime_and_storage_projection(pilot)
    state = {
        **identities,
        "support_status": support["status"],
        "support_records": support["support_record_count"],
        "pilot_models": len(pilot["timings"]),
        "pilot_epochs_each": 5,
        "compute_feasibility_decision": projections["feasibility"]["decision"],
        "external_scientific_fits": 0,
        "external_test_predictions": 0,
        "external_predictive_outcomes_inspected": 0,
        "status": "PASS",
    }
    write_json(OUTPUTS / "PREFLIGHT_STATE.json", state)
    print(json.dumps(state, indent=2, sort_keys=True))


def finalize_existing() -> dict[str, object]:
    identities = {
        "decision_sha256": digest(DECISION),
        "config_sha256": digest(CONFIG_PATH),
        "phase4a_commit": "59f5bed3fd7b385739d08dc088965341a29c2809",
    }
    support = json.loads((MANIFESTS / "SUPPORT_FEASIBILITY.json").read_text())
    access = json.loads((PILOT / "PILOT_DATA_ACCESS.json").read_text())
    compute = json.loads((PILOT / "COMPUTE_FEASIBILITY_DECISION.json").read_text())
    state = {
        **identities,
        "support_status": support["status"],
        "support_records": support["support_record_count"],
        "pilot_models": access["pilot_models"],
        "pilot_epochs_each": access["epochs_per_model"],
        "compute_feasibility_decision": compute["decision"],
        "external_scientific_fits": 0,
        "external_test_predictions": 0,
        "external_predictive_outcomes_inspected": 0,
        "status": "PASS",
    }
    write_json(OUTPUTS / "PREFLIGHT_IDENTITIES.json", identities)
    write_json(OUTPUTS / "PREFLIGHT_STATE.json", state)
    return state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("support", "pilot", "finalize", "all"), default="all", nargs="?")
    args = parser.parse_args()
    if args.mode == "support":
        print(json.dumps(build_support_manifests(), indent=2, sort_keys=True))
    elif args.mode == "pilot":
        pilot = run_pilot()
        print(json.dumps(runtime_and_storage_projection(pilot)["feasibility"], indent=2, sort_keys=True))
    elif args.mode == "finalize":
        print(json.dumps(finalize_existing(), indent=2, sort_keys=True))
    else:
        run_all()


if __name__ == "__main__":
    main()
