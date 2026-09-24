# Phase 2B-2A1 DLinear Scientific Report

This is a descriptive report; no statistical-significance test is performed.

## Aggregate lead results

| Lead | DLinear F0 MAE | DLinear F1 MAE | Matched F1 gain (%) |
|---:|---:|---:|---:|
| 1 | 1.4017 | 1.5047 | -5.336 |
| 2 | 1.7511 | 1.7766 | -2.245 |
| 4 | 1.8587 | 1.8966 | -2.354 |
| 8 | 1.8903 | 1.9290 | -2.520 |
| 16 | 1.8841 | 1.9234 | -2.149 |
| 32 | 1.9316 | 1.9776 | -2.758 |
| 64 | 2.0059 | 2.0516 | -3.119 |
| 128 | 2.1691 | 2.2210 | -2.463 |

## Descriptive answers

1. DLinear F0 MAE rises across the lead profile from 1.4017 at lead 1 to 2.1691 at lead 128; the complete eight-lead profile is tabulated above.
2. F1 throughput has an overall matched cell-mean MAE gain of -2.868% versus DLinear F0.
3. Positive aggregate leads: [] (0/8).
4. Positive machine means: ['machine03'] (1/7).
5. Positive fold means: [] (0/5).
6. Seed mean gains are {0: -4.028, 1: -2.117, 2: -2.459}; 0/3 seeds are positive overall.
7. F0 selected-L counts: {32: 14, 64: 4, 128: 17}.
8. F1 selected-L counts: {32: 15, 64: 1, 128: 19}.
9. Throughput changes the preferred L in 4/35 machine-fold cells.
10. DLinear F0 beats accepted matched LightGBM F0 at 0/8 aggregate leads on exact common evaluation subsets.
11. DLinear F1 beats accepted LightGBM F1 at 0/8 aggregate leads on exact common evaluation subsets.
12. DLinear has a larger incremental throughput gain than LightGBM at 0/8 aggregate leads on those subsets.

All LightGBM comparisons were recomputed on exact per-cell intersections without retraining. Machine/fold support relations and hashes are recorded in `dlinear_vs_lightgbm.csv`; no differently supported aggregate was compared silently.

## DLinear throughput decision

Prospective rule: `BROAD_POSITIVE` requires positive overall gain, 8/8 positive leads, at least 5/7 positive machines, at least 4/5 positive folds, and 3/3 positive seeds; `CONDITIONALLY_POSITIVE` requires positive overall gain, at least 4/8 leads, 4/7 machines, 3/5 folds, and 2/3 seeds; `BROAD_NEGATIVE` requires negative overall gain, at least 6/8 negative leads, 5/7 machines, 4/5 folds, and 3/3 seeds; all other patterns are `NEUTRAL`.

**BROAD_NEGATIVE**

The prospective criteria are frozen in `benchmark/neural_v2/DLINEAR_DECISION_CRITERIA.md`. Observed consistency counts were {'overall_mean_gain_pct': -2.867954122384713, 'positive_leads': 0, 'positive_machines': 1, 'positive_folds': 0, 'positive_seeds': 0, 'negative_leads': 8, 'negative_machines': 6, 'negative_folds': 5, 'negative_seeds': 3}.

No LSTM, TCN-v2, PatchTST, B4-v1, or multi-target model was executed.
