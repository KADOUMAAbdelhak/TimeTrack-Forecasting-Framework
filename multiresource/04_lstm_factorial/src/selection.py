"""Prospective normalized-MAE context selection with smaller-L ties."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SelectionRow:
    formulation: str
    context_length: int
    seed: int
    nmae: np.ndarray
    best_epoch: int


@dataclass(frozen=True)
class SelectionResult:
    context_length: int
    score: float
    best_epoch_by_seed: dict[int, int]


def select_context(rows: list[SelectionRow], formulation: str) -> SelectionResult:
    expected_shape = (4, 8) if formulation == "M1" else (8,)
    if formulation not in {"S1", "S2", "M1"}:
        raise ValueError(formulation)
    scores: dict[int, float] = {}
    for length in (32, 64, 128):
        selected = [row for row in rows if row.context_length == length and row.formulation == formulation]
        if {row.seed for row in selected} != {0, 1, 2} or any(np.asarray(row.nmae).shape != expected_shape for row in selected):
            raise ValueError("Selection requires all three seeds and exact normalized-MAE shape")
        scores[length] = float(np.mean([row.nmae for row in selected]))
    chosen = min(scores, key=lambda length: (scores[length], length))
    chosen_rows = [row for row in rows if row.context_length == chosen and row.formulation == formulation]
    return SelectionResult(chosen, scores[chosen], {row.seed: row.best_epoch for row in chosen_rows})
