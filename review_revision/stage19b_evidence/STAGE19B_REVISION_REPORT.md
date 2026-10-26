# Stage 19B — framework and methodology alignment

STAGE_19B_PASS. Branch: `paper/jss-review-revision`. HEAD: `f6936cd111d911e40ec2725a18fdfc53768d9ccf`. Commit=no; push=no.

## Scope

Only manuscript source edited: `manuscript/jss/manuscript.tex`, Sections 3–4 and the associated framework caption. The user additionally authorised replacing the single internal R4 label in Results §5.4 with “Temporal heterogeneity confirmed”. Every other byte from Results through EOF is unchanged from Stage19A. All front matter, Abstract, Introduction and Related Work are byte-identical to Stage19A. Figures, table sources, bibliography and supplement remain unchanged.

## Methodological corrections

- Replaced affirmative factorial descriptions with three matched operational formulations/comparisons; retained the explicit incomplete 2×2-design limitation. Remaining occurrences elsewhere explicitly deny factorial isolation.
- Defined entity-specific models and the per-entity × outer-fold × seed four-target complement: four independent S1/S2 networks versus one joint M1 network, without pooling across machines/VMs. Distinguished this inventory from candidate-context fits and final refits.
- Distinguished transformed/robust-scaled MSE training and early stopping; transformed/scaled validation MAE context selection at each seed’s MSE-selected epoch; and native-unit MAE/MacroMAE evaluation after inversion/projection. Native NMAE now explicitly divides by native outer-training IQR, using a distinct symbol from the transformed scaler IQR.
- Defined M1 as the arithmetic mean of four scaled resource MSEs, without implying equal realised loss or gradient contributions. RQ2 now asks about the implemented shared-LSTM comparison; RQ1–RQ4 numbering is retained.
- Located parameter inventories at the local target complement: external S2/M1 206,100/52,500 and TimeTrack 206,880/53,280. Defined summed successful worker fit-hours, inner/final coverage and exclusions; ruled out interpreting them as elapsed wall time, energy or deployment latency/cost. Epoch/context differences, rather than input width alone, qualify S1/S2 timing interpretation.
- Exposed the frozen broad-positive, conditionally-positive, broad-negative and neutral/mixed rules, including TimeTrack/external count thresholds and strict-positive semantics. Distinguished point signs, consistency classes and bootstrap intervals; full trace/RQ predicates remain unchanged in the supplement/protocol.
- Added §4.11, explicitly post-hoc, describing S2 common-context restrictions/reuse, H129 approximate aggregate capacity matching with fresh inner selection, and deterministic matched-context Ridge AR/ARX with nested five-alpha selection on native validation MAE. Stated each control’s scope and residual confounds without reporting performance results. Evaluation remains §4.8, preserving existing cross-references.

## Verification

Desktop compilation succeeded. Independent Tectonic compilation succeeded, including a final cached-only rebuild: **19 pages**, no undefined references/citations or rerun request. Changed pages 4–12 and the authorised label on page 14 were visually checked without clipping or overlap. A missing small-caps font was retrieved by the compiler; no manuscript dependency was edited. Existing CAS empty-anchor/overfull warnings, underfull spacing warnings, and two bibliography empty-pages warnings remain non-blocking and are outside the authorised content corrections.

Full SHA256 preservation verified **395,784 protected files unchanged**, excluding only the explicitly authorised manuscript source; membership and Git refs are unchanged. All 25 inventoried Stage18C1 evidence outputs also match. Scientific modifications=0; training=0; inference=0. Exact before/after source hashes, scope assertions and build checks are in `verification.json`; executable audit code is `verify_revision.py`.

The revised build is `build/manuscript.pdf` in this evidence folder. Historical `manuscript/jss/manuscript.pdf` and build artifacts were preserved. No new experiment, statistic, result-table update or downstream prose revision was performed. Later Results/Discussion integration remains a separately authorised stage, not a blocker to these methodology corrections.
