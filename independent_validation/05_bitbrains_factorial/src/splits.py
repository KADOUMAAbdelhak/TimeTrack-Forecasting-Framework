"""Frozen five-fold origin-count boundaries and target-time purges."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import CONTEXTS, LEADS
from .support import origin_ids, sample_set_hash


@dataclass(frozen=True)
class ExternalFold:
    environment: str
    vm_id: str
    fold: int
    inner_train: np.ndarray
    inner_validation: np.ndarray
    outer_train: np.ndarray
    outer_test: np.ndarray
    hashes: dict[str, str]
    boundary_timestamps: dict[str, str]


def _purge_before(frame: pd.DataFrame, origins: np.ndarray, boundary_origin: int) -> np.ndarray:
    timestamps = frame.timestamp_seconds.to_numpy(dtype=np.int64)
    boundary = timestamps[int(boundary_origin)]
    targets = timestamps[np.asarray(origins, dtype=np.int64) + max(LEADS)]
    return np.asarray(origins, dtype=np.int64)[targets < boundary]


def _iso(frame: pd.DataFrame, row: int) -> str:
    return pd.to_datetime(int(frame.timestamp_seconds.iloc[row]), unit="s", utc=True).isoformat()


def build_folds(frame: pd.DataFrame, environment: str, vm_id: str, origins: np.ndarray) -> list[ExternalFold]:
    origins = np.asarray(origins, dtype=np.int64)
    if len(origins) == 0 or np.any(np.diff(origins) <= 0):
        raise ValueError("Legal origins must be nonempty, sorted, and unique")
    n = len(origins)
    boundaries = [math.floor(n * fraction) for fraction in (0.5, 0.6, 0.7, 0.8, 0.9)] + [n]
    folds = []
    for fold in range(1, 6):
        test_start, test_end = boundaries[fold - 1], boundaries[fold]
        outer_test = origins[test_start:test_end]
        if not len(outer_test):
            raise RuntimeError(f"Empty outer test: {environment}/{vm_id}/fold{fold}")
        outer_train = _purge_before(frame, origins[:test_start], int(outer_test[0]))
        validation_count = max(1, math.ceil(0.15 * len(outer_train)))
        validation_start = len(outer_train) - validation_count
        inner_validation = outer_train[validation_start:]
        inner_train = _purge_before(frame, outer_train[:validation_start], int(inner_validation[0]))
        sets = {
            "inner_train": inner_train,
            "inner_validation": inner_validation,
            "outer_train": outer_train,
            "outer_test": outer_test,
        }
        hashes = {name: sample_set_hash(origin_ids(frame, values)) for name, values in sets.items()}
        boundary_timestamps = {
            "outer_train_first": _iso(frame, int(outer_train[0])),
            "outer_train_last": _iso(frame, int(outer_train[-1])),
            "outer_test_first": _iso(frame, int(outer_test[0])),
            "outer_test_last": _iso(frame, int(outer_test[-1])),
            "inner_train_first": _iso(frame, int(inner_train[0])),
            "inner_train_last": _iso(frame, int(inner_train[-1])),
            "inner_validation_first": _iso(frame, int(inner_validation[0])),
            "inner_validation_last": _iso(frame, int(inner_validation[-1])),
        }
        folds.append(ExternalFold(environment, vm_id, fold, inner_train, inner_validation, outer_train, outer_test, hashes, boundary_timestamps))
    return folds


def manifest_rows(frame: pd.DataFrame, folds: list[ExternalFold]) -> list[dict[str, object]]:
    rows = []
    segments = frame.segment_id.to_numpy(dtype=np.int64)
    for item in folds:
        exact_ids = {
            name: origin_ids(frame, getattr(item, name)).tolist()
            for name in ("inner_train", "inner_validation", "outer_train", "outer_test")
        }
        for context in CONTEXTS:
            row: dict[str, object] = {
                "environment": item.environment,
                "vm_id": item.vm_id,
                "fold": item.fold,
                "L": context,
            }
            for name in ("inner_train", "inner_validation", "outer_train", "outer_test"):
                values = getattr(item, name)
                row[f"{name}_count"] = len(values)
                row[f"{name}_hash"] = item.hashes[name]
                row[f"{name}_origin_ids"] = exact_ids[name]
                row[f"{name}_segment_ids"] = sorted(set(int(value) for value in segments[values]))
            row.update(item.boundary_timestamps)
            rows.append(row)
    return rows


def assert_support_minima(folds: list[ExternalFold], minima: dict[str, int]) -> list[dict[str, object]]:
    failures = []
    for fold in folds:
        for name, threshold in minima.items():
            observed = len(getattr(fold, name))
            if observed < threshold:
                failures.append({
                    "environment": fold.environment,
                    "vm_id": fold.vm_id,
                    "fold": fold.fold,
                    "split": name,
                    "observed": observed,
                    "required": threshold,
                })
    return failures

