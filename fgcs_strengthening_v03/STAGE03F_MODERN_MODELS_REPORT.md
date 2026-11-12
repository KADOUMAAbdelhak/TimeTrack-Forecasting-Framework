# Stage 3F modern-model generalisation and pilot framework

Implemented the reduced modern-model study in §8 of `review_revision/fgcs_strengthening/analysis_plan_v0.3.md`. The protocol and configuration SHA-256 values remain `7b8f80be597148f5413582bf936d13a79bfc05d0725d734dfec83b5443246076` and `59cda69a3e9b6b789aa09f70d2c606fce41a5d4b37d5a1d8dfe0a9b819cff62b`. No protocol deviation was identified.

## Files created or changed

- `src/models/dlinear.py`, `src/models/patchtst.py` and `src/models/itransformer.py` implement the three families. `src/models/_transformer.py` builds their common encoder configuration, and `src/models/registry.py` binds the model, scope and optimiser for each family.
- `src/modern/design.py` provides dry enumeration and exact pilot membership checks. `src/modern/structure.py` provides synthetic structural validation. `src/modern/runner.py` provides one-identity fits, sealed family validation, failure handling and explicit pilot reuse.
- `src/training.py` exposes preparation, model and validation hooks for the modern runner and records its selected inner checkpoint. `plan_execution.py` reuses the modern identity enumerator. `src/provenance.py` seals the new planner dependency.
- Added `tests/test_dlinear.py`, `tests/test_patchtst.py`, `tests/test_itransformer.py`, `tests/test_modern_routing.py`, `tests/test_modern_training.py` and `tests/test_modern_pilot_plan.py`. Updated the source-count expectation in `tests/test_training_provenance.py`.

## Architectures and parameter counts

- **DLinear.** Replicate-padded moving averages use kernels 3, 9 and 17 at L=4, 9 and 18. Biased L→5 projections map trend and residual separately and their forecasts are summed. An independent model takes one declared resource. A shared model applies the same two projections separately to four histories.
- **PatchTST-style.** Overlapping length-two patches at stride one give 3, 8 and 17 tokens, with every lag covered. A biased patch projection maps to width 64 and learned position parameters start at zero. Attention has four heads in each of two post-normalised GELU encoder layers, with feed-forward width 128 and dropout 0.1. The same backbone processes each channel as a separate batch element. Mean pooling over tokens feeds a resource-specific biased five-output head.
- **iTransformer-style.** A biased L→64 projection produces one token for each of the four histories. Two post-normalised GELU encoder layers use four-head cross-variate attention, feed-forward width 128 and dropout 0.1. Flattening the four encoded tokens feeds a separate biased 256→5 head for each declared output. Both variants consume all four histories and use no added input normalisation or resource embedding.

| Family | L | One independent model | Four-model independent complement | One shared model |
| --- | ---: | ---: | ---: | ---: |
| DLinear | 4 | 50 | 200 | 50 |
| DLinear | 9 | 100 | 400 | 100 |
| DLinear | 18 | 190 | 760 | 190 |
| PatchTST-style | 4 | 67,653 | 270,612 | 68,628 |
| PatchTST-style | 9 | 67,973 | 271,892 | 68,948 |
| PatchTST-style | 18 | 68,549 | 274,196 | 69,524 |
| iTransformer-style | 4 | 68,549 | 274,196 | 72,404 |
| iTransformer-style | 9 | 68,869 | 275,476 | 72,724 |
| iTransformer-style | 18 | 69,445 | 277,780 | 73,300 |

The synthetic gate checks all 45 family/context/path combinations. It checks exact shapes and five horizons, finite outputs and gradients, connectivity of every parameter to the loss, patch/token counts, and lag coverage with input perturbations. Shared DLinear and PatchTST-style perturbations affect only the corresponding resource. In both iTransformer-style complements every input can affect every target. A separate perturbation of each variate token verifies cross-token effects within the encoder, before flattening or the output heads.

## Training, pilot reuse and failure handling

DLinear uses Adam at 0.001. PatchTST-style and iTransformer-style use AdamW at 0.001 with weight decay 0.0001. The runner shares the deterministic CPU lifecycle with batch 256, clip 1, epoch cap 50 and patience 7. Modern identities use seed 0. Validation uses the unweighted mean of scaled per-task MSEs and verifies finite inverse-transformed validation predictions at each epoch. The earliest strict minimum selects the epoch. The selected inner model is saved for audit. A final fit starts afresh and trains for that epoch count using the exact matched outer-training partition. The runner never materialises outer-test windows.

A sealed synthetic certificate is required before any fit. Structural or technical fit failure retains immutable evidence and halts that family. An interrupted claim remains visible and blocks new work for the family. The runner exposes an explicit read-only pilot reuse call that verifies the full source/config/input seal, exact scientific identity and partition metadata, structural certificate and selected checkpoint byte and tensor hashes. It neither claims another fit nor reads model data.

The fit outcome binds family, variant, optimiser configuration, architecture, context, split and scaler identities, entity/fold/seed, selected epoch, model hashes and checkpoint artifact hashes to the existing journal seal. The combined seal covers 36 inputs and 40 sources with digest `dd06216fb96976efe4cab9f1bdea05594b1d60be7e5491edf4e67857b9d8b327`.

## Dry schedule

| Family | Inner | Final | Total |
| --- | ---: | ---: | ---: |
| DLinear | 500 | 500 | 1,000 |
| PatchTST-style | 500 | 500 | 1,000 |
| iTransformer-style | 500 | 500 | 1,000 |
| **Total** | **1,500** | **1,500** | **3,000** |

The fastStorage V2-ranked cohort is 697, 860, 366, 679, 360, 505, 481, 109, 680, 50. The Rnd cohort is 99, 409, 269, 493, 474, 97, 118, 233, 142, 151. The 30 pilots are exact inner identities for fastStorage VM 697 at L=18 and Rnd VM 99 at L=4, fold 1 and seed 0, with five models per family and environment. All 30 are members of the 1,500 inner fits. The full planner's modern identity set matches the reduced planner exactly.

## Tests and preservation

```sh
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  old_fgcs_rejected/.venv_legacy/bin/python -B -m unittest discover -s fgcs_strengthening_v03/tests -v
old_fgcs_rejected/.venv_legacy/bin/python -B -m fgcs_strengthening_v03.src.modern.design
```

**87 tests passed in 49.824 seconds**, including 15 Stage 3F tests and 72 Stage 3A–3E tests. Source compilation and whitespace checks passed. Synthetic inner and final trajectories reproduced exactly across both complements in all three families. The tests checked correct optimisers, fresh refits, no outer-test access, immutable failures and rejection of a tampered pilot checkpoint. Canonical inner/final epoch histories, selections and initial/terminal model hashes matched all four previously recorded LSTM signatures byte-for-byte.

The before/after preservation inventory matched for 449,448 paths outside the implementation namespace on path, mode, size, modification time and change time. Both inventories had SHA-256 `aeb829a9ae55f893f3a10363c451375bfceb5f211256b04231849e58b5f7944b`. Tracked-file status was identical and no test runtime journal remained. All model fits and forwards in verification used generated tensors. The existing Stage 3A adapter tests read frozen data to verify input support and scalers without running models on those data. The manuscript, supplement, submission files, protocol and historical artifacts were preserved. No scientific fits, inference, pilots or experiments ran. No dependencies were installed or downloaded. No staging, commit, tag or push occurred.

**Wall-clock start:** `2026-11-11T12:32:00+00:00` (first repository check). **End:** `2026-11-11T12:42:37+00:00` (report finalisation). **Elapsed:** 10 min 37 s.

## Stage 3G handoff

No implementation blocker for Stage 3G. The scientific pilot identities remain unexecuted.

STAGE03F_PASS
