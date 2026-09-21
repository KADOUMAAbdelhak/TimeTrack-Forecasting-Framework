# FINAL MANUSCRIPT REVIEW

Date: 2026-08-05  
Base commit: `0db3b4e`  
Scientific status: `GO_SCOPE_NARROWED` (H = multi-output width; all metrics one-step)

## A. Submission compliance

| Item | Status |
|------|--------|
| FGCS page maximum (≤18) | Pass (14) |
| Internal page limit (≤15) | Pass (14) |
| Highlights handling | Pass — `highlights.txt` only; removed from `manuscript.tex` / PDF |
| Abstract words | 171 ≤ 250 |
| Keywords | 8 (in 6–10) |
| References cited | 39 |
| Review model | **Single anonymized** (official guide, 2026-08-05) — authors retained |
| Data statement | Present (Kaggle + dataset paper) |
| Source packages | Structured Overleaf ZIP + flat EM ZIP |

## B. Scientific integrity

- Accepted freeze evidence only; no new experiments.
- One-step semantics explicit in Abstract, Methods, Protocol, Results, Discussion, Conclusion.
- H interpreted as joint multi-output training width; not evaluated lead.
- CPU: LightGBM+MinT best observed frozen aggregate; Ridge+BU bottom-preserving.
- Memory: conditional; EWMA strongest robust comparator; seed-2 reversal retained.
- Disk: boundary; BU harms aggregate; TD preserves top at bottom cost.
- Peaks: P1/P2/P4 unsupported; P3 supported; P5 diagnostic supported.
- Seed treatment: LightGBM invariance; DLinear practically stable.
- Baseline strength: comparisons vs Ridge/persistence/EWMA as appropriate; no weak-baseline wins.

## C. Article quality

Narrative flow Introduction→Related Work→Dataset→Methods→Protocol→Results→Discussion→Conclusion is coherent. Related work positions reconciliation vs independent forecasting without cross-paper numerical superiority. Methodology and protocol are leakage-aware and freeze-documented. Results interpret without new numbers. Discussion synthesizes mechanisms as interpretations. Conclusion closes RQ1–RQ5.

## D. Visual quality

Main PDF: 0 overfull; no highlights page; no float-only page; no figures after references. Supplement: S-numbering; 0 overfull after one-column + table resize; 12 pages. Captions state one-step / H-width where relevant.

## E. References

39 cited entries; no duplicates/uncited keys in validator; HARMONY blank-author defect previously fixed. Metadata previously audited in `reference_audit.csv`.

## F. Declarations and metadata

| Item | Status |
|------|--------|
| Authors / order / emails / affiliation | Present; University of Vaasa |
| Corresponding author | Abdelhak Kadouma |
| CRediT | Present |
| Competing interests | Present |
| Data availability | Present |
| Code availability | Public URL verified |
| Funding | **Author confirmation required** |
| Acknowledgements | Generic text removed |
| AI declaration | Candidate file only — **author confirmation required** |

## G. Remaining author actions

1. Confirm/insert generative-AI declaration wording (`AI_DECLARATION_CANDIDATE.txt`).
2. Confirm funding statement (grant text vs “no specific grant”).
3. Optionally restore a specific acknowledgement with verified names.
4. Confirm author biographies/photos if required by Editorial Manager at upload time.
5. Do not submit until those author-controlled items are resolved.

## Decision

**READY_AFTER_AUTHOR_CONFIRMATION**
