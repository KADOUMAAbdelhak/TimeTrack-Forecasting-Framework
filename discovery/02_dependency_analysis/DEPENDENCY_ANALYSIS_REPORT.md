# Phase 1B Dependency Analysis Report

This report synthesizes the frozen descriptive association screen and the
already-computed incremental Ridge screen. No model was rerun during
classification, no threshold was changed, and no candidate was selected using
test performance.

## Evidence layers

**Descriptive association** compares `x[t-lag]` with `y[t+lead]` within
canonical temporal segments. Supporting lags were selected on validation and
then evaluated on held-out test data. Association does not establish
causality.

**Incremental held-out prediction** compares target own-history Ridge with the
same history plus the candidate's complete frozen predictor-history vector.
Both models use identical candidate-specific rows, and scaling/model fitting
use training data only.

**Classification** applies the predeclared STRONG, MODERATE, WEAK, and
UNSUPPORTED criteria literally.

## Classification operationalization

Immediate lead neighbors are defined by `[1,2,4,8,16,32,64,128]`.
Neighboring support requires at least 1% test MAE gain for the exact same
target, predictor, candidate family, and analysis mode at an immediate lead.

Multi-machine support requires the focal experiment to meet all five MODERATE
primary conditions and the same direction, candidate family, normalized
candidate concept, mode, and lead to meet them on at least two distinct target
machines. Candidate concepts distinguish disk used/read/write, each exact
RTT/jitter signal, leave-one-machine-out mean versus median, and pairwise
same-resource telemetry. Unrelated predictors are not pooled.

For the otherwise qualitative WEAK rule, positive incremental evidence means
at least one positive test MAE gain, RMSE gain, or R² delta. Association
evidence means absolute held-out Spearman at least 0.10, matching the frozen
MODERATE support threshold. Experiments satisfying neither are UNSUPPORTED.

## Test-segment limitation

The segment table contains 4,928 experiment IDs and 4,928 rows: every
experiment has exactly one eligible test segment. The frozen STRONG rule
requires at least two eligible test segments. It was not modified, so no
experiment can satisfy STRONG. Experiments otherwise meeting all STRONG
criteria are flagged `strong_numeric_but_segment_ineligible` and record
`insufficient_test_segments_for_strong`.

## Classification totals

- STRONG: 0
- MODERATE: 163
- WEAK: 3025
- UNSUPPORTED: 1740
- Numeric-STRONG but segment-ineligible: 38

## Same-machine cross-resource synthesis

Direction-level results include all seven machines and all frozen leads rather
than ranking a single favorable experiment. Leading aggregate directions are:

- CPU <- throughput (native): median MAE gain 0.592%, positive fraction 0.589, MODERATE 15
- disk <- memory (change): median MAE gain -0.013%, positive fraction 0.321, MODERATE 0
- memory <- RTT (change): median MAE gain -0.030%, positive fraction 0.308, MODERATE 0
- memory <- RTT (level): median MAE gain -0.030%, positive fraction 0.304, MODERATE 0
- CPU <- RTT (native): median MAE gain -0.033%, positive fraction 0.388, MODERATE 0
- CPU <- jitter (native): median MAE gain -0.041%, positive fraction 0.375, MODERATE 0
- memory <- jitter (level): median MAE gain -0.043%, positive fraction 0.304, MODERATE 0
- memory <- jitter (change): median MAE gain -0.043%, positive fraction 0.304, MODERATE 0
- memory <- disk (change): median MAE gain -0.049%, positive fraction 0.286, MODERATE 6
- CPU <- disk (native): median MAE gain -0.062%, positive fraction 0.458, MODERATE 23

The complete direction/lead/mode distributions are in
`outputs/resource_direction_predictive_summary.csv`.

All requested directions:

- CPU <- RTT (native): median gain -0.033%, positive fraction 0.388, positive machines 7/7, classifications 0/0/106/118 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- CPU <- disk (native): median gain -0.062%, positive fraction 0.458, positive machines 6/7, classifications 0/23/99/46 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- CPU <- jitter (native): median gain -0.041%, positive fraction 0.375, positive machines 5/7, classifications 0/0/24/32 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- CPU <- memory (native): median gain -0.702%, positive fraction 0.339, positive machines 5/7, classifications 0/3/45/8 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- CPU <- throughput (native): median gain 0.592%, positive fraction 0.589, positive machines 6/7, classifications 0/15/35/6 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- disk <- CPU (change): median gain -0.871%, positive fraction 0.286, positive machines 4/7, classifications 0/3/41/12 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- disk <- CPU (level): median gain -1.371%, positive fraction 0.214, positive machines 3/7, classifications 0/4/42/10 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- disk <- RTT (change): median gain -0.107%, positive fraction 0.232, positive machines 6/7, classifications 0/0/112/112 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- disk <- RTT (level): median gain -0.104%, positive fraction 0.228, positive machines 6/7, classifications 0/0/110/114 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- disk <- jitter (change): median gain -0.229%, positive fraction 0.268, positive machines 5/7, classifications 0/0/30/26 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- disk <- jitter (level): median gain -0.229%, positive fraction 0.250, positive machines 4/7, classifications 0/0/35/21 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- disk <- memory (change): median gain -0.013%, positive fraction 0.321, positive machines 6/7, classifications 0/0/38/18 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- disk <- memory (level): median gain -2.284%, positive fraction 0.268, positive machines 3/7, classifications 0/0/56/0 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- disk <- throughput (change): median gain -0.205%, positive fraction 0.232, positive machines 5/7, classifications 0/0/30/26 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- disk <- throughput (level): median gain -0.337%, positive fraction 0.232, positive machines 5/7, classifications 0/2/33/21 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- memory <- CPU (change): median gain -0.207%, positive fraction 0.375, positive machines 4/7, classifications 0/2/37/17 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- memory <- CPU (level): median gain -0.206%, positive fraction 0.375, positive machines 4/7, classifications 0/0/50/6 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- memory <- RTT (change): median gain -0.030%, positive fraction 0.308, positive machines 7/7, classifications 0/0/98/126 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- memory <- RTT (level): median gain -0.030%, positive fraction 0.304, positive machines 7/7, classifications 0/0/97/127 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- memory <- disk (change): median gain -0.049%, positive fraction 0.286, positive machines 7/7, classifications 0/6/75/87 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- memory <- disk (level): median gain -0.225%, positive fraction 0.274, positive machines 5/7, classifications 0/8/114/46 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- memory <- jitter (change): median gain -0.043%, positive fraction 0.304, positive machines 4/7, classifications 0/0/22/34 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- memory <- jitter (level): median gain -0.043%, positive fraction 0.304, positive machines 4/7, classifications 0/0/27/29 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- memory <- throughput (change): median gain -0.109%, positive fraction 0.268, positive machines 4/7, classifications 0/2/40/14 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- memory <- throughput (level): median gain -0.109%, positive fraction 0.268, positive machines 4/7, classifications 0/4/44/8 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- throughput <- CPU (native): median gain -0.649%, positive fraction 0.411, positive machines 5/7, classifications 0/6/43/7 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- throughput <- RTT (native): median gain -0.062%, positive fraction 0.397, positive machines 7/7, classifications 0/0/115/109 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- throughput <- disk (native): median gain -0.261%, positive fraction 0.387, positive machines 6/7, classifications 0/6/106/56 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- throughput <- jitter (native): median gain -0.113%, positive fraction 0.339, positive machines 4/7, classifications 0/0/25/31 (STRONG/MODERATE/WEAK/UNSUPPORTED)
- throughput <- memory (native): median gain -1.521%, positive fraction 0.446, positive machines 4/7, classifications 0/1/49/6 (STRONG/MODERATE/WEAK/UNSUPPORTED)

## Cross-machine synthesis

- CPU (native), leave_one_machine_out_mean: median gain -0.144%, positive fraction 0.464, MODERATE 7
- CPU (native), leave_one_machine_out_median: median gain 0.471%, positive fraction 0.732, MODERATE 12
- CPU (native), pairwise_machine: median gain -0.030%, positive fraction 0.464, MODERATE 16
- memory (change), leave_one_machine_out_mean: median gain -0.013%, positive fraction 0.393, MODERATE 0
- memory (change), leave_one_machine_out_median: median gain -0.019%, positive fraction 0.304, MODERATE 0
- memory (change), pairwise_machine: median gain -0.016%, positive fraction 0.310, MODERATE 0
- memory (level), leave_one_machine_out_mean: median gain -1.172%, positive fraction 0.250, MODERATE 3
- memory (level), leave_one_machine_out_median: median gain -1.578%, positive fraction 0.143, MODERATE 0
- memory (level), pairwise_machine: median gain -0.088%, positive fraction 0.378, MODERATE 15
- throughput (native), leave_one_machine_out_mean: median gain -0.011%, positive fraction 0.464, MODERATE 6
- throughput (native), leave_one_machine_out_median: median gain -0.018%, positive fraction 0.482, MODERATE 10
- throughput (native), pairwise_machine: median gain 0.028%, positive fraction 0.506, MODERATE 9

These summaries compare pairwise predictors against leave-one-machine-out mean
and median contexts after accounting for each target's own history.

- CPU (native): leave_one_machine_out_median has the highest median gain (0.471%) among the three context forms.
- memory (change): leave_one_machine_out_mean has the highest median gain (-0.013%) among the three context forms.
- memory (level): pairwise_machine has the highest median gain (-0.088%) among the three context forms.
- throughput (native): pairwise_machine has the highest median gain (0.028%) among the three context forms.

## Level versus change synthesis

- Memory level: median gain -0.086%,
  positive fraction 0.313,
  MODERATE 30.
- Memory change: median gain -0.025%,
  positive fraction 0.311,
  MODERATE 10.
- Disk level: median gain -0.193%,
  positive fraction 0.234,
  MODERATE 6.
- Disk change: median gain -0.131%,
  positive fraction 0.254,
  MODERATE 3.

The change results are the relevant check against apparent dependencies driven
only by persistent future levels.

## Lead dependence

- lead 32: median gain -0.035%, positive fraction 0.390, MODERATE 19
- lead 64: median gain -0.047%, positive fraction 0.356, MODERATE 9
- lead 16: median gain -0.047%, positive fraction 0.378, MODERATE 15
- lead 8: median gain -0.049%, positive fraction 0.356, MODERATE 27
- lead 128: median gain -0.060%, positive fraction 0.343, MODERATE 11
- lead 4: median gain -0.067%, positive fraction 0.378, MODERATE 26
- lead 2: median gain -0.084%, positive fraction 0.338, MODERATE 30
- lead 1: median gain -0.103%, positive fraction 0.307, MODERATE 26

“Best augmentation” rows and curves use validation MAE improvement for
candidate selection and report test results only after that selection.

## Limitations

- Only one eligible test segment is available, preventing STRONG classification
  under the frozen rule and limiting independent temporal replication.
- Ridge tests incremental linear information only; absent gain does not rule
  out every nonlinear relationship.
- Multiple candidate experiments are screened, so isolated favorable rows are
  less persuasive than direction-level and multi-machine consistency.
- Sparse packet-event channels were excluded from the dense predictive screen.
- Units and missingness differ across telemetry families; matched-row
  comparisons prevent sample-set artifacts but do not remove measurement
  limitations.

## What the Old Study Missed

The archived formulation forecast CPU, memory, and disk separately, relied
primarily on each metric's own history, scored one-step results, and applied
post-hoc reconciliation. The new evidence tests whether other resources,
machines, shared context, and longer leads add information beyond that same
own-history baseline. It also separates persistent levels from
origin-to-future changes and distinguishes pair-specific machine telemetry from
leave-one-machine-out common context. Where MODERATE evidence is distributed
across directions or machines, the data justify investigating formulations
beyond independent per-metric prediction. Where evidence is weak,
level-specific, or isolated, the old formulation should not be replaced on
association alone.

## Evidence for the New Research Direction

1. **Does cross-resource information improve future CPU prediction beyond CPU
   history alone?** The same-machine/global CPU set has median gain
   -0.038%, positive fraction
   0.423, and
   41 MODERATE rows. Evidence is
   heterogeneous rather than broadly positive; CPU <- throughput is the only
   same-machine direction with positive aggregate median gain.
2. **Does it improve future memory prediction beyond memory history?** Memory
   same-machine/global level has median gain
   -0.058% with
   12 MODERATE rows; change has
   -0.043% with
   10 MODERATE rows. This is
   isolated support, not broad median improvement.
3. **Does it improve future disk prediction beyond disk history?** Disk level
   has same-machine/global median gain
   -0.193% and
   6 MODERATE rows; disk change
   has -0.131% and
   3 MODERATE rows. Broad
   improvement is not supported.
4. **Does network throughput provide useful predictive context?** Directions
   using throughput have native-target median gain
   0.592% and
   15 MODERATE rows, led by
   CPU <- throughput. Level/change target medians are
   -0.274% and
   -0.170%, so support is
   target-specific.
5. **Do RTT/jitter provide useful predictive context?** Broadly no: RTT has
   median gain -0.049% and
   0 MODERATE rows; jitter has
   -0.099% and
   0 MODERATE rows.
6. **Are cross-machine signals useful after accounting for each machine's own
   history?** The pairwise/common-context summary above gives the held-out
   comparison. Cross-machine investigation is
   supported for investigation.
7. **Which directional relationships are strongest?** The leading
   direction-level median gain is CPU <- throughput at
   0.592%. All other same-machine/global
   direction-mode medians are negative, even where isolated MODERATE rows
   exist.
8. **At which future leads does cross-signal information remain useful?** The
   broadest median gains occur at leads 32, 64, 16; this is a screening
   result, not a final horizon decision.
9. **Do useful dependencies survive first-difference/change analysis?**
   Partially: some change-mode experiments reach MODERATE, but memory and disk change medians remain negative.
10. **Are effects consistent across machines or concentrated on a few
    machines?** There are 71 rows with frozen
    multi-machine support, concentrated mainly in CPU directions; memory and
    disk change have no broad multi-machine support. The evidence is therefore
    mixed and often concentrated rather than universally consistent.
11. **Is there empirical evidence supporting a JOINT MULTI-METRIC forecaster
    rather than independent per-metric models?**
    Partially supported for investigation by replicated MODERATE cross-resource evidence, especially CPU <- throughput/CPU <- disk, while most direction medians are nonpositive.
12. **Is there empirical evidence supporting a JOINT MULTI-MACHINE
    forecaster?**
    Partially supported for investigation by cross-machine/common-context MODERATE evidence.
13. **Is there evidence supporting both jointly?**
    Partially supported: both evidence types occur, but the one-test-segment limitation prevents STRONG classification.
14. **Which metrics should probably be targets?** CPU, used memory, used disk,
    and validated bidirectional throughput remain defensible continuous
    targets; memory and disk should retain both level and change evaluation.
15. **Which metrics should probably be context/exogenous inputs rather than
    targets?** Global RTT/jitter, disk read/write activity, and transparent
    leave-one-machine-out summaries are context candidates rather than primary
    targets in this screen.
16. **Which signals should currently be excluded because of quality/sparsity
    problems?** Sparse packet drop/error channels should remain event context,
    not dense targets; per-core CPU remains outside the compact panel; heavily
    zero-dominated disk-activity channels require caution.
17. **What are the strongest candidate forecast leads for the NEXT modeling
    phase?** No lead has positive broad median gain. Leads 32, 64, 16 are the
    least adverse by broad median and therefore cautious investigation
    priorities, not finalized horizons; lead-specific MODERATE counts should
    also be retained.
