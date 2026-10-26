# Stage 19F1 manuscript compression and consistency report

Status: STAGE_19F1_PASS

## Outcome and scope

The double-column manuscript is **17 pages, down from 20**. No font, margin,
figure, table, equation or spacing settings were reduced to reach the target.
Raw LaTeX source word count fell from 11,922 to 9,432; this is an editorial
source count, not a scientific statistic.

Edited sources:

- `manuscript/jss/manuscript.tex`
- `manuscript/jss/references.bib`

New evidence and build files are confined to this directory. The prior source
and full bibliography are retained under `before/`.

## Main compression and cleanup

Introduction now states the design question, contrasts, control overview and
bounded result once, pointing to the detailed protocol. Framework prose is
shorter around the unchanged equations. Methodology cross-references the
model-complement and refitting definitions instead of repeating them.

Results retains all detailed primary classifications, intervals, post-hoc
findings, persistence values and fit-hour totals. Repetitive interpretation is
shortened. Synthesis preserves source-specific comparisons; Discussion uses
cross-references for the Ridge outlier, sharing controls and consolidation
details. Threats retains residual confounds and uncertainty without restating
the protocol; Conclusion is a compact bounded thesis.

Hard-coded section numbers were replaced with existing label references.
Obsolete skeleton/future-workflow comments and the residual factorial wording
were removed. Contextual input and representation sharing are distinguished
consistently; shared-LSTM, MacroMAE, persistence skill, post-hoc sensitivity
controls, entity-specific models, worker fit-hours and dependent temporal
blocks retain their defined meanings. There are no internal R-stage/R4
implementation tokens or outdated wholly-uncontrolled-confound statements.

The writing-style guidance informed concise prose and cross-reference use.
The PDF workflow informed whole-document visual review.

## Bibliography audit

The initial 39 entries included five uncited keys. Four genuinely unused
entries were removed:

- `Bergmeir2018CrossValidation`
- `Islam2012Provisioning`
- `Toka2021KubernetesScaling`
- `Zeng2023LinearForecasting`

They have no remaining claim, method or experiment role and are recoverable
from `before/references.bib`. `Hochreiter1997LSTM` was retained as a relevant
foundational method reference and is now cited at the LSTM backbone definition.
This reuses an existing reference; no new reference was added. All original
cited keys remain represented, and all retained entry text is unchanged.
Final bibliography: **35 entries, all cited; no orphan entries**.

## Deliberately retained evidence

- Related Work and its seven-row evidence table are unchanged from Stage 19E.
- Abstract, keywords, author metadata/credits, funding and data availability
  are unchanged.
- All 14 equation environments, both figure environments/captions, every
  table source/artwork file, labels and section structure are preserved.
- Four contributions and four RQs, including their exact list text, are
  unchanged. Frozen classification predicates are unchanged.
- Dataset details, preprocessing, leakage control, horizons, evaluation and
  the detailed completed post-hoc protocols are not compressed away.
- Exact primary result narratives, post-hoc numerical findings, seed counts,
  persistence boundaries and fitting-workload totals remain. Every scientific
  numeric literal in the source is retained; only hard-coded section numbers
  were replaced. The typical-cell/magnitude distinction, separate-control
  limitations, non-causal interpretation, three-seed uncertainty, Ridge design
  limits, source dependence and population restrictions remain explicit.

## Build, visual and preservation checks

- Tectonic and independent desktop editor compiler: successful.
- Final PDF: 17 pages; every page rendered and inspected, including all five
  tables, both figures, equations, declarations and references.
- Undefined references/citations: 0. New overfull lines: 0.
- Remaining warnings are pre-existing CAS title-box/empty-anchor and underfull
  warnings, plus empty-pages fields for the two conference references
  `Liu2024iTransformer` and `Nie2023PatchTST`. No visible clipping was found;
  no unrelated metadata was invented to suppress these warnings.
- Full protected-tree SHA-256 audit: 395,784 files unchanged; all 395,786
  protected members accounted for, with only the two authorised source edits.
  Earlier authorised manuscript asset revisions were checked against their
  Stage 19C/19E hashes, not overwritten.
- All 25 Stage 18C1 output hashes match. HEAD, branch and scientific refs are
  unchanged; no staged changes. `git diff --check` passes.

Detailed checks and the retained-qualification ledger are in `verification.json`;
all-page inspection is recorded in hash-bound `visual_signoff.json`.

Scientific modifications=0; training/inference/new statistics=0;
commit=no; push=no.

STAGE_19F1_PASS
