# Phase 1C Rolling-Origin Robustness Protocol

Status: **FROZEN before Phase 1C model execution**  
Freeze date: 2026-09-21

This phase tests stability across multiple chronological periods in the same
TimeTrack dataset. It is not an independent replication dataset and does not
redefine Phase 1B evidence or classifications.

## 1. Fixed hypotheses and candidates

Primary target: machine-level CPU utilization for `machine01` through
`machine07`. There is no cluster-average target.

The candidate set is exactly:

1. same-machine bidirectional throughput total;
2. same-machine used memory;
3. same-machine used disk;
4. global mean RTT (`global__rtt_average`);
5. global jitter (`global__jitter`);
6. leave-one-machine-out CPU mean;
7. leave-one-machine-out CPU median.

No candidate may be added or removed after fold results are observed.

H1: same-machine throughput adds predictive information for future CPU beyond
CPU own history.

H2: leave-one-machine-out CPU context adds predictive information for future
CPU beyond target-machine CPU history.

Memory, used disk, RTT, and jitter are fixed negative/comparison contexts.

## 2. Leads, features, and model

The measured median interval is 42.285164 seconds. Leads are:

- 1 = 42.285164 s (0.704753 min)
- 2 = 84.570328 s (1.409505 min)
- 4 = 169.140656 s (2.819011 min)
- 8 = 338.281312 s (5.638022 min)
- 16 = 676.562624 s (11.276044 min)
- 32 = 1,353.125248 s (22.552087 min)
- 64 = 2,706.250496 s (45.104175 min)
- 128 = 5,412.500992 s (90.208350 min)

Baseline features are target CPU at lags `[0,1,2,4,8,16,32]`. The augmented
model adds exactly one candidate at the same seven lags. Baseline and augmented
models use identical candidate-specific rows.

The model is `Ridge(alpha=1.0)` with intercept and no tuning. X is standardized
with a `StandardScaler` fit on that fold's training rows only. The CPU target
is not scaled.

## 3. Eligible origins and segment safety

For each target and lead, an origin is eligible only when every target-history
value and `y[t+h]` exists and all history/target indices share the origin's
canonical segment. Candidate histories must independently satisfy the same
segment rule. Models are global chronological models, never segment-specific.

## 4. Deterministic rolling folds

Sort all target/lead eligible origins globally. With `N` origins, use zero-based
half-open test slices:

- fold 1: `[floor(0.50N), floor(0.60N))`;
- fold 2: `[floor(0.60N), floor(0.70N))`;
- fold 3: `[floor(0.70N), floor(0.80N))`;
- fold 4: `[floor(0.80N), floor(0.90N))`;
- fold 5: `[floor(0.90N), N)`.

The provisional training origins are every eligible origin before that fold's
test start position. Training expands, and prior test blocks become available
to later folds.

For each fold, retain a provisional training origin only when its target
timestamp is strictly earlier than the first test origin timestamp:

`train_target_time < min(test_origin_time)`.

This lead-aware purge is the only embargo. Test blocks are non-overlapping.

## 5. Metrics and matched rows

For each target, lead, candidate, and fold, create the complete finite-data
intersection first. Use those exact row IDs for baseline and augmentation
training/test sets. Record deterministic hashes.

Report MAE, RMSE, R², their augmentation improvements/delta, and pointwise:

`delta_abs_error = abs(y - baseline_prediction) - abs(y - augmented_prediction)`.

Positive values mean augmentation reduced absolute error. Segment IDs remain
attached to compact paired-error diagnostics.

## 6. Frozen Phase 1C robustness labels

These labels are separate from Phase 1B.

`ROBUST_POSITIVE` requires all:

- exactly five valid folds;
- positive MAE gain in at least four folds;
- median fold MAE gain >= 1%;
- sample-weighted aggregate MAE gain >= 1%;
- median RMSE gain > 0;
- median R² delta >= 0.

`CONSISTENT_SMALL_POSITIVE` requires:

- exactly five valid folds;
- positive MAE gain in at least four folds;
- median MAE gain > 0;
- weighted aggregate MAE gain > 0;
- at least one of median MAE gain or weighted aggregate MAE gain is below 1%,
  so the >=1% robust magnitude requirement fails.

`NEGATIVE` applies when at least four folds have nonpositive MAE gain, or both
median and weighted aggregate MAE gain are <=0.

`MIXED` applies when positive-fold count is two or three, median and weighted
gain disagree in sign, or MAE consistency is positive but RMSE/R² evidence
prevents the two positive labels. Label precedence is:
ROBUST_POSITIVE, CONSISTENT_SMALL_POSITIVE, NEGATIVE, then MIXED.

Fewer than five valid folds is always `INSUFFICIENT_FOLDS`, with a reason. The
five-fold thresholds are never silently weakened.

## 7. Frozen decision gate

Throughput support exists when at least two machines are `ROBUST_POSITIVE` for
same-machine throughput at the same lead.

Common-system support exists when at least two machines are
`ROBUST_POSITIVE` for either leave-one-machine-out CPU mean or median at the
same lead.

The final gate is:

- throughput only: `PROCEED_WITH_CONTEXT_AWARE_CPU_FORECASTING`;
- common-system only: `PROCEED_WITH_MULTI_MACHINE_CPU_FORECASTING`;
- both: `PROCEED_WITH_BOTH`;
- neither: `CROSS_SIGNAL_EVIDENCE_TOO_WEAK`.

No architecture name or final forecast horizon is selected in this phase.
