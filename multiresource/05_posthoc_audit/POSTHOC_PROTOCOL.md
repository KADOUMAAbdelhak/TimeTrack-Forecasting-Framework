# Phase 3D Post-Hoc Heterogeneity Audit Protocol

Date: 2026-09-28 (Europe/Helsinki)

## Status and evidentiary boundary

All five Phase 3C outer folds have already been inspected scientifically.
Every Phase 3D analysis is exploratory and post-hoc. No Phase 3D result may be
presented as untouched confirmatory evidence. Any hypothesis generated here
requires fresh temporal or external data for confirmation.

This audit uses only frozen Phase 3C predictions, metrics, support records,
selections, loss histories, and training-side telemetry. It performs no model
training, refitting, tuning, prediction modification, or architecture design.
The accepted Phase 3C aggregation and decisions remain unchanged.

## Fixed comparisons and aggregation

The comparisons are `S2_vs_S1`, `M1_vs_S2`, and `M1_vs_S1`. Native-unit MAE
is calculated for matched observations. Seeds are averaged within each
machine-fold-resource-lead cell; machine-fold cells then receive equal weight.
Reference and candidate MAEs are aggregated separately before relative gain:

`gain_pct = 100 * (MAE_reference - MAE_candidate) / MAE_reference`.

Absolute benefit is `MAE_reference - MAE_candidate` in native target units.
Positive values mean that the candidate helped. Native errors are never
averaged across resources.

## Fixed machine labels

`STABLE_POSITIVE_MACHINE` requires overall machine gain greater than zero,
positive folds at least 4/5, and positive leads at least 6/8.

`PARTIAL_POSITIVE_MACHINE` requires overall gain greater than zero, positive
folds at least 3/5, and positive leads at least 4/8, without satisfying the
stable rule. Everything else is `UNSTABLE_OR_NEGATIVE`. These are exploratory
descriptions, not confirmatory labels.

## Origin-time regime descriptors

All regime descriptors use a fixed trailing diagnostic window of 32 canonical
observations ending at the forecast origin. No value after the origin is used.
For each resource the audit records last native and transformed values and the
transformed trailing mean, median, standard deviation, IQR, least-squares
slope, mean absolute first difference, maximum, and minimum. Throughput and
disk-write additionally receive native zero fraction and spike ratio
`max / median` when the median is positive. The audit also records trailing
CPU-throughput Spearman correlation. Transforms are identity for CPU and
memory and `log1p` for throughput and disk-write.

The controlled regime list is fixed before analysis:

- CPU target: CPU level, CPU volatility, throughput level, throughput
  volatility, CPU-throughput correlation.
- Throughput target: throughput level, throughput volatility, CPU level, CPU
  volatility.
- Memory target: memory level, memory volatility, memory mean absolute change,
  CPU level, throughput level.
- Disk-write target: disk-write level, disk-write volatility, CPU level,
  throughput level.

No descriptor combinations or outcome-guided subgroup search are permitted.

## Training-derived bins

For each machine, fold, and descriptor, thresholds are derived only from that
fold's legal outer-training origins. The 33rd and 67th percentiles define:

- `LOW`: value less than or equal to the 33rd percentile;
- `MID`: above the 33rd and at or below the 67th percentile;
- `HIGH`: above the 67th percentile.

Missing correlations remain unbinned. Test gains have no role in threshold
selection. Threshold values and training counts are persisted.

## Dependency analysis

Training-region transformed level and first-difference Spearman dependencies
are fixed as CPU-throughput, throughput-CPU, memory-CPU,
memory-throughput, disk-write-CPU, and disk-write-throughput. Dependency
strength is compared descriptively with frozen outer-test S2-versus-S1 gain.
Across the 35 machine-fold cells, absolute dependency values are divided into
descriptive quartiles; no causal interpretation is allowed.

## Loss-share and selected-context analyses

M1 selected-inner-epoch validation loss share and normalized resource loss are
matched by resource, machine, fold, and seed to frozen M1-versus-S2 test gain.
Spearman relationships and descriptive quartile groups are reported without
causal claims. Existing selected contexts are split only into equality versus
inequality: S2 context equals S1 context, and M1 context equals the target's S2
context.

## Post-hoc bootstrap uncertainty

Exactly 10,000 paired hierarchical bootstrap replicates use deterministic seed
`20260928`. For each comparison and resource, seven machines are sampled with
replacement; within each sampled machine, five folds are sampled with
replacement. Paired reference/candidate cell MAEs and all applicable leads are
carried together. Each replicate separately macro-averages reference and
candidate MAE before calculating gain. Lead-specific and overall 2.5th and
97.5th percentiles are reported as **POST-HOC BOOTSTRAP UNCERTAINTY
INTERVALS**, not confirmatory confidence intervals. They create no decision
labels.

## Benefit concentration

For each comparison and resource, positive native absolute improvements are
sorted from largest to smallest. The audit reports the fraction of all
machine-fold-lead cells needed to accumulate 50% and 80% of total positive
improvement. This is descriptive and does not override the stability rules.

## Exploratory pattern rule

A positive controlled regime pattern is `STABLE_EXPLORATORY_PATTERN` only if:

- its gain is positive in at least 4/5 folds;
- its gain is positive in at least 5/7 represented machines;
- at least two adjacent leads have positive gain;
- it contains at least 20% of relevant matched predictions; and
- both relative gain and native absolute MAE benefit are positive.

It is `PARTIAL_EXPLORATORY_PATTERN` only if it does not satisfy the stable rule
but has positive gain in at least 3/5 folds and 3/7 machines, at least two
adjacent positive leads, at least 10% coverage, and positive relative and
absolute effects. Everything else is `UNSTABLE_PATTERN`. All labels remain
exploratory.

## Final research-direction mapping

- `NO_STABLE_CONTEXT_BENEFIT`: no meaningful positive S2-versus-S1 pattern
  reaches `STABLE_EXPLORATORY_PATTERN` for any resource.
- `TARGET_SPECIFIC_CONTEXT_HYPOTHESIS`: stable benefit exists but is specific
  to one or more targets rather than broadly shared.
- `REGIME_CONDITIONAL_CONTEXT_HYPOTHESIS`: stable benefit is confined to one
  or more pre-origin regimes.
- `SHARED_REPRESENTATION_MECHANISM_HYPOTHESIS`: stable S2 benefit exists in
  specific pockets, M1 systematically degrades those same pockets, and a
  specific sharing-failure hypothesis is supported.
- `INCONCLUSIVE_POSTHOC_HETEROGENEITY`: positive pockets exist but fail the
  required stability or coverage criteria.

The least novel applicable outcome is chosen. No architecture is selected or
implemented.
