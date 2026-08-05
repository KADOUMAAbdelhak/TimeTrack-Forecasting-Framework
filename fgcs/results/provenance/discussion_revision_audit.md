# Discussion revision audit (Section 7)

## Length
| Metric | Before | After |
|--------|--------|-------|
| Section 7 prose words | ~172 | ~944 |
| Rendered Discussion | ≪1 page (stubs) | ~1.3 pages (PDF pp. 12–13; Conclusion starts p. 14) |
| Full article pages | 15 | 15 |

## Subsection structure
**Before:** Accuracy–Coherence Trade-offs; Why Reconciliation Is Hierarchy-Dependent; Implications for Application Profiling; Limitations.

**After:**
1. Why Reconciliation Helps CPU Forecasting
2. Hierarchy-Dependent Method Selection
3. Implications for Application Profiling and Operation
4. Limitations and Future Research (with `\paragraph{Limitations.}` / `\paragraph{Future research.}`)

## Artifacts moved to supplementary
- `fgcs/figs/cpu_peak_results.pdf` (main stacked peak figure; wide layout already in supplement)
- `fgcs/figs/bootstrap_relative_effects.pdf` (claim-relevant forest; full forest already in supplement)
- Section 6.4 retains P1–P5 prose + Table `tab:stats`; peak panels referenced as supplementary

## Interpretations added
- **CPU:** baseline difficulty ranking; complementary residual interpretation (non-causal); BU vs WLS/MinT operational distinction; coherence ≠ accuracy.
- **Memory:** EWMA as robust comparator; seed-2 WLS reversal as methodological example.
- **Disk:** used-disk semantics; BU/TD/WLS–MinT boundary without labeled reset causation.
- **Selection framework:** hierarchy-aware frozen-evaluation interpretation (not production policy).
- **Profiling:** possible predictive fields; coherent-profile motivation; unevaluated integration.
- **Peaks:** MAE vs threshold metrics; DLinear compression; operational qualification.
- **Limitations / future work:** one-step/`H` semantics; dataset; model/seed; peak protocol; no live loop; lead-time/`H` separation; adaptive selection; probabilistic; profile integration; valid resolution.

## Unsupported-claim review
- No new numerical results; no universal recon/LightGBM/EWMA claims; no causal MinT mechanism; no production/profile integration claim; no cross-paper MAE superiority; no network/downsampling/probabilistic results; no long-horizon/`H`-as-lead claims.

## Page-budget actions
Moved CPU peak + bootstrap figures to supplement; removed `\clearpage` before bibliography; compacted Discussion compounds that caused overfull boxes.

## Build
15 pages; 0 overfull; 0 unresolved citations/references; validate_manuscript OK; Conclusion untouched.
