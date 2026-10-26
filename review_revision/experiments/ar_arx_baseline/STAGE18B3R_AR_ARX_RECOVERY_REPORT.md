# STAGE 18B3R AR/ARX RECOVERY REPORT

POST-HOC SENSITIVITY RESULT

Complete: STAGE_18B3R_PASS. This is a POST-HOC SENSITIVITY CONTROL, not a replacement for frozen results. The generated draft has been numerically and scientifically reviewed; all24 table rows were independently recomputed from persisted per-cell metrics with equal entity/fold and horizon weighting.

## Recovery, hashes and exact scope

The blocked run's3176 files were copied and individually SHA256-verified at
`review_revision/experiments/ar_arx_baseline_predecessor_stage18b3`. The original
runner, config, provenance seal, report,1400 valid inner completions,280 existing
selections,35 failed attempts/failures and original STOP are retained there;
original failures/attempts/STOP, scientific plans and blocked report also remain
unchanged in this experiment. Recovery does not erase the failed execution.

- Predecessor runner SHA256: `5e220630aca9bafe2d0f79ee4f6bf86b0f74262f07908b5070d272890163b7ad`.
- Final successor runner SHA256: `3a256e9a8b7835a15fbce87bfdcc5783d8ed61359016724f59324391e7f82565`.
- Unchanged scientific config SHA256: `ae97a89cb1e8034890256fa8f21ea242fa729fcb725be43088be7552e1309626`; scientific config changes=0.
- Original provenance seal SHA256: `df7a79a2751defcdc97e31c80eb264dcb15c59aeff957314cdd656e33017735c`.
- Final recovery seal (`recovery/successor_audit_reduction_fix.json`) SHA256: `ef92ed24f57c75e531d7f42e6c330e927a2594b12466c82b5047347c47bec9be`.
- Snapshot manifest SHA256: `98a7f111de87730c5d61b437bb3cbb7f499f9cd552086f61bed7569662b7460c`.

Exact scientific-adapter fix: cast TimeTrack truth and persistence operands to
float64 **before** persistence-reference residual/MAE calculation, reproducing
the frozen baseline metric. Retain its original strict `rtol=1e-12, atol=0`
reference check and fail on genuine mismatch. External arithmetic is unchanged.
The original per-cell persistence-skill denominator arithmetic is separately
retained; no learned prediction, primary MAE, alpha selection or aggregation
formula was altered. Worker exceptions now cross multiprocessing as built-in
RuntimeError values, so a real failure terminates the pool cleanly without
editing the frozen Conflict implementation.

Two checker-only precision issues were also repaired, without new scientific
fits or changes to persisted metrics: NumPy2 Python-float/float32 scalar
promotion in the TimeTrack skill checker, and one Rnd row's different vector/
column MAE reduction order (2.6e-14 MAE difference). The checker independently
verifies native MAE, then checks its derived skill using the verified stored MAE
and original denominator. Neither tolerance was relaxed. Both failed audit
records, prior seals/code/logs and exact diffs are preserved under `recovery/`.
The full original-to-first-successor diff is `exact_adapter_diff.patch`; the
two subsequent checker-only diffs are `audit_checker_exact_diff.patch` and
`reduction_checker_exact_diff.patch`. Analysis code changes only recognise
hash-resolved historical failures and use a separate recovery report filename;
its scientific aggregation/comparison code is unchanged.

Tests: **15 checks PASS**: the original8 synthetic safety checks,5 recovery
regressions and2 additional read-only checker regressions. Evidence reproduces
all35 old float32 blockers, exactly matches1120 TimeTrack persistence-reference
values, verifies unchanged behaviour for all5 external blocks, rejects genuine
mismatches, verifies unchanged config/training/selection helpers and fit/predict
calls, and tests exception transport. The original13-test suite was rerun after
the final checker correction and still passes. The checker regressions verify
all2240 TimeTrack stored metrics and the exact stored-skill formula in Rnd;
no scientific fit/inference was performed by these read-only regressions.

The35 failed CPU-AR finals had **0 complete reusable model/prediction artifacts**.
Each therefore received exactly1 expressly authorised same-identity final
refit/test prediction:35 reruns,0 artifact reuses,35 recovered completions,
0 unresolved recovery identities. Selected alpha, L, support/scaler hashes and
scientific model specification exactly match the failed identities. No prior
test values were used for tuning or reselection. All1400 previously valid inner
completions and all280 pre-existing selections remain byte-identical;27720
valid files present before the last checker correction also remain unchanged.

## Verification and counts

All six block audits pass. Valid completions:36,400 inner +7,280 final =43,680
scientific identities, exactly1 valid completion per identity; duplicates=0.
There are7280 alpha selections, final model-state files and prediction files,
and37240 per-lead metric rows. No artificial seed repetitions or cross-VM
pooling. No inner checkpoint is claimed: all5 alpha scores/identities are kept.

Execution accounting is distinct:35 historical failed final fits/test calls are
preserved and resolved. Total actual fits=43,715; total final test calls=7315
(7280 accepted finals plus35 historical failed evaluations). This recovery run
reused1400 inner fits and executed35000 remaining inner+7280 final fits;35 of
those final fits are the authorised recoveries, not new identities. Current
scientific fit failures=0; unresolved failures=0. The2 subsequent checker audit
failures were corrected read-only; they caused no additional fit/test repetition.

| Block | Inner completions | Final completions | Metric rows | Undefined skill cells | Audit |
|---|---:|---:|---:|---:|---|
| TimeTrack | 1400 | 280 | 2240 | 0 | PASS |
| fastStorage | 7000 | 1400 | 7000 | 0 | PASS |
| Rnd | 7000 | 1400 | 7000 | 60 | PASS |
| Materna T1 | 7000 | 1400 | 7000 | 0 | PASS |
| Materna T2 | 7000 | 1400 | 7000 | 0 | PASS |
| Materna T3 | 7000 | 1400 | 7000 | 0 | PASS |

Every final completion passes frozen cohort/context, split/purging/legal-support,
source scaler, native target/timestamp, persistence-reference, model/prediction
hash, finiteness, selection and identity audits. Training-only preprocessing
and lag-only input construction are retained. Direct multi-output fit/test
calls are unchanged. Independent final checks confirm all counts and all24
MacroMAE/gain/persistence/directional rows. No current failures or interrupted
units remain. Historical STOP/failure records are resolved by exact evidence,
not deleted or ignored.

## Results

Native-unit MAEs; positive gain favours ARX (or frozen S2). Skill is 1−MAE/persistence-MAE per entity/fold/lead, averaged over entity/fold then equally over horizons; it is not 1−MacroMAE/MacroPersistenceMAE. Higher skill is better, zero matches persistence. Undefined zero-denominator skills are omitted by the frozen mean semantics, with explicit counts in the CSV and metric records.

Rnd throughput has30 undefined zero-persistence-MAE cells per formulation
(60 total); no other block/resource has undefined skill cells. Primary MAEs and
predictions remain finite for all of these cells. TimeTrack retains its frozen
raw-window-precision skill denominator while its baseline persistence-MAE
reference uses float64; these two quantities must not be silently conflated.

| Block / resource | AR MAE | ARX MAE | ARX:AR % | AR skill | ARX skill | S2:S1 % | Direction |
|---|---:|---:|---:|---:|---:|---:|---|
| TimeTrack / CPU | 1.84710981 | 2.10577268 | -14.0036546 | 0.159343298 | 0.0815464905 | -3.31304939 | agree |
| TimeTrack / THROUGHPUT | 28.7398913 | 269.709436 | -838.449742 | 0.334121212 | -3.89912618 | -0.242751999 | agree |
| TimeTrack / MEMORY | 285921753 | 352294282 | -23.2135287 | 0.08131747 | -0.0977108962 | 0.859389141 | disagree |
| TimeTrack / DISK_WRITE | 3113844.51 | 3349727.3 | -7.57529129 | 0.359678175 | -1.75602777 | -0.492319437 | agree |
| fastStorage / CPU | 0.903490393 | 0.942933821 | -4.36567212 | -0.0219856351 | -0.176805914 | -3.19851921 | agree |
| fastStorage / THROUGHPUT | 180.666082 | 218.14695 | -20.7459347 | -0.0544734019 | -0.0531314558 | 0.0127305837 | disagree |
| fastStorage / MEMORY | 82862.8121 | 80479.8998 | 2.8757318 | 0.239857394 | 0.255033573 | 2.44998537 | agree |
| fastStorage / DISK_WRITE | 12.4779617 | 12.3471595 | 1.04826621 | 0.244750631 | 0.218528523 | 2.68920706 | agree |
| Rnd / CPU | 1.66059802 | 1.65689715 | 0.222863439 | -0.102667662 | -0.123740202 | 1.41286654 | agree |
| Rnd / THROUGHPUT | 297.212154 | 296.124718 | 0.365878813 | -0.152224314 | -0.0152147666 | -7.21449131 | disagree |
| Rnd / MEMORY | 179094.05 | 171467.311 | 4.25851044 | 0.167068045 | 0.19297438 | 1.67308265 | agree |
| Rnd / DISK_WRITE | 115.126219 | 113.188117 | 1.68345784 | 0.282755118 | -0.147219147 | 0.160399841 | agree |
| Materna-T1 / CPU | 1.03542198 | 0.970484277 | 6.27161727 | -0.0341789997 | 0.0695182796 | -4.31795795 | disagree |
| Materna-T1 / THROUGHPUT | 240.856034 | 274.3359 | -13.900364 | 0.105601746 | 0.0272661373 | 0.986935426 | disagree |
| Materna-T1 / MEMORY | 273701.208 | 253935.173 | 7.22175656 | 0.256869712 | 0.293004157 | -0.0196923064 | disagree |
| Materna-T1 / DISK_WRITE | 293.14022 | 287.140613 | 2.04666767 | 0.139825783 | 0.10324847 | -6.6996617 | disagree |
| Materna-T2 / CPU | 1.14891739 | 1.03783759 | 9.66821464 | 0.0288119013 | 0.0875702852 | 4.20762447 | agree |
| Materna-T2 / THROUGHPUT | 368.478565 | 365.121428 | 0.911080694 | 0.227356342 | 0.217187622 | 0.294315345 | agree |
| Materna-T2 / MEMORY | 285176.347 | 266728.273 | 6.46900568 | 0.267813508 | 0.294421811 | 3.94817079 | agree |
| Materna-T2 / DISK_WRITE | 219.798709 | 197.658792 | 10.072815 | 0.321262097 | 0.346215088 | -1.12018147 | disagree |
| Materna-T3 / CPU | 1.12453508 | 1.10009013 | 2.17378219 | 0.0690411745 | 0.075678655 | -2.78754756 | disagree |
| Materna-T3 / THROUGHPUT | 362.761757 | 370.556797 | -2.14880399 | 0.179377353 | 0.110706097 | 0.0447658987 | disagree |
| Materna-T3 / MEMORY | 291292.537 | 286013.07 | 1.81242772 | 0.240701286 | 0.237930881 | 3.08900159 | agree |
| Materna-T3 / DISK_WRITE | 79.9782874 | 80.5307297 | -0.690740332 | 0.0168918195 | 0.114440209 | 1.90716833 | disagree |

## Direction and magnitude, without thresholds or significance tests

- TimeTrack CPU: Ridge -14.003655% versus frozen LSTM -3.313049%; agreement, larger absolute gain magnitude; difference -10.690605 percentage points.
- TimeTrack THROUGHPUT: Ridge -838.449742% versus frozen LSTM -0.242752%; agreement, larger absolute gain magnitude; difference -838.206990 percentage points.
- TimeTrack MEMORY: Ridge -23.213529% versus frozen LSTM +0.859389%; disagreement, larger absolute gain magnitude; difference -24.072918 percentage points.
- TimeTrack DISK_WRITE: Ridge -7.575291% versus frozen LSTM -0.492319%; agreement, larger absolute gain magnitude; difference -7.082972 percentage points.
- fastStorage CPU: Ridge -4.365672% versus frozen LSTM -3.198519%; agreement, larger absolute gain magnitude; difference -1.167153 percentage points.
- fastStorage THROUGHPUT: Ridge -20.745935% versus frozen LSTM +0.012731%; disagreement, larger absolute gain magnitude; difference -20.758665 percentage points.
- fastStorage MEMORY: Ridge +2.875732% versus frozen LSTM +2.449985%; agreement, larger absolute gain magnitude; difference +0.425746 percentage points.
- fastStorage DISK_WRITE: Ridge +1.048266% versus frozen LSTM +2.689207%; agreement, smaller absolute gain magnitude; difference -1.640941 percentage points.
- Rnd CPU: Ridge +0.222863% versus frozen LSTM +1.412867%; agreement, smaller absolute gain magnitude; difference -1.190003 percentage points.
- Rnd THROUGHPUT: Ridge +0.365879% versus frozen LSTM -7.214491%; disagreement, smaller absolute gain magnitude; difference +7.580370 percentage points.
- Rnd MEMORY: Ridge +4.258510% versus frozen LSTM +1.673083%; agreement, larger absolute gain magnitude; difference +2.585428 percentage points.
- Rnd DISK_WRITE: Ridge +1.683458% versus frozen LSTM +0.160400%; agreement, larger absolute gain magnitude; difference +1.523058 percentage points.
- Materna-T1 CPU: Ridge +6.271617% versus frozen LSTM -4.317958%; disagreement, larger absolute gain magnitude; difference +10.589575 percentage points.
- Materna-T1 THROUGHPUT: Ridge -13.900364% versus frozen LSTM +0.986935%; disagreement, larger absolute gain magnitude; difference -14.887299 percentage points.
- Materna-T1 MEMORY: Ridge +7.221757% versus frozen LSTM -0.019692%; disagreement, larger absolute gain magnitude; difference +7.241449 percentage points.
- Materna-T1 DISK_WRITE: Ridge +2.046668% versus frozen LSTM -6.699662%; disagreement, smaller absolute gain magnitude; difference +8.746329 percentage points.
- Materna-T2 CPU: Ridge +9.668215% versus frozen LSTM +4.207624%; agreement, larger absolute gain magnitude; difference +5.460590 percentage points.
- Materna-T2 THROUGHPUT: Ridge +0.911081% versus frozen LSTM +0.294315%; agreement, larger absolute gain magnitude; difference +0.616765 percentage points.
- Materna-T2 MEMORY: Ridge +6.469006% versus frozen LSTM +3.948171%; agreement, larger absolute gain magnitude; difference +2.520835 percentage points.
- Materna-T2 DISK_WRITE: Ridge +10.072815% versus frozen LSTM -1.120181%; disagreement, larger absolute gain magnitude; difference +11.192996 percentage points.
- Materna-T3 CPU: Ridge +2.173782% versus frozen LSTM -2.787548%; disagreement, smaller absolute gain magnitude; difference +4.961330 percentage points.
- Materna-T3 THROUGHPUT: Ridge -2.148804% versus frozen LSTM +0.044766%; disagreement, larger absolute gain magnitude; difference -2.193570 percentage points.
- Materna-T3 MEMORY: Ridge +1.812428% versus frozen LSTM +3.089002%; agreement, smaller absolute gain magnitude; difference -1.276574 percentage points.
- Materna-T3 DISK_WRITE: Ridge -0.690740% versus frozen LSTM +1.907168%; disagreement, smaller absolute gain magnitude; difference -2.597909 percentage points.

## Central scientific conclusion

Cross-resource context is **selective rather than uniformly beneficial under
Ridge too**, but the particular gains are model-/design-specific. All4 TimeTrack
resources worsen with ARX; all4 Rnd resources improve in MacroMAE. Other blocks
have resource-specific mixtures. This is evidence against a model-independent
claim that adding cross-resource inputs is uniformly helpful, not evidence
that the selective phenomenon is unique to LSTMs.

Memory shows repeated positive ARX-vs-AR MacroMAE gains in every external block:
fastStorage +2.875732%, Rnd +4.258510%, T1 +7.221757%, T2 +6.469006%, T3
+1.812428%. It is not universal: TimeTrack reverses from frozen LSTM +0.859389%
to Ridge -23.213529%. Both AR/ARX memory skills are positive in the5 external
blocks; TimeTrack ARX memory skill is negative. T3's ARX memory skill is slightly
lower despite its positive MacroMAE gain, reflecting different aggregation
weights, not a contradiction.

Frozen positive LSTM contextual effects reverse under Ridge for TimeTrack
memory, fastStorage throughput, Materna T1 throughput and T3 throughput/disk.
Frozen negative LSTM effects reverse to positive Ridge effects for Rnd
throughput, T1 CPU/memory/disk, T2 disk and T3 CPU. No displayed gain is exactly
zero: no effect is declared to have "disappeared" using an invented threshold.
Examples of reduced magnitude without reversal include Rnd CPU (+1.412867%
LSTM to +0.222863% Ridge), fastStorage disk (+2.689207% to +1.048266%) and T3
memory (+3.089002% to +1.812428%). All24 exact signed comparisons and their
descriptive magnitude differences are above and in `posthoc_results.csv`.

Therefore conclusions about **which resources and blocks benefit** must be
model-family/design-specific. Repeated external-memory benefits provide a
limited cross-family recurrence; they do not support a universal memory claim.
This comparison does not isolate architecture alone: Ridge shares frozen M1
contexts, whereas frozen S1/S2 selected their own contexts and used neural
epoch/optimisation procedures.

## Persistence and unexpected findings

- TimeTrack AR beats persistence on all4 mean-skill summaries; ARX does so only
  for CPU. Its throughput gain is -838.449742% (native MAE28.7398913 to
  269.709436), with mean skill falling from +0.334121 to -3.899126. This large
  deterioration is finite and verified, not a missing-value or display error.
  No cap, alpha/context retuning or post-test repair was introduced. The frozen
  log1p inverse allows large finite extrapolation; the result alone does not
  establish the detailed cause of the deterioration.
- fastStorage CPU/throughput and Rnd CPU/throughput have negative mean skill for
  both models. Rnd's positive throughput MacroMAE gain does not make its ARX
  mean skill positive. Rnd disk improves in MacroMAE but ARX mean skill is
  negative (+0.282755 AR to -0.147219 ARX).
- Materna T1 CPU changes from negative AR skill to positive ARX skill; its other
  resources and all T2/T3 resources have positive skill for both models.
- A positive MacroMAE gain need not improve mean relative skill (e.g.,
  fastStorage disk, Rnd CPU/disk, T2 throughput and T3 memory). MacroMAE averages
  absolute errors; mean skill first divides each cell by its own persistence
  error. Both endpoints are retained rather than replacing either with a new
  ratio, pooled statistic or significance test.

## Protocol and limitations

Original frozen M1-H64 selected context is shared by AR and ARX in each entity/fold. No contexts, seeds, cohorts, horizons, purging or legal origins were tuned. Five alphas (0.01, 0.1, 1, 10, 100) are scored strictly on inner validation by native-unit MAE after frozen inversion/nonnegative projection, equally over horizons; ties choose smaller alpha using the existing selector at fixed L. Each selected alpha is refit once on the frozen outer training partition. Targets use the frozen identity/log1p transforms and training-only median/IQR source scalers. Existing RidgeForecaster adds its own training-only lag-feature StandardScaler, identically for both forms. Direct multi-output horizon prediction, per-entity fits, deterministic Ridge and no artificial repetitions are used.

This is not a generic architecture-only causal comparison: the shared contexts were chosen by original M1, whereas original S1/S2 selected their own contexts; Ridge's alpha objective and linear regularisation differ from neural optimisation/epoch selection. The five-alpha grid, additive linear specification, frozen eligible populations and finite horizons limit generalisation. A single deterministic fit does not provide sampling uncertainty. Larger or smaller point gains do not establish statistical or practical importance. No thresholds, pooled cross-block statistic, significance tests, capacity retuning or additional experiments were introduced.

## Preservation and artifacts

Writes were confined to this new review_revision experiment and its explicitly
requested predecessor preservation snapshot. Full post-fit SHA256 membership/
content and Git refs pass for all283245 protected files, including original
scientific/manuscript trees, completed Stage18B1R and its predecessor, completed
Stage18B2 and benchmark/src. The entire3176-file blocked snapshot and retained
local scientific/recovery evidence also pass hash verification. HEAD remains
`f6936cd111d911e40ec2725a18fdfc53768d9ccf`, scientific parent/main/tag target
`fee20c316040c57b69ba12a193530c955b539771`; paper/jss and scientific tag objects
are unchanged. Tracked/staged diffs are empty. Manuscript modifications=0;
frozen artifacts modified=0; prior controls modified=0. Commit=no; push=no.

Configuration/source/plan hashes: provenance/experiment.json. Exact plans: plans/. Fit identities/scores/final metrics/hashes: attempts/, completions/, selections/. Final coefficient/intercept/feature-scaler arrays: models/. Native predictions/support: predictions/. Six-block audits: validation/full_audit_*.json. Detailed results: posthoc_results.csv and posthoc_metric_rows.parquet. Full protected baseline/after audit: provenance/. Output hashes: output_sha256_inventory.json.

Recovery authority, immutable predecessor manifest, three successor seals,
exact diffs, tests,35 individual recovery outcomes and valid-artifact byte
preservation evidence: `recovery/`. Independent final unit and result-table
audits: `validation/independent_final_units.json` and
`validation/independent_result_table.json`. The original blocked report is
`STAGE18B3_AR_ARX_BASELINE_REPORT.md`; this recovery report does not replace it.
No further experiment or manuscript revision was started. Quiet follow-up is
paused at terminal completion.

STAGE_18B3R_PASS
