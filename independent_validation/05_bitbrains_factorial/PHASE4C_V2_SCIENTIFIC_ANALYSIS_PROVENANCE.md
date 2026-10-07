# Phase 4C V2 Scientific-Analysis Provenance

- Analysis date: 2026-10-07 (Europe/Helsinki)
- Execution-freeze commit: `549020a1a0b19d3c633d21cd13d2c8ff007225f1`
- Execution-freeze tag: `phase4c-v2-dual-environment-execution-freeze-v1`
- V2 config SHA-256: `627391b84887411d8b930fd5d00cdd9a1f90f3990f958d582f4329424353fa4e`
- Prospective criteria SHA-256: `79df6a168d7021dbafd6080640a506d22699e9d4989d422f924b178600465f12`
- Execution-correction decision SHA-256: `bd0a51380409290dd9deefd2cf25bbc783b018b559121bd21ba37fdfcb07e86d`
- Heavy execution inventory SHA-256: `42e085403d331bc903afd484582bf4d57c68477513ef6a948c3d40c2c5cf4377`
- Execution-tree SHA-256: `deeea76548071f08915d2c80944da4a196e1032e62a918c6e5753dd887e0c1c0`
- Compact checkpoint inventory SHA-256: `44a22a8f9699b407bbb0c239d990d204e097ddd05ea389ab33de8d7c38bbc58b`
- Checkpoint-tree SHA-256: `8e4310b4ae2ae0cd2644f418b1734abb97b80ef28b354252573084992ded96f7`
- Bootstrap replicates: 10,000 paired VM-cluster resamples per environment
- Bootstrap RNG seed: `20261007`

The prospective config and criteria did not freeze an RNG seed. The seed above
was selected once, before any bootstrap interval was calculated, and is reused
for every bootstrap family. It will not be changed based on interval appearance.

## Frozen analysis inputs

| Role | File | SHA-256 |
|---|---|---|
| fastStorage metrics | `outputs/scientific_v2/fastStorage/metrics.parquet` | `3edbbe0d74a76b4a99ee110ef9f42919700cf4b88273b568924816e828a05309` |
| Rnd metrics | `outputs/scientific_v2/Rnd/metrics.parquet` | `4072332fde01457e7d1fc89086d840a730844d8a25366c0abaaf6d69c472de4c` |
| fastStorage persistence | `outputs/scientific_v2/fastStorage/persistence_metrics.parquet` | `729d66bff8f16160968270d35e7908f62eaa3ff654d00ba72311621b4628b8ef` |
| Rnd persistence | `outputs/scientific_v2/Rnd/persistence_metrics.parquet` | `151d3f12030c31ab42c2fad068ac1d9de6fd8d8afb2303ec1934e768f7bd1d59` |
| fastStorage selected contexts | `outputs/scientific_v2/fastStorage/selected_contexts.csv` | `fb1946585217a48d7038a3d58c3ce8791b6e83b3047805d06b785cdf0a97e6da` |
| Rnd selected contexts | `outputs/scientific_v2/Rnd/selected_contexts.csv` | `8d8ae87fb9053aee96f11538bca5a60eae2c6af919c3e9819224c914211f4403` |
| fastStorage selected epochs | `outputs/scientific_v2/fastStorage/selected_epochs.csv` | `9d971c60c16def9f84e79a2dec22e50889d9356f0c8aeaf13b708e03a28d2058` |
| Rnd selected epochs | `outputs/scientific_v2/Rnd/selected_epochs.csv` | `df48933ca57689cc56d9bbb51cc593b5fce47030c8cc56378a7819acceaa92c2` |

Prediction identity is supplied by the 56,723-entry execution inventory above:
it contains exactly 9,450 prediction artifacts and 9,450 models, with the
frozen execution-tree digest. Analysis uses the compact metric and persistence
tables and does not rewrite predictions, selections, or any execution artifact.

This is the first scientific inspection of the completed dual-environment
predictive results. Earlier access was limited to technical validation that did
not inspect predictive metric values.

**NO MODEL TRAINING OCCURRED DURING SCIENTIFIC ANALYSIS.**
