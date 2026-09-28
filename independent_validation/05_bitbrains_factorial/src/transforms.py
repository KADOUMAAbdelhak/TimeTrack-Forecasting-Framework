"""Frozen transforms, training-only robust scaling, and physical inversion."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import RESOURCE_ORDER
from .panel import scaler_rows


LOG_RESOURCES = frozenset({"THROUGHPUT", "DISK_WRITE"})


def transform_resource(values: np.ndarray, resource: str) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if resource not in RESOURCE_ORDER:
        raise ValueError(resource)
    if resource in LOG_RESOURCES:
        if np.any(values < 0):
            raise ValueError(f"Negative {resource} supplied to log1p")
        return np.log1p(values)
    return values.copy()


@dataclass(frozen=True)
class ResourceScaler:
    transformed_median: np.ndarray
    transformed_iqr: np.ndarray
    native_iqr: np.ndarray

    @classmethod
    def fit(cls, native_values: np.ndarray) -> "ResourceScaler":
        values = np.asarray(native_values, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != 4 or not np.isfinite(values).all():
            raise ValueError("Scaler requires finite [N,4] native values")
        transformed = np.column_stack([
            transform_resource(values[:, index], resource)
            for index, resource in enumerate(RESOURCE_ORDER)
        ])
        q25, median, q75 = np.quantile(transformed, [0.25, 0.5, 0.75], axis=0)
        iqr = q75 - q25
        native_q25, native_q75 = np.quantile(values, [0.25, 0.75], axis=0)
        native_iqr = native_q75 - native_q25
        if np.any(iqr <= 0) or np.any(native_iqr <= 0):
            raise ValueError("IQR_ZERO_STOP")
        return cls(median, iqr, native_iqr)

    def transform(self, native_values: np.ndarray) -> np.ndarray:
        values = np.asarray(native_values, dtype=np.float64)
        transformed = np.stack([
            transform_resource(values[..., index], resource)
            for index, resource in enumerate(RESOURCE_ORDER)
        ], axis=-1)
        return ((transformed - self.transformed_median) / self.transformed_iqr).astype(np.float32)

    def inverse_one(self, scaled: np.ndarray, resource: str, project: bool = True) -> tuple[np.ndarray, float, np.ndarray]:
        index = RESOURCE_ORDER.index(resource)
        transformed = np.asarray(scaled, dtype=np.float64) * self.transformed_iqr[index] + self.transformed_median[index]
        native = np.expm1(transformed) if resource in LOG_RESOURCES else transformed
        negative_fraction = float(np.mean(native < 0)) if resource in LOG_RESOURCES else 0.0
        projected = np.maximum(native, 0.0) if project and resource in LOG_RESOURCES else native
        return projected, negative_fraction, native


def fit_partition_scaler(frame: pd.DataFrame, origins: np.ndarray, context_length: int) -> ResourceScaler:
    rows = scaler_rows(origins, context_length)
    values = frame.loc[rows, list(RESOURCE_ORDER)].to_numpy(dtype=np.float64)
    return ResourceScaler.fit(values)


def scale_windows(X: np.ndarray, y: np.ndarray, scaler: ResourceScaler) -> tuple[np.ndarray, np.ndarray]:
    X_scaled = scaler.transform(X)
    y_scaled = scaler.transform(np.moveaxis(y, 1, -1))
    return X_scaled, np.moveaxis(y_scaled, -1, 1)
