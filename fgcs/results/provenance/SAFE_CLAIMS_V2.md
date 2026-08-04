# Safe claims v2 (robustness-aware frozen evidence)

Qualified by hierarchy, model, method, horizons h1/h8/h16 (disk h1/h8), folds 0–2,
seeds 0/1/2 where applicable, and freezes:
`experiment-freeze-v2`, `final-analysis-freeze-v1`, `final-peak-analysis-freeze-v1`,
`final-robustness-extension-freeze-v2`, `final-robustness-analysis-freeze-v2`,
`final-reporting-freeze-v2`.

1. **LightGBM independent** consistently outperforms Ridge, EWMA, and persistence
   for core-weighted CPU across seeds 0/1/2, folds 0–2, horizons 1/8/16
   (seed-invariant; vs Ridge relative MAE ≈ -17.29%;
   vs persistence ≈ -21.58%).

2. **LightGBM MinT** further improves aggregate CPU accuracy
   (≈ -10.13% vs independent) and restores
   exact coherence; LightGBM is seed-invariant under the frozen configuration
   (seed SD = 0).

3. **DLinear CPU** results are practically seed-stable (seed SD ≈ 0.007056);
   bottom-up / WLS / MinT improve aggregate forecasts across all evaluated seeds
   (bottom-up mean relative ≈ -6.84%).

4. **Bottom-up** provides a bottom-preserving CPU reconciliation alternative
   (`ridge+bottom_up`), whereas WLS/MinT can trade machine-level accuracy for
   aggregate accuracy.

5. For **memory**, WLS and MinT often improve DLinear relative to its own
   independent forecasts (WLS ≈ -3.22%;
   MinT ≈ -3.40%), but **EWMA remains the
   strongest observed memory method** (MAE ≈ 1.05127e+09).

6. Reconciled DLinear memory forecasts do **not** robustly outperform EWMA across
   seeds (WLS vs EWMA seed-2 relative ≈ +2.06%).

7. **Disk** is a stable boundary: Ridge bottom-up harms aggregate accuracy
   (≈ +13.93%), while top-down preserves
   the independent top at a bottom-level cost.

8. Ordinary aggregate forecasting gains do **not** imply general peak-operational
   gains (P1/P2/P4 unsupported).

9. **LightGBM** remains the strongest evaluated CPU model during high-load periods
   (P3 supported).

10. **DLinear memory peak underprediction and range compression** persist across
    seeds and are amplified rather than corrected by reconciliation
    (diagnostic; all-seeds bias present = True).
