"""Training-only resource transforms, robust scaling, and physical inversion."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import FUTURE_LEADS, RESOURCE_ORDER, target_columns


LOG_RESOURCES = frozenset({"THROUGHPUT", "DISK_WRITE"})


def transform_resource(values: np.ndarray, resource: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if resource in LOG_RESOURCES:
        if np.any(array < 0):
            raise ValueError(f"{resource} contains negative native values")
        return np.log1p(array)
    if resource not in RESOURCE_ORDER:
        raise ValueError(resource)
    return array.copy()


@dataclass(frozen=True)
class ResourceScaler:
    transformed_median: np.ndarray
    transformed_iqr: np.ndarray
    native_iqr: np.ndarray

    @classmethod
    def fit(cls, native_values: np.ndarray) -> "ResourceScaler":
        values = np.asarray(native_values, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != 4 or not np.isfinite(values).all():
            raise ValueError("Scaler fit requires finite [N,4] values")
        transformed = np.column_stack([transform_resource(values[:, i], resource) for i, resource in enumerate(RESOURCE_ORDER)])
        q25, median, q75 = np.quantile(transformed, [0.25, 0.5, 0.75], axis=0)
        iqr = q75 - q25
        native_q25, native_q75 = np.quantile(values, [0.25, 0.75], axis=0)
        native_iqr = native_q75 - native_q25
        if np.any(iqr <= 0):
            bad = [RESOURCE_ORDER[i] for i in np.flatnonzero(iqr <= 0)]
            raise ValueError(f"Non-positive transformed IQR: {bad}")
        if np.any(native_iqr <= 0):
            bad = [RESOURCE_ORDER[i] for i in np.flatnonzero(native_iqr <= 0)]
            raise ValueError(f"Non-positive native IQR: {bad}")
        return cls(median.astype(np.float64), iqr.astype(np.float64), native_iqr.astype(np.float64))

    def transform(self, native_values: np.ndarray) -> np.ndarray:
        values = np.asarray(native_values, dtype=np.float64)
        if values.shape[-1] != 4:
            raise ValueError("Resource axis must be last and have size four")
        transformed = np.stack([transform_resource(values[..., i], resource) for i, resource in enumerate(RESOURCE_ORDER)], axis=-1)
        return ((transformed - self.transformed_median) / self.transformed_iqr).astype(np.float32)

    def inverse(self, scaled_values: np.ndarray, physical_projection: bool = True) -> tuple[np.ndarray, np.ndarray]:
        scaled = np.asarray(scaled_values, dtype=np.float64)
        if scaled.shape[-1] != 4:
            raise ValueError("Resource axis must be last and have size four")
        transformed = scaled * self.transformed_iqr + self.transformed_median
        native = transformed.copy()
        pre_negative = np.zeros(4, dtype=np.float64)
        for i, resource in enumerate(RESOURCE_ORDER):
            if resource in LOG_RESOURCES:
                native[..., i] = np.expm1(transformed[..., i])
                pre_negative[i] = float(np.mean(native[..., i] < 0))
                if physical_projection:
                    native[..., i] = np.maximum(0.0, native[..., i])
        return native.astype(np.float64), pre_negative

    def metadata(self) -> dict[str, dict[str, float]]:
        return {resource: {"transformed_median": float(self.transformed_median[i]), "transformed_iqr": float(self.transformed_iqr[i]), "native_iqr": float(self.native_iqr[i])} for i, resource in enumerate(RESOURCE_ORDER)}


def fit_partition_scaler(panel: pd.DataFrame, machine: str, origins: np.ndarray, context_length: int) -> ResourceScaler:
    origins = np.asarray(origins, dtype=np.int64)
    history = (origins[:, None] - np.arange(context_length - 1, -1, -1)).ravel()
    targets = (origins[:, None] + np.asarray(FUTURE_LEADS)).ravel()
    rows = np.unique(np.concatenate([history, targets]))
    values = panel.loc[rows, list(target_columns(machine))].to_numpy(dtype=np.float64)
    return ResourceScaler.fit(values)


def scale_windows(X: np.ndarray, y: np.ndarray, scaler: ResourceScaler) -> tuple[np.ndarray, np.ndarray]:
    X_scaled = scaler.transform(X)
    y_scaled = scaler.transform(np.moveaxis(y, 1, -1))
    return X_scaled, np.moveaxis(y_scaled, -1, 1)
