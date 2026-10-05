# Phase 4C External Scientific Decision Criteria

Date frozen: 2026-09-30 (Europe/Helsinki)  
Parent checkpoint: `b162b8907f5f063ef969c02bd5d175edd3471028`  
Parent tag: `phase4b-bitbrains-factorial-protocol-freeze-v1`

This decision record was written and hashed before the first Bitbrains
scientific model fit and before any Bitbrains scientific outer-test prediction,
comparison, gain, or H1/H2/H3 result existed. It cannot be changed after
scientific execution starts.

The primary statistic is the ratio of matched macro MAEs. For each environment,
comparison, and resource, the overall primary gain is
`100 * (MacroMAE_reference - MacroMAE_candidate) / MacroMAE_reference` after
seed averaging within VM/fold/resource/lead and equal weighting of VM-fold
cells. Horizon, VM, fold, and seed-level signs are computed from their matched
aggregates under the frozen Phase 4B aggregation rules.

## Resource-level consistency labels

### BROAD_POSITIVE

All conditions are required:

- overall primary gain is at least +1.0%;
- at least 4 of 5 horizon gains are positive;
- at least 25 of 35 VM gains are positive;
- at least 4 of 5 fold gains are positive;
- at least 2 of 3 seed-level aggregate gains are positive.

### CONDITIONALLY_POSITIVE

All conditions are required, and `BROAD_POSITIVE` must not apply:

- overall primary gain is greater than 0%;
- at least 3 of 5 horizon gains are positive;
- at least 15 of 35 VM gains are positive;
- at least 3 of 5 fold gains are positive;
- at least 2 of 3 seed-level aggregate gains are positive.

### BROAD_NEGATIVE

All conditions are required:

- overall primary gain is at most -1.0%;
- at most 1 of 5 horizon gains is positive;
- at most 10 of 35 VM gains are positive;
- at most 1 of 5 fold gains is positive;
- at most 1 of 3 seed-level aggregate gains is positive.

### NEUTRAL_OR_MIXED

Every case not satisfying one of the three definitions above is
`NEUTRAL_OR_MIXED`.

These thresholds are proportionally adapted from the frozen TimeTrack
consistency logic to 35 VMs and five external horizons. They are descriptive
consistency labels, not significance tests. Bootstrap intervals cannot change
these labels.

## Per-environment S2-versus-S1 decision

Assign `CROSS_RESOURCE_INPUT_SUPPORTED` when all are true:

- at least 3 of 4 resources are `BROAD_POSITIVE` or
  `CONDITIONALLY_POSITIVE`;
- equal-resource mean primary gain is positive;
- at most one resource is `BROAD_NEGATIVE`.

Assign `CROSS_RESOURCE_INPUT_NOT_SUPPORTED` when either is true:

- at most 1 of 4 resources is positive and equal-resource mean primary gain is
  nonpositive; or
- at least 2 of 4 resources are `BROAD_NEGATIVE`.

Otherwise assign `CROSS_RESOURCE_INPUT_MIXED`.

## Per-environment M1-versus-S2 decision

Assign `SHARED_REPRESENTATION_SUPPORTED` when all are true:

- at least 3 of 4 resources are `BROAD_POSITIVE` or
  `CONDITIONALLY_POSITIVE`;
- equal-resource mean primary gain is positive;
- no resource is `BROAD_NEGATIVE`.

Assign `SHARED_REPRESENTATION_CONDITIONALLY_SUPPORTED` when all are true:

- equal-resource mean primary gain is positive;
- at least 2 of 4 resources are positive;
- the full supported criteria do not apply.

Assign `SHARED_REPRESENTATION_NEGATIVE_TRANSFER` when at least one resource is
positive and either at least two resources are materially negative or
`BROAD_NEGATIVE`, or strong target-specific trade-offs are present.

Assign `SHARED_REPRESENTATION_NOT_SUPPORTED` when at most 1 of 4 resources is
positive and equal-resource mean primary gain is nonpositive.

When rules overlap, use the most conservative applicable label and record the
overlap and reason.

## Cross-environment H1 logic

Assign `H1_BOUNDARY_CONFIRMED` when:

- neither environment is `CROSS_RESOURCE_INPUT_SUPPORTED`;
- the equal-environment mean of the four resource-specific primary gains is
  nonpositive overall; and
- no more than one resource has positive equal-environment synthesized gain.

Assign `H1_BOUNDARY_PARTIALLY_REPLICATED` when neither environment is
`CROSS_RESOURCE_INPUT_SUPPORTED`, but synthesized evidence is mixed or weakly
positive.

Assign `H1_BOUNDARY_NOT_REPLICATED` when at least one environment is
`CROSS_RESOURCE_INPUT_SUPPORTED` and external synthesis shows broad positive
cross-resource benefit.

## Cross-environment H2 logic

Assign `H2_BOUNDARY_CONFIRMED` when:

- neither environment is `SHARED_REPRESENTATION_SUPPORTED`;
- equal-environment mean M1-versus-S2 gain is nonpositive; and
- no more than one resource has positive synthesized gain.

Assign `H2_BOUNDARY_PARTIALLY_REPLICATED` when neither environment is fully
supported, but sharing evidence remains mixed.

Assign `H2_BOUNDARY_NOT_REPLICATED` when at least one environment is
`SHARED_REPRESENTATION_SUPPORTED` and synthesized evidence is broadly positive.

## Cross-environment H3 logic

Assign `HETEROGENEITY_CONFIRMED` when benefits materially differ across
resources, VMs, horizons, or environments and no broad, consistently positive
context effect dominates both environments.

Assign `HETEROGENEITY_WEAK_OR_MIXED` when some heterogeneity exists but the
patterns are limited.

Assign `HETEROGENEITY_NOT_REPLICATED` when effects are broadly consistent in
sign and magnitude across both environments.

These are confirmation labels for the frozen TimeTrack boundary questions.

## Final Phase 4C outcome

- `BOUNDARY_CONFIRMED_ACROSS_BOTH_ENVIRONMENTS`: H1 and H2 are confirmed and
  H3 is confirmed or otherwise consistent with the boundary study.
- `BOUNDARY_PARTIALLY_REPLICATED`: one or more TimeTrack boundary conclusions
  replicate but external evidence is materially mixed.
- `EXTERNAL_EVIDENCE_CONTRADICTS_TIMETRACK_BOUNDARY`: external data show broad,
  reproducible benefits from cross-resource input and/or naive sharing.
- `ENVIRONMENT_DEPENDENT_BOUNDARY`: fastStorage and Rnd give materially
  different scientific conclusions.
- `EXTERNAL_CONFIRMATION_INCONCLUSIVE`: evidence does not support a clear
  preceding outcome.

The outcome is selected by these definitions, never by publication preference.

## Confirmatory uncertainty

For each environment separately, use a paired VM-cluster bootstrap with 10,000
replicates. Each replicate samples 35 VMs with replacement, retains all five
folds for every sampled VM, retains paired formulation results and the
seed-averaged matched structure, computes formulation macro MAEs, and computes
the relative gain from the macro-MAE ratio. Report 2.5th and 97.5th percentile
intervals for every comparison/resource/lead and every comparison/resource
overall. No p-value fishing is permitted, and bootstrap intervals do not alter
the classification thresholds.

## Publication-scope gate

- `MULTIDATASET_BOUNDARY_STUDY_SUPPORTED`: independent Bitbrains evidence
  meaningfully replicates the central TimeTrack boundary—cross-resource/context
  benefit is limited, inconsistent, or environment/resource dependent, and
  naive sharing is not broadly advantageous.
- `MULTIDATASET_BOUNDARY_STUDY_SUPPORTED_WITH_MIXED_REPLICATION`: some central
  boundary findings replicate but important Bitbrains results contradict
  TimeTrack.
- `TIMETRACK_BOUNDARY_NOT_EXTERNALLY_SUPPORTED`: Bitbrains broadly and
  consistently shows benefits that contradict the TimeTrack conclusion.
- `EXTERNAL_RESULTS_INCONCLUSIVE`: Bitbrains itself is too inconsistent to
  support either boundary or contradiction.

## Materna recommendation

- `MATERNA_NOT_NEEDED`: both Bitbrains environments provide sufficiently clear
  primary replication.
- `MATERNA_USEFUL_SECONDARY_REPLICATION`: Bitbrains evidence is meaningful but
  environment heterogeneity would benefit from another temporal dataset.
- `MATERNA_NEEDED_FOR_RESOLUTION`: fastStorage and Rnd materially conflict.

Materna is not executed in Phase 4C.
