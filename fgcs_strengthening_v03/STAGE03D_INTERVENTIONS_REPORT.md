# Stage 3D registered M1 interventions

Implemented the two optimisation interventions from `review_revision/fgcs_strengthening/analysis_plan_v0.3.md`. The protocol SHA-256 remains `7b8f80be597148f5413582bf936d13a79bfc05d0725d734dfec83b5443246076` and the configuration SHA-256 remains `59cda69a3e9b6b789aa09f70d2c606fce41a5d4b37d5a1d8dfe0a9b819cff62b`. No protocol deviation was identified.

## Files created or changed

- `src/optim/pcgrad.py` and `src/optim/gradnorm.py` implement the registered updates and expose step diagnostics.
- `src/training.py` admits the declared intervention modes and records their histories using the existing identity, validation and final-refit lifecycle.
- `src/provenance.py` adds write-once publication for GradNorm optimiser states under the new runtime namespace.
- `tests/test_pcgrad.py`, `tests/test_gradnorm.py` and `tests/test_intervention_training.py` cover analytical and end-to-end synthetic cases. `tests/test_training_provenance.py` checks the two additional sealed sources.

## PCGrad

Each ordinary training forward yields four unweighted resource MSEs. The encoder gradients are flattened per task and copied into projected rows. Each task gets its own PCG64 stream derived from the SHA-256 key `fgcs-v03|pcgrad|seed|epoch|batch|task`, using the first eight digest bytes little-endian. Epochs are one-based and batch indices zero-based. Permutations use neither the data-loader generator nor the ambient Python, NumPy or Torch RNGs.

Each current projected row is compared with the other task's immutable original row. Projection occurs only for a negative dot and positive squared reference norm. The projected encoder rows are averaged. Head gradients come from the ordinary mean task loss. The assembled model gradient receives one global clip at 1.0 before Adam at 0.001. The step API returns the assembled encoder mean before clipping. The journal stores its hash and norm, permutation seeds and orders, original and sequential pre/post dots, projection counts, zero-direction skips, pre-clip model norm and optimiser settings.

## GradNorm

The first actual shuffled training minibatch supplies the four reference losses, using its training-mode forward before either update. Each L_i is scaled MSE divided by four. With unit weights, J is the baseline mean MSE. The norm uses all four registered layer-2 tensors, `weight_ih_l1`, `weight_hh_l1`, `bias_ih_l1` and `bias_hh_l1`.

The implementation computes q_i, r_i, G_i and detached mean(G) × r_i^1.5 from the same pre-update state. For positive w_i, G_i equals |w_i| times the norm of the detached unweighted gradient over W. The weight objective sums absolute deviations and differentiates only the weights. The model gradient uses detached pre-update weights. The weight Adam step at 0.025 precedes global clipping and the model Adam step at 0.001, using the saved gradients. Renormalisation to a weight sum of four is applied after the model step. Zero subgradients are retained at absolute-value and norm ties. Invalid reference losses, rates, proposed weights or nonfinite quantities fail the identity without an alternate loss or weight clamp.

Each step records reference and current losses, q, r, norms, targets, weight objective, weight gradient, proposed and renormalised weights, and the clipping and renormalisation values. The outcome references a hashed, immutable artifact containing both Adam states, terminal task weights and reference losses. This state is also exposed in the serialisable epoch boundary.

## Analytical and integration evidence

| Case | Expected and observed |
| --- | --- |
| PCGrad aligned vectors and a zero reference | No projections and two zero-direction skips |
| PCGrad (1,0) versus (−1,1) | Projected rows (0.5,0.5) and (0,1), mean (0.25,0.75), two projections, both post-projection dots zero |
| PCGrad three-task order sensitivity | First row (0.2,−0.1) for order 1→2 and (0.2,0.2) for order 2→1 |
| GradNorm q = (1,2,1,2) | r = (2/3,4/3,2/3,4/3). For G = (2,6,2,3), targets ≈ (1.769076,5.003702,1.769076,5.003702), objective ≈ 3.461848 and weight derivative (2,3,4,−6) |
| GradNorm analytical layer-2 gradients | Norms √30 × (1,2,3,4), including both bias tensors |
| GradNorm invalid first reference or proposed weight | Terminal failure. An invalid proposed weight prevents the model Adam step |

`equal_loss` remains the default for core and capacity identities. The explicit `pcgrad` and `gradnorm` modes require their corresponding declared M1 identities and cannot borrow the equal-loss inner selection. Inner validation uses the same unweighted MSE as before. Final refits initialise afresh and follow their own mode's selected epoch without materialising outer-test windows. Synthetic inner/final reruns matched exactly for each intervention across histories, selected epochs, batch orders and model-state hashes. Provenance tests rejected duplicate intervention claims and verified optimiser-state and outcome hashes.

The pre/post Stage 3D trajectory check hashed canonical inner/final histories, selection and initial/terminal model-state hashes. Both sides matched byte-for-byte for all four baseline formulations. Runtime timings and the updated source seal were outside the trajectory comparison.

| Baseline | Matching pre/post SHA-256 |
| --- | --- |
| S1 | `bcebe61c2e2b4a3d0fd03d6cde8ec58352219b52907b35116de07ef700e4473f` |
| S2 | `7c8c7319bf71ce54a6d2701abb257098df1839f0352e3c66f268aabab72f2fd4` |
| M0 | `57e782f847048007826ec8d4a907e188a45ff5734dd569f14f921c2277073718` |
| M1 | `489df219476e3d71cb8f52d820ebba0eebe986afe8108cee2d41f2071d039f98` |

The training seal covers 36 inputs and 24 sources with digest `48800afa6673dd5473480012b0a9c6f40706e6a0b6f6c36f846244a1fbd4b3e4`. The combined training/diagnostic seal covers 36 inputs and 29 sources with digest `0e700ec457720b8cde200cae3f94188cccb2615bad02024a0363356c848556e7`.

## Tests and preservation

Full regression command from the repository root.

```sh
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  old_fgcs_rejected/.venv_legacy/bin/python -B -m unittest discover -s fgcs_strengthening_v03/tests -v
```

**56 tests passed in 40.116 seconds**, comprising 14 Stage 3D tests and 42 Stage 3A–3C regression tests. Static compilation and whitespace checks passed. The before/after inventory matched for all 449,448 paths outside the implementation namespace on mode, size, modification time and change time, with SHA-256 `aeb829a9ae55f893f3a10363c451375bfceb5f211256b04231849e58b5f7944b`. Tracked-file status remained identical and the test journals were removed. All fitting, model forwards and gradient calculations used generated tensors. The existing Stage 3A adapter tests read frozen data for input, support and scaler conformance without running models on those data. The manuscript, supplement, submission files, protocol and historical artifacts were preserved. No scientific intervention, training, inference, diagnostic, pilot or experiment ran. No dependencies were installed or downloaded. No staging, commit, tag or push occurred.

## Handoff

No implementation blocker for the next stage. The registered author approval, registration and host/software seal remain pre-execution requirements.

STAGE03D_PASS
