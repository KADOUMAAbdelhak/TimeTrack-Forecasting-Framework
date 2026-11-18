# FGCS submission package — checklist

**Journal:** Future Generation Computer Systems (ISSN 0167-739X).
**Article type:** Full Length Article.
**Source:** repository commit `b186ee6e47`, `manuscript/jss/`. The scientific content is unchanged.
**Requirements source:** FGCS Guide for Authors (PDF saved 18 Nov 2026) and Elsevier's LaTeX instructions.
**Status:** not committed, not pushed, not submitted. The main text was condensed to meet the 18-page limit (Option B).

## Package layout

| Path | What it is | Editorial Manager item type |
|---|---|---|
| `submission_files/Manuscript.pdf` | Manuscript built from the zip below (**16 pages**, two-column) | Manuscript |
| `submission_files/FGCS_LaTeX_Source.zip` | **Flat** source: `manuscript.tex`, `references.bib`, `manuscript.bbl`, `Figure_1.pdf`–`Figure_4.pdf` (no subfolders) | LaTeX source files |
| `latex_source/` | The same seven files unzipped, for inspection | — |
| `submission_files/Highlights.docx` (+ `.txt`) | 5 highlights, 67–73 characters each | Highlights |
| `submission_files/Supplementary_Material.pdf` | Supplement built from its zip (43 pages, including S-A to S-E moved from the main text) | Supplementary material |
| `submission_files/FGCS_Supplement_Source.zip` / `supplement_source/` | Flat supplement source (`supplement.tex`, `references.bib`, `supplement.bbl`) | Keep for revision; do not upload LaTeX as a Supplemental item |
| `submission_files/Cover_Letter.pdf` (+ `.docx`, `.tex`) | Cover letter, **with one paragraph you must complete** | Cover letter |
| `submission_files/Author_Biographies.docx` | Biographies of 47, 68 and 50 words (photos not supplied) | Vitae / author biography |
| Declaration of Interests `.docx` | **Not supplied.** Generate it with Elsevier's declarations tool and upload it unchanged | Declaration of interest |

Suggested caption for the supplement: "Supplementary material: tier-1 matched-cell and seed diagnostics, tier-2 contrast, interaction, baseline, parameter and D-1 to D-7 diagnostic tables, the DLinear Rnd CPU audit, the frozen decision criteria and the tier-1 overall bootstrap intervals."

## What changed from the JSS source (formatting and metadata only)

- **Class and title page:** `cas-dc` became `elsarticle` (`5p,twocolumn`, newtx Times fonts). The front matter now uses `frontmatter`, `keyword`, `\corref`, `\affiliation` and `\journal{Future Generation Computer Systems}`. The JSS short title, running header and source comment are gone.
- **Bibliography:** `cas-model2-names` (author–year) became `elsarticle-num-names`. Citations are numbered in order of appearance; `\citet` still prints "Author et al. [n]".
- **CRediT:** `\credit{}`/`\printcredits` became a "CRediT authorship contribution statement" section with the same roles.
- **Tables:** the seven `\input{tables/...}` files are inlined verbatim.
- **Figures:** renamed `Figure_1`–`Figure_4` in order of appearance. They are byte-identical PDFs.
- **Float placement:** the preamble float fractions were relaxed. Without this, all seven tables and two figures were deferred to the end; now each sits near its first mention.
- **Supplement:** flattened into one file, with `tier2_supplement.tex` inlined verbatim. Two frozen fragments from the same commit were appended at the end: `decision_criteria.tex`, which the main text cites as "supplementary decision criteria", and `overall_bootstrap_intervals.tex`, the source of the tier-1 intervals quoted in Results. The existing S1–S2 and tier-2 table numbers are unchanged.

## Readability and positioning pass (review step 2)

Changes in response to the pre-submission review, without new experiments:

- **New title.** "Contextual Input versus Representation Sharing in Multi-Metric Runtime Forecasting: Selective Gains and a Recurring Sharing Cost". It replaces "...Are Separable Design Decisions...", which could read as true by definition.
- **Abstract** (241 words) and **introduction** rewritten around three findings. The scale-free typical-cell results (matched-cell median ratios and win rates) now come first; MacroMAE stays the prespecified endpoint.
- **Related Work:** a new paragraph positions the design against channel-independent versus channel-dependent forecasting. It cites Han, Ye and Zhan (TKDE 2024), CCM (NeurIPS 2024) and TimeXer (NeurIPS 2024), each checked against its publisher or proceedings record, and states what S1/S2 add.
- **Results:** the sharing paragraphs lead with typical-cell statistics, then the MacroMAE gains and classes.
- **Caveats:** repeated caveats were cut from Results and RQ4 and point to Threats to Validity.
- **Supplement:** the RQ-renumbering paragraph and the full tier-2 freezing and execution paragraph moved verbatim to the new Supplementary Section S-E.
- **Precision:** 42.285164 s became about 42.3 s; 0.705–90.208 min became about 0.7–90 min; worker-hours became 85.6, 75.3 and 20.4. These roundings are the only numbers not found verbatim in the original.
- **Discussion:** "Separate Decisions" became "What the Separation Means in Practice", with actionable guidance.
- **Highlights and cover letter** were updated to match. The persistence statement is limited to the 20 tier-2 Bitbrains VMs, because tier-1 Rnd S1 throughput skill was slightly positive.
- **Checks:**
  - no citation lost;
  - 40 references, all cited;
  - every −139.61 % keeps its caveat;
  - the 16 pages, all identifiers, and builds without undefined references are unchanged.
- **Not done** (it needs new frozen experiments): tuned modern baselines, the loss-balancing intervention, larger or modern traces, more seeds.

## Length reduction (Option B, implemented)

- **Main text:** 16,215 → 9,650 words of running text; 25 → 16 pages.
- **Moved to the supplement:** Table 1 (related-work comparison) and Table 5 (tier-2 diagnostic statistics), now Supplementary Tables S14 and S15. The post-hoc control gains table was moved and then **restored at the author's request**; it is now main-text Table 3, byte-identical, still at 16 pages.
- **New supplement sections S-A to S-D:** these carry every removed passage, table and definition **verbatim**. A check matched every moved paragraph. Only cross-references were rewritten ("main-text Section~n") and headings made unnumbered. In the supplement only, the moved full-width tables use footnotesize so they fit a single-column page.
- **Kept verbatim in the main text:** all figures, the remaining tables, every equation, the tier-2 results paragraphs, the DLinear Rnd CPU caveat paragraph, the RQ4 diagnostics and the core Discussion paragraph on adverse transfer.
- **Rewritten more briefly (new prose):** the Introduction precedents paragraph, Related Work, formulation linking text, the Methods data/training/evaluation/post-hoc/backbone/diagnostic summaries, the tier-1 Results narratives, the joint-system, heterogeneity, persistence and efficiency summaries, parts of the Discussion, Threats and Conclusion, and the Data availability wording.
- **Checks on the rewrite:**
  - every number in the new main text occurs in the 25-page original;
  - all 37 references are still cited in the main text;
  - all identifiers (DOIs, tag, commit, hashes) are present;
  - every −139.61 % keeps its caveat;
  - 0.046 is used;
  - no obsolete claims returned.
- **Not moved:** the Introduction and Conclusion were shortened, but their removed sentences only summarised material that remains elsewhere, so they were not copied to the supplement.
- **Reproducibility:** `tools/` holds the assembly script, the template and the 25-page and 15-page originals.

## Verification done

- **Before condensation**, the 25-page body was checked against `b186ee6e47`: re-applying the packaging changes reproduced it exactly. **After condensation**, the abstract, title, keywords, bibliography, all four figures, every kept table and equation, and every `%%KEEP` passage are byte-identical to that 25-page body. The removed material appears verbatim in supplement sections S-A to S-D.
- Every block of the four original supplement source files appears verbatim in `supplement.tex`.
- Both documents were built from the extracted zips:
  - **Manuscript:** 16 pages, no undefined references or citations, Tables 1–5, Figures 1–4, 40 references (all 40 `.bib` entries cited in the main text).
  - **Supplement:** 43 pages, no warnings.
- These strings were found in the manuscript PDF:
  - DOIs and identifiers: `10.5281/zenodo.24339239`, `10.5281/zenodo.24189108`, tag `fgcs-v04-min-final-r2`, and both SHA-256 values.
  - Key numbers: −139.61, 98.6 %, 0.046, 29 of 32, 11/24, 29/32 and 0.04–1.40.
- The only overflow warning is 1.7 pt, in elsarticle's page-1 e-mail footnote.

## FGCS requirements

**Status key:** ✅ met · ⚠️ needs author action or judgement · ❌ not met.

| Requirement (Guide for Authors) | Status |
|---|---|
| Full Length Article: double column, single spaced | ✅ `elsarticle` 5p two-column |
| **Full Length Article: at most 18 pages including figures, tables and references; longer manuscripts are returned without review** | ✅ **16 pages** after Option B in `PAGE_LIMIT_CUT_PLAN.md`; see "Length reduction" below. |
| ORCID: the corresponding author's verified ORCID must be visible (set to "Everyone"), otherwise the submission is rejected | ⚠️ Set this in the ORCID record and in Editorial Manager. No ORCIDs are in the manuscript. |
| Title concise; no undefined abbreviations | ✅ |
| Author names; affiliations with lowercase superscript letters, **full postal address and country** | ⚠️ South Asian University has a full address. **University of Vaasa has only city and country: add the street address and postcode.** |
| Corresponding author marked; e-mail on the title page | ✅ |
| Abstract at most 250 words, no references, abbreviations defined | ✅ 241 words |
| 6–10 keywords, English, avoiding "and"/"of" | ✅ 7 keywords |
| Highlights: 3–5 bullets, at most 85 characters each, separate editable file with "highlights" in the name | ✅ 5 bullets, 67–73 characters, `Highlights.docx` |
| Editable `.tex` source; a PDF is not a source file | ✅ |
| Equations editable, numbered | ✅ |
| Tables editable, captioned, cited, numbered, notes below, no vertical rules | ✅ |
| Figures as separate files with logical names (Figure_1…), vector PDF, captioned, cited, numbered | ✅ Fonts were embedded by the generators (matplotlib Type 42; TikZ) but not re-checked with a font tool. |
| Do not combine multiple graphs into one file (except images meant for comparison) | ⚠️ Figures 2–4 are multi-panel comparison figures. I judged this within the exception; the editor may ask for splits. |
| Generative AI in figures | ⚠️ The figures are data visualisations rendered by deterministic code from the frozen outputs, with AI-assisted code development. This is allowed and already disclosed in the declaration. No per-caption disclosure was added; confirm you agree. |
| Supplementary material cited in the text, captioned, submitted with the manuscript | ✅ Use the caption above in Editorial Manager. |
| Research data (Option C): deposit in a repository and link at submission | ✅ Zenodo 10.5281/zenodo.24339239 and 10.5281/zenodo.24189108; code at the Git tag. ⚠️ Enter the dataset link in Editorial Manager. |
| Data and software references with `[dataset]` in the reference list | ⚠️ Encouraged, not required. Datasets and code are cited in Data availability by link, not as reference entries. Adding them would change the reference list, so this was not done. |
| Numbered sections; no abstract numbering | ✅ |
| CRediT author statement | ✅ |
| Acknowledgements section before the references (if any) | ✅ None |
| Funding statement (standard sentence if none) | ✅ Exact standard sentence |
| Declaration of competing interests in the manuscript | ✅ |
| Declaration of Interests Word file from the Elsevier declarations tool, uploaded at submission | ⚠️ **Author action:** complete the tool and upload its `.docx` unchanged. |
| GenAI declaration: titled section before the reference list, naming the tools and reasons, with the required responsibility sentence | ✅ Section present with the exact title, before the references. It names ChatGPT, Codex and Claude Code. |
| Numbered reference style, in order of appearance | ✅ `elsarticle-num-names` |
| Every reference real; DOIs where available | ✅ 28 of 37 have DOIs. The 9 without are 8 conference papers whose proceedings issue no DOIs (ICML, NeurIPS, ICLR, AISTATS) and one online book (OTexts). |
| Journal names abbreviated per LTWA | ⚠️ Full journal names are printed. The production team usually abbreviates them; change the `.bib` if you want them abbreviated at submission. |
| Vitae: biography of at most 100 words per author, editable, **plus passport-type photograph** | ⚠️ Biographies are supplied. **Photographs are not available in the repository.** |
| British or American English, not mixed | ✅ British English. A search for American spellings found nothing. |
| Submission declaration: not published elsewhere and **not under consideration elsewhere**; prior submissions disclosed | ⚠️ **Author must confirm.** The branch history is a JSS review revision, and the repository has a folder named `old_fgcs_rejected`. Confirm that the JSS manuscript is withdrawn or finally decided, and state any earlier FGCS submission in the cover-letter placeholder. |
| Not a conference extension | ✅ None declared |
| Cover letter | ⚠️ Supplied; **complete or delete the bracketed paragraph.** |
| Editorial Manager LaTeX: PDF as Manuscript, flat source archive as "LaTeX source files", `.bib` + `.bbl`, LaTeX not uploaded as Supplemental | ✅ |
| Compiles on Editorial Manager's pdfLaTeX | ⚠️ Built locally with XeTeX (tectonic); pdfLaTeX was not available here. All packages (`elsarticle`, `newtx`, `booktabs`, `array`, `seqsplit`, `hyperref`, `amsmath`, `graphicx`) are standard TeX Live. Check the PDF Editorial Manager builds. |
| APC awareness (open access only) | ⚠️ Author choice at acceptance |

## Unresolved before upload

1. **Page limit:** resolved (16 pages), but **read the condensed text before submission**. It was shortened editorially (see "Length reduction"), and the authors should approve the wording.
2. **ORCID:** a verified, publicly visible ORCID for the corresponding author.
3. **University of Vaasa address:** full postal address (street, postcode).
4. **Declaration of Interests:** the `.docx` from Elsevier's declarations tool.
5. **Submission history:** confirm the JSS manuscript is withdrawn or finally decided, and complete the cover-letter paragraph on prior submissions.
6. **Photographs:** passport-type photos for the vitae.
7. **Optional:** LTWA journal abbreviations; `[dataset]`/software reference entries; per-caption AI notes on figures (not required under Elsevier's data-visualisation rule).
8. **Final build:** check the PDF that Editorial Manager builds (pdfLaTeX).
