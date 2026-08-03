# Development Evidence Summary

Status: living document. Development-stage only (`eligible_for_final_claims: false`).
Updated after MASE fix, in-distribution global/local, DLinear diagnosis, C2 router, peaks, downsampling, and contribution gate.

---

## 1. Does reconciliation provide value beyond exact arithmetic consistency?

**Yes for memory and core-weighted CPU; selective for bond0; not for disk bottom-up.**

Mean top MAE relative to independent (tree/linear screen, 558 runs):

| Hierarchy | Best recon | top_mae_rel | coherence |
|-----------|------------|-------------|-----------|
| memory_um | WLS / MinT | ~0.951 | exact |
| cpu_core_weighted | MinT | ~0.940 | exact |
| bond0_acamas TX | bottom_up_nn | ~0.995 | exact |
| disk_ud | top_down | ~1.0 | exact; BU ~3.4× worse |

Neural confirmation (LSTM/DLinear, memory+CPU) is in progress to test model-agnostic gains.

---

## 2. Do global models outperform local models on average?

**No (in-distribution, ridge).**

| Family | Best method | Macro MAE (h=1) |
|--------|-------------|-----------------|
| CU | local ≈ global_residual | ~1.527 |
| UM | local ≈ global_residual | ~2.21e8 |

Pooled / one-hot worse; embedding unstable on UM (huge errors).

---

## 3. Which machines benefit or degrade?

See `global_vs_local_per_machine` figures/tables. Residual tracks local closely; pooled hurts high-scale UM machines most.

---

## 4. Can the framework forecast an unseen machine?

**Yes with unknown-entity policy; accuracy weak vs local history (LOMO).**

CU persistence_local MAE ~1.66 vs global ~2.09. UM gap much larger without calibration.

---

## 5. How much local calibration is required?

UM: more samples help (0→1024) but still worse than local persistence. CU: small calibration harmful.

---

## 6. Do correlated inputs improve forecasting?

Mostly no under matched ridge/lightgbm budgets; TX←TX+RX is the clear exception.

---

## 7. Do ensembles / routers beat their strongest constituent?

- Stacking helps `cluster_mean_CU` in earlier ensemble screen.
- C2 routers/mixtures: intermittent per-target beat_rate>0 but **mean MAE_rel ≈ 1.05–1.16** vs best constituent → not a robust win.

---

## 8. Which contribution candidate is strongest for FGCS?

**C1 hierarchical reconciliation** — see `docs/CONTRIBUTION_SELECTION_DECISION.md`.

---

## 9. Which experiments remain before freeze?

- Finish neural hierarchy confirmation (≥2 seeds).
- Final efficiency tables + block-bootstrap on frozen comparisons.
- Optional LightGBM in-distribution global/local (OMP-isolated) if needed.
- Still **do not** run `publication.yaml`.

---

## 10. Is any candidate clearly unsupported?

- C3 as LOMO/in-distribution accuracy win: unsupported.
- C2 as primary adaptive contribution: unsupported at this gate (demote).
- Blind disk bottom-up: unsupported.

---

## MASE policy

- Denominator: finite lag-1 pairs on outer-train only.
- Invalid ⇒ `mase_valid=false` + reason; excluded from averages.
- Secondary: `nmae_train_range`, `rmsse` when valid.

## DLinear

Bounded/included in selected experiments only (`docs/DLINEAR_RUNTIME_DIAGNOSIS.md`).
