# Dataset / hierarchy Section 3 revision audit

**Task:** Expand Section 3 — TimeTrack Dataset and Telemetry Hierarchies  
**Base commit:** `836f040` (accepted Related Work)  
**Date:** 2026-08-05

## Length

| Metric | Before | After |
|--------|--------|-------|
| Section 3 prose words | ~190 | ~753 |
| Numbered subsections | 4 (`###`) | 0 (run-in `\paragraph` only) |
| Article pages (`Page N of M`) | 12 | 13 |
| PDF pages (incl. front matter) | 13 | 14 |
| Section 3 rendered span | ≪0.5 page | ≈1.0 page (art.\ p.5 → mid p.6) |

## Source documents used

- `fgcs/manuscript.tex`, `fgcs/references.bib`
- `docs/DATASET_AND_REPOSITORY_AUDIT.md`
- `docs/HIERARCHICAL_FORECASTING_DESIGN.md`
- `docs/_audit_cache/semantics.json`, `machine_host_mapping.json`
- `timetrack/hierarchy_registry.py`, `models/hybrid/reconciliation.py`
- `results/final/aggregate/{FINAL_EVIDENCE_SUMMARY_V2,REPRODUCIBILITY_REPORT_V2,EXECUTION_DEVIATIONS_SUMMARY_V2,SAFE_CLAIMS_V2}.md`
- `docs/FGCS_PUBLICATION_READINESS_FINAL.md`
- TimeTrack paper (Meliani et al., ICC 2025) + Kaggle entry (paraphrased; not copied)
- Direct verification on `compute_dataset.csv` / `disk_dataset.csv`

## Timeline (verified)

| Item | Value |
|------|-------|
| Full span | 2024-06-24 13:37:06 → 2024-07-19 16:27:05 (~25.12 days) |
| Nominal interval (paper) | ~45 s |
| Measured median interval | ~42.285 s |
| Outage | 2024-06-28 13:10:49 → 2024-07-03 10:05:20 (~4.87 days) |
| Aligned timestamps (hierarchy checks) | 41,362 |
| Retained post-outage observations | 33,235 |
| Duplicate timestamps | 0 |
| Outage handling | No interpolation; no window crosses gap |

## CPU core mapping

| Source | machine05 | machine07 | Total |
|--------|-----------|-----------|-------|
| Publication Table I / raw `totalCpuCores*` | 24 | 20 | 236 |
| Verified (host corr.\ + core columns) | 20 (pegase) | 24 (phaedra) | 236 |

**Resolution:** Correlate machine CU with per-core host traces; inventory host core columns; retain mapping yielding exact weighted-sum identity with $C=236$. Do not use conflicting raw m05/m07 labels.

## Memory / disk identity

| Hierarchy | Rows checked | Max abs error | Exact |
|-----------|-------------:|--------------:|:----:|
| Used memory (byte sum) | 41,362 | 0 | yes |
| Used disk (level sum) | 41,362 | 0 | yes |
| CPU weighted sum | by construction under verified cores | — | yes |

## Exclusions

- Network bond/interface approximate relations (not exact enough for final claims)
- Latency / RTT traces (not used as a hierarchy)
- Disk write/read rates and cumulative I/O counters (not the UD level target)

## Table / figure

- **Added:** `fgcs/tables/dataset_hierarchy_summary.tex` (Section 3; data/hierarchy semantics)
- **Slimmed:** `fgcs/tables/experiment_registry.tex` (Section 5; protocol only; `\FloatBarrier` after input)
- **Figure:** `figs/architecture_or_hierarchy.pdf` kept in Section 3; caption updated (CPU weighted; memory/disk sums; recon on forecasts)
- Bibliography unchanged; `reference_audit.csv` not regenerated

## Unsupported-claim check

- No dataset-creation contribution claimed
- No final network-hierarchy claim
- No premature Results MAE / method ranking
- Disk described as used-disk level, not write forecasting
- Nominal vs measured interval distinguished
- m05/m07 discrepancy stated neutrally

## Build / layout

- Compilation errors: 0
- Unresolved citations/references: 0
- Overfull boxes: 0
- Article length: 13 pages (target 12–13)
- Section 3 ≈ 1.0 page (target 0.9–1.2)
- Protocol table retained in Section 5 (not floated into Results)
- Figure remains in Section 3; Section 4 begins cleanly on art.\ p.6

## Recommendation

`READY_FOR_METHODOLOGY_EXPANSION`
