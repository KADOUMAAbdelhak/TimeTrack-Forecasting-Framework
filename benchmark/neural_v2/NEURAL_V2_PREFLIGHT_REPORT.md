# Neural V2 Design and Preflight Report

Date: 2026-09-23 (Europe/Helsinki)

Status: **IMPLEMENTED AND PREFLIGHTED; FULL SCIENTIFIC EXECUTION NOT STARTED**

## Prospective identity

- Decision record: `benchmark/neural_v2/NEURAL_V2_DECISION.md`
- Decision SHA-256:
  `9cec1dc25dc20dd1bf20ac3d7d495f731d41106935a66726d79a182fd058a08c`
- Configuration SHA-256:
  `39f511e1a09f5e466aab89cee0164be29b04ec0745d1ff5e4422b5556011272e`
- Accepted deterministic checkpoint:
  `bdc7c9243cb33cbb3fadee7b911810a164d8da43`
- Accepted deterministic tag:
  `phase2b1-corrected-deterministic-freeze-v1`

The decision was created and hashed before neural implementation was executed.
No scientific neural result existed or was inspected. The only neural fitting
performed was the explicitly authorized non-scientific five-epoch timing pilot.

## Files created

- `NEURAL_V2_DECISION.md`
- `PROTOCOL.md`
- `NEURAL_V2_PREFLIGHT_REPORT.md`
- `configs/neural_v2.json`
- `run_neural_v2.py`
- `src/data.py`, `src/splits.py`, `src/training.py`, `src/selection.py`
- `src/metrics.py`, `src/validation.py`
- `src/models/dlinear.py`, `src/models/lstm.py`, `src/models/tcn.py`
- `src/models/patchtst.py`
- five test/support modules under `tests/`
- `pilot/run_pilot.py`, `pilot/project_runtime.py`
- `pilot/timing_results.json`, `pilot/runtime_projection.json`
- `outputs/README.md`, which confirms that no scientific output exists

All additions are under `benchmark/neural_v2/`. No frozen Phase 2A or
deterministic implementation file was edited.

## Scientific design

Target: machine-level CPU utilization for machines 01-07.

Real future leads: `[1,2,4,8,16,32,64,128]`, approximately `[0.705, 1.410,
2.819, 5.638, 11.276, 22.552, 45.104, 90.208]` minutes. Every network produces
exactly eight CPU forecasts for these real future targets.

Feature sets are exactly:

- `F0_LOCAL`: target-machine CPU only;
- `F1_THROUGHPUT`: target-machine CPU plus validated same-machine total
  throughput (`bond0 TX + bond0 RX`).

LOMO CPU, memory, disk, RTT, jitter, packet telemetry, and per-core CPU are
absent. The narrowing is prospectively evidence-informed by the frozen
corrected deterministic result; it is not described as untouched confirmation.

### Common support

Eligibility requires finite CPU and throughput history, all eight finite CPU
targets, complete history, and no history/target segment crossing. A single
F1-finite maximum-history support (128 samples) is used for F0, F1, and every
candidate L. Shorter models receive the final L observations from that support.
This deliberately strict rule guarantees identical sample IDs and hashes even
if F0 and F1 independently select different L values.

The five accepted expanding outer boundaries and lead-128 target-time purge are
reused read-only. Inner validation is the chronologically latest 15% of legal
outer training, with a separate lead-128 purge. No outer-test value enters
context selection, epoch selection, scaling, fitting, or normalization.

### Context and epoch selection

For each model-feature-machine-fold cell, L is selected from `{32,64,128}` by
mean inner-validation MAE over three seeds and eight leads. Exact ties select
the smaller L. One L is shared by all three final seeds. Each seed retains its
own best inner epoch at that L. Final training starts from scratch on full legal
outer training for that fixed epoch count and evaluates outer test once.

## Fixed model definitions

| Model | Definition |
|---|---|
| DLinear | Multivariate input, moving-average kernel 25, trend/residual decomposition, eight CPU outputs |
| LSTM | Hidden size 64, two unidirectional layers, inter-layer dropout 0.1, final recurrent representation, eight-output head |
| TCN-v2 | Six width-32 causal residual blocks, kernel 3, dilations 1/2/4/8/16/32, two convolutions per block, dropout 0.1 |
| PatchTST | Patch 8, stride 4, d_model 64, four heads, two layers, FFN 128, dropout 0.1, channel-independent shared encoding with fixed late head mixing |

DLinear, LSTM, and TCN-v2 use Adam. PatchTST uses the prospectively frozen
AdamW choice with weight decay 0.0001. All use learning rate 0.001, batch size
256, maximum 50 epochs, patience 7, MSE, and gradient clipping 1.0. Input
standardization is fit on training only. Targets are not standardized.

### Exact TCN receptive field

`RF = 1 + 2 * (3 - 1) * (1 + 2 + 4 + 8 + 16 + 32) = 253`

Therefore RF 253 is greater than the maximum selected history 128. Analytical
and perturbation-based causality tests pass. The frozen B4-v1 RF=13 source was
not modified.

## Validation tests

Result: **28 passed, 0 failed**.

Coverage includes exact leads and feature scope, F0/F1 parity, parity across
candidate lengths, segment safety, both purges, train-only transformations,
all four `[N,8]` output shapes, DLinear channel handling, unidirectional LSTM,
TCN RF=253 and causality, PatchTST patch construction/history-only input,
deterministic seed behavior, seed-mean selection and tie-break, per-seed epoch
records, fixed-epoch final retraining, absence of outer-test control, stable
unique run IDs, output schemas, atomic completion records, and exact fit scale.

## Environment and device

- Device: CPU
- OS: macOS 26.6.2, Darwin arm64
- Logical CPUs: 8
- Python: 3.13.2
- PyTorch: 2.14.0
- PyTorch threads: 4
- CUDA available: no
- MPS available: no

The earlier temporary deterministic environment no longer existed. An isolated
temporary environment was recreated at
`/private/tmp/timetrack-neural-v2-venv` using the exact committed package
versions. It is outside the repository and is not staged.

## Five-epoch runtime pilot

Pilot scope: machine01, outer fold 1, seed 0, L=64, full legal inner support,
exactly five epochs, no early stop, CPU. Training samples: 7,864; validation
samples: 1,392.

- Train support SHA-256:
  `6c0c68a93140d4abf1104aee5c956f1800e28c291c6e21676f3d0e30dcc853b4`
- Validation support SHA-256:
  `36989163d3890296afd73c9089a9e4fb29a706bac7e3bd7386047a5762c26bba`

F0 and F1 hashes were identical. No outer-test window was built or evaluated.

| Model | Feature | Parameters | s/epoch | Train s | Validation s | Train samples/s | Peak RSS MiB | Mean process CPU % |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| DLinear | F0 | 1,042 | 0.018 | 0.086 | 0.002 | 454,740 | 622.3 | 104.0 |
| DLinear | F1 | 1,043 | 0.022 | 0.105 | 0.003 | 373,253 | 627.0 | 131.4 |
| LSTM | F0 | 50,952 | 1.410 | 6.693 | 0.359 | 5,875 | 793.6 | 147.1 |
| LSTM | F1 | 51,208 | 1.417 | 6.739 | 0.345 | 5,835 | 793.8 | 144.5 |
| TCN-v2 | F0 | 34,600 | 5.702 | 26.115 | 2.393 | 1,506 | 830.5 | 139.8 |
| TCN-v2 | F1 | 34,728 | 5.805 | 26.621 | 2.405 | 1,477 | 684.6 | 139.4 |
| PatchTST | F0 | 69,000 | 0.950 | 4.564 | 0.189 | 8,616 | 735.4 | 133.9 |
| PatchTST | F1 | 69,512 | 1.718 | 8.216 | 0.376 | 4,786 | 811.1 | 146.8 |

Process CPU percentages can exceed 100% because they measure aggregate use
across logical cores. Pilot losses and predictions are intentionally not
reported or interpreted.

## Full-run scale and runtime projection

Exact scale:

- Model-feature-machine-fold selection cells: 280
- Inner fits: `280 * 3 L * 3 seeds = 2,520`
- Final refits: `280 * 3 seeds = 840`
- Total fits: 3,360
- Final seed-level lead metric rows: `840 * 8 = 6,720`

Projection uses measured train/validation seconds per sample, exact support
sizes across all 35 machine-fold cells, linear history-length scaling for
DLinear/LSTM/TCN, and patch-count scaling for PatchTST.

| Scenario | Mean epochs | Selected-L assumption | Projected hours | Projected days |
|---|---:|---:|---:|---:|
| Optimistic | 10 | 32 | 27.3 | 1.14 |
| Central | 25 | 64 | 77.7 | 3.24 |
| Conservative | 50 | 128 | 192.9 | 8.04 |

Central model totals are approximately: DLinear 0.2 h, LSTM 12.9 h,
PatchTST 12.3 h, and TCN-v2 52.2 h. Realized cost remains uncertain because
selected L and early-stopping epochs are scientific outputs, and hardware
contention and nonlinear sequence cost may change throughput.

## Resumability and disk estimate

The guarded driver defaults to plan-only and requires two explicit execution
flags. It was not run scientifically. Its resumability design uses:

- atomic model/feature/machine/fold/L/seed inner completion records;
- atomic selection-progress and selected-L records;
- per-seed best-epoch retention;
- atomic prediction, metric, and final completion writes;
- config, decision, sample-set, prediction, and metric hashes;
- skip-on-restart only after all identities and hashes validate;
- rerun of an interrupted current fit instead of trusting partial state;
- no permanent every-epoch checkpoints.

At L=64, the expected 840 final runs contain about 12.3 million prediction
rows. Using the accepted deterministic parquet density gives about 147 MiB;
150-300 MiB is budgeted for predictions and schema variation. Compact metrics,
selection, completion, and runtime records should remain below 20 MiB. Optional
final raw model states are about 132 MiB before serialization overhead. A
practical total budget is 0.2-0.35 GiB without final weights or 0.35-0.55 GiB
with them, plus less than 0.1 GiB transient checkpoint headroom.

## Implementation risks and readiness

- TCN-v2 dominates projected CPU time and is the principal operational risk.
- PatchTST F1 cost is materially higher than F0 because each channel is encoded
  independently before late mixing.
- The projection has only one machine/fold/seed timing point; epoch count and L
  remain unknown until authorized inner selection.
- The temporary environment is reproducible from the committed snapshot but
  should be replaced by a project lockfile or durable environment before a
  multi-day run.
- Parallel workers might reduce wall time, but thread contention and peak memory
  must be piloted before changing the serial projection.

Technical readiness: **YES**. Protocol guards, common support, models,
selection, fixed-epoch refit, schemas, atomic resumability, tests, and a guarded
driver are implemented.

Execution recommendation: **do not launch all four models serially on this CPU
without a dedicated multi-day window and monitoring**. All four remain
scientifically implementable, but a faster CPU host or a separately authorized
small parallelism pilot is recommended. If this host must be used, resumable
staged execution is preferable and TCN-v2 should be scheduled as the long pole;
models should not be dropped after observing results without a new prospective
decision.

## Relationship to the Multi-Resource Study

Neural-v2 remains a CPU-target benchmark.

It is NOT intended as the final paper scope.

Its purpose is to establish strong temporal baselines before the next phase.

The next major research phase, if neural-v2 completes successfully, will
prospectively test TRUE MULTI-TARGET forecasting. A candidate target vector per
machine would include CPU, throughput, used memory, and used disk across real
future leads.

The future research question will be:

Does shared multi-resource temporal representation learning improve
multi-horizon cloud telemetry forecasting relative to independently trained
single-resource forecasters?

That phase is not implemented here.

## Final confirmation

No scientific neural outer run was executed. No neural accuracy result was
interpreted. No deterministic result, raw file, canonical file, Phase 2A
protocol, frozen B4-v1 source, or corrected Phase 2B-1 artifact was modified.
No multi-target model was created. No commit or push was performed.
