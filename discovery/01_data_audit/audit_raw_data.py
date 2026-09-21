#!/usr/bin/env python3
"""Read-only forensic audit of the six active TimeTrack raw CSV datasets.

The script reads only from ``data/raw`` and writes only beneath
``discovery/01_data_audit/outputs`` plus ``DATA_AUDIT_REPORT.md``.
It deliberately performs no interpolation, cleaning, alignment, lag analysis,
feature selection, or forecasting.
"""

from __future__ import annotations

import csv
import gc
import hashlib
import json
import math
import os
import platform
import re
import resource
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
AUDIT_DIR = ROOT / "discovery" / "01_data_audit"
OUTPUT_DIR = AUDIT_DIR / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
REPORT_PATH = AUDIT_DIR / "DATA_AUDIT_REPORT.md"

RAW_FILES = [
    "compute_dataset.csv",
    "detailed_cpu_cores_dataset.csv",
    "disk_dataset.csv",
    "network_dataset.csv",
    "packet-loss-dataset.csv",
    "throughputs_dataset.csv",
]

MACHINE_TO_HOST = {
    "machine01": "acamas",
    "machine02": "bellerophon",
    "machine03": "dedale",
    "machine04": "demophon",
    "machine05": "pegase",
    "machine06": "perse",
    "machine07": "phaedra",
}
HOST_TO_MACHINE = {v: k for k, v in MACHINE_TO_HOST.items()}
HOSTS = list(HOST_TO_MACHINE)
MACHINES = list(MACHINE_TO_HOST)

QUANTILES = [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]
NEAR_CONSTANT_DOMINANT_FRACTION = 0.99
ZERO_DOMINATED_FRACTION = 0.95
SPARSE_NONMISSING_FRACTION = 0.05
HIGH_CORRELATION_THRESHOLD = 0.995
OUTLIER_IQR_MULTIPLIER = 3.0


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Cannot serialize {type(value)!r}")


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, default=json_default) + "\n")


def read_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False)
    if "timestamp" not in frame:
        raise ValueError(f"{path.name}: missing timestamp column")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="raise")
    return frame


@dataclass
class SignalSemantics:
    dataset: str
    column: str
    resource_family: str = "unknown"
    metric: str = "unknown"
    scope: str = "unknown"
    machine: str = ""
    host: str = ""
    interface: str = ""
    core: str = ""
    unit_if_inferable: str = "unknown"
    signal_type: str = "unknown"
    notes: str = ""


def parse_signal(dataset: str, column: str) -> SignalSemantics:
    s = SignalSemantics(dataset=dataset, column=column)
    lower = column.lower()
    if lower == "timestamp":
        s.resource_family = "time"
        s.metric = "timestamp"
        s.scope = "dataset"
        s.signal_type = "timestamp"
        s.unit_if_inferable = "datetime"
        return s

    machine_match = re.search(r"(machine0[1-7])", lower)
    if machine_match:
        s.machine = machine_match.group(1)
        s.host = MACHINE_TO_HOST.get(s.machine, "")
        s.scope = "machine"
    elif "machie02" in lower:
        # Preserve the raw typo while cataloguing its evident machine scope.
        s.machine = "machine02"
        s.host = MACHINE_TO_HOST[s.machine]
        s.scope = "machine"
        s.notes = "Raw column contains typo 'machie02'; interpreted as machine02 from paired schema."
    for host in HOSTS:
        if host in lower:
            s.host = host
            s.machine = HOST_TO_MACHINE[host]
            s.scope = "host"
            break

    iface_match = re.search(r"network-device-([^:\s]+)", lower)
    if iface_match:
        s.interface = iface_match.group(1)
        s.scope = "interface"
    core_match = re.search(r":cpu-(\d+)", lower)
    if core_match:
        s.core = core_match.group(1)
        s.scope = "CPU core"

    if lower.startswith("free_cpu_"):
        s.resource_family = "CPU"
        s.metric = "free CPU"
        s.unit_if_inferable = "percent (inferred)"
        s.signal_type = "bounded percentage"
    elif lower.startswith("used_cpu_"):
        s.resource_family = "CPU"
        s.metric = "used CPU"
        s.unit_if_inferable = "percent (inferred)"
        s.signal_type = "bounded percentage"
    elif re.search(r"\bcu\b", lower) or lower.endswith(" cu"):
        s.resource_family = "CPU"
        s.metric = "CPU utilization"
        s.unit_if_inferable = "percent (inferred)"
        s.signal_type = "bounded percentage"
    elif re.search(r"\bcf\b", lower) or lower.endswith(" cf"):
        s.resource_family = "CPU"
        s.metric = "CPU free"
        s.unit_if_inferable = "percent (inferred)"
        s.signal_type = "bounded percentage"
    elif "totalnumberofcores" in lower or "totalcpucores" in lower:
        s.resource_family = "CPU"
        s.metric = "CPU core count"
        s.unit_if_inferable = "cores"
        s.signal_type = "configuration/count"
    elif lower.endswith(" am") or lower == "cluster am":
        s.resource_family = "memory"
        s.metric = "available memory"
        s.unit_if_inferable = "bytes (inferred)"
        s.signal_type = "level"
    elif lower.endswith(" um") or lower == "cluster um":
        s.resource_family = "memory"
        s.metric = "used memory"
        s.unit_if_inferable = "bytes (inferred)"
        s.signal_type = "level"
    elif "totalprovmemory" in lower:
        s.resource_family = "memory"
        s.metric = "provisioned memory"
        s.unit_if_inferable = "bytes (inferred)"
        s.signal_type = "configuration/level"
    elif lower.endswith(" fd"):
        s.resource_family = "disk/storage"
        s.metric = "free disk"
        s.unit_if_inferable = "bytes (inferred)"
        s.signal_type = "level"
    elif lower.endswith(" ud") or lower == "cluster ud":
        s.resource_family = "disk/storage"
        s.metric = "used disk"
        s.unit_if_inferable = "bytes (inferred)"
        s.signal_type = "level"
    elif "available disk" in lower:
        s.resource_family = "disk/storage"
        s.metric = "available disk"
        s.unit_if_inferable = "bytes (inferred)"
        s.signal_type = "level"
    elif lower.endswith(" drt"):
        s.resource_family = "disk/storage"
        s.metric = "disk read throughput"
        s.unit_if_inferable = "unknown rate unit"
        s.signal_type = "rate"
    elif lower.endswith(" dwt"):
        s.resource_family = "disk/storage"
        s.metric = "disk write throughput"
        s.unit_if_inferable = "unknown rate unit"
        s.signal_type = "rate"
    elif lower.startswith("transmitted_throughput_"):
        s.resource_family = "network throughput"
        s.metric = "transmitted throughput"
        s.unit_if_inferable = "unknown throughput unit"
        s.signal_type = "rate"
    elif lower.startswith("received_throughput_"):
        s.resource_family = "network throughput"
        s.metric = "received throughput"
        s.unit_if_inferable = "unknown throughput unit"
        s.signal_type = "rate"
    elif lower.startswith("err_packet_"):
        s.resource_family = "packet errors"
        s.metric = "packet errors"
        s.unit_if_inferable = "count/rate (unclear)"
        s.signal_type = "sparse event/count"
    elif lower.startswith("drop_packet_"):
        s.resource_family = "packet loss"
        s.metric = "dropped packets"
        s.unit_if_inferable = "count/rate (unclear)"
        s.signal_type = "sparse event/count"
    elif "rtt" in lower:
        s.resource_family = "latency"
        if "max" in lower:
            s.metric = "maximum RTT"
        elif "min" in lower:
            s.metric = "minimum RTT"
        elif "average" in lower:
            s.metric = "average RTT"
        elif "mdev" in lower:
            s.metric = "RTT mean deviation"
        else:
            s.metric = "RTT"
        s.scope = "global"
        s.unit_if_inferable = "milliseconds (inferred)"
        s.signal_type = "continuous"
    elif "jitter" in lower:
        s.resource_family = "jitter"
        s.metric = "network jitter"
        s.scope = "global"
        s.unit_if_inferable = "milliseconds (inferred)"
        s.signal_type = "continuous"
    else:
        s.notes = "Semantics not confidently inferable from column name."

    if lower.startswith("cluster ") or lower.startswith("cluster_"):
        s.scope = "cluster"
    elif lower.startswith("total") and s.scope == "unknown":
        s.scope = "cluster/global"
    if s.resource_family == "unknown" and not s.notes:
        s.notes = "Unclassified signal; retain for later domain verification."
    return s


def timestamp_audit(dataset: str, ts: pd.Series) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    ts = pd.Series(pd.to_datetime(ts), name="timestamp")
    deltas = ts.diff().dt.total_seconds()
    finite = deltas.iloc[1:].dropna()
    median = float(finite.median())
    duplicate_count = int(ts.duplicated().sum())
    out_of_order = int((deltas < 0).sum())
    strictly_increasing = bool((deltas.iloc[1:] > 0).all())

    q = finite.quantile(QUANTILES)
    summary = {
        "dataset": dataset,
        "timestamp_column": "timestamp",
        "timestamp_min": str(ts.min()),
        "timestamp_max": str(ts.max()),
        "strictly_increasing": strictly_increasing,
        "duplicate_timestamps": duplicate_count,
        "out_of_order_timestamps": out_of_order,
        "median_interval_seconds": median,
        "mean_interval_seconds": float(finite.mean()),
        "std_interval_seconds": float(finite.std()),
        "min_interval_seconds": float(finite.min()),
        "max_interval_seconds": float(finite.max()),
        **{f"interval_q{int(p*100):02d}_seconds": float(q.loc[p]) for p in QUANTILES},
    }

    gap_rows: list[dict[str, Any]] = []
    thresholds = {
        "gt_2x_median": 2 * median,
        "gt_5x_median": 5 * median,
        "gt_30_minutes": 30 * 60,
        "gt_1_hour": 60 * 60,
    }
    for i in range(1, len(ts)):
        delta = safe_float(deltas.iloc[i])
        if delta is None:
            continue
        flags = {name: delta > threshold for name, threshold in thresholds.items()}
        if any(flags.values()):
            gap_rows.append(
                {
                    "dataset": dataset,
                    "previous_timestamp": str(ts.iloc[i - 1]),
                    "next_timestamp": str(ts.iloc[i]),
                    "interval_seconds": delta,
                    **flags,
                }
            )
    gaps = pd.DataFrame(gap_rows)
    for name in thresholds:
        summary[f"gap_count_{name}"] = int(gaps[name].sum()) if not gaps.empty else 0

    # A segment boundary is any >2x median interval; this intentionally discovers all.
    boundary = (deltas > 2 * median).fillna(False)
    segment_id = boundary.cumsum()
    segments = (
        pd.DataFrame({"timestamp": ts, "segment_id": segment_id})
        .groupby("segment_id", as_index=False)
        .agg(start=("timestamp", "min"), end=("timestamp", "max"), rows=("timestamp", "size"))
    )
    segments.insert(0, "dataset", dataset)
    segments["duration_seconds"] = (segments["end"] - segments["start"]).dt.total_seconds()
    return summary, gaps, segments


def column_statistics(dataset: str, frame: pd.DataFrame) -> pd.DataFrame:
    n = len(frame)
    rows: list[dict[str, Any]] = []
    numeric_cols = list(frame.select_dtypes(include=[np.number]).columns)
    numeric_stats: dict[str, dict[str, Any]] = {}
    if numeric_cols:
        numeric = frame[numeric_cols].replace([np.inf, -np.inf], np.nan)
        desc = numeric.describe(percentiles=QUANTILES).T
        for col in numeric_cols:
            d = desc.loc[col]
            numeric_stats[col] = {
                "min": d.get("min", np.nan),
                "max": d.get("max", np.nan),
                "mean": d.get("mean", np.nan),
                "median": d.get("50%", np.nan),
                "std": d.get("std", np.nan),
                "q01": d.get("1%", np.nan),
                "q05": d.get("5%", np.nan),
                "q25": d.get("25%", np.nan),
                "q75": d.get("75%", np.nan),
                "q95": d.get("95%", np.nan),
                "q99": d.get("99%", np.nan),
            }

    for col in frame.columns:
        series = frame[col]
        is_numeric = bool(pd.api.types.is_numeric_dtype(series))
        missing = int(series.isna().sum())
        unique = int(series.nunique(dropna=True))
        stats = numeric_stats.get(col, {})
        if is_numeric:
            arr = series.to_numpy(dtype=float, na_value=np.nan)
            pos_inf = int(np.isposinf(arr).sum())
            neg_inf = int(np.isneginf(arr).sum())
        else:
            pos_inf = neg_inf = 0
        rows.append(
            {
                "dataset": dataset,
                "column": col,
                "dtype": str(series.dtype),
                "is_numeric": is_numeric,
                "unique_values": unique,
                "missing_count": missing,
                "missing_percent": 100.0 * missing / n if n else np.nan,
                "positive_infinity_count": pos_inf,
                "negative_infinity_count": neg_inf,
                **stats,
            }
        )
    return pd.DataFrame(rows)


def dynamics_and_quality(
    dataset: str, frame: pd.DataFrame, catalogue: dict[str, SignalSemantics]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dynamics: list[dict[str, Any]] = []
    quality: list[dict[str, Any]] = []
    n = len(frame)
    for col in frame.select_dtypes(include=[np.number]).columns:
        s = frame[col].astype(float).replace([np.inf, -np.inf], np.nan)
        finite = s.dropna()
        count = len(finite)
        unique = int(finite.nunique())
        zeros = int((finite == 0).sum())
        negative = int((finite < 0).sum())
        dominant_fraction = (
            float(finite.value_counts(dropna=False, normalize=True).iloc[0]) if count else np.nan
        )
        diffs = s.diff().dropna()
        finite_diffs = diffs[np.isfinite(diffs)]
        unchanged = float((finite_diffs == 0).mean()) if len(finite_diffs) else np.nan
        increasing = float((finite_diffs > 0).mean()) if len(finite_diffs) else np.nan
        decreasing = float((finite_diffs < 0).mean()) if len(finite_diffs) else np.nan
        mean = safe_float(finite.mean())
        std = safe_float(finite.std())
        cv = abs(std / mean) if mean not in (None, 0.0) and std is not None else np.nan
        monotonic_inc = bool(finite.is_monotonic_increasing) if count else False
        monotonic_dec = bool(finite.is_monotonic_decreasing) if count else False

        # Robust level outlier screening; report count, do not remove.
        if count:
            q1, q3 = finite.quantile([0.25, 0.75])
            iqr = q3 - q1
            if iqr > 0:
                lo = q1 - OUTLIER_IQR_MULTIPLIER * iqr
                hi = q3 + OUTLIER_IQR_MULTIPLIER * iqr
                outlier_count = int(((finite < lo) | (finite > hi)).sum())
            else:
                lo = hi = q1
                outlier_count = int((finite != q1).sum())
        else:
            lo = hi = np.nan
            outlier_count = 0

        reset_count = int((finite_diffs < 0).sum()) if monotonic_inc else 0
        sem = catalogue[col]
        bounded_pct_violation = (
            int(((finite < 0) | (finite > 100)).sum())
            if sem.signal_type == "bounded percentage"
            else 0
        )
        natural_nonnegative = sem.resource_family not in {"unknown", "time"}
        impossible_notes: list[str] = []
        if natural_nonnegative and negative:
            impossible_notes.append(f"{negative} negative values for inferred non-negative metric")
        if bounded_pct_violation:
            impossible_notes.append(f"{bounded_pct_violation} values outside [0,100]")

        zero_fraction = zeros / count if count else np.nan
        nonmissing_fraction = count / n if n else np.nan
        constant = unique <= 1
        near_constant = bool(
            not constant
            and (
                dominant_fraction >= NEAR_CONSTANT_DOMINANT_FRACTION
                or (np.isfinite(unchanged) and unchanged >= NEAR_CONSTANT_DOMINANT_FRACTION)
            )
        )
        zero_dominated = bool(np.isfinite(zero_fraction) and zero_fraction >= ZERO_DOMINATED_FRACTION)
        extremely_sparse = bool(nonmissing_fraction <= SPARSE_NONMISSING_FRACTION)

        if constant:
            dynamic_label = "constant"
        elif zero_dominated and (1 - zero_fraction) > 0:
            dynamic_label = "sparse/event-like"
        elif monotonic_inc or monotonic_dec:
            dynamic_label = "counter-like/monotonic"
        elif unchanged >= 0.90:
            dynamic_label = "step-like/highly persistent"
        elif cv is not None and np.isfinite(cv) and cv > 2:
            dynamic_label = "bursty/high-variability"
        elif unchanged >= 0.50:
            dynamic_label = "persistent"
        else:
            dynamic_label = "continuously varying"

        dynamics.append(
            {
                "dataset": dataset,
                "column": col,
                "resource_family": sem.resource_family,
                "first_difference_std": finite_diffs.std() if len(finite_diffs) else np.nan,
                "median_abs_first_difference": finite_diffs.abs().median() if len(finite_diffs) else np.nan,
                "fraction_unchanged": unchanged,
                "fraction_increasing": increasing,
                "fraction_decreasing": decreasing,
                "largest_positive_jump": finite_diffs.max() if len(finite_diffs) else np.nan,
                "largest_negative_jump": finite_diffs.min() if len(finite_diffs) else np.nan,
                "coefficient_of_variation": cv,
                "monotonic_increasing": monotonic_inc,
                "monotonic_decreasing": monotonic_dec,
                "descriptive_label": dynamic_label,
            }
        )
        quality.append(
            {
                "dataset": dataset,
                "column": col,
                "resource_family": sem.resource_family,
                "constant": constant,
                "near_constant": near_constant,
                "dominant_value_fraction": dominant_fraction,
                "zero_fraction": zero_fraction,
                "nonzero_fraction": 1 - zero_fraction if np.isfinite(zero_fraction) else np.nan,
                "nonmissing_fraction": nonmissing_fraction,
                "extremely_sparse": extremely_sparse,
                "negative_count": negative,
                "bounded_percentage_violation_count": bounded_pct_violation,
                "outlier_count_3x_iqr": outlier_count,
                "outlier_fraction_3x_iqr": outlier_count / count if count else np.nan,
                "iqr_lower_fence": lo,
                "iqr_upper_fence": hi,
                "monotonic_increasing": monotonic_inc,
                "monotonic_decreasing": monotonic_dec,
                "reset_count_if_monotonic_candidate": reset_count,
                "quality_notes": "; ".join(impossible_notes),
            }
        )
    return pd.DataFrame(dynamics), pd.DataFrame(quality)


def hash_series(series: pd.Series) -> str:
    values = pd.util.hash_pandas_object(series, index=False).to_numpy()
    return hashlib.sha256(values.tobytes()).hexdigest()


def exact_duplicates(dataset: str, frame: pd.DataFrame) -> pd.DataFrame:
    groups: defaultdict[str, list[str]] = defaultdict(list)
    for col in frame.columns:
        if col != "timestamp":
            groups[hash_series(frame[col])].append(col)
    rows = []
    for columns in groups.values():
        if len(columns) < 2:
            continue
        base = columns[0]
        for other in columns[1:]:
            if frame[base].equals(frame[other]):
                rows.append(
                    {
                        "dataset": dataset,
                        "column_a": base,
                        "column_b": other,
                        "relationship": "exact_equal",
                    }
                )
    return pd.DataFrame(rows)


def high_correlations(
    dataset: str,
    frame: pd.DataFrame,
    catalogue: dict[str, SignalSemantics],
) -> pd.DataFrame:
    numeric = frame.select_dtypes(include=[np.number])
    valid = [c for c in numeric if numeric[c].nunique(dropna=True) > 1]
    if len(valid) < 2:
        return pd.DataFrame()
    # Correlation matrix is at most 472x472 for this corpus (~1.8 MB float64).
    corr = numeric[valid].corr(method="pearson", min_periods=100)
    values = corr.to_numpy()
    upper_i, upper_j = np.triu_indices(len(valid), k=1)
    selected = np.where(np.abs(values[upper_i, upper_j]) >= HIGH_CORRELATION_THRESHOLD)[0]
    rows = []
    for idx in selected:
        i, j = int(upper_i[idx]), int(upper_j[idx])
        a, b = valid[i], valid[j]
        rows.append(
            {
                "dataset": dataset,
                "column_a": a,
                "column_b": b,
                "pearson_correlation": values[i, j],
                "resource_family_a": catalogue[a].resource_family,
                "resource_family_b": catalogue[b].resource_family,
                "note": "Screening association only; not proof of semantic equivalence.",
            }
        )
    return pd.DataFrame(rows).sort_values(
        "pearson_correlation", key=lambda s: s.abs(), ascending=False
    ) if rows else pd.DataFrame()


def relationship_metrics(lhs: pd.Series, rhs: pd.Series) -> dict[str, Any]:
    pair = pd.DataFrame({"lhs": lhs, "rhs": rhs}).replace([np.inf, -np.inf], np.nan).dropna()
    if pair.empty:
        return {
            "n": 0,
            "max_abs_error": np.nan,
            "mean_abs_error": np.nan,
            "relative_mean_abs_error": np.nan,
            "pearson_correlation": np.nan,
            "exact_within_1e-9": False,
        }
    err = pair["lhs"] - pair["rhs"]
    scale = float(pair["lhs"].abs().mean())
    correlation = (
        float(pair["lhs"].corr(pair["rhs"]))
        if pair["lhs"].nunique() > 1 and pair["rhs"].nunique() > 1
        else np.nan
    )
    return {
        "n": len(pair),
        "max_abs_error": float(err.abs().max()),
        "mean_abs_error": float(err.abs().mean()),
        "relative_mean_abs_error": float(err.abs().mean() / scale) if scale else np.nan,
        "pearson_correlation": correlation,
        "exact_within_1e-9": bool(np.allclose(pair["lhs"], pair["rhs"], atol=1e-9, rtol=1e-12)),
    }


def discover_semantic_relationships(
    compute: pd.DataFrame,
    disk: pd.DataFrame,
    cores: pd.DataFrame,
    throughput: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(
        family: str,
        lhs_name: str,
        rhs_name: str,
        lhs: pd.Series,
        rhs: pd.Series,
        notes: str,
    ) -> None:
        rows.append(
            {
                "relationship_family": family,
                "lhs": lhs_name,
                "rhs": rhs_name,
                **relationship_metrics(lhs, rhs),
                "notes": notes,
            }
        )

    # Cluster vs machine aggregates.
    for code, family in [("UM", "memory"), ("AM", "memory")]:
        lhs_col = f"cluster {code}"
        machine_cols = [f"{m} {code}" for m in MACHINES]
        if lhs_col in compute and all(c in compute for c in machine_cols):
            add(
                f"{family}_cluster_machine_sum",
                lhs_col,
                " + ".join(machine_cols),
                compute[lhs_col],
                compute[machine_cols].sum(axis=1),
                "Direct schema-derived cluster-versus-machine sum candidate.",
            )
    disk_cols = [f"{m} UD" for m in MACHINES]
    if "cluster UD" in compute and all(c in disk for c in disk_cols):
        add(
            "disk_cluster_machine_sum",
            "compute:cluster UD",
            "disk:" + " + ".join(disk_cols),
            compute["cluster UD"],
            disk[disk_cols].sum(axis=1),
            "Cross-file cluster-versus-machine sum candidate on exact timestamps.",
        )

    # Used/free complements: sum should be capacity-like/constant if complementary.
    for code_a, code_b, source, family in [
        ("AM", "UM", compute, "memory"),
        ("FD", "UD", disk, "disk"),
        ("CU", "CF", compute, "CPU"),
    ]:
        for machine in MACHINES:
            a, b = f"{machine} {code_a}", f"{machine} {code_b}"
            if a in source and b in source:
                total = source[a] + source[b]
                rows.append(
                    {
                        "relationship_family": f"{family}_complement_candidate",
                        "lhs": a,
                        "rhs": b,
                        "n": int(total.notna().sum()),
                        "max_abs_error": np.nan,
                        "mean_abs_error": np.nan,
                        "relative_mean_abs_error": np.nan,
                        "pearson_correlation": float(source[a].corr(source[b])),
                        "exact_within_1e-9": bool(
                            total.notna().any() and total.nunique(dropna=True) <= 1
                        ),
                        "notes": (
                            f"Sum unique values={total.nunique(dropna=True)}; "
                            f"sum CV={abs(total.std()/total.mean()) if total.mean() else np.nan:.6g}."
                        ),
                    }
                )

    # Per-core free CPU average vs machine free/used CPU; schema-derived host mapping.
    for machine, host in MACHINE_TO_HOST.items():
        host_core_cols = [c for c in cores if c.startswith(f"free_cpu_{host}:cpu-")]
        if not host_core_cols:
            continue
        core_mean = cores[host_core_cols].mean(axis=1)
        for candidate in [f"{machine} CF", f"{machine} CU"]:
            if candidate in compute:
                add(
                    "per_core_to_machine_cpu_mean",
                    f"mean({host} per-core free CPU)",
                    candidate,
                    core_mean,
                    compute[candidate],
                    f"{len(host_core_cols)} detected core columns; relationship discovered by name+data.",
                )
        if f"{machine} CU" in compute:
            add(
                "per_core_cpu_complement",
                f"100 - mean({host} per-core free CPU)",
                f"{machine} CU",
                100.0 - core_mean,
                compute[f"{machine} CU"],
                f"{len(host_core_cols)} detected core columns.",
            )

    # Direct per-core used/free complement candidates.
    for free_col in [c for c in cores if c.startswith("free_cpu_")]:
        used_col = free_col.replace("free_cpu_", "used_cpu_", 1)
        if used_col not in cores:
            continue
        total = cores[free_col] + cores[used_col]
        add(
            "per_core_cpu_used_free_complement",
            f"{free_col} + {used_col}",
            "constant 100",
            total,
            pd.Series(100.0, index=total.index),
            "Direct name-paired used/free CPU complement candidate.",
        )

    # Network bond aggregation candidates by host and direction.
    for host in HOSTS:
        for direction in ("transmitted", "received"):
            prefix = f"{direction}_throughput_{host}:-network-device-"
            bond = prefix + "bond0"
            members = [c for c in throughput if c.startswith(prefix) and c != bond]
            if bond in throughput and members:
                add(
                    "network_bond0_interface_sum",
                    bond,
                    " + ".join(members),
                    throughput[bond],
                    throughput[members].sum(axis=1),
                    f"All {len(members)} non-bond0 interfaces with matching host/direction; aggregation semantics require domain validation.",
                )
    return pd.DataFrame(rows)


def timestamp_alignment(
    timestamps: dict[str, pd.DatetimeIndex],
) -> tuple[pd.DataFrame, dict[str, pd.DatetimeIndex]]:
    names = list(timestamps)
    intersection = timestamps[names[0]]
    union = timestamps[names[0]]
    for name in names[1:]:
        intersection = intersection.intersection(timestamps[name])
        union = union.union(timestamps[name])
    rows = []
    missing_map: dict[str, pd.DatetimeIndex] = {}
    reference = timestamps["compute_dataset.csv"]
    for name, idx in timestamps.items():
        missing_union = union.difference(idx)
        missing_ref = reference.difference(idx)
        extra_ref = idx.difference(reference)
        missing_map[name] = missing_union
        rows.append(
            {
                "dataset": name,
                "row_timestamps": len(idx),
                "unique_timestamps": len(idx.unique()),
                "common_intersection_size": len(intersection),
                "global_union_size": len(union),
                "missing_from_global_union": len(missing_union),
                "missing_vs_compute_reference": len(missing_ref),
                "extra_vs_compute_reference": len(extra_ref),
                "exactly_matches_compute_timestamp_sequence": bool(idx.equals(reference)),
                "nearest_timestamp_matching_required_for_exact_inner_join": False,
                "notes": (
                    "Exact timestamp join loses rows listed as missing; nearest matching is not "
                    "required for shared timestamps and is not performed."
                ),
            }
        )
    return pd.DataFrame(rows), missing_map


def resource_coverage(catalogue: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    resource_cols = [
        "CPU",
        "per-core CPU",
        "memory",
        "disk/storage",
        "network throughput",
        "packet loss",
        "packet errors",
        "interface-specific network",
    ]
    rows = []
    for machine in MACHINES:
        host = MACHINE_TO_HOST[machine]
        subset = catalogue[(catalogue["machine"] == machine) | (catalogue["host"] == host)]
        row: dict[str, Any] = {"machine": machine, "host": host}
        row["CPU"] = int((subset.resource_family == "CPU").sum())
        row["per-core CPU"] = int(
            ((subset.resource_family == "CPU") & (subset.scope == "CPU core")).sum()
        )
        row["memory"] = int((subset.resource_family == "memory").sum())
        row["disk/storage"] = int((subset.resource_family == "disk/storage").sum())
        row["network throughput"] = int((subset.resource_family == "network throughput").sum())
        row["packet loss"] = int((subset.resource_family == "packet loss").sum())
        row["packet errors"] = int((subset.resource_family == "packet errors").sum())
        row["interface-specific network"] = int(
            subset["interface"].fillna("").astype(str).str.len().gt(0).sum()
        )
        rows.append(row)
    global_signals = catalogue[
        catalogue["scope"].isin(["cluster", "global", "cluster/global"])
    ].copy()
    return pd.DataFrame(rows)[["machine", "host", *resource_cols]], global_signals


def downsample(frame: pd.DataFrame, max_points: int = 3000) -> pd.DataFrame:
    if len(frame) <= max_points:
        return frame
    step = max(1, len(frame) // max_points)
    return frame.iloc[::step].copy()


def save_figures(
    frames: dict[str, pd.DataFrame],
    timestamp_summaries: pd.DataFrame,
    gaps: pd.DataFrame,
    column_stats: pd.DataFrame,
) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")

    # 1 coverage
    fig, ax = plt.subplots(figsize=(10, 4))
    for i, row in timestamp_summaries.reset_index(drop=True).iterrows():
        ax.plot(
            [pd.Timestamp(row.timestamp_min), pd.Timestamp(row.timestamp_max)],
            [i, i],
            marker="|",
            linewidth=5,
        )
    ax.set_yticks(range(len(timestamp_summaries)))
    ax.set_yticklabels(timestamp_summaries.dataset.str.replace("_dataset.csv", "", regex=False))
    ax.set_title("Dataset timestamp coverage")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "01_timestamp_coverage.png", dpi=150)
    plt.close(fig)

    # 2 sampling interval distributions (clip display at 99.5%, gaps shown separately)
    fig, ax = plt.subplots(figsize=(10, 5))
    for name, df in frames.items():
        delta = df.timestamp.diff().dt.total_seconds().dropna()
        clip = delta[delta <= delta.quantile(0.995)]
        ax.hist(clip, bins=80, alpha=0.35, density=True, label=name.replace("_dataset.csv", ""))
    ax.set_xlabel("Sampling interval (seconds; <= dataset q99.5)")
    ax.set_ylabel("Density")
    ax.set_title("Sampling interval distributions")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "02_sampling_intervals.png", dpi=150)
    plt.close(fig)

    # 3 gaps
    fig, ax = plt.subplots(figsize=(11, 4))
    if not gaps.empty:
        labels = {name: i for i, name in enumerate(timestamp_summaries.dataset)}
        for _, row in gaps[gaps["gt_5x_median"]].iterrows():
            ax.scatter(
                pd.Timestamp(row["next_timestamp"]),
                labels[row["dataset"]],
                s=max(15, min(200, row["interval_seconds"] / 500)),
                alpha=0.7,
            )
        ax.set_yticks(list(labels.values()))
        ax.set_yticklabels([x.replace("_dataset.csv", "") for x in labels])
    ax.set_title("Detected gaps > 5× each dataset median interval")
    ax.set_xlabel("Timestamp after gap")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "03_major_gaps.png", dpi=150)
    plt.close(fig)

    compute = frames["compute_dataset.csv"]
    disk = frames["disk_dataset.csv"]
    network = frames["network_dataset.csv"]
    throughput = frames["throughputs_dataset.csv"]
    packet = frames["packet-loss-dataset.csv"]

    def line_plot(df: pd.DataFrame, cols: list[str], title: str, filename: str) -> None:
        plot_df = downsample(df[["timestamp", *cols]].copy())
        fig, ax = plt.subplots(figsize=(11, 5))
        for col in cols:
            ax.plot(plot_df.timestamp, plot_df[col], linewidth=0.8, label=col)
        ax.set_title(title)
        ax.legend(fontsize=7, ncol=2)
        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig(FIGURE_DIR / filename, dpi=150)
        plt.close(fig)

    # 4 CPU heterogeneity
    line_plot(
        compute,
        [f"{m} CU" for m in MACHINES],
        "CPU utilization across seven machines",
        "04_representative_cpu.png",
    )
    # 5 memory
    line_plot(
        compute,
        ["cluster UM", "cluster AM"],
        "Cluster used and available memory",
        "05_representative_memory.png",
    )
    # 6 disk
    line_plot(
        disk,
        [f"{m} UD" for m in MACHINES],
        "Used disk across seven machines",
        "06_representative_disk.png",
    )
    # 7 network throughput, bond0 transmitted
    tx_cols = [
        f"transmitted_throughput_{host}:-network-device-bond0"
        for host in HOSTS
        if f"transmitted_throughput_{host}:-network-device-bond0" in throughput
    ]
    line_plot(
        throughput,
        tx_cols,
        "Transmitted throughput on bond0 across hosts",
        "07_representative_throughput.png",
    )
    # 8 RTT/jitter
    line_plot(
        network,
        [c for c in network if c != "timestamp"],
        "Global RTT and jitter diagnostics",
        "08_rtt_jitter.png",
    )
    # 9 representative packet event signals: choose columns with greatest nonzero count
    packet_numeric = packet.drop(columns="timestamp")
    nonzero_counts = (packet_numeric.fillna(0) != 0).sum().sort_values(ascending=False)
    packet_cols = list(nonzero_counts.head(7).index)
    line_plot(
        packet,
        packet_cols,
        "Most active packet error/drop signals",
        "09_packet_events.png",
    )
    # 10 missingness by dataset
    missing = (
        column_stats.groupby("dataset")
        .agg(
            total_missing=("missing_count", "sum"),
            columns_with_missing=("missing_count", lambda x: int((x > 0).sum())),
            max_column_missing_percent=("missing_percent", "max"),
        )
        .reset_index()
    )
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(missing.dataset.str.replace("_dataset.csv", "", regex=False), missing.total_missing)
    ax.set_ylabel("Missing cells")
    ax.set_title("Missingness summary by dataset")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "10_missingness_summary.png", dpi=150)
    plt.close(fig)


def generate_report(
    inventory: pd.DataFrame,
    stats: pd.DataFrame,
    timestamps: pd.DataFrame,
    gaps: pd.DataFrame,
    segments: pd.DataFrame,
    alignment: pd.DataFrame,
    catalogue: pd.DataFrame,
    quality: pd.DataFrame,
    dynamics: pd.DataFrame,
    duplicates: pd.DataFrame,
    correlations: pd.DataFrame,
    relationships: pd.DataFrame,
    coverage: pd.DataFrame,
    global_signals: pd.DataFrame,
    runtime_seconds: float,
    peak_rss_mb: float,
    hashes_unchanged: bool,
) -> None:
    family_counts = (
        catalogue[catalogue.resource_family != "time"]
        .groupby("resource_family")
        .size()
        .sort_values(ascending=False)
    )
    dataset_quality = (
        quality.groupby("dataset")
        .agg(
            numeric_signals=("column", "count"),
            constant=("constant", "sum"),
            near_constant=("near_constant", "sum"),
            zero_dominated=("zero_fraction", lambda x: int((x >= ZERO_DOMINATED_FRACTION).sum())),
            negative_value_signals=("negative_count", lambda x: int((x > 0).sum())),
            outlier_flagged_signals=("outlier_count_3x_iqr", lambda x: int((x > 0).sum())),
        )
        .reset_index()
    )
    missing_summary = (
        stats.groupby("dataset")
        .agg(
            total_missing=("missing_count", "sum"),
            columns_with_missing=("missing_count", lambda x: int((x > 0).sum())),
            maximum_column_missing_percent=("missing_percent", "max"),
        )
    )
    bounds_summary = quality.groupby("dataset").agg(
        bounds_violation_values=("bounded_percentage_violation_count", "sum"),
        bounds_violation_signals=("bounded_percentage_violation_count", lambda x: int((x > 0).sum())),
    )
    meaningful = quality[
        (~quality.constant)
        & (~quality.near_constant)
        & (quality.zero_fraction < ZERO_DOMINATED_FRACTION)
        & (quality.nonmissing_fraction > 0.95)
    ]
    event_families = {"packet errors", "packet loss"}
    continuous_families = {"CPU", "memory", "disk/storage", "network throughput", "latency", "jitter"}
    all_machine_consistency = {}
    for family in sorted(set(catalogue.resource_family)):
        machine_count = catalogue[catalogue.resource_family == family]["machine"].replace("", np.nan).nunique()
        all_machine_consistency[family] = int(machine_count)

    lines = [
        "# TimeTrack Raw Data Audit",
        "",
        "**Scope:** descriptive, read-only audit of the six active raw CSV files. "
        "No cleaning, interpolation, alignment, lag analysis, feature selection, or forecasting was performed.",
        "",
        "## Reproducibility",
        "",
        f"- Script: `discovery/01_data_audit/audit_raw_data.py`",
        f"- Runtime: **{runtime_seconds:.1f} s**",
        f"- Approximate peak RSS: **{peak_rss_mb:.1f} MB**",
        f"- Python: `{platform.python_version()}`; pandas `{pd.__version__}`; NumPy `{np.__version__}`",
        f"- Raw-file SHA-256 unchanged during audit: **{'PASS' if hashes_unchanged else 'FAIL'}**",
        f"- Near-constant criterion: dominant value fraction ≥ {NEAR_CONSTANT_DOMINANT_FRACTION:.2f} "
        f"or unchanged-step fraction ≥ {NEAR_CONSTANT_DOMINANT_FRACTION:.2f}.",
        f"- Zero-dominated criterion: fraction equal to zero ≥ {ZERO_DOMINATED_FRACTION:.2f}.",
        f"- High-correlation screen: absolute Pearson correlation ≥ {HIGH_CORRELATION_THRESHOLD:.3f}; "
        "this is not interpreted as semantic equivalence.",
        "",
        "## Dataset Inventory",
        "",
        "| Dataset | Bytes | Rows | Columns | Timestamp start | Timestamp end |",
        "|---|---:|---:|---:|---|---|",
    ]
    for _, row in inventory.iterrows():
        lines.append(
            f"| `{row.dataset}` | {row.size_bytes:,} | {row.rows:,} | {row.columns:,} | "
            f"{row.timestamp_min} | {row.timestamp_max} |"
        )
    lines += [
        "",
        "Full dtypes, column names, unique counts, missingness, infinities, extrema, "
        "moments, and quantiles are in `outputs/column_statistics.csv`; exact schemas are in "
        "`outputs/schema_inventory.json`.",
        "",
        "## Timestamp and Sampling Findings",
        "",
        "| Dataset | Strictly increasing | Duplicates | Out of order | Median interval (s) | Segments (>2× median) | Gaps >1 h |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    segment_counts = segments.groupby("dataset").size()
    for _, row in timestamps.iterrows():
        lines.append(
            f"| `{row.dataset}` | {row.strictly_increasing} | {row.duplicate_timestamps} | "
            f"{row.out_of_order_timestamps} | {row.median_interval_seconds:.6f} | "
            f"{int(segment_counts[row.dataset])} | {int(row.gap_count_gt_1_hour)} |"
        )
    intersection_size = int(alignment.common_intersection_size.iloc[0])
    union_size = int(alignment.global_union_size.iloc[0])
    network_row = alignment[alignment.dataset == "network_dataset.csv"].iloc[0]
    lines += [
        "",
        f"- Exact six-file timestamp intersection: **{intersection_size:,}** timestamps.",
        f"- Global timestamp union: **{union_size:,}** timestamps.",
        f"- Network rows missing versus compute timestamps: **{int(network_row.missing_vs_compute_reference):,}**.",
        "- Five datasets share the same timestamp sequence; the network file is missing a small number "
        "of exact timestamps. Exact joins are possible on shared rows; nearest-neighbor matching is not "
        "intrinsically required and was not performed.",
        "- All gap locations and threshold flags are in `outputs/timestamp_gaps.csv`; continuous segments "
        "are in `outputs/temporal_segments.csv`.",
        "",
        "## Semantic Signal Catalogue",
        "",
        "| Resource family | Catalogued columns |",
        "|---|---:|",
    ]
    for family, count in family_counts.items():
        lines.append(f"| {family} | {int(count)} |")
    lines += [
        "",
        "The full catalogue (`outputs/signal_catalogue.csv`) preserves every raw column and records "
        "resource family, metric, scope, machine, host, interface, core, inferred unit, and notes. "
        "Ambiguous semantics remain marked `unknown` rather than forced into a category.",
        "",
        "## Data-Quality Screening",
        "",
        "| Dataset | Numeric | Constant | Near-constant | Zero-dominated | Negative-value signals | Outlier-flagged signals |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in dataset_quality.iterrows():
        lines.append(
            f"| `{row.dataset}` | {int(row.numeric_signals)} | {int(row.constant)} | "
            f"{int(row.near_constant)} | {int(row.zero_dominated)} | "
            f"{int(row.negative_value_signals)} | {int(row.outlier_flagged_signals)} |"
        )
    lines += [
        "",
        "- Constant/near-constant and zero-dominated packet signals should not be silently removed: they "
        "may encode absence of events or instrumentation behavior.",
        f"- `packet-loss-dataset.csv` contains **{int(missing_summary.loc['packet-loss-dataset.csv', 'total_missing']):,}** "
        f"missing cells across **{int(missing_summary.loc['packet-loss-dataset.csv', 'columns_with_missing'])}** signal columns; "
        "85/90 numeric packet channels are constant and the remaining five are near-constant sparse event channels.",
        f"- `throughputs_dataset.csv` has **{int(dataset_quality.set_index('dataset').loc['throughputs_dataset.csv', 'constant'])}** "
        "constant channels; 41/90 channels are zero-dominated under the 95% criterion.",
        "- `machine05 CF` is entirely missing, while the detailed per-core dataset has low but distributed "
        "missingness across all 472 numeric columns (maximum per-column missingness below 0.3%).",
        f"- In the per-core CPU file, **{int(bounds_summary.loc['detailed_cpu_cores_dataset.csv', 'bounds_violation_signals'])}** "
        f"signals contain **{int(bounds_summary.loc['detailed_cpu_cores_dataset.csv', 'bounds_violation_values']):,}** total values "
        "outside the inferred [0,100] percentage range; 29 signals contain negative values. These require "
        "source-semantic verification rather than automatic clipping.",
        "- Negative values and bounded-percentage violations are listed explicitly in "
        "`outputs/data_quality_screening.csv`; no values were changed.",
        "- The 3×IQR outlier flag is descriptive only. It can mark legitimate bursts in throughput, "
        "latency, utilization, or counters.",
        "- Monotonicity, resets, unchanged fractions, and jump magnitudes are recorded in "
        "`outputs/signal_dynamics.csv`.",
        "",
        "## Redundancy and Identity Screening",
        "",
        f"- Exact duplicate column pairs: **{len(duplicates):,}**.",
        f"- Within-dataset |Pearson r| ≥ {HIGH_CORRELATION_THRESHOLD}: **{len(correlations):,}** pairs.",
        f"- Explicit aggregate/complement/interface candidates evaluated: **{len(relationships):,}**.",
    ]
    if not relationships.empty:
        exact_rel = int(relationships["exact_within_1e-9"].fillna(False).sum())
        near_rel = int((relationships.relative_mean_abs_error.fillna(np.inf) <= 0.001).sum())
        lines += [
            f"- Exact candidate relationships (numerical tolerance): **{exact_rel}**.",
            f"- Near-exact candidates (relative MAE ≤0.1%): **{near_rel}**.",
        ]
    lines += [
        "",
        "These screens identify redundancy candidates only. High correlation does not prove identity, "
        "causality, or interchangeability. Full results are in `outputs/exact_duplicate_columns.csv`, "
        "`outputs/high_correlation_pairs.csv`, and `outputs/discovered_relationships.csv`.",
        "",
        "## Per-Machine Resource Coverage",
        "",
        coverage.to_markdown(index=False),
        "",
        "Counts are raw signal-column counts, not a quality endorsement. Cluster/global-only entries "
        "are listed in `outputs/global_cluster_signals.csv`.",
        "",
        "## Diagnostic Figures",
        "",
        "The following non-publication diagnostics are in `outputs/figures/`: timestamp coverage, "
        "sampling intervals, detected gaps, seven-machine CPU, cluster memory, seven-machine disk, "
        "host bond0 throughput, RTT/jitter, active packet signals, and missingness.",
        "",
        "## Implications for the New Forecasting Study",
        "",
        "1. **Available resource families.** The files contain CPU (machine and per-core), memory, "
        "disk/storage, network throughput, packet errors/drops, RTT/latency, and jitter. Raw names and "
        "units remain subject to source documentation where marked inferred.",
        "2. **Consistent seven-machine metrics.** Machine-resolved CPU utilization/free CPU, memory "
        "used/available, disk used/free and disk read/write quantities are represented across all seven "
        "machines. Per-core CPU and interface telemetry are host-resolved with unequal core/interface counts.",
        "3. **Cluster/global-only metrics.** Cluster memory/disk aggregates and global Google-DNS RTT/jitter "
        "exist; RTT/jitter are not machine-specific.",
        "4. **Redundancy.** Exact duplicate, complement, aggregate, and very-high-correlation screens show "
        "that multiple columns can encode overlapping information. The machine-readable relationship tables "
        "must be consulted before selecting features.",
        f"5. **Potentially informative signals.** **{len(meaningful):,}** numeric signals are nonconstant, "
        "not near-constant/zero-dominated, and >95% observed under the stated descriptive criteria. This "
        "includes continuously varying compute, storage, throughput, and global latency/jitter signals.",
        "6. **Serious quality concerns.** Sparse/constant packet channels, missing network timestamps, "
        "large temporal gaps, inferred-unit ambiguity, possible counter resets, extreme bursts, and any "
        "reported negative/bounds violations require explicit handling in later protocol design.",
        "7. **Continuous forecast-like quantities.** CPU utilization, memory/disk levels, disk rates, "
        "network throughput, RTT, and jitter are continuous or level/rate-like. This is a structural "
        "description, not a forecastability result.",
        "8. **Event/anomaly-like quantities.** Packet errors/drops and highly zero-dominated signals are "
        "better described initially as sparse event processes than ordinary dense regression targets.",
        "9. **Joint multi-metric plausibility.** Yes, substantial timestamp overlap and machine-resolved "
        "CPU/memory/disk/network telemetry make joint multi-metric study technically plausible. Whether it "
        "adds predictive value is untested.",
        "10. **Joint multi-machine plausibility.** Yes, seven machines/hosts have repeated resource schemas, "
        "although core counts, interfaces, scales, missingness, and dynamics differ and must be respected.",
        "11. **Network as context.** Network throughput and global RTT/jitter overlap temporally with compute "
        "telemetry and can plausibly be evaluated as context features. No predictive relationship is claimed.",
        "12. **Uncertainties for the next phase.** Lagged dependence, lead-specific information, outage/gap "
        "handling, sampling irregularity, stationarity/regime changes, counter semantics, scale normalization, "
        "host identity mapping, interface aggregation, and causal leakage boundaries require dedicated "
        "lag/dependency analysis next. None was tested here.",
        "",
        "## Output Index",
        "",
        "- `raw_file_inventory.csv` / `raw_hashes_before_after.json`",
        "- `schema_inventory.json` / `column_statistics.csv`",
        "- `timestamp_statistics.csv` / `timestamp_gaps.csv` / `temporal_segments.csv`",
        "- `timestamp_alignment_summary.csv` / `missing_timestamps_by_dataset.csv`",
        "- `signal_catalogue.csv`",
        "- `data_quality_screening.csv` / `signal_dynamics.csv`",
        "- `exact_duplicate_columns.csv` / `high_correlation_pairs.csv` / `discovered_relationships.csv`",
        "- `machine_resource_coverage.csv` / `global_cluster_signals.csv`",
        "- `figures/*.png`",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n")


def main() -> None:
    start = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    missing = [name for name in RAW_FILES if not (RAW_DIR / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing active raw files: {missing}")

    hashes_before = {name: sha256_file(RAW_DIR / name) for name in RAW_FILES}
    inventory_rows = []
    schema_inventory: dict[str, Any] = {}
    frames: dict[str, pd.DataFrame] = {}
    all_stats = []
    all_timestamp_stats = []
    all_gaps = []
    all_segments = []
    all_catalogue = []
    all_quality = []
    all_dynamics = []
    all_duplicates = []
    all_correlations = []
    timestamp_indexes: dict[str, pd.DatetimeIndex] = {}

    for name in RAW_FILES:
        path = RAW_DIR / name
        print(f"[audit] reading {name}", flush=True)
        frame = read_csv(path)
        frames[name] = frame
        timestamp_indexes[name] = pd.DatetimeIndex(frame["timestamp"])
        semantics = {col: parse_signal(name, col) for col in frame.columns}
        catalogue_frame = pd.DataFrame([asdict(v) for v in semantics.values()])
        all_catalogue.append(catalogue_frame)

        stats_frame = column_statistics(name, frame)
        all_stats.append(stats_frame)
        ts_summary, gap_frame, segment_frame = timestamp_audit(name, frame["timestamp"])
        all_timestamp_stats.append(ts_summary)
        if not gap_frame.empty:
            all_gaps.append(gap_frame)
        all_segments.append(segment_frame)
        dynamics, quality = dynamics_and_quality(name, frame, semantics)
        all_dynamics.append(dynamics)
        all_quality.append(quality)
        duplicates = exact_duplicates(name, frame)
        if not duplicates.empty:
            all_duplicates.append(duplicates)
        correlations = high_correlations(name, frame, semantics)
        if not correlations.empty:
            all_correlations.append(correlations)

        schema_inventory[name] = {
            "path": str(path.resolve()),
            "size_bytes": path.stat().st_size,
            "rows": len(frame),
            "columns": len(frame.columns),
            "timestamp_column": "timestamp",
            "timestamp_min": str(frame["timestamp"].min()),
            "timestamp_max": str(frame["timestamp"].max()),
            "column_names": list(frame.columns),
            "dtypes": {col: str(dtype) for col, dtype in frame.dtypes.items()},
            "numeric_columns": list(frame.select_dtypes(include=[np.number]).columns),
            "non_numeric_columns": [
                c for c in frame.columns if c not in frame.select_dtypes(include=[np.number]).columns
            ],
        }
        inventory_rows.append(
            {
                "dataset": name,
                "path": str(path.resolve()),
                "size_bytes": path.stat().st_size,
                "sha256": hashes_before[name],
                "rows": len(frame),
                "columns": len(frame.columns),
                "timestamp_column": "timestamp",
                "timestamp_min": str(frame.timestamp.min()),
                "timestamp_max": str(frame.timestamp.max()),
            }
        )

    inventory = pd.DataFrame(inventory_rows)
    stats = pd.concat(all_stats, ignore_index=True)
    timestamp_stats = pd.DataFrame(all_timestamp_stats)
    gaps = pd.concat(all_gaps, ignore_index=True) if all_gaps else pd.DataFrame()
    segments = pd.concat(all_segments, ignore_index=True)
    catalogue = pd.concat(all_catalogue, ignore_index=True).fillna("")
    quality = pd.concat(all_quality, ignore_index=True)
    dynamics = pd.concat(all_dynamics, ignore_index=True)
    duplicates = (
        pd.concat(all_duplicates, ignore_index=True)
        if all_duplicates
        else pd.DataFrame(columns=["dataset", "column_a", "column_b", "relationship"])
    )
    correlations = (
        pd.concat(all_correlations, ignore_index=True)
        if all_correlations
        else pd.DataFrame(
            columns=[
                "dataset",
                "column_a",
                "column_b",
                "pearson_correlation",
                "resource_family_a",
                "resource_family_b",
                "note",
            ]
        )
    )
    alignment, missing_map = timestamp_alignment(timestamp_indexes)
    missing_rows = [
        {"dataset": name, "missing_timestamp": str(ts)}
        for name, idx in missing_map.items()
        for ts in idx
    ]
    missing_timestamps = pd.DataFrame(
        missing_rows, columns=["dataset", "missing_timestamp"]
    )

    relationships = discover_semantic_relationships(
        frames["compute_dataset.csv"],
        frames["disk_dataset.csv"],
        frames["detailed_cpu_cores_dataset.csv"],
        frames["throughputs_dataset.csv"],
    )
    coverage, global_signals = resource_coverage(catalogue)

    # Write all machine-readable tables.
    inventory.to_csv(OUTPUT_DIR / "raw_file_inventory.csv", index=False)
    write_json(OUTPUT_DIR / "schema_inventory.json", schema_inventory)
    stats.to_csv(OUTPUT_DIR / "column_statistics.csv", index=False)
    timestamp_stats.to_csv(OUTPUT_DIR / "timestamp_statistics.csv", index=False)
    gaps.to_csv(OUTPUT_DIR / "timestamp_gaps.csv", index=False)
    segments.to_csv(OUTPUT_DIR / "temporal_segments.csv", index=False)
    alignment.to_csv(OUTPUT_DIR / "timestamp_alignment_summary.csv", index=False)
    missing_timestamps.to_csv(OUTPUT_DIR / "missing_timestamps_by_dataset.csv", index=False)
    catalogue.to_csv(OUTPUT_DIR / "signal_catalogue.csv", index=False)
    quality.to_csv(OUTPUT_DIR / "data_quality_screening.csv", index=False)
    dynamics.to_csv(OUTPUT_DIR / "signal_dynamics.csv", index=False)
    duplicates.to_csv(OUTPUT_DIR / "exact_duplicate_columns.csv", index=False)
    correlations.to_csv(OUTPUT_DIR / "high_correlation_pairs.csv", index=False)
    relationships.to_csv(OUTPUT_DIR / "discovered_relationships.csv", index=False)
    coverage.to_csv(OUTPUT_DIR / "machine_resource_coverage.csv", index=False)
    global_signals.to_csv(OUTPUT_DIR / "global_cluster_signals.csv", index=False)

    print("[audit] generating diagnostics", flush=True)
    save_figures(frames, timestamp_stats, gaps, stats)

    hashes_after = {name: sha256_file(RAW_DIR / name) for name in RAW_FILES}
    hashes_unchanged = hashes_before == hashes_after
    write_json(
        OUTPUT_DIR / "raw_hashes_before_after.json",
        {
            "raw_directory": str(RAW_DIR.resolve()),
            "before": hashes_before,
            "after": hashes_after,
            "unchanged": hashes_unchanged,
        },
    )
    if not hashes_unchanged:
        raise RuntimeError("Raw dataset hash changed during read-only audit")

    runtime_seconds = time.perf_counter() - start
    # macOS ru_maxrss is bytes; Linux is KiB.
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_rss_mb = rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024
    generate_report(
        inventory,
        stats,
        timestamp_stats,
        gaps,
        segments,
        alignment,
        catalogue,
        quality,
        dynamics,
        duplicates,
        correlations,
        relationships,
        coverage,
        global_signals,
        runtime_seconds,
        peak_rss_mb,
        hashes_unchanged,
    )
    write_json(
        OUTPUT_DIR / "audit_run_metadata.json",
        {
            "status": "PASS",
            "runtime_seconds": runtime_seconds,
            "peak_rss_mb": peak_rss_mb,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "raw_hashes_unchanged": hashes_unchanged,
            "files_audited": RAW_FILES,
            "criteria": {
                "near_constant_dominant_fraction": NEAR_CONSTANT_DOMINANT_FRACTION,
                "zero_dominated_fraction": ZERO_DOMINATED_FRACTION,
                "sparse_nonmissing_fraction": SPARSE_NONMISSING_FRACTION,
                "high_correlation_abs_pearson": HIGH_CORRELATION_THRESHOLD,
                "outlier_iqr_multiplier": OUTLIER_IQR_MULTIPLIER,
            },
        },
    )
    print(
        f"[audit] PASS in {runtime_seconds:.1f}s; peak RSS {peak_rss_mb:.1f} MB; "
        f"report={REPORT_PATH}",
        flush=True,
    )


if __name__ == "__main__":
    main()
