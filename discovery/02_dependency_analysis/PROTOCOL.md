# Phase 1B Canonical Panel and Dependency-Screening Protocol

Status: **FROZEN before dependency experiments**  
Freeze date: 2026-09-21

This protocol governs the later lagged cross-metric and cross-machine
dependency screen. The panel has been built and validated, but no association
ranking, Ridge fit, dependency classification, or forecasting experiment has
been run.

**Pre-experiment amendment, 2026-09-21:** The original origin-only
60%/20%/20% assignment was replaced before any dependency experiment because a
late origin in one split can have `y[t+h]` inside the next split's origin-time
region. Section 9 now uses lead-aware target-time purging. No lead, lag,
candidate family, model setting, signal, threshold, throughput definition, or
target definition changed.

## 1. Inputs, alignment, and immutable-data rule

The only scientific inputs are the six active files under `data/raw/`:

- `compute_dataset.csv`
- `detailed_cpu_cores_dataset.csv`
- `disk_dataset.csv`
- `network_dataset.csv`
- `packet-loss-dataset.csv`
- `throughputs_dataset.csv`

Phase 1A tables under `discovery/01_data_audit/outputs/` supply metadata and
redundancy evidence. Nothing under `old_fgcs_rejected/` is imported. Raw files
are read-only and are verified against their Phase 1A SHA-256 values before and
after panel construction.

Timestamps are parsed exactly and the canonical time axis is the sorted set
intersection of timestamps in all six files. No nearest-time matching,
resampling, imputation, interpolation, or value cleaning is performed.
Per-core CPU values are excluded; the per-core file contributes only to the
all-file timestamp intersection.

The frozen panel has 41,356 rows and 116 columns: `timestamp`,
`interval_seconds`, `segment_id`, and 113 registered signals. Its range is
2024-06-24 13:37:06.164306 through 2024-07-19 16:27:05.246403.

## 2. Temporal segments and admissible windows

The measured canonical median interval is **42.285164 seconds**. A new segment
starts when the current retained timestamp minus the previous retained
timestamp is strictly greater than:

`2 * 42.285164 = 84.570328 seconds`.

This yields nine segments. The six timestamps absent from the network file
remain absent from the exact intersection and create six of the retained
short-gap boundaries. They are not interpolated.

Every later origin must satisfy all of the following:

1. every required historical feature index exists in the origin's segment;
2. the future target index exists in that same segment;
3. all values required by that particular comparison are finite/observed.

An origin, feature window, or target window may never cross a segment
boundary. Segment IDs must remain attached to results. The exact segment table
is `outputs/canonical_temporal_segments.csv`.

## 3. Canonical signals and target roles

For each machine, the panel retains direct machine-level CPU utilization, used
memory, used disk, disk-read activity/rate, and disk-write activity/rate.
Primary later regression targets are:

- CPU utilization;
- used memory level and its origin-to-future change;
- used disk level and its origin-to-future change;
- bidirectional machine throughput.

Disk read and write signals are retained as separate candidate predictors, not
summed and not used as primary targets in this screen. Directional network TX
and RX signals are retained as components, while bidirectional throughput is
the primary throughput target/predictor. The five global network signals are
minimum, maximum, average, and mean-deviation RTT plus jitter.

The signal-level provenance, transformations, quality flags, and analysis role
are frozen in `outputs/canonical_signal_registry.csv`.

## 4. Machine throughput decision

Raw names explicitly distinguish `transmitted_throughput` and
`received_throughput`. For each host and direction, `bond0` was accepted as the
smallest nonduplicative representation only after comparison with the sum of
all named non-bond interfaces for that host and direction. Acceptance required:

- overlap at least 95% of canonical rows;
- bond nonmissing fraction at least 95%;
- Pearson correlation at least 0.999;
- relative mean absolute reconstruction error at most 0.005;
- direction semantics supported by raw names.

All 14 host-direction cases pass. The observed correlations are
0.999999-1.000000 and relative errors are 0.000003-0.001170. This is numerical
validation, not an assumption that `bond0` is authoritative.

For machine `i`:

`throughput_total_i[t] = bond0_TX_i[t] + bond0_RX_i[t]`.

The total is missing if either direction is missing. Non-bond interfaces are
not added again. Details and component lists are in
`outputs/network_representation_decisions.csv`.

## 5. Packet telemetry

Only the five raw packet channels found nonconstant in Phase 1A are retained:

- acamas `bond0` dropped packets;
- acamas `eno1` dropped packets;
- dedale `bond0` dropped packets;
- demophon `bond0` dropped packets;
- perse `bond0` dropped packets.

Each raw value is preserved. Its paired event variable is exactly:

`event[t] = 1` if the observed raw drop value is greater than zero, otherwise
`0`; if the raw value is missing, the event is missing.

These channels remain overwhelmingly sparse/near-constant. They are optional
event context only, never dense regression targets. They are not part of the
primary candidate families in Section 10; adding a packet-event experiment
would require a protocol amendment made before viewing its results.

## 6. Future leads, predictor lags, and notation

At forecast origin `t`:

- target lead `h` means `y[t+h]`;
- predictor lag `l` means `x[t-l]`;
- an association cell compares `x[t-l]` with `y[t+h]`.

Lag zero is information observed at origin `t`; it is current context, not
future information.

Frozen future leads and measured approximate wall-clock equivalents:

- 1 sample = 42.285164 s (0.704753 min)
- 2 samples = 84.570328 s (1.409505 min)
- 4 samples = 169.140656 s (2.819011 min)
- 8 samples = 338.281312 s (5.638022 min)
- 16 samples = 676.562624 s (11.276044 min)
- 32 samples = 1,353.125248 s (22.552087 min)
- 64 samples = 2,706.250496 s (45.104175 min)
- 128 samples = 5,412.500992 s (90.208350 min)

Association predictor lags are `[0, 1, 2, 4, 8, 16, 32, 64, 128]`.

## 7. Fixed own-history and augmentation features

The baseline uses target lags `[0, 1, 2, 4, 8, 16, 32]`, namely
`y[t], y[t-1], y[t-2], y[t-4], y[t-8], y[t-16], y[t-32]`.

One augmented comparison adds exactly one candidate's history at
`[0, 1, 2, 4, 8, 16, 32]` to the unchanged baseline. Lags 64 and 128 are
descriptive-association lags only and are not Ridge features in this phase.
No relationship-specific history tuning is allowed.

For a level-like predictor, any predictor-side historical change at lag `l`
must use only information available by the origin. The one-step form is
`x[t-l] - x[t-l-1]`; no value later than `t` may enter a predictor feature.
Such a transformation must be identified before test evaluation and selected
using train/validation only.

## 8. Level and change targets

For level-like used-memory and used-disk targets, both definitions are tested:

- level: `y[t+h]`;
- cumulative origin-to-future change: `y[t+h] - y[t]`.

The change target is never `y[t+h] - y[t+h-1]`; that expression uses a future
reference and answers a different question.

## 9. Target-time-purged global chronological split

For each primary target and lead, construct the master eligible-origin set
using the fixed target history, future target, and same-segment requirements.
Sort the `N` eligible origins globally by origin timestamp. Treat this sorted
sequence as zero-based. Define:

- `train_cut_index = floor(0.60 * N)`;
- `validation_cut_index = floor(0.80 * N)`;
- `train_cut` as the origin timestamp at `train_cut_index`;
- `validation_cut` as the origin timestamp at `validation_cut_index`.

Thus “timestamp at `floor(...)`” means the timestamp at that exact zero-based
position, not the last timestamp before it. For each origin, define
`target_timestamp` as the observed canonical timestamp at positional lead
`t+h`, not as origin wall-clock time plus an assumed fixed interval.

Assign origins as follows:

- TRAIN when `target_timestamp <= train_cut`;
- VALIDATION when `origin_timestamp > train_cut` and
  `target_timestamp <= validation_cut`;
- TEST when `origin_timestamp > validation_cut`.

Eligible origins not satisfying one of those rules are deliberately unused:

- the train-validation purge contains origins at or before `train_cut` whose
  target is later than `train_cut`;
- the validation-test purge contains origins after `train_cut` and at or
  before `validation_cut` whose target is later than `validation_cut`.

These lead-aware exclusions are the embargo; no artificial fixed-size embargo
is added. Every nonempty split must satisfy:

`max(train target_timestamp) <= train_cut < min(validation origin_timestamp)`

and:

`max(validation target_timestamp) <= validation_cut < min(test origin_timestamp)`.

There is no segment-local 60/20/20 split and no retraining separately in later
segments. Exact target/lead timestamp boundaries are recorded in
`outputs/split_boundaries_by_target_lead.csv`.

Candidate missingness is handled within these fixed, purged target/lead
partitions.
For a candidate comparison, remove rows lacking any required candidate or
baseline value, then evaluate the baseline and augmented model on exactly the
same remaining rows. Candidate availability must not move the master temporal
split boundaries.

All feature scaling parameters are fit on training rows only and then applied
unchanged to validation and test. Validation alone may select a candidate,
association lag, predeclared transformation, or displayed augmentation. Test
is untouched by selection. When a final “best” augmentation is displayed, it
is selected by validation MAE improvement (ties: RMSE improvement, then
lexicographic canonical candidate name) and evaluated once on test.

## 10. Frozen candidate families

### 10.1 Same-machine cross-resource

The following ordered directions are eligible:

- CPU <- memory, disk, throughput, RTT/jitter
- memory <- CPU, disk, throughput, RTT/jitter
- disk <- CPU, memory, throughput, RTT/jitter
- throughput <- CPU, memory, disk, RTT/jitter

Here CPU means machine CPU utilization; memory means used memory; disk target
means used disk; throughput means bidirectional throughput total. When disk is
a predictor, used disk, disk read, and disk write are separate one-candidate
augmentations. RTT/jitter means each of the five global signals is considered
separately. TX and RX remain provenance-bearing components and are not primary
candidate directions.

### 10.2 Same-resource cross-machine

For every ordered machine pair `i != j`, test:

- `CPU_i -> CPU_j`;
- `memory_i -> memory_j`;
- `throughput_i -> throughput_j`.

The source is one machine signal, not a cluster aggregate.

### 10.3 Leave-one-machine-out common context

For target machine `i` and each of CPU, memory, and throughput, the panel
contains two one-dimensional candidates:

- mean of the corresponding signals on the other six machines;
- median of the corresponding signals on the other six machines.

Machine `i` is explicitly excluded. The context is missing if any of the six
components is missing. No aggregate containing the target machine may be
described as independent cross-machine context.

### 10.4 Global context

Each RTT signal and jitter may predict each eligible machine-level primary
target. No full cross-resource-plus-cross-machine permutation is permitted.

## 11. Descriptive association screen

For each predeclared candidate, lead, and association lag, compute pairwise
complete Pearson, Spearman, and bounded mutual information for
`x[t-l]` versus `y[t+h]`, without crossing segments. For memory and used disk,
repeat against `y[t+h] - y[t]`.

Report pooled split-level values and retain segment-level values. A
segment-level coefficient is undefined when fewer than 30 complete pairs
exist or either variable is constant; report the reason rather than replacing
it with zero. Mutual information uses
`sklearn.feature_selection.mutual_info_regression`, `n_neighbors=3`, and
`random_state=0`. If a split/segment has more than 20,000 complete pairs, use
20,000 indices evenly spaced over chronological order (including endpoints).
No random result-dependent subsampling is allowed.

Association is descriptive, not causal. For classification support, the
candidate's association lag is selected on validation by largest absolute
Spearman (ties: smaller lag), and the corresponding test Spearman is used.

## 12. Incremental Ridge screen

The primary model is `Ridge(alpha=1)` with an intercept and no hyperparameter
optimization. Inputs use training-fitted standard scaling; the target remains
in its native unit. The baseline and candidate-augmented model are fit on the
same training origins and evaluated on identical validation/test origins.

Report MAE, RMSE, and R². Percentage improvement is:

`100 * (baseline_error - augmented_error) / baseline_error`.

R² delta is `augmented_R2 - baseline_R2`. If a baseline denominator is zero,
or R² is mathematically undefined, the affected criterion is explicitly
undefined; no epsilon or weakened substitute is allowed.

All predeclared relationships may be reported individually. Any relationship
called “best,” used in a lead-decay display, or promoted across alternative
candidates/lags/transformations must be selected using train/validation only
and evaluated exactly once on test.

## 13. Frozen evidence classification

Segment positivity means augmented segment MAE is strictly lower than baseline
segment MAE on matched test rows. Positive test-segment sample weight is:

`sum(test rows in positive eligible segments) / sum(test rows in all eligible segments)`.

A segment is eligible for this calculation when it has at least 30 matched
test rows and finite baseline and augmented MAE.

### STRONG

All conditions are required:

- test MAE improvement >= 3%;
- test RMSE improvement >= 2%;
- test R² delta > 0;
- absolute test Spearman at the validation-selected lag >= 0.20;
- positive test-segment sample weight >= 67% across at least two eligible test
  segments;
- MAE gain >= 1% at at least one immediately adjacent lead in the frozen lead
  grid, with that neighboring result independently selected on validation.

At grid endpoints there is one adjacent lead; elsewhere there are two.

### MODERATE

All first five conditions and one support condition are required:

- test MAE improvement >= 1%;
- test RMSE improvement >= 0.5%;
- test R² delta >= 0;
- absolute test Spearman at the validation-selected lag >= 0.10;
- positive eligible test-segment sample weight >= 50%;
- plus either MAE gain >= 1% at an immediately adjacent lead, or comparable
  support on multiple machines.

“Comparable support on multiple machines” means the same ordered
resource-family direction and lead satisfies the preceding five MODERATE
conditions on at least two distinct target machines, including the focal one.

### WEAK

Either there is positive incremental test evidence that fails MODERATE, or
there is association evidence without convincing incremental held-out gain.

### UNSUPPORTED

There is no useful incremental held-out evidence, or evidence is inconsistent
or adverse.

If any required condition is undefined, report it. A relationship cannot be
promoted to STRONG or MODERATE by silently omitting or weakening that
condition. Thresholds may not be changed after rankings are observed.

## 14. Frozen validation artifacts

- `outputs/canonical_panel.parquet`
- `outputs/canonical_signal_registry.csv`
- `outputs/network_representation_decisions.csv`
- `outputs/canonical_temporal_segments.csv`
- `outputs/future_lead_wallclock.csv`
- `outputs/split_boundaries_by_target_lead.csv`
- `outputs/panel_validation.json`

`build_analysis_panel.py` reproduces these artifacts and validates exact
alignment, timestamp order, segment assignment, target-window admissibility,
network representation gates, per-core exclusion, and raw SHA-256 stability.
