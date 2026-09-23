# TimeTrack Neural-v2 Reproducibility Freeze Manifest

Freeze date: 2026-09-23 (Europe/Helsinki)

Branch: `main`

Pre-freeze HEAD: `bdc7c9243cb33cbb3fadee7b911810a164d8da43`

Checkpoint tag to create: `neural-v2-protocol-freeze-v1`

**NO SCIENTIFIC NEURAL RESULT EXISTED AT FREEZE TIME.**

Only the approved non-scientific, five-epoch CPU timing pilot existed. It used
machine01, outer fold 1, seed 0, L=64, full legal inner train/validation
support, and never built or evaluated an outer-test window.

## Provenance

- Accepted deterministic checkpoint commit:
  `bdc7c9243cb33cbb3fadee7b911810a164d8da43`
- Accepted deterministic checkpoint tag:
  `phase2b1-corrected-deterministic-freeze-v1`
- Neural-v2 prospective decision SHA-256:
  `9cec1dc25dc20dd1bf20ac3d7d495f731d41106935a66726d79a182fd058a08c`
- Protocol SHA-256:
  `c7e886dda22b052e53973c28ba0f5f0817c851bfd62ab38e81292e47e955cff1`
- Configuration SHA-256:
  `39f511e1a09f5e466aab89cee0164be29b04ec0745d1ff5e4422b5556011272e`
- Timing result SHA-256:
  `b971a8acd320aa5bdaf128708e45581aaa5aeffb0864e0d3dec6ed0d5aabff4b`
- Runtime projection SHA-256:
  `d8a73fd6916333cd509e1a2faa1b1f4f05ef25574044cd6c5fcfc815572cbac7`
- Complete compact inventory:
  `benchmark/neural_v2/NEURAL_V2_ARTIFACT_SHA256.csv`
- Compact inventory SHA-256:
  `5af4ae5bc9f275cd658ca0a8ee3a075a4abcd6bbba145ea14ef3e78075d58681`
- Inventoried compact files: 29

The committed inventory records the exact path, byte size, and SHA-256 of the
protocol, decision, configuration, all source files, all tests, both pilot JSON
records, the preflight report, guarded driver, pilot scripts, package markers,
and scientific-output README.

## Scientific task and features

Target: machine-level CPU utilization for machines 01-07.

Every model outputs CPU at the eight genuine future leads
`[1,2,4,8,16,32,64,128]`, approximately `[0.705,1.410,2.819,5.638,11.276,
22.552,45.104,90.208]` minutes.

Feature sets are exactly:

- `F0_LOCAL`: target-machine CPU only;
- `F1_THROUGHPUT`: target-machine CPU plus validated same-machine total
  throughput, defined as bond0 TX plus bond0 RX.

LOMO CPU, memory, disk, RTT, jitter, packet telemetry, and per-core CPU are not
part of neural-v2. The narrowed scope was prospectively informed by the already
frozen corrected deterministic evidence.

## Common support, folds, and purge

For every machine, fold, and candidate context, eligibility requires finite
target CPU and same-machine throughput history, all eight finite CPU targets,
complete history, and no history or target crossing a canonical temporal
segment.

A single F1-finite maximum-history support of 128 samples is used unchanged for
F0, F1, and L in `{32,64,128}`. Shorter models receive the final contiguous L
observations from that support. Thus F0/F1 inner-train, inner-validation, final
outer-train, and outer-test sample IDs and hashes remain identical even if the
two features select different L values.

The accepted deterministic five expanding chronological outer-fold boundaries
are reused read-only. Their five test blocks remain non-overlapping. Both outer
and inner training apply target-time purge at the longest lead 128. Inner
validation is the chronologically latest 15% of legal outer training. There is
no chronological shuffle and no outer-test input to selection, scaling,
normalization, fitting, early stopping, or epoch choice.

## Seeds, selection, and final refit

- Seeds: `[0,1,2]`
- Candidate context lengths: `[32,64,128]`
- Inner score: mean validation MAE across all three seeds and eight leads
- L tie-break: smaller L
- Selected L: one per model-feature-machine-fold cell, shared by final seeds
- Epoch record: best inner-validation epoch retained separately per seed at the
  selected L
- Final refit: initialize from scratch, fit full legal outer training for that
  seed's fixed epoch count, then evaluate outer test once

The final-refit API accepts no validation or test input, preventing
outer-test-controlled training by construction. The guarded driver defaults to
plan-only and requires two explicit execution flags.

## Exact model definitions

### DLinear

Input `[batch,L,channels]`; one channel for F0 and two for F1. Moving-average
kernel 25, replicated edge padding, trend/residual decomposition, independent
linear history-to-eight projections, then learned channel projection to eight
CPU targets.

### LSTM

Input `[batch,L,channels]`; hidden size 64, two unidirectional layers, dropout
0.1 between layers, no attention, no bidirectionality, final recurrent
representation, and an eight-output linear head.

### Full-receptive-field causal TCN-v2

Six causal residual blocks with channels `[32,32,32,32,32,32]`, kernel 3,
dilations `[1,2,4,8,16,32]`, two causal convolutions per block, dropout 0.1,
and an eight-output head on the final causal representation.

Exact receptive field:

`RF = 1 + 2 * (3 - 1) * (1 + 2 + 4 + 8 + 16 + 32) = 253`

Therefore RF 253 is at least the maximum selected history 128. The Phase 2A
B4-v1 RF=13 implementation remains unchanged and preserved for provenance.

### PatchTST

Patch length 8, stride 4, d_model 64, four attention heads, two encoder layers,
feed-forward dimension 128, and dropout 0.1. Patches contain only observed
history at or before the forecast origin. Tokenization and transformer encoding
are channel-independent with shared weights; the fixed output head performs
late multivariate channel mixing and emits eight CPU targets.

## Training defaults

| Setting | Frozen value |
|---|---|
| Loss | MSE |
| Batch size | 256 |
| Maximum epochs | 50 |
| Early-stopping patience | 7 |
| Gradient clipping | 1.0 |
| DLinear/LSTM/TCN optimizer | Adam |
| PatchTST optimizer | AdamW |
| Learning rate | 0.001 |
| PatchTST weight decay | 0.0001 |
| Feature scaling | training-support only |
| Target scaling | none; physical CPU-utilization scale retained |

## Parameter counts

| Model | Feature | L=32 | L=64 | L=128 |
|---|---|---:|---:|---:|
| DLinear | F0 | 530 | 1,042 | 2,066 |
| DLinear | F1 | 531 | 1,043 | 2,067 |
| LSTM | F0 | 50,952 | 50,952 | 50,952 |
| LSTM | F1 | 51,208 | 51,208 | 51,208 |
| TCN-v2 | F0 | 34,600 | 34,600 | 34,600 |
| TCN-v2 | F1 | 34,728 | 34,728 | 34,728 |
| PatchTST | F0 | 68,488 | 69,000 | 70,024 |
| PatchTST | F1 | 69,000 | 69,512 | 70,536 |

## Validation result

The complete neural-v2 test suite passed: **28 passed, 0 failed**.

Coverage includes exact leads and feature scope, common-support identity across
F0/F1 and all L, segment safety, both purges, training-only transformations,
output shapes, all model definitions, RF=253, TCN causality, PatchTST patching,
deterministic seeds, seed-mean selection and tie-break, per-seed epochs, fixed
final refit, absence of outer-test controls, unique IDs, schemas, atomic
completion validation, and execution counts.

## Non-scientific timing pilot

Pilot support: 7,864 inner-training samples and 1,392 inner-validation samples.
F0 and F1 used identical train and validation hashes. Each run completed
exactly five epochs.

| Model | F0 s/epoch | F1 s/epoch | F0 train samples/s | F1 train samples/s |
|---|---:|---:|---:|---:|
| DLinear | 0.018 | 0.022 | 454,740 | 373,253 |
| LSTM | 1.410 | 1.417 | 5,875 | 5,835 |
| TCN-v2 | 5.702 | 5.805 | 1,506 | 1,477 |
| PatchTST | 0.950 | 1.718 | 8,616 | 4,786 |

The pilot is timing/provenance data only. Its losses and predictions are not
reported, retained as scientific output, or interpreted.

## Expected scale and runtime

- Model-feature-machine-fold cells: 280
- Inner fits: `280 * 3 L * 3 seeds = 2,520`
- Final refits: `280 * 3 seeds = 840`
- Total fits: 3,360
- Final lead-metric rows: `840 * 8 = 6,720`

Measured-throughput projections:

| Scenario | Mean epochs | Selected-L assumption | Projected runtime |
|---|---:|---:|---:|
| Optimistic | 10 | 32 | 27.3 h / 1.14 d |
| Central | 25 | 64 | 77.7 h / 3.24 d |
| Conservative | 50 | 128 | 192.9 h / 8.04 d |

## Expected output schemas and resumability

Final prediction records contain:

`run_id, model, feature_set, machine, outer_fold, seed, lead, sample_id,
origin_index, origin_timestamp, target_timestamp, y_true, y_pred,
sample_set_hash`

Final metric records contain:

`run_id, model, feature_set, machine, outer_fold, seed, lead, mae, rmse, r2`

Compact selection records additionally retain selected L, seed-mean inner MAE,
per-seed best epochs, config hash, decision hash, and support hashes. Final
completion records retain run/config/support identity and hashes of prediction
and metric artifacts.

Writes are atomic. Restart skipping is allowed only after identity and artifact
hash validation. An interrupted current fit is rerun; partial state is never
treated as complete. No every-epoch checkpoint is retained. Future checkpoints,
predictions, and temporary progress are not part of this protocol freeze.

## Freeze boundary

At freeze time:

- scientific neural outer runs: 0;
- scientific neural predictions or metrics: 0;
- deterministic artifacts modified: 0;
- raw or canonical artifacts modified: 0;
- Phase 2A or B4-v1 files modified: 0;
- multi-target models created: 0.

**NO SCIENTIFIC NEURAL RESULT EXISTED AT FREEZE TIME.**
