# Phase 3B Plain-LSTM S1/S2/M1 Protocol Draft

## Scope and immutable inputs

This protocol implements the Phase 3A four-resource factorial as a plain-LSTM
baseline. It does not authorize scientific execution. The canonical panel must
retain SHA-256 `c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`.
The prospective decision record SHA-256 is
`2bfb2610bd8e869dc038bccd6b18656cd2c968b9d548c758487cae500cbf5677`.

## Targets and normalization

The fixed order is CPU, throughput, memory, disk-write. The canonical columns
are `machineXX__cpu_utilization`, `machineXX__throughput_total`,
`machineXX__memory_used`, and `machineXX__disk_write`. CPU and memory use the
identity transform; throughput and disk-write use `log1p`. After transforming,
each resource is scaled by its training-partition median and IQR. Inner scalers
use inner train only; final scalers are refit on legal outer train. A
non-positive IQR is fatal.

Throughput and disk-write predictions are inverted by undoing robust scaling,
then applying `expm1`, then deterministically projecting to `max(0, y)`. The
pre-projection negative rate and unclipped minimum are retained. CPU and memory
are inverse-scaled without projection.

## Support, folds, and purging

All formulations, targets, and context candidates use one support universe
constructed with `Lmax=128`. Histories and all four resources at all eight
future leads `[1,2,4,8,16,32,64,128]` must be finite and contained in the
origin's canonical segment. Shorter contexts receive no extra origins.

The five accepted chronological outer boundaries are reused with expanding
training and non-overlapping tests. Lead-128 target timestamps in training must
precede the first test origin. Within filtered outer train, the latest 15% is
inner validation and earlier observations are lead-128 target-time purged.
Support IDs and hashes are persisted. Outer-test values are unavailable to
preprocessing, context selection, epoch selection, and fitting.

## Architectures and loss

Every encoder is a two-layer, unidirectional LSTM with hidden size 64, dropout
0.1, and the last recurrent output as representation.

- S1 consumes `[N,L,1]` for one resource and uses a linear `64 -> 8` head.
- S2 consumes `[N,L,4]` in fixed resource order and uses a linear `64 -> 8`
  head for one independently trained target.
- M1 consumes `[N,L,4]`, has one shared encoder, and exactly four independent
  linear `64 -> 8` heads stacked as `[N,4,8]`.

S1/S2 minimize mean transformed/scaled MSE over batch and horizons. M1 computes
one such MSE per resource and minimizes their arithmetic mean. It logs each
resource MSE and its share of the four-resource MSE sum. There is no learned,
dynamic, uncertainty, or hand-tuned weighting.

## Training, selection, and refit

Adam uses learning rate 0.001, batch size 256, maximum 50 epochs, patience 7,
gradient clipping 1.0, seeds `[0,1,2]`, and contexts `[32,64,128]`. S1 and S2
choose one context per resource/machine/fold by mean transformed/scaled
validation MAE over eight horizons and three seeds. M1 chooses one context per
machine/fold by an equal mean over four resources, eight horizons, and three
seeds. Smaller context wins ties.

Each seed retains its own best inner epoch at the selected context. Final models
start from scratch, refit scaling on full outer train, and train for that fixed
epoch count without validation or test callbacks.

## Metrics and aggregation

Native MAE, RMSE, R-squared, NMAE (`MAE / training native IQR`), and persistence
skill are reported per resource and lead. Native MAEs are never averaged across
resources. For stochastic macro reporting, metrics are computed per
machine-fold-seed-resource-lead, seeds are averaged within each cell, and
machine-fold cells receive equal weight. Relative gains are calculated from
the formulation macro MAEs. Pooled metrics, cell-relative improvements,
positive-machine/fold fractions, and seed robustness remain secondary.

The comparisons are S2 versus S1 (cross-resource input), M1 versus S2 (shared
representation, primary multi-task statistic), and M1 versus S1 (total-system
value), each computed separately by resource.

## Capacity, workload, and resumability

S1 has 50,952 parameters per model and 203,808 across four independent models.
S2 has 51,720 per model and 206,880 across four. M1 has 51,200 shared encoder
parameters plus 2,080 across four heads, totaling 53,280.

The planned workload is 2,835 inner fits, 945 final fits, 3,780 total fits, and
10,080 final resource-lead metric rows. Stable run identity includes
formulation, target resource where applicable, machine, fold, context, seed,
inner/final phase, config hash, and support hash. Atomic completion records may
skip work only when identity, support, config, and expected artifact hashes all
validate. Permanent per-epoch checkpoints are not retained.

## Preflight-only execution boundary

The sole pilot is machine01/fold1/seed0/L64, nine models, exactly five epochs.
It does not select context, refit outer train, construct outer-test windows,
generate outer predictions, or produce scientific evidence. No attention,
adapters, selective fusion, private branches, gates, dynamic weighting,
machine embeddings, MoE, Transformer, PatchTST, TCN-v2, or novel architecture
is included.
