# Stage 19C — Results and Cross-Dataset Synthesis

STAGE_19C_PASS. Branch `paper/jss-review-revision`; HEAD `f6936cd111d911e40ec2725a18fdfc53768d9ccf`. Scientific modifications=0; commit=no; push=no.

## Files and scope

Edited manuscript source: `manuscript/jss/manuscript.tex`, confined to Sections 5–6. Associated files: `figures/results_signed_matrix.py`, its generated PDF, and `tables/efficiency_summary.tex` (caption/header/notes only). Added `tables/posthoc_controls.tex`. All paths in this paragraph are under `manuscript/jss/`.

Front matter, Abstract, Introduction, Related Work and Methods are byte-identical to the Stage19B predecessor. Discussion through EOF is also byte-identical, including Threats, Conclusion and bibliography declarations. Figure 1, numerical result-table sources, bibliography and supplement are unchanged. The source predecessor hash matches Stage19B's recorded successor.

## Results and synthesis

- Retained original frozen S1/S2/M1 results as primary; labelled added controls and existing-artifact diagnostics POST-HOC.
- Integrated Ridge contextual-input evidence and the recurring but non-universal external-memory pattern. Included the existing 9/24 S2:S1 and 4/24 M1:S2 seed sign-flip counts without treating small point effects as stable gains or reversals.
- Integrated separate common-context and H129 sharing controls. Throughput, memory and disk-write point directions remain adverse across all six blocks under both controls, without identifying sharing alone as the cause.
- Added the existing matched-cell interpretation: all 24 original M1:S2 block/resource summaries have median ratio >1 and win rate <50%. T1/T3 disk median ratios 1.0246/1.0347 qualify the much larger MacroMAE penalties rather than implying uniformly severe VM-level degradation.
- Reported Ridge TimeTrack throughput −838.45% only with its CONCENTRATED_DEGRADATION diagnosis: machine06/fold3 contributes 99.93% of positive excess, ARX improves 21/35 machine/fold pairs and the median ratio is 0.9963. No implementation defect is demonstrated.
- Removed the six-block disk-write arithmetic mean headline without substituting a pooled global statistic. Retained frozen Bitbrains/Materna source summaries and Materna temporal dependence. Efficiency now uses local complements and summed successful worker fit-hours, not elapsed runtime, energy, deployment cost or production savings.

## Table, figure and traceability

One two-panel full-width table displays the requested 6×4 comparisons. All **120 displayed entries** independently match the appropriate authoritative CSV fields at declared two-decimal precision. `posthoc_table_trace.json` records each source SHA256, field, block/resource, exact stored string and display string; no MAE or gain was recomputed.

Figure 2 retains all **72 frozen values and printed labels**, verified against its predecessor PDF, unchanged decimal constants, frozen manifests and existing primary table. Only presentation changes: continuous symmetric asinh colour mapping, raw-percentage legend ticks, contrast-aware text, no clipping and no significance encoding. Colour and greyscale renders are legible. The frozen primary-gains and cross-study-synthesis table sources are byte-identical; efficiency numeric rows are unchanged.

Existing seed flags, 24 saved matched-cell summaries and the saved throughput diagnosis reconcile with the manuscript claims. No training, inference, bootstrap, extra seed, retuning, new endpoint or statistical analysis was run.

## Build and preservation

Tectonic and desktop compilation succeeded: **20 pages**, no unresolved references/citations. Pages 12–16, the full-width table and colour/greyscale figure were visually checked. Only pre-existing CAS/spacing and two bibliography empty-pages warnings remain; no new blocking issue was found. The build is `build/manuscript.pdf` in this evidence directory; historical manuscript-root build artifacts are preserved.

Full SHA256 audit: **395,781 protected files unchanged**, excluding only the four authorised existing manuscript assets; exactly one permitted manuscript table was added. All 25 inventoried Stage18C1 outputs and Git refs are unchanged. Exact scope, source hashes and checks are recorded in `verification.json` and `verify_revision.py`.
