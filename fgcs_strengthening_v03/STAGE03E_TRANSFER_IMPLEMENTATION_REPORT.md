# Stage 3E empirical-transfer implementation

Implemented the pairwise and leave-one-out study in §7 of `review_revision/fgcs_strengthening/analysis_plan_v0.3.md`. The protocol and configuration SHA-256 values remain `7b8f80be597148f5413582bf936d13a79bfc05d0725d734dfec83b5443246076` and `59cda69a3e9b6b789aa09f70d2c606fce41a5d4b37d5a1d8dfe0a9b819cff62b`, respectively. No protocol deviation was identified.

## Files created or changed

- `src/transfer/design.py` defines fixed subset identities, directed entries, BH family slots and dry budget checks.
- `src/transfer/estimands.py` validates matched native-MAE grids and calculates entity and complete-cohort F/Q effects.
- `src/transfer/runner.py` exposes one-identity fit and explicit post-fit evaluation calls.
- `plan_execution.py` reuses the transfer identity enumerator. `src/training.py` admits the two registered arms through the existing equal-loss path. `src/provenance.py` seals the transfer design and journals one evaluation independently of the final fit.
- `tests/test_transfer_routing.py`, `tests/test_transfer_identities.py`, `tests/test_transfer_estimands.py`, `tests/test_transfer_matrices.py` and `tests/test_transfer_runner.py` cover the transfer layer. `tests/test_training_provenance.py` verifies the updated source inventory count.

## Identity, routing and dry schedule

The registered scope is the 35 frozen V2-ranked entities in each of fastStorage and Rnd, all five folds, seeds 0–2 and H64. The runner consumes the Stage 3A verified phase partition, which supplies the exact v1 M1 context, support and scaler. The enumerator uses all six unordered pairs and all four triples formed by omitting one task. Scientific identity canonicalises task ordering, so reversing a pair preserves its ID.

Each fit uses a single shared encoder, retains only the requested heads and optimises the equal mean of the retained scaled task MSEs with the existing Adam and epoch-selection lifecycle. Own-input sharing reuses the size-1 M0 encoder separately across retained task histories. All-input sharing uses the size-4 M1 encoder for every retained task and keeps the omitted output task's input history.

| Registered arm | Inner | Final | Total |
| --- | ---: | ---: | ---: |
| Pairwise, both input scopes | 12,600 | 12,600 | 25,200 |
| Leave-one-out, both input scopes | 8,400 | 8,400 | 16,800 |
| **Transfer total** | **21,000** | **21,000** | **42,000** |

The transfer-only and full planners enumerated the same set of transfer identities. The full v0.3 fit and wrapper budget remains 174,500. The transfer study reuses its corresponding core comparisons.

## Estimands and matrix registration

F is ln(A_independent/A_shared-subset), where A is native MAE averaged over the prescribed horizons, folds and seeds 0–2 within an entity before taking the log. S1 supplies own-input reference cells and common-context S2 supplies all-input reference cells. Q is ln(A_shared-without-source/A_full-shared), using the same three-seed core M0 or M1 slice. Positive F favours sharing and positive Q favours adding the omitted task's supervision. Q compares operational fits and does not isolate a causal task effect.

The analytical tests give +ln(2) for an aggregate numerator of 4 and denominator of 2, and −ln(2) after reversal, for both F and Q with their registered numerator/denominator roles. For varying cells with numerator fold + seed + lead and denominator 2, the entity aggregates are 10.8 and 2 and the effect is ln(5.4). The code rejects extra seeds, duplicate cells and wrong comparators. Missing cells, mismatched support/context/scaler and nonfinite MAE make the result unavailable. Zero cell MAEs contribute to averages. Zero aggregates preserve the registered extended ratio/log or undefined result. A cohort mean requires all 35 available entity effects.

Each environment/scope has twelve directed pairwise F entries, twelve leave-one-out F entries and twelve descriptive Q entries in canonical target-then-source order. A pairwise source is the sharing partner. In a leave-one-out entry the source names the omitted supervision. The eight fixed F families each have 12 slots at BH q=.05, giving 96 planned tests. Unavailable slots retain raw p=1. Available slots carry a pending p-value for the later statistics implementation. Q is excluded from all BH families. No bootstrap or significance calculations ran.

## Fit and evaluation boundary

`TransferRunner.fit` runs one declared subset identity and the final phase requires the matching completed inner outcome. It invokes no outer-test materialisation. `TransferRunner.evaluate` is a distinct explicit call that first verifies the completed final outcome, the matching partition metadata and the primary checkpoint. It then uses the saved checkpoint to calculate native-unit MAE by retained task and horizon on the ordered test origins. The same explicit evaluation path can read completed registered core comparator fits on seeds 0–2. A successful evaluation can supply typed inputs to the estimand code. Fit and evaluation claims and outcomes are independently write-once. Failures remain terminal, and repeat requests cannot rematerialise the test set through the runner.

The combined seal covers 36 inputs and 32 sources with digest `2c0cb0a3bc32fca25f1a29f567a05d9083cc0d42bdb27762df1af586b8f3a9b0`.

## Tests, preservation and elapsed time

Commands from the repository root.

```sh
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  old_fgcs_rejected/.venv_legacy/bin/python -B -m unittest discover -s fgcs_strengthening_v03/tests -v
old_fgcs_rejected/.venv_legacy/bin/python -B -m fgcs_strengthening_v03.src.transfer.design
```

**72 tests passed in 42.211 seconds**, including 16 Stage 3E tests and 56 Stage 3A–3D regression tests. Static compilation and whitespace checks passed. The before/after preservation inventory matched for 449,448 paths outside the implementation namespace on path, mode, size, modification time and change time, with SHA-256 `aeb829a9ae55f893f3a10363c451375bfceb5f211256b04231849e58b5f7944b`. The tracked-file status was identical and no runtime test journal remained. All fitting, model forwards and MAE evaluation in the tests used synthetic data. The existing Stage 3A conformance tests read frozen inputs to verify supports, scalers and window preparation without running models on those data. Manuscript, supplement, submission files, protocol and historical artifacts were preserved. No scientific run, dependency install/download, Git staging, commit, tag or push occurred.

**Stage 3E wall-clock elapsed time was 9 min 30 s**, from the first repository check at `2026-11-11T12:15:52+00:00` to report finalisation at `2026-11-11T12:25:22+00:00`.

## Stage 3F handoff

No implementation blocker for Stage 3F. No scientific transfer identities were executed.

STAGE03E_PASS
