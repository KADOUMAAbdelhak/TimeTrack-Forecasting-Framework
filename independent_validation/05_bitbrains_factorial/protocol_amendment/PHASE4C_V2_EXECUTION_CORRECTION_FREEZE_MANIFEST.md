# Phase 4C V2 Execution-Conformance Correction Freeze Manifest

## Identity

- Date: 2026-10-05 (Europe/Helsinki)
- Pre-correction HEAD: `5a643567f466c66a5134e41d8c0ae05f8b971763`
- Phase 4B commit/tag: `b162b8907f5f063ef969c02bd5d175edd3471028` /
  `phase4b-bitbrains-factorial-protocol-freeze-v1`
- Phase 4C V2 amendment commit/tag:
  `5a643567f466c66a5134e41d8c0ae05f8b971763` /
  `phase4c-bitbrains-training-scale-amendment-freeze-v1`
- Correction classification: `IMPLEMENTATION_CONFORMANCE_CORRECTION`
- Correction decision SHA-256:
  `bd0a51380409290dd9deefd2cf25bbc783b018b559121bd21ba37fdfcb07e86d`
- Unchanged V2 scientific config SHA-256:
  `627391b84887411d8b930fd5d00cdd9a1f90f3990f958d582f4329424353fa4e`
- Unchanged prospective criteria SHA-256:
  `79df6a168d7021dbafd6080640a506d22699e9d4989d422f924b178600465f12`

## Corrected defects

The runner previously defined `outputs/scientific_v2/` centrally but retained
two legacy literals for final models and predictions under
`outputs/scientific/`. All V2 paths now use one canonical relative root and
path builder. Inner/final completions, selections, models, predictions,
metrics, persistence, M1 loss histories, runtime, validation, and any future
analysis output therefore resolve beneath `outputs/scientific_v2/`.

Inner completion metadata explicitly records `outer_test_accessed=false`.
Successful final completion metadata explicitly records
`outer_test_accessed=true` only after the authorized evaluation, prediction
artifact persistence, and metric-record creation. Missing evaluation,
prediction persistence, or metric records prevents final completion metadata
from being emitted. Both phases also carry the correction-decision SHA-256, and
resumability rejects records without that identity.

Historical files under `outputs/scientific/` were not moved, deleted, read for
performance, or made reusable.

## Modified source and added tests

Modified source files:

- `independent_validation/05_bitbrains_factorial/run_phase4c_scientific.py`
- `independent_validation/05_bitbrains_factorial/validate_phase4c_environment.py`
- `independent_validation/05_bitbrains_factorial/protocol_amendment/validate_phase4c_v2_protocol.py`

Added regression suite:

- `independent_validation/05_bitbrains_factorial/tests/test_phase4c_v2_execution_conformance.py`

The tests cover V2 model/prediction/completion routing, absence of legacy path
returns, inner/final access flags, prevention of premature final completion,
failure-before-access behavior, old-record rejection, and unchanged config and
criteria hashes.

## Verification

- New regression tests: **13 passed**.
- Full relevant Phase 4B/Phase 4C suite: **58 passed**.
- Independent corrected V2 validation: **PASS**.
- Diff audit: **PASS**, with no scientific-setting differences.
- Historical amendment tag resolves to
  `5a643567f466c66a5134e41d8c0ae05f8b971763`; its 29-entry inventory SHA-256
  remains `323b5a0ca9ba1a7c0180a4faf973f74676dd6a40f99106ab497ebf51baeb4dc0`
  and tree SHA-256 remains
  `3fa66a780e4e87553325ae8bb136d31289f560c37fce20f1f3a2be514bb6de74`.
- Valid V2 scientific fits: **0/37,800**.
- Optimizer executions during correction: **0**.
- V2 outer-test target accesses: **0**.
- V2 outer-test predictions: **0**.
- Predictive outcomes inspected: **0**.
- Preserved pre-amendment records: **154**, reused: **0**.

## Scientific invariance

The V2 config, cohorts, eligibility, support, folds, leads, contexts, resources,
transforms, scaler, S1/S2/M1 architectures, optimizer and training settings,
M1 loss, selection objective, epoch lifecycle, physical inversion, metrics,
aggregation, bootstrap, and H1/H2/H3 criteria are unchanged.

**THIS CHECKPOINT CHANGES EXECUTION CONFORMANCE ONLY.**

**NO SCIENTIFIC PROTOCOL SETTING WAS CHANGED.**

No Phase 4C scientific execution was started.
