# Manuscript revision plan (v0.4 evidence, three revision comments only)

**Status: plan only; the manuscript is not edited.** Baseline: `manuscript/jss/manuscript.tex` (1,597 lines) with its `tables/`, `figures/` and `supplementary/` files. Scope: the three comments in analysis plan v0.4 §P0, and the reporting rules in §P10 and §P11. Nothing else in the paper changes.

| # | Comment | What the paper gains |
|---|---|---|
| C1 | Add DLinear, PatchTST and iTransformer | A baseline-accuracy table, contrasts per backbone and a cross-backbone summary |
| C2 | Explain shared-representation degradation (task affinity, gradient conflict, correlation, transfer) | Diagnostics D-1 to D-7, reported as associations |
| C3 | Reframe around contextual input versus representation sharing | A 2×2 framing (S1/S2/M0/M1), a new abstract, introduction and conclusion, and a new title chosen after the results |

## 0. Evidence that must be preserved verbatim

**Tier 1 (unchanged, full cohort, six blocks).** All current S1/S2/M1 LSTM results, Figure 2, Tables 2–5, Supplementary Tables S1–S2 and the post-hoc controls. These values are not recomputed, rounded differently or reworded into stronger claims.

**Tier 2 (v0.4 extension).**
- **Scope:** 20 Bitbrains VMs (10 fastStorage, 10 Rnd); 4 backbones; the 2×2 design; three seeds; descriptive only.
- **Source:** `fgcs_strengthening_v04/runtime/analysis/analysis_v04.json`, sha256 `308841865ec87b04e10ecb64f20bc13ce2e671511a1574056028f7b5710dd17a`.
- **Provenance:** tag `fgcs-v04-min-final-r2`, execution seal `f52e07ff…cfac`, package `cb3bd387…e6a0`.

The figures used throughout this plan are taken from the analysis file:

| Contrast | Rows | Gain < 0 | Matched median ratio > 1 | Win rate < 0.5 | Broad Negative | Positive classes |
|---|---:|---:|---:|---:|---:|---:|
| S2:S1 context, independent | 24 | 11 | 13 | 13 | 2 | 8 |
| M1:M0 context, shared | 24 | 17 | 14 | 14 | 4 | 5 |
| M0:S1 sharing, own input | 24 | 15 | 20 | 20 | 8 | 5 |
| M1:S2 sharing, all input | 32 | 29 | 30 | 30 | 12 | 1 |

- **Cross-backbone summary:** 2 of 32 cells generalise across backbones. Both are negative: M0:S1 on Rnd CPU and on Rnd DISK_WRITE. The other 30 depend on the backbone.
- **Mandatory caveat, DLinear Rnd CPU** (audit `runtime/analysis/audits/dlinear_rnd_cpu_m0/summary.json`):
  - M0:S1 = −139.6 % and M1:M0 = +46.2 %. Both reproduce exactly under the frozen P4 rule.
  - The aggregate is scale-dominated: VM 233 contributes 98.6 % of the M0 − S1 excess.
  - The negative direction is broad: 8 of 10 VMs are worse; 0 of 5 horizons, 0 of 5 folds and 0 of 3 seeds are positive; frozen median ratio 1.051, win rate 0.34.
  - The fits are complete and seed-stable on VM 233. M0's DLinear form is fully weight-tied (§P11.6).
- **Corrected figure:** the largest seed spread on the other VMs (excluding 233 and 269) is **0.046** (VM 151, S1). The earlier "about 0.01" must not appear anywhere.
- **Mechanism figures (LSTM; associations only):**
  - D-4: median excess conflict K is between −0.04 and +0.03; median |cos| is 0.10–0.16; median max/min gradient-norm ratio is about 11 (fastStorage) and about 89 (Rnd).
  - D-7: final-epoch loss share ranges from 0.11 to 0.42 (Rnd THROUGHPUT 0.42; fastStorage THROUGHPUT 0.11).
  - D-3: in 29 of 32 cells the interval includes 0.
  - D-6: F is mostly ≤ 0 and Q is about 0.

## 1. Front matter

| Item | Action | Content |
|---|---|---|
| Title (l.16) | **Replace after the results are agreed** (§P10) | Candidate wording, to be chosen by the authors: "Contextual Input and Representation Sharing Are Separable Design Decisions in Multi-Metric Runtime Forecasting". Keep the current title if the authors judge the claim too strong. |
| Abstract (l.45–70) | **Replace** | About 230 words, in this order: (1) the two design decisions; (2) the 2×2 instrument (S1/S2/M0/M1); (3) tier 1: LSTM, six blocks, unchanged findings; (4) tier 2: four backbones on 20 Bitbrains VMs, where M1:S2 gain is negative in 29/32 backbone × resource × block cells and the median ratio is > 1 in 30/32, while context effects are small and backbone-dependent; (5) LSTM diagnostics show near-orthogonal task gradients with large size imbalance rather than excess conflict (associational); (6) the consolidation trade-off and persistence boundary. Remove the post-hoc control detail (it moves to Methods). |
| Keywords | **Modify** | Add "representation sharing" (replacing "shared representations") and "negative transfer diagnostics". Keep the others. |
| `highlights.tex` | **Replace** | Five bullets that mirror the new abstract: separability, the cross-backbone sharing penalty, backbone-dependent context, imbalance rather than conflict, and the consolidation trade-off. |

## 2. Introduction (§1, l.85–171)

- **Keep:** paragraphs 1–3 (motivation, precedents, the definitions of contextual input and representation sharing). Paragraph 3 already states the C3 distinction.
- **Replace paragraph 4 (l.124–138):** present the 2×2 as the study's instrument. Context is varied with sharing held fixed (S2:S1, M1:M0), and sharing with input fixed (M0:S1, M1:S2). Tier 1 provides S1/S2/M1 LSTM evidence across six blocks. Tier 2 completes the 2×2 and repeats it for DLinear, PatchTST-style and iTransformer-style backbones (C1).
- **Replace paragraph 5 (RQ preview)** to match the new RQ structure in §5 below.
- **Shorten paragraph 6 (post-hoc controls, l.143–148)** to one sentence with a forward reference; the detail stays in §4.
- **Replace paragraph 7 (findings, l.150–161)** with the findings stated in §0 above, kept separately for each tier.
- **Replace the contributions (l.162–171).** Four items:
  1. A 2×2 decomposition that separates contextual input from representation sharing, applied to four backbone families (C1, C3).
  2. Evidence that the value of context is selective and depends on the backbone, whereas the direction of the all-input sharing penalty recurs across backbones. Its magnitude is resource-, block- and tail-dependent (C1, C3).
  3. Training-side and outcome-side diagnostics (D-1 to D-7) that relate the sharing penalty to task-gradient size imbalance and loss-share imbalance rather than excess gradient conflict or input dependence, stated as associations (C2).
  4. An accuracy-consolidation account with parameter counts across backbones, bounded by persistence skill and tail concentration (kept from the current item 4).

## 3. Related work (§2)

- **§2.1 Runtime forecasting:** no change.
- **§2.2 Information scope and sharing (l.208–238): modify.**
  - Extend the PatchTST/iTransformer paragraph to say both are evaluated here as declared adaptations.
  - Add DLinear (decomposition plus linear maps). This needs a new bib entry: Zeng et al., AAAI 2023, *Are Transformers Effective for Time Series Forecasting?*. Verify it before adding.
  - Note that PatchTST's channel-independent weight reuse is exactly an M0-type arrangement. This links the related work to the M0 cell.
- **§2.3 Multi-task learning (l.239–275): modify.** Add task-affinity and gradient-magnitude literature next to the existing conflict citations (Fifty 2021 is already cited; Standley 2020 too). Add GradNorm (Chen et al., ICML 2018; new bib entry, to be verified) for magnitude imbalance. Keep the sentence that these methods "are established responses…", and change "not evidence of a measured mechanism in our resource forecasters" to point forward to §6.5, stated as associations.
- **§2.4 Evaluation gap (l.276–303): replace l.288–295.** "not … a complete 2×2 design" is no longer true for tier 2. New text: tier 1 has three LSTM cells; tier 2 completes the 2×2 on a reduced cohort. List the design-defined exceptions (iTransformer S1/M0 undefined; DLinear M0 fully weight-tied; DLinear M1 bottleneck).
- **`tables/related_work_comparison.tex`: modify.** Add a "This study" row, or update the existing one, to show the 2×2, four backbone families and mechanism diagnostics.

## 4. Framework (§3) and Methods (§4)

| Location | Action | Content |
|---|---|---|
| Fig. 1 `figures/framework_s1_s2_m1.{tex,pdf}` (l.313–326) | **Replace** with `framework_2x2` | The central conceptual figure (§P10). Rows: input scope (own / all). Columns: parameters (independent / shared). Cells: S1, S2, M0, M1. Arrows for the four contrasts and the interaction. Remove "not a complete 2×2" from the caption (l.324). |
| §3.3–3.5 (S1, S2, M1) | **Keep**; add **§3.x "M0 Shared Own-Input Forecasting"** | M0 is one shared model applied to each resource's own history, with four target outputs. |
| §3.6 Decomposition (l.487–521) | **Modify** | Add C_context\|shared = D_Q(M0→M1) and C_sharing\|own = D_Q(S1→M0), and the interaction I = ln A_M1 − ln A_S2 − ln A_M0 + ln A_S1. Keep the additivity caveat; add that two paths now connect S1 to M1. |
| §4.1 RQs (l.529–557) | **Replace** | Following §P10: **RQ1** How do the backbones compare in baseline accuracy? (C1) **RQ2** When does contextual input help (S2:S1, M1:M0)? **RQ3** When does representation sharing hurt (M0:S1, M1:S2, interaction)? **RQ4** Which diagnostics are associated with the sharing penalty (D-1 to D-7)? (C2) **RQ5** Heterogeneity and the accuracy-consolidation trade-off. State that tier-1 answers to the old RQ1–RQ4 are kept, re-indexed under RQ2/RQ3/RQ5. |
| New §4.x "Tier-2 extension design" | **Add** | Cohort (20 VMs by frozen rank). Backbone and cell specifications (§P3, compact), with fixed untuned hyperparameters and imposed LSTM H64-M1 contexts. Unchanged folds, horizons, scalers and native MAE. Freezing by Git tag, package and seal (deviation D1; OSF `kuwra` superseded as v0.3 historical evidence). Execution facts: 13,500 inner fits (including the 90 canary fits), 13,500 final fits, 600 diagnostic extractions and 13,500 evaluations all complete, with 0 retries and 0 missing units. |
| New §4.x "Tier-2 analysis and diagnostics" | **Add** | P4 classes with VM thresholds rescaled to 10, the bootstrap (10,000 replicates, seed 20261007, one draw matrix per block), and the cross-backbone rule. A compact table of the D-1 to D-7 definitions (§P5). The statement "descriptive; no p-values; intervals do not enter classes". |
| §4.13 Post-hoc controls (l.926–983) | **Modify** | Replace "address reviewer challenges" (l.929) with neutral wording, e.g. "were added after the original experiment was frozen". |
| §4.9 Evaluation | **Modify** (one paragraph) | State that MacroMAE averages native MAE across entities without rescaling, so high-scale entities can dominate an aggregate. Point to the matched-cell median ratio and win rate as scale-free companions. This sets up the DLinear caveat. |

## 5. Results (§5), reorganised by question (§P10)

Order: RQ1 → RQ2 → RQ3 → RQ4 → RQ5. Tier-1 and tier-2 results stay in separate, labelled paragraphs within each subsection (§P10 "Tiers").

| Subsection | Action | Exhibits and content |
|---|---|---|
| Results intro (l.985–996) | **Modify** | Add the tier distinction and point to the new exhibits. |
| **RQ1 Baseline accuracy (new)** | **Add** | **New Table `tables/baseline_accuracy.tex`:** block × resource rows; columns are each backbone's MacroMAE ratio to the best defined backbone and persistence skill. Main text shows S2 and M1; S1 and M0 go to the supplement. Text: the LSTM's ratio to the best backbone is 1.00–1.04 except fastStorage CPU (1.9–2.2× DLinear). CPU and throughput skill is negative for all backbones. Descriptive, no ranking claim. **C1** |
| **RQ2 Context** (current §5.1, l.1015–1068) | **Modify** | Keep the tier-1 text unchanged. Add a tier-2 paragraph: S2:S1 and M1:M0 per backbone; 8/24 S2:S1 cells positive-class, 2 Broad Negative; no context cell generalises across backbones; Rnd DISK_WRITE S2:S1 is negative for all three full-2×2 backbones. **C1, C3** |
| **RQ3 Sharing** (current §5.2–5.3, l.1069–1172) | **Modify** | Keep the tier-1 text, Table 4 and the VM266/VM272 attribution unchanged. Add a tier-2 block: M1:S2 gain < 0 in 29/32, median ratio > 1 in 30/32, win rate < 0.5 in 30/32, 12 Broad Negative, 1 positive (iTransformer fastStorage CPU). M0:S1: 8 Broad Negative, concentrated on Rnd. The 2 generalising cells. Interaction: positive for the LSTM in 8/8 (6 intervals exclude 0), negative for DLinear Rnd, about 0 for PatchTST. **DLinear Rnd CPU caveat paragraph** using the figures in §0. **C1, C3** |
| **New Figure `figures/v04_contrast_matrix.pdf`** | **Add** | Signed matrix in the style of `results_signed_matrix.py`. Panels are the four contrasts; rows are backbone × block; columns are resources. Cells show the gain with a class marker; undefined cells are hatched. Use the same asinh colour rule and caption conventions as Fig. 2. Annotate the DLinear Rnd CPU cells "scale-dominated, see text". |
| **New Table `tables/cross_backbone.tex`** | **Add** (or fold into the figure caption) | 32 cells: class per backbone and verdict; generalising: 2/32, both negative. |
| **RQ4 Diagnostics (new)** | **Add** | **New Figure `figures/v04_mechanism.pdf`**, three panels: (a) D-4 K and |cos| against the norm ratio per block; (b) D-7 loss share per resource over epochs; (c) the D-6 F/Q heatmap per block. **New compact Table `tables/diagnostics_summary.tex`** for D-1 (median and maximum |r|), D-3 (ρ with intervals; 3/32 exclude 0) and D-4 medians. Text: dependence (D-1/D-2) is not consistently associated with the context or sharing effects (D-3). Task gradients are near-orthogonal with no excess conflict (K ≈ 0). Gradient size (D-4) and loss share (D-7) are highly unequal, most on Rnd, where the LSTM sharing penalty is largest. Single-source transfer (D-6 F) is mostly ≤ 0, and leaving one source out (Q) is about 0. Every sentence is phrased as "is associated with" or "coincides with". **C2** |
| Persistence boundary (l.1216–1252) | **Modify** | Keep tier 1. Add one tier-2 sentence from the baseline table (negative CPU/THROUGHPUT skill across backbones; DLinear M0 Rnd CPU −0.85, dominated by VM 233). |
| Accuracy-efficiency (l.1253–1277) and `tables/efficiency_summary.tex` | **Modify** | Add M0 and the modern backbones' complement parameter counts (from P4 `parameter_counts`, external context 4/9/18), e.g. LSTM M0 51,732; PatchTST S2 272–276k against M1 69–70k; iTransformer S2 274–278k against M1 72–73k; DLinear 50–2,900. Keep the Materna worker-hours column as tier-1 only. Note that the DLinear M1 bottleneck has lower rank than S2 (§P11.6). |

## 6. Cross-dataset synthesis (§6) and Discussion (§7)

| Section | Action | Content |
|---|---|---|
| §6 Cross-dataset synthesis, `tables/cross_study_synthesis.tex` | **Modify** | Add a "Bitbrains 20-VM, four backbones (tier 2)" column or row, labelled as not a replication of tier 1 and with no Materna or TimeTrack. |
| §7.1 When context helps (l.1336–1353) | **Modify** | Add that the direction of context effects depends on the backbone (tier 2), consistent with the existing Ridge AR/ARX reversal. |
| §7.2 Shared representation and adverse transfer (l.1354–1377) | **Replace l.1370–1377** | Remove "Gradient conflict, representation interference and capacity competition were not measured" (l.1371–1372). It is no longer true for gradient conflict (LSTM only). New text: conflict was measured (LSTM, final epoch) and shows no excess; imbalance in gradient size and loss share is large and largest where the penalty is largest; dependence does not track effects. These are associations from 20 VMs with no intervention (§P11.11). Representation interference and capacity competition remain unmeasured. PCGrad, GradNorm and grouping remain untested remedies (§P6). Also state that the sharing penalty's direction recurs across backbones but its magnitude does not, and that DLinear M0's full weight tying makes its M0:S1 the most extreme form of sharing. **C2** |
| §7.4 Accuracy-consolidation trade-off | **Modify** | Add cross-backbone parameter reductions alongside the cross-backbone sharing penalties. |
| §7.5 Applicability | **Modify** | Remove the untested-Transformers claim; keep foundation and global models as untested. |
| New closing paragraph of §7 (C3) | **Add** | Separability: context and sharing have different, resource-specific consequences and should be decided and validated separately. Adding context does not imply sharing should follow. |

## 7. Threats to validity (§8)

| Subsection | Action | Content |
|---|---|---|
| Construct (l.1424–1441) | **Replace l.1427** | Instead of "not a complete 2×2 design": tier 1 has three cells; tier 2 completes the 2×2, with design-defined exceptions (iTransformer S1/M0 undefined; DLinear M0 weight-tied with no heads; DLinear M1 rank-limited) and PatchTST/iTransformer as declared adaptations. |
| Internal (l.1442–1465) | **Modify** | Remove "reviewer-motivated" (l.1449). Add: tier 2 uses three seeds; on the DLinear Rnd CPU check, seed spread is at most 0.046 outside the two high-scale VMs. Hyperparameters are fixed and untuned. LSTM-selected contexts are imposed on every backbone. D-4 is LSTM-only. Replace "missing gradient/clipping histories limit mechanism attribution" with the D-4 scope limits. |
| External (l.1466–1482) | **Modify l.1477–1479** | "Transformers … were not tested" becomes: PatchTST-style and iTransformer-style adaptations and DLinear were tested on 20 Bitbrains VMs only, with no Materna or TimeTrack. Mixture-of-experts, selective grouping, adaptive sharing, gradient surgery and foundation forecasters remain untested. |
| Conclusion validity (l.1483–1502) | **Modify** | Add: MacroMAE is scale-weighted. In the DLinear Rnd CPU example, one VM produces 98.6 % of the aggregate excess, so tier-2 claims cite matched-cell medians and win rates alongside MacroMAE. Ten-VM intervals are wide; tier 2 makes no confirmatory claim; there is no external preregistration of v0.4 (Git-tag freezing, D1). |

## 8. Conclusion, declarations and supplement

| Item | Action | Content |
|---|---|---|
| Conclusion (l.1503–1538) | **Replace** | Three paragraphs: separability (C3); context selective and backbone-dependent, against the sharing penalty's direction recurring across backbones, with tail-dependent magnitude and the DLinear caveat (C1); diagnostics point to imbalance rather than conflict, stated as associations, with interventions as future work (C2). Keep the tier-1 statements. |
| Data availability (l.1539–1570) | **Modify** | Add the v0.4 tag, package digest, seal, the analysis file hash `3088418…7a`, the audit summary path, Zenodo `10.5281/zenodo.24189108` for the sealed inputs, and OSF `kuwra` as superseded v0.3 historical evidence. |
| AI declaration (l.1582+) | **Author check** | If AI assistance was used for the v0.4 code, analysis or audit, extend the existing statement to cover it. Wording is the authors' choice. |
| `supplementary/final_evidence_supplement.tex` | **Add sections** | S3 v0.4 protocol summary and deviation D1. S4 all 104 contrast rows (gain, class, counts, interval, median ratio, win rate). S5 interaction (24 rows). S6 full baseline accuracy (32 rows) and parameter counts (42 rows). S7 D-1 to D-7 full tables. S8 DLinear Rnd CPU audit: per-VM table, seed values, aggregation and skill checks, 0.046 seed spread. Keep S1–S2 unchanged. |
| `supplementary/decision_criteria.tex` | **Modify** | Add the classes with VM thresholds rescaled to 10 and the cross-backbone rule. |

## 9. Removals and wording checks

- **Remove "reviewer" wording:** l.929 "address reviewer challenges" and l.1449 "reviewer-motivated" (§P10).
- **Remove statements the tier-2 evidence now contradicts:** l.292 and l.324 ("not … a complete 2×2"), l.1371–1372 ("Gradient conflict … not measured"), l.1427, and l.1477–1479 ("Transformers … not tested").
- **Move repeated protocol caveats to the supplement** where they repeat across abstract, introduction and results (§P10). Tier-1 numbers are not removed.
- **Words to avoid in new text:** "causes", "explains", "mechanism is" and "generalises" (except as the defined cross-backbone verdict). Use "is associated with", "coincides with" and "descriptive".

## 10. New and changed files (when editing begins)

| Status | Files |
|---|---|
| New | `figures/framework_2x2.{tex,pdf}`, `figures/v04_contrast_matrix.{py,pdf}`, `figures/v04_mechanism.{py,pdf}`, `tables/baseline_accuracy.tex`, `tables/cross_backbone.tex`, `tables/diagnostics_summary.tex` |
| Modified | `manuscript.tex`, `highlights.tex`, `references.bib` (Zeng 2023, Chen 2018, verified), `tables/efficiency_summary.tex`, `tables/related_work_comparison.tex`, `tables/cross_study_synthesis.tex`, both supplement files |
| Retired | `figures/framework_s1_s2_m1.*`, once Fig. 1 is replaced (keep it in git history) |
| Unchanged | `figures/results_signed_matrix.*`, `tables/posthoc_controls.tex`, `tables/primary_gains.tex`, `tables/dataset_summary.tex` |

Every new figure and table script must read only `analysis_v04.json` (and, for S8, the audit `summary.json`), and must record their sha256 in the generated output.
