# Stage 02A — planning report

10 November 2026. Repository /Users/fgtek002/TimeTrack, branch paper/jss-review-revision, HEAD 0e8cad884896a706f62f0fae4ab2b52812f9b033. This is planning only. The companion analysis_plan_v0.2.md is a concrete specification for review before registration, not an externally registered protocol or permission to implement/train.

## Evidence used and scope

Read /Users/fgtek002/TimeTrack/review_revision/fgcs_strengthening/stage01_repository_audit.md, including its complete 48-row log-variance and seed-sensitivity panels. Verified relevant current repository code by inspection: benchmark/neural_v2/src/models/patchtst.py (patch8 rejects L4); benchmark/neural_v2/src/training.py (PatchTST AdamW); historical Phase3B/Phase4B freeze manifests (GradNorm was prohibited). Project search found no repository GradNorm implementation/default. No online search/download or unverified claim of a repository-supported alpha was used. Alpha1.5 is explicitly a proposed fixed GradNorm-style design choice with an equation-check acceptance gate, not a performance-selected or freshly literature-validated optimum.

No v1 endpoint was recomputed in this stage. Stage01's observed three-seed variance is not substituted for the new five-seed entity-aggregate endpoint. No new fit, inference, bootstrap, pilot, dependency installation or external registration was executed. The only files created are the requested plan and this report. The existing two tracked JSS manuscript modifications predate this stage and were not edited. Frozen scientific sources, supplements, submission packages, historical reports and the Stage01 report were not written.

## Decisions incorporated

- Near-factorial S1/S2/M0/M1, frozen v1 M1-selected common L, seeds0..4, unchanged external35 cohorts; TimeTrack descriptive, no cohort or seed escalation.
- M0 H64 own-history/shared encoder without embeddings; H128 sensitivity matched approximately to four-S1 capacity. Historical M1 H129 retained for M1/S2 only, with its unmatched context/seed limitations explicit.
- Equal native MAE aggregation within entity across horizons, folds and seeds before the log ratio. Positive log error ratio means candidate worse. Interaction is D(M1:S2)−D(M0:S1), defined once. Zero cells remain; a zero whole-entity aggregate makes the planned log test unavailable rather than triggering epsilon or entity deletion.
- One24-test primary Holm family, separate declared secondary Holm families; paired10,000-replicate entity bootstrap with PCG64 seed20261110; same Materna VM resampled jointly across temporal blocks. BH is restricted to exploratory transfer affinity matrices. Approximate centred-bootstrap p-values and marginal interval limits are explicit.
- Same-task independent minibatches replace shuffled/noise tasks. One primary excess-conflict statistic K, exact encoder tensors, batch hashes, schedule, dropout-off clone-only gradient calculation, zero-norm and RNG/optimizer safeguards specified.
- Checkpoint comparison reuses one extended core trajectory with prespecified task/joint states, without test-driven selection or duplicated retraining. Its extra epochs and four-target deployment footprint are charged separately.
- Six pairs and four leave-one-out subsets, both input scopes, with S1 versus common-S2 comparators and precise signs. Supervision omission is distinguished from input omission.
- GradNorm alpha1.5 fixed; PCGrad and GradNorm are distinct interventions. Algorithms, clipping/update order, positive-weight constraints and early-stopping objective are stated for implementation review.
- Persistence and deterministic Ridge retained, seasonal-naive removed, LightGBM own/all input added without artificial repeated seeds.
- Technical modern-model criteria do not require beating persistence. DLinear kernels3/9/17 and PatchTST-style patch2/stride1 are fixed short-context adaptations. An explicit one-variate iTransformer attention limitation remains for review.
- Separate model-selection/final-fit/diagnostic/checkpoint-tail costs, fixed CPU threads,20 warm-ups/100 measurements, batch1/128, exact footprint and platform-specific memory units.

## Fixed reductions and budget cross-check

The full five-seed six-block core and M0 H128 sensitivity are retained. Transfer, PCGrad, GradNorm and task-checkpoint secondary comparisons are fixed to all35 FS/Rnd VMs and three seeds0..2; comparator slicing uses the same three seeds. Modern models use the first10 already frozen SHA-ranked FS/Rnd VMs per environment, all five folds, seed0. These restrictions are chosen before new results. No success-triggered expansion or poor-performing-family deletion is permitted.

| Scheduled work | Inner | Final | Total |
| --- | ---: | ---: | ---: |
| Five-seed LSTM core |45,500|45,500|91,000|
| M0 H128 |4,550|4,550|9,100|
| Pairwise sharing |12,600|12,600|25,200|
| Leave-one-out |8,400|8,400|16,800|
| PCGrad |1,050|1,050|2,100|
| GradNorm |1,050|1,050|2,100|
| Modern reduced study |2,400|2,400|4,800|
| Neural subtotal |75,550|75,550|151,100|
| LightGBM target/config wrappers |22,400|2,800|25,200|
| Combined wrapper/trajectory accounting |97,950|78,350|176,300|

Replacing the LightGBM wrappers by their five scalar horizon fits gives112,000 inner/14,000 final tree-estimator fits, or **277,100** scalar-adjusted training units overall. This is not a duration estimate. Modern technical pilots require24 inner fits already contained in the scheduled2,400 modern inner identities; do not add or rerun them if their exact sealed identities are reused. Persistence, historical Ridge/H129 and gradient diagnostics add zero training trajectories. Gradient work remains substantial:1,747,200 task-gradient extractions at27,300 logical checkpoint slots. Checkpoint control extends1,050 core M1 trajectories and requests4,200 logical task states, without adding trajectories; extra epochs cannot be determined numerically before inner selection and must be recorded as actual extra training cost.

The omitted exhaustive alternatives cost182,000 subset fits,18,200 intervention fits and218,400 modern-model fits. The fixed reductions schedule42,000,4,200 and4,800 respectively. Budget counts are maximum required successful identities under technical feasibility, not an instruction to conceal missing identities on failure. All iTransformer slots remain visible until the explicit review decision; a failed family cannot quietly disappear from the denominator.

## Remaining decisions and acceptance gates

**Before external registration:**

1. Review the iTransformer single-variate limit. With one own-input resource, cross-variate attention has exactly one token and cannot mix variates. Temporal projection still learns a history-to-output mapping, but a claim of equally non-degenerate canonical attention on both input scopes is impossible without changing the scientific input design. The plan proposes a labelled single-variate-limit comparator and flags that it does not meet a strict non-degenerate-attention criterion. Accept that limitation explicitly or amend the arm prospectively; do not add fake channels or silently skip it. The1,600 provisional iTransformer trajectories are included in the4,800 budget but are not cleared for launch.
2. Review/approve fixed GradNorm alpha1.5 and the specified calibration/weight update variant. Stage2B must independently check equations before implementation acceptance. No adaptive alpha tuning is permitted. If this is changed, issue a pre-execution versioned amendment.
3. Approve the fixed reduced secondary scope, hypothesis families, aggregate-zero stopping policy and approximate cluster-bootstrap testing method. They are fully specified proposals, not assumptions of power or general-population IID sampling. The current cohort/seed counts are locked; no minimum-effect size or precision guarantee has been fabricated.

**Before execution, not scientific choices deferred to results:** record the exact CPU-host identifier/environment/hash manifests; validate all admissions/supports and preserve originals; pass independent unit/conformance checks; resolve any unavailable dependency or device incompatibility without installing/downloading in this stage. These are technical acceptance gates, not authority for a pilot now.

The protocol is sufficiently specified **for author review**: all estimands, signs, matching, zero/failure rules, families and accounting units are explicit. It is not yet a claim of registration/launch readiness while items1–3 await author approval. No manuscript writing begins until complete independent experimental/synthesis validation.

## Exact Stage2B implementation map — proposed files only

Create a new namespace /Users/fgtek002/TimeTrack/fgcs_strengthening_v02/ after separate authorisation. Do not edit historical modules. The following are specific proposed new paths, not files created here:

- configs/protocol_v02.json — locked cohorts/seeds/context-source hashes, architectures, subsets, policies and secondary restrictions.
- manifests/build_manifest.py — deterministic scientific identity and complete expected-unit planner; fixed ranked pilot IDs and frozen common contexts.
- src/data_adapters.py — read-only TT/Bitbrains/Materna inputs and exact supports/scaler partitions.
- src/models/lstm.py — S1/S2/M0/M1 and task-subset routing with declared horizon count/capacity.
- src/models/dlinear.py, src/models/patchtst.py, src/models/itransformer.py — explicitly named short-context/reduced-family variants, subject to the stated review gate.
- src/models/lightgbm.py — deterministic own/all input direct-horizon wrappers and fit-unit accounting.
- src/training.py — baseline inner/final lifecycle, task-state retention, exact optimizer/RNG resume semantics and epoch cost components.
- src/optim/pcgrad.py, src/optim/gradnorm.py — separately tested gradient and task-weight update rules.
- src/diagnostics/gradients.py, src/diagnostics/batches.py — named-parameter extraction, immutable diagnostic clones and independent batch-ID manifests.
- src/checkpoints.py — joint/task epoch selection, single final trajectory with prespecified checkpoint retrieval and deployment counting.
- src/metrics.py, src/aggregation.py — native metrics, exact entity A/D/I/F/Q definitions and explicit zero/failure semantics.
- src/statistics.py — fixed paired cluster bootstrap, Holm/BH families, unavailable slots and correlation degeneracy handling.
- src/systems.py — isolated CPU memory, workload and latency/throughput measurement.
- src/provenance.py — immutable input/config/source hashes, atomic attempts/completions and preservation checks.
- plan_execution.py — expected identities, all units/folds/seeds/arms and the exact budget assertion; no fit execution on import.
- validate_implementation.py, validate_outputs.py — independent preflight and final artifact/identity/finite/support checks.
- run_pilot.py, run_study.py, analyse_study.py — explicit separately authorised pilot/execution/analysis entry points with no test-driven configuration.
- tests/test_routing.py, test_support_scalers.py, test_checkpoint_selection.py, test_gradient_controls.py, test_pcgrad.py, test_gradnorm.py, test_short_contexts.py, test_entity_endpoint.py, test_statistics.py, test_budget.py, test_preservation.py — synthetic mathematical/protocol invariants and no historical writes.
- README.md, environment.json, source_hashes.json — public reproducibility/environment record and new execution seal generated only at acceptance.

No path above has been created. No experiment, inference, code implementation, download/install, manuscript edit, external registration or Git mutation occurred.

STAGE02A_PASS
