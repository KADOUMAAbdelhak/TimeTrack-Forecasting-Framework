"""Eight direct deterministic LightGBM regressors."""

from __future__ import annotations

import numpy as np
from lightgbm import LGBMRegressor

from .base import ForecastModel


class LightGBMForecaster(ForecastModel):
    def __init__(
        self,
        num_leaves: int,
        learning_rate: float,
        n_estimators: int,
    ) -> None:
        self.config = {
            "num_leaves": num_leaves,
            "learning_rate": learning_rate,
            "n_estimators": n_estimators,
        }
        self.models: list[LGBMRegressor] = []

    @staticmethod
    def _flatten(X: np.ndarray) -> np.ndarray:
        return X.reshape(len(X), -1)

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_validation: np.ndarray | None = None,
        y_validation: np.ndarray | None = None,
    ) -> "LightGBMForecaster":
        train = self._flatten(X_train)
        self.models = []
        for lead_column in range(y_train.shape[1]):
            model = LGBMRegressor(
                objective="regression_l1",
                max_depth=-1,
                min_child_samples=20,
                subsample=1.0,
                colsample_bytree=1.0,
                reg_alpha=0.0,
                reg_lambda=0.0,
                random_state=0,
                n_jobs=1,
                deterministic=True,
                force_col_wise=True,
                verbosity=-1,
                **self.config,
            )
            model.fit(train, y_train[:, lead_column])
            self.models.append(model)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        flattened = self._flatten(X)
        return np.column_stack([model.predict(flattened) for model in self.models])
