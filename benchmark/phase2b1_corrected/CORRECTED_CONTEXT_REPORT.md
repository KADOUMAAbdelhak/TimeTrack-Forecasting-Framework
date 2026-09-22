# Corrected Phase 2B-1 Context Report

This report is descriptive; it is not a statistical-significance decision.

## Corrected gains by lead

| model | candidate_feature_set | lead | corrected_context_mae_gain_pct | median_corrected_context_mae_gain_pct | min_corrected_context_mae_gain_pct | max_corrected_context_mae_gain_pct | positive_machine_fold_fraction | corrected_context_rmse_gain_pct | corrected_context_r2_delta |
|---|---|---|---|---|---|---|---|---|---|
| LightGBM | F1_THROUGHPUT | 1.000 | 0.643 | 1.923 | -14.579 | 9.265 | 0.686 | 1.010 | 0.014 |
| LightGBM | F1_THROUGHPUT | 2.000 | 0.592 | 1.330 | -22.304 | 11.119 | 0.771 | 0.678 | 0.011 |
| LightGBM | F1_THROUGHPUT | 4.000 | 0.795 | 1.097 | -8.067 | 4.393 | 0.743 | 0.661 | 0.012 |
| LightGBM | F1_THROUGHPUT | 8.000 | 1.010 | 0.565 | -3.481 | 6.498 | 0.743 | 0.445 | 0.007 |
| LightGBM | F1_THROUGHPUT | 16.000 | 0.868 | 0.793 | -3.704 | 5.435 | 0.714 | 0.242 | 0.004 |
| LightGBM | F1_THROUGHPUT | 32.000 | 0.643 | 0.534 | -4.571 | 3.191 | 0.714 | 0.062 | 0.001 |
| LightGBM | F1_THROUGHPUT | 64.000 | 0.356 | 0.217 | -2.153 | 3.315 | 0.629 | 0.017 | 0.000 |
| LightGBM | F1_THROUGHPUT | 128.000 | 0.848 | 0.840 | -4.386 | 5.031 | 0.829 | 0.333 | 0.005 |
| LightGBM | F2_LOMO_MEAN | 1.000 | -1.382 | 0.109 | -16.849 | 5.946 | 0.543 | -0.149 | -0.005 |
| LightGBM | F2_LOMO_MEAN | 2.000 | -0.532 | -0.185 | -14.272 | 12.881 | 0.429 | 0.299 | 0.003 |
| LightGBM | F2_LOMO_MEAN | 4.000 | -1.114 | -0.291 | -14.482 | 8.669 | 0.486 | -0.050 | 0.002 |
| LightGBM | F2_LOMO_MEAN | 8.000 | -0.845 | -0.237 | -8.248 | 7.498 | 0.371 | 0.249 | 0.008 |
| LightGBM | F2_LOMO_MEAN | 16.000 | -0.901 | -0.370 | -5.782 | 2.383 | 0.286 | -0.192 | -0.001 |
| LightGBM | F2_LOMO_MEAN | 32.000 | -0.939 | -0.114 | -9.452 | 6.729 | 0.457 | 0.011 | 0.004 |
| LightGBM | F2_LOMO_MEAN | 64.000 | -0.449 | -0.001 | -5.830 | 2.717 | 0.486 | 0.156 | 0.006 |
| LightGBM | F2_LOMO_MEAN | 128.000 | -0.749 | -0.366 | -4.327 | 2.766 | 0.314 | -0.266 | -0.003 |
| LightGBM | F3_LOMO_MEDIAN | 1.000 | -1.371 | -0.328 | -13.450 | 4.837 | 0.400 | -0.986 | -0.012 |
| LightGBM | F3_LOMO_MEDIAN | 2.000 | -0.568 | -0.423 | -10.931 | 14.372 | 0.400 | 1.237 | 0.148 |
| LightGBM | F3_LOMO_MEDIAN | 4.000 | -0.956 | -0.197 | -11.886 | 1.850 | 0.486 | -0.454 | -0.005 |
| LightGBM | F3_LOMO_MEDIAN | 8.000 | -0.934 | -0.467 | -8.011 | 3.559 | 0.314 | -0.484 | -0.006 |
| LightGBM | F3_LOMO_MEDIAN | 16.000 | -0.358 | -0.300 | -5.118 | 4.395 | 0.286 | -0.051 | 0.001 |
| LightGBM | F3_LOMO_MEDIAN | 32.000 | -0.596 | -0.334 | -8.740 | 5.052 | 0.400 | 0.019 | 0.004 |
| LightGBM | F3_LOMO_MEDIAN | 64.000 | -0.501 | -0.030 | -7.643 | 3.593 | 0.457 | -0.028 | 0.002 |
| LightGBM | F3_LOMO_MEDIAN | 128.000 | -0.664 | -0.088 | -5.013 | 0.917 | 0.457 | -0.322 | -0.005 |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 1.000 | -1.022 | 0.118 | -17.174 | 11.699 | 0.514 | 0.637 | 0.009 |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 2.000 | -2.400 | -0.484 | -29.757 | 11.604 | 0.371 | -0.514 | -0.008 |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 4.000 | -2.578 | -1.097 | -37.222 | 8.821 | 0.457 | 0.135 | 0.007 |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 8.000 | -2.706 | -2.189 | -20.640 | 4.344 | 0.314 | -0.233 | 0.000 |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 16.000 | -1.877 | -0.797 | -20.186 | 5.252 | 0.400 | 0.022 | 0.001 |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 32.000 | -1.439 | -0.462 | -16.046 | 7.399 | 0.371 | 0.020 | 0.005 |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 64.000 | -1.778 | -0.625 | -30.931 | 3.220 | 0.371 | -0.157 | -0.000 |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 128.000 | -0.479 | -0.143 | -6.558 | 3.390 | 0.457 | 0.029 | 0.003 |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 1.000 | -1.095 | 0.411 | -15.321 | 10.931 | 0.514 | -0.468 | -0.005 |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 2.000 | -1.743 | -0.631 | -23.894 | 11.174 | 0.429 | -0.445 | -0.008 |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 4.000 | -1.407 | 0.381 | -15.977 | 5.335 | 0.543 | -0.131 | 0.002 |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 8.000 | -1.569 | -0.358 | -16.171 | 4.279 | 0.457 | -0.501 | -0.005 |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 16.000 | -1.540 | -0.363 | -17.927 | 5.423 | 0.486 | -0.183 | -0.002 |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 32.000 | -1.071 | -0.649 | -13.869 | 7.623 | 0.457 | -0.234 | -0.001 |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 64.000 | -0.895 | 0.051 | -15.143 | 4.143 | 0.514 | -0.045 | 0.001 |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 128.000 | -0.277 | 0.243 | -12.978 | 3.519 | 0.543 | 0.078 | 0.003 |
| Ridge | F1_THROUGHPUT | 1.000 | -2.060 | 0.860 | -26.006 | 7.087 | 0.571 | 0.848 | 0.011 |
| Ridge | F1_THROUGHPUT | 2.000 | -1.795 | 0.906 | -21.699 | 8.552 | 0.571 | 0.190 | 0.003 |
| Ridge | F1_THROUGHPUT | 4.000 | -1.590 | 0.846 | -23.136 | 8.049 | 0.543 | -0.380 | -0.008 |
| Ridge | F1_THROUGHPUT | 8.000 | -1.460 | 0.086 | -22.542 | 5.858 | 0.514 | -0.627 | -0.013 |
| Ridge | F1_THROUGHPUT | 16.000 | -1.467 | 0.258 | -19.878 | 9.990 | 0.514 | -0.506 | -0.011 |
| Ridge | F1_THROUGHPUT | 32.000 | -1.834 | -0.411 | -18.716 | 9.259 | 0.486 | -0.415 | -0.009 |
| Ridge | F1_THROUGHPUT | 64.000 | -2.003 | -1.059 | -13.265 | 6.415 | 0.486 | -0.336 | -0.007 |
| Ridge | F1_THROUGHPUT | 128.000 | -1.527 | -0.549 | -9.921 | 2.209 | 0.429 | -0.375 | -0.008 |
| Ridge | F2_LOMO_MEAN | 1.000 | -12.332 | -7.052 | -67.982 | 7.653 | 0.171 | -2.981 | -0.045 |
| Ridge | F2_LOMO_MEAN | 2.000 | -10.552 | -6.497 | -74.930 | 12.775 | 0.229 | -3.223 | -0.056 |
| Ridge | F2_LOMO_MEAN | 4.000 | -8.287 | -4.252 | -56.949 | 14.489 | 0.257 | -3.144 | -0.061 |
| Ridge | F2_LOMO_MEAN | 8.000 | -6.786 | -4.885 | -33.442 | 15.684 | 0.257 | -2.654 | -0.050 |
| Ridge | F2_LOMO_MEAN | 16.000 | -5.037 | -3.465 | -26.767 | 14.261 | 0.257 | -2.403 | -0.046 |
| Ridge | F2_LOMO_MEAN | 32.000 | -4.737 | -4.046 | -23.988 | 15.384 | 0.229 | -2.624 | -0.048 |
| Ridge | F2_LOMO_MEAN | 64.000 | -6.246 | -2.800 | -41.657 | 5.849 | 0.229 | -3.254 | -0.067 |
| Ridge | F2_LOMO_MEAN | 128.000 | -7.910 | -3.718 | -52.341 | 7.585 | 0.171 | -3.334 | -0.074 |
| Ridge | F3_LOMO_MEDIAN | 1.000 | -8.070 | -5.597 | -42.535 | 10.972 | 0.200 | -4.343 | -0.176 |
| Ridge | F3_LOMO_MEDIAN | 2.000 | -8.212 | -5.598 | -53.514 | 11.177 | 0.229 | -5.018 | -0.317 |
| Ridge | F3_LOMO_MEDIAN | 4.000 | -5.975 | -2.987 | -54.029 | 12.727 | 0.314 | -5.046 | -0.447 |
| Ridge | F3_LOMO_MEDIAN | 8.000 | -5.169 | -3.171 | -49.123 | 12.347 | 0.314 | -4.668 | -0.582 |
| Ridge | F3_LOMO_MEDIAN | 16.000 | -4.610 | -2.806 | -50.029 | 11.322 | 0.229 | -4.270 | -0.388 |
| Ridge | F3_LOMO_MEDIAN | 32.000 | -3.566 | -3.385 | -23.495 | 14.309 | 0.229 | -3.175 | -0.117 |
| Ridge | F3_LOMO_MEDIAN | 64.000 | -4.869 | -2.807 | -36.876 | 8.267 | 0.286 | -2.559 | -0.056 |
| Ridge | F3_LOMO_MEDIAN | 128.000 | -6.189 | -2.272 | -34.264 | 10.724 | 0.200 | -2.399 | -0.049 |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 1.000 | -19.362 | -8.825 | -189.266 | 13.576 | 0.143 | -5.997 | -0.116 |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 2.000 | -17.801 | -8.579 | -208.472 | 16.128 | 0.171 | -7.678 | -0.176 |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 4.000 | -15.579 | -6.373 | -159.578 | 16.012 | 0.200 | -7.266 | -0.157 |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 8.000 | -12.474 | -5.013 | -107.843 | 16.655 | 0.257 | -6.865 | -0.149 |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 16.000 | -9.607 | -2.426 | -92.409 | 16.322 | 0.286 | -5.765 | -0.129 |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 32.000 | -10.126 | -3.861 | -77.075 | 12.416 | 0.229 | -5.584 | -0.123 |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 64.000 | -11.351 | -5.553 | -110.949 | 5.788 | 0.171 | -5.967 | -0.141 |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 128.000 | -8.465 | -3.747 | -78.715 | 16.088 | 0.229 | -3.962 | -0.084 |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 1.000 | -14.170 | -9.629 | -121.215 | 16.945 | 0.229 | -4.187 | -0.070 |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 2.000 | -13.338 | -6.265 | -126.703 | 15.247 | 0.171 | -5.630 | -0.118 |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 4.000 | -11.940 | -4.952 | -115.947 | 14.630 | 0.229 | -5.887 | -0.116 |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 8.000 | -9.496 | -3.738 | -82.086 | 11.940 | 0.257 | -5.794 | -0.116 |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 16.000 | -8.839 | -3.587 | -96.521 | 12.290 | 0.286 | -5.068 | -0.113 |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 32.000 | -9.630 | -4.412 | -92.798 | 11.738 | 0.171 | -5.266 | -0.118 |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 64.000 | -10.055 | -4.654 | -101.287 | 7.263 | 0.171 | -5.088 | -0.116 |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 128.000 | -8.309 | -3.567 | -73.460 | 16.078 | 0.200 | -4.298 | -0.090 |

## Machine/fold consistency

| model | candidate_feature_set | mean_gain_pct | positive_cell_fraction | machines_positive_of_7 | folds_positive_of_5 |
|---|---|---|---|---|---|
| LightGBM | F1_THROUGHPUT | 0.719 | 0.729 | 5.000 | 4.000 |
| LightGBM | F2_LOMO_MEAN | -0.864 | 0.421 | 3.000 | 1.000 |
| LightGBM | F3_LOMO_MEDIAN | -0.743 | 0.400 | 3.000 | 1.000 |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | -1.785 | 0.407 | 2.000 | 1.000 |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | -1.200 | 0.493 | 1.000 | 1.000 |
| Ridge | F1_THROUGHPUT | -1.717 | 0.514 | 3.000 | 0.000 |
| Ridge | F2_LOMO_MEAN | -7.736 | 0.225 | 0.000 | 0.000 |
| Ridge | F3_LOMO_MEDIAN | -5.832 | 0.250 | 0.000 | 0.000 |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | -13.096 | 0.211 | 0.000 | 0.000 |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | -10.722 | 0.214 | 0.000 | 0.000 |

## Corrected descriptive answers

1. **Ridge throughput:** No aggregate improvement. F1 remains negative at all eight leads; its overall mean gain is -1.717%.
2. **LightGBM throughput:** Yes, modestly and heterogeneously. F1 is positive at all eight aggregate leads (0.356% to 1.010%) and averages 0.719%.
3. **LOMO mean:** No broad benefit. F2 is negative at every lead for both Ridge and LightGBM.
4. **LOMO median:** No broad benefit. F3 is negative at every lead for both models.
5. **Combined F4/F5:** No broad benefit. Both combined contexts are negative at every aggregate lead for both models.
6. **Positive real leads:** Only LightGBM F1 is aggregate-positive, at all leads [1, 2, 4, 8, 16, 32, 64, 128].
7. **Machine consistency:** LightGBM F1 is positive on 5/7 machine averages: ['machine02', 'machine03', 'machine05', 'machine06', 'machine07'].
8. **Fold consistency:** LightGBM F1 is positive on 4/5 fold averages: [1, 2, 3, 4]; fold 5 is negative.
9. **Material bias:** Yes. Median absolute cell correction is 1.704 percentage points, and the original LightGBM F1 overall mean changes from -0.108% to +0.719%.
10. **Magnitude versus direction:** Both changed. Most aggregate LOMO/combined and Ridge conclusions remain negative but less adverse; LightGBM F1 reverses overall direction. At cell level 560/2800 signs change.
11. **Local CPU sufficiency:** Local CPU remains a strong and broadly sufficient LightGBM baseline. Throughput adds only a small, nonuniform incremental gain; LOMO and combined contexts remain adverse.
12. **Research-direction decision:** **CONDITIONALLY_SUPPORTED**. Only same-machine throughput with LightGBM has consistent aggregate lead-level support, and the effect is small and not positive on every machine or fold. A broad context-aware CPU direction is not supported.

## Detailed model-feature summary

- Ridge throughput: mean gain -1.717%; positive leads []; positive machines 3/7; positive folds 0/5.
- Ridge LOMO mean: mean gain -7.736%; positive leads []; positive machines 0/7; positive folds 0/5.
- Ridge LOMO median: mean gain -5.832%; positive leads []; positive machines 0/7; positive folds 0/5.
- Ridge throughput + LOMO mean: mean gain -13.096%; positive leads []; positive machines 0/7; positive folds 0/5.
- Ridge throughput + LOMO median: mean gain -10.722%; positive leads []; positive machines 0/7; positive folds 0/5.
- LightGBM throughput: mean gain 0.719%; positive leads [1, 2, 4, 8, 16, 32, 64, 128]; positive machines 5/7; positive folds 4/5.
- LightGBM LOMO mean: mean gain -0.864%; positive leads []; positive machines 3/7; positive folds 1/5.
- LightGBM LOMO median: mean gain -0.743%; positive leads []; positive machines 3/7; positive folds 1/5.
- LightGBM throughput + LOMO mean: mean gain -1.785%; positive leads []; positive machines 2/7; positive folds 1/5.
- LightGBM throughput + LOMO median: mean gain -1.200%; positive leads []; positive machines 1/7; positive folds 1/5.

The support correction changed 560 of 2800 cell signs (486 negative-to-positive; 74 positive-to-negative). Median absolute correction was 1.704 percentage points.

Context-aware CPU direction decision: **CONDITIONALLY_SUPPORTED**.

DLinear and TCN were not executed.
