# TimeTrack Neural Benchmark V2 Protocol

Status: prospective design and implementation freeze candidate. No scientific
neural result exists.

Decision record SHA-256:
`9cec1dc25dc20dd1bf20ac3d7d495f731d41106935a66726d79a182fd058a08c`

## Scope

Neural-v2 is a separate CPU-target extension. It does not alter Phase 2A, the
frozen B4-v1 TCN, or the accepted deterministic benchmark. It evaluates exactly
four fixed neural baselines and two feature sets:

- DLinear, LSTM, full-receptive-field causal TCN-v2, and compact PatchTST;
- `F0_LOCAL`: target-machine CPU;
- `F1_THROUGHPUT`: target-machine CPU plus same-machine total throughput,
  defined as bond0 TX plus bond0 RX.

LOMO CPU, memory, disk, RTT, jitter, packet telemetry, and per-core CPU are
excluded. This narrowed feature scope is evidence-informed by the already
frozen corrected deterministic benchmark and is not an untouched confirmatory
hypothesis.

## Target and real forecast leads

The target is machine-level CPU utilization for machines 01-07. Every model
maps a contiguous history `[batch, L, channels]` to exactly eight CPU outputs:

`[CPU(t+1), CPU(t+2), CPU(t+4), CPU(t+8), CPU(t+16), CPU(t+32), CPU(t+64), CPU(t+128)]`

The corresponding approximate real horizons are 0.705, 1.410, 2.819, 5.638,
11.276, 22.552, 45.104, and 90.208 minutes. These are eight genuinely evaluated
future targets, not a dense or fake output-width interpretation.

## Common support and splits

For each machine, outer fold, and context length, the eligible origins require:

- finite CPU and same-machine throughput across the full history;
- all eight finite CPU targets;
- a complete history;
- no history or target crossing a canonical temporal segment.

This F1-finite support is used unchanged for both F0 and F1. Their inner-train,
inner-validation, final outer-train, and outer-test sample IDs and hashes must
therefore be identical. F0 never receives a larger feature-value support.
Eligibility is deliberately fixed using the maximum 128-sample F1 history for
all three candidate L values. A shorter model receives the final L contiguous
observations from that support. This stricter rule keeps sample IDs identical
even when F0 and F1 select different context lengths.

The accepted deterministic benchmark's five expanding chronological outer-fold
boundaries are reused read-only. Its longest-lead target-time purge is retained.
Within the F1-supported outer training set, the chronologically latest 15% is
inner validation; inner training is purged so every lead-128 target precedes the
first validation origin. There is no shuffle of chronology and no outer-test
input to selection, scaling, fitting, or epoch choice.

## Context and seed selection

Candidate context lengths are `L={32,64,128}` and seeds are `[0,1,2]`. For each
model, feature set, machine, and outer fold, all three seeds are trained for all
three lengths. The selection score is mean inner-validation MAE across the
three seeds and eight leads. The lowest score wins; an exact tie selects the
smaller L. This yields one L shared by all seeds in the final cell.

The best epoch is retained separately for each seed at the selected L. Each
final model is initialized from scratch, fit on full legal outer-training
support for that fixed epoch count, and evaluated on outer test once. Outer test
is never used for early stopping.

## Fixed model definitions

### DLinear

Multivariate input, CPU-only eight-lead output, moving-average kernel 25, and
trend/residual linear projections. F0 has one channel and F1 has two.

### LSTM

Unidirectional two-layer LSTM, hidden size 64, inter-layer dropout 0.1, final
recurrent representation, and an eight-output linear head. There is no
attention, bidirectionality, or architecture tuning.

### TCN-v2

Six causal residual blocks, widths `[32,32,32,32,32,32]`, kernel 3, dilations
`[1,2,4,8,16,32]`, two causal convolutions per block, and dropout 0.1. Its exact
effective receptive field is:

`1 + 2 * (3 - 1) * (1 + 2 + 4 + 8 + 16 + 32) = 253`

Thus RF 253 covers every candidate history, including L=128. The output head
uses only the final causal representation. This does not modify B4-v1.

### PatchTST

Patch length 8, stride 4, d_model 64, four heads, two encoder layers, feed-forward
dimension 128, dropout 0.1, and an eight-output head. Tokenization and transformer
encoding are channel-independent with shared weights. Fixed late mixing occurs
only in the output head after one representation is obtained per channel. All
patches contain observed history at or before the forecast origin.

## Training

DLinear, LSTM, and TCN-v2 use Adam, learning rate 0.001, batch size 256,
maximum 50 epochs, patience 7, MSE loss, and gradient clipping at 1.0. PatchTST
uses AdamW prospectively with learning rate 0.001 and weight decay 0.0001; all
other defaults are identical. These values are not tuned.

Input standardization is fit only on the applicable training support. Targets
are not standardized and remain in physical CPU-utilization scale. Metrics are
MAE, RMSE, and R-squared per seed and lead. Exact F1-versus-F0 gains require
identical stored sample hashes and include MAE gain, RMSE gain, and R-squared
delta, plus seed mean, standard deviation, minimum, maximum, and positive-seed
count.

## Execution scale

For each of 280 model-feature-machine-fold cells, context selection requires
three lengths times three seeds: 2,520 inner fits. The selected length then has
three final seed refits per cell: 840 final fits. A complete run therefore
requires exactly 3,360 fits and produces 840 final run records and 6,720
seed-level lead-metric rows.

## Resumability and retention

Each fit key contains protocol/config hash, model, feature, machine, fold, seed,
L, and stage. Selection progress is written atomically after each inner fit.
Final completion records are written only after predictions and metrics have
been flushed and hashed. Restart logic may skip a run only when the completion
record, config hash, sample-set hash, and prediction/metric hashes all validate;
otherwise it reruns that fit.

Only the best inner state for each active seed/L is needed until selection.
After selection, non-selected model states can be discarded while their compact
scores and epoch records remain. Final model weights are optional; predictions,
metrics, completion records, selected L, per-seed epoch counts, sample hashes,
and configuration identity are mandatory. Every-epoch checkpoints are not
retained.

The timing pilot is explicitly non-scientific: machine01, fold 1, seed 0, L=64,
both feature sets, full legal inner support, and exactly five epochs per model.
Pilot losses and predictions must not enter scientific selection or claims.
