#!/usr/bin/env python3
"""Freeze outcome-independent Phase 4A entity cohorts from structural eligibility."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
ELIGIBILITY = BASE / "01_dataset_audit/ENTITY_STRUCTURAL_ELIGIBILITY.csv"
OUT_CSV = Path(__file__).resolve().parent / "SELECTED_ENTITY_COHORTS.csv"
OUT_JSON = Path(__file__).resolve().parent / "SELECTED_ENTITY_COHORTS_SUMMARY.json"
N_SELECT = 35
POLICY_VERSION = "phase4a-v1"
PRIMARY = {
    "GWA-T-12_Bitbrains_fastStorage": "PRIMARY_EXTERNAL_CONFIRMATION",
    "GWA-T-12_Bitbrains_Rnd": "PRIMARY_EXTERNAL_CONFIRMATION",
}
MATERNA = [
    "GWA-T-13_Materna_trace_1",
    "GWA-T-13_Materna_trace_2",
    "GWA-T-13_Materna_trace_3",
]


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def cohort_digest(frame: pd.DataFrame) -> str:
    payload = "".join(
        f"{row.rank}\0{row.entity_id}\0{row.selection_key}\0{row.selection_sha256}\n"
        for row in frame.itertuples(index=False)
    )
    return digest_text(payload)


def ranked_rows(
    entity_ids: set[str], environment: str, role: str, selection_environment: str | None = None
) -> list[dict[str, object]]:
    selection_environment = selection_environment or environment
    candidates = []
    for entity_id in entity_ids:
        key = f"{POLICY_VERSION}|{selection_environment}|{entity_id}"
        candidates.append((digest_text(key), entity_id, key))
    candidates.sort(key=lambda item: (item[0], item[1]))
    return [
        {
            "cohort_role": role,
            "environment": environment,
            "rank": rank,
            "entity_id": entity_id,
            "selection_key": key,
            "selection_sha256": digest,
        }
        for rank, (digest, entity_id, key) in enumerate(candidates[:N_SELECT], start=1)
    ]


def build_selection() -> tuple[pd.DataFrame, dict[str, object]]:
    eligibility = pd.read_csv(ELIGIBILITY, dtype={"entity": str})
    eligibility = eligibility[eligibility.structurally_eligible.astype(bool)]
    rows: list[dict[str, object]] = []
    candidate_counts: dict[str, int] = {}
    for environment, role in PRIMARY.items():
        ids = set(eligibility.loc[eligibility.dataset.eq(environment), "entity"])
        candidate_counts[environment] = len(ids)
        rows.extend(ranked_rows(ids, environment, role))

    materna_sets = [
        set(eligibility.loc[eligibility.dataset.eq(environment), "entity"])
        for environment in MATERNA
    ]
    shared = set.intersection(*materna_sets)
    candidate_counts["GWA-T-13_Materna_shared_all_three"] = len(shared)
    rows.extend(
        ranked_rows(
            shared,
            "GWA-T-13_Materna_shared_all_three",
            "SECONDARY_EXTERNAL_REPLICATION_NOT_PRIMARY_EXECUTION",
            selection_environment="Materna-shared",
        )
    )
    selected = pd.DataFrame(rows)
    summaries = {}
    for environment, group in selected.groupby("environment", sort=True):
        ordered = group.sort_values("rank")
        summaries[environment] = {
            "candidate_count": candidate_counts[environment],
            "selected_count": len(ordered),
            "selected_ids_sha256": digest_text("\n".join(ordered.entity_id) + "\n"),
            "selection_records_sha256": cohort_digest(ordered),
        }
    summary: dict[str, object] = {
        "status": "PASS",
        "policy_version": POLICY_VERSION,
        "selection_count_per_cohort": N_SELECT,
        "selection_basis": "ascending SHA-256 over policy version, environment, and exact VM ID",
        "outcome_dependent_inputs": 0,
        "cohorts": summaries,
    }
    return selected, summary


def main() -> None:
    selected, summary = build_selection()
    selected.to_csv(OUT_CSV, index=False)
    OUT_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
