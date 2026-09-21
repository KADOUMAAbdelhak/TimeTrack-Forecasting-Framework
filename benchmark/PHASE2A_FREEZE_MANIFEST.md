# TimeTrack Phase 2A Reproducibility Freeze Manifest

Freeze date: 2026-09-21

Branch: `main`

Pre-freeze HEAD: `6cf775e2292a9d86af9a326295f872de70d057f8`

Pre-freeze status: `benchmark/` and `discovery/` untracked; no staged files

Checkpoint tag to create: `phase2a-benchmark-protocol-freeze-v1`

This manifest freezes the redesigned TimeTrack discovery evidence and the
approved pre-benchmark Phase 2A protocol. No full benchmark result existed
before this freeze: `run_registry.csv`, `metrics.parquet`, and
`selected_configs.csv` each contained zero rows. The only model executions
were the approved ten execution-only smoke cases; their accuracy is not a
scientific result.

## Repository provenance

Tags present before this freeze:

`experiment-freeze-v1`, `experiment-freeze-v2`,
`final-analysis-freeze-v1`, `final-peak-analysis-freeze-v1`,
`final-reporting-freeze-v1`, `final-reporting-freeze-v2`,
`final-robustness-analysis-freeze-v1`,
`final-robustness-analysis-freeze-v2`,
`final-robustness-extension-freeze-v1`, and
`final-robustness-extension-freeze-v2`.

`data/raw/` and `old_fgcs_rejected/.venv_legacy/` were ignored and untracked.
No raw CSV was staged. The archived rejected study had no working-tree
modification.

## Active raw datasets

| Path | SHA-256 |
|---|---|
| `data/raw/compute_dataset.csv` | `9204c25fe1079a18982f811131910d03f60d075aea29353f4198e434ecbe8904` |
| `data/raw/detailed_cpu_cores_dataset.csv` | `8630691e51d926269ebdc4f1df5c6848e2e879eafb67aa68958b5667713f708c` |
| `data/raw/disk_dataset.csv` | `2e4dcc1e2a79380dbba876422e42a6741a08da5cb55c15d29fb63a610d24aa6f` |
| `data/raw/network_dataset.csv` | `75ffdd7fc260010ad3a4549af3b3978eb1aa7657e5f992969b0c5a58e4fcf1d2` |
| `data/raw/packet-loss-dataset.csv` | `e586455adbb3561795ad6309c71ea3d8fb650251ec68c19c85ba08d2b4a5eb37` |
| `data/raw/throughputs_dataset.csv` | `22739d4527c56a15ba11ebf4090dc44138bc5549cea88d0eddc126a70053393f` |

These hashes exactly match both the before and after hashes from Phase 1A.

## Canonical and protocol hashes

| Path | SHA-256 |
|---|---|
| `discovery/02_dependency_analysis/outputs/canonical_panel.parquet` | `c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a` |
| `discovery/02_dependency_analysis/outputs/canonical_signal_registry.csv` | `cf8af7a315d0717bf6e1b8865677999afe4d73088c249498065ee499bf98f562` |
| `discovery/02_dependency_analysis/PROTOCOL.md` | `0098b272411cc5c546613933407928b6acdf8ba8e6e7a878528db6c295c56283` |
| `discovery/03_rolling_robustness/ROLLING_PROTOCOL.md` | `499ce00aaee1e823d3598b3e49f4e1fb3f9dddc666219e6823bdd57ba860dcfb` |
| `benchmark/PROTOCOL.md` | `70737cefea67024da8ab471686227d00723565f0b65641ef801f00ac457b59f5` |
| `benchmark/configs/benchmark.json` | `cf9f46d81c0d5016b0c5bfd79e1fb26a5269550f31f488fb8d04ed606b4deb03` |

## Frozen benchmark design

- Future leads: `[1, 2, 4, 8, 16, 32, 64, 128]`.
- Context lengths: `[32, 64, 128]`.
- F0: target-machine CPU history.
- F1: target CPU plus same-machine total throughput.
- F2: target CPU plus leave-one-machine-out CPU mean.
- F3: target CPU plus leave-one-machine-out CPU median.
- F4: target CPU, throughput, and LOMO CPU mean.
- F5: target CPU, throughput, and LOMO CPU median.
- B0: last-value persistence.
- B1: direct multi-output Ridge.
- B2: eight lead-specific LightGBM regressors.
- B3: multivariate-input/eight-output DLinear.
- B4: causal multivariate-input/eight-output TCN.
- Outer evaluation: five non-overlapping chronological test blocks, about 50%
  initial training followed by five about-10% blocks, with expanding history.
- Inner validation: chronologically latest 15% of eligible outer-training
  origins; no shuffle and no outer-test-controlled selection.
- Purging: every retained outer- or inner-training origin must satisfy
  `timestamp(t+128) < first evaluation-origin timestamp`.
- Neural seeds: `[0, 1, 2]`.
- Expected full scale: 1,890 outer run records and 15,120 lead-level metric
  rows.
- Phase 2A validation: 18 tests passed, zero failures/errors.
- Smoke validation: 10 of 10 model-feature executions passed.

## Benchmark source and test hashes

| Path | Bytes | SHA-256 |
|---|---:|---|
| `benchmark/src/__init__.py` | 43 | `cc120cf2669e8e5b0206de8ad2ca2c3c39345c118b8814f7e418bc03c6acedd8` |
| `benchmark/src/data.py` | 2,009 | `7508b3d492ddba0b71b4256f95059aa0a0d7d6d97f91033b8d4410859e8cb901` |
| `benchmark/src/features.py` | 1,968 | `6313dea203b568a1c5033368ccf1647d52a0f4992e7e57d397fb02623eefcdce` |
| `benchmark/src/metrics.py` | 1,219 | `4f7b4e448f9c2e395285c3c91525189d916f4765d88e6ec753fcaff205f24a39` |
| `benchmark/src/selection.py` | 2,013 | `04ba2ad8b12f398f84fa2fc0390773f89afb6969df81c99e89b34a47af007b44` |
| `benchmark/src/splits.py` | 8,302 | `e56d7d580335701e9cbefd836a0fe15e1b6f69d2287b56b1f9523738b9e58cc7` |
| `benchmark/src/validation.py` | 2,889 | `6aaaf5f096cb5e657d9322deb9abe25ed2abcb3ae4a42c9f5d080ad0f5f4ac23` |
| `benchmark/src/windows.py` | 3,913 | `37b9b7019c3c7a08182daae7e43cb070d560db57493ba1fd47bbd557957c7d39` |
| `benchmark/src/models/__init__.py` | 386 | `29e0626a61abb6b453d934b2db6723b7c03b3f864ad99c376ac5fcaf30405403` |
| `benchmark/src/models/base.py` | 525 | `83f7e8d473ca8be8a275bb74fca011f2ae54d536f4d1726d0720d6731054df4f` |
| `benchmark/src/models/dlinear.py` | 1,920 | `4ba56313559303987455c51d8b35bd0bb6a213178e9625c2f56f3c555355b4e1` |
| `benchmark/src/models/lightgbm_model.py` | 1,756 | `3dc082a56ead177963f67660bbc6c6563619c1dc5c293e33115c7d73fac7b1b2` |
| `benchmark/src/models/neural.py` | 4,926 | `3db65c7ce8aaf36282483669432aa2c3311c69e7f188de5d746002b44a0b2317` |
| `benchmark/src/models/persistence.py` | 739 | `fafb0c304a26e5fb2bd74dc56c781b7364bba1703d2095da3dbaf0c11c5799d3` |
| `benchmark/src/models/ridge.py` | 977 | `39ae76a11ce57b5516ed60f123c93dd8355c8f64de22d0770e17c725121cbcb9` |
| `benchmark/src/models/tcn.py` | 3,224 | `5d81a0d32825aaac21a35ffc153f575fe070dabd095259565dbf2b81e45d76b4` |
| `benchmark/tests/conftest.py` | 278 | `d7c8643d626d7b4e24b286f35d8dc02b22523154acfba4d9f4d098a5664ac0ad` |
| `benchmark/tests/test_data_windows.py` | 2,914 | `e3e1217ddb4ba738f4d75d9e2debac8a19c65212aea6349b51fee043526a58e4` |
| `benchmark/tests/test_models.py` | 2,898 | `5d128a4359d01b9f8d0c6b0c067f9bd590aa13770355eb6d4ca0d1e20041213d` |
| `benchmark/tests/test_splits_validation.py` | 3,046 | `3bc7e415ce3db1d0b15a3ebbee3d08d0073caf778af79e418c1ccd22cff5af0b` |

## Local reproducible generated artifacts

Parquet artifacts remain local and ignored by the existing precise artifact
policy; they were not staged. They are reproducible from committed source and
compact evidence. Local files were not removed.

| Path | Bytes | SHA-256 |
|---|---:|---|
| `discovery/02_dependency_analysis/outputs/canonical_panel.parquet` | 24,673,592 | `c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a` |
| `discovery/02_dependency_analysis/outputs/cross_machine_association_summary.parquet` | 81,172 | `b860ec5c3d12fb541f53460ef9448c5213983f3fe00fb6db96de247a03b5f17a` |
| `discovery/02_dependency_analysis/outputs/dependency_evidence_classified.parquet` | 599,216 | `c7dd7df51a158595eec4ff7fea6ffed361f4e6012ee28fc217e52b9a7393fb61` |
| `discovery/02_dependency_analysis/outputs/incremental_predictive_value.parquet` | 983,328 | `86a7777f98fc7dcafc0a3f16a0d090b6a5257fb309e86625d8fbab4924ea0bf2` |
| `discovery/02_dependency_analysis/outputs/incremental_predictive_value_by_segment.parquet` | 427,993 | `013fd55ca3273a962a96afb2d797ea945cd86179399ceed9a2466b0ec772e9e6` |
| `discovery/02_dependency_analysis/outputs/lagged_association_summary.parquet` | 3,253,685 | `91b7a5dc57c4c97184b8a14f7ef78dd4845627ff2a614248d19e68671b91cb75` |
| `discovery/02_dependency_analysis/outputs/lagged_associations.parquet` | 8,567,293 | `c0148ddd2c557009b34332beb52dc24e9a2fa7320bf52448fbea27520c9d720a` |
| `discovery/02_dependency_analysis/outputs/mutual_information_summary.parquet` | 289,557 | `7d71ed5f35e5d4ad688e993c2fd5531eae97f0869f694b8ce7a190222b4b4116` |
| `discovery/02_dependency_analysis/outputs/test_association_at_selected_lag.parquet` | 213,078 | `b04892576e6313a3aac34974a3f741c8adfd7a2db2b5b5fe2b704026f67ea42f` |
| `discovery/03_rolling_robustness/outputs/rolling_paired_error_summary.parquet` | 184,490 | `859502e22f624d0cc18e550c7f1c03b70251c56ab543e1b8643b18f0764792f9` |
| `discovery/03_rolling_robustness/outputs/rolling_predictive_value.parquet` | 348,447 | `ad46306192c5c0d91e7273feaf796c1779878f451ae863a0b954db1df2736c80` |
| `benchmark/outputs/metrics.parquet` (empty schema) | 5,720 | `b801eb8d68772e4130fccbf1d3a704574dd0bd3ac8ab85fc547284145f3ecfd1` |
| `benchmark/outputs/smoke/metrics_not_for_interpretation.parquet` | 6,118 | `ac2b5a90e935583e9e02b9d5d7a282bac8c4b2f34f03630ce3e149145e84d3af` |

No prediction file, trained-model artifact, full benchmark metric, or tuning
database existed at freeze time.
