"""Native-scale neural-v2 metrics and exact matched F1 gains."""

from __future__ import annotations

import numpy as np


def per_lead_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, np.ndarray]:
    if y_true.shape != y_pred.shape or y_true.ndim != 2 or y_true.shape[1] != 8:
        raise ValueError("Targets and predictions must both have shape [N,8]")
    residual = y_true.astype(float) - y_pred.astype(float)
    mae = np.mean(np.abs(residual), axis=0)
    rmse = np.sqrt(np.mean(residual**2, axis=0))
    centered = y_true - y_true.mean(axis=0, keepdims=True)
    total = np.sum(centered**2, axis=0)
    r2 = np.full(8, np.nan, dtype=float)
    valid = total > 0
    r2[valid] = 1.0 - np.sum(residual[:, valid] ** 2, axis=0) / total[valid]
    return {"mae": mae, "rmse": rmse, "r2": r2}


def matched_gains(
    f0: dict[str, np.ndarray], f1: dict[str, np.ndarray]
) -> dict[str, np.ndarray]:
    return {
        "mae_gain_pct": 100.0 * (f0["mae"] - f1["mae"]) / f0["mae"],
        "rmse_gain_pct": 100.0 * (f0["rmse"] - f1["rmse"]) / f0["rmse"],
        "r2_delta": f1["r2"] - f0["r2"],
    }


def seed_summary(values: np.ndarray) -> dict[str, np.ndarray]:
    if values.ndim != 2 or values.shape[0] != 3:
        raise ValueError("Seed summaries require [3 seeds, N metrics]")
    return {
        "mean": values.mean(axis=0),
        "std": values.std(axis=0, ddof=1),
        "min": values.min(axis=0),
        "max": values.max(axis=0),
        "positive_seed_count": (values > 0).sum(axis=0),
    }
