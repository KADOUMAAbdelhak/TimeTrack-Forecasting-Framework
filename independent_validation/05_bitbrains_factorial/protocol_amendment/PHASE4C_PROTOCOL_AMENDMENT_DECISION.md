# Phase 4C Prospective Protocol-Amendment Decision

Date frozen: 2026-10-05 (Europe/Helsinki)

## Decision

`REVISE_ENTITY_ELIGIBILITY_AND_RESELECT`

This decision is prospective. It is adopted before any valid external Phase 4C
scientific result exists and does not authorize scientific execution.

## Reason

Zero-IQR training partitions are broadly present in Bitbrains and violate the
frozen median/IQR robust-scaling requirement. The completed training-only audit
found that approximately 35% of each structurally eligible pool fails the
strict all-partition criterion. THROUGHPUT is the most frequent source, and the
failure is not meaningfully concentrated by fold, inner/final phase, or context.

Changing scaler semantics would change normalized optimization and could alter
the equal-resource balance of M1. Dropping or conditionally masking resources
would change the frozen four-resource factorial and M1 loss. Deterministic
entity reselection is therefore the least semantically disruptive amendment.

## Amended eligibility and deterministic selection

A scientific-confirmation VM must satisfy the original Phase 4A structural
eligibility rule and `TRAINING_SCALE_ELIGIBLE`: every transformed resource must
have training IQR greater than zero in every unique scaler partition keyed by
`(environment, VM_ID, fold, phase, L)`. There are 30 partitions per VM: five
folds, two training phases, and contexts 4, 9, and 18.

After this binary filter, cohorts are selected by the unchanged ascending
SHA-256 ranking of `phase4a-v1|<environment>|<exact-VM-ID>`. No new salt,
outcome, variance magnitude, correlation, persistence, support-size
optimization, or model result enters selection.

## Preserved scientific semantics

The amendment preserves target semantics, all four resources, transformations,
the no-fallback robust scaler, S1/S2/M1 architectures, common support, folds,
horizons, contexts, equal M1 loss, training lifecycle, aggregation, paired
VM-cluster bootstrap, and the frozen H1/H2/H3 criteria.

The only scientific change is the eligible population and its deterministically
selected cohort.

## Population consequence

External confirmation no longer targets every structurally valid Bitbrains VM.
It targets structurally valid Bitbrains VMs with nondegenerate four-resource
training variability in every scientific scaler-fit partition. This excludes a
substantial idle, quiescent, or resource-constant portion of the structural
population and must be stated in every future interpretation.

## Outcome independence and timing

This amendment used no outer-test target values, outer-test predictions,
forecasting performance, persistence performance, or S1/S2/M1 outcome. It
predates all valid external scientific results. The 154 interrupted
pre-amendment inner fits are retained only as aborted provenance and cannot be
reused under the amended identity.
