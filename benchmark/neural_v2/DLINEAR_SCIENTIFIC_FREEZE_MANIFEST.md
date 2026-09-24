# Neural-v2 DLinear Scientific Freeze Manifest

## Checkpoint identity

- Freeze date: 2026-09-24 (Europe/Helsinki)
- Pre-freeze HEAD: `08697069cf54f4c94cbd2a449b3e2050405328fb`
- Neural-v2 protocol freeze commit: `08697069cf54f4c94cbd2a449b3e2050405328fb`
- Neural-v2 protocol freeze tag: `neural-v2-protocol-freeze-v1`
- Neural-v2 prospective decision SHA-256:
  `9cec1dc25dc20dd1bf20ac3d7d495f731d41106935a66726d79a182fd058a08c`
- Model identity: `DLinear` (`N1`)
- Accepted DLinear throughput decision: **BROAD_NEGATIVE**

This checkpoint freezes the first scientific Neural-v2 execution. It contains
only DLinear scientific results. No DLinear fit was rerun while this checkpoint
was created.

## Frozen scientific design

- Feature sets: `F0_LOCAL` and `F1_THROUGHPUT`.
- Machines: `machine01` through `machine07`.
- Rolling outer folds: 1 through 5, unchanged from the frozen protocol.
- Seeds: `[0, 1, 2]`.
- Real future leads: `[1, 2, 4, 8, 16, 32, 64, 128]`.
- Context candidates: `[32, 64, 128]`.
- Common support: F1-finite eligibility with maximum-history (`L=128`)
  enforcement. F0 and F1 use identical inner-training, inner-validation,
  final-training, and outer-test sample IDs. The completed validation found
  zero support-hash or sample-ID mismatches.
- Context selection: for each feature/machine/fold cell, evaluate every context
  with all three seeds on inner validation only; minimize mean validation MAE
  over eight leads and three seeds; break ties in favor of smaller `L`.
- Epoch selection: retain each seed's own best inner-validation epoch for the
  selected context. Final refits start from scratch on full legal outer
  training support, use that fixed per-seed epoch count, perform no final
  early stopping, and evaluate the outer test once after fitting.

## Execution and validation

| Item | Frozen value |
|---|---:|
| Inner fits | 630 |
| Final fits | 210 |
| Total fits | 840 |
| Final metric rows | 1,680 |
| Prediction files | 210 |
| Selected-context records | 70 |
| Scientific figures | 4 |
| Neural-v2 tests | 28 passed |
| Independent validation | PASS |

The independent validation recorded zero segment-crossing histories, zero
segment-crossing targets, zero outer target-time leakage, zero inner
target-time leakage, zero support-hash mismatches, zero selected-context or
selected-epoch mismatches, zero missing/duplicate run IDs, and exact stored
prediction metric recomputation.

## Runtime accounting

- Execution wall time: `1003.7363964159995` seconds.
- Inner-selection phase wall time: `739.4757292080012` seconds.
- Final-refit phase wall time: `264.20664987499913` seconds.
- Analysis wall time: `2.0052382499998203` seconds.
- Validation wall time: `6.091855499998928` seconds.
- Total recorded wall time: `1011.8334901659982` seconds.
- Peak RSS: `853835776` bytes.
- Mean/median best inner epoch: `33.66825396825397` / `33.0`.
- Prediction artifact bytes: `51219843`.
- Pilot central DLinear projection: `0.19980739012466953` hours.
- Actual execution/pilot ratio: `1.3954221888246694`.

## Selected context distribution

| Feature set | L=32 | L=64 | L=128 |
|---|---:|---:|---:|
| F0_LOCAL | 14 | 4 | 17 |
| F1_THROUGHPUT | 15 | 1 | 19 |

Throughput changed the preferred context in 4 of 35 machine/fold cells.

## Frozen DLinear result

Values below are ordered by real future lead
`[1, 2, 4, 8, 16, 32, 64, 128]`.

- Exact F0 mean MAE vector:
  `[1.4016802785725453, 1.7510815760852925, 1.8587437954960266, 1.890263141006715, 1.8840976763757304, 1.9315891148424122, 2.005898198639471, 2.1690943031442975]`
- Exact F1 mean MAE vector:
  `[1.504680099669901, 1.776559678546397, 1.896645881001408, 1.928965405753623, 1.92336960349237, 1.9776077572577933, 2.051575215046287, 2.220956538464668]`
- Exact matched cell-mean F1 context-gain vector (%):
  `[-5.335600580939563, -2.2446865814785038, -2.35354705376196, -2.5199511672205634, -2.1493459861823117, -2.7582572806444676, -3.119018689213523, -2.4632256396368106]`
- Overall matched cell-mean F1 context gain: `-2.867954122384713%`.
- Positive aggregate leads: 0/8.
- Positive machine means: 1/7 (`machine03`).
- Positive fold means: 0/5.
- Positive seed means: 0/3.
- Seed mean gains: seed 0 `-4.028%`, seed 1 `-2.117%`, seed 2
  `-2.459%` (rounded to three decimals).

Throughput degraded DLinear aggregate MAE at all eight leads. Under the
prospectively recorded consistency rule, the accepted decision is
**BROAD_NEGATIVE**.

## Compatible LightGBM comparison

Accepted LightGBM predictions were not rerun. Comparisons used exact identical
support where available and exact common evaluation intersections without
retraining otherwise. The machine/fold comparison table records the support
relationship and common-support hash for every comparison.

- DLinear F0 beat accepted matched LightGBM F0 at 0/8 aggregate leads.
- DLinear F1 beat accepted LightGBM F1 at 0/8 aggregate leads.
- DLinear had a larger incremental throughput gain than LightGBM at 0/8
  aggregate leads.

DLinear did not outperform LightGBM at any evaluated lead on compatible
support.

## Heavy scientific artifact preservation

Local scientific outputs remain under
`benchmark/neural_v2/outputs/dlinear/`. They were not deleted or regenerated.
The committed `DLINEAR_SCIENTIFIC_ARTIFACT_SHA256.csv` records exact relative
path, byte size, and SHA-256 for every local output file, including:

- `metrics.parquet`;
- `inner_selection_runs.parquet`;
- `f0_f1_matched_metrics.parquet`;
- all 210 prediction parquet files;
- all inner, selection, final, and metric completion records;
- all compact tables, reports, runtime/validation records, and figures.

Inventory scope:

- files: 1,347;
- bytes: 53,479,140;
- prediction files/bytes: 210 / 51,219,843;
- scientific output-tree SHA-256:
  `f36561563c8b4b541edea0d930d0eb7e4ffdfe5cd4d546ee56041fe23ffb4371`;
- committed inventory SHA-256:
  `fd4e0fe3a1413c6f9a0b942627858354e736e4beb479f77ef71ae2c3aa46d41a`.

The output-tree digest is computed over sorted repository-relative paths and
each file's SHA-256, encoded as `path + NUL + sha256 + newline`. Heavy local
parquet predictions are represented by the committed inventory rather than
being staged blindly.

## Frozen-history integrity at checkpoint creation

- Neural-v2 source/test/config inventory: 29/29 unchanged.
- Phase 2A frozen hashes: 33/33 unchanged.
- Original deterministic heavy artifacts: 632/632 unchanged.
- Corrected deterministic inventory: 1,070/1,070 unchanged.
- Raw hashes: unchanged.
- Canonical panel SHA-256:
  `c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`.

The accepted deterministic LightGBM evidence remains: throughput is
**conditionally positive**.

## Scope interpretation and stop state

These findings apply to DLinear only. They do **not** establish that throughput
is universally useless. At this checkpoint:

- LSTM scientific runs: 0;
- PatchTST scientific runs: 0;
- TCN-v2 scientific runs: 0;
- multi-target model runs: 0.

No LSTM, PatchTST, TCN-v2, B4-v1, or multi-target scientific execution is part
of this checkpoint.
