"""Frozen benchmark feature-set definitions."""

from __future__ import annotations

import json

import pandas as pd


FEATURE_SET_IDS = [
    "F0_LOCAL",
    "F1_THROUGHPUT",
    "F2_LOMO_MEAN",
    "F3_LOMO_MEDIAN",
    "F4_THROUGHPUT_LOMO_MEAN",
    "F5_THROUGHPUT_LOMO_MEDIAN",
]


def feature_columns(machine: str, feature_set: str) -> list[str]:
    cpu = f"{machine}__cpu_utilization"
    throughput = f"{machine}__throughput_total"
    mean = f"{machine}__lomo_cpu_utilization_mean"
    median = f"{machine}__lomo_cpu_utilization_median"
    definitions = {
        "F0_LOCAL": [cpu],
        "F1_THROUGHPUT": [cpu, throughput],
        "F2_LOMO_MEAN": [cpu, mean],
        "F3_LOMO_MEDIAN": [cpu, median],
        "F4_THROUGHPUT_LOMO_MEAN": [cpu, throughput, mean],
        "F5_THROUGHPUT_LOMO_MEDIAN": [cpu, throughput, median],
    }
    if feature_set not in definitions:
        raise KeyError(f"Unknown frozen feature set: {feature_set}")
    return definitions[feature_set]


def common_finite_columns(machine: str) -> list[str]:
    """Union used to hold origin rows fixed across all six ablations."""
    columns: list[str] = []
    for feature_set in FEATURE_SET_IDS:
        for column in feature_columns(machine, feature_set):
            if column not in columns:
                columns.append(column)
    return columns


def validate_lomo_exclusion(registry: pd.DataFrame, machine: str) -> bool:
    rows = registry[
        registry["canonical_name"].isin(
            [
                f"{machine}__lomo_cpu_utilization_mean",
                f"{machine}__lomo_cpu_utilization_median",
            ]
        )
    ]
    if len(rows) != 2:
        return False
    for row in rows.itertuples(index=False):
        components = json.loads(row.component_columns)
        if any(component.startswith(f"{machine}__") for component in components):
            return False
        if len(components) != 6:
            return False
    return True
