"""Native metrics, physical inversion, and equal-cell macro aggregation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .data import RESOURCE_ORDER
from .transforms import LOG_RESOURCES, ResourceScaler


def inverse_one(scaled: np.ndarray, scaler: ResourceScaler, resource: str, project: bool = True) -> tuple[np.ndarray, float, np.ndarray]:
    index = RESOURCE_ORDER.index(resource)
    transformed = np.asarray(scaled, dtype=float) * scaler.transformed_iqr[index] + scaler.transformed_median[index]
    unclipped = np.expm1(transformed) if resource in LOG_RESOURCES else transformed
    rate = float(np.mean(unclipped < 0)) if resource in LOG_RESOURCES else 0.0
    prediction = np.maximum(0.0, unclipped) if project and resource in LOG_RESOURCES else unclipped
    return prediction, rate, unclipped


def per_lead_metrics(y_true: np.ndarray, y_pred: np.ndarray, training_native_iqr: float, persistence: np.ndarray | None = None) -> dict[str, np.ndarray]:
    if y_true.shape != y_pred.shape or y_true.ndim != 2 or y_true.shape[1] != 8:
        raise ValueError("Expected matching [N,8] arrays")
    if training_native_iqr <= 0:
        raise ValueError("NMAE denominator must be positive")
    residual = y_true.astype(float) - y_pred.astype(float)
    mae = np.mean(np.abs(residual), axis=0); rmse = np.sqrt(np.mean(residual ** 2, axis=0))
    total = np.sum((y_true - y_true.mean(axis=0, keepdims=True)) ** 2, axis=0)
    r2 = np.full(8, np.nan, dtype=float)
    valid = total > 0
    r2[valid] = 1 - np.sum(residual[:, valid] ** 2, axis=0) / total[valid]
    result = {"mae": mae, "rmse": rmse, "r2": r2, "nmae": mae / training_native_iqr}
    if persistence is not None:
        pmae = np.mean(np.abs(y_true - persistence), axis=0)
        result["persistence_skill"] = 1.0 - mae / pmae
    return result


def macro_mae(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"formulation", "machine", "fold", "seed", "resource", "lead", "mae"}
    if not required.issubset(frame.columns):
        raise ValueError("Metric frame lacks macro keys")
    seed_mean = frame.groupby(["formulation", "machine", "fold", "resource", "lead"], as_index=False).mae.mean()
    return seed_mean.groupby(["formulation", "resource", "lead"], as_index=False).mae.mean().rename(columns={"mae": "macro_mae"})


def comparison_gain(baseline: float, candidate: float) -> float:
    return 100.0 * (baseline - candidate) / baseline
