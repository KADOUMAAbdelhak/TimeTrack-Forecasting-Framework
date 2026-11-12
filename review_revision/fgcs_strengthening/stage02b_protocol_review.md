# Stage 02B — protocol finalisation review

11 November 2026. Repository /Users/fgtek002/TimeTrack. v0.3 is ready for author approval and external registration. This is a protocol review, not an author approval, registration, implementation or execution record.

Reviewed the complete v0.2 plan, Stage02A report and Stage01 audit in this directory, frozen Bitbrains V2 cohort ranks and fold-1 M1 context entries. No new model, prediction, metric, simulation or scientific test was run. The canonical GradNorm paper was read through its publisher's online viewer for equation verification; no paper, code, dependency or data file was downloaded to the repository or installed.

## Rechecks

| Topic | Final determination |
| --- | --- |
| Endpoint and zeros | Equal horizon/fold/seed weights on matched native MAEs within entity precede the log. Zero cells are included. Whole-entity zero marks the registered group log test unavailable, with exact zero category and raw p=1 retained for correction. No epsilon or complete-case switch. |
| Interaction | D(M1:S2)−D(M0:S1) = ln A_M1−ln A_S2−ln A_M0+ln A_S1. Same paired entities/supports, positive means greater penalty with all-input sharing. Materna averages complete within-VM trace contrasts first. No causal factorial interpretation. |
| Checkpoint selection | Joint and per-target best epochs use only observed inner validation trajectory, earliest ties. One outer trajectory saves the prespecified states and evaluates only after training ends. Core uses its original joint-selected epoch, with extra epochs charged to the secondary control. No new trajectories or outer-test selection. |
| PCGrad | Sequential projection uses the current task's working gradient and immutable other-task originals; skip zero-norm directions; mean projected shared gradients, unchanged mean-loss head gradients, then clip/step. Isolated projection RNG. |
| Noise-floor comparison | Same-task A/B batches are independently keyed draws from legal training support, not repeated identical inputs. K is cross-task conflict frequency minus same-task conflict frequency, with declared zero-gradient unavailability. It is reference-adjusted, not an unbiased noise correction. Eval clone and state/RNG hashes guard live training. |
| Transfer | F=ln(A_independent/A_subset), positive is benefit; Q=ln(A_omit/A_full), positive is benefit of adding supervision. Own-input reference S1, all-input reference common-context S2. Retain all four inputs for all-input omitted-task variants. Match exact three-seed comparator slice. |
| Resampling and correction | Fixed paired 10,000-replicate PCG64 bootstrap with rank-ordered entity IDs, joint three-trace Materna clusters and no TimeTrack inference. Centred two-sided bootstrap p-values are approximate; marginal CIs remain unadjusted. Explicit Holm/BH adjusted-p formulas, tie ordering and unavailable slots. BH only on eight prespecified 12-entry exploratory transfer matrices; no arbitrary-dependence guarantee. |

The locked v0.2 core context, seed/cohort rule, M0 H128 sensitivity, historical M1 H129/Ridge controls, LightGBM, persistence, exclusions, diagnostic budget and systems scope remain. No seasonal-naive, shuffled/noise task, adaptive seed/cohort escalation or post-test design changes.

## Exact changes from v0.2

1. **Primary family:** 9 prior-informed directional predictions for throughput/memory/disk (D>0), 3 nondirectional CPU sharing tests and 12 nondirectional interaction tests. All use two-sided p-values and one fixed Holm family of24. An opposite-sign significant result does not replicate a predicted penalty; CPU has no registered direction. Family membership is not adjusted after execution.
2. **Modern architectures:** replaced universal own/all contrasts with S1/M0-like own-input DLinear and PatchTST-style comparisons, and S2/M1-like all-input iTransformer-style comparisons. All compare four independent models against one shared model. No iTransformer own-input arm remains. Short-context operators are identical within each matched comparison; removed DLinear channel projection and PatchTST cross-channel mixing, retained patch2/stride1 and kernels3/9/17. Both iTransformer complements use four real variate tokens. No claim of canonical cross-family interaction equivalence. Fixed descriptive scope remains first10 V2-ranked VMs in FS and Rnd, seed0, five folds. Pilot identities are FS 697 at L18 and Rnd 99 at L4, fold1/seed0, each family × four independent target fits and shared-ALL, all inner-only. Pilot30 is contained in 1,500 modern inner fits, not additive. Modern total4,800→3,000; aggregate budget decreases by1,800 units.
3. **GradNorm canonical check:** compared [Chen et al. (2018), §§3.1–3.2, Algorithm 1, §5.1 and Table 1](https://proceedings.mlr.press/v80/chen18a/chen18a.pdf). Alpha1.5 has an explicit paper precedent and is fixed, not optimal by assumption. Norms use all four trainable layer-2 encoder tensors, including biases, a valid choice of the shared subset W. Replaced the eval-mode calibration batch with first training minibatch losses at t=0; removed the custom positive-weight clamp. Relative training rates, L2 gradient norms, detached targets and summed L1 norm residuals follow the paper. Both gradients come from the same pre-update state: update task weights, apply precomputed model update, then renormalise weights to sum4. No recalculation with new weights. Task-weight Adam .025 is fixed; model Adam .001 and clip1 retain the study baseline. Define each task loss as its scaled MSE/4 so the summed canonical objective at unit weights equals the baseline mean. Nonpositive references, undefined rates or invalid weight updates stop the identity instead of switching algorithms. Equal-loss M1 remains the comparator.
4. **Operational clarifications:** explicit zero-ratio cases, PCGrad working/original vectors, diagnostic reference interpretation, quantile/correction algorithms and frozen rank ordering. No further v1 statistic is required before registration. Batch keys now use the v0.3 namespace. Removed all pending scientific choices from the former review gate; only technical input/environment/hardware sealing and implementation conformance remain before execution.

## Final experiment and budget table

Counts are scheduled identities, not measured time or executed work. Core 910 entity-fold groups; secondary Bitbrains350; modern100. Neural and tree-wrapper columns use one training trajectory/configuration wrapper per unit.

| Arm | Inner | Final | Total | Basis |
| --- | ---: | ---: | ---: | --- |
| LSTM core S1/S2/M0/M1 |45,500|45,500|91,000|910×5 seeds×10 models per phase |
| M0 H128 |4,550|4,550|9,100|910×5 per phase |
| Pairwise sharing |12,600|12,600|25,200|350×3×2 scopes×6 |
| Leave-one-out |8,400|8,400|16,800|350×3×2 scopes×4 |
| PCGrad |1,050|1,050|2,100|350×3 |
| GradNorm |1,050|1,050|2,100|350×3 |
| DLinear reduced |500|500|1,000|100×(4 independent+1 shared), seed0 |
| PatchTST-style reduced |500|500|1,000|same count |
| iTransformer-style reduced |500|500|1,000|same count; all-input only |
| Modern pilots, included above |30|0|30 included|10 per family; reuse exact inner identities |
| Neural subtotal |74,650|74,650|149,300|no double-counted pilots |
| LightGBM wrappers |22,400|2,800|25,200|350×4 targets×2 scopes×8/1 configs |
| Combined trajectory/wrapper total |97,050|77,450|174,500|neural + tree wrappers |
| Scalar-adjusted total |186,650|88,650|275,300|replace wrappers with112,000 inner/14,000 final scalar regressors |
| Gradient diagnostics |0|0|0 new fits|27,300 checkpoint slots,218,400 batch pairs,1,747,200 task-gradient extractions |
| Task checkpoint control |0|0|0 new fits|1,050 extended core trajectories,4,200 logical task-state requests; extra epochs separately measured |
| Existing H129 / persistence / Ridge |0|0|0|reuse; no repeated deterministic seeds |

**True blocker:** none for author approval and registration of v0.3. Before execution, a separately authorised implementation must satisfy the technical gates and preserve historical artifacts. No model code, manuscript, result, prior plan/report, package, Git ref or external registration was changed. Only analysis_plan_v0.3.md and this report were created.

STAGE02B_PASS
