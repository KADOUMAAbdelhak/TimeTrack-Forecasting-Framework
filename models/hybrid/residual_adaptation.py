"""Global forecast + lightweight entity residual adaptation."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.linear_model import Ridge

from models.base import BaseForecaster
from models.multivariate.entity_features import EntityVocab, TargetScaler, append_entity_features
from models.registry import build_model, register


@register("global_residual")
class GlobalResidualAdaptationForecaster(BaseForecaster):
    """
    Shared global backbone + per-entity residual head (Ridge on residuals).

    For LOMO / unseen entities: use global prediction only (no learned residual head).
    Optional limited local calibration fits a residual head on pre-eval samples.
    """

    name = "global_residual"

    def __init__(
        self,
        base_model: str = "ridge",
        residual_alpha: float = 1.0,
        scaler_mode: str = "per_entity",
        entities: list[str] | None = None,
        use_onehot_in_global: bool = True,
        base_kwargs: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.base_model = base_model
        self.residual_alpha = residual_alpha
        self.scaler_mode = scaler_mode
        self.entities = entities
        self.use_onehot_in_global = use_onehot_in_global
        self.base_kwargs = base_kwargs or {}

    def fit(self, X, y, X_val=None, y_val=None, entity_keys=None, entity_keys_val=None):
        if entity_keys is None:
            raise ValueError("entity_keys required")
        ents = self.entities or sorted(set(map(str, entity_keys)))
        self.vocab_ = EntityVocab(tuple(ents))
        self.scaler_ = TargetScaler(mode=self.scaler_mode)  # type: ignore[arg-type]
        y_flat = np.asarray(y, dtype=float)
        self.scaler_.fit(y_flat.reshape(len(entity_keys), -1)[:, 0], entity_keys)
        y_s = self.scaler_.transform(y, entity_keys)
        yv_s = (
            self.scaler_.transform(y_val, entity_keys_val)
            if y_val is not None and entity_keys_val is not None
            else None
        )

        Xg = append_entity_features(X, entity_keys, self.vocab_, mode="one_hot") if self.use_onehot_in_global else X
        Xvg = (
            append_entity_features(X_val, entity_keys_val, self.vocab_, mode="one_hot")
            if self.use_onehot_in_global and X_val is not None and entity_keys_val is not None
            else X_val
        )

        def _fit():
            self.global_ = build_model(
                self.base_model,
                horizon=self.horizon,
                context_length=self.context_length,
                seed=self.seed,
                **self.base_kwargs,
            )
            self.global_.fit(Xg, y_s, Xvg, yv_s)
            # Residual heads on train residuals (scaled space)
            g_pred = self.global_.predict(Xg)
            resid = np.asarray(y_s, dtype=float) - np.asarray(g_pred, dtype=float)
            if resid.ndim == 1:
                resid = resid[:, None]
            X_flat = np.asarray(X, dtype=float)
            if X_flat.ndim == 3:
                X_flat = X_flat.reshape(X_flat.shape[0], -1)
            self.residual_heads_: dict[str, list] = {}
            keys = np.asarray(entity_keys).astype(str)
            for e in ents:
                mask = keys == e
                if mask.sum() < 5:
                    continue
                heads = []
                for h in range(resid.shape[1]):
                    est = Ridge(alpha=self.residual_alpha, random_state=self.seed)
                    est.fit(X_flat[mask], resid[mask, h])
                    heads.append(est)
                self.residual_heads_[e] = heads
            self.metadata.n_parameters = int(
                (self.global_.metadata.n_parameters or 0)
                + sum(sum(h.coef_.size + 1 for h in hs) for hs in self.residual_heads_.values())
            )
            return self

        return self._timed_fit(_fit)

    def fit_calibration(self, X_cal, y_cal, entity_key: str) -> None:
        """Limited local residual calibration for one entity (pre-eval samples only)."""
        if not self.is_fitted:
            raise RuntimeError("fit global backbone first")
        n = int(np.asarray(X_cal).shape[0])
        keys = [entity_key] * n
        Xg = (
            append_entity_features(X_cal, keys, self.vocab_, mode="one_hot")
            if self.use_onehot_in_global
            else X_cal
        )
        y_s = self.scaler_.transform(y_cal, keys)
        g_pred = self.global_.predict(Xg)
        resid = np.asarray(y_s, dtype=float) - np.asarray(g_pred, dtype=float)
        if resid.ndim == 1:
            resid = resid[:, None]
        X_flat = np.asarray(X_cal, dtype=float)
        if X_flat.ndim == 3:
            X_flat = X_flat.reshape(X_flat.shape[0], -1)
        heads = []
        for h in range(resid.shape[1]):
            est = Ridge(alpha=self.residual_alpha, random_state=self.seed)
            est.fit(X_flat, resid[:, h])
            heads.append(est)
        self.residual_heads_[entity_key] = heads

    def predict(self, X, entity_keys=None, allow_residual: bool = True):
        if entity_keys is None:
            raise ValueError("entity_keys required")
        Xg = append_entity_features(X, entity_keys, self.vocab_, mode="one_hot") if self.use_onehot_in_global else X
        X_flat = np.asarray(X, dtype=float)
        if X_flat.ndim == 3:
            X_flat = X_flat.reshape(X_flat.shape[0], -1)
        keys = np.asarray(entity_keys).astype(str)

        def _predict(_X):
            pred = np.asarray(self.global_.predict(Xg), dtype=float)
            single = pred.ndim == 1
            if single:
                pred = pred[:, None]
            if allow_residual:
                for i, e in enumerate(keys):
                    heads = self.residual_heads_.get(e)
                    if not heads:
                        continue  # unseen / no head → global only
                    for h, est in enumerate(heads):
                        pred[i, h] = pred[i, h] + float(est.predict(X_flat[i : i + 1])[0])
            if single or self.horizon == 1:
                pred = pred.reshape(-1)
            return self.scaler_.inverse_transform(pred, entity_keys)

        return self._timed_predict(_predict, X)
