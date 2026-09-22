# Original versus Corrected Context Gains

The original candidate predictions and absolute metrics are unchanged. Only the matched F0 comparator changed.

| model | candidate_feature_set | lead | original_context_mae_gain_pct | corrected_context_mae_gain_pct | difference_percentage_points | sign_changed |
|---|---|---|---|---|---|---|
| LightGBM | F1_THROUGHPUT | 1.000 | -0.892 | 0.643 | 1.535 | True |
| LightGBM | F1_THROUGHPUT | 2.000 | 0.129 | 0.592 | 0.462 | False |
| LightGBM | F1_THROUGHPUT | 4.000 | -0.116 | 0.795 | 0.911 | True |
| LightGBM | F1_THROUGHPUT | 8.000 | 0.136 | 1.010 | 0.874 | False |
| LightGBM | F1_THROUGHPUT | 16.000 | -0.175 | 0.868 | 1.042 | True |
| LightGBM | F1_THROUGHPUT | 32.000 | -0.134 | 0.643 | 0.777 | True |
| LightGBM | F1_THROUGHPUT | 64.000 | -0.032 | 0.356 | 0.388 | True |
| LightGBM | F1_THROUGHPUT | 128.000 | 0.216 | 0.848 | 0.632 | False |
| LightGBM | F2_LOMO_MEAN | 1.000 | -4.904 | -1.382 | 3.523 | False |
| LightGBM | F2_LOMO_MEAN | 2.000 | -3.575 | -0.532 | 3.043 | False |
| LightGBM | F2_LOMO_MEAN | 4.000 | -3.551 | -1.114 | 2.437 | False |
| LightGBM | F2_LOMO_MEAN | 8.000 | -2.360 | -0.845 | 1.515 | False |
| LightGBM | F2_LOMO_MEAN | 16.000 | -2.426 | -0.901 | 1.525 | False |
| LightGBM | F2_LOMO_MEAN | 32.000 | -2.406 | -0.939 | 1.466 | False |
| LightGBM | F2_LOMO_MEAN | 64.000 | -1.784 | -0.449 | 1.335 | False |
| LightGBM | F2_LOMO_MEAN | 128.000 | -1.627 | -0.749 | 0.878 | False |
| LightGBM | F3_LOMO_MEDIAN | 1.000 | -4.979 | -1.371 | 3.608 | False |
| LightGBM | F3_LOMO_MEDIAN | 2.000 | -3.868 | -0.568 | 3.299 | False |
| LightGBM | F3_LOMO_MEDIAN | 4.000 | -3.403 | -0.956 | 2.448 | False |
| LightGBM | F3_LOMO_MEDIAN | 8.000 | -2.486 | -0.934 | 1.552 | False |
| LightGBM | F3_LOMO_MEDIAN | 16.000 | -1.893 | -0.358 | 1.536 | False |
| LightGBM | F3_LOMO_MEDIAN | 32.000 | -2.070 | -0.596 | 1.474 | False |
| LightGBM | F3_LOMO_MEDIAN | 64.000 | -1.864 | -0.501 | 1.364 | False |
| LightGBM | F3_LOMO_MEDIAN | 128.000 | -1.567 | -0.664 | 0.903 | False |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 1.000 | -6.632 | -1.022 | 5.611 | False |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 2.000 | -7.161 | -2.400 | 4.761 | False |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 4.000 | -6.663 | -2.578 | 4.085 | False |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 8.000 | -4.485 | -2.706 | 1.779 | False |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 16.000 | -4.149 | -1.877 | 2.272 | False |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 32.000 | -4.524 | -1.439 | 3.085 | False |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 64.000 | -3.634 | -1.778 | 1.856 | False |
| LightGBM | F4_THROUGHPUT_LOMO_MEAN | 128.000 | -3.974 | -0.479 | 3.495 | False |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 1.000 | -6.956 | -1.095 | 5.861 | False |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 2.000 | -6.662 | -1.743 | 4.919 | False |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 4.000 | -5.614 | -1.407 | 4.208 | False |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 8.000 | -3.496 | -1.569 | 1.927 | False |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 16.000 | -3.988 | -1.540 | 2.447 | False |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 32.000 | -4.185 | -1.071 | 3.114 | False |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 64.000 | -2.801 | -0.895 | 1.906 | False |
| LightGBM | F5_THROUGHPUT_LOMO_MEDIAN | 128.000 | -3.812 | -0.277 | 3.535 | False |
| Ridge | F1_THROUGHPUT | 1.000 | -2.373 | -2.060 | 0.313 | False |
| Ridge | F1_THROUGHPUT | 2.000 | -1.628 | -1.795 | -0.167 | False |
| Ridge | F1_THROUGHPUT | 4.000 | -1.458 | -1.590 | -0.132 | False |
| Ridge | F1_THROUGHPUT | 8.000 | -1.670 | -1.460 | 0.210 | False |
| Ridge | F1_THROUGHPUT | 16.000 | -2.065 | -1.467 | 0.598 | False |
| Ridge | F1_THROUGHPUT | 32.000 | -2.247 | -1.834 | 0.414 | False |
| Ridge | F1_THROUGHPUT | 64.000 | -1.872 | -2.003 | -0.131 | False |
| Ridge | F1_THROUGHPUT | 128.000 | -1.751 | -1.527 | 0.224 | False |
| Ridge | F2_LOMO_MEAN | 1.000 | -16.981 | -12.332 | 4.650 | False |
| Ridge | F2_LOMO_MEAN | 2.000 | -15.029 | -10.552 | 4.477 | False |
| Ridge | F2_LOMO_MEAN | 4.000 | -12.583 | -8.287 | 4.296 | False |
| Ridge | F2_LOMO_MEAN | 8.000 | -10.974 | -6.786 | 4.188 | False |
| Ridge | F2_LOMO_MEAN | 16.000 | -9.572 | -5.037 | 4.535 | False |
| Ridge | F2_LOMO_MEAN | 32.000 | -8.615 | -4.737 | 3.879 | False |
| Ridge | F2_LOMO_MEAN | 64.000 | -8.049 | -6.246 | 1.803 | False |
| Ridge | F2_LOMO_MEAN | 128.000 | -8.447 | -7.910 | 0.537 | False |
| Ridge | F3_LOMO_MEDIAN | 1.000 | -12.154 | -8.070 | 4.084 | False |
| Ridge | F3_LOMO_MEDIAN | 2.000 | -12.248 | -8.212 | 4.036 | False |
| Ridge | F3_LOMO_MEDIAN | 4.000 | -9.699 | -5.975 | 3.725 | False |
| Ridge | F3_LOMO_MEDIAN | 8.000 | -9.214 | -5.169 | 4.045 | False |
| Ridge | F3_LOMO_MEDIAN | 16.000 | -8.967 | -4.610 | 4.356 | False |
| Ridge | F3_LOMO_MEDIAN | 32.000 | -7.149 | -3.566 | 3.583 | False |
| Ridge | F3_LOMO_MEDIAN | 64.000 | -6.476 | -4.869 | 1.607 | False |
| Ridge | F3_LOMO_MEDIAN | 128.000 | -5.484 | -6.189 | -0.705 | False |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 1.000 | -22.946 | -19.362 | 3.583 | False |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 2.000 | -21.505 | -17.801 | 3.704 | False |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 4.000 | -19.264 | -15.579 | 3.685 | False |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 8.000 | -17.180 | -12.474 | 4.706 | False |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 16.000 | -15.219 | -9.607 | 5.612 | False |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 32.000 | -13.347 | -10.126 | 3.220 | False |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 64.000 | -11.894 | -11.351 | 0.543 | False |
| Ridge | F4_THROUGHPUT_LOMO_MEAN | 128.000 | -9.961 | -8.465 | 1.496 | False |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 1.000 | -17.747 | -14.170 | 3.576 | False |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 2.000 | -17.063 | -13.338 | 3.725 | False |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 4.000 | -15.508 | -11.940 | 3.568 | False |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 8.000 | -13.925 | -9.496 | 4.429 | False |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 16.000 | -14.404 | -8.839 | 5.565 | False |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 32.000 | -12.859 | -9.630 | 3.229 | False |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 64.000 | -10.641 | -10.055 | 0.586 | False |
| Ridge | F5_THROUGHPUT_LOMO_MEDIAN | 128.000 | -9.829 | -8.309 | 1.520 | False |

## Cell-level sign changes

- machine_fold_lead_cells: 2800
- sign_changed: 560
- negative_to_positive: 486
- positive_to_negative: 74
- median_signed_correction_pp: 1.3844652598673695
- median_absolute_correction_pp: 1.7043316696064084
