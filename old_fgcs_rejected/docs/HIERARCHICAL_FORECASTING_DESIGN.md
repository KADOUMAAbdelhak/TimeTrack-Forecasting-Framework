# Hierarchical Forecasting Design

Technical design for TimeTrack aggregation hierarchies and forecast reconciliation.
Not manuscript prose. Development-stage only until publication freeze.

## 1. Hierarchy definitions

### 1.1 Memory (exact)

- Bottoms: `machine01_UM` … `machine07_UM`
- Top: `cluster_UM`
- Relation (audit-verified): `cluster_UM = Σ_k machine0k_UM`
- Hierarchy name: `memory_um`

### 1.2 Disk (exact)

- Bottoms: `machine01_UD` … `machine07_UD`
- Top: `cluster_UD`
- Relation: `cluster_UD = Σ_k machine0k_UD`
- Hierarchy name: `disk_ud`
- Reset-aware variants of UD are handled at the target-construction layer; reconciliation still assumes the sum identity on the chosen UD representation.

### 1.3 CPU (core-weighted)

`cluster_mean_CU` in the raw panel is an unweighted mean and is **not** a sum hierarchy.

For reconciliation we use core-weighted contributions:

- `z_k = c_k · CU_k`
- Top: `cluster_CU_wsum = Σ_k z_k`
- Weighted-mean CU: `Σ z / Σ c`

Core counts `c_k` come from verified host mapping (`MACHINE_TO_HOST` → `HOST_CORE_COUNTS`), **not** from raw `totalCpuCoresmachine05/07` which are swapped relative to pegase/phaedra.

Provenance fields stored on the hierarchy meta:

- `core_counts` (corrected)
- `raw_conflicting_labels` (preserve mislabeled static fields)
- `machine_to_host`

`assert_not_using_raw_conflicting_labels` rejects accidental use of the swapped pair.

### 1.4 Network bond0 (approximate)

For selected hosts, member NIC TX/RX ≈ bond0 TX/RX (audit near-exact).

- Bottoms: member interface throughput columns
- Top: `…bond0`
- Meta: `relation=approximate_sum`
- Use only when empirical aggregation error on the evaluation window is acceptably small; otherwise skip or report as approximate coherence.

## 2. Aggregation / summing matrix

For a sum hierarchy with `n` bottoms:

```
S = [ I_n ]
    [ 1'  ]     shape (n+1, n)
```

Full coherent series: `y = S b` where `b` is the bottom vector.

`Hierarchy.project(bottom)` implements `y = S @ b`.
`verify_summing_identity` checks reconciled outputs satisfy this.

## 3. Reconciliation formulas

All methods operate on base forecasts `ŷ` ordered as bottoms then top.

| Method | Formula / rule |
|--------|----------------|
| independent | leave `ŷ` unchanged (may be incoherent) |
| bottom_up | `b̃ = ŷ_bottom`, `t̃ = 1' b̃` |
| top_down | proportions from base bottoms applied to `ŷ_top` |
| OLS | `ỹ = S (S'S)⁺ S' ŷ` |
| WLS | `ỹ = S (S' W⁻¹ S)⁺ S' W⁻¹ ŷ` with `W = diag(σ²)` |
| MinT-shrink | same as WLS with `W` = shrunk residual covariance |

After optional nonnegative projection on bottoms, re-close via bottom-up so `y = S b` holds for sum hierarchies.

## 4. Covariance / variance estimation (leakage rule)

For WLS and MinT:

- Estimate `series_var` / `residual_cov` from **training or inner-fold residuals only**.
- API: `estimate_residual_covariance(y_true_full, y_pred_full)`.
- **Never** fit covariance on the outer evaluation block.
- Singular / ill-conditioned covariances: diagonal shrinkage + ridge + `pinv`.
- If fewer than 2 residual rows, fall back to identity.

## 5. Nonnegative handling

`nonnegative=True` clamps bottoms to `≥ 0`, then bottom-up reclosure.
Appropriate for non-negative physical quantities (memory used, disk used, throughput).
Not forced for signed residuals or demeaned series.

## 6. Missing child series

`mask_missing_children` / `missing_mask` in `reconcile`:

- Fill unavailable children with a documented constant (default 0).
- Callers must log which series/timestamps were excluded.
- Coherence is then with respect to the filled bottoms (operational policy), not imputed physics.

## 7. Data-quality conflict (machine05 / machine07 cores)

| Source | machine05 | machine07 |
|--------|-----------|-----------|
| Verified (hostname mapping) | pegase → 20 | phaedra → 24 |
| Raw `totalCpuCores*` labels | 24 | 20 |

Aggregation **must** use verified counts. Tests refuse the swapped raw pair.

## 8. Coherence verification

- Exact sum hierarchies: `is_coherent` / `coherence_error` with absolute/relative tolerances scaled to series magnitude.
- Bond0: report approximate coherence error; do not claim exact arithmetic identity.
- Reconciled methods (not independent) must satisfy `summing_ok` via `S @ b`.

## 9. Limitations

- CPU path reconciles weighted contributions, not raw `cluster_mean_CU`.
- Bond0 is approximate; NIC membership can change operationally.
- MinT quality depends on residual sample size and stationarity within the train/inner window.
- Nonnegative + bottom-up reclosure can increase bottom MAE while guaranteeing coherence.
- Hierarchy screen is development-stage; not eligible for final claims until freeze.
