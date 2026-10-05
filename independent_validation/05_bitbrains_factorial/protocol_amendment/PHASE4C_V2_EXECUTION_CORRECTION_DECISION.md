# Phase 4C V2 Execution-Conformance Correction Decision

Date: 2026-10-05 (Europe/Helsinki)

Classification: `IMPLEMENTATION_CONFORMANCE_CORRECTION`

This is **not** a scientific protocol amendment.

The frozen V2 protocol already requires every scientific artifact to reside
under `outputs/scientific_v2/`. The frozen runner correctly defines that output
root for completions, selections, metrics, loss histories, runtime records, and
validation, but two legacy literals still route final models and final
predictions through `outputs/scientific/`.

The frozen V2 execution contract also requires a successful final completion
record, written after the single authorized outer-test evaluation, to state
`outer_test_accessed=true`. Inner records correctly state false, but final
records omitted the field.

The correction therefore centralizes every V2 artifact path through the one V2
scientific root and makes outer-test access explicit in atomic completion
metadata. A final completion may be serialized only after final fitting,
authorized test evaluation, prediction persistence, and metric-record creation
have succeeded. A failure before test access cannot record true.

The correction changes artifact routing and provenance metadata only. It does
not change data, population, cohorts, training-scale eligibility, support,
predictions, model architecture, optimizer or training settings, context
selection, epoch lifecycle, transforms, scaling, physical inversion, metrics,
aggregation, bootstrap, scientific criteria, or H1/H2/H3.

At discovery and correction time, valid Phase 4C V2 fits were 0/37,800;
optimizer executions, V2 outer-test target accesses, and V2 predictions were
zero. No external predictive result had been inspected. The 154 pre-amendment
records remained preserved, scientifically non-reusable provenance.

This correction is therefore prospective with respect to every valid Phase 4C
V2 scientific outcome.
