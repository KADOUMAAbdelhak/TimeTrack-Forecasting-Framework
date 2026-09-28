from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import RESOURCE_ORDER
from src.cleaning import clean_and_segment
from src.ingestion import RawVM, archive_path, config, parse_timestamp_seconds, read_vm, required_columns, selected_ids, sha256_file


def test_resource_order():
    assert RESOURCE_ORDER == ("CPU", "THROUGHPUT", "MEMORY", "DISK_WRITE")


def test_selected_vm_counts_and_first_ids():
    cohorts = selected_ids()
    assert {key: len(value) for key, value in cohorts.items()} == {
        "GWA-T-12_Bitbrains_Rnd": 35,
        "GWA-T-12_Bitbrains_fastStorage": 35,
    }
    assert cohorts["GWA-T-12_Bitbrains_fastStorage"][0] == "697"
    assert cohorts["GWA-T-12_Bitbrains_Rnd"][0] == "99"


@pytest.mark.parametrize("environment", ["GWA-T-12_Bitbrains_fastStorage", "GWA-T-12_Bitbrains_Rnd"])
def test_archive_identity(environment):
    cfg = config()["archives"][environment]
    assert sha256_file(archive_path(environment)) == cfg["sha256"]


def test_timestamp_seconds_interpretation():
    series = pd.Series([1_600_000_000, 1_600_000_300])
    assert parse_timestamp_seconds(series).tolist() == [1_600_000_000, 1_600_000_300]
    with pytest.raises(RuntimeError):
        parse_timestamp_seconds(pd.Series([1_600_000_000_000]))


def test_exact_column_mapping():
    columns = [
        "Timestamp [ms]", "CPU usage [%]", "Memory usage [KB]",
        "Disk write throughput [KB/s]", "Network received throughput [KB/s]",
        "Network transmitted throughput [KB/s]",
    ]
    assert set(required_columns(columns)) == {
        "timestamp", "cpu", "memory", "disk_write", "network_received", "network_transmitted"
    }


def _raw(frame: pd.DataFrame) -> RawVM:
    return RawVM("synthetic", "1", frame, [], Path("synthetic.zip"), "0" * 64)


def base_raw_frame(n: int = 20) -> pd.DataFrame:
    return pd.DataFrame({
        "timestamp_seconds": 1_600_000_000 + np.arange(n) * 300,
        "CPU": np.linspace(1, 2, n),
        "MEMORY": np.linspace(10, 20, n),
        "DISK_WRITE": np.linspace(1, 3, n),
        "network_received": np.linspace(2, 4, n),
        "network_transmitted": np.linspace(3, 5, n),
        "raw_member": "x.csv",
    })


def test_duplicate_rejection():
    frame = base_raw_frame()
    frame.loc[1, "timestamp_seconds"] = frame.loc[0, "timestamp_seconds"]
    with pytest.raises(RuntimeError, match="Duplicate"):
        clean_and_segment(_raw(frame))


def test_invalid_row_rejected_not_clipped_or_imputed():
    frame = base_raw_frame()
    frame.loc[5, "CPU"] = 101
    clean = clean_and_segment(_raw(frame))
    assert clean.quality["invalid_rows"] == 1
    assert len(clean.frame) == len(frame) - 1
    assert 101 not in clean.frame.CPU.values


def test_invalid_row_creates_discontinuity():
    frame = base_raw_frame()
    frame.loc[5, "MEMORY"] = -1
    clean = clean_and_segment(_raw(frame))
    assert clean.quality["segment_count"] == 2
    assert clean.quality["largest_valid_gap_seconds"] == 600


def test_no_interpolation_or_timestamp_synthesis():
    frame = base_raw_frame()
    frame.loc[5, "DISK_WRITE"] = np.nan
    clean = clean_and_segment(_raw(frame))
    assert set(clean.frame.timestamp_seconds) == set(frame.timestamp_seconds) - {frame.loc[5, "timestamp_seconds"]}


def test_throughput_total_construction():
    frame = base_raw_frame()
    clean = clean_and_segment(_raw(frame))
    expected = frame.network_received + frame.network_transmitted
    assert np.allclose(clean.frame.THROUGHPUT, expected)


@pytest.mark.parametrize("environment,vm_id", [
    ("GWA-T-12_Bitbrains_fastStorage", "697"),
    ("GWA-T-12_Bitbrains_Rnd", "99"),
])
def test_real_selected_pilot_ingestion_and_cadence(environment, vm_id):
    clean = clean_and_segment(read_vm(environment, vm_id))
    assert clean.quality["duplicate_timestamps"] == 0
    assert clean.quality["valid_rows"] > 0
    assert all(segment["median_cadence_seconds"] == 300 for segment in clean.segments if segment["observations"] > 1)
    assert list(clean.frame.columns[:5]) == ["timestamp_seconds", *RESOURCE_ORDER]

