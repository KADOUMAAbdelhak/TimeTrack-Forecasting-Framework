"""Pooled and entity-aware global forecasters wrapping registry models."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np

from models.base import BaseForecaster
from models.multivariate.entity_features import EntityVocab, TargetScaler, append_entity_features
from models.registry import build_model, register

IdentityMode = Literal["none", "one_hot"]
ScalerMode = Literal["global", "per_entity", "scale_normalized", "capacity"]


@register("global_pooled")
class GlobalPooledForecaster(BaseForecaster):
    """
    All machines pooled as samples from one process — no machine identity.
    Base learner selected via `base_model` (default ridge).
    """

    name = "global_pooled"

    def __init__(
        self,
        base_model: str = "ridge",
        scaler_mode: ScalerMode = "per_entity",
        capacity: dict[str, float] | None = None,
        base_kwargs: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.base_model = base_model
        self.scaler_mode = scaler_mode
        self.capacity = capacity
        self.base_kwargs = base_kwargs or {}
        self.identity_mode: IdentityMode = "none"

    def fit(self, X, y, X_val=None, y_val=None, entity_keys=None, entity_keys_val=None):
        if entity_keys is None:
            raise ValueError("global models require entity_keys aligned with X")
        self.scaler_ = TargetScaler(mode=self.scaler_mode)
        self.scaler_.fit(np.asarray(y).reshape(len(entity_keys), -1)[:, 0], entity_keys, capacity=self.capacity)
        y_s = self.scaler_.transform(y, entity_keys)
        yv_s = self.scaler_.transform(y_val, entity_keys_val) if y_val is not None and entity_keys_val is not None else y_val

        def _fit():
            self.model_ = build_model(
                self.base_model,
                horizon=self.horizon,
                context_length=self.context_length,
                seed=self.seed,
                **self.base_kwargs,
            )
            self.model_.fit(X, y_s, X_val, yv_s)
            self.metadata.n_parameters = self.model_.metadata.n_parameters
            return self

        return self._timed_fit(_fit)

    def predict(self, X, entity_keys=None):
        if entity_keys is None:
            raise ValueError("predict requires entity_keys for inverse scaling")

        def _predict(_X):
            pred = self.model_.predict(X)
            return self.scaler_.inverse_transform(pred, entity_keys)

        return self._timed_predict(_predict, X)


@register("global_onehot")
class GlobalOneHotForecaster(BaseForecaster):
    """Global model with one-hot machine identity (tree/linear friendly)."""

    name = "global_onehot"

    def __init__(
        self,
        base_model: str = "ridge",
        entities: list[str] | None = None,
        scaler_mode: ScalerMode = "per_entity",
        capacity: dict[str, float] | None = None,
        base_kwargs: dict[str, Any] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.base_model = base_model
        self.entities = entities
        self.scaler_mode = scaler_mode
        self.capacity = capacity
        self.base_kwargs = base_kwargs or {}

    def fit(self, X, y, X_val=None, y_val=None, entity_keys=None, entity_keys_val=None):
        if entity_keys is None:
            raise ValueError("entity_keys required")
        ents = self.entities or sorted(set(map(str, entity_keys)))
        self.vocab_ = EntityVocab(tuple(ents))
        self.scaler_ = TargetScaler(mode=self.scaler_mode)
        self.scaler_.fit(np.asarray(y).reshape(len(entity_keys), -1)[:, 0], entity_keys, capacity=self.capacity)
        y_s = self.scaler_.transform(y, entity_keys)
        yv_s = (
            self.scaler_.transform(y_val, entity_keys_val)
            if y_val is not None and entity_keys_val is not None
            else y_val
        )
        X_e = append_entity_features(X, entity_keys, self.vocab_, mode="one_hot")
        Xv_e = (
            append_entity_features(X_val, entity_keys_val, self.vocab_, mode="one_hot")
            if X_val is not None and entity_keys_val is not None
            else X_val
        )

        def _fit():
            self.model_ = build_model(
                self.base_model,
                horizon=self.horizon,
                context_length=self.context_length,
                seed=self.seed,
                **self.base_kwargs,
            )
            self.model_.fit(X_e, y_s, Xv_e, yv_s)
            self.metadata.n_parameters = self.model_.metadata.n_parameters
            return self

        return self._timed_fit(_fit)

    def predict(self, X, entity_keys=None):
        if entity_keys is None:
            raise ValueError("entity_keys required")
        X_e = append_entity_features(X, entity_keys, self.vocab_, mode="one_hot")

        def _predict(_X):
            pred = self.model_.predict(X_e)
            return self.scaler_.inverse_transform(pred, entity_keys)

        return self._timed_predict(_predict, X_e)


@register("global_embed")
class GlobalEmbeddingForecaster(BaseForecaster):
    """
    Neural global model with learned entity embedding.
    Unseen entities use a dedicated unknown embedding row (index 0 reserved as UNK).
    """

    name = "global_embed"

    def __init__(
        self,
        entities: list[str] | None = None,
        embed_dim: int = 8,
        hidden: int = 64,
        epochs: int = 20,
        batch_size: int = 256,
        lr: float = 1e-3,
        scaler_mode: ScalerMode = "per_entity",
        capacity: dict[str, float] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.entities = entities
        self.embed_dim = embed_dim
        self.hidden = hidden
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        self.scaler_mode = scaler_mode
        self.capacity = capacity

    def fit(self, X, y, X_val=None, y_val=None, entity_keys=None, entity_keys_val=None):
        import torch
        import torch.nn as nn

        if entity_keys is None:
            raise ValueError("entity_keys required")
        ents = self.entities or sorted(set(map(str, entity_keys)))
        # index 0 = UNK; 1..n = known entities
        self.vocab_ = EntityVocab(tuple(ents))
        self.scaler_ = TargetScaler(mode=self.scaler_mode)
        self.scaler_.fit(np.asarray(y).reshape(len(entity_keys), -1)[:, 0], entity_keys, capacity=self.capacity)
        y_s = self.scaler_.transform(y, entity_keys)
        X_arr = np.asarray(X, dtype=np.float32)
        if X_arr.ndim == 3:
            X_arr = X_arr.reshape(X_arr.shape[0], -1)
        y_arr = np.asarray(y_s, dtype=np.float32)
        if y_arr.ndim == 1:
            y_arr = y_arr[:, None]
        e_idx = self._entity_indices(entity_keys)

        n_ent = self.vocab_.n_entities + 1  # +UNK
        in_dim = X_arr.shape[1]
        out_dim = y_arr.shape[1]

        emb_dim = self.embed_dim
        hidden = self.hidden

        class Net(nn.Module):
            def __init__(self_net):
                super().__init__()
                self_net.emb = nn.Embedding(n_ent, emb_dim)
                self_net.mlp = nn.Sequential(
                    nn.Linear(in_dim + emb_dim, hidden),
                    nn.ReLU(),
                    nn.Linear(hidden, out_dim),
                )

            def forward(self_net, x, e):
                return self_net.mlp(torch.cat([x, self_net.emb(e)], dim=-1))

        def _fit():
            torch.manual_seed(self.seed)
            self.net_ = Net()
            opt = torch.optim.Adam(self.net_.parameters(), lr=self.lr)
            loss_fn = nn.MSELoss()
            Xt = torch.tensor(X_arr)
            yt = torch.tensor(y_arr)
            et = torch.tensor(e_idx)
            for _ in range(self.epochs):
                self.net_.train()
                perm = torch.randperm(len(Xt))
                for i in range(0, len(Xt), self.batch_size):
                    sl = perm[i : i + self.batch_size]
                    opt.zero_grad()
                    pred = self.net_(Xt[sl], et[sl])
                    loss = loss_fn(pred, yt[sl])
                    loss.backward()
                    opt.step()
            self.metadata.n_parameters = int(sum(p.numel() for p in self.net_.parameters()))
            return self

        return self._timed_fit(_fit)

    def _entity_indices(self, keys) -> np.ndarray:
        raw = self.vocab_.encode(keys)
        # map known idx i -> i+1; unknown (-1) -> 0
        out = np.zeros(len(raw), dtype=np.int64)
        known = raw >= 0
        out[known] = raw[known] + 1
        return out

    def predict(self, X, entity_keys=None):
        import torch

        if entity_keys is None:
            raise ValueError("entity_keys required")
        X_arr = np.asarray(X, dtype=np.float32)
        if X_arr.ndim == 3:
            X_arr = X_arr.reshape(X_arr.shape[0], -1)
        e_idx = self._entity_indices(entity_keys)

        def _predict(_X):
            self.net_.eval()
            with torch.no_grad():
                pred = self.net_(torch.tensor(X_arr), torch.tensor(e_idx)).cpu().numpy()
            if self.horizon == 1:
                pred = pred.reshape(-1)
            return self.scaler_.inverse_transform(pred, entity_keys)

        return self._timed_predict(_predict, X_arr)
