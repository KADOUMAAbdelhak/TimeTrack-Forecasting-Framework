# Phase 2B-1 Deterministic Benchmark Report

This is a descriptive benchmark execution report, not manuscript text.
No statistical significance test, neural model, or proposed architecture is included.

## Execution

- Completed runs: 630 / 630.
- Lead-level metric rows: 5040 / 5,040.
- Models: Persistence, Ridge, and LightGBM only.
- Feature sets: frozen F0-F5; machines 01-07; folds 1-5.

## F0 ranking by real lead

| lead | rank | model | macro_machine_mae |
|---|---|---|---|
| 1.000 | 1.000 | LightGBM | 1.032 |
| 1.000 | 2.000 | Ridge | 1.454 |
| 1.000 | 3.000 | Persistence | 1.635 |
| 2.000 | 1.000 | LightGBM | 1.227 |
| 2.000 | 2.000 | Ridge | 1.834 |
| 2.000 | 3.000 | Persistence | 2.107 |
| 4.000 | 1.000 | LightGBM | 1.352 |
| 4.000 | 2.000 | Ridge | 1.961 |
| 4.000 | 3.000 | Persistence | 2.421 |
| 8.000 | 1.000 | LightGBM | 1.470 |
| 8.000 | 2.000 | Ridge | 1.995 |
| 8.000 | 3.000 | Persistence | 2.606 |
| 16.000 | 1.000 | LightGBM | 1.470 |
| 16.000 | 2.000 | Ridge | 1.963 |
| 16.000 | 3.000 | Persistence | 2.633 |
| 32.000 | 1.000 | LightGBM | 1.481 |
| 32.000 | 2.000 | Ridge | 2.001 |
| 32.000 | 3.000 | Persistence | 2.541 |
| 64.000 | 1.000 | LightGBM | 1.485 |
| 64.000 | 2.000 | Ridge | 2.075 |
| 64.000 | 3.000 | Persistence | 2.500 |
| 128.000 | 1.000 | LightGBM | 1.498 |
| 128.000 | 2.000 | Ridge | 2.132 |
| 128.000 | 3.000 | Persistence | 2.675 |

## Matched-F0 context summary

| model | feature_set | mean_gain_pct | best_lead_gain_pct | positive_detail_fraction |
|---|---|---|---|---|
| LightGBM | F1_THROUGHPUT | -0.108 | 0.216 | 0.539 |
| LightGBM | F2_LOMO_MEAN | -2.829 | -1.627 | 0.182 |
| LightGBM | F3_LOMO_MEDIAN | -2.766 | -1.567 | 0.175 |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | -5.153 | -3.634 | 0.154 |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | -4.689 | -2.801 | 0.154 |
| Ridge | F1_THROUGHPUT | -1.883 | -1.458 | 0.475 |
| Ridge | F2_LOMO_MEAN | -11.281 | -8.049 | 0.161 |
| Ridge | F3_LOMO_MEDIAN | -8.924 | -5.484 | 0.211 |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | -16.414 | -9.961 | 0.164 |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | -13.997 | -9.829 | 0.179 |

## Matched-F0 gain by real lead

| model | lead | feature_set | mean_context_mae_gain_pct |
|---|---|---|---|
| LightGBM | 1.000 | F1_THROUGHPUT | -0.892 |
| LightGBM | 1.000 | F2_LOMO_MEAN | -4.904 |
| LightGBM | 1.000 | F3_LOMO_MEDIAN | -4.979 |
| LightGBM | 1.000 | F4_THROUGHPUT_LOMO_MEAN | -6.632 |
| LightGBM | 1.000 | F5_THROUGHPUT_LOMO_MEDIAN | -6.956 |
| LightGBM | 2.000 | F1_THROUGHPUT | 0.129 |
| LightGBM | 2.000 | F2_LOMO_MEAN | -3.575 |
| LightGBM | 2.000 | F3_LOMO_MEDIAN | -3.868 |
| LightGBM | 2.000 | F4_THROUGHPUT_LOMO_MEAN | -7.161 |
| LightGBM | 2.000 | F5_THROUGHPUT_LOMO_MEDIAN | -6.662 |
| LightGBM | 4.000 | F1_THROUGHPUT | -0.116 |
| LightGBM | 4.000 | F2_LOMO_MEAN | -3.551 |
| LightGBM | 4.000 | F3_LOMO_MEDIAN | -3.403 |
| LightGBM | 4.000 | F4_THROUGHPUT_LOMO_MEAN | -6.663 |
| LightGBM | 4.000 | F5_THROUGHPUT_LOMO_MEDIAN | -5.614 |
| LightGBM | 8.000 | F1_THROUGHPUT | 0.136 |
| LightGBM | 8.000 | F2_LOMO_MEAN | -2.360 |
| LightGBM | 8.000 | F3_LOMO_MEDIAN | -2.486 |
| LightGBM | 8.000 | F4_THROUGHPUT_LOMO_MEAN | -4.485 |
| LightGBM | 8.000 | F5_THROUGHPUT_LOMO_MEDIAN | -3.496 |
| LightGBM | 16.000 | F1_THROUGHPUT | -0.175 |
| LightGBM | 16.000 | F2_LOMO_MEAN | -2.426 |
| LightGBM | 16.000 | F3_LOMO_MEDIAN | -1.893 |
| LightGBM | 16.000 | F4_THROUGHPUT_LOMO_MEAN | -4.149 |
| LightGBM | 16.000 | F5_THROUGHPUT_LOMO_MEDIAN | -3.988 |
| LightGBM | 32.000 | F1_THROUGHPUT | -0.134 |
| LightGBM | 32.000 | F2_LOMO_MEAN | -2.406 |
| LightGBM | 32.000 | F3_LOMO_MEDIAN | -2.070 |
| LightGBM | 32.000 | F4_THROUGHPUT_LOMO_MEAN | -4.524 |
| LightGBM | 32.000 | F5_THROUGHPUT_LOMO_MEDIAN | -4.185 |
| LightGBM | 64.000 | F1_THROUGHPUT | -0.032 |
| LightGBM | 64.000 | F2_LOMO_MEAN | -1.784 |
| LightGBM | 64.000 | F3_LOMO_MEDIAN | -1.864 |
| LightGBM | 64.000 | F4_THROUGHPUT_LOMO_MEAN | -3.634 |
| LightGBM | 64.000 | F5_THROUGHPUT_LOMO_MEDIAN | -2.801 |
| LightGBM | 128.000 | F1_THROUGHPUT | 0.216 |
| LightGBM | 128.000 | F2_LOMO_MEAN | -1.627 |
| LightGBM | 128.000 | F3_LOMO_MEDIAN | -1.567 |
| LightGBM | 128.000 | F4_THROUGHPUT_LOMO_MEAN | -3.974 |
| LightGBM | 128.000 | F5_THROUGHPUT_LOMO_MEDIAN | -3.812 |
| Ridge | 1.000 | F1_THROUGHPUT | -2.373 |
| Ridge | 1.000 | F2_LOMO_MEAN | -16.981 |
| Ridge | 1.000 | F3_LOMO_MEDIAN | -12.154 |
| Ridge | 1.000 | F4_THROUGHPUT_LOMO_MEAN | -22.946 |
| Ridge | 1.000 | F5_THROUGHPUT_LOMO_MEDIAN | -17.747 |
| Ridge | 2.000 | F1_THROUGHPUT | -1.628 |
| Ridge | 2.000 | F2_LOMO_MEAN | -15.029 |
| Ridge | 2.000 | F3_LOMO_MEDIAN | -12.248 |
| Ridge | 2.000 | F4_THROUGHPUT_LOMO_MEAN | -21.505 |
| Ridge | 2.000 | F5_THROUGHPUT_LOMO_MEDIAN | -17.063 |
| Ridge | 4.000 | F1_THROUGHPUT | -1.458 |
| Ridge | 4.000 | F2_LOMO_MEAN | -12.583 |
| Ridge | 4.000 | F3_LOMO_MEDIAN | -9.699 |
| Ridge | 4.000 | F4_THROUGHPUT_LOMO_MEAN | -19.264 |
| Ridge | 4.000 | F5_THROUGHPUT_LOMO_MEDIAN | -15.508 |
| Ridge | 8.000 | F1_THROUGHPUT | -1.670 |
| Ridge | 8.000 | F2_LOMO_MEAN | -10.974 |
| Ridge | 8.000 | F3_LOMO_MEDIAN | -9.214 |
| Ridge | 8.000 | F4_THROUGHPUT_LOMO_MEAN | -17.180 |
| Ridge | 8.000 | F5_THROUGHPUT_LOMO_MEDIAN | -13.925 |
| Ridge | 16.000 | F1_THROUGHPUT | -2.065 |
| Ridge | 16.000 | F2_LOMO_MEAN | -9.572 |
| Ridge | 16.000 | F3_LOMO_MEDIAN | -8.967 |
| Ridge | 16.000 | F4_THROUGHPUT_LOMO_MEAN | -15.219 |
| Ridge | 16.000 | F5_THROUGHPUT_LOMO_MEDIAN | -14.404 |
| Ridge | 32.000 | F1_THROUGHPUT | -2.247 |
| Ridge | 32.000 | F2_LOMO_MEAN | -8.615 |
| Ridge | 32.000 | F3_LOMO_MEDIAN | -7.149 |
| Ridge | 32.000 | F4_THROUGHPUT_LOMO_MEAN | -13.347 |
| Ridge | 32.000 | F5_THROUGHPUT_LOMO_MEDIAN | -12.859 |
| Ridge | 64.000 | F1_THROUGHPUT | -1.872 |
| Ridge | 64.000 | F2_LOMO_MEAN | -8.049 |
| Ridge | 64.000 | F3_LOMO_MEDIAN | -6.476 |
| Ridge | 64.000 | F4_THROUGHPUT_LOMO_MEAN | -11.894 |
| Ridge | 64.000 | F5_THROUGHPUT_LOMO_MEDIAN | -10.641 |
| Ridge | 128.000 | F1_THROUGHPUT | -1.751 |
| Ridge | 128.000 | F2_LOMO_MEAN | -8.447 |
| Ridge | 128.000 | F3_LOMO_MEDIAN | -5.484 |
| Ridge | 128.000 | F4_THROUGHPUT_LOMO_MEAN | -9.961 |
| Ridge | 128.000 | F5_THROUGHPUT_LOMO_MEDIAN | -9.829 |

## Leads with largest matched context gain

| model | feature_set | lead | mean_context_mae_gain_pct |
|---|---|---|---|
| LightGBM | F1_THROUGHPUT | 128.000 | 0.216 |
| LightGBM | F2_LOMO_MEAN | 128.000 | -1.627 |
| LightGBM | F3_LOMO_MEDIAN | 128.000 | -1.567 |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 64.000 | -3.634 |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 64.000 | -2.801 |
| Ridge | F1_THROUGHPUT | 4.000 | -1.458 |
| Ridge | F2_LOMO_MEAN | 64.000 | -8.049 |
| Ridge | F3_LOMO_MEDIAN | 128.000 | -5.484 |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 128.000 | -9.961 |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 128.000 | -9.829 |

## Selection audit

Selected context lengths:

| model | context_length | selected_runs |
|---|---|---|
| LightGBM | 32 | 44 |
| LightGBM | 64 | 42 |
| LightGBM | 128 | 124 |
| Ridge | 32 | 68 |
| Ridge | 64 | 50 |
| Ridge | 128 | 92 |

Selected Ridge alphas:

| alpha | selected_runs |
|---|---|
| 0.01 | 11.00 |
| 10.00 | 1.00 |
| 100.00 | 198.00 |

Selected LightGBM joint configurations:

| context_length | num_leaves | learning_rate | n_estimators | selected_runs |
|---|---|---|---|---|
| 32.000 | 15.000 | 0.030 | 200.000 | 6.000 |
| 32.000 | 15.000 | 0.030 | 400.000 | 3.000 |
| 32.000 | 15.000 | 0.050 | 200.000 | 5.000 |
| 32.000 | 15.000 | 0.050 | 400.000 | 4.000 |
| 32.000 | 31.000 | 0.030 | 200.000 | 12.000 |
| 32.000 | 31.000 | 0.030 | 400.000 | 6.000 |
| 32.000 | 31.000 | 0.050 | 200.000 | 2.000 |
| 32.000 | 31.000 | 0.050 | 400.000 | 6.000 |
| 64.000 | 15.000 | 0.030 | 200.000 | 15.000 |
| 64.000 | 15.000 | 0.030 | 400.000 | 6.000 |
| 64.000 | 15.000 | 0.050 | 200.000 | 3.000 |
| 64.000 | 15.000 | 0.050 | 400.000 | 1.000 |
| 64.000 | 31.000 | 0.030 | 200.000 | 1.000 |
| 64.000 | 31.000 | 0.030 | 400.000 | 5.000 |
| 64.000 | 31.000 | 0.050 | 200.000 | 2.000 |
| 64.000 | 31.000 | 0.050 | 400.000 | 9.000 |
| 128.000 | 15.000 | 0.030 | 200.000 | 41.000 |
| 128.000 | 15.000 | 0.030 | 400.000 | 8.000 |
| 128.000 | 15.000 | 0.050 | 200.000 | 2.000 |
| 128.000 | 15.000 | 0.050 | 400.000 | 2.000 |
| 128.000 | 31.000 | 0.030 | 200.000 | 9.000 |
| 128.000 | 31.000 | 0.030 | 400.000 | 34.000 |
| 128.000 | 31.000 | 0.050 | 200.000 | 2.000 |
| 128.000 | 31.000 | 0.050 | 400.000 | 26.000 |

## Machine/fold consistency

| model | feature_set | mean_gain_pct | positive_machine_fold_fraction | machines_positive_of_7 | folds_positive_of_5 |
|---|---|---|---|---|---|
| LightGBM | F1_THROUGHPUT | -0.108 | 0.539 | 3.000 | 4.000 |
| LightGBM | F2_LOMO_MEAN | -2.829 | 0.182 | 0.000 | 0.000 |
| LightGBM | F3_LOMO_MEDIAN | -2.766 | 0.175 | 0.000 | 0.000 |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | -5.153 | 0.154 | 0.000 | 0.000 |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | -4.689 | 0.154 | 0.000 | 0.000 |
| Ridge | F1_THROUGHPUT | -1.883 | 0.475 | 2.000 | 0.000 |
| Ridge | F2_LOMO_MEAN | -11.281 | 0.161 | 0.000 | 0.000 |
| Ridge | F3_LOMO_MEDIAN | -8.924 | 0.211 | 0.000 | 0.000 |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | -16.414 | 0.164 | 0.000 | 0.000 |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | -13.997 | 0.179 | 0.000 | 0.000 |

## Benchmark questions

1. **BQ1:** Ridge throughput was adverse at every lead (-2.373% to -1.458%). LightGBM F1 was weakly positive at leads [2, 8, 128], with its largest gain 0.216%.
2. **BQ2:** F2/F3 aggregate gains were adverse at every lead (-16.981% to -1.567%); no F2/F3 model had a positive machine-average or fold-average effect.
3. **BQ3:** Combined context beat F1 at 0/8 Ridge leads and 0/8 LightGBM leads. Combined-minus-F1 average gain is LightGBM -4.581 pp, Ridge -12.114 pp.
4. **BQ4:** Median LOMO was less adverse than mean LOMO on average: Ridge F3 -8.924% vs F2 -11.281%, LightGBM F3 -2.766% vs F2 -2.829%. F5 was also less adverse than F4 for Ridge (-13.997% vs -16.414%) and LightGBM (-4.689% vs -5.153%).
5. **BQ5:** Context was most useful for LightGBM F1 at real lead 128 (0.216%); Ridge had no positive aggregate contextual lead.
6. **BQ6:** Mean positive machine-fold fraction across contextual profiles is 0.239. F1-positive machine averages were Ridge: machine03, machine07; LightGBM: machine03, machine05, machine06. Other context sets had no positive model-level machine average.
7. **BQ7:** Mean context gain over F1-F5/leads is Ridge -10.500% and LightGBM -3.109%; LightGBM extracted more useful/less harmful context descriptively.
8. **BQ8:** NOT YET EVALUATED.
9. **BQ9:** The F0 ranking did not change: LightGBM first, Ridge second, Persistence third at all eight real leads.
10. **BQ10:** Positive context effects were concentrated in F1 and specific machines/folds; the machine/fold table above and `deterministic_context_ablation.csv` retain the full descriptive detail.

## Scope

The figures showing a best contextual feature choose that feature by inner-validation MAE only, then display outer-test gain. Outer-test performance never chooses a feature or configuration.
