"""Frozen chronological folds with neural-v2 F1 common support."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from benchmark.src.splits import build_inner_split, build_outer_folds
from benchmark.src.windows import joint_eligible_origins

from .data import f1_finite_origins, sample_set_hash


@dataclass(frozen=True)
class SupportedFold:
    fold: int
    context_length: int
    inner_train_indices: np.ndarray
    inner_validation_indices: np.ndarray
    outer_train_indices: np.ndarray
    outer_test_indices: np.ndarray
    inner_train_hash: str
    inner_validation_hash: str
    outer_train_hash: str
    outer_test_hash: str


def build_supported_folds(
    panel: pd.DataFrame, machine: str, context_length: int
) -> list[SupportedFold]:
    """Apply F1 finiteness inside the exact accepted deterministic boundaries."""
    structural_origins = joint_eligible_origins(panel, machine, max_context=128)
    rows: list[SupportedFold] = []
    for outer in build_outer_folds(panel, structural_origins):
        outer_train = f1_finite_origins(
            panel, machine, context_length, outer.train_indices
        )
        outer_test = f1_finite_origins(
            panel, machine, context_length, outer.test_indices
        )
        inner = build_inner_split(panel, outer_train, validation_fraction=0.15)
        rows.append(
            SupportedFold(
                fold=outer.fold,
                context_length=context_length,
                inner_train_indices=inner.train_indices,
                inner_validation_indices=inner.validation_indices,
                outer_train_indices=outer_train,
                outer_test_indices=outer_test,
                inner_train_hash=sample_set_hash(inner.train_indices),
                inner_validation_hash=sample_set_hash(inner.validation_indices),
                outer_train_hash=sample_set_hash(outer_train),
                outer_test_hash=sample_set_hash(outer_test),
            )
        )
    return rows
