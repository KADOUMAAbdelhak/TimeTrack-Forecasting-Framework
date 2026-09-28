# Phase 3C Full Multi-Resource LSTM Factorial Scientific Report

## Execution and validation

All 3,780 frozen fits completed: 2,835 inner and 945 final. Validation status: **PASS** (zero structural failures; metrics and aggregation independently reproduced). Decision criteria SHA-256: `3157a233c3c76b126ff939f7e0588c9c2d21f98bb7d3e6355f13a5d1bc470d57`.

## Native performance by resource and lead

| formulation | resource | lead | mae | rmse | r2 | nmae | persistence_skill |
|---|---|---|---|---|---|---|---|
| M1 | CPU | 1 | 1.6742 | 4.4579 | 0.0971 | 2.7909 | -0.0840 |
| M1 | CPU | 2 | 1.6953 | 4.5679 | 0.0760 | 2.8255 | 0.0790 |
| M1 | CPU | 4 | 1.7642 | 4.6694 | 0.0436 | 2.9447 | 0.1446 |
| M1 | CPU | 8 | 1.8680 | 4.8047 | -0.0042 | 3.1328 | 0.1634 |
| M1 | CPU | 16 | 1.8608 | 4.7679 | -0.0120 | 3.0960 | 0.1981 |
| M1 | CPU | 32 | 1.9315 | 4.8987 | -0.0187 | 3.2206 | 0.1381 |
| M1 | CPU | 64 | 1.9694 | 4.9860 | -0.0196 | 3.2304 | 0.1107 |
| M1 | CPU | 128 | 2.1127 | 5.3551 | -0.0026 | 3.5215 | 0.1803 |
| M1 | DISK_WRITE | 1 | 3026380.8959 | 14455665.6500 | -0.0116 | 50.9233 | 0.2652 |
| M1 | DISK_WRITE | 2 | 3006288.4822 | 14355955.5453 | -0.0135 | 50.2498 | 0.3338 |
| M1 | DISK_WRITE | 4 | 3029289.6785 | 14585556.3999 | -0.0176 | 51.0949 | 0.3385 |
| M1 | DISK_WRITE | 8 | 3075747.1796 | 15000055.6328 | -0.0243 | 52.0975 | 0.3644 |
| M1 | DISK_WRITE | 16 | 3118739.6900 | 15341123.7691 | -0.0276 | 51.9477 | 0.3699 |
| M1 | DISK_WRITE | 32 | 3337718.4308 | 15864743.5719 | -0.0277 | 54.3170 | 0.3705 |
| M1 | DISK_WRITE | 64 | 3219519.7079 | 15416480.2187 | -0.0930 | 52.2490 | 0.3600 |
| M1 | DISK_WRITE | 128 | 3563119.9240 | 16715351.3795 | -0.0229 | 47.0324 | 0.3673 |
| M1 | MEMORY | 1 | 357198427.9286 | 737606601.7433 | -0.4889 | 1.2177 | -1.6647 |
| M1 | MEMORY | 2 | 363078375.9227 | 750620778.4027 | -0.4454 | 1.2328 | -0.9832 |
| M1 | MEMORY | 4 | 371607787.7455 | 774041622.6484 | -0.6054 | 1.2559 | -0.6442 |
| M1 | MEMORY | 8 | 381189185.4053 | 779422390.1725 | -0.6523 | 1.2992 | -0.4385 |
| M1 | MEMORY | 16 | 379620178.0749 | 775601144.7786 | -0.7885 | 1.2864 | -0.3820 |
| M1 | MEMORY | 32 | 369402535.5740 | 791499446.0752 | -0.4529 | 1.2982 | -0.2982 |
| M1 | MEMORY | 64 | 380126060.0343 | 840587547.1997 | -0.5119 | 1.3340 | -0.2477 |
| M1 | MEMORY | 128 | 387086224.5244 | 850276912.0280 | -0.6550 | 1.3630 | -0.1793 |
| M1 | THROUGHPUT | 1 | 30.7620 | 104.2075 | 0.0167 | 52.4316 | 0.0868 |
| M1 | THROUGHPUT | 2 | 30.6869 | 103.3435 | 0.0137 | 51.7323 | 0.2454 |
| M1 | THROUGHPUT | 4 | 30.3179 | 102.7390 | 0.0160 | 51.3233 | 0.2937 |
| M1 | THROUGHPUT | 8 | 30.2081 | 102.3147 | 0.0080 | 49.2593 | 0.3268 |
| M1 | THROUGHPUT | 16 | 29.7075 | 101.6728 | 0.0065 | 46.0267 | 0.3515 |
| M1 | THROUGHPUT | 32 | 29.2017 | 100.9000 | 0.0069 | 41.0189 | 0.3386 |
| M1 | THROUGHPUT | 64 | 28.4813 | 100.9550 | 0.0128 | 32.0187 | 0.3258 |
| M1 | THROUGHPUT | 128 | 31.6055 | 110.1906 | 0.0042 | 37.6115 | 0.3585 |
| S1 | CPU | 1 | 1.5615 | 4.2695 | 0.1869 | 2.5916 | 0.0019 |
| S1 | CPU | 2 | 1.6187 | 4.4624 | 0.1521 | 2.6946 | 0.1433 |
| S1 | CPU | 4 | 1.7099 | 4.6475 | 0.1057 | 2.8614 | 0.1937 |
| S1 | CPU | 8 | 1.8137 | 4.7700 | 0.0591 | 3.0530 | 0.1986 |
| S1 | CPU | 16 | 1.8062 | 4.7215 | 0.0262 | 3.0136 | 0.2241 |
| S1 | CPU | 32 | 1.9023 | 4.8725 | 0.0161 | 3.1944 | 0.1463 |
| S1 | CPU | 64 | 1.9497 | 4.9647 | 0.0019 | 3.2197 | 0.1137 |
| S1 | CPU | 128 | 2.1051 | 5.3309 | 0.0275 | 3.5262 | 0.1875 |
| S1 | DISK_WRITE | 1 | 2883021.9632 | 14094303.2643 | 0.0111 | 48.7657 | 0.2843 |
| S1 | DISK_WRITE | 2 | 2920223.0825 | 14162627.7905 | 0.0030 | 49.0906 | 0.3459 |
| S1 | DISK_WRITE | 4 | 2992723.8408 | 14526621.2322 | -0.0032 | 50.7414 | 0.3466 |
| S1 | DISK_WRITE | 8 | 3062799.3129 | 15005556.8503 | -0.0152 | 51.9797 | 0.3705 |
| S1 | DISK_WRITE | 16 | 3108724.8422 | 15340425.3219 | -0.0161 | 51.8187 | 0.3759 |
| S1 | DISK_WRITE | 32 | 3324682.3587 | 15866410.8367 | -0.0172 | 54.1948 | 0.3771 |
| S1 | DISK_WRITE | 64 | 3208619.5653 | 15411250.5968 | -0.0277 | 52.1809 | 0.3672 |
| S1 | DISK_WRITE | 128 | 3552370.2087 | 16712472.2857 | -0.0096 | 47.0431 | 0.3751 |
| S1 | MEMORY | 1 | 250474087.9211 | 632817656.0360 | 0.3271 | 0.9052 | -0.5620 |
| S1 | MEMORY | 2 | 280358731.3887 | 686161967.0727 | 0.2034 | 0.9840 | -0.2928 |
| S1 | MEMORY | 4 | 312078040.9162 | 725887920.4019 | 0.1033 | 1.1100 | -0.1239 |
| S1 | MEMORY | 8 | 337842462.2679 | 735187646.1564 | -0.0108 | 1.1903 | -0.0460 |
| S1 | MEMORY | 16 | 333875734.9740 | 728386104.0154 | -0.1269 | 1.1531 | -0.0033 |
| S1 | MEMORY | 32 | 325591598.0823 | 754941592.1409 | -0.0026 | 1.1702 | 0.0044 |
| S1 | MEMORY | 64 | 346629445.4476 | 809091930.2733 | -0.0836 | 1.2530 | -0.0093 |
| S1 | MEMORY | 128 | 358136830.4232 | 817965378.5507 | -0.1751 | 1.2906 | 0.0156 |
| S1 | THROUGHPUT | 1 | 30.3331 | 103.8870 | 0.0208 | 52.0865 | 0.0975 |
| S1 | THROUGHPUT | 2 | 30.2456 | 103.1698 | 0.0158 | 51.4554 | 0.2529 |
| S1 | THROUGHPUT | 4 | 30.0278 | 102.7317 | 0.0147 | 51.0652 | 0.2988 |
| S1 | THROUGHPUT | 8 | 30.2083 | 102.5559 | 0.0006 | 49.0259 | 0.3274 |
| S1 | THROUGHPUT | 16 | 29.7878 | 102.0789 | -0.0067 | 45.7955 | 0.3469 |
| S1 | THROUGHPUT | 32 | 29.0420 | 101.2065 | -0.0003 | 40.7946 | 0.3432 |
| S1 | THROUGHPUT | 64 | 27.7372 | 100.7251 | 0.0183 | 31.7844 | 0.3418 |
| S1 | THROUGHPUT | 128 | 31.0028 | 110.1585 | 0.0044 | 37.4025 | 0.3703 |
| S2 | CPU | 1 | 1.6737 | 4.4090 | 0.1481 | 2.7790 | -0.0623 |
| S2 | CPU | 2 | 1.6975 | 4.5142 | 0.1289 | 2.8183 | 0.1052 |
| S2 | CPU | 4 | 1.7700 | 4.6422 | 0.0879 | 2.9465 | 0.1681 |
| S2 | CPU | 8 | 1.8773 | 4.7911 | 0.0448 | 3.1422 | 0.1868 |
| S2 | CPU | 16 | 1.8742 | 4.7610 | 0.0269 | 3.1136 | 0.2161 |
| S2 | CPU | 32 | 1.9399 | 4.8910 | 0.0138 | 3.2406 | 0.1591 |
| S2 | CPU | 64 | 1.9797 | 4.9703 | 0.0080 | 3.2472 | 0.1258 |
| S2 | CPU | 128 | 2.1341 | 5.3412 | 0.0306 | 3.5394 | 0.1955 |
| S2 | DISK_WRITE | 1 | 2872416.8953 | 13997262.4832 | 0.0171 | 48.8653 | 0.2834 |
| S2 | DISK_WRITE | 2 | 2912073.5647 | 14092897.3494 | 0.0031 | 48.8044 | 0.3425 |
| S2 | DISK_WRITE | 4 | 3011580.4953 | 14516184.2889 | -0.0101 | 50.6606 | 0.3375 |
| S2 | DISK_WRITE | 8 | 3097813.4149 | 15014302.5624 | -0.0160 | 52.2586 | 0.3612 |
| S2 | DISK_WRITE | 16 | 3141428.0497 | 15336848.4211 | -0.0156 | 52.1486 | 0.3702 |
| S2 | DISK_WRITE | 32 | 3345768.7503 | 15862374.8407 | -0.0199 | 54.4690 | 0.3735 |
| S2 | DISK_WRITE | 64 | 3227132.7281 | 15411831.5371 | -0.0648 | 52.3777 | 0.3618 |
| S2 | DISK_WRITE | 128 | 3568292.8774 | 16711126.9725 | -0.0091 | 47.2215 | 0.3718 |
| S2 | MEMORY | 1 | 270874585.5073 | 649298953.1605 | 0.0857 | 0.9600 | -0.7773 |
| S2 | MEMORY | 2 | 282727174.6511 | 675981354.9079 | 0.0715 | 0.9786 | -0.3607 |
| S2 | MEMORY | 4 | 300237621.1346 | 721058329.8976 | -0.0184 | 1.0531 | -0.1257 |
| S2 | MEMORY | 8 | 321914227.0575 | 735446065.3303 | -0.1184 | 1.1422 | -0.0188 |
| S2 | MEMORY | 16 | 320682191.2013 | 726898465.7159 | -0.1848 | 1.1211 | 0.0248 |
| S2 | MEMORY | 32 | 322970920.8684 | 755851436.5996 | -0.0591 | 1.1618 | 0.0129 |
| S2 | MEMORY | 64 | 350898590.2466 | 816210095.7948 | -0.1209 | 1.2396 | 0.0064 |
| S2 | MEMORY | 128 | 352810279.4240 | 820920221.9147 | -0.1856 | 1.2602 | 0.0434 |
| S2 | THROUGHPUT | 1 | 30.2481 | 103.5092 | 0.0271 | 52.2722 | 0.0989 |
| S2 | THROUGHPUT | 2 | 30.0723 | 102.5852 | 0.0266 | 51.5783 | 0.2581 |
| S2 | THROUGHPUT | 4 | 29.8842 | 102.1978 | 0.0241 | 51.1484 | 0.3003 |
| S2 | THROUGHPUT | 8 | 29.9559 | 102.2055 | 0.0100 | 49.0851 | 0.3310 |
| S2 | THROUGHPUT | 16 | 29.6457 | 101.7368 | 0.0060 | 45.8719 | 0.3531 |
| S2 | THROUGHPUT | 32 | 29.2087 | 101.0641 | 0.0042 | 40.8467 | 0.3386 |
| S2 | THROUGHPUT | 64 | 28.3641 | 101.0665 | 0.0106 | 31.8306 | 0.3271 |
| S2 | THROUGHPUT | 128 | 31.5843 | 110.3375 | 0.0016 | 37.4802 | 0.3580 |

## Cross-resource input: S2 vs S1

| resource | primary_gain_pct | positive_leads | positive_machines | positive_folds | positive_seeds | classification |
|---|---|---|---|---|---|---|
| CPU | -3.3130 | 0.0000 | 3.0000 | 3.0000 | 0.0000 | NEUTRAL_OR_MIXED |
| THROUGHPUT | -0.2428 | 5.0000 | 3.0000 | 3.0000 | 0.0000 | NEUTRAL_OR_MIXED |
| MEMORY | 0.8594 | 5.0000 | 2.0000 | 2.0000 | 2.0000 | NEUTRAL_OR_MIXED |
| DISK_WRITE | -0.4923 | 2.0000 | 3.0000 | 1.0000 | 0.0000 | NEUTRAL_OR_MIXED |

## Shared representation: M1 vs S2

| resource | primary_gain_pct | positive_leads | positive_machines | positive_folds | positive_seeds | classification |
|---|---|---|---|---|---|---|
| CPU | 0.4696 | 7.0000 | 1.0000 | 3.0000 | 2.0000 | NEUTRAL_OR_MIXED |
| THROUGHPUT | -0.8401 | 1.0000 | 3.0000 | 1.0000 | 1.0000 | NEUTRAL_OR_MIXED |
| MEMORY | -18.4769 | 0.0000 | 0.0000 | 1.0000 | 0.0000 | BROAD_NEGATIVE |
| DISK_WRITE | -0.7956 | 5.0000 | 1.0000 | 2.0000 | 0.0000 | NEUTRAL_OR_MIXED |

## Total effect: M1 vs S1

| resource | primary_gain_pct | positive_leads | positive_machines | positive_folds | positive_seeds | classification |
|---|---|---|---|---|---|---|
| CPU | -2.8279 | 0.0000 | 2.0000 | 2.0000 | 0.0000 | NEUTRAL_OR_MIXED |
| THROUGHPUT | -1.0849 | 2.0000 | 3.0000 | 3.0000 | 0.0000 | NEUTRAL_OR_MIXED |
| MEMORY | -17.4587 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | BROAD_NEGATIVE |
| DISK_WRITE | -1.2918 | 0.0000 | 1.0000 | 0.0000 | 0.0000 | BROAD_NEGATIVE |

## Global decisions

- Cross-resource input: **CROSS_RESOURCE_INPUT_NOT_SUPPORTED**
- Shared representation: **SHARED_REPRESENTATION_NOT_SUPPORTED**
- Equal-resource mean S2-vs-S1 gain: -0.7972%
- Equal-resource mean M1-vs-S2 gain: -4.9107%

## Positive horizons

| comparison | resource | positive_horizons |
|---|---|---|
| s2_vs_s1 | CPU | none |
| s2_vs_s1 | THROUGHPUT | 1,2,4,8,16 |
| s2_vs_s1 | MEMORY | 4,8,16,32,128 |
| s2_vs_s1 | DISK_WRITE | 1,2 |
| m1_vs_s2 | CPU | 2,4,8,16,32,64,128 |
| m1_vs_s2 | THROUGHPUT | 32 |
| m1_vs_s2 | MEMORY | none |
| m1_vs_s2 | DISK_WRITE | 8,16,32,64,128 |
| m1_vs_s1 | CPU | none |
| m1_vs_s1 | THROUGHPUT | 8,16 |
| m1_vs_s1 | MEMORY | none |
| m1_vs_s1 | DISK_WRITE | none |

## Optimization and negative transfer

The selected-inner CPU mean loss share was 48.24%; the pre-execution CPU-majority pattern did not persist. DISK_WRITE received the smallest mean numerical loss share. M1 was BROAD_NEGATIVE for MEMORY versus S2 (-18.4769%), which is resource-specific evidence of negative transfer. The frozen global label is **SHARED_REPRESENTATION_NOT_SUPPORTED** because no resource met the positive resource classification. Loss-share alignment is descriptive and **consistent with**, not proof of, task imbalance.

| resource | mean_loss_share_pct | median_loss_share_pct |
|---|---|---|
| CPU | 48.2362 | 51.8358 |
| DISK_WRITE | 11.7704 | 7.4686 |
| MEMORY | 13.6720 | 3.1449 |
| THROUGHPUT | 26.3214 | 12.3515 |

## Context and epoch selection

S2 selected a different context from S1 in 62/140 matched resource-machine-fold cells. M1 differed from the corresponding S2 target context in 85/140 comparisons.

| formulation | resource | selected_L | count |
|---|---|---|---|
| M1 | ALL | 32 | 10 |
| M1 | ALL | 64 | 10 |
| M1 | ALL | 128 | 15 |
| S1 | CPU | 32 | 8 |
| S1 | CPU | 64 | 15 |
| S1 | CPU | 128 | 12 |
| S1 | DISK_WRITE | 32 | 10 |
| S1 | DISK_WRITE | 64 | 2 |
| S1 | DISK_WRITE | 128 | 23 |
| S1 | MEMORY | 32 | 12 |
| S1 | MEMORY | 64 | 11 |
| S1 | MEMORY | 128 | 12 |
| S1 | THROUGHPUT | 32 | 8 |
| S1 | THROUGHPUT | 64 | 7 |
| S1 | THROUGHPUT | 128 | 20 |
| S2 | CPU | 32 | 8 |
| S2 | CPU | 64 | 17 |
| S2 | CPU | 128 | 10 |
| S2 | DISK_WRITE | 32 | 8 |
| S2 | DISK_WRITE | 64 | 5 |
| S2 | DISK_WRITE | 128 | 22 |
| S2 | MEMORY | 32 | 11 |
| S2 | MEMORY | 64 | 10 |
| S2 | MEMORY | 128 | 14 |
| S2 | THROUGHPUT | 32 | 6 |
| S2 | THROUGHPUT | 64 | 8 |
| S2 | THROUGHPUT | 128 | 21 |

| phase | formulation | count | mean | median | min | max |
|---|---|---|---|---|---|---|
| inner_executed | M1 | 315 | 32.4286 | 31.0000 | 9 | 50 |
| inner_executed | S1 | 1260 | 28.0817 | 25.0000 | 8 | 50 |
| inner_executed | S2 | 1260 | 24.3548 | 20.0000 | 8 | 50 |
| final_fixed_refit | M1 | 105 | 29.3048 | 26.0000 | 2 | 50 |
| final_fixed_refit | S1 | 420 | 23.5619 | 20.0000 | 1 | 50 |
| final_fixed_refit | S2 | 420 | 19.1595 | 14.0000 | 1 | 50 |

## Persistence results

| formulation | resource | mean_persistence_skill | positive_leads |
|---|---|---|---|
| M1 | CPU | 0.1163 | 7 |
| M1 | DISK_WRITE | 0.3462 | 8 |
| M1 | MEMORY | -0.6047 | 0 |
| M1 | THROUGHPUT | 0.2909 | 8 |
| S1 | CPU | 0.1511 | 8 |
| S1 | DISK_WRITE | 0.3553 | 8 |
| S1 | MEMORY | -0.1272 | 2 |
| S1 | THROUGHPUT | 0.2973 | 8 |
| S2 | CPU | 0.1368 | 7 |
| S2 | DISK_WRITE | 0.3502 | 8 |
| S2 | MEMORY | -0.1494 | 4 |
| S2 | THROUGHPUT | 0.2956 | 8 |

## Efficiency

S2 uses 206,880 parameters across four inference models; M1 uses 53,280 in one model, a 74.25% parameter reduction and 75% model-count reduction. M1 is operationally smaller, but its similar CPU accuracy does not offset the large MEMORY degradation; accuracy and efficiency remain separate conclusions.

| formulation | inner_fit_hours | final_fit_hours | prediction_hours |
|---|---|---|---|
| S1 | 30.5146 | 10.8342 | 0.0341 |
| S2 | 28.4970 | 8.7892 | 0.0344 |
| M1 | 9.7465 | 3.0855 | 0.0071 |

Total recorded fit time: 91.467 h; prediction time: 0.076 h; main resumed invocation wall time: 23.555 h; peak RSS: 1.759 GiB. The recorded wall time was above the 12.27 h optimistic projection and below the 30.68 h central and 61.36 h conservative projections.

## Research direction

Cross-resource inputs were not supported globally, and plain sharing was not supported. The evidence therefore does not justify continuing directly to a more complex multi-resource forecaster. MEMORY shows a strong negative-transfer pattern, but adaptive weighting is not justified from loss shares alone and selective sharing is not justified as the next mandatory mechanism while the cross-resource premise itself is weak. A future targeted diagnostic study could revisit those mechanisms, but none is implemented here.

## Artifact and integrity summary

Scientific output tree size: 621.45 MiB. Models: 945; prediction files: 945; figures: 8; metric rows: 10,080; selected-context records: 315.

Independent validation checks execution counts, matched support, leakage, selection, fixed epochs, train-only scalers, timestamps, transforms, physical projection, metric/aggregation recomputation, prior frozen histories, raw hashes, and canonical-panel identity. The validator must report PASS before conclusions are accepted.

## Generated files

Core outputs are under `outputs/scientific/`: `inner_run_registry.csv`, `run_registry.csv`, `selected_contexts.csv`, `selected_epochs.csv`, `metrics.parquet`, `persistence_metrics.parquet`, `m1_resource_loss_history.parquet`, `m1_loss_balance_summary.csv`, `support_manifest.parquet`, `comparisons/`, `figures/`, `runtime/runtime_accounting.json`, and `validation/validation.json`.

## Phase 3C Decision

**MULTI_RESOURCE_FORECASTING_PREMISE_WEAK**
