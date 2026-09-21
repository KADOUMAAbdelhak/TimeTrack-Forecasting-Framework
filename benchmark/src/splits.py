"""Independent target-time-purged outer and inner chronological splits."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .windows import FUTURE_LEADS
from .windows import joint_eligible_origins


ROOT = Path(__file__).resolve().parents[2]
PHASE1C_BOUNDARIES = (
    ROOT
    / "discovery"
    / "03_rolling_robustness"
    / "outputs"
    / "rolling_fold_boundaries.csv"
)
PHASE1C_HISTORY_LAGS = [0, 1, 2, 4, 8, 16, 32]


@dataclass(frozen=True)
class OuterFold:
    fold: int
    train_indices: np.ndarray
    test_indices: np.ndarray
    purged_indices: np.ndarray
    first_test_origin_timestamp: np.datetime64


@dataclass(frozen=True)
class InnerSplit:
    train_indices: np.ndarray
    validation_indices: np.ndarray
    purged_indices: np.ndarray
    first_validation_origin_timestamp: np.datetime64


def build_outer_folds(
    panel: pd.DataFrame, eligible_indices: np.ndarray
) -> list[OuterFold]:
    indices = np.asarray(eligible_indices, dtype=np.int64)
    if len(indices) == 0 or np.any(np.diff(indices) <= 0):
        raise ValueError("Eligible origins must be nonempty and sorted")
    n = len(indices)
    starts = [math.floor(n * value) for value in (0.5, 0.6, 0.7, 0.8, 0.9)]
    ends = [math.floor(n * value) for value in (0.6, 0.7, 0.8, 0.9, 1.0)]
    timestamps = panel["timestamp"].to_numpy()
    folds: list[OuterFold] = []
    previous_test: set[int] = set()
    previous_train_n = 0
    for fold, start, end in zip(range(1, 6), starts, ends):
        test = indices[start:end]
        provisional_train = indices[:start]
        first_test_time = timestamps[test[0]]
        latest_train_targets = timestamps[provisional_train + max(FUTURE_LEADS)]
        keep = latest_train_targets < first_test_time
        train = provisional_train[keep]
        purged = provisional_train[~keep]
        if previous_test.intersection(test.tolist()):
            raise RuntimeError("Outer test blocks overlap")
        if len(train) <= previous_train_n:
            raise RuntimeError("Outer training set did not expand")
        if not np.all(timestamps[train + max(FUTURE_LEADS)] < first_test_time):
            raise RuntimeError("Outer target-time purge failed")
        folds.append(
            OuterFold(
                fold=fold,
                train_indices=train,
                test_indices=test,
                purged_indices=purged,
                first_test_origin_timestamp=first_test_time,
            )
        )
        previous_test.update(test.tolist())
        previous_train_n = len(train)
    return folds


def build_inner_split(
    panel: pd.DataFrame,
    outer_train_indices: np.ndarray,
    validation_fraction: float = 0.15,
) -> InnerSplit:
    indices = np.asarray(outer_train_indices, dtype=np.int64)
    split_position = math.floor(len(indices) * (1.0 - validation_fraction))
    if split_position <= 0 or split_position >= len(indices):
        raise ValueError("Outer train set is too small for inner validation")
    provisional_train = indices[:split_position]
    validation = indices[split_position:]
    timestamps = panel["timestamp"].to_numpy()
    first_validation = timestamps[validation[0]]
    keep = timestamps[provisional_train + max(FUTURE_LEADS)] < first_validation
    train = provisional_train[keep]
    purged = provisional_train[~keep]
    if not np.all(timestamps[train + max(FUTURE_LEADS)] < first_validation):
        raise RuntimeError("Inner target-time purge failed")
    return InnerSplit(
        train_indices=train,
        validation_indices=validation,
        purged_indices=purged,
        first_validation_origin_timestamp=first_validation,
    )


def phase1c_per_lead_origins(
    panel: pd.DataFrame, target: str, lead: int
) -> np.ndarray:
    y = panel[target]
    segment = panel["segment_id"]
    eligible = pd.Series(True, index=panel.index)
    for lag in PHASE1C_HISTORY_LAGS:
        eligible &= y.shift(lag).notna()
    eligible &= y.shift(-lead).notna()
    eligible &= segment.eq(segment.shift(max(PHASE1C_HISTORY_LAGS)))
    eligible &= segment.eq(segment.shift(-lead))
    return np.flatnonzero(eligible.to_numpy())


def validate_against_phase1c(
    panel: pd.DataFrame, boundary_path: Path = PHASE1C_BOUNDARIES
) -> dict[str, int | bool]:
    frozen = pd.read_csv(
        boundary_path,
        parse_dates=[
            "max_train_target_timestamp",
            "test_origin_start",
            "test_origin_end",
        ],
    )
    timestamps = panel["timestamp"].to_numpy()
    failures = 0
    checked = 0
    for (target, lead), rows in frozen.groupby(["target", "lead"]):
        indices = phase1c_per_lead_origins(panel, target, int(lead))
        n = len(indices)
        starts = [math.floor(n * value) for value in (0.5, 0.6, 0.7, 0.8, 0.9)]
        ends = [math.floor(n * value) for value in (0.6, 0.7, 0.8, 0.9, 1.0)]
        for row, start, end in zip(
            rows.sort_values("fold").itertuples(index=False), starts, ends
        ):
            test = indices[start:end]
            provisional_train = indices[:start]
            first_test = timestamps[test[0]]
            keep = timestamps[provisional_train + int(lead)] < first_test
            train = provisional_train[keep]
            checks = [
                len(indices) == row.eligible_n,
                len(provisional_train) == row.train_n_before_purge,
                len(train) == row.train_n_after_purge,
                int((~keep).sum()) == row.purged_n,
                len(test) == row.test_n,
                pd.Timestamp(timestamps[test[0]]) == row.test_origin_start,
                pd.Timestamp(timestamps[test[-1]]) == row.test_origin_end,
                pd.Timestamp(timestamps[train + int(lead)].max())
                == row.max_train_target_timestamp,
            ]
            failures += int(not all(checks))
            checked += 1
    return {"checked": checked, "failures": failures, "pass": failures == 0}


def joint_fold_boundary_table(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    timestamps = panel["timestamp"].to_numpy()
    for machine_number in range(1, 8):
        machine = f"machine{machine_number:02d}"
        eligible = joint_eligible_origins(panel, machine)
        for fold in build_outer_folds(panel, eligible):
            rows.append(
                {
                    "target_machine": machine,
                    "fold": fold.fold,
                    "joint_eligible_n": len(eligible),
                    "train_n_after_purge": len(fold.train_indices),
                    "purged_n": len(fold.purged_indices),
                    "test_n": len(fold.test_indices),
                    "train_origin_start": timestamps[fold.train_indices[0]],
                    "train_origin_end": timestamps[fold.train_indices[-1]],
                    "max_train_target_timestamp": timestamps[
                        fold.train_indices + max(FUTURE_LEADS)
                    ].max(),
                    "test_origin_start": timestamps[fold.test_indices[0]],
                    "test_origin_end": timestamps[fold.test_indices[-1]],
                    "leakage_check": bool(
                        timestamps[fold.train_indices + max(FUTURE_LEADS)].max()
                        < timestamps[fold.test_indices[0]]
                    ),
                }
            )
    return pd.DataFrame(rows)


def joint_eligibility_comparison(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for machine_number in range(1, 8):
        machine = f"machine{machine_number:02d}"
        target = f"{machine}__cpu_utilization"
        joint_n = len(joint_eligible_origins(panel, machine))
        for lead in FUTURE_LEADS:
            phase1c_n = len(phase1c_per_lead_origins(panel, target, lead))
            rows.append(
                {
                    "target_machine": machine,
                    "lead": lead,
                    "phase1c_per_lead_eligible_n": phase1c_n,
                    "phase2_joint_eligible_n": joint_n,
                    "joint_reduction_n": phase1c_n - joint_n,
                    "joint_reduction_pct": 100.0 * (phase1c_n - joint_n) / phase1c_n,
                }
            )
    return pd.DataFrame(rows)
