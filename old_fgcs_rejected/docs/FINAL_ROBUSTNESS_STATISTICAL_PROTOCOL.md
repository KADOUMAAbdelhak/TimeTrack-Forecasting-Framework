# Final robustness statistical protocol

Tag: `final-robustness-analysis-freeze-v2`  
Supersedes: `final-robustness-analysis-freeze-v1` (mutated; archived; not claim-eligible)  
Source prediction freeze: `experiment-freeze-v2`  
Source robustness-extension freeze: `final-robustness-extension-freeze-v2`

## Purpose

Regenerate claim-eligible multi-seed robustness statistics from **accepted**
prediction artifacts only. Never train models. Never consume provisional
post-freeze derived summaries, rejected LightGBM v1 packs, or the archived
mutated analysis-freeze-v1 pack.

## Freeze immutability

Tags are immutable. Corrections require a new versioned freeze tag.

Never use `git tag -f`, `git push --force`, or `git push --force-with-lease` for
freeze tags. Create tags with `scripts/create_immutable_freeze_tag.py`.

Execution requires `HEAD == final-robustness-analysis-freeze-v2^{commit}`.

## Inputs

| Source | Role |
|--------|------|
| `cpu_classical` / `memory_classical` | seed-0 persistence/ridge/lightgbm |
| `cpu_dlinear` / `memory_dlinear` | seed-0 DLinear |
| `01_ewma_baselines` | EWMA (`8c7c971920dd0c71`) |
| `02_lightgbm_seed_robustness` | LightGBM v2 (`446473103b0cf235`) |
| `03_dlinear_seed_robustness` predictions | DLinear (`ecd66cd4bc4a7770`) |

## Comparators (fixed)

- CPU strongest deterministic: **Ridge independent**
- Memory strongest deterministic: **EWMA independent**

## Bootstrap

Paired moving-block bootstrap within `seed × fold × horizon` (n_boot=5000,
seed=0). Direct relative effects. Do not pool timestamps across seeds.
Model seed columns must never be overwritten by the bootstrap RNG seed.

## Holm families

Eight families as listed in `configs/final_robustness_statistics.yaml`.

## Memory interpretation (safe)

Reconciliation often improves DLinear relative to its own independent
forecasts, but EWMA remains the strongest observed memory forecasting method,
and the reconciled DLinear variants do not robustly outperform it across seeds.
Memory remains secondary / conditional reconciliation evidence, not best-model
evidence.

## Runner

```bash
python scripts/validate_robustness_statistics_config.py \
    --config configs/final_robustness_statistics.yaml --require-frozen
python scripts/analyze_robustness_statistics.py \
    --config configs/final_robustness_statistics.yaml \
    --output results/final/robustness/04_robustness_statistics \
    --require-frozen
```
