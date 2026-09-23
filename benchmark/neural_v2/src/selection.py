"""Seed-mean inner-validation context selection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class InnerResult:
    context_length: int
    seed: int
    mae_by_lead: tuple[float, ...]
    best_epoch: int


@dataclass(frozen=True)
class ContextSelection:
    context_length: int
    seed_mean_validation_mae: float
    best_epoch_by_seed: dict[int, int]


def select_context(results: list[InnerResult]) -> ContextSelection:
    if not results:
        raise ValueError("No inner results supplied")
    by_context: dict[int, list[InnerResult]] = {}
    for result in results:
        if len(result.mae_by_lead) != 8:
            raise ValueError("Every inner result must contain eight lead MAEs")
        by_context.setdefault(result.context_length, []).append(result)
    expected_contexts = {32, 64, 128}
    if set(by_context) != expected_contexts:
        raise ValueError("Context selection requires L={32,64,128}")
    expected_seeds = {0, 1, 2}
    scores: dict[int, float] = {}
    for context_length, context_results in by_context.items():
        if {result.seed for result in context_results} != expected_seeds:
            raise ValueError("Each context requires seeds {0,1,2}")
        scores[context_length] = float(
            np.mean([result.mae_by_lead for result in context_results])
        )
    selected_length = min(scores, key=lambda length: (scores[length], length))
    selected_rows = by_context[selected_length]
    return ContextSelection(
        context_length=selected_length,
        seed_mean_validation_mae=scores[selected_length],
        best_epoch_by_seed={row.seed: row.best_epoch for row in selected_rows},
    )
