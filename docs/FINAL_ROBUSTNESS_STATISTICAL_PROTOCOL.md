# Final robustness statistical protocol

Tag: `final-robustness-analysis-freeze-v1`  
Source prediction freeze: `experiment-freeze-v2`  
Source robustness-extension freeze: `final-robustness-extension-freeze-v2`

## Purpose

Regenerate claim-eligible multi-seed robustness statistics from **accepted**
prediction artifacts only. Never train models. Never consume provisional
post-freeze derived summaries or rejected LightGBM v1 packs.

## Inputs

| Source | Role |
|--------|------|
| `cpu_classical` / `memory_classical` | seed-0 persistence/ridge/lightgbm |
| `cpu_dlinear` / `memory_dlinear` | seed-0 DLinear |
| `01_ewma_baselines` | EWMA |
| `02_lightgbm_seed_robustness` | LightGBM seeds 1–2 (+ seed-0 analysis via classical) |
| `03_dlinear_seed_robustness` predictions | DLinear seeds 1–2 |

## Comparators (fixed)

- CPU strongest deterministic: **Ridge independent**
- Memory strongest deterministic: **EWMA independent**

## Bootstrap

Paired moving-block bootstrap within `seed × fold × horizon` (n_boot=5000,
seed=0). Direct relative effects. Do not pool timestamps across seeds.

## Holm families

Eight families as listed in `configs/final_robustness_statistics.yaml`.

## Runner

```bash
python scripts/analyze_robustness_statistics.py \
    --config configs/final_robustness_statistics.yaml \
    --output results/final/robustness/04_robustness_statistics
```
