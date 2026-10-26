# Stage 18B3 execution handoff

POST-HOC SENSITIVITY CONTROL. Writes are confined to this namespace. Frozen
drivers are imported as readers only; their writers, main functions, neural
training and context-selection procedures are never called.

AR and ARX share original frozen M1-H64 context per entity/fold. Five Ridge
alphas are selected per formulation/target on inner native-unit MAE after
frozen inverse transforms/projection, equally over horizons. Source scalers
are rebuilt from the exact frozen training support and checked against original
inner/final records. Existing RidgeForecaster's lag-column StandardScaler is
training-only. No artificial seeds or cross-VM pooling. Each selected alpha is
refit once with one outer-test predict call. Expected: 36,400 inner + 7,280 final
fits, 7,280 alpha selections, 37,240 metric rows.

Run synthetic checks before prepare; prepare records protected SHA256 baseline,
all six block plans and a source/config/plan seal. Do not patch sealed sources
or config during execution. Use the legacy environment with bytecode disabled.

```
PYTHONDONTWRITEBYTECODE=1 old_fgcs_rejected/.venv_legacy/bin/python -B review_revision/experiments/ar_arx_baseline/test_linear_control.py
PYTHONDONTWRITEBYTECODE=1 old_fgcs_rejected/.venv_legacy/bin/python -B review_revision/experiments/ar_arx_baseline/run_linear_control.py prepare
PYTHONDONTWRITEBYTECODE=1 old_fgcs_rejected/.venv_legacy/bin/python -B review_revision/experiments/ar_arx_baseline/run_linear_control.py run --workers 4
```

Never duplicate an active runner. The advisory runtime lock enforces this.
Inspect execution.log, progress/, STOP.json, failures/, attempts/ and completions/.
An attempt without valid completion or any failure requires stop and explicit
recovery approval; no silent retry. Successful exact completions are hash checked
on resume. Each block receives an independent support/scaler/context/selection/
artifact/numerical/identity audit. After all fits, full preservation is checked,
then analysis runs. Its report is a draft, not terminal PASS: audit the 24 rows,
skill semantics, frozen directional/magnitude comparisons and central conclusion,
finish the report and refresh output inventory without overwriting the audit.

No manuscript revision, additional experiments, commits or pushes. The user
approved automatic follow-up. Heartbeat continue-stage-18b3-ar-arx-baseline was
created and is now PAUSED after the persistence-verification failure. See
STAGE18B3_AR_ARX_BASELINE_REPORT.md and STOP.json; do not resume without an
explicit recovery decision. Original sealed source/config/plans are unchanged.

## Authorised Stage18B3R recovery (current)

The user explicitly authorised correcting persistence-reference arithmetic/error
handling and one same-identity recovery fit/test prediction for each of the35
failed finals if complete artifacts were absent. All35 had no model/prediction
files. The entire blocked run (3176files) is copied/hash-verified at the sibling
ar_arx_baseline_predecessor_stage18b3; never change that snapshot. Original
STOP.json, failures/, attempts/, provenance/experiment.json and blocked report
remain immutable historical evidence. Config is byte-identical; all plans and
the1400 valid inner completions/280 existing selections are preserved.

recovery/successor.json seals float64 TimeTrack persistence-reference MAE and
pickle-safe worker errors. Original relative-skill denominator arithmetic is
unchanged.13checks pass (8original+5recovery), including1120 exact TT reference
values, reproduction of35 float32 blockers and all5external block checks.

All35 recoveries completed. A post-fit checker scalar-promotion defect was then
found: NumPy2 Pythonfloat/float32 division rounded the recomputed skill. A checker-
only float64 numerator correction is separately sealed by
recovery/successor_audit_fix.json. A read-only test verifies all2240 TT metric
rows exactly without fitting/inference or metric changes. Prior checker code,
seal, test, STOP and log are hash-preserved under recovery/audit_checker_predecessor.
The TT full audit passes (1400inner/280final/2240metrics/0duplicates). No completed
TT fit/test is repeated when remaining blocks resume.

Current adapter SHA256:20823a79400ce20400ad1a79232dceeb9d044e6a94fe4d18d5f9b85b07459ab3.
Scientific config SHA256:ae97a89cb1e8034890256fa8f21ea242fa729fcb725be43088be7552e1309626.
Current launch:recovery/audit_fix_launch.json; verify live process rather than PID.
Log:recovery/resumed_execution.log. Historical recovery/STOP.json is resolved
only through its exact hash in the new seal; recovery/current_STOP.json or new
recovery/failures/ are CURRENT blockers. Never retry new interrupted attempts.
Use unresolved_failures(), successor hashes and recovery/authorisation.json.
Never patch code/config/plans while running. Preserve all historical evidence.

Expected final valid units:36400inner+7280final=43680,37240metric rows,7280 final
models/predictions/selections. Historical extra failed final fits/test calls=35,
so actual total executed fits=43715 and final test calls=7315 if complete.
New recovery execution performs35000 remaining inner+7280 final fits, reusing
1400valid inner records.35 authorised recovery finals are included in7280valid
finals, not additional identities. One valid completion per scientific identity.

Automatic follow-up was restored under the user's approval; keep quiet while
healthy, pause on true terminal completion or current blocker. Finish separate
STAGE18B3R_AR_ARX_RECOVERY_REPORT.md after all-six-block audits and full283245-file
protected-tree audit. Do not overwrite the blocked report. Report all35 historical
failures as resolved, not erased, and distinguish valid units from actual fits.
Refresh output inventory after report-only edits. No extra experiments or
manuscript edits; commit=no,push=no.

## Terminal completion

STAGE_18B3R_PASS. All6 block audits and the283245 protected-file SHA256/ref audit
passed. Valid completions36400inner/7280final;37240metrics;7280 models,
predictions and selections;0duplicates/current failures/nonfinite primary values.
All35 historical failed finals are recovered, not deleted:0artifactreuse,
35authorised same-identity reruns;1400 valid original inner records preserved.
Actualfits including historical failures43715; finaltestcalls7315. No other
completed unit was refitted. All27720 valid files recorded before the last
checker correction remain identical.

The final audit-only reduction-order correction uses the independently verified
stored MAE for its derived skill. Scientific metrics and strict tolerances are
unchanged. Final seal:recovery/successor_audit_reduction_fix.json; final runner
SHA256:3a256e9a8b7835a15fbce87bfdcc5783d8ed61359016724f59324391e7f82565.
Historicalrecovery/current_STOP.json is hash-resolved by that seal; any later
STOP would remain a blocker. Exact diffs and all prior checker evidence remain.
Original13tests rerunPASS plus2read-only audit regression checks=15checksPASS.

Final human-reviewed report:STAGE18B3R_AR_ARX_RECOVERY_REPORT.md.
Independent unit/result audits:validation/independent_final_units.json and
validation/independent_result_table.json. Handoff:recovery/final_handoff.json.
completion_summary.json is terminalPASS, not draft. Output inventory is refreshed
after final report/metadata edits. The original blocked report is unchanged.
Heartbeatcontinue-stage-18b3-ar-arx-baseline isPAUSED. Do not restart any fitting
or begin additional experiments/manuscript work. Manuscript/frozen/prior-control
modifications=0;commit=no,push=no.
