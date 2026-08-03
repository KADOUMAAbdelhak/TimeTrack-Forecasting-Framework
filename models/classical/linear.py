"""Classical linear models on engineered lag features."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import ElasticNet, Lasso, Ridge

from models.base import BaseForecaster
from models.registry import register


class _SklearnMultiHorizon(BaseForecaster):
    estimator_factory = None

    def fit(self, X, y, X_val=None, y_val=None):
        X_arr = np.asarray(X, dtype=float)
        if X_arr.ndim == 3:
            X_arr = X_arr.reshape(X_arr.shape[0], -1)
        y_arr = np.asarray(y, dtype=float)

        def _fit():
            self.models_ = []
            if y_arr.ndim == 1:
                est = self.estimator_factory()
                est.fit(X_arr, y_arr)
                self.models_ = [est]
            else:
                for h in range(y_arr.shape[1]):
                    est = self.estimator_factory()
                    est.fit(X_arr, y_arr[:, h])
                    self.models_.append(est)
            self.metadata.n_parameters = int(
                sum(getattr(m, "coef_", np.array([])).size + 1 for m in self.models_)
            )
            return self

        return self._timed_fit(_fit)

    def predict(self, X):
        X_arr = np.asarray(X, dtype=float)
        if X_arr.ndim == 3:
            X_arr = X_arr.reshape(X_arr.shape[0], -1)

        def _predict(_X):
            preds = [m.predict(X_arr) for m in self.models_]
            if len(preds) == 1:
                return preds[0]
            return np.column_stack(preds)

        return self._timed_predict(_predict, X_arr)


@register("ridge")
class RidgeForecaster(_SklearnMultiHorizon):
    name = "ridge"

    def __init__(self, alpha: float = 1.0, **kwargs):
        super().__init__(**kwargs)
        self.alpha = alpha

    def estimator_factory(self):
        return Ridge(alpha=self.alpha, random_state=self.seed)


@register("lasso")
class LassoForecaster(_SklearnMultiHorizon):
    name = "lasso"

    def __init__(self, alpha: float = 0.001, **kwargs):
        super().__init__(**kwargs)
        self.alpha = alpha

    def estimator_factory(self):
        return Lasso(alpha=self.alpha, random_state=self.seed, max_iter=5000)


@register("elasticnet")
class ElasticNetForecaster(_SklearnMultiHorizon):
    name = "elasticnet"

    def __init__(self, alpha: float = 0.001, l1_ratio: float = 0.5, **kwargs):
        super().__init__(**kwargs)
        self.alpha = alpha
        self.l1_ratio = l1_ratio

    def estimator_factory(self):
        return ElasticNet(alpha=self.alpha, l1_ratio=self.l1_ratio, random_state=self.seed, max_iter=5000)
