"""Future seed-mean normalized-MAE context selection with smaller-L ties."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import CONTEXTS, SEEDS


@dataclass(frozen=True)
class SelectionRow:
    formulation: str
    context_length: int
    seed: int
    normalized_mae: np.ndarray
    best_epoch: int


@dataclass(frozen=True)
class SelectionResult:
    context_length: int
    score: float
    best_epoch_by_seed: dict[int, int]


def select_context(rows: list[SelectionRow], formulation: str) -> SelectionResult:
    if formulation not in {"S1", "S2", "M1"}:
        raise ValueError(formulation)
    expected_shape = (4, 5) if formulation == "M1" else (5,)
    scores = {}
    for context in CONTEXTS:
        selected = [row for row in rows if row.formulation == formulation and row.context_length == context]
        if {row.seed for row in selected} != set(SEEDS):
            raise ValueError("Selection requires all three seeds")
        if any(np.asarray(row.normalized_mae).shape != expected_shape for row in selected):
            raise ValueError("Unexpected normalized-MAE shape")
        scores[context] = float(np.mean([row.normalized_mae for row in selected]))
    chosen = min(scores, key=lambda context: (scores[context], context))
    chosen_rows = [row for row in rows if row.formulation == formulation and row.context_length == chosen]
    return SelectionResult(chosen, scores[chosen], {row.seed: row.best_epoch for row in chosen_rows})

