# Robustness execution notes

Extension freeze: `final-robustness-extension-freeze-v1`  
Source prediction freeze: `experiment-freeze-v2`  
Publication status: **CONDITIONAL GO**

## Accepted packs

| Pack | Status |
|------|--------|
| `ewma_baselines` | COMPLETE (accepted) |
| `lightgbm_seed_robustness` | pending / in progress |
| `dlinear_seed_robustness` | not launched |
| `robustness_statistics` | not launched |

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
  Ridge, and EWMA (~−0.8% vs persistence; ~−2.7% vs Ridge independent).
- Final memory claims must compare Ridge/DLinear reconciliation against **EWMA**,
  not only persistence.
- Do **not** claim that Ridge independent is the strongest classical memory model.

### Disk

- EWMA is approximately tied with persistence and better than Ridge independent
  on top MAE.
- The disk boundary remains based primarily on:
  - Ridge bottom-up degradation,
  - Ridge top-down preservation,
  - persistence/EWMA strength.
- Do **not** reinterpret LightGBM disk stress as the primary disk effect.

### Units

EWMA CPU outer metrics were stored in **weighted-sum** (`cluster_CU_wsum`) units.

Future aggregate reporting must convert:

```text
weighted_mean_cpu = weighted_sum_cpu / 236
```

Do not compare weighted-sum MAE directly with percentage MAE.
