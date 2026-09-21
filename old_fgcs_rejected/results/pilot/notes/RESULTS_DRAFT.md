# Results Draft (Executed Only)

Tables: `results/tables/latex/main_comparison.tex`, `ablation_results.tex`  
Leaderboards: `results/metrics/leaderboard.csv`  
Aggregate: `results/metrics/all_runs.csv` (352 rows)

## Per-target notes

### CPU (`cluster_mean_CU`, `machine01_CU`)
LightGBM achieved the lowest smoke MAE among tested models at h1/h4, improving over last-value persistence. Ridge helped on cluster CPU vs persistence at short horizon.

### Memory (`cluster_UM`)
Ridge/LightGBM improved R² versus persistence, but errors remain large in absolute bytes. Normalize before cross-metric ranking.

### Network TX (`tx_bond0_acamas`)
Predictability is weak (R² near 0). LightGBM/ridge edge persistence slightly at h1; gains shrink / baselines remain relevant at h4.

## Efficiency
See `results/figures/efficiency/mae_vs_train_time.pdf`. Baselines are essentially free; LightGBM training remains modest on this data scale.
