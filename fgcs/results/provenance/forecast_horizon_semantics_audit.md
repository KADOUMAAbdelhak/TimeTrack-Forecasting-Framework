# Forecast-horizon / output-width semantics audit

**Date:** 2026-08-05  
**Base commit:** `f7bb6c6`  
**Decision:** **Interpretation B** — configuration values \(1,8,16\) are joint prediction / multi-output training widths \(H\); frozen metrics score **one-step** forecasts only.

## Decision summary

| Question | Answer |
|----------|--------|
| Interpretation | **B** (not A) |
| Meaning of 1/8/16 | Joint prediction width \(H\) (number of future samples in the training target vector) |
| Scored forecast lead | **1 step** (\(y_{t+1}\) vs \(\hat y_{t+1\mid t}\)) for every \(H\) |
| Scored prediction component | Index **0** via `_first_step` |
| Reconciliation component | Same first component (1-D vectors in frozen NPZs) |
| Peak extraction | Uses NPZ `yt_test`/`pt_test` already reduced to first component |

## Implementation files inspected

| Role | Path | Function / class |
|------|------|------------------|
| Window / target construction | `timetrack/splits.py` | `build_windows`, `origins_for_split` |
| Split packaging | `experiments/runner.py` | `prepare_split_windows` |
| First-component extraction | `experiments/final_hierarchy_runner.py` | `_first_step` |
| Final pack fit/score | `experiments/pack_runner.py` | `_fit_predict` → `_first_step` on `y`/`pred` |
| Hierarchy runner | `experiments/final_hierarchy_runner.py` | `_fit_predict_series` |
| Robustness LightGBM/DLinear/EWMA | `experiments/robustness_extension.py`, `lightgbm_seed_analysis.py`, `dlinear_seed_analysis.py` | reuse `_fit_predict` / aligned NPZs |
| Reconciliation | `models/hybrid/reconciliation.py` | `reconcile` on 1-D top / (n,7) bottoms |
| Peak | `timetrack/peak_reporting.py` | `load_npz` → `yt_test`, `pt_test` |

## Exact array shapes (proven)

For origin \(o\), context \(L=32\), width \(H\):

- Context indices: \([o-L+1,\ldots,o]\)
- Target indices: \([o+1,\ldots,o+H]\)
- Target array: shape `(n,)` if \(H=1\), else `(n,H)` with column \(k\) = \(y_{o+1+k}\)
- After `_first_step`: shape `(n,)` = column 0 = \(y_{o+1}\)
- Frozen NPZ (example LightGBM CPU fold0):  
  - \(H=1\): `yt_test`/`pt_test` shape `(4847,)`  
  - \(H=8\): `(4295,)`  
  - \(H=16\): `(3707,)`  
  All are **1-D** — multi-step vectors are discarded before metrics/recon/peak.

## Concrete timestamp example

Saved in `forecast_semantics_example.csv`.

Representative origin (fold 0, `cluster_UM`):

- Origin \(t\): `2024-07-07 13:12:25.639671`
- Context end: same
- Scored timestamp for **every** \(H\in\{1,8,16\}\): `2024-07-07 13:13:07.924451` (= \(t+1\))
- For \(H=16\), last jointly trained target: `2024-07-07 13:23:42.070753` (= \(t+16\)) — **trained, not scored**
- Reconciliation timestamp: same as scored timestamp (\(t+1\))

## Evaluation-set differences

From `forecast_semantics_eval_sets.csv` / pack comparisons:

| Hierarchy | Fold | \(H=1\) test | \(H=8\) test | \(H=16\) test | Identical timestamps? |
|-----------|------|-------------:|-------------:|--------------:|:----------------------|
| CPU | 0 | 4847 | 4295 | 3707 | **No** (\(H\) drops final + NaN-invalid origins) |
| Memory | 0 | 8276 | 8269 | 8261 | **No** (drops final \(H-1\) origins) |
| Disk | 0 | 8276 | 8269 | — | **No** |

Larger \(H\) never adds scored leads; it only restricts admissible origins (and, for sparse CPU, removes additional NaN-spanning windows).

## Manuscript terminology corrections applied

- Intro / RQ2: “horizons” → multi-output-width configurations
- §3: “horizon interpretation” → wall-clock sampling-step interpretation
- §4: define \(H\); state one-step scoring and recon explicitly
- §5 protocol table: Output widths + Scored lead
- §6 captions/prose: width-mean / width-level; CPU figure → `cpu_accuracy_vs_output_width.pdf`
- Tables / supplementary: horizon → output width / \(H\)
- Figures regenerated from **same** aggregate CSVs (labels only)

## Claim impact

| Claim | Status |
|-------|--------|
| LightGBM independent vs Ridge on CPU | **unchanged** (one-step comparisons) |
| LightGBM MinT vs independent | **unchanged** |
| DLinear recon consistency | **unchanged** |
| Memory DLinear vs own independent | **unchanged** |
| Memory vs EWMA | **unchanged** numerically; wording “horizon-mean” → “width-mean” |
| Disk BU / TD boundary | **unchanged** numerically |
| Peak conclusions | **unchanged** (same first-component NPZs) |
| Seed robustness | **unchanged** |
| “Across forecast horizons / long-horizon robustness” | **narrowed** → across output-width configurations |
| Multi-lead-time forecasting accuracy | **unsupported** (must not be claimed) |

## Numerical impact

- Result **values** unchanged (no rerun)
- Tables/figures **numerically** unchanged
- Labels/captions/filenames corrected

## GO-scope assessment

**GO_SCOPE_NARROWED**

Primary CPU/memory/disk reconciliation evidence remains valid as **one-step** hierarchy-aware forecasting under multiple joint prediction widths. The publication GO remains appropriate only after reframing: the paper must not claim multi-lead-time or long-horizon evaluation. RQ2 loses a true forecast-horizon dimension and retains fold/width/model/seed stability.

## Recommendation

`READY_FOR_EXPERIMENTAL_PROTOCOL_EXPANSION` (after this correction commit)
