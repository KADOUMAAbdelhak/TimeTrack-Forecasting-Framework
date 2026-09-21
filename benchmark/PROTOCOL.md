# Phase 2A CPU Forecasting Benchmark Protocol

Status: **FROZEN before full benchmark execution**  
Freeze date: 2026-09-21

Phase 2A establishes baseline value from local history, context, and model
family before any proposed architecture is designed. It uses only the
validated canonical panel and never imports the archived study.

## Scientific task

For each machine independently, forecast the real future CPU vector:

`[CPU[t+1], CPU[t+2], CPU[t+4], CPU[t+8], CPU[t+16], CPU[t+32], CPU[t+64], CPU[t+128]]`.

The leads correspond to approximately 0.705, 1.410, 2.819, 5.638, 11.276,
22.552, 45.104, and 90.208 minutes at the measured 42.285164-second median
interval. Output width is not interpreted as a horizon.

Targets are machine01 through machine07 CPU utilization and are always retained
as separate evaluation entities.

## Canonical inputs and six frozen feature sets

The sole data input is
`discovery/02_dependency_analysis/outputs/canonical_panel.parquet`.
Throughput remains validated `bond0 TX + bond0 RX`. LOMO context excludes the
target machine by construction.

- `F0_LOCAL`: target CPU.
- `F1_THROUGHPUT`: target CPU + same-machine throughput total.
- `F2_LOMO_MEAN`: target CPU + other-six CPU mean.
- `F3_LOMO_MEDIAN`: target CPU + other-six CPU median.
- `F4_THROUGHPUT_LOMO_MEAN`: target CPU + throughput + other-six CPU mean.
- `F5_THROUGHPUT_LOMO_MEDIAN`: target CPU + throughput + other-six CPU median.

Memory, disk, RTT, jitter, packet events, and per-core CPU are excluded from
the primary benchmark. The feature set cannot be expanded after results.

## History windows and eligibility

Candidate context lengths are `L in {32,64,128}`. Every model receives the same
contiguous `L x channels` information; tabular models flatten it and temporal
models retain sequence shape.

The common outer-fold origin universe uses the strictest target-CPU history
(`L=128`) and all eight future CPU targets. Every target-history index and all
targets through lead 128 must be finite and share the origin's canonical
segment. There is no interpolation, nearest matching, or gap crossing.

After outer/inner boundaries are fixed, each feature set applies its own
finite-history mask. This avoids discarding valid F0 CPU samples merely because
an excluded context channel is missing. Feature-value comparisons must use a
candidate-matched F0 reference on the exact context feature's train/test rows;
the standalone F0 result may additionally use all F0-valid rows. This
matched-reference rule prevents context gains from being attributed to
different missing-data samples.

The frozen joint structural origin counts range from 26,729 to 29,986 by
machine. Phase 1C per-lead counts ranged from 39,165 to 40,481. Requiring a
contiguous 128-sample CPU history and all eight targets therefore reduces
eligible counts by approximately 24.0%-33.5%, depending on machine and the
per-lead comparison. Exact values are in
`outputs/joint_eligibility_comparison.csv`.

## Outer rolling evaluation

For each machine, sort jointly eligible origins globally. With `N` origins,
five half-open test blocks are:

- fold 1: `[floor(.50N), floor(.60N))`
- fold 2: `[floor(.60N), floor(.70N))`
- fold 3: `[floor(.70N), floor(.80N))`
- fold 4: `[floor(.80N), floor(.90N))`
- fold 5: `[floor(.90N), N)`

Training expands from the beginning. For each fold, retain a provisional
training origin only when:

`timestamp(t+128) < first outer-test origin timestamp`.

Test blocks do not overlap. Prior test periods may enter later training
history. Models are not trained separately by canonical segment.

`benchmark/src/splits.py` independently reconstructs the Phase 1C per-lead
fold algorithm and must match all 280 Phase 1C boundary timestamp definitions
when given equivalent sparse-history/per-lead eligibility.

## Inner validation and selection

Within each purged outer-training set, the chronologically latest 15% of
origins is provisional inner validation. Let its first origin be `v`. Inner
training retains only earlier origins satisfying:

`timestamp(t+128) < v`.

There is no shuffle. Outer test data cannot choose configuration, context
length, epoch count, or candidate.

For each model family, feature set, machine, and outer fold:

- Ridge jointly selects `L` and alpha by lowest mean eight-lead inner MAE.
  Ties: shorter `L`, then smaller alpha.
- LightGBM jointly selects `L` and its frozen grid by lowest mean eight-lead
  inner MAE. Ties: shorter `L`, smaller `num_leaves`, lower learning rate,
  then fewer estimators.
- DLinear and TCN select `L` by mean inner MAE across seeds 0, 1, and 2. Ties:
  shorter `L`. Each selected configuration is then reported at all three
  seeds.
- Persistence has no selected configuration and repeats the last observed
  target CPU for all leads.

The capped smoke run uses seed 0 and reduced epochs/tree counts solely to
verify execution. It is not a benchmark result or final neural selection.

## Frozen model families

### B0 Persistence

Predict `CPU[t]` at every lead. No fitting.

### B1 Ridge

Direct multi-output Ridge on flattened windows. X standardization is fit on
training only; targets stay in CPU units.

Alpha grid: `[0.01,0.1,1.0,10.0,100.0]`.

### B2 LightGBM

Eight direct lead-specific `LGBMRegressor` models on the same flattened
window. Grid:

- `num_leaves`: `[15,31]`
- `learning_rate`: `[0.03,0.05]`
- `n_estimators`: `[200,400]`

Frozen settings: `objective="regression_l1"`, `max_depth=-1`,
`min_child_samples=20`, `subsample=1.0`, `colsample_bytree=1.0`,
`reg_alpha=0`, `reg_lambda=0`, `random_state=0`, `n_jobs=1`,
`deterministic=True`, `force_col_wise=True`, and `verbosity=-1`.

### B3 DLinear

Input `[batch,L,channels]`, output `[batch,8]`. A moving-average decomposition
(kernel 25) separates trend and residual components. Frozen linear temporal
maps project each component from `L` to eight leads, and a learned channel
projection produces target CPU. It is genuinely multivariate for F1-F5.

### B4 causal TCN

Input `[batch,L,channels]`, output `[batch,8]`. Two causal residual convolution
blocks use channels `[32,32]`, kernel 3, dropout 0.1, and a final linear
eight-lead head. Left padding only guarantees no later history position enters
an earlier convolutional representation.

No Transformer, recurrent model, or proposed architecture is included.

## Neural training defaults

- seeds: `[0,1,2]`
- optimizer: Adam
- learning rate: 0.001
- batch size: 256
- maximum epochs: 50
- early-stopping patience: 7
- loss: mean squared error
- gradient clipping norm: 1.0
- target scaling: none
- feature scaling: per-channel mean/std fitted on training only
- initialization: PyTorch defaults after setting Python, NumPy, and PyTorch
  seed; deterministic algorithms requested where supported
- device: CUDA, then Apple MPS, otherwise CPU

Early stopping observes inner validation only. Outer test cannot control
training duration.

## Metrics and aggregation

For every machine, fold, lead, model, feature set, and neural seed where
applicable, retain MAE, RMSE, and R². Relative MAE change is:

`100 * (reference_MAE - model_MAE) / reference_MAE`.

References are persistence and the same model's F0_LOCAL result. Positive means
the evaluated model/feature set is better. Machine-level results are always
retained.

Predeclared summaries are macro mean across seven machines, median across
machines, worst-machine MAE, and fold-level macro MAE. Neural reporting retains
seed mean, standard deviation, and min/max; seeds are not independent datasets.

## Comparison rules

Feature value compares F1-F5 against F0 within the same model. Model value
compares model families using the same feature set and origin rows. Gains are
never attributed to architecture when information differs.

## Frozen benchmark questions

1. BQ1: Does same-machine throughput improve over local CPU history?
2. BQ2: Does LOMO CPU context improve forecasting?
3. BQ3: Does throughput plus LOMO outperform either alone?
4. BQ4: Is LOMO mean or median more useful?
5. BQ5: At which real leads does context provide the largest gain?
6. BQ6: Is context beneficial across machines and rolling folds?
7. BQ7: Do nonlinear models extract more cross-signal value than Ridge?
8. BQ8: Do temporal neural models outperform strong tree/linear baselines?
9. BQ9: Does model ranking change by lead?
10. BQ10: Are gains concentrated in one machine, fold, or neural seed?

## Reproducibility and expected scale

A run ID hashes model, feature set, machine, fold, selected configuration,
context length, and seed. The complete outer factorial contains:

- 210 Persistence records
- 210 Ridge records
- 210 LightGBM records
- 630 DLinear seed records
- 630 TCN seed records

Total: **1,890 outer run records** and **15,120 lead-level metric rows** before
prediction-row storage. Persistence is deliberately repeated across feature
sets as an invariant reference.

Prepared outputs are `run_registry.csv`, `metrics.parquet`,
`selected_configs.csv`, and partitioned files under `predictions/`.
