# Editorial Manager double-anonymized upload guide

## A. Flat anonymous manuscript sources (LaTeX)

Directory (all files at one level — no subfolders):

`fgcs/fgcs_em_anonymous/`

### Upload order on Editorial Manager

1. Item type **Manuscript WITHOUT Author Identifiers** / **Manuscript File**  
   Upload first: `manuscript_anonymous.tex`
2. Then add remaining flat files with the closest item types:
   - `references_anonymous.bib`, `manuscript_anonymous.bbl`
   - `cas-dc.cls`, `cas-common.sty`, `cas-model2-names.bst`
   - table `.tex` files
   - figures (`architecture_or_hierarchy.png`, `cpu_accuracy_vs_output_width.pdf`, `top_bottom_tradeoff.pdf`)
   - CAS thumbnail JPEGs (`cas-*.jpeg`) required by `cas-common.sty`
3. Let Editorial Manager build the PDF and inspect it before approving.
4. Do **not** upload the structured Overleaf ZIP as the manuscript file.
5. Only upload a ZIP if EM later offers a dedicated LaTeX Source Files/Archive type.

Local preview PDF (not for EM manuscript upload):  
`fgcs/submission/manuscript_anonymous_preview.pdf`

## B. Title page (author identities)

Upload under **Author Names, affiliations, and corresponding author details**:

- Preferred: `fgcs/submission/title_page.pdf`
- Source: `fgcs/submission/title_page.tex`
- Also available: `fgcs/submission/author_details.docx`

Contains: title, authors, affiliation, corresponding author, funding, acknowledgements, CRediT, competing interest, non-anonymized code URL.

## C. Declaration of Interest Statement (required)

Upload separately:

- `fgcs/submission/declaration_of_interest.pdf`

## D. Anonymized supplementary material

- PDF: `fgcs/submission/supplementary_anonymous.pdf`
- Source: `fgcs/supplementary/supplementary_anonymous.tex`

Freeze tags replaced by neutral snapshot IDs (see private mapping; do not upload the mapping).

## E. Anonymous code repository (author action required)

The anonymous manuscript currently contains the placeholder:

`https://anonymous.4open.science/r/TimeTrack-Forecasting-Framework-E369`

Before submission:

1. Create an [Anonymous GitHub](https://anonymous.4open.science/) read-only mirror of the public repo.
2. Configure replacements for: `KADOUMAAbdelhak`, author names, University of Vaasa, Fingletek, author emails.
3. Replace the placeholder URL in `fgcs_em_anonymous/manuscript_anonymous.tex`.
4. Recompile locally / re-upload the `.tex` (and regenerate `.bbl` if needed).
5. Open the anonymous URL in an incognito window and verify owner/commits/emails/institution links are hidden.

Alternative: upload `fgcs/submission/anonymized_artifacts_bundle.zip` as anonymized supplementary material (no `.git`, no author names).

## F. What changed for anonymity

- Authors → Anonymous Author(s)
- Self-citations → `\cite{anonymous2025profile}` with anonymized bib entry
- GitHub URL removed from the anonymous manuscript
- `final-reporting-freeze-v2` and related tags neutralized
- Funding / Acknowledgements / CRediT / Competing Interest moved to title page
- AI declaration updated to disclose AI-assisted Figure 1 layout
- PDF metadata set to Anonymous

## G. Identified manuscript

`fgcs/manuscript.tex` remains the non-anonymized production source (authors + funding + acknowledgements + CRediT + competing interest + public code URL). AI figure disclosure was also updated there.
