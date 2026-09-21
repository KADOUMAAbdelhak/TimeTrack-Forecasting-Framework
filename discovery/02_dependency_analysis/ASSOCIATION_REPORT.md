# Phase 1B-1 Lagged Association Report

This report describes association only. It contains no Ridge results,
forecasting claims, dependency classifications, or causal claims. In
particular, causality has not been established.

## Method and interpretation boundaries

- The comparison is `x[t-lag]` against `y[t+lead]`.
- Lag 0 is contemporaneous origin-time context; positive lags are historical
  predictor observations.
- Leads and lags are the frozen grids in `PROTOCOL.md`.
- All train/validation/test assignments use the target-time-purged split.
- Correlations are computed within canonical temporal segments. The summary
  coefficients are deterministic sample-weighted averages of eligible
  segment coefficients; segments with fewer than 30 complete pairs or a
  constant variable remain undefined.
- The supporting lag is selected only from validation weighted Spearman.
  Held-out test association is evaluated at that unchanged selected lag.
- Memory and used disk are reported both as future levels and as cumulative
  origin-to-future changes. Level-like predictors in change mode use only the
  historical difference `x[t-l] - x[t-l-1]`.
- Mutual information is auxiliary. It is evaluated at lag 0 and one nonzero
  validation-selected lag, with deterministic capping at 20,000 observations.

Lag 0 and positive historical lags should not be conflated. A large held-out
coefficient at a validation-selected positive lag is still descriptive
association and does not demonstrate incremental predictive value beyond the
target's own history.

## Execution summary

- Runtime: 544.6 seconds
- Candidate relationships: 434
- Candidate/target/mode combinations: 616
- Split-level association cells: 133056
- Segment-level cells: 437778
- Validation-selected relationships: 4928
- Mutual-information evaluations: 29568
- Segment crossings: 0
- Test-based lag selections: 0

## Strongest descriptive resource directions

The largest median absolute held-out associations across the frozen
same-machine/global directions were:

- CPU <- throughput (native): median absolute test Spearman 0.216
- disk <- memory (level): median absolute test Spearman 0.213
- throughput <- CPU (native): median absolute test Spearman 0.178
- memory <- throughput (level): median absolute test Spearman 0.135
- memory <- CPU (level): median absolute test Spearman 0.133
- CPU <- memory (native): median absolute test Spearman 0.131
- memory <- disk (level): median absolute test Spearman 0.130
- throughput <- memory (native): median absolute test Spearman 0.121
- memory <- CPU (change): median absolute test Spearman 0.111
- memory <- throughput (change): median absolute test Spearman 0.073

## Level and change contrast

The strongest change-mode directions were:

- memory <- CPU: median absolute test Spearman 0.111
- memory <- throughput: median absolute test Spearman 0.073
- memory <- disk: median absolute test Spearman 0.040
- disk <- throughput: median absolute test Spearman 0.029
- disk <- CPU: median absolute test Spearman 0.025
- disk <- memory: median absolute test Spearman 0.016

Level coefficients can reflect persistence and shared trends. Change-mode
coefficients ask the narrower question of whether historical predictor
information aligns with cumulative target movement from origin to lead.

## Cross-machine and shared context

Median absolute held-out cross-machine coefficients:

- CPU native: 0.081
- memory level: 0.127
- memory change: 0.011
- throughput native: 0.101

Pairwise and leave-one-machine-out comparison:

- CPU (native), leave_one_machine_out: median absolute test Spearman 0.187
- CPU (native), pairwise_machine: median absolute test Spearman 0.081
- memory (change), leave_one_machine_out: median absolute test Spearman 0.016
- memory (change), pairwise_machine: median absolute test Spearman 0.011
- memory (level), leave_one_machine_out: median absolute test Spearman 0.101
- memory (level), pairwise_machine: median absolute test Spearman 0.127
- throughput (native), leave_one_machine_out: median absolute test Spearman 0.160
- throughput (native), pairwise_machine: median absolute test Spearman 0.101

## Global RTT and jitter context

- RTT median absolute held-out association:
  0.017
- Jitter median absolute held-out association:
  0.026

## Lead dependence

Median of direction-level median absolute held-out Spearman by lead:
1: 0.047, 2: 0.051, 4: 0.053, 8: 0.054, 16: 0.055, 32: 0.055, 64: 0.042, 128: 0.053.

## Association Findings Before Predictive Screening

1. **Which directional resource pairs show the strongest held-out lagged
   associations?** CPU <- throughput is strongest in aggregate, followed by
   disk <- memory level, throughput <- CPU, and memory <- throughput level.
   Signal-specific and lead-specific results remain in the machine-readable
   outputs.
2. **Which relationships survive change analysis?** The change-mode list above
   shows that memory <- CPU retains the clearest aggregate coefficient
   (0.111); memory <- throughput is smaller, and disk change associations are
   weak in aggregate.
3. **Are CPU cross-machine associations strong?** Not broadly: the median
   absolute held-out coefficient is 0.081, although individual pairs and
   leads are heterogeneous.
4. **Are memory cross-machine associations strong?** Level associations are
   noticeable at 0.127, but the change result is only 0.011. The cross-machine
   pattern therefore does not remain strong after removing the future-level
   representation.
5. **Are throughput cross-machine associations strong?** They are modest in
   aggregate at 0.101, with pair-specific detail retained by lead.
6. **Are pair-specific machine associations stronger than leave-one-machine-out
   context?** Usually not in aggregate: leave-one-machine-out context is
   stronger for CPU and throughput and slightly stronger for memory change.
   Pairwise memory level is the exception, exceeding its common context.
7. **Do RTT or jitter show notable lagged associations?** No broad pattern is
   apparent: their median absolute held-out values are 0.017 and 0.026,
   respectively.
8. **How quickly do associations decay with future lead?** The aggregate
   median does not decay monotonically: it remains near 0.05 through lead 32,
   dips at lead 64, and rebounds slightly at lead 128. No forecast horizon is
   selected from this pattern.
9. **Which relationships are worth testing in the already-predeclared Ridge
   screen?** CPU <-> throughput, disk <- memory level, memory <- CPU change,
   and memory <- throughput change are the clearest discussion priorities.
   This prioritization does not remove any candidate: the Ridge phase must
   evaluate the complete frozen candidate set and compare every augmentation
   with the own-history baseline.
