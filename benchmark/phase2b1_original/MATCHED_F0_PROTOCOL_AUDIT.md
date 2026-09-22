# Matched-F0 Protocol Audit

## Frozen text

The controlling text is `benchmark/PROTOCOL.md`, lines 51-57:

> After outer/inner boundaries are fixed, each feature set applies its own
> finite-history mask. This avoids discarding valid F0 CPU samples merely
> because an excluded context channel is missing. Feature-value comparisons
> must use a candidate-matched F0 reference on the exact context feature's
> train/test rows; the standalone F0 result may additionally use all F0-valid
> rows. This matched-reference rule prevents context gains from being
> attributed to different missing-data samples.

Related selection text is at lines 91-109:

> Within each purged outer-training set, the chronologically latest 15% of
> origins is provisional inner validation.

> For each model family, feature set, machine, and outer fold: Ridge jointly
> selects L and alpha ... LightGBM jointly selects L and its frozen grid ...

The comparison rule at lines 193-197 says feature value compares F1-F5 with
F0 within the same model and that gains must not be attributed to architecture
when information differs. Neither `benchmark/configs/benchmark.json` nor
`benchmark/PHASE2A_FREEZE_MANIFEST.md` adds a more specific matched-F0
selection rule.

## Literal answers

### A. Exact candidate training rows

**YES.** The phrase "exact context feature's train/test rows" explicitly
requires the matched F0 comparator to be trained on the candidate's exact
training rows. Reusing a standalone F0 model trained on all F0-valid rows does
not satisfy this sentence.

### B. Exact candidate inner-validation rows

**AMBIGUOUS.** The protocol names exact "train/test rows" but does not say
whether `train` means only the final outer-training support or also both
partitions used during inner selection. Inner validation is described
separately as a subset of outer training, but the matched-reference paragraph
does not explicitly mention it.

### C. Exact candidate test rows

**YES.** Exact test-row matching is explicit. The original execution satisfies
this portion: every candidate test set is a subset of the corresponding
standalone F0 test set, and analysis aligns F0 predictions to exactly the
candidate origins and targets.

### D. Re-execute F0 configuration selection on candidate-matched inner data

**AMBIGUOUS.** The protocol requires configuration selection for each model
family and feature set, but does not explicitly define whether a
candidate-matched F0 comparator is a new comparator feature-set instance that
must repeat selection, or a refit using the already selected standalone F0
configuration.

### E. Reuse standalone F0 configuration and retrain only

**AMBIGUOUS.** This is not expressly authorized or prohibited. It would meet
the literal final-training-row requirement, but the protocol does not state
that standalone F0's selected `L` and hyperparameters may be transferred to a
candidate-matched comparator.

### F. Persistence, Ridge, and LightGBM

- **Persistence:** It has no fitting or configuration selection. Exact
  train-row matching has no operational meaning. Exact candidate test-row
  evaluation is sufficient.
- **Ridge and LightGBM:** Both are fitted and selected models, so the exact
  final-training-row requirement applies equally. The ambiguity about inner
  validation and repeated selection applies equally to both.

## Consequence

The protocol is unambiguous that the original fitted matched-F0 comparator is
nonconforming on final training support, but ambiguous about how to select its
configuration. Therefore this audit does not choose or implement a correction
method. Conditional fit counts and cost envelopes may be used for planning,
but no correction execution should be designed until this ambiguity is
resolved by an explicit prospective interpretation record that does not alter
the frozen protocol text.

## Executed mismatch summary

`matched_f0_row_mismatch.csv` contains 350 rows: two fitted model families,
five contextual feature sets, seven machines, and five folds.

Ratio summaries (candidate count divided by standalone F0 count):

| Group | Train min/median/mean/max | Inner-train min/median/mean/max | Inner-validation min/median/mean/max | Test min/median/mean/max |
|---|---|---|---|---|
| Ridge | 0.109 / 0.438 / 0.445 / 0.917 | 0.104 / 0.429 / 0.444 / 0.918 | 0.047 / 0.476 / 0.457 / 0.942 | 0.079 / 0.476 / 0.453 / 0.926 |
| LightGBM | 0.109 / 0.330 / 0.378 / 0.917 | 0.104 / 0.331 / 0.376 / 0.918 | 0.026 / 0.320 / 0.389 / 0.942 | 0.023 / 0.312 / 0.387 / 0.926 |
| F1 | 0.438 / 0.675 / 0.708 / 0.917 | 0.429 / 0.674 / 0.707 / 0.918 | 0.454 / 0.692 / 0.710 / 0.942 | 0.465 / 0.715 / 0.722 / 0.926 |
| F2 | 0.174 / 0.223 / 0.367 / 0.663 | 0.177 / 0.222 / 0.364 / 0.659 | 0.090 / 0.301 / 0.383 / 0.721 | 0.102 / 0.303 / 0.373 / 0.719 |
| F3 | 0.174 / 0.213 / 0.356 / 0.663 | 0.177 / 0.216 / 0.354 / 0.659 | 0.090 / 0.291 / 0.372 / 0.721 | 0.102 / 0.274 / 0.363 / 0.719 |
| F4 | 0.109 / 0.327 / 0.316 / 0.595 | 0.104 / 0.318 / 0.314 / 0.600 | 0.026 / 0.325 / 0.328 / 0.638 | 0.023 / 0.288 / 0.323 / 0.640 |
| F5 | 0.109 / 0.327 / 0.311 / 0.595 | 0.104 / 0.318 / 0.309 / 0.600 | 0.026 / 0.322 / 0.322 / 0.638 | 0.023 / 0.262 / 0.317 / 0.640 |

Absolute ranges across the 350 rows are:

- Standalone F0 final train: 13,251-26,859; candidate: 1,439-24,375.
- Standalone F0 inner train: 11,138-22,702; candidate: 1,162-20,610.
- Standalone F0 inner validation: 1,988-4,029; candidate: 69-3,680.
- Standalone F0 test: 2,673-2,999; candidate: 69-2,773.

For train, inner-train, inner-validation, and test, each candidate support is
the full intersection with standalone F0 support. Existing test comparisons
are therefore correctly row-matched; the nonconformance concerns model fitting
and possibly selection, not test alignment.

## Candidate validity

The original F1-F5 candidate models themselves remain protocol-conforming:

- each selected its configuration using only its feature-specific, purged
  inner-train and inner-validation rows;
- Ridge scaling was fitted on training data only; LightGBM requires no feature
  scaling;
- outer and inner target-time purges passed;
- segment-boundary checks passed;
- each model was evaluated on its legal feature-finite test rows;
- outer test columns were unavailable to selection.

No candidate F1-F5 rerun is indicated by this audit. Only the fitted F0
comparator evidence requires correction after the ambiguity is resolved.

## Persistence

Persistence has no trainable parameters, context length, or selected
configuration. Its prediction is the origin CPU value repeated across leads.
The original execution emitted Persistence separately on every feature set's
legal test rows, and stored validation confirms exact values. Persistence
requires no correction.

## Conditional correction arithmetic only

Because the selection rule is ambiguous, neither condition below is selected.

| Conditional interpretation | Persistence | Ridge | LightGBM inner lead models | LightGBM final lead models | New fitted F0 variants |
|---|---:|---:|---:|---:|---:|
| Reuse standalone F0 configuration; refit on exact candidate final-train rows | 0 | 175 final multi-output fits | 0 | 1,400 | 175 per fitted family |
| Repeat candidate-matched F0 selection, then refit | 0 | 2,625 inner + 175 final = 2,800 multi-output fits | 33,600 | 1,400 | 175 per fitted family |

There are 175 contextual variants per fitted model family:
`5 feature sets x 7 machines x 5 folds`.

Measured-throughput-only wall-time envelopes, assuming the original seven-way
parallelism, are:

| Conditional interpretation | Optimistic | Central | Conservative |
|---|---:|---:|---:|
| Refit only | about 8 min | about 15 min | about 25 min |
| Repeat selection and refit | about 3.1 h | about 6.25 h | about 9.4 h |

LightGBM dominates both estimates. Ridge arithmetic is seconds at the measured
throughput and should fit within the orchestration margin of these totals.
The optimistic/conservative bounds are 0.5x/1.5x the direct LightGBM
throughput extrapolation. They are planning estimates, not authorization to
execute either interpretation.

## Interpretation status

Standalone F0 model rankings and candidate-model absolute metrics remain as
executed. All headline F1-F5 versus F0 context-gain conclusions are
**provisional** until a protocol interpretation is recorded and corrected F0
comparators are evaluated.
