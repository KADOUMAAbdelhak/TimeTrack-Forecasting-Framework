"""Bounded non-scientific Phase 3B pilot and future workload accounting."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data import CONTEXT_LENGTHS, FUTURE_LEADS, MACHINES, RESOURCE_ORDER, RawWindows, build_raw_windows, load_panel
from .metrics import inverse_one, per_lead_metrics
from .models import MultiTargetLSTM, SingleTargetLSTM
from .splits import build_factorial_folds
from .training import encoder_parameter_count, fit_inner, head_parameter_count, parameter_count, serialized_state_bytes
from .transforms import fit_partition_scaler, scale_windows
from .validation import atomic_json_write


BASE = Path(__file__).resolve().parents[1]
CONFIG = BASE / "configs/lstm_factorial.json"
DECISION = BASE / "FACTORIAL_DECISION.md"
PILOT = BASE / "pilot"
EXPECTED_DECISION_HASH = "2bfb2610bd8e869dc038bccd6b18656cd2c968b9d548c758487cae500cbf5677"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def planned_counts() -> dict[str, dict[str, int]]:
    return {
        "S1": {"inner_fits": 1260, "final_fits": 420, "metric_rows": 3360},
        "S2": {"inner_fits": 1260, "final_fits": 420, "metric_rows": 3360},
        "M1": {"inner_fits": 315, "final_fits": 105, "metric_rows": 3360},
        "TOTAL": {"inner_fits": 2835, "final_fits": 945, "total_fits": 3780, "metric_rows": 10080},
    }


def parameter_accounting() -> dict[str, object]:
    s1 = SingleTargetLSTM(1); s2 = SingleTargetLSTM(4); m1 = MultiTargetLSTM(4)
    return {
        "S1": {"parameters_per_resource_model": parameter_count(s1), "total_parameters_four_models": 4 * parameter_count(s1), "training_models_per_cell": 4, "inference_models_per_cell": 4, "serialized_state_bytes_per_model": serialized_state_bytes(s1)},
        "S2": {"parameters_per_target_model": parameter_count(s2), "total_parameters_four_models": 4 * parameter_count(s2), "training_models_per_cell": 4, "inference_models_per_cell": 4, "serialized_state_bytes_per_model": serialized_state_bytes(s2)},
        "M1": {"shared_encoder_parameters": encoder_parameter_count(m1), "four_head_parameters": head_parameter_count(m1), "total_shared_system_parameters": parameter_count(m1), "training_models_per_cell": 1, "inference_models_per_cell": 1, "serialized_state_bytes_per_model": serialized_state_bytes(m1)},
    }


def _scaled_views(X: np.ndarray, y: np.ndarray, formulation: str, resource: str | None) -> tuple[np.ndarray, np.ndarray]:
    if formulation == "M1": return X, y
    index = RESOURCE_ORDER.index(str(resource))
    return (X[:, :, index:index + 1] if formulation == "S1" else X), y[:, index, :]


def _support_manifest(panel: pd.DataFrame) -> tuple[list[dict[str, object]], int]:
    rows, total_outer_test = [], 0
    for machine in MACHINES:
        folds = build_factorial_folds(panel, machine, 128)
        total_outer_test += sum(len(fold.outer_test) for fold in folds)
        for length in CONTEXT_LENGTHS:
            for fold in folds:
                rows.append({"machine": machine, "fold": fold.fold, "context_length": length, "inner_train_n": len(fold.inner_train), "inner_validation_n": len(fold.inner_validation), "outer_train_n": len(fold.outer_train), "outer_test_n": len(fold.outer_test), **{f"{key}_hash": value for key, value in fold.hashes.items()}})
    return rows, total_outer_test


def _sanity_rows(formulation: str, resource: str, prediction_scaled: np.ndarray, truth_native: np.ndarray, persistence_native: np.ndarray, scaler, negative_rate: float) -> list[dict[str, object]]:
    resource_index = RESOURCE_ORDER.index(resource)
    prediction_native, _, unclipped = inverse_one(prediction_scaled, scaler, resource, project=True)
    metrics = per_lead_metrics(truth_native, prediction_native, scaler.native_iqr[resource_index], persistence_native)
    rows = []
    for position, lead in enumerate(FUTURE_LEADS):
        rows.append({"formulation": formulation, "resource": resource, "lead": lead, "mae": metrics["mae"][position], "rmse": metrics["rmse"][position], "r2": metrics["r2"][position], "nmae": metrics["nmae"][position], "persistence_skill": metrics["persistence_skill"][position], "pre_projection_negative_rate": negative_rate, "unclipped_prediction_min": float(np.min(unclipped[:, position])), "scientific": False})
    return rows


def _runtime_projection(timings: list[dict[str, object]], outer_train_ratio: float, state: dict[str, object], total_outer_test: int) -> dict[str, object]:
    by_formulation = {}
    counts = planned_counts()
    for formulation in ("S1", "S2", "M1"):
        selected = [row for row in timings if row["formulation"] == formulation]
        by_formulation[formulation] = {"train_seconds_per_epoch": float(np.mean([row["total_5_epoch_training_seconds"] / 5 for row in selected])), "validation_seconds_per_epoch": float(np.mean([row["validation_seconds"] / 5 for row in selected]))}
    scenarios = {}
    for name, epochs in (("OPTIMISTIC", 10), ("CENTRAL", 25), ("CONSERVATIVE", 50)):
        detail, subtotal = {}, 0.0
        for formulation in ("S1", "S2", "M1"):
            rates = by_formulation[formulation]; count = counts[formulation]
            inner = count["inner_fits"] * epochs * (rates["train_seconds_per_epoch"] + rates["validation_seconds_per_epoch"])
            final = count["final_fits"] * epochs * rates["train_seconds_per_epoch"] * outer_train_ratio
            detail[formulation] = {"inner_selection_seconds": inner, "final_refit_seconds": final, "training_total_seconds": inner + final}
            subtotal += inner + final
        overhead = 0.05 * subtotal
        scenarios[name] = {"effective_epochs": epochs, "by_formulation": detail, "analysis_validation_overhead_seconds": overhead, "total_seconds": subtotal + overhead, "total_cpu_hours": (subtotal + overhead) / 3600}
    model_bytes = 420 * state["S1"]["serialized_state_bytes_per_model"] + 420 * state["S2"]["serialized_state_bytes_per_model"] + 105 * state["M1"]["serialized_state_bytes_per_model"]
    prediction_rows = total_outer_test * 3 * 12 * 8
    prediction_bytes = prediction_rows * 64
    return {"basis": by_formulation, "outer_to_inner_training_sample_ratio": outer_train_ratio, "scenarios": scenarios, "disk_projection": {"saved_model_bytes": model_bytes, "prediction_resource_lead_rows": prediction_rows, "assumed_compressed_bytes_per_prediction_row": 64, "prediction_bytes": prediction_bytes, "compact_metadata_and_metrics_bytes": 25_000_000, "total_estimated_bytes": model_bytes + prediction_bytes + 25_000_000, "note": "Prediction estimate is planning-only; no outer-test prediction was generated."}}


def run_pilot() -> None:
    if digest(DECISION) != EXPECTED_DECISION_HASH:
        raise RuntimeError("Prospective decision record changed")
    PILOT.mkdir(parents=True, exist_ok=True)
    panel = load_panel()
    support_rows, total_outer_test = _support_manifest(panel)
    atomic_json_write(PILOT / "SUPPORT_MANIFEST.json", {"maximum_support_context": 128, "expected_formulation_resource_mismatches": 0, "outer_test_values_accessed": False, "rows": support_rows})
    fold = build_factorial_folds(panel, "machine01", 64)[0]
    scaler = fit_partition_scaler(panel, "machine01", fold.inner_train, 64)
    atomic_json_write(PILOT / "SCALER_METADATA.json", {"fit_partition": "inner_train_only", "support_hash": fold.hashes["inner_train"], "resources": scaler.metadata()})
    train_raw = build_raw_windows(panel, "machine01", 64, fold.inner_train)
    validation_raw = build_raw_windows(panel, "machine01", 64, fold.inner_validation)
    X_train, y_train = scale_windows(train_raw.X, train_raw.y, scaler)
    X_validation, y_validation = scale_windows(validation_raw.X, validation_raw.y, scaler)
    timings, sanity, m1_logs = [], [], []
    fits = [(formulation, resource) for formulation in ("S1", "S2") for resource in RESOURCE_ORDER] + [("M1", None)]
    for formulation, target_resource in fits:
        train_x, train_y = _scaled_views(X_train, y_train, formulation, target_resource)
        validation_x, validation_y = _scaled_views(X_validation, y_validation, formulation, target_resource)
        result = fit_inner(formulation, target_resource, 0, train_x, train_y, validation_x, validation_y, fixed_epochs=5, device="cpu")
        params = parameter_count(result.model)
        timings.append({"formulation": formulation, "resource": target_resource or "ALL", "parameter_count": params, "training_samples": len(train_x), "validation_samples": len(validation_x), "seconds_per_epoch": result.train_seconds / 5, "total_5_epoch_training_seconds": result.train_seconds, "validation_seconds": result.validation_seconds, "samples_per_second": len(train_x) * 5 / result.train_seconds, "peak_rss_bytes": result.peak_rss_bytes, "input_channels": train_x.shape[-1], "output_dimensions": [4, 8] if formulation == "M1" else [8], "epochs_completed": result.epochs_trained, "best_epoch_for_diagnostic_only": result.best_epoch, "scientific": False})
        if formulation == "M1":
            for log in result.epoch_logs:
                for resource_name in RESOURCE_ORDER:
                    m1_logs.append({"row_type": "epoch", "epoch": log["epoch"], "resource": resource_name, "train_resource_mse": log["train_resource_mse"][resource_name], "validation_resource_mse": log["validation_resource_mse"][resource_name], "train_loss_share": log["train_loss_share"][resource_name], "validation_loss_share": log["validation_loss_share"][resource_name]})
            for resource_name in RESOURCE_ORDER:
                final = [row for row in m1_logs if row["row_type"] == "epoch" and row["resource"] == resource_name and row["epoch"] >= 3]
                m1_logs.append({"row_type": "final3_mean", "epoch": "", "resource": resource_name, **{key: float(np.mean([row[key] for row in final])) for key in ("train_resource_mse", "validation_resource_mse", "train_loss_share", "validation_loss_share")}})
            for index, resource_name in enumerate(RESOURCE_ORDER):
                native_prediction, rate, _ = inverse_one(result.validation_prediction[:, index, :], scaler, resource_name)
                _ = native_prediction
                persistence = np.repeat(validation_raw.X[:, -1, index, None], 8, axis=1)
                sanity.extend(_sanity_rows("M1", resource_name, result.validation_prediction[:, index, :], validation_raw.y[:, index, :], persistence, scaler, rate))
        else:
            index = RESOURCE_ORDER.index(str(target_resource))
            _, rate, _ = inverse_one(result.validation_prediction, scaler, str(target_resource))
            persistence = np.repeat(validation_raw.X[:, -1, index, None], 8, axis=1)
            sanity.extend(_sanity_rows(formulation, str(target_resource), result.validation_prediction, validation_raw.y[:, index, :], persistence, scaler, rate))
    pd.DataFrame(m1_logs).to_csv(PILOT / "M1_LOSS_BALANCE.csv", index=False)
    pd.DataFrame(sanity).to_csv(PILOT / "SANITY_METRICS.csv", index=False)
    state = parameter_accounting(); atomic_json_write(PILOT / "PARAMETER_ACCOUNTING.json", state)
    atomic_json_write(PILOT / "TIMING_RESULTS.json", {"pilot_models": len(timings), "epochs_each": 5, "machine": "machine01", "fold": 1, "seed": 0, "context_length": 64, "inner_train_support_hash": fold.hashes["inner_train"], "inner_validation_support_hash": fold.hashes["inner_validation"], "outer_test_accessed": False, "models": timings})
    projection = _runtime_projection(timings, len(fold.outer_train) / len(fold.inner_train), state, total_outer_test)
    atomic_json_write(PILOT / "RUNTIME_PROJECTION.json", projection)
    atomic_json_write(PILOT / "PILOT_PROVENANCE.json", {"decision_sha256": digest(DECISION), "config_sha256": digest(CONFIG), "scientific": False, "context_selection_executed": False, "outer_refit_executed": False, "outer_test_values_accessed": False, "outer_test_predictions_generated": False, "models": 9, "epochs_per_model": 5, "proposed_architecture_implemented": False})


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    if not args.pilot: raise SystemExit("Only the explicitly bounded --pilot mode is implemented for execution")
    run_pilot()


if __name__ == "__main__": main()
