# Phase 3A Multi-Resource Target and Design Freeze Manifest

## Checkpoint identity

- Freeze date: 2026-09-26 (Europe/Helsinki)
- Pre-freeze HEAD: `102c05d4eb6e09fea2a0288ec037267b9c6e9569`
- Preceding frozen CPU-baseline commit: `102c05d4eb6e09fea2a0288ec037267b9c6e9569`
- Preceding frozen CPU-baseline tag: `neural-v2-patchtst-scientific-freeze-v1`
- Phase 3A decision gate: `MULTI_RESOURCE_STUDY_SUPPORTED_WITH_TARGET_CHANGES`
- Phase 3A artifact inventory: `multiresource/PHASE3A_ARTIFACT_SHA256.csv`
- Inventory rows: 25
- Inventory SHA-256: `3bc8472b69aa345a6e9e1917ac90377609b2f1f50bf6167f169c078aabec2ef0`

The inventory records repository-relative path, byte size, and SHA-256 for all
substantive Phase 3A discovery and design artifacts present before checkpoint
metadata was added. The inventory and this manifest are excluded from the
inventory because including either while recording the inventory hash here
would create a circular, non-stable checksum dependency.

**NO FORECASTING MODEL WAS TRAINED DURING PHASE 3A.**

**NO MULTI-TARGET ARCHITECTURE WAS IMPLEMENTED.**

Forecasting fits in Phase 3A: **0**. Multi-target implementations: **0**.
Multi-target scientific runs: **0**. TCN-v2 scientific runs: **0**.

## Immutable input identities

All six raw hashes match the Phase 1 before/after record and were unchanged at
freeze time.

| Raw file | SHA-256 |
|---|---|
| `compute_dataset.csv` | `9204c25fe1079a18982f811131910d03f60d075aea29353f4198e434ecbe8904` |
| `detailed_cpu_cores_dataset.csv` | `8630691e51d926269ebdc4f1df5c6848e2e879eafb67aa68958b5667713f708c` |
| `disk_dataset.csv` | `2e4dcc1e2a79380dbba876422e42a6741a08da5cb55c15d29fb63a610d24aa6f` |
| `network_dataset.csv` | `75ffdd7fc260010ad3a4549af3b3978eb1aa7657e5f992969b0c5a58e4fcf1d2` |
| `packet-loss-dataset.csv` | `e586455adbb3561795ad6309c71ea3d8fb650251ec68c19c85ba08d2b4a5eb37` |
| `throughputs_dataset.csv` | `22739d4527c56a15ba11ebf4090dc44138bc5549cea88d0eddc126a70053393f` |

- Canonical panel SHA-256:
  `c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`
- Canonical signal registry SHA-256:
  `cf8af7a315d0717bf6e1b8865677999afe4d73088c249498065ee499bf98f562`

## Frozen development region

`MULTIRESOURCE_DESIGN_REGION` is exactly the canonical rows strictly before the
earliest first outer-test origin among the seven frozen CPU benchmark machine
splits.

| Property | Frozen value |
|---|---|
| Row indices | 0-16877 inclusive |
| Row count | 16,878 |
| Start timestamp | 2024-06-24 13:37:06.164306 |
| End timestamp | 2024-07-07 16:52:17.183763 |
| Earliest excluded test origin | 2024-07-07 16:52:59.474465 |
| Membership SHA-256 | `9980b51cd09ed865bc87b01de074d20413c853cfa5e67d96832e69557acb9e03` |
| Definition-file SHA-256 | `b3a24cd1ffdfc947fbf5e5742a6f1266325230d45501023af4c115345640b0f6` |

All statistical target and experimental-design decisions were derived only
from this development region. Structural/full-data availability audits remain
only as explicitly documented and did not supply test-period statistics to the
target or design decisions.

## Primary target definitions

| Resource | Canonical target | Training transform | Training scaling | Evaluation / semantic unit |
|---|---|---|---|---|
| CPU | `machineXX__cpu_utilization` | identity | fold-local robust | native-unit metrics; percent-like, inferred |
| Throughput | `machineXX__throughput_total` = bond0 TX + bond0 RX | `log1p` | fold-local robust | `expm1` then native-unit metrics; physical unit unknown |
| Memory | `machineXX__memory_used` | identity | fold-local robust | native-unit metrics; bytes, inferred |
| Disk | `machineXX__disk_write` | `log1p` | fold-local robust | `expm1` then native-unit metrics; disk-write activity, physical unit unknown |

No consistent free/total memory series exists from which a safe utilization
percentage can be derived. Used-disk occupancy is not the primary disk target:
it is too persistent/trivial for the intended forecasting study. Disk-read
activity is rejected from the core tuple because its zero concentration is
extreme. Disk-write activity must not be relabelled as disk throughput unless
metadata later establishes its physical unit.

## Frozen candidate classifications

- `PRIMARY_TARGET_CANDIDATE`: CPU utilization; `log1p` total throughput;
  used-memory level; `log1p` disk-write activity.
- `SECONDARY_TARGET_CANDIDATE`: raw total throughput; memory change;
  used-disk change; raw disk-write activity.
- `AUXILIARY_ONLY`: TX; RX; used-disk occupancy.
- `REJECT_FOR_MULTI_TARGET`: disk-read activity; `log1p` disk-read activity.

## Compact target-dynamics evidence

- CPU is dynamic/bursty; median skewness is about 6.04 and persistence
  MAE/IQR rises from about 1.27 to 2.32 between leads 1 and 128.
- Throughput is nonnegative; median raw skewness is about 8.04, median `log1p`
  skewness about 2.47, and persistence MAE/IQR about 1.02-1.35.
- Memory has lag-1 autocorrelation about 0.860; median absolute change grows
  from about 27 MB at lead 1 to 131 MB at lead 128; persistence MAE/IQR grows
  from about 0.36 to 0.84 and persistence R-squared falls from about 0.67 to
  -0.26.
- Used-disk occupancy has lag-1 autocorrelation about 0.9991 and lag-128 about
  0.9788; persistence MAE/IQR is about 0.0045-0.0281 and lead-128 persistence
  R-squared is about 0.958.
- Disk-write activity has median raw skewness about 21.9, median `log1p`
  skewness about 2.08, persistence MAE/IQR about 0.97-1.05, and negative
  persistence R-squared.
- Disk-read zero fraction ranges from roughly 71% to 99.7% by machine, so it is
  rejected as a dense shared target.

## Joint-support evidence

Legal-origin counts are frozen as follows.

| Tuple | Minimum per machine | Median per machine | Total |
|---|---:|---:|---:|
| CPU only | 26,729 | 29,542 | 204,374 |
| CPU + throughput | 12,344 | 18,286 | 124,108 |
| CPU + throughput + memory | 12,344 | 18,286 | 124,108 |
| CPU + throughput + memory + disk-write | 8,221 | 14,345 | 92,994 |

The primary four-resource tuple loses substantial support relative to CPU-only
but retains enough legal origins to justify the next experimental phase. This
is an empirical design decision, not a broader claim of sample sufficiency.

## Cross-resource dependency evidence

Median contemporaneous design-region Spearman correlations are CPU-throughput
0.333, CPU-memory 0.250, CPU-disk-write 0.171, throughput-memory 0.150,
throughput-disk-write 0.105, and memory-disk-write 0.039. On differenced
signals, CPU-throughput is about 0.262 and CPU-memory about 0.145; most other
median magnitudes are below 0.08.

These are descriptive dependency signals. They do not establish causality and
do not establish that joint forecasting will outperform independent
forecasting.

## Transform, scaling, and evaluation design

For resource `r`, every future training partition must compute only from its
own training observations:

```text
z_r = (g_r(y_r) - median_train,r) / IQR_train,r
```

Here `g_r` is identity for CPU and memory and `log1p` for throughput and
disk-write. Predictions must be inverse-transformed to native resource units
before evaluation. Raw joint MSE is prohibited because resource scales differ
by many orders of magnitude and high-scale targets would dominate it.

Native metrics are MAE, RMSE, and R-squared per resource. Scale-normalized MAE
is `MAE / training-region IQR`. Persistence skill is
`1 - MAE_model / MAE_persistence`. Native MAEs must not be averaged across
resources.

The primary multi-task comparison is computed separately for each resource:

```text
100 * (MacroMAE_S2 - MacroMAE_M1) / MacroMAE_S2
```

Seeds are averaged inside machine-fold-lead cells before equal machine-fold
aggregation.

## Frozen S1/S2/M1 factorial design

- **S1 - Independent / own-resource input:** for resource `r`, use only the
  history of `r`, predict only future `r`, and train a separate model per
  resource.
- **S2 - Independent / all-resource input:** use histories of all selected
  resources, predict one resource, and retain one independently trained model
  per target.
- **M1 - Shared multi-target:** use histories of all selected resources, a
  shared temporal representation, and resource-specific outputs/heads for all
  selected resources simultaneously.

S2 versus S1 measures cross-resource input value. M1 versus S2 measures the
value of shared representation / multi-task learning. M1 versus S1 measures
total joint-system benefit.

The **primary** S1/S2/M1 factorial comparison must use identical legal sample
support derived from the complete selected four-resource tuple. S1 must not
gain samples merely because its own resource is available while another tuple
resource is missing. Larger native-support standalone results may later be
reported separately, but must not enter the primary factorial comparison. This
prevents sample-support differences from being confounded with input sharing or
multi-task effects.

## Future baseline and machine strategy

- Mandatory baseline: persistence.
- Strong independent S1/S2 reference: LightGBM.
- Primary neural S1/S2/M1 factorial backbone: LSTM.
- Optional later secondary factorial: PatchTST.
- Initially omitted: DLinear.
- TCN-v2: `DEFERRED`.
- Proposed novel architecture: not selected.
- Primary machine strategy: separate model per machine.
- Possible later extension: a global model with machine conditioning.

No baseline, factorial, global-machine, multi-target, or novel architecture was
implemented in Phase 3A.

## Artifact hashes and sizes

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `01_target_audit/FUTURE_CHANGE_DISTRIBUTIONS.csv` | 146,890 | `ae123ace39975fd0f2e26720ff3747815e4a8290e474686419e1df89ab9ef6a9` |
| `01_target_audit/JOINT_SUPPORT_AUDIT.csv` | 30,463 | `f2a53c05917842c7c2d9f99d080dc076d3a1ff4f4671a2a956f99061bd341ff4` |
| `01_target_audit/JOINT_SUPPORT_SUMMARY.csv` | 390 | `7cd7982e7df63cac5ab85bfed21da0e24731e6f29b104c1ef69b963ab47603ad` |
| `01_target_audit/LEVEL_CHANGE_AUDIT.csv` | 15,716 | `9b35739cc44578b61fc09767690df26e12c9f7dab81e057cf74357651800505f` |
| `01_target_audit/MULTIRESOURCE_DESIGN_REGION.json` | 1,731 | `b3a24cd1ffdfc947fbf5e5742a6f1266325230d45501023af4c115345640b0f6` |
| `01_target_audit/MULTIRESOURCE_DESIGN_REGION_SHA256.txt` | 99 | `d9b0b4a504023ede89a7c83183e4e9a1193dba0ec98a941db38344cd8d3f25e0` |
| `01_target_audit/MULTIRESOURCE_TARGET_AUDIT_REPORT.md` | 11,009 | `d5803236116fe7ba0670d6559e8cd46d5e8bc6cf2bd8e2e676abfaaff3c50eef` |
| `01_target_audit/PERSISTENCE_DIFFICULTY.csv` | 94,429 | `36b1b44ba890fc8e07cf9538dbad9335ddca8c0f1e607744d7e32d3e5e9116c7` |
| `01_target_audit/PERSISTENCE_DIFFICULTY_SUMMARY.csv` | 11,463 | `696a634d809b124dbbab8ab7c048d40cf5bc624c9ca513350ce86b6b24ac3063` |
| `01_target_audit/TARGET_CANDIDATE_REGISTRY.csv` | 50,949 | `75ca0cae9f757e9403ce71c2ff08185faf8c3ba6b61216d06524655b8fe915f6` |
| `01_target_audit/TARGET_DYNAMICS.csv` | 34,248 | `44a02d9e178baba29dec3462eb288d15fcf9022dd94af9e3234bd478be5cb17c` |
| `01_target_audit/TARGET_SCALE_AUDIT.csv` | 5,881 | `8b7454e4e88cac7807e5bc175226d49ce7ae4e59e5f4051d177cbd699577928c` |
| `01_target_audit/figures/01_normalized_time_series_machine01.png` | 149,202 | `17c6b3341202b56c7de1cc4dabd4e8117791609dc652a3ac61c19906caf51764` |
| `01_target_audit/figures/02_distribution_skewness.png` | 71,691 | `59b587ca26354a589fa7cd2f5b75de20ee173d90819bce4350900f433c1ee7b5` |
| `01_target_audit/figures/03_persistence_difficulty.png` | 72,363 | `4f3c2a5bea5ac51c6a0f5f69342b22f6826ea1d2229b22feec8d7f80c8a85b99` |
| `01_target_audit/figures/04_lagged_dependency_matrix.png` | 43,470 | `92eb0907fb4cbbf98986178fd8027743cf596d3127013897cfde5a27352f0807` |
| `01_target_audit/figures/05_joint_support_by_machine.png` | 64,690 | `5d3ded05609f8d9d64bd8e9f9c8be37f32b78e98395ce6bd19a361cf578c51f0` |
| `01_target_audit/figures/06_level_change_variability.png` | 45,988 | `e0c686567ef4d698435248ba8e3faf4972749aca11da1316821f24a2d584deb7` |
| `01_target_audit/run_target_audit.py` | 21,375 | `d8da82fa6dce26640c3fb5ea8853a43a9b0eb4585e824b1095009fb127ad910b` |
| `02_dependency_design/CROSS_RESOURCE_DEPENDENCY_DESIGN.md` | 3,210 | `870acf7a90c940b869c5a07f58cc44d6babfc19c2beaabdcc353772415aae871` |
| `02_dependency_design/DEPENDENCY_SUMMARY.csv` | 23,773 | `80fdb186a825a69a5bb74e0f00de63d1af7febb4dce62fac61ae83cf5a108575` |
| `02_dependency_design/LAGGED_SPEARMAN_DEPENDENCIES.csv` | 92,518 | `ab2e0acb3fb373649cfdb004c889ad47ab4b7960dea437a445058e02e3ab0bf8` |
| `03_experiment_design/MULTIRESOURCE_EXPERIMENT_DESIGN.md` | 11,306 | `2d45516b235c96081e0ca323ceff3ad39dc08fd189c7a813e7c5570c9c88e319` |
| `PHASE3A_AUDIT_VALIDATION.json` | 757 | `b650f5dd184cd21b2c0adec477284bb8b7e134bbcd8dde70f2e86fa1946d80ee` |
| `validate_phase3a_audit.py` | 4,395 | `2ef981f5b414cc07e02bbbe3720efab02f38c614c6e891becb273c7ae533813a` |

## Validation and frozen-history integrity

Phase 3A validation: **PASS**. It verified the exact development-region
membership and definition hashes, 91 candidate-registry rows, 630 support-audit
rows, 1,512 dependency rows, six nonempty figures, nonnegative `log1p` targets,
and an `expm1(log1p(x))` maximum absolute floating-point error of
`7.748603820800781e-07`. It reported scientific execution `NONE`, model
implementation `NONE`, and no failures.

Independent pre-commit inventory verification also passed:

| Frozen evidence | Verified entries | Result |
|---|---:|---|
| Neural-v2 protocol/source/test/config | 29 | PASS |
| DLinear scientific inventory | 1,347 | PASS |
| LSTM scientific inventory | 1,349 | PASS |
| PatchTST scientific inventory | 1,352 | PASS |
| Phase 2A | 33 | PASS |
| Original deterministic | 632 | PASS |
| Corrected deterministic | 1,070 | PASS |
| Raw files | 6 | PASS |
| Canonical panel | 1 | PASS |

The preceding frozen scientific history, raw data, and canonical panel were not
modified while creating this checkpoint.
