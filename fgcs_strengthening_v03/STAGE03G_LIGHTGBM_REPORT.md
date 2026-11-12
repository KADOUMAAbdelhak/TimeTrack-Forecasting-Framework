# Stage 3G deterministic LightGBM baseline

Implemented the registered LightGBM baseline in §8 of `review_revision/fgcs_strengthening/analysis_plan_v0.3.md`. The protocol SHA-256 remains `7b8f80be597148f5413582bf936d13a79bfc05d0725d734dfec83b5443246076` and the configuration SHA-256 remains `59cda69a3e9b6b789aa09f70d2c606fce41a5d4b37d5a1d8dfe0a9b819cff62b`. No protocol deviation was identified.

## Files created or changed

- `src/models/lightgbm.py` defines the registered feature layout, scalar estimator settings, model serialisation and native scoring.
- `src/tree/design.py` implements the fixed grid, wrapper identities, validation selector and dry accounting.
- `src/tree/runner.py` runs one declared wrapper or one explicit post-fit evaluation using the existing journal and frozen adapter.
- `plan_execution.py` reuses the LightGBM identity enumerator. `src/provenance.py` seals the planner dependency and adds write-once storage and verification for the five final scalar models.
- Added `tests/test_lightgbm_features.py`, `tests/test_lightgbm_selection.py`, `tests/test_lightgbm_runner.py` and `tests/test_lightgbm_budget.py`. Updated the sealed source-count expectation in `tests/test_training_provenance.py`.

## Features, grid and selection

The scope is fastStorage and Rnd, the 35 frozen V2-ranked entities in each, all five folds, seed 0 and four target resources. The runner consumes the Stage 3A prepared partition for exact v1 M1 context, splits, phase scaler and transforms. Each wrapper fits separate scalar models at leads 1, 2, 4, 9 and 18.

For an input of shape `[origin, lag, resource]`, own-input features contain the declared target's L values from oldest to newest. All-input features concatenate the CPU, THROUGHPUT, MEMORY and DISK_WRITE histories, each oldest to newest, producing 4L values. Feature names record lag L−1 first and lag 0 last for each resource. The exact ordered names are embedded in the fitted model and checked on load.

The eight configurations are the Cartesian product of leaves 15/31, learning rates 0.03/0.05 and configured estimator counts 200/400. The installed LightGBM 4.7.0 received `regression_l1`, `random_state=0`, `n_jobs=1`, deterministic column-wise training and full row and column sampling. Predictions use all fitted trees on one thread. Per-model provenance records the realised tree count as well as the fixed configured estimator count. Suppressed library logging is an operational setting.

Each inner wrapper fits only on legal inner-training rows, scores its five horizons after inverse transformation on the legal validation rows and averages the five native MAEs equally. The final selector requires all eight authenticated candidates with identical inner support and scaler. Exact score ties select fewer leaves, then the lower learning rate, then fewer estimators. The final wrapper creates five fresh estimators for that configuration and fits them on the complete legal outer-training set. No fitting path materialises the outer-test windows.

## Explicit evaluation and provenance

The evaluation entry point verifies the completed final record and all five model artifacts before accessing outer-test windows. It returns one native MAE cell per horizon with block, entity, fold, target, scope, final model identity, model hash, context value and hashes for context, support, scaler and ordered test origins. The context hash includes the exact frozen context-source fingerprint. No scientific effect calculation is performed.

The journal records LightGBM version, estimator and native parameter mappings, exact feature order, inner native MAEs and prediction hashes, selected configuration and candidate outcome hashes, scalar model hashes and the shared input/config/source seal. Inner model hashes are retained in the outcome. Final scalar models are retained as separate hashed LightGBM text artifacts for later evaluation. Fit and evaluation records are independently write-once. Invalid or incomplete candidates cannot feed final selection. A nonfinite fit or prediction fails its claimed identity and no automatic retry or fallback occurs.

On generated data, repeat runs reproduced every inner validation score and scaled/native forecast hash, the selected configuration, scalar model hashes and explicit test prediction hashes in both input scopes. A tampered synthetic final model was rejected before test materialisation. The combined seal covers 36 inputs and 43 sources with digest `bc6e72d7b5010cb2735f883c6b6f105b844a4a75f8808967bec9db3f4b6b24d8`.

## Dry accounting

| Phase | Wrapper fits | Scalar estimator fits |
| --- | ---: | ---: |
| Inner | 22,400 | 112,000 |
| Final | 2,800 | 14,000 |
| **Total** | **25,200** | **126,000** |

The full planner and LightGBM-only planner enumerate the same identities. Each wrapper represents one target and five direct scalar fits. Seed 0 is the only seed identity.

## Tests and preservation

```sh
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  old_fgcs_rejected/.venv_legacy/bin/python -B -m unittest discover -s fgcs_strengthening_v03/tests -v
old_fgcs_rejected/.venv_legacy/bin/python -B -m fgcs_strengthening_v03.src.tree.design
```

**97 tests passed in 55.327 seconds**, including 10 Stage 3G tests and 87 Stage 3A–3F regression tests. Source compilation and whitespace checks passed. The before/after preservation inventory matched on path, mode, size, modification time and change time for 449,448 entries outside the implementation namespace. Both inventories had SHA-256 `aeb829a9ae55f893f3a10363c451375bfceb5f211256b04231849e58b5f7944b`. The tracked-file status was identical and no test journal remained. All test fits and predictions used generated data. The existing Stage 3A conformance tests read frozen inputs for support and scaler checks without running models on those inputs. Manuscript, supplement, submission files, protocol and historical artifacts were preserved. No scientific fits, inference or experiments ran. No dependencies were installed or downloaded. No staging, commit, tag or push occurred.

**Wall-clock start:** `2026-11-11T13:19:26+00:00` (first repository check). **End:** `2026-11-11T13:27:51+00:00` (report finalisation). **Elapsed:** 8 min 25 s.

## Stage 3H handoff

No implementation blocker for Stage 3H. All scientific LightGBM identities remain unexecuted.

STAGE03G_PASS
