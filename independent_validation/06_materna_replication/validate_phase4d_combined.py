#!/usr/bin/env python3
"""Technical-only combined gate for the three completed Materna traces."""

from __future__ import annotations

import json
from collections import Counter

import pandas as pd

from phase4d_execution import COHORT_SHA256, SCIENTIFIC_ROOT, SELECTED_IDS, TRACES, atomic_json_write
from run_phase4d_scientific import verify_frozen_identities
from validate_phase4d_preflight import verify_historical_protocol


def main() -> None:
    failures: list[str] = []
    verify_frozen_identities()
    if verify_historical_protocol():
        failures.append("historical_protocol_or_phase4c_history")
    run_ids: set[str] = set()
    counts = Counter()
    cohort_hashes: set[str] = set()
    for trace in TRACES:
        validation_path = SCIENTIFIC_ROOT / trace / "validation/technical_validation.json"
        if not validation_path.is_file():
            failures.append(f"missing_trace_validation:{trace}")
            continue
        validation = json.loads(validation_path.read_text())
        if validation.get("status") != "PASS":
            failures.append(f"trace_validation:{trace}")
        cohort_hashes.add(validation.get("frozen_identity", {}).get("cohort_sha256", ""))
        contexts = pd.read_csv(SCIENTIFIC_ROOT / trace / "selected_contexts.csv", dtype={"vm_id": str})
        if set(contexts.vm_id) != set(SELECTED_IDS):
            failures.append(f"cohort_ids:{trace}")
        for phase in ("inner", "final"):
            directory = SCIENTIFIC_ROOT / trace / "runtime/completions" / phase
            for path in sorted(directory.glob("*.json")):
                row = json.loads(path.read_text())
                identity = row.get("identity", {})
                run_id = str(identity.get("run_id"))
                if run_id in run_ids:
                    failures.append(f"cross_trace_run_id:{run_id}")
                run_ids.add(run_id)
                if identity.get("trace") != trace:
                    failures.append(f"trace_namespace:{run_id}")
                if "bitbrains" in path.as_posix().lower() or not path.is_relative_to(SCIENTIFIC_ROOT / trace):
                    failures.append(f"foreign_artifact_reuse:{run_id}")
                if identity.get("run_kind") != "scientific":
                    failures.append(f"pilot_reuse:{run_id}")
                counts[phase] += 1
                counts["fits"] += 1
                if phase == "final":
                    counts["metrics"] += len(row.get("metrics", []))
        env = SCIENTIFIC_ROOT / trace
        counts["selected_contexts"] += sum(1 for _ in open(env / "selected_contexts.csv")) - 1
        counts["models"] += len(list(env.glob("*/models/*.pt")))
        counts["predictions"] += len(list(env.glob("*/predictions/*.parquet")))
    expected = {
        "inner": 42525, "final": 14175, "fits": 56700,
        "metrics": 94500, "selected_contexts": 4725,
        "models": 14175, "predictions": 14175,
    }
    if dict(counts) != expected:
        failures.append("combined_counts")
    if cohort_hashes != {COHORT_SHA256}:
        failures.append("cohort_mismatch")
    result = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "counts": dict(counts),
        "expected_counts": expected,
        "unique_run_ids": len(run_ids),
        "cross_trace_collisions": sum(item.startswith("cross_trace") for item in failures),
        "scientific_analysis_performed": False,
        "predictive_metric_values_inspected": False,
    }
    destination = SCIENTIFIC_ROOT / "validation/combined_technical_validation.json"
    atomic_json_write(destination, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
