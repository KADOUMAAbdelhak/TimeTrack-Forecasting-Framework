#!/usr/bin/env python3
"""Execute one frozen amended-V2 Phase 4C environment with atomic resumability."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import resource as process_resource
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from src import CONTEXTS, HORIZON_MINUTES, LEADS, RESOURCE_ORDER, SEEDS
from src.cleaning import CleanVM, clean_and_segment
from src.ingestion import CONFIG_PATH as PHASE4B_CONFIG_PATH, read_vm
from src.metrics import per_lead_metrics
from src.panel import build_windows
from src.selection import SelectionRow, select_context
from src.splits import ExternalFold, build_folds
from src.support import legal_origins
from src.training import (
    BATCH_SIZE,
    GRADIENT_CLIP,
    LEARNING_RATE,
    build_model,
    fit_inner,
    parameter_count,
    resource_losses,
    set_seed,
)
from src.transforms import ResourceScaler, fit_partition_scaler, scale_windows
from src.validation import atomic_json_write, canonical_hash


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
SCIENTIFIC_RELATIVE_ROOT = Path("outputs/scientific_v2")
OUT = BASE / SCIENTIFIC_RELATIVE_ROOT
CRITERIA = BASE / "EXTERNAL_SCIENTIFIC_DECISION_CRITERIA.md"
AMENDMENT = BASE / "protocol_amendment"
CONFIG_PATH = BASE / "configs/bitbrains_lstm_factorial_phase4c_v2.json"
COHORT_PATH = AMENDMENT / "PHASE4C_V2_SELECTED_COHORTS.csv"
SUPPORT = AMENDMENT / "PHASE4C_V2_SUPPORT_MANIFEST.parquet"
AMENDMENT_DECISION = AMENDMENT / "PHASE4C_PROTOCOL_AMENDMENT_DECISION.md"
ELIGIBILITY = AMENDMENT / "TRAINING_SCALE_ELIGIBILITY.csv"
PHASE4B_COMMIT = "b162b8907f5f063ef969c02bd5d175edd3471028"
PHASE4B_DECISION_HASH = "247197a787250f9e81ea3b858a9f79dd8f5377d548da2fbc2bdec514e420b81e"
PHASE4B_CONFIG_HASH = "deedcd31616861f1f6ee4517cc0552a05d54d0b334364f9674b06a1dcab6dc1a"
CONFIG_HASH = "627391b84887411d8b930fd5d00cdd9a1f90f3990f958d582f4329424353fa4e"
CRITERIA_HASH = "79df6a168d7021dbafd6080640a506d22699e9d4989d422f924b178600465f12"
AMENDMENT_DECISION_HASH = "4261300afd29362cf3d7faecc068bfc8170d5ac046691e80dd7b642d0a0add57"
TRAINING_SCALE_ELIGIBILITY_VERSION = "phase4c-training-scale-eligibility-v1"
TRAINING_SCALE_ELIGIBILITY_HASH = "1ab811bc94b130a7a496eb56a0d90eac0aa6cb5616a10c5e362289476349b6a4"
EXECUTION_CORRECTION_HASH = "bd0a51380409290dd9deefd2cf25bbc783b018b559121bd21ba37fdfcb07e86d"
ENVIRONMENTS = {
    "fastStorage": "GWA-T-12_Bitbrains_fastStorage",
    "Rnd": "GWA-T-12_Bitbrains_Rnd",
}
ARCHIVE_HASHES = {
    "fastStorage": "11313f528a0cbcbe57e63162f8ae5a41a9c7e7c1a79872e294ff3c5bbaa2e671",
    "Rnd": "d3d9ddebb689c0b5463f2e4cfd8956e84bdcdf138b4476320855393e2b229a06",
}
COHORT_HASHES = {
    "fastStorage": "ff2d65ff43bedae076f913e4b9e175e7762d835eafe5efc8c2a2590e487fc07c",
    "Rnd": "f175f8b443adbed472caf5a2b26f9d73f989faf9f68334e520655c33ae982d2e",
}

_VM_CACHE: dict[tuple[str, str], tuple[CleanVM, list[ExternalFold]]] = {}


def selected_ids() -> dict[str, list[str]]:
    frame = pd.read_csv(COHORT_PATH, dtype={"entity_id": str})
    return {
        environment: list(group.sort_values("rank").entity_id)
        for environment, group in frame.groupby("environment", sort=True)
    }


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def atomic_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(temporary, index=False, compression="zstd")
    os.replace(temporary, path)


def atomic_torch(path: Path, state: dict[str, torch.Tensor]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(state, temporary)
    os.replace(temporary, path)


def worker_init() -> None:
    torch.set_num_threads(1)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass


def environment_dir(environment_key: str) -> Path:
    return OUT / environment_key


def scientific_relative_path(*parts: str) -> Path:
    """Return a canonical repository-relative path inside the V2 namespace."""
    path = SCIENTIFIC_RELATIVE_ROOT.joinpath(*parts)
    if not path.is_relative_to(SCIENTIFIC_RELATIVE_ROOT):
        raise ValueError("V2 artifact escaped the scientific_v2 namespace")
    return path


def completion_access_metadata(
    phase: str,
    *,
    evaluation_completed: bool = False,
    prediction_persisted: bool = False,
    metric_record_count: int = 0,
) -> dict[str, Any]:
    """Encode test access only after a successful authorized final evaluation."""
    if phase == "inner":
        if evaluation_completed or prediction_persisted or metric_record_count:
            raise ValueError("Inner completion cannot record outer-test activity")
        accessed = False
    elif phase == "final":
        if not evaluation_completed or not prediction_persisted or metric_record_count <= 0:
            raise RuntimeError("Final completion requires completed test evaluation and artifacts")
        accessed = True
    else:
        raise ValueError(f"Unknown completion phase: {phase}")
    return {
        "outer_test_accessed": accessed,
        "execution_correction_sha256": EXECUTION_CORRECTION_HASH,
    }


def vm_data(environment_key: str, vm_id: str) -> tuple[CleanVM, list[ExternalFold]]:
    cache_key = (environment_key, vm_id)
    if cache_key not in _VM_CACHE:
        environment = ENVIRONMENTS[environment_key]
        clean = clean_and_segment(read_vm(environment, vm_id))
        folds = build_folds(clean.frame, environment, vm_id, legal_origins(clean.frame))
        _VM_CACHE[cache_key] = (clean, folds)
    return _VM_CACHE[cache_key]


def scaler_payload(scaler: ResourceScaler) -> dict[str, list[float]]:
    return {
        "transformed_median": scaler.transformed_median.tolist(),
        "transformed_iqr": scaler.transformed_iqr.tolist(),
        "native_iqr": scaler.native_iqr.tolist(),
    }


def run_identity(
    environment_key: str,
    formulation: str,
    resource_name: str | None,
    vm_id: str,
    fold: int,
    context_length: int,
    seed: int,
    phase: str,
    support_hash: str,
    selected_epoch: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "environment": ENVIRONMENTS[environment_key],
        "environment_key": environment_key,
        "formulation": formulation,
        "resource": resource_name,
        "vm_id": vm_id,
        "fold": fold,
        "L": context_length,
        "seed": seed,
        "phase": phase,
        "config_hash": CONFIG_HASH,
        "phase4c_amendment_decision_hash": AMENDMENT_DECISION_HASH,
        "training_scale_eligibility_version": TRAINING_SCALE_ELIGIBILITY_VERSION,
        "training_scale_eligibility_hash": TRAINING_SCALE_ELIGIBILITY_HASH,
        "phase4b_decision_hash": PHASE4B_DECISION_HASH,
        "criteria_hash": CRITERIA_HASH,
        "support_hash": support_hash,
        "archive_hash": ARCHIVE_HASHES[environment_key],
        "cohort_hash": COHORT_HASHES[environment_key],
    }
    if selected_epoch is not None:
        payload["selected_epoch"] = int(selected_epoch)
    payload["run_id"] = canonical_hash(payload)[:24]
    return payload


def completion_path(environment_key: str, phase: str, run_id: str) -> Path:
    return environment_dir(environment_key) / "runtime/completions" / phase / f"{run_id}.json"


def valid_inner(path: Path, expected: dict[str, Any]) -> bool:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return (
        payload.get("status") == "complete"
        and payload.get("identity") == expected
        and payload.get("outer_test_accessed") is False
        and payload.get("execution_correction_sha256") == EXECUTION_CORRECTION_HASH
        and isinstance(payload.get("best_epoch"), int)
        and isinstance(payload.get("validation_nmae"), list)
    )


def valid_final(path: Path, expected: dict[str, Any]) -> bool:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    if (
        payload.get("status") != "complete"
        or payload.get("identity") != expected
        or payload.get("outer_test_accessed") is not True
        or payload.get("execution_correction_sha256") != EXECUTION_CORRECTION_HASH
    ):
        return False
    for key in ("model", "prediction"):
        artifact = BASE / payload.get(f"{key}_path", "missing")
        if not artifact.is_file() or digest(artifact) != payload.get(f"{key}_sha256"):
            return False
    expected_metric_rows = 20 if expected["formulation"] == "M1" else 5
    return len(payload.get("metrics", [])) == expected_metric_rows


def scaled_views(
    X: np.ndarray,
    y: np.ndarray,
    formulation: str,
    target: str | None,
) -> tuple[np.ndarray, np.ndarray]:
    if formulation == "M1":
        return X, y
    index = RESOURCE_ORDER.index(str(target))
    return (X[:, :, index:index + 1] if formulation == "S1" else X), y[:, index, :]


def split_hash(fold: ExternalFold, *names: str) -> str:
    return canonical_hash({name: fold.hashes[name] for name in names})


def inner_worker(task: dict[str, Any]) -> dict[str, float]:
    environment_key = task["environment_key"]
    formulation = task["formulation"]
    vm_id = task["vm_id"]
    fold_number = int(task["fold"])
    length = int(task["L"])
    clean, folds = vm_data(environment_key, vm_id)
    fold = folds[fold_number - 1]
    support = split_hash(fold, "inner_train", "inner_validation")
    targets: tuple[str | None, ...] = RESOURCE_ORDER if formulation in {"S1", "S2"} else (None,)
    pending: list[tuple[str | None, int, dict[str, Any]]] = []
    for target in targets:
        for seed in SEEDS:
            identity = run_identity(
                environment_key, formulation, target, vm_id, fold_number,
                length, seed, "inner", support,
            )
            if not valid_inner(completion_path(environment_key, "inner", identity["run_id"]), identity):
                pending.append((target, seed, identity))
    if not pending:
        return {"executed": 0, "skipped": len(targets) * len(SEEDS), "fit_seconds": 0.0, "peak_rss_bytes": 0}

    scaler = fit_partition_scaler(clean.frame, fold.inner_train, length)
    X_train, y_train, _ = build_windows(clean.frame, fold.inner_train, length)
    X_validation, y_validation, _ = build_windows(clean.frame, fold.inner_validation, length)
    X_train, y_train = scale_windows(X_train, y_train, scaler)
    X_validation, y_validation = scale_windows(X_validation, y_validation, scaler)
    seconds = 0.0
    peak_rss = 0
    for target, seed, identity in pending:
        train_x, train_y = scaled_views(X_train, y_train, formulation, target)
        validation_x, validation_y = scaled_views(X_validation, y_validation, formulation, target)
        result = fit_inner(
            formulation, target, seed, train_x, train_y,
            validation_x, validation_y, device="cpu",
        )
        train_seconds = float(sum(result.epoch_train_seconds))
        validation_seconds = float(sum(result.epoch_validation_seconds))
        seconds += train_seconds + validation_seconds
        peak_rss = max(peak_rss, result.peak_rss_bytes)
        validation_nmae = np.mean(
            np.abs(validation_y - result.validation_prediction), axis=0
        ).tolist()
        payload = {
            "status": "complete",
            "identity": identity,
            "best_epoch": int(result.best_epoch),
            "epochs_trained": int(result.epochs_trained),
            "validation_nmae": validation_nmae,
            "train_seconds": train_seconds,
            "validation_seconds": validation_seconds,
            "parameter_count": parameter_count(result.model),
            "inner_train_n": len(train_x),
            "inner_validation_n": len(validation_x),
            "inner_train_hash": fold.hashes["inner_train"],
            "inner_validation_hash": fold.hashes["inner_validation"],
            "scaler_fit_split": "inner_train_only",
            "scaler": scaler_payload(scaler),
            "epoch_logs": result.epoch_logs if formulation == "M1" else [],
            **completion_access_metadata("inner"),
            "peak_rss_bytes": int(result.peak_rss_bytes),
        }
        atomic_json_write(completion_path(environment_key, "inner", identity["run_id"]), payload)
    return {
        "executed": len(pending),
        "skipped": len(targets) * len(SEEDS) - len(pending),
        "fit_seconds": seconds,
        "peak_rss_bytes": peak_rss,
    }


def inner_records(environment_key: str) -> list[dict[str, Any]]:
    directory = environment_dir(environment_key) / "runtime/completions/inner"
    return [json.loads(path.read_text()) for path in sorted(directory.glob("*.json"))]


def select_all_contexts(
    environment_key: str,
    records: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup = {
        (
            row["identity"]["formulation"], row["identity"]["resource"],
            row["identity"]["vm_id"], row["identity"]["fold"],
            row["identity"]["L"], row["identity"]["seed"],
        ): row
        for row in records
    }
    context_rows: list[dict[str, Any]] = []
    epoch_rows: list[dict[str, Any]] = []
    vm_ids = selected_ids()[ENVIRONMENTS[environment_key]]
    for formulation in ("S1", "S2", "M1"):
        targets: tuple[str | None, ...] = RESOURCE_ORDER if formulation in {"S1", "S2"} else (None,)
        for target in targets:
            for vm_id in vm_ids:
                for fold in range(1, 6):
                    candidates = []
                    for length in CONTEXTS:
                        for seed in SEEDS:
                            row = lookup[(formulation, target, vm_id, fold, length, seed)]
                            candidates.append(SelectionRow(
                                formulation, length, seed,
                                np.asarray(row["validation_nmae"], dtype=float),
                                int(row["best_epoch"]),
                            ))
                    result = select_context(candidates, formulation)
                    context_rows.append({
                        "environment": ENVIRONMENTS[environment_key],
                        "environment_key": environment_key,
                        "formulation": formulation,
                        "resource": target,
                        "vm_id": vm_id,
                        "fold": fold,
                        "selected_L": result.context_length,
                        "selection_score": result.score,
                        "selection_source": "inner_validation_only",
                    })
                    for seed, epoch in result.best_epoch_by_seed.items():
                        epoch_rows.append({
                            "environment": ENVIRONMENTS[environment_key],
                            "environment_key": environment_key,
                            "formulation": formulation,
                            "resource": target,
                            "vm_id": vm_id,
                            "fold": fold,
                            "seed": seed,
                            "selected_L": result.context_length,
                            "selected_epoch": epoch,
                        })
    contexts = pd.DataFrame(context_rows)
    epochs = pd.DataFrame(epoch_rows)
    contexts.to_csv(environment_dir(environment_key) / "selected_contexts.csv", index=False)
    epochs.to_csv(environment_dir(environment_key) / "selected_epochs.csv", index=False)
    return contexts, epochs


def fit_final_model(
    formulation: str,
    target: str | None,
    seed: int,
    X: np.ndarray,
    y: np.ndarray,
    epochs: int,
) -> tuple[nn.Module, list[dict[str, Any]], float, int]:
    set_seed(seed)
    model = build_model(formulation, X.shape[-1])
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(
        TensorDataset(torch.from_numpy(X.astype(np.float32)), torch.from_numpy(y.astype(np.float32))),
        batch_size=BATCH_SIZE, shuffle=True, generator=generator, num_workers=0,
    )
    logs: list[dict[str, Any]] = []
    total_seconds = 0.0
    for epoch in range(1, epochs + 1):
        model.train()
        sums: dict[str, float] = {}
        seen = 0
        started = time.perf_counter()
        for batch_x, batch_y in loader:
            optimizer.zero_grad(set_to_none=True)
            joint, losses = resource_losses(model(batch_x), batch_y, formulation, target)
            joint.backward()
            nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
            for name, value in losses.items():
                sums[name] = sums.get(name, 0.0) + float(value.detach()) * len(batch_x)
            seen += len(batch_x)
        total_seconds += time.perf_counter() - started
        means = {name: value / seen for name, value in sums.items()}
        denominator = sum(means.values())
        logs.append({
            "epoch": epoch,
            "train_resource_mse": means,
            "train_loss_share": {name: value / denominator for name, value in means.items()},
            "joint_loss": denominator / len(means),
        })
    model.eval()
    rss = process_resource.getrusage(process_resource.RUSAGE_SELF).ru_maxrss
    rss_bytes = int(rss if rss > 10_000_000 else rss * 1024)
    return model, logs, total_seconds, rss_bytes


def prediction_frame(
    identity: dict[str, Any],
    resource_name: str,
    clean: CleanVM,
    origins: np.ndarray,
    selected_epoch: int,
    y_true: np.ndarray,
    prediction_scaled: np.ndarray,
    prediction_native: np.ndarray,
    prediction_unclipped: np.ndarray,
) -> pd.DataFrame:
    origins = np.asarray(origins, dtype=np.int64)
    leads = np.asarray(LEADS, dtype=np.int64)
    targets = origins[:, None] + leads
    timestamps = clean.frame.timestamp_seconds.to_numpy(dtype=np.int64)
    n = len(origins)
    return pd.DataFrame({
        "run_id": identity["run_id"],
        "environment": identity["environment"],
        "formulation": identity["formulation"],
        "resource": resource_name,
        "vm_id": identity["vm_id"],
        "fold": identity["fold"],
        "seed": identity["seed"],
        "selected_L": identity["L"],
        "selected_epoch": selected_epoch,
        "origin_index": np.repeat(origins, len(LEADS)),
        "origin_timestamp_seconds": np.repeat(timestamps[origins], len(LEADS)),
        "lead": np.tile(leads, n),
        "horizon_minutes": np.tile(np.asarray(HORIZON_MINUTES), n),
        "target_index": targets.ravel(),
        "target_timestamp_seconds": timestamps[targets].ravel(),
        "y_true": y_true.ravel(),
        "y_pred_scaled": prediction_scaled.ravel(),
        "y_pred": prediction_native.ravel(),
        "y_pred_unclipped": prediction_unclipped.ravel(),
        "support_hash": identity["support_hash"],
    })


def final_worker(task: dict[str, Any]) -> dict[str, float]:
    environment_key = task["environment_key"]
    formulation = task["formulation"]
    vm_id = task["vm_id"]
    fold_number = int(task["fold"])
    clean, folds = vm_data(environment_key, vm_id)
    fold = folds[fold_number - 1]
    support = split_hash(fold, "outer_train", "outer_test")
    executed = skipped = 0
    fit_seconds = prediction_seconds = 0.0
    peak_rss = 0
    cache: dict[int, tuple[ResourceScaler, np.ndarray, np.ndarray]] = {}
    for spec in task["specs"]:
        target = spec["resource"]
        seed = int(spec["seed"])
        length = int(spec["L"])
        epoch_count = int(spec["epoch"])
        identity = run_identity(
            environment_key, formulation, target, vm_id, fold_number,
            length, seed, "final", support, selected_epoch=epoch_count,
        )
        completion = completion_path(environment_key, "final", identity["run_id"])
        if valid_final(completion, identity):
            skipped += 1
            continue
        if length not in cache:
            scaler = fit_partition_scaler(clean.frame, fold.outer_train, length)
            X_train, y_train, _ = build_windows(clean.frame, fold.outer_train, length)
            X_train, y_train = scale_windows(X_train, y_train, scaler)
            cache[length] = (scaler, X_train, y_train)
        scaler, X_train, y_train = cache[length]
        train_x, train_y = scaled_views(X_train, y_train, formulation, target)
        model, loss_logs, seconds, rss = fit_final_model(
            formulation, target, seed, train_x, train_y, epoch_count,
        )
        fit_seconds += seconds
        peak_rss = max(peak_rss, rss)
        relative_model = scientific_relative_path(
            environment_key, formulation.lower(), "models", f"{identity['run_id']}.pt"
        )
        model_path = BASE / relative_model
        atomic_torch(model_path, model.state_dict())

        # Outer-test values are materialized only after the fixed-epoch refit is complete.
        X_test_native, y_test_native, persistence_native = build_windows(
            clean.frame, fold.outer_test, length
        )
        X_test, y_test = scale_windows(X_test_native, y_test_native, scaler)
        test_x, _ = scaled_views(X_test, y_test, formulation, target)
        started = time.perf_counter()
        with torch.no_grad():
            prediction_scaled = model(torch.from_numpy(test_x.astype(np.float32))).numpy()
        run_prediction_seconds = time.perf_counter() - started
        prediction_seconds += run_prediction_seconds

        resources = RESOURCE_ORDER if formulation == "M1" else (str(target),)
        prediction_frames: list[pd.DataFrame] = []
        metric_rows: list[dict[str, Any]] = []
        persistence_rows: list[dict[str, Any]] = []
        for resource_name in resources:
            resource_index = RESOURCE_ORDER.index(resource_name)
            scaled_part = (
                prediction_scaled[:, resource_index, :]
                if formulation == "M1" else prediction_scaled
            )
            native_prediction, negative_rate, unclipped = scaler.inverse_one(
                scaled_part, resource_name, project=True
            )
            truth = y_test_native[:, resource_index, :]
            persistence = persistence_native[:, resource_index, :]
            calculated = per_lead_metrics(
                truth, native_prediction, float(scaler.native_iqr[resource_index]), persistence
            )
            baseline = per_lead_metrics(
                truth, persistence, float(scaler.native_iqr[resource_index])
            )
            for position, (lead, minutes) in enumerate(zip(LEADS, HORIZON_MINUTES)):
                common = {
                    "environment": ENVIRONMENTS[environment_key],
                    "environment_key": environment_key,
                    "formulation": formulation,
                    "resource": resource_name,
                    "vm_id": vm_id,
                    "fold": fold_number,
                    "seed": seed,
                    "lead": lead,
                    "horizon_minutes": minutes,
                    "selected_L": length,
                    "selected_epoch": epoch_count,
                    "n": len(truth),
                    "outer_test_hash": fold.hashes["outer_test"],
                }
                metric_rows.append(common | {
                    "run_id": identity["run_id"],
                    "mae": float(calculated["mae"][position]),
                    "rmse": float(calculated["rmse"][position]),
                    "r2": float(calculated["r2"][position]),
                    "nmae": float(calculated["nmae"][position]),
                    "persistence_skill": float(calculated["persistence_skill"][position]),
                    "pre_projection_negative_fraction": float(negative_rate),
                })
                persistence_rows.append(common | {
                    "mae": float(baseline["mae"][position]),
                    "rmse": float(baseline["rmse"][position]),
                    "r2": float(baseline["r2"][position]),
                    "nmae": float(baseline["nmae"][position]),
                })
            prediction_frames.append(prediction_frame(
                identity, resource_name, clean, fold.outer_test, epoch_count,
                truth, scaled_part, native_prediction, unclipped,
            ))

        relative_prediction = scientific_relative_path(
            environment_key, formulation.lower(), "predictions", f"{identity['run_id']}.parquet"
        )
        prediction_path = BASE / relative_prediction
        atomic_parquet(prediction_path, pd.concat(prediction_frames, ignore_index=True))
        payload = {
            "status": "complete",
            "identity": identity,
            "model_path": relative_model.as_posix(),
            "model_sha256": digest(model_path),
            "model_bytes": model_path.stat().st_size,
            "prediction_path": relative_prediction.as_posix(),
            "prediction_sha256": digest(prediction_path),
            "prediction_bytes": prediction_path.stat().st_size,
            "metrics": metric_rows,
            "persistence_metrics": persistence_rows,
            "outer_train_n": len(train_x),
            "outer_test_n": len(test_x),
            "outer_train_hash": fold.hashes["outer_train"],
            "outer_test_hash": fold.hashes["outer_test"],
            "scaler_fit_split": "complete_legal_outer_train_only",
            "scaler": scaler_payload(scaler),
            "train_seconds": seconds,
            "prediction_seconds": run_prediction_seconds,
            "peak_rss_bytes": rss,
            "epoch_logs": loss_logs if formulation == "M1" else [],
            "test_evaluations": 1,
            **completion_access_metadata(
                "final",
                evaluation_completed=True,
                prediction_persisted=prediction_path.is_file(),
                metric_record_count=len(metric_rows),
            ),
        }
        atomic_json_write(completion, payload)
        executed += 1
    return {
        "executed": executed,
        "skipped": skipped,
        "fit_seconds": fit_seconds,
        "prediction_seconds": prediction_seconds,
        "peak_rss_bytes": peak_rss,
    }


def run_tasks(
    tasks: list[dict[str, Any]],
    worker: Any,
    workers: int,
    label: str,
) -> dict[str, float]:
    totals = {
        "executed": 0.0,
        "skipped": 0.0,
        "fit_seconds": 0.0,
        "prediction_seconds": 0.0,
        "peak_rss_bytes": 0.0,
    }
    context = mp.get_context("spawn")
    with context.Pool(workers, initializer=worker_init) as pool:
        for completed, result in enumerate(pool.imap_unordered(worker, tasks, chunksize=1), 1):
            for key in totals:
                if key == "peak_rss_bytes":
                    totals[key] = max(totals[key], result.get(key, 0))
                else:
                    totals[key] += result.get(key, 0)
            if completed % 10 == 0 or completed == len(tasks):
                print(
                    f"PROGRESS {label} groups={completed}/{len(tasks)} "
                    f"fits_executed={int(totals['executed'])} "
                    f"fits_skipped={int(totals['skipped'])}",
                    flush=True,
                )
    return totals


def support_snapshot(environment_key: str) -> None:
    source = pd.read_parquet(SUPPORT)
    source = source[source.environment.eq(ENVIRONMENTS[environment_key])].copy()
    if len(source) != 525:
        raise RuntimeError(f"Expected 525 frozen support rows, found {len(source)}")
    for (_vm, _fold), group in source.groupby(["vm_id", "fold"]):
        if set(group.L) != set(CONTEXTS):
            raise RuntimeError("Frozen support contexts differ")
        for split in ("inner_train", "inner_validation", "outer_train", "outer_test"):
            if group[f"{split}_hash"].nunique() != 1:
                raise RuntimeError("Frozen maximum-history support differs by context")
    atomic_parquet(environment_dir(environment_key) / "support_reference.parquet", source)


def consolidate(
    environment_key: str,
    contexts: pd.DataFrame,
    epochs: pd.DataFrame,
    stage_runtime: dict[str, Any],
    invocation_started: float,
) -> None:
    inner = inner_records(environment_key)
    inner_rows: list[dict[str, Any]] = []
    m1_loss_rows: list[dict[str, Any]] = []
    for row in inner:
        item = row["identity"] | {
            "best_epoch": row["best_epoch"],
            "epochs_trained": row["epochs_trained"],
            "validation_nmae": json.dumps(row["validation_nmae"], separators=(",", ":")),
            "train_seconds": row["train_seconds"],
            "validation_seconds": row["validation_seconds"],
            "peak_rss_bytes": row["peak_rss_bytes"],
        }
        inner_rows.append(item)
        if item["formulation"] == "M1":
            for log in row["epoch_logs"]:
                for resource_name in RESOURCE_ORDER:
                    m1_loss_rows.append({
                        "phase": "inner",
                        "run_id": item["run_id"],
                        "environment": item["environment"],
                        "vm_id": item["vm_id"],
                        "fold": item["fold"],
                        "L": item["L"],
                        "seed": item["seed"],
                        "epoch": log["epoch"],
                        "resource": resource_name,
                        "validation_resource_mse": log["validation_resource_mse"][resource_name],
                        "validation_loss_share": log["validation_loss_share"][resource_name],
                        "train_resource_mse": log["train_resource_mse"][resource_name],
                        "train_loss_share": log["train_loss_share"][resource_name],
                    })
    inner_frame = pd.DataFrame(inner_rows).sort_values(
        ["formulation", "vm_id", "fold", "resource", "L", "seed"], na_position="last"
    )
    inner_frame.to_csv(environment_dir(environment_key) / "inner_run_registry.csv", index=False)

    final_directory = environment_dir(environment_key) / "runtime/completions/final"
    final_records = [json.loads(path.read_text()) for path in sorted(final_directory.glob("*.json"))]
    registry_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    persistence_rows: list[dict[str, Any]] = []
    for row in final_records:
        item = row["identity"] | {
            "model_path": row["model_path"],
            "model_sha256": row["model_sha256"],
            "model_bytes": row["model_bytes"],
            "prediction_path": row["prediction_path"],
            "prediction_sha256": row["prediction_sha256"],
            "prediction_bytes": row["prediction_bytes"],
            "train_seconds": row["train_seconds"],
            "prediction_seconds": row["prediction_seconds"],
            "peak_rss_bytes": row["peak_rss_bytes"],
        }
        registry_rows.append(item)
        metric_rows.extend(row["metrics"])
        persistence_rows.extend(row["persistence_metrics"])
        if item["formulation"] == "M1":
            for log in row["epoch_logs"]:
                for resource_name in RESOURCE_ORDER:
                    m1_loss_rows.append({
                        "phase": "final",
                        "run_id": item["run_id"],
                        "environment": item["environment"],
                        "vm_id": item["vm_id"],
                        "fold": item["fold"],
                        "L": item["L"],
                        "seed": item["seed"],
                        "epoch": log["epoch"],
                        "resource": resource_name,
                        "validation_resource_mse": np.nan,
                        "validation_loss_share": np.nan,
                        "train_resource_mse": log["train_resource_mse"][resource_name],
                        "train_loss_share": log["train_loss_share"][resource_name],
                    })
    registry = pd.DataFrame(registry_rows).sort_values(
        ["formulation", "vm_id", "fold", "resource", "seed"], na_position="last"
    )
    metrics = pd.DataFrame(metric_rows).sort_values(
        ["formulation", "resource", "vm_id", "fold", "seed", "lead"]
    )
    persistence = pd.DataFrame(persistence_rows).sort_values(
        ["formulation", "resource", "vm_id", "fold", "seed", "lead"]
    )
    registry.to_csv(environment_dir(environment_key) / "run_registry.csv", index=False)
    atomic_parquet(environment_dir(environment_key) / "metrics.parquet", metrics)
    atomic_parquet(environment_dir(environment_key) / "persistence_metrics.parquet", persistence)
    atomic_parquet(
        environment_dir(environment_key) / "m1_resource_loss_history.parquet",
        pd.DataFrame(m1_loss_rows),
    )
    if len(inner_frame) != 14_175:
        raise RuntimeError(f"Expected 14,175 inner fits, found {len(inner_frame)}")
    if len(registry) != 4_725:
        raise RuntimeError(f"Expected 4,725 final fits, found {len(registry)}")
    if len(metrics) != 31_500:
        raise RuntimeError(f"Expected 31,500 metric rows, found {len(metrics)}")
    if len(contexts) != 1_575 or len(epochs) != 4_725:
        raise RuntimeError("Selected context/epoch count mismatch")
    expected = {
        "S1": {"inner": 6_300, "final": 2_100, "metrics": 10_500},
        "S2": {"inner": 6_300, "final": 2_100, "metrics": 10_500},
        "M1": {"inner": 1_575, "final": 525, "metrics": 10_500},
    }
    observed = {
        formulation: {
            "inner": int(inner_frame.formulation.eq(formulation).sum()),
            "final": int(registry.formulation.eq(formulation).sum()),
            "metrics": int(metrics.formulation.eq(formulation).sum()),
        }
        for formulation in ("S1", "S2", "M1")
    }
    if observed != expected:
        raise RuntimeError(f"Per-formulation counts differ: {observed}")
    accounting = {
        "status": "EXECUTION_COMPLETE_TECHNICAL_VALIDATION_PENDING",
        "environment": ENVIRONMENTS[environment_key],
        "environment_key": environment_key,
        "criteria_sha256": CRITERIA_HASH,
        "config_sha256": CONFIG_HASH,
        "counts": observed,
        "inner_total": len(inner_frame),
        "final_total": len(registry),
        "fit_total": len(inner_frame) + len(registry),
        "metric_rows": len(metrics),
        "selected_context_records": len(contexts),
        "stage_runtime": stage_runtime,
        "summed_inner_fit_seconds": float(
            (inner_frame.train_seconds + inner_frame.validation_seconds).sum()
        ),
        "summed_final_fit_seconds": float(registry.train_seconds.sum()),
        "summed_prediction_seconds": float(registry.prediction_seconds.sum()),
        "invocation_wall_seconds": time.perf_counter() - invocation_started,
        "peak_rss_bytes": int(max(
            inner_frame.peak_rss_bytes.max(), registry.peak_rss_bytes.max()
        )),
        "model_artifact_bytes": int(registry.model_bytes.sum()),
        "prediction_artifact_bytes": int(registry.prediction_bytes.sum()),
        "newly_executed_fits": int(sum(
            value["executed"] for value in stage_runtime.values()
        )),
        "resumed_skipped_valid_fits": int(sum(
            value["skipped"] for value in stage_runtime.values()
        )),
        "failed_retried_fits": 0,
    }
    atomic_json_write(environment_dir(environment_key) / "runtime/runtime_accounting.json", accounting)


def verify_frozen_identities() -> None:
    if digest(PHASE4B_CONFIG_PATH) != PHASE4B_CONFIG_HASH:
        raise RuntimeError("Frozen Phase 4B config differs")
    if digest(CONFIG_PATH) != CONFIG_HASH:
        raise RuntimeError("Frozen amended Phase 4C V2 config differs")
    if digest(BASE / "EXTERNAL_FACTORIAL_DECISION.md") != PHASE4B_DECISION_HASH:
        raise RuntimeError("Frozen Phase 4B decision differs")
    if digest(CRITERIA) != CRITERIA_HASH:
        raise RuntimeError("Prospective Phase 4C criteria differ")
    if digest(AMENDMENT_DECISION) != AMENDMENT_DECISION_HASH:
        raise RuntimeError("Prospective Phase 4C amendment decision differs")
    if digest(ELIGIBILITY) != TRAINING_SCALE_ELIGIBILITY_HASH:
        raise RuntimeError("Training-scale eligibility audit differs")
    tag_target = subprocess.check_output(
        ["git", "rev-parse", "phase4b-bitbrains-factorial-protocol-freeze-v1^{}"],
        cwd=ROOT, text=True,
    ).strip()
    if tag_target != PHASE4B_COMMIT:
        raise RuntimeError("Phase 4B checkpoint tag differs")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", PHASE4B_COMMIT, "HEAD"],
        cwd=ROOT, check=False,
    )
    if ancestor.returncode != 0:
        raise RuntimeError("Current HEAD does not contain the frozen Phase 4B checkpoint")


def plan(environment_key: str) -> dict[str, Any]:
    vm_count = len(selected_ids()[ENVIRONMENTS[environment_key]])
    return {
        "environment_key": environment_key,
        "environment": ENVIRONMENTS[environment_key],
        "selected_vms": vm_count,
        "inner_groups_per_formulation": vm_count * 5 * len(CONTEXTS),
        "inner_fits": {"S1": 6_300, "S2": 6_300, "M1": 1_575},
        "final_fits": {"S1": 2_100, "S2": 2_100, "M1": 525},
        "total_fits": 18_900,
        "metric_rows": 31_500,
        "selected_context_records": 1_575,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", choices=tuple(ENVIRONMENTS), required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    verify_frozen_identities()
    if args.plan:
        print(json.dumps(plan(args.environment), indent=2, sort_keys=True))
        return
    if args.workers < 1:
        raise ValueError("workers must be positive")
    invocation_started = time.perf_counter()
    env_dir = environment_dir(args.environment)
    for relative in (
        "s1/models", "s1/predictions", "s2/models", "s2/predictions",
        "m1/models", "m1/predictions", "validation",
        "runtime/completions/inner", "runtime/completions/final",
    ):
        (env_dir / relative).mkdir(parents=True, exist_ok=True)
    support_snapshot(args.environment)
    vm_ids = selected_ids()[ENVIRONMENTS[args.environment]]
    stage_runtime: dict[str, Any] = {}
    for formulation in ("S1", "S2", "M1"):
        tasks = [
            {
                "environment_key": args.environment,
                "formulation": formulation,
                "vm_id": vm_id,
                "fold": fold,
                "L": length,
            }
            for vm_id in vm_ids
            for fold in range(1, 6)
            for length in CONTEXTS
        ]
        stage_runtime[f"{formulation}_inner"] = run_tasks(
            tasks, inner_worker, args.workers, f"{args.environment}_{formulation}_INNER"
        )
    records = inner_records(args.environment)
    if len(records) != 14_175:
        raise RuntimeError(f"Expected 14,175 inner completion records, found {len(records)}")
    contexts, epochs = select_all_contexts(args.environment, records)
    for formulation in ("S1", "S2", "M1"):
        tasks = []
        for vm_id in vm_ids:
            for fold in range(1, 6):
                selected = epochs[
                    epochs.formulation.eq(formulation)
                    & epochs.vm_id.astype(str).eq(str(vm_id))
                    & epochs.fold.eq(fold)
                ]
                specs = [
                    {
                        "resource": None if pd.isna(row.resource) else row.resource,
                        "seed": int(row.seed),
                        "L": int(row.selected_L),
                        "epoch": int(row.selected_epoch),
                    }
                    for row in selected.itertuples(index=False)
                ]
                tasks.append({
                    "environment_key": args.environment,
                    "formulation": formulation,
                    "vm_id": vm_id,
                    "fold": fold,
                    "specs": specs,
                })
        stage_runtime[f"{formulation}_final"] = run_tasks(
            tasks, final_worker, args.workers, f"{args.environment}_{formulation}_FINAL"
        )
    consolidate(args.environment, contexts, epochs, stage_runtime, invocation_started)
    print(
        f"ENVIRONMENT_EXECUTION_COMPLETE environment={args.environment} "
        "technical_validation_pending=true scientific_analysis_started=false",
        flush=True,
    )


if __name__ == "__main__":
    main()
