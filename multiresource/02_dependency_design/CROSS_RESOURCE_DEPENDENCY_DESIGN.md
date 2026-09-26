# Cross-Resource Dependency Design Audit

## Scope and leakage control

All statistics in this document use only `MULTIRESOURCE_DESIGN_REGION`, rows
0-16,877 of the canonical panel. The region ends at
2024-07-07 16:52:17.183763, immediately before the earliest first outer-test
origin used by any frozen CPU machine split. Membership SHA-256 is
`9980b51cd09ed865bc87b01de074d20413c853cfa5e67d96832e69557acb9e03`.

The audited resource representations are CPU utilization, `log1p` total
throughput, used-memory level, and `log1p` disk-write activity. Spearman
correlations were computed per machine at predictor lags
`[0,1,2,4,8,16,32,64,128]`, within temporal segments. Both levels and
segment-safe first differences were audited. Correlation is descriptive and is
not interpreted as predictive causality.

## Main relationships

Median machine-level contemporaneous Spearman correlations in level space are:

| Pair | Median rho | Machine range |
|---|---:|---:|
| CPU / throughput | 0.333 | 0.210 to 0.575 |
| CPU / memory | 0.250 | heterogeneous; near zero to moderate positive |
| CPU / disk-write | 0.171 | 0.061 to 0.507 |
| throughput / memory | 0.150 | 0.035 to 0.378 |
| throughput / disk-write | 0.105 | heterogeneous, including near zero |
| memory / disk-write | 0.039 | -0.030 to 0.534 |

CPU/throughput is the clearest broadly positive relationship. Its median
first-difference correlation remains 0.262 (machine range 0.146-0.335), so the
association is not solely a shared persistent level. CPU/memory difference
correlation is smaller but remains positive at 0.145. Most other differenced
relationships have median magnitudes below 0.08.

## Directionality and lag structure

Lag zero is necessarily symmetric. At positive predictor lags, the strongest
median level relationships generally remain at lag 0 or short lags:

- CPU <- memory peaks at lag 4 (median rho 0.252), while memory <- CPU peaks at
  lag 2 (0.258).
- memory <- throughput peaks at lag 2 (0.156), while throughput <- memory peaks
  at lag 0 (0.150).
- disk-write <- throughput peaks at lag 2 (0.111), while throughput <-
  disk-write peaks weakly at lag 16 (0.110).
- long-lag median correlations generally decay, and isolated machine maxima do
  not constitute general directional evidence.

Directionality asymmetry is therefore modest and machine-dependent. The audit
does not justify hard-coded causal routing between resources.

## Design implications

1. Cross-resource input value is plausible, especially for CPU/throughput, but
   prior CPU benchmarks show it is architecture-dependent.
2. Sharing should be tested rather than assumed; weak median differenced
   dependencies argue for resource-specific output heads and against forcing a
   fully homogeneous latent representation.
3. Resource-specific normalization is mandatory before fusion.
4. Selective fusion, adapters, or shared/private representations are reasonable
   later hypotheses, but none is selected in Phase 3A.
5. The mandatory S1/S2/M1 factorial is required to distinguish input-information
   value from multi-task representation-sharing value.

Machine-readable results are in `LAGGED_SPEARMAN_DEPENDENCIES.csv` and
`DEPENDENCY_SUMMARY.csv`.
