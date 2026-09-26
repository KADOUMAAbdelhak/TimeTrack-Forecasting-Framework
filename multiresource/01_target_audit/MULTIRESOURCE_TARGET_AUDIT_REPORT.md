# Multi-Resource Target Audit Report

## Audit status and data separation

This is discovery/design evidence only. No forecasting model was trained, no
multi-target architecture was implemented, and no frozen benchmark result or
raw/canonical data was changed.

Full-panel inspection was restricted to structural facts: timestamp coverage,
missingness, units, raw/canonical identity, impossible values, constants,
duplicates, and legal-support counts. Every statistic capable of influencing a
target, transform, dependency, scaling, or loss decision uses only
`MULTIRESOURCE_DESIGN_REGION`.

The design region is canonical rows 0-16,877 (16,878 rows), ending at
2024-07-07 16:52:17.183763. It precedes the earliest first outer-test origin
across all frozen machine splits, 2024-07-07 16:52:59.474465. It contains no
outer-test row.

- Membership SHA-256:
  `9980b51cd09ed865bc87b01de074d20413c853cfa5e67d96832e69557acb9e03`
- Region JSON SHA-256:
  `b3a24cd1ffdfc947fbf5e5742a6f1266325230d45501023af4c115345640b0f6`
- Canonical panel SHA-256:
  `c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`

## Candidate decisions

| Candidate | Status | Rationale |
|---|---|---|
| CPU utilization | `PRIMARY_TARGET_CANDIDATE` | Existing frozen CPU target and anchor |
| Network TX | `AUXILIARY_ONLY` | Directional component of accepted total |
| Network RX | `AUXILIARY_ONLY` | Directional component of accepted total |
| Raw total throughput | `SECONDARY_TARGET_CANDIDATE` | Native target/evaluation, strongly skewed for training |
| `log1p` total throughput | `PRIMARY_TARGET_CANDIDATE` | Nonnegative, exact inverse, materially lower skew |
| Used-memory level | `PRIMARY_TARGET_CANDIDATE` | Only available memory level; dynamic and nontrivial beyond short leads |
| Used-memory change | `SECONDARY_TARGET_CANDIDATE` | Useful robustness/auxiliary target, noisier than level |
| Used-disk occupancy level | `AUXILIARY_ONLY` | Operationally real but nearly trivial under persistence |
| Used-disk occupancy change | `SECONDARY_TARGET_CANDIDATE` | Tests occupancy dynamics without rewarding static level |
| Disk-read raw / `log1p` | `REJECT_FOR_MULTI_TARGET` | 71.0%-99.7% zero across machines; inconsistent dense-target semantics |
| Disk-write raw | `SECONDARY_TARGET_CANDIDATE` | Dynamic native activity but extremely heavy-tailed |
| `log1p` disk-write | `PRIMARY_TARGET_CANDIDATE` | Dynamic across machines, exact inverse, much lower skew |

The proposed four-resource tuple is therefore CPU utilization, `log1p` total
throughput, used-memory level, and `log1p` disk-write activity.

## CPU

### Identity and quality

The target remains exactly `machineXX__cpu_utilization`, sourced from
`compute_dataset.csv`, raw column `machineXX CU`. Its inferred semantics are
percent utilization. It is the unchanged target from the completed CPU
benchmark. Full-panel finite missingness is approximately 0.18%-0.28%; two
retained negative values (-0.6 minimum) occur for machine06 and are already
documented frozen-data quality anomalies. No cleaning is introduced.

### Dynamics and persistence

Across machines in the design region, median mean is 3.96, standard deviation
2.06, IQR 0.774, skewness 6.04, lag-1 autocorrelation 0.601, and lag-128
autorrelation 0.037. The series is bursty rather than static. Median persistence
MAE/IQR rises from 1.269 at lead 1 to 2.316 at lead 128; median persistence R2
is already negative from lead 2 onward.

### Recommendation

Keep the identity representation and evaluate in native percent-like units.
Use train-only robust scaling for joint optimization. CPU is the anchor that
connects Phase 3 to the frozen CPU baseline.

## Throughput

### Identity and units

For each machine, the accepted total is:

`machineXX__network_tx + machineXX__network_rx`,

where TX and RX are the direction-explicit `bond0` aggregate-interface raw
columns from `throughputs_dataset.csv`. The total is missing if either
direction is missing; component interfaces are not added again. Raw throughput
units remain unknown. Full-panel totals are nonnegative (minimum 0.899) with at
most 199 missing rows for a machine.

### Dynamics and transform

Raw totals are strongly heavy-tailed: the across-machine median design-region
skewness is 8.04 and median coefficient of variation is 3.47. `log1p` reduces
median skewness to 2.47 and coefficient of variation to 0.279 while preserving
ordering and permitting exact `expm1` inversion. The `log1p` representation has
lag-1 autocorrelation 0.316 and lag-128 autocorrelation 0.098. Persistence
MAE/IQR is approximately 1.02 at lead 1 and 1.35 at lead 128, with negative
median R2 throughout, so this is not a trivial target.

### Recommendation

Use `log1p(total throughput)` for training and recover native total throughput
for MAE/RMSE/R2. Retain raw total as the native evaluation target and TX/RX as
auxiliary diagnostics, not separate core targets.

## Memory

### Available candidates and missing capacity information

The canonical registry contains only `machineXX__memory_used`, sourced from
`compute_dataset.csv` raw column `machineXX UM`, with inferred byte units. No
free-memory, total-capacity, cached/buffered, or utilization-percent signal is
available in the canonical repeated schema. Consequently, `used + free`
identities and percentage utilization cannot be established safely. A capacity
normalization must not be invented.

### Dynamics, level, and change

Used memory is finite throughout the panel. Design-region machine medians have
mean approximately 1.62e10 bytes, standard deviation 5.62e8, IQR 3.23e8,
skewness 0.55, lag-1 autocorrelation 0.860, and lag-128 autocorrelation 0.405.
It is persistent, but actual median absolute origin-to-future change grows from
about 27.0 MB at lead 1 to 130.6 MB at lead 128. Persistence MAE/IQR increases
from 0.363 to 0.844 and median R2 falls from 0.669 to -0.261.

Segment-safe first differences are essentially never zero and are much noisier:
median first-difference standard deviation is 2.39e8 bytes, while the
first-difference lag-1 autocorrelation is -0.204. Change is scientifically
useful for robustness and dependency checks, but making it the only target
would discard the meaningful level state.

### Recommendation

Use used-memory level as the primary candidate, with per-machine, train-only
median/IQR scaling. Retain origin-to-future change as a secondary target or
evaluation view. Report native byte errors and do not describe the signal as
memory utilization percentage.

## Disk/storage

### Occupancy

`machineXX__disk_used` comes from `disk_dataset.csv`, raw column `machineXX UD`,
with inferred byte units and complete structural coverage. It is extremely
persistent: median lag-1 autocorrelation is 0.9991 and lag-128 autocorrelation
0.9788. Persistence MAE/IQR is only 0.0045 at lead 1 and 0.0281 at lead 128;
median persistence R2 remains 0.958 at lead 128. Although actual median absolute
change grows from 1.72 MB to 118.3 MB, the level's huge scale makes naive
forecasting appear exceptionally strong.

Used-disk level is therefore auxiliary-only for the primary multi-target study.
Origin-to-future occupancy change remains a secondary scientific question.

### Read activity

`machineXX__disk_read` is a raw activity/rate signal from `compute_dataset.csv`
(`machineXX DRT`), with unknown rate units. Its zero fraction ranges from about
71.0% to 99.7%; median design-region zero fraction is 96.7%. Raw median skewness
is 46.9 and even `log1p` skewness is 5.70. This machine-inconsistent event-like
behavior is unsuitable as one dense shared regression target and is rejected
for the core tuple.

### Write activity

`machineXX__disk_write` is the corresponding `machineXX DWT` activity/rate.
Except for machine06 (about 4.4% zeros), it is dense. Raw values are
nonnegative, but median skewness is 21.9 and coefficient of variation 4.86.
`log1p` reduces median skewness to 2.08. The transformed target remains dynamic:
lag-1 autocorrelation is only 0.062, persistence MAE/IQR is about 0.97-1.05
across leads, and median R2 is negative. Median absolute transformed changes
remain near 0.2 while their variance grows with horizon.

### Recommendation

Use `log1p(disk write activity)` as the primary disk target and evaluate after
exact `expm1` inversion in the available raw rate units. Keep raw write as a
secondary representation, occupancy level as auxiliary, occupancy change as a
secondary target, and reject disk-read activity from the primary tuple.

## Joint support

Legal support requires 128 finite historical samples for every included
resource, all eight finite future targets, and no history or target segment
crossing.

| Tuple | Min/machine | Median/machine | Max/machine | Total |
|---|---:|---:|---:|---:|
| CPU only | 26,729 | 29,542 | 29,986 | 204,374 |
| CPU + throughput | 12,344 | 18,286 | 19,602 | 124,108 |
| + memory | 12,344 | 18,286 | 19,602 | 124,108 |
| + used-disk | 12,344 | 18,286 | 19,602 | 124,108 |
| + disk-read | 7,184 | 14,212 | 15,027 | 92,546 |
| + disk-write | 8,221 | 14,345 | 14,967 | 92,994 |

Throughput causes the largest first support reduction (median 37.6% versus CPU
only). Memory and used-disk add no loss. Disk-write raises the median loss to
about 51.6%, but every machine retains at least 8,221 legal origins. This loss
must be accepted and matched across S1/S2/M1 if disk-write remains in the tuple.
Detailed counts by machine, segment, and existing outer fold are in
`JOINT_SUPPORT_AUDIT.csv`.

## Cross-resource dependencies

The clearest level relationship is CPU/throughput: median contemporaneous
Spearman rho 0.333 across machines (range 0.210-0.575). It survives first
differencing with median rho 0.262. CPU/memory is moderate (about 0.250 level,
0.145 difference); CPU/disk-write is weaker and heterogeneous (0.171 level,
0.073 difference). Other pair medians are 0.039-0.150 in levels and mostly below
0.08 after differencing. Short-lag directionality asymmetries exist but are not
consistent enough to imply causal routing.

These results support testing cross-resource information and shared learning;
they do not guarantee improvement and do not establish predictive causality.

## Scale and loss implications

Median raw variance proxies differ dramatically: CPU 4.25, throughput 7.23e3,
disk-write 1.86e12, and memory 3.16e17. Raw joint MSE would be almost entirely a
memory loss. The recommended baseline is fixed resource-specific transforms
followed by train-only median/IQR scaling and equal resource/horizon weight in
normalized space. Native-unit metrics must always be recovered and reported
per resource.

## Final target gate

**B. MULTI_RESOURCE_STUDY_SUPPORTED_WITH_TARGET_CHANGES**

Four resource families have defensible targets and adequate joint support, but
the primary disk target should be transformed write activity rather than used
capacity, and throughput should use a log training representation. No model or
architecture is authorized by this decision.
