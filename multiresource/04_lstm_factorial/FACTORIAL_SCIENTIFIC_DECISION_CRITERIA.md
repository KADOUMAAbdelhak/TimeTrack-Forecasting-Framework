# Phase 3C Prospective Scientific Decision Criteria

Date frozen: 2026-09-27 (Europe/Helsinki)

This record precedes the first scientific S1/S2/M1 fit. It applies unchanged to
the three matched comparisons: S2 versus S1, M1 versus S2, and M1 versus S1.
These are descriptive consistency labels, not statistical-significance tests.

## Primary statistic and sign summaries

For each resource and comparison, the primary statistic is the ratio of matched
macro MAEs:

```text
gain = 100 * (MacroMAE_baseline - MacroMAE_candidate) / MacroMAE_baseline
```

Seeds are first averaged within machine-fold-resource-lead cells, machine-fold
cells then receive equal weight, and formulation macro MAEs are computed
separately before taking their ratio.

- Overall resource gain uses the ratio after equally averaging the eight lead
  macro MAEs within each formulation.
- A lead is positive when its primary macro-MAE gain is greater than zero.
- A machine sign uses the ratio of formulation MAEs equally averaged over that
  machine's folds, seeds, and leads.
- A fold sign uses the ratio equally averaged over machines, seeds, and leads.
- A seed sign uses the ratio equally averaged over machines, folds, and leads.
- Exact zero is not positive.

## Resource-level classifications

`BROAD_POSITIVE` requires all of:

- overall primary gain at least +1.0%;
- at least 6/8 positive leads;
- at least 5/7 positive machines;
- at least 4/5 positive folds;
- at least 2/3 positive seed-level aggregate signs.

`CONDITIONALLY_POSITIVE` requires all of:

- overall primary gain greater than zero;
- at least 4/8 positive leads;
- at least 3/7 positive machines;
- at least 3/5 positive folds;
- at least 2/3 positive seed-level aggregate signs;
- and the result is not `BROAD_POSITIVE`.

`BROAD_NEGATIVE` requires all of:

- overall primary gain at most -1.0%;
- at most 2/8 positive leads;
- at most 2/7 positive machines;
- at most 1/5 positive folds;
- at most 1/3 positive seed-level aggregate signs.

Everything else is `NEUTRAL_OR_MIXED`.

## Global cross-resource-input decision

Apply these rules to the four S2-versus-S1 resource labels and overall gains.

- `CROSS_RESOURCE_INPUT_SUPPORTED`: at least three resources are
  `BROAD_POSITIVE` or `CONDITIONALLY_POSITIVE`, the equal-resource mean primary
  gain is positive, and no more than one resource is `BROAD_NEGATIVE`.
- `CROSS_RESOURCE_INPUT_NOT_SUPPORTED`: at most one resource is positive and
  the equal-resource mean primary gain is non-positive, or at least two
  resources are `BROAD_NEGATIVE`.
- `CROSS_RESOURCE_INPUT_MIXED`: every other heterogeneous result.

If supported and not-supported conditions could both apply, the conservative
`CROSS_RESOURCE_INPUT_NOT_SUPPORTED` label takes precedence.

## Global shared-representation decision

Apply these rules to M1 versus S2. A resource is "positive" when classified
`BROAD_POSITIVE` or `CONDITIONALLY_POSITIVE`. A materially negative resource is
one classified `BROAD_NEGATIVE`; a strong trade-off additionally means at least
one resource has overall gain at least +1.0% while at least two resources have
overall gains at most -1.0%.

Precedence is conservative, in this order:

1. `SHARED_REPRESENTATION_NEGATIVE_TRANSFER` if at least one resource is
   positive while at least two are materially negative, or a strong trade-off
   is present.
2. `SHARED_REPRESENTATION_NOT_SUPPORTED` if at most one resource is positive
   and the equal-resource mean primary gain is non-positive.
3. `SHARED_REPRESENTATION_SUPPORTED` if at least three resources are positive,
   the equal-resource mean primary gain is positive, and no resource is
   `BROAD_NEGATIVE`.
4. `SHARED_REPRESENTATION_CONDITIONALLY_SUPPORTED` if the equal-resource mean
   primary gain is positive and at least two resources are positive.
5. A remaining heterogeneous result is conservatively
   `SHARED_REPRESENTATION_NEGATIVE_TRANSFER`; a remaining uniformly weak result
   is `SHARED_REPRESENTATION_NOT_SUPPORTED`.

## Phase 3C next-direction mapping

The final primary direction is selected mechanically:

- `PLAIN_SHARED_MULTI_TASK_SUFFICIENT` when shared representation is
  `SHARED_REPRESENTATION_SUPPORTED` and no important negative transfer exists.
- `SHARING_HELPFUL_BUT_NEGATIVE_TRANSFER_PRESENT` when shared representation is
  `SHARED_REPRESENTATION_NEGATIVE_TRANSFER` and at least two resources are
  positive.
- `CROSS_RESOURCE_INPUT_HELPFUL_BUT_NAIVE_SHARING_NOT_SUPPORTED` when
  cross-resource input is supported and shared representation is not supported
  (including negative transfer with fewer than two positive resources).
- `MULTI_RESOURCE_FORECASTING_PREMISE_WEAK` when both cross-resource input and
  shared representation are not supported.
- `MIXED_REQUIRES_TARGETED_MECHANISM_STUDY` for every remaining heterogeneous
  or conditionally supported combination.

No result may change these definitions after scientific execution begins.
