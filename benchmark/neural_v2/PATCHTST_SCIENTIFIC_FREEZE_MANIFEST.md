# Neural-v2 PatchTST Scientific Freeze Manifest

## Checkpoint identity

- Freeze date: 2026-09-25 (Europe/Helsinki)
- Pre-freeze HEAD: `2845aafb44ebf2d4541e14f8a4af5c6c6176146a`
- Neural-v2 protocol: `08697069cf54f4c94cbd2a449b3e2050405328fb`
  (`neural-v2-protocol-freeze-v1`)
- DLinear scientific freeze: `2aa7e795fa3c7ccb5657ced43c19eb3e5922a1b6`
  (`neural-v2-dlinear-scientific-freeze-v1`)
- LSTM scientific freeze: `2845aafb44ebf2d4541e14f8a4af5c6c6176146a`
  (`neural-v2-lstm-scientific-freeze-v1`)
- Cross-model aggregation standard SHA-256:
  `327ad544769fc13fc619f6d60abf9fa8f206863fa231a8f325c5220217403875`
- Prospective PatchTST decision-criteria SHA-256:
  `c431f575706dd013a43ebedbd5ac695a6c615d3855b5bba709372afb82273203`

The decision criteria existed and were hashed before the first scientific
PatchTST fit. No PatchTST fit was rerun while creating this checkpoint.

## Frozen scientific design

The model is the frozen compact channel-independent PatchTST with fixed late
output mixing. It accepts `[batch, L, channels]` and returns eight CPU forecasts.
Patch length is 8, stride is 4, `d_model` is 64, there are 4 attention heads and
2 encoder layers, feed-forward width is 128, and dropout is 0.1. F0 has one
channel; F1 has two. Training used the frozen AdamW configuration (learning rate
0.001, weight decay 0.0001), batch size 256, MSE loss, maximum 50 epochs,
patience 7, and gradient clipping 1.0.

- Feature sets: `F0_LOCAL`, `F1_THROUGHPUT`
- Machines: `machine01` through `machine07`
- Rolling outer folds: 1 through 5
- Seeds: `[0,1,2]`
- Real leads: `[1,2,4,8,16,32,64,128]`
- Context candidates: `[32,64,128]`
- Support: maximum-history (`L=128`) F1-finite eligibility; F0 and F1 retain
  identical inner-training, inner-validation, final-training, and outer-test IDs.
- Context selection: minimize mean inner-validation MAE over all eight leads and
  all three seeds for each feature/machine/fold; smaller `L` wins ties.
- Epoch selection: retain each selected context's seed-specific best inner epoch.
  Final models are refit from scratch on complete legal outer-training support
  for that fixed epoch count. Outer-test data controls no preprocessing,
  selection, fitting, or early stopping.

## Execution, selection, and runtime

| Item | Frozen value |
|---|---:|
| Inner fits | 630 |
| Final fits | 210 |
| Total fits | 840 |
| Lead-level metric rows | 1,680 |
| Prediction files | 210 |
| Selected contexts | 70 |
| Scientific figures | 6 |
| Independent validation | PASS |
| Neural-v2 tests | 28 passed |

Selected-L distribution:

| Feature | L=32 | L=64 | L=128 |
|---|---:|---:|---:|
| F0_LOCAL | 15 | 3 | 17 |
| F1_THROUGHPUT | 13 | 4 | 18 |

- Inner-selection phase: 24,510.342 seconds
- Final-refit phase: 9,361.381 seconds
- Scientific execution: 33,883.714 seconds
- Analysis: 10.926 seconds
- Validation: 5.923 seconds
- Total recorded: 33,900.563 seconds
- Peak RSS: 719,110,144 bytes
- Prediction artifacts: 51,228,537 bytes
- Pilot projection: 12.3366 hours; actual/pilot ratio: 0.76295
- Selected epochs: range 1-50, mean 25.733, median 28

## Accepted PatchTST results

Leads are ordered `[1,2,4,8,16,32,64,128]`.

- F0 macro MAE: `[1.348908,1.541915,1.799564,1.890924,1.929108,1.978855,2.040326,2.211267]`
- F1 macro MAE: `[1.462756,1.599020,1.805180,1.895441,1.942017,1.977098,2.026881,2.213060]`
- Primary macro-MAE gain (%): `[-8.440064,-3.703514,-0.312121,-0.238882,-0.669155,+0.088763,+0.658975,-0.081060]`
- Pooled gain (%): `[-8.681950,-3.844765,-0.312712,-0.456965,-0.991625,-0.077733,+0.462220,-0.291240]`
- Mean cell-relative gain (%): `[-6.653319,-3.363532,-2.406693,-2.314501,-2.417446,-1.319214,-0.588988,-0.928518]`

Overall summaries are primary macro-MAE gain **-1.225078%**, pooled gain
**-1.407016%**, and mean cell-relative gain **-2.499026%**.

The prospectively defined decision is **NEUTRAL**. The mechanical consistency
counts are 2/8 positive leads, 2/7 positive machines (`machine04`, `machine07`),
2/5 positive folds (3, 4), and 1/3 positive seeds (seed 0). Negative counts are
6/8 leads, 5/7 machines, 3/5 folds, and 2/3 seeds. This does not satisfy the
prospective `BROAD_NEGATIVE` fold and seed requirements, so the label must remain
`NEUTRAL`.

## Compatible-support comparisons

- LightGBM: PatchTST won 0/8 F0 leads and 0/8 F1 leads; its primary context
  gain was larger at 1/8 leads.
- DLinear: PatchTST won 3/8 F0 leads and 7/8 F1 leads; its primary context gain
  was larger at 6/8 leads.
- LSTM: PatchTST won 8/8 F0 leads and 8/8 F1 leads; its primary context gain
  was larger at 0/8 leads.

PatchTST is a stronger absolute forecaster than DLinear and LSTM in this
benchmark, but does not outperform LightGBM at any evaluated lead.

Throughput does not provide broad incremental benefit to PatchTST.

## Standardized five-model overall context table

| Model | Primary macro-MAE gain | Pooled gain | Mean cell-relative gain |
|---|---:|---:|---:|
| Ridge | -3.838048% | -3.631815% | -1.716727% |
| LightGBM | +0.014935% | -0.086515% | +0.719205% |
| DLinear | -2.604757% | -2.589275% | -2.867954% |
| LSTM | +1.252207% | +0.849314% | +3.087378% |
| PatchTST | -1.225078% | -1.407016% | -2.499026% |

## Heavy-artifact preservation and validation

The local output tree was not deleted or regenerated during freeze creation.

- Files: 1,352
- Bytes: 53,994,678
- Output-tree SHA-256:
  `8eb7fbe338660fb07a6ef58df0670c29318812c844c895d5af18eeb4250f4e52`
- Artifact inventory SHA-256:
  `59cd587415b43d100ff5e27f76a27b596afe4316e17209ef2bcd624bc37fab58`

The accepted tree digest uses sorted paths relative to
`benchmark/neural_v2/outputs/patchtst/`, encoded as
`path + NUL + sha256 + newline`. The inventory itself stores repository-relative
paths, byte sizes, and SHA-256 values. Ignored predictions, parquet files, and
atomic progress records remain local and are represented by the committed
inventory rather than being staged.

Independent validation passed with zero missing or duplicate runs, segment
crossings, inner/outer target-time leakage, support mismatches, sample-ID or
timestamp mismatches, selected-L or epoch mismatches, run-ID or prediction-hash
mismatches. Metric recomputation was exact; primary, pooled, and cell-relative
aggregation recomputation differed by at most `4.44e-16`.

## Frozen-history integrity

- Neural-v2 source/test/config: 29/29 unchanged
- DLinear scientific inventory: 1,347/1,347 unchanged
- LSTM scientific inventory: 1,349/1,349 unchanged
- Phase 2A: 33/33 unchanged
- Original deterministic: 632/632 unchanged
- Corrected deterministic: 1,070/1,070 unchanged
- Raw hashes: unchanged
- Canonical panel SHA-256:
  `c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`
- TCN-v2 scientific runs: 0
- Multi-target scientific models: 0
