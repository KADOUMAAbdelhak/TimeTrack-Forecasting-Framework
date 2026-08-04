# Final peak-analysis protocol (analysis freeze)

Separate from the prediction freeze. Consumes `experiment-freeze-v2` outer NPZs
only; never trains or retunes models; never modifies the frozen pack runner.

| Layer | Tag |
|-------|-----|
| Predictions | `experiment-freeze-v2` |
| Peak analysis | `final-peak-analysis-freeze-v1` |

## Why a separate freeze

The freeze-v2 pack runner `run_peak_analysis` uses `bottom_up_proxy` that
reuses independent forecasts. It cannot support reconciliation peak claims.
See `results/final/PEAK_ANALYSIS_BLOCKER.md`.

## Inputs

Packs: `memory_classical`, `memory_dlinear`, `cpu_classical`, `cpu_dlinear`.

## Reconstruction gate

Reconstruct `independent` / `bottom_up` / `wls` / `mint` from NPZs with the same
validation-residual covariance / WLS variances and `nonnegative=false`. Match
accepted `reconciliation_results.csv` within abs ≤ 1e-9 or rel ≤ 1e-8 before
any peak metric is written. Abort on mismatch.

## CPU units

Peak metrics use `cluster_CU_weighted_mean = cluster_CU_wsum / 236` with verified
cores `[36,48,36,36,20,36,24]`. Weighted-sum retained for coherence checks.

## Matrix

2 hierarchies × 4 models × 3 horizons × 3 folds × 4 methods × 2 thresholds
= **576** atomic rows. No outer-MAE method selection.

## Thresholds

Per hierarchy × fold from **train** target only: q90, q95.
`actual_peak = y ≥ q`, `predicted_peak = ŷ ≥ q`. Exact timestamps only.

## Entrypoint

```bash
python scripts/analyze_final_peaks.py \
  --config configs/final_peak_analysis.yaml \
  --source-config configs/final_fgcs_packs.yaml \
  --output results/final/packs/07_peak_analysis
```
