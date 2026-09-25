# Prospective PatchTST Throughput Decision Criteria

Recorded before the first Neural-v2 PatchTST scientific fit on 2026-09-24
(Europe/Helsinki).

## Primary statistic

The PatchTST F1-throughput decision uses the prospectively frozen cross-model
reporting statistic: **ratio of macro-aggregated matched MAEs**. Positive means
lower F1 MAE than matched F0 MAE.

For every real lead, MAE is first computed for each
`machine x fold x seed x lead` run. Seeds are averaged separately for F0 and
F1 within each `machine x fold x lead` cell. The resulting machine-fold cells
receive equal weight, F0 and F1 MAEs are aggregated separately, and gain is:

`100 * (macro_F0_MAE - macro_F1_MAE) / macro_F0_MAE`.

The overall primary value is calculated from separately aggregated overall F0
and F1 macro MAEs; it is not an average of lead percentages.

Machine, fold, and seed signs use the same ratio-of-aggregated-MAEs principle
within each subgroup. A machine aggregates its folds, seeds, and leads; a fold
aggregates its machines, seeds, and leads; and a seed aggregates its machines,
folds, and leads. Balanced constituent cells receive equal weight.

## Fixed descriptive labels

- `BROAD_POSITIVE`: overall primary gain is positive; all 8 lead primary gains
  are positive; at least 5/7 machine aggregates are positive; at least 4/5 fold
  aggregates are positive; and all 3 seed aggregates are positive.
- `CONDITIONALLY_POSITIVE`: `BROAD_POSITIVE` is not met, but overall primary
  gain is positive; at least 4/8 lead primary gains are positive; at least 4/7
  machine aggregates are positive; at least 3/5 fold aggregates are positive;
  and at least 2/3 seed aggregates are positive.
- `BROAD_NEGATIVE`: overall primary gain is negative; at least 6/8 lead primary
  gains are negative; at least 5/7 machine aggregates are negative; at least
  4/5 fold aggregates are negative; and all 3 seed aggregates are negative.
- `NEUTRAL`: every other result pattern.

## Prospectively retained secondary summaries

The scientific report will also retain pooled-prediction MAE gain, mean and
median matched cell-relative MAE gain, positive-cell fraction, and detailed
machine/fold/seed heterogeneity. These are descriptive secondary summaries and
do not replace the primary decision statistic.

These criteria must not be altered after any PatchTST scientific result is
observed.
