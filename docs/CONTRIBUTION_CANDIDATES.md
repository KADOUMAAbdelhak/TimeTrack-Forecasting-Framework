# Contribution Candidates (pre-final, evidence-gated)

Status: living document. No novelty claims until design is stable and literature
comparison is done in the manuscript phase (currently embargoed).

Pilot-derived signals informing candidates:

- Hierarchy exactness: cluster UM/UD = machine sums; bond0 ≈ NIC sum
- Heterogeneous winners by target/horizon (pilot only — claim-ineligible)
- Cross-machine CPU coupling selective (e.g., m1–m4); memory correlations less stable
- machine05/07 core-count label conflict → aggregation matrix must use verified mapping

---

## C1. Hierarchically coherent infrastructure forecasting

| Field | Content |
|-------|---------|
| Problem | Independent forecasts violate known sum/aggregate constraints used in capacity planning |
| Algorithm | Bottom-up / top-down / OLS / WLS / MinT-style reconciliation with nonnegative projection where needed |
| Implementation status | **Not started** |
| Expected novelty | Systems-facing coherent multi-level telemetry forecasting on TimeTrack hierarchies |
| Closest baseline | Independent local/global models without reconciliation |
| Evidence so far | Audit proofs of hierarchy; no forecasting evidence yet |
| Weaknesses | CPU aggregation needs careful core weighting; NIC bond≈sum is approximate |
| Decision | **retain** (priority) |

---

## C2. Metric–horizon adaptive selection / mixture

| Field | Content |
|-------|---------|
| Problem | Pilot suggests no universal winner across metrics/horizons |
| Algorithm | Validation-only router or constrained mixture using target, horizon, volatility, ACF, regime |
| Implementation status | **Not started** |
| Expected novelty | Operational routing for heterogeneous infra metrics under matched budgets |
| Closest baseline | Best fixed model per target-horizon; simple ensemble |
| Evidence so far | Pilot winner heterogeneity only (ineligible for claims) |
| Weaknesses | Risk of overfitting router to pilot terminal test — must use inner folds only |
| Decision | **retain** |

---

## C3. Global model + entity residual adaptation

| Field | Content |
|-------|---------|
| Problem | Pure local wastes shared structure; pure global ignores machine idiosyncrasy; LOMO needs transfer |
| Algorithm | Shared backbone + machine embedding + lightweight residual/calibration head |
| Implementation status | **Not started** |
| Expected novelty | Residual adaptation for CI/CD cluster machines under LOMO |
| Closest baseline | Local; pooled global; global+one-hot |
| Evidence so far | Mapping + weak cross-machine CPU corr |
| Weaknesses | Embedding useless for truly unseen machine without features |
| Decision | **retain** |

---

## C4. Regime-aware forecasting

| Field | Content |
|-------|---------|
| Problem | Idle vs burst vs cleanup regimes (esp. disk) |
| Algorithm | Train-only regime labels; indicators / experts / gating |
| Implementation status | **Not started** |
| Expected novelty | Secondary unless strong ablation wins |
| Closest baseline | Single model + calendar features |
| Evidence so far | Disk resets; CPU spikes; weekend ratios |
| Weaknesses | Regime definition leakage risk |
| Decision | **revise** after C1–C3 development results |

---

## Selection rule (pre-registered)

Keep the candidate with the best combination of: accuracy lift on development outer folds, coherence/LOMO/calibration benefit, ablation clarity, and CPU cost. Reject others with written rationale before freeze.
