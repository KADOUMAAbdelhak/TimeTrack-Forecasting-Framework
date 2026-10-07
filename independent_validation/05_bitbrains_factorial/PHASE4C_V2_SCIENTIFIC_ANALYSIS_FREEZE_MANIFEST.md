# Phase 4C V2 Scientific-Analysis Freeze Manifest

## Freeze identity and scope

- Freeze date: 2026-10-07 (Europe/Helsinki)
- Pre-freeze execution commit: `549020a1a0b19d3c633d21cd13d2c8ff007225f1`
- Pre-freeze execution tag: `phase4c-v2-dual-environment-execution-freeze-v1`
- Analysis status: `PASS`
- Bootstrap seed: `20261007`
- Bootstrap replicates per family: `10000`
- Scientific figures: `12 / 12`
- Materna executions: `0`
- New post-Phase4C architecture implementations: `0`

This checkpoint freezes the completed external-confirmation analysis only. It does not pool the two Bitbrains environments and does not pool Bitbrains with TimeTrack. The synthesis values below are equal-environment means.

**NO MODEL TRAINING OCCURRED DURING ANALYSIS.**

## Protected provenance and hashes

| Protected identity | SHA-256 |
|---|---|
| V2 scientific config | `627391b84887411d8b930fd5d00cdd9a1f90f3990f958d582f4329424353fa4e` |
| prospective scientific criteria | `79df6a168d7021dbafd6080640a506d22699e9d4989d422f924b178600465f12` |
| execution-correction decision | `bd0a51380409290dd9deefd2cf25bbc783b018b559121bd21ba37fdfcb07e86d` |
| heavy execution inventory | `42e085403d331bc903afd484582bf4d57c68477513ef6a948c3d40c2c5cf4377` |
| execution tree | `deeea76548071f08915d2c80944da4a196e1032e62a918c6e5753dd887e0c1c0` |
| compact execution-checkpoint inventory | `44a22a8f9699b407bbb0c239d990d204e097ddd05ea389ab33de8d7c38bbc58b` |
| compact execution-checkpoint tree | `8e4310b4ae2ae0cd2644f418b1734abb97b80ef28b354252573084992ded96f7` |
| scientific-analysis inventory | `0bebe6a722794e9d6db04f62974131c0e6d43cc5640524703d2591f05af5042c` |
| scientific-analysis tree | `6fc60878e7329ca61e876b7889df4d42988006df074fdbc1ba0ddd217852448d` |

The detailed input hashes, first-inspection boundary, and bootstrap-seed provenance are recorded in `PHASE4C_V2_SCIENTIFIC_ANALYSIS_PROVENANCE.md`.

## Independent validation

The independent validator returned `PASS` with:

- metric rows: `63000`
- seed-averaged VM-fold cells: `21000`
- primary lead cells: `120`
- bootstrap rows: `144`
- bootstrap replicates per family: `10000`
- scientific figures: `12`
- forbidden training tokens: none
- model training during analysis: `0`
- heavy execution inventory: `56723 / 56723 PASS`
- compact execution inventory: `35 / 35 PASS`

## Primary MacroMAE gains

Positive values favor the candidate named first.

| Environment | Comparison | CPU | Throughput | Memory | Disk-write |
|---|---|---:|---:|---:|---:|
| fastStorage | S2 vs S1 | -3.198519% | +0.012731% | +2.449985% | +2.689207% |
| fastStorage | M1 vs S2 | +0.045047% | -27.094152% | -4.867061% | -4.072129% |
| fastStorage | M1 vs S1 | -3.152031% | -27.077972% | -2.297834% | -1.273414% |
| Rnd | S2 vs S1 | +1.412867% | -7.214491% | +1.673083% | +0.160400% |
| Rnd | M1 vs S2 | -16.509941% | -14.318987% | -8.915737% | -5.551233% |
| Rnd | M1 vs S1 | -14.863811% | -22.566520% | -7.093487% | -5.381929% |

## Equal-environment synthesis

These values are equal-environment synthesis only; the Bitbrains environments are not pooled.

| Comparison | CPU | Throughput | Memory | Disk-write |
|---|---:|---:|---:|---:|
| S2 vs S1 | -0.892826% | -3.600880% | +2.061534% | +1.424803% |
| M1 vs S2 | -8.232447% | -20.706569% | -6.891399% | -4.811681% |
| M1 vs S1 | -9.007921% | -24.822246% | -4.695660% | -3.327671% |

## Resource classifications

Legend: `BP` = `BROAD_POSITIVE`; `CP` = `CONDITIONALLY_POSITIVE`; `NM` = `NEUTRAL_OR_MIXED`; `BN` = `BROAD_NEGATIVE`.

| Environment | Comparison | CPU | Throughput | Memory | Disk-write |
|---|---|---|---|---|---|
| fastStorage | S2 vs S1 | NM | NM | BP | CP |
| fastStorage | M1 vs S2 | NM | BN | BN | BN |
| fastStorage | M1 vs S1 | BN | BN | NM | NM |
| Rnd | S2 vs S1 | CP | NM | CP | NM |
| Rnd | M1 vs S2 | BN | BN | BN | BN |
| Rnd | M1 vs S1 | BN | BN | BN | BN |

## Environment decisions

| Environment | Comparison | Frozen decision |
|---|---|---|
| fastStorage | S2 vs S1 | `CROSS_RESOURCE_INPUT_MIXED` |
| fastStorage | M1 vs S2 | `SHARED_REPRESENTATION_NEGATIVE_TRANSFER` |
| Rnd | S2 vs S1 | `CROSS_RESOURCE_INPUT_MIXED` |
| Rnd | M1 vs S2 | `SHARED_REPRESENTATION_NOT_SUPPORTED` |

## Prospective bootstrap uncertainty

Label: **PROSPECTIVELY DEFINED EXTERNAL CONFIRMATION UNCERTAINTY INTERVALS**. These are the frozen overall paired VM-cluster percentile intervals and are not post-hoc intervals. The full 144-row table is preserved in `outputs/scientific_v2/comparisons/bootstrap_uncertainty.csv`.

| Environment | Comparison | CPU | Throughput | Memory | Disk-write |
|---|---|---|---|---|---|
| fastStorage | S2 vs S1 | [-6.898569, 0.156585] | [-0.196145, 2.884660] | [0.755152, 4.115624] | [-0.651726, 6.614115] |
| fastStorage | M1 vs S2 | [-10.743364, 3.522183] | [-29.160196, -1.877989] | [-10.424843, -1.161258] | [-7.843704, -1.428346] |
| fastStorage | M1 vs S1 | [-13.484962, 0.321638] | [-29.353265, -0.616196] | [-7.671704, 1.995266] | [-5.977187, 1.363362] |
| Rnd | S2 vs S1 | [-3.187107, 3.752170] | [-49.980626, 4.130459] | [-2.099639, 4.608034] | [-4.226429, 2.528665] |
| Rnd | M1 vs S2 | [-24.737170, -3.500449] | [-26.166866, -6.407809] | [-12.240103, -4.043654] | [-15.714522, -4.236874] |
| Rnd | M1 vs S1 | [-21.525672, -3.872703] | [-88.870111, -3.371989] | [-10.804742, -3.039767] | [-19.646321, -2.801144] |

## Persistence boundary

No formulation beats persistence across all four resources. CPU persistence skill is negative overall for S1, S2, and M1 in both environments. Throughput persistence skill is negative for all three formulations in fastStorage; in Rnd it is slightly positive for S1 and negative for S2 and M1. Memory and disk-write persistence skill are positive for every formulation in both environments.

Relative S1/S2/M1 comparisons do not imply universal absolute forecasting superiority. This distinction must remain explicit in future manuscript work.

## H1, H2, H3, and final outcome

- H1: `H1_BOUNDARY_PARTIALLY_REPLICATED`. Neither environment globally supports S2. Equal-environment evidence is mixed: CPU and throughput are negative; memory and disk-write are positive.
- H2: `H2_BOUNDARY_CONFIRMED`. Neither environment supports M1 sharing, and all four equal-environment M1-vs-S2 resource gains are negative.
- H3: `HETEROGENEITY_CONFIRMED`. Effects differ across environments, resources, VMs, horizons, and folds; no broadly positive cross-resource effect dominates both environments.
- Final Phase 4C outcome: `BOUNDARY_PARTIALLY_REPLICATED`.

The external evidence does not reproduce every TimeTrack direction. It independently supports the broader boundary that cross-resource context is not universally beneficial, benefits are resource/environment dependent, naive shared representation is not broadly beneficial, and heterogeneous transfer behavior is reproducible.

## TimeTrack comparison

| Comparison | CPU | Throughput | Memory | Disk-write |
|---|---:|---:|---:|---:|
| TimeTrack S2 vs S1 | -3.3130% | -0.2428% | +0.8594% | -0.4923% |
| TimeTrack M1 vs S2 | +0.4696% | -0.8401% | -18.4769% | -0.7956% |
| TimeTrack M1 vs S1 | -2.8279% | -1.0849% | -17.4587% | -1.2918% |

S2 memory is directionally positive across TimeTrack, fastStorage, and Rnd, but the TimeTrack gain is below 1%, so this is weak directional consistency rather than a strong universal effect. S2 CPU reverses sign, S2 throughput reverses and is materially negative in Rnd, and S2 disk-write is negative in TimeTrack but positive in both Bitbrains environments. Cross-resource-input utility is therefore resource/environment dependent.

M1-vs-S2 throughput, memory, and disk-write are negative in all three datasets/environments. M1 CPU is weakly positive in TimeTrack, nearly neutral in fastStorage, and strongly negative in Rnd. M1-vs-S1 is negative for every resource in TimeTrack, fastStorage, and Rnd; this is a central cross-dataset result. No pooled cross-dataset score was calculated.

## M1 loss balance

| Environment | Statistic | CPU | Throughput | Memory | Disk-write |
|---|---|---:|---:|---:|---:|
| fastStorage | mean | 37.885905% | 13.493035% | 25.708970% | 22.912090% |
| fastStorage | median | 28.837561% | 3.467968% | 20.138211% | 8.341557% |
| Rnd | mean | 26.950113% | 33.243624% | 15.811861% | 23.994402% |
| Rnd | median | 18.568015% | 25.453376% | 8.067387% | 17.663502% |
| TimeTrack | descriptive mean | 48.24% | 26.32% | 13.67% | 11.77% |

Loss-balance profiles differ substantially across datasets/environments. No causal explanation for M1 negative transfer is established.

## Context selection

The complete resource-specific distribution is frozen in `outputs/scientific_v2/analysis/context_selection_distribution.csv`. Aggregated counts are:

| Environment | Formulation | L=4 | L=9 | L=18 |
|---|---|---:|---:|---:|
| fastStorage | S1 | 158 | 164 | 378 |
| fastStorage | S2 | 201 | 167 | 332 |
| fastStorage | M1 | 66 | 42 | 67 |
| Rnd | S1 | 120 | 151 | 429 |
| Rnd | S2 | 184 | 161 | 355 |
| Rnd | M1 | 57 | 64 | 54 |

These counts sum to the frozen `3150` selected contexts. They are descriptive records of prospective inner-selection outcomes, not post-hoc subgroup selections.

## Efficiency

| Formulation | Parameters | Models per target set | Combined fit-hours |
|---|---:|---:|---:|
| S1 | 203028 | 4 | 74.104886 |
| S2 | 206100 | 4 | 66.854440 |
| M1 | 52500 | 1 | 19.888078 |

Relative to S2, M1 reduces parameters by `74.526929%` and model count by `75%`. M1 therefore offers substantial model-footprint and computational efficiency, but that advantage is accompanied by materially worse predictive accuracy for most externally evaluated resources. Accuracy and efficiency are separate conclusions.

## Population restriction

- fastStorage training-scale eligible: `596 / 916`
- Rnd training-scale eligible: `272 / 416`

Approximately 35% of structurally eligible VMs are excluded in each environment because at least one scientific training partition has zero IQR for one or more resources. The confirmation applies only to structurally valid VMs with nondegenerate four-resource training variability in every scientific scaler-fit partition. It must not be generalized without qualification to idle, quiescent, resource-constant, or the entire structurally valid Bitbrains population.

## Publication, Materna, and architecture gates

- Publication scope: `MULTIDATASET_BOUNDARY_STUDY_SUPPORTED_WITH_MIXED_REPLICATION`.
- Intended contribution: a controlled multi-dataset empirical study of the boundaries of cross-resource context and naive shared multi-task forecasting in cloud telemetry.
- The contribution is not a new neural architecture, loss, attention mechanism, or optimizer.
- Core evidence: real multi-horizon prediction; matched S1/S2/M1 factorial decomposition; common-support control; resource- and environment-specific effects; external Bitbrains confirmation; negative-transfer evidence; persistence boundary; accuracy-efficiency trade-off; explicit population boundary; prospective decision criteria; and independently validated execution.
- Materna gate: `MATERNA_USEFUL_SECONDARY_REPLICATION`. Materna is not needed to interpret the two pristine Bitbrains environments, but it may strengthen or constrain generalizability because H1 is mixed and effects are environment dependent. Prior DynAPM exposure makes Materna secondary, not pristine primary confirmation. Materna was not executed.
- New-architecture gate: `NO`. No stable beneficial mechanism emerges consistently across TimeTrack and both Bitbrains environments; H1 is mixed, H2 rejects naive sharing, heterogeneity alone is insufficient motivation, and the environment-varying M1 loss balance does not establish a single optimization failure mechanism.

## Artifact boundary

The 46-entry scientific-analysis inventory covers 2,233,982 bytes, has SHA-256 `0bebe6a722794e9d6db04f62974131c0e6d43cc5640524703d2591f05af5042c`, and resolves to analysis-tree SHA-256 `6fc60878e7329ca61e876b7889df4d42988006df074fdbc1ba0ddd217852448d`. The scientific checkpoint inventory adds this manifest, its reproducible builder, and both analysis-inventory records. Heavy models, predictions, environments, caches, legacy progress, and Materna outputs remain outside the compact checkpoint.

Execution immutability was rechecked through the frozen heavy inventory: `56723 / 56723 PASS`. Model artifacts changed: `0`; prediction artifacts changed: `0`; metric source artifacts changed: `0`; selection source artifacts changed: `0`.
