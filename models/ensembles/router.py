"""Validation-only metric–horizon adaptive routing (C2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
from sklearn.neighbors import KNeighborsRegressor

from models.ensembles.constrained_mixture import apply_mixture, fit_constrained_mixture
from models.ensembles.gating_features import batch_gating_features
from models.ensembles.strategies import ensemble_predict, inverse_mae_weights


@dataclass
class RouterConfig:
    constituent_names: tuple[str, ...]
    key_fields: tuple[str, ...] = ("target", "horizon")
    min_val_samples: int = 50
    seed: int = 0


@dataclass
class StaticRouter:
    """Select best constituent by inner-validation MAE for each target×horizon key."""

    config: RouterConfig
    selection_: dict[tuple, str] = field(default_factory=dict)
    val_mae_: dict[tuple, dict[str, float]] = field(default_factory=dict)

    def fit(
        self,
        keys: list[tuple],
        y_val: dict[tuple, np.ndarray],
        preds_val: dict[tuple, dict[str, np.ndarray]],
    ) -> "StaticRouter":
        rng_keys = sorted(set(keys))
        for key in rng_keys:
            y = y_val[key]
            maes = {
                name: float(np.mean(np.abs(np.asarray(preds_val[key][name]) - y)))
                for name in self.config.constituent_names
                if name in preds_val[key]
            }
            if not maes:
                continue
            self.val_mae_[key] = maes
            self.selection_[key] = min(maes, key=maes.get)
        return self

    def predict_key(self, key: tuple, preds_test: dict[str, np.ndarray]) -> tuple[np.ndarray, str]:
        name = self.selection_.get(key)
        if name is None or name not in preds_test:
            # fallback: first available
            name = next(iter(preds_test))
        return np.asarray(preds_test[name]), name


@dataclass
class RegimeRouter:
    """
    KNN over gating features → predicted best constituent index.
    Trained on validation origins only (labels = argmin constituent MAE at that origin).
    """

    config: RouterConfig
    n_neighbors: int = 25
    models_: dict[tuple, Any] = field(default_factory=dict)
    fallback_: dict[tuple, str] = field(default_factory=dict)

    def fit(
        self,
        keys: list[tuple],
        X_val: dict[tuple, np.ndarray],
        y_val: dict[tuple, np.ndarray],
        preds_val: dict[tuple, dict[str, np.ndarray]],
        hours: dict[tuple, np.ndarray] | None = None,
        weekends: dict[tuple, np.ndarray] | None = None,
    ) -> "RegimeRouter":
        names = list(self.config.constituent_names)
        for key in sorted(set(keys)):
            y = np.asarray(y_val[key], dtype=float).reshape(-1)
            errs = np.column_stack(
                [np.abs(np.asarray(preds_val[key][n]).reshape(-1) - y) for n in names if n in preds_val[key]]
            )
            used = [n for n in names if n in preds_val[key]]
            if errs.shape[0] < self.config.min_val_samples:
                mae = errs.mean(axis=0)
                self.fallback_[key] = used[int(np.argmin(mae))]
                continue
            labels = np.argmin(errs, axis=1)
            G = batch_gating_features(
                X_val[key],
                hours=None if hours is None else hours[key],
                weekends=None if weekends is None else weekends[key],
            )
            knn = KNeighborsRegressor(n_neighbors=min(self.n_neighbors, len(G)), weights="distance")
            # predict soft label via one-hot regression then argmax
            oh = np.eye(len(used))[labels]
            knn.fit(G, oh)
            self.models_[key] = (knn, used)
            self.fallback_[key] = used[int(np.argmin(errs.mean(axis=0)))]
        return self

    def predict_key(
        self,
        key: tuple,
        X_test: np.ndarray,
        preds_test: dict[str, np.ndarray],
        hours: np.ndarray | None = None,
        weekends: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Returns (pred, selected_name_per_row as object array)."""
        if key not in self.models_:
            name = self.fallback_.get(key, next(iter(preds_test)))
            p = np.asarray(preds_test[name])
            return p, np.array([name] * len(p), dtype=object)
        knn, used = self.models_[key]
        G = batch_gating_features(X_test, hours=hours, weekends=weekends)
        soft = knn.predict(G)
        idx = np.argmax(soft, axis=1)
        names = np.array([used[i] for i in idx], dtype=object)
        out = np.zeros(len(idx), dtype=float)
        for i, n in enumerate(names):
            out[i] = float(np.asarray(preds_test[n]).reshape(-1)[i])
        return out, names


def oracle_selector(y_true: np.ndarray, preds: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """
    Per-timestep best constituent using true labels — analysis upper bound only.
    NEVER deployable.
    """
    names = list(preds.keys())
    P = np.column_stack([np.asarray(preds[n]).reshape(-1) for n in names])
    y = np.asarray(y_true).reshape(-1)
    idx = np.argmin(np.abs(P - y[:, None]), axis=1)
    sel = np.array([names[i] for i in idx], dtype=object)
    return P[np.arange(len(y)), idx], sel
