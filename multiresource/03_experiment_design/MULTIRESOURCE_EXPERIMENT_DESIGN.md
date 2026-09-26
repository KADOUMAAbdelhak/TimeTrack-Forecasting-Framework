# Multi-Resource Experiment Design

## Status

**DRAFT DESIGN — NOT SCIENTIFICALLY FROZEN.**

No forecasting model was trained or implemented during this audit. No final
novel architecture is selected.

## Leakage-safe development region

`MULTIRESOURCE_DESIGN_REGION` is the canonical chronological prefix containing
rows 0-16,877 (16,878 rows), from 2024-06-24 13:37:06.164306 through
2024-07-07 16:52:17.183763. It ends before the earliest first outer-test origin
across all seven frozen CPU benchmark machine splits (machine06, row 16,878).

- Membership SHA-256:
  `9980b51cd09ed865bc87b01de074d20413c853cfa5e67d96832e69557acb9e03`
- Region JSON SHA-256:
  `b3a24cd1ffdfc947fbf5e5742a6f1266325230d45501023af4c115345640b0f6`

All decisions about representation, transforms, dependencies, scaling, and
losses use only this region. Full-panel access was limited to structural
availability, missingness, units, identity checks, impossible values, and
support counts.

## Proposed target tuple

| Resource | Canonical signal | Training representation | Native evaluation |
|---|---|---|---|
| CPU | `machineXX__cpu_utilization` | identity, then robust scale | percent-like raw units |
| Throughput | `machineXX__throughput_total` | `log1p`, then robust scale | exact `expm1`, raw throughput units |
| Memory | `machineXX__memory_used` | identity, then robust scale | bytes |
| Disk | `machineXX__disk_write` | `log1p`, then robust scale | exact `expm1`, raw activity/rate units |

Used-disk occupancy is retained as an auxiliary/secondary analysis target, not
the primary disk target. Disk-read activity is rejected for the core tuple
because its zero fraction is highly inconsistent and reaches 99.7%.

The conceptual M1 output tensor is `[batch, resource, horizon]`, ordinarily
`[batch,4,8]`, ordered CPU, throughput, memory, disk-write and leads
`[1,2,4,8,16,32,64,128]`. If a target later fails preflight, its resource axis
entry is removed consistently from S1, S2, and M1; it is not silently masked in
only one formulation.

## Common support and folds

- Maximum history: 128 samples.
- Every history and all eight future targets must be finite for every selected
  resource.
- Histories and targets may not cross canonical temporal segments.
- Use the existing five expanding chronological outer-fold convention and
  lead-128 target-time purge; do not create random splits.
- The inner validation split and purge must remain nested inside each outer
  training region.
- For every comparison, S1, S2, and M1 must use identical origin IDs, target
  IDs, machines, folds, leads, and seeds.

The proposed disk-write tuple retains 8,221-14,967 legal full-panel origins per
machine (median 14,345; total 92,994). This is about 52% below CPU-only support
but remains substantial. Used-disk occupancy would lose no additional support
beyond CPU+throughput, but its near-trivial persistence makes it a poor primary
target.

## Preprocessing and target scaling

Every fold fits preprocessing on legal outer-training data only. For resource
`r`, after its fixed transform `g_r`, use:

`z_r = (g_r(y_r) - median_train,r) / IQR_train,r`.

Use an explicitly predeclared fallback (training standard deviation, then 1)
only if training IQR is zero. Inputs and targets use resource-specific
statistics. CPU and memory use identity transforms; throughput and disk-write
use `log1p`. Both audited log transforms are valid because their full-panel
values are nonnegative. `expm1(log1p(x)) = x` permits native-unit evaluation.

Raw joint MSE is forbidden: median development-region raw variance proxies are
approximately 4.25 for CPU, 7.23e3 for throughput, 3.16e17 for memory, and
1.86e12 for disk-write. Memory would dominate by many orders of magnitude.
The baseline loss is the equal-resource, equal-horizon mean of squared errors
in normalized target space. Resource-level losses must also be logged
separately. Adaptive loss balancing is a later ablation, not the baseline.

## Metrics and primary comparisons

For every resource, machine, fold, seed, and lead, report native-unit MAE,
RMSE, and R2. Never average native MAEs across resources.

Training-only robust normalized MAE is:

`NMAE_r = MAE_r / IQR_train,r`.

Persistence skill is:

`Skill_r = 1 - MAE_model,r / MAE_persistence,r`.

For formulation `A` against matched reference `B`, first average seeds within
machine-fold-lead cells, then give machine-fold cells equal weight separately
for each resource and lead:

`Gain_r,h(A vs B) = 100 * (MacroMAE_r,h(B) - MacroMAE_r,h(A)) / MacroMAE_r,h(B)`.

The primary multi-task claim is the per-resource vector `Gain(M1 vs S2)`, not a
sum of heterogeneous errors. `M1 vs S1` measures total joint-system benefit;
`S2 vs S1` measures cross-resource input information. Equal-resource mean or
median relative gain and mean NMAE may be secondary unitless summaries, but the
resource-wise results and harm counts remain mandatory.

## Mandatory S1/S2/M1 factorial

### S1 — independent / own-resource input

One model per target resource. Input is only that resource's history; output is
only that resource's eight horizons. This is the pure single-resource baseline.

### S2 — independent / all-resource input

One model per target resource. Input contains all selected resource histories;
output remains only one resource. `S2 - S1` isolates cross-resource input value.

### M1 — shared multi-target

One model consumes all selected histories, uses a shared temporal
representation, and emits all resources through resource-specific output heads.
`M1 - S2` isolates multi-task/shared-representation value. `M1 - S1` measures
total joint-system benefit.

S1 and S2 must not be conflated with M1. A multi-task claim is invalid if M1 is
compared only with S1, because both input scope and sharing change.

## Machine strategy

The primary experiment uses a separate model per machine. Prior results and the
Phase 3A dependency audit show substantial machine heterogeneity, while seven
machines are few enough for controlled matched comparisons. A global model with
machine identity/conditioning is a later extension after the factorial is
resolved; adding it now would multiply questions and obscure the sharing test.

## Baseline families

Keep the baseline set small:

1. Persistence: mandatory, parameter-free difficulty reference.
2. LightGBM: strong independent S1/S2 absolute-performance reference; it does
   not provide an equivalent shared M1 and therefore is not the sharing
   backbone.
3. LSTM: recommended primary S1/S2/M1 factorial backbone because the same
   temporal encoder can support all three formulations, CPU context benefit was
   positive overall, and compute is manageable.
4. PatchTST: optional secondary factorial backbone if budget remains. It is a
   strong neural absolute forecaster but did not broadly exploit throughput in
   the CPU-only benchmark.
5. DLinear: omit from the initial Phase 3 factorial; it was weaker and showed a
   negative CPU throughput effect, so it adds cost without a distinct necessary
   control.

This is a baseline recommendation, not selection of a proposed novel model.

## Model-capacity and cost fairness

Report, for every formulation:

- parameters per model;
- total parameters across the deployed four-target system;
- training fits, epochs, and wall/CPU time;
- peak memory;
- per-origin inference time and total inference cost; and
- storage/checkpoint size.

Architectures should use the same backbone depth/width where possible. Do not
force identical parameter counts if doing so creates artificial architectures.
Interpret M1 against both S2 per-model capacity and the total four-model S2
system. Include a modest capacity-matched sensitivity check only if M1's shared
core is materially larger than an S2 model.

## Approximate experiment scale and runtime tiers

With four resources, seven machines, five folds, three seeds, three context
candidates, and one S1/S2/M1-capable backbone:

- S1 inner fits: 1,260; final fits: 420.
- S2 inner fits: 1,260; final fits: 420.
- M1 inner fits: 315; final fits: 105.
- Total: 2,835 inner + 945 final = 3,780 fits.

Runtime tiers should be measured by a non-scientific timing pilot before a
freeze: persistence/structural checks (minutes), LightGBM independent
references (low), LSTM factorial (medium; likely tens of CPU-hours), and an
optional PatchTST replication (high). Based on prior neural CPU runs, budget a
rough 35-75 CPU-hour range for one full neural factorial until the pilot replaces
this estimate. Parallel wall time, resource contention, and multi-output cost
must be recorded rather than inferred from single-target fits.

## Potential novelty mechanisms — not selected

| Mechanism | Evidence that could justify it | Required comparison | Failure mode addressed |
|---|---|---|---|
| Resource-aware shared encoder | radically different dynamics/scales | M1 vs S2 plus homogeneous-M1 ablation | negative transfer from treating resources identically |
| Resource-specific adapters | weak/heterogeneous differenced dependencies | adapter M1 vs plain shared M1 | shared core erases resource-specific dynamics |
| Resource-specific normalization | raw variance differs by many orders | fixed robust scaling vs shared/raw scaling | loss and representation domination |
| Horizon-specific heads | persistence difficulty changes with lead | common head vs horizon heads | one representation underfits long horizons |
| Adaptive loss balancing | residual normalized losses remain imbalanced | fixed equal loss vs predeclared adaptive method | one task dominates optimization |
| Selective cross-resource fusion | CPU/throughput strong; other pairs weak | selective fusion vs all-to-all S2/M1 | noisy or harmful resource transfer |
| Shared/private latent decomposition | level links exceed differenced links | shared/private vs shared-only M1 | confounding common level with task-specific changes |
| Cross-resource attention | lag profiles differ by pair | attention vs parameter-matched fusion | fixed fusion misses delayed relationships |
| Machine-aware conditioning | dependency ranges vary strongly by machine | global conditioned model vs separate-machine primary | global model averages incompatible regimes |

## Major scientific risks

- Joint support falls materially when disk activity is included.
- Memory and disk byte units lack explicit capacity telemetry; memory
  utilization percentage cannot be derived safely.
- Disk-write units are unknown and require cautious native-unit labeling.
- Log-space optimization may not optimize native-unit tail error.
- Cross-resource correlations are heterogeneous and do not establish causality.
- Separate-machine factorial size is substantial; changing backbones before a
  timing freeze risks uncontrolled scope growth.
- A shared model can win through parameter efficiency or regularization rather
  than cross-resource mechanisms; capacity and total-system reporting is vital.

## Design gate

**B. MULTI_RESOURCE_STUDY_SUPPORTED_WITH_TARGET_CHANGES**

Four target families remain feasible, but the defensible disk target changes
from occupancy to transformed write activity, and throughput should use a
`log1p` training representation. Nothing in this draft authorizes model
implementation or scientific execution.
