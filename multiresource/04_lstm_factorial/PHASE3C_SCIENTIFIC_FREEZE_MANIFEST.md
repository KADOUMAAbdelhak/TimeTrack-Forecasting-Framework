# Phase 3C Scientific Freeze Manifest

## Checkpoint identity

- Freeze date: 2026-09-28 (Europe/Helsinki)
- Pre-freeze HEAD: `42c98ea0f63549ecc8e073352a4fe1247a263aaf`
- Phase 3A checkpoint: `70eea336302aebfaaa20c79b1972b1ebb835442c`
  (`phase3a-multiresource-design-freeze-v1`)
- Phase 3B checkpoint: `42c98ea0f63549ecc8e073352a4fe1247a263aaf`
  (`phase3b-lstm-factorial-protocol-freeze-v1`)
- Phase 3C scientific criteria SHA-256:
  `3157a233c3c76b126ff939f7e0588c9c2d21f98bb7d3e6355f13a5d1bc470d57`
- Frozen configuration SHA-256:
  `fe985007ebd72417dcab8e8a1851c358d3d9a3da26f372595ac7ff6b499eedd6`

The criteria file existed before the first scientific fit. Its classifications
and decision mapping were applied mechanically without post-result changes.

**NO POST-PHASE3C ARCHITECTURE WAS IMPLEMENTED BEFORE THIS FREEZE.**

## Frozen targets, horizons, and support

| Index | Resource | Canonical target | Transform |
|---:|---|---|---|
| 0 | CPU | `machineXX__cpu_utilization` | identity |
| 1 | THROUGHPUT | `machineXX__throughput_total` (bond0 TX + bond0 RX) | `log1p` |
| 2 | MEMORY | `machineXX__memory_used` | identity |
| 3 | DISK_WRITE | `machineXX__disk_write` | `log1p` |

The fixed leads are `[1,2,4,8,16,32,64,128]`; context candidates are
`[32,64,128]`; seeds are `[0,1,2]`; and the five rolling outer folds are
unchanged. All formulations use the common legal-origin universe defined by
the complete four-resource tuple, maximum context 128, segment-safe histories
and targets, all eight leads, and lead-128 target-time purging. Shorter contexts
and single-target formulations receive no extra samples. Robust median/IQR
scalers are fitted only on the applicable training partition.

## Frozen architecture identities

- **S1:** one independent two-layer unidirectional LSTM per target, own-resource
  input `[N,L,1]`, hidden size 64, dropout 0.1, final recurrent representation,
  linear eight-horizon output.
- **S2:** one independent LSTM per target with the same backbone and ordered
  four-resource input `[N,L,4]`, producing eight horizons for that target.
- **M1:** one shared LSTM encoder consuming `[N,L,4]`, followed by four separate
  linear heads in `CPU, THROUGHPUT, MEMORY, DISK_WRITE` order, output
  `[N,4,8]`. Its loss is the unchanged equal mean of the four resource MSEs.

No attention, gating, adapters, selective fusion, shared/private encoders,
adaptive weighting, machine embeddings, Transformer, or other proposed
architecture is part of this checkpoint.

## Execution and validation

| Formulation | Inner fits | Final fits | Metric rows |
|---|---:|---:|---:|
| S1 | 1,260 | 420 | 3,360 |
| S2 | 1,260 | 420 | 3,360 |
| M1 | 315 | 105 | 3,360 |
| **Total** | **2,835** | **945** | **10,080** |

- Total fits: **3,780**
- Selected contexts: **315**
- Scientific figures: **8**
- Phase 3B tests: **48/48 PASS**
- Independent Phase 3C validation: **PASS**
- Missing or duplicate scientific runs: **0**
- Support, resource-support, leakage, segment-crossing, context-selection,
  epoch-selection, transform, scaler, artifact, metric-recomputation, and
  aggregation mismatches: **0**

## Frozen primary results and prospective classifications

| Comparison | Resource | Primary macro-MAE gain | Classification |
|---|---|---:|---|
| S2 vs S1 | CPU | -3.3130% | NEUTRAL_OR_MIXED |
| S2 vs S1 | THROUGHPUT | -0.2428% | NEUTRAL_OR_MIXED |
| S2 vs S1 | MEMORY | +0.8594% | NEUTRAL_OR_MIXED |
| S2 vs S1 | DISK_WRITE | -0.4923% | NEUTRAL_OR_MIXED |
| M1 vs S2 | CPU | +0.4696% | NEUTRAL_OR_MIXED |
| M1 vs S2 | THROUGHPUT | -0.8401% | NEUTRAL_OR_MIXED |
| M1 vs S2 | MEMORY | -18.4769% | BROAD_NEGATIVE |
| M1 vs S2 | DISK_WRITE | -0.7956% | NEUTRAL_OR_MIXED |
| M1 vs S1 | CPU | -2.8279% | NEUTRAL_OR_MIXED |
| M1 vs S1 | THROUGHPUT | -1.0849% | NEUTRAL_OR_MIXED |
| M1 vs S1 | MEMORY | -17.4587% | BROAD_NEGATIVE |
| M1 vs S1 | DISK_WRITE | -1.2918% | BROAD_NEGATIVE |

- Global cross-resource input decision: **CROSS_RESOURCE_INPUT_NOT_SUPPORTED**
- Global shared-representation decision: **SHARED_REPRESENTATION_NOT_SUPPORTED**
- Phase 3C decision: **MULTI_RESOURCE_FORECASTING_PREMISE_WEAK**

Cross-resource input augmentation was not broadly beneficial. S2 improved only
memory overall, modestly, while CPU, throughput, and disk-write degraded. M1
provided a small CPU improvement relative to S2 but degraded the other three
resources, with the largest degradation in memory. M1 was worse than S1 for
all four resources overall. Resource-specific negative transfer is
descriptively present, especially for memory, but no causal failure mechanism
is claimed.

## M1 loss balance and efficiency

| Resource | Scientific selected-inner mean loss share |
|---|---:|
| CPU | 48.24% |
| THROUGHPUT | 26.32% |
| MEMORY | 13.67% |
| DISK_WRITE | 11.77% |

The non-scientific pilot CPU share was approximately 81-84%; the scientific
CPU share was 48.24%. The preliminary CPU-majority pattern did not persist at
the same magnitude. The evidence does not justify attributing M1's performance
primarily to simple numerical CPU loss domination, nor does it make adaptive
loss weighting the automatic next experiment.

S2 uses 206,880 parameters across four independent inference models. M1 uses
53,280 parameters in one inference model: a **74.25% parameter reduction** and
**75% model-count reduction**. This is substantial footprint efficiency, but
it does not compensate scientifically for the accuracy degradation, especially
for memory. Accuracy and efficiency are separate conclusions.

## Runtime and artifact record

| Formulation | Inner fit-hours | Final fit-hours | Prediction hours |
|---|---:|---:|---:|
| S1 | 30.5146 | 10.8342 | 0.0341 |
| S2 | 28.4970 | 8.7892 | 0.0344 |
| M1 | 9.7465 | 3.0855 | 0.0071 |

- Main resumed invocation wall time: **23.555 hours**
- Aggregate fit time: **91.467 hours**
- Aggregate prediction time: **0.076 hours**
- Peak RSS: **1.759 GiB**
- Scientific artifacts: approximately **621.45 MiB**

## Scientific artifact inventory

- Inventory: `PHASE3C_SCIENTIFIC_ARTIFACT_SHA256.csv`
- Inventory entries: **5,706**
- Inventory total bytes: **651,721,110**
- Inventory SHA-256:
  `95bbb842f60bbc8c2c1bc11704c413e8e654594476d16c40850a217913c5155e`
- Scientific-tree SHA-256:
  `ec35446710f90a7b1e1a86cdbca6bedd4face31ec68ea56e83fd682addd89a65`

The inventory covers the prospective criteria, scientific execution/analysis/
validation code, scientific report, and every file under
`outputs/scientific`, including ignored models, predictions, completion
records, registries, selections, metrics, support and persistence artifacts,
M1 loss histories, comparisons, figures, runtime accounting, and validation.
The scientific-tree digest is SHA-256 over the sorted UTF-8 records
`relative_path,byte_size,sha256\n`, excluding the inventory itself to avoid a
circular checksum dependency.

## Frozen-history integrity

The independent validator reverified Phase 3B, Phase 3A, Neural-v2, DLinear,
LSTM, PatchTST, Phase 2A, original deterministic, corrected deterministic, all
six raw inputs, and the canonical panel. Every inventory passed. The canonical
panel SHA-256 remains
`c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`.
TCN-v2 scientific runs remain **0**; PatchTST multi-resource scientific runs
remain **0**; post-Phase3C proposed architecture implementations remain **0**.
