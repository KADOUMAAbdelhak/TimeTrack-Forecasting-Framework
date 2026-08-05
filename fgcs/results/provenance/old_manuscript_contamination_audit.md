# Old-manuscript contamination audit

- Date: 2026-08-05
- Scope: `fgcs/` submission workspace vs Materna legacy markers

## Search terms
Materna, GWA-T-13, VMware ESX, 1,576 VMs, 520/527/547 VMs, Random Forest/XGBoost Materna results, CPU/memory/disk/network R² claims from old manuscript, obsolete figure names.

## Findings
| Location | Hit | Action |
|----------|-----|--------|
| `fgcs/CLEANUP_REPORT.md` | Historical cleanup notes describing Materna asset removal | Keep (process documentation; not manuscript prose) |
| `fgcs/manuscript.tex` | **none** | Pass |
| `fgcs/highlights.txt` | **none** | Pass |
| `fgcs/supplementary/` | **none** | Pass |
| `fgcs/references.bib` | **none** Materna-specific | Pass |
| `fgcs/figs/` filenames | No Materna figure assets present | Pass |

## Overlap vs retained old sources
No Materna `.tex` scientific source remains in `fgcs/` for n-gram comparison (removed in cleanup Stage 0). Template boilerplate / author metadata / declarations / bibliography excluded by policy.

## Conclusion
No nontrivial old scientific prose contamination in the submission manuscript.
