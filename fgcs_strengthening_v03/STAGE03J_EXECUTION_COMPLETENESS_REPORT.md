# Stage 3J — Execution completeness

Scope: `STAGE03J_SCOPE.md`, the re-scope approved on 2026-11-12. Freeze and registration move to Stage 3K. No scientific fit, no outer-test materialisation of real data and no scientific runtime journal. No manuscript, protocol or historical artifact was edited.

## Why the re-scope

The pre-freeze assessment found that freezing at the end of Stage 3I would have sealed an incomplete executor:

- Outer-test evaluation existed only for LightGBM and the transfer arms (plus core in fastStorage/Rnd, seeds 0–2).
- Nothing turned journal outcomes or the reused historical results into the analysis bundle.
- There was no orchestrator, no crash recovery, no retry mechanism and no blinding order.

The author fixed decisions C1–C4 before any implementation. They are recorded in `STAGE03J_CLARIFICATIONS_DRAFT.md`.

## What was added

**3J1 — One outer-test evaluator for every neural arm** (`src/evaluation.py`).

- Covers core in all blocks and seeds, M0-H128, PCGrad, GradNorm, pairwise, leave-one-out and the modern families. Independent own-input models receive only their own channel.
- Task-checkpoint logical requests are evaluated once each from the parent core-M1 trajectory's E_r checkpoint. `Journal.start` gained a parent-source argument restricted to that case.
- Evaluation requires a complete, full-length final trajectory and a hash-verified checkpoint. It records per-target scaled and native prediction hashes, the projected fraction, the ordered test-ID hash and per-horizon native MAE.
- `TransferRunner.evaluate` and `completed_cells` now delegate to it, so there is one evaluation path. All 18 transfer tests pass unchanged.

**3J2 — Historical and persistence reader** (`src/historical.py`, `configs/historical_results_v03.json`).

- Covers 15 reused tables: six v1 metrics, six v1 persistence, plus Stage-18 common-S2, H129 and Ridge AR/ARX. Each is registered by SHA-256, tracked and byte-identical to tag `jss-review-robustness-reproducibility-v1`.
- The 6 v1 metrics and 3 post-hoc hashes equal `stage01_repository_audit.md` §8 and `posthoc_provenance.json`.
- Historical tables store counts but not ordered origin IDs, so each row is bound to its frozen final partition:
  - by outer-test count;
  - by outer-test hash, where recorded (external blocks);
  - by frozen common L, for M1-H64-v1, S2-common-v1 and Ridge.
- Support and ordered-test-ID fingerprints are then taken from that partition, exactly as for new evaluations. Without this, persistence and historical contrasts would fail the analysis's cross-model support match.
- v1 persistence must agree exactly across its repeated formulation and seed rows. Any binding mismatch fails closed.

**3J3 — Scientific bundle builder** (`src/manifest_builder.py`).

- Enumerates the required cells from the registered analysis catalogue itself: 1,085,800 cells.
- Their 81,650 evaluation identities equal the v0.3 budget exactly: 45,500 core + 4,550 H128 + 21,000 transfer + 2,100 interventions + 2,800 LightGBM + 1,500 modern + 4,200 task-checkpoint requests.
- Historical counts equal their source tables: 18,620 persistence; 55,860 each for S2-v1, M1-H64-v1, S2-common-v1 and H129; 18,620 each for Ridge AR/ARX.
- Failed and abandoned identities become explicit `failed`, `nonfinite_prediction` or `missing` rows, with evidence hashes.
- It refuses to run while any registered identity lacks a terminal record (`ScheduleNotClosed`).
- Every evidence file and historical table enters the bundle's input hashes. The output passes `analyse_study`'s own scientific record checks: seal requirement, file verification, identity digests, frozen contexts and fingerprint presence.

**3J4 — Orchestrator** (`src/orchestrator.py`, plus `Journal.quarantine` and `Journal.amend` in `src/provenance.py`).

- **Schedule.** A frozen schedule of 283,635 units:

| Phase | Units |
|---|---|
| certify | 3 |
| canary | 96 |
| inner | 96,954 |
| final | 77,450 |
| diagnostics | 27,300 |
| systems | 182 |
| evaluation | 81,650 |

- **Phase order.** Modern certificates, then the canary stop gate (approval required), then inner, final and diagnostics, then fit closure, and only after that systems and evaluation, then evaluation closure. Outer-test data cannot be read before every fit is terminal (C6).
- **Locks.**
  - Per-unit `flock` leases.
  - A host lock: shared for fits, exclusive for systems benchmarks.
  - Execution is bound to the registration record's hash and the registered worker count.
- **Recovery (C3).**
  - Interrupted attempts and infrastructure-type failures are quarantined (moved byte-for-byte, with a reason) and retried at most twice.
  - Other failures are terminal.
  - Refusals before any attempt are recorded as abandoned. Units blocked by a failed dependency are abandoned with that dependency named.
  - `reopen` exists for documented amendments.
- **Seal amendments** are chained by digest. Affected identities must be quarantined first, only they re-run, and records under earlier seals stay valid for unaffected identities.
- **Diagnostics** restore live model, optimiser and shuffle state from the persisted, hash-bound terminal training state, so a worker crash between the final fit and its diagnostics loses nothing.
- **Session records** carry scheduler wall time per phase and never include outer-test values.
- `execution_fingerprints()` is the single runtime seal: 36 inputs, 60 sources, current digest `efc1764d26f5e016111fc4316d313432cd76cce23642424e51b0d3ded245f909`. The schedule digest is `ad6c16935eb438c4f48c48c22b6b69530776d394d3aeeb043df2606c5e7dfee2`.

**3J5 — Systems and feasibility.**

- **C1.** Benchmark origins are now keyed by partition (`partition_origin_key`). The end-to-end test asserts that a different deployment on the same partition receives identical origins.
- **C2.** A population of 182 partitions and 1,380 deployments. The systems executor also emits training-cost rows with scheduler wall time.
- **Feasibility** (`feasibility.py` → `feasibility/estimate.json`).
  - Method: the real training functions are timed on generated windows at each partition's frozen L and support counts, using v1 mean epochs. The estimator reads only metadata and v1 epoch and seconds columns.
  - Calibration: v1 measured final-fit seconds divided by the model, median 1.97 (range 1.69–2.01, 18 cells).
  - Projected single-worker work is about 67 days.
  - Measured multi-process scaling on this M3 (4 performance + 4 efficiency cores):

| Workers | Speedup | Projected wall time |
|---|---|---|
| 2 | 1.75 | about 38 days |
| 4 | 2.87 | about 23 days |
| 6 | 2.95 | about 23 days |
| 8 | 3.16 | about 21 days |

## Validation

All tests use generated data and tiny generated fits:

- `test_evaluation` (6). Every neural arm, including TimeTrack seed 4 and Materna seed 3 outside the transfer scope:
  - independent recomputation of every MAE from the journalled checkpoint;
  - outer test read only by the explicit evaluation;
  - task requests at epochs 3 and 2;
  - failures that are terminal and leave no cells;
  - wrong-partition and unfitted refusals.
- `test_historical` (4). Every reused table format; all binding failures fail closed; nonfinite historical MAE becomes explicit; the real manifest's 15 hashes are verified.
- `test_manifest_builder` (2). The full end-to-end bundle passes the analysis scientific record checks, with M1, persistence and Ridge fingerprints matching. Also an exact budget-to-catalogue identity count.
- `test_orchestrator` (6). Gates and blinding; resume-state diagnostics; interrupted attempt plus two infrastructure retries, then terminal; non-retryable and pre-attempt refusals; dependent abandonment; leases and the exclusive host lock; seal amendment re-running only quarantined identities; the production schedule's exact shape.
- `test_feasibility` (2). All 910 partitions covered from metadata; projection arithmetic.

**167 tests pass in 92.5 s.** That is 20 new Stage 3J tests plus the 147 Stage 3A–3I tests. Two Stage 3I systems tests were updated for C1: the shared-origin assertion, and the tamper case now uses another support's origins.

Other checks:

- Static compilation, whitespace/EOF and top-level unused-import scans are clean.
- **LSTM trajectories are unchanged.** The pre-3I reconstruction and current code produce byte-identical canonical evidence for S1/S2/M0/M1, H128, PCGrad, GradNorm and M1 seed 1 with tail (16 records, SHA-256 `da6bf8e0…`). This was run under the same seal. The only seal-dependent field is the GradNorm optimizer-state artifact, which embeds the seal digest.

## Preservation

- 449,584 entries outside `fgcs_strengthening_v03/` match the pre-Stage-3I inventory, excluding the `.git` directory's own timestamp. Hash: `a1a5f53d31278ba83e794522ad2bb90e596d4997105bbab9d362644af53e89f8`.
- Tracked status is unchanged. The pre-existing `manuscript/jss` edits were left untouched.
- No runtime directory, temporary directory or bytecode remains.
- Real data were read only as frozen metadata: support manifests, context sources, v1 registry epoch and seconds columns, and historical-table bytes for hashing. No outer-test window, prediction or historical MAE value was materialised for inspection.
- Nothing was installed. Nothing was staged or committed.

## Protocol deviations

None. C1–C9 are clarifications of points v0.3 leaves open, drafted for author approval and registration in Stage 3K.

## Stage 3K preconditions (author decisions)

1. ~~Choose N.~~ **Decided 2026-11-12: N = 4** (C4). The orchestrator records it as the registered worker count. The fanless-host throttling caveat remains.
2. ~~Approve the clarifications C1–C9.~~ **Approved by the author on 2026-11-12**, without changes.
3. Authorise committing and tagging the protocol and implementation. Both are untracked today, so a registration has no commit to reference.

Then Stage 3K builds the immutable registration package (protocol, configuration, historical manifest, clarifications, execution seal digest, schedule digest, host manifest and the feasibility record) and runs the independent §11 audit. The runtime journal is created only at the start of Stage 4A.

**Wall-clock:**

- Author decisions recorded about 15:30.
- Start `2026-11-12T15:33:36+02:00` (first Stage 3J artifact).
- End `2026-11-12T16:02:19+02:00`.
- Elapsed **28 min 43 s**.

STAGE03J_PASS
