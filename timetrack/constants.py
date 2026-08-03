"""Shared constants derived from the Phase-1 audit."""

from __future__ import annotations

# Empirically measured median sampling interval (seconds). NOT 45.
SAMPLING_SECONDS = 42.285166

# Major outage (inclusive of the first post-gap timestamp as resume point)
OUTAGE_START = "2024-06-28 13:10:49.165290"
OUTAGE_END = "2024-07-03 10:05:20.693178"

MACHINE_TO_HOST = {
    "machine01": "acamas",
    "machine02": "bellerophon",
    "machine03": "dedale",
    "machine04": "demophon",
    "machine05": "pegase",  # correlation-based; core-count label conflicts
    "machine06": "perse",
    "machine07": "phaedra",  # correlation-based; core-count label conflicts
}

HOST_TO_MACHINE = {v: k for k, v in MACHINE_TO_HOST.items()}

RAW_FILES = [
    "compute_dataset.csv",
    "detailed_cpu_cores_dataset.csv",
    "disk_dataset.csv",
    "network_dataset.csv",
    "packet-loss-dataset.csv",
    "throughputs_dataset.csv",
]

# MAPE: observations with |y| < this are excluded from MAPE (reported separately)
MAPE_ZERO_EPS = 1e-8
