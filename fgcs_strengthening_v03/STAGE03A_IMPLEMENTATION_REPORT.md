# Stage 3A implementation report

The isolated foundation follows `review_revision/fgcs_strengthening/analysis_plan_v0.3.md` at SHA-256 `7b8f80be597148f5413582bf936d13a79bfc05d0725d734dfec83b5443246076`. The checked-out baseline is `paper/jss-review-revision` at `0e8cad884896a706f62f0fae4ab2b52812f9b033`. The tag `jss-review-robustness-reproducibility-v1` resolves to the same commit. No protocol deviation was identified.

## Files created

| Path within `fgcs_strengthening_v03/` | Purpose |
| --- | --- |
| `configs/protocol_v03.json` | Exact ranked cohorts, v1 reference fingerprints, resources, folds, horizons, contexts, seeds, formulation and protocol settings, and fit budgets |
| `src/identity.py` | Canonical full-SHA-256 identities, exact cohort IDs, protocol arm validation and order-independent task subset identity |
| `src/provenance.py` | Frozen configuration, input and source fingerprints, atomic exclusive attempt and terminal outcome publication, duplicate rejection |
| `src/data_adapters.py` | Read-only TimeTrack, Bitbrains V2 and Materna readers with v1 context, common support, purge and scaler enforcement |
| `src/models/lstm.py` | S1, S2, M0 H64/H128 and M1 H64 with declared task heads and canonical task-axis order |
| `plan_execution.py` | Standard-library dry enumeration and budget validation, with optional JSON Lines identities on stdout |
| `tests/test_identity.py`, `tests/test_routing.py`, `tests/test_support_scalers.py`, `tests/test_parameter_counts.py`, `tests/test_budget.py`, `tests/test_preservation.py` | Unit and frozen-artifact conformance checks |
| `STAGE03A_IMPLEMENTATION_REPORT.md` | Scope, checks and handoff |

The adapters use the original v1 M1 selection CSVs at the exact entity/fold key. Each split is checked against the v1 support manifest at every frozen context, including explicit origin IDs where the manifest stores them. Scalers are refit from the unique history and horizon rows of the requested phase's legal training origins and checked against the sealed Stage 18B2 partition references. The tests separately compare the resulting support and scaler identities against the original seed-0 M1 completion records. The original TimeTrack and external numeric window conventions are retained, including native inversion with nonnegative projection on the two log-transformed targets. The inner partition API exposes validation windows, and the final partition API materialises test windows on explicit request. The training engine will own the timing of that request.

The LSTM takes `[batch, context, four resources]` and returns `[batch, declared task, horizon]`, including a singleton task axis for S1/S2. M0 routes each retained resource through the same input-size-1 two-layer encoder in separate calls and applies that resource's biased head. S2 and M1 pass all four histories to one encoder call, including when an M1 subset omits an output. Canonical task ordering makes a reordered subset the same identity. Diagnostic and task-checkpoint identities are bookkeeping entries. The 30 modern pilot identities are members of the reduced inner schedule.

The journal writes only under the new namespace's `runtime/` path. It binds to one fingerprint set and uses same-directory atomic publication without replacing an existing record. Failed outcomes are terminal at this stage. Any later same-identity recovery needs a separate explicit authorisation and implementation that preserves the original evidence.

## Verified trainable parameter counts

| Complement | TimeTrack | External |
| --- | ---: | ---: |
| S1 H64, four independent networks | 203,808 | 203,028 |
| S2 H64, four independent networks | 206,880 | 206,100 |
| M0 H64 | 52,512 | 51,732 |
| M0 H128 | 203,296 | 201,748 |
| M1 H64 | 53,280 | 52,500 |

## Expected schedule

| Fit arm | Inner | Final | Total |
| --- | ---: | ---: | ---: |
| Core, seeds 0–4 | 45,500 | 45,500 | 91,000 |
| M0 H128 | 4,550 | 4,550 | 9,100 |
| Pairwise | 12,600 | 12,600 | 25,200 |
| Leave-one-out | 8,400 | 8,400 | 16,800 |
| PCGrad | 1,050 | 1,050 | 2,100 |
| GradNorm | 1,050 | 1,050 | 2,100 |
| Modern families, 500 per family per phase | 1,500 | 1,500 | 3,000 |
| Neural subtotal | 74,650 | 74,650 | 149,300 |
| LightGBM wrappers | 22,400 | 2,800 | 25,200 |
| **Total with tree wrappers** | **97,050** | **77,450** | **174,500** |
| LightGBM scalar estimators within wrappers | 112,000 | 14,000 | 126,000 |
| **Total counting scalar tree estimators** | **186,650** | **88,650** | **275,300** |

The planner verified 206,000 unique identities across 174,500 fit/wrapper units, 27,300 diagnostic slots and 4,200 task-checkpoint requests on 1,050 already scheduled final trajectories. Diagnostics account for 218,400 batch pairs and 1,747,200 gradient extractions. The pilot subset, diagnostic slots and checkpoint requests add zero fits. Historical H129, persistence and Ridge add zero fits.

## Verification

Commands from the repository root, using the existing environment.

```sh
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 old_fgcs_rejected/.venv_legacy/bin/python -B -m unittest discover -s fgcs_strengthening_v03/tests -v
old_fgcs_rejected/.venv_legacy/bin/python -B -m fgcs_strengthening_v03.plan_execution
git diff --check
git diff --cached --name-only
```

- **15 tests passed in 31.782 seconds.** All 910 entity/fold groups across six blocks matched the v1 context, support and scaler records for both phases, for 1,820 verified partitions. The conformance checks used saved metadata and raw data preparation. Routing used synthetic tensors only and confirmed that perturbing another resource leaves the M0 latent and output unchanged at both widths.
- **Dry planner passed.** The planner imported no Torch, LightGBM, NumPy or pandas in a fresh process. The identity tests covered canonical ordering, invalid arm settings, seed/scope separation and duplicate prevention. The journal concurrency test admitted one writer among 12 competing claims, then rejected repeated outcomes and replacement of a failed record.
- **Fingerprints passed.** The check authenticated 36 inputs and 20 source files, including 15 reused historical sources. Configuration SHA-256 is `59cda69a3e9b6b789aa09f70d2c606fce41a5d4b37d5a1d8dfe0a9b819cff62b`. The Stage 3A fingerprint set digest is `baf8c26cd9a76a39697da494d80b5758e7426f3a695301159bc675740b4bfc50`. This is a foundation fingerprint, before the training engine and host/environment seal.
- **Preservation.** New durable files were confined to the paths above. A before/after inventory of 449,448 entries outside the new namespace matched on path, file mode, size, modification time and change time. The inventory SHA-256 was `aeb829a9ae55f893f3a10363c451375bfceb5f211256b04231849e58b5f7944b`. The protocol hash remained exact. The existing manuscript modifications were already present at the start. There were no new changes to the tracked tree or index and no commit, tag or push. Scientific fitting, inference, pilots, statistics and experimental execution were zero.

## Handoff

No Stage 3A blocker. The foundation is ready for training-engine implementation. Author approval, registration and the machine/software seal remain the protocol's pre-execution gates. PCGrad, GradNorm, gradient diagnostics, modern models, LightGBM, statistics and systems measurements are specified or counted where applicable. Their implementations belong to later stages.

STAGE03A_PASS
