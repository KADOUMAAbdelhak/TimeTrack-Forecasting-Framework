# TimeTrack — Current Implementation Status

**Verification date (UTC):** 2026-08-03  
**Verified by:** live repository inspection + `python scripts/tt_cli.py test`  
**Authority:** code and artifacts over conversational summary

---

## 1. Git / provenance (critical discrepancy)

| Claim in prior summary | Verified state |
|------------------------|----------------|
| “Phase 1 audit completed and committed” | **FALSE** — **no `.git` directory**; `git status` / `git log` fail with “not a git repository” |
| Current branch / commit hash | **N/A** — repository was never initialized |
| Pushable remote | **None** |

**Action required:** initialize Git and create an initial checkpoint commit after protocol separation (this phase).

---

## 2. Tests

```text
python scripts/tt_cli.py test
.............  [100%]
13 passed in ~5s   # before evaluation-stage tests added
```

After adding `tests/test_evaluation_stage.py`, expected count increases (see post-change re-run).

---

## 3. Data

| Item | Status |
|------|--------|
| Six raw CSVs at project root | Present (hard-linked into `data/raw/`) |
| Sampling median ≈ 42.285 s | Confirmed in code (`timetrack.constants.SAMPLING_SECONDS`) and audit |
| Major outage ~4.87 days | Confirmed (`OUTAGE_START` / `OUTAGE_END`) |
| Dataset fingerprint (MANIFEST) | `bf06dc0e7fe6ff5e` |

---

## 4. Implemented models (registered)

Via `python scripts/tt_cli.py list-models` (**19** registered):

**Baselines:** persistence, seasonal_persistence, historical_mean, moving_average, ewma, drift  

**Classical:** ridge, lasso, elasticnet  

**Trees:** random_forest, extra_trees, lightgbm, xgboost, catboost  

**Neural / modern:** mlp, lstm, gru, tcn, dlinear  

**Stubs only (empty packages):** `models/ensembles/`, `models/multivariate/`, `models/hybrid/`

---

## 5. Executed targets and runs (pilot)

| Metric | Verified |
|--------|----------|
| Raw JSON run files | **352** under legacy `results/metrics/raw_runs` (pre-migration) |
| Predictions | 352 |
| Saved model dirs | 352 |
| Aggregate rows | 352 in `all_runs.csv` |
| Configs executed | `configs/smoke.yaml`, `configs/medium_lite.yaml` |
| Horizons | 1, 4, 8 |
| Context | 32 only |
| Seeds | 0 and/or 1 |

**Targets with executed runs (11):**

- `cluster_mean_CU`, `machine01_CU`, `machine04_CU`, `machine06_CU`
- `cluster_UM`, `machine01_UM`
- `machine01_DWT`
- `averageRttWithGoogleDns`, `jitterWithGoogleDns`
- `tx_bond0_acamas`, `rx_bond0_acamas`

**Models with executed runs (10):**  
persistence, historical_mean, moving_average, ewma, drift, ridge, lightgbm, xgboost, dlinear, lstm  

**Registered but not executed in the 352:**  
seasonal_persistence, lasso, elasticnet, random_forest, extra_trees, catboost, mlp, gru, tcn  

---

## 6. Failed / incomplete historical attempts

`results/logs/failures.jsonl` contains **10** early failure records from the first smoke pass (variable-shadowing in ridge/lightgbm; DLinear pickle). Later re-runs completed those models; failures file was **not** cleaned (stale log).

No missing raw JSON among the final 352 successful artifacts.

---

## 7. Evaluation protocol status (pre-correction)

| Requirement in RESEARCH_PLAN | Actual practice in 352 runs |
|------------------------------|-----------------------------|
| Terminal test untouched until Stage E | **Violated** — runner always scored `metrics_test` and wrote leaderboards used for “provisional winners” |
| `experiment_stage` metadata | **Absent** on all 352 JSON files prior to migration |
| Nested rolling-origin / outer folds | **Not implemented** — only single chronological 70/15/15 `post_outage_split` |
| LOMO / global / ensembles / reconciliation | **Not implemented** |
| Optuna | Script exists (`scripts/tune_optuna.py`, ~116 lines) — **not executed**; no study DB artifacts |
| `publication.yaml` | Present but **must not** be run until freeze |

**Correction:** all 352 runs are **pilot / development_benchmark**, `eligible_for_final_claims: false`. See `docs/EVALUATION_PROTOCOL_V2.md`.

---

## 8. Reusable functionality

- Data panel builder + fingerprinting (`timetrack/data.py`)
- Chronological post-outage split + windowing with outage guards (`timetrack/splits.py`)
- Metrics with MAPE zero policy / MASE / peak helpers (`timetrack/metrics.py`)
- Model registry + factory (`models/forecasting.py`)
- Config-driven runner (`experiments/runner.py`) — now stage-aware
- CLI (`scripts/tt_cli.py`)
- Optuna skeleton (`scripts/tune_optuna.py`)
- Bootstrap pairwise script (`scripts/statistical_compare.py`)
- Audit + research plan + experiment matrix docs

---

## 9. Missing functionality (before final experiments)

| Capability | Status | Est. compute (Apple Silicon CPU, order-of-magnitude) |
|------------|--------|------------------------------------------------------|
| Pilot/final isolation + tests | **This checkpoint** | minutes |
| Nested rolling-origin / outer folds | Missing | implementation days; runtime fold×current |
| Optuna complete (plots, fold-aware, export) | Partial | hours–days per target-model; budgeted trials |
| Global + identity + residual adaptation | Missing | ×7 machines vs local; LOMO ×7 |
| Leave-one-machine-out | Missing | ~7× selected model grid |
| Multivariate / multi-output | Missing | ×2–4 vs univariate |
| Ensembles / stacking | Missing | cheap once constituents exist |
| Hierarchical reconciliation | Missing | moderate; systems contribution |
| Probabilistic / conformal | Missing | ×1.5–3 train cost |
| Peak-aware losses | Missing | modest |
| Packet-drop two-stage | Missing; may be **unsupported** | small if events exist |
| Downsampling study | Missing | ×4 resolutions |
| Efficiency instrumentation (RAM/GPU, cold/warm) | Partial (wall times only) | measurement overhead |
| Fresh-env reproducibility script | Missing | CI-like hours |
| Git history / freeze tags | Missing | — |

---

## 10. Discrepancies vs conversational summary

1. **No Git commits** despite “committed” wording.  
2. Provisional winners used **test MAE** → pilot contamination.  
3. “13 tests” true at verification start; stage tests added afterward.  
4. Optuna / global / LOMO / ensembles listed as “remaining” — confirmed **absent or stub**.  
5. `results/paper/*` are **internal notes**, not manuscript sections (correct to keep embargoed).  
6. Failure log still lists bugs that were later fixed (stale).  

---

## 11. Config hashes (verified)

| Config | Hash | Stage (updated) | Targets | Models | Horizons | Seeds |
|--------|------|-----------------|---------|--------|----------|-------|
| smoke | `5010b966bd17`* | pilot | 4 | 8 | 1,4 | 0 |
| medium_lite | `ef1996ef5443`* | pilot | 11 | 7 | 1,8 | 0,1 |
| medium | `8fd8b1f2fd03`* | development | 14 | 16 | 1,4,8,16 | 0,1,2 |
| publication | `9488803c9b7d`* | development (blocked from final) | 22 | 18 | 1–32 | 0–4 |

\*Hashes change after adding `experiment_stage` keys; recompute after config edits.

---

## 12. Next stage after this checkpoint

1. Finish pilot migration + stage tests green.  
2. Initialize Git + commit protocol correction.  
3. Implement nested evaluation, then Optuna hardening, then contribution candidates (hierarchy / adaptive routing).  
4. **Do not** launch `publication.yaml` as final until freeze.  
