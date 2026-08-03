"""Ensemble strategies package."""

from models.ensembles.strategies import (
    ensemble_predict,
    inverse_mae_weights,
    nonnegative_constrained_weights,
    oof_stacking,
    simple_mean,
)

__all__ = [
    "simple_mean",
    "inverse_mae_weights",
    "nonnegative_constrained_weights",
    "oof_stacking",
    "ensemble_predict",
]
