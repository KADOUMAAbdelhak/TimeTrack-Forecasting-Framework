# Stage 3I — Systems measurements

Protocol authority: `review_revision/fgcs_strengthening/analysis_plan_v0.3.md` §9 and `configs/protocol_v03.json` `systems_spec`. Stage 3I implements the measurement machinery only. No scientific training, inference, benchmark, diagnostics or analysis ran.

## Takeover state

Codex started Stage 3I at `2026-11-12T12:59:32+02:00`. Its usage limit ended the session at about 13:14. The `fgcs_strengthening_v03/` tree is untracked, so `git diff` is empty. I reconstructed the takeover state from file times newer than the Stage 3H report and from Codex's own session log.

**New systems sources already present:**

- `src/systems.py` contains origin sampling, footprints, `ForwardPath`/`Complement` routing and the complement loader for core, capacity, PCGrad, GradNorm, modern, LightGBM and checkpoint-request deployments. It also contains timing, training-cost separation, `run_isolated`, `SystemsRunner` (prepare, measure, costs, memory and publish) and the child replay `_memory_condition`.
- `src/systems_environment.py` contains the hardware/software/conditions manifest, the live-host observer, the fail-closed `require_environment`, the Darwin/Linux `ru_maxrss` conversion and the current-RSS readers.
- `src/systems_records.py` contains the typed records `CheckpointRef`, `MeasurementBinding`, `Footprint`, `Deployment`, `TrainingCost`, `InferenceLatency`, `InferenceThroughput` and `PeakMemory`.
- `src/systems_worker.py` is the fresh-interpreter RSS worker.

**Codex also instrumented shared sources:**

- `data_adapters.py` gained benchmark origin IDs, ordered history replay and the scaler hook.
- `provenance.py` gained `measure_seconds` and `Journal.terminal_evidence`, which also returns failed outcomes.
- `training.py` gained checkpoint serialisation/IO timing by category, optimizer-state byte counts and moved the `elapsed` stamp.
- `optim/pcgrad.py` and `optim/gradnorm.py` gained overhead spans.
- `tree/runner.py` gained LightGBM timing fields.

**Tests already present:** `systems_fixtures.py` plus `test_systems_{complement,footprint,memory,timing}.py`, 10 tests in all. Nine passed and one failed: `test_fit_costs_separate_failure_tail_diagnostics_and_elapsed` built an invalid diagnostic identity (`variant="gradient"`; the registered slots are `epoch0/mid/final`). There was no `test_systems_provenance.py` and no Stage 3I report.

## What I added or fixed

- **Fix:** the diagnostic fixture identity now uses the registered `final` slot. The production cost logic was correct.
- **Cleanup:** I removed an unused `_encode` import from `src/systems.py`. I made no other source change. The Codex implementation met every v0.3 requirement on review, so the remaining work was verification.
- **New `tests/test_systems_provenance.py` (5 tests):**
  - Registered conditions fail closed on MPS, 2 workers, threads ≠ 1, empty or other env thread values and a bool-for-int job count.
  - `require_environment` rejects a missing manifest, unregistered declared or live conditions, a different live host and an unobservable host.
  - The manifest round-trips. Hardware and software hashes are separate.
  - Binding and `CheckpointRef` reject malformed SHA, warm-up/repetition changes, non-canonical tasks, inner identities, missing target routing and illegal LightGBM horizons.
  - `SystemsRunner` refuses a journal sealed without the systems sources.
  - A **fresh-process end-to-end run** with a scratch journal sealed by `systems_fingerprints()` does the following:
    - Runs a real tiny M1 inner fit and final fit on generated windows. Generated losses select joint epoch 2 and a MEMORY task epoch of 3, which produces a 1-epoch checkpoint tail.
    - Prepares a plan with 128 distinct, order-preserving, reproducible origins and publishes the origin manifest.
    - Measures all 20 latency and 20 throughput conditions (complement plus four per-target slices × 2 modes × 2 batches).
    - Computes the deployment and the six cost rows. Selection equals inner `elapsed`, final-fit optimisation excludes the tail, the tail is charged separately and diagnostic captures are separate.
    - Measures a checkpoint-request complement: 2 physical checkpoints and 4 logical models.
    - Checks short support: batch 128 is unavailable, its RSS returns `None` and batch 1 stays available.
    - Replays RSS through `_memory_condition` with an exact binding check, and rejects a mismatched worker payload or binding.
    - Publishes 54 immutable records. A re-publish raises `DuplicateIdentity`, and tampered host, origins or checkpoints are rejected.
    - Confirms no energy/carbon field appears in any output.
- **`test_systems_complement.py` (+4):**
  - The three modern families in both complements. Own-input independent models receive exactly their own channel `(128, L, 1)`, four times sequentially per call. Outputs equal direct model calls. Shared models run one joint forward even for a target slice.
  - Real generated LightGBM wrappers: five scalar boosters per target, outputs equal direct `predict`, both timing modes, 20 physical / 4 logical deployment, and a 4-booster wrapper is rejected.
  - The labels M0-H128, M0-H64, pcgrad-M1 and gradnorm-M1, each as one joint forward.
  - Rejection of incompatible complements: missing target, wrong seed, wrong context, float64 input, and task checkpoints on S1.
- **`test_systems_footprint.py` (+2):** checkpoint-hash mismatch and compressed state-dict bytes are rejected. Optimizer state is reported but excluded from deployed bytes. Footprints bound to a different complement are rejected.
- **`test_systems_memory.py` (+2):**
  - A 64 MiB touch appears in the peak increment (≥ 48 MiB).
  - A manifest-guarded worker runs an M1 LSTM batch-128 workload with torch threads 1/1.
  - A worker given a different host manifest exits with `ProvenanceError`, and workload failures propagate.

### Trajectory preservation check for Codex's shared-source edits

The GradNorm edit reorders `model_loss` construction relative to the weight-gradient call, so preservation was verified rather than assumed. I recovered Codex's exact edit scripts (`11:04:24Z` and `11:12:07Z`) and the original `_save_model_checkpoint` from its session log. From these I rebuilt the pre-3I `training.py`, `provenance.py`, `pcgrad.py` and `gradnorm.py` in a scratch directory with exact-match inverse replacements. The rebuild matches the logged original GradNorm order. Both source sets then ran identical generated inner and final trajectories in separate fresh processes:

- S1, S2, M0 and M1 (seed 0)
- M0-H128
- PCGrad-M1
- GradNorm-M1
- M1 seed 1, with task checkpoints at epochs 1/14/21

All 16 canonical evidence records were **byte-identical**: epochs, batch orders, validation histories, selection, initial and terminal model hashes, checkpoint file hashes and intervention step records. Run-specific metadata was excluded: timings, byte counts, the resume-state hash and the inner outcome-file hash, which embeds UTC time and attempt token. Comparison SHA-256 was `0cb89f3c…1510` on both sides. Prior LSTM trajectory fingerprints are unchanged.

## Systems methodology (as implemented)

- **Host and software:**
  - `MachineManifest` records the following:
    - Hardware: hostname, CPU model, physical and logical cores, RAM bytes, OS, kernel and power mode (`pmset` on Darwin, platform profile/governor on Linux).
    - Software: Python, NumPy, PyTorch, LightGBM, scikit-learn, and the NumPy/Torch build configuration plus `threadpoolctl` pools.
    - Conditions: device and worker count, plus torch intra/inter-op, `OMP`/`MKL`/`OPENBLAS` and LightGBM threads.
  - Conditions must equal `cpu, 1 worker, 1/1 torch threads, "1"×3, LightGBM 1`, or the run stops.
  - Every prepare, measure, memory and publish call re-observes the live host and requires exact equality with the declared manifest. A per-run `flock` enforces one benchmark worker.
  - The manifest is published once, immutably. Background load (`getloadavg`) is recorded on every measurement record.
- **Model loading:**
  - Neural deployments: only the primary joint-selected checkpoint, or the logged task epochs for the checkpoint-request control. The load is verified against the journal file hash and tensor hash, restored strictly in CPU float32 and switched to eval mode.
  - LightGBM: five verified scalar text models per target, with the feature layout and `num_threads=1`.
  - Shared physical checkpoints are consolidated.
  - All loading happens outside timed work.
- **Origins:**
  - After selection, 128 legal test origins are drawn without replacement with PCG64. The seed is the first 8 little-endian bytes of `SHA-256("fgcs-v03|systems-origins|" + run identity)`. The run identity is the identity digest, or the digest of the ordered digests for a complement.
  - Batch 1 uses the first sampled origin, repeated.
  - Fewer than 128 legal origins mark batch 128 `insufficient_legal_test_origins`, with no substitute batch size.
  - The origin manifest (run identity, support hash, count, positions and IDs) is published immutably and hashed into every record.
- **Timing:**
  - Forward-only takes a prepared float32 scaled input, so preprocessing, I/O and loading are excluded.
  - End-to-end in-memory covers scaling, preparation, forward and per-target inverse transform.
  - Each condition runs 20 warm-ups and then 100 calls timed with `perf_counter_ns` under `torch.inference_mode()`.
  - Reported statistics: median and p95 (linear interpolation) in ms, and throughput = batch / mean latency in seconds.
  - Complements: four sequential independent models (S1, S2, modern independent, LightGBM) versus one joint forward (M0, M1, M0-H128, PCGrad, GradNorm, modern shared). Per-target slices are reported too.
  - No measurement feeds selection.
- **Footprint and deployment:**
  - Recorded: trainable parameters, raw state-dict tensor bytes, and uncompressed (`ZIP_STORED`-verified) state-dict bytes per physical checkpoint. Deployment records distinct checkpoint count and bytes and the number of logical target models.
  - Optimizer bytes (Adam, plus the GradNorm weight optimizer) are recorded per fit and excluded from deployed bytes.
  - LightGBM: parameters are N/A, raw tensor bytes 0 and model bytes are the scalar text size. Each wrapper counts five physical scalar artifacts.
- **Training cost:** each row type reads journalled terminal outcomes.
  - `selection_cost`: summed `elapsed` of all complete inner candidates, including the LightGBM grid. Validation is also reported separately, and failed-attempt time is separate.
  - `final_fit_cost`: optimisation to the primary epoch plus primary checkpoint serialisation and IO.
  - `checkpoint_tail_cost`: extra epochs and task-checkpoint saves, charged only to the control.
  - `diagnostic_cost`: diagnostic seconds plus diagnostic checkpoint captures.
  - `pcgrad_overhead` and `gradnorm_overhead`: sub-spans flagged `included_in_optimisation`.
  - Scheduler elapsed wall time is reported separately and never equated with summed work, money or energy.
- **Peak memory:** each condition runs in a fresh interpreter with threads forced to 1 and the manifest re-verified.
  - The worker reads baseline RSS (Darwin `proc_pidinfo` resident size, Linux `/proc/self/statm`) before importing the workload.
  - The worker re-derives the plan, requires an identical binding hash and runs the condition.
  - Peak is `ru_maxrss`, with Darwin bytes used as-is and Linux KiB × 1024. Other platforms are rejected.
  - Baseline, peak, increment, interpretation and worker PID are reported.
- **Provenance:** each record binds the following:
  - all checkpoint references (identity, checkpoint SHA, outcome SHA, epoch or horizon) and per-target checkpoint routing
  - the formulation label and context
  - hardware and software hashes and the origin-manifest hash
  - protocol, config, source-map and input-map hashes from the journal seal
  - the run identities and the 20/100 condition
  Records are published once by atomic link and keyed by record type, run, mode, batch, subject, label and artifact.
- **No energy, power-draw or carbon quantity is measured or emitted** (asserted in tests).

## Synthetic validation results

All inputs were generated:

- Analytic timing reference: durations 1…100 ms give median 50.5, p95 95.05 and mean 50.5. Throughput at batch 128 is 128/0.0505 s⁻¹.
- Origin sampling matches an independent reference implementation of the key.
- Parameter counts: S1 50,757, S2 51,525, M0 51,732, M1 52,500 and M0-H128 201,748. Raw bytes are 4 × params.
- End-to-end M1: 52,500 params, 210,000 raw bytes, 1 physical / 1 logical. The checkpoint-request control has 2 physical (epochs 2 and 3) / 4 logical, with CPU, THROUGHPUT and DISK_WRITE routed to one checkpoint and MEMORY to another.
- The RSS increment reflects a 64 MiB allocation.

## Tests

```sh
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  old_fgcs_rejected/.venv_legacy/bin/python -B -m unittest discover -s fgcs_strengthening_v03/tests
```

**147 tests passed in 74.7 s**: 23 Stage 3I tests (10 pre-existing, 1 of them repaired, plus 13 new) and the 124 Stage 3A–3H regression tests, all unchanged and passing. The systems-only subset ran 23/23.

Other checks:

- Static compilation and whitespace/EOF checks over all `.py`, `.md` and `.json` files in the namespace passed (0 issues).
- An AST unused-import scan of the systems sources and tests is clean.
- No `runtime/`, temporary directory or `__pycache__` remained.

The systems seal (`systems_fingerprints()`) covers 36 inputs and 55 sources, digest `3db49a4e713352b2aa04c52b42364e27650cec43359eb4426ad099290727e3b9`. Configuration SHA-256 is unchanged at `59cda69a3e9b6b789aa09f70d2c606fce41a5d4b37d5a1d8dfe0a9b819cff62b`.

## Preservation

- The before/after inventory covered 449,584 entries outside `fgcs_strengthening_v03/`, on path, mode, size, mtime and ctime.
  - The only difference was the `.git` directory's own timestamp, caused by `git status` index-lock handling.
  - Excluding that line, both inventories hash to `a1a5f53d31278ba83e794522ad2bb90e596d4997105bbab9d362644af53e89f8`.
- Tracked-file status was identical before and after: `efc10648…a5484`. The pre-existing `manuscript/jss/manuscript.{tex,pdf}` modifications were present at takeover and were not touched.
- No manuscript, supplement, submission, protocol or historical artifact was edited.
- Nothing was installed or downloaded. No staging, commit, tag or push occurred.
- The scratch trajectory comparison lived outside the repository.

## Protocol deviations

None. Interpretations where v0.3 is silent:

1. When support has fewer than 128 origins, batch 1 uses one hashed draw from the legal support.
2. Origins are keyed by each complement's own run identity, as the protocol literally states. Different models on the same partition therefore get different 128-origin samples.
3. Under a manifest, the RSS baseline is taken after the interpreter, numerical runtimes and host verification are loaded. The peak includes the frozen-adapter replay and model load, which are common to all models on that partition.
4. Background load is recorded per measurement rather than in the immutable manifest.
5. LightGBM physical artifact count is five scalar models per wrapper.

## Stage 3J blockers and preconditions

No implementation blocker. The following preconditions apply:

1. The scientific journal must be sealed with `systems_fingerprints()`, the union of all engine, analysis and systems sources, before the first fit. A journal sealed only for training is refused by `SystemsRunner`, and a runtime binds to exactly one seal.
2. The benchmark process must set `torch.set_num_interop_threads(1)` and `set_num_threads(1)` at start. This host defaults to 8 inter-op threads, which the guard rejects.
3. A pre-execution machine manifest must be frozen on the reference host. The observed host is an Apple M3, 8 cores, 24 GiB, Darwin 25.6.0, `lowpowermode 0`, Python 3.13.2, NumPy 2.5.1, PyTorch 2.13.0, LightGBM 4.7.0, scikit-learn 1.9.0. All compared models must use it.
4. The orchestrator must supply scheduler elapsed wall time.
5. The real `TimeTrack`/external benchmark-history adapters are exercised only after final fits, under Stage 3J. Stage 3I verified them by code inspection and synthetic replay, not on frozen data, by design.

**Wall-clock (this session):** start `2026-11-12T14:28:00+02:00` (first repository check); end `2026-11-12T14:49:26+02:00` (report finalisation); elapsed **21 min 26 s**. Codex's preceding partial work ran 12:59:32 to about 13:14 local.

STAGE03I_PASS
