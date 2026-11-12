# Stage 3B baseline training and checkpoint engine

The implementation follows the unchanged `review_revision/fgcs_strengthening/analysis_plan_v0.3.md` at SHA-256 `7b8f80be597148f5413582bf936d13a79bfc05d0725d734dfec83b5443246076`. No protocol deviation was identified.

## Files

- Created `src/training.py` for deterministic CPU fitting, validation, fresh refits and serialisable epoch state.
- Created `src/checkpoints.py` for strict epoch selection and logical task checkpoint planning.
- Extended `src/provenance.py` to verify full protocol seal coverage, read and authenticate completed inner outcomes, and publish immutable model-only checkpoints.
- Added `tests/test_training_selection.py`, `tests/test_final_refit.py`, `tests/test_checkpoint_selection.py`, `tests/test_determinism.py` and `tests/test_training_provenance.py`, with shared generated-data fixtures in `tests/training_fixtures.py`.
- Created this report.

## Training and checkpoints

The engine accepts a Stage 3A `PreparedPartition` bound to the exact core or M0 capacity identity and phase. The adapter supplies the frozen context, support and phase-specific scaler. Inner fits materialise only training and validation windows. Final fits materialise only the full legal outer-training windows, and require a matching completed inner outcome with the same context and split hashes before claiming an attempt. The final plan is reconstructed from the recorded inner validation history and bound to the byte SHA-256 of that outcome.

Each epoch shuffles only training origins using a dedicated CPU generator and consumes every training row, including the last short batch. Validation traverses its windows in their prepared order in eval mode. Adam uses learning rate 0.001 and batches of 256. One global gradient-norm clip at 1.0 runs before each optimiser step. S1 and S2 optimise the declared target's scaled MSE. M0 and M1 optimise the equal mean of the declared per-task scaled MSEs. The engine retains per-task training losses and validation losses for each observed epoch. Epoch summaries weight by origin count. Validation accumulates squared scaled errors in float64 across all origins and horizons, then gives the tasks equal weight.

The first strictly lowest joint validation MSE selects the epoch. Exact ties retain the earlier epoch and count towards the seven epochs of patience. The inner trajectory stops at patience or epoch 50. Final refits create a new model and empty Adam state from the same declared seed. An ordinary refit runs exactly to the selected epoch.

For the registered fastStorage/Rnd core M1 identities with seeds 0–2, four earliest task-specific epoch requests are derived solely from the observed joint inner trajectory. The final refit continues to the maximum requested epoch. It saves one model-only file per distinct epoch and keeps four logical task requests. The joint-selected checkpoint is written at its own epoch and remains the primary checkpoint. Tail optimisation and inner validation have timing fields separate from primary optimisation. The engine has no outer-test materialisation or prediction step.

## Determinism and provenance

Python, NumPy and Torch CPU RNG states are set from the declared seed inside an isolated trajectory scope and restored on exit. A separate Torch generator owns minibatch permutations. The serialisable epoch state includes model tensors and mode, Adam state, Python/NumPy/Torch CPU RNG state, the shuffle generator state, exact identity, fingerprint digest and the histories needed to reconstruct selection. The engine returns the last boundary as bytes and records its SHA-256. Requested deployment checkpoints contain model tensors only. Automatic resume and failed-run recovery were outside this stage.

The journal binds attempt and outcome records to the exact scientific identity and shared configuration/input/source seal. Outcomes include phase context, split/support/scaler hashes, initial and terminal parameter-state hashes, parameter count, selected epochs, training and validation losses, batch-order hashes, timings and checkpoint byte hashes where applicable. An error after an attempt records a terminal failure and retains available partial evidence. A missing or incompatible predecessor blocks the final request before claiming its attempt. Attempts, outcomes and checkpoint files use exclusive publication.

## Verification

Run from the repository root with the existing legacy Python environment.

```sh
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 old_fgcs_rejected/.venv_legacy/bin/python -B -m unittest -v \
  fgcs_strengthening_v03.tests.test_training_selection \
  fgcs_strengthening_v03.tests.test_final_refit \
  fgcs_strengthening_v03.tests.test_checkpoint_selection \
  fgcs_strengthening_v03.tests.test_determinism \
  fgcs_strengthening_v03.tests.test_training_provenance \
  fgcs_strengthening_v03.tests.test_identity \
  fgcs_strengthening_v03.tests.test_routing \
  fgcs_strengthening_v03.tests.test_parameter_counts \
  fgcs_strengthening_v03.tests.test_budget \
  fgcs_strengthening_v03.tests.test_preservation
```

**27 tests passed in 5.508 seconds** across 14 Stage 3B tests and 13 Stage 3A regression tests. Static Python compilation and whitespace checks passed. The Stage 3B fits and forwards in this suite use generated tensors only. Frozen input files are read for hash verification. The test suite covers strict improvement, earliest ties, patience reset, the 50-epoch cap, target-specific and equal-task losses, weighting of a short validation batch, fresh exact-length refits, outer-test exclusion, four observed-only task requests, deduplicated checkpoint bytes and hashes, and preservation of the primary checkpoint when extension occurs. Repeated same-identity runs matched initial weights, batch orders, validation histories, selected epochs and terminal weights. Changing the seed changed the initial state, batch order and terminal state. Restoring the serialised state reproduced the next optimisation epoch of an uninterrupted synthetic trajectory exactly.

The Stage 3B fingerprint covers 36 inputs and 22 sources. Its digest is `4b00560871e39b5e797c05bd0a202a22985065250c66f722e46109ca4433bf34`. The v0.3 JSON configuration remained at SHA-256 `59cda69a3e9b6b789aa09f70d2c606fce41a5d4b37d5a1d8dfe0a9b819cff62b`.

The before/after preservation inventory matched on path, mode, size, modification time and change time for 449,448 entries outside the namespace. Both inventories had SHA-256 `aeb829a9ae55f893f3a10363c451375bfceb5f211256b04231849e58b5f7944b`. The tracked-file status remained identical and no runtime journal or checkpoints remained after the tests.

## Stage 3C handoff

The baseline training and checkpoint engine has no blocker for gradient-diagnostic implementation. Scientific execution remains subject to the protocol's author approval, registration and host/software seal. No manuscript, supplement, submission, protocol or historical artifact was edited. No scientific training, inference, pilot, statistics, experiment or systems benchmark ran. No dependencies were installed or downloaded and no staging, commit, tag or push occurred.

STAGE03B_PASS
