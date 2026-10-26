# STAGE 19G1 — Final evidence surfacing report

**Status: STAGE_19G1_PASS.** Existing-artifact evidence only. No training,
model inference, manuscript edit, frozen/post-hoc result edit or new experiment.
All new attribution summaries are **POST-HOC DIAGNOSTICS**, not replacements
for frozen MacroMAE gains or prospective consistency classifications.

Repository: `/Users/fgtek002/TimeTrack`; branch `paper/jss-review-revision`;
HEAD `f6936cd111d911e40ec2725a18fdfc53768d9ccf`.

## 1. Estimands and traceability

Materna repeats the Stage 18A1 estimand: for each VM, average the existing
seed-mean MAEs equally across five outer folds and five forecast leads.
TimeTrack uses the analogous original M1:S2 matched errors, with three seed
MAEs averaged first and eight leads weighted equally. Machine/fold summaries
average those lead errors; machine summaries average five folds and fold
summaries seven machines. No pooling of predictions, native errors across
resources, or blocks is introduced.

For any stated aggregation unit, excess is M1 MAE minus S2 MAE. Net excess is
the sum of these unit-level differences; positive excess is the sum of their
positive parts. Contributor percentages divide the stated unit's excess by
that same aggregation level's net or positive total. Taking positive parts
after aggregation is not interchangeable with taking them at a finer level.
The tables explicitly identify the level. These diagnostics neither reweight
the frozen endpoint nor remove an adverse machine/VM.

The 24-cell table projects Stage 18C1's **seed-mean entity×fold×lead** robust
table verbatim, not its separate seed-matched panel. Win fractions are merely
expressed as percentages. The 48-row seed table copies the existing gains,
range and population SD (`ddof=0`) without recalculating or rounding them.
Stable/FLIP uses the existing strict-positive-and-negative-seed definition,
not an effect-size cutoff. All source decimal strings survive CSV round-trip
checks. Overlapping folds/leads, three fixed seeds and dependent Materna
blocks are not IID replicates.

Inputs: Stage 18A1 diagnostic report; Stage 18C1 synthesis, matched errors,
robust and seed tables; original frozen metrics, contexts, registries,
completion/scaler/support records, saved predictions and checkpoints; completed
H129 results. `input_sha256_inventory.json` records every directly read source.
`surface_evidence.py` and `verify_materna_saved.py` implement only descriptive
arithmetic and static artifact checks. No model is instantiated or called.

## 2. Materna T1/T3 disk attribution — re-verified

| Block | M1 worse VMs | M1 better VMs | Ties | Median VM M1/S2 | Largest VM | Largest / positive excess | Top-3 VMs | Top-3 / positive excess |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Materna-T1 | 28 | 7 | 0 | 1.034334 | 266 | 82.10% | 266, 442, 92 | 91.72% |
| Materna-T3 | 32 | 3 | 0 | 1.045846 | 272 | 86.97% | 272, 397, 299 | 92.93% |

All **70 per-VM S2/M1 MAEs, ratios and excesses** reproduce Stage 18A1
Appendix E to every displayed six-decimal digit. The original 28/7 and 32/3
counts, VM266/VM272 concentration and 82.10/91.72% and 86.97/92.93% contributor
shares agree. See Appendix A below for every VM, including leading-zero IDs.
No different estimand or leave-one-VM-out endpoint is substituted.

**Fitting diagnosis remains NO_TRAINING_FAILURE_VISIBLE for both traces.**
Freshly inspected all 2,100 relevant original S2-disk/M1 final checkpoints and
prediction files across T1/T3: registry/completion hashes match, weights and
saved disk targets/predictions are finite, parameter counts are correct,
paired target/support signatures agree, saved log1p inverse/expm1/projection
maps reproduce exactly, and saved prediction MAEs reproduce stored metrics.
One final test evaluation is recorded per valid fit; none was newly executed.
All selected final scaler vectors match the frozen training-partition manifest
exactly (259 distinct selected partitions in T1 and 252 in T3). Existing
technical validations remain PASS with zero recorded violations. Their scope
is technical conformance, not proof of ideal predictive quality.

Stage 18A1's raw-archive reconstruction of all **3,150 inner/final scaler
partitions** is reused with unchanged source/artifact hashes; that entire raw
reconstruction was not rerun in this stage. Its conclusion about positive,
non-singular scales and the large dominant-VM disk IQRs remains applicable.
The fresh final-scaler checks above are against that frozen partition manifest,
not falsely described as a new 3,150-partition raw reconstruction.

VM266's M1 selected epochs remain 26–50; VM272's 40–50. M1 logs contain finite
joint losses. VM266 is context-matched at L18 in all five folds. VM272 is
matched in folds 1 and 4 and mismatched in 2,3,5; its largest fold excess is
the matched fold 1. The preserved T1 failed attempt is S1 CPU/VM74/fold1/seed0
(`KeyError: support_hash`), not an M1 disk fitting failure; it has not been
erased or reused. T3 has no saved failure record. S1/S2 detailed epoch-loss
histories and gradient/clipping diagnostics remain incomplete. Finite artifacts
do not establish optimisation optimality or identify a transfer mechanism.

Interpretation is unchanged: adverse direction is widespread, but the large
absolute-error magnitude is concentrated. The per-VM medians above differ
legitimately from the Stage 18C1 **entity×fold×lead** disk medians
1.024565/1.034743; they aggregate at different levels.

## 3. TimeTrack memory attribution — original M1:S2

**Descriptive classification: BROAD_DEGRADATION, with nonuniform magnitude.**
This is not an added frozen consistency rule or a numerical concentration
threshold. All seven machine averages worsen, as do 31/35 machine/fold pairs
and 239/280 seed-mean machine/fold/lead cells. One machine contributes a large
share of magnitude, but the direction is not an isolated-outlier failure.

| Aggregation level | M1 worse | M1 better | Ties | Median M1/S2 ratio |
| --- | --- | --- | --- | --- |
| Machine (7) | 7 | 0 | 0 | 1.206158670 |
| Fold (5) | 4 | 1 | 0 | 1.184750108 |
| Machine/fold (35) | 31 | 4 | 0 | 1.195276413 |
| Machine/fold/lead (280) | 239 | 41 | 0 | 1.192135308 |

Per-machine and per-fold native-memory MAEs below retain original units; no unit conversion is applied.

| Scope / identity | S2 MAE | M1 MAE | M1/S2 | Excess MAE |
| --- | --- | --- | --- | --- |
| machine / machine01 | 473218419.440813 | 679759544.846285 | 1.436460 | 206541125.405471 |
| machine / machine02 | 178997354.965127 | 228727432.840176 | 1.277826 | 49730077.875049 |
| machine / machine03 | 791837611.455316 | 863607108.536751 | 1.090637 | 71769497.081436 |
| machine / machine04 | 404119396.066292 | 437606496.050545 | 1.082864 | 33487099.984252 |
| machine / machine05 | 107206946.569986 | 129308588.105289 | 1.206159 | 22101641.535303 |
| machine / machine06 | 10554101.493224 | 19083065.243527 | 1.808118 | 8528963.750303 |
| machine / machine07 | 241792311.338766 | 257552942.685851 | 1.065183 | 15760631.347085 |
| fold / 1 | 470523612.022768 | 460534488.559644 | 0.978770 | -9989123.463124 |
| fold / 2 | 245644000.598723 | 330605295.278615 | 1.345872 | 84961294.679891 |
| fold / 3 | 168083723.433490 | 276599186.611135 | 1.645604 | 108515463.177646 |
| fold / 4 | 331423995.106649 | 392654613.994389 | 1.184750 | 61230618.887740 |
| fold / 5 | 361271912.645174 | 407924400.062234 | 1.129134 | 46652487.417060 |

[timetrack_memory_attribution.csv](/Users/fgtek002/TimeTrack/review_revision/stage19g1_evidence/timetrack_memory_attribution.csv) contains all **47 rows**: 35 machine/fold pairs, 7 machine averages and 5 fold averages, including context-match status for each pair.

| Level | Positive excess sum | Net excess sum | Largest unit | Largest / positive | Largest / net | Top-3 units | Top-3 / positive | Top-3 / net |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Machine | 407919036.978898 | 407919036.978898 | machine01 | 50.6329% | 50.6329% | machine01; machine03; machine02 | 80.4181% | 80.4181% |
| Machine/fold | 2203793963.476366 | 2039595184.894492 | machine01/2 | 21.8035% | 23.5588% | machine01/2; machine01/3; machine03/5 | 51.0590% | 55.1696% |

At machine/fold level, the largest excess is machine01/fold2:
S2=446438210.31378144, M1=926941614.6238251, ratio=2.0763043870557567,
excess=480503404.31004363. Next are machine01/fold3 and machine03/fold5.
The largest three supply 51.0590% of positive and 55.1696% of net excess.
Machine01 alone supplies 50.6329% of positive/net **per-machine** excess;
machine01, machine03 and machine02 supply 80.4181% together. These statements
describe different levels and must not be conflated.

The top three machine/fold contexts (S2/M1) are 128/64, 32/64 and 64/32:
all mismatched. There are 17 mismatches across 35 pairs. However, the next
two largest pairs, machine01/fold4 and machine03/fold3, both match at 128/128
and still have substantial positive excess. Mismatch is not demonstrated as a
cause or a necessary condition. Common-context S2 is a separate already
completed sensitivity control, not a reason to replace these frozen errors.

**Fresh static checks:** all **210** original S2-memory/M1 final checkpoints
and prediction files checked; finite weights/targets/native/scaled predictions;
correct 51,720/53,280 parameter counts; file hashes agree with registries and
completions; exact matched target/support IDs; correct target timestamps and
float32 canonical native targets; saved prediction MAEs agree with all
**1,680** original memory metric rows. Memory is identity-transformed, not
log-transformed: float64 affine inverse maps reproduce saved native predictions
exactly, with no log-resource projection applied to memory. All **52 distinct
selected final memory scaler partitions** were independently reconstructed by
quantiles of the original legal outer-training history/target row union and
match stored centres/IQRs exactly. Target-time purging and test-origin hashes
pass. The canonical panel SHA matches the frozen anchor. No model forward
pass, new checkpoint, selection or test evaluation occurred.

Existing full TimeTrack validation remains PASS with zero structural
violations/failures. These checks demonstrate no current implementation defect;
they do not measure gradient conflict, make optimisation ideal, or uniquely
attribute the loss to representation sharing. The diagnosis is broader than
the concentrated Ridge-throughput outlier and must not inherit that outlier's
classification.

## 4. Exact Table A TimeTrack memory check

| Quantity | Exact authoritative value |
| --- | --- |
| Original S2 MacroMAE | 315389448.76136076 |
| Original H64 M1 MacroMAE | 373663596.9012034 |
| H129 M1 MacroMAE | 373688413.1997836 |
| Original H64 M1:S2 gain % | -18.476885757816117 |
| H129 M1:S2 gain % | -18.484754219705916 |
| Existing H129:H64 gain % | -0.006641347668338885 |

**Both gains legitimately round to −18.48% at two decimals. They are not
identical results.** H129 has slightly higher MAE. The original H64 value
cross-checks to the frozen comparison row; the H129 value is copied from
`m1_capacity_matched/posthoc_results.csv`. The manuscript post-hoc Table A's
original/common/H129 memory values are correctly distinguished. No figure,
table source or result was changed.

## 5. Reviewer-facing robust and seed tables

- [m1_s2_robustness_24.csv](/Users/fgtek002/TimeTrack/review_revision/stage19g1_evidence/m1_s2_robustness_24.csv): **24 unique block/resource rows**, original M1:S2 gain, median candidate/reference MAE ratio, win percent and ties. All ratios exceed 1, win percentages are below 50, ties=0.

- [seed_sensitivity_48.csv](/Users/fgtek002/TimeTrack/review_revision/stage19g1_evidence/seed_sensitivity_48.csv): **48 unique rows**, 24 S2:S1 and 24 M1:S2. Seed0/1/2 gains, range in percentage points, population SD in percentage points and stable/FLIP. S2 has 15 stable/9 FLIP summaries; M1 has 20 stable/4 FLIP summaries. No interval, significance test, new seed or effect-size cutoff added.


Exact CSV values, not the report's display rounding, should populate later
manuscript/supplement tables. Gain is positive when the candidate has lower
MacroMAE. Ratios greater than one favour the reference. Win percentages count
strictly lower candidate MAE; exact ties remain separate. The seed table
preserves SD `ddof=0` and must not be relabelled standard error or confidence.
The three-seed summary does not independently validate a temporal regime.

## 6. RQ4 wording audit — recommendations only

The stored seven classification changes and five raw sign reversals across
12 resource/comparison pairs were verified against the frozen temporal table.
The frozen rule/outcome remains unchanged. Several relevant small point signs
vary across seeds (e.g. S2 throughput in T1/T2/T3, T1 S2 memory, and T1 M1 CPU).
This supports bounded wording, not declaring the prespecified criterion invalid.
Not all seven class changes are near-zero sign changes: M1:S1 throughput
changes class while its points remain negative. No seed-specific RQ4 rerun was
performed; the supplied seed table covers S2:S1 and M1:S2, not M1:S1.

The current surrounding paragraph already calls the outcome frozen and rejects
causal mechanisms/post-hoc regimes. The isolated word “confirmed” can still be
read as stronger seed-stable/inferential confirmation than demonstrated. This
is the essential minimal wording change, not a numerical correction:


### 1. Manuscript lines 1162–1162

Required interpretation clarification; preserve frozen decision/counts.

Current exact source:

```latex
Temporal heterogeneity confirmed.
```

Recommended:

```latex
The prespecified RQ4 criterion for temporal heterogeneity was met.
```


### 2. Manuscript lines 1133–1134

Optional precision; the existing sentence is not itself a false numerical claim.

Current exact source:

```latex
Figure~\ref{fig:primary-gains} reveals heterogeneity at each prespecified
level.
```

Recommended:

```latex
Figure~\ref{fig:primary-gains} describes variation in point estimates across resources, environments and dependent temporal blocks.
```


### 3. Manuscript lines 1142–1145

Optional point-estimate qualifier; T1 M1:S2 CPU is seed-variable. Preserve the recorded classes.

Current exact source:

```latex
Temporal heterogeneity within the dependent
Materna blocks is distinct: M1-versus-S2 CPU changed from positive in T1 to
negative in T2--T3, moving from neutral or mixed to broadly negative and back
to neutral or mixed.
```

Recommended:

```latex
Across the dependent Materna blocks, frozen M1-versus-S2 CPU point estimates changed from positive in T1 to negative in T2--T3, while the frozen class changed from neutral or mixed to broadly negative and back to neutral or mixed.
```


If one further short qualifier is useful, follow the retained rule/counts with:
“This rule-based result concerns the frozen classifications and trace decisions;
it does not establish seed-stable temporal regimes.” Keep seven/12, five sign
changes, trace decisions and their frozen definitions intact. The two optional
edits above qualify point-estimate language rather than alleging false counts.
No manuscript change has been made.

## 7. Verification and bounded disposition

- All requested outputs exist and their fields round-trip exactly. Robust and
  seed tables are projections, not recomputed alternative estimands.
- Materna per-VM attribution reproduces Stage 18A1. Fresh saved-artifact checks
  cover 2,100 S2-disk/M1 final fits; TimeTrack checks cover 210 S2-memory/M1 fits.
  **Training=0; model inference=0.** Loading weights-only tensors and checking
  saved prediction arithmetic is not model execution.
- Full protected-tree audit: **395,786 files unchanged**, including manuscript,
  frozen outputs, completed post-hoc controls and predecessors, plus all
  **25 Stage 18C1 output hashes**. Earlier authorised manuscript revisions are
  matched to their existing hashes, not overwritten. Branch/HEAD/scientific
  refs unchanged; no staged changes; `git diff --check` passes. Directly read
  inputs are additionally rehashed at final handoff.
- The spreadsheet workflow informed flat records, explicit units/denominators,
  exact decimal preservation and CSV round-trip checks. The writing guidance
  informed a status-led, bounded interpretation. No extra workbook, submission
  package or manuscript revision was created.

**Implementation defect demonstrated: NO. Further experiment required: NO.**
No evidence supports outcome-driven refitting/reselection of the adverse cells.
Residual limitations are the original fixed cohort/design, only three seeds,
dependent temporal blocks, finite artifacts that cannot prove optimiser
optimality, and absence of complete gradient/clipping diagnostics. Context and
capacity controls remain separate, incomplete causal controls. This audit
does not resolve the metadata/declaration/package blocks found in Stage 19F2A.

Manuscript modifications=0; frozen/post-hoc/scientific modifications=0;
commit=no; push=no.

## Appendix A. All Materna T1/T3 disk per-VM errors

Existing Stage 18A1 estimand, reproduced at its six-decimal display precision.
Native MAE/excess units KB/s; ratios dimensionless; VM identifiers are text.

| Block | VM | S2 MAE | M1 MAE | M1/S2 | Excess MAE |
| --- | --- | --- | --- | --- | --- |
| Materna-T1 | 04 | 1.135757 | 1.132254 | 0.996915 | -0.003503 |
| Materna-T1 | 08 | 5.742846 | 6.528369 | 1.136783 | 0.785523 |
| Materna-T1 | 103 | 1220.593160 | 1203.204181 | 0.985754 | -17.388979 |
| Materna-T1 | 105 | 339.687602 | 351.878829 | 1.035890 | 12.191227 |
| Materna-T1 | 128 | 23.689825 | 23.792878 | 1.004350 | 0.103053 |
| Materna-T1 | 133 | 1364.473522 | 1293.278778 | 0.947823 | -71.194744 |
| Materna-T1 | 134 | 650.568942 | 691.483073 | 1.062890 | 40.914131 |
| Materna-T1 | 227 | 10.455147 | 11.424334 | 1.092700 | 0.969187 |
| Materna-T1 | 246 | 717.018004 | 788.845437 | 1.100175 | 71.827433 |
| Materna-T1 | 26 | 44.042334 | 44.012903 | 0.999332 | -0.029431 |
| Materna-T1 | 266 | 176.658776 | 2253.499329 | 12.756226 | 2076.840553 |
| Materna-T1 | 272 | 5.051907 | 5.225361 | 1.034334 | 0.173453 |
| Materna-T1 | 281 | 2758.336578 | 2757.697267 | 0.999768 | -0.639311 |
| Materna-T1 | 299 | 18.028664 | 61.130522 | 3.390741 | 43.101858 |
| Materna-T1 | 302 | 5.332419 | 5.317254 | 0.997156 | -0.015166 |
| Materna-T1 | 303 | 5.469010 | 5.478084 | 1.001659 | 0.009074 |
| Materna-T1 | 305 | 28.349731 | 32.068161 | 1.131163 | 3.718430 |
| Materna-T1 | 306 | 2.436375 | 2.442161 | 1.002375 | 0.005787 |
| Materna-T1 | 343 | 18.245999 | 18.466281 | 1.012073 | 0.220282 |
| Materna-T1 | 345 | 3.660863 | 3.703258 | 1.011581 | 0.042395 |
| Materna-T1 | 380 | 5.973878 | 6.137269 | 1.027351 | 0.163391 |
| Materna-T1 | 393 | 334.947012 | 352.515775 | 1.052452 | 17.568763 |
| Materna-T1 | 397 | 0.912289 | 0.984158 | 1.078778 | 0.071868 |
| Materna-T1 | 416 | 1.562698 | 1.624131 | 1.039313 | 0.061434 |
| Materna-T1 | 440 | 19.504348 | 26.611836 | 1.364405 | 7.107488 |
| Materna-T1 | 442 | 594.815182 | 762.607080 | 1.282091 | 167.791898 |
| Materna-T1 | 478 | 124.342370 | 131.229892 | 1.055392 | 6.887522 |
| Materna-T1 | 493 | 3.212915 | 3.315972 | 1.032076 | 0.103058 |
| Materna-T1 | 498 | 0.908239 | 0.935385 | 1.029888 | 0.027146 |
| Materna-T1 | 508 | 16.925326 | 16.923918 | 0.999917 | -0.001408 |
| Materna-T1 | 74 | 45.156342 | 45.983106 | 1.018309 | 0.826764 |
| Materna-T1 | 75 | 42.093361 | 42.098170 | 1.000114 | 0.004809 |
| Materna-T1 | 76 | 53.137155 | 55.731921 | 1.048831 | 2.594766 |
| Materna-T1 | 92 | 244.253437 | 319.799375 | 1.309293 | 75.545938 |
| Materna-T1 | 98 | 1.321367 | 1.393027 | 1.054232 | 0.071660 |
| Materna-T3 | 04 | 0.984095 | 0.995275 | 1.011360 | 0.011180 |
| Materna-T3 | 08 | 4.068691 | 4.057442 | 0.997235 | -0.011249 |
| Materna-T3 | 103 | 3.765787 | 3.886765 | 1.032126 | 0.120978 |
| Materna-T3 | 105 | 589.928739 | 617.236881 | 1.046291 | 27.308142 |
| Materna-T3 | 128 | 10.300430 | 10.221418 | 0.992329 | -0.079012 |
| Materna-T3 | 133 | 21.567378 | 21.568920 | 1.000072 | 0.001542 |
| Materna-T3 | 134 | 21.656235 | 22.224387 | 1.026235 | 0.568152 |
| Materna-T3 | 227 | 26.477548 | 28.409495 | 1.072965 | 1.931947 |
| Materna-T3 | 246 | 6.351634 | 6.459205 | 1.016936 | 0.107571 |
| Materna-T3 | 26 | 11.158819 | 12.005500 | 1.075876 | 0.846681 |
| Materna-T3 | 266 | 1.276635 | 1.624699 | 1.272641 | 0.348064 |
| Materna-T3 | 272 | 126.056883 | 1714.519358 | 13.601156 | 1588.462475 |
| Materna-T3 | 281 | 23.254637 | 25.037782 | 1.076679 | 1.783144 |
| Materna-T3 | 299 | 30.574696 | 82.920848 | 2.712074 | 52.346152 |
| Materna-T3 | 302 | 136.352015 | 149.582586 | 1.097032 | 13.230570 |
| Materna-T3 | 303 | 152.549486 | 159.543266 | 1.045846 | 6.993779 |
| Materna-T3 | 305 | 20.401088 | 27.068221 | 1.326803 | 6.667133 |
| Materna-T3 | 306 | 2.094740 | 2.582239 | 1.232726 | 0.487500 |
| Materna-T3 | 343 | 0.944428 | 0.948852 | 1.004684 | 0.004423 |
| Materna-T3 | 345 | 6.359597 | 9.391989 | 1.476821 | 3.032392 |
| Materna-T3 | 380 | 6.341284 | 6.448201 | 1.016861 | 0.106918 |
| Materna-T3 | 393 | 1.504039 | 1.506887 | 1.001894 | 0.002848 |
| Materna-T3 | 397 | 254.383129 | 310.991427 | 1.222532 | 56.608298 |
| Materna-T3 | 416 | 36.104423 | 37.660309 | 1.043094 | 1.555886 |
| Materna-T3 | 440 | 136.817175 | 136.936658 | 1.000873 | 0.119482 |
| Materna-T3 | 442 | 85.096058 | 85.233549 | 1.001616 | 0.137490 |
| Materna-T3 | 478 | 4.560419 | 4.553840 | 0.998557 | -0.006579 |
| Materna-T3 | 493 | 1.132270 | 1.173528 | 1.036438 | 0.041258 |
| Materna-T3 | 498 | 0.877861 | 0.889830 | 1.013634 | 0.011969 |
| Materna-T3 | 508 | 1.200939 | 1.266330 | 1.054451 | 0.065392 |
| Materna-T3 | 74 | 122.577608 | 129.093596 | 1.053158 | 6.515988 |
| Materna-T3 | 75 | 114.709157 | 130.032866 | 1.133587 | 15.323708 |
| Materna-T3 | 76 | 433.750112 | 447.929723 | 1.032691 | 14.179611 |
| Materna-T3 | 92 | 157.701880 | 184.624406 | 1.170718 | 26.922526 |
| Materna-T3 | 98 | 8.918737 | 9.609149 | 1.077411 | 0.690412 |

STAGE_19G1_PASS
