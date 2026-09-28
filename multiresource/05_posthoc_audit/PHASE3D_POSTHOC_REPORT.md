# Phase 3D Post-Hoc Heterogeneity and Research-Direction Audit

## Evidentiary status

This audit is explicitly post-hoc and exploratory. All five outer folds were previously inspected. Protocol SHA-256: `c1ed2d6ae3ee3afe20c70b8561cc58d340c0ee70e0686e642f461b7e0f702da8`. Validation status: **PASS**.

## Frozen Phase 3C reproduction

| comparison | resource | gain_pct | absolute_mae_benefit |
|---|---|---|---|
| S2_vs_S1 | CPU | -3.3130 | -0.0599 |
| S2_vs_S1 | DISK_WRITE | -0.4923 | -15417.7002 |
| S2_vs_S1 | MEMORY | 0.8594 | 2733917.6663 |
| S2_vs_S1 | THROUGHPUT | -0.2428 | -0.0723 |
| M1_vs_S2 | CPU | 0.4696 | 0.0088 |
| M1_vs_S2 | DISK_WRITE | -0.7956 | -25037.1516 |
| M1_vs_S2 | MEMORY | -18.4769 | -58274148.1398 |
| M1_vs_S2 | THROUGHPUT | -0.8401 | -0.2509 |
| M1_vs_S1 | CPU | -2.8279 | -0.0511 |
| M1_vs_S1 | DISK_WRITE | -1.2918 | -40454.8518 |
| M1_vs_S1 | MEMORY | -17.4587 | -55540230.4736 |
| M1_vs_S1 | THROUGHPUT | -1.0849 | -0.3233 |

## Machine heterogeneity

Stable positive S2-vs-S1 machines: 4. Partial positive machines: 6.

| resource | machine | gain_pct | positive_folds | positive_leads | stability_label |
|---|---|---|---|---|---|
| DISK_WRITE | machine06 | 0.1677 | 4 | 8 | STABLE_POSITIVE_MACHINE |
| MEMORY | machine04 | 3.4446 | 4 | 7 | STABLE_POSITIVE_MACHINE |
| THROUGHPUT | machine02 | 2.7791 | 4 | 6 | STABLE_POSITIVE_MACHINE |
| THROUGHPUT | machine05 | 3.0575 | 4 | 6 | STABLE_POSITIVE_MACHINE |
| CPU | machine02 | 0.6961 | 3 | 5 | PARTIAL_POSITIVE_MACHINE |
| CPU | machine04 | 0.7915 | 3 | 6 | PARTIAL_POSITIVE_MACHINE |
| CPU | machine05 | 2.1982 | 3 | 8 | PARTIAL_POSITIVE_MACHINE |
| DISK_WRITE | machine07 | 0.1824 | 3 | 5 | PARTIAL_POSITIVE_MACHINE |
| MEMORY | machine01 | 12.4138 | 3 | 7 | PARTIAL_POSITIVE_MACHINE |
| THROUGHPUT | machine01 | 0.4457 | 4 | 4 | PARTIAL_POSITIVE_MACHINE |

## Horizon heterogeneity

- CPU: short:negative, medium:negative, long:negative
- THROUGHPUT: short:positive, medium:mixed, long:negative
- MEMORY: short:mixed, medium:positive, long:mixed
- DISK_WRITE: short:mixed, medium:negative, long:negative

## Fold heterogeneity

| resource | fold | gain_pct | positive_machines | positive_leads |
|---|---|---|---|---|
| CPU | 1 | -14.2132 | 2 | 0 |
| CPU | 2 | 3.4013 | 5 | 8 |
| CPU | 3 | 5.5407 | 6 | 6 |
| CPU | 4 | 1.2270 | 5 | 6 |
| CPU | 5 | -3.0502 | 0 | 0 |
| DISK_WRITE | 1 | -1.1923 | 5 | 0 |
| DISK_WRITE | 2 | -0.1908 | 5 | 2 |
| DISK_WRITE | 3 | -4.3737 | 0 | 0 |
| DISK_WRITE | 4 | -0.0047 | 4 | 2 |
| DISK_WRITE | 5 | 0.5244 | 4 | 7 |
| MEMORY | 1 | -8.6036 | 0 | 0 |
| MEMORY | 2 | 16.3789 | 4 | 8 |
| MEMORY | 3 | 11.9861 | 4 | 7 |
| MEMORY | 4 | -0.3817 | 4 | 4 |
| MEMORY | 5 | -5.4895 | 2 | 1 |
| THROUGHPUT | 1 | -2.7328 | 3 | 0 |
| THROUGHPUT | 2 | -2.7882 | 5 | 0 |
| THROUGHPUT | 3 | 1.6330 | 4 | 6 |
| THROUGHPUT | 4 | 0.9747 | 4 | 6 |
| THROUGHPUT | 5 | 1.3015 | 3 | 5 |

## Controlled regime heterogeneity

Stable controlled S2-vs-S1 patterns: 0. Partial patterns: 10.

| resource | descriptor | regime_bin | gain_pct | absolute_mae_benefit | coverage_fraction | positive_machine_count | positive_fold_count | pattern_classification |
|---|---|---|---|---|---|---|---|---|
| THROUGHPUT | throughput_level | HIGH | 0.4807 | 0.2429 | 0.3816 | 4 | 3 | PARTIAL_EXPLORATORY_PATTERN |
| THROUGHPUT | throughput_volatility | HIGH | 0.4284 | 0.2149 | 0.3336 | 4 | 3 | PARTIAL_EXPLORATORY_PATTERN |
| THROUGHPUT | cpu_volatility | LOW | 0.3025 | 0.0555 | 0.3366 | 3 | 3 | PARTIAL_EXPLORATORY_PATTERN |
| MEMORY | memory_level | HIGH | 1.7339 | 9134314.0505 | 0.5058 | 3 | 3 | PARTIAL_EXPLORATORY_PATTERN |
| MEMORY | memory_volatility | LOW | 5.4947 | 8886041.6963 | 0.3372 | 3 | 4 | PARTIAL_EXPLORATORY_PATTERN |
| MEMORY | memory_volatility | MID | 5.3528 | 10397900.5249 | 0.2810 | 3 | 3 | PARTIAL_EXPLORATORY_PATTERN |
| MEMORY | memory_change | LOW | 4.6357 | 7857953.9963 | 0.3615 | 3 | 4 | PARTIAL_EXPLORATORY_PATTERN |
| MEMORY | memory_change | MID | 5.8490 | 11809566.3348 | 0.2975 | 3 | 3 | PARTIAL_EXPLORATORY_PATTERN |
| MEMORY | cpu_level | LOW | 6.5588 | 12910856.9403 | 0.3055 | 4 | 3 | PARTIAL_EXPLORATORY_PATTERN |
| MEMORY | throughput_level | LOW | 10.9852 | 18582212.9289 | 0.2329 | 4 | 4 | PARTIAL_EXPLORATORY_PATTERN |

## Dependency versus benefit

Spearman associations below compare absolute training-side dependency with S2-versus-S1 test gain; they are non-causal.

| resource | predictor_resource | dependency_kind | dependency_gain_spearman |
|---|---|---|---|
| CPU | THROUGHPUT | difference | -0.0591 |
| CPU | THROUGHPUT | level | 0.1137 |
| DISK_WRITE | CPU | difference | 0.1143 |
| DISK_WRITE | CPU | level | 0.0048 |
| DISK_WRITE | THROUGHPUT | difference | 0.0857 |
| DISK_WRITE | THROUGHPUT | level | -0.0849 |
| MEMORY | CPU | difference | 0.2714 |
| MEMORY | CPU | level | 0.2882 |
| MEMORY | THROUGHPUT | difference | -0.2218 |
| MEMORY | THROUGHPUT | level | 0.5014 |
| THROUGHPUT | CPU | difference | 0.2359 |
| THROUGHPUT | CPU | level | 0.0434 |

## M1 loss share versus M1-S2 performance

These resource-specific Spearman relationships are descriptive only.

| resource | loss_share_gain_spearman | normalized_loss_gain_spearman | mean_loss_share | mean_m1_vs_s2_gain_pct |
|---|---|---|---|---|
| CPU | 0.1749 | 0.1172 | 0.4824 | -3.1148 |
| DISK_WRITE | -0.0627 | -0.0678 | 0.1177 | -0.8003 |
| MEMORY | 0.4134 | 0.1960 | 0.1367 | -36.1164 |
| THROUGHPUT | 0.1991 | 0.2326 | 0.2632 | -0.7917 |

## Context-length relationship

Selected-L equality/inequality is an association, not a causal intervention.

| comparison | resource | context_relationship | cell_count | gain_pct | absolute_mae_benefit | positive_cell_fraction |
|---|---|---|---|---|---|---|
| S2_vs_S1 | CPU | DIFFERENT | 112 | -6.9435 | -0.1826 | 0.4732 |
| S2_vs_S1 | CPU | MATCH | 168 | 1.7355 | 0.0219 | 0.4940 |
| S2_vs_S1 | DISK_WRITE | DIFFERENT | 104 | -1.8804 | -36516.2387 | 0.5192 |
| S2_vs_S1 | DISK_WRITE | MATCH | 176 | -0.0769 | -2950.3820 | 0.4716 |
| S2_vs_S1 | MEMORY | DIFFERENT | 152 | 1.8215 | 6608566.3333 | 0.3750 |
| S2_vs_S1 | MEMORY | MATCH | 128 | -0.7044 | -1867227.6259 | 0.5312 |
| S2_vs_S1 | THROUGHPUT | DIFFERENT | 128 | -0.9763 | -0.3543 | 0.5469 |
| S2_vs_S1 | THROUGHPUT | MATCH | 152 | 0.6788 | 0.1651 | 0.5132 |
| M1_vs_S2 | CPU | DIFFERENT | 176 | 1.1989 | 0.0199 | 0.3750 |
| M1_vs_S2 | CPU | MATCH | 104 | -0.4528 | -0.0101 | 0.3173 |
| M1_vs_S2 | DISK_WRITE | DIFFERENT | 176 | -0.6747 | -24252.5755 | 0.3580 |
| M1_vs_S2 | DISK_WRITE | MATCH | 104 | -1.1033 | -26364.8959 | 0.3269 |
| M1_vs_S2 | MEMORY | DIFFERENT | 136 | -38.6902 | -83468503.2863 | 0.0735 |
| M1_vs_S2 | MEMORY | MATCH | 144 | -8.4198 | -34479479.3904 | 0.2153 |
| M1_vs_S2 | THROUGHPUT | DIFFERENT | 192 | -0.9440 | -0.2752 | 0.3698 |
| M1_vs_S2 | THROUGHPUT | MATCH | 88 | -0.6297 | -0.1979 | 0.4773 |
| M1_vs_S1 | CPU | DIFFERENT | 192 | -3.9624 | -0.0704 | 0.4219 |
| M1_vs_S1 | CPU | MATCH | 88 | -0.4814 | -0.0090 | 0.3523 |
| M1_vs_S1 | DISK_WRITE | DIFFERENT | 176 | -1.2525 | -39109.8892 | 0.3409 |
| M1_vs_S1 | DISK_WRITE | MATCH | 104 | -1.3577 | -42730.9424 | 0.3750 |
| M1_vs_S1 | MEMORY | DIFFERENT | 144 | -9.5385 | -28899997.0882 | 0.1458 |
| M1_vs_S1 | MEMORY | MATCH | 136 | -25.0625 | -83747536.4110 | 0.1029 |
| M1_vs_S1 | THROUGHPUT | DIFFERENT | 160 | -0.4438 | -0.1219 | 0.4250 |
| M1_vs_S1 | THROUGHPUT | MATCH | 120 | -1.7989 | -0.5917 | 0.4750 |

## Memory failure decomposition

Native macro-MAE degradation M1 versus S2: 58274148.1398; mean cell-relative degradation: 38.4399%.

| dimension | positive_degradation_units | total_units |
|---|---|---|
| machines | 7 | 7 |
| folds | 4 | 5 |
| leads | 8 | 8 |

## M1 negative-transfer localization

No controlled M1-versus-S2 regime was stably positive; 3 were partially
positive. Memory degradation was present across all 7 machines, all 8 leads,
and 4/5 folds, so the memory failure is broad rather than confined to one
operating regime. Other resources show mixed cell-level pockets but no stable
shared-representation benefit.

| resource | descriptor | regime_bin | gain_pct | absolute_mae_benefit | coverage_fraction | positive_machine_count | positive_fold_count | pattern_classification |
|---|---|---|---|---|---|---|---|---|
| CPU | throughput_level | HIGH | 1.0626 | 0.0359 | 0.3816 | 3 | 4 | PARTIAL_EXPLORATORY_PATTERN |
| CPU | cpu_throughput_corr | MID | 1.1919 | 0.0195 | 0.3271 | 3 | 3 | PARTIAL_EXPLORATORY_PATTERN |
| THROUGHPUT | cpu_volatility | HIGH | 0.0546 | 0.0287 | 0.3473 | 4 | 3 | PARTIAL_EXPLORATORY_PATTERN |

## CPU special case

M1's small gain versus S2 is not evidence of beating S1. S2-versus-S1 and M1-versus-S1 CPU stability summaries remain the required local-baseline comparison.

| comparison | machine | gain_pct | positive_folds | positive_leads | stability_label |
|---|---|---|---|---|---|
| S2_vs_S1 | machine01 | -11.7804 | 3 | 0 | UNSTABLE_OR_NEGATIVE |
| S2_vs_S1 | machine02 | 0.6961 | 3 | 5 | PARTIAL_POSITIVE_MACHINE |
| S2_vs_S1 | machine03 | -0.8838 | 3 | 2 | UNSTABLE_OR_NEGATIVE |
| S2_vs_S1 | machine04 | 0.7915 | 3 | 6 | PARTIAL_POSITIVE_MACHINE |
| S2_vs_S1 | machine05 | 2.1982 | 3 | 8 | PARTIAL_POSITIVE_MACHINE |
| S2_vs_S1 | machine06 | -3.1812 | 1 | 1 | UNSTABLE_OR_NEGATIVE |
| S2_vs_S1 | machine07 | -4.7746 | 2 | 0 | UNSTABLE_OR_NEGATIVE |
| M1_vs_S1 | machine01 | -5.5954 | 2 | 0 | UNSTABLE_OR_NEGATIVE |
| M1_vs_S1 | machine02 | -6.1115 | 1 | 0 | UNSTABLE_OR_NEGATIVE |
| M1_vs_S1 | machine03 | -1.8209 | 2 | 2 | UNSTABLE_OR_NEGATIVE |
| M1_vs_S1 | machine04 | 0.5919 | 3 | 6 | PARTIAL_POSITIVE_MACHINE |
| M1_vs_S1 | machine05 | 1.5423 | 4 | 6 | STABLE_POSITIVE_MACHINE |
| M1_vs_S1 | machine06 | -7.9647 | 0 | 0 | UNSTABLE_OR_NEGATIVE |
| M1_vs_S1 | machine07 | -8.6570 | 2 | 0 | UNSTABLE_OR_NEGATIVE |

| comparison | lead | gain_pct | positive_machines | positive_folds |
|---|---|---|---|---|
| S2_vs_S1 | 1 | -7.1801 | 1 | 1 |
| S2_vs_S1 | 2 | -4.8713 | 1 | 1 |
| S2_vs_S1 | 4 | -3.5147 | 3 | 3 |
| S2_vs_S1 | 8 | -3.5073 | 3 | 3 |
| S2_vs_S1 | 16 | -3.7688 | 3 | 3 |
| S2_vs_S1 | 32 | -1.9766 | 4 | 3 |
| S2_vs_S1 | 64 | -1.5375 | 3 | 3 |
| S2_vs_S1 | 128 | -1.3763 | 4 | 3 |
| M1_vs_S1 | 1 | -7.2133 | 0 | 0 |
| M1_vs_S1 | 2 | -4.7382 | 1 | 0 |
| M1_vs_S1 | 4 | -3.1781 | 2 | 2 |
| M1_vs_S1 | 8 | -2.9936 | 2 | 2 |
| M1_vs_S1 | 16 | -3.0237 | 2 | 2 |
| M1_vs_S1 | 32 | -1.5359 | 2 | 3 |
| M1_vs_S1 | 64 | -1.0113 | 2 | 3 |
| M1_vs_S1 | 128 | -0.3610 | 3 | 3 |

## Throughput and disk-write boundary

Machine-level mixtures distinguish uniform small effects from cancelling positive and negative pockets.

| resource | machine | gain_pct | positive_folds | positive_leads | positive_cell_fraction | stability_label |
|---|---|---|---|---|---|---|
| DISK_WRITE | machine01 | -2.8620 | 1 | 0 | 0.2500 | UNSTABLE_OR_NEGATIVE |
| DISK_WRITE | machine02 | -1.0707 | 1 | 0 | 0.3500 | UNSTABLE_OR_NEGATIVE |
| DISK_WRITE | machine03 | -0.0695 | 4 | 2 | 0.5750 | UNSTABLE_OR_NEGATIVE |
| DISK_WRITE | machine04 | 0.1901 | 3 | 3 | 0.4250 | UNSTABLE_OR_NEGATIVE |
| DISK_WRITE | machine05 | -0.7921 | 2 | 0 | 0.4000 | UNSTABLE_OR_NEGATIVE |
| DISK_WRITE | machine06 | 0.1677 | 4 | 8 | 0.8500 | STABLE_POSITIVE_MACHINE |
| DISK_WRITE | machine07 | 0.1824 | 3 | 5 | 0.5750 | PARTIAL_POSITIVE_MACHINE |
| THROUGHPUT | machine01 | 0.4457 | 4 | 4 | 0.6750 | PARTIAL_POSITIVE_MACHINE |
| THROUGHPUT | machine02 | 2.7791 | 4 | 6 | 0.7750 | STABLE_POSITIVE_MACHINE |
| THROUGHPUT | machine03 | -1.2877 | 1 | 0 | 0.3000 | UNSTABLE_OR_NEGATIVE |
| THROUGHPUT | machine04 | -0.0563 | 2 | 0 | 0.3250 | UNSTABLE_OR_NEGATIVE |
| THROUGHPUT | machine05 | 3.0575 | 4 | 6 | 0.7500 | STABLE_POSITIVE_MACHINE |
| THROUGHPUT | machine06 | -0.2665 | 2 | 0 | 0.3750 | UNSTABLE_OR_NEGATIVE |
| THROUGHPUT | machine07 | -4.9590 | 2 | 0 | 0.5000 | UNSTABLE_OR_NEGATIVE |

## Post-hoc bootstrap uncertainty

These are POST-HOC BOOTSTRAP UNCERTAINTY INTERVALS, not confirmatory confidence intervals.

| comparison | resource | observed_gain_pct | lower_2_5_pct | upper_97_5_pct |
|---|---|---|---|---|
| S2_vs_S1 | CPU | -3.3130 | -15.0122 | 2.1246 |
| S2_vs_S1 | DISK_WRITE | -0.4923 | -3.1471 | 0.3829 |
| S2_vs_S1 | MEMORY | 0.8594 | -8.0232 | 11.6017 |
| S2_vs_S1 | THROUGHPUT | -0.2428 | -3.4060 | 2.0263 |
| M1_vs_S2 | CPU | 0.4696 | -4.8265 | 6.0221 |
| M1_vs_S2 | DISK_WRITE | -0.7956 | -1.8864 | 1.4694 |
| M1_vs_S2 | MEMORY | -18.4769 | -42.4724 | -7.1631 |
| M1_vs_S2 | THROUGHPUT | -0.8401 | -2.0689 | 0.4709 |
| M1_vs_S1 | CPU | -2.8279 | -9.6160 | 1.7040 |
| M1_vs_S1 | DISK_WRITE | -1.2918 | -2.2560 | -0.6240 |
| M1_vs_S1 | MEMORY | -17.4587 | -31.4726 | -8.9048 |
| M1_vs_S1 | THROUGHPUT | -1.0849 | -4.3645 | 1.6860 |

## Benefit concentration


| comparison | resource | positive_cell_fraction | fraction_cells_for_50pct | fraction_cells_for_80pct |
|---|---|---|---|---|
| M1_vs_S1 | CPU | 0.4000 | 0.0571 | 0.1250 |
| M1_vs_S1 | DISK_WRITE | 0.3536 | 0.0286 | 0.0643 |
| M1_vs_S1 | MEMORY | 0.1250 | 0.0250 | 0.0500 |
| M1_vs_S1 | THROUGHPUT | 0.4464 | 0.0857 | 0.1679 |
| M1_vs_S2 | CPU | 0.3536 | 0.0286 | 0.0964 |
| M1_vs_S2 | DISK_WRITE | 0.3464 | 0.0214 | 0.0500 |
| M1_vs_S2 | MEMORY | 0.1464 | 0.0214 | 0.0571 |
| M1_vs_S2 | THROUGHPUT | 0.4036 | 0.0464 | 0.1286 |
| S2_vs_S1 | CPU | 0.4857 | 0.0750 | 0.1857 |
| S2_vs_S1 | DISK_WRITE | 0.4893 | 0.0214 | 0.0536 |
| S2_vs_S1 | MEMORY | 0.4464 | 0.0357 | 0.1107 |
| S2_vs_S1 | THROUGHPUT | 0.5286 | 0.0821 | 0.1857 |

## Exploratory pattern classifications

Stable patterns: 0; partial patterns: 10; all remaining controlled patterns are unstable. These are exploratory labels only.

## Research-direction decision

**INCONCLUSIVE_POSTHOC_HETEROGENEITY**

Surviving hypothesis: None survived the stable exploratory rule. Ten partial
patterns remain exploratory pockets and are insufficient to define a
confirmatory target or regime hypothesis.

Any surviving or partial hypothesis requires an untouched temporal holdout, newly collected TimeTrack telemetry, an external compatible dataset, or another genuinely independent source. The five existing folds cannot provide untouched confirmation.

No implementation details or new architecture are proposed.
