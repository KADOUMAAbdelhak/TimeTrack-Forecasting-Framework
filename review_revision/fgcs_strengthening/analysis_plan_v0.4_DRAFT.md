# Analysis plan v0.4 (minimal): FGCS revision protocol — DRAFT

**Status: draft, 2026-11-15. Not frozen, sealed or registered; nothing has run.** It replaces the earlier v0.4 draft (commit `00111dcb`) with the smallest design that addresses the three revision comments.

- **Supersedes:** v0.3 (`analysis_plan_v0.3.md`; registration package r3; OSF `kuwra`) **before any v0.3 execution**. No v0.3 scientific fit, outer-test evaluation or analysis has occurred.
- **Baseline:** manuscript "Evaluating Contextual Input and Shared Representation in Multi-Metric Runtime Forecasting for Cloud Software Systems" (repository tag `jss-review-robustness-reproducibility-v1`).

## P0. Scope and evidence tiers

v0.4 addresses three revision comments only:

1. Add **DLinear, PatchTST and iTransformer** as modern baselines.
2. Explain **shared-representation degradation** using task affinity, gradient conflict, correlation analysis and transfer diagnostics.
3. Reframe the eventual manuscript around **contextual input versus representation sharing** (P10).

| Tier | Content | Status |
|---|---|---|
| **Tier 1, frozen primary study** | S1/S2/M1 LSTM, three seeds, model-specific selected contexts, all six blocks | Unchanged; already observed; reported as is |
| **Tier 2, extension** | The existing post-hoc controls (common-context S2, M1-H129, Ridge AR/ARX) plus everything in P1–P6 | Existing controls already observed and labelled post-hoc; P1–P6 are prospective |

- Tier 2 tests no confirmatory hypothesis: no p-values, no multiplicity families.
- Diagnostics are descriptive and associational. Null, mixed or conflicting results are valid outcomes and will be reported as such.
- Gradient conflict is not assumed to explain sharing degradation.

## P1. Cohort and data (common to every new run)

- **Cohort.** The 20 Bitbrains VMs already frozen in `fgcs_strengthening_v03/configs/protocol_v03.json`: the first 10 per block by frozen V2 cohort rank. They were selected by rank, not by any outcome.
  - fastStorage: 697, 860, 366, 679, 360, 505, 481, 109, 680, 50.
  - Rnd: 99, 409, 269, 493, 474, 97, 118, 233, 142, 151.
- **Unchanged from tier 1 and v0.3:**
  - the v1 origin IDs and maximum-context legal support;
  - five purged expanding outer folds, each with exactly one inner train/validation split (as in v0.3);
  - horizons {1, 2, 4, 9, 18};
  - source-specific transforms, training-only median/IQR scalers, native inverse and the non-negativity projection;
  - native MAE on exactly the same test origins for every compared model.
- **Context.** Every model uses the **frozen v1 H64-M1-selected context L** for each entity and fold. There is no new context selection.
- **Inputs.** Byte-identical to the sealed inputs (Zenodo `10.5281/zenodo.24189108` plus the tracked repository inputs).
- **Execution rules.** No outer-test data are read before fit closure (v0.3 C6). Retries and code repairs follow v0.3 C3.

## P2. Design: 2×2 per backbone

| Cell | Input | Parameters |
|---|---|---|
| **S1** | own resource | independent model per target (4 models) |
| **S2** | all four resources | independent model per target (4 models) |
| **M0** | own resource | one shared model with four target outputs |
| **M1** | all four resources | one shared model with four target outputs |

| Backbone | S1 | S2 | M0 | M1 |
|---|---|---|---|---|
| LSTM | ✓ | ✓ | ✓ | ✓ |
| DLinear | ✓ | ✓ new | ✓ | ✓ new |
| PatchTST-style | ✓ | ✓ new | ✓ | ✓ new |
| iTransformer-style | undefined | ✓ | undefined | ✓ |

**Contrasts** (candidate:reference):
- context, independent: **S2:S1**; context, shared: **M1:M0**;
- sharing, own input: **M0:S1**; sharing, all input: **M1:S2**;
- interaction: reported descriptively (P4).

## P3. Model specifications and fixed hyperparameters

There is no hyperparameter search. Every setting below is fixed in advance and identical across cells, except where a cell's definition requires otherwise.

**Shared training settings.**
- Learning rate 1e-3; batch 256; at most 50 inner epochs; patience 7; global gradient clipping 1.0.
- Inner early stopping on scaled validation MSE (for shared models, the equal mean of the four target MSEs), keeping the earliest strictly lowest epoch.
- The final refit is fixed at each seed's selected epoch.
- Optimisers: Adam for LSTM and DLinear; AdamW with weight decay 1e-4 for the transformer families.
- **Seeds:** 0, 1 and 2 for every stochastic model.

**LSTM** (v0.3 §1; existing code). Two layers, unidirectional, dropout 0.1, H64, biased linear horizon heads.
- S1/S2: four own-input or all-input networks.
- M0: an input-size-1 encoder shared across the four own-resource histories, four resource heads, no resource embedding.
- M1: an all-four-input encoder with four heads.

**DLinear.** Replicate-padded moving average with kernel min(25, largest odd integer ≤ L), giving 3, 9 and 17.
- **S1:** per target, separate trend and residual linear maps L→5 on the target's own channel (existing).
- **M0:** one pair of trend/residual maps reused on each resource channel (weight tying), with no channel mixing (existing).
- **S2 (new):** per target, one linear map from all four channels' trend and residual components (8L inputs) to 5 outputs: a decomposed linear ARX.
- **M1 (new):** a shared linear bottleneck 8L → 16 with no activation, then per-target linear heads 16 → 5. Without a shared component, a joint linear map trained with a per-target-separable loss has the same optimum as four S2 maps, so sharing would be vacuous.

**PatchTST-style.** Patch length 2, stride 1 (3, 8 or 17 patches); d_model 64, 4 heads, 2 encoder layers, feed-forward 128, dropout 0.1; learned positional encoding; mean pooling over patch tokens; GELU; post-normalisation.
- **S1:** four own-input models (existing).
- **M0:** one backbone applied separately to each resource channel, with resource-specific linear heads (existing).
- **S2 (new):** channel-dependent tokens. Each token holds the four channels' values within one patch (4 × 2 = 8 values), projected linearly to d_model. One model per target, with one head.
- **M1 (new):** the same channel-dependent backbone, shared, with four resource-specific heads.
- These are declared adaptations, not canonical PatchTST.

**iTransformer-style** (existing). Variate tokens via Linear(L, 64); 2 layers, 4 heads, feed-forward 128, dropout 0.1; the four encoded tokens are flattened before each 5-output head.
- S2: four independent models, each seeing all four variate tokens and predicting one resource. M1: one joint model with four heads.
- **S1/M0 are structurally undefined.** With a single variate token, attention attends only to itself and the model reduces to a token-wise MLP. These cells are not fitted and are shown as undefined in every table.

**Structural checks** before any data fit, for every new cell, at L = 4, 9 and 18:
- finite forward and backward passes, and five outputs per target;
- every lag reaches an output, and every parameter connects to the loss;
- own-input independence for S1/M0;
- cross-channel input-perturbation effects for S2/M1.

If any check fails, no data fit of that backbone starts. The failure is recorded; a code repair goes only through a chained seal amendment (v0.3 C3), after which every check for that backbone is repeated. Other backbones are unaffected.

## P4. Endpoints and analysis (as in the paper)

- **Aggregation.** Native MAE is averaged over seeds 0–2 within each block × entity × fold × resource × horizon × cell. MacroMAE gives those cells equal weight. The resource-overall MacroMAE gives every horizon equal weight.
- **Notation.** A_X is the entity-level MacroMAE of cell X for one entity, resource and backbone (over that entity's five folds and five horizons, seed-averaged). The entity log effect is D(C:B) = ln A_C − ln A_B, so a negative D means C is more accurate than B.
- **Primary endpoint.** The MacroMAE gain G(C:B) = 100 · (MacroMAE(B) − MacroMAE(C)) / MacroMAE(B), per contrast, resource, block and backbone.
- **Consistency classes.** The paper's predicates with seed thresholds unchanged (three seeds). VM thresholds are rescaled to 10 VMs per block, rounding conservatively:

  | Class | Gain | Horizons positive | VMs positive | Folds positive | Seeds positive |
  |---|---|---|---|---|---|
  | Broad Positive | ≥ +1 % | ≥ 4/5 | ≥ 8/10 | ≥ 4/5 | ≥ 2/3 |
  | Conditionally Positive | > 0 (broad rule fails) | ≥ 3/5 | ≥ 5/10 | ≥ 3/5 | ≥ 2/3 |
  | Broad Negative | ≤ −1 % | ≤ 1/5 | ≤ 2/10 | ≤ 1/5 | ≤ 1/3 |
  | Neutral or Mixed | every remaining case | | | | |

- **Uncertainty.** The paper's paired VM-cluster bootstrap, run within each block: 10 VMs resampled with replacement, all five folds and the paired cell structure kept, on seed-averaged matched MAEs. 10,000 replicates, percentile 95 % intervals, random seed 20261007. Intervals never enter the classification predicates.
- **Interaction.** Both sharing gains are reported side by side, together with the entity log-ratio I = ln A_M1 − ln A_S2 − ln A_M0 + ln A_S1 and its bootstrap interval. This is descriptive, not a test.
- **Secondary descriptives:** the matched-cell median MAE ratio and win rate; persistence skill, computed per cell and averaged as in the paper, with undefined zero-denominator skills counted, not replaced.
- **Cross-backbone summary.** For each contrast × resource × block, each backbone's class is tabulated. An effect **generalises across backbones** only if every backbone for which the contrast is defined has a non-neutral class of the same sign. Otherwise it is **backbone-dependent**. No pooled cross-backbone statistic is computed.
- **Baseline accuracy (comment 1).** For each cell × resource × block, every backbone's MacroMAE and mean persistence skill are tabulated side by side, with the LSTM's ratio to the most accurate defined backbone. This shows whether the LSTM is competitive with the modern baselines. It is descriptive: no class, test or ranking claim.
- **Parameter counts** are reported per cell, because consolidation (four models into one) is part of the sharing question.
- **Missing fits.** A fit that still fails after its v0.3 C3 retries makes that block × entity × fold × resource × seed missing for every cell of that backbone, so contrasts stay paired. Seed averages then use the remaining seeds. Each predicate keeps its numerator and denominator over the units still available (for example 7/9 VMs, not 7/10), and the thresholds become the same fractions (≥ 0.8, ≥ 0.5, ≤ 0.2 of available VMs). Every missing unit is listed in the results.

## P5. Mechanism diagnostics

All diagnostics use the P1 cohort and are computed after fit closure (for the training-side measures) or after evaluation closure (for anything involving outcomes). None alters a model.

| # | Diagnostic | Definition | Data |
|---|---|---|---|
| **D-1** | Lagged cross-correlation | Pearson correlation between each ordered resource pair (i→j) on transformed, robust-scaled series, lags 1–18. Summary per entity × fold: maximum absolute correlation over lags | Inner-training windows only |
| **D-2** | Conditional predictive dependence | **Reused:** the existing matched-context Ridge AR/ARX results, which use the same frozen H64-M1 context per entity and fold with inner-selected α, restricted to the 20 P1 VMs. Statistic: the entity-level gain G(ARX:AR) per target. It is the model-based form of the correlation analysis and an input to D-3 | Existing post-hoc results (tier 2, already observed) |
| **D-3** | Dependence vs effects | Spearman correlation across the 10 entities of each block between D-1 or D-2 and the v0.4 LSTM entity log effects D(S2:S1) and D(M1:S2) (P4 notation), per resource × block. Intervals: VM-cluster bootstrap with the P4 settings (10,000 replicates, percentile 95 %, seed 20261007) | After evaluation closure |
| **D-4** | Gradient conflict and magnitude imbalance | LSTM M1 shared encoder (M0 descriptive), at the final selected epoch E only, with eight keyed A/B batch pairs of size 128 (v0.3 §5 keys and statistic; existing code). v0.3's epoch-0 and mid-training slots are not extracted in v0.4. Reported: the six pairwise task-gradient cosines, the max/min task-gradient L2-norm ratio, and excess conflict K (cross-task minus same-task sign-conflict rate) | Outer-training batches only |
| **D-5** | Transfer lattice | All-input LSTM (H64, all four input channels) trained on each of the 6 pairwise and 4 leave-one-out task subsets, with retained-task heads only, the equal mean of retained-task losses, its own inner early stopping and a fixed-epoch refit. References: S2 per target; full model: M1 | Fits on training data; analysed after evaluation closure |
| **D-6** | Task affinity (4×4) | Directed pairwise transfer F_i(j) = ln[A(S2_i) / A(pair_{i,j}, target i)] for i ≠ j. Leave-one-out contribution Q_{i,j} = ln[A(subset without j, target i) / A(M1, target i)] | From D-5 |
| **D-7** | Per-task loss shares | Each task's share of M1's training MSE per epoch and at E: the loss-side counterpart of D-4's magnitude imbalance | Existing training journal fields (`train_task_mse`) |

**Interpretation rules.**
- These are descriptive associations, not causal identification.
- A null or opposite-direction association is reported as such.
- No diagnostic changes the design or analysis of any other component.
- D-2 reuses outcomes already observed post-hoc and is labelled accordingly. D-1 is the prospective, training-only dependence measure.

## P6. Interventions

None in v0.4. Huber loss, PCGrad, GradNorm and task-grouping interventions require a separate, later amendment, justified by the P5 diagnostics and registered before any such run.

## P7. Reused without re-running

- Tier-1 results for every block (including Materna and TimeTrack) and the existing post-hoc controls (common-context S2, M1-H129, Ridge AR/ARX).
- v1 persistence results.
- The frozen contexts, supports and scalers.
- The Zenodo input archive.
- The validated v0.3 code for existing cells, the transfer runner, the gradient diagnostics, the journal, the blinding gate and the launcher.

**Not reused:** v1 LSTM fits. v1's S1/S2 used model-specific contexts, there is no v1 M0, and identical training runs between the v1 pipeline and the v0.3 engine haven't been shown. Mixing pipelines would confound the 2×2. All four LSTM cells are refitted with the v0.3 engine.

## P8. Not done in v0.4

- Five-seed expansion; hyperparameter grids.
- Materna or TimeTrack reruns.
- Huber, PCGrad, GradNorm, task-grouping and task-checkpoint control.
- M0-H128 capacity sensitivity; lookahead (TAG) affinity.
- LightGBM; systems latency, throughput and RSS benchmarks; the provisioning simulation.
- Any other scope expansion.

## P9. Budget, compute and execution

**Fit counts.** There are 100 groups (20 VMs × 5 folds) and 3 seeds. A full 2×2 is 10 trajectories per phase (S1 4, S2 4, M0 1, M1 1), so 20 counting inner and final.

| Component | Fits |
|---|---:|
| LSTM 2×2 | 6,000 |
| DLinear 2×2 | 6,000 |
| PatchTST 2×2 | 6,000 |
| iTransformer S2/M1 | 3,000 |
| Transfer lattice (D-5: 10 subsets) | 6,000 |
| **Total** | **27,000** |

Gradient diagnostics (D-4) add 600 extractions, not fits. D-1, D-2, D-3, D-6 and D-7 need no fits. Failures and retries are additional to these counts.

**Compute.** Estimates use the measured component timings in `fgcs_strengthening_v03/feasibility/estimate.json`, calibrated ×1.97 (range 1.69–2.01). The modern-family timings were measured on these 20 VMs.

| Component | Basis | Single-worker seconds |
|---|---|---:|
| LSTM | 22.5 s per fit (conservative average) | 135,000 |
| PatchTST | ≤ 1,700 s per group and seed, both phases (S1+M0 measured at 850; S2+M1 assumed no costlier) | 510,000 |
| Transfer lattice | 42.5 s per fit | 255,000 |
| iTransformer | about 84 s per group and seed | 25,000 |
| DLinear | negligible | about 3,000 |
| **Total** | | **about 928,000 (about 10.7 days)** |

- **Worker speedups** come from a sustained 12-minute synthetic benchmark on AC power (2026-11-14/15), so they already include thermal throttling: the thermal state reached "fair" (1) at every worker count, never "serious" (2) or "critical" (3), and there were no errors. The model classes and training mix match v0.4-min; the data were random tensors. The earlier short-probe speedup (2.87 for four workers) overstated sustained throughput.

  | Workers | Sustained speedup | Fits per hour | Compute |
  |---:|---:|---:|---:|
  | 4 | 2.55 | about 267 | about **4.2 days** |
  | 6 | 3.00 | about 314 | about **3.6 days** |
  | 8 | 3.04 | about 319 | about 3.5 days; not used: the 1-minute load reached 87, leaving no headroom for the monitor or backups |

- **Worker count: exactly six fit workers**, each a separate single-threaded process (torch intra-op and inter-op threads 1; `OMP_NUM_THREADS`, `MKL_NUM_THREADS` and `OPENBLAS_NUM_THREADS` set to 1 before Python starts; CPU only). Six gave 18 % more sustained throughput than four with the same thermal state and no errors; eight added 1 % and overloaded the host. The v0.4 schedule and launcher enforce six; r3's four-worker limit applies only to r3.
- **Compute with six workers:** about **3.6 days**; allowing about 10 % for retries and real-fit overhead (data loading, checkpoints) that the synthetic benchmark excluded, about **3.9 days**.
- **Storage:** about 5–6 GB. Each float32 checkpoint is about 0.2–0.3 MB (about 50,000–73,000 parameters for LSTM, PatchTST and iTransformer; 190 for DLinear). One checkpoint per final fit (13,500, about 3.4 GB), the selected state of each modern inner fit (about 1.3 GB) and v0.3's three diagnostic checkpoints per LSTM M0/M1 final fit (about 0.4 GB), plus journal records. r3's 40–62 GB projection does not scale down to v0.4: most of it came from components v0.4 drops (interventions, task-checkpoint control, LightGBM and 1.7 million gradient extractions).

**Run order.** Each step starts only after the previous one is complete:
1. structural checks for every new cell (P3), one worker;
2. a canary of inner fits on six workers, with the v0.3 canary gate (technical evidence only, approved by the author);
3. all inner fits;
4. all final fits;
5. D-4 gradient extractions;
6. fit closure;
7. evaluation closure, after which outer-test outcomes and the outcome-based diagnostics (D-3, D-5 analysis, D-6) are computed.

r3's systems phase is dropped: v0.4 runs no systems benchmarks (P8).

**Execution.**
- New code: DLinear S2/M1, PatchTST S2/M1, the D-1/D-3/D-6 analyses, the P4 analysis, and the v0.4 schedule.
- Then: a new execution seal and registration package, an independent audit, and the launcher re-pointed to the v0.4 seal, with six worker slots and no systems phase. The r3 package stays locked permanently (`EXECUTION_UNLOCKED = NO`).
- **Registration:** a new OSF registration (Secondary Data Preregistration), registered before any v0.4 run. It links to OSF `kuwra`, states that v0.3 was superseded before execution, and reuses the Zenodo input archive. `kuwra` is not withdrawn.
- **Deviations:** any change after freezing is logged with its date, reason and affected components, through a chained seal amendment.

## P10. Reporting (comment 3; after results are fixed)

- **Central thesis, if supported:** contextual input and representation sharing are separable design decisions with different resource-specific consequences.
- **Instruments:** S1, S2, M0 and M1 are instruments, not the object of study. The 2×2 is the central conceptual figure.
- **Structure:** results are organised by question: how the backbones compare (baseline accuracy, P4); when context helps; when sharing hurts; and why (P5). Parameter counts appear with the sharing results.
- **Abstract and introduction** are rewritten around the findings. Repeated protocol detail and caveats move to the supplement.
- **Wording:** "reviewer challenges" and "reviewer-motivated" are removed.
- **Updated sections:** related work, discussion, threats to validity and conclusion.
- **Title:** a finding-based title is chosen only after results.
- **Tiers:** tier-1 and tier-2 results always appear separately.

## P11. Declared compromises (to be stated in the paper)

1. **Reduced cohort.** 20 of 70 Bitbrains VMs, so precision is lower and intervals at 10 VMs per block are wide. New claims are limited to these VMs; tier 1 remains the full-cohort evidence for S1/S2/M1.
2. **No Materna or TimeTrack in the new work.** The modern-baseline and mechanism findings are Bitbrains-only, with no temporal replication.
3. **Three seeds.** This matches tier 1, but seed-stability evidence is weaker than with five.
4. **Fixed, untuned hyperparameters.** The modern baselines may be under-tuned. Fairness rests on identical treatment, not equal tuning effort.
5. **LSTM-selected contexts** are imposed on every backbone, and PatchTST uses short-patch adaptations.
6. **Design-defined cells.** iTransformer S1/M0 are undefined. DLinear M1's sharing exists only through the d = 16 bottleneck, which at L = 4 has lower rank (16) than S2's four maps (up to 20), so DLinear M1:S2 partly reflects reduced capacity. DLinear M0 shares one map across all four resources with no resource-specific head, unlike the LSTM and PatchTST M0 cells.
7. **Full 2×2 for the modern backbones.** Comment 1 asks for modern baselines; DLinear and PatchTST receive new S2/M1 cells so that comment 3's context-versus-sharing contrasts can be tested beyond the LSTM. This is the largest discretionary cost (new code; about half of the PatchTST compute).
8. **Gradient diagnostics are LSTM-only.** Conflict is not measured for the modern shared models.
9. **Affinity comes from empirical pairwise transfer**, not training-time lookahead.
10. **Dependence evidence partly reuses post-hoc Ridge outcomes** already observed (tier 2). Only D-1 is new and training-only.
11. **No interventions.** The explanation of sharing degradation remains associational.
