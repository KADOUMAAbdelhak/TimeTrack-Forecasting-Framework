# Submission file inventory

Generated: 2026-08-05  
Manuscript commit base: `0db3b4e` (+ final review commit)

Full checksums: `fgcs/dist/editorial_manager/SHA256SUMS.txt`

## Manuscript

| File | Purpose | Upload item type | Required | SHA-256 (prefix) | Pages | Author confirmation |
|------|---------|------------------|----------|------------------|-------|---------------------|
| `dist/editorial_manager/manuscript.pdf` | Review/production PDF (no highlights page) | Manuscript | required | `e45fc384…` | 14 | none |

## LaTeX source files

| File | Purpose | Upload item type | Required | SHA-256 (prefix) | Notes |
|------|---------|------------------|----------|------------------|-------|
| `dist/editorial_manager/timetrack_fgcs_em_flat.zip` | Flat LaTeX sources for Editorial Manager | LaTeX source files | required | `06ea4a18…` | 24 files; no subfolders |
| `dist/timetrack_fgcs_overleaf.zip` | Structured Overleaf workspace | optional/local | optional | `77452038…` | 67 files |

## Highlights

| File | Purpose | Upload item type | Required | Notes |
|------|---------|------------------|----------|-------|
| `highlights.txt` / EM copy | 5 bullets ≤85 chars | Highlights | required | SHA `abbb8d0e…`; not rendered in manuscript PDF |

## Supplementary material

| File | Purpose | Upload item type | Required | SHA-256 (prefix) | Pages |
|------|---------|------------------|----------|------------------|-------|
| `dist/editorial_manager/supplementary_material.pdf` | Independent supplement | Supplementary material | required | `550cb707…` | 12 |

## Optional / conditional

| File | Purpose | Required | Status |
|------|---------|----------|--------|
| Title page (separate) | Only if double-anonymized | no | Not needed — FGCS is **single anonymized** |
| Anonymized manuscript | Double-blind review | no | Not needed |
| Graphical abstract | Optional | no | Not prepared |
| `AI_DECLARATION_CANDIDATE.txt` | Generative-AI disclosure | required at submission | **Author must confirm wording before insert/upload** |
| Public code URL | Already in Code Availability | required | Verified public: `https://github.com/KADOUMAAbdelhak/TimeTrack-Forecasting-Framework` |
| Funding statement | Elsevier funding section | required | **Author must confirm** (CRediT lists funding acquisition; no grant text in-repo) |
| Acknowledgements | Optional | optional | Generic text removed; restore only with verified names |

## Do not upload in this task

- Cover letter
- Raw predictions / models / datasets
- Provenance audit CSVs (unless journal asks)
