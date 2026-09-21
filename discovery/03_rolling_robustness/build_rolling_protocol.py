#!/usr/bin/env python3
"""Freeze deterministic rolling-origin folds for Phase 1C."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "discovery" / "03_rolling_robustness"
OUTPUT_DIR = PHASE_DIR / "outputs"
PANEL_PATH = (
    ROOT
    / "discovery"
    / "02_dependency_analysis"
    / "outputs"
    / "canonical_panel.parquet"
)
PHASE1_HASH_PATH = (
    ROOT / "discovery" / "01_data_audit" / "outputs" / "raw_hashes_before_after.json"
)

LEADS = [1, 2, 4, 8, 16, 32, 64, 128]
HISTORY_LAGS = [0, 1, 2, 4, 8, 16, 32]
MACHINES = [f"machine{i:02d}" for i in range(1, 8)]
FOLDS = [1, 2, 3, 4, 5]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def eligible_origins(panel: pd.DataFrame, target: str, lead: int) -> pd.DataFrame:
    y = panel[target]
    segment = panel["segment_id"]
    eligible = pd.Series(True, index=panel.index)
    for lag in HISTORY_LAGS:
        eligible &= y.shift(lag).notna()
    eligible &= y.shift(-lead).notna()
    eligible &= segment.eq(segment.shift(max(HISTORY_LAGS)))
    eligible &= segment.eq(segment.shift(-lead))
    return pd.DataFrame(
        {
            "origin_timestamp": panel.loc[eligible, "timestamp"],
            "target_timestamp": panel["timestamp"].shift(-lead).loc[eligible],
            "segment_id": segment.loc[eligible],
        }
    ).reset_index(drop=True)


def build_boundaries(panel: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for machine in MACHINES:
        target = f"{machine}__cpu_utilization"
        for lead in LEADS:
            origins = eligible_origins(panel, target, lead)
            n = len(origins)
            boundaries = [math.floor(n * fraction) for fraction in (0.5, 0.6, 0.7, 0.8, 0.9)]
            ends = [math.floor(n * fraction) for fraction in (0.6, 0.7, 0.8, 0.9, 1.0)]
            previous_test_end = None
            previous_train_n = None
            for fold, start, end in zip(FOLDS, boundaries, ends):
                test = origins.iloc[start:end]
                train_before = origins.iloc[:start]
                if len(test) == 0 or len(train_before) == 0:
                    raise RuntimeError(f"Empty rolling fold: {target}, lead={lead}, fold={fold}")
                test_start = test["origin_timestamp"].iloc[0]
                train = train_before[
                    train_before["target_timestamp"].lt(test_start)
                ]
                leakage_ok = bool(
                    len(train)
                    and train["target_timestamp"].max() < test_start
                )
                nonoverlap_ok = bool(
                    previous_test_end is None
                    or previous_test_end < test["origin_timestamp"].iloc[0]
                )
                expanding_ok = bool(
                    previous_train_n is None or len(train) > previous_train_n
                )
                if not leakage_ok or not nonoverlap_ok or not expanding_ok:
                    raise RuntimeError(
                        f"Rolling invariant failure: {target}, lead={lead}, fold={fold}"
                    )
                rows.append(
                    {
                        "target": target,
                        "target_machine": machine,
                        "lead": lead,
                        "fold": fold,
                        "eligible_n": n,
                        "train_n_before_purge": len(train_before),
                        "train_n_after_purge": len(train),
                        "purged_n": len(train_before) - len(train),
                        "test_n": len(test),
                        "train_origin_start": train["origin_timestamp"].iloc[0],
                        "train_origin_end": train["origin_timestamp"].iloc[-1],
                        "max_train_target_timestamp": train["target_timestamp"].max(),
                        "test_origin_start": test["origin_timestamp"].iloc[0],
                        "test_origin_end": test["origin_timestamp"].iloc[-1],
                        "test_segment_ids": json.dumps(
                            sorted(test["segment_id"].unique().tolist())
                        ),
                        "leakage_check": leakage_ok,
                        "nonoverlapping_test_check": nonoverlap_ok,
                        "expanding_training_check": expanding_ok,
                        "test_start_position_zero_based": start,
                        "test_end_position_exclusive": end,
                    }
                )
                previous_test_end = test["origin_timestamp"].iloc[-1]
                previous_train_n = len(train)
    return pd.DataFrame(rows)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frozen_raw = json.loads(PHASE1_HASH_PATH.read_text())["after"]
    raw_before = {
        name: sha256_file(ROOT / "data" / "raw" / name) for name in frozen_raw
    }
    panel_hash = sha256_file(PANEL_PATH)
    panel = pd.read_parquet(PANEL_PATH)
    panel["timestamp"] = pd.to_datetime(panel["timestamp"])
    boundaries = build_boundaries(panel)
    if len(boundaries) != 7 * 8 * 5:
        raise RuntimeError("Expected 280 target/lead/fold definitions")
    boundaries.to_csv(OUTPUT_DIR / "rolling_fold_boundaries.csv", index=False)
    raw_after = {
        name: sha256_file(ROOT / "data" / "raw" / name) for name in frozen_raw
    }
    validation = {
        "rows": len(boundaries),
        "leakage_failures": int((~boundaries["leakage_check"]).sum()),
        "test_overlap_failures": int((~boundaries["nonoverlapping_test_check"]).sum()),
        "expanding_training_failures": int(
            (~boundaries["expanding_training_check"]).sum()
        ),
        "panel_unchanged": sha256_file(PANEL_PATH) == panel_hash,
        "raw_hashes_unchanged_and_match_phase1": raw_before == raw_after == frozen_raw,
    }
    if (
        validation["leakage_failures"]
        or validation["test_overlap_failures"]
        or validation["expanding_training_failures"]
        or not validation["panel_unchanged"]
        or not validation["raw_hashes_unchanged_and_match_phase1"]
    ):
        raise RuntimeError("Rolling protocol validation failed")
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
