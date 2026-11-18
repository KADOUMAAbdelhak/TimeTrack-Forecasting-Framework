# v0.4 amendment A1 (frozen): loss-balancing intervention for the shared LSTM

**Status: approved by the authors as written, 18 Nov 2026 (all four Section 9 decisions as recommended: both arms, 6-of-8 rule with manipulation check, α = 1.5 on the second LSTM layer, existing v0.4 references reused).** Implemented in `fgcs_strengthening_v04a1/`; the Section 10 implementation choices were confirmed by the authors on 18 Nov 2026. **Frozen 18 Nov 2026** (tag `fgcs-v04-a1-intervention`); no A1 fit had run before the freeze. It is frozen by its own package, execution seal and Git tag (`fgcs-v04-a1-intervention`) before any A1 fit (analysis plan v0.4, §P6 and §P9; Section 6). Every section below is a decision; changing any of them after the freeze is a logged deviation.

## 1. Why this amendment

§P6 of the v0.4 plan allows an intervention only if the P5 diagnostics justify it. They do:

- **No excess conflict:** in the LSTM M1 shared encoder, task gradients were close to orthogonal. Median excess conflict K was −0.037 (fastStorage) and −0.021 (Rnd), and median |cos| was 0.171 and 0.134.
- **Unequal sizes:** gradient magnitudes were strongly unequal. The median max/min task-gradient norm ratio was 10.8 (fastStorage) and 89.2 (Rnd).
- **Unequal loss shares:** shares at the selected epoch ranged from 0.114 to 0.421, against an equal share of 0.25.

These are associations. A1 tests one causal reading of them:

> **H-A1.** Equalising the tasks' contributions to the shared encoder's training reduces the shared LSTM's typical-cell accuracy penalty, compared with the equal-weight loss.

**Pre-stated direction:** if H-A1 holds, the A1 arms are more accurate than equal-loss M1 in most resource × block cells, and their gradient-norm imbalance is smaller. A null or adverse result is reported as such.

## 2. What changes and what does not

Only the **training loss weighting** of the shared all-input LSTM (M1) changes. Everything else is v0.4 tier 2 exactly:

- **Data:** the same 20 Bitbrains VMs, the frozen H64-M1 context per entity and fold, the same purged folds, inner split, scalers, transforms and native-unit test origins.
- **Model:** the same LSTM: two layers, H64, dropout 0.1, four resource heads.
- **Training settings:** Adam with learning rate 10⁻³, batch size 256, at most 50 inner epochs, patience 7, global gradient clipping at 1.0 (applied after weighting), seeds 0–2.
- **Epoch selection:** unchanged. It uses the **equal-mean scaled validation MSE**, as for M1, so both arms choose epochs by the same criterion as the reference. The final refit uses the selected epoch with the same weighting rule as the inner fit.
- **References (not refitted):** the v0.4 equal-loss LSTM M1, S2 and S1 outcomes on the same units. A1 adds new fits only.

## 3. Arms

| Arm | Rule | Settings (fixed, no tuning) |
|---|---|---|
| **M1-GN** (primary) | GradNorm [Chen et al., ICML 2018]. Learnable task weights wᵢ are updated so that each task's gradient norm on the **last shared layer** (the second LSTM layer's weights and biases) moves towards the mean norm × (relative inverse training rate)^α. After each step the weights are renormalised to sum to 4. | α = 1.5 (the paper's default); weights initialised to 1 and optimised by Adam at learning rate 10⁻³; inverse training rate measured against the first-epoch task losses. |
| **M1-UW** (secondary) | Uncertainty weighting [Kendall, Gal and Cipolla, CVPR 2018, pp. 7482–7491, doi:10.1109/CVPR.2018.00781; verified 18 Nov 2026]: loss = Σᵢ ( exp(−sᵢ) · Lᵢ + sᵢ ), with learnable sᵢ = log σᵢ². | sᵢ initialised to 0 and trained jointly by the same Adam optimiser. |

**Why two arms:** GradNorm targets gradient magnitude directly, which is what D-4 measured. Uncertainty weighting targets loss scale with no extra hyperparameter. If both agree, the conclusion does not hinge on one balancing rule.

## 4. Endpoints

All endpoints are per arm, for each resource × block (8 cells), on the same 20 VMs.

- **Primary (typical cell):** the matched-cell median MAE ratio and win rate of M1-x against equal-loss M1. These are seed-averaged entity × fold × horizon cells, as in P4.
- **Prespecified aggregate:**
  - the MacroMAE gain G(M1-x : M1), with the P4 consistency classes (VM thresholds rescaled to 10);
  - VM-cluster bootstrap intervals (10,000 replicates, seed 20261007, reusing the v0.4 draw matrices).
- **Effect on the sharing penalty:** G(M1-x : S2) against the existing G(M1 : S2), and the matched-cell median ratio of M1-x against S2.
- **Manipulation checks** (same D-4 and D-7 code, at the selected epoch):
  - the max/min task-gradient norm ratio and K for M1-x;
  - the D-7 loss shares under the arm's own weighting, and as unweighted task MSE.

## 5. Decision rule (frozen before any run; descriptive, no p-values)

For each arm:

- **Supported** if both:
  - in at least **6 of 8** resource × block cells, the matched-cell median ratio M1-x / M1 is below 1 **and** the win rate is above 0.5; and
  - the median norm ratio for M1-x is below that of equal-loss M1 in **both** blocks (manipulation check).
- **Penalty removed** if supported **and** the matched-cell median ratio of M1-x against S2 is at most 1 in at least 6 of 8 cells.
- **Not supported** otherwise. This includes the case where the manipulation check fails: weighting that does not reduce the imbalance cannot test H-A1.
- **Adverse** if the median ratio M1-x / M1 is above 1 in at least 6 of 8 cells.

The DLinear scale-dominance lesson applies: MacroMAE gains are reported, but the decision uses the scale-free typical-cell statistics.

## 6. Scale and execution

- **Fits:** per arm, 20 VMs × 5 folds × 3 seeds = 300 inner + 300 final, plus 300 D-4 extractions. Both arms together: 1,200 fits and 600 extractions.
- **Time:** the median fit time in v0.4 was about 13 s. With six workers, the whole amendment is estimated at **one to two hours**, plus evaluation.
- **Architecture (revised before freezing, 18 Nov 2026):** the v0.4 journal's fit and evaluation gates are closed, and by rule C6 it accepts no new fits; its amendment mechanism only repairs quarantined identities. A1 therefore runs in a **separate derived package**, `fgcs_strengthening_v04a1/`, built from the v0.4 code at tag `fgcs-v04-min-final-r2`:
  - its own namespace (`fgcs-strengthening-v04a1`), runtime directory, configuration, execution seal and Git tag (`fgcs-v04-a1-intervention`);
  - its configuration records the v0.4 tag, commit and seal it derives from;
  - only the A1 arms are scheduled; the same orchestrator, journal, retry and quarantine rules, gates and blinding (C6), and launcher phases (canary, inner, final, diagnostics, evaluation, closure) apply;
  - the v0.4 equal-loss references are read **read-only** through the v0.4 package against its own seal; nothing in v0.4 changes.
- **Freezing:** audit the A1 package, tag it, set its own execution unlock, run the canary, and wait for the authors' approval before the full run.
- **Analysis:** `analyse_intervention.py` reads only the closed A1 journal and the closed v0.4 journal.
- **Failures:** the v0.3 C3 retry rules apply. A fit still failing after retries makes the unit missing for every A1 arm.

## 7. Implementation (after approval, before the freeze)

1. Add training modes `gradnorm` and `uncertainty` in `src/training.py` (the per-task loss vector already exists). The equal-loss path must stay byte-identical.
2. Create the derived package (renamed namespace, configuration and runtime), then add identities for the A1 arms (`arm="intervention"`, formulation M1, LSTM), the schedule, canary, evaluation and D-4 bindings, and a read-only reader for the v0.4 references.
3. Tests:
   - weights stay positive and sum to 4 (GradNorm);
   - the gradient reaches the weights;
   - repeated runs are deterministic;
   - equal-loss outcomes are unchanged (golden-hash test against existing v0.4 fits);
   - selection uses the unweighted validation MSE.
4. Add `analyse_intervention.py` and its exhibit script, with the hash check on the analysis output.
5. Add the new bibliography entry (Kendall et al. 2018) after verification.
6. Audit the package, tag it, unlock it, run the canary and wait for the authors' approval.

## 8. Reporting

- **Where:** a new main-text paragraph in RQ4 ("Loss-balancing intervention"), with the full tables in the supplement.
- **Prediction stated in advance:** the H-A1 prediction stated before the runs is reported verbatim.
- **Any outcome is reported**, supported, removed, not supported or adverse. Wording becomes causal only for what A1 tests: the effect of loss weighting on this model, cohort and design.
- **Limits stay in Threats:** one backbone, 20 VMs, three seeds, fixed α.

## 9. Decisions needed from the authors

1. **Arms:** GradNorm and uncertainty weighting (recommended), or GradNorm only.
2. **Decision thresholds:** "6 of 8 cells" and the manipulation check, as written.
3. **GradNorm settings:** α = 1.5 and the last shared layer = the second LSTM layer, fixed without tuning.
4. **Reference outcomes:** the existing v0.4 equal-loss M1/S2/S1 outcomes serve as references (recommended, same pipeline), or the equal-loss M1 is refitted alongside.

## 10. Implementation choices (confirmed by the authors before the freeze, 18 Nov 2026)

The approved text leaves these points open. The implementation fixes them as follows; all are recorded in `configs/protocol_v04a1.json` under `intervention`.

1. **GradNorm reference losses.** The "first-epoch task losses" are the unweighted task MSEs of the first training mini-batch of epoch 1 (the paper's t = 0), taken anew in each fit (inner, and final refit from initialisation).
2. **GradNorm weight floor.** After each weight step, weights are clamped at 0.001 and then rescaled to sum to 4, so they stay positive. The number of clamps is recorded per fit. The approved text does not mention a floor.
3. **Manipulation check.** The norm ratio for M1-x uses *effective* task-gradient norms: the unweighted D-4 norm of each task × that task's training weight at the selected epoch (GradNorm wᵢ; uncertainty exp(−sᵢ)). This is what the arms equalise. The unweighted ratio and K are reported alongside. The equal-loss M1 reference has equal weights, so its ratio is the published one (10.76 fastStorage, 89.18 Rnd, medians of entity means).
4. **Uncertainty optimiser.** The sᵢ are updated by their own Adam instance at the model's learning rate. Adam is per-parameter, so this equals one Adam over model and sᵢ. Gradient clipping (1.0) applies to the model parameters only.
5. **Loss scale.** Both arms optimise a sum over tasks (GradNorm Σ wᵢLᵢ with Σ wᵢ = 4; uncertainty Σ exp(−sᵢ)Lᵢ + sᵢ), so the initial loss is four times the equal-mean loss. Adam is nearly invariant to this, and clipping applies after weighting as approved.
6. **Pairing.** Each A1 fit starts from the same initial model and uses the same shuffle stream as the v0.4 M1 fit with the same seed. D-4 uses the same gradient batch draws as the v0.4 M1 final slot of the same unit.
7. **Missing units.** A unit (block × VM × fold × resource × seed) failed in any of M1-GN, M1-UW, M1, S2 or S1 is missing for all five, so every comparison stays paired. A cell whose median ratio or win rate is undefined does not count towards the 6-of-8 threshold.
8. **Cost (measured).** On the canary VM, a GradNorm inner fit took 19 s, an uncertainty fit 10 s and an equal-loss fit 10 s. The one-to-two-hour estimate in Section 6 stands.

**Checks done before the freeze:**
- The A1 code trains the equal-loss path identically to the tagged v0.4 engine: model hashes, epochs and selection match on synthetic data, and on a real v0.4 fit (fastStorage VM 697, fold 1, seed 0).
- The read-only v0.4 reader reproduces the published D-4 medians.

