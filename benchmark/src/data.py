"""Canonical-panel loading and immutable input checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PANEL_PATH = (
    ROOT
    / "discovery"
    / "02_dependency_analysis"
    / "outputs"
    / "canonical_panel.parquet"
)
REGISTRY_PATH = (
    ROOT
    / "discovery"
    / "02_dependency_analysis"
    / "outputs"
    / "canonical_signal_registry.csv"
)
PHASE1_HASH_PATH = (
    ROOT / "discovery" / "01_data_audit" / "outputs" / "raw_hashes_before_after.json"
)
EXPECTED_PANEL_SHA256 = "c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_canonical_panel(verify_hash: bool = True) -> pd.DataFrame:
    if verify_hash and sha256_file(PANEL_PATH) != EXPECTED_PANEL_SHA256:
        raise RuntimeError("Canonical panel hash differs from the Phase 2A freeze")
    panel = pd.read_parquet(PANEL_PATH)
    panel["timestamp"] = pd.to_datetime(panel["timestamp"], errors="raise")
    if panel["timestamp"].duplicated().any() or not panel["timestamp"].is_monotonic_increasing:
        raise RuntimeError("Canonical timestamps are not unique and increasing")
    required = {"timestamp", "segment_id"}
    if not required.issubset(panel.columns):
        raise RuntimeError("Canonical panel metadata columns are missing")
    return panel


def load_registry() -> pd.DataFrame:
    return pd.read_csv(REGISTRY_PATH)


def raw_hashes() -> dict[str, str]:
    frozen = json.loads(PHASE1_HASH_PATH.read_text())["after"]
    return {
        name: sha256_file(ROOT / "data" / "raw" / name)
        for name in frozen
    }


def verify_raw_hashes() -> bool:
    frozen = json.loads(PHASE1_HASH_PATH.read_text())["after"]
    return raw_hashes() == frozen
