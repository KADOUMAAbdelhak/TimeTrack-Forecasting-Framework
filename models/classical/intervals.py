"""Simple residual conformal prediction intervals (validation-calibrated)."""

from __future__ import annotations

from typing import Any

import numpy as np

from models.base import BaseForecaster
from models.registry import build_model, register


@register("conformal_ridge")
class ConformalRidgeForecaster(BaseForecaster):
    """
    Point Ridge forecast + symmetric absolute residual conformal interval.
    Calibration residuals from validation fold only (not outer test).
    """

    name = "conformal_ridge"

    def __init__(self, alpha: float = 0.1, ridge_alpha: float = 1.0, **kwargs):
        super().__init__(**kwargs)
        self.alpha = alpha
        self.ridge_alpha = ridge_alpha

    def fit(self, X, y, X_val=None, y_val=None):
        def _fit():
            self.model_ = build_model(
                "ridge",
                horizon=self.horizon,
                context_length=self.context_length,
                seed=self.seed,
                alpha=self.ridge_alpha,
            )
            self.model_.fit(X, y, X_val, y_val)
            if X_val is None or y_val is None or len(X_val) == 0:
                self.q_ = 0.0
            else:
                pred = np.asarray(self.model_.predict(X_val), dtype=float).reshape(-1)
                yt = np.asarray(y_val, dtype=float).reshape(-1)
                n = min(len(pred), len(yt))
                resid = np.abs(yt[:n] - pred[:n])
                # split-conformal quantile
                level = np.ceil((n + 1) * (1 - self.alpha)) / max(n, 1)
                level = min(1.0, max(0.0, level))
                self.q_ = float(np.quantile(resid, level)) if n else 0.0
            self.metadata.n_parameters = self.model_.metadata.n_parameters
            return self

        return self._timed_fit(_fit)

    def predict(self, X):
        return self._timed_predict(lambda _X: self.model_.predict(X), X)

    def predict_quantiles(self, X, quantiles: list[float] | None = None):
        point = np.asarray(self.predict(X), dtype=float)
        q = getattr(self, "q_", 0.0)
        # map requested quantiles to symmetric interval around point using calibrated width
        out = {}
        for qq in quantiles or [self.alpha / 2, 0.5, 1 - self.alpha / 2]:
            if abs(qq - 0.5) < 1e-12:
                out[qq] = point
            elif qq < 0.5:
                out[qq] = point - q
            else:
                out[qq] = point + q
        return out

    def predict_interval(self, X) -> dict[str, Any]:
        point = np.asarray(self.predict(X), dtype=float)
        q = getattr(self, "q_", 0.0)
        return {"point": point, "lower": point - q, "upper": point + q, "halfwidth": q, "alpha": self.alpha}
