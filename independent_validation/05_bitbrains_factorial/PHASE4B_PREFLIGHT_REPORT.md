# Phase 4B Bitbrains Factorial Implementation and Preflight Report

Date: 2026-09-28  
Scope: implementation, complete support/split construction, tests, and a non-scientific inner-only pilot. No external scientific experiment was run.

## 1. Frozen-history status

- Preflight HEAD: `59f5bed3fd7b385739d08dc088965341a29c2809`.
- Annotated checkpoint tag `phase4a-external-confirmation-design-freeze-v1` resolves to the same commit.
- Phase 4A validation: PASS.
- Phase 4A inventory SHA-256: `b3fb2186d16fcdd28862a2ba6dd6c76c701d66dc5387ce9aa57bf04b3e1f7cc3` (27 entries).
- Phase 4A tree SHA-256: `a22bb756fed1fff2ad04cf1e0155f70df1f4682390cf54a0877490d4d3132194`.
- Prior frozen TimeTrack histories passed their recursive integrity validation.
- External scientific S1/S2/M1 fits: 0. External outer-test predictions: 0. External predictive outcomes inspected: 0.

## 2. Prospective decision record

`EXTERNAL_FACTORIAL_DECISION.md` was created and hashed before support construction or pilot execution. Its SHA-256 is:

`247197a787250f9e81ea3b858a9f79dd8f5377d548da2fbc2bdec514e420b81e`

The frozen configuration SHA-256 is:

`deedcd31616861f1f6ee4517cc0552a05d54d0b334364f9674b06a1dcab6dc1a`

The record prospectively fixes the environments, cohorts, mappings, H1/H2/H3, cleaning, segmentation, support, splits, pilot boundary, support minima, and compute-feasibility thresholds.

## 3. Archive identities

| Archive | SHA-256 | Status |
|---|---|---|
| Bitbrains fastStorage | `11313f528a0cbcbe57e63162f8ae5a41a9c7e7c1a79872e294ff3c5bbaa2e671` | verified |
| Bitbrains Rnd | `d3d9ddebb689c0b5463f2e4cfd8956e84bdcdf138b4476320855393e2b229a06` | verified |
| Materna | `1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4` | verified; not used |

The implementation reads selected members directly from the official frozen ZIP archives. `RAW_MEMBER_MANIFEST.csv` records archive, member path, VM ID, byte size, and member SHA-256.

## 4. Selected cohort identities

| Environment | Frozen VMs | ID-list SHA-256 | Selection-record SHA-256 |
|---|---:|---|---|
| fastStorage | 35 | `97742a6e10858c9b8a021d3142419d66f41b2ac67e5944f95c2a4b8931f4632d` | `3ccbdb4d3615d323d54127f63eb72f588893d9bd48593a82dcccc10754a60b38` |
| Rnd | 35 | `5674f15382d5efb795cbda46a34f1f766e859413857475212023afc36ffcdc1a` | `5cfbd93103881a8af258ed9ecc6e317601c7b6b44825d2f790a1a81ed1731f9c` |

All 70 frozen IDs were retained; no VM was substituted.

## 5. Pilot VM identities

The pilot VMs were fixed before training as the first IDs in the already frozen SHA-ranked cohorts:

| Environment | VM | Fold | Seed | Context | Epochs |
|---|---:|---:|---:|---:|---:|
| fastStorage | 697 | 1 | 0 | 9 | 5 |
| Rnd | 99 | 1 | 0 | 9 | 5 |

## 6. Ingestion rules

The parser uses exact official fields for Unix-second timestamp, CPU usage percentage, active memory KB, disk-write throughput KB/s, network-received throughput KB/s, and network-transmitted throughput KB/s. `THROUGHPUT = received + transmitted`. Fixed resource order is CPU, THROUGHPUT, MEMORY, DISK_WRITE. Ten-digit timestamps are interpreted as Unix seconds and converted deterministically to UTC. The nominal cadence is 300 seconds. There is no resampling, interpolation, forward fill, or timestamp synthesis.

## 7. Invalid-row handling

A required-resource row is available only when CPU is finite and in [0,100], both network components are finite/nonnegative, memory and disk write are finite/nonnegative, and computed total throughput is finite/nonnegative. Invalid rows are removed as unavailable observations; they are not clipped, imputed, replaced, or repaired. Duplicate timestamps are rejected, not resolved.

| Environment | Raw rows | Valid rows | Invalid rows | Median invalid fraction | Maximum invalid fraction | Duplicates |
|---|---:|---:|---:|---:|---:|---:|
| fastStorage | 294,639 | 294,630 | 9 | 0 | 0.000696 | 0 |
| Rnd | 842,501 | 842,385 | 116 | 0 | 0.004101 | 0 |
| Combined | 1,137,140 | 1,137,015 | 125 | — | — | 0 |

Per-VM counts and reason counts are preserved in `SELECTED_VM_QUALITY.csv`.

## 8. Segment construction

Valid observations are sorted chronologically and a segment breaks whenever the next timestamp gap exceeds 450 seconds. Histories and targets cannot cross segments; an invalid-row removal normally creates a discontinuity. No values are interpolated across a boundary.

| Environment | Segments | Median observations/segment | Maximum observations/segment | Median duration, seconds | Maximum internal gap, seconds | Largest between-valid-observation gap, seconds |
|---|---:|---:|---:|---:|---:|---:|
| fastStorage | 418 | 255.5 | 4,077 | 76,358 | 310 | 2,100 |
| Rnd | 911 | 375 | 8,151 | 112,220 | 355 | 113,413 |

The exact 1,329 segment rows, timestamps, sizes, durations, and gap diagnostics are in `BITBRAINS_SEGMENT_MANIFEST.csv`.

## 9. Support semantics

Support is constructed once at Lmax=18 per environment/VM. Every legal origin has a complete same-segment four-resource history and all four finite targets at leads `[1,2,4,9,18]`. All lead targets remain in the same segment. Shorter contexts 4 and 9 reuse the identical L18 origin IDs and gain no origins. Every S1 resource, every S2 resource, and M1 therefore shares the same support. Maximum-lead target-time purge is applied before outer-test and inner-validation boundaries.

The exact origin-ID lists and hashes are stored in `EXTERNAL_SUPPORT_MANIFEST.parquet`; the compact counts, hashes, segment IDs, and boundary timestamps are in `EXTERNAL_SUPPORT_SUMMARY.csv`. Neither artifact stores outer-test target values.

## 10. Split and fold semantics

For each VM, legal origins are chronological. The first 50% forms the initial training region and the next five 10% blocks form five expanding outer folds; boundaries use floor-count construction and the final boundary is forced to the legal-origin count. Outer train is lead-18 target-time purged against the first test origin. Within the resulting outer train, the latest `ceil(15%)` is inner validation, and inner train is lead-18 purged against it. There are no random splits.

## 11. Support counts by environment, VM, and fold

There are exactly 525 records per environment (`35 VMs × 5 folds × 3 contexts`) and 1,050 combined. Counts are intentionally identical at L=4, 9, and 18 because all contexts use maximum-history support. The canonical per-environment/VM/fold counts and hashes are the 1,050 rows of `EXTERNAL_SUPPORT_SUMMARY.csv`; the ranges below summarize its 350 unique VM/fold cells.

| Environment | Partition | Minimum | Median | Maximum |
|---|---|---:|---:|---:|
| fastStorage | inner train | 1,683 | 4,895 | 6,493 |
| fastStorage | inner validation | 301 | 867 | 1,149 |
| fastStorage | outer train | 2,002 | 5,780 | 7,660 |
| fastStorage | outer test | 404 | 829 | 854 |
| Rnd | inner train | 8,369 | 13,823 | 19,339 |
| Rnd | inner validation | 1,481 | 2,443 | 3,417 |
| Rnd | outer train | 9,868 | 16,284 | 22,774 |
| Rnd | outer test | 1,977 | 2,431 | 2,533 |

Total legal origins across selected VMs are 284,882 for fastStorage and 818,879 for Rnd.

## 12. Support feasibility and failures

The prospective minima were outer train 1,024, inner train 512, inner validation 128, and outer test 256. All 350 VM/fold cells exceed all minima. Support failures: 0. S1/S2/M1 formulation/resource mismatches: 0. Duplicate-timestamp failures: 0. IQR-zero failures encountered in the pilot partitions: 0.

## 13. Transforms and scalers

CPU and MEMORY use the identity transform. THROUGHPUT and DISK_WRITE use `log1p`. Each resource is then median/IQR robust-scaled, with scalers fitted only on inner train during selection and on the complete legal outer train in a future final refit. IQR must be strictly positive; zero IQR stops execution without epsilon fallback. Native inversion applies inverse scaling, then `expm1` and `max(0,prediction)` for throughput and disk write. Pre-projection negative fractions are retained.

## 14. S1, S2, and M1 definitions and shapes

All formulations use a two-layer, unidirectional LSTM with hidden size 64, dropout 0.1, and the final recurrent hidden representation.

| Formulation | Input | Model organization | Output |
|---|---|---|---|
| S1 | `[N,L,1]` | one independent model/resource | `[N,5]` |
| S2 | `[N,L,4]` | one independent model/target resource | `[N,5]` |
| M1 | `[N,L,4]` | one shared encoder, four independent linear heads | `[N,4,5]` |

M1 uses the unweighted mean of four resource-specific normalized MSE losses. No architecture enhancement, adaptive weighting, selective fusion, or cross-environment pooling was introduced.

## 15. Exact parameter counts

| Item | Parameters |
|---|---:|
| S1 per model | 50,757 |
| S1 four-model total | 203,028 |
| S2 per model | 51,525 |
| S2 four-model total | 206,100 |
| M1 shared encoder | 51,200 |
| M1 four heads | 1,300 |
| M1 total | 52,500 |

Counts are calculated programmatically and tested exactly.

## 16. Tests and independent validation

- Test suite: 45 passed, 0 failed.
- Independent Phase 4B validator: PASS.
- Validator reproduced all 1,050 support records and verified Phase 4A bytes, archives, cohorts, no replacement, duplicates, invalid-row policy, segments, hashes, pilot isolation, model/workload counts, and the absence of scientific results.

## 17. Non-scientific pilot timing

Exactly 18 models ran for exactly five epochs each, using inner train and inner validation only. This table aggregates the exact model-level rows in `PILOT_TIMINGS.csv`; timing values are technical diagnostics.

| Environment | Formulation | Models | Train samples/model | Validation samples/model | Median seconds/epoch | Sum 5-epoch train seconds | Sum validation seconds | Peak RSS bytes |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| fastStorage | S1 | 4 | 3,458 | 614 | 0.082121 | 1.642813 | 0.148694 | 449,855,488 |
| fastStorage | S2 | 4 | 3,458 | 614 | 0.083093 | 1.662322 | 0.148929 | 449,904,640 |
| fastStorage | M1 | 1 | 3,458 | 614 | 0.086661 | 0.433305 | 0.037558 | 449,921,024 |
| Rnd | S1 | 4 | 10,340 | 1,828 | 0.243251 | 4.870569 | 0.459779 | 436,436,992 |
| Rnd | S2 | 4 | 10,340 | 1,828 | 0.246890 | 4.945706 | 0.456853 | 437,010,432 |
| Rnd | M1 | 1 | 10,340 | 1,828 | 0.258467 | 1.292336 | 0.114766 | 437,075,968 |

## 18. M1 loss-balance diagnostics

`M1_LOSS_BALANCE.csv` contains all 40 environment/epoch/resource rows. Train shares and validation shares each sum to one within every environment/epoch. The endpoint values below are reported only to establish finite logging and equal-loss implementation; they are not evidence for reweighting or predictive interpretation.

| Environment | Resource | Epoch 1 train MSE/share | Epoch 1 validation MSE/share | Epoch 5 train MSE/share | Epoch 5 validation MSE/share |
|---|---|---|---|---|---|
| fastStorage | CPU | 0.543071 / 0.037362 | 0.605671 / 0.012878 | 0.456526 / 0.034805 | 0.358097 / 0.007536 |
| fastStorage | THROUGHPUT | 0.724325 / 0.049831 | 1.564300 / 0.033260 | 0.502228 / 0.038290 | 1.354501 / 0.028506 |
| fastStorage | MEMORY | 0.721903 / 0.049665 | 1.021225 / 0.021714 | 0.636775 / 0.048547 | 0.787423 / 0.016572 |
| fastStorage | DISK_WRITE | 12.546209 / 0.863142 | 43.840603 / 0.932148 | 11.521017 / 0.878358 | 45.016163 / 0.947386 |
| Rnd | CPU | 72.884669 / 0.188547 | 44.294685 / 0.063756 | 68.700789 / 0.253065 | 40.280411 / 0.101376 |
| Rnd | THROUGHPUT | 255.988552 / 0.662223 | 532.930298 / 0.767079 | 175.877770 / 0.647860 | 312.907013 / 0.787512 |
| Rnd | MEMORY | 0.797216 / 0.002062 | 0.598913 / 0.000862 | 0.738367 / 0.002720 | 0.595120 / 0.001498 |
| Rnd | DISK_WRITE | 56.889123 / 0.147168 | 116.928818 / 0.168303 | 26.158117 / 0.096356 | 43.553543 / 0.109614 |

Loss weights remain exactly equal at one quarter in the M1 objective; observed loss shares do not alter them.

## 19. Inner-validation inversion sanity

`INNER_VALIDATION_SANITY.csv` contains 120 rows: two environments × three formulations × four resources × five horizons. All MAE, RMSE, R-squared, and NMAE values are finite after physical inversion. Resource ordering, target ordering, scaler inversion, `expm1`, and native-unit metric paths completed without numerical failure. These inner-validation numbers are explicitly non-scientific and are not compared across formulations, environments, or TimeTrack evidence.

## 20. Negative projection rates

The maximum pre-projection negative native prediction fraction is 0.0 for every environment/formulation group, including throughput and disk write. Projection logic was nevertheless executed and remains mandatory for future scientific outputs.

## 21. Projected runtime by environment

One environment requires 14,175 inner fits, 4,725 final fits, 18,900 total fits, and 31,500 future resource-lead metric rows. Both environments require 28,350 inner fits, 9,450 final fits, 37,800 total fits, and 63,000 metric rows.

| Scenario | Effective epochs | fastStorage aggregate fit-hours | Rnd aggregate fit-hours | Combined aggregate fit-hours |
|---|---:|---:|---:|---:|
| Optimistic | 10 | 4.6539 | 13.8473 | 18.5012 |
| Central | 25 | 11.6347 | 34.6182 | 46.2530 |
| Conservative | 50 | 23.2695 | 69.2365 | 92.5059 |

Detailed S1-inner/final, S2-inner/final, and M1-inner/final estimates for each environment and scenario are in `RUNTIME_PROJECTION.json`.

## 22. Projected one-worker and four-worker wall time

| Scenario | Combined one-worker hours | Combined four-worker hours | fastStorage four-worker hours | Rnd four-worker hours |
|---|---:|---:|---:|---:|
| Optimistic | 18.5012 | 4.6253 | 1.1635 | 3.4618 |
| Central | 46.2530 | 11.5632 | 2.9087 | 8.6546 |
| Conservative | 92.5059 | 23.1265 | 5.8174 | 17.3091 |

Four-worker numbers are idealized effective-worker estimates from observed environment-specific throughput. Central and conservative combined estimates are 0.4818 and 0.9636 days, respectively.

## 23. Projected retained storage

| Component | Bytes |
|---|---:|
| Model artifacts, both environments | 1,973,625,150 |
| Prediction payloads, both environments | 883,038,400 |
| Metrics and manifests | 65,656,632 |
| Total | 2,922,320,182 (2.9223 GB decimal) |

Median serialized model-state sizes observed were 206,533 bytes for S1, 209,605 for S2, and 215,091 for M1.

## 24. Resumability design

The future scientific runner uses an identity containing environment, formulation, target resource where applicable, VM, fold, context, seed, phase, config hash, support hash, archive hash, and cohort hash. Completion records are written atomically. A fit is skipped only when the completion identity matches and all expected artifacts validate. Final refits have no validation/test arguments, train from scratch for the seed-specific selected epoch on complete legal outer train, and evaluate outer test once. Unnecessary epoch checkpoints are not retained.

## 25. Compute-feasibility decision

`FULL_35_VM_CONFIRMATION_FEASIBLE`

This decision uses only timing, memory, storage, support feasibility, and technical correctness. The central four-worker estimate is 0.4818 days; the conservative estimate is 0.9636 days; retained storage is 2.9223 GB; pilot peak RSS is 449,921,024 bytes; detected physical RAM is 25,769,803,776 bytes; and the four-worker memory gate passes. No pilot predictive accuracy contributed to the decision.

## 26. Technical readiness

Implementation, cohort/archive identity checks, direct ingestion, strict cleaning, segmentation, common support, folds, purges, transformations, architectures, context selection, epoch lifecycle, physical inversion, metrics, aggregation, resumability, support construction, tests, non-scientific pilot, projections, and independent validation are complete. No scientific context selection, final refit, outer-test target access, outer-test prediction, H1/H2/H3 result, new architecture, Materna run, or TimeTrack rerun occurred.

External scientific fits: 0.  
External outer-test predictions: 0.  
External predictive outcomes inspected: 0.

READY_FOR_EXTERNAL_PROTOCOL_FREEZE
