# Analysis plan v0.4: FGCS revision protocol amendment — DRAFT

**Status: draft, 2026-11-13; author decisions D1–D16 resolved 2026-11-14 (all as recommended). Not yet frozen, sealed or registered; nothing has run.**

- **Supersedes:** v0.3 (`analysis_plan_v0.3.md`; registration package r3, OSF `kuwra`) **before any v0.3 execution**. No v0.3 scientific fit, outer-test evaluation or analysis has occurred.
- **Baseline:** manuscript "Evaluating Contextual Input and Shared Representation in Multi-Metric Runtime Forecasting for Cloud Software Systems" (repository tag `jss-review-robustness-reproducibility-v1`).
- **Decisions** D1–D16 are resolved (see the table at the end). Freezing still requires the implementation review in A11.

---

## A0. Purpose, scope and evidence tiers

**Revision objective.** Study two design choices, **contextual input** and **representation sharing**, as separable decisions. Determine whether their effects generalise across model families, and whether the observed sharing degradation can be explained empirically. S1, S2, M0 and M1 are experimental instruments, not the object of study.

**Evidence tiers** (kept separate in every table, figure and claim):

| Tier | Content | Status |
|---|---|---|
| **Tier 1, frozen primary study** | S1/S2/M1 LSTM, three seeds, model-specific selected contexts, all six blocks | Unchanged; already observed. Nothing in v0.4 re-analyses or replaces it |
| **Tier 2, extension** | The existing post-hoc controls (common-context S2, M1-H129, Ridge AR/ARX) plus everything specified below | Existing controls are already observed and labelled post-hoc. All new work is prospective under v0.4 |

**Hypothesis status.**
- Tier 2 tests no new confirmatory hypothesis (**D1**).
- It reports the paper's descriptive endpoints, frozen classifications and bootstrap intervals. There are no p-values and no multiplicity families.
- The v0.3 Holm and BH families are withdrawn.

**Outcomes.** Null, mixed or conflicting results from any diagnostic are valid outcomes and will be reported as such. **Gradient conflict is not assumed to explain sharing degradation.**

## A1. Retained without change (from tier 1 and v0.3)

- **Cohorts.** The existing 35 selected VMs in each Bitbrains environment (fastStorage, Rnd) and in Materna (T1–T3, the same VMs per trace). The eligibility rules (Section "Population Restrictions") are unchanged.
- **Data handling:**
  - the v1 origin IDs and maximum-context legal support;
  - five purged expanding outer folds, plus inner splits;
  - horizons {1, 2, 4, 9, 18};
  - source-specific transforms, training-only median/IQR scalers, native inverse and the non-negativity projection.
- **Inputs.** Byte-identical to the sealed inputs archived at Zenodo `10.5281/zenodo.24189108`, plus the tracked repository inputs.
- **Evaluation.** Native MAE on the exact same test origins for every compared model, and persistence as the absolute check.
- **Training rules, for all neural backbones:**
  - batch size 256, at most 50 inner epochs, patience 7, gradient clipping 1.0;
  - inner early stopping on scaled validation MSE (joint mean MSE for shared models), with the earliest strictly lowest epoch kept;
  - the final refit uses each seed's selected epoch, with no outer-test selection.
- **Execution rules.** Phase order and blinding (v0.3 C6): no outer-test data are read before fit closure. Retry and amendment rules follow v0.3 C3.
- **Out of scope:** TimeTrack. It stays tier-1 only (development data; descriptive).

## A2. Design: 2×2 per backbone

| Cell | Input | Parameters |
|---|---|---|
| **S1** | own resource | independent model per target (4 models) |
| **S2** | all four resources | independent model per target (4 models) |
| **M0** | own resource | one shared model, four target outputs |
| **M1** | all four resources | one shared model, four target outputs |

**Contrasts** (candidate:reference):
- **context, independent:** S2:S1;
- **context, shared:** M1:M0;
- **sharing, own input:** M0:S1;
- **sharing, all input:** M1:S2;
- **interaction:** sharing effect under all-input minus sharing effect under own-input.

**Context length.** Every cell uses the **frozen v1 H64-M1-selected context L** for each entity and fold; there is no new context selection. This is declared as a fairness threat: L was selected for an LSTM. The difference from tier 1 (model-specific selected L) is declared too.

**Validity by backbone:**

| Backbone | S1 | S2 | M0 | M1 | Notes |
|---|---|---|---|---|---|
| LSTM | ✓ | ✓ | ✓ | ✓ | v0.3 implementation |
| DLinear | ✓ | ✓ new | ✓ | ✓ new | Mixing form in A3.2 |
| PatchTST-style | ✓ | ✓ new | ✓ | ✓ new | Channel-dependent tokens in A3.3 |
| iTransformer-style | — | ✓ | — | ✓ | S1/M0 are **structurally undefined** (A3.4) |

## A3. Backbone specifications

### A3.1 LSTM (v0.3 §1, unchanged)

- Two layers, unidirectional, dropout 0.1, hidden size H64, biased linear horizon heads.
- S1: four own-input networks. S2: four all-input networks.
- M0: an input-size-1 encoder shared across the four own-resource histories, four resource heads, no resource embedding.
- M1: an all-four-input encoder with four heads.
- Shared models use the equal arithmetic mean of the four scaled-resource MSEs.

### A3.2 DLinear (replicate-padded moving average, kernel = min(25, largest odd integer ≤ L), i.e. 3/9/17)

- **S1:** per target, separate trend and residual linear maps L→5 on the target's own channel.
- **M0:** one pair of trend/residual maps reused on each resource channel (weight tying), with four resource outputs and no channel mixing. *Sharing here is weight tying across channels.*
- **S2 (new):** per target, a linear map from all four channels' trend and residual components (8L inputs) to 5 outputs: a decomposed linear ARX.
- **M1 (new):** a **shared linear bottleneck**, 8L → d (no activation), then per-target linear heads d → 5.
  - **Why the bottleneck is required:** without it, a joint linear map trained with a per-target-separable loss has an optimum identical, target by target, to four S2 maps. Sharing would then be vacuous, coupled only through the optimiser.
  - **D2:** d = 16. That keeps M1's parameter count close to the four-map S2 complement at L = 18 (about 2.6k vs 2.9k).

### A3.3 PatchTST-style (patch 2, stride 1, giving 3/8/17 patches; d_model 64, 4 heads, 2 layers, FF 128, dropout 0.1, learned positional encoding, mean pooling, GELU, post-norm)

- **S1:** four own-input models. **M0:** one backbone applied separately to each resource channel, with resource-specific linear heads (v0.3).
- **S2 (new):** channel-dependent tokens. Each token is the four channels' values in one patch (4 × 2 = 8 values), projected linearly to d_model. There is one model per target, with one head.
- **M1 (new):** the same channel-dependent backbone, shared, with four resource-specific heads.
- These are declared adaptations (short patches, channel-dependent embedding), not canonical PatchTST.

### A3.4 iTransformer-style (variate tokens via Linear(L, 64); 2 layers, 4 heads, FF 128, dropout 0.1; the four encoded tokens flattened before each 5-output head)

- **S2:** four independent models, each seeing all four variate tokens and predicting one resource. **M1:** one joint model with four heads.
- **S1/M0 are structurally undefined.** A single variate token makes self-attention attend only to itself, so the backbone degenerates to a token-wise MLP.
  - **D3:** S1/M0 are omitted for iTransformer and shown as undefined in every table.

### A3.5 Shared settings and validity checks

- **Optimisers.** LSTM and DLinear use Adam. Transformers use AdamW with weight decay 1e-4.
- **Synthetic structural tests** before any data fit, for every new cell, at L = 4, 9 and 18:
  - finite forward and backward passes;
  - five outputs per target;
  - every lag reaches an output;
  - every parameter connects to the loss;
  - own-input independence for S1/M0 (varying the other channels leaves outputs unchanged);
  - input-perturbation effects across channels for S2/M1.

## A4. Hyperparameter grid, seeds and selection

- **Grid (D4):** learning rate ∈ {1e-3, 3e-3} for every backbone and cell. Architecture constants are fixed as in A3, so parameter counts stay comparable.
- **Selection:**
  1. For each block × backbone × cell, fit seed 0 at both learning rates on all entities and folds (inner phase only).
  2. Choose the rate with the lower mean inner-validation scaled MSE (joint mean MSE for shared models), averaged equally over entities and folds. A tie goes to 1e-3.
  3. Use the selected rate for seeds 0–4. Seed 0's inner fits at that rate are reused.
- **Seeds:** **0–4** for every stochastic model, LSTM included (5 seeds).
- **Parameter counts:** recorded per model and per complement. **Fit-hours:** from the journal's optimisation, validation and checkpoint timings; per-fit seconds are summed and reported per cell.

## A5. Endpoints and analysis (as in the paper; tier 2 only)

- **Aggregation.** Native MAE is averaged over the **five** seeds within each environment/trace × entity × fold × resource × horizon × cell. MacroMAE gives those cells equal weight. The resource-overall MacroMAE gives every horizon equal weight.
- **Primary endpoint.** The MacroMAE gain G(C:B) = 100 · (MacroMAE(B) − MacroMAE(C)) / MacroMAE(B), per contrast, resource, block and backbone. Materna's temporal synthesis is G_temporal = (G_T1 + G_T2 + G_T3)/3.
- **Consistency classes.** These are the paper's predicates, with the seed thresholds rescaled for five seeds (**D5**):
  - **Broad Positive:** G ≥ +1 %, with ≥ 4/5 horizons, ≥ 25/35 VMs, ≥ 4/5 folds and **≥ 4/5 seeds** positive.
  - **Conditionally Positive:** G > 0, with ≥ 3/5 horizons, ≥ 15/35 VMs, ≥ 3/5 folds and **≥ 3/5 seeds** positive.
  - **Broad Negative:** G ≤ −1 %, with ≤ 1/5 horizons, ≤ 10/35 VMs, ≤ 1/5 folds and **≤ 1/5 seeds** positive.
  - **Neutral or Mixed:** everything else.
- **Uncertainty.** A paired VM-cluster bootstrap within each Bitbrains environment and each Materna trace: 35 VMs resampled with replacement, all five folds and the paired cell structure kept, run on seed-averaged matched MAEs. 10,000 replicates; percentile 95 % intervals; random seed **20261007**, as in the paper (**D6**). Intervals never enter the classification predicates.
- **Interaction.** Reported descriptively: both sharing gains side by side, and the entity log-ratio I = ln A_M1 − ln A_S2 − ln A_M0 + ln A_S1 with its bootstrap interval. It is a secondary quantity, not a test.
- **Secondary descriptives:**
  - the matched-cell median MAE ratio and win rate;
  - persistence skill, computed per cell then averaged as in the paper, with undefined zero-denominator skills counted, not replaced.
- **Cross-backbone effect-direction summary (D7).** For each contrast × resource × group, tabulate each backbone's class. An effect **"generalises across backbones"** only if every backbone for which the contrast is defined has a non-neutral class of the same sign. **"Backbone-dependent"** covers mixed signs, or at least one neutral where others agree. No pooled cross-backbone statistic is computed.

## A6. Mechanism diagnostics (Workstream 2)

All are computed from training-side data or post-closure outcomes, as stated for each. None changes any model.

| # | Diagnostic | Definition | Data used | Scope |
|---|---|---|---|---|
| **W2.1a** | Lagged cross-correlation | Pearson correlation between ordered resource pairs (i→j) on transformed, robust-scaled series, lags 1…L_max = 18; summary: the maximum absolute value over lags, per entity × fold | Inner-training windows only | FS, Rnd, Materna |
| **W2.1b** | Conditional predictive dependence (Granger-style, residual-based) | Per target: Ridge AR (own lags) vs ARX (all four lag windows) at frozen L, α ∈ {0.01, 0.1, 1, 10, 100} chosen on the inner split; statistic ΔR_r = 1 − MSE_ARX / MSE_AR on inner-validation residuals | Inner split only | FS, Rnd, Materna |
| **W2.1c** | Relationship to effects | Spearman correlation across entities between W2.1a/b and the entity LSTM log effects D(S2:S1) and D(M1:S2), per resource × group, with VM-cluster bootstrap intervals | After evaluation closure | FS, Rnd, Materna |
| **W2.2** | Gradient conflict and magnitude imbalance | On the M1 shared encoder (all LSTM encoder weights and biases, in named order), at the final selected epoch E, with eight keyed A/B batch pairs of 128 (v0.3 §5 keys): the six pairwise task-gradient cosines, the max/min task-gradient L2-norm ratio, and excess conflict K (cross-task minus same-task sign-conflict rate). M0 is descriptive. Final slot only; no per-epoch logging (**D8**) | Outer-training batches only | All LSTM M0/M1 finals, seeds 0–4 |
| **W2.3** | Task affinity (4×4) | Directed pairwise transfer F_i({i,j}) = ln[A(S2_i) / A(pair_{i,j}, target i)], per target i ≠ j. The lookahead method of Fifty et al. is **not** used (**D9**): with four tasks, the empirical pairwise lattice measures transfer directly | After evaluation closure | FS, Rnd |
| **W2.4** | Transfer lattice | All-input LSTM (H64, all four input channels) on the 6 pairwise and 4 leave-one-out subsets, retained-task heads only, equal mean retained-task loss, with its own inner early stopping and fixed-epoch refit. Reference: S2 per target; full reference: M1. Leave-one-out contribution Q_{i,j} = ln[A(subset without j, target i) / A(M1, target i)]. Seeds 0–2 (**D10**) | Fits on training data; analysed after closure | FS, Rnd |
| **W2.5a** | Per-task loss contributions | Each task's share of M1's training MSE per epoch, and at E (already in the training journal) | Training only | All M1 |
| **W2.5b** | Robust-loss sensitivity | M1 retrained with Huber loss on robust-scaled targets, δ = 1.0 (**D11**), other settings unchanged, five seeds; compared with M1-MSE and S2 | Fits on training data; analysed after closure | FS, Rnd, Materna |
| **W2.5c** | Outlier sensitivity (analysis only, no fits) | **(i)** Named: exclude Materna VM266 and VM272 (the paper's T1/T3 disk-write tail VMs) from all three traces. **(ii)** Training-only rule: exclude, per block, the 3 VMs with the largest native disk-write training IQR (**D12**). Both re-compute A5 for the LSTM 2×2. Variant (i) is labelled outcome-informed (the VMs were identified from tier-1 errors); (ii) is the prospective analogue | After closure | Materna (i); all blocks (ii) |

**Interpretation rules.**
- Diagnostics are **descriptive associations**, not causal identification.
- A null or opposite-direction association is reported as such.
- No diagnostic result changes the design or the analysis of any other component.

## A7. Interventions (conditional; run only after diagnostics)

- **Trigger (D13).** Uses training-side diagnostics only (W2.2, no outer-test data), evaluated at fit closure of the core LSTM M1 runs. PCGrad-M1 and GradNorm-M1 are run if, in fastStorage or Rnd, either:
  - the mean entity K at E has a VM-cluster bootstrap 95 % interval entirely above 0; or
  - the median task-gradient norm ratio exceeds 2.

  The trigger's evaluation and result are reported whether it fires or not.
- **PCGrad-M1 and GradNorm-M1:** exactly as v0.3 §6 (PCGrad: independent permutations, projection against the original gradients; GradNorm: α = 1.5 on the second-layer encoder tensors, as implemented). FS and Rnd, seeds 0–4, both phases. Compared with M1 and S2 using A5.
- **Best task grouping (no new fits).**
  - Of the 15 partitions of {CPU, THROUGHPUT, MEMORY, DISK_WRITE}, choose per block the one with the lowest mean inner-validation scaled MSE across targets. Each group in a partition maps to S2 (size 1), a pairwise model (size 2), a leave-one-out model (size 3) or M1 (size 4), all from W2.4 and the 2×2.
  - The chosen partition is then evaluated once on the outer test against M1 and S2. Selection never uses outer-test data.

## A8. Sensitivities (diagnostic only, never primary)

- Robust loss (W2.5b) and outlier exclusion (W2.5c).
- The existing tier-2 post-hoc controls are reported as before.
- No M0-H128 capacity sensitivity (**D14**); tier 1's M1-H129 control remains.

## A9. Not done in v0.4

- LightGBM.
- Systems latency, throughput and RSS benchmarks. Parameter counts and fit-hours suffice.
- Task-checkpoint control.
- TimeTrack in tier 2.
- The v0.3 inferential families.
- The optional provisioning simulation (only after Workstreams 1–3, under a separate amendment).

## A10. Budget (successful required fits; failures and retries are additional)

**Groups** (entity × fold): FS and Rnd 350; Materna T1–T3 525.

A full 2×2 is **10 trajectories per phase** (S1 4, S2 4, M0 1, M1 1), so 20 counting inner and final.

| Component | Scope | Seeds | Fits |
|---|---|---:|---:|
| LSTM 2×2 | FS, Rnd, Materna (875 groups) | 5 | 87,500 |
| DLinear 2×2 | FS, Rnd | 5 | 35,000 |
| PatchTST 2×2 | FS, Rnd, **first 10 VMs per block by frozen cohort rank** (100 groups) (**D15**) | 5 | 10,000 |
| iTransformer S2/M1 | FS, Rnd | 5 | 17,500 |
| Learning-rate grid (second rate, inner, seed 0) | as above | 1 | about 15,000 |
| Transfer lattice (W2.4) | FS, Rnd | 3 | 21,000 |
| Robust-loss M1 (W2.5b) | FS, Rnd, Materna | 5 | 8,750 |
| *Conditional:* PCGrad-M1 and GradNorm-M1 | FS, Rnd | 5 | *7,000* |
| **Total** | | | **about 194,750, plus 7,000 conditional** |

**Compute.** Estimates use measured component timings (`fgcs_strengthening_v03/feasibility/estimate.json`) calibrated ×1.97 (range 1.69–2.01) and the measured 4-worker speedup of 2.87. Thermal throttling on the fanless host may lengthen them.

| Design (D16: recommended variant) | Single worker | Four workers |
|---|---:|---:|
| Required fits (table above) | about 51 days | about 18 days |
| Conditional interventions, if triggered | +2.8 days | +1 day |

The cost drivers are the LSTM 2×2 (about 7.9 days at four workers), the lattice (about 3.6), and PatchTST (about 3.8 with D15). Running PatchTST on the full cohort would add about 23 days at four workers.


## A11. Execution, registration and deviations

- **Implementation changes (code; reviewed and audited before sealing):**
  - DLinear S2/M1 (A3.2);
  - PatchTST S2/M1 (A3.3);
  - iTransformer validity handling (A3.4);
  - the learning-rate grid and block-level selection;
  - Huber loss;
  - W2.1 dependence analyses;
  - the W2.3/W2.4 lattice and best-grouping analyses;
  - the A5 analysis (G, five-seed classes, bootstrap, cross-backbone summary);
  - the v0.4 schedule;
- **Reused:** the v0.3 data adapters, journal, blinding gate, retry/amendment rules, orchestrator, launcher (re-pointed to the v0.4 seal and package) and backups.
- **Sealing.** A new execution seal and registration package, `v0.4`. The r3 package stays locked permanently (`EXECUTION_UNLOCKED = NO`).
- **Registration.** A new OSF registration (Secondary Data Preregistration) that links to OSF `kuwra` and states that v0.3 was superseded before execution. It reuses Zenodo `10.5281/zenodo.24189108` for the unchanged inputs. `kuwra` is not withdrawn.
- **Deviations.** Any change after freezing is logged with its date, reason and affected components, and goes through a chained seal amendment.

## A12. Reporting (Workstream 3; after results are fixed)

- **Central thesis, if supported:** contextual input and representation sharing are separable design decisions with different resource-specific consequences.
- **Structure:** results organised by question (when context helps; when sharing hurts; why; cost and trade-offs), with the 2×2 as the central conceptual figure.
- **Housekeeping:** repeated protocol detail moves to the supplement, and "reviewer challenges"/"reviewer-motivated" wording is removed.
- **Updates:** related work, discussion, threats and conclusion.
- **Title and cover letter:** a title based on the finding is chosen only after results. The FGCS cover letter positions this as a follow-up to MMRP.
- **Tiers:** tier-1 and tier-2 results always appear separately.

---

### Author decisions (resolved 2026-11-14)

| # | Decision | Resolution |
|---|---|---|
| D1 | Confirmatory tests in tier 2 | None: descriptive classes and intervals, as in the paper |
| D2 | DLinear M1 | Shared linear bottleneck, d = 16 |
| D3 | iTransformer S1/M0 | Omitted; shown as structurally undefined |
| D4 | Grid | Learning rate {1e-3, 3e-3}, selected per block × backbone × cell on seed 0 |
| D5 | Five-seed class thresholds | 4/5 (broad), 3/5 (conditional), ≤ 1/5 (broad negative) |
| D6 | Bootstrap seed | 20261007 (the paper's) |
| D7 | "Generalises" rule | Same-sign non-neutral class for every backbone where defined |
| D8 | Gradient logging | Final slot only |
| D9 | Lookahead affinity (Fifty et al.) | Not used; empirical pairwise lattice instead |
| D10 | Lattice seeds | 0–2 |
| D11 | Huber δ | 1.0 on robust-scaled targets |
| D12 | Outlier rules | (i) named VM266 and VM272, labelled outcome-informed; (ii) top 3 by native disk-write training IQR per block |
| D13 | Intervention trigger | K interval above 0, or median norm ratio > 2, in fastStorage or Rnd |
| D14 | M0-H128 capacity sensitivity | Not included |
| D15 | PatchTST cohort | First 10 VMs per block by frozen cohort rank |
| D16 | Budget variant | Recommended: about 194,750 fits, about 18 days on four workers |
