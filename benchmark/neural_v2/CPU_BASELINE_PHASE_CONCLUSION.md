# CPU Baseline Phase Conclusion

## Status

**CPU baseline phase: CLOSED.**

This is a technical research-decision record. It closes the CPU-only baseline
after validated evaluation of Persistence, Ridge, LightGBM, DLinear, LSTM, and
PatchTST over eight real future leads.

## Evidence summary

1. Strong local CPU history is highly predictive.
2. LightGBM remains the strongest absolute CPU forecaster among executed models
   across all eight evaluated real future leads.
3. Throughput context is not universally beneficial.
4. Ridge has a negative throughput effect.
5. LightGBM is effectively neutral under the primary macro-MAE and pooled
   metrics.
6. DLinear has a negative throughput effect.
7. LSTM has a modest positive throughput effect overall under all three
   aggregation definitions.
8. PatchTST has a `NEUTRAL` prospective decision and a negative overall primary
   context gain (-1.225078%).
9. Cross-resource input concatenation alone is therefore neither sufficient
   novelty nor a universally beneficial strategy.
10. The CPU-only benchmark now spans linear, tree-based nonlinear,
    decomposition-based neural, recurrent neural, and patch/Transformer-style
    forecasting families.

The standardized overall primary/pooled/mean-cell-relative context effects are:

| Model | Primary | Pooled | Cell-relative |
|---|---:|---:|---:|
| Ridge | -3.838048% | -3.631815% | -1.716727% |
| LightGBM | +0.014935% | -0.086515% | +0.719205% |
| DLinear | -2.604757% | -2.589275% | -2.867954% |
| LSTM | +1.252207% | +0.849314% | +3.087378% |
| PatchTST | -1.225078% | -1.407016% | -2.499026% |

## TCN-v2 disposition

TCN-v2 was prospectively designed and validated but has **not** been
scientifically executed. It is **DEFERRED, not deleted**.

Its projected runtime is disproportionately high, while the completed benchmark
already covers a sufficiently broad set of model families for the current CPU
baseline objective. The incremental scientific value does not currently justify
the execution cost. This is not a claim that TCN-v2 would fail.

## Next Research Phase

The next research phase will investigate:

**TRUE MULTI-RESOURCE, MULTI-TARGET, MULTI-HORIZON FORECASTING.**

Candidate target resources are:

- CPU utilization
- network throughput
- used memory
- used disk

The central question becomes:

> Does shared multi-resource temporal representation learning improve real
> multi-horizon cloud telemetry forecasting relative to independently trained
> single-resource forecasting models?

This is distinct from simply concatenating extra input features, from the
rejected hierarchical reconciliation study, and from CPU-only context
augmentation.

No multi-target architecture is selected yet. No multi-target model is
implemented in this checkpoint.
