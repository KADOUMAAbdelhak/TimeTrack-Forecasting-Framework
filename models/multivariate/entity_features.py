"""Entity identity features and train-only scaling for global models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

ScalerMode = Literal["global", "per_entity", "scale_normalized", "capacity"]


@dataclass
class EntityVocab:
    """Maps entity keys to indices. Unknown entities map to `unknown_index`."""

    entities: tuple[str, ...]
    unknown_token: str = "__UNK__"

    def __post_init__(self):
        self._to_idx = {e: i for i, e in enumerate(self.entities)}

    @property
    def n_entities(self) -> int:
        return len(self.entities)

    @property
    def unknown_index(self) -> int:
        return -1

    def encode(self, keys: list[str] | np.ndarray) -> np.ndarray:
        out = np.empty(len(keys), dtype=int)
        for i, k in enumerate(keys):
            out[i] = self._to_idx.get(str(k), self.unknown_index)
        return out

    def one_hot(self, keys: list[str] | np.ndarray, *, unknown_as_zeros: bool = True) -> np.ndarray:
        """One-hot with shape (n, n_entities). Unknown -> zeros (no fabricated identity)."""
        idx = self.encode(keys)
        oh = np.zeros((len(idx), self.n_entities), dtype=float)
        known = idx >= 0
        oh[np.arange(len(idx))[known], idx[known]] = 1.0
        if not unknown_as_zeros:
            # reserved: could append unknown column; policy is zeros + optional flag
            pass
        return oh

    def unknown_mask(self, keys: list[str] | np.ndarray) -> np.ndarray:
        return self.encode(keys) < 0


@dataclass
class TargetScaler:
    """Train-only target scaling. Never fit on held-out entity in LOMO."""

    mode: ScalerMode = "per_entity"
    global_mean_: float | None = None
    global_std_: float | None = None
    entity_mean_: dict[str, float] | None = None
    entity_std_: dict[str, float] | None = None
    capacity_: dict[str, float] | None = None
    fitted_entities_: tuple[str, ...] = ()

    def fit(
        self,
        y: np.ndarray,
        entity_keys: list[str] | np.ndarray,
        capacity: dict[str, float] | None = None,
    ) -> "TargetScaler":
        y = np.asarray(y, dtype=float).reshape(-1)
        keys = np.asarray(entity_keys).astype(str)
        if len(y) != len(keys):
            raise ValueError("y/entity_keys length mismatch")
        self.fitted_entities_ = tuple(sorted(set(keys.tolist())))
        self.global_mean_ = float(np.mean(y))
        self.global_std_ = float(np.std(y) + 1e-12)
        self.entity_mean_ = {}
        self.entity_std_ = {}
        for e in self.fitted_entities_:
            mask = keys == e
            self.entity_mean_[e] = float(np.mean(y[mask]))
            self.entity_std_[e] = float(np.std(y[mask]) + 1e-12)
        self.capacity_ = dict(capacity) if capacity else None
        return self

    def transform(self, y: np.ndarray, entity_keys: list[str] | np.ndarray) -> np.ndarray:
        y = np.asarray(y, dtype=float).copy()
        keys = np.asarray(entity_keys).astype(str)
        shape = y.shape
        y1 = y.reshape(len(keys), -1)
        for i, e in enumerate(keys):
            y1[i] = self._scale_row(y1[i], e)
        return y1.reshape(shape)

    def inverse_transform(self, y: np.ndarray, entity_keys: list[str] | np.ndarray) -> np.ndarray:
        y = np.asarray(y, dtype=float).copy()
        keys = np.asarray(entity_keys).astype(str)
        shape = y.shape
        y1 = y.reshape(len(keys), -1)
        for i, e in enumerate(keys):
            y1[i] = self._unscale_row(y1[i], e)
        return y1.reshape(shape)

    def _mean_std(self, e: str) -> tuple[float, float]:
        if self.mode == "global":
            return self.global_mean_ or 0.0, self.global_std_ or 1.0
        if self.mode in {"per_entity", "scale_normalized"}:
            if e in (self.entity_mean_ or {}):
                return self.entity_mean_[e], self.entity_std_[e]
            # Unseen entity: use global train stats only (never held-out fit)
            return self.global_mean_ or 0.0, self.global_std_ or 1.0
        if self.mode == "capacity":
            cap = (self.capacity_ or {}).get(e)
            if cap is None or cap == 0:
                return 0.0, self.global_std_ or 1.0
            return 0.0, float(cap)
        raise ValueError(self.mode)

    def _scale_row(self, row: np.ndarray, e: str) -> np.ndarray:
        mu, sd = self._mean_std(e)
        return (row - mu) / sd

    def _unscale_row(self, row: np.ndarray, e: str) -> np.ndarray:
        mu, sd = self._mean_std(e)
        return row * sd + mu

    def assert_entity_excluded(self, held_out: str) -> None:
        if held_out in self.fitted_entities_:
            raise AssertionError(f"held-out entity {held_out} leaked into scaler fit")


def append_entity_features(
    X: np.ndarray,
    entity_keys: list[str] | np.ndarray,
    vocab: EntityVocab,
    mode: Literal["none", "one_hot"] = "one_hot",
) -> np.ndarray:
    """Append entity features to flat X (n, d) or keep 3D and append as extra feature channels flattened later."""
    X = np.asarray(X, dtype=float)
    if mode == "none":
        return X
    oh = vocab.one_hot(entity_keys)
    if X.ndim == 2:
        return np.concatenate([X, oh], axis=1)
    if X.ndim == 3:
        # broadcast one-hot across time then concat on feature axis
        oh_t = np.repeat(oh[:, None, :], X.shape[1], axis=1)
        return np.concatenate([X, oh_t], axis=2)
    raise ValueError(f"unsupported X ndim {X.ndim}")


def make_global_sample_meta(
    *,
    entity_key: str,
    timestamp: Any,
    horizon: int,
    context: int,
    fold: int | str,
    source_machine: str,
    target_scale: dict[str, float] | None = None,
) -> dict[str, Any]:
    return {
        "entity_key": entity_key,
        "timestamp": str(timestamp),
        "horizon": horizon,
        "context": context,
        "fold": fold,
        "source_machine": source_machine,
        "target_scale": target_scale or {},
    }
