"""Inner-validation-only configuration enumeration and selection."""

from __future__ import annotations

import itertools
from typing import Any

import pandas as pd


RIDGE_ALPHAS = [0.01, 0.1, 1.0, 10.0, 100.0]
LIGHTGBM_GRID = {
    "num_leaves": [15, 31],
    "learning_rate": [0.03, 0.05],
    "n_estimators": [200, 400],
}
CONTEXT_LENGTHS = [32, 64, 128]


def ridge_configurations() -> list[dict[str, Any]]:
    return [
        {"context_length": length, "alpha": alpha}
        for length in CONTEXT_LENGTHS
        for alpha in RIDGE_ALPHAS
    ]


def lightgbm_configurations() -> list[dict[str, Any]]:
    return [
        {
            "context_length": length,
            "num_leaves": leaves,
            "learning_rate": learning_rate,
            "n_estimators": estimators,
        }
        for length in CONTEXT_LENGTHS
        for leaves, learning_rate, estimators in itertools.product(
            LIGHTGBM_GRID["num_leaves"],
            LIGHTGBM_GRID["learning_rate"],
            LIGHTGBM_GRID["n_estimators"],
        )
    ]


def neural_context_configurations() -> list[dict[str, int]]:
    return [{"context_length": length} for length in CONTEXT_LENGTHS]


def select_from_inner_validation(
    scores: pd.DataFrame, model: str
) -> pd.Series:
    """Select without accepting or referencing any outer-test metric."""
    forbidden = [column for column in scores if "test" in column.lower()]
    if forbidden:
        raise ValueError(f"Outer-test columns forbidden during selection: {forbidden}")
    required = {"inner_validation_mae", "context_length"}
    if not required.issubset(scores.columns):
        raise ValueError("Missing inner-validation selection columns")
    tie_columns = ["inner_validation_mae", "context_length"]
    if model == "Ridge":
        tie_columns += ["alpha"]
    elif model == "LightGBM":
        tie_columns += ["num_leaves", "learning_rate", "n_estimators"]
    selected = scores.sort_values(tie_columns, kind="stable").iloc[0]
    return selected
