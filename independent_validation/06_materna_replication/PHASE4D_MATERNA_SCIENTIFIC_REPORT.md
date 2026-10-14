# Phase 4D Materna Scientific Report

## 1. Provenance

This is the first authorized scientific inspection of the completed Materna predictive results. Inputs and hashes are frozen in `PHASE4D_MATERNA_SCIENTIFIC_ANALYSIS_PROVENANCE.md`. No model training occurred during analysis.

## 2. Aggregation semantics

Native MAE is seed-averaged inside matched trace/VM/fold/resource/lead/formulation cells. VM-fold cells are equally weighted; overall resource MacroMAE equally weights five horizons. Prediction-pooled and cell-relative results are diagnostics only.

## 3. Materna-T1 results

| comparison | resource | overall_primary_gain_percent | positive_horizons | positive_vms | positive_folds | positive_seed_aggregates | classification |
|---|---|---|---|---|---|---|---|
| S2_vs_S1 | CPU | -4.317958 | 0 | 15 | 1 | 0 | NEUTRAL_OR_MIXED |
| S2_vs_S1 | THROUGHPUT | 0.986935 | 3 | 18 | 3 | 2 | CONDITIONALLY_POSITIVE |
| S2_vs_S1 | MEMORY | -0.019692 | 2 | 22 | 4 | 1 | NEUTRAL_OR_MIXED |
| S2_vs_S1 | DISK_WRITE | -6.699662 | 0 | 18 | 2 | 0 | NEUTRAL_OR_MIXED |
| M1_vs_S2 | CPU | 0.882699 | 4 | 14 | 4 | 2 | NEUTRAL_OR_MIXED |
| M1_vs_S2 | THROUGHPUT | -7.308355 | 0 | 5 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S2 | MEMORY | -13.218360 | 0 | 4 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S2 | DISK_WRITE | -27.457746 | 0 | 7 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S1 | CPU | -3.397145 | 0 | 14 | 1 | 0 | NEUTRAL_OR_MIXED |
| M1_vs_S1 | THROUGHPUT | -6.249291 | 0 | 9 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S1 | MEMORY | -13.240655 | 0 | 13 | 0 | 0 | NEUTRAL_OR_MIXED |
| M1_vs_S1 | DISK_WRITE | -35.996983 | 0 | 6 | 0 | 0 | BROAD_NEGATIVE |

Trace decisions:

- S2 vs S1: `CROSS_RESOURCE_INPUT_NOT_SUPPORTED` — frozen non-support predicate applied
- M1 vs S2: `SHARED_REPRESENTATION_NOT_SUPPORTED` — at most one positive resource and nonpositive equal-resource mean
- M1 vs S1: `JOINT_SYSTEM_BROADLY_HARMFUL`

## 4. Materna-T2 results

| comparison | resource | overall_primary_gain_percent | positive_horizons | positive_vms | positive_folds | positive_seed_aggregates | classification |
|---|---|---|---|---|---|---|---|
| S2_vs_S1 | CPU | 4.207624 | 5 | 27 | 5 | 3 | BROAD_POSITIVE |
| S2_vs_S1 | THROUGHPUT | 0.294315 | 2 | 23 | 3 | 2 | NEUTRAL_OR_MIXED |
| S2_vs_S1 | MEMORY | 3.948171 | 5 | 27 | 5 | 3 | BROAD_POSITIVE |
| S2_vs_S1 | DISK_WRITE | -1.120181 | 1 | 17 | 3 | 0 | NEUTRAL_OR_MIXED |
| M1_vs_S2 | CPU | -2.564363 | 0 | 10 | 1 | 0 | BROAD_NEGATIVE |
| M1_vs_S2 | THROUGHPUT | -8.692761 | 0 | 5 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S2 | MEMORY | -9.266823 | 0 | 6 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S2 | DISK_WRITE | -7.888503 | 0 | 6 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S1 | CPU | 1.751160 | 4 | 19 | 4 | 3 | CONDITIONALLY_POSITIVE |
| M1_vs_S1 | THROUGHPUT | -8.372862 | 1 | 14 | 0 | 0 | NEUTRAL_OR_MIXED |
| M1_vs_S1 | MEMORY | -4.952782 | 0 | 11 | 0 | 0 | NEUTRAL_OR_MIXED |
| M1_vs_S1 | DISK_WRITE | -9.097050 | 0 | 7 | 0 | 0 | BROAD_NEGATIVE |

Trace decisions:

- S2 vs S1: `CROSS_RESOURCE_INPUT_MIXED` — neither frozen support nor non-support predicate applied
- M1 vs S2: `SHARED_REPRESENTATION_NOT_SUPPORTED` — at most one positive resource and nonpositive equal-resource mean
- M1 vs S1: `JOINT_SYSTEM_BROADLY_HARMFUL`

## 5. Materna-T3 results

| comparison | resource | overall_primary_gain_percent | positive_horizons | positive_vms | positive_folds | positive_seed_aggregates | classification |
|---|---|---|---|---|---|---|---|
| S2_vs_S1 | CPU | -2.787548 | 0 | 17 | 4 | 2 | NEUTRAL_OR_MIXED |
| S2_vs_S1 | THROUGHPUT | 0.044766 | 3 | 15 | 2 | 1 | NEUTRAL_OR_MIXED |
| S2_vs_S1 | MEMORY | 3.089002 | 5 | 22 | 5 | 3 | CONDITIONALLY_POSITIVE |
| S2_vs_S1 | DISK_WRITE | 1.907168 | 5 | 18 | 3 | 2 | CONDITIONALLY_POSITIVE |
| M1_vs_S2 | CPU | -8.099015 | 0 | 13 | 0 | 0 | NEUTRAL_OR_MIXED |
| M1_vs_S2 | THROUGHPUT | -7.914278 | 0 | 8 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S2 | MEMORY | -8.702593 | 0 | 6 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S2 | DISK_WRITE | -71.295095 | 0 | 3 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S1 | CPU | -11.112327 | 0 | 10 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S1 | THROUGHPUT | -7.865970 | 0 | 5 | 0 | 0 | BROAD_NEGATIVE |
| M1_vs_S1 | MEMORY | -5.344768 | 0 | 13 | 0 | 0 | NEUTRAL_OR_MIXED |
| M1_vs_S1 | DISK_WRITE | -68.028209 | 0 | 9 | 0 | 0 | BROAD_NEGATIVE |

Trace decisions:

- S2 vs S1: `CROSS_RESOURCE_INPUT_MIXED` — neither frozen support nor non-support predicate applied
- M1 vs S2: `SHARED_REPRESENTATION_NOT_SUPPORTED` — at most one positive resource and nonpositive equal-resource mean
- M1 vs S1: `JOINT_SYSTEM_BROADLY_HARMFUL`

## 6. Bootstrap

| trace | comparison | resource | lower_2_5_percent | median_percent | upper_97_5_percent |
|---|---|---|---|---|---|
| Materna-T1 | S2_vs_S1 | CPU | -8.507541 | -4.217930 | -0.183132 |
| Materna-T1 | S2_vs_S1 | THROUGHPUT | -1.958157 | 0.869248 | 5.213276 |
| Materna-T1 | S2_vs_S1 | MEMORY | -5.531625 | 0.291571 | 4.509772 |
| Materna-T1 | S2_vs_S1 | DISK_WRITE | -28.002811 | -6.035990 | 3.977370 |
| Materna-T1 | M1_vs_S2 | CPU | -2.573616 | 0.725901 | 4.503487 |
| Materna-T1 | M1_vs_S2 | THROUGHPUT | -10.413407 | -7.243660 | -3.988227 |
| Materna-T1 | M1_vs_S2 | MEMORY | -23.574678 | -12.729278 | -4.869169 |
| Materna-T1 | M1_vs_S2 | DISK_WRITE | -119.728200 | -25.390232 | -0.769377 |
| Materna-T1 | M1_vs_S1 | CPU | -6.437362 | -3.289214 | -0.981578 |
| Materna-T1 | M1_vs_S1 | THROUGHPUT | -9.442352 | -6.207515 | -2.070284 |
| Materna-T1 | M1_vs_S1 | MEMORY | -22.226177 | -12.885736 | -4.209839 |
| Materna-T1 | M1_vs_S1 | DISK_WRITE | -132.790238 | -33.534856 | -3.161794 |
| Materna-T2 | S2_vs_S1 | CPU | 0.594606 | 4.185031 | 7.410353 |
| Materna-T2 | S2_vs_S1 | THROUGHPUT | -5.102338 | 0.179829 | 4.632397 |
| Materna-T2 | S2_vs_S1 | MEMORY | 0.349406 | 3.920283 | 6.946000 |
| Materna-T2 | S2_vs_S1 | DISK_WRITE | -5.676732 | -0.959128 | 1.709059 |
| Materna-T2 | M1_vs_S2 | CPU | -5.299874 | -2.613604 | -0.287428 |
| Materna-T2 | M1_vs_S2 | THROUGHPUT | -13.358700 | -8.477224 | -2.420657 |
| Materna-T2 | M1_vs_S2 | MEMORY | -17.038766 | -9.070268 | -4.192264 |
| Materna-T2 | M1_vs_S2 | DISK_WRITE | -12.413613 | -7.792907 | -3.999305 |
| Materna-T2 | M1_vs_S1 | CPU | -3.520298 | 1.678098 | 6.065077 |
| Materna-T2 | M1_vs_S1 | THROUGHPUT | -12.782691 | -8.272150 | -3.453738 |
| Materna-T2 | M1_vs_S1 | MEMORY | -13.590910 | -4.926133 | 1.068959 |
| Materna-T2 | M1_vs_S1 | DISK_WRITE | -14.732454 | -9.111197 | -4.143627 |
| Materna-T3 | S2_vs_S1 | CPU | -14.647369 | -2.152477 | 3.807079 |
| Materna-T3 | S2_vs_S1 | THROUGHPUT | -2.253080 | -0.080161 | 4.718064 |
| Materna-T3 | S2_vs_S1 | MEMORY | -0.187203 | 3.082681 | 6.558171 |
| Materna-T3 | S2_vs_S1 | DISK_WRITE | -1.919858 | 1.945229 | 6.483796 |
| Materna-T3 | M1_vs_S2 | CPU | -16.409493 | -7.876955 | -2.280011 |
| Materna-T3 | M1_vs_S2 | THROUGHPUT | -12.547591 | -7.723343 | -1.973290 |
| Materna-T3 | M1_vs_S2 | MEMORY | -14.684325 | -8.602040 | -4.110036 |
| Materna-T3 | M1_vs_S2 | DISK_WRITE | -239.631147 | -66.894190 | -5.936909 |
| Materna-T3 | M1_vs_S1 | CPU | -31.106957 | -10.127454 | -0.612997 |
| Materna-T3 | M1_vs_S1 | THROUGHPUT | -11.941162 | -7.640640 | -2.198659 |
| Materna-T3 | M1_vs_S1 | MEMORY | -11.001011 | -5.385166 | 0.016658 |
| Materna-T3 | M1_vs_S1 | DISK_WRITE | -226.236474 | -63.809054 | -4.622369 |

## 7. Persistence

| trace | formulation | resource | persistence_skill | beats_persistence |
|---|---|---|---|---|
| Materna-T1 | M1 | CPU | 0.088852 | True |
| Materna-T1 | M1 | DISK_WRITE | -1.758953 | False |
| Materna-T1 | M1 | MEMORY | 0.276180 | True |
| Materna-T1 | M1 | THROUGHPUT | -0.060838 | False |
| Materna-T1 | S1 | CPU | 0.118963 | True |
| Materna-T1 | S1 | DISK_WRITE | 0.173869 | True |
| Materna-T1 | S1 | MEMORY | 0.319763 | True |
| Materna-T1 | S1 | THROUGHPUT | -0.143269 | False |
| Materna-T1 | S2 | CPU | 0.050980 | True |
| Materna-T1 | S2 | DISK_WRITE | 0.154283 | True |
| Materna-T1 | S2 | MEMORY | 0.322302 | True |
| Materna-T1 | S2 | THROUGHPUT | 0.081347 | True |
| Materna-T2 | M1 | CPU | 0.190974 | True |
| Materna-T2 | M1 | DISK_WRITE | 0.368236 | True |
| Materna-T2 | M1 | MEMORY | 0.267503 | True |
| Materna-T2 | M1 | THROUGHPUT | 0.245664 | True |
| Materna-T2 | S1 | CPU | 0.199651 | True |
| Materna-T2 | S1 | DISK_WRITE | 0.405716 | True |
| Materna-T2 | S1 | MEMORY | 0.322750 | True |
| Materna-T2 | S1 | THROUGHPUT | 0.301309 | True |
| Materna-T2 | S2 | CPU | 0.223126 | True |
| Materna-T2 | S2 | DISK_WRITE | 0.392817 | True |
| Materna-T2 | S2 | MEMORY | 0.329413 | True |
| Materna-T2 | S2 | THROUGHPUT | 0.314746 | True |
| Materna-T3 | M1 | CPU | 0.005393 | True |
| Materna-T3 | M1 | DISK_WRITE | -1.349340 | False |
| Materna-T3 | M1 | MEMORY | 0.218590 | True |
| Materna-T3 | M1 | THROUGHPUT | -0.262904 | False |
| Materna-T3 | S1 | CPU | 0.140544 | True |
| Materna-T3 | S1 | DISK_WRITE | 0.233905 | True |
| Materna-T3 | S1 | MEMORY | 0.261037 | True |
| Materna-T3 | S1 | THROUGHPUT | 0.025915 | True |
| Materna-T3 | S2 | CPU | 0.103629 | True |
| Materna-T3 | S2 | DISK_WRITE | 0.208474 | True |
| Materna-T3 | S2 | MEMORY | 0.270899 | True |
| Materna-T3 | S2 | THROUGHPUT | 0.059412 | True |

Overall cells beating persistence — Materna-T1 M1: CPU, MEMORY; Materna-T1 S1: CPU, DISK_WRITE, MEMORY; Materna-T1 S2: CPU, DISK_WRITE, MEMORY, THROUGHPUT; Materna-T2 M1: CPU, DISK_WRITE, MEMORY, THROUGHPUT; Materna-T2 S1: CPU, DISK_WRITE, MEMORY, THROUGHPUT; Materna-T2 S2: CPU, DISK_WRITE, MEMORY, THROUGHPUT; Materna-T3 M1: CPU, MEMORY; Materna-T3 S1: CPU, DISK_WRITE, MEMORY, THROUGHPUT; Materna-T3 S2: CPU, DISK_WRITE, MEMORY, THROUGHPUT.

Overall cells not beating persistence — Materna-T1 M1: DISK_WRITE, THROUGHPUT; Materna-T1 S1: THROUGHPUT; Materna-T1 S2: none; Materna-T2 M1: none; Materna-T2 S1: none; Materna-T2 S2: none; Materna-T3 M1: DISK_WRITE, THROUGHPUT; Materna-T3 S1: none; Materna-T3 S2: none.

Across trace-resource overall aggregates, universally persistence-positive formulations: S2. S2 is positive in all 12 overall trace-resource cells.

Across every trace-resource-lead cell, universally persistence-positive formulations: none.

Persistence is an absolute forecasting sanity check and does not redefine R1-R4. Relative formulation improvements do not imply absolute superiority over persistence.

## 8. Temporal synthesis

| comparison | resource | Materna-T1 | Materna-T2 | Materna-T3 | equal_temporal_block_gain_percent | sign_pattern | max_minus_min_temporal_spread_percent |
|---|---|---|---|---|---|---|---|
| M1_vs_S1 | CPU | -3.397145 | 1.751160 | -11.112327 | -4.252770 | -/+/- | 12.863487 |
| M1_vs_S1 | DISK_WRITE | -35.996983 | -9.097050 | -68.028209 | -37.707414 | -/-/- | 58.931159 |
| M1_vs_S1 | MEMORY | -13.240655 | -4.952782 | -5.344768 | -7.846069 | -/-/- | 8.287873 |
| M1_vs_S1 | THROUGHPUT | -6.249291 | -8.372862 | -7.865970 | -7.496041 | -/-/- | 2.123571 |
| M1_vs_S2 | CPU | 0.882699 | -2.564363 | -8.099015 | -3.260227 | +/-/- | 8.981714 |
| M1_vs_S2 | DISK_WRITE | -27.457746 | -7.888503 | -71.295095 | -35.547114 | -/-/- | 63.406591 |
| M1_vs_S2 | MEMORY | -13.218360 | -9.266823 | -8.702593 | -10.395925 | -/-/- | 4.515767 |
| M1_vs_S2 | THROUGHPUT | -7.308355 | -8.692761 | -7.914278 | -7.971798 | -/-/- | 1.384406 |
| S2_vs_S1 | CPU | -4.317958 | 4.207624 | -2.787548 | -0.965960 | -/+/- | 8.525582 |
| S2_vs_S1 | DISK_WRITE | -6.699662 | -1.120181 | 1.907168 | -1.970892 | -/-/+ | 8.606830 |
| S2_vs_S1 | MEMORY | -0.019692 | 3.948171 | 3.089002 | 2.339160 | -/+/+ | 3.967863 |
| S2_vs_S1 | THROUGHPUT | 0.986935 | 0.294315 | 0.044766 | 0.442006 | +/+/+ | 0.942170 |

## 9. R1

`R1_RESOURCE_TEMPORAL_DEPENDENCE_CONFIRMED` — broad benefit failed and frozen temporal-dependence criteria applied

## 10. R2

`R2_NEGATIVE_SHARING_REPLICATED` — zero supported traces, at most one conditional trace, nonpositive synthesized mean, and at most one positive synthesized resource

## 11. R3

`R3_JOINT_SYSTEM_UNDERPERFORMANCE_REPLICATED` — all four synthesized gains are negative and at least two traces are broadly harmful

## 12. R4

`R4_TEMPORAL_HETEROGENEITY_CONFIRMED` — at least two resource/comparison classes vary or a frozen global trace decision differs

Resource/comparison class changes: `7`. Raw sign reversals: `5`. S2 global decisions differ: `True`. M1 global decisions differ: `False`.

| comparison | resource | Materna-T1_classification | Materna-T2_classification | Materna-T3_classification | Materna-T1_gain_percent | Materna-T2_gain_percent | Materna-T3_gain_percent | temporally_classification_variable | raw_sign_reversal |
|---|---|---|---|---|---|---|---|---|---|
| S2_vs_S1 | CPU | NEUTRAL_OR_MIXED | BROAD_POSITIVE | NEUTRAL_OR_MIXED | -4.317958 | 4.207624 | -2.787548 | True | True |
| S2_vs_S1 | THROUGHPUT | CONDITIONALLY_POSITIVE | NEUTRAL_OR_MIXED | NEUTRAL_OR_MIXED | 0.986935 | 0.294315 | 0.044766 | True | False |
| S2_vs_S1 | MEMORY | NEUTRAL_OR_MIXED | BROAD_POSITIVE | CONDITIONALLY_POSITIVE | -0.019692 | 3.948171 | 3.089002 | True | True |
| S2_vs_S1 | DISK_WRITE | NEUTRAL_OR_MIXED | NEUTRAL_OR_MIXED | CONDITIONALLY_POSITIVE | -6.699662 | -1.120181 | 1.907168 | True | True |
| M1_vs_S2 | CPU | NEUTRAL_OR_MIXED | BROAD_NEGATIVE | NEUTRAL_OR_MIXED | 0.882699 | -2.564363 | -8.099015 | True | True |
| M1_vs_S2 | THROUGHPUT | BROAD_NEGATIVE | BROAD_NEGATIVE | BROAD_NEGATIVE | -7.308355 | -8.692761 | -7.914278 | False | False |
| M1_vs_S2 | MEMORY | BROAD_NEGATIVE | BROAD_NEGATIVE | BROAD_NEGATIVE | -13.218360 | -9.266823 | -8.702593 | False | False |
| M1_vs_S2 | DISK_WRITE | BROAD_NEGATIVE | BROAD_NEGATIVE | BROAD_NEGATIVE | -27.457746 | -7.888503 | -71.295095 | False | False |
| M1_vs_S1 | CPU | NEUTRAL_OR_MIXED | CONDITIONALLY_POSITIVE | BROAD_NEGATIVE | -3.397145 | 1.751160 | -11.112327 | True | True |
| M1_vs_S1 | THROUGHPUT | BROAD_NEGATIVE | NEUTRAL_OR_MIXED | BROAD_NEGATIVE | -6.249291 | -8.372862 | -7.865970 | True | False |
| M1_vs_S1 | MEMORY | NEUTRAL_OR_MIXED | NEUTRAL_OR_MIXED | NEUTRAL_OR_MIXED | -13.240655 | -4.952782 | -5.344768 | False | False |
| M1_vs_S1 | DISK_WRITE | BROAD_NEGATIVE | BROAD_NEGATIVE | BROAD_NEGATIVE | -35.996983 | -9.097050 | -68.028209 | False | False |

## 13. M1 loss balance

| trace | resource | mean_percent | median_percent |
|---|---|---|---|
| Materna-T1 | CPU | 49.322575 | 51.085206 |
| Materna-T1 | DISK_WRITE | 18.178900 | 11.606897 |
| Materna-T1 | MEMORY | 18.224778 | 10.756030 |
| Materna-T1 | THROUGHPUT | 14.273747 | 5.760236 |
| Materna-T2 | CPU | 40.930648 | 37.776859 |
| Materna-T2 | DISK_WRITE | 21.477012 | 14.535965 |
| Materna-T2 | MEMORY | 20.019186 | 14.720477 |
| Materna-T2 | THROUGHPUT | 17.573155 | 11.832334 |
| Materna-T3 | CPU | 49.121690 | 57.670780 |
| Materna-T3 | DISK_WRITE | 17.863643 | 8.077422 |
| Materna-T3 | MEMORY | 15.791133 | 14.131010 |
| Materna-T3 | THROUGHPUT | 17.223535 | 7.058228 |

Reference means: TimeTrack CPU 48.24%, throughput 26.32%, memory 13.67%, disk-write 11.77%; fastStorage 37.885905%, 13.493035%, 25.708970%, 22.912090%; Rnd 26.950113%, 33.243624%, 15.811861%, 23.994402%. The comparison is descriptive and not causal.

## 14. Efficiency

| formulation | parameters | models_per_target_set | actual_Materna_fit_hours | parameter_reduction_vs_S2_percent | model_count_reduction_vs_S2_percent |
|---|---|---|---|---|---|
| S1 | 203028 | 4 | 85.594240 | 1.490539 | 0.000000 |
| S2 | 206100 | 4 | 75.303186 | 0.000000 | 0.000000 |
| M1 | 52500 | 1 | 20.405083 | 74.526929 | 75.000000 |

M1 uses 52,500 parameters versus 206,100 for S2, a 74.526929% reduction, and one model versus four, a 75% model-count reduction. Efficiency and accuracy are separate conclusions.

## 15. Population boundary

Structural common pool: 398. Training-scale eligible: 74. Selected: 35. Retention: 18.5930%. Results apply only to structurally valid VMs with nondegenerate four-resource training variability across every scientific scaler-fit partition in all three temporal blocks; they do not generalize to the complete Materna population.

## 16. TimeTrack comparison

| comparison | resource | TimeTrack_gain_percent | Materna-T1_gain_percent | Materna-T2_gain_percent | Materna-T3_gain_percent | Materna_equal_temporal_block_gain_percent |
|---|---|---|---|---|---|---|
| S2_vs_S1 | CPU | -3.313000 | -4.317958 | 4.207624 | -2.787548 | -0.965960 |
| S2_vs_S1 | THROUGHPUT | -0.242800 | 0.986935 | 0.294315 | 0.044766 | 0.442006 |
| S2_vs_S1 | MEMORY | 0.859400 | -0.019692 | 3.948171 | 3.089002 | 2.339160 |
| S2_vs_S1 | DISK_WRITE | -0.492300 | -6.699662 | -1.120181 | 1.907168 | -1.970892 |
| M1_vs_S2 | CPU | 0.469600 | 0.882699 | -2.564363 | -8.099015 | -3.260227 |
| M1_vs_S2 | THROUGHPUT | -0.840100 | -7.308355 | -8.692761 | -7.914278 | -7.971798 |
| M1_vs_S2 | MEMORY | -18.476900 | -13.218360 | -9.266823 | -8.702593 | -10.395925 |
| M1_vs_S2 | DISK_WRITE | -0.795600 | -27.457746 | -7.888503 | -71.295095 | -35.547114 |
| M1_vs_S1 | CPU | -2.827900 | -3.397145 | 1.751160 | -11.112327 | -4.252770 |
| M1_vs_S1 | THROUGHPUT | -1.084900 | -6.249291 | -8.372862 | -7.865970 | -7.496041 |
| M1_vs_S1 | MEMORY | -17.458700 | -13.240655 | -4.952782 | -5.344768 | -7.846069 |
| M1_vs_S1 | DISK_WRITE | -1.291800 | -35.996983 | -9.097050 | -68.028209 | -37.707414 |

## 17. Bitbrains comparison

| comparison | resource | fastStorage_gain_percent | Rnd_gain_percent | Bitbrains_equal_environment_gain_percent | Materna_equal_temporal_block_gain_percent |
|---|---|---|---|---|---|
| S2_vs_S1 | CPU | -3.198519 | 1.412867 | -0.892826 | -0.965960 |
| S2_vs_S1 | THROUGHPUT | 0.012731 | -7.214491 | -3.600880 | 0.442006 |
| S2_vs_S1 | MEMORY | 2.449985 | 1.673083 | 2.061534 | 2.339160 |
| S2_vs_S1 | DISK_WRITE | 2.689207 | 0.160400 | 1.424804 | -1.970892 |
| M1_vs_S2 | CPU | 0.045047 | -16.509941 | -8.232447 | -3.260227 |
| M1_vs_S2 | THROUGHPUT | -27.094152 | -14.318987 | -20.706570 | -7.971798 |
| M1_vs_S2 | MEMORY | -4.867061 | -8.915737 | -6.891399 | -10.395925 |
| M1_vs_S2 | DISK_WRITE | -4.072129 | -5.551233 | -4.811681 | -35.547114 |
| M1_vs_S1 | CPU | -3.152031 | -14.863811 | -9.007921 | -4.252770 |
| M1_vs_S1 | THROUGHPUT | -27.077972 | -22.566520 | -24.822246 | -7.496041 |
| M1_vs_S1 | MEMORY | -2.297834 | -7.093487 | -4.695660 | -7.846069 |
| M1_vs_S1 | DISK_WRITE | -1.273414 | -5.381929 | -3.327672 | -37.707414 |

## 18. Complete cross-study synthesis

| comparison | resource | TimeTrack_gain_percent | fastStorage_gain_percent | Rnd_gain_percent | Bitbrains_equal_environment_gain_percent | fastStorage_classification | Rnd_classification | Bitbrains_classification_consistency | Materna-T1_gain_percent | Materna-T2_gain_percent | Materna-T3_gain_percent | Materna_equal_temporal_block_gain_percent | all_six_environment_sign_consistency | environment_or_time_dependence | Materna-T1_classification | Materna-T2_classification | Materna-T3_classification | Materna_classification_consistency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S2_vs_S1 | CPU | -3.313000 | -3.198519 | 1.412867 | -0.892826 | NEUTRAL_OR_MIXED | CONDITIONALLY_POSITIVE | False | -4.317958 | 4.207624 | -2.787548 | -0.965960 | False | True | NEUTRAL_OR_MIXED | BROAD_POSITIVE | NEUTRAL_OR_MIXED | False |
| S2_vs_S1 | THROUGHPUT | -0.242800 | 0.012731 | -7.214491 | -3.600880 | NEUTRAL_OR_MIXED | NEUTRAL_OR_MIXED | True | 0.986935 | 0.294315 | 0.044766 | 0.442006 | False | True | CONDITIONALLY_POSITIVE | NEUTRAL_OR_MIXED | NEUTRAL_OR_MIXED | False |
| S2_vs_S1 | MEMORY | 0.859400 | 2.449985 | 1.673083 | 2.061534 | BROAD_POSITIVE | CONDITIONALLY_POSITIVE | False | -0.019692 | 3.948171 | 3.089002 | 2.339160 | False | True | NEUTRAL_OR_MIXED | BROAD_POSITIVE | CONDITIONALLY_POSITIVE | False |
| S2_vs_S1 | DISK_WRITE | -0.492300 | 2.689207 | 0.160400 | 1.424804 | CONDITIONALLY_POSITIVE | NEUTRAL_OR_MIXED | False | -6.699662 | -1.120181 | 1.907168 | -1.970892 | False | True | NEUTRAL_OR_MIXED | NEUTRAL_OR_MIXED | CONDITIONALLY_POSITIVE | False |
| M1_vs_S2 | CPU | 0.469600 | 0.045047 | -16.509941 | -8.232447 | NEUTRAL_OR_MIXED | BROAD_NEGATIVE | False | 0.882699 | -2.564363 | -8.099015 | -3.260227 | False | True | NEUTRAL_OR_MIXED | BROAD_NEGATIVE | NEUTRAL_OR_MIXED | False |
| M1_vs_S2 | THROUGHPUT | -0.840100 | -27.094152 | -14.318987 | -20.706570 | BROAD_NEGATIVE | BROAD_NEGATIVE | True | -7.308355 | -8.692761 | -7.914278 | -7.971798 | True | False | BROAD_NEGATIVE | BROAD_NEGATIVE | BROAD_NEGATIVE | True |
| M1_vs_S2 | MEMORY | -18.476900 | -4.867061 | -8.915737 | -6.891399 | BROAD_NEGATIVE | BROAD_NEGATIVE | True | -13.218360 | -9.266823 | -8.702593 | -10.395925 | True | False | BROAD_NEGATIVE | BROAD_NEGATIVE | BROAD_NEGATIVE | True |
| M1_vs_S2 | DISK_WRITE | -0.795600 | -4.072129 | -5.551233 | -4.811681 | BROAD_NEGATIVE | BROAD_NEGATIVE | True | -27.457746 | -7.888503 | -71.295095 | -35.547114 | True | False | BROAD_NEGATIVE | BROAD_NEGATIVE | BROAD_NEGATIVE | True |
| M1_vs_S1 | CPU | -2.827900 | -3.152031 | -14.863811 | -9.007921 | BROAD_NEGATIVE | BROAD_NEGATIVE | True | -3.397145 | 1.751160 | -11.112327 | -4.252770 | False | True | NEUTRAL_OR_MIXED | CONDITIONALLY_POSITIVE | BROAD_NEGATIVE | False |
| M1_vs_S1 | THROUGHPUT | -1.084900 | -27.077972 | -22.566520 | -24.822246 | BROAD_NEGATIVE | BROAD_NEGATIVE | True | -6.249291 | -8.372862 | -7.865970 | -7.496041 | True | False | BROAD_NEGATIVE | NEUTRAL_OR_MIXED | BROAD_NEGATIVE | False |
| M1_vs_S1 | MEMORY | -17.458700 | -2.297834 | -7.093487 | -4.695660 | NEUTRAL_OR_MIXED | BROAD_NEGATIVE | False | -13.240655 | -4.952782 | -5.344768 | -7.846069 | True | False | NEUTRAL_OR_MIXED | NEUTRAL_OR_MIXED | NEUTRAL_OR_MIXED | True |
| M1_vs_S1 | DISK_WRITE | -1.291800 | -1.273414 | -5.381929 | -3.327672 | NEUTRAL_OR_MIXED | BROAD_NEGATIVE | False | -35.996983 | -9.097050 | -68.028209 | -37.707414 | True | False | BROAD_NEGATIVE | BROAD_NEGATIVE | BROAD_NEGATIVE | True |

No pooled global score was calculated across TimeTrack, Bitbrains, and Materna. Synthesis is descriptive direction/classification consistency only.
The strongest repeated negative-transfer result is M1_vs_S1 for DISK_WRITE: it is negative in TimeTrack, both Bitbrains environments, and all three Materna blocks (six-source mean -20.178231%).
The strongest repeated positive/context result is S2 vs S1 for memory: it is positive in TimeTrack, both Bitbrains environments, Materna T2, and Materna T3, while Materna T1 is -0.019692%; therefore it is repeated but not universal.

## 19. Final cross-resource boundary

`CROSS_RESOURCE_BOUNDARY_STRENGTHENED`

## 20. Final shared-representation boundary

`SHARED_REPRESENTATION_BOUNDARY_STRENGTHENED`

## 21. Final joint-system boundary

`JOINT_SYSTEM_UNDERPERFORMANCE_STRENGTHENED`

## 22. Final paper-scope gate

`MULTIDATASET_TEMPORAL_BOUNDARY_STUDY_STRONGLY_SUPPORTED`

## 23. Stop-experimentation decision

`STOP_EXPERIMENTATION_AND_WRITE`

Exactly 12 diagnostic scientific figures were generated. Model training during analysis: `0`.

