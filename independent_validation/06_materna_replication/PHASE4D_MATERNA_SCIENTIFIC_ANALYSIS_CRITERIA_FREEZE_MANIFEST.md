# Phase 4D Materna Scientific-Analysis Criteria Freeze Manifest

Date: 2026-10-14 (Europe/Helsinki)

**THESE ANALYSIS AND DECISION RULES WERE FROZEN AFTER TECHNICAL EXECUTION BUT BEFORE FIRST SCIENTIFIC INSPECTION OF MATERNA PREDICTIVE RESULTS.**

## Checkpoint and protected identities

- Execution checkpoint: `dba05d2505e91170f7d4de69027f4692e5b30584` (`phase4d-materna-three-trace-execution-freeze-v1`)
- Execution-conformance checkpoint: `5e7a42acf47dc0f14a73e7188c17831629f2229d` (`phase4d-materna-execution-conformance-freeze-v1`)
- Scientific-protocol checkpoint: `c4077318bfbb02e112b439baa3ae7a0e35db0dc5` (`phase4d-materna-secondary-replication-protocol-freeze-v1`)
- Materna config SHA-256: `064ef5a4864f5590b8149242c4011c37a49aee35cf60a4690f6aa126b98fce27`
- Heavy execution inventory SHA-256: `8484e62b2dae596ece90308c18ea617ec904ea55ceb4fbfc76e2fcaa55dd1718`
- Execution-tree SHA-256: `3d9a6ffe1b7d520bc5ca0e3f36e147f39e87590c88f8289a26c962a09e6756e1`
- Compact execution-checkpoint inventory SHA-256: `ba7e4e3cc39b6d3a9318db6e27573a41edc115e654ef82866ec9a080b5065d84`
- Execution-checkpoint tree SHA-256: `abb816d612d9ab84d9bd118536e74793d4556b1258995c612efc6382c977248d`
- Scientific-analysis criteria SHA-256: `19345874ff91474f8ef414e4240886630a4864d8d7dcd824b9427a49147eeca4`

The heavy execution inventory remains `141785 / 141785 PASS`. The checkpoint was prepared using criteria, Git identities, technical summaries, file names, byte sizes, and hashes only. No Materna formulation MAE, persistence value, prediction value, gain, bootstrap result, temporal synthesis, or scientific figure was opened or calculated.

## Rationale and analysis boundary

The scientific rules are fixed after execution so the completed data products and their exact identities can be protected, but before result inspection so observed directions or magnitudes cannot influence aggregation, classifications, decision thresholds, or claim gates. The primary estimator is inherited unchanged from Phase 4C. Materna's three temporal blocks are analyzed independently and synthesized with equal block weight; they are not treated as independent datasets.

At freeze time: gains calculated `0`; bootstrap executed `0`; R1/R2/R3/R4 evaluated `no`; predictive metric values scientifically inspected `no`; scientific figures `0`.

## Primary and secondary aggregation

Within each trace, VM, fold, resource, lead, and formulation, average native MAE over the three seeds. Give every VM-fold cell equal weight to obtain lead-specific MacroMAE. Resource-overall MacroMAE is the equal mean over the five lead-specific MacroMAEs. Do not pool individual prediction samples for primary conclusions.

Primary gain is `100 * (baseline MacroMAE - candidate MacroMAE) / baseline MacroMAE`:

- S2 vs S1: `100 * (S1 - S2) / S1`
- M1 vs S2: `100 * (S2 - M1) / S2`
- M1 vs S1: `100 * (S1 - M1) / S1`

Secondary diagnostics are pooled prediction-level MAE gain, mean and median matched VM-fold cell-relative gain, and positive VM-fold fraction. Any primary/secondary sign reversal must be reported, but secondary diagnostics cannot replace the primary estimator.

Positive consistency counts are computed per trace/comparison/resource: horizons `0-5`, VMs `0-35`, folds `0-5`, and seeds `0-3`. VM signs aggregate folds and horizons first; fold signs aggregate VMs and horizons first; seed signs aggregate VMs, folds, and horizons first.

## Frozen resource classifications

- `BROAD_POSITIVE`: overall gain at least `+1.0%`, at least `4/5` positive horizons, `25/35` positive VMs, `4/5` positive folds, and `2/3` positive seeds.
- `CONDITIONALLY_POSITIVE`: not broad positive, overall gain greater than `0`, at least `3/5` positive horizons, `15/35` positive VMs, `3/5` positive folds, and `2/3` positive seeds.
- `BROAD_NEGATIVE`: overall gain at most `-1.0%`, at most `1/5` positive horizons, `10/35` positive VMs, `1/5` positive folds, and `1/3` positive seeds.
- Everything else: `NEUTRAL_OR_MIXED`.

The thresholds cannot change. A positive resource means `BROAD_POSITIVE` or `CONDITIONALLY_POSITIVE`. A materially negative resource has overall primary gain at most `-1%`. Strong target-specific trade-offs require a maximum resource gain of at least `+1%` and a minimum resource gain of at most `-1%`.

## Frozen trace decisions

For S2 vs S1:

- `CROSS_RESOURCE_INPUT_SUPPORTED`: at least three positive resources, positive equal-resource mean gain, and at most one broad-negative resource.
- `CROSS_RESOURCE_INPUT_NOT_SUPPORTED`: at most one positive resource with nonpositive equal-resource mean, or at least two broad-negative resources.
- Otherwise `CROSS_RESOURCE_INPUT_MIXED`.

For M1 vs S2:

- `SHARED_REPRESENTATION_SUPPORTED`: at least three positive resources, positive equal-resource mean, and zero broad-negative resources.
- `SHARED_REPRESENTATION_CONDITIONALLY_SUPPORTED`: positive equal-resource mean, at least two positive resources, and full support fails.
- `SHARED_REPRESENTATION_NEGATIVE_TRANSFER`: at least one positive resource with at least two broad/materially negative resources, or strong target-specific trade-offs.
- `SHARED_REPRESENTATION_NOT_SUPPORTED`: at most one positive resource and nonpositive equal-resource mean.

Overlaps use conservative precedence: negative transfer, not supported, supported, conditionally supported. Any otherwise uncovered state is conservatively `SHARED_REPRESENTATION_NOT_SUPPORTED` with reason `residual_no_support`.

For M1 vs S1, `JOINT_SYSTEM_BROADLY_BENEFICIAL` requires at least three positive-gain resources and a positive equal-resource mean; `JOINT_SYSTEM_BROADLY_HARMFUL` requires at least three negative-gain resources and a negative mean; otherwise use `JOINT_SYSTEM_MIXED`. This label is used only for R3.

## Temporal synthesis and uncertainty

For each comparison/resource/lead and each comparison/resource overall, calculate `(T1 gain + T2 gain + T3 gain) / 3` and label it `EQUAL_TEMPORAL_BLOCK_SYNTHESIS`. Report T1, T2, T3, synthesis, sign pattern, and maximum-minus-minimum spread together. Never weight by rows, origins, predictions, duration, or fit count, and never describe this as an independent-dataset meta-analysis.

Bootstrap each trace separately with paired VM-cluster resampling: draw 35 VMs with replacement, retain all five folds, preserve formulation pairing, and use seed-averaged matched MAEs. Use `10000` percentile replicates and `[2.5, 97.5]` intervals for every trace/comparison/resource/lead and resource overall. The deterministic Phase 4C seed `20261007` is reused. Do not bootstrap traces as independent observations and do not construct a nominal temporal-synthesis interval.

Persistence remains a separate absolute forecasting sanity check at trace/resource/lead scope using MAE, RMSE, R², NMAE, and formulation persistence skill. It cannot redefine R1-R4. Reports must state that relative formulation improvements do not imply absolute superiority over persistence.

## Frozen R1-R4 rules

R1 precedence is broad benefit, temporal dependence, not supported, mixed/inconclusive.

- `R1_BROAD_CROSS_RESOURCE_BENEFIT`: at least 2/3 traces support cross-resource input, the mean of four synthesized resource gains is positive, and at least 3/4 synthesized resources are positive.
- `R1_RESOURCE_TEMPORAL_DEPENDENCE_CONFIRMED`: broad benefit fails and trace decisions differ, at least two resources change sign, or at least two resources change frozen class.
- `R1_CROSS_RESOURCE_INPUT_NOT_SUPPORTED`: no trace supports it, the four-resource synthesized mean is nonpositive, at most one synthesized resource is positive, and temporal dependence does not dominate.
- Otherwise `R1_MIXED_OR_INCONCLUSIVE`.

R2 precedence is negative replication, mixed effect, benefit replication, inconclusive.

- `R2_NEGATIVE_SHARING_REPLICATED`: zero supported traces, at most one conditionally supported trace, nonpositive four-resource synthesized mean, and at most one positive synthesized resource.
- `R2_MIXED_SHARING_EFFECT`: no supported trace but synthesized evidence contains material positive and negative effects, mechanically at least one synthesized gain at least `+1%` and one at most `-1%`.
- `R2_SHARING_BENEFIT_REPLICATED`: at least 2/3 traces are supported or conditionally supported, the four-resource mean is positive, and at least 3/4 synthesized resources are positive.
- Otherwise `R2_INCONCLUSIVE`.

R3 precedence is replicated underperformance, partial underperformance, benefit, mixed/inconclusive.

- `R3_JOINT_SYSTEM_UNDERPERFORMANCE_REPLICATED`: all four synthesized M1-vs-S1 resource gains are negative and at least 2/3 traces are broadly harmful.
- `R3_JOINT_SYSTEM_PARTIAL_UNDERPERFORMANCE`: synthesized mean is nonpositive, at most two synthesized resources are positive, and full replication fails.
- `R3_JOINT_SYSTEM_BENEFIT`: at least three synthesized resources are positive, synthesized mean is positive, and at least two traces are broadly beneficial.
- Otherwise `R3_MIXED_OR_INCONCLUSIVE`.

For R4, a resource/comparison is `TEMPORALLY_CLASSIFICATION_VARIABLE` when its frozen class differs across T1/T2/T3. `R4_TEMPORAL_HETEROGENEITY_CONFIRMED` requires at least two variable resource/comparison combinations or differing S2-vs-S1 or M1-vs-S2 global trace decisions. `R4_TEMPORAL_HETEROGENEITY_WEAK` requires exactly one variable combination with identical global decisions. `R4_TEMPORAL_HETEROGENEITY_NOT_SUPPORTED` requires no variable combinations and identical global decisions. Raw sign reversal is reported separately; post-hoc regime mining is forbidden.

## Cross-study, paper-scope, and stop gates

Cross-study synthesis compares TimeTrack; Bitbrains fastStorage, Rnd, and the frozen equal-environment synthesis; and Materna T1, T2, T3, and equal-temporal-block synthesis. It is descriptive plus direction/classification consistency. No pooled numeric score may combine these sources because dataset roles, dependence, and sample structures differ.

The exact cross-resource, shared-representation, and joint-system claim gates are encoded in the criteria JSON. Their labels are, respectively: `CROSS_RESOURCE_BOUNDARY_STRENGTHENED/MIXED/NOT_SUPPORTED`; `SHARED_REPRESENTATION_BOUNDARY_STRENGTHENED/MIXED/NOT_SUPPORTED`; and `JOINT_SYSTEM_UNDERPERFORMANCE_STRENGTHENED/PARTIAL/NOT_REPLICATED`.

The final paper-scope labels are `MULTIDATASET_TEMPORAL_BOUNDARY_STUDY_STRONGLY_SUPPORTED`, `MULTIDATASET_TEMPORAL_BOUNDARY_STUDY_SUPPORTED`, `MULTIDATASET_BOUNDARY_STUDY_REQUIRES_QUALIFICATION`, and `MULTIDATASET_BOUNDARY_STUDY_NOT_SUPPORTED`. Publication desirability cannot influence selection.

After coherent R1-R4 results and passing execution/analysis validation with no unresolved protocol defect, select `STOP_EXPERIMENTATION_AND_WRITE`, regardless of result direction. `ADDITIONAL_EXPERIMENT_REQUIRED` is allowed only for a genuine methodological defect invalidating a required conclusion; inconvenient results are not such a defect.

## Independent zero-result validation

`validate_phase4d_analysis_criteria.py` validates the JSON structure, frozen constants and thresholds, deterministic rule precedence and label reachability, frozen Git/config identities, the complete heavy and compact execution inventories, and absence of comparison/bootstrap/figure artifacts. It never parses a Materna metric, persistence, or prediction table and records the result in `PHASE4D_MATERNA_SCIENTIFIC_ANALYSIS_CRITERIA_VALIDATION.json`.
