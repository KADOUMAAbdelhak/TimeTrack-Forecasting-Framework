"""Ensemble strategies package."""

from models.ensembles.strategies import (
    ensemble_predict,
    inverse_mae_weights,
    nonnegative_constrained_weights,
    oof_stacking,
    simple_mean,
)
from models.ensembles.router import RegimeRouter, StaticRouter, oracle_selector
from models.ensembles.constrained_mixture import apply_mixture, fit_constrained_mixture

__all__ = [
    "simple_mean",
    "inverse_mae_weights",
    "nonnegative_constrained_weights",
    "oof_stacking",
    "ensemble_predict",
    "StaticRouter",
    "RegimeRouter",
    "oracle_selector",
    "fit_constrained_mixture",
    "apply_mixture",
]
