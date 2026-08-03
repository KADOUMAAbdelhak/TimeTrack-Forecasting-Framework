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
| Algorithm | Bottom-up / top-down / OLS / WLS / MinT-shrink reconciliation with nonnegative projection where needed |
| Implementation status | **Implemented** (`models/hybrid/reconciliation.py`); design in `docs/HIERARCHICAL_FORECASTING_DESIGN.md`; expanded development runner `scripts/run_hierarchy_dev.py` |
| Expected novelty | Systems-facing coherent multi-level telemetry forecasting on TimeTrack hierarchies |
| Closest baseline | Independent local/global models without reconciliation |
| Evidence so far | Expanded development screen (558 runs; 3 outer folds; persistence/ridge/lightgbm; h∈{1,8}): **memory_um** WLS/MinT/BU top MAE ~0.95–0.96× independent with exact coherence; **cpu_core_weighted** MinT/WLS/BU ~0.94–0.95×; **bond0_acamas** near-parity + exact coherence; **disk_ud** BU/WLS/MinT materially worsen top MAE (top_down preserves accuracy while restoring coherence) |
| Weaknesses | CPU uses core-weighted contributions not raw mean; bond0 approximate; disk hierarchy accuracy-sensitive; dlinear hierarchy add-on not in main screen (slow) |
| Decision | **retain** — value beyond arithmetic consistency on memory/CPU (and bond0); revise disk policy toward top_down / selective reconciliation |

---

## C2. Metric–horizon adaptive selection / mixture

| Field | Content |
|-------|---------|
| Problem | Pilot suggests no universal winner across metrics/horizons |
| Algorithm | Validation-only router or constrained mixture using target, horizon, volatility, ACF, regime |
| Implementation status | Ensemble weight utilities ready (`models/ensembles/strategies.py`); router not started |
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
| Algorithm | Shared backbone + one-hot/embedding + residual/calibration head |
| Implementation status | **Implemented** (`global_pooled`, `global_onehot`, `global_embed`, `global_residual`); LOMO runner + tests |
| Expected novelty | Residual adaptation for CI/CD cluster machines under LOMO |
| Closest baseline | Local; pooled global; global+one-hot |
| Evidence so far | LOMO (dev): local persistence beats all global variants on CU/UM; UM calibration 0→1024 helps but remains worse than local; CU small-cal harmful |
| Weaknesses | Embedding useless for truly unseen machine without features; scale / MASE issues on CU |
| Decision | **revise** — keep infrastructure; do not claim LOMO accuracy win; re-evaluate in-distribution global vs local |

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
