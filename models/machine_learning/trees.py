"""Tree-based forecasting models."""

from __future__ import annotations

import numpy as np

from models.base import BaseForecaster
from models.registry import register


class _TreeMultiHorizon(BaseForecaster):
    def _make_estimator(self):
        raise NotImplementedError

    def fit(self, X, y, X_val=None, y_val=None):
        X_arr = np.asarray(X, dtype=float)
        if X_arr.ndim == 3:
            X_arr = X_arr.reshape(X_arr.shape[0], -1)
        y_arr = np.asarray(y, dtype=float)
        Xv = None
        yv = None
        if X_val is not None and y_val is not None:
            Xv = np.asarray(X_val, dtype=float)
            if Xv.ndim == 3:
                Xv = Xv.reshape(Xv.shape[0], -1)
            yv = np.asarray(y_val, dtype=float)

        def _fit():
            self.models_ = []
            ys = [y_arr] if y_arr.ndim == 1 else [y_arr[:, h] for h in range(y_arr.shape[1])]
            for yi in ys:
                est = self._make_estimator()
                if Xv is not None and yv is not None:
                    if yv.ndim == 2:
                        idx = len(self.models_)
                        yv_h = yv[:, min(idx, yv.shape[1] - 1)]
                    else:
                        yv_h = yv
                    fitted = False
                    for kwargs in (
                        {"eval_X": Xv, "eval_y": yv_h},
                        {"eval_set": [(Xv, yv_h)], "verbose": False},
                        {},
                    ):
                        try:
                            est.fit(X_arr, yi, **kwargs)
                            fitted = True
                            break
                        except TypeError:
                            continue
                    if not fitted:
                        est.fit(X_arr, yi)
                else:
                    est.fit(X_arr, yi)
                self.models_.append(est)
            n_params = 0
            for m in self.models_:
                if hasattr(m, "n_estimators"):
                    n_params += int(m.n_estimators) * int(getattr(m, "max_depth", 1) or 1)
            self.metadata.n_parameters = n_params
            return self

        return self._timed_fit(_fit)

    def predict(self, X):
        X_arr = np.asarray(X, dtype=float)
        if X_arr.ndim == 3:
            X_arr = X_arr.reshape(X_arr.shape[0], -1)

        def _predict(_X):
            preds = [m.predict(X_arr) for m in self.models_]
            if len(preds) == 1:
                return np.asarray(preds[0])
            return np.column_stack(preds)

        return self._timed_predict(_predict, X_arr)


@register("random_forest")
class RandomForestForecaster(_TreeMultiHorizon):
    name = "random_forest"

    def __init__(self, n_estimators: int = 100, max_depth: int | None = 12, **kwargs):
        super().__init__(**kwargs)
        self.n_estimators = n_estimators
        self.max_depth = max_depth

    def _make_estimator(self):
        from sklearn.ensemble import RandomForestRegressor

        return RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=self.seed,
            n_jobs=-1,
        )


@register("extra_trees")
class ExtraTreesForecaster(_TreeMultiHorizon):
    name = "extra_trees"

    def __init__(self, n_estimators: int = 100, max_depth: int | None = 12, **kwargs):
        super().__init__(**kwargs)
        self.n_estimators = n_estimators
        self.max_depth = max_depth

    def _make_estimator(self):
        from sklearn.ensemble import ExtraTreesRegressor

        return ExtraTreesRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=self.seed,
            n_jobs=-1,
        )


@register("lightgbm")
class LightGBMForecaster(_TreeMultiHorizon):
    name = "lightgbm"

    def __init__(
        self,
        n_estimators: int = 200,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        max_depth: int = -1,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.max_depth = max_depth

    def _make_estimator(self):
        from lightgbm import LGBMRegressor

        # Must match experiment-freeze-v2 seed-0 wrapper exactly.
        # Only random_state varies across robustness seeds; n_jobs stays -1.
        return LGBMRegressor(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            num_leaves=self.num_leaves,
            max_depth=self.max_depth,
            random_state=self.seed,
            n_jobs=-1,
            verbosity=-1,
        )


@register("xgboost")
class XGBoostForecaster(_TreeMultiHorizon):
    name = "xgboost"

    def __init__(
        self,
        n_estimators: int = 200,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth

    def _make_estimator(self):
        from xgboost import XGBRegressor

        return XGBRegressor(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            max_depth=self.max_depth,
            random_state=self.seed,
            n_jobs=-1,
            verbosity=0,
        )


@register("catboost")
class CatBoostForecaster(_TreeMultiHorizon):
    name = "catboost"

    def __init__(self, iterations: int = 200, learning_rate: float = 0.05, depth: int = 6, **kwargs):
        super().__init__(**kwargs)
        self.iterations = iterations
        self.learning_rate = learning_rate
        self.depth = depth

    def _make_estimator(self):
        try:
            from catboost import CatBoostRegressor
        except ImportError as e:
            raise ImportError("catboost is not installed") from e
        return CatBoostRegressor(
            iterations=self.iterations,
            learning_rate=self.learning_rate,
            depth=self.depth,
            random_seed=self.seed,
            verbose=False,
        )
