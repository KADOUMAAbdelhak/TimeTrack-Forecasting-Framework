# Phase 4C V2 Dual-Environment External Confirmation Report

## 1. Analysis provenance

Analysis used only the frozen compact metrics, persistence, selection, and M1 loss-history artifacts identified in `PHASE4C_V2_SCIENTIFIC_ANALYSIS_PROVENANCE.md`. Bootstrap seed: `20261007`; replicates: 10,000. No model training occurred.

## 2. Primary aggregation semantics

Native MAE was averaged across three seeds within each matched environment/VM/fold/resource/lead/formulation cell. VM-fold cells then received equal weight. Overall resource MacroMAE is the equal mean of the five lead-specific MacroMAEs. Pooled prediction-level MAE is secondary only.

## 3. fastStorage

### Absolute overall MacroMAEs

| formulation | resource | macro_mae |
|---|---|---|
| M1 | CPU | 1.2645 |
| M1 | DISK_WRITE | 12.6934 |
| M1 | MEMORY | 83430.0237 |
| M1 | THROUGHPUT | 193.0372 |
| S1 | CPU | 1.2259 |
| S1 | DISK_WRITE | 12.5338 |
| S1 | MEMORY | 81556.0025 |
| S1 | THROUGHPUT | 151.9045 |
| S2 | CPU | 1.2651 |
| S2 | DISK_WRITE | 12.1968 |
| S2 | MEMORY | 79557.8923 |
| S2 | THROUGHPUT | 151.8852 |

### Gains, classifications, and consistency

| comparison | resource | overall_primary_gain_percent | positive_horizons | positive_vms | positive_folds | positive_seed_aggregates | classification |
|---|---|---|---|---|---|---|---|
| S2_vs_S1 | CPU | -3.1985 | 0 | 19 | 1 | 0 | NEUTRAL_OR_MIXED |
| S2_vs_S1 | THROUGHPUT | 0.0127 | 3 | 15 | 1 | 1 | NEUTRAL_OR_MIXED |
| S2_vs_S1 | MEMORY | 2.4500 | 5 | 27 | 5 | 3 | BROAD_POSITIVE |
| S2_vs_S1 | DISK_WRITE | 2.6892 | 5 | 18 | 3 | 3 | CONDITIONALLY_POSITIVE |
| M1_vs_S2 | CPU | 0.0450 | 2 | 10 | 1 | 2 | NEUTRAL_OR_MIXED |
| M1_vs_S2 | THROUGHPUT | -27.0942 | 0 | 8 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S2 | MEMORY | -4.8671 | 0 | 3 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S2 | DISK_WRITE | -4.0721 | 0 | 5 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S1 | CPU | -3.1520 | 1 | 10 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S1 | THROUGHPUT | -27.0780 | 0 | 5 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S1 | MEMORY | -2.2978 | 0 | 16 | 0 | 0 | NEUTRAL_OR_MIXED |
| M1_vs_S1 | DISK_WRITE | -1.2734 | 0 | 11 | 1 | 0 | NEUTRAL_OR_MIXED |

### Global decisions

- S2 vs S1: `CROSS_RESOURCE_INPUT_MIXED`
- M1 vs S2: `SHARED_REPRESENTATION_NEGATIVE_TRANSFER` — conservative overlap rule: positive target evidence coexists with at least two broad negatives or strong trade-offs

## 4. Rnd

### Absolute overall MacroMAEs

| formulation | resource | macro_mae |
|---|---|---|
| M1 | CPU | 1.8140 |
| M1 | DISK_WRITE | 106.3057 |
| M1 | MEMORY | 178826.8036 |
| M1 | THROUGHPUT | 345.6778 |
| S1 | CPU | 1.5792 |
| S1 | DISK_WRITE | 100.8766 |
| S1 | MEMORY | 166981.9601 |
| S1 | THROUGHPUT | 282.0328 |
| S2 | CPU | 1.5569 |
| S2 | DISK_WRITE | 100.7148 |
| S2 | MEMORY | 164188.2139 |
| S2 | THROUGHPUT | 302.3800 |

### Gains, classifications, and consistency

| comparison | resource | overall_primary_gain_percent | positive_horizons | positive_vms | positive_folds | positive_seed_aggregates | classification |
|---|---|---|---|---|---|---|---|
| S2_vs_S1 | CPU | 1.4129 | 5 | 15 | 4 | 3 | CONDITIONALLY_POSITIVE |
| S2_vs_S1 | THROUGHPUT | -7.2145 | 0 | 15 | 0 | 0 | NEUTRAL_OR_MIXED |
| S2_vs_S1 | MEMORY | 1.6731 | 4 | 23 | 4 | 3 | CONDITIONALLY_POSITIVE |
| S2_vs_S1 | DISK_WRITE | 0.1604 | 1 | 7 | 3 | 2 | NEUTRAL_OR_MIXED |
| M1_vs_S2 | CPU | -16.5099 | 0 | 3 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S2 | THROUGHPUT | -14.3190 | 0 | 10 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S2 | MEMORY | -8.9157 | 0 | 3 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S2 | DISK_WRITE | -5.5512 | 0 | 2 | 1 | 0 | BROAD_NEGATIVE |
| M1_vs_S1 | CPU | -14.8638 | 0 | 6 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S1 | THROUGHPUT | -22.5665 | 0 | 9 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S1 | MEMORY | -7.0935 | 0 | 10 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S1 | DISK_WRITE | -5.3819 | 1 | 2 | 0 | 0 | BROAD_NEGATIVE |

### Global decisions

- S2 vs S1: `CROSS_RESOURCE_INPUT_MIXED`
- M1 vs S2: `SHARED_REPRESENTATION_NOT_SUPPORTED` — at most one positive resource and nonpositive equal-resource mean

## 5. Secondary aggregation diagnostics

Primary, pooled, mean/median cell-relative gains, positive-cell fractions, and explicit sign-reversal flags are preserved in the six comparison CSVs and `secondary_aggregation_diagnostics.csv`.

## 6. Bootstrap uncertainty

Intervals are prospectively defined paired VM-cluster percentile intervals and do not change classifications.

| environment | comparison | resource | lower_2_5_percent | median_percent | upper_97_5_percent |
|---|---|---|---|---|---|
| fastStorage | S2_vs_S1 | CPU | -6.8986 | -3.0526 | 0.1566 |
| fastStorage | S2_vs_S1 | THROUGHPUT | -0.1961 | 0.0346 | 2.8847 |
| fastStorage | S2_vs_S1 | MEMORY | 0.7552 | 2.3661 | 4.1156 |
| fastStorage | S2_vs_S1 | DISK_WRITE | -0.6517 | 2.5426 | 6.6141 |
| fastStorage | M1_vs_S2 | CPU | -10.7434 | 0.0998 | 3.5222 |
| fastStorage | M1_vs_S2 | THROUGHPUT | -29.1602 | -26.7871 | -1.8780 |
| fastStorage | M1_vs_S2 | MEMORY | -10.4248 | -4.6462 | -1.1613 |
| fastStorage | M1_vs_S2 | DISK_WRITE | -7.8437 | -4.1006 | -1.4283 |
| fastStorage | M1_vs_S1 | CPU | -13.4850 | -3.1528 | 0.3216 |
| fastStorage | M1_vs_S1 | THROUGHPUT | -29.3533 | -26.7466 | -0.6162 |
| fastStorage | M1_vs_S1 | MEMORY | -7.6717 | -2.0841 | 1.9953 |
| fastStorage | M1_vs_S1 | DISK_WRITE | -5.9772 | -1.3856 | 1.3634 |
| Rnd | S2_vs_S1 | CPU | -3.1871 | 1.3474 | 3.7522 |
| Rnd | S2_vs_S1 | THROUGHPUT | -49.9806 | -6.8327 | 4.1305 |
| Rnd | S2_vs_S1 | MEMORY | -2.0996 | 1.6139 | 4.6080 |
| Rnd | S2_vs_S1 | DISK_WRITE | -4.2264 | 0.0364 | 2.5287 |
| Rnd | M1_vs_S2 | CPU | -24.7372 | -15.9456 | -3.5004 |
| Rnd | M1_vs_S2 | THROUGHPUT | -26.1669 | -14.1439 | -6.4078 |
| Rnd | M1_vs_S2 | MEMORY | -12.2401 | -8.7861 | -4.0437 |
| Rnd | M1_vs_S2 | DISK_WRITE | -15.7145 | -5.6364 | -4.2369 |
| Rnd | M1_vs_S1 | CPU | -21.5257 | -14.5872 | -3.8727 |
| Rnd | M1_vs_S1 | THROUGHPUT | -88.8701 | -22.0312 | -3.3720 |
| Rnd | M1_vs_S1 | MEMORY | -10.8047 | -6.9790 | -3.0398 |
| Rnd | M1_vs_S1 | DISK_WRITE | -19.6463 | -5.6066 | -2.8011 |

## 7. Persistence

Persistence absolute metrics are reported per environment/resource/lead; model persistence skill is reported separately. Positive skill means the formulation beats persistence; nonpositive cells are retained as an absolute-forecasting warning.

| environment | resource | lead | horizon_minutes | mae | rmse | r2 | nmae |
|---|---|---|---|---|---|---|---|
| fastStorage | CPU | 1 | 5 | 0.5975 | 1.3237 | -0.5069 | 0.7011 |
| fastStorage | CPU | 2 | 10 | 0.5119 | 1.4508 | -0.4388 | 0.7919 |
| fastStorage | CPU | 4 | 20 | 0.6548 | 1.7709 | -0.5352 | 1.0515 |
| fastStorage | CPU | 9 | 45 | 1.0496 | 2.3439 | -0.6168 | 1.5601 |
| fastStorage | CPU | 18 | 90 | 1.1363 | 2.5631 | -0.6370 | 2.0557 |
| fastStorage | DISK_WRITE | 1 | 5 | 15.9516 | 80.8858 | -0.7388 | 4.2110 |
| fastStorage | DISK_WRITE | 2 | 10 | 16.3610 | 87.6083 | -0.8371 | 4.7683 |
| fastStorage | DISK_WRITE | 4 | 20 | 17.3070 | 90.2434 | -0.9055 | 5.1911 |
| fastStorage | DISK_WRITE | 9 | 45 | 18.5789 | 92.3069 | -0.9225 | 5.8704 |
| fastStorage | DISK_WRITE | 18 | 90 | 19.2272 | 94.1698 | -0.9103 | 6.9752 |
| fastStorage | MEMORY | 1 | 5 | 86371.3491 | 128319.0690 | -0.3895 | 0.7135 |
| fastStorage | MEMORY | 2 | 10 | 104728.5364 | 157895.6629 | -0.8082 | 0.8327 |
| fastStorage | MEMORY | 4 | 20 | 109121.5054 | 167444.5852 | -0.9269 | 0.8651 |
| fastStorage | MEMORY | 9 | 45 | 112132.5508 | 172830.5117 | -0.8123 | 0.8491 |
| fastStorage | MEMORY | 18 | 90 | 115698.2576 | 177935.7089 | -0.8904 | 0.8786 |
| fastStorage | THROUGHPUT | 1 | 5 | 77.6726 | 220.2729 | -0.5802 | 6.5531 |
| fastStorage | THROUGHPUT | 2 | 10 | 107.9521 | 283.3855 | -0.6822 | 8.2347 |
| fastStorage | THROUGHPUT | 4 | 20 | 142.2739 | 347.3955 | -0.7446 | 9.8252 |
| fastStorage | THROUGHPUT | 9 | 45 | 190.3078 | 425.3486 | -0.8109 | 11.6900 |
| fastStorage | THROUGHPUT | 18 | 90 | 243.0408 | 511.4016 | -0.7952 | 15.1853 |
| Rnd | CPU | 1 | 5 | 0.7011 | 2.2213 | 0.0974 | 0.7582 |
| Rnd | CPU | 2 | 10 | 0.9528 | 2.9767 | -0.1047 | 0.9297 |
| Rnd | CPU | 4 | 20 | 1.2925 | 3.7668 | -0.1176 | 1.1251 |
| Rnd | CPU | 9 | 45 | 1.6545 | 4.5163 | -0.3566 | 1.3585 |
| Rnd | CPU | 18 | 90 | 2.1359 | 5.2232 | -0.4235 | 1.4024 |
| Rnd | DISK_WRITE | 1 | 5 | 80.8596 | 383.1880 | -0.4896 | 6.8678 |
| Rnd | DISK_WRITE | 2 | 10 | 105.3979 | 497.6772 | -0.6676 | 8.2472 |
| Rnd | DISK_WRITE | 4 | 20 | 130.4317 | 563.4474 | -0.8797 | 9.0761 |
| Rnd | DISK_WRITE | 9 | 45 | 166.7602 | 634.6281 | -0.9647 | 9.7147 |
| Rnd | DISK_WRITE | 18 | 90 | 206.4500 | 697.3606 | -1.0167 | 9.9812 |
| Rnd | MEMORY | 1 | 5 | 137839.9439 | 244828.4096 | 0.0398 | 0.6195 |
| Rnd | MEMORY | 2 | 10 | 179524.3641 | 326277.8253 | -0.3954 | 0.7618 |
| Rnd | MEMORY | 4 | 20 | 203225.4762 | 376009.1598 | -0.5841 | 0.8254 |
| Rnd | MEMORY | 9 | 45 | 223406.2814 | 415516.8380 | -0.7000 | 0.8800 |
| Rnd | MEMORY | 18 | 90 | 238034.0328 | 439412.5763 | -0.7420 | 0.9030 |
| Rnd | THROUGHPUT | 1 | 5 | 286.4604 | 912.3218 | -0.1608 | 8.8948 |
| Rnd | THROUGHPUT | 2 | 10 | 343.2051 | 1017.0032 | -0.3582 | 10.8406 |
| Rnd | THROUGHPUT | 4 | 20 | 380.0497 | 1070.4343 | -0.4900 | 12.7642 |
| Rnd | THROUGHPUT | 9 | 45 | 403.6304 | 1093.2420 | -0.6166 | 15.4733 |
| Rnd | THROUGHPUT | 18 | 90 | 434.0912 | 1127.5418 | -0.9141 | 15.9319 |

| environment | formulation | resource | persistence_skill |
|---|---|---|---|
| fastStorage | M1 | CPU | -0.2334 |
| fastStorage | M1 | DISK_WRITE | 0.1626 |
| fastStorage | M1 | MEMORY | 0.2338 |
| fastStorage | M1 | THROUGHPUT | -0.3162 |
| fastStorage | S1 | CPU | -0.1711 |
| fastStorage | S1 | DISK_WRITE | 0.2558 |
| fastStorage | S1 | MEMORY | 0.2540 |
| fastStorage | S1 | THROUGHPUT | -0.1478 |
| fastStorage | S2 | CPU | -0.1927 |
| fastStorage | S2 | DISK_WRITE | 0.2523 |
| fastStorage | S2 | MEMORY | 0.2652 |
| fastStorage | S2 | THROUGHPUT | -0.2180 |
| Rnd | M1 | CPU | -0.2742 |
| Rnd | M1 | DISK_WRITE | 0.2312 |
| Rnd | M1 | MEMORY | 0.1610 |
| Rnd | M1 | THROUGHPUT | -0.1176 |
| Rnd | S1 | CPU | -0.0499 |
| Rnd | S1 | DISK_WRITE | 0.3616 |
| Rnd | S1 | MEMORY | 0.2049 |
| Rnd | S1 | THROUGHPUT | 0.0384 |
| Rnd | S2 | CPU | -0.0914 |
| Rnd | S2 | DISK_WRITE | 0.3283 |
| Rnd | S2 | MEMORY | 0.2123 |
| Rnd | S2 | THROUGHPUT | -0.0257 |

No formulation beats persistence across every resource. All three formulations have negative overall CPU persistence skill in both environments. All three also have negative throughput skill in fastStorage; in Rnd, S2 and M1 remain negative while S1 is only slightly positive. Memory and disk-write are positive for all formulations in both environments.

## 8. Heterogeneity

| environment | comparison | resource | positive_vm_fraction | positive_horizon_fraction | positive_fold_fraction | vm_gain_iqr_percent | fold_gain_range_percent | lead_gain_range_percent |
|---|---|---|---|---|---|---|---|---|
| fastStorage | S2_vs_S1 | CPU | 0.5429 | 0.0000 | 0.2000 | 6.7457 | 6.6627 | 4.3106 |
| fastStorage | S2_vs_S1 | THROUGHPUT | 0.4286 | 0.6000 | 0.2000 | 7.7635 | 20.1212 | 40.3649 |
| fastStorage | S2_vs_S1 | MEMORY | 0.7714 | 1.0000 | 1.0000 | 2.1737 | 4.0788 | 1.4982 |
| fastStorage | S2_vs_S1 | DISK_WRITE | 0.5143 | 1.0000 | 0.6000 | 6.7404 | 9.0190 | 1.6108 |
| fastStorage | M1_vs_S2 | CPU | 0.2857 | 0.4000 | 0.2000 | 7.3370 | 11.0629 | 4.2742 |
| fastStorage | M1_vs_S2 | THROUGHPUT | 0.2286 | 0.0000 | 0.0000 | 15.8970 | 54.9236 | 26.9876 |
| fastStorage | M1_vs_S2 | MEMORY | 0.0857 | 0.0000 | 0.0000 | 2.6405 | 2.8298 | 7.1600 |
| fastStorage | M1_vs_S2 | DISK_WRITE | 0.1429 | 0.0000 | 0.0000 | 12.8018 | 4.5494 | 2.7680 |
| fastStorage | M1_vs_S1 | CPU | 0.2857 | 0.2000 | 0.0000 | 10.2074 | 8.3205 | 8.7185 |
| fastStorage | M1_vs_S1 | THROUGHPUT | 0.1429 | 0.0000 | 0.0000 | 18.8411 | 29.7911 | 81.5127 |
| fastStorage | M1_vs_S1 | MEMORY | 0.4571 | 0.0000 | 0.0000 | 3.4491 | 2.8372 | 5.9598 |
| fastStorage | M1_vs_S1 | DISK_WRITE | 0.3143 | 0.0000 | 0.2000 | 13.2173 | 9.6218 | 1.5097 |
| Rnd | S2_vs_S1 | CPU | 0.4286 | 1.0000 | 0.8000 | 6.8481 | 5.0665 | 2.4390 |
| Rnd | S2_vs_S1 | THROUGHPUT | 0.4286 | 0.0000 | 0.0000 | 4.0293 | 9.7460 | 8.5517 |
| Rnd | S2_vs_S1 | MEMORY | 0.6571 | 0.8000 | 0.8000 | 4.4503 | 5.5783 | 4.6745 |
| Rnd | S2_vs_S1 | DISK_WRITE | 0.2000 | 0.2000 | 0.6000 | 7.0001 | 5.5994 | 11.6260 |
| Rnd | M1_vs_S2 | CPU | 0.0857 | 0.0000 | 0.0000 | 10.2296 | 12.5380 | 41.2958 |
| Rnd | M1_vs_S2 | THROUGHPUT | 0.2857 | 0.0000 | 0.0000 | 5.6583 | 9.7591 | 15.0934 |
| Rnd | M1_vs_S2 | MEMORY | 0.0857 | 0.0000 | 0.0000 | 6.1787 | 8.1268 | 23.0053 |
| Rnd | M1_vs_S2 | DISK_WRITE | 0.0571 | 0.0000 | 0.2000 | 18.7764 | 17.1818 | 8.7354 |
| Rnd | M1_vs_S1 | CPU | 0.1714 | 0.0000 | 0.0000 | 15.4731 | 9.3780 | 38.5646 |
| Rnd | M1_vs_S1 | THROUGHPUT | 0.2571 | 0.0000 | 0.0000 | 9.6950 | 10.1064 | 26.0018 |
| Rnd | M1_vs_S1 | MEMORY | 0.2857 | 0.0000 | 0.0000 | 7.9636 | 13.5014 | 17.3746 |
| Rnd | M1_vs_S1 | DISK_WRITE | 0.0571 | 0.2000 | 0.0000 | 27.8971 | 11.5409 | 21.1076 |

Frozen H3 label: `HETEROGENEITY_CONFIRMED`. predefined environment/resource/VM/lead/fold dimensions show sign or magnitude variation, without a broadly positive effect dominating both environments

## 9. M1 loss balance

| environment_key | resource | mean_percent | median_percent |
|---|---|---|---|
| Rnd | CPU | 26.9501 | 18.5680 |
| Rnd | DISK_WRITE | 23.9944 | 17.6635 |
| Rnd | MEMORY | 15.8119 | 8.0674 |
| Rnd | THROUGHPUT | 33.2436 | 25.4534 |
| fastStorage | CPU | 37.8859 | 28.8376 |
| fastStorage | DISK_WRITE | 22.9121 | 8.3416 |
| fastStorage | MEMORY | 25.7090 | 20.1382 |
| fastStorage | THROUGHPUT | 13.4930 | 3.4680 |

TimeTrack descriptive mean shares were CPU 48.24%, throughput 26.32%, memory 13.67%, and disk-write 11.77%. These differences are descriptive and not causal.

## 10. Context selection

| environment | formulation | resource | L | count |
|---|---|---|---|---|
| fastStorage | M1 | ALL | 4 | 66 |
| fastStorage | M1 | ALL | 9 | 42 |
| fastStorage | M1 | ALL | 18 | 67 |
| fastStorage | S1 | CPU | 4 | 34 |
| fastStorage | S1 | CPU | 9 | 42 |
| fastStorage | S1 | CPU | 18 | 99 |
| fastStorage | S1 | DISK_WRITE | 4 | 35 |
| fastStorage | S1 | DISK_WRITE | 9 | 51 |
| fastStorage | S1 | DISK_WRITE | 18 | 89 |
| fastStorage | S1 | MEMORY | 4 | 21 |
| fastStorage | S1 | MEMORY | 9 | 32 |
| fastStorage | S1 | MEMORY | 18 | 122 |
| fastStorage | S1 | THROUGHPUT | 4 | 68 |
| fastStorage | S1 | THROUGHPUT | 9 | 39 |
| fastStorage | S1 | THROUGHPUT | 18 | 68 |
| fastStorage | S2 | CPU | 4 | 43 |
| fastStorage | S2 | CPU | 9 | 46 |
| fastStorage | S2 | CPU | 18 | 86 |
| fastStorage | S2 | DISK_WRITE | 4 | 62 |
| fastStorage | S2 | DISK_WRITE | 9 | 29 |
| fastStorage | S2 | DISK_WRITE | 18 | 84 |
| fastStorage | S2 | MEMORY | 4 | 28 |
| fastStorage | S2 | MEMORY | 9 | 45 |
| fastStorage | S2 | MEMORY | 18 | 102 |
| fastStorage | S2 | THROUGHPUT | 4 | 68 |
| fastStorage | S2 | THROUGHPUT | 9 | 47 |
| fastStorage | S2 | THROUGHPUT | 18 | 60 |
| Rnd | M1 | ALL | 4 | 57 |
| Rnd | M1 | ALL | 9 | 64 |
| Rnd | M1 | ALL | 18 | 54 |
| Rnd | S1 | CPU | 4 | 41 |
| Rnd | S1 | CPU | 9 | 54 |
| Rnd | S1 | CPU | 18 | 80 |
| Rnd | S1 | DISK_WRITE | 4 | 14 |
| Rnd | S1 | DISK_WRITE | 9 | 35 |
| Rnd | S1 | DISK_WRITE | 18 | 126 |
| Rnd | S1 | MEMORY | 4 | 21 |
| Rnd | S1 | MEMORY | 9 | 22 |
| Rnd | S1 | MEMORY | 18 | 132 |
| Rnd | S1 | THROUGHPUT | 4 | 44 |
| Rnd | S1 | THROUGHPUT | 9 | 40 |
| Rnd | S1 | THROUGHPUT | 18 | 91 |
| Rnd | S2 | CPU | 4 | 70 |
| Rnd | S2 | CPU | 9 | 43 |
| Rnd | S2 | CPU | 18 | 62 |
| Rnd | S2 | DISK_WRITE | 4 | 26 |
| Rnd | S2 | DISK_WRITE | 9 | 32 |
| Rnd | S2 | DISK_WRITE | 18 | 117 |
| Rnd | S2 | MEMORY | 4 | 28 |
| Rnd | S2 | MEMORY | 9 | 40 |
| Rnd | S2 | MEMORY | 18 | 107 |
| Rnd | S2 | THROUGHPUT | 4 | 60 |
| Rnd | S2 | THROUGHPUT | 9 | 46 |
| Rnd | S2 | THROUGHPUT | 18 | 69 |

Context selections are descriptive and are not causal evidence.

## 11. Efficiency

| formulation | parameters | models_per_target_set | parameter_reduction_vs_S2_percent | model_count_reduction_vs_S2_percent | combined_actual_fit_hours |
|---|---|---|---|---|---|
| S1 | 203028 | 4 | 1.4905 | 0.0000 | 74.1049 |
| S2 | 206100 | 4 | 0.0000 | 0.0000 | 66.8544 |
| M1 | 52500 | 1 | 74.5269 | 75.0000 | 19.8881 |

M1 uses 52,500 parameters versus 206,100 for four S2 models, a 74.5269% reduction, and one model versus four, a 75% model-count reduction. Accuracy conclusions remain separate from efficiency.

## 12. Population/generalizability restriction

The confirmation population is restricted to structurally valid VMs with nondegenerate four-resource training variability in every scaler partition: fastStorage 596/916 and Rnd 272/416 were scale eligible. Approximately 35% were excluded in each environment for zero-IQR structure. Conclusions do not generalize to idle, quiescent, or resource-constant VMs.

## 13. Equal-environment synthesis

No weighting by VM count, origin count, prediction count, or duration was used.

| comparison | resource | fastStorage | Rnd | synthesized_gain_percent | sign_agreement | absolute_environment_disagreement_percent |
|---|---|---|---|---|---|---|
| M1_vs_S1 | CPU | -3.1520 | -14.8638 | -9.0079 | True | 11.7118 |
| M1_vs_S1 | DISK_WRITE | -1.2734 | -5.3819 | -3.3277 | True | 4.1085 |
| M1_vs_S1 | MEMORY | -2.2978 | -7.0935 | -4.6957 | True | 4.7957 |
| M1_vs_S1 | THROUGHPUT | -27.0780 | -22.5665 | -24.8222 | True | 4.5115 |
| M1_vs_S2 | CPU | 0.0450 | -16.5099 | -8.2324 | False | 16.5550 |
| M1_vs_S2 | DISK_WRITE | -4.0721 | -5.5512 | -4.8117 | True | 1.4791 |
| M1_vs_S2 | MEMORY | -4.8671 | -8.9157 | -6.8914 | True | 4.0487 |
| M1_vs_S2 | THROUGHPUT | -27.0942 | -14.3190 | -20.7066 | True | 12.7752 |
| S2_vs_S1 | CPU | -3.1985 | 1.4129 | -0.8928 | False | 4.6114 |
| S2_vs_S1 | DISK_WRITE | 2.6892 | 0.1604 | 1.4248 | True | 2.5288 |
| S2_vs_S1 | MEMORY | 2.4500 | 1.6731 | 2.0615 | True | 0.7769 |
| S2_vs_S1 | THROUGHPUT | 0.0127 | -7.2145 | -3.6009 | False | 7.2272 |

## 14. H1

`H1_BOUNDARY_PARTIALLY_REPLICATED` — neither environment supported S2, but synthesized resource evidence remained mixed

## 15. H2

`H2_BOUNDARY_CONFIRMED` — neither environment supported M1 sharing, synthesis mean was nonpositive, and no more than one resource was positive

## 16. H3

`HETEROGENEITY_CONFIRMED` — predefined environment/resource/VM/lead/fold dimensions show sign or magnitude variation, without a broadly positive effect dominating both environments

## 17. TimeTrack comparison

| comparison | resource | TimeTrack_gain_percent | fastStorage_gain_percent | Rnd_gain_percent | Bitbrains_equal_environment_gain_percent | all_three_sign_agreement |
|---|---|---|---|---|---|---|
| S2_vs_S1 | CPU | -3.3130 | -3.1985 | 1.4129 | -0.8928 | False |
| S2_vs_S1 | THROUGHPUT | -0.2428 | 0.0127 | -7.2145 | -3.6009 | False |
| S2_vs_S1 | MEMORY | 0.8594 | 2.4500 | 1.6731 | 2.0615 | True |
| S2_vs_S1 | DISK_WRITE | -0.4923 | 2.6892 | 0.1604 | 1.4248 | False |
| M1_vs_S2 | CPU | 0.4696 | 0.0450 | -16.5099 | -8.2324 | False |
| M1_vs_S2 | THROUGHPUT | -0.8401 | -27.0942 | -14.3190 | -20.7066 | True |
| M1_vs_S2 | MEMORY | -18.4769 | -4.8671 | -8.9157 | -6.8914 | True |
| M1_vs_S2 | DISK_WRITE | -0.7956 | -4.0721 | -5.5512 | -4.8117 | True |
| M1_vs_S1 | CPU | -2.8279 | -3.1520 | -14.8638 | -9.0079 | True |
| M1_vs_S1 | THROUGHPUT | -1.0849 | -27.0780 | -22.5665 | -24.8222 | True |
| M1_vs_S1 | MEMORY | -17.4587 | -2.2978 | -7.0935 | -4.6957 | True |
| M1_vs_S1 | DISK_WRITE | -1.2918 | -1.2734 | -5.3819 | -3.3277 | True |

TimeTrack and Bitbrains remain separate evidence environments; no pooled cross-dataset score was calculated.

## 18. Cross-dataset resource consistency

| comparison | resource | cross_dataset_consistency |
|---|---|---|
| S2_vs_S1 | CPU | INCONSISTENT_OR_ENVIRONMENT_DEPENDENT |
| S2_vs_S1 | THROUGHPUT | INCONSISTENT_OR_ENVIRONMENT_DEPENDENT |
| S2_vs_S1 | MEMORY | DIRECTIONALLY_POSITIVE_BUT_WEAK |
| S2_vs_S1 | DISK_WRITE | INCONSISTENT_OR_ENVIRONMENT_DEPENDENT |
| M1_vs_S2 | CPU | INCONSISTENT_OR_ENVIRONMENT_DEPENDENT |
| M1_vs_S2 | THROUGHPUT | CONSISTENTLY_NEGATIVE |
| M1_vs_S2 | MEMORY | CONSISTENTLY_NEGATIVE |
| M1_vs_S2 | DISK_WRITE | CONSISTENTLY_NEGATIVE |
| M1_vs_S1 | CPU | CONSISTENTLY_NEGATIVE |
| M1_vs_S1 | THROUGHPUT | CONSISTENTLY_NEGATIVE |
| M1_vs_S1 | MEMORY | CONSISTENTLY_NEGATIVE |
| M1_vs_S1 | DISK_WRITE | CONSISTENTLY_NEGATIVE |

## 19. Final Phase 4C outcome

`BOUNDARY_PARTIALLY_REPLICATED`

## 20. Publication-scope gate

`MULTIDATASET_BOUNDARY_STUDY_SUPPORTED_WITH_MIXED_REPLICATION`

## 21. Materna gate

`MATERNA_USEFUL_SECONDARY_REPLICATION`. Materna was not executed.

## 22. New-architecture gate

`NO` — external evidence does not reveal a stable replicated beneficial mechanism unavailable from TimeTrack; heterogeneity and negative naive-sharing results are not an architecture mandate

