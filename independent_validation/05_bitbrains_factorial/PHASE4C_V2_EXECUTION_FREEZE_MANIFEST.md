# Phase 4C V2 Dual-Environment Scientific-Execution Freeze Manifest

## Checkpoint identity

- Freeze date: 2026-10-07 (Europe/Helsinki)
- Pre-freeze HEAD: `30cb7b042726b6e6db8c6bf5ed43324b620ca42e`
- Phase 4B checkpoint: `b162b8907f5f063ef969c02bd5d175edd3471028` / `phase4b-bitbrains-factorial-protocol-freeze-v1`
- Phase 4C V2 training-scale amendment checkpoint: `5a643567f466c66a5134e41d8c0ae05f8b971763` / `phase4c-bitbrains-training-scale-amendment-freeze-v1`
- Phase 4C V2 execution-conformance checkpoint: `30cb7b042726b6e6db8c6bf5ed43324b620ca42e` / `phase4c-v2-execution-conformance-freeze-v1`
- V2 config SHA-256: `627391b84887411d8b930fd5d00cdd9a1f90f3990f958d582f4329424353fa4e`
- Prospective criteria SHA-256: `79df6a168d7021dbafd6080640a506d22699e9d4989d422f924b178600465f12`
- Execution-correction decision SHA-256: `bd0a51380409290dd9deefd2cf25bbc783b018b559121bd21ba37fdfcb07e86d`
- Full relevant test suite: **58 passed**
- Isolated prospective V2 protocol validation: **PASS**
- fastStorage technical validation: **PASS**
- Rnd technical validation: **PASS**
- Combined technical validation: **PASS**

**THE 37,800-FIT DUAL-ENVIRONMENT EXECUTION WAS COMPLETE AND TECHNICALLY VALID BEFORE ANY PHASE 4C SCIENTIFIC AGGREGATION OR H1/H2/H3 INTERPRETATION.**

## Exact frozen cohorts

The exact 70-row cohort is preserved in
`protocol_amendment/PHASE4C_V2_SELECTED_COHORTS.csv` (SHA-256
`a56192c6d0f7c3274b0899a18cc6b2748586d5a3950ca79a40692358e9617ccf`).
No VM replacement occurred.

| Environment | VMs | ID-list SHA-256 | Selection-record SHA-256 |
|---|---:|---|---|
| `GWA-T-12_Bitbrains_fastStorage` | 35 | `ff2d65ff43bedae076f913e4b9e175e7762d835eafe5efc8c2a2590e487fc07c` | `168ccae403488cc06a60b5a2d6da1c57a88f32f793c4356bcecdfa4bf445d648` |
| `GWA-T-12_Bitbrains_Rnd` | 35 | `f175f8b443adbed472caf5a2b26f9d73f989faf9f68334e520655c33ae982d2e` | `09f6b782a8cc5df7683e1dccf6a05551b0bf91daa64fde7868c1c145f48f0357` |

## Exact execution counts

| Scope | Inner fits | Final fits | Total fits | Metrics | Persistence | Selected contexts | Selected epochs | Models | Predictions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fastStorage | 14,175 | 4,725 | 18,900 | 31,500 | 31,500 | 1,575 | 4,725 | 4,725 | 4,725 |
| Rnd | 14,175 | 4,725 | 18,900 | 31,500 | 31,500 | 1,575 | 4,725 | 4,725 | 4,725 |
| Combined | **28,350** | **9,450** | **37,800** | **63,000** | **63,000** | **3,150** | **9,450** | **9,450** | **9,450** |

All 37,800 fits were unique new V2 fits. Failed fits, retried fits, permanently
failed fits, invalid-identity reuse, and pre-amendment reuse were all zero.

## Resumption and pre-amendment provenance

The Rnd execution was interrupted and resumed. The resumable runner recognized
and skipped **9,211** already-complete V2 fit encounters whose full frozen run
identity and artifacts validated. These skips are not additional fits and are
not pre-amendment reuse. fastStorage had zero resumed/skipped encounters.

The **154** historical records remain labelled
`ABORTED_PRE_AMENDMENT_PROVENANCE`; all remain non-reusable and **0** were
reused. Their frozen CSV SHA-256 is
`bf8b21b878b3203608084dc215793a927b8d1d4bc349decfc169e6fbe4a2d049`.

## Support, scaler, lifecycle, and technical integrity

- Frozen support manifest SHA-256: `690677c99d4e7cb3b790bf4ef60041282d28877deaa75d5cc53ced400490ce22`
- Frozen scaler-partition SHA-256: `50e8af2151c8e2170089073791405e23da7dd99cdeb0269edbbb2bacfbd0d1ca`
- Support records: 1,050 total, 525 per environment
- Scaler partitions: 2,100 total, 30 per VM
- Zero-IQR failures: 0

The combined technical validator recorded zero for every protected failure
class: invalid identity reuse, pre-amendment reuse, support mismatch, target-ID
mismatch, history or target segment crossing, inner or outer leakage, zero-IQR
scaler fit, scaler fallback, transform or scaler leakage, context-selection or
epoch-selection mismatch, final-refit lifecycle mismatch, resource-order or
horizon-order mismatch, inverse-transform or projection mismatch, metric
recomputation mismatch, namespace violation, outer-test-access metadata
violation, environment-isolation violation, and permanently failed fits.

Inner completion records have `outer_test_accessed=false`. Final completion
records have `outer_test_accessed=true` only after the fixed-epoch refit,
single authorized outer-test evaluation, prediction persistence, metric-record
creation, and artifact validation. No unauthorized outer-test access occurred.

## Runtime accounting

| Environment/stage | S1 inner | S1 final | S2 inner | S2 final | M1 inner | M1 final | Total fit-hours |
|---|---:|---:|---:|---:|---:|---:|---:|
| fastStorage | 13.408 | 5.518 | 13.136 | 5.016 | 4.130 | 1.543 | 42.752 |
| Rnd | 38.974 | 16.204 | 36.323 | 12.380 | 10.842 | 3.372 | 118.095 |

- Combined fit-hours: **160.847**
- Combined elapsed accounting: **41h 4m 19.5s**
- fastStorage elapsed: **10h 49m 4.6s**; mean/median fit **8.14/5.82 s**;
  four-worker utilization **98.80%**; peak RSS **539.7 MiB**
- Rnd elapsed: **30h 15m 14.9s**; mean/median fit **22.49/16.81 s**;
  four-worker utilization **97.59%**; peak RSS **764.8 MiB**

## Selected-context and selected-epoch identity

| Environment | Formulation | L4 | L9 | L18 |
|---|---|---:|---:|---:|
| fastStorage | S1 | 158 | 164 | 378 |
| fastStorage | S2 | 201 | 167 | 332 |
| fastStorage | M1 | 66 | 42 | 67 |
| Rnd | S1 | 120 | 151 | 429 |
| Rnd | S2 | 184 | 161 | 355 |
| Rnd | M1 | 57 | 64 | 54 |

The complete selected-epoch distributions are preserved, without scientific
interpretation, in
`outputs/scientific_v2/runtime/combined_runtime_storage_accounting.json`.
Selected-epoch artifact SHA-256 identities are:

- fastStorage: `9d971c60c16def9f84e79a2dec22e50889d9356f0c8aeaf13b708e03a28d2058`
- Rnd: `df48933ca57689cc56d9bbb51cc593b5fce47030c8cc56378a7819acceaa92c2`

## Storage and heavy-artifact identity

| Category | Bytes |
|---|---:|
| Models | 1,982,823,150 |
| Predictions | 2,977,637,056 |
| Metrics | 3,703,431 |
| Selections | 854,086 |
| Loss histories | 15,059,575 |
| Completions | 267,140,824 |
| Total inventoried | **5,295,782,138** |

The complete execution contains **56,723** inventoried files, approximately
**4.932 GiB**. The complete execution artifact inventory SHA-256 is
`42e085403d331bc903afd484582bf4d57c68477513ef6a948c3d40c2c5cf4377`;
the execution-tree SHA-256 is
`deeea76548071f08915d2c80944da4a196e1032e62a918c6e5753dd887e0c1c0`.
The approximately 1.98 GB of models and 2.98 GB of predictions remain local
and ignored; the checkpoint commits their complete path, size, and digest
inventory rather than duplicating them in Git.

## Historical chain verification

Current-tree verification found zero modified artifacts in the corrected
deterministic inventories, Neural-v2 protocol and DLinear/LSTM/PatchTST
inventories, Phase 3A/3B/3C/3D inventories, and Phase 4A/4B inventories. The
historical Phase 4C amendment was verified at its tag because the later
execution-conformance checkpoint intentionally superseded four implementation
files; its 29-entry inventory and tree also pass. The execution-correction
10-entry inventory passes in the current tree.

All requested annotated tags resolve to their frozen commits: Phase 4A, Phase
4B, Phase 3D, Phase 3C, Phase 3B, Phase 3A, Neural-v2 protocol, DLinear, LSTM,
PatchTST, Phase 2A, corrected deterministic, Phase 4C amendment, and Phase 4C
execution-conformance. TimeTrack raw inputs pass 6/6, canonical panel SHA-256
is `c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`,
and all three Bitbrains raw archive hashes pass.

## Scientific-analysis lock

No predictive metric value was inspected during technical validation. No
scientific gain or formulation comparison has been calculated, no bootstrap
has been run, H1/H2/H3 remain unevaluated, and comparison, synthesis, and
scientific-figure artifact counts are all zero. Materna was not executed.

This checkpoint freezes completed execution and technical provenance only. It
does not authorize or contain Phase 4C scientific aggregation or interpretation.
