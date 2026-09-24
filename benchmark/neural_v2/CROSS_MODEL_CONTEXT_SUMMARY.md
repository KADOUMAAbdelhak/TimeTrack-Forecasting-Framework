# Cross-Model Context Summary

**POST-AUDIT REPORTING STANDARD.** This table is descriptive reporting, not a
prospective hypothesis-test, selection, or decision criterion. Previously frozen
decision labels are unchanged.

The primary statistic is the ratio of separately macro-aggregated matched F0 and
F1 MAEs. For stochastic neural models, seed MAEs are first averaged within each
machine-fold-lead cell; machine-fold-lead cells then receive equal weight. The
OVERALL macro F0 and F1 values are equal-weight means of the 8 lead-specific macro
MAEs, and the overall primary percentage is calculated from those MAEs rather than
by averaging lead percentages. Pooled values weight every stored prediction equally.
Cell-relative summaries retain the original matched-cell percentage definition.

## Overall standardized context summary

| model | lead | macro_f0_mae | macro_f1_mae | primary_ratio_macro_mae_gain_pct | pooled_f0_mae | pooled_f1_mae | pooled_gain_pct | mean_cell_relative_gain_pct | median_cell_relative_gain_pct | positive_cell_fraction |
|---|---|---|---|---|---|---|---|---|---|---|
| Ridge | OVERALL | 1.893436 | 1.966107 | -3.838048 | 2.002772 | 2.075509 | -3.631815 | -1.716727 | 0.121375 | 0.514286 |
| LightGBM | OVERALL | 1.344404 | 1.344203 | 0.014935 | 1.427921 | 1.429156 | -0.086515 | 0.719205 | 0.838148 | 0.728571 |
| DLinear | OVERALL | 1.861556 | 1.910045 | -2.604757 | 1.908509 | 1.957925 | -2.589275 | -2.867954 | -1.617576 | 0.321429 |
| LSTM | OVERALL | 1.944550 | 1.920200 | 1.252207 | 1.990639 | 1.973732 | 0.849314 | 3.087378 | 2.397566 | 0.657143 |

## LSTM lead-level aggregation semantics

| model | lead | macro_f0_mae | macro_f1_mae | primary_ratio_macro_mae_gain_pct | pooled_f0_mae | pooled_f1_mae | pooled_gain_pct | mean_cell_relative_gain_pct | median_cell_relative_gain_pct | positive_cell_fraction |
|---|---|---|---|---|---|---|---|---|---|---|
| LSTM | 1 | 1.585953 | 1.624127 | -2.407038 | 1.624226 | 1.671058 | -2.883392 | 2.350609 | 3.057056 | 0.647619 |
| LSTM | 2 | 1.683514 | 1.664761 | 1.113965 | 1.726469 | 1.715996 | 0.606644 | 2.962204 | 2.420095 | 0.666667 |
| LSTM | 4 | 1.871421 | 1.834446 | 1.975767 | 1.920326 | 1.890000 | 1.579175 | 3.486647 | 2.930755 | 0.685714 |
| LSTM | 8 | 1.959361 | 1.939077 | 1.035258 | 2.008492 | 1.995713 | 0.636260 | 2.184512 | 2.140505 | 0.638095 |
| LSTM | 16 | 1.996559 | 1.974454 | 1.107186 | 2.045330 | 2.028679 | 0.814098 | 1.693184 | 1.220424 | 0.590476 |
| LSTM | 32 | 2.078603 | 2.039038 | 1.903419 | 2.124992 | 2.091169 | 1.591659 | 3.135049 | 1.791920 | 0.676190 |
| LSTM | 64 | 2.113833 | 2.064931 | 2.313428 | 2.161697 | 2.121614 | 1.854228 | 4.212020 | 2.375037 | 0.676190 |
| LSTM | 128 | 2.267155 | 2.220768 | 2.046065 | 2.313578 | 2.275626 | 1.640428 | 4.674800 | 2.690310 | 0.676190 |

LSTM lead 1 is positive under the prospective mean cell-relative metric
(+2.3506%) but negative under both the primary macro-MAE ratio (-2.4070%) and
pooled-prediction gain (-2.8834%). Leads 2 through 128 are positive under all
three summaries.

## Interpretation

- Ridge: throughput is detrimental.
- DLinear: throughput is detrimental.
- LightGBM: the mean cell-relative effect is small and positive, but the macro-MAE
  result is effectively neutral and the pooled result is slightly negative.
- LSTM: throughput is positive overall under all three definitions, with smaller
  magnitude under macro-MAE and pooled reporting than under cell percentages.

Throughput usefulness is therefore architecture-dependent. Absolute CPU forecast
performance is a separate question: LSTM did not beat accepted LightGBM absolute
performance at any of the eight evaluated leads, and is not claimed to be the best
forecasting model.

The complete 36-row machine-readable table is `CROSS_MODEL_CONTEXT_SUMMARY.csv`.
