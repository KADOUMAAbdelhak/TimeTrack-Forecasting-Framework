# Phase 4D Materna Three-Trace Scientific-Execution Freeze Manifest

Date: 2026-10-14

Scope: completed scientific execution and technical validation only; no scientific formulation comparison or interpretation.

## Frozen checkpoints and identities

- Execution-conformance checkpoint: `5e7a42acf47dc0f14a73e7188c17831629f2229d` (`phase4d-materna-execution-conformance-freeze-v1`)
- Scientific-protocol checkpoint: `c4077318bfbb02e112b439baa3ae7a0e35db0dc5` (`phase4d-materna-secondary-replication-protocol-freeze-v1`)
- Scientific configuration SHA-256: `064ef5a4864f5590b8149242c4011c37a49aee35cf60a4690f6aa126b98fce27`
- Materna archive SHA-256: `1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4`
- Selected cohort SHA-256: `4c9e8f4cfa5cf26c4188924c486cdfbe9d78972eec1f84f5e0f23b1e94353140`
- Execution-conformance decision SHA-256: `3f5a780128f0d7931a44078d2f55f8168e3b444d51d2eb03cd635266b6bd368b`

## Exact execution counts

| Scope | S1 inner | S1 final | S2 inner | S2 final | M1 inner | M1 final | Inner | Final | Total | Metrics | Contexts | Models | Predictions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Materna-T1 | 6300 | 2100 | 6300 | 2100 | 1575 | 525 | 14175 | 4725 | 18900 | 31500 | 1575 | 4725 | 4725 |
| Materna-T2 | 6300 | 2100 | 6300 | 2100 | 1575 | 525 | 14175 | 4725 | 18900 | 31500 | 1575 | 4725 | 4725 |
| Materna-T3 | 6300 | 2100 | 6300 | 2100 | 1575 | 525 | 14175 | 4725 | 18900 | 31500 | 1575 | 4725 | 4725 |
| Combined | 18900 | 6300 | 18900 | 6300 | 4725 | 1575 | 42525 | 14175 | 56700 | 94500 | 4725 | 14175 | 14175 |

## Persistence and resumability provenance

Persistence rows are **31500** for T1, **31500** for T2, and **31500** for T3; combined **94500**. The schema and count are consistent across all traces and were not interpreted scientifically.

Unique successful scientific completions: **56700**. Valid resumed/skipped completion encounters: **14175**, all in **1** resumed T1 invocation. Preserved failed attempts: **1**. Retried fits: **1**. Permanently failed fits: **0**. Pilot reuse: **0**.

T1 contains one preserved non-reusable attempt-1 failure after outer-test access; the same exact scientific run identity later completed successfully. Attempt history was not erased.

## Technical validation and outer-test provenance

Corrected preflight, isolated empty-namespace implementation conformance, T1, T2, T3, combined validation, and the 42-test regression suite all pass. Every violation class recorded by the per-trace validators is zero, including identity, resumability, pilot reuse, support/target mismatch, segment crossing, leakage, scaler/transform, context/epoch selection, lifecycle, resource/horizon order, inversion/projection, metric recomputation, namespace, trace mixing, and outer-test metadata.

Inner successful completions with incorrect outer-test access: **0**. Final successful completions without outer-test access: **0**. Successful final lifecycle failures: **0**.

Successful final completions require the fixed-epoch refit, one authorized outer-test evaluation, prediction persistence, metric persistence, and artifact-hash validation before atomic completion publication.

## Trace isolation

All traces use the same exact frozen 35 VM IDs: **True**. Cross-trace run-ID collisions: **0**. Trace-mixing violations: **0**. T1, T2, and T3 training and validation namespaces remain isolated.

## Selected-L distributions

| Trace | Formulation | L4 | L9 | L18 |
|---|---|---:|---:|---:|
| Materna-T1 | S1 | 96 | 156 | 448 |
| Materna-T1 | S2 | 179 | 155 | 366 |
| Materna-T1 | M1 | 55 | 57 | 63 |
| Materna-T2 | S1 | 97 | 161 | 442 |
| Materna-T2 | S2 | 126 | 179 | 395 |
| Materna-T2 | M1 | 43 | 60 | 72 |
| Materna-T3 | S1 | 106 | 122 | 472 |
| Materna-T3 | S2 | 157 | 161 | 382 |
| Materna-T3 | M1 | 44 | 44 | 87 |

Complete per-resource S1/S2 selected-L distributions are preserved in `outputs/scientific_v1/runtime/selected_L_epoch_diagnostics.json` without relation to outer-test performance.

## Selected-epoch descriptive summaries

| Trace | Formulation | Count | Mean | Median | Min | Q25 | Q75 | Max |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Materna-T1 | M1 | 525 | 33.387 | 36.0 | 2 | 19.0 | 48.0 | 50 |
| Materna-T1 | S1 | 2100 | 32.646 | 35.0 | 1 | 19.0 | 48.0 | 50 |
| Materna-T1 | S2 | 2100 | 30.269 | 31.0 | 1 | 17.0 | 46.0 | 50 |
| Materna-T2 | M1 | 525 | 37.242 | 43.0 | 4 | 26.0 | 49.0 | 50 |
| Materna-T2 | S1 | 2100 | 32.314 | 35.0 | 1 | 19.0 | 48.0 | 50 |
| Materna-T2 | S2 | 2100 | 30.545 | 32.0 | 1 | 17.0 | 47.0 | 50 |
| Materna-T3 | M1 | 525 | 30.846 | 32.0 | 2 | 19.0 | 45.0 | 50 |
| Materna-T3 | S1 | 2100 | 30.602 | 31.0 | 1 | 19.0 | 45.0 | 50 |
| Materna-T3 | S2 | 2100 | 27.149 | 26.0 | 1 | 15.0 | 40.0 | 50 |

These are technical selection diagnostics only; no relationship to predictive performance was calculated.

## Runtime accounting

| Trace | S1 inner h | S1 final h | S2 inner h | S2 final h | M1 inner h | M1 final h | Total fit h | Elapsed h | Utilization | Mean fit s | Median fit s | Peak RSS MiB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Materna-T1 | 19.134379 | 8.468749 | 16.706893 | 6.908583 | 4.484401 | 1.597623 | 57.300628 | 27.897161 | 51.3499% | 10.914405 | 8.484284 | 550.281 |
| Materna-T2 | 18.670151 | 8.193477 | 17.640580 | 7.536233 | 5.069523 | 1.947918 | 59.057882 | 24.360462 | 60.6083% | 11.249120 | 8.797102 | 558.266 |
| Materna-T3 | 21.379311 | 9.748173 | 18.928511 | 7.582386 | 5.198363 | 2.107255 | 64.943999 | 16.355305 | 99.2705% | 12.370286 | 9.762382 | 599.609 |

Combined fit-hours: **181.302509126**. Combined elapsed accounting: **247006.542057 seconds** (**68.612928 hours**).

## Storage and artifact accounting

| Category | Bytes |
|---|---:|
| Models | 2989430325 |
| Predictions | 2617203098 |
| Metrics | 125572510 |
| Selections | 1035812 |
| Loss histories | 183840884 |
| Completions | 419200192 |
| Persistence | 683745 |
| Runtime | 46327 |
| Validation | 6290 |

Heavy execution inventory: **141785 / 141785 PASS**, **6381741517 bytes**. Inventory SHA-256: `8484e62b2dae596ece90308c18ea617ec904ea55ceb4fbfc76e2fcaa55dd1718`. Execution-tree SHA-256: `3d9a6ffe1b7d520bc5ca0e3f36e147f39e87590c88f8289a26c962a09e6756e1`.

Large model and prediction artifacts remain local and are identified by the full inventory; they are not duplicated or staged by this checkpoint.

## Historical chain

Historical tag and inventory verification: **PASS** across 18 frozen tags, including Phase 4D execution conformance and protocol, Phase 4C analysis/execution/amendment/conformance, Phase 4B, Phase 4A, Phase 3D/3C/3B/3A, Phase 2 histories, Neural-v2, raw/canonical TimeTrack identities, Bitbrains archives, and the Materna archive.

## Scientific-analysis lock

At this checkpoint: T1 was not scientifically interpreted before T2; T1/T2 were not scientifically interpreted before T3; no S2-vs-S1, M1-vs-S2, or M1-vs-S1 gain was calculated; no formulation ranking or resource classification was assigned; no bootstrap uncertainty or equal-temporal-block synthesis was run; R1/R2/R3/R4 were not evaluated; no TimeTrack/Materna or Bitbrains/Materna scientific comparison was performed; scientific comparison figures = **0**; and no publication conclusion was modified.

**THE 56,700-FIT THREE-TRACE MATERNA EXECUTION WAS COMPLETE AND TECHNICALLY VALID BEFORE ANY PHASE 4D SCIENTIFIC FORMULATION COMPARISON, TEMPORAL SYNTHESIS, OR R1/R2/R3/R4 INTERPRETATION.**
