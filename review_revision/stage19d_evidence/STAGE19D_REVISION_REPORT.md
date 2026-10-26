# Stage 19D revision report

Status: STAGE_19D_PASS

## Scope and changes

Only `manuscript/jss/manuscript.tex` changed in this stage, within Discussion,
Threats to Validity and Conclusion. The source before Discussion and from
Data availability onwards is byte-identical to the Stage 19C version. All
section labels are preserved. Abstract, Introduction, Related Work, Methods,
Results, Cross-Dataset Synthesis, figures, tables, bibliography and supplement
are untouched by this stage.

- Discussion now separates selective contextual-input value from the operational
  sharing comparison. It explains model-family dependence, the separate
  common-context/H129 controls, typical-cell direction versus concentrated
  error magnitude, and the concentrated TimeTrack Ridge throughput penalty.
  It makes no causal-sharing or unmeasured production-benefit claim.
- Threats now acknowledge the completed controls without implying joint causal
  isolation. They include post-hoc selection, three-seed sign variation
  (9/24 S2:S1 and 4/24 M1:S2), Ridge's fixed contexts and finite alpha grid,
  persistence boundaries, MacroMAE versus typical-cell interpretation,
  dependent Materna blocks and non-IID inference limits.
- Conclusion states the bounded design-specific thesis: contextual value is
  selective; the evaluated shared LSTM consolidates local models while generally
  losing throughput/memory/disk accuracy; adverse point directions survive
  separate controls, without identifying sharing alone as the mechanism or
  rejecting all shared forecasting.

The writing-style guidance informed compact prose and removal of repetitive
defensive language. The PDF workflow informed final page rendering and visual
inspection.

## Numerical and consistency checks

Numerical prose is traced to the unchanged Stage 18C1 synthesis in
`verification.json`, including:

- all 24 M1:S2 block/resource median ratios above one and win rates below 50%;
- Materna T1/T3 disk medians rounded to 1.025/1.035;
- TimeTrack Ridge throughput gain −838.45%, machine06/fold3's 99.93% share of
  positive excess error, 21/35 improved pairs and median ratio 0.9963;
- the existing seed sign-variable counts and persistence limitations.

The existing 74.5% parameter and 75% model reductions remain restricted to the
original H64 external per-entity/fold/seed complement. H129 does not inherit
the H64 parameter-reduction claim. Worker fit-hours remain training workload,
not elapsed time, energy, cost or production savings. No new statistics,
training, inference or scientific analysis was performed.

## Build and preservation

- Tectonic: successful; desktop editor compiler: independently successful.
- PDF: 20 pages; final rendered pages 16–19 inspected and readable.
- Undefined references/citations: 0; new overfull lines: 0.
- Unresolved issues: no new blocking issue. Pre-existing CAS title-box,
  empty-anchor and underfull-box warnings remain, as do two empty-pages
  bibliography warnings (`Liu2024iTransformer`, `Nie2023PatchTST`). No edits
  outside the authorised sections were made to address them.
- Full SHA-256 audit: 395,785 protected files unchanged; membership of all
  395,786 protected files verified, with only the main source permitted to
  change. The historical baseline was overlaid with authorised Stage 19C
  asset hashes, not treated as permission for new asset changes.
- All 25 Stage 18C1 output hashes match. Git branch, HEAD and scientific refs
  are unchanged; no staged changes.

Source SHA-256 before:
`1194d9bb0fe85c07df499c5737e43fddc127b6a48d2bed00b7391230daa47915`

Source SHA-256 after:
`58c49d9793b4508d2190de62ea344698aafc35c1612e7e2263f31a6a764f2e2b`

Revised build: `build/manuscript.pdf`. Detailed audit: `verification.json`.
Reproducible read-only checks: `verify_revision.py`.

Scientific modifications=0; frozen artifacts modified=0; commit=no; push=no.

STAGE_19D_PASS
