# Phase 4B Bitbrains External-Factorial Protocol Freeze Manifest

## Checkpoint identity

- Freeze date: 2026-09-28 (Europe/Helsinki)
- Pre-freeze HEAD: `59f5bed3fd7b385739d08dc088965341a29c2809`
- Phase 4A checkpoint: `59f5bed3fd7b385739d08dc088965341a29c2809`
- Phase 4A annotated tag: `phase4a-external-confirmation-design-freeze-v1`
- Phase 4B decision SHA-256: `247197a787250f9e81ea3b858a9f79dd8f5377d548da2fbc2bdec514e420b81e`
- Phase 4B config SHA-256: `deedcd31616861f1f6ee4517cc0552a05d54d0b334364f9674b06a1dcab6dc1a`
- Phase 4B tests: **45 passed**
- Independent Phase 4B validation: **PASS**
- Compute-feasibility decision: **FULL_35_VM_CONFIRMATION_FEASIBLE**

**NO EXTERNAL SCIENTIFIC OUTER-TEST RESULT EXISTED AT FREEZE TIME.**

External scientific S1 fits, S2 fits, M1 fits, scientific context selections,
scientific final refits, outer-test predictions, predictive outcomes inspected,
and H1/H2/H3 results were all zero at freeze time. This checkpoint does not
authorize Phase 4C or scientific execution.

## Prior frozen history and raw identity

The Phase 4B validator reproduced the frozen Phase 4A inventory and tree, whose
recursive validation chain covers Phase 3D, Phase 3C, Phase 3B, Phase 3A,
Neural-v2, DLinear, LSTM, PatchTST, Phase 2A, both deterministic histories, all
six TimeTrack raw inputs, and the canonical panel. All report PASS.

- Phase 4A inventory SHA-256: `b3fb2186d16fcdd28862a2ba6dd6c76c701d66dc5387ce9aa57bf04b3e1f7cc3`
- Phase 4A tree SHA-256: `a22bb756fed1fff2ad04cf1e0155f70df1f4682390cf54a0877490d4d3132194`
- TimeTrack raw identities: **6/6 PASS**
- Canonical panel: **PASS**

The external archives remain ignored and local under `data/external/raw/`:

| Archive | Bytes | SHA-256 |
|---|---:|---|
| `gwa_t_12_fastStorage.zip` | 134,047,207 | `11313f528a0cbcbe57e63162f8ae5a41a9c7e7c1a79872e294ff3c5bbaa2e671` |
| `gwa_t_12_rnd.zip` | 163,099,172 | `d3d9ddebb689c0b5463f2e4cfd8956e84bdcdf138b4476320855393e2b229a06` |
| `gwa_t_13_materna.zip` | 145,292,565 | `1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4` |

Materna is not part of this execution protocol and was not run.

## Frozen cohorts

| Environment | Eligible | Selected | ID-list SHA-256 | Selection-record SHA-256 |
|---|---:|---:|---|---|
| Bitbrains fastStorage | 916 | 35 | `97742a6e10858c9b8a021d3142419d66f41b2ac67e5944f95c2a4b8931f4632d` | `3ccbdb4d3615d323d54127f63eb72f588893d9bd48593a82dcccc10754a60b38` |
| Bitbrains Rnd | 416 | 35 | `5674f15382d5efb795cbda46a34f1f766e859413857475212023afc36ffcdc1a` | `5cfbd93103881a8af258ed9ecc6e317601c7b6b44825d2f790a1a81ed1731f9c` |

No VM replacement is permitted after this freeze. The two environments remain
independent and their observations and predictions may not be pooled.

## Ingestion, cleaning, and segmentation

The only data source is the official Bitbrains archives. Ten-digit timestamps
are Unix seconds converted deterministically to UTC. Nominal cadence is 300
seconds. There is no resampling, interpolation, forward fill, or synthetic
timestamp construction.

The fixed resource order is CPU, THROUGHPUT, MEMORY, DISK_WRITE, where
THROUGHPUT is network-received KB/s plus network-transmitted KB/s. A usable row
requires finite CPU in [0,100] and finite, nonnegative network RX, network TX,
memory, disk write, and constructed throughput. Invalid rows are unavailable;
they are never clipped, imputed, interpolated, or replaced. Duplicate
timestamps are a protocol failure and are never repaired.

| Environment | Raw rows | Invalid rows | Duplicate timestamps | Segments |
|---|---:|---:|---:|---:|
| fastStorage | 294,639 | 9 | 0 | 418 |
| Rnd | 842,501 | 116 | 0 | 911 |
| Combined | 1,137,140 | 125 | 0 | 1,329 |

A temporal segment breaks whenever consecutive valid timestamps differ by more
than 450 seconds. Histories and targets cannot cross a segment boundary. The
exact segment records and raw-member identities are frozen in the manifests.

## Horizons, contexts, and common support

- Sample leads: `[1,2,4,9,18]`
- Output durations and order: `[5,10,20,45,90]` minutes
- Context candidates: `[4,9,18]`, approximately `[20,45,90]` minutes
- Primary support history: `Lmax=18`

An origin is legal only when a complete L18 history lies in one valid segment,
all four history resources are finite, all four resource targets exist and are
finite at every lead, no future target crosses a segment boundary, and the
lead-18 target-time purge is satisfied. L4 and L9 reuse the L18 origin set and
gain no origins. All four S1 models, all four S2 models, and M1 use exactly the
same origin IDs and support hashes.

| Environment | Support records | Total legal origins |
|---|---:|---:|
| fastStorage | 525 | 284,882 |
| Rnd | 525 | 818,879 |
| Combined | 1,050 | 1,103,761 |

Support failures and formulation/resource support mismatches are both zero.
Exact origin-ID lists, split hashes, segment IDs, boundary timestamps, and
counts are frozen in `EXTERNAL_SUPPORT_MANIFEST.parquet` and
`EXTERNAL_SUPPORT_SUMMARY.csv`. Outer-test target values are not stored there.

## Fold and inner-validation semantics

Each VM has five chronological expanding outer folds. The first 50% of legal
origins is the initial training region and each following 10% block is one
outer test. Integer boundaries use floor-count construction and the final
boundary is forced to the legal-origin count. Outer train is lead-18
target-time purged before the first test origin.

Within purged outer train, the latest `ceil(15%)` legal origins form inner
validation. Earlier origins form inner train and receive the same lead-18 purge
against the first inner-validation origin. There are no random folds. Outer
test cannot participate in transform/scaler fitting, context or epoch
selection, fitting, or early stopping. All inner-train, inner-validation,
outer-train, and outer-test IDs, hashes, and boundary timestamps are frozen.

## Transforms and physical inversion

| Resource | Transform | Native inversion |
|---|---|---|
| CPU | identity | inverse robust scaler |
| THROUGHPUT | `log1p` | inverse scaler, `expm1`, nonnegative projection |
| MEMORY | identity | inverse robust scaler |
| DISK_WRITE | `log1p` | inverse scaler, `expm1`, nonnegative projection |

Each resource then uses median/IQR robust scaling fitted only on inner train
during selection and on complete legal outer train during final refit. IQR must
be strictly positive; there is no fallback. Pre-projection negative fractions
are retained, while primary native metrics use physically projected
throughput/disk-write predictions.

## Frozen plain-LSTM factorial

All models are two-layer, unidirectional LSTMs with hidden size 64, dropout 0.1,
and the final recurrent hidden state.

| Formulation | Input | Organization | Output | Parameters |
|---|---|---|---|---:|
| S1 | `[N,L,1]` | separate model/resource | `[N,5]` | 50,757/model; 203,028/four |
| S2 | `[N,L,4]` | separate model/target resource | `[N,5]` | 51,525/model; 206,100/four |
| M1 | `[N,L,4]` | shared encoder plus four independent heads | `[N,4,5]` | 51,200 encoder; 1,300 heads; 52,500 total |

No architecture modification, task weighting, or selective fusion is part of
this protocol.

## Training, loss, selection, and epoch lifecycle

- Optimizer: Adam
- Learning rate: 0.001
- Batch size: 256
- Maximum epochs: 50
- Early-stopping patience: 7
- Gradient clipping: 1.0
- Seeds: `[0,1,2]`
- Contexts: `[4,9,18]`
- Hyperparameter search: context length only

M1 is the arithmetic mean of CPU, THROUGHPUT, MEMORY, and DISK_WRITE MSE, each
itself averaged across batch and five horizons in transformed/scaled space.
Resource losses and shares are logged separately. Adaptive, learned,
uncertainty, GradNorm, and resource reweighting are prohibited.

S1 and S2 select one L independently per environment/VM/fold/target by mean
inner-validation NMAE across five horizons and three seeds. M1 selects one L
per environment/VM/fold by equal mean NMAE across four resources, five
horizons, and three seeds. All ties choose the smaller L. Outer test cannot
influence selection.

Inner fits early-stop only on inner validation and retain each seed's best
epoch. Final refit initializes from scratch with the selected L and that
seed-specific fixed epoch, fits complete legal outer train without outer-test
early stopping, and evaluates outer test once afterward.

## Metrics, aggregation, and environment synthesis

MAE, RMSE, R-squared, NMAE, and persistence skill are recorded per
environment/VM/fold/seed/resource/lead. Native MAE is never combined across
resources. Seeds are averaged within VM/fold/resource/lead, then VM-fold cells
receive equal weight. Matched gains are calculated separately per environment
as S2 versus S1, M1 versus S2, and M1 versus S1 percentage reductions in the
corresponding macro MAE.

Only after both environments independently complete and validate may an
equal-environment synthesis average their effects for each
comparison/resource/lead. It is not weighted by VM count, origin count,
prediction count, or duration, and environment disagreement and reversals must
remain explicit.

## Frozen questions

- H1: Does S2 fail to provide broad per-resource improvement over S1?
- H2: Does M1 fail to provide broad per-resource improvement over S2?
- H3: Are cross-resource benefits heterogeneous rather than consistently
  positive across VMs, environments, resources, and horizons?

No external predictive result had been inspected when these questions were
frozen.

## Scientific workload

| Formulation | Inner/environment | Final/environment |
|---|---:|---:|
| S1 | 6,300 | 2,100 |
| S2 | 6,300 | 2,100 |
| M1 | 1,575 | 525 |
| Total | 14,175 | 4,725 |

Each environment therefore has 18,900 fits and 31,500 future resource-lead
metric rows. Both environments have 28,350 inner fits, 9,450 final fits, 37,800
total fits, and 63,000 metric rows.

## Preserved non-scientific pilot

The pilot used the first frozen SHA-ranked VM in each cohort: fastStorage 697
and Rnd 99. It used fold 1, seed 0, L9, exactly five epochs, and inner train and
inner validation only. It ran four S1 models, four S2 models, and one M1 model
per environment: 18 total. Outer-test target access was false.

| Environment | S1 median sec/epoch | S2 median sec/epoch | M1 sec/epoch |
|---|---:|---:|---:|
| fastStorage | 0.082121 | 0.083093 | 0.086661 |
| Rnd | 0.243251 | 0.246890 | 0.258467 |

Pilot loss and inner-validation metrics are non-scientific technical
diagnostics and cannot support forecast-quality interpretation or H1/H2/H3.

## Runtime, storage, and feasibility

| Effective epochs | fastStorage fit-hours | Rnd fit-hours | Combined fit-hours | Four-worker wall hours |
|---:|---:|---:|---:|---:|
| 10 | 4.6539 | 13.8473 | 18.5012 | 4.6253 |
| 25 | 11.6347 | 34.6182 | 46.2530 | 11.5632 |
| 50 | 23.2695 | 69.2365 | 92.5059 | 23.1265 |

Projected retained scientific storage is 2.9223 GB. The frozen decision is
`FULL_35_VM_CONFIRMATION_FEASIBLE`; no cohort reduction is authorized.

## Resumability

Run identity includes environment, formulation, resource where applicable, VM,
fold, L, seed, phase, config hash, support hash, archive hash, and cohort hash.
Completion records are atomic. A run may be skipped only when its completion
identity and support hash match and all expected artifacts validate. Failed or
missing runs may never be silently omitted from aggregation. Unnecessary epoch
checkpoints are not retained.

## Artifact inventory

- Inventory: `PHASE4B_ARTIFACT_SHA256.csv`
- Inventory entries: **43**
- Inventory total bytes: **46,916,611**
- Inventory SHA-256: `4e0de1ce213408c5d3860cca985a4d44669b9b04c0c34aadf72b52bf4d17ddf8`
- Phase 4B tree SHA-256: `fb049da91ae0a5ea97a9882f8488f24f1de012886687e8e636ed420f678cca50`

The tree digest is SHA-256 over sorted UTF-8 records
`relative_path,byte_size,sha256\n`. The inventory covers all substantive Phase
4B source, tests, config, protocol, decision, support and segment manifests,
pilot outputs, preflight state, validator, validation result, preflight report,
and inventory builder. The inventory and this freeze manifest are excluded from
their own digest to avoid circular checksum dependencies; the Git commit and
annotated tag protect both metadata files.
