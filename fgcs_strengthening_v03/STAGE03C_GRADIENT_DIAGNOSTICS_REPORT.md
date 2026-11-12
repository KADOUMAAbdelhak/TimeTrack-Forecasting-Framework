# Stage 3C gradient diagnostics

The implementation follows `review_revision/fgcs_strengthening/analysis_plan_v0.3.md`, SHA-256 `7b8f80be597148f5413582bf936d13a79bfc05d0725d734dfec83b5443246076`. The v0.3 configuration remained at SHA-256 `59cda69a3e9b6b789aa09f70d2c606fce41a5d4b37d5a1d8dfe0a9b819cff62b`. No protocol deviation was identified.

## Files created or changed

- `src/diagnostics/batches.py` implements deterministic origin draws and ordered manifest hashes.
- `src/diagnostics/gradients.py` implements clone-only extraction and live-state fingerprints.
- `src/diagnostics/metrics.py` implements pair scores, slot scores and secondary diagnostics.
- `src/diagnostics/aggregation.py` implements complete-grid entity and Materna aggregation.
- `src/diagnostics/engine.py` implements one journalled slot invocation bound to a completed final fit.
- `src/checkpoints.py`, `src/training.py` and `src/provenance.py` now schedule, save and authenticate the required diagnostic checkpoints.
- `tests/test_diagnostic_batches.py`, `tests/test_gradient_extraction.py`, `tests/test_gradient_noise_floor.py`, `tests/test_diagnostic_state_isolation.py` and `tests/test_gradient_aggregation.py` cover the diagnostic requirements. `tests/training_fixtures.py` accepts the diagnostic seal for synthetic final fits.

## Batch and checkpoint semantics

The engine draws from the verified final partition's ordered outer-training windows. Each slot has eight independently keyed A/B pairs, with 128 origins sampled with replacement per draw. Each key is UTF-8 `fgcs-v03|block|exact_entity_id|fold|seed|slot|pair_index|A_or_B`. The implementation uses pair indices 0–7 and the existing slot labels `epoch0`, `mid` and `final`. The first eight SHA-256 digest bytes, interpreted little-endian, seed a fresh NumPy PCG64 generator. Ordered IDs, indices and per-draw hashes are retained in a hashed manifest. Every task on a draw uses the same input rows and forward pass.

M0 and M1 core final fits save states at epoch 0, ceil(E_joint/2) and E_joint. Logical slot identities and batch manifests remain separate when physical epochs coincide. Matching deployment checkpoints are reused by reference. The journal authenticates the parent final outcome, checkpoint byte hash and tensor hash before extracting gradients. The final M1 slot at E_joint is the primary endpoint. The other M1 slots and all M0 slots are descriptive. A task-checkpoint tail after E_joint does not change its state or score.

## Gradient and score semantics

Extraction runs on an isolated CPU float32 model clone in eval mode. For each task, `autograd.grad` differentiates the task's scaled MSE averaged over origins and horizons before joint loss weighting. Encoder gradients are concatenated in the exact order `weight_ih_l0`, `weight_hh_l0`, `bias_ih_l0`, `bias_hh_l0`, `weight_ih_l1`, `weight_hh_l1`, `bias_ih_l1`, `bias_hh_l1`. Heads and optimiser state are excluded.

For each A/B pair, C is the fraction of the six same-A cross-task dots below zero. N is the fraction of the four same-task A/B dots below zero. K_pair is C−N. Exact zero dot products contribute zero to the conflict count. Any exact zero gradient norm makes that pair unavailable and its undefined cosines are recorded as null, with the slot, pair, side and task retained. K is the mean of all eight K_pair values only when all eight are available. A slot with zero-gradient evidence is explicitly recorded as unavailable and retains its secondary outputs.

Secondary outputs include cross-task and same-task dots, cosines and norm ratios, per-draw task norms, zero-gradient counts, negative-cosine frequencies with defined denominators, and a task-pair frequency matrix. Entity K requires all 25 final-slot M1 scores from the five folds and five seeds. Materna K requires all three trace scores for the same exact VM. Missing or unavailable components yield an unavailable aggregate. The implementation performs no association tests.

## State isolation and provenance

The guard hashes live parameters, buffers, module modes, optimiser state, existing gradients, Python RNG, NumPy RNG, Torch CPU RNG and the training shuffle generator before and after each claimed slot. A mismatch is a terminal failure. Diagnostics use neither the training loader nor its generator and their elapsed time is recorded separately from optimisation timing. The test suite verified all guard categories, demonstrated terminal failure under intentional shuffle-generator contamination and rejected a tampered synthetic checkpoint.

The immutable diagnostic outcome binds the final-fit identity and outcome SHA-256, checkpoint SHA-256, exact partition fingerprints, batch-manifest hash and shared source/config/input fingerprint. Duplicate claims are rejected. Partial technical failure retains the current draw and any completed pair evidence, with no primary score. The Stage 3C fingerprint covers 36 inputs and 27 sources and has digest `27e445f44a87b1b7f2a39537b935445cdcf3b8382c09293bb191c6b57bac99f8`.

## Tests and preservation

Full suite command from the repository root.

```sh
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  old_fgcs_rejected/.venv_legacy/bin/python -B -m unittest discover -s fgcs_strengthening_v03/tests -v
```

**42 tests passed in 37.927 seconds**, comprising 13 Stage 3C tests and 29 Stage 3A–3B regression tests. Static compilation and whitespace checks passed. All diagnostic extraction and model fitting in these tests used synthetic data. The existing Stage 3A adapter conformance tests read frozen data for support/scaler verification and window preparation. They invoked no model on those data.

The before/after preservation inventory matched for 449,448 entries outside the new namespace on path, mode, size, modification time and change time. Both inventories had SHA-256 `aeb829a9ae55f893f3a10363c451375bfceb5f211256b04231849e58b5f7944b`. The tracked-file status was identical and no runtime journal remained.

## Stage 3D handoff

There is no implementation blocker for PCGrad/GradNorm development. PCGrad and GradNorm implementation is deferred to Stage 3D. No scientific diagnostic execution, training, inference, pilot, experiment or association testing ran. The manuscript, supplement, submission files, protocol and frozen artifacts were preserved. No dependencies were installed or downloaded. No staging, commit, tag or push occurred.

STAGE03C_PASS
