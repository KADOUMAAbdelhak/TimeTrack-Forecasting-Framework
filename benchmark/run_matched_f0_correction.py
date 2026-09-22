#!/usr/bin/env python3
"""Run prospective exact-support/reselected F0 comparator corrections."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from benchmark.src.data import load_canonical_panel
from benchmark.src.features import FEATURE_SET_IDS
from benchmark.src.metrics import per_lead_metrics
from benchmark.src.models.lightgbm_model import LightGBMForecaster
from benchmark.src.models.ridge import RidgeForecaster
from benchmark.src.selection import select_from_inner_validation
from benchmark.src.splits import build_inner_split, build_outer_folds
from benchmark.src.validation import deterministic_run_id
from benchmark.src.windows import FUTURE_LEADS, finite_feature_origins, joint_eligible_origins


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "benchmark" / "outputs"
ORIGINAL_AUDIT = ROOT / "benchmark" / "phase2b1_original"
BASE = ROOT / "benchmark" / "phase2b1_corrected"
OUTPUTS = BASE / "outputs"
PREDICTIONS = OUTPUTS / "matched_f0_predictions"
CHECKPOINTS = OUTPUTS / "checkpoints"
PROGRESS = OUTPUTS / "selection_progress"
SUPPORT_PATH = BASE / "matched_support_manifest.parquet"
DECISION_SHA256 = "72b5bf5b984c5eeb5b8d4b21b83f9b2fa9807f6fc944c79ee5edc89aeb33dd8e"
MACHINES = [f"machine{i:02d}" for i in range(1, 8)]
FEATURES = FEATURE_SET_IDS[1:]
LENGTHS = [32, 64, 128]
ALPHAS = [0.01, 0.1, 1.0, 10.0, 100.0]
LGB_CONFIGS = [
    {"num_leaves": nl, "learning_rate": lr, "n_estimators": ne}
    for nl in [15, 31]
    for lr in [0.03, 0.05]
    for ne in [200, 400]
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def index_hash(indices: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(indices, dtype="<i8").tobytes()).hexdigest()


def sample_id_hash(machine: str, indices: np.ndarray) -> str:
    payload = "\n".join(f"{machine}:{int(i)}" for i in indices).encode()
    return hashlib.sha256(payload).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.parquet")
    frame.to_parquet(temporary, index=False, compression="zstd")
    temporary.replace(path)


def verify_original_heavy() -> dict[str, Any]:
    inventory = pd.read_csv(ORIGINAL_AUDIT / "HEAVY_ARTIFACT_SHA256.csv")
    failures = []
    for row in inventory.itertuples(index=False):
        path = ROOT / row.path
        if not path.exists():
            failures.append({"path": row.path, "reason": "missing"})
        elif path.stat().st_size != int(row.size_bytes):
            failures.append({"path": row.path, "reason": "size"})
        elif sha256(path) != row.sha256:
            failures.append({"path": row.path, "reason": "sha256"})
    result = {
        "status": "PASS" if not failures else "FAIL",
        "checked": len(inventory),
        "failures": failures,
        "inventory_sha256": sha256(ORIGINAL_AUDIT / "HEAVY_ARTIFACT_SHA256.csv"),
    }
    atomic_json(OUTPUTS / "original_integrity_preflight.json", result)
    if failures:
        raise RuntimeError("Original Phase 2B-1 heavy artifact integrity failure")
    return result


def support_sets(panel: pd.DataFrame, machine: str, feature_set: str, fold: int, length: int) -> dict[str, np.ndarray]:
    outer = build_outer_folds(panel, joint_eligible_origins(panel, machine))[fold - 1]
    inner = build_inner_split(panel, outer.train_indices)
    return {
        "inner_train": finite_feature_origins(panel, machine, feature_set, length, inner.train_indices),
        "inner_validation": finite_feature_origins(panel, machine, feature_set, length, inner.validation_indices),
        "final_train": finite_feature_origins(panel, machine, feature_set, length, outer.train_indices),
        "test": finite_feature_origins(panel, machine, feature_set, length, outer.test_indices),
    }


def prepare_support() -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    decision = BASE / "PROSPECTIVE_MATCHED_F0_DECISION.md"
    if sha256(decision) != DECISION_SHA256:
        raise RuntimeError("Prospective decision record hash changed")
    verify_original_heavy()
    panel = load_canonical_panel()
    registry = pd.read_csv(ORIGINAL / "run_registry.csv").set_index(
        ["model", "feature_set", "machine", "outer_fold"]
    )
    selected = pd.read_csv(ORIGINAL / "selected_configs.csv").set_index(
        ["model", "feature_set", "machine", "outer_fold"]
    )
    rows = []
    failures = []
    for model in ["Ridge", "LightGBM"]:
        for feature_set in FEATURES:
            for machine in MACHINES:
                for fold in range(1, 6):
                    choice = selected.loc[(model, feature_set, machine, fold)]
                    run = registry.loc[(model, feature_set, machine, fold)]
                    length = int(choice.context_length)
                    sets = support_sets(panel, machine, feature_set, fold, length)
                    expected = {
                        "inner_train": (int(choice.inner_train_n), choice.inner_train_sample_set_hash),
                        "inner_validation": (int(choice.inner_validation_n), choice.inner_validation_sample_set_hash),
                        "final_train": (int(run.train_sample_count), None),
                        "test": (int(run.test_sample_count), run.test_sample_set_hash),
                    }
                    for name, values in sets.items():
                        if len(values) != expected[name][0]:
                            failures.append(f"{model}/{feature_set}/{machine}/{fold}/{name}/count")
                        if expected[name][1] and index_hash(values) != expected[name][1]:
                            failures.append(f"{model}/{feature_set}/{machine}/{fold}/{name}/hash")
                        for f0_length in LENGTHS:
                            f0 = finite_feature_origins(panel, machine, "F0_LOCAL", f0_length, values)
                            if not np.array_equal(f0, values):
                                failures.append(f"{model}/{feature_set}/{machine}/{fold}/{name}/F0L{f0_length}")
                    prediction = pd.read_parquet(ROOT / run.prediction_path)
                    prediction_origins = np.sort(prediction.origin_index.unique())
                    if not np.array_equal(prediction_origins, sets["test"]):
                        failures.append(f"{model}/{feature_set}/{machine}/{fold}/prediction_test_ids")
                    rows.append({
                        "model": model,
                        "candidate_feature_set": feature_set,
                        "machine": machine,
                        "fold": fold,
                        "candidate_context_length": length,
                        "inner_train_n": len(sets["inner_train"]),
                        "inner_validation_n": len(sets["inner_validation"]),
                        "final_train_n": len(sets["final_train"]),
                        "test_n": len(sets["test"]),
                        "inner_train_hash": index_hash(sets["inner_train"]),
                        "inner_validation_hash": index_hash(sets["inner_validation"]),
                        "final_train_hash": index_hash(sets["final_train"]),
                        "test_hash": index_hash(sets["test"]),
                        "inner_train_sample_id_hash": sample_id_hash(machine, sets["inner_train"]),
                        "inner_validation_sample_id_hash": sample_id_hash(machine, sets["inner_validation"]),
                        "final_train_sample_id_hash": sample_id_hash(machine, sets["final_train"]),
                        "test_sample_id_hash": sample_id_hash(machine, sets["test"]),
                        "candidate_run_id": run.run_id,
                        "candidate_prediction_path": run.prediction_path,
                    })
    if failures:
        atomic_json(OUTPUTS / "support_preflight_failure.json", {"status": "FAIL", "failures": failures})
        raise RuntimeError(f"Exact support preflight failed: {len(failures)} failures")
    frame = pd.DataFrame(rows).sort_values(["model", "candidate_feature_set", "machine", "fold"])
    atomic_parquet(frame, SUPPORT_PATH)
    atomic_parquet(frame, OUTPUTS / "matched_support_manifest.parquet")
    atomic_json(OUTPUTS / "support_preflight.json", {
        "status": "PASS", "comparisons": len(frame), "failures": [],
        "decision_sha256": DECISION_SHA256, "support_manifest_sha256": sha256(SUPPORT_PATH),
    })
    print(json.dumps({"status": "PASS", "comparisons": len(frame), "support_manifest_sha256": sha256(SUPPORT_PATH)}, indent=2))


def arrays(panel: pd.DataFrame, machine: str, length: int, indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = panel[[f"{machine}__cpu_utilization"]].to_numpy(dtype=np.float32)
    positions = indices[:, None] - np.arange(length - 1, -1, -1, dtype=np.int64)
    X = values[positions]
    target = values[:, 0]
    y = target[indices[:, None] + np.asarray(FUTURE_LEADS)]
    if not np.isfinite(X).all() or not np.isfinite(y).all():
        raise RuntimeError("Non-finite matched F0 array")
    return X, y


def progress_path(model: str, row: Any) -> Path:
    return PROGRESS / model / f"{row.machine}_{row.candidate_feature_set}_fold{int(row.fold)}.json"


def checkpoint_path(model: str, row: Any) -> Path:
    return CHECKPOINTS / model / f"{row.machine}_{row.candidate_feature_set}_fold{int(row.fold)}.json"


def load_valid_checkpoint(model: str, row: Any) -> dict[str, Any] | None:
    path = checkpoint_path(model, row)
    if not path.exists():
        return None
    value = json.loads(path.read_text())
    prediction = ROOT / value["registry"]["prediction_path"]
    if (
        value.get("candidate_run_id") == row.candidate_run_id
        and value.get("support_hashes", {}).get("test") == row.test_hash
        and prediction.exists()
        and sha256(prediction) == value.get("prediction_sha256")
    ):
        return value
    return None


def prediction_frame(panel: pd.DataFrame, run_id: str, row: Any, indices: np.ndarray, y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame:
    timestamps = panel.timestamp.to_numpy()
    segments = panel.segment_id.to_numpy()
    leads = np.asarray(FUTURE_LEADS, dtype=np.int16)
    repeated = np.repeat(indices, len(leads))
    return pd.DataFrame({
        "run_id": run_id,
        "model": row.model,
        "candidate_feature_set": row.candidate_feature_set,
        "machine": row.machine,
        "outer_fold": int(row.fold),
        "lead": np.tile(leads, len(indices)),
        "sample_id": [f"{row.machine}:{int(i)}" for i in repeated],
        "origin_index": repeated,
        "origin_timestamp": np.repeat(timestamps[indices], len(leads)),
        "target_index": (indices[:, None] + leads.astype(np.int64)).reshape(-1),
        "target_timestamp": timestamps[(indices[:, None] + leads.astype(np.int64)).reshape(-1)],
        "segment_id": np.repeat(segments[indices], len(leads)),
        "y_true": y_true.reshape(-1),
        "y_pred": y_pred.reshape(-1),
    })


def process_variant(panel: pd.DataFrame, row: Any) -> dict[str, Any]:
    model_name = row.model
    existing = load_valid_checkpoint(model_name, row)
    if existing is not None:
        return existing
    started = time.perf_counter()
    sets = support_sets(panel, row.machine, row.candidate_feature_set, int(row.fold), int(row.candidate_context_length))
    expected_hashes = {
        "inner_train": row.inner_train_hash, "inner_validation": row.inner_validation_hash,
        "final_train": row.final_train_hash, "test": row.test_hash,
    }
    if any(index_hash(sets[name]) != value for name, value in expected_hashes.items()):
        raise RuntimeError("Support changed after preflight")
    pp = progress_path(model_name, row)
    progress = json.loads(pp.read_text()) if pp.exists() else {
        "candidate_run_id": row.candidate_run_id, "support_hashes": expected_hashes,
        "scores": [], "inner_runtime_seconds": 0.0,
    }
    if progress.get("candidate_run_id") != row.candidate_run_id or progress.get("support_hashes") != expected_hashes:
        raise RuntimeError("Selection progress provenance mismatch")
    completed = {(int(v["context_length"]), v["config_key"]) for v in progress["scores"]}
    for length in LENGTHS:
        X_train, y_train = arrays(panel, row.machine, length, sets["inner_train"])
        X_validation, y_validation = arrays(panel, row.machine, length, sets["inner_validation"])
        configs = ([{"alpha": alpha} for alpha in ALPHAS] if model_name == "Ridge" else LGB_CONFIGS)
        for config in configs:
            key = json.dumps(config, sort_keys=True, separators=(",", ":"))
            if (length, key) in completed:
                continue
            fit_started = time.perf_counter()
            if model_name == "Ridge":
                model = RidgeForecaster(alpha=float(config["alpha"]))
            else:
                model = LightGBMForecaster(**config)
            model.fit(X_train, y_train)
            prediction = model.predict(X_validation)
            progress["scores"].append({
                "context_length": length, **config, "config_key": key,
                "inner_validation_mae": float(np.mean(np.abs(y_validation - prediction))),
            })
            progress["inner_runtime_seconds"] += time.perf_counter() - fit_started
            atomic_json(pp, progress)
    scores = pd.DataFrame(progress["scores"])
    selected = select_from_inner_validation(scores, model_name)
    length = int(selected.context_length)
    config = ({"alpha": float(selected.alpha)} if model_name == "Ridge" else {
        "num_leaves": int(selected.num_leaves), "learning_rate": float(selected.learning_rate),
        "n_estimators": int(selected.n_estimators),
    })
    X_train, y_train = arrays(panel, row.machine, length, sets["final_train"])
    X_test, y_test = arrays(panel, row.machine, length, sets["test"])
    final_started = time.perf_counter()
    final_model = RidgeForecaster(alpha=config["alpha"]) if model_name == "Ridge" else LightGBMForecaster(**config)
    final_model.fit(X_train, y_train)
    prediction = final_model.predict(X_test)
    final_seconds = time.perf_counter() - final_started
    run_id = deterministic_run_id(f"MatchedF0{model_name}", row.candidate_feature_set, row.machine, int(row.fold), length, {**config, "candidate_run_id": row.candidate_run_id}, None)
    frame = prediction_frame(panel, run_id, row, sets["test"], y_test, prediction)
    destination = PREDICTIONS / f"{run_id}.parquet"
    atomic_parquet(frame, destination)
    metrics = per_lead_metrics(y_test, prediction)
    metric_rows = [
        {"run_id": run_id, "model": model_name, "candidate_feature_set": row.candidate_feature_set,
         "machine": row.machine, "outer_fold": int(row.fold), "lead": int(m.lead),
         "mae": float(m.mae), "rmse": float(m.rmse), "r2": float(m.r2),
         "n_samples": len(sets["test"]), "test_hash": row.test_hash}
        for m in metrics.itertuples(index=False)
    ]
    registry = {
        "run_id": run_id, "model": model_name, "candidate_feature_set": row.candidate_feature_set,
        "machine": row.machine, "outer_fold": int(row.fold), "context_length": length,
        "config_json": json.dumps(config, sort_keys=True, separators=(",", ":")),
        "candidate_run_id": row.candidate_run_id, "status": "completed",
        "inner_train_n": len(sets["inner_train"]), "inner_validation_n": len(sets["inner_validation"]),
        "final_train_n": len(sets["final_train"]), "test_n": len(sets["test"]),
        "inner_train_hash": row.inner_train_hash, "inner_validation_hash": row.inner_validation_hash,
        "final_train_hash": row.final_train_hash, "test_hash": row.test_hash,
        "prediction_path": str(destination.relative_to(ROOT)),
    }
    selected_record = {
        "model": model_name, "candidate_feature_set": row.candidate_feature_set, "machine": row.machine,
        "outer_fold": int(row.fold), "context_length": length,
        "config_json": registry["config_json"], "selection_metric": "mean_eight_lead_inner_validation_mae",
        "inner_validation_mae": float(selected.inner_validation_mae),
        "candidate_configuration_count": 15 if model_name == "Ridge" else 24,
        "tie_break_rule": "inner MAE, shorter L, smaller alpha" if model_name == "Ridge" else "inner MAE, shorter L, smaller num_leaves, lower learning_rate, fewer n_estimators",
        "outer_test_columns_available_to_selector": False,
        "inner_train_hash": row.inner_train_hash, "inner_validation_hash": row.inner_validation_hash,
    }
    value = {
        "candidate_run_id": row.candidate_run_id, "support_hashes": expected_hashes,
        "registry": registry, "selected_config": selected_record, "metrics": metric_rows,
        "inner_candidate_fits": 15 if model_name == "Ridge" else 24,
        "inner_lead_models": 0 if model_name == "Ridge" else 192,
        "final_models": 1 if model_name == "Ridge" else 8,
        "inner_runtime_seconds": progress["inner_runtime_seconds"], "final_runtime_seconds": final_seconds,
        "total_runtime_seconds": time.perf_counter() - started,
        "prediction_sha256": sha256(destination),
    }
    atomic_json(checkpoint_path(model_name, row), value)
    return value


def process_machine(model_name: str, machine: str) -> dict[str, Any]:
    panel = load_canonical_panel()
    support = pd.read_parquet(SUPPORT_PATH)
    rows = support[(support.model == model_name) & (support.machine == machine)]
    completed, failures = 0, []
    for row in rows.itertuples(index=False):
        try:
            process_variant(panel, row)
            completed += 1
            print(f"{model_name} {machine} {row.candidate_feature_set} fold {row.fold} completed", flush=True)
        except Exception as exc:
            failures.append({"feature_set": row.candidate_feature_set, "fold": int(row.fold), "error": repr(exc)})
            break
    return {"model": model_name, "machine": machine, "completed": completed, "failures": failures}


def consolidate() -> None:
    values = []
    for model_name in ["Ridge", "LightGBM"]:
        for path in sorted((CHECKPOINTS / model_name).glob("*.json")):
            value = json.loads(path.read_text())
            prediction = ROOT / value["registry"]["prediction_path"]
            if prediction.exists() and sha256(prediction) == value["prediction_sha256"]:
                values.append(value)
    registry = pd.DataFrame([v["registry"] for v in values])
    selected = pd.DataFrame([v["selected_config"] for v in values])
    metrics = pd.DataFrame([m for v in values for m in v["metrics"]])
    order = ["model", "candidate_feature_set", "machine", "outer_fold"]
    if len(registry): registry = registry.sort_values(order)
    if len(selected): selected = selected.sort_values(order)
    if len(metrics): metrics = metrics.sort_values(order + ["lead"])
    registry.to_csv(OUTPUTS / "matched_f0_run_registry.csv", index=False)
    selected.to_csv(OUTPUTS / "matched_f0_selected_configs.csv", index=False)
    atomic_parquet(metrics, OUTPUTS / "matched_f0_metrics.parquet")
    expected = {(m, f, machine, fold) for m in ["Ridge", "LightGBM"] for f in FEATURES for machine in MACHINES for fold in range(1, 6)}
    actual = set(zip(registry.model, registry.candidate_feature_set, registry.machine, registry.outer_fold)) if len(registry) else set()
    runtime = {
        "completed_comparators": len(actual), "failed_or_missing_comparators": len(expected - actual),
        "completed_comparator_ids": sorted("/".join(map(str, x)) for x in actual),
        "failed_or_missing_comparator_ids": sorted("/".join(map(str, x)) for x in expected - actual),
        "inner_candidate_fits": sum(v["inner_candidate_fits"] for v in values),
        "inner_lead_models": sum(v["inner_lead_models"] for v in values),
        "final_models": sum(v["final_models"] for v in values),
        "inner_runtime_seconds_sum": sum(v["inner_runtime_seconds"] for v in values),
        "final_runtime_seconds_sum": sum(v["final_runtime_seconds"] for v in values),
        "comparator_runtime_seconds_sum": sum(v["total_runtime_seconds"] for v in values),
        "per_comparator": [{"run_id": v["registry"]["run_id"], "seconds": v["total_runtime_seconds"]} for v in values],
    }
    atomic_json(OUTPUTS / "runtime_accounting.json", runtime)


def execute(model_name: str, workers: int) -> None:
    if not SUPPORT_PATH.exists():
        raise RuntimeError("Support manifest must pass before training")
    preflight = json.loads((OUTPUTS / "support_preflight.json").read_text())
    if preflight["status"] != "PASS" or preflight["comparisons"] != 350:
        raise RuntimeError("Support preflight is not complete")
    started = time.perf_counter()
    context = get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as executor:
        futures = {executor.submit(process_machine, model_name, machine): machine for machine in MACHINES}
        failures = []
        for future in as_completed(futures):
            result = future.result()
            failures.extend(result["failures"])
            print(json.dumps(result), flush=True)
    consolidate()
    runtime_path = OUTPUTS / "runtime_accounting.json"
    runtime = json.loads(runtime_path.read_text())
    runtime.setdefault("family_wall_runtime_seconds", {})[model_name] = time.perf_counter() - started
    atomic_json(runtime_path, runtime)
    if failures:
        raise RuntimeError(f"{model_name} comparator failures: {failures}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-support", action="store_true")
    parser.add_argument("--family", choices=["Ridge", "LightGBM"])
    parser.add_argument("--workers", type=int, default=min(7, os.cpu_count() or 1))
    args = parser.parse_args()
    if args.prepare_support:
        prepare_support()
    elif args.family:
        execute(args.family, args.workers)
    else:
        parser.error("choose --prepare-support or --family")


if __name__ == "__main__":
    main()
