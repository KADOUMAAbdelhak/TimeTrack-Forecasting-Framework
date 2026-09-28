# Phase 4A External-Confirmation Design Freeze Manifest

Freeze date: 2026-09-28
Pre-freeze HEAD: `f9b11adb5dc3a0c2802703ceb1cbafb060c6f341`
Prior checkpoint: commit `f9b11adb5dc3a0c2802703ceb1cbafb060c6f341`, annotated tag `phase3d-posthoc-research-boundary-freeze-v1`
Phase 4A decision: **EXTERNAL_CONFIRMATION_FEASIBLE_WITH_PROTOCOL_ADAPTATION**

**NO EXTERNAL FORECASTING MODEL WAS TRAINED.**

**NO EXTERNAL PREDICTIVE RESULT WAS INSPECTED.**

No new architecture was implemented. This checkpoint does not authorize Phase 4B or any scientific external run.

## Frozen-history and audit state

The Phase 3D validator passes and recursively verifies Phase 3C, Phase 3B, Phase 3A, Neural-v2, DLinear, LSTM, PatchTST, Phase 2A, both deterministic histories, all six TimeTrack raw files, and canonical panel SHA-256 `c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`. Phase 4A validation reports zero model fits, zero predictive outcomes inspected, and zero new architectures.

## External source and raw archive identity

| Dataset | Official source | Raw archive | Bytes | SHA-256 |
|---|---|---|---:|---|
| GWA-T-12 Bitbrains fastStorage | `https://atlarge-research.com/gwa-t-12/` | `gwa_t_12_fastStorage.zip` | 134,047,207 | `11313f528a0cbcbe57e63162f8ae5a41a9c7e7c1a79872e294ff3c5bbaa2e671` |
| GWA-T-12 Bitbrains Rnd | `https://atlarge-research.com/gwa-t-12/` | `gwa_t_12_rnd.zip` | 163,099,172 | `d3d9ddebb689c0b5463f2e4cfd8956e84bdcdf138b4476320855393e2b229a06` |
| GWA-T-13 Materna | `https://atlarge-research.com/gwa-t-13/` | `gwa_t_13_materna.zip` | 145,292,565 | `1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4` |

The archives remain ignored under `data/external/raw/` and are not part of Git. Alibaba 2018, Google 2019, and Azure VM traces were assessed from official metadata and were not downloaded.

## Structural audit identity and eligibility

| Artifact | SHA-256 |
|---|---|
| `01_dataset_audit/EXTERNAL_DATASET_STRUCTURAL_AUDIT.csv` | `9cf4b1be8330661b094009fd81d17619e7e48590861bab31898c0637fb114107` |
| `01_dataset_audit/ENTITY_STRUCTURAL_ELIGIBILITY.csv` | `ce5b8a3023912c2f7ce18df4f34a1e1b1f78ec87e2715dbf247b1d1879ff532b` |
| `01_dataset_audit/RAW_ARCHIVE_MANIFEST.csv` | `e493cbf7e554b49b77843e331bedf786aedbf0def076689044ccf5cae5ffedf1` |
| `01_dataset_audit/MATERNA_VM_OVERLAP.csv` | `bfaf5b0c2f72feec3081185cfef9c2c3fd9ce9b52eaa62a1204356f3f4485a74` |

Eligibility requires no duplicate timestamps, at least 14 days of coverage, at least 95% physically valid four-resource rows, nonconstant values for every required target, a median interval within one second of 300 seconds, and a contiguous run of at least 2,016 observations with no gap above 450 seconds. Physical validity is CPU in [0,100] and nonnegative throughput, memory, and disk-write.

| Environment | Raw entities/files | Structurally eligible |
|---|---:|---:|
| Bitbrains fastStorage | 1,250 | 916 |
| Bitbrains Rnd | 500 | 416 |
| Materna trace 1 | 519 | 475 |
| Materna trace 2 | 527 | 483 |
| Materna trace 3 | 547 | 495 |
| Materna shared across all three traces | 519 raw IDs shared | 398 eligible shared IDs |

The complete 3,343-row entity eligibility record is frozen without reduction.

## Selected entity cohorts

Selection is independent within each environment by ascending SHA-256 of `phase4a-v1|<environment>|<exact-VM-ID>`. Materna uses the fixed environment token `Materna-shared`. No resource correlation, persistence difficulty, forecast error, S1/S2/M1 result, or predictability enters the selection.

| Cohort | Candidates | Selected | Selected-ID-list SHA-256 | Selection-record SHA-256 |
|---|---:|---:|---|---|
| Bitbrains fastStorage | 916 | 35 | `97742a6e10858c9b8a021d3142419d66f41b2ac67e5944f95c2a4b8931f4632d` | `3ccbdb4d3615d323d54127f63eb72f588893d9bd48593a82dcccc10754a60b38` |
| Bitbrains Rnd | 416 | 35 | `5674f15382d5efb795cbda46a34f1f766e859413857475212023afc36ffcdc1a` | `5cfbd93103881a8af258ed9ecc6e317601c7b6b44825d2f790a1a81ed1731f9c` |
| Materna common cohort | 398 | 35 | `08705c602ca13ab47fd5b245fac5369f038c79747d9d079c61358d4ea5f45763` | `c9dcb3e0ad4ced836f865099ab16824ac1f33eb1659872f3be10e5025cd902fa` |

The exact records are in `03_evaluation_design/SELECTED_ENTITY_COHORTS.csv` (SHA-256 `bb30651b10fd23dc88cd9b14e4c54929ff1a80dced3b11d813e294ebbf9cca4e`). Materna is not part of primary confirmation execution.

## Dataset roles and independence

| Dataset | Frozen role | Independence classification |
|---|---|---|
| Bitbrains fastStorage | `PRIMARY_EXTERNAL_CONFIRMATION` | pristine for the present predictive question |
| Bitbrains Rnd | `PRIMARY_EXTERNAL_CONFIRMATION` | pristine for the present predictive question |
| Materna | `SECONDARY_EXTERNAL_REPLICATION` | prior exposure in separate DynAPM research |
| Alibaba 2018 | `STRUCTURALLY_INCOMPATIBLE` | not used; disk-write target absent |
| Google 2019 | `STRUCTURALLY_INCOMPATIBLE` | not used; network/disk-write targets absent |
| Azure VM traces | `STRUCTURALLY_INCOMPATIBLE` | not used; required dynamic tuple absent |
| Later TimeTrack telemetry | `NOT_NEEDED_UNLESS_OBTAINED` | unavailable locally; contact required |

Bitbrains fastStorage and Rnd are separate confirmation environments. Observations and VM identities must not be pooled. Results must be reported per environment before an equal-environment synthesis; synthesis must not be weighted by VM count.

## Resource order, targets, and transformations

The fixed external resource order is CPU, THROUGHPUT, MEMORY, DISK_WRITE.

| Resource | Bitbrains/Materna mapping | Transform | Native inversion |
|---|---|---|---|
| CPU | CPU usage % | identity | inverse robust scaler |
| THROUGHPUT | network received KB/s + network transmitted KB/s | log1p | inverse robust scaler, `expm1`, nonnegative projection |
| MEMORY | active/used memory KB | identity | inverse robust scaler |
| DISK_WRITE | disk write throughput KB/s | log1p | inverse robust scaler, `expm1`, nonnegative projection |

Each resource then uses a training-only median/IQR robust scaler. These are close semantic matches, not exact raw-unit replication of TimeTrack. Transforms cannot change after any external predictive result is inspected. Target mapping table SHA-256: `911e8642eca6d8b61d3b49cff5301fe975d2dca0b2a67c6d9f9bd72ea58ce1f9`.

## Elapsed-time horizons and contexts

Maximum alignment error is `max(2.5 minutes, 15% of desired duration)`. Every frozen mapping passes.

| Desired horizon | TimeTrack lead / actual minutes | Five-minute lead / actual minutes |
|---:|---|---|
| 5 min | 8 / 5.638 | 1 / 5 |
| 10 min | 16 / 11.276 | 2 / 10 |
| 20 min | 32 / 22.552 | 4 / 20 |
| 45 min | 64 / 45.104 | 9 / 45 |
| 90 min | 128 / 90.208 | 18 / 90 |

Horizon mapping SHA-256: `190b6f19234e08f1c3344d0223b2b993150efb9e8ba4ee33cb417bf33edb3d6d`.

| Desired context | TimeTrack | Five-minute external |
|---:|---|---|
| approximately 22.5 min | L32 / 22.552 min | L4 / 20 min |
| 45 min | L64 / 45.104 min | L9 / 45 min |
| 90 min | L128 / 90.208 min | L18 / 90 min |

Context mapping SHA-256: `14c44a5eb9fd90797c8e8823df203563ebbd9b143579c15bbcab23c5af1fb135`. These are elapsed-time conceptual matches, not identical sample-context replication.

## Frozen questions and replication type

- H1: Does S2 fail to provide broad per-resource improvement over S1?
- H2: Does M1 fail to provide broad per-resource improvement over S2?
- H3: Are cross-resource benefits heterogeneous rather than consistently positive across VMs, environments, resources, and horizons?

Bitbrains is a **CONCEPTUAL EXTERNAL REPLICATION** because sampling, units, and workload environment differ. It preserves the same four meanings, S1/S2/M1 factorial, plain-LSTM concept, common support, training-only scaling, seed treatment, matched comparisons, and resource-specific macro aggregation. No new architecture hypothesis exists.

## Publication scope and minimum evidence

The frozen preferred scope is **MULTI-DATASET EMPIRICAL BOUNDARY STUDY**: when cross-resource context and naive multi-task sharing help or fail in cloud telemetry forecasting. The intended contribution is empirical/methodological, not a new architecture, attention mechanism, loss, or optimizer. Manuscript writing is not authorized.

Before manuscript work: freeze the external protocol, selected IDs, and support/splits; independently execute and validate fastStorage, then Rnd; report H1-H3 separately; perform equal-environment synthesis; show duplicate/invalid handling does not determine conclusions; verify native inversion; and complete final literature and licensing/acknowledgement reviews. Materna may later strengthen replication but does not replace primary Bitbrains confirmation.
