# STAGE 19H2A — Final scientific wording integration

Status: **STAGE_19H2A_PASS**. Wording and existing-value formatting only.
New analysis=0; training=0; inference=0; scientific-result modifications=0.

## Changed files and scope

- `manuscript/jss/manuscript.tex`: Abstract, Introduction, Results §§5.1–5.2.
- `manuscript/jss/supplementary/final_evidence_supplement.tex`: Table S2
  introductory note and caption only.
- `manuscript/jss/tables/posthoc_controls.tex`: one explanatory Table 3 note.

Methods/protocol, primary result rows, all figures, bibliography, declarations,
repository metadata and submission assets are unchanged. Discussion and
Conclusion already contain the bounded accuracy/consolidation interpretation
and required no edits. Contributions, RQs, existing labels and citations are
preserved. Before-source snapshots and stage-only diffs are retained here.

## Integrated clarifications

Results §5.2 explicitly identifies VM266 as the T1 tail contributor and VM272
as the T3 contributor, retaining their **82.10%/86.97%** positive-excess shares.
The existing H1 frozen-partition audit is described using each VM's frozen
M1-selected context within the same fold:

| Dominant VM | Log-space IQR rank | IQR / cohort median |
| --- | --- | --- |
| T1 VM266 | 33–34/35 | approximately 7.86–8.19× |
| T3 VM272 | 35/35 | approximately 7.59–7.75× |

Both have the largest native disk-write IQR in every fold. The text states:
“Unusually small training IQRs are therefore not supported as an explanation
for these tails.” It expressly does not establish that large scale caused
the errors or that sharing is causal.

Main Results and the Table S2 caption/note define **stable** as **“no sign flip
across the three recorded seeds”**. They explicitly distinguish sign from
magnitude stability, using the stored T3 M1:S2 disk gains **−54.65%, −71.55%,
−87.84%**. No new interval, test, seed or estimand was introduced. All 24/48
supplementary data rows and 312 underlying numeric strings remain identical.

The abstract and Introduction now explain that median M1 matched-cell MAE
ratios are **close to one in many comparisons**, while some larger MacroMAE
penalties are tail-concentrated. Per-entity consolidation is presented as a
target-specific accuracy/consolidation trade-off, with adverse tails still
requiring assessment. The abstract contains **228 words** and does not use
the undefined word “small”. The post-hoc, persistence and non-causal bounds
are retained.

Results §5.1 now states that memory S2:S1 gains in **fastStorage, Rnd, Materna
T2 and T3 are positive in all three recorded seeds**. TimeTrack/T1 and
model-family qualifications remain; no universal-memory claim is added.

Table 3 retains exact-source TimeTrack memory gains **−18.476885757816117%
(H64)** and **−18.484754219705916% (H129)**, both displayed as **−18.48%**.
The new note explains that they are distinct before rounding. Every numeric
table row is byte-identical to the predecessor.

## Verification and builds

- Scale ranks/ratios were checked against H1's existing records; the seed
  statements/example against G1's stored seed table. These are source checks,
  not new scientific analysis. The interpretation agrees with C1/G1/G2/H1.
- Main and supplement cached-only Tectonic builds succeed: **18 double-column
  manuscript pages; 3 supplement pages**, unchanged from the predecessor.
- Zero unresolved references/citations or duplicate labels. Supplementary S1/S2
  identifiers resolve to the same compiled tables. All page layouts were
  inspected, with full-page review of the abstract, Introduction, §§5.1–5.2,
  Table 3 note and complete seed table. No new clipping, table overflow or
  overfull body text remains. Figures and table fonts were not reduced.
- Existing non-fatal CAS front-matter/empty-anchor, underfull-line, PDF-version
  and two bibliography empty-pages warnings remain. No integration blocker.
  Separate submission-readiness housekeeping is not certified by this stage.
- Protected membership remains **395,787**. The after-scan verifies **395,784**
  files unchanged, allowing only the three source edits above. All 25 C1,
  19 G1, 47 G2 and 10 H1 output hashes are reverified. Refs/branch are unchanged,
  the index has no staged changes, and `git diff --check` passes.

The final PDFs are `build/manuscript.pdf` and
`build/supplement/final_evidence_supplement.pdf` in this evidence directory.
The historical root PDF and all prior audit outputs are untouched.
`verification.json`, `visual_signoff.json` and the input/output SHA-256
inventories bind the final source, PDFs and checks.

Scientific modifications=0; commit=no; push=no.

STAGE_19H2A_PASS
