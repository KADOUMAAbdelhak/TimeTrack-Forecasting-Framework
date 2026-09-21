# Methodology Section 4 revision audit

**Task:** Expand Section 4 — Forecasting and Reconciliation Methodology  
**Base commit:** `4ff0488` (accepted dataset/hierarchy)  
**Date:** 2026-08-05

## Length

| Metric | Before | After |
|--------|--------|-------|
| Section 4 prose words | ~220 | ~948 |
| Numbered subsections | 4 (short titles) | 4 (renamed/expanded) |
| Article pages | 13 | **14** |
| PDF pages | 14 | 15 |
| Section 4 rendered span | ≪0.5 page | ≈1.5–1.6 pages (art.\ p.6–p.8) |

### Subsections retained/renamed

| Before | After |
|--------|-------|
| Forecasting Problem | Forecasting Problem and Hierarchical Representation |
| Baselines and Forecasting Models | Forecasting Baselines and Learned Models |
| Reconciliation Methods | Forecast Reconciliation |
| Evaluation Metrics | Accuracy, Coherence, and Operational Metrics |

## Equations added

1. `\eqref{eq:hierarchy}` — \(\mathbf{y}_t=\mathbf{S}\mathbf{b}_t\)
2. `\eqref{eq:recon}` — \(\tilde{\mathbf{y}}=\mathbf{S}\mathbf{G}\hat{\mathbf{y}}\)
3. `\eqref{eq:projection}` — WLS/MinT projection form
4. Unnumbered \(\Delta_{\mathrm{rel}}\) definition

## Notation

- \(n=7\), \(m=8\), \(\mathbf{b}_t\), \(\mathbf{y}_t\), \(\mathbf{S}\)
- hats = base forecasts; tildes = reconciled
- \(L=32\), multi-output width \(h\)
- \(\mathbf{W}\), \(\mathbf{G}\), coherence residual, adjustment magnitude

## Models / reconciliation / metrics documented

- Persistence, EWMA (\(\alpha=0.90\)), Ridge, LightGBM (CPU/memory/disk-transfer), DLinear
- Independent, bottom-up, top-down (disk; \(\varepsilon=10^{-12}\)), WLS, MinT-shrink, OLS ablation note
- MAE, RMSE, MASE (lag-1 train scale; undefined policy), \(R^2\), top/bottom/worst/core-weighted MAE, \(\Delta_{\mathrm{rel}}\), peak suite

## Implementation sources consulted

- `models/classical/baselines.py`, `linear.py`
- `models/machine_learning/trees.py`
- `models/deep_learning/neural.py`
- `models/hybrid/reconciliation.py`
- `timetrack/splits.py`, `metrics.py`, `peak_reporting.py`
- `experiments/pack_runner.py`, `final_hierarchy_runner.py`, `robustness_extension.py`
- `configs/final_fgcs_packs.yaml`, `configs/final_robustness_extension.yaml`
- `results/final/packs/00_shared_tuning/selected_hyperparameters.yaml`
- `results/final/robustness/01_ewma_baselines/selected_ewma_params.yaml`
- `docs/EVALUATION_PROTOCOL_V2.md`, `FINAL_STATISTICAL_PROTOCOL.md`, `FINAL_PEAK_ANALYSIS_PROTOCOL.md`
- aggregate SAFE/UNSUPPORTED/FINAL evidence summaries

## Key implementation deviations noted in manuscript

1. **Evaluation uses first multi-output component** (`_first_step` → \(y_{t+1}\)), while models train length-\(h\) vectors; \(h\) still affects training width and admissible origins.
2. **MinT-shrink applied twice** (cov estimate shrink \(0.1\) + reconciler shrink \(0.1\) + ridge).
3. **Disk LightGBM** = transferred memory hyperparameters.
4. **Top-down proportions** from base bottom forecasts (not historical averages).
5. **No calendar covariates**; univariate per-series models; context \(L=32\).

## Duplication / placement

- Baseline table roles stripped of result-winner language (moved to Results conceptually)
- Protocol details left in Section 5; forward references only
- `\FloatBarrier` after baseline table; architecture figure remains in Section 3

## Unsupported-claim review

- No new reconciliation algorithm claimed
- No universal MinT / BU / TD / LightGBM / EWMA / DLinear superiority
- Coherence ≠ accuracy stated explicitly
- Seed invariance framed as frozen-config empirical property
- Peak metrics not claimed optimized during training
- Result numbers deferred

## Build / layout

- Compilation errors: 0
- Unresolved citations/references: 0
- Overfull boxes: 0
- Article length: 14 pages (preferred)
- Citation instances in Section 4: 8 (within 8–12 band)
- Section 5 starts cleanly on art.\ p.8

## Recommendation

`READY_FOR_EXPERIMENTAL_PROTOCOL_EXPANSION`
