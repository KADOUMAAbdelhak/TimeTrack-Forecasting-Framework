# Safe claims (final frozen evidence only)

Qualified by hierarchy, model, horizons, folds, and freeze tags
(`experiment-freeze-v2`, `final-analysis-freeze-v1`, `final-peak-analysis-freeze-v1`,
`final-reporting-freeze-v1`).

1. **Hierarchical reconciliation restores machine–cluster coherence** for CPU
   (`cpu_core_weighted`) and memory (`memory_um`): coherence error after
   bottom_up / WLS / MinT is essentially zero on evaluated outer folds.

2. **For core-weighted CPU**, reconciliation reduces aggregate MAE versus the
   same-model independent forecast for Ridge, LightGBM, and DLinear across
   horizons h1/h8/h16 and folds 0–2 (Claim B supported; mean relative effects
   about -9.2% to -10.1% depending on model/method).

3. **LightGBM + MinT is the best observed CPU configuration** in the frozen
   outer evaluation (MAE 0.9311 weighted-mean %), about
   -29.5% versus persistence independent.
   Bottom-up remains preferable when bottom-level preservation is required.

4. **For memory**, WLS/MinT provide modest aggregate improvements for Ridge and
   DLinear in many cells, but Claim C is only partially supported (fold/horizon
   uncertainty). Persistence independent remains a strong baseline; LightGBM is
   a frozen negative baseline versus persistence.

5. **Disk is hierarchy- and method-dependent**: Ridge bottom_up degrades
   aggregate MAE (Claim D1; mean relative ≈ 14.8%).
   Top-down preserves the independently forecast top while harming bottoms
   (Claim D2). Persistence independent is the best observed disk base.

6. **Ordinary aggregate-MAE gains do not imply universal peak-operational
   gains** (P1/P2 unsupported). Peak benefits are model-specific (esp. LightGBM).

7. **LightGBM remains the strongest evaluated CPU model during high-load
   periods** (Claim P3 supported across q90/q95 × folds × horizons).

Numbers: best observed / recommended operational wording only — not prospective
deployment selection.
