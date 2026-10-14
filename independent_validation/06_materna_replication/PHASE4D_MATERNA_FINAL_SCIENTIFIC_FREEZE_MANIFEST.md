# Final Phase 4D Materna Scientific Freeze Manifest

Date: 2026-10-14

Status: **FINAL EXPERIMENTAL REPRODUCIBILITY CHECKPOINT**

Scope: freeze the completed Materna three-trace scientific analysis and its cross-study boundary conclusions before manuscript writing. This checkpoint performs no model training, prediction generation, bootstrap rerun, scientific recalculation, subgroup mining, or manuscript drafting.

## Provenance and frozen identities

- Parent scientific-analysis criteria commit: `2d8a47a9272f1253d34da5a325dc748dd69b8e31`
- Criteria tag: `phase4d-materna-analysis-criteria-freeze-v1`
- Scientific-analysis criteria SHA-256: `19345874ff91474f8ef414e4240886630a4864d8d7dcd824b9427a49147eeca4`
- Three-trace execution commit: `dba05d2505e91170f7d4de69027f4692e5b30584`
- Execution tag: `phase4d-materna-three-trace-execution-freeze-v1`
- Execution inventory SHA-256: `8484e62b2dae596ece90308c18ea617ec904ea55ceb4fbfc76e2fcaa55dd1718`
- Execution-tree SHA-256: `3d9a6ffe1b7d520bc5ca0e3f36e147f39e87590c88f8289a26c962a09e6756e1`
- Scientific-analysis inventory: **38 / 38 PASS**, **3,208,698 bytes**
- Scientific-analysis inventory SHA-256: `b10d2520e2f5ba13fb0282ba2b2d98f2c25798a0bde51b64321a9ca87b54555f`
- Scientific-analysis tree SHA-256: `a138f6c2831779276833fc1bb748ced71d49a84db54f0f495f752c266bb4aab2`
- Scientific-analysis validator: **PASS**
- Scientific figures: **12**
- Model training during scientific analysis and final freeze: **0**

The full execution inventory was reverified byte-for-byte at final freeze: **141,785 / 141,785 PASS**, totaling **6,381,741,517 bytes**. Models changed: **0**. Predictions changed: **0**. Source metrics changed: **0**. Selections changed: **0**. Completions changed: **0**.

## Frozen Materna primary gains

Gain is `100 * (MAE_baseline - MAE_candidate) / MAE_baseline`; positive values favor the first formulation.

| Trace | Comparison | CPU | Throughput | Memory | Disk-write |
|---|---|---:|---:|---:|---:|
| T1 | S2 vs S1 | -4.317958% | +0.986935% | -0.019692% | -6.699662% |
| T1 | M1 vs S2 | +0.882699% | -7.308355% | -13.218360% | -27.457746% |
| T1 | M1 vs S1 | -3.397145% | -6.249291% | -13.240655% | -35.996983% |
| T2 | S2 vs S1 | +4.207624% | +0.294315% | +3.948171% | -1.120181% |
| T2 | M1 vs S2 | -2.564363% | -8.692761% | -9.266823% | -7.888503% |
| T2 | M1 vs S1 | +1.751160% | -8.372862% | -4.952782% | -9.097050% |
| T3 | S2 vs S1 | -2.787548% | +0.044766% | +3.089002% | +1.907168% |
| T3 | M1 vs S2 | -8.099015% | -7.914278% | -8.702593% | -71.295095% |
| T3 | M1 vs S1 | -11.112327% | -7.865970% | -5.344768% | -68.028209% |

## Frozen equal-temporal-block synthesis

| Comparison | CPU | Throughput | Memory | Disk-write |
|---|---:|---:|---:|---:|
| S2 vs S1 | -0.965960% | +0.442006% | +2.339160% | -1.970892% |
| M1 vs S2 | -3.260227% | -7.971798% | -10.395925% | -35.547114% |
| M1 vs S1 | -4.252770% | -7.496041% | -7.846069% | -37.707414% |

## Bootstrap identity

- Resampling unit: paired VM clusters
- VM count: 35
- Fold count: 5
- Replicates: 10,000
- Seed: `20261007`
- Frozen bootstrap table: `outputs/scientific_v1/comparisons/bootstrap_uncertainty.csv`
- Frozen bootstrap-table SHA-256: `49067a3e5c13ad5456b559c98f4d3c2aeb512de1da64a84a591a6d3d8f6bdd3b`

Bootstrap uncertainty is descriptive and does not replace the frozen resource classification or trace-decision rules.

## Frozen trace decisions

| Trace | Cross-resource input | Shared representation | Joint system |
|---|---|---|---|
| T1 | `CROSS_RESOURCE_INPUT_NOT_SUPPORTED` | `SHARED_REPRESENTATION_NOT_SUPPORTED` | `JOINT_SYSTEM_BROADLY_HARMFUL` |
| T2 | `CROSS_RESOURCE_INPUT_MIXED` | `SHARED_REPRESENTATION_NOT_SUPPORTED` | `JOINT_SYSTEM_BROADLY_HARMFUL` |
| T3 | `CROSS_RESOURCE_INPUT_MIXED` | `SHARED_REPRESENTATION_NOT_SUPPORTED` | `JOINT_SYSTEM_BROADLY_HARMFUL` |

## Persistence conclusions

- S2 is better than persistence in all 12 trace-resource overall aggregates.
- No formulation is better than persistence in every trace-resource-lead cell.
- Relative formulation comparisons remain distinct from persistence-based absolute forecasting performance.
- Persistence does not redefine R1, R2, R3, or R4.

## Frozen R1-R4

- R1: `R1_RESOURCE_TEMPORAL_DEPENDENCE_CONFIRMED`
- R2: `R2_NEGATIVE_SHARING_REPLICATED`
- R3: `R3_JOINT_SYSTEM_UNDERPERFORMANCE_REPLICATED`
- R4: `R4_TEMPORAL_HETEROGENEITY_CONFIRMED`

## Frozen cross-study scientific observations

- Cross-resource S2 effects vary by resource, environment, and temporal block.
- S2 memory is the strongest repeated contextual benefit but is not universal.
- M1-vs-S2 is broadly negative across external evidence.
- M1-vs-S1 is repeatedly negative across the study.
- Disk-write M1-vs-S1 is negative across TimeTrack, fastStorage, Rnd, T1, T2, and T3.
- Six-source mean disk-write M1-vs-S1: **-20.178231%**.
- Shared representation offers major model-efficiency gains but does not translate into broadly improved forecasting accuracy.
- Relative formulation comparisons must remain distinct from persistence-based absolute forecasting performance.
- Materna conclusions apply to the **18.5930%** training-scale-eligible shared VM population.

No pooled global score was calculated across TimeTrack, Bitbrains, and Materna.

## Efficiency boundary

| Formulation | Parameters | Models per target set | Actual Materna fit-hours |
|---|---:|---:|---:|
| S1 | 203,028 | 4 | 85.594240 |
| S2 | 206,100 | 4 | 75.303186 |
| M1 | 52,500 | 1 | 20.405083 |

Relative to S2, M1 reduces parameters by **74.526929%** and model count by **75%**. Efficiency and predictive accuracy remain separate conclusions.

## Population restriction

- Structural common pool: 398 VMs
- Training-scale eligible: 74 VMs
- Selected shared cohort: 35 VMs
- Retention among training-scale-eligible VMs: **18.5930%**

The Materna conclusions apply only to structurally valid VMs with nondegenerate four-resource training variability across every scientific scaler-fit partition in all three temporal blocks. They do not generalize to the complete Materna population.

## Frozen final boundaries

- Cross-resource boundary: `CROSS_RESOURCE_BOUNDARY_STRENGTHENED`
- Shared-representation boundary: `SHARED_REPRESENTATION_BOUNDARY_STRENGTHENED`
- Joint-system boundary: `JOINT_SYSTEM_UNDERPERFORMANCE_STRENGTHENED`
- Paper-scope gate: `MULTIDATASET_TEMPORAL_BOUNDARY_STUDY_STRONGLY_SUPPORTED`
- Stop-experimentation gate: `STOP_EXPERIMENTATION_AND_WRITE`

## Final experimental authorization boundary

**NO ADDITIONAL DATASET, FORECASTING MODEL, ARCHITECTURE, FEATURE SET, HYPERPARAMETER SWEEP, OR POST-HOC EXPERIMENT IS SCIENTIFICALLY AUTHORIZED BY THE CURRENT STUDY.**

Further experiments are permitted only if a later reproducibility or manuscript audit exposes a genuine methodological defect.

**STOP. NO MORE EXPERIMENTAL PHASES.**
