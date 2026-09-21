"""Last-value multi-lead persistence."""

from __future__ import annotations

import numpy as np

from .base import ForecastModel


class PersistenceForecaster(ForecastModel):
    def __init__(self, output_size: int = 8, target_channel: int = 0) -> None:
        self.output_size = output_size
        self.target_channel = target_channel

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_validation: np.ndarray | None = None,
        y_validation: np.ndarray | None = None,
    ) -> "PersistenceForecaster":
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        last = X[:, -1, self.target_channel]
        return np.repeat(last[:, None], self.output_size, axis=1)
