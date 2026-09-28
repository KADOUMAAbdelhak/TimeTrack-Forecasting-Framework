# Phase 3D Post-Hoc Audit Freeze Manifest

## Checkpoint identity

- Freeze date: 2026-09-28 (Europe/Helsinki)
- Pre-freeze HEAD: `b2064719631736f00bc87446252226d9c743c58b`
- Phase 3C checkpoint: `b2064719631736f00bc87446252226d9c743c58b`
- Phase 3C tag: `phase3c-lstm-factorial-scientific-freeze-v1`
- Phase 3D protocol SHA-256:
  `c1ed2d6ae3ee3afe20c70b8561cc58d340c0ee70e0686e642f461b7e0f702da8`
- Phase 3C inventory SHA-256:
  `95bbb842f60bbc8c2c1bc11704c413e8e654594476d16c40850a217913c5155e`
- Phase 3C scientific-tree SHA-256:
  `ec35446710f90a7b1e1a86cdbca6bedd4face31ec68ea56e83fd682addd89a65`

**NO MODEL WAS TRAINED IN PHASE 3D.**

**NO NEW FORECASTING ARCHITECTURE WAS IMPLEMENTED.**

All five Phase 3C outer folds had already been inspected. Phase 3D is a
post-hoc, exploratory audit and cannot provide untouched confirmatory evidence.

## Source and validation identity

| Artifact | SHA-256 |
|---|---|
| `run_posthoc_audit.py` | `6288770287c802fed523dbd4b3b2cd3a85bbc102b288d8b3d87823204c6f1f49` |
| `validate_posthoc_audit.py` | `8176ee1ed7037f4d5b66bfcae095fd798ee54b49b7308309e31a52f3cde3bbc1` |
| `build_phase3d_inventory.py` | `534450cf0280ef7a7e5d818476fe57e0544c5e41c93b851150c8635ce84f0d84` |
| `validation.json` | `f9e95c258af775b9b615bed51b3d8b27af759ddb5ccd78718d2ee78633e635d3` |
| `multiresource/MULTIRESOURCE_RESEARCH_BOUNDARY.md` | `31e9f5277638cb4176fb65b820a42ade36ddf9c85bade8d27c8e9212b843c28c` |

Independent validation status: **PASS**. It verified zero training-framework or
optimizer calls, zero Phase 3D forecasting fits, zero Phase 3D architecture
definitions, all 945 frozen prediction files, all 5,706 Phase 3C inventory
entries, legal forecast-origin descriptors, training-derived thresholds, no
future descriptor access, and exactly ten figures.

## Artifact inventory

- Inventory: `PHASE3D_ARTIFACT_SHA256.csv`
- Inventory entries: **37**
- Inventory total bytes: **445,981,302**
- Inventory SHA-256:
  `cd3ea3d730e99546e52c55720508685e269bb77017fcde27ecd6cbf0dca2f7a2`
- Phase 3D tree SHA-256:
  `eddfd8e347c95b3aad7d8a0d97ae592cd06483c4712243303ddacadf3f62cd4d`

The tree digest is SHA-256 over sorted UTF-8 records
`relative_path,byte_size,sha256\n`. The inventory and this manifest are excluded
from that digest to avoid circular checksum dependencies. The Git commit and
annotated tag protect those two metadata files. The inventory covers all Phase
3D source, protocol, derived outputs, figures, reports, validation, and the
multi-resource boundary record. The large origin-descriptor and sample-error
parquet files are inventoried locally but remain excluded from Git by the
repository's large-data policy; the compact cell-level parquet is committed.

## Frozen output hashes

| Output | SHA-256 |
|---|---|
| `audit_metadata.json` | `1d4643ee247aa4979980a9eb008cc88171e7a42cb92cf834d39c76973aad5793` |
| `benefit_concentration.csv` | `cc5db1924783a70f92bc7f4b01bd9ec6cd02247983dc191ce7fa57238a189c2e` |
| `cell_gain_distribution_summary.csv` | `d379d7925785b464f0b71f642641a65158a14297b6e45a93a4c42c76a02e44ec` |
| `cell_level_gain_matrix.parquet` | `2bd29c2737a7b221f40293532edd310262afc9790280e79027974de31dedc7da` |
| `context_length_heterogeneity.csv` | `8350715d42d01893a4a0af1c30668a91ae8d562cc04926451c9dedecc10aec54` |
| `dependency_vs_context_gain.csv` | `4368f92a564709b8e1e0f5081e8494d83081a9a32b4a5ddf7e65faa251c88092` |
| `gain_by_fold.csv` | `d74e294f0648d9406d723e1a66dafc9059efb5c0938ccc8261743dfe324054ef` |
| `gain_by_horizon.csv` | `4666d23bd01402c98759f66b8eb7ae8d93d56f7a305986443ebf65f49f32952a` |
| `gain_by_machine.csv` | `8d5ef5d314db9109fb18b4b22acdf71c6cc9eb0df710e8a6612d630855c7057e` |
| `loss_share_relationship_summary.csv` | `c2d8959ccdd9c080eb29b0c7f121e8e10d4675878bc9e16ffc620baf697b7a4a` |
| `loss_share_vs_negative_transfer.csv` | `8fb9dd904a6eeb25e51dbacf60f07d4da942ec48c0624f0142dcb62edc3a765e` |
| `m1_vs_s2_regime_analysis.csv` | `4ebd7c8002c622258fa36608440b3e1860222cbc47a21ad4041c8cf967e9701f` |
| `memory_failure_decomposition.csv` | `c7539288819e0de3a3380f8bdb26ece89130bbd090e9632f2da82d03eb8d90f5` |
| `origin_regime_descriptors.parquet` | `1acf4c690209f975acfb82fa94910c1ad5aeaee39bb80ee5569e85433a073846` |
| `phase3c_primary_reproduction.csv` | `fd85bd78700c22eebc01aca7d4bfc2a79c8060f5fdddd943138f6fed8633b9b4` |
| `posthoc_bootstrap_uncertainty.csv` | `e7b8cb124550a87ed141a22165ae7a62480e4b8f33070c1283a0c5e43416d4dd` |
| `regime_thresholds.csv` | `e82616d359365feb5cb219cbfb4a23aa6aeabea0e26a323c959a8d7e885526fe` |
| `s2_vs_s1_regime_analysis.csv` | `c44070fcac39769e4f773cb77b88ad721936ca2dc668bac7bb1df7b0261788d4` |
| `sample_error_differences.parquet` | `b3d9985a9c9701770c77fb6d46d594b702d6eb5379ba164acb5b53249b339996` |

## Frozen figure hashes

| Figure | SHA-256 |
|---|---|
| `01_s2_vs_s1_machine_lead_heatmaps.png` | `7dc0295ffacf1a87b8feb5e0be32195e31bd5a27d1755629ed4f669b63946a8a` |
| `02_m1_vs_s2_machine_lead_heatmaps.png` | `a24b1485b4ff6238e60f300cbc1cd408ac32037849468d759078ea2bb54b3d50` |
| `03_s2_vs_s1_fold_gains.png` | `a68808c3e3e5058b1e81dc6299631e1a4ec0dfa75c4beb63d197a389f66cf264` |
| `04_m1_vs_s2_fold_gains.png` | `9bf2eccbbaa29234b52509e45febcba142d9370d77421e0ef8ba89bbd84c4a6d` |
| `05_regime_conditional_s2_vs_s1.png` | `9c16da98a22454eecdaab256e78bbc93e73cfb37fc559685725d5b23ac5a0d9b` |
| `06_dependency_vs_context_gain.png` | `b0266c4e0d00cd7295470a1e4dfe8c78388f5b204024b30837b5e24631d4e955` |
| `07_loss_share_vs_m1_s2_gain.png` | `d500f0edbb8939f2a6b7185a04937f95443f8c417397784a0f92f22c47f968cd` |
| `08_memory_failure_decomposition.png` | `a5d9a91d6152ee6f6b792abae1bd5d55b6376396e74a78ce097a72e6db0280c1` |
| `09_benefit_concentration.png` | `33543897fdfaadf42f25436ebeb39bb89440b5900c0b5e2d087fe6f372b4fff0` |
| `10_posthoc_bootstrap_uncertainty.png` | `ae2311f115096122363a233f7efd1d1d2603397d275b526d0fe4efab4289eb9f` |

## Exact Phase 3C reproduction

| Comparison | CPU | Throughput | Memory | Disk-write |
|---|---:|---:|---:|---:|
| S2 vs S1 | -3.3130% | -0.2428% | +0.8594% | -0.4923% |
| M1 vs S2 | +0.4696% | -0.8401% | -18.4769% | -0.7956% |
| M1 vs S1 | -2.8279% | -1.0849% | -17.4587% | -1.2918% |

All twelve values reproduce from frozen Phase 3C evidence.

## Machine, horizon, and fold findings

The S2-versus-S1 prospective stable-positive machine labels are disk-write
machine06 (+0.1677%), memory machine04 (+3.4446%), throughput machine02
(+2.7791%), and throughput machine05 (+3.0575%). Six additional machines have
partial-positive labels. None of these isolated effects satisfies the broader
cross-machine exploratory stability rule.

No resource has a stable positive horizon pattern. CPU is negative at every
aggregate lead; throughput has an insufficiently stable short-horizon positive
region; memory has mixed/positive medium-horizon behavior without sufficient
stability; and disk-write has limited short-lead pockets only.

No resource is positive in four of five folds overall. Positive-fold counts are
CPU 3/5, throughput 3/5, memory 2/5, and disk-write 1/5. This temporal
inconsistency is a principal reason no conditional-context hypothesis survived.

## Controlled regimes and exploratory patterns

Stable controlled S2-versus-S1 regimes: **0**. Partial controlled regimes:
**10**. Partial pockets involve high or volatile throughput and memory level,
memory volatility/change, CPU level, and throughput level. No partial pocket is
promoted to a hypothesis. All remaining controlled patterns are unstable.

No pattern satisfies the predeclared requirement for consistency across folds,
machines, adjacent horizons, sufficient prediction coverage, and simultaneous
relative and native-unit improvement. No confirmatory target-specific or
regime-specific hypothesis is selected.

## Dependency and M1 loss-share findings

The strongest dependency-benefit association is memory context benefit versus
absolute training-region memory-throughput level dependence, Spearman
`rho=0.5014`. Other associations range approximately from `-0.2218` to
`+0.2882`. Training-side dependency does not reliably predict context benefit;
the memory association is exploratory and neither predictive nor causal.

Memory selected-inner loss share versus M1-versus-S2 gain has Spearman
`rho=0.4134`; other resources range approximately from `-0.0627` to `+0.1991`.
These mostly weak relationships do not support attributing M1 negative transfer
primarily to loss-share imbalance or justify adaptive task weighting.

## Memory failure and CPU special case

M1 memory native MAE degradation versus S2 is **58,274,148.1398**, with primary
relative degradation **-18.4769%**. Degradation occurs across 7/7 machines, 4/5
folds, and 8/8 leads. Its post-hoc bootstrap uncertainty interval is
`[-42.4724%, -7.1631%]`. Memory negative transfer is broad, not dominated by an
isolated machine, fold, or horizon. The interval is exploratory, not a
confirmatory confidence interval.

For CPU, M1 gains +0.4696% versus S2 but loses -2.8279% versus S1. M1 therefore
only partially recovers S2's harm and does not beat the own-resource baseline
overall. Machine05 has an isolated stable-positive M1-versus-S1 machine label
and machine04 a partial-positive label, but every aggregate CPU lead remains
negative versus S1. No broadly stable CPU subgroup establishes multi-resource
superiority.

## Throughput/disk-write boundary and concentration

S2-versus-S1 positive-cell fractions are 52.86% for throughput and 48.93% for
disk-write. Their small aggregate losses mix positive and negative local effects
rather than being uniformly negative, but the positive pockets are not stable
across machines, folds, and horizons.

For S2 versus S1, only approximately 2.14%-8.21% of cells account for 50% of
total positive native-unit improvement, and 5.36%-18.57% account for 80%.
Positive benefit is highly concentrated and cannot support a broadly distributed
cross-resource context advantage.

## Post-hoc bootstrap uncertainty

These are **POST-HOC BOOTSTRAP UNCERTAINTY INTERVALS**, not confirmatory
confidence intervals:

| Resource | S2-vs-S1 interval |
|---|---:|
| CPU | [-15.0122%, +2.1246%] |
| Throughput | [-3.4060%, +2.0263%] |
| Memory | [-8.0232%, +11.6017%] |
| Disk-write | [-3.1471%, +0.3829%] |

All cross zero and do not replace the prospective Phase 3C decisions.

## Decision, closure, and independence requirement

The frozen Phase 3D decision is **INCONCLUSIVE_POSTHOC_HETEROGENEITY**. Positive
context effects exist in isolated pockets, but no controlled pattern is stable
and broad enough to define a new hypothesis. Phase 3D does not justify gating,
target-specific routing, selective fusion, adaptive sharing, or another
multi-task architecture on the inspected TimeTrack evidence.

Multi-resource model development is **CLOSED PENDING INDEPENDENT DATA**. Any
future hypothesis informed by Phase 3C or Phase 3D is post-hoc with respect to
all five existing test folds. Confirmation requires newly collected TimeTrack
telemetry, a previously untouched temporal extension, an external compatible
dataset, or an independent deployment/workload source. Existing folds may be
used only for clearly labelled exploratory analysis, debugging, or mechanism
development.

The next recommended phase is **INDEPENDENT DATA / RESEARCH-SCOPE AUDIT**, with
no model training.

## Frozen-history integrity

Phase 3C passed 5,706/5,706 entries. Phase 3B, Phase 3A, Neural-v2, DLinear,
LSTM, PatchTST, Phase 2A, original deterministic, and corrected deterministic
inventories all passed. All six raw inputs and the canonical panel passed; the
canonical panel SHA-256 remains
`c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`.

TCN-v2 scientific runs: **0**. PatchTST multi-resource scientific runs: **0**.
Post-Phase3C architecture implementations: **0**. Phase 3D forecasting fits:
**0**.
