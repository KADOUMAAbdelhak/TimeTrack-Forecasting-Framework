# Stage 3J — Execution completeness (re-scoped)

Status: approved re-scope, 2026-11-12. The freeze and registration package moves to Stage 3K. Stage 3J performs zero scientific fits, zero outer-test materialisation of real data and creates no scientific runtime journal. It changes no protocol, manuscript or historical artifact.

## Author decisions recorded for the clarifications addendum

These resolve points v0.3 leaves open. They are implementation clarifications fixed before any result exists, not design changes.

- **C1 — Benchmark origins per partition.** The 128 benchmark origins are keyed by the partition (block, exact entity ID, fold), not by each model complement. Every compared model on that partition is timed on identical inputs. Batch 1 uses the first of those origins. With fewer than 128 legal origins, batch 128 is unavailable and batch 1 uses one origin drawn by the same keyed generator.
- **C2 — Systems benchmark population.** Inference latency, throughput and peak RSS are measured for seed 0, fold 1, every registered entity in every block. Each measured arm is one that exists as a final identity there: core S1, S2, M0, M1 and M0-H128 everywhere. PCGrad-M1, GradNorm-M1, the task-checkpoint control and LightGBM own/all are measured only in fastStorage/Rnd. Modern independent/shared are measured only in the 20-VM modern cohort. Peak RSS is measured per complement for each mode and batch. Training costs are reported from the journal for every fit.
- **C3 — Retry and repair.**
  - An interrupted attempt (no outcome) or a failed outcome caused by infrastructure may be retried automatically up to twice for the same identity under identical sources.
  - Any code repair requires a documented, chained seal amendment. Only the affected identities are re-run under it.
  - Every attempt and failure stays in the record.
  - No repair decision may use outer-test outcomes.
  - If the retries are exhausted, the identity is marked incomplete under v0.3 §2.
- **C4 — Training concurrency.** Stage 3J measures synthetic real-shape fit times and projects runtime for N = 1…8 workers. The author then fixes N before registration. Training-cost seconds are reported under that recorded load. Systems benchmarks always run with exclusive use of the host.
- **C5 — Stage 3I interpretations retained.**
  - RSS baseline and peak include the frozen-adapter replay, which is common to all models on a partition.
  - Background load is recorded per measurement.
  - A LightGBM wrapper counts as five physical scalar artifacts.

## Sub-stages

1. **3J1 — Outer-test evaluation for every arm.** One evaluator for every neural final identity: core in all blocks and seeds, M0-H128, PCGrad, GradNorm, pairwise and leave-one-out, and modern families. The checkpoint-control task-epoch predictions are evaluated once per logical request. LightGBM keeps its existing evaluator. All of them produce the same per-cell evidence: target, horizon, native MAE, ordered test-ID hash, support, scaler and context.
2. **3J2 — Historical and persistence readers.** Read-only normalisers for the reused v1 and Stage-18 results: persistence, Ridge AR/ARX, M1-H129-v1, M1-H64-v1, S2-common-v1 and S2-v1. They must produce support and ordered-test-ID hashes byte-compatible with 3J1.
3. **3J3 — Scientific manifest builder.** Converts journal evaluation and diagnostic outcomes plus the historical readers into the `cells`/`diagnostics` JSON Lines bundle accepted by `analyse_study --scientific-input`, with evidence hashes bound to the seal. Missing or failed identities become explicit status rows, never silently dropped.
4. **3J4 — Orchestrator.**
   - Registered schedule ordering and a host-wide exclusive lock shared by fit workers and benchmarks.
   - Scheduler wall-time capture.
   - Outer-test blinding: no outer-test metric is displayed or aggregated before synthesis.
   - Recovery of interrupted attempts, quarantine of failures and same-identity retry (C3).
   - Seal-amendment chaining.
   - A canary or pilot stop gate.
5. **3J5 — Systems changes.** Partition-keyed origins (C1), the measurement population (C2) and synthetic real-shape feasibility timing (C4).
6. **3J6 — Report.** Full regression, preservation, a draft clarifications addendum and the Stage 3K handoff.
