"""Native per-lead metrics and environment-isolated macro aggregation."""

from __future__ import annotations

import numpy as np
import pandas as pd


def per_lead_metrics(y_true: np.ndarray, y_pred: np.ndarray, training_native_iqr: float, persistence: np.ndarray | None = None) -> dict[str, np.ndarray]:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    if y_true.shape != y_pred.shape or y_true.ndim != 2 or y_true.shape[1] != 5:
        raise ValueError("Expected matching [N,5] arrays")
    if training_native_iqr <= 0:
        raise ValueError("NMAE denominator must be positive")
    residual = y_true - y_pred
    mae = np.mean(np.abs(residual), axis=0)
    rmse = np.sqrt(np.mean(residual ** 2, axis=0))
    total = np.sum((y_true - y_true.mean(axis=0, keepdims=True)) ** 2, axis=0)
    r2 = np.full(5, np.nan, dtype=float)
    valid = total > 0
    r2[valid] = 1.0 - np.sum(residual[:, valid] ** 2, axis=0) / total[valid]
    result = {"mae": mae, "rmse": rmse, "r2": r2, "nmae": mae / training_native_iqr}
    if persistence is not None:
        persistence_mae = np.mean(np.abs(y_true - np.asarray(persistence, float)), axis=0)
        result["persistence_skill"] = np.divide(
            persistence_mae - mae,
            persistence_mae,
            out=np.full(5, np.nan),
            where=persistence_mae > 0,
        )
    return result


def environment_macro(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"environment", "formulation", "vm_id", "fold", "seed", "resource", "lead", "mae"}
    if not required.issubset(frame.columns):
        raise ValueError("Metric frame lacks required macro keys")
    if frame.environment.nunique() != 1:
        raise ValueError("fastStorage and Rnd cannot be pooled")
    seed_mean = frame.groupby(
        ["environment", "formulation", "vm_id", "fold", "resource", "lead"], as_index=False
    ).mae.mean()
    return seed_mean.groupby(
        ["environment", "formulation", "resource", "lead"], as_index=False
    ).mae.mean().rename(columns={"mae": "macro_mae"})


def equal_environment_synthesis(frame: pd.DataFrame) -> pd.DataFrame:
    expected = {"GWA-T-12_Bitbrains_fastStorage", "GWA-T-12_Bitbrains_Rnd"}
    if set(frame.environment) != expected:
        raise ValueError("Both and only the two frozen environments are required")
    return frame.groupby(["formulation", "resource", "lead"], as_index=False).macro_mae.mean()


def comparison_gain(baseline: float, candidate: float) -> float:
    return 100.0 * (baseline - candidate) / baseline

