# Proposed cuts: 25 → 18 pages (FGCS Full Length Article)

**Status:** Option B implemented in the FGCS package (18 Nov 2026). The result is 16 pages. Table 4 (post-hoc controls) was afterwards restored to the main text at the author's request, still at 16 pages; see `SUBMISSION_CHECKLIST.md`.

## Measurements (elsarticle 5p, built 18 Nov 2026)

| Component | Pages |
|---|---:|
| Running text (16,215 words, about 900 words per page) | ≈ 18.1 |
| Seven tables and four figures | ≈ 5 |
| References (37 entries) | ≈ 1.9 |
| **Current total** | **25** |

Moving whole tables alone saves only about one page (24 with Table 1 moved). The rest has to come from text.

## Feasibility test (scratch copy only)

I trimmed a scratch copy mechanically to the budget below, keeping all equations, figures and back matter:

| Variant | Pages | Last page |
|---|---:|---|
| Text budget + Table 1 and Table 5 to supplement | 19 | — |
| … + class-threshold list and tier-2 backbone list to supplement | 19 | one third full |
| … + D-1–D-7 definitions condensed to one sentence (Option A) | **18** | nearly full (tight) |
| … + Table 4 (post-hoc controls) to supplement (Option B) | **18** | about 40 % full (margin) |

The trim simply dropped the largest paragraphs. It only proves the budget is feasible; it is not the proposed text.

## Rules every cut keeps

- **Numbers:** no number, class, interval or hash changes.
- **Nothing is lost:** every passage removed from the main text moves verbatim into new supplement sections S-A to S-C. The main text then points to them ("Supplementary Section S-B").
- **Tiers:** tier-1 and tier-2 results stay in separate paragraphs.
- **DLinear caveat:** the DLinear Rnd CPU paragraph stays whole in the main text, and −139.61 % never appears without its caveat.
- **Wording:** mechanism language stays associational.
- **Main-text findings:** every headline finding in the abstract, highlights and conclusion keeps its supporting number in the main text.
- **References:** all 37 references stay cited in the main text. If a cut would leave a reference cited only in the supplement, the citation sentence stays.

## Section budget (words of running text)

| Section | Now | Target | Cut | What moves or condenses |
|---|---:|---:|---:|---|
| 1 Introduction | 751 | 550 | −200 | Shorten the precedents paragraph (it repeats §2) and the tiers paragraph (it repeats §4). Keep contributions and findings. |
| 2 Related Work | 1,073 | 650 | −420 | Merge 2.1 and 2.2. **Table 1 (related-work comparison) → Table S-A1.** Keep 2.3 (gradient conflict and balancing) and the 2.4 gap statement. |
| 3 Framework | 1,424 | 950 | −470 | Merge the four S1/S2/M0/M1 subsections into one subsection, "Four formulations", with Eqs. 3–7 kept. Keep the M1 loss and the decomposition and interaction equations. |
| 4 Methodology | 5,167 | 2,900 | −2,270 | **4.2–4.5 and 4.10** (datasets, targets, leakage, horizons, population) become one ~650-word subsection, with detail → S-B1. **4.6–4.7** (architecture, selection) → ~350 words, detail → S-B2. **4.8 evaluation:** the class-threshold list → S-B3 (it already duplicates the decision criteria). **4.11 post-hoc controls** → ~250 words, procedures → S-B4. **4.12 tier-2 design:** the backbone specification list → Table S-B5, ~450 words kept. **4.13 tier-2 analysis:** D-1–D-7 definitions → S-B6, one-sentence summary kept; **Table 5 (diagnostic statistics) → Table S-B7** (Figure 4 and the RQ4 text keep the numbers). |
| 5 Results | 4,381 | 3,000 | −1,380 | **RQ2:** the tier-1 block-by-block (Materna) narrative and the Ridge TimeTrack concentration paragraph → S-C1; keep the summary sentences and Figure 2. **RQ3:** the tier-1 class-by-class narrative is condensed, and the VM266/VM272 and TimeTrack-memory attribution → S-C2. Keep the post-hoc control conclusion and the tier-2 paragraphs, and keep the **DLinear caveat paragraph intact**. **Joint M1:S1** → 100 words. **RQ5** → 200 words, with the original-RQ4 outcome stated in one sentence. **Persistence** → 200 words. **Efficiency** → 180 words. |
| 6 Cross-Dataset Synthesis | 356 | 120 | −236 | Fold into RQ5 as one paragraph; keep Table 7 with its tier-2 row. |
| 7 Discussion | 1,058 | 750 | −310 | Trim repetition of Results. Keep 7.2 (adverse transfer and diagnostics) and 7.6 (separate decisions). |
| 8 Threats to Validity | 947 | 600 | −350 | Remove limits already stated in §4 and §5. Keep each validity type and the tier-2 limits (cohort, seeds, tuning, D-4 LSTM-only, scale weighting, no preregistration). |
| 9 Conclusion | 409 | 300 | −110 | Tighten; keep all four findings. |
| Back matter | 648 | 500 | −150 | Shorten Data availability wording; keep every DOI, URL, tag and hash. |
| **Total** | **16,215** | **≈ 10,300** | **≈ −5,900** | |

**Floats:** Option A moves Table 1 and Table 5. Option B also moves Table 4 (post-hoc controls; its conclusion stays in the RQ3 text). Figures 1–4 and Tables 2, 3, 6 and 7 stay.

## New supplement structure (verbatim moves)

The current S1–S2 and tier-2 tables keep their order, and the new sections are added after them:

- **S-A Extended related work:** Table S-A1 (the current Table 1).
- **S-B Extended methods:**
  - S-B1 data and leakage control;
  - S-B2 architecture and selection;
  - S-B3 class thresholds;
  - S-B4 post-hoc procedures;
  - S-B5 backbone specifications;
  - S-B6 D-1–D-7 definitions;
  - S-B7 the current Table 5.
- **S-C Extended tier-1 results:**
  - S-C1 per-block context narrative and the Ridge concentration;
  - S-C2 sharing-tail attribution (VM266, VM272, TimeTrack memory);
  - (Option B) S-C3 the current Table 4.

## Decisions for the authors

1. **Option A or B.** I recommend B, because rewriting usually adds a few linking sentences and B leaves room for them.
2. **Where the shortened text lives:** an FGCS-specific version derived from `b186ee6e47`, which I recommend, leaving the JSS-format manuscript as it is; or the shared manuscript source.
3. **Any section you would rather cut less.** Methodology carries the largest cut; Results is the second-largest.
