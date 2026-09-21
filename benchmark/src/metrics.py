"""Per-lead forecasting metrics and relative comparisons."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .windows import FUTURE_LEADS


def per_lead_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame:
    if y_true.shape != y_pred.shape or y_true.ndim != 2:
        raise ValueError("Expected matching [N, leads] arrays")
    rows = []
    for column, lead in enumerate(FUTURE_LEADS):
        truth = y_true[:, column].astype(float)
        prediction = y_pred[:, column].astype(float)
        residual = truth - prediction
        mae = float(np.mean(np.abs(residual)))
        rmse = float(np.sqrt(np.mean(residual**2)))
        total = float(np.sum((truth - truth.mean()) ** 2))
        r2 = (
            float(1.0 - np.sum(residual**2) / total)
            if len(truth) >= 2 and total > 0
            else np.nan
        )
        rows.append({"lead": lead, "mae": mae, "rmse": rmse, "r2": r2})
    return pd.DataFrame(rows)


def relative_mae_change(reference_mae: float, evaluated_mae: float) -> float:
    if not np.isfinite(reference_mae) or reference_mae == 0:
        return np.nan
    return float(100.0 * (reference_mae - evaluated_mae) / reference_mae)
