# Phase 4D Materna Three-Trace Execution and Technical Validation Report

## Outcome

Phase 4D technical execution and validation **PASS** for Materna-T1, Materna-T2, and Materna-T3. This report contains no scientific comparison or interpretation.

## Frozen identities

- Execution checkpoint: `5e7a42acf47dc0f14a73e7188c17831629f2229d` (`phase4d-materna-execution-conformance-freeze-v1`)
- Historical protocol: `c4077318bfbb02e112b439baa3ae7a0e35db0dc5` (`phase4d-materna-secondary-replication-protocol-freeze-v1`)
- Configuration SHA-256: `064ef5a4864f5590b8149242c4011c37a49aee35cf60a4690f6aa126b98fce27`
- Archive SHA-256: `1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4`
- Cohort SHA-256: `4c9e8f4cfa5cf26c4188924c486cdfbe9d78972eec1f84f5e0f23b1e94353140`
- Selection-record SHA-256: `63c1a7266057c4344bfd6211ee7d3fd2deba283e4b41797fc4e412483469b24b`
- Execution-conformance SHA-256: `3f5a780128f0d7931a44078d2f55f8168e3b444d51d2eb03cd635266b6bd368b`

## Counts and validation

| Scope | Inner | Final | Fits | Metric rows | Selected contexts | Models | Predictions | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Materna-T1 | 14175 | 4725 | 18900 | 31500 | 1575 | 4725 | 4725 | PASS |
| Materna-T2 | 14175 | 4725 | 18900 | 31500 | 1575 | 4725 | 4725 | PASS |
| Materna-T3 | 14175 | 4725 | 18900 | 31500 | 1575 | 4725 | 4725 | PASS |
| Combined | 42525 | 14175 | 56700 | 94500 | 4725 | 14175 | 14175 | PASS |

Unique run IDs: **56700**. Cross-trace collisions: **0**. Namespace, access, trace-identity, and permanent-failure violations: **0**.

Persistence records: **94,500** combined (**31,500** per trace), verified on the final matched support without scientific interpretation.

## Resumability and failures

- Unique successful completions: **56700**
- Valid skipped/resumed fit encounters: **14175**
- Preserved failed attempt records: **1**
- Retried fits later completed successfully: **1**
- Permanently failed fits: **0**

The single preserved T1 attempt-1 record is non-reusable failure provenance. Its exact run identity subsequently completed successfully; it is not a permanent failure.

## Runtime accounting

| Trace/stage | S1 inner | S1 final | S2 inner | S2 final | M1 inner | M1 final | Total fit-hours |
|---|---:|---:|---:|---:|---:|---:|---:|
| Materna-T1 | 19.134 | 8.469 | 16.707 | 6.909 | 4.484 | 1.598 | 57.301 |
| Materna-T2 | 18.670 | 8.193 | 17.641 | 7.536 | 5.070 | 1.948 | 59.058 |
| Materna-T3 | 21.379 | 9.748 | 18.929 | 7.582 | 5.198 | 2.107 | 64.944 |

Combined fit-hours: **181.303**. Combined elapsed accounting: **68.613 h**.

- Materna-T1: elapsed 27.897 h; mean/median fit 10.91/8.48 s; four-worker utilization 51.35%; peak RSS 550.3 MiB.
- Materna-T2: elapsed 24.360 h; mean/median fit 11.25/8.80 s; four-worker utilization 60.61%; peak RSS 558.3 MiB.
- Materna-T3: elapsed 16.355 h; mean/median fit 12.37/9.76 s; four-worker utilization 99.27%; peak RSS 599.6 MiB.

## Selected-L and selected-epoch diagnostics

Complete formulation-level and S1/S2 resource-level distributions are recorded in `outputs/scientific_v1/runtime/selected_L_epoch_diagnostics.json`. They are selection diagnostics only and were not correlated with outer-test performance.

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

## Storage and artifact identity

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

The full scientific_v1 inventory contains **141785 files** and **6381741517 bytes**. Inventory SHA-256: `8484e62b2dae596ece90308c18ea617ec904ea55ceb4fbfc76e2fcaa55dd1718`. Execution-tree SHA-256: `3d9a6ffe1b7d520bc5ca0e3f36e147f39e87590c88f8289a26c962a09e6756e1`.

## Scientific-analysis lock

No formulation gains, rankings, signs, classifications, cross-trace scientific comparisons, bootstrap results, R1/R2/R3/R4 decisions, or scientific comparison figures were produced. Predictive metric values were used only inside the technical integrity validators; this report performs no scientific analysis.
