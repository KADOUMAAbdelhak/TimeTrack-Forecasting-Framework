# v0.3 implementation clarifications — author-approved

Status: C1–C9 approved by the author on 2026-11-12. Not yet registered: they enter the Stage 3K registration package unchanged. These clarifications resolve points v0.3 leaves open. They are fixed before any scientific result exists. None changes a cohort, seed, model, architecture, endpoint, estimand, multiplicity family or budget. Protocol `analysis_plan_v0.3.md` (SHA-256 `7b8f80be…6076`) and configuration `protocol_v03.json` (SHA-256 `59cda69a…f62b`) are unchanged.

## Author decisions (2026-11-12)

**C1 — Benchmark origins per partition (§9).** "Hashed run identity" is implemented as the partition (block, exact entity ID, fold).

- The 128 legal outer-test origins are drawn without replacement by PCG64. The generator is seeded from SHA-256 of `fgcs-v03|systems-origins|<partition key>`.
- Every model compared on that partition is timed on identical inputs.
- Batch 1 repeats the first sampled origin.
- With fewer than 128 legal origins, batch 128 is unavailable, and batch 1 uses one origin drawn by the same keyed generator.

**C2 — Systems benchmark population (§9).**

- Population: seed 0, fold 1, every registered entity in every block (182 partitions).
- Arms measured:
  - core S1, S2, M0 and M1 and M0-H128 everywhere;
  - PCGrad-M1, GradNorm-M1, the task-checkpoint control and LightGBM own/all in fastStorage/Rnd;
  - modern independent/shared in the 20-VM modern cohort.
- That is 1,380 deployments.
- Latency and throughput are measured for the complement and the four per-target slices, in 2 modes × 2 batches.
- Peak RSS is measured for the complement in 2 modes × 2 batches, each in a fresh process.
- Training costs are reported from the journal for every fit.

**C3 — Retry and repair (§2 "documented technical repair and same-identity retry").**

- An attempt with no outcome (interrupted), or a failed outcome whose recorded error type is an infrastructure error, is retried for the same identity under unchanged sources at most twice. The infrastructure types are `OSError`, `MemoryError`, `TimeoutError`, `InterruptedError`, `BrokenPipeError`, `ConnectionError`, `BlockingIOError`, `ChildProcessError` and `KeyboardInterrupt`.
- Before each retry, the earlier attempt's records and artifacts are moved, byte-for-byte, to a numbered quarantine with a documented reason.
- Every other failure is terminal, including registered aborts such as GradNorm invalid updates and modern technical-check failures.
- A unit refused before any attempt, such as a stopped modern family, is recorded as abandoned with its reason.
- A code repair requires a chained seal amendment. The amendment records the predecessor and successor seal digests, the reason and the affected identities. Those identities must already be quarantined, and only they re-run. Records under earlier seals remain valid for unaffected identities.
- No repair decision may use outer-test outcomes; C6 makes this structurally impossible during fitting.
- Terminal failures and abandonments become explicit `failed`, `nonfinite_prediction` or `missing` cells. The arm is then incomplete under §2.

**C4 — Training concurrency: N = 4 (author decision, 2026-11-12).** Every fit runs with exactly four concurrent single-thread workers. Systems benchmarks always run with exclusive use of the host. Training-cost seconds are reported under this recorded load. The supporting results are in `feasibility/estimate.json`.

- The estimate times the actual training functions on generated windows at each partition's frozen L and support counts, with v1 mean epochs.
- It is calibrated by the median ratio of v1 measured final-fit seconds to the model, 1.97. The ratio ranges from 1.69 to 2.01 across 18 block/formulation cells.
- Projected single-worker work is about 67 days.
- Measured aggregate speedup on this host (4 performance + 4 efficiency cores):

| N | Speedup | Projected wall time |
|---|---|---|
| 1 | 1.00 | about 67 days |
| 2 | 1.75 | about 38 days |
| 4 | 2.87 | about 23 days |
| 6 | 2.95 | about 23 days |
| 8 | 3.16 | about 21 days |

- Systems benchmarks are excluded, since they are bounded and run exclusively.
- Caveats:
  - The host is fanless, so sustained thermal throttling over weeks is not captured by these short probes.
  - With N > 4, some fits run on efficiency cores, which makes per-fit training seconds heterogeneous.
- N = 4 matches the host's four performance cores. The projected wall time is about 23 days.

**C5 — Stage 3I interpretations retained.**

- RSS baseline and peak include the frozen-adapter replay, which is common to all models on a partition.
- Background load is recorded per measurement.
- A LightGBM wrapper counts as five physical scalar artifacts.

## Implementation rules requiring registration

**C6 — Phase order and blinding.**

1. Execution proceeds in a fixed order: modern structural certificates, canary, all inner fits, all final fits, diagnostics, then fit closure.
2. Only after fit closure come systems benchmarks and outer-test evaluation, then evaluation closure, then the analysis bundle.
3. Outer-test data are materialised only in the evaluation phase. That phase cannot start until every fit and diagnostic unit is terminal and the closure record exists.
4. Workers and the orchestrator never display or aggregate outer-test values. The bundle builder runs only on a closed schedule.

**C7 — Canary stop gate.**

- The first execution is 96 registered inner identities and nothing else:
  - the 30 modern pilots (§8);
  - for the first registered entity of each block, fold 1, seed 0: core S1×4, S2×4, M0 and M1, plus M0-H128.
- They are ordinary completions, so nothing is added to the budget.
- Execution then stops. Continuing requires a recorded author approval of the canary gate. The approval may not cite any outer-test quantity, since none exists yet.

**C8 — Reused historical results (§1, §5).** Fifteen tables are registered by SHA-256 in `configs/historical_results_v03.json` (SHA-256 `32d9dd3d…6a31`):

- six v1 `metrics.parquet`, which supply M1-H64-v1 and S2-v1;
- six v1 `persistence_metrics.parquet`;
- the Stage-18 common-S2, H129 and Ridge AR/ARX `posthoc_metric_rows.parquet`.

All fifteen are tracked and byte-identical to tag `jss-review-robustness-reproducibility-v1`. They match `stage01_repository_audit.md` §8 and `stage18c1_evidence/posthoc_provenance.json`.

Each historical row must match its frozen final partition:

- on outer-test count;
- on outer-test hash, where recorded (external blocks);
- for M1-H64-v1, S2-common-v1 and Ridge, on frozen common L.

Support and ordered-test-ID fingerprints are then taken from that partition, exactly as for new evaluations. Any mismatch stops the analysis. v1 persistence repeats identically per formulation and seed; it must agree exactly and is kept once.

**C9 — Execution seal and diagnostics.**

- The scientific runtime is sealed once with `execution_fingerprints()`: 36 inputs and 60 sources. It covers every engine, evaluation, historical, analysis, systems and orchestrator source. The registered digest is the one recorded in `registration/execution_seal.json`.
- C6 is enforced in the evaluators themselves, not only by the orchestrator. Every outer-test entry point refuses unless the journal holds the fit-closure record covering all fit phases.
- Diagnostics run after each core M0/M1 final fit, restoring live model, optimiser and shuffle state from the persisted, hash-bound terminal training state.
- Each task-checkpoint logical request is evaluated exactly once, from its parent's E_r checkpoint.
