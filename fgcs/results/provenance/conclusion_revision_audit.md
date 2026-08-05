# Conclusion revision audit (Section 8)

## Length
| Metric | Before | After |
|--------|--------|-------|
| Section 8 prose words | ~52 | ~461 |
| Paragraphs | 1 | 6 |
| Rendered Conclusion | ≪0.25 page | ~0.6 page (end of p.13 through mid-p.14) |
| Full article pages | 15 | 15 |

## Headline values retained
- ≈17.3% LightGBM independent vs Ridge (matches Introduction; audit −17.29%)
- ≈10.1% LightGBM MinT vs LightGBM independent (matches Introduction; audit −10.13%)

No other new numerical findings.

## RQ closure map
| RQ | Closure in Conclusion |
|----|------------------------|
| RQ1 | LightGBM+MinT improves CPU aggregate MAE ≈10.1% and restores exact coherence |
| RQ2 | Persists across folds / H / models / seeds; not across evaluated lead times; H = output width |
| RQ3 | Memory recon helps DLinear vs itself; EWMA remains strongest; no robust beat of EWMA |
| RQ4 | Disk: hierarchy validity ≠ recon gains; BU harms aggregate; TD preserves top at bottom cost |
| RQ5 | Ordinary MAE ≠ universal peak gains; P3 LightGBM high-load; recall/FA not generally established; DLinear compression |

## Consistency
- **Abstract:** same selective hierarchy-dependent message; no new claims.
- **Introduction:** headline percentages and scoped findings aligned.
- **Results:** CPU/memory/disk/peak synthesis without restating tables.
- **Discussion:** limitations and future work echoed compactly; no duplication of mechanistic essays.
- **SAFE / UNSUPPORTED:** no universal recon/LightGBM/EWMA/peak/SOTA claims; no profile integration or live orchestration claim.

## Page-budget actions
Moved `fgcs/figs/disk_boundary.pdf` to supplementary (label `fig:disk`); retained `tables/disk_boundary_results.tex` and full §6.3 prose; optional supplement pointer in §6.3.

## Unsupported-claim review
Pass: one-step/`H`-width explicit; no long-horizon; no universal method; no evaluated profile/orchestration integration; no cross-paper numerical superiority; no new results.

## Build
15 pages; 0 overfull; 0 unresolved citations/references; validate_manuscript OK.
