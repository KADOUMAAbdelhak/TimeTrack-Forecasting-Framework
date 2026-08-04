# Robustness execution notes

Active extension freeze: `final-robustness-extension-freeze-v2`  
Peeled commit: `9750626607e4bf8bc6d45f89f6ee5805c87f3251`  
Scientific config hash: `f19707c2a6f24478`  
Preserved (not altered): `final-robustness-extension-freeze-v1`  
Source prediction freeze: `experiment-freeze-v2`  
Publication status: **CONDITIONAL GO**

## Pack status

| Pack | Status |
|------|--------|
| `ewma_baselines` | COMPLETE (accepted) |
| `lightgbm_seed_robustness` (freeze-v1) | **REJECTED provisional** → `results/development/provisional_robustness/final-robustness-extension-freeze-v1/lightgbm_seed_robustness/` |
| `lightgbm_seed_robustness` (freeze-v2) | COMPLETE (accepted) |
| `dlinear_seed_robustness` | pending / in progress |
| `robustness_statistics` | not launched |

## Accepted LightGBM v2 interpretation (do not rerun)

### CPU

- LightGBM predictions are **bitwise identical** across seeds 0, 1, and 2.
- LightGBM independent beats the strongest deterministic CPU baseline (**Ridge**)
  in all **27** seed×fold×horizon cells.
- MinT improves LightGBM CPU in all **27** cells (~−10% vs independent).
- The frozen LightGBM configuration is **seed-invariant** because bagging and
  feature subsampling are disabled (`subsample=1`, `subsample_freq=0`,
  `colsample_bytree=1`) with seed-0-matching `n_jobs=-1`.
- Multi-seed testing confirms **invariance**, not stochastic dispersion.

### Memory

- LightGBM remains approximately **38.8% worse than EWMA**.
- No seed supports a positive memory LightGBM claim.
- LightGBM memory remains a **negative baseline**.

## EWMA interpretation (accepted; do not rerun)

### CPU

- EWMA ≈ persistence; weaker than Ridge and LightGBM.
- Strongest deterministic CPU baseline: **Ridge**.

### Memory

- EWMA is the strongest deterministic independent baseline among persistence,
  Ridge, and EWMA.
- Compare Ridge/DLinear reconciliation against **EWMA**, not only persistence.

### Disk

- EWMA ≈ persistence; better than Ridge independent on top MAE.
- Boundary remains Ridge BU/TD + persistence/EWMA; not LightGBM disk stress.

### Units

```text
weighted_mean_cpu = weighted_sum_cpu / 236
```
