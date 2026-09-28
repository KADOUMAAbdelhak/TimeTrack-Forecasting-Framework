#!/usr/bin/env python3
"""Structural-only audit of official GWA archives; never trains or scores models."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/external/raw"
OUT = Path(__file__).resolve().parent
ARCHIVES = {
    "GWA-T-12_Bitbrains_fastStorage": RAW / "gwa_t_12_fastStorage.zip",
    "GWA-T-12_Bitbrains_Rnd": RAW / "gwa_t_12_rnd.zip",
    "GWA-T-13_Materna": RAW / "gwa_t_13_materna.zip",
}
URLS = {
    "GWA-T-12_Bitbrains_fastStorage": "https://atlarge-research.com/gwa-traces/gwa_t_12_fastStorage.zip",
    "GWA-T-12_Bitbrains_Rnd": "https://atlarge-research.com/gwa-traces/gwa_t_12_rnd.zip",
    "GWA-T-13_Materna": "https://atlarge-research.com/gwa-traces/gwa_t_13_materna.zip",
}
REQUIRED = ("cpu", "throughput", "memory", "disk_write")


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\t", " ").strip().lower())


def locate_columns(columns: list[str]) -> dict[str, str]:
    lookup = {normalized(column): column for column in columns}
    def find(*parts: str) -> str:
        candidates = [original for key, original in lookup.items() if all(part in key for part in parts)]
        if len(candidates) != 1:
            raise RuntimeError(f"Expected one column containing {parts}, found {candidates}")
        return candidates[0]
    return {
        "timestamp": find("timestamp"),
        "cpu": find("cpu usage", "[%]"),
        "memory": find("memory usage", "[kb]"),
        "disk_write": find("disk write throughput"),
        "network_received": find("network received throughput"),
        "network_transmitted": find("network transmitted throughput"),
    }


def numeric(series: pd.Series) -> np.ndarray:
    """Parse both dot-decimal Bitbrains and comma-decimal Materna values."""
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce").to_numpy(float)


def timestamps_seconds(series: pd.Series) -> np.ndarray:
    """Normalize Unix values or Materna day-first datetimes to epoch seconds."""
    values = pd.to_numeric(series, errors="coerce").to_numpy(float)
    if np.isfinite(values).any():
        finite = values[np.isfinite(values)]
        if np.nanmedian(finite) > 1e11:
            values = values / 1000.0
        return values
    parsed = pd.to_datetime(series, format="%d.%m.%Y %H:%M:%S", utc=True, errors="coerce")
    result = parsed.to_numpy(dtype="datetime64[ns]").astype("int64").astype(float) / 1e9
    result[parsed.isna().to_numpy()] = np.nan
    return result


def partition_and_entity(archive_key: str, member: str) -> tuple[str, str]:
    stem = Path(member).stem
    if archive_key != "GWA-T-13_Materna":
        return archive_key, stem
    match = re.search(r"materna-trace-([123])", member, flags=re.IGNORECASE)
    suffix = match.group(1) if match else "unknown"
    return f"GWA-T-13_Materna_trace_{suffix}", stem


def longest_regular_run(times: np.ndarray, maximum_gap_seconds: float = 450.0) -> int:
    if len(times) == 0:
        return 0
    unique = np.unique(times)
    if len(unique) == 1:
        return 1
    gaps = np.diff(unique)
    breaks = np.flatnonzero(gaps > maximum_gap_seconds)
    bounds = np.r_[-1, breaks, len(gaps)]
    return int(np.max(np.diff(bounds)))


def scan_archives() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    datasets: dict[str, dict] = defaultdict(lambda: {
        "archive": "", "members": 0, "observations": 0,
        "missing": 0, "values": 0, "invalid": 0,
        "min_timestamp": np.inf, "max_timestamp": -np.inf,
        "resource_min": {resource: np.inf for resource in REQUIRED},
        "resource_max": {resource: -np.inf for resource in REQUIRED},
        "entities": defaultdict(lambda: {
            "times": [], "observations": 0, "finite": 0, "valid": 0, "invalid_values": 0,
            "resource_min": {resource: np.inf for resource in REQUIRED},
            "resource_max": {resource: -np.inf for resource in REQUIRED},
        }),
    })
    archive_rows = []
    for archive_key, archive in ARCHIVES.items():
        if not archive.exists():
            raise FileNotFoundError(archive)
        with zipfile.ZipFile(archive) as bundle:
            members = sorted(name for name in bundle.namelist() if name.lower().endswith(".csv"))
            top_levels = sorted({Path(name).parts[0] for name in bundle.namelist() if Path(name).parts})
            archive_rows.append({
                "dataset": archive_key,
                "official_url": URLS[archive_key],
                "download_date": "2026-09-28",
                "archive_filename": archive.name,
                "archive_byte_size": archive.stat().st_size,
                "sha256": sha256(archive),
                "csv_members": len(members),
                "uncompressed_bytes": sum(info.file_size for info in bundle.infolist()),
                "extraction_layout": ";".join(top_levels),
            })
            for member in members:
                with bundle.open(member) as stream:
                    frame = pd.read_csv(stream, sep=";", engine="c")
                frame.columns = [column.strip() for column in frame.columns]
                columns = locate_columns(list(frame.columns))
                partition, entity = partition_and_entity(archive_key, member)
                state = datasets[partition]
                state["archive"] = archive.name
                state["members"] += 1
                state["observations"] += len(frame)
                timestamp = timestamps_seconds(frame[columns["timestamp"]])
                finite_timestamp = timestamp[np.isfinite(timestamp)]
                values = {
                    "cpu": numeric(frame[columns["cpu"]]),
                    "memory": numeric(frame[columns["memory"]]),
                    "disk_write": numeric(frame[columns["disk_write"]]),
                }
                received = numeric(frame[columns["network_received"]])
                transmitted = numeric(frame[columns["network_transmitted"]])
                values["throughput"] = received + transmitted
                matrix = np.column_stack([values[resource] for resource in REQUIRED])
                finite = np.isfinite(matrix)
                state["missing"] += int((~finite).sum())
                state["values"] += int(finite.size)
                invalid = (matrix < 0) | ((np.arange(len(REQUIRED)) == 0)[None, :] & (matrix > 100))
                state["invalid"] += int((invalid & finite).sum())
                if finite_timestamp.size:
                    state["min_timestamp"] = min(state["min_timestamp"], float(finite_timestamp.min()))
                    state["max_timestamp"] = max(state["max_timestamp"], float(finite_timestamp.max()))
                entity_state = state["entities"][entity]
                entity_state["times"].append(timestamp[np.isfinite(timestamp)])
                entity_state["observations"] += len(frame)
                entity_state["finite"] += int(np.all(finite, axis=1).sum())
                entity_state["valid"] += int((np.all(finite, axis=1) & ~np.any(invalid, axis=1)).sum())
                entity_state["invalid_values"] += int((invalid & finite).sum())
                for resource, array in values.items():
                    clean = array[np.isfinite(array)]
                    if clean.size:
                        low, high = float(clean.min()), float(clean.max())
                        state["resource_min"][resource] = min(state["resource_min"][resource], low)
                        state["resource_max"][resource] = max(state["resource_max"][resource], high)
                        entity_state["resource_min"][resource] = min(entity_state["resource_min"][resource], low)
                        entity_state["resource_max"][resource] = max(entity_state["resource_max"][resource], high)

    rows = []
    entity_rows = []
    for dataset, state in sorted(datasets.items()):
        durations, intervals, longest_runs = [], [], []
        duplicates = 0
        eligible = 0
        constant_entities = 0
        for entity, entity_state in sorted(state["entities"].items()):
            times = np.sort(np.concatenate(entity_state["times"]))
            unique = np.unique(times)
            duplicates_entity = len(times) - len(unique)
            duplicates += duplicates_entity
            duration_days = float((unique[-1] - unique[0]) / 86400.0) if len(unique) > 1 else 0.0
            differences = np.diff(unique)
            positive = differences[differences > 0]
            median_interval = float(np.median(positive)) if positive.size else np.nan
            run = longest_regular_run(times)
            finite_fraction = entity_state["finite"] / max(entity_state["observations"], 1)
            valid_fraction = entity_state["valid"] / max(entity_state["observations"], 1)
            nonconstant = all(
                np.isfinite(entity_state["resource_min"][resource])
                and entity_state["resource_max"][resource] > entity_state["resource_min"][resource]
                for resource in REQUIRED
            )
            if not nonconstant:
                constant_entities += 1
            is_eligible = (
                duplicates_entity == 0
                and duration_days >= 14.0
                and valid_fraction >= 0.95
                and nonconstant
                and np.isfinite(median_interval)
                and abs(median_interval - 300.0) <= 1.0
                and run >= 2016
            )
            eligible += int(is_eligible)
            durations.append(duration_days)
            intervals.append(median_interval)
            longest_runs.append(run)
            entity_rows.append({
                "dataset": dataset, "entity": entity,
                "observations": entity_state["observations"],
                "duration_days": duration_days,
                "median_sampling_seconds": median_interval,
                "duplicate_timestamps": duplicates_entity,
                "four_resource_finite_fraction": finite_fraction,
                "four_resource_valid_fraction": valid_fraction,
                "invalid_required_values": entity_state["invalid_values"],
                "required_targets_nonconstant": nonconstant,
                "longest_regular_run_observations": run,
                "structurally_eligible": is_eligible,
            })
        intervals_array = np.asarray(intervals, float)
        finite_intervals = intervals_array[np.isfinite(intervals_array)]
        constant_targets = [
            resource for resource in REQUIRED
            if state["resource_max"][resource] == state["resource_min"][resource]
        ]
        rows.append({
            "dataset": dataset,
            "audit_basis": "OFFICIAL_RAW_ARCHIVE",
            "archive_filename": state["archive"],
            "entity_type": "VM",
            "number_entities": len(state["entities"]),
            "file_members": state["members"],
            "observation_count": state["observations"],
            "timestamp_type": (
                "day-first UTC-naive wall clock parsed as UTC"
                if "Materna" in dataset
                else "Unix epoch numeric; raw values resolve as seconds despite ms-labelled header"
            ),
            "start_timestamp_utc": pd.to_datetime(state["min_timestamp"], unit="s", utc=True).isoformat(),
            "end_timestamp_utc": pd.to_datetime(state["max_timestamp"], unit="s", utc=True).isoformat(),
            "median_entity_duration_days": float(np.median(durations)),
            "min_entity_duration_days": float(np.min(durations)),
            "max_entity_duration_days": float(np.max(durations)),
            "median_sampling_interval_seconds": float(np.median(finite_intervals)),
            "p10_entity_median_interval_seconds": float(np.quantile(finite_intervals, 0.1)),
            "p90_entity_median_interval_seconds": float(np.quantile(finite_intervals, 0.9)),
            "missing_required_values": state["missing"],
            "missing_required_fraction": state["missing"] / max(state["values"], 1),
            "duplicate_timestamps": duplicates,
            "invalid_required_values": state["invalid"],
            "constant_required_columns": ";".join(constant_targets) or "NONE",
            "entities_with_any_constant_required_target": constant_entities,
            "required_resource_families": "CPU;THROUGHPUT;MEMORY;DISK_WRITE",
            "four_resource_eligible_entities": eligible,
            "eligibility_rule": "no duplicates; >=14d span; >=95% physically valid four-resource rows; all targets nonconstant; 300+/-1s median interval; >=2016-observation <=450s-gap run",
            "structural_status": "RAW_AUDITED",
        })

    metadata_rows = [
        {
            "dataset": "Alibaba_cluster_trace_2018", "audit_basis": "OFFICIAL_METADATA_ONLY",
            "archive_filename": "NOT_DOWNLOADED_49GB", "entity_type": "machine/container",
            "number_entities": 4000, "file_members": 6, "observation_count": "",
            "timestamp_type": "relative seconds", "start_timestamp_utc": "", "end_timestamp_utc": "",
            "median_entity_duration_days": 8, "min_entity_duration_days": "", "max_entity_duration_days": "",
            "median_sampling_interval_seconds": "NOT_RAW_VERIFIED", "p10_entity_median_interval_seconds": "",
            "p90_entity_median_interval_seconds": "", "missing_required_values": "NOT_RAW_VERIFIED",
            "missing_required_fraction": "", "duplicate_timestamps": "NOT_RAW_VERIFIED",
            "invalid_required_values": "official schema documents -1/101 sentinels", "constant_required_columns": "NOT_RAW_VERIFIED",
            "entities_with_any_constant_required_target": "", "required_resource_families": "CPU;normalized network;memory utilization;disk I/O utilization",
            "four_resource_eligible_entities": 0, "eligibility_rule": "not applied: disk-write throughput absent",
            "structural_status": "METADATA_ONLY_STRUCTURALLY_INCOMPATIBLE",
        },
        {
            "dataset": "Google_cluster_trace_2019", "audit_basis": "OFFICIAL_METADATA_ONLY",
            "archive_filename": "NOT_DOWNLOADED_2.4TiB", "entity_type": "Borg task/machine", "number_entities": "8 cells",
            "file_members": "BigQuery tables", "observation_count": "", "timestamp_type": "relative time",
            "start_timestamp_utc": "", "end_timestamp_utc": "", "median_entity_duration_days": 31,
            "min_entity_duration_days": "", "max_entity_duration_days": "", "median_sampling_interval_seconds": 300,
            "p10_entity_median_interval_seconds": "", "p90_entity_median_interval_seconds": "",
            "missing_required_values": "NOT_RAW_VERIFIED", "missing_required_fraction": "",
            "duplicate_timestamps": "NOT_RAW_VERIFIED", "invalid_required_values": "NOT_RAW_VERIFIED",
            "constant_required_columns": "NOT_RAW_VERIFIED", "entities_with_any_constant_required_target": "",
            "required_resource_families": "CPU;memory/request usage;no comparable network/disk-write targets",
            "four_resource_eligible_entities": 0, "eligibility_rule": "not applied: required resource families absent",
            "structural_status": "METADATA_ONLY_STRUCTURALLY_INCOMPATIBLE",
        },
        {
            "dataset": "Azure_Public_VM_Traces_2017_2019", "audit_basis": "OFFICIAL_METADATA_ONLY",
            "archive_filename": "NOT_DOWNLOADED_78.5_TO_156GB", "entity_type": "VM",
            "number_entities": "2013767/2695548", "file_members": "128/198", "observation_count": "1.25B/1.94B",
            "timestamp_type": "relative seconds", "start_timestamp_utc": "", "end_timestamp_utc": "",
            "median_entity_duration_days": 30, "min_entity_duration_days": "", "max_entity_duration_days": "",
            "median_sampling_interval_seconds": 300, "p10_entity_median_interval_seconds": "",
            "p90_entity_median_interval_seconds": "", "missing_required_values": "NOT_RAW_VERIFIED",
            "missing_required_fraction": "", "duplicate_timestamps": "NOT_RAW_VERIFIED",
            "invalid_required_values": "NOT_RAW_VERIFIED", "constant_required_columns": "NOT_RAW_VERIFIED",
            "entities_with_any_constant_required_target": "", "required_resource_families": "CPU time series only; memory is static VM capacity",
            "four_resource_eligible_entities": 0, "eligibility_rule": "not applied: throughput, active memory, and disk-write absent",
            "structural_status": "METADATA_ONLY_STRUCTURALLY_INCOMPATIBLE",
        },
    ]
    rows.extend(metadata_rows)
    structural = pd.DataFrame(rows)
    entities = pd.DataFrame(entity_rows)
    archives = pd.DataFrame(archive_rows)
    return structural, entities, archives


def materna_overlap(entities: pd.DataFrame) -> pd.DataFrame:
    groups = {
        dataset: set(group.entity.astype(str))
        for dataset, group in entities[entities.dataset.str.contains("Materna")].groupby("dataset")
    }
    rows = []
    for left in sorted(groups):
        for right in sorted(groups):
            if left >= right:
                continue
            intersection = len(groups[left] & groups[right])
            union = len(groups[left] | groups[right])
            rows.append({
                "trace_a": left, "trace_b": right,
                "entities_a": len(groups[left]), "entities_b": len(groups[right]),
                "shared_entity_ids": intersection,
                "jaccard_overlap": intersection / union if union else np.nan,
            })
    if len(groups) == 3:
        shared_all = len(set.intersection(*groups.values()))
        rows.append({
            "trace_a": "ALL_THREE", "trace_b": "ALL_THREE",
            "entities_a": sum(len(value) for value in groups.values()), "entities_b": "",
            "shared_entity_ids": shared_all, "jaccard_overlap": "",
        })
    return pd.DataFrame(rows)


def main() -> None:
    structural, entities, archives = scan_archives()
    structural.to_csv(OUT / "EXTERNAL_DATASET_STRUCTURAL_AUDIT.csv", index=False)
    entities.to_csv(OUT / "ENTITY_STRUCTURAL_ELIGIBILITY.csv", index=False)
    archives.to_csv(OUT / "RAW_ARCHIVE_MANIFEST.csv", index=False)
    materna_overlap(entities).to_csv(OUT / "MATERNA_VM_OVERLAP.csv", index=False)
    result = {
        "status": "PASS",
        "forecasting_models_trained": 0,
        "predictive_performance_inspected": False,
        "raw_archives": len(archives),
        "raw_dataset_partitions": int(structural.audit_basis.eq("OFFICIAL_RAW_ARCHIVE").sum()),
        "entity_records": len(entities),
    }
    (OUT / "STRUCTURAL_AUDIT_VALIDATION.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
