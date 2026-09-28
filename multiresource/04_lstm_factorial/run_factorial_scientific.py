#!/usr/bin/env python3
"""Execute the frozen Phase 3C S1/S2/M1 factorial with atomic resumability."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import resource as process_resource
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from src.data import CONTEXT_LENGTHS, FUTURE_LEADS, MACHINES, RESOURCE_ORDER, build_raw_windows, load_panel
from src.metrics import inverse_one, per_lead_metrics
from src.selection import SelectionRow, select_context
from src.splits import build_factorial_folds
from src.training import BATCH_SIZE, GRADIENT_CLIP, LEARNING_RATE, build_model, fit_inner, parameter_count, resource_losses, set_seed
from src.transforms import fit_partition_scaler, scale_windows
from src.validation import atomic_json_write, canonical_hash


BASE = Path(__file__).resolve().parent
OUT = BASE / "outputs/scientific"
CONFIG = BASE / "configs/lstm_factorial.json"
CRITERIA = BASE / "FACTORIAL_SCIENTIFIC_DECISION_CRITERIA.md"
FROZEN_CONFIG_HASH = "fe985007ebd72417dcab8e8a1851c358d3d9a3da26f372595ac7ff6b499eedd6"
CRITERIA_HASH = "3157a233c3c76b126ff939f7e0588c9c2d21f98bb7d3e6355f13a5d1bc470d57"
_PANEL: pd.DataFrame | None = None


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(temporary, index=False, compression="zstd")
    os.replace(temporary, path)


def atomic_torch(path: Path, payload: dict[str, torch.Tensor]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, temporary)
    os.replace(temporary, path)


def worker_init() -> None:
    global _PANEL
    torch.set_num_threads(1)
    try: torch.set_num_interop_threads(1)
    except RuntimeError: pass
    _PANEL = load_panel()


def panel() -> pd.DataFrame:
    global _PANEL
    if _PANEL is None: _PANEL = load_panel()
    return _PANEL


def identity(formulation: str, target: str | None, machine: str, fold: int, length: int, seed: int, phase: str, support_hash: str) -> dict[str, Any]:
    payload = {"formulation": formulation, "resource": target, "machine": machine, "fold": fold, "L": length, "seed": seed, "phase": phase, "config_hash": FROZEN_CONFIG_HASH, "criteria_hash": CRITERIA_HASH, "support_hash": support_hash}
    payload["run_id"] = canonical_hash(payload)[:24]
    return payload


def completion_path(phase: str, run_id: str) -> Path:
    return OUT / "runtime/completions" / phase / f"{run_id}.json"


def valid_inner(path: Path, expected: dict[str, Any]) -> bool:
    try: payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError): return False
    return payload.get("status") == "complete" and payload.get("identity") == expected and "validation_nmae" in payload and "best_epoch" in payload


def valid_final(path: Path, expected: dict[str, Any]) -> bool:
    try: payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError): return False
    if payload.get("status") != "complete" or payload.get("identity") != expected: return False
    for key in ("model", "prediction"):
        artifact = BASE.parents[1] / payload[f"{key}_path"]
        if not artifact.exists() or digest(artifact) != payload[f"{key}_sha256"]: return False
    return len(payload.get("metrics", [])) in {8, 32}


def scaled_views(X: np.ndarray, y: np.ndarray, formulation: str, target: str | None) -> tuple[np.ndarray, np.ndarray]:
    if formulation == "M1": return X, y
    index = RESOURCE_ORDER.index(str(target))
    return (X[:, :, index:index + 1] if formulation == "S1" else X), y[:, index, :]


def inner_worker(task: dict[str, Any]) -> dict[str, Any]:
    formulation, machine, fold_number, length = task["formulation"], task["machine"], task["fold"], task["L"]
    fold = build_factorial_folds(panel(), machine, length)[fold_number - 1]
    support_hash = canonical_hash({"train": fold.hashes["inner_train"], "validation": fold.hashes["inner_validation"]})
    targets = RESOURCE_ORDER if formulation in {"S1", "S2"} else (None,)
    pending = []
    for target in targets:
        for seed in (0, 1, 2):
            run = identity(formulation, target, machine, fold_number, length, seed, "inner", support_hash)
            if not valid_inner(completion_path("inner", run["run_id"]), run): pending.append((target, seed, run))
    if not pending: return {"executed": 0, "skipped": len(targets) * 3, "seconds": 0.0}
    scaler = fit_partition_scaler(panel(), machine, fold.inner_train, length)
    train_raw = build_raw_windows(panel(), machine, length, fold.inner_train)
    validation_raw = build_raw_windows(panel(), machine, length, fold.inner_validation)
    X_train, y_train = scale_windows(train_raw.X, train_raw.y, scaler)
    X_validation, y_validation = scale_windows(validation_raw.X, validation_raw.y, scaler)
    total_seconds = 0.0
    for target, seed, run in pending:
        train_x, train_y = scaled_views(X_train, y_train, formulation, target)
        validation_x, validation_y = scaled_views(X_validation, y_validation, formulation, target)
        result = fit_inner(formulation, target, seed, train_x, train_y, validation_x, validation_y, device="cpu")
        validation_nmae = np.mean(np.abs(validation_y - result.validation_prediction), axis=0).tolist()
        payload = {"status": "complete", "identity": run, "best_epoch": result.best_epoch, "epochs_trained": result.epochs_trained, "validation_nmae": validation_nmae, "train_seconds": result.train_seconds, "validation_seconds": result.validation_seconds, "parameter_count": parameter_count(result.model), "inner_train_n": len(train_x), "inner_validation_n": len(validation_x), "inner_train_hash": fold.hashes["inner_train"], "inner_validation_hash": fold.hashes["inner_validation"], "scaler_metadata": scaler.metadata(), "epoch_logs": result.epoch_logs if formulation == "M1" else []}
        atomic_json_write(completion_path("inner", run["run_id"]), payload)
        total_seconds += result.train_seconds + result.validation_seconds
    return {"executed": len(pending), "skipped": len(targets) * 3 - len(pending), "seconds": total_seconds}


def read_inner_records() -> list[dict[str, Any]]:
    return [json.loads(path.read_text()) for path in sorted((OUT / "runtime/completions/inner").glob("*.json"))]


def select_all_contexts(records: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup = {(row["identity"]["formulation"], row["identity"]["resource"], row["identity"]["machine"], row["identity"]["fold"], row["identity"]["L"], row["identity"]["seed"]): row for row in records}
    contexts, epochs = [], []
    for formulation in ("S1", "S2", "M1"):
        targets = RESOURCE_ORDER if formulation in {"S1", "S2"} else (None,)
        for target in targets:
            for machine in MACHINES:
                for fold in range(1, 6):
                    rows = []
                    for length in CONTEXT_LENGTHS:
                        for seed in (0, 1, 2):
                            record = lookup[(formulation, target, machine, fold, length, seed)]
                            rows.append(SelectionRow(formulation, length, seed, np.asarray(record["validation_nmae"]), int(record["best_epoch"])))
                    selected = select_context(rows, formulation)
                    contexts.append({"formulation": formulation, "resource": target, "machine": machine, "fold": fold, "selected_L": selected.context_length, "selection_score": selected.score})
                    for seed, epoch in selected.best_epoch_by_seed.items():
                        epochs.append({"formulation": formulation, "resource": target, "machine": machine, "fold": fold, "seed": seed, "selected_L": selected.context_length, "selected_epoch": epoch})
    context_frame, epoch_frame = pd.DataFrame(contexts), pd.DataFrame(epochs)
    context_frame.to_csv(OUT / "selected_contexts.csv", index=False)
    epoch_frame.to_csv(OUT / "selected_epochs.csv", index=False)
    return context_frame, epoch_frame


def fit_final_model(formulation: str, target: str | None, seed: int, X: np.ndarray, y: np.ndarray, epochs: int) -> tuple[nn.Module, list[dict[str, Any]], float, int]:
    set_seed(seed); model = build_model(formulation, X.shape[-1]); optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(TensorDataset(torch.from_numpy(X.astype(np.float32)), torch.from_numpy(y.astype(np.float32))), batch_size=BATCH_SIZE, shuffle=True, generator=generator, num_workers=0)
    logs, total_seconds = [], 0.0
    for epoch in range(1, epochs + 1):
        model.train(); sums = {name: 0.0 for name in RESOURCE_ORDER}; seen = 0; started = time.perf_counter()
        for batch_x, batch_y in loader:
            optimizer.zero_grad(set_to_none=True); joint, losses = resource_losses(model(batch_x), batch_y, formulation, target)
            joint.backward(); nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP); optimizer.step()
            for name, value in losses.items(): sums[name] += float(value.detach()) * len(batch_x)
            seen += len(batch_x)
        total_seconds += time.perf_counter() - started
        means = {name: sums[name] / seen for name in losses}; denominator = sum(means.values())
        logs.append({"epoch": epoch, "train_resource_mse": means, "train_loss_share": {name: value / denominator for name, value in means.items()}, "joint_loss": sum(means.values()) / len(means)})
    rss = process_resource.getrusage(process_resource.RUSAGE_SELF).ru_maxrss
    return model.eval(), logs, total_seconds, int(rss if rss > 10_000_000 else rss * 1024)


def prediction_frame(run: dict[str, Any], resource_name: str, raw, scaled_prediction: np.ndarray, prediction: np.ndarray, unclipped: np.ndarray) -> pd.DataFrame:
    n = len(raw.origins); leads = np.asarray(FUTURE_LEADS); targets = raw.origins[:, None] + leads
    index = RESOURCE_ORDER.index(resource_name)
    return pd.DataFrame({"run_id": run["run_id"], "formulation": run["formulation"], "resource": resource_name, "machine": run["machine"], "fold": run["fold"], "seed": run["seed"], "selected_L": run["L"], "selected_epoch": run["selected_epoch"], "origin_index": np.repeat(raw.origins, 8), "lead": np.tile(leads, n), "target_index": targets.ravel(), "sample_id": np.repeat(raw.sample_ids, 8), "origin_timestamp": np.repeat(raw.origin_timestamps, 8), "target_timestamp": raw.target_timestamps.ravel(), "y_true": raw.y[:, index, :].ravel(), "y_pred_scaled": scaled_prediction.ravel(), "y_pred": prediction.ravel(), "y_pred_unclipped": unclipped.ravel(), "support_hash": raw.support_hash})


def final_worker(task: dict[str, Any]) -> dict[str, Any]:
    formulation, machine, fold_number, specs = task["formulation"], task["machine"], task["fold"], task["specs"]
    executed = skipped = 0; fit_seconds = prediction_seconds = 0.0; peak_rss = 0
    cache: dict[int, tuple[Any, Any, Any, np.ndarray, np.ndarray]] = {}
    for spec in specs:
        target, seed, length, epoch_count = spec["resource"], spec["seed"], spec["L"], spec["epoch"]
        fold = build_factorial_folds(panel(), machine, length)[fold_number - 1]
        support_hash = canonical_hash({"train": fold.hashes["outer_train"], "test": fold.hashes["outer_test"]})
        run = identity(formulation, target, machine, fold_number, length, seed, "final", support_hash); run["selected_epoch"] = epoch_count
        path = completion_path("final", run["run_id"])
        if valid_final(path, run): skipped += 1; continue
        if length not in cache:
            scaler = fit_partition_scaler(panel(), machine, fold.outer_train, length)
            train_raw = build_raw_windows(panel(), machine, length, fold.outer_train)
            X_train, y_train = scale_windows(train_raw.X, train_raw.y, scaler)
            cache[length] = (fold, scaler, train_raw, X_train, y_train)
        fold, scaler, train_raw, X_train, y_train = cache[length]
        train_x, train_y = scaled_views(X_train, y_train, formulation, target)
        model, loss_logs, seconds, rss = fit_final_model(formulation, target, seed, train_x, train_y, epoch_count)
        fit_seconds += seconds; peak_rss = max(peak_rss, rss)
        model_rel = Path(f"multiresource/04_lstm_factorial/outputs/scientific/{formulation.lower()}/models/{run['run_id']}.pt")
        model_path = BASE.parents[1] / model_rel; atomic_torch(model_path, model.state_dict())
        # Outer-test values are first materialized only after fitting is complete.
        test_raw = build_raw_windows(panel(), machine, length, fold.outer_test)
        X_test, y_test = scale_windows(test_raw.X, test_raw.y, scaler); test_x, _ = scaled_views(X_test, y_test, formulation, target)
        started = time.perf_counter()
        with torch.no_grad(): scaled_prediction = model(torch.from_numpy(test_x.astype(np.float32))).numpy()
        run_prediction_seconds = time.perf_counter() - started
        prediction_seconds += run_prediction_seconds
        resources = RESOURCE_ORDER if formulation == "M1" else (str(target),)
        frames, metric_rows, persistence_rows = [], [], []
        for resource_name in resources:
            resource_index = RESOURCE_ORDER.index(resource_name)
            scaled_part = scaled_prediction[:, resource_index, :] if formulation == "M1" else scaled_prediction
            native_prediction, negative_rate, unclipped = inverse_one(scaled_part, scaler, resource_name, project=True)
            truth = test_raw.y[:, resource_index, :]
            persistence = np.repeat(test_raw.X[:, -1, resource_index, None], 8, axis=1)
            calculated = per_lead_metrics(truth, native_prediction, scaler.native_iqr[resource_index], persistence)
            baseline = per_lead_metrics(truth, persistence, scaler.native_iqr[resource_index])
            for position, lead in enumerate(FUTURE_LEADS):
                metric_rows.append({"run_id": run["run_id"], "formulation": formulation, "resource": resource_name, "machine": machine, "fold": fold_number, "seed": seed, "lead": lead, "selected_L": length, "selected_epoch": epoch_count, "n": len(truth), "mae": float(calculated["mae"][position]), "rmse": float(calculated["rmse"][position]), "r2": float(calculated["r2"][position]), "nmae": float(calculated["nmae"][position]), "persistence_skill": float(calculated["persistence_skill"][position]), "pre_projection_negative_rate": negative_rate})
                persistence_rows.append({"formulation": formulation, "resource": resource_name, "machine": machine, "fold": fold_number, "selected_L": length, "lead": lead, "n": len(truth), "mae": float(baseline["mae"][position]), "rmse": float(baseline["rmse"][position]), "r2": float(baseline["r2"][position]), "nmae": float(baseline["nmae"][position])})
            frames.append(prediction_frame(run, resource_name, test_raw, scaled_part, native_prediction, unclipped))
        prediction_rel = Path(f"multiresource/04_lstm_factorial/outputs/scientific/{formulation.lower()}/predictions/{run['run_id']}.parquet")
        prediction_path = BASE.parents[1] / prediction_rel; atomic_parquet(prediction_path, pd.concat(frames, ignore_index=True))
        payload = {"status": "complete", "identity": run, "model_path": str(model_rel), "model_sha256": digest(model_path), "model_bytes": model_path.stat().st_size, "prediction_path": str(prediction_rel), "prediction_sha256": digest(prediction_path), "prediction_bytes": prediction_path.stat().st_size, "metrics": metric_rows, "persistence_metrics": persistence_rows, "outer_train_n": len(train_x), "outer_test_n": len(test_x), "outer_train_hash": fold.hashes["outer_train"], "outer_test_hash": fold.hashes["outer_test"], "scaler_metadata": scaler.metadata(), "train_seconds": seconds, "prediction_seconds": run_prediction_seconds, "peak_rss_bytes": rss, "epoch_logs": loss_logs if formulation == "M1" else []}
        atomic_json_write(path, payload); executed += 1
    return {"executed": executed, "skipped": skipped, "fit_seconds": fit_seconds, "prediction_seconds": prediction_seconds, "peak_rss_bytes": peak_rss}


def run_tasks(tasks: list[dict[str, Any]], worker, workers: int, label: str) -> dict[str, float]:
    totals = {"executed": 0, "skipped": 0, "seconds": 0.0, "fit_seconds": 0.0, "prediction_seconds": 0.0, "peak_rss_bytes": 0}
    context = mp.get_context("spawn")
    with context.Pool(workers, initializer=worker_init) as pool:
        for completed, result in enumerate(pool.imap_unordered(worker, tasks, chunksize=1), 1):
            for key in totals:
                if key == "peak_rss_bytes": totals[key] = max(totals[key], result.get(key, 0))
                else: totals[key] += result.get(key, 0)
            if completed % 5 == 0 or completed == len(tasks):
                print(f"PROGRESS {label} groups={completed}/{len(tasks)} fits_executed={int(totals['executed'])} fits_skipped={int(totals['skipped'])}", flush=True)
    return totals


def create_support_manifest() -> pd.DataFrame:
    source = json.loads((BASE / "pilot/SUPPORT_MANIFEST.json").read_text())["rows"]
    frame = pd.DataFrame(source).sort_values(["machine", "fold", "context_length"]).reset_index(drop=True)
    for (_machine, _fold), group in frame.groupby(["machine", "fold"]):
        for column in ("inner_train_hash", "inner_validation_hash", "outer_train_hash", "outer_test_hash"):
            if group[column].nunique() != 1: raise RuntimeError("Frozen support differs across context lengths")
    atomic_parquet(OUT / "support_manifest.parquet", frame)
    return frame


def consolidate(contexts: pd.DataFrame, epochs: pd.DataFrame, stage_runtime: dict[str, Any], started: float) -> None:
    inner = read_inner_records()
    inner_rows, m1_loss_rows = [], []
    for row in inner:
        item = row["identity"] | {"best_epoch": row["best_epoch"], "epochs_trained": row["epochs_trained"], "validation_nmae": json.dumps(row["validation_nmae"], separators=(",", ":")), "train_seconds": row["train_seconds"], "validation_seconds": row["validation_seconds"]}
        inner_rows.append(item)
        if item["formulation"] == "M1":
            for log in row["epoch_logs"]:
                for resource_name in RESOURCE_ORDER:
                    m1_loss_rows.append({"phase": "inner", "run_id": item["run_id"], "machine": item["machine"], "fold": item["fold"], "L": item["L"], "seed": item["seed"], "epoch": log["epoch"], "resource": resource_name, "resource_mse": log["validation_resource_mse"][resource_name], "loss_share": log["validation_loss_share"][resource_name], "train_resource_mse": log["train_resource_mse"][resource_name], "train_loss_share": log["train_loss_share"][resource_name]})
    pd.DataFrame(inner_rows).to_csv(OUT / "inner_run_registry.csv", index=False)
    final_records = [json.loads(path.read_text()) for path in sorted((OUT / "runtime/completions/final").glob("*.json"))]
    registry, metrics, persistence = [], [], []
    for row in final_records:
        item = row["identity"] | {"model_path": row["model_path"], "model_sha256": row["model_sha256"], "model_bytes": row["model_bytes"], "prediction_path": row["prediction_path"], "prediction_sha256": row["prediction_sha256"], "prediction_bytes": row["prediction_bytes"], "train_seconds": row["train_seconds"], "prediction_seconds": row["prediction_seconds"]}
        registry.append(item); metrics.extend(row["metrics"]); persistence.extend(row["persistence_metrics"])
        if item["formulation"] == "M1":
            for log in row["epoch_logs"]:
                for resource_name in RESOURCE_ORDER:
                    m1_loss_rows.append({"phase": "final", "run_id": item["run_id"], "machine": item["machine"], "fold": item["fold"], "L": item["L"], "seed": item["seed"], "epoch": log["epoch"], "resource": resource_name, "resource_mse": log["train_resource_mse"][resource_name], "loss_share": log["train_loss_share"][resource_name], "train_resource_mse": log["train_resource_mse"][resource_name], "train_loss_share": log["train_loss_share"][resource_name]})
    registry_frame = pd.DataFrame(registry).sort_values(["formulation", "machine", "fold", "resource", "seed"], na_position="last")
    registry_frame.to_csv(OUT / "run_registry.csv", index=False)
    metric_frame = pd.DataFrame(metrics).sort_values(["formulation", "resource", "machine", "fold", "seed", "lead"])
    atomic_parquet(OUT / "metrics.parquet", metric_frame)
    persistence_frame = pd.DataFrame(persistence).drop_duplicates(["formulation", "resource", "machine", "fold", "selected_L", "lead"]).sort_values(["formulation", "resource", "machine", "fold", "lead"])
    atomic_parquet(OUT / "persistence_metrics.parquet", persistence_frame)
    atomic_parquet(OUT / "m1_resource_loss_history.parquet", pd.DataFrame(m1_loss_rows))
    if len(inner_rows) != 2835 or len(registry_frame) != 945 or len(metric_frame) != 10080 or len(contexts) != 315 or len(epochs) != 945:
        raise RuntimeError("Scientific execution count mismatch")
    counts = {formulation: {"inner": sum(row["identity"]["formulation"] == formulation for row in inner), "final": int((registry_frame.formulation == formulation).sum()), "metrics": int((metric_frame.formulation == formulation).sum())} for formulation in ("S1", "S2", "M1")}
    accounting = {"status": "EXECUTION_COMPLETE_ANALYSIS_PENDING", "criteria_sha256": CRITERIA_HASH, "config_sha256": FROZEN_CONFIG_HASH, "counts": counts, "stage_runtime": stage_runtime, "summed_inner_fit_seconds": float(sum(row["train_seconds"] + row["validation_seconds"] for row in inner)), "summed_final_fit_seconds": float(registry_frame.train_seconds.sum()), "summed_prediction_seconds": float(registry_frame.prediction_seconds.sum()), "total_wall_seconds_current_invocation": time.perf_counter() - started, "peak_rss_bytes": int(max([row.get("peak_rss_bytes", 0) for row in final_records] or [0])), "model_artifact_bytes": int(registry_frame.model_bytes.sum()), "prediction_artifact_bytes": int(registry_frame.prediction_bytes.sum()), "scientific_tree_bytes_pre_analysis": sum(path.stat().st_size for path in OUT.rglob("*") if path.is_file())}
    atomic_json_write(OUT / "runtime/runtime_accounting.json", accounting)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--workers", type=int, default=4); args = parser.parse_args()
    if digest(CONFIG) != FROZEN_CONFIG_HASH or digest(CRITERIA) != CRITERIA_HASH: raise RuntimeError("Frozen scientific identity differs")
    started = time.perf_counter()
    for directory in ("s1/models", "s1/predictions", "s2/models", "s2/predictions", "m1/models", "m1/predictions", "comparisons", "figures", "validation", "runtime/completions/inner", "runtime/completions/final"):
        (OUT / directory).mkdir(parents=True, exist_ok=True)
    create_support_manifest()
    inner_tasks = [{"formulation": formulation, "machine": machine, "fold": fold, "L": length} for formulation in ("S1", "S2", "M1") for machine in MACHINES for fold in range(1, 6) for length in CONTEXT_LENGTHS]
    stage_runtime: dict[str, Any] = {}
    for formulation in ("S1", "S2", "M1"):
        tasks = [task for task in inner_tasks if task["formulation"] == formulation]
        stage_runtime[f"{formulation}_inner"] = run_tasks(tasks, inner_worker, args.workers, f"{formulation}_INNER")
    records = read_inner_records()
    if len(records) != 2835: raise RuntimeError(f"Expected 2835 inner records, found {len(records)}")
    contexts, epochs = select_all_contexts(records)
    final_tasks = []
    for formulation in ("S1", "S2", "M1"):
        for machine in MACHINES:
            for fold in range(1, 6):
                selected = epochs[(epochs.formulation == formulation) & (epochs.machine == machine) & (epochs.fold == fold)]
                specs = [{"resource": None if pd.isna(row.resource) else row.resource, "seed": int(row.seed), "L": int(row.selected_L), "epoch": int(row.selected_epoch)} for row in selected.itertuples(index=False)]
                final_tasks.append({"formulation": formulation, "machine": machine, "fold": fold, "specs": specs})
    for formulation in ("S1", "S2", "M1"):
        tasks = [task for task in final_tasks if task["formulation"] == formulation]
        stage_runtime[f"{formulation}_final"] = run_tasks(tasks, final_worker, args.workers, f"{formulation}_FINAL")
    consolidate(contexts, epochs, stage_runtime, started)
    print("SCIENTIFIC_EXECUTION_COMPLETE analysis_pending=true", flush=True)


if __name__ == "__main__": main()
