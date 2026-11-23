# Amendment A3: validation-gated consolidation and task grouping

**Status:** post-hoc amendment on existing fits. It was proposed after every tier-1, tier-2
and A1 result was known. It was specified and frozen under the annotated tag
`fgcs-v04-a3-validation-gate` before any gated, grouping, fallback, oracle or detection
statistic was computed. No model is fitted. Everything is descriptive: no p-values.

**Machine-readable rules:** `fgcs_strengthening_v04a3/configs/protocol_v04a3.json`. Where
this text and the configuration differ, the configuration governs.

## 1. Question

The manuscript recommends checking context and consolidation for each resource before
adopting them. A3 tests whether that recommendation works when it is made operational with
the information an engineer has before deployment: the inner-validation errors of the
candidate models.

- **H-A3a (gate works).** A rule that consolidates a machine's four targets into one
  shared model only when the shared model's inner-validation error is within a tolerance
  of the independent models' keeps at least half of the model saving of always sharing.
  It does so while incurring the typical-cell sharing cost in at most half as many cells
  as always sharing.
- **H-A3b (validation detects the cost).** For each machine, fold and seed, the
  validation-error ratio of the shared to the independent all-input models is rank
  correlated with the corresponding outer-test ratio.
- **H-A3c (selective grouping).** For the tier-2 LSTM, letting validation choose among all
  15 groupings of the four resources saves more models than the all-or-nothing gate,
  without more cost cells.
- **Fallback (secondary).** In tier 2, replacing a target's model by persistence where
  persistence validates better restores positive persistence skill for CPU and throughput.

## 2. Data and units (reused, read only)

**Tier 1.** LSTM S1, S2 and M1 in six blocks: TimeTrack (7 machines, 8 leads), Bitbrains
fastStorage and Rnd, and Materna T1–T3 (35 VMs each, 5 leads). It uses 5 folds and 3
seeds, at the context L that each formulation's inner validation selected.

- **Outer errors:** native MAE from each block's `metrics.parquet`.
- **Validation errors:** `validation_nmae` from `inner_run_registry.csv`. This is the
  inner-validation MAE in training-scaled units at the best epoch, for the same seed and
  the selected L, averaged over leads.
- **Integrity:** every input file is bound to the SHA-256 recorded in the configuration.

**Tier 2.** The closed v0.4 journal, read through a reader that refuses every write.

- **Backbones and cells:** LSTM, DLinear, PatchTST-style and iTransformer-style; S1, S2,
  M0 and M1 where defined.
- **LSTM groupings:** the stored all-input models for the six resource pairs and the four
  triples.
- **Cohort:** 20 VMs, 5 folds, 3 seeds.
- **Outer errors:** native MAE from the closed evaluations.
- **Validation errors:** each inner fit's per-task scaled validation MSE at the epoch
  selected for the final refit.
- **Persistence:** the same MSE for the last scaled value of the resource's own input
  channel, on the same inner-validation windows. The windows are rebuilt with the frozen
  adapters and must match the inner fits' recorded split hash, scaler hash and context.
- **Outer persistence:** v1 persistence on the frozen outer-test support.

**Unit of decision.** Block × entity × fold × seed. A policy uses only that unit's
inner-validation errors. The outer-test errors enter only the evaluation, and the oracle.

## 3. Policies

- **Fixed.** S1, S2, M0 (tier 2, where defined) and M1 for every unit.
- **G-ctx.** For each resource, S2 if its validation error is strictly lower than S1's,
  otherwise S1.
- **G-share(τ)** (primary). Use M1 if the mean over the four resources of the validation
  ratio M1/S2 is at most 1 + τ, otherwise S2.
- **G-full(τ).**
  - The independent baseline is G-ctx, or S2 where S1 is undefined.
  - The shared candidate is whichever of M1 and M0 has the lower mean validation ratio
    against that baseline.
  - Consolidate if that ratio is at most 1 + τ.
- **G-group(τ)** (tier-2 LSTM only).
  - Each of the 15 partitions of the four resources uses S2 for singletons, the stored
    pair and triple models, and M1 for the full set.
  - A partition is feasible if its mean validation ratio against S2 is at most 1 + τ.
  - Choose the feasible partition with the fewest models; break ties by the lower ratio,
    then by the fixed partition order.
- **Fallback** (tier 2). After S2, G-share(1%) or G-group(1%), a target goes to
  persistence where persistence validates strictly better. A persistence target uses no
  model.
- **Oracle** (descriptive upper bound; never a policy, never in a verdict). For each unit,
  the G-share or G-group candidate with the lowest outer score. The outer score is the mean
  over resources of the seed-specific horizon-mean outer MAE ratio against S2.
- **Fixed partitions** (tier-2 LSTM, descriptive). Each of the 15 partitions applied to
  every unit.

τ ∈ {0, 0.5%, 1%, 2%}. The primary tolerance is 1%, the margin already used in the
manuscript.

## 4. Outcomes

- **Accuracy**, per policy × block × resource (× backbone in tier 2):
  - matched-cell median MAE ratio and win rate against S2;
  - matched-cell median ratio against M1;
  - MacroMAE gain against S2.
  All are computed over seed-averaged entity × fold × horizon cells, exactly as in the
  manuscript.
- **Savings:**
  - mean models per unit;
  - savings retained, R = (models(S2) − models(policy)) / (models(S2) − models(M1));
  - in tier 2, mean parameters.
- **Intervals:** VM-cluster percentile bootstrap, seed 20261007, 10,000 replicates.
  - Tier 2 reuses the frozen tier-2 draw matrices.
  - Tier 1 draws one matrix per block from one generator, in the configured block order,
    over entities in lexicographic order.
- **Detection (H-A3b):** Spearman ρ per frame (tier-1 block; tier-2 backbone × block)
  between the unit-level validation score and the unit-level outer score, with a
  VM-cluster interval. Also the balanced accuracy of the sign.

## 5. Decision rules (frozen)

**H-A3a**, judged separately for tier 1 (24 cells) and tier 2 (32 cells), for G-share at 1%:

- A cost cell is a cell whose policy:S2 median ratio exceeds 1.01.
- The reference is the number of M1:S2 cost cells: 22 in tier 1 and 13 in tier 2. The run
  recomputes and checks both.
- cost_ok means the cost cells number at most floor(reference / 2).

| Verdict | Condition |
| --- | --- |
| keeps most savings at reduced cost | R ≥ 0.5 and cost_ok |
| rarely consolidates | R < 0.25 |
| keeps some savings at reduced cost | 0.25 ≤ R < 0.5 and cost_ok |
| does not avoid the cost | R ≥ 0.25 and not cost_ok |

**H-A3b**, per frame:

- **detects:** ρ ≥ 0.3 and the interval's lower bound > 0;
- **weak:** lower bound > 0 and ρ < 0.3;
- **does not detect:** otherwise.

**H-A3c**, for the tier-2 LSTM, G-group(1%) against G-share(1%):

- **grouping adds savings:** mean models at least 0.25 lower, with at most one more cost
  cell;
- **no added savings:** a smaller reduction;
- **adds savings at a cost:** otherwise.

**Fallback.** "Restores positive skill" if S2 + fallback has positive persistence skill in
at least 8 of the 16 tier-2 CPU and throughput cells.

## 6. What each outcome would mean for the manuscript (stated in advance)

| Result | Meaning | Manuscript change |
| --- | --- | --- |
| H-A3a "keeps most savings" and H-A3b "detects" | The recommendation becomes a tested procedure: a validation check makes consolidation cheap and safe | Lead contribution, reporting the saving retained and the cost cells avoided against always sharing |
| H-A3a "rarely consolidates" | At a 1% tolerance, validation almost always rejects sharing | Strengthens the sharing-cost claim at the decision level; consolidation is rarely justified for these models |
| H-A3a "does not avoid the cost", or H-A3b "does not detect" | The usual inner validation cannot tell when sharing will cost accuracy | Qualifies the paper's own advice: validation-based consolidation is unreliable here, and a held-out backtest is needed. Reported as a main result |
| H-A3c "grouping adds savings" | Choosing which resources share recovers savings that all-or-nothing sharing loses | Answers the "selective grouping is untested" limitation with data |
| H-A3c "no added savings" | Groupings offer little beyond all-or-nothing | Selective grouping is tested and does not help here; the limitation is removed and the result reported |
| Fallback restores positive skill | A model-or-persistence check fixes the CPU and throughput boundary in practice | The abstract's persistence sentence becomes a result |
| Fallback does not restore it | Even per-target fallback leaves the boundary | The boundary is reported as robust |

Results are reported whatever their direction. A result that weakens a claim weakens the claim.

## 7. Integrity

- The outer-test errors of every component fit were computed earlier, and their fixed-cell
  contrasts are published. Whoever wrote these rules had seen those contrasts. A3 is
  therefore not a prospective test of the components. What is new is the policies'
  outcomes, which were not computed before the freeze.
- Before the freeze, the input readers and the reproduction guards were run once on the
  real data (`fgcs_strengthening_v04a3/check_readers.py`). They read the inputs and compared
  fixed-cell values with the published results:
  - tier-1 seed means matched the published matched cells within a relative 3 × 10⁻¹³;
  - all 104 tier-2 fixed contrasts matched `analysis_v04.json` exactly;
  - the persistence validation windows matched the recorded splits.
  No policy, oracle, grouping, fallback or detection statistic was computed.
- In tier 1, the inner-validation errors also selected the context L, so they are slightly
  optimistic for every formulation alike.
- Tier-1 validation is a scaled MAE and tier-2 validation a scaled MSE; outer errors are
  native MAE. A gate that compares different metrics is part of what is being tested.
- **Guards** (the run refuses on any failure):
  - recorded input digests and the tier-2 seal;
  - reproduction of the published fixed-cell values;
  - the reference cost-cell counts, 22 and 13;
  - complete links from final fits to inner fits;
  - persistence-window split checks.
- **Limits** carried into Threats to Validity:
  - post hoc;
  - the same cohorts, untuned hyperparameters and fixed contexts as tier 1 and tier 2;
  - ten VMs per tier-2 block;
  - task grouping covers the tier-2 LSTM only.
