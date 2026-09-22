# Prospective Matched-F0 Comparator Decision

Decision date: 2026-09-22 (Europe/Helsinki)

Repository state at decision:

- Current HEAD: `0b4269270b0a121f0ba1e19355c6cd24b72abeb5`
- Phase 2A freeze commit: `0b4269270b0a121f0ba1e19355c6cd24b72abeb5`
- Phase 2A freeze tag: `phase2a-benchmark-protocol-freeze-v1`
- Original Phase 2B-1 preservation manifest:
  `benchmark/phase2b1_original/ORIGINAL_PHASE2B1_MANIFEST.md`

## Ambiguity being resolved

The frozen protocol requires a candidate-matched F0 reference on the exact
context feature's train and test rows. It does not explicitly state whether
the matched F0 comparator must repeat configuration selection on the
candidate's exact inner-training and inner-validation support, or whether the
standalone F0 configuration can be reused before an exact-row final refit.

## Prospective decision

For every contextual feature-set comparison F1-F5, candidate-matched F0 must
use exactly the contextual candidate's:

- inner-training sample IDs;
- inner-validation sample IDs;
- final outer-training sample IDs;
- outer-test sample IDs.

Configuration selection is independently repeated for F0 using those exact
matched inner-training and inner-validation rows. The frozen model-specific
configuration grid, eight-lead mean inner-validation MAE objective, and frozen
tie-breaking rule remain unchanged.

After selection, matched F0 is refit using exactly the candidate's final
outer-training rows and evaluated once using exactly the candidate's
outer-test rows.

The contextual candidate retains its already valid selected configuration,
predictions, and metrics. No contextual candidate is rerun. Standalone F0
results remain unchanged. Persistence requires no fitted correction.

This is a prospective interpretation of an ambiguous comparator clause, not a
retrospective modification based on observed corrected results. No corrected
matched-F0 comparator results existed when this decision was recorded.
