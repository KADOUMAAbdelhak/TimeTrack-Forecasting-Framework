"""Deterministic direct-horizon LightGBM components for the v0.3 wrapper."""

from dataclasses import dataclass
from hashlib import sha256
import re

import numpy as np

from ..identity import RESOURCES
from ..tree.design import GRID, SETTINGS

_NONFINITE_NUMBER = re.compile(rb"(?<![A-Za-z0-9_])[+-]?(?:nan|inf(?:inity)?)(?=[\s,\]]|$)", re.I)


@dataclass(frozen=True, slots=True)
class FeatureLayout:
    context: int
    target: str
    scope: str

    def __post_init__(self):
        if type(self.context) is not int or self.context not in (4, 9, 18):
            raise ValueError("Expected a registered frozen context")
        if self.target not in RESOURCES or self.scope not in SETTINGS["scopes"]:
            raise ValueError("Unknown target or input scope")

    @property
    def resources(self):
        return (self.target,) if self.scope == "own" else RESOURCES

    @property
    def names(self):
        return tuple(f"{resource}_lag_{lag}" for resource in self.resources
                     for lag in range(self.context - 1, -1, -1))

    def flatten(self, windows):
        array = np.asarray(windows)
        if array.ndim != 3 or array.shape[1:] != (self.context, len(RESOURCES)) or not len(array):
            raise ValueError("Expected nonempty [origins, frozen context, four resources] windows")
        indices = [RESOURCES.index(resource) for resource in self.resources]
        features = np.ascontiguousarray(array[:, :, indices].transpose(0, 2, 1).reshape(len(array), -1))
        if not np.isfinite(features).all():
            raise ValueError("Nonfinite flattened LightGBM feature")
        return features

    def payload(self):
        return {"dimension": len(self.names), "feature_order": list(self.names),
                "lag_order": "oldest_to_newest", "resource_order": list(self.resources)}


def prediction_sha256(values):
    return sha256(np.asarray(values, dtype="<f8").tobytes(order="C")).hexdigest()


def new_estimator(config):
    from lightgbm import LGBMRegressor

    if config not in GRID:
        raise ValueError("Unregistered LightGBM configuration")
    return LGBMRegressor(**config.payload(), objective=SETTINGS["objective"],
                         random_state=SETTINGS["seed"], n_jobs=SETTINGS["threads"],
                         deterministic=SETTINGS["deterministic"], force_col_wise=True,
                         subsample=SETTINGS["row_subsample"], subsample_freq=0,
                         colsample_bytree=SETTINGS["column_subsample"], verbosity=-1)


def fit_horizon(config, X, y, names):
    estimator = new_estimator(config)
    estimator.fit(X, y, feature_name=list(names))
    return estimator


def encode_booster(booster):
    encoded = booster.model_to_string(num_iteration=-1).encode("utf-8")
    if booster.num_trees() < 1 or _NONFINITE_NUMBER.search(encoded):
        raise ValueError("Empty or nonfinite LightGBM scalar model")
    return encoded


def predict_scaled(booster, X):
    prediction = np.asarray(booster.predict(X, num_iteration=-1, num_threads=SETTINGS["threads"]), dtype=np.float64)
    if prediction.shape != (len(X),) or not np.isfinite(prediction).all():
        raise ValueError("Invalid scaled scalar prediction")
    return prediction


def score_native_horizon(partition, booster, X, actual, target):
    scaled = predict_scaled(booster, X)
    native, fraction, raw = partition.inverse_target(scaled, target)
    if (native.shape != actual.shape or raw.shape != native.shape or not np.isfinite(fraction)
            or not all(np.isfinite(values).all() for values in (native, raw, actual))):
        raise ValueError("Invalid native scalar prediction or target")
    mae = float(np.mean(np.abs(native - actual)))
    if not np.isfinite(mae):
        raise ValueError("Nonfinite native MAE")
    return {"native_mae": mae, "scaled_prediction_sha256": prediction_sha256(scaled),
            "native_prediction_sha256": prediction_sha256(native)}
