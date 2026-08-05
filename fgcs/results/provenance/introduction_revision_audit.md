# Introduction revision audit (Stage 1)

Date: 2026-08-05  
Base layout commit: `ead81f3`  
Revision commit: (pending at write time; see git)

## Length

| Metric | Before | After |
|--------|--------|-------|
| Approximate word count | ~310 | ~1128 |
| Rendered Introduction | ~0.45–0.55 double-column pages | ~1.5–1.6 double-column pages (starts mid page 1; Related Work begins lower page 2) |
| Article page count (footer) | 10 | 11 |
| PDF pages including highlights | 11 | 12 |
| Paragraph blocks (substantive) | 4 (+ RQ list + contributions) | 10 connected paragraphs (context → coherence → forecasting limits → profile continuity → TimeTrack → gap → study → findings → RQs → contributions/organization) |
| Citation instances in Introduction | ~5 | 21 (~12 cite commands) |
| New bibliography entries | — | **0** (all keys already verified in `references.bib`) |

## Paragraph-by-paragraph purpose map

1. **Operational context** — Multi-level cloud–edge telemetry; forecast-dependent planning actions (capacity, scaling, placement, admission, SLA risk, profile maintenance).
2. **Coherence problem** — Concrete seven-machine vs cluster CPU example; consequences; coherence as operational requirement.
3. **Ordinary forecasting insufficient** — Point-accuracy and independent-stream autoscaling literature; lowest MAE ≠ machine-to-cluster consistency.
4. **Application-profile continuity** — Unified profile model citation; predictive behavior as prior direction; this paper supplies coherent forecasting layer without schema redesign.
5. **TimeTrack suitability** — Public OAI CI/CD, seven machines, 42.285 s median, verified aggregates; distinguish dataset paper / Kaggle / Zero-Touch / this paper.
6. **Research gap** — Joint evaluation missing; hierarchical methods exist but transfer is not automatic; positive and negative hierarchy cases needed.
7. **Study overview** — Models, modes, hierarchies, chronological/seed/freeze protocol; defers formulas to §§4–5.
8. **Principal findings** — CPU 17.3% / 10.1% / coherence / seed facts; memory conditional vs EWMA; disk BU/TD boundary; peaks non-transfer.
9. **Research questions** — Compact RQ1–RQ5 with improved transition.
10. **Contributions + organization** — Six contribution items with evidence/why; short §2–§8 roadmap.

## Exact prior-profile continuity wording

> Our earlier unified application-profile model for microservices-based applications formalized requirements, components, deployment constraints, and continuum resources in a single representation, and identified predictive resource behavior as a direction for moving from descriptive profiles toward proactive profile management [kadouma2025unifiedprofile]. The present work develops and evaluates the coherent forecasting and reconciliation layer needed for that progression. It does not redesign the profile ontology or schema; instead, it supplies freeze-scoped forecast evidence that can later populate or maintain dynamic application-profile fields under exact machine-to-cluster constraints.

Framed as research continuity / architectural motivation / future integration potential — **not** as an evaluated profile-integration experiment.

## Research gap statement (summary)

Lack of a joint evaluation combining verified physical machine-to-cluster hierarchies, strong deterministic and learned baselines, multiple reconciliation modes, leakage-controlled chronological outer evaluation, MBB/multiple-comparison correction, seed robustness, top/bottom trade-offs, peak-operational qualification, and positive/negative hierarchy cases — without claiming “first” or “state of the art.”

## Key findings stated in Introduction

- CPU: LightGBM independent ≈ +17.3% vs Ridge (relative MAE improvement); LightGBM MinT ≈ +10.1% vs independent; exact coherence restored; LightGBM seed-invariant; DLinear recon gains seed-stable.
- Memory: recon often helps DLinear vs self; EWMA strongest robust; reconciled DLinear does not robustly beat EWMA.
- Disk: Ridge BU harms aggregate; TD preserves independent top at bottom cost.
- Peaks: ordinary aggregate MAE gains ⇏ universal peak-recall/false-alarm gains.
- Scoped as frozen outer-evaluation observations, not a prospective deployment winner.

## Unsupported claims check

Excluded / not asserted:

- universal reconciliation benefit
- robust memory win over EWMA
- general peak benefit
- downsampling / network / SOTA / first / multi-dataset generalization
- evaluated application-profile integration experiment

## Layout result

- `bash scripts/build_manuscript.sh`: BUILD OK
- `python scripts/validate_manuscript.py`: OK
- compilation errors: 0
- unresolved citations/references: 0
- overfull boxes: 0
- Related Work begins cleanly on article page 2
- no float-only page induced by Introduction
- Stage 0.1 table/float layout preserved (Introduction-only edit)

## Files changed

- `fgcs/manuscript.tex` (Section 1 only)
- `fgcs/results/provenance/introduction_revision_audit.md` (this file)

Sections intentionally untouched: Related Work and all later sections (no content edits beyond Introduction cross-references already present via `\ref`).
