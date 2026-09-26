"""Frozen five-fold boundaries with common support and target-time purges."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from benchmark.src.splits import build_inner_split, build_outer_folds
from benchmark.src.windows import joint_eligible_origins

from .data import CONTEXT_LENGTHS, sample_set_hash
from .support import four_resource_finite_origins


@dataclass(frozen=True)
class FactorialFold:
    machine: str
    fold: int
    context_length: int
    inner_train: np.ndarray
    inner_validation: np.ndarray
    outer_train: np.ndarray
    outer_test: np.ndarray
    hashes: dict[str, str]


def build_factorial_folds(panel: pd.DataFrame, machine: str, context_length: int) -> list[FactorialFold]:
    if context_length not in CONTEXT_LENGTHS:
        raise ValueError(context_length)
    structural = joint_eligible_origins(panel, machine, max_context=128)
    rows = []
    for outer in build_outer_folds(panel, structural):
        outer_train = four_resource_finite_origins(panel, machine, outer.train_indices)
        outer_test = four_resource_finite_origins(panel, machine, outer.test_indices)
        inner = build_inner_split(panel, outer_train, validation_fraction=0.15)
        sets = {"inner_train": inner.train_indices, "inner_validation": inner.validation_indices, "outer_train": outer_train, "outer_test": outer_test}
        rows.append(FactorialFold(machine, outer.fold, context_length, inner.train_indices, inner.validation_indices, outer_train, outer_test, {key: sample_set_hash(value) for key, value in sets.items()}))
    return rows


def assert_context_invariant_support(folds_by_context: dict[int, list[FactorialFold]]) -> None:
    if set(folds_by_context) != {32, 64, 128}:
        raise ValueError("All three context lengths are required")
    reference = folds_by_context[128]
    for length, folds in folds_by_context.items():
        for expected, observed in zip(reference, folds, strict=True):
            if expected.fold != observed.fold or expected.hashes != observed.hashes:
                raise RuntimeError(f"Support differs at L={length}, fold={observed.fold}")
