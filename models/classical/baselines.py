"""Simple statistical baselines."""

from __future__ import annotations

import numpy as np

from models.base import BaseForecaster
from models.registry import register


def _last_context_value(X: np.ndarray) -> np.ndarray:
    """X is (n, context) flat last-dim target lags or (n, context, feats)."""
    X = np.asarray(X, dtype=float)
    if X.ndim == 3:
        # last timestep, first feature = target
        return X[:, -1, 0]
    if X.ndim == 2:
        # assume columns are [target_lag_context, ..., target_lag_1, ...]
        # For baseline flat windows built from univariate series only: last col is lag1
        return X[:, -1]
    raise ValueError(f"bad X ndim {X.ndim}")


@register("persistence")
class PersistenceForecaster(BaseForecaster):
    name = "persistence"

    def fit(self, X, y, X_val=None, y_val=None):
        def _fit():
            self._y_mean = float(np.mean(y)) if np.size(y) else 0.0
            self.metadata.n_parameters = 0
            return self

        return self._timed_fit(_fit)

    def predict(self, X):
        def _predict(X):
            last = _last_context_value(X)
            if self.horizon == 1:
                return last
            return np.tile(last.reshape(-1, 1), (1, self.horizon))

        return self._timed_predict(_predict, X)


@register("seasonal_persistence")
class SeasonalPersistenceForecaster(BaseForecaster):
    """Repeat value from `seasonality` steps before origin (requires flat lag features)."""

    name = "seasonal_persistence"

    def __init__(self, seasonality: int = 1920, **kwargs):
        super().__init__(**kwargs)
        self.seasonality = seasonality

    def fit(self, X, y, X_val=None, y_val=None):
        def _fit():
            self.metadata.n_parameters = 1
            self.metadata.config["seasonality"] = self.seasonality
            return self

        return self._timed_fit(_fit)

    def predict(self, X):
        def _predict(X):
            X = np.asarray(X, dtype=float)
            if X.ndim == 3:
                # use lag at seasonality if context long enough else last
                idx = -min(self.seasonality, X.shape[1])
                last = X[:, idx, 0]
            else:
                idx = -min(self.seasonality, X.shape[1])
                last = X[:, idx]
            if self.horizon == 1:
                return last
            return np.tile(last.reshape(-1, 1), (1, self.horizon))

        return self._timed_predict(_predict, X)


@register("historical_mean")
class HistoricalMeanForecaster(BaseForecaster):
    name = "historical_mean"

    def fit(self, X, y, X_val=None, y_val=None):
        def _fit():
            self.mean_ = float(np.mean(y))
            self.metadata.n_parameters = 1
            return self

        return self._timed_fit(_fit)

    def predict(self, X):
        def _predict(X):
            n = len(X)
            if self.horizon == 1:
                return np.full(n, self.mean_)
            return np.full((n, self.horizon), self.mean_)

        return self._timed_predict(_predict, X)


@register("moving_average")
class MovingAverageForecaster(BaseForecaster):
    name = "moving_average"

    def __init__(self, window: int | None = None, **kwargs):
        super().__init__(**kwargs)
        self.window = window

    def fit(self, X, y, X_val=None, y_val=None):
        def _fit():
            self.window_ = self.window or min(self.context_length, 8)
            self.metadata.n_parameters = 1
            return self

        return self._timed_fit(_fit)

    def predict(self, X):
        def _predict(X):
            X = np.asarray(X, dtype=float)
            w = self.window_
            if X.ndim == 3:
                ctx = X[:, -w:, 0]
            else:
                ctx = X[:, -w:]
            avg = np.nanmean(ctx, axis=1)
            if self.horizon == 1:
                return avg
            return np.tile(avg.reshape(-1, 1), (1, self.horizon))

        return self._timed_predict(_predict, X)


@register("ewma")
class EWMAForecaster(BaseForecaster):
    name = "ewma"

    def __init__(self, alpha: float = 0.3, **kwargs):
        super().__init__(**kwargs)
        self.alpha = alpha

    def fit(self, X, y, X_val=None, y_val=None):
        def _fit():
            self.metadata.n_parameters = 1
            return self

        return self._timed_fit(_fit)

    def predict(self, X):
        def _predict(X):
            X = np.asarray(X, dtype=float)
            if X.ndim == 3:
                ctx = X[:, :, 0]
            else:
                ctx = X
            # EWMA over context axis
            alpha = self.alpha
            s = ctx[:, 0].copy()
            for t in range(1, ctx.shape[1]):
                s = alpha * ctx[:, t] + (1 - alpha) * s
            if self.horizon == 1:
                return s
            return np.tile(s.reshape(-1, 1), (1, self.horizon))

        return self._timed_predict(_predict, X)


@register("drift")
class DriftForecaster(BaseForecaster):
    """Last value + average drift over context."""

    name = "drift"

    def fit(self, X, y, X_val=None, y_val=None):
        def _fit():
            self.metadata.n_parameters = 0
            return self

        return self._timed_fit(_fit)

    def predict(self, X):
        def _predict(X):
            X = np.asarray(X, dtype=float)
            if X.ndim == 3:
                ctx = X[:, :, 0]
            else:
                ctx = X
            last = ctx[:, -1]
            first = ctx[:, 0]
            drift = (last - first) / max(ctx.shape[1] - 1, 1)
            if self.horizon == 1:
                return last + drift
            steps = np.arange(1, self.horizon + 1).reshape(1, -1)
            return last.reshape(-1, 1) + drift.reshape(-1, 1) * steps

        return self._timed_predict(_predict, X)
