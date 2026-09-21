# TimeTrack Experiment Matrix

Companion to `docs/RESEARCH_PLAN.md`. Cells mark **planned** experiments. Only cells that are actually executed may appear in `results/paper/*`.

Legend: `S` = smoke, `M` = medium, `P` = publication, `—` = not planned, `E` = experimental track.

---

## 1. Config tiers

| Tier | Context | Horizons | Seeds | HPO trials / model | Targets |
|------|---------|----------|------:|-------------------:|---------|
| `smoke` | 32 | 1, 4 | 1 | 0 (defaults) | cluster_mean_CU, machine01_CU, cluster_UM, tx_bond0_acamas |
| `medium` | 32, 64 | 1, 4, 8, 16 | 3 | 20 | all high-priority dense targets |
| `publication` | 16, 32, 64, 128 | 1, 2, 4, 8, 16, 32 | 5 | 40 (matched) | high-priority + selected secondary + experimental pilots |

---

## 2. Task registry (initial)

| task_id | target | entity | inputs | interval | context | horizons | transform | loss | why |
|---------|--------|--------|--------|----------|---------|----------|-----------|------|-----|
| `cpu_m_local` | machine CU | machine | univ. / +UM | native | 32–64 | 1–16 | none / robust scale | MAE | prior baseline metric, multi-machine |
| `cpu_cluster` | cluster_mean_CU | cluster | univ. / +cluster_UM | native | 32–64 | 1–16 | robust | MAE | cluster pressure |
| `mem_m_local` | machine UM | machine | univ. / +CU | native | 32–64 | 1–16 | robust | MAE | capacity planning |
| `mem_cluster` | cluster UM | cluster | univ. / +cluster_CU | native | 32–64 | 1–16 | robust | MAE | cluster memory |
| `disk_dwt` | machine DWT | machine | univ. | native | 32–64 | 1–8 | log1p | MAE | write pressure |
| `disk_ud_diff` | ΔUD | machine | univ. + reset feats | native | 32–64 | 1–8 | none | MAE/Huber | disk change |
| `net_tx_bond` | TX bond0 | host | univ. / +RX | native | 32–64 | 1–16 | log1p | MAE | network egress |
| `net_rx_bond` | RX bond0 | host | univ. / +TX | native | 32–64 | 1–16 | log1p | MAE | network ingress |
| `rtt_avg` | average RTT | collector | univ. / +jitter | native | 32–64 | 1–16 | none | MAE | latency |
| `rtt_max` | max RTT | collector | univ. / +avg | native | 32–64 | 1–16 | none | MAE/Huber | peak latency |
| `jitter` | jitter | collector | univ. / +avg | native | 32–64 | 1–16 | log1p | MAE | variability |
| `drop_two_stage` | drop event+mag | host bond0 | univ. + load | native | 64 | 1–4 | — | BCE+MAE | sparse events (E) |
| `cpu_core_pilot` | selected cores | core | univ. / global | native | 32 | 1–4 | robust | MAE | justify vs machine CU (E) |

---

## 3. Model × stage matrix

| Model family | Stage A | Stage B | Stage C | Stage D | Notes |
|--------------|---------|---------|---------|---------|-------|
| Persistence (last) | S/M/P | M/P | P | P | mandatory baseline |
| Seasonal persistence | S | M/P | P | P | only if val seasonal ACF supports |
| Historical mean | S | M/P | P | P | |
| Moving average | S | M/P | P | P | |
| EWMA | S | M/P | P | P | |
| Drift | S | M/P | P | P | |
| Ridge / Lasso / ElasticNet | — | M/P | P | P | lag features |
| ARIMA / ETS | — | M | optional P | — | local shortlist only |
| VAR / ridge-VAR | — | — | — | M/P | correlated groups |
| Random Forest | — | M/P | P | P | |
| Extra Trees | — | M/P | P | P | |
| LightGBM | — | M/P | P | P | primary tree |
| XGBoost | — | M/P | P | P | |
| CatBoost | — | M | P | P | |
| MLP | — | — | M/P | P | |
| LSTM / GRU | — | — | M/P | P | prior TimeTrack families |
| TCN | — | — | M/P | P | |
| CNN-LSTM | — | — | M | P | |
| DLinear / NLinear | — | — | M/P | P | strong modern linear TS |
| N-BEATS / N-HiTS | — | — | M/P | P | |
| PatchTST | — | — | M | P | if budget |
| TFT / TimesNet / iTransformer | — | — | — | optional | only if justified |
| Multi-output / shared encoder | — | — | — | M/P | RQ3 |
| Global + machine ID | — | — | — | M/P | RQ4/RQ5 |
| Residual hybrid / blend | — | — | — | M/P | RQ10 |
| Two-stage drop model | — | — | — | E | RQ sparse |

---

## 4. Ablation matrix

| Ablation ID | Factor | Levels | Applies to | Tier |
|-------------|--------|--------|------------|------|
| A1 | features | raw lags / +rolling / +calendar / full | LightGBM, Ridge | M/P |
| A2 | input scope | univariate / multivariate group | LightGBM, LSTM | M/P |
| A3 | output scope | single / multi-output group | selected | M/P |
| A4 | locality | local / global / global+ID | CU, UM | M/P |
| A5 | context | 16/32/64/128 | top-2 models per target | P |
| A6 | horizon | h1…h32 | all main | M/P |
| A7 | scaling | none / standard / robust / minmax | trees+neural | M |
| A8 | target form | level / diff (disk, memory optional) | disk, mem | M/P |
| A9 | time features | on / off | trees | M/P |
| A10 | cross-metric lags | on / off | multivariate tasks | M/P |
| A11 | resolution | native / 2× / ~3min / ~5min | CPU, UM, TX, RTT | M/P |
| A12 | ensemble | single vs val-weighted blend | top models | P |
| A13 | loss | MAE / Huber / peak-weighted | CPU, DWT | M/P |
| A14 | multi-step strategy | direct / recursive / seq2seq | neural | M/P |
| A15 | train volume | 25/50/75/100% train | top models | P |

Staged elimination: drop levels that are uniformly worse on validation before publication tier.

---

## 5. Evaluation slices (same test timestamps)

| Slice ID | Definition | RQ |
|----------|------------|----|
| `full_test` | entire chronological test | all |
| `weekday` | Mon–Fri hours in test | calendar |
| `weekend` | Sat–Sun in test | calendar |
| `workhours` | 09–17 local naive hour | calendar |
| `high_cpu` | target > train 95th pct | RQ11 |
| `spike_windows` | |y−med|>5×MAD events | RQ11 |
| `lomo_m{k}` | train w/o machine k | RQ5 |

---

## 6. Metrics matrix

| Metric | Dense continuous | Sparse / zero-inflated | Peaks | Probabilistic |
|--------|------------------|------------------------|-------|---------------|
| MAE / RMSE / MSE | ✓ | ✓ | ✓ | |
| R² (no clamp) | ✓ | ✓ | | |
| MAPE | ✓ w/ policy | report NA or masked | | |
| sMAPE / MASE | ✓ | ✓ primary | | |
| nRMSE | ✓ | ✓ | | |
| MedAE / MaxAE | ✓ | | ✓ | |
| Peak P/R / timing | | | ✓ | |
| Quantile loss / PICP / width | | | | ✓ |
| Train/infer time, size, params | ✓ | ✓ | ✓ | ✓ |

MAPE policy: if |y|<ε, exclude from MAPE denominator set and report `% excluded`; never silent ε-substitution as default ranking metric.

---

## 7. Run ID schema

```
{scope}__{target}__h{horizon}__c{context}__{model}__seed{seed}
```

Examples:

- `local__machine01_CU__h4__c32__lightgbm__seed0`
- `global__CU__h8__c64__lstm__seed1`
- `lomo__machine03_UM__h1__c32__ridge__seed0`

---

## 8. Result artifacts per executed run

- `results/metrics/raw_runs/{run_id}.json`
- `results/predictions/{run_id}.parquet` (or `.npz` if parquet unused)
- `results/models/{run_id}/` (weights + scaler + config hash)
- Aggregations updated into `results/metrics/all_runs.csv` and leaderboards

---

## 9. Statistical tests (Stage E)

For top-2 models per target–horizon:

- Paired bootstrap CI on MAE difference (test residuals)
- Effect size (standardized mean difference of absolute errors)
- Holm correction across model pairs within target

Do not declare winners on tiny single-seed gaps.

---

## 10. Execution checklist (high level)

1. [ ] Stage A smoke green + tests pass  
2. [ ] Stage B tree/linear leaderboard on medium targets  
3. [ ] Drop unsuitable tasks with written rationale  
4. [ ] Stage C neural on survivors  
5. [ ] Stage D multivariate/global/ensemble  
6. [ ] Stage E freeze + paper drafts from **executed** cells only  
