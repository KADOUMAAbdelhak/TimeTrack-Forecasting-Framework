"""
Central public interface for TimeTrack forecasting models.

Usage:
    from models.forecasting import build_model, list_available_models, fit, predict, save, load
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

# Import model modules for side-effect registration
from models.classical import baselines as _baselines  # noqa: F401
from models.classical import linear as _linear  # noqa: F401
from models.classical import intervals as _intervals  # noqa: F401
from models.machine_learning import trees as _trees  # noqa: F401
from models.deep_learning import neural as _neural  # noqa: F401
from models.multivariate import global_models as _global  # noqa: F401
from models.hybrid import residual_adaptation as _residual  # noqa: F401
from models.registry import (
    build_model as _build,
    get_model_metadata as _meta,
    list_available_models as _list,
)


def list_available_models() -> list[str]:
    return _list()


def build_model(name: str, **kwargs: Any):
    return _build(name, **kwargs)


def fit(model, X: np.ndarray, y: np.ndarray, X_val=None, y_val=None):
    return model.fit(X, y, X_val=X_val, y_val=y_val)


def predict(model, X: np.ndarray) -> np.ndarray:
    return model.predict(X)


def predict_quantiles(model, X: np.ndarray, quantiles: list[float] | None = None):
    return model.predict_quantiles(X, quantiles=quantiles)


def save(model, path: str | Path) -> None:
    model.save(path)


def load(path: str | Path):
    from models.base import BaseForecaster

    return BaseForecaster.load(path)


def get_model_metadata(model) -> dict[str, Any]:
    return _meta(model)
