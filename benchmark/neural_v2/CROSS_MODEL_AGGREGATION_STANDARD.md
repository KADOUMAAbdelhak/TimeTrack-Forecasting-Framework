# Cross-Model Aggregation Standard

## Status

**POST-AUDIT REPORTING STANDARD**

This convention was selected after the Ridge, LightGBM, DLinear, and LSTM
results existed. It is a descriptive reporting convention, not a prospective
hypothesis-test, model-selection, or decision criterion. It does not alter any
previously frozen scientific decision label.

In particular, the prospective LSTM decision remains **CONDITIONALLY_POSITIVE**
under its authoritative mean matched cell-level relative MAE gain criterion.

## Primary cross-model statistic

The primary F1-throughput context statistic is the **ratio of macro-aggregated
matched MAEs**.

For stochastic neural models, for every real lead:

1. average seed MAE separately for F0 and F1 within each
   `machine x fold x lead` cell;
2. give the resulting machine-fold cells equal weight;
3. aggregate matched F0 and F1 MAEs separately; and
4. calculate

   `100 * (macro_F0_MAE - macro_F1_MAE) / macro_F0_MAE`.

For deterministic models, the same procedure begins with the single matched
F0/F1 result in each machine-fold-lead cell.

The overall primary value is not an average of lead percentages. Overall F0
and F1 macro MAEs are formed by giving the eight lead-specific macro MAEs equal
weight, and the percentage is calculated once from those two overall MAEs.

Positive gain means lower F1 MAE than matched F0 MAE.

## Secondary statistics

Cross-model reports also retain:

- pooled-prediction MAE gain, with every stored prediction receiving equal
  weight;
- mean matched cell-level relative MAE gain;
- median matched cell-level relative MAE gain;
- positive-cell fraction; and
- machine, fold, and seed heterogeneity.

The pooled statistic describes observation-weighted performance but may give
more influence to machines or folds with larger test supports. The cell-level
percentage summaries expose heterogeneity but may give disproportionate
influence to cells with small baseline MAE. These are complementary summaries,
not replacements for the primary macro-MAE statistic.

Future positive-machine, positive-fold, and positive-seed reporting under this
standard should derive each subgroup sign from separately aggregated F0 and F1
MAEs within that subgroup. Original prospective consistency counts remain
preserved under their original criteria and must be labelled accordingly.
