# DLinear Runtime Diagnosis

Development investigation of slow/hanging DLinear runs in hierarchy screens.

## Profiled configuration

Single-series development outer fold 0, target `cluster_mean_CU`, h=1, c=32, n_train≈7030.

| Setting | Fit (s) | Predict (s) | Notes |
|---------|---------|-------------|-------|
| epochs=5, timeout=60 | ~1.4 | ~0.002 | Baseline bounded |
| epochs=30, max_batches=50 | ~0.15 | ~0.002 | Batch cap dominates |
| epochs=30, timeout=30, max_batches=20 | ~0.11 | ~0.002 | Hard bound |

Artifact: `results/development/metrics/dlinear_runtime_profile.json`.

## Findings

1. **Not a single-series algorithmic hang.** Window construction, tensor conversion, init, epoch loop, and predict are all sub-second to low-second for one series.
2. **Pipeline multiplicity.** Hierarchy screens fit DLinear independently for each bottom + top series (≈8–9 fits) × models × horizons × folds. Without progress logging between series, a multi-hour wall-clock looks like a hang.
3. **Process contention.** Concurrent LOMO + hierarchy Python processes competed for CPU; DLinear jobs were observed at 0% CPU while another job held the core.
4. **No DataLoader worker deadlock** — training uses manual batching, not `DataLoader`.
5. **Thread oversubscription risk** — mitigated by `torch.set_num_threads(1)` default in bounded mode.
6. **Memory** — predict now chunks batches; arrays forced contiguous.

## Controls added (`DLinearForecaster`)

- `timeout_sec` (default 180)
- `patience` / early stopping on validation loss
- `max_batches_per_epoch`
- `num_threads` (default 1)
- `runtime_meta_` recorded on the model (`timed_out`, `epochs_ran`, epoch timing)

## Decision

**Bounded and included only in selected experiments.**

- Default hierarchy / multivariate grids keep `INCLUDE_DLINEAR=False`.
- Neural confirmation and optional screens may enable DLinear with `epochs≤8`, `timeout_sec=120`, `num_threads=1`.
- Not scientifically excluded: single-series cost is acceptable; unbounded multi-series grids are operationally excluded.
