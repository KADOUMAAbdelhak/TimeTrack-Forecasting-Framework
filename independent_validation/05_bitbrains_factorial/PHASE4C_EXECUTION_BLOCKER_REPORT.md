# Phase 4C Execution Blocker Report

Date: 2026-09-30 (Europe/Helsinki)  
Status: **STOPPED — FROZEN IQR-ZERO GATE TRIGGERED**

## Executive finding

Phase 4C cannot be completed under the frozen Phase 4B protocol. Stage A
fastStorage stopped automatically during S1 inner fitting when a required
training partition produced `IQR_ZERO_STOP` in the frozen robust-scaler fit.

The frozen rule is explicit: every transformed and native training-partition
IQR must be greater than zero; there is no epsilon fallback, alternate scaler,
clipping, cohort substitution, or silent omission. Phase 4C therefore stopped
without modifying the protocol.

No final refit, outer-test target access, outer-test prediction, comparison,
scientific analysis, H1/H2/H3 result, figure, Rnd fit, or Materna run occurred.

## Frozen identities and pre-execution state

- Phase 4B commit: `b162b8907f5f063ef969c02bd5d175edd3471028`
- Phase 4B tag: `phase4b-bitbrains-factorial-protocol-freeze-v1`
- Phase 4B decision SHA-256: `247197a787250f9e81ea3b858a9f79dd8f5377d548da2fbc2bdec514e420b81e`
- Phase 4B config SHA-256: `deedcd31616861f1f6ee4517cc0552a05d54d0b334364f9674b06a1dcab6dc1a`
- Phase 4C prospective criteria SHA-256: `79df6a168d7021dbafd6080640a506d22699e9d4989d422f924b178600465f12`
- Phase 4B tests before execution: 45 passed
- Independent Phase 4B validation before execution: PASS
- Scientific fits before execution: 0
- Outer-test predictions before execution: 0
- H1/H2/H3 results before execution: 0

The criteria record and `PRE_EXECUTION_IDENTITY.json` predate every Phase 4C
scientific fit and outer-test prediction.

## Partial execution state

| Item | Count |
|---|---:|
| Completed fastStorage S1 inner fits | 154 |
| Completed fastStorage S2 inner fits | 0 |
| Completed fastStorage M1 inner fits | 0 |
| Completed final refits | 0 |
| Rnd scientific fits | 0 |
| Outer-test target accesses | 0 |
| Outer-test predictions | 0 |
| Scientific comparisons | 0 |
| H1/H2/H3 results | 0 |

All 154 completion records have status `complete`, belong to fastStorage VM
697, and explicitly record `outer_test_accessed=false`. They are preserved as
resumable provenance and were not deleted or interpreted.

## Full training-only IQR audit

The technical audit checked every required inner-train and prospective
outer-train scaler partition for all frozen VMs, folds, and contexts. It used
training partitions only and did not access outer-test targets or predictions.

| Environment | Affected VMs | Affected VM-folds | Unique failing scaler partitions | Inner-train partitions | Outer-train partitions | Resource-level failure cells |
|---|---:|---:|---:|---:|---:|---:|
| fastStorage | 10 | 50 | 297 | 150 | 147 | 585 |
| Rnd | 13 | 62 | 366 | 183 | 183 | 525 |
| Combined | 23 | 112 | 663 | 333 | 330 | 1,110 |

Affected fastStorage VMs:

`52, 58, 563, 733, 757, 813, 908, 947, 1111, 1225`

Affected Rnd VMs:

`184, 276, 283, 350, 370, 381, 391, 404, 448, 454, 480, 486, 491`

Resource-level zero-IQR counts:

| Environment | CPU | THROUGHPUT | MEMORY | DISK_WRITE |
|---|---:|---:|---:|---:|
| fastStorage | 198 | 240 | 57 | 90 |
| Rnd | 120 | 357 | 0 | 48 |

Every listed failure has transformed IQR and/or native IQR equal to zero. The
exact 1,110 environment/VM/fold/context/split/resource records are preserved in
`outputs/scientific/validation/IQR_ZERO_FAILURES.csv`.

The earliest affected fastStorage VM in frozen cohort order is VM 1225. Its
fold-1 L4 inner-training partition has zero IQR for CPU, THROUGHPUT, and
DISK_WRITE, so the shared four-resource scaler cannot be fitted under the
frozen rule.

## Why execution cannot continue

Any continuation requires at least one prospective scientific change:

- replace or reduce frozen VM cohorts;
- define a zero-IQR scaling policy or alternate denominator;
- change the common four-resource scaling/model eligibility rule; or
- declare the planned confirmation infeasible under the frozen protocol.

Each option changes a frozen Phase 4B scientific setting. None is authorized by
the current Phase 4C request, and choosing among them requires a new prospective
decision before any additional scientific fit or outer-test access.

The completed 154 inner fits may be reused only if a new prospective decision
explicitly preserves their identities and scaler semantics. Otherwise they
must be treated as superseded provenance, not silently mixed with a revised
protocol.

## Required next state

`NEW_PROSPECTIVE_PROTOCOL_DECISION_BEFORE_RESUME`

Phase 4C remains scientifically unanalysed. The pristine outer-test confirmation
boundary remains intact.
