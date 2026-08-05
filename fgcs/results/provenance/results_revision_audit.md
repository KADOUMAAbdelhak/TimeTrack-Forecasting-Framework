# Results revision audit (Section 6)

## Length
| Metric | Before | After |
|--------|--------|-------|
| Section 6 prose words | ~461 | ~1265 |
| Rendered Results | fragmented (~1–1.5 pp effective) | ~2.5–3.0 pages (pp. 9–11/12) |
| Full article pages | 15 | 14 (≤15) |

## Subsection structure
**Before:** CPU Forecasting and Reconciliation; Memory Results; Disk Failure Boundary; Peak-Operational Analysis; Seed Robustness.

**After:**
1. CPU Forecast Accuracy, Coherence, and Trade-offs
2. Conditional Memory Results
3. Disk Reconciliation Failure Boundary
4. Operational and Robustness Evidence

## Main tables before → after
| Artifact | Action |
|----------|--------|
| cpu_main_results | Redesigned with H=1/8/16 columns |
| memory_main_results | Redesigned; seed-aware vs EWMA; notes for ratio vs mean-rel |
| disk_boundary_results | Retained/tightened; +13.93% primary; +14.83% note |
| statistical_evidence | Redesigned compact A1–P5 claim summary |
| peak_results | Moved to supplementary |
| seed_robustness | Moved to supplementary |
| method_selection | Moved to supplementary |
| claim_summary | Moved to supplementary |

## Main figures before → after
| Figure | Action |
|--------|--------|
| cpu_accuracy_vs_output_width | Retained (main) |
| bootstrap_relative_effects | Retained (main) |
| top_bottom_tradeoff | Retained (main) |
| disk_boundary | Retained (main) |
| cpu_peak_results | Retained as operational figure |
| coherence_before_after | Supplementary |
| memory_reconciliation_vs_ewma | Supplementary |
| dlinear_memory_peak_bias_by_seed | Supplementary |
| cpu_reconciliation_effect_by_seed | Supplementary |

## Narrative additions
- **CPU:** independent ranking; −17.29%/−21.59%; MinT −10.13%; coherence; Ridge BU; DLinear −6.84% and 27/27; H-width semantics; top/bottom; RQ1/RQ2.
- **Memory:** EWMA strongest; DLinear vs indep 16/27,20/27,21/27; vs EWMA contradicted/unsupported; seed-2 +2.06%; +36.89% vs +38.82%; RQ3.
- **Disk:** baselines; BU +13.93% (ratio) vs +14.83%; TD 0% top / bottom 3.79→4.55×10^8; WLS/MinT; RQ4.
- **Ops:** P3 with q90/q95 MAE; P1/P2/P4 unsupported; P5 range 0.46–0.51; seed synthesis; literature positioning without cross-paper MAE; RQ2/RQ5.

## RQ answers
- RQ1: CPU accuracy+coherence improve under selected recon (LGBM+MinT).
- RQ2: CPU persists across folds/H/seeds; H≠lead.
- RQ3: Memory conditional; EWMA remains strongest robust.
- RQ4: Disk exposes top/bottom boundary.
- RQ5: Ordinary MAE gains ≠ universal peak transfer.

## Page-budget actions
Moved secondary tables/figures to supplementary; compacted claim table; removed standalone seed subsection; integrated seeds into CPU/memory/ops prose.

## Build
14 pages; 0 overfull; 0 unresolved citations/refs; validate_manuscript OK.
