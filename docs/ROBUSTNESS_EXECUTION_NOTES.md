# Robustness execution notes

Active extension freeze: `final-robustness-extension-freeze-v2`  
Preserved (not altered): `final-robustness-extension-freeze-v1`  
Source prediction freeze: `experiment-freeze-v2`  
Publication status: **CONDITIONAL GO**

## Accepted / provisional packs

| Pack | Status |
|------|--------|
| `ewma_baselines` | COMPLETE (accepted) |
| `lightgbm_seed_robustness` (freeze-v1 execution) | **REJECTED provisional** → `results/development/provisional_robustness/final-robustness-extension-freeze-v1/lightgbm_seed_robustness/` |
| `lightgbm_seed_robustness` (freeze-v2) | pending / in progress |
| `dlinear_seed_robustness` | not launched |
| `robustness_statistics` | not launched |

Rejection reasons for v1 LightGBM execution:

- execution_logic_differs_from_extension_freeze
- config_hash_differs_from_extension_freeze
- thread_count_differs_from_seed0_source
- seed_not_only_changed_variable

## EWMA interpretation (accepted; do not rerun)

### CPU

- EWMA is effectively tied with persistence (~−0.11% mean independent).
- EWMA is weaker than Ridge and LightGBM.
- Existing CPU model ranking remains unchanged:
  **LightGBM ≫ Ridge > EWMA ≈ persistence**.
- LightGBM must be compared against the strongest deterministic CPU baseline
  among persistence, EWMA, and Ridge.
- **Strongest deterministic CPU baseline: Ridge.**

### Memory

- EWMA is the strongest deterministic independent baseline among persistence,
  Ridge, and EWMA.
- Final memory claims must compare Ridge/DLinear reconciliation against **EWMA**,
  not only persistence.
- Do **not** claim that Ridge independent is the strongest classical memory model.

### Disk

- EWMA is approximately tied with persistence and better than Ridge independent
  on top MAE.
- The disk boundary remains based primarily on Ridge BU/TD and persistence/EWMA.
- Do **not** reinterpret LightGBM disk stress as the primary disk effect.

### Units

```text
weighted_mean_cpu = weighted_sum_cpu / 236
```
