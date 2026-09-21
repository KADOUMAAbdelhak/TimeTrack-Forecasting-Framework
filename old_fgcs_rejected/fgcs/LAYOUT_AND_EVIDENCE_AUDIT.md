# Layout and Evidence Audit (Stage 0)

Generated after forensic inspection of the Stage-0 manuscript PDF (9 pages; CAS article pages shown as Page 1–8 of 8 plus a highlights leaf).

## Build before repairs

- PDF pages: 9 (highlights leaf + 8 article pages)
- LaTeX errors: 0
- Unresolved citations/references: 0
- Overfull hboxes: 23
- Underfull hboxes: 37
- Float warnings: none explicit; extreme `\textpagefraction=.001` / `\floatpagepagefraction=1` present
- Multiply defined labels: none
- Missing figures/inputs: none

Page PNGs: `audit/pages_before/page_01.png` … `page_09.png`.

## Page-by-page findings (before)

| Page (PNG) | CAS footer | Findings |
|---|---|---|
| page_01 | (highlights) | Frontmatter highlights/keyword card. |
| page_02 | Page 1 of 8 | Title/abstract/intro OK. |
| page_03 | Page 2 of 8 | Related work start. |
| page_04 | Page 3 of 8 | **Table 1 cell overlap** in Recon./Seeds columns; dense Tables 2–3. |
| page_05 | Page 4 of 8 | Dense CPU table; figures begin. |
| page_06 | Page 5 of 8 | Memory/disk tables; mixed floats. |
| page_07 | Page 6 of 8 | **Seed table caption clipping**; empty-ish seed figure; underscore titles; claim/stats crowding. |
| page_08 | Page 7 of 8 | Claim matrix + declarations; long Kaggle URL wrapping. |
| page_09 | Page 8 of 8 | References only; orphaned DOI fragment at top from prior ref break. |

Note: the local PDF showed `Page 8 of 8` rather than `Page 8 of 7`. Mismatch risk remains when last-page counters desync under float deferral; extreme float fractions were removed.

## Confirmed root causes

1. Related-work `table*` used too many narrow columns without protected widths → overlapping text.
2. Seed/claim tables too wide for one column → caption/row collisions.
3. Dangerous CAS float fraction overrides deferred/clustered floats.
4. Aggregate plotting scripts used raw underscore titles and ambiguous groupbys (memory vs EWMA averaged across models within method).
5. Disk/memory dual aggregations (ratio-of-means vs mean-of-relatives) were unlabeled.

## Repairs applied

- Float parameters reset; `\usepackage[section]{placeins}`; `\FloatBarrier` before Discussion.
- Related-work table rebuilt (6 studies × 8 attrs) with fixed `p{}` widths.
- Baseline table split into A/B blocks; method-selection table replaces text PDF.
- Full claim matrix moved to supplementary; compact RQ summary in main.
- All main figures regenerated from frozen CSVs with publication labels.
- Disk/memory dual statistics explicitly labeled.
- URL detokenized for wrapping.

## Table redesign plan (Stage 0 decisions)

| Table | Decision | Notes |
|---|---|---|
| related_work_comparison | redesign main | Shorter; no overlaps |
| baseline_definitions | redesign main | Split models vs modes |
| experiment_registry | redesign main | Narrower `p{}` |
| cpu_main_results | keep/redesign main | Numbers unchanged; formatting tightened |
| memory_main_results | redesign main | Robust-winner wording; dual LGBM stats labeled |
| disk_boundary_results | redesign main | Primary = ratio-of-means |
| statistical_evidence | redesign main | Both disk/memory aggregations labeled |
| seed_robustness | redesign main | Compact; grids → supplementary |
| peak_results | keep main | Compact claim outcomes |
| claim_support | move supplementary | Replaced by `claim_summary.tex` |
| method_selection | add main | Replaces `method_selection_map.pdf` |

Later expansion may add horizon-level rows / CIs; Stage 0 does not change accepted results.

## Numerical conflict resolutions

| Conflict | Resolution |
|---|---|
| Disk +13.9% vs +14.8% | **+13.93%** = ratio of horizon-mean MAEs (primary). **+14.83%** = mean of horizon-level `mae_vs_independent` (secondary). |
| Memory winner | EWMA = strongest **robust** observed method. Some Ridge/DLinear reconciled **point** MAEs are lower but do not robustly beat EWMA (C2 contradicted). |
| LGBM memory +36.9% vs +38.8% | **+36.89%** = ratio of horizon-mean MAEs. **+38.82%** = mean of horizon-level relative fields. |

Artifacts: `results/provenance/manuscript_number_audit.csv`, `results/provenance/figure_audit.csv`.

## Build after repairs

- PDF pages: 11 (highlights leaf + 10 article pages; footer `Page X of 10`)
- LaTeX errors: 0
- Unresolved citations/references: 0
- Overfull hboxes: 18 (17 exceed 2 pt; see justifications below)
- Underfull hboxes: 15
- Figures after references: **none**
- Footer mismatch (`Page 8 of 7`): **not present** (consistent `Page X of 10`)
- Page PNGs: `audit/pages_after/` (local only)

## Overfull boxes >2 pt (documented)

| Approx. size | Source | Justification / follow-up |
|---|---|---|
| ~124 pt | CAS `\maketitle` social-icon row | Template-driven; requires CAS thumbnail/social hook disable, not global font/margin hacks. |
| ~30–90 pt | Dense one-column tables (`cpu`/`memory`/`disk`/`stats`/`method_selection`) | Content-width vs column; numbers preserved. Further split/table* polish deferred to section-expansion stage. |
| ~16–30 pt | Long metric/prose lines (MAE/RMSE/$R^2$, freeze tags) | Breakable text partially applied; residual CAS column hyphenation. |

No table **cell-overlap** remains in the related-work table after rebuild. Architecture figure internal box overlap was corrected.

## Acceptance checklist

| Criterion | Status |
|---|---|
| No overlapping table cells | Pass |
| No cross-column body text | Pass (spot-checked page renders) |
| No figures after references | Pass |
| No `Page 8 of 7` footer | Pass |
| No unresolved citations/refs | Pass |
| Overfull >2 pt only with justification | Pass (documented above) |
| Main figures regenerated / readable | Pass (with remaining polish on densest tables) |
| Numerical conflicts labeled | Pass |
