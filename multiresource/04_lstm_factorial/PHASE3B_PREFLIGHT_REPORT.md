# Phase 3B Plain-LSTM Factorial Preflight Report

## Status and frozen history

Phase 3B implementation validation is **PASS**. Preflight began at commit
`70eea336302aebfaaa20c79b1972b1ebb835442c`, tagged
`phase3a-multiresource-design-freeze-v1`. The prospective factorial decision
SHA-256 is
`2bfb2610bd8e869dc038bccd6b18656cd2c968b9d548c758487cae500cbf5677`.

Phase 3A (25/25), Neural-v2 (29/29), DLinear (1,347/1,347), LSTM
(1,349/1,349), PatchTST (1,352/1,352), Phase 2A (33/33), original
deterministic (632/632), and corrected deterministic (1,070/1,070) inventories
all pass. All six raw hashes are unchanged. The canonical panel SHA-256 remains
`c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`.

## Targets, order, and preprocessing

The fixed resource order is CPU, throughput, memory, disk-write. The fixed
horizon order is `[1,2,4,8,16,32,64,128]`. CPU utilization and memory used
receive the identity transform. Total throughput (bond0 TX + RX) and disk-write
activity receive `log1p`. Training-partition median/IQR scaling follows the
resource transform. Inner scalers use inner train only; future final scalers
must use legal outer train only. Non-positive IQR is a hard error.

Throughput and disk-write inversion is inverse robust scaling, `expm1`, then
the prospectively fixed physical projection `max(0, prediction)`. The pilot
also recorded unclipped minima and pre-projection negative rates.

## Common support, folds, and leakage controls

One complete four-resource, eight-lead support universe is formed with
`Lmax=128`. All histories and targets must be finite and segment-safe. Contexts
32 and 64 gain no extra origins. All S1 targets, all S2 targets, and M1 use the
same hashes for inner train, inner validation, outer train, and outer test.
The 105 machine-fold-context support records have **0** mismatches.

The accepted five expanding chronological folds are reused. Outer training and
the chronological latest-15% inner split are both target-time purged at lead
128. No random split exists. The pilot constructed only inner-training and
inner-validation windows; outer-test support was hashed as metadata, but no
outer-test value, window, prediction, or metric was accessed.

For the pilot cell, support is:

| Partition | Origins | SHA-256 |
|---|---:|---|
| Inner train | 5,835 | `a694afda3cbbf49b0978a9f3014be0dd0874807b6df93a9716e0a4992387279c` |
| Inner validation | 1,044 | `e74b78cf44a0383558f778204b610994de8588da569399d5f8520ebed9eb2445` |
| Outer train metadata | 6,959 | `93add5d4d2b941f30b019eed673699888959295783028dc125bb554fdd67a16d` |
| Outer test metadata only | 1,514 | `59561fe6e2193ae1e9c1c155ad2c6bc664b6328bd4ea5cdebaeca71791569d1c` |

## Plain factorial architectures

- **S1:** `[N,L,1]`, one resource only, one independent two-layer
  unidirectional LSTM and linear `64 -> 8` head per resource.
- **S2:** `[N,L,4]`, fixed four-resource order, one independent plain LSTM and
  linear `64 -> 8` head per target resource.
- **M1:** `[N,L,4]`, one shared plain LSTM encoder and exactly four independent
  linear `64 -> 8` heads, stacked as `[N,4,8]`.

All use hidden size 64, two layers, dropout 0.1, and the final recurrent output.
There is no attention, adapter, gating, private encoder, selective fusion,
adaptive weighting, machine embedding, MoE, Transformer, or novel architecture.

## Loss, selection, and refit lifecycle

S1/S2 loss is mean transformed/scaled MSE over batch and eight horizons. M1
computes one such loss per resource and minimizes their unweighted arithmetic
mean. Each loss and its fraction of the four-resource sum are logged.

S1 and S2 context selection minimizes mean normalized validation MAE over eight
horizons and three seeds independently per target/machine/fold. M1 minimizes
the equal mean over four resources, eight horizons, and three seeds per
machine/fold. Smaller L breaks ties. Each selected seed retains its own best
inner epoch. The final-refit API starts from scratch with a fixed epoch count
and exposes neither validation nor outer test.

## Metric and aggregation semantics

Native MAE, RMSE, R-squared, NMAE, and persistence skill are retained per
resource and lead. Native MAEs are not averaged across resources. Primary macro
results first average seeds inside machine-fold-resource-lead cells, weight
machine-fold cells equally, aggregate each formulation separately, then compute
relative gain. Pooled and cell-relative results and positive machine/fold/seed
fractions remain secondary diagnostics.

## Capacity accounting

| Formulation | Encoder / model parameters | Head parameters | Total system parameters | Inference models per cell | Serialized bytes/model |
|---|---:|---:|---:|---:|---:|
| S1 | 50,952 per resource model | included | 203,808 across four | 4 | 207,301 |
| S2 | 51,720 per target model | included | 206,880 across four | 4 | 210,373 |
| M1 | 51,200 shared | 2,080 across four heads | 53,280 | 1 | 218,163 |

Counts are reported transparently; parameter totals were not artificially
equalized.

## Planned scientific scale

| Formulation | Inner fits | Final fits | Total fits | Resource-lead metric rows |
|---|---:|---:|---:|---:|
| S1 | 1,260 | 420 | 1,680 | 3,360 |
| S2 | 1,260 | 420 | 1,680 | 3,360 |
| M1 | 315 | 105 | 420 | 3,360 |
| **Total** | **2,835** | **945** | **3,780** | **10,080** |

No part of this planned workload was executed.

## Tests

The suite contains **48 tests**, all passing. It covers target/resource/horizon
identity, transformations and physical inversion, train-only scaling and fatal
zero IQR, maximum-history common support, segment and purge safety, identical
formulation IDs, architecture and output shapes, actual M1 sharing and separate
heads, equal four-resource loss and logging, determinism, all selection rules,
per-seed fixed-epoch refit, outer-test-free fitting APIs, metrics and macro
aggregation, parameter accounting, unique run IDs, and atomic resumability.

## Non-scientific nine-model pilot

The pilot used machine01, fold 1, seed 0, L=64, full legal inner support, and
exactly five epochs without early stopping or context selection.

| Formulation | Target | Parameters | Train s/epoch | Five-epoch train s | Validation s | Samples/s |
|---|---|---:|---:|---:|---:|---:|
| S1 | CPU | 50,952 | 1.019 | 5.097 | 0.288 | 5,724.4 |
| S1 | throughput | 50,952 | 1.016 | 5.081 | 0.287 | 5,741.8 |
| S1 | memory | 50,952 | 1.017 | 5.086 | 0.286 | 5,736.2 |
| S1 | disk-write | 50,952 | 1.016 | 5.078 | 0.287 | 5,745.5 |
| S2 | CPU | 51,720 | 1.022 | 5.110 | 0.280 | 5,709.5 |
| S2 | throughput | 51,720 | 1.026 | 5.130 | 0.283 | 5,686.9 |
| S2 | memory | 51,720 | 1.022 | 5.112 | 0.279 | 5,707.0 |
| S2 | disk-write | 51,720 | 1.025 | 5.127 | 0.280 | 5,690.5 |
| M1 | all four | 53,280 | 1.028 | 5.140 | 0.281 | 5,675.8 |

Peak process RSS was about 1.33 GB. Each model used 5,835 training and 1,044
validation samples.

## M1 loss-balance diagnostic

Final-three-epoch means are:

| Resource | Train normalized MSE | Validation normalized MSE | Train share | Validation share |
|---|---:|---:|---:|---:|
| CPU | 273.197 | 266.109 | 83.96% | 80.81% |
| Throughput | 2.227 | 1.805 | 0.68% | 0.55% |
| Memory | 28.129 | 33.812 | 8.65% | 10.27% |
| Disk-write | 21.828 | 27.597 | 6.71% | 8.38% |

CPU numerically dominates this pilot cell even after robust scaling and alone
accounts for a majority of joint normalized loss. The four losses are not all
within a broadly comparable order of magnitude. This is a scientific risk and
a result of differing normalized task difficulty, not a reason to change the
prospectively fixed equal-weight plain baseline. No adaptive balancing was
implemented.

## Native-unit sanity checks

These results are transform/order/numerical diagnostics only, not benchmark
evidence. Values below average the eight validation leads.

| Formulation | Resource | Mean MAE | Mean RMSE | Mean R-squared | Mean NMAE | Negative pre-projection rate |
|---|---|---:|---:|---:|---:|---:|
| S1 | CPU | 3.852 | 12.128 | 0.069 | 5.149 | 0% |
| S1 | throughput | 33.827 | 157.924 | 0.023 | 4.451 | 0% |
| S1 | memory | 616,748,529 | 1,755,187,000 | 0.122 | 1.983 | 0% |
| S1 | disk-write | 10,455,638 | 46,033,830 | -0.042 | 130.682 | 0% |
| S2 | CPU | 3.769 | 12.072 | 0.078 | 5.038 | 0% |
| S2 | throughput | 33.214 | 157.495 | 0.027 | 4.371 | 0% |
| S2 | memory | 488,491,366 | 1,748,438,000 | 0.129 | 1.571 | 0% |
| S2 | disk-write | 10,487,331 | 46,020,240 | -0.042 | 131.078 | 0% |
| M1 | CPU | 3.619 | 12.060 | 0.080 | 4.837 | 0% |
| M1 | throughput | 33.286 | 158.444 | 0.016 | 4.380 | 0% |
| M1 | memory | 566,612,976 | 1,791,775,000 | 0.085 | 1.822 | 0% |
| M1 | disk-write | 10,518,005 | 46,104,770 | -0.046 | 131.461 | 0% |

All inversions were finite, ordering checks passed, physical projection was
applied consistently, and throughput/disk-write produced no negative native
prediction before projection in this pilot.

## Measured runtime and disk projection

The projection uses the nine measured CPU timings, measured validation costs,
the fold-1 outer/inner training-size ratio 1.1926 for final refits, and 5%
analysis/validation overhead.

| Scenario | Effective epochs | S1 train total | S2 train total | M1 train total | Overhead | Total CPU-hours |
|---|---:|---:|---:|---:|---:|---:|
| Optimistic | 10 | 5.18 h | 5.21 h | 1.31 h | 0.58 h | 12.27 h |
| Central | 25 | 12.94 h | 13.01 h | 3.27 h | 1.46 h | 30.68 h |
| Conservative | 50 | 25.88 h | 26.02 h | 6.53 h | 2.92 h | 61.36 h |

Projected retained model states use 198,330,195 bytes. Planning for 13,286,880
resource-lead prediction rows at 64 compressed bytes/row adds 850,360,320
bytes, and compact metrics/provenance are budgeted 25 MB. Total expected disk
use is about **1.073 GB**. This is a planning estimate; no outer-test prediction
was generated to obtain it.

## Resumability

Run identity includes formulation, resource if applicable, machine, fold, L,
seed, inner/final phase, config hash, and support hash. Atomic completion files
are trusted only when identity and all expected artifact hashes validate.
Incomplete, malformed, config-mismatched, support-mismatched, or artifact-
mismatched records are rerun. Only best-epoch selection/restart/provenance state
is retained; permanent epoch checkpoints are excluded.

## Risks and readiness

1. Four-resource common support is materially smaller than CPU-only support.
2. Separate-machine S1/S2 produces many models and operational overhead.
3. CPU and memory have different persistence and error behavior.
4. Throughput and disk-write require transformed-space training and physical
   inversion.
5. Equal robust scaling does not equalize task difficulty; CPU dominated this
   pilot's M1 normalized loss.
6. M1 uses one inference model where S2 uses four, so efficiency and accuracy
   must both be reported.
7. Several cross-resource dependencies are weak, so negative transfer is
   plausible.
8. Plain M1 is intentionally not novel; it exists to determine whether naive
   sharing helps before any mechanism is proposed.

The implementation is technically ready for a separate protocol-freeze step.
This conclusion is based on support, leakage, lifecycle, transform, test, and
execution-boundary validation—not on pilot accuracy.

## Final preflight disposition

**READY_FOR_FACTORIAL_FREEZE**

No scientific result, scientific context selection, full outer refit,
outer-test performance inspection, TCN-v2 execution, PatchTST multi-resource
run, or proposed architecture was produced.
