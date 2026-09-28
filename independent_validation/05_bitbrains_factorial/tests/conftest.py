from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]
sys.path.insert(0, str(BASE))


@pytest.fixture
def synthetic_panel() -> pd.DataFrame:
    n = 4000
    index = np.arange(n, dtype=float)
    return pd.DataFrame({
        "timestamp_seconds": 1_600_000_000 + np.arange(n, dtype=np.int64) * 300,
        "CPU": 20 + np.sin(index / 17),
        "THROUGHPUT": 100 + np.mod(index, 31),
        "MEMORY": 1000 + np.mod(index, 47),
        "DISK_WRITE": 10 + np.mod(index, 13),
        "segment_id": np.zeros(n, dtype=np.int64),
        "timestamp_utc": pd.to_datetime(1_600_000_000 + np.arange(n) * 300, unit="s", utc=True),
    })

