# Development Evidence Summary

Status: living document. Development-stage only (`eligible_for_final_claims: false`).
Not manuscript prose. Updated after hierarchy expansion + global/LOMO infrastructure.

Dataset fingerprint: see run meta JSON files under `results/development/`.

---

## 1. Does reconciliation provide value beyond exact arithmetic consistency?

**Yes for memory and core-weighted CPU; selective for bond0; not for disk bottom-up.**

Artifacts: `results/development/metrics/hierarchy_all_runs.csv` (558 rows), `hierarchy_summary.csv`, `tables/hierarchy_comparison.*`, figures under `results/development/figures/hierarchy_*.pdf`.

Mean top MAE relative to independent (all models/folds/horizons in screen):

| Hierarchy | Best recon method | top_mae_rel | coherence |
|-----------|-------------------|-------------|-----------|
| memory_um | WLS / MinT | ~0.951 | exact (0) |
| cpu_core_weighted | MinT | ~0.940 | exact (0) |
| bond0_transmitted_acamas | bottom_up_nn | ~0.995 | exact (0) |
| disk_ud | top_down (not BU) | ~1.0 | exact; BU ~3.4× worse |

Independent coherence errors are large on memory/disk/CPU weighted scale; reconciled methods close them without (memory/CPU) or with modest (bond0) accuracy cost.

---

## 2. Do global models outperform local models on average?

**No (development LOMO + transfer setting).**

On leave-one-machine-out (ridge backbone, CU & UM, h∈{1,8}, 3 outer folds × 7 machines):

| Family | Best local | Best global (no cal) | Macro MAE |
|--------|------------|----------------------|-----------|
| CU h=1 | persistence_local | global_onehot / residual_no_head | 1.66 vs 2.09 |
| UM h=1 | persistence_local | global_pooled | 1.92e8 vs 7.58e9 |

Global without held-out identity loses badly on memory scale; CPU transfer gap is smaller but still favors local persistence.

---

## 3. Which machines benefit or degrade?

See `results/development/tables/lomo_per_machine.csv` and `figures/lomo_per_machine.pdf`.

- Worst-machine MAE (CU h=1): persistence ~3.67; global_onehot ~5.47; unstable cal64 up to ~112.
- Do **not** average away catastrophic calibration failures (documented in summary `mae_worst_machine`).

---

## 4. Can the framework forecast an unseen machine?

**Yes, with a defined unknown-entity policy — but accuracy is weak vs local history.**

Policy:

- one-hot → zeros for unseen machine
- embedding → reserved UNK index 0
- residual adaptation → global-only (no fabricated residual head)

Global CU MAE ~2.09 vs local persistence ~1.66. Operationally usable only if no local history exists.

---

## 5. How much local calibration is required?

**UM:** more calibration helps monotonically (0 → 64 → 256 → 1024) but even 1024 samples remain worse than persistence_local.

**CU:** small calibration (64/256) is **harmful** (unstable residual head); 1024 still worse than cal0 / persistence.

Predeclared sizes: 0, 64, 256, 1024 (chronology: cal origins from train+val only).

---

## 6. Do correlated inputs improve forecasting?

**Mostly no under matched ridge/lightgbm budgets (development).**

Artifact: `results/development/tables/univariate_vs_multivariate.csv` (144 rows) + `figures/multivariate_gain_by_correlation.pdf`.

- Clear gain: `machine01_tx_bond0` ← TX+RX (ridge/LGBM MAE ↓ ~0.5–0.7).
- Elsewhere (CPU↔memory, RX←TX, RTT group, jitter←RTT): multivariate **worsens** mean MAE.
- Do not claim causality from correlation–gain scatter; neural multivariate (DLinear/LSTM) not in this screen (flagged slow).

---

## 7. Do ensembles beat their strongest constituent?

**Sometimes on CPU mean; rarely elsewhere.**

Artifacts: `results/development/metrics/ensemble_all_runs.csv` / `ensemble_summary.csv`.

- `cluster_mean_CU`: stacking beats best constituent on all folds at h=1 (beat_rate=1.0); often at h=8.
- `cluster_UM` / RTT: ensembles rarely beat persistence (best constituent); inverse-MAE occasionally helps UM (beat_rate=1/3).
- Rule enforced: must beat strongest constituent, not only persistence — stacking is the only clear partial win.

---

## 8. Which contribution candidate is strongest for FGCS?

**Tentative ranking (development):**

1. **C1 hierarchical coherence** — strongest systems story if expanded hierarchy screen confirms non-inferior accuracy + exact coherence (still the leading candidate).
2. **C3 global+residual** — **revise**: LOMO evidence currently does **not** support global/residual over local persistence; calibration helps UM somewhat but not enough.
3. **C2 adaptive routing** — still pending; pilot heterogeneity remains the motivation.

---

## 9. Which experiments remain before freeze?

- Optional DLinear/LSTM hierarchy + multivariate add-ons (`INCLUDE_*` flags)
- Local vs pooled global **in-distribution** (not only LOMO) for C3 fairness
- Target-/horizon-specific ensembles with broader frozen constituent set
- Fix CU MASE NaNs in LOMO (train scale edge cases)
- Still **do not** launch `publication.yaml` / manuscript

---

## 10. Is any candidate clearly unsupported?

- **C3 as “global beats local for unseen machines without calibration”**: unsupported by current LOMO.
- **Small-sample residual calibration (≤256) on CU**: unsupported / harmful.
- C1 not unsupported; evidence incomplete until expanded hierarchy summary is in.

---

## Compute consumed (this checkpoint)

- LOMO development screen: ~1.5 h wall-clock on laptop CPU; 672 rows.
- Hierarchy expanded screen: multi-hour with dlinear; rerun without dlinear for tractability.
- Tests: 50 passing at last full suite before LOMO artifact commit.
