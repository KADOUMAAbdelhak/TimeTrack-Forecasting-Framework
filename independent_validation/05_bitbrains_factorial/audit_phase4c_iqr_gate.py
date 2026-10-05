#!/usr/bin/env python3
"""Record the frozen Phase 4C IQR feasibility gate without predictive access."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from src import CONTEXTS, RESOURCE_ORDER
from src.cleaning import clean_and_segment
from src.ingestion import read_vm, selected_ids
from src.panel import scaler_rows
from src.splits import build_folds
from src.support import legal_origins
from src.transforms import transform_resource
from src.validation import atomic_json_write


BASE = Path(__file__).resolve().parent
OUT = BASE / "outputs/scientific"
DESTINATION = OUT / "validation"


def environment_key(environment: str) -> str:
    return "fastStorage" if environment.endswith("fastStorage") else "Rnd"


def scan() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for environment, vm_ids in selected_ids().items():
        for vm_id in vm_ids:
            clean = clean_and_segment(read_vm(environment, vm_id))
            folds = build_folds(clean.frame, environment, vm_id, legal_origins(clean.frame))
            for fold in folds:
                for length in CONTEXTS:
                    for split in ("inner_train", "outer_train"):
                        fit_rows = scaler_rows(getattr(fold, split), length)
                        values = clean.frame.loc[fit_rows, list(RESOURCE_ORDER)].to_numpy(float)
                        for index, resource in enumerate(RESOURCE_ORDER):
                            transformed = transform_resource(values[:, index], resource)
                            transformed_q25, transformed_q75 = np.quantile(transformed, [0.25, 0.75])
                            native_q25, native_q75 = np.quantile(values[:, index], [0.25, 0.75])
                            transformed_iqr = float(transformed_q75 - transformed_q25)
                            native_iqr = float(native_q75 - native_q25)
                            if transformed_iqr <= 0 or native_iqr <= 0:
                                rows.append({
                                    "environment": environment,
                                    "environment_key": environment_key(environment),
                                    "vm_id": vm_id,
                                    "fold": fold.fold,
                                    "L": length,
                                    "split": split,
                                    "resource": resource,
                                    "scaler_row_count": len(fit_rows),
                                    "transformed_iqr": transformed_iqr,
                                    "native_iqr": native_iqr,
                                    "gate_result": "IQR_ZERO_STOP",
                                })
    return pd.DataFrame(rows).sort_values(
        ["environment", "vm_id", "fold", "L", "split", "resource"]
    ).reset_index(drop=True)


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    failures = scan()
    failures.to_csv(DESTINATION / "IQR_ZERO_FAILURES.csv", index=False)
    environments: dict[str, object] = {}
    for key, group in failures.groupby("environment_key", sort=True):
        partitions = group[["vm_id", "fold", "L", "split"]].drop_duplicates()
        environments[key] = {
            "resource_failure_cells": len(group),
            "unique_scaler_partitions": len(partitions),
            "inner_train_partitions": int(partitions.split.eq("inner_train").sum()),
            "outer_train_partitions": int(partitions.split.eq("outer_train").sum()),
            "affected_vms": sorted(group.vm_id.astype(str).unique(), key=int),
            "affected_vm_count": int(group.vm_id.nunique()),
            "affected_vm_fold_count": int(group[["vm_id", "fold"]].drop_duplicates().shape[0]),
            "resource_failure_counts": {
                str(name): int(value)
                for name, value in Counter(group.resource).items()
            },
        }
    completion_dir = OUT / "fastStorage/runtime/completions/inner"
    completion_paths = sorted(completion_dir.glob("*.json"))
    completions = [json.loads(path.read_text()) for path in completion_paths]
    summary = {
        "status": "STOP_IQR_ZERO",
        "protocol_rule": "IQR must be > 0; no epsilon or alternate scaler is permitted",
        "scan_scope": "training partitions only; no outer-test target or prediction access",
        "environments": environments,
        "partial_execution": {
            "fastStorage_completed_inner_fits": len(completions),
            "completed_status_count": sum(row.get("status") == "complete" for row in completions),
            "formulation_counts": {
                name: sum(row.get("identity", {}).get("formulation") == name for row in completions)
                for name in ("S1", "S2", "M1")
            },
            "outer_test_access_count": sum(row.get("outer_test_accessed") is not False for row in completions),
            "final_fits": 0,
            "outer_test_predictions": 0,
            "Rnd_scientific_fits": 0,
            "scientific_analysis_started": False,
            "h1_h2_h3_results": 0,
        },
        "required_next_step": "NEW_PROSPECTIVE_PROTOCOL_DECISION_BEFORE_RESUME",
    }
    atomic_json_write(DESTINATION / "IQR_ZERO_GATE_SUMMARY.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    raise SystemExit(2)


if __name__ == "__main__":
    main()
