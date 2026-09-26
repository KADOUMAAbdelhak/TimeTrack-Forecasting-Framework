#!/usr/bin/env python3
"""Validate Phase 3B implementation and bounded pilot without scientific fits."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark.neural_v2.validate_dlinear_scientific import phase2a_hashes, sha256, verify_inventory
from benchmark.src.data import PANEL_PATH, verify_raw_hashes


ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
PILOT = BASE / "pilot"
EXPECTED_DECISION = "2bfb2610bd8e869dc038bccd6b18656cd2c968b9d548c758487cae500cbf5677"
EXPECTED_PANEL = "c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a"


def digest(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    failures: list[str] = []
    histories = {
        "phase3a": (ROOT / "multiresource/PHASE3A_ARTIFACT_SHA256.csv", 25),
        "neural_v2": (ROOT / "benchmark/neural_v2/NEURAL_V2_ARTIFACT_SHA256.csv", 29),
        "dlinear": (ROOT / "benchmark/neural_v2/DLINEAR_SCIENTIFIC_ARTIFACT_SHA256.csv", 1347),
        "lstm": (ROOT / "benchmark/neural_v2/LSTM_SCIENTIFIC_ARTIFACT_SHA256.csv", 1349),
        "patchtst": (ROOT / "benchmark/neural_v2/PATCHTST_SCIENTIFIC_ARTIFACT_SHA256.csv", 1352),
        "original_deterministic": (ROOT / "benchmark/phase2b1_original/HEAVY_ARTIFACT_SHA256.csv", 632),
        "corrected_deterministic": (ROOT / "benchmark/phase2b1_corrected/CORRECTION_ARTIFACT_SHA256.csv", 1070),
    }
    history_result = {}
    for name, (path, expected) in histories.items():
        count, bad = verify_inventory(path); ok = count == expected and not bad
        history_result[name] = {"count": count, "expected": expected, "status": "PASS" if ok else "FAIL"}
        if not ok: failures.append(name)
    phase2a_count, phase2a_bad = phase2a_hashes()
    if phase2a_count != 33 or phase2a_bad: failures.append("phase2a")
    if not verify_raw_hashes(): failures.append("raw")
    panel_hash = sha256(PANEL_PATH)
    if panel_hash != EXPECTED_PANEL: failures.append("canonical")
    if digest(BASE / "FACTORIAL_DECISION.md") != EXPECTED_DECISION: failures.append("decision")

    timing = json.loads((PILOT / "TIMING_RESULTS.json").read_text())
    expected_models = {(f, r) for f in ("S1", "S2") for r in ("CPU", "THROUGHPUT", "MEMORY", "DISK_WRITE")} | {("M1", "ALL")}
    observed_models = {(row["formulation"], row["resource"]) for row in timing["models"]}
    if timing["pilot_models"] != 9 or observed_models != expected_models or any(row["epochs_completed"] != 5 for row in timing["models"]): failures.append("pilot shape")
    provenance = json.loads((PILOT / "PILOT_PROVENANCE.json").read_text())
    forbidden_true = ["scientific", "context_selection_executed", "outer_refit_executed", "outer_test_values_accessed", "outer_test_predictions_generated", "proposed_architecture_implemented"]
    if any(provenance[key] for key in forbidden_true): failures.append("pilot boundary")

    support = json.loads((PILOT / "SUPPORT_MANIFEST.json").read_text())
    support_rows = support["rows"]
    mismatch = 0
    for (_machine, _fold), group in pd.DataFrame(support_rows).groupby(["machine", "fold"]):
        for column in ("inner_train_hash", "inner_validation_hash", "outer_train_hash", "outer_test_hash"):
            mismatch += int(group[column].nunique() != 1)
    if len(support_rows) != 105 or mismatch or support["outer_test_values_accessed"]: failures.append("common support")

    balance = pd.read_csv(PILOT / "M1_LOSS_BALANCE.csv")
    sanity = pd.read_csv(PILOT / "SANITY_METRICS.csv")
    if len(balance[balance.row_type.eq("epoch")]) != 20 or len(balance[balance.row_type.eq("final3_mean")]) != 4: failures.append("loss balance")
    if len(sanity) != 96 or sanity.scientific.astype(str).str.lower().eq("true").any() or not np.isfinite(sanity[["mae", "rmse", "nmae"]]).all().all(): failures.append("sanity metrics")
    if not (BASE / "outputs/README.md").exists() or len(list((BASE / "outputs").glob("*"))) != 1: failures.append("scientific output absence")

    result = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "decision_sha256": digest(BASE / "FACTORIAL_DECISION.md"),
        "canonical_panel_sha256": panel_hash,
        "raw_hashes_unchanged": verify_raw_hashes(),
        "frozen_history": history_result,
        "phase2a": {"count": phase2a_count, "status": "PASS" if not phase2a_bad and phase2a_count == 33 else "FAIL"},
        "pilot_models": timing["pilot_models"],
        "epochs_per_model": timing["epochs_each"],
        "support_manifest_rows": len(support_rows),
        "support_hash_mismatches": mismatch,
        "sanity_metric_rows": len(sanity),
        "outer_test_values_accessed": False,
        "scientific_results": 0,
        "scientific_context_selections": 0,
        "scientific_outer_refits": 0,
        "multi_target_scientific_runs": 0,
        "proposed_architectures": 0,
        "tcn_v2_scientific_runs": 0,
    }
    (BASE / "PREFLIGHT_VALIDATION.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures: raise RuntimeError("Phase 3B preflight validation failed")


if __name__ == "__main__": main()
