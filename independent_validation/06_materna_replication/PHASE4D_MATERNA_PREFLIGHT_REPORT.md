# Phase 4D Materna Secondary-Replication Preflight Report

Date: 2026-10-08

Scope: training-scale audit, protocol preflight, and explicitly non-scientific timing pilot only

Validation: **PASS**

No full Materna scientific execution was started. Materna scientific forecasting fits = **0**; scientific outer-test target accesses = **0**; outer-test predictions = **0**; scientific predictive outcomes inspected = **0**.

## 1. Historical integrity

- HEAD is `d9c8ed80a90085d989d1dacc40f1c27377a4a76f`.
- Annotated tag `phase4c-v2-bitbrains-external-confirmation-freeze-v1` resolves to that commit.
- Sixteen frozen checkpoint tags passed exact target verification.
- Phase 4C analysis and scientific checkpoint, execution, execution-conformance correction, training-scale amendment, Phase 4B, Phase 4A, Phase 3D, Phase 3C, Phase 3B, Phase 3A, Neural-v2, DLinear, LSTM, PatchTST, Phase 2A, and corrected deterministic inventories passed SHA-256 and entry verification. Four Phase 4C amendment entries intentionally superseded by the later execution-correction freeze were validated against that later inventory.
- TimeTrack raw inputs passed 6/6 exact hashes. The canonical panel hash remains `c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`.
- Bitbrains raw archives remain `11313f528a0cbcbe57e63162f8ae5a41a9c7e7c1a79872e294ff3c5bbaa2e671` (`fastStorage`) and `d3d9ddebb689c0b5463f2e4cfd8956e84bdcdf138b4476320855393e2b229a06` (`Rnd`).

## 2. Materna raw identity

The raw archive `gwa_t_13_materna.zip` has SHA-256 `1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4`, exactly matching the prospective identity.

Raw file counts are 519 (T1), 527 (T2), and 547 (T3). Materna-T1, T2, and T3 are consecutive temporal environments from the same Materna source, not three independent datasets.

## 3. Structural shared cohort

The frozen Phase 4A structural rules reproduce 475 eligible VMs in T1, 483 in T2, and 495 in T3. Their exact three-trace intersection contains **398 VMs**.

## 4. Training-scale audit

The prospective eligibility key is `(trace, VM_ID, fold, phase, L)`. For each of 398 shared VMs, the audit covered 3 traces × 5 folds × 2 phases × 3 contexts = 90 unique scaler partitions, or **35,820 partitions** and **143,280 transformed resource-partition cells**. Formulation is absent from the key because S1, S2, and M1 use the same training partition scaler semantics.

A VM qualifies only when every transformed CPU, throughput, memory, and disk-write training partition has IQR > 0. No fallback or epsilon was used, and no predictive outcome entered eligibility. Native/transformed gate disagreements = 0.

## 5. Zero-IQR prevalence

Across 11,940 partitions per trace and resource:

| Trace | CPU | Throughput | Memory | Disk write |
|---|---:|---:|---:|---:|
| Materna-T1 | 187 (1.5662%) | 5,070 (42.4623%) | 171 (1.4322%) | 3,088 (25.8626%) |
| Materna-T2 | 123 (1.0302%) | 5,167 (43.2747%) | 150 (1.2563%) | 3,120 (26.1307%) |
| Materna-T3 | 135 (1.1307%) | 5,186 (43.4338%) | 108 (0.9045%) | 3,004 (25.1591%) |

Resource-cell failures total 445 CPU, 15,423 throughput, 429 memory, and 9,212 disk-write. Unique partitions with at least one failure total 5,796 in T1, 5,702 in T2, and 5,778 in T3.

Across all resource cells, failure counts by fold are 5,175, 5,124, 5,094, 5,087, and 5,029 for folds 1–5. Counts are 12,817 for inner and 12,692 for final partitions; by context they are 8,507 (L4), 8,506 (L9), and 8,496 (L18).

## 6. Final scale-eligible pool

Of 398 structurally shared VMs, **74** are `MATERNA_TEMPORAL_SCALE_ELIGIBLE`; 324 are rejected. Retention is **18.5929648241%**. Because 74 ≥ 35, the cohort-sufficiency gate passes without loosening any scaler or scientific requirement.

## 7. Candidate 35-VM cohort

After filtering for structural and scale eligibility, the cohort is the first 35 VMs under ascending SHA-256 of `phase4a-v1|Materna-shared|<exact-VM-ID>`:

`74, 134, 397, 266, 380, 281, 393, 227, 128, 299, 272, 08, 75, 133, 440, 306, 343, 305, 26, 302, 498, 103, 303, 76, 493, 416, 478, 442, 246, 345, 04, 98, 105, 92, 508`.

Four Phase 4A selections are retained: `74, 134, 266, 397`. The 31 replaced Phase 4A IDs are `17, 30, 65, 78, 84, 131, 140, 148, 159, 167, 198, 204, 220, 222, 228, 240, 253, 274, 297, 310, 338, 352, 385, 399, 408, 445, 448, 452, 494, 497, 518`. Replacement IDs are `04, 08, 26, 75, 76, 92, 98, 103, 105, 128, 133, 227, 246, 272, 281, 299, 302, 303, 305, 306, 343, 345, 380, 393, 416, 440, 442, 478, 493, 498, 508`.

## 8. Cohort hashes

- Candidate ID-list SHA-256: `4c9e8f4cfa5cf26c4188924c486cdfbe9d78972eec1f84f5e0f23b1e94353140`
- Selection-record SHA-256: `63c1a7266057c4344bfd6211ee7d3fd2deba283e4b41797fc4e412483469b24b`
- Predictive outcomes used for selection: 0

## 9. Support counts

The exact L18-common four-resource support contains **1,575 records**: 525 per trace (35 VMs × 5 folds × 3 contexts). S1/S2/M1 formulation mismatches = 0, support-minimum failures = 0, candidate-cohort zero-IQR failures = 0, and target-time leakage violations = 0. The 3,150 candidate scaler partitions (inner/final) all pass.

Support hashes are stored per trace/VM/fold/context and were independently reproduced for all 1,575 records.

## 10. Segmentation

Cleaning preserves legal contiguous 300-second segments independently by trace and VM. The candidate cohort yields 268 segments: 113 in T1 (289,802 observations), 78 in T2 (308,126), and 77 in T3 (359,943). No legal origin crosses a segment.

## 11. Transforms

Resource order is CPU, THROUGHPUT, MEMORY, DISK_WRITE. CPU usage percent and memory usage KB use identity transforms. Throughput is received KB/s plus transmitted KB/s followed by `log1p`; disk-write throughput KB/s uses `log1p`. Training-only median/IQR robust scaling has no fallback and no epsilon.

## 12. Horizons

Sample leads are exactly `[1, 2, 4, 9, 18]`, corresponding at 300-second cadence to `[5, 10, 20, 45, 90]` minutes. All five future four-resource target tuples must be finite and remain within the legal segment.

## 13. Contexts

Contexts are exactly `[4, 9, 18]`, approximately `[20, 45, 90]` minutes. L18 defines common support; shorter contexts receive no additional origins.

## 14. Splits

Materna-T1, T2, and T3 are separate temporal replication blocks. Each independently uses five chronological expanding outer folds, the latest 15% of legal outer-training support for inner validation, common four-resource support, and maximum-horizon target-time purge. Cross-trace train/validation/test splitting is prohibited.

## 15. Architecture

The frozen plain-LSTM factorial is unchanged:

- S1: `[N,L,1] → [N,5]`, one model per resource, 50,757 parameters/model.
- S2: `[N,L,4] → [N,5]`, one independent model per target, 51,525 parameters/model.
- M1: `[N,L,4]` shared encoder with four heads → `[N,4,5]`, 52,500 parameters total.

No new architecture was implemented.

## 16. Training and selection

Frozen defaults are Adam, learning rate 0.001, batch 256, maximum 50 epochs, patience 7, gradient clipping 1.0, and seeds `[0,1,2]`. M1 minimizes the equal mean of the four resource MSE losses.

S1 and S2 select context independently per trace/VM/fold/resource using mean inner-validation NMAE across five horizons and three seeds; ties choose smaller L. M1 selects one context per trace/VM/fold using equal resource mean validation NMAE across four resources, five horizons, and three seeds. Each seed retains its own best epoch. A future final refit must start from scratch on full legal outer training at the selected fixed epoch and evaluate outer test once. None of these scientific selections or refits ran during preflight.

## 17. Replication questions

No new hypotheses are introduced. R1 asks whether S2 benefit remains resource/time-block dependent; R2 whether M1 again lacks broad improvement over S2; R3 whether M1 again lacks broad improvement over S1; and R4 whether effects vary across T1/T2/T3.

## 18. Classification rules

For each trace and resource, the Bitbrains thresholds are frozen unchanged:

- `BROAD_POSITIVE`: overall gain ≥ +1%, positive horizons ≥ 4/5, VMs ≥ 25/35, folds ≥ 4/5, seeds ≥ 2/3.
- `CONDITIONALLY_POSITIVE`: overall > 0, positive horizons ≥ 3/5, VMs ≥ 15/35, folds ≥ 3/5, seeds ≥ 2/3, and not broad positive.
- `BROAD_NEGATIVE`: overall ≤ −1%, positive horizons ≤ 1/5, VMs ≤ 10/35, folds ≤ 1/5, seeds ≤ 1/3.
- Otherwise: `NEUTRAL_OR_MIXED`.

## 19. Equal-temporal-block synthesis

Each trace must be reported first. Any combined point estimate is the unweighted arithmetic mean `(gain_T1 + gain_T2 + gain_T3) / 3`, labelled **EQUAL-TEMPORAL-BLOCK SYNTHESIS**. It is not an independent-dataset meta-analysis and is not weighted by duration, origins, rows, or prediction count.

## 20. Bootstrap

Future analysis uses 10,000 paired VM-cluster bootstrap replicates separately within each trace. Sampling unit is VM; all folds and paired formulation structure are retained. The deterministic Phase 4C RNG policy is preserved. T1/T2/T3 are not treated as independent bootstrap units.

## 21. Workload

| Scope | S1 inner | S1 final | S2 inner | S2 final | M1 inner | M1 final | All fits | Metrics | Selected contexts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Per trace | 6,300 | 2,100 | 6,300 | 2,100 | 1,575 | 525 | 18,900 | 31,500 | 1,575 |
| Three traces | 18,900 | 6,300 | 18,900 | 6,300 | 4,725 | 1,575 | **56,700** | **94,500** | **4,725** |

Combined inner fits = 42,525; final fits = 14,175. The arithmetic was verified programmatically.

## 22. Non-scientific timing pilot

Only the authorized first SHA-ranked VM (`74`) was used. The pilot trained exactly 27 models: nine per trace, fold 1, seed 0, L9, exactly five epochs, inner train/validation only. It ran four S1 resource models, four S2 target models, and one M1 model per trace.

| Trace | Formulation | Models | Mean sec/epoch | Sum 5-epoch fit sec | Mean samples/sec | Peak RSS bytes |
|---|---:|---:|---:|---:|---:|---:|
| T1 | S1 | 4 | 0.087336 | 2.378309 | 40,132.73 | 369,983,488 |
| T1 | S2 | 4 | 0.083989 | 1.821118 | 41,684.32 | 370,786,304 |
| T1 | M1 | 1 | 0.088204 | 0.477130 | 39,691.87 | 371,376,128 |
| T2 | S1 | 4 | 0.092475 | 1.998319 | 40,497.48 | 381,976,576 |
| T2 | S2 | 4 | 0.090804 | 1.963527 | 41,242.78 | 382,074,880 |
| T2 | M1 | 1 | 0.094466 | 0.510618 | 39,643.98 | 382,205,952 |
| T3 | S1 | 4 | 0.104624 | 2.253482 | 41,472.27 | 391,380,992 |
| T3 | S2 | 4 | 0.104035 | 2.240870 | 41,707.40 | 391,659,520 |
| T3 | M1 | 1 | 0.108845 | 0.585818 | 39,864.14 | 392,069,120 |

Scientific predictive metrics computed = 0; scientific context selections = 0; scientific final refits = 0; outer-test targets accessed = 0; outer-test predictions generated = 0.

## 23. Runtime and storage projection

| Effective epochs | Combined fit-hours / 1-worker wall-hours | Four-worker wall-hours |
|---:|---:|---:|
| 10 | 22.1698 | 5.5424 |
| 25 | 55.4244 | 13.8561 |
| 50 | 110.8488 | 27.7122 |

At 25 effective epochs, per-trace four-worker projections are 4.2001 hours (T1), 4.4835 (T2), and 5.1725 (T3). The retained-storage projection is 4,383,480,273 bytes: 2,960,437,725 model bytes, 1,324,557,600 prediction bytes, and 98,484,948 metric/manifest bytes. Heavy scientific outputs created during preflight = 0.

## 24. Compute gate

**FULL_35_VM_THREE_TRACE_REPLICATION_EXPENSIVE_BUT_FEASIBLE**.

This decision uses only support, scale eligibility, runtime, memory, storage, and implementation correctness. Predictive performance used = 0. No cohort reduction is authorized automatically.

## 25. Publication role

Materna is frozen as **SECONDARY TEMPORAL REPLICATION**, not pristine independent confirmation, because of prior exposure in separate DynAPM research and the shared, consecutive temporal structure. Its role is temporal robustness, additional environment evidence, constraint on generalizability, clarification of the mixed H1 boundary, and an additional test of the H2 negative-sharing boundary. It cannot upgrade itself to pristine confirmation or retrospectively change TimeTrack, Bitbrains, H1/H2/H3, or the Phase 4C conclusions.

## Independent validation conclusion

`PHASE4D_MATERNA_PREFLIGHT_VALIDATION.json` reports **PASS**. Exact archive and frozen-history identities, scale eligibility, deterministic cohort selection, candidate support, target-time purge, formulation equality, architecture, training settings, workload, and pilot access boundaries were independently reproduced. Full Materna scientific execution remains unauthorized and has not begun.
