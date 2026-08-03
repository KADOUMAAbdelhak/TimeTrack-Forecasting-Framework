# Publication Gates (pre-registered)

Defined **before** final outer-fold results are used for method selection.
Do not edit thresholds after inspecting final outcomes; amend only with a new
versioned gate document and re-freeze.

Venue positioning: predictive resource management for cloud-edge / distributed
CI/CD infrastructures (FGCS), not a generic ML bake-off.

---

## Gate 1 — Reproducibility

- [ ] Clean env install from locked deps
- [ ] All tests pass
- [ ] Deterministic split/fold indices (hashed)
- [ ] Dataset + config + freeze commit hashes recorded
- [ ] `python scripts/reproduce.py --tier smoke` works
- [ ] One final run regenerates within numeric tolerance

## Gate 2 — Baseline strength

Final comparisons must include at least:

- persistence
- EWMA
- Ridge (tuned or nested-selected)
- Strongest tuned tree (LightGBM or XGBoost)
- Strongest tuned neural/modern (LSTM and/or DLinear)
- Relevant hierarchical and/or ensemble baselines when claiming C1/C2

## Gate 3 — Experimental breadth

- ≥2 metric families among {CPU, memory, network rate, latency}
- ≥3 horizons
- ≥3 machines (or LOMO covering all 7)
- ≥3 seeds for stochastic models
- ≥3 chronological outer folds

## Gate 4 — Statistical support

- Confidence intervals on primary metrics
- Paired fold-level or block-bootstrap comparisons
- Effect sizes / relative improvement
- Holm (or pre-specified) correction within comparison families
- No claim from a single seed

## Gate 5 — Practical significance

Pass if **either**:

**A.** Material error reduction vs strongest tuned baseline on multiple independent
target families **or** on a substantial fraction of target–horizon tasks  
(guideline: ≥5% relative MAE or MASE reduction on ≥30% of frozen tasks, and
consistent sign across outer folds)

**OR**

**B.** Comparable accuracy with a clear advantage in hierarchical coherence,
unseen-machine generalization, calibration, peak prediction, or efficiency
(guideline: ≥2× inference speedup or ≥50% coherence-error reduction with
non-inferior accuracy within 2% relative MAE)

## Gate 6 — Robustness

- Not driven by one seed, one easy target, or one horizon
- No catastrophic machine (worst-machine MAE inflation disclosed)
- Pilot contamination disclosed

## Gate 7 — Ablation

Every proposed component ablated; gains not solely from extra parameters or
unequal HPO budgets.

## Gate 8 — Scientific honesty

Negative results retained; unsupported tasks excluded; no SOTA language without
gates 2–5.

---

## Decision rule

| Outcome | Meaning |
|---------|---------|
| GO | All gates satisfied; manuscript phase may begin after template provided |
| CONDITIONAL GO | Specific missing experiments listed; reassess after |
| NO-GO | Contribution or evidence insufficient for FGCS submission |

Decision document after finals: `docs/FGCS_PUBLICATION_READINESS.md` (not yet).
