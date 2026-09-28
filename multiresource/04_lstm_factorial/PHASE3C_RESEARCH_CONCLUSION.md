# Phase 3C Research Conclusion

## Decision record

Phase 3C completed and independently validated the frozen plain-LSTM S1/S2/M1
factorial. Its primary next-direction decision is:

**MULTI_RESOURCE_FORECASTING_PREMISE_WEAK**

Cross-resource input augmentation was not broadly beneficial under the tested
plain-LSTM formulation. S2 improved only memory overall (+0.8594%) and degraded
CPU (-3.3130%), throughput (-0.2428%), and disk-write (-0.4923%) relative to
S1. Plain shared multi-task M1 improved CPU only slightly relative to S2
(+0.4696%) while degrading throughput (-0.8401%), memory (-18.4769%), and
disk-write (-0.7956%). Relative to S1, M1 was worse for every resource.

Resource-specific negative transfer is descriptively present, especially for
memory. This does not establish a causal failure mechanism. In particular, the
scientific CPU loss share was 48.24%, compared with approximately 81-84% in the
non-scientific pilot, so the preliminary CPU-majority loss pattern did not
persist at the same magnitude. The evidence does not justify claiming that
simple numerical CPU loss domination primarily caused M1's failure.

M1 supplies a 74.25% parameter reduction and 75% inference model-count
reduction relative to S2. That footprint advantage is real, but it does not
compensate scientifically for the accuracy degradation. Accuracy and efficiency
remain separate conclusions.

## Architecture escalation boundary

Phase 3C does **not** support immediately proceeding to:

- adaptive task weighting;
- selective fusion;
- shared/private representation;
- cross-resource attention;
- larger multi-task networks;
- PatchTST multi-resource; or
- another architecture escalation.

The S2-versus-S1 experiment shows that additional cross-resource input itself
is not broadly useful under the tested setting. An architecture designed only
to improve cross-resource sharing therefore lacks sufficient current empirical
motivation. Adaptive loss weighting is not justified automatically from these
results, and no new architecture is selected or implemented in this checkpoint.

This result does not prove that multi-resource forecasting is universally
impossible. It establishes a boundary for this dataset, these four target
definitions, these forecast horizons, this common-support construction, this
plain-LSTM factorial, and the evaluated period.

## Post-Phase3C Evaluation Independence

The five outer folds have now been used to obtain scientific evidence for S1,
S2, and M1. Any future architecture designed in response to these Phase 3C test
results is **post-hoc** with respect to those folds. Those same folds must not
be presented as an untouched confirmatory evaluation for a newly designed
method.

A future proposed architecture requires one of:

- an untouched temporal holdout not used in Phases 1-3;
- newly collected TimeTrack telemetry;
- an external compatible dataset; or
- another genuinely independent evaluation source.

Existing folds may still be used for exploratory or mechanistic development
if they are explicitly labelled as such.

## Next action

**POST-HOC HETEROGENEITY + RESEARCH-DIRECTION AUDIT**

No training is authorized by this recommendation. The audit should use the
existing S1/S2/M1 predictions to determine whether stable subgroups exist where
cross-resource information is useful and whether an evidence-supported new
hypothesis remains. It must not select or implement a new architecture during
this checkpoint.
