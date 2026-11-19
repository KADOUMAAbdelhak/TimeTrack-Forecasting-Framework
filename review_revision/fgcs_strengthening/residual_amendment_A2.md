# v0.4 amendment A2 (frozen): forecasting the change from the last value

**Status: approved by the authors as written, 19 Nov 2026 (all four Section 9 decisions as recommended: all four backbones, change parameterisation for all four resources, the stated thresholds, longer contexts and tuning out of scope).** Implemented in `fgcs_strengthening_v04a2/`. **Frozen 19 Nov 2026** (tag `fgcs-v04-a2-residual`); no A2 fit had run before the freeze. Once approved, A2 is frozen by its own package, execution seal and Git tag before any A2 fit, as A1 was. After the freeze, every section below is a decision, and changing one is a logged deviation.

## 1. Why this amendment

In tier 2, no backbone beat persistence for CPU or throughput. Memory and disk write beat it everywhere.

| Block | Resource | Backbone × cell combinations with positive persistence skill | Best skill |
|---|---|---:|---:|
| fastStorage | CPU | 0 / 14 | −0.058 (DLinear S1) |
| fastStorage | Throughput | 0 / 14 | −0.039 (PatchTST M0) |
| fastStorage | Memory | 14 / 14 | +0.193 |
| fastStorage | Disk write | 14 / 14 | +0.297 |
| Rnd | CPU | 0 / 14 | −0.090 (DLinear S2) |
| Rnd | Throughput | 0 / 14 | −0.037 (LSTM S1) |
| Rnd | Memory | 14 / 14 | +0.178 |
| Rnd | Disk write | 14 / 14 | +0.313 |

(Source: `analysis_v04.json`, P4 baseline accuracy; skill = mean over cells of 1 − MAE/MAE_persistence.)

A reviewer can therefore read the sharing cost as a difference between models that are worse than the simplest forecast. A2 asks whether the cost remains when every model can reproduce persistence exactly and only has to learn the change.

**Timing, stated plainly:** A2 is post hoc. It was motivated by the tier-2 persistence results and by an external review, after tier 2 and A1 were complete. It is specified before any A2 fit.

> **H-A2.** When each forecast is parameterised as the last observed value plus a learned change, shared models remain less accurate than independent models in typical cells (M1:S2, and M0:S1).

**Pre-stated direction:** if the sharing cost is a property of sharing rather than of models that fail to beat persistence, M1:S2 median ratios stay above 1 in most cells under A2. A reduced, absent or reversed cost is reported as such.

**Precondition:** H-A2 can only answer the reviewer's question if the change parameterisation makes the models beat persistence. Section 5 therefore checks this first.

## 2. What changes and what does not

**Changes: only the output parameterisation.** For target resource *k*, horizon *h* and origin *t*, every model outputs

  ŝ_k(t+h) = s_k(t) + f_k,h(x),

where:
- s_k(t) is the scaled value of resource *k* in the last row of the input window, using the same training-only scaler as the targets;
- f is the backbone's usual output.

Training still minimises the scaled MSE, which equals the MSE on the scaled change s_k(t+h) − s_k(t). The anchor s_k(t) is taken from the input window only, never from a target.

**Consequences:**
- **Nesting:** with f ≡ 0, the inverse transform and projection return the last observed native value. The model then nests v1 persistence, up to float32 rounding. This is verified on real units before the freeze, by the persistence-nesting test in Section 7.
- **Log resources:** for throughput and disk write (log1p transform), the learned change is a change in log space, so roughly a relative change.
- **DLinear:** a linear map can already copy the last value, so the reparameterisation does not enlarge its hypothesis class. Any DLinear difference comes from initialisation and optimisation, not capacity.

**Unchanged (tier 2 exactly):**
- **Data:** the 20 Bitbrains VMs, purged folds, frozen H64-M1 contexts L ∈ {4, 9, 18}, horizons {1, 2, 4, 9, 18}, transforms, training-only scalers, inverse transform, projection and native-unit test origins.
- **Backbones and training:** architectures and fixed hyperparameters (learning rate 10⁻³, batch 256, at most 50 inner epochs, patience 7, clipping 1.0, seeds 0–2).
- **Loss:** the equal-weight loss. A1's weighting is not combined with A2.
- **Selection:** the equal-mean scaled validation MSE, with a final refit at the selected epoch.
- **Not addressed:** longer contexts and tuning, the review's second experiment, are not part of A2.

## 3. Arms

| Backbone | A2 cells (change parameterisation) | References (read only, not refitted) |
|---|---|---|
| LSTM | S1, S2, M0, M1 | tier-2 level-parameterised cells; v1 persistence |
| DLinear | S1, S2, M0, M1 | same |
| PatchTST-style | S1, S2, M0, M1 | same |
| iTransformer-style | S2, M1 (S1 and M0 undefined, as in tier 2) | same |

The anchor is added after each backbone's output layer, for every cell and all four resources (Section 9, decision 2).

## 4. Endpoints

All endpoints use the tier-2 P4 machinery: seed-averaged entity × fold × horizon cells; MacroMAE; consistency classes with VM thresholds for ten VMs; and VM-cluster bootstrap with 10,000 replicates, seed 20261007, reusing the tier-2 draw matrices.

- **Precondition:** persistence skill of every A2 backbone × cell × resource × block, computed as in tier 2 against v1 persistence on the same units.
- **Primary (sharing under the change parameterisation):** for M1:S2, the matched-cell median MAE ratio and win rate per backbone × resource × block. That is 32 cells, the same construction as the tier-2 headline (30 of 32 ratios above 1).
- **Secondary:**
  - M0:S1 (24 cells), and the context contrasts S2:S1 and M1:M0;
  - MacroMAE gains, classes and intervals for every contrast;
  - the per-cell effect of the parameterisation, A2 cell : tier-2 cell (matched median ratio, win rate).
- **Restricted analysis:** M1:S2 over the cells where both A2 M1 and A2 S2 have positive persistence skill.

## 5. Decision rule (frozen before any run; descriptive, no p-values)

1. **Precondition met** if A2 S2 has positive persistence skill in at least **8 of the 16** backbone × block × {CPU, throughput} cells. If it is not met, A2's main result is that the change parameterisation does not make these models beat persistence. The sharing endpoints are still reported, but they cannot answer the reviewer's question.
2. **Sharing cost holds** if the M1:S2 median ratio is above 1 in at least **24 of 32** cells. **Does not hold** if it is above 1 in at most **16 of 32**. **Mixed** otherwise.
3. **Restricted analysis:** the sharing cost **holds among persistence-beating models** if the restricted set has at least 8 cells and the M1:S2 median ratio is above 1 in at least three quarters of them. **Too few cells** if the set has fewer than 8.

As in tier 2, the decision uses the scale-free typical-cell statistics; MacroMAE gains are reported but do not decide.

## 6. Scale and execution

- **Fits:** the tier-2 2×2 for four backbones:
  - LSTM 3,000 + 3,000;
  - DLinear 3,000 + 3,000;
  - PatchTST-style 3,000 + 3,000;
  - iTransformer-style 1,500 + 1,500.

  That is **21,000 fits** (inner + final) and **10,500 outer-test evaluations**, with no D-4 or transfer lattice.
- **Time:** the same cells took **84 worker-hours** in tier 2 (LSTM 43, PatchTST-style 36, iTransformer-style 4.4, DLinear 0.8), so about **14 hours** with six workers, plus evaluation. The estimate is 15–20 hours. The machine must stay on AC power, because the launcher pauses after two minutes on battery.
- **Architecture** (as A1): a derived package `fgcs_strengthening_v04a2/`, built from tag `fgcs-v04-a1-intervention`.
  - It has its own namespace, runtime, configuration, execution seal and tag `fgcs-v04-a2-residual`, and records its lineage to the tier-2 and A1 tags.
  - Only A2 units are scheduled.
  - The tier-2 references and v1 persistence are read through the read-only reader.
- **Certify and canary:**
  - The three modern structural certificates are re-run for the anchored outputs.
  - The canary is the first cohort VM per block, fold 1, seed 0, inner fits of every A2 cell: 35 per block, 70 in all. It stops for author approval.
- **Rules:** the v0.3 C3 retry rules and C6 blinding apply. A unit that still fails after retries is missing for every cell of its backbone.

## 7. Implementation (after approval, before the freeze)

1. **Anchor:** a single anchored-output wrapper used by every backbone and cell. It reads s_k(t) from the last input row of resource *k*, including for own-input cells, whose model sees only that channel.
2. **Identities:** A2 identities carry the parameterisation explicitly, so they can never collide with tier-2 identities. The schedule, canary, certify, evaluation and read-only reference bindings follow.
3. **Tests:**
   - **Persistence nesting:** with f ≡ 0, the native predictions on real units equal the v1 persistence forecasts within float32 tolerance, and the persistence MAE is reproduced.
   - **No leakage:** changing the targets never changes the anchor.
   - **Level path unchanged:** a level-parameterised fit equals its tier-2 journal record (golden hash, as for A1).
   - **Determinism** and unchanged selection.
4. **Analysis:** `analyse_residual.py` (the P4 code plus the precondition, restricted analysis and decision rule) and its exhibit script, with the output-hash check.
5. **Freeze and canary:** audit, tag, unlock, certify and canary, then wait for the authors' approval.

## 8. Reporting

- **Where:**
  - a short paragraph in RQ1 (persistence) and one in RQ3 (sharing), with one main-text table;
  - full tables in a new supplement Section S-G;
  - the abstract's persistence sentence updated with the result.
- **Prediction:** the H-A2 prediction is reported verbatim, with its post-hoc motivation.
- **Any outcome is reported:** precondition met or not; sharing cost holds, does not hold or is mixed.
- **Limits in Threats:**
  - post hoc;
  - still fixed, LSTM-selected short contexts and untuned hyperparameters;
  - 20 VMs and three seeds;
  - change parameterisation in scaled space only.

## 9. Decisions needed from the authors

1. **Backbones:**
   - **all four (recommended, about 15–20 hours):** keeps the cross-backbone claim testable; or
   - **LSTM and DLinear only (about 8 hours):** faster, but the claim then rests on two backbones.
2. **Resources:**
   - **all four resources (recommended):** one uniform parameterisation, so shared models predict all targets the same way and the contrasts stay comparable; or
   - **CPU and throughput only:** shared models would then mix level and change outputs.
3. **Thresholds:** the precondition at 8 of 16, "holds" at 24 of 32, "does not hold" at 16 of 32 or fewer, and the restricted analysis at 8 or more cells with three quarters above 1.
4. **Scope:** A2 leaves longer contexts and tuning, the review's second experiment, for a later amendment or the revision.

## 10. Implementation notes (recorded before the freeze, 19 Nov 2026)

These follow from Sections 2 and 7 and change no decision.

1. **Hook.** The anchor is a forward hook attached wherever a model is built: LSTM training, the modern runner, outer-test evaluation and the modern structural certificates. It adds s_k(t) to every horizon of task *k*'s output. It has no parameters, so state dicts, checkpoints and architectures equal those of the level models. The configuration fixes the parameterisation as `change`; a `level` setting exists only for the golden tests.
2. **Identities.** Every A2 identity payload records `target_parameterisation: change` (schema version 2).
3. **Checks before the freeze:**
   - **Persistence nesting:** with a zero learned change, the anchored native forecast reproduces the frozen v1 persistence MAE on real units in both blocks, worst relative difference 1.2 × 10⁻⁶ (float32 rounding).
   - **Level path:** level-parameterised LSTM M1 and DLinear S1 fits reproduce their tier-2 journal records exactly (model hashes, epochs, selection).
   - **Certificates:** the anchored structural certificates pass for all three modern families.
4. **Analysis.**
   - The precondition uses the tier-2 baseline-accuracy construction (common units across backbones).
   - The restricted analysis uses the persistence skills computed with each M1:S2 contrast.

