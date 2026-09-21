# TimeTrack Raw Data Audit

**Scope:** descriptive, read-only audit of the six active raw CSV files. No cleaning, interpolation, alignment, lag analysis, feature selection, or forecasting was performed.

## Reproducibility

- Script: `discovery/01_data_audit/audit_raw_data.py`
- Runtime: **17.0 s**
- Approximate peak RSS: **1751.5 MB**
- Python: `3.13.2`; pandas `3.0.5`; NumPy `2.5.1`
- Raw-file SHA-256 unchanged during audit: **PASS**
- Near-constant criterion: dominant value fraction ≥ 0.99 or unchanged-step fraction ≥ 0.99.
- Zero-dominated criterion: fraction equal to zero ≥ 0.95.
- High-correlation screen: absolute Pearson correlation ≥ 0.995; this is not interpreted as semantic equivalence.

## Dataset Inventory

| Dataset | Bytes | Rows | Columns | Timestamp start | Timestamp end |
|---|---:|---:|---:|---|---|
| `compute_dataset.csv` | 26,942,966 | 41,362 | 56 | 2024-06-24 13:37:06.164306 | 2024-07-19 16:27:05.246403 |
| `detailed_cpu_cores_dataset.csv` | 331,354,469 | 41,362 | 473 | 2024-06-24 13:37:06.164306 | 2024-07-19 16:27:05.246403 |
| `disk_dataset.csv` | 8,425,241 | 41,362 | 15 | 2024-06-24 13:37:06.164306 | 2024-07-19 16:27:05.246403 |
| `network_dataset.csv` | 2,932,318 | 41,356 | 6 | 2024-06-24 13:37:06.164306 | 2024-07-19 16:27:05.246403 |
| `packet-loss-dataset.csv` | 12,389,830 | 41,362 | 91 | 2024-06-24 13:37:06.164306 | 2024-07-19 16:27:05.246403 |
| `throughputs_dataset.csv` | 40,993,889 | 41,362 | 91 | 2024-06-24 13:37:06.164306 | 2024-07-19 16:27:05.246403 |

Full dtypes, column names, unique counts, missingness, infinities, extrema, moments, and quantiles are in `outputs/column_statistics.csv`; exact schemas are in `outputs/schema_inventory.json`.

## Timestamp and Sampling Findings

| Dataset | Strictly increasing | Duplicates | Out of order | Median interval (s) | Segments (>2× median) | Gaps >1 h |
|---|---:|---:|---:|---:|---:|---:|
| `compute_dataset.csv` | True | 0 | 0 | 42.285166 | 3 | 1 |
| `detailed_cpu_cores_dataset.csv` | True | 0 | 0 | 42.285166 | 3 | 1 |
| `disk_dataset.csv` | True | 0 | 0 | 42.285166 | 3 | 1 |
| `network_dataset.csv` | True | 0 | 0 | 42.285164 | 9 | 1 |
| `packet-loss-dataset.csv` | True | 0 | 0 | 42.285166 | 3 | 1 |
| `throughputs_dataset.csv` | True | 0 | 0 | 42.285166 | 3 | 1 |

- Exact six-file timestamp intersection: **41,356** timestamps.
- Global timestamp union: **41,362** timestamps.
- Network rows missing versus compute timestamps: **6**.
- Five datasets share the same timestamp sequence; the network file is missing a small number of exact timestamps. Exact joins are possible on shared rows; nearest-neighbor matching is not intrinsically required and was not performed.
- All gap locations and threshold flags are in `outputs/timestamp_gaps.csv`; continuous segments are in `outputs/temporal_segments.csv`.

## Semantic Signal Catalogue

| Resource family | Catalogued columns |
|---|---:|
| CPU | 494 |
| network throughput | 90 |
| packet errors | 45 |
| packet loss | 45 |
| disk/storage | 30 |
| memory | 17 |
| latency | 4 |
| jitter | 1 |

The full catalogue (`outputs/signal_catalogue.csv`) preserves every raw column and records resource family, metric, scope, machine, host, interface, core, inferred unit, and notes. Ambiguous semantics remain marked `unknown` rather than forced into a category.

## Data-Quality Screening

| Dataset | Numeric | Constant | Near-constant | Zero-dominated | Negative-value signals | Outlier-flagged signals |
|---|---:|---:|---:|---:|---:|---:|
| `compute_dataset.csv` | 55 | 9 | 2 | 4 | 1 | 44 |
| `detailed_cpu_cores_dataset.csv` | 472 | 0 | 0 | 0 | 29 | 472 |
| `disk_dataset.csv` | 14 | 0 | 0 | 0 | 0 | 0 |
| `network_dataset.csv` | 5 | 0 | 0 | 0 | 0 | 5 |
| `packet-loss-dataset.csv` | 90 | 85 | 5 | 48 | 0 | 5 |
| `throughputs_dataset.csv` | 90 | 41 | 0 | 41 | 0 | 45 |

- Constant/near-constant and zero-dominated packet signals should not be silently removed: they may encode absence of events or instrumentation behavior.
- `packet-loss-dataset.csv` contains **1,921,993** missing cells across **90** signal columns; 85/90 numeric packet channels are constant and the remaining five are near-constant sparse event channels.
- `throughputs_dataset.csv` has **41** constant channels; 41/90 channels are zero-dominated under the 95% criterion.
- `machine05 CF` is entirely missing, while the detailed per-core dataset has low but distributed missingness across all 472 numeric columns (maximum per-column missingness below 0.3%).
- In the per-core CPU file, **67** signals contain **400,053** total values outside the inferred [0,100] percentage range; 29 signals contain negative values. These require source-semantic verification rather than automatic clipping.
- Negative values and bounded-percentage violations are listed explicitly in `outputs/data_quality_screening.csv`; no values were changed.
- The 3×IQR outlier flag is descriptive only. It can mark legitimate bursts in throughput, latency, utilization, or counters.
- Monotonicity, resets, unchanged fractions, and jump magnitudes are recorded in `outputs/signal_dynamics.csv`.

## Redundancy and Identity Screening

- Exact duplicate column pairs: **93**.
- Within-dataset |Pearson r| ≥ 0.995: **66** pairs.
- Explicit aggregate/complement/interface candidates evaluated: **294**.
- Exact candidate relationships (numerical tolerance): **3**.
- Near-exact candidates (relative MAE ≤0.1%): **83**.

These screens identify redundancy candidates only. High correlation does not prove identity, causality, or interchangeability. Full results are in `outputs/exact_duplicate_columns.csv`, `outputs/high_correlation_pairs.csv`, and `outputs/discovered_relationships.csv`.

## Per-Machine Resource Coverage

| machine   | host        |   CPU |   per-core CPU |   memory |   disk/storage |   network throughput |   packet loss |   packet errors |   interface-specific network |
|:----------|:------------|------:|---------------:|---------:|---------------:|---------------------:|--------------:|----------------:|-----------------------------:|
| machine01 | acamas      |    75 |             72 |        2 |              4 |                   10 |             5 |               5 |                           20 |
| machine02 | bellerophon |    99 |             96 |        2 |              4 |                   14 |             7 |               7 |                           28 |
| machine03 | dedale      |    75 |             72 |        2 |              4 |                   14 |             7 |               7 |                           28 |
| machine04 | demophon    |    75 |             72 |        2 |              4 |                   10 |             5 |               5 |                           20 |
| machine05 | pegase      |    43 |             40 |        2 |              4 |                   14 |             7 |               7 |                           28 |
| machine06 | perse       |    75 |             72 |        2 |              4 |                   14 |             7 |               7 |                           28 |
| machine07 | phaedra     |    51 |             48 |        2 |              4 |                   14 |             7 |               7 |                           28 |

Counts are raw signal-column counts, not a quality endorsement. Cluster/global-only entries are listed in `outputs/global_cluster_signals.csv`.

## Diagnostic Figures

The following non-publication diagnostics are in `outputs/figures/`: timestamp coverage, sampling intervals, detected gaps, seven-machine CPU, cluster memory, seven-machine disk, host bond0 throughput, RTT/jitter, active packet signals, and missingness.

## Implications for the New Forecasting Study

1. **Available resource families.** The files contain CPU (machine and per-core), memory, disk/storage, network throughput, packet errors/drops, RTT/latency, and jitter. Raw names and units remain subject to source documentation where marked inferred.
2. **Consistent seven-machine metrics.** Machine-resolved CPU utilization/free CPU, memory used/available, disk used/free and disk read/write quantities are represented across all seven machines. Per-core CPU and interface telemetry are host-resolved with unequal core/interface counts.
3. **Cluster/global-only metrics.** Cluster memory/disk aggregates and global Google-DNS RTT/jitter exist; RTT/jitter are not machine-specific.
4. **Redundancy.** Exact duplicate, complement, aggregate, and very-high-correlation screens show that multiple columns can encode overlapping information. The machine-readable relationship tables must be consulted before selecting features.
5. **Potentially informative signals.** **581** numeric signals are nonconstant, not near-constant/zero-dominated, and >95% observed under the stated descriptive criteria. This includes continuously varying compute, storage, throughput, and global latency/jitter signals.
6. **Serious quality concerns.** Sparse/constant packet channels, missing network timestamps, large temporal gaps, inferred-unit ambiguity, possible counter resets, extreme bursts, and any reported negative/bounds violations require explicit handling in later protocol design.
7. **Continuous forecast-like quantities.** CPU utilization, memory/disk levels, disk rates, network throughput, RTT, and jitter are continuous or level/rate-like. This is a structural description, not a forecastability result.
8. **Event/anomaly-like quantities.** Packet errors/drops and highly zero-dominated signals are better described initially as sparse event processes than ordinary dense regression targets.
9. **Joint multi-metric plausibility.** Yes, substantial timestamp overlap and machine-resolved CPU/memory/disk/network telemetry make joint multi-metric study technically plausible. Whether it adds predictive value is untested.
10. **Joint multi-machine plausibility.** Yes, seven machines/hosts have repeated resource schemas, although core counts, interfaces, scales, missingness, and dynamics differ and must be respected.
11. **Network as context.** Network throughput and global RTT/jitter overlap temporally with compute telemetry and can plausibly be evaluated as context features. No predictive relationship is claimed.
12. **Uncertainties for the next phase.** Lagged dependence, lead-specific information, outage/gap handling, sampling irregularity, stationarity/regime changes, counter semantics, scale normalization, host identity mapping, interface aggregation, and causal leakage boundaries require dedicated lag/dependency analysis next. None was tested here.

## Output Index

- `raw_file_inventory.csv` / `raw_hashes_before_after.json`
- `schema_inventory.json` / `column_statistics.csv`
- `timestamp_statistics.csv` / `timestamp_gaps.csv` / `temporal_segments.csv`
- `timestamp_alignment_summary.csv` / `missing_timestamps_by_dataset.csv`
- `signal_catalogue.csv`
- `data_quality_screening.csv` / `signal_dynamics.csv`
- `exact_duplicate_columns.csv` / `high_correlation_pairs.csv` / `discovered_relationships.csv`
- `machine_resource_coverage.csv` / `global_cluster_signals.csv`
- `figures/*.png`
