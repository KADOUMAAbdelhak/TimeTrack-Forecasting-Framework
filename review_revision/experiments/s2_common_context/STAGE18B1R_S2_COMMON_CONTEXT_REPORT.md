# STAGE 18B1R S2 COMMON-CONTEXT RECOVERY AND COMPLETION REPORT

POST-HOC SENSITIVITY CONTROL

## 1. Status and provenance

All six blocks completed. This control is post-hoc, not a replacement for frozen S2 or a prospective primary result.

Scientific parent: `fee20c316040c57b69ba12a193530c955b539771`. Manuscript parent/source commit: `f6936cd111d911e40ec2725a18fdfc53768d9ccf`.

**STAGE_18B1R_PASS.** Required final units: 10,920; exact frozen reuse: 5,208; newly completed fixed-epoch refits: 5,712; unresolved failed final units: 0. One historical serialisation failure remains preserved and has verified recovery evidence; it is not a failed final unit or an additional successful completion.

Completion and analysis finished on 21 October 2026 at 17:57 Europe/Helsinki. All six full numerical/provenance audits and the original protected-tree SHA-256 preservation check passed before analysis. An additional independent final audit passed at 18:02 Europe/Helsinki. The control process has exited. No further experiment is running under this stage.

## 2. Predecessor adapter hash

`63d7f21a27fe0bcaf836ddb91a275d0ff48fd9d5b930fbf9a56dd0b50375e806`

The entire blocked tree was copied to sibling `s2_common_context_predecessor_stage18b1r/` before editing. All 8,694 predecessor files were hash-verified again at completion. The snapshot includes code/config, blocked report, original experiment provenance, STOP/heartbeat state, failure/attempt records, completions, models and predictions. Predecessor provenance was not overwritten.

## 3. Successor adapter hash

`d227ff7d6fd443b9ba3a6e1d532acedbb14045986ef6dd4143dfa88d87513b9d`

Successor source and test hashes, predecessor links and justification are recorded in `provenance/recovery_stage18b1r_successor.json`; the exact changes are in `recovery/adapter_successor_exact.diff`. The justification is **strict-JSON representation of legitimately undefined ancillary metrics**. Accompanying administrative changes preserve separate recovery journals, recognise verified historical-failure resolution, strengthen read-only final audits and direct successor reporting to a separate path. No training/selection/aggregation numerical rule was changed.

## 4. Exact serialisation change

The known failed reuse record, Rnd VM474/fold2/THROUGHPUT/seed0, had an all-zero target, zero target variance and zero persistence MAE. Its R² and persistence skill are mathematically undefined; its MAEs and predictions are finite.

Only recognised optional undefined values are converted:

```json
{
  "r2": null,
  "r2_status": "undefined_zero_target_variance",
  "persistence_skill": null,
  "persistence_skill_status": "undefined_zero_persistence_mae"
}
```

Each affected metric retains an `original_raw_ancillary_semantics` entry with metric index, lead, field, `original_raw_value: "NaN"` and reason. Reuse completions retain the original frozen source path and SHA-256, `reuse: true`, `no_training: true`, `no_new_test_evaluation: true` and `test_evaluations: 0`.

Finite ancillary values remain numerically identical. NaN/Inf primary MAEs, targets, predictions, contexts, epochs, scaler values, checkpoint parameters and required evaluation timestamps/identities are not converted to null: they fail closed. Unknown nonfinite diagnostics, infinite R² and NaN ancillary values without the recognised zero-denominator basis are also rejected. Across the completed control, 120 ancillary-field annotations retain undefined semantics; these are not additional scientific endpoints or failed models.

## 5. New regression tests

`test_serialisation_recovery.py` adds 18 tests covering constant-target R², zero-persistence-MAE skill, unchanged finite ancillary values, primary-MAE/prediction rejection, strict JSON, unchanged source payload/hash, finite-payload semantic identity, unknown diagnostics, infinity, nonconstant-target R², positive persistence denominators, nonfinite targets/scalers/context/epoch/identity/timestamps, scaled/unclipped predictions, duplicate-identity guard and integration with the exact failed frozen reuse.

The integration test prevents calls to model construction/training and verifies unchanged MAEs and original model/prediction/source hashes, with no new test evaluation.

## 6. Full test result

**28 PASS: original 10 safety tests + 18 new regressions.** The original 10-test file is byte-identical to its preserved predecessor. Evidence: `recovery/tests_stage18b1r.log`. The tests did not train models. All six subsequent full artifact audits and the final independent audit also passed.

## 7. Configuration changes

**0.** `control_config.json` remains SHA-256 `6a3236cfa1bc46acc3bcc384a74cb766aceab6ab6fd6b4bdba70e5ea80bab78d`. Scientific question, cohorts, context/epoch rules, architecture, optimiser, seeds, preprocessing, support, scalers, metrics and gain formula are unchanged.

## 8–9. Original failure preserved; exact-reuse recovery

Original failure record SHA-256: `4475544e51605386f8ad79ce1ed636f6e9e93b2900b8d2d31dc7bc1b610161d4`. It remains in `failures/Rnd/` under control run ID `518ea20860f5e00b03261916d14c5051f5a5a71fea5bd44336a813db7f326481`; the original STOP and attempt are unchanged.

Recovered frozen run `df65aac12e3c835c7078b529` used the original record with L18/epoch48/seed0. There was **no training, inference or new test evaluation**. Its five MAEs remain exactly `[0.0008179784041826214, 0.0014686678305489771, 0.0009733683347845272, 0.000023067593700173684, 0.0]`.

The original model SHA-256 remains `e3ec3c55d86ca1cc4adf543e9ae216bfa63a02e8636c1fdffa7fc79615073b46`; prediction SHA-256 remains `2a1f7b4a4cb9f8100bd52f4f30dbdd1c4282df5a24a743d408a134014e29ec93`. A separate recovery completion/evidence record links the failure, original attempt, successor adapter and unchanged scientific identity.

## 10–11. Interrupted-attempt preservation and refit recovery

All original interrupted-attempt records remain unchanged. Separate recovery journals/evidence are in `recovery/attempts/Rnd/` and `recovery/evidence/Rnd/`.

| Rnd unit | Control run ID | Forced L | Existing S2 best epoch | Seed | Recovery result |
|---|---|---:|---:|---:|---|
| VM493/fold4/DISK_WRITE | `4ce3021757a4964518d83768a3dae00623f6cd037e2e44a2980df949cec03b40` | 9 | 21 | 2 | PASS; one final test evaluation |
| VM493/fold5/MEMORY | `7777ba54638937de20cb39c518545eaae8343f1aca3a7ec0cb89106bb859478b` | 9 | 12 | 2 | PASS; one final test evaluation |
| VM474/fold1/DISK_WRITE | `bf03831196fb1a150e17c8e2fd89094ff71608a03b9d16381915136d60d80826` | 9 | 17 | 0 | PASS; one final test evaluation |

Scientific inputs/identities, support, scalers, architecture and fixed-epoch policy match exactly. Each new model and prediction has its own recorded hash. The frozen seed function and CPU single-thread/warn-only deterministic-algorithm settings were retained. This policy does not guarantee bitwise equality across arbitrary environments; the interrupted attempts had no completed outputs for a bitwise comparison. No successful fit was rerun to demonstrate repeatability.

## 12. Pre-existing valid completions skipped without rerun

**2,767**, comprising TimeTrack420, fastStorage2,100 and Rnd247. All these completion records, their 1,564 pre-existing new model files and 1,564 pre-existing new prediction files remain byte-identical after the full run. Including historical journals and original blocked/provenance records, 8,670 pre-existing protected review artifacts were checked unchanged. The predecessor snapshot itself also remains intact.

## 13–16. Final completion/reuse/new-refit/failure counts

| Block | Eligible entities | Valid final completions | Exact frozen reuses | New fixed-epoch refits / model files | Metric rows | Full audit |
|---|---:|---:|---:|---:|---:|---|
| TimeTrack | 7 machines | 420 | 165 | 255 | 3,360 | PASS |
| fastStorage | 35 VMs | 2,100 | 918 | 1,182 | 10,500 | PASS |
| Rnd | 35 VMs | 2,100 | 981 | 1,119 | 10,500 | PASS |
| Materna T1 | 35 VMs | 2,100 | 1,026 | 1,074 | 10,500 | PASS |
| Materna T2 | 35 VMs | 2,100 | 1,035 | 1,065 | 10,500 | PASS |
| Materna T3 | 35 VMs | 2,100 | 1,083 | 1,017 | 10,500 | PASS |
| Technical accounting only | source-specific cohorts unchanged | **10,920** | **5,208** | **5,712** | **55,860** | PASS |

There are exactly 5,712 new saved prediction files. The three interrupted same-identity recovery refits are included once among the 5,712 successful final refits, not counted twice. One preserved historical failed reuse is resolved; **failed/unresolved final units = 0**, new recovery failure records = 0. Technical fit/row totals are not a pooled scientific statistic.

## 17. Duplicate-completion audit

**0 duplicated scientific identities.** Completion filenames exactly cover the planned run IDs, with one valid completion per unit. Independent metric-key checking also found no duplicated block/resource/entity/fold/seed/lead row. Historical failed/interrupted journals are never counted as successful completions.

## 18. Forced-context and epoch verification

PASS. The unchanged eligible cohorts supply 910 source/entity/fold common-context groups. Every one of the four S2 target models and three seeds uses the exact frozen M1 selected context for its group. No new context was selected, averaged or inferred. Every fixed epoch matches the corresponding exact forced-L S2 inner record and hash—not M1's epoch or S2's epoch at another L. No new inner fit was run.

## 19. Support/scaler and numerical verification

PASS. All six full audits verified legal support, forced-L training-only scalers, source identities/hashes, frozen selection/inner records, finite required prediction/target/checkpoint values and finite primary MAEs. Prediction origins/leads/targets/timestamps/native targets match original frozen S2 support exactly. Reused model/prediction hashes match frozen originals; new model/prediction hashes are recorded. Final audits performed no model inference or test evaluation.

## 20. Six-block completion status

**All six COMPLETE / full audit PASS.** Only after all 10,920 valid completions, full audits and original-baseline preservation did `analyse_control.py` run. `completion_summary.json` records COMPLETE; `validation/stage18b1r_final_independent_audit.json` independently verifies counts, identity uniqueness, the control aggregation and all three authorised gain formulas. The independent audit did not rerun training or frozen headline aggregation.

## 21–24. Full scientific result table and authorised comparisons

POST-HOC SENSITIVITY RESULT

| Block/resource | S1 MAE | S2 MAE | Common S2 MAE | M1 MAE | Original M1:S2 % | Common:S2 % | M1:Common % | Common:S1 % | Context matched | Category |
|---|---|---|---|---|---|---|---|---|---|---|
| TimeTrack / CPU | 1.80838356 | 1.8682962 | 1.84467005 | 1.85952338 | 0.469562155 | 1.2645823 | -0.805202599 | -2.00657085 | 13/35 | GAP_REVERSED |
| TimeTrack / THROUGHPUT | 29.7980861 | 29.8704216 | 29.9600003 | 30.1213583 | -0.840084191 | -0.29989091 | -0.538578134 | -0.5433709 | 11/35 | GAP_REDUCED |
| TimeTrack / MEMORY | 318123366 | 315389449 | 317228559 | 373663597 | -18.4768858 | -0.583123706 | -17.7900242 | 0.281276737 | 18/35 | GAP_REDUCED |
| TimeTrack / DISK_WRITE | 3131645.65 | 3147063.35 | 3154439.57 | 3172100.5 | -0.795571899 | -0.234384217 | -0.559875422 | -0.727857573 | 13/35 | GAP_REDUCED |
| fastStorage / CPU | 1.22590479 | 1.26511559 | 1.26907405 | 1.26454569 | 0.0450473868 | -0.312892724 | 0.356823635 | -3.52141987 | 85/175 | GAP_LARGELY_UNCHANGED |
| fastStorage / THROUGHPUT | 151.904496 | 151.885158 | 160.45416 | 193.037153 | -27.0941515 | -5.64176377 | -20.30673 | -5.62831495 | 77/175 | GAP_REDUCED |
| fastStorage / MEMORY | 81556.0025 | 79557.8923 | 79889.5268 | 83430.0237 | -4.86706123 | -0.416846685 | -4.43174098 | 2.04335137 | 72/175 | GAP_REDUCED |
| fastStorage / DISK_WRITE | 12.533837 | 12.1967762 | 12.4747054 | 12.6934446 | -4.07212856 | -2.27871035 | -1.75346189 | 0.471775951 | 72/175 | GAP_REDUCED |
| Rnd / CPU | 1.57924886 | 1.55693618 | 1.55944909 | 1.81398543 | -16.5099408 | -0.161400732 | -16.322196 | 1.25374619 | 86/175 | GAP_REDUCED |
| Rnd / THROUGHPUT | 282.032798 | 302.38003 | 307.084119 | 345.677786 | -14.3189866 | -1.55568784 | -12.5677833 | -8.88241412 | 92/175 | GAP_REDUCED |
| Rnd / MEMORY | 166981.96 | 164188.214 | 164535.998 | 178826.804 | -8.91573725 | -0.21182065 | -8.68551888 | 1.46480594 | 77/175 | GAP_REDUCED |
| Rnd / DISK_WRITE | 100.876592 | 100.714787 | 102.495494 | 106.305699 | -5.55123314 | -1.76806998 | -3.71743629 | -1.60483416 | 72/175 | GAP_REDUCED |
| Materna-T1 / CPU | 0.938313948 | 0.97882995 | 0.964300026 | 0.970189829 | 0.882698801 | 1.48441757 | -0.610785373 | -2.76944386 | 84/175 | GAP_REVERSED |
| Materna-T1 / THROUGHPUT | 222.014671 | 219.82353 | 220.075943 | 235.889014 | -7.3083551 | -0.114825347 | -7.18527923 | 0.873243331 | 86/175 | GAP_REDUCED |
| Materna-T1 / MEMORY | 232769.78 | 232815.618 | 239306.362 | 263590.024 | -13.21836 | -2.78793333 | -10.1475205 | -2.80817464 | 81/175 | GAP_REDUCED |
| Materna-T1 / DISK_WRITE | 237.998971 | 253.944097 | 252.906062 | 323.671421 | -27.4577457 | 0.408764922 | -27.9808867 | -6.26351091 | 91/175 | GAP_LARGELY_UNCHANGED |
| Materna-T2 / CPU | 0.926460743 | 0.887478754 | 0.897817973 | 0.910236932 | -2.56436309 | -1.16501028 | -1.38323795 | 3.09163344 | 84/175 | GAP_REDUCED |
| Materna-T2 / THROUGHPUT | 286.574227 | 285.730795 | 289.537514 | 310.568691 | -8.69276116 | -1.3322747 | -7.26371384 | -1.03403827 | 96/175 | GAP_REDUCED |
| Materna-T2 / MEMORY | 252266.422 | 242306.512 | 246249.943 | 264760.629 | -9.26682326 | -1.62745553 | -7.51703138 | 2.38496998 | 85/175 | GAP_REDUCED |
| Materna-T2 / DISK_WRITE | 142.894997 | 144.49568 | 144.437272 | 155.894226 | -7.88850311 | 0.040422132 | -7.93213158 | -1.07930654 | 80/175 | GAP_LARGELY_UNCHANGED |
| Materna-T3 / CPU | 1.12003835 | 1.15125995 | 1.15870567 | 1.24450067 | -8.09901546 | -0.646745237 | -7.40438273 | -3.45232113 | 88/175 | GAP_REDUCED |
| Materna-T3 / THROUGHPUT | 344.053728 | 343.899709 | 345.427121 | 371.116889 | -7.91427836 | -0.444144676 | -7.4371022 | -0.399179952 | 85/175 | GAP_REDUCED |
| Materna-T3 / MEMORY | 278479.261 | 269877.033 | 272151.783 | 293363.332 | -8.70259284 | -0.842884106 | -7.79401423 | 2.27215419 | 90/175 | GAP_REDUCED |
| Materna-T3 / DISK_WRITE | 74.6173252 | 73.1942472 | 73.8961942 | 125.378155 | -71.2950946 | -0.959019295 | -69.6679462 | 0.966439152 | 98/175 | GAP_REDUCED |

MAEs are in each source/resource's original native units; they must not be compared across unlike resources or datasets. Exact machine-readable values are in `posthoc_results.csv`. Original S1/S2/M1 values and original M1:S2 gains were read from frozen aggregate tables; only the control's authorised post-hoc aggregate and comparisons were calculated. Negative gain means the candidate has higher error.

For each column `candidate:reference`, gain is `100 × (reference MacroMAE − candidate MacroMAE) / reference MacroMAE`. Common:S2 and M1:Common are the primary sensitivity contrasts; Common:S1 is completeness-only. Equal seed means within entity/fold/horizon are followed by equal entity/fold means and equal horizon means, separately for each block. These are not sample-count-weighted pooled errors. Changing the reference MAE also changes the percentage denominator; a percentage-point gap change is not an additive or causally isolated fraction of the original effect.

Categories are descriptive, not hypothesis tests or materiality decisions. No percentage cut-off is introduced. GAP_REVERSED means a sign reversal; GAP_REMOVED would require an exactly zero point gap; GAP_REDUCED means a smaller absolute point gap, even when the numerical reduction is tiny. GAP_LARGELY_UNCHANGED here describes persistence without reduction, with actual widening stated explicitly below. The fastStorage CPU entry remains a small M1 advantage, whereas the T1/T2 disk-write entries remain adverse and widen slightly. These labels do not conceal those distinctions. There are 19 GAP_REDUCED, 3 GAP_LARGELY_UNCHANGED, 2 GAP_REVERSED and 0 GAP_REMOVED entries; this is categorical bookkeeping, not a pooled effect estimate.

## 26. All 24 block/resource categories and numerical interpretation

- TimeTrack CPU: GAP_REVERSED; M1 gap 0.469562% → -0.805203% (-1.274765 percentage points); absolute gap widens. Common-S2 versus original S2: +1.264582%.
- TimeTrack THROUGHPUT: GAP_REDUCED; M1 gap -0.840084% → -0.538578% (+0.301506 percentage points); absolute gap narrows. Common-S2 versus original S2: -0.299891%.
- TimeTrack MEMORY: GAP_REDUCED; M1 gap -18.476886% → -17.790024% (+0.686862 percentage points); absolute gap narrows. Common-S2 versus original S2: -0.583124%.
- TimeTrack DISK_WRITE: GAP_REDUCED; M1 gap -0.795572% → -0.559875% (+0.235696 percentage points); absolute gap narrows. Common-S2 versus original S2: -0.234384%.
- fastStorage CPU: GAP_LARGELY_UNCHANGED; M1 gap 0.045047% → 0.356824% (+0.311776 percentage points); absolute gap widens. Common-S2 versus original S2: -0.312893%.
- fastStorage THROUGHPUT: GAP_REDUCED; M1 gap -27.094152% → -20.306730% (+6.787422 percentage points); absolute gap narrows. Common-S2 versus original S2: -5.641764%.
- fastStorage MEMORY: GAP_REDUCED; M1 gap -4.867061% → -4.431741% (+0.435320 percentage points); absolute gap narrows. Common-S2 versus original S2: -0.416847%.
- fastStorage DISK_WRITE: GAP_REDUCED; M1 gap -4.072129% → -1.753462% (+2.318667 percentage points); absolute gap narrows. Common-S2 versus original S2: -2.278710%.
- Rnd CPU: GAP_REDUCED; M1 gap -16.509941% → -16.322196% (+0.187745 percentage points); absolute gap narrows. Common-S2 versus original S2: -0.161401%.
- Rnd THROUGHPUT: GAP_REDUCED; M1 gap -14.318987% → -12.567783% (+1.751203 percentage points); absolute gap narrows. Common-S2 versus original S2: -1.555688%.
- Rnd MEMORY: GAP_REDUCED; M1 gap -8.915737% → -8.685519% (+0.230218 percentage points); absolute gap narrows. Common-S2 versus original S2: -0.211821%.
- Rnd DISK_WRITE: GAP_REDUCED; M1 gap -5.551233% → -3.717436% (+1.833797 percentage points); absolute gap narrows. Common-S2 versus original S2: -1.768070%.
- Materna-T1 CPU: GAP_REVERSED; M1 gap 0.882699% → -0.610785% (-1.493484 percentage points); absolute gap narrows. Common-S2 versus original S2: +1.484418%.
- Materna-T1 THROUGHPUT: GAP_REDUCED; M1 gap -7.308355% → -7.185279% (+0.123076 percentage points); absolute gap narrows. Common-S2 versus original S2: -0.114825%.
- Materna-T1 MEMORY: GAP_REDUCED; M1 gap -13.218360% → -10.147521% (+3.070839 percentage points); absolute gap narrows. Common-S2 versus original S2: -2.787933%.
- Materna-T1 DISK_WRITE: GAP_LARGELY_UNCHANGED; M1 gap -27.457746% → -27.980887% (-0.523141 percentage points); absolute gap widens. Common-S2 versus original S2: +0.408765%.
- Materna-T2 CPU: GAP_REDUCED; M1 gap -2.564363% → -1.383238% (+1.181125 percentage points); absolute gap narrows. Common-S2 versus original S2: -1.165010%.
- Materna-T2 THROUGHPUT: GAP_REDUCED; M1 gap -8.692761% → -7.263714% (+1.429047 percentage points); absolute gap narrows. Common-S2 versus original S2: -1.332275%.
- Materna-T2 MEMORY: GAP_REDUCED; M1 gap -9.266823% → -7.517031% (+1.749792 percentage points); absolute gap narrows. Common-S2 versus original S2: -1.627456%.
- Materna-T2 DISK_WRITE: GAP_LARGELY_UNCHANGED; M1 gap -7.888503% → -7.932132% (-0.043628 percentage points); absolute gap widens. Common-S2 versus original S2: +0.040422%.
- Materna-T3 CPU: GAP_REDUCED; M1 gap -8.099015% → -7.404383% (+0.694633 percentage points); absolute gap narrows. Common-S2 versus original S2: -0.646745%.
- Materna-T3 THROUGHPUT: GAP_REDUCED; M1 gap -7.914278% → -7.437102% (+0.477176 percentage points); absolute gap narrows. Common-S2 versus original S2: -0.444145%.
- Materna-T3 MEMORY: GAP_REDUCED; M1 gap -8.702593% → -7.794014% (+0.908579 percentage points); absolute gap narrows. Common-S2 versus original S2: -0.842884%.
- Materna-T3 DISK_WRITE: GAP_REDUCED; M1 gap -71.295095% → -69.667946% (+1.627148 percentage points); absolute gap narrows. Common-S2 versus original S2: -0.959019%.

## 25. Five priority-case interpretations

- TimeTrack MEMORY: M1:original-S2 -18.476886%; M1:common-S2 -17.790024%; common-S2 MAE 317228559 versus original-S2 315389449; context matches 18/35.
- fastStorage THROUGHPUT: M1:original-S2 -27.094152%; M1:common-S2 -20.306730%; common-S2 MAE 160.45416 versus original-S2 151.885158; context matches 77/175.
- Rnd CPU: M1:original-S2 -16.509941%; M1:common-S2 -16.322196%; common-S2 MAE 1.55944909 versus original-S2 1.55693618; context matches 86/175.
- Materna-T1 DISK_WRITE: M1:original-S2 -27.457746%; M1:common-S2 -27.980887%; common-S2 MAE 252.906062 versus original-S2 253.944097; context matches 91/175.
- Materna-T3 DISK_WRITE: M1:original-S2 -71.295095%; M1:common-S2 -69.667946%; common-S2 MAE 73.8961942 versus original-S2 73.1942472; context matches 98/175.

Interpretation without a formal materiality threshold: fastStorage throughput shows a conspicuous partial narrowing of 6.787422 percentage points, but a −20.306730% M1 deficit remains. TimeTrack memory changes by only 0.686862 points and retains a −17.790024% deficit. Rnd CPU changes by only 0.187745 points and retains a −16.322196% deficit. T1 disk write does not improve; T3 disk write changes by 1.627148 points but retains the extreme −69.667946% deficit. Thus context restriction does not materially explain the large memory/Rnd-CPU/Materna-disk deficits in the ordinary descriptive sense used here, while it contributes appreciably to the fastStorage throughput comparator difference. No binary numerical materiality rule or significance test was introduced.

## 27. Central context-confound answer

**Only partially and in a resource/environment-specific way; it does not generally explain away the M1 degradation.** Restricting S2 to frozen M1 contexts worsens S2 test error in many cells and narrows many M1 gaps. The fastStorage throughput and disk-write comparisons demonstrate a meaningful comparator effect numerically (−27.094152→−20.306730% and −4.072129→−1.753462%). Nevertheless, M1 remains worse than context-aligned S2 for throughput, memory and disk write in every block. Large deficits persist, including the three priority cases above. This is the consequence of the implemented S2 context restriction, not complete causal isolation of representation sharing.

## 28. Materna T1 disk-write answer

**No.** Common-context S2 improves slightly relative to original S2: MAE253.944097→252.906062, gain+0.408765%. With fixed original M1 MAE323.671421, the M1 gap widens from −27.457746% to **−27.980887%**. Removing target-specific context freedom therefore does not explain this degradation.

## 29. Materna T3 disk-write answer

**Not to a degree that accounts for the extreme degradation.** Common-context S2 worsens slightly: MAE73.194247→73.896194, gain−0.959019%. The M1 gap narrows from −71.295095% to **−69.667946%**, retaining its direction and large magnitude. This is limited comparator sensitivity, not removal of the failure to match S2 accuracy.

## 30–32. Throughput, memory and disk-write answers across six blocks

POST-HOC SENSITIVITY RESULT — M1 versus S2-common-context gain (%):

| Block | Throughput | Memory | Disk write |
|---|---:|---:|---:|
| TimeTrack | −0.538578 | −17.790024 | −0.559875 |
| fastStorage | −20.306730 | −4.431741 | −1.753462 |
| Rnd | −12.567783 | −8.685519 | −3.717436 |
| Materna T1 | −7.185279 | −10.147521 | −27.980887 |
| Materna T2 | −7.263714 | −7.517031 | −7.932132 |
| Materna T3 | −7.437102 | −7.794014 | −69.667946 |

**Throughput:** all six remain adverse for M1. Context restriction narrows each point gap, most visibly fastStorage, but removes/reverses none.

**Memory:** all six remain adverse for M1. Each point gap narrows, including T1 −13.218360→−10.147521%, but the context-aligned result does not eliminate the disadvantage.

**Disk write:** all six remain adverse for M1. TimeTrack, fastStorage, Rnd and T3 narrow; T1 and T2 widen slightly. In particular, context freedom is not an adequate explanation for the two extreme Materna disk-write results.

No across-block mean or new global statistic was calculated.

## 33. Unexpected findings

- Removing context freedom sometimes **improves** S2 outer-test MAE. TimeTrack CPU (+1.264582% common:S2) and T1 CPU (+1.484418%) turn small original M1 advantages into disadvantages: +0.469562→−0.805203% and +0.882699→−0.610785%, respectively. Target-specific validation selection is not guaranteed to minimise outer-test error; this observation does not identify why it occurred.
- fastStorage CPU retains a small M1 advantage (+0.045047→+0.356824%); it is the only positive M1:common-S2 point gain in the table. CPU is not uniformly adverse.
- T1 and T2 disk-write common-context S2 MAEs improve slightly, so the corresponding M1 disadvantages increase rather than shrink.
- The recovered serialisation case was not unique: 120 explicit ancillary undefined-field annotations occur across final completions. These preserve legitimate undefined diagnostics without changing finite MAE endpoints. No primary nonfinite result was accepted.

## 34. Scientific interpretation

Four independent H64/two-layer S2 networks remain per entity/fold/seed. Each forced L comes directly from frozen M1; each epoch comes from existing S2 inner best_epoch at that exact L. Source-specific support/scalers, transforms and horizons are preserved. Exact frozen reuse is reference-based, not copied/retrained. New final refits use one test forward pass only. No inner fit, new selection, bootstrap, global pooled statistic or capacity-matched M1 was run.

The result strengthens the limited operational conclusion that matching input-history length does not by itself remove the evaluated shared model's accuracy disadvantage for the three non-CPU resources. It also demonstrates that the original M1:S2 contrast contains a context-selection-freedom component in some cells. Neither observation identifies a pure mechanistic or universal multi-task-learning effect. The frozen primary results are not replaced, reclassified or rewritten by this post-hoc control.

## 35. Limitations

The numerical consequence of restricting S2 context selection is estimated within this implemented pipeline. This does not completely isolate representation sharing, capacity, optimisation geometry or model-count differences. Scaler training-row sets and refit epochs can change as protocol-prescribed consequences of changing L. Three seeds and the original eligible populations remain the scope. Materna traces are dependent temporal replications, not independent datasets. The control was motivated after observing the original results and is not prospective confirmatory evidence. No bootstrap, new interval or significance test was run. Descriptive point-gap reductions do not establish statistical or operational importance. Concurrent unrelated workload was observed, so recorded runtime is not a clean hardware-efficiency experiment.

## 36–40. Preservation, commit and push

Full original-baseline content SHA-256, membership, size and mtime checks passed for **204,747 protected files** after fitting. Manuscript modifications=**0**; frozen scientific artifact modifications=**0**; original frozen result modifications=**0**. `paper/jss` and revision HEAD remain `f6936cd111d911e40ec2725a18fdfc53768d9ccf`; `main` and the scientific tag target remain `fee20c316040c57b69ba12a193530c955b539771`; the annotated tag object is unchanged. Tracked and staged diffs are empty. The original blocked report, STOP/failure/attempts, original experiment provenance and predecessor copy remain preserved. Only review-revision artifacts changed. Commit=**NO**; push=**NO**.

Detailed fit identities, source paths/hashes, equality checks, support/scaler hashes, new model/prediction hashes and timestamps are in plans/, completions/ and provenance/. Every output belongs to this new post-hoc namespace.

The automatic follow-up is paused after this completed handoff. No capacity-matched M1 or manuscript revision was started.

STAGE_18B1R_PASS
