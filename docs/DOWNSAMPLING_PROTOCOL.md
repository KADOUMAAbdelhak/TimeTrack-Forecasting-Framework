# Downsampling Protocol

Development protocol for quantifying forecasting loss under coarser telemetry.

## Native resolution

- Median sampling interval: **42.285166 s** (`timetrack.constants.SAMPLING_SECONDS`).
- Aggregation factors are integer multiples of the native row grid (post-alignment panel).

## Resolutions

| Label | Factor | Approx wall-clock bin |
|-------|--------|------------------------|
| native | 1 | ≈42.285 s |
| 2x | 2 | ≈84.6 s |
| ~3min | 4 | ≈169 s ≈ 2.8 min |
| ~5min | 7 | ≈296 s ≈ 4.9 min |

## Metric-specific aggregation

Applied on each contiguous post-outage segment independently (no cross-gap bins):

| Metric family | Rule |
|---------------|------|
| CPU (CU), memory (UM), RTT, jitter | mean within bin |
| Disk write throughput (DWT) | mean within bin |
| TX/RX throughput | mean within bin |
| Peak analysis on downsampled series | recompute train thresholds on downsampled train only |

Bins with all-NaN values are dropped.

## Equivalent wall-clock context

Context length in steps scales inversely with factor so that wall-clock history is matched:

```
context_steps(factor) = max(4, round(32 * 1 / factor * factor)) 
# i.e. keep ~32 native steps of wall-clock ≈ 32/factor downsampled steps? 
```

Specification used in code:

```
context_steps = max(4, int(round(32 / factor)))
horizon_steps = max(1, int(round(h_native / factor)))  # optional; default keep h in steps
```

For the development screen we keep **horizon in steps** at {1,8} on the downsampled grid (same step count, longer wall-clock lead time) and report both step-horizon and approximate wall-clock horizon.

## Models

- persistence
- strongest fixed (ridge)
- C1 bottom_up on cluster_UM when factor=1 and applicable

## Leakage

- Aggregation uses only past/current bin values.
- Thresholds / scalers fit on outer-train downsampled series only.
- Development outer folds only; claim-ineligible.
