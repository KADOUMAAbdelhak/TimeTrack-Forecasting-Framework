# TimeTrack Research Plan

**Status:** Planning document derived from `docs/DATASET_AND_REPOSITORY_AUDIT.md`  
**Date:** 2026-08-03  
**Scope:** Multi-metric infrastructure time-series forecasting on the downloaded TimeTrack CSVs

Hypotheses below are **not** established findings. They define what experiments must test.

---

## 1. Verified problem setting

| Fact | Source |
|------|--------|
| Greenfield repo (data only) | Audit §3.1 |
| ~25.1 calendar days, 7 machines | Audit §3.2 |
| Median sampling **42.285 s** (not 45 s) | Audit §3.4 |
| Hard outage ~4.87 days (2024-06-28 → 2024-07-03) | Audit §3.4 |
| Deterministic redundancies (CU/CF, sums, bond0) | Audit §3.3 |
| Packet errors all zero; drops extremely sparse | Audit §3.6 |

### Primary scientific goal

Build a **leakage-safe, multi-metric forecasting benchmark** that:

1. Goes beyond prior CPU-only TimeTrack studies.
2. Selects architectures from experimental evidence.
3. Reports accuracy, uncertainty (where applicable), efficiency, and statistical comparisons.
4. Allows different winners per target and horizon.

---

## 2. Entity and metric registry (working)

### Entity keys

| Key | Meaning |
|-----|---------|
| `machine01`…`machine07` | Aggregate compute/disk series |
| Hostnames | `acamas`, `bellerophon`, `dedale`, `demophon`, `pegase`, `perse`, `phaedra` |
| Mapping | Correlation-based (audit table); note m05↔pegase / m07↔phaedra vs swapped core-count labels |

### Target tiers (from audit)

- **High-priority:** machine/cluster CU, UM; bond0 TX/RX; avg/max RTT; jitter; selected DWT; UD differences
- **Secondary:** UD levels; min/mdev RTT; sparse DRT
- **Experimental:** packet-drop events; per-core CPU (staged)
- **Excluded:** CF, AM (as scored targets), err_packet, constants, bond0+member double-counting

---

## 3. Evaluation protocol (frozen intent)

### Chronological splits (post-outage primary track)

Use the **post-outage segment** as the main benchmark track (≈33,235 points from 2024-07-03 10:05:20 to 2024-07-19 16:27:05):

| Split | Fraction (approx.) | Role |
|-------|--------------------|------|
| Train | first 70% | fit models, scalers, features |
| Validation | next 15% | model selection, HPO, early stopping |
| Test | final 15% | **untouched** final evaluation |

Exact indices will be computed from timestamps and written into configs with hashes.

### Additional protocols

1. **Gap-aware full timeline:** train on pre-gap, validate/test on post-gap (domain shift / cold continuity).
2. **Rolling-origin backtesting** on post-gap train+val region only (test still held out for final report).
3. **Leave-one-machine-out** for global models (RQ5).
4. **Weekday→weekend** and **low vs high load** slices on the same test timestamps.
5. **Seeds:** ≥3 for stochastic models; report mean±std, not best seed.

### Leakage rules (non-negotiable)

- Scalers / encoders fit on train only.
- No interpolation using future points.
- Windows must not cross split boundaries or the outage gap.
- HPO uses validation only.
- Feature selection must not inspect test labels.

### Horizons (based on Δt ≈ 42.3 s)

| Steps | Approx. wall time | Label |
|------:|-------------------|-------|
| 1 | ~42 s | h1 |
| 2 | ~85 s | h2 |
| 4 | ~2.8 min | h4 |
| 8 | ~5.6 min | h8 |
| 16 | ~11.3 min | h16 |
| 32 | ~22.5 min | h32 |

**Default publication subset (compute budget):** h1, h4, h8, h16. Full set in complete config.

### Context lengths to ablate

Default candidates: 16, 32, 64, 128 steps (~11 min to ~90 min). Start with 32/64.

### Forecasting strategies to compare

- One-step
- Direct multi-horizon
- Recursive multi-step
- Seq2seq multi-output (selected neural models)

---

## 4. Research questions

### RQ1. Which model performs best per metric and horizon?

- **Hypothesis:** No single architecture dominates all targets; tree models competitive on memory/disk rates; neural/modern models may win on bursty CPU/network with sufficient data.
- **Data:** post-gap primary track; high-priority targets.
- **Baselines:** persistence, seasonal-naive (if daily ACF warrants), mean, MA, EWMA, drift.
- **Candidates:** Ridge/Lasso lags, RF/ET/LightGBM/XGBoost/CatBoost, MLP/LSTM/GRU/TCN, DLinear/NLinear/N-BEATS/N-HiTS/PatchTST (subset by Stage C evidence).
- **Metrics:** MAE, RMSE, sMAPE, MASE, R² (allow negative), peak metrics; MAPE with explicit zero policy.
- **Ablations:** context length, strategy (direct vs recursive).
- **Artifacts:** per-target and per-horizon leaderboards; statistical tests.

### RQ2. When does multivariate input beat univariate?

- **Hypothesis:** Multivariate helps when contemporaneous corr ≳ 0.5 (e.g., CU–UM on m1/m3/m4; RX–TX on some hosts) and hurts under weak coupling / extra noise.
- **Inputs:** target lags only vs + within-group exogenous lags.
- **Ablation:** univariate vs multivariate for fixed model family (LightGBM + LSTM).

### RQ3. Joint vs single-target prediction

- **Hypothesis:** Multi-output helps correlated pairs but harms when targets have mismatched scales/noise without loss balancing.
- **Compare:** one-model-per-target vs grouped multi-output vs shared encoder + heads.

### RQ4. Global vs machine-specific models

- **Hypothesis:** Global models win on data-poor / similar machines; local models win when dynamics differ (e.g., m6 low persistent CPU vs bursty m1).
- **Protocol:** local per machine vs global with optional machine ID embedding/one-hot.

### RQ5. Unseen-machine generalization

- **Hypothesis:** Global models transfer partially for CU/UM but degrade for host-specific network rates.
- **Protocol:** leave-one-machine-out; report gap vs in-machine test.

### RQ6. Feature engineering value

- **Hypothesis:** Calendar + rolling stats help tree/linear models more than deep sequence models with long context.
- **Ablation:** raw lags vs full feature set vs time-only vs cross-metric lags.

### RQ7. Horizon degradation

- **Hypothesis:** Error increases sublinearly for persistent memory; faster for jitter/spikes.
- **Output:** error-vs-horizon curves with CI.

### RQ8. Downsampling information loss

- **Hypothesis:** Aggregating to ~3–5 min reduces spike fidelity and hurts peak metrics more than MAE on smooth memory.
- **Resolutions:** native ~42.3 s; 2×; ~3 min; ~5 min (exact rules in config).

### RQ9. Accuracy–efficiency trade-off

- **Hypothesis:** LightGBM/DLinear form the operational Pareto front; Transformers rarely justify cost on this dataset size.
- **Measure:** train time, infer latency, params, model size, peak RAM/GPU.

### RQ10. Hybrids / ensembles

- **Hypothesis:** Validation-weighted blends beat the single best model on some targets, especially across horizons.
- **Constraint:** ensemble weights from validation only.

### RQ11. Spike / peak prediction

- **Hypothesis:** Standard MAE-optimal models under-detect CPU and DWT peaks; peak-aware losses or quantile models improve recall at some precision cost.
- **Metrics:** peak precision/recall, timing error, high-util MAE.

### RQ12. Probabilistic calibration

- **Hypothesis:** Quantile regression / conformal intervals can achieve near-nominal coverage on RTT and memory; CPU spikes remain under-covered.
- **Metrics:** PICP, interval width, quantile loss.

---

## 5. Staged execution strategy

### Stage A — Foundations (smoke)

- Immutable raw data layout + fingerprinting
- Loaders, gap handling, chronological splits, windowing
- Baselines + metrics + leakage tests
- Smoke config on 1–2 targets × h1/h4

### Stage B — Classical + trees

- Ridge/Lasso/ElasticNet, RF/ET, LightGBM/XGBoost/CatBoost
- Identify forecastable vs hopeless tasks
- Feature ablations (RQ6)

### Stage C — Neural + modern

- MLP, LSTM/GRU, TCN, DLinear/NLinear, N-BEATS/N-HiTS
- Add PatchTST/TFT only if Stage B leaves clear residual structure and budget allows
- Tuned only for promising target–model pairs with **matched HPO budgets**

### Stage D — Multivariate / global / hybrid

- RQ2–RQ5, RQ10
- Packet two-stage pilot (experimental track)

### Stage E — Final freeze

- Fixed seeds/folds, statistical tests, Pareto, paper drafts, MANIFEST

---

## 6. Hyperparameter optimization

- **Framework:** Optuna (fresh project; no existing NNI/Ray Tune).
- **Sampler seed** fixed; prune with median pruner where supported.
- **Budgets:** declared per stage in configs (`smoke`, `medium`, `publication`).
- Comparable trial counts across families unless justified in the report.
- Objective: **MASE** (primary) or MAE for dense continuous targets; **event F1** for drop classifiers — **not MAPE** when zeros are common.

---

## 7. Deliverable mapping

| Deliverable | Produces evidence for |
|-------------|------------------------|
| Leaderboards | RQ1, RQ7 |
| Ablation tables | RQ2, RQ3, RQ4, RQ6, RQ8, RQ15-list |
| LOMO tables | RQ5 |
| Pareto + timing | RQ9 |
| Ensemble table | RQ10 |
| Peak case studies | RQ11 |
| Calibration plots | RQ12 |
| `results/paper/*` | Full narrative of executed work only |

---

## 8. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| 45 s assumption leaks into code | Config stores `sampling_seconds: 42.285`; tests assert median≈42.3 |
| Gap leakage | Split builder refuses windows spanning outage |
| Inflated multi-output scores via complements | Target registry marks excluded pairs |
| Over-claiming SOTA | Require baselines + seeds + tests + scoped wording |
| Per-core explosion | Stage gate: must beat machine CU aggregation first |
| Packet all-zero errors | Exclude from main leaderboard |

---

## 9. Immediate implementation priorities

1. Repository skeleton + `data/raw` mirroring (copy/link, no delete).
2. Config-driven pipeline + task registry.
3. Baselines + evaluation + tests.
4. Stage A smoke run producing real `results/` rows.
5. Expand through stages B–E as compute allows, documenting only executed experiments in paper drafts.
