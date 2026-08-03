"""Base forecasting model interface."""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np


@dataclass
class ModelMetadata:
    model_name: str
    target: str | None = None
    horizon: int | None = None
    context_length: int | None = None
    n_parameters: int | None = None
    training_time_sec: float | None = None
    inference_time_sec: float | None = None
    seed: int | None = None
    config: dict[str, Any] = field(default_factory=dict)
    software_versions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseForecaster(ABC):
    """Consistent estimator API for TimeTrack models."""

    name: str = "base"

    def __init__(self, horizon: int = 1, context_length: int = 32, seed: int = 0, **kwargs: Any):
        self.horizon = horizon
        self.context_length = context_length
        self.seed = seed
        self.kwargs = kwargs
        self.metadata = ModelMetadata(
            model_name=self.name,
            horizon=horizon,
            context_length=context_length,
            seed=seed,
            config=dict(kwargs),
        )
        self.is_fitted = False

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray, X_val: np.ndarray | None = None, y_val: np.ndarray | None = None) -> "BaseForecaster":
        ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        ...

    def predict_quantiles(self, X: np.ndarray, quantiles: list[float] | None = None) -> dict[float, np.ndarray]:
        raise NotImplementedError(f"{self.name} does not support predict_quantiles")

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path / "model.joblib")
        (path / "metadata.json").write_text(json.dumps(self.metadata.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path | str) -> "BaseForecaster":
        return joblib.load(Path(path) / "model.joblib")

    def _timed_fit(self, fn, *args, **kwargs):
        t0 = time.perf_counter()
        out = fn(*args, **kwargs)
        self.metadata.training_time_sec = time.perf_counter() - t0
        self.is_fitted = True
        return out

    def _timed_predict(self, fn, X: np.ndarray) -> np.ndarray:
        t0 = time.perf_counter()
        pred = fn(X)
        self.metadata.inference_time_sec = time.perf_counter() - t0
        pred = np.asarray(pred)
        if self.horizon == 1 and pred.ndim > 1 and pred.shape[-1] == 1:
            pred = pred.reshape(-1)
        return pred
