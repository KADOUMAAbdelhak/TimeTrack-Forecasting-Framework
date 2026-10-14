# Phase 4D Materna Scientific-Analysis Provenance

- Analysis date: 2026-10-14 (Europe/Helsinki)
- Criteria checkpoint: `2d8a47a9272f1253d34da5a325dc748dd69b8e31` (`phase4d-materna-analysis-criteria-freeze-v1`)
- Execution checkpoint: `dba05d2505e91170f7d4de69027f4692e5b30584` (`phase4d-materna-three-trace-execution-freeze-v1`)
- Scientific-analysis criteria SHA-256: `19345874ff91474f8ef414e4240886630a4864d8d7dcd824b9427a49147eeca4`
- Scientific config SHA-256: `064ef5a4864f5590b8149242c4011c37a49aee35cf60a4690f6aa126b98fce27`
- Heavy execution inventory SHA-256: `8484e62b2dae596ece90308c18ea617ec904ea55ceb4fbfc76e2fcaa55dd1718`
- Execution-tree SHA-256: `3d9a6ffe1b7d520bc5ca0e3f36e147f39e87590c88f8289a26c962a09e6756e1`
- Heavy execution inventory verification: `141785 / 141785 PASS`
- Bootstrap RNG seed: `20261007`
- Bootstrap replicates per family: `10000`
- Model training during analysis: `0`

**THIS IS THE FIRST AUTHORIZED SCIENTIFIC INSPECTION OF THE COMPLETED MATERNA PREDICTIVE RESULTS.**

Before this provenance record was created, access in this task was limited to frozen criteria, Git identities, technical-validation summaries, file paths, byte sizes, and SHA-256 hashes. No Materna predictive metric value, persistence value, prediction value, formulation gain, loss share, temporal synthesis, or bootstrap result had been scientifically inspected or calculated.

## Frozen scientific-analysis inputs

| Trace | Role | File | SHA-256 |
|---|---|---|---|
| Materna-T1 | metrics | `outputs/scientific_v1/Materna-T1/metrics.parquet` | `f4ed6252ce72c3bb0b05b78cd471331c86ac9701a72756968207088c7f36d370` |
| Materna-T1 | persistence | `outputs/scientific_v1/Materna-T1/persistence_metrics.parquet` | `b151fc44a962270c42ed811d7ab06e702a622fdddaeeafaa937bb2c429731989` |
| Materna-T1 | selected contexts | `outputs/scientific_v1/Materna-T1/selected_contexts.csv` | `1f67fbfed25e34b29d0f2e28a220a3f73e8cd795b746c0d8ef08a8794997cfea` |
| Materna-T1 | selected epochs | `outputs/scientific_v1/Materna-T1/selected_epochs.csv` | `8ae73a05e7b1128171af6f5aabf023c20cde17c0baf156eae0761183ff432ec9` |
| Materna-T1 | M1 loss history | `outputs/scientific_v1/Materna-T1/m1_resource_loss_history.parquet` | `a1e95c096b3341317e0bce8ac09b1161567923f43c4069e1a06371088cbc6c36` |
| Materna-T2 | metrics | `outputs/scientific_v1/Materna-T2/metrics.parquet` | `24b670e03c152018cccf9fc23a6d2b7fe1d9a693783d53b2290c167144b4720d` |
| Materna-T2 | persistence | `outputs/scientific_v1/Materna-T2/persistence_metrics.parquet` | `8b37b0e986886f40e7d177f95f846c95e1a60806bdddf335a7bf57df94eacbbc` |
| Materna-T2 | selected contexts | `outputs/scientific_v1/Materna-T2/selected_contexts.csv` | `caf446c19e319c47d3ad345fe3110f0e804a01b051473ec408819edeab422f06` |
| Materna-T2 | selected epochs | `outputs/scientific_v1/Materna-T2/selected_epochs.csv` | `11afe345f78f4378356ba3210dfa3ad785c0b6ec3939f05c52e1d9ef561582da` |
| Materna-T2 | M1 loss history | `outputs/scientific_v1/Materna-T2/m1_resource_loss_history.parquet` | `9f049f1724b30dfc4dc70b01c1f52523c56a5b2182bd1543da3068b31ced39de` |
| Materna-T3 | metrics | `outputs/scientific_v1/Materna-T3/metrics.parquet` | `50767c5f371a6dc5c528b6c5bd777a7660faa8176d7c1f8d2a7a443f18e8b843` |
| Materna-T3 | persistence | `outputs/scientific_v1/Materna-T3/persistence_metrics.parquet` | `f06a77a33b2056f74b423b054c7b4f2aa75dc28c30d1cc10f966e46015aae5eb` |
| Materna-T3 | selected contexts | `outputs/scientific_v1/Materna-T3/selected_contexts.csv` | `dc2f5d1772e039f6a9a0748ad2ae428fb4592b349282512d1d09ea3b2aaf067d` |
| Materna-T3 | selected epochs | `outputs/scientific_v1/Materna-T3/selected_epochs.csv` | `895d228f17d3d70f5a3896b1737267ebb60814d9340c98487eaf8aa21bb2dc8d` |
| Materna-T3 | M1 loss history | `outputs/scientific_v1/Materna-T3/m1_resource_loss_history.parquet` | `48b3666ab1955713f1d97194fe452db9ceeb8743a06b81b5c51dadb288d52404` |

Prediction and model identity is supplied by the frozen 141,785-entry execution inventory, which contains exactly 14,175 prediction artifacts and 14,175 model artifacts. Analysis reads the frozen compact metric, persistence, selection, and loss-history inputs above and does not rewrite any execution artifact.
