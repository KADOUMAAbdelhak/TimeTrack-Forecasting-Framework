# Evaluation Protocol V2

**Effective:** 2026-08-03  
**Reason:** The first 352 smoke/medium_lite runs scored the terminal chronological holdout and those scores informed subsequent modeling discussion. Under `docs/RESEARCH_PLAN.md`, that holdout was intended to remain untouched until Stage E. Those runs are therefore **pilot contamination** relative to a blind final test narrative.

This document supersedes the “untouched terminal test” wording in the research plan for claim-making purposes. The research plan’s leakage rules (no future leakage in windows/scalers/HPO) remain in force.

---

## 0. Hard rule

| Stage | `experiment_stage` | `eligible_for_final_claims` | `evaluation_role` |
|-------|--------------------|-----------------------------|-------------------|
| Pilot (existing 352 + future smoke) | `pilot` | `false` | `development_benchmark` |
| Development / inner selection | `development` | `false` | `inner_model_selection` |
| Final outer evaluation | `final` | `true` | `outer_evaluation` |

**Automated safeguards:**

- Run JSON must include the three metadata fields above.
- Artifacts write under `results/pilot/`, `results/development/`, or `results/final/`.
- `build_final_leaderboards()` **raises** if any row is not final-eligible.
- Pilot aggregation **raises** if final-stage rows appear in a pilot file (anti-mix).
- `append_all_runs` refuses mixed stages in one batch.

Legacy path `results/metrics/` after migration contains only a README pointer.

---

## 1. Pilot phase

**Contents:** all existing 352 runs; any future smoke / debugging runs.

**Allowed uses:**

- pipeline debugging,
- target triage (exclude impossible tasks),
- candidate model-family shortlisting,
- rough compute budgeting,
- designing contribution hypotheses.

**Forbidden uses:**

- FGCS final statistical claims,
- “state of the art” or “best model” language in a paper sense,
- sole justification of the final method without outer-fold confirmation.

**Disclosure (mandatory in any later manuscript methods):**  
The terminal chronological block was inspected during pilot work and is **not** a blind test.

---

## 2. Inner model-selection procedure

Operate only on training + validation regions of each outer training span.

1. **Outer chronological folds** (post-outage primary track; gap-aware).  
2. Within each outer training span, build **inner rolling-origin or expanding-window** folds.  
3. On inner folds only:
   - HPO (Optuna),
   - feature / context selection,
   - early stopping,
   - ensemble weights / stacking meta-learners,
   - routing / gating parameters for adaptive methods.
4. Refit selected configuration on the full outer training span (train∪inner-val policy as frozen later).  
5. Evaluate on the outer evaluation block **once per frozen config**.

Windows must never cross the major outage, split/fold boundaries, or missing-target stretches.

---

## 3. Outer final-evaluation procedure

1. Predefine ≥3 chronological outer folds on the post-outage segment (exact cut points frozen in config + hash).  
2. All compared models share identical origin timestamps per fold/task.  
3. After freeze: **no architecture changes** based on outer-fold metrics.  
4. Aggregate across folds and seeds (mean±std; paired tests at fold or block-bootstrap level).  
5. Write only to `results/final/` with `eligible_for_final_claims: true`.

---

## 4. Terminal chronological confirmation set

The original 70/15/15 terminal test block may be retained as a **confirmation set**:

- useful for continuity with pilot diagnostics,
- must be labeled `confirmation_set` / exposed-during-pilot,
- **must not** be the sole basis for publication claims,
- must not be described as untouched/blind.

---

## 5. Generalization tracks (final-eligible when frozen)

| Track | Purpose |
|-------|---------|
| Leave-one-machine-out | Cross-machine transfer |
| Pre-outage → post-outage | Temporal domain shift |
| Weekday / weekend slices | Calendar generalization |
| Low-load / high-load slices | Regime robustness |
| Spike-event slices | Peak operational relevance |

Inner HPO for LOMO must not use the held-out machine.

---

## 6. Freeze procedure

Before any `experiment_stage: final` publication run:

1. Select retained models + contribution.  
2. Freeze targets, exclusions, folds, seeds, HPO budgets, metrics, tests, plot schemas.  
3. Full test suite green.  
4. Config validation.  
5. **Git commit** + tag e.g. `experiment-freeze-v1`.  
6. Record commit hash inside final config.  
7. Dry-run plan: run count, runtime, disk.  
8. Execute into `results/final/` only.

Any post-freeze logic change requires a new freeze version and rerun of affected comparisons.

---

## 7. Directory layout

```text
results/
  pilot/           # exploratory; ineligible
    metrics/raw_runs/
    predictions/
    models/
    notes/         # former results/paper internal notes
  development/     # optional inner-selection artifacts
  final/           # empty until freeze; only eligible claims
```

---

## 8. Relation to RESEARCH_PLAN.md

- Leakage-safe windowing/scaling/HPO-on-validation: **unchanged**.  
- “Untouched final test until Stage E”: **replaced** by nested outer folds + explicit confirmation-set disclosure.  
- Pilot results remain scientifically useful but **claim-ineligible**.  
