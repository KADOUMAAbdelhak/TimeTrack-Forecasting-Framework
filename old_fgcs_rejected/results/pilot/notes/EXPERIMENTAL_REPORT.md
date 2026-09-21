# Experimental Report (Executed Work Only)

**Generated:** 2026-08-03T09:43:21.937717+00:00  
**Dataset fingerprint:** `bf06dc0e7fe6ff5e`  
**Executed runs in aggregate table:** 352  
**Raw JSON runs:** 352  
**Configs executed:** `configs/smoke.yaml`, `configs/medium_lite.yaml`

## What was inspected

See `docs/DATASET_AND_REPOSITORY_AUDIT.md`. Repository was greenfield (six CSVs only). Median sampling interval ≈ **42.3 s** (not 45). Outage 2024-06-28 → 2024-07-03.

## Data actually available

Six CSVs under project root / `data/raw/`: compute, detailed CPU cores, disk, network RTT, packet-loss, throughputs.

## Metrics selected vs excluded

**Selected (executed):** cluster/machine CU, cluster/machine UM, machine01 DWT, average RTT, jitter, acamas TX/RX bond0.  
**Excluded from scoring:** CF/AM complements, all `err_packet_*` (identically zero), member-NIC duplicates of bond0, constants.

## Protocol used in executed runs

- Track: post-outage chronological 70/15/15 train/val/test
- Context: 32
- Horizons executed: [1, 4, 8]
- Seeds: 0 (smoke) and 0–1 (medium_lite)
- Leakage controls: split-bounded windows; no test fitting

## Targets evaluated

- `averageRttWithGoogleDns`
- `cluster_UM`
- `cluster_mean_CU`
- `jitterWithGoogleDns`
- `machine01_CU`
- `machine01_DWT`
- `machine01_UM`
- `machine04_CU`
- `machine06_CU`
- `rx_bond0_acamas`
- `tx_bond0_acamas`

## Models evaluated

- `dlinear`
- `drift`
- `ewma`
- `historical_mean`
- `lightgbm`
- `lstm`
- `moving_average`
- `persistence`
- `ridge`
- `xgboost`

## Winners by target/horizon (lowest mean test MAE among executed models)

- `averageRttWithGoogleDns` h=1: **ewma** (mean MAE=0.3062, mean R²=0.585, seeds=2)
- `averageRttWithGoogleDns` h=8: **ewma** (mean MAE=0.3458, mean R²=0.455, seeds=2)
- `cluster_UM` h=1: **persistence** (mean MAE=1.12e+09, mean R²=0.332, seeds=2)
- `cluster_UM` h=4: **ridge** (mean MAE=1.501e+09, mean R²=0.279, seeds=1)
- `cluster_UM` h=8: **ridge** (mean MAE=1.694e+09, mean R²=0.185, seeds=2)
- `cluster_mean_CU` h=1: **xgboost** (mean MAE=1.14, mean R²=0.638, seeds=2)
- `cluster_mean_CU` h=4: **lightgbm** (mean MAE=1.488, mean R²=0.394, seeds=1)
- `cluster_mean_CU` h=8: **lightgbm** (mean MAE=1.608, mean R²=0.300, seeds=2)
- `jitterWithGoogleDns` h=1: **dlinear** (mean MAE=0.3155, mean R²=0.111, seeds=2)
- `jitterWithGoogleDns` h=8: **dlinear** (mean MAE=0.318, mean R²=0.088, seeds=2)
- `machine01_CU` h=1: **xgboost** (mean MAE=2.115, mean R²=0.649, seeds=2)
- `machine01_CU` h=4: **lightgbm** (mean MAE=3.545, mean R²=0.317, seeds=1)
- `machine01_CU` h=8: **lstm** (mean MAE=3.51, mean R²=-0.012, seeds=2)
- `machine01_DWT` h=1: **lstm** (mean MAE=5.059e+06, mean R²=-0.024, seeds=2)
- `machine01_DWT` h=8: **lstm** (mean MAE=5.074e+06, mean R²=-0.024, seeds=2)
- `machine01_UM` h=1: **persistence** (mean MAE=2.853e+08, mean R²=0.304, seeds=2)
- `machine01_UM` h=8: **ridge** (mean MAE=4.756e+08, mean R²=0.052, seeds=2)
- `machine04_CU` h=1: **lightgbm** (mean MAE=3.72, mean R²=0.675, seeds=2)
- `machine04_CU` h=8: **dlinear** (mean MAE=6.493, mean R²=0.164, seeds=2)
- `machine06_CU` h=1: **lightgbm** (mean MAE=0.06147, mean R²=0.289, seeds=2)
- `machine06_CU` h=8: **lightgbm** (mean MAE=0.07128, mean R²=0.172, seeds=2)
- `rx_bond0_acamas` h=1: **lstm** (mean MAE=18.57, mean R²=0.048, seeds=2)
- `rx_bond0_acamas` h=8: **lstm** (mean MAE=18.25, mean R²=0.040, seeds=2)
- `tx_bond0_acamas` h=1: **lstm** (mean MAE=48.82, mean R²=0.024, seeds=2)
- `tx_bond0_acamas` h=4: **dlinear** (mean MAE=59.33, mean R²=0.084, seeds=1)
- `tx_bond0_acamas` h=8: **lstm** (mean MAE=50.34, mean R²=0.013, seeds=2)

## Notable observations (executed evidence only; provisional)

1. Tree models (**LightGBM/XGBoost**) often win short-horizon CPU tasks versus persistence.
2. **Persistence** remains best or near-best for some memory levels at h1 — high lag-1 autocorrelation.
3. **LSTM/DLinear** appear competitive on some network throughput and disk-write tasks under the medium_lite budget.
4. External RTT is somewhat persistence/EWMA friendly; jitter often favors DLinear in these runs.
5. Do **not** compare raw MAE across targets with different units (bytes vs % vs ms vs rate).
6. MAPE zero-exclusion and occasional MASE=NaN (zero naive scale) are logged explicitly.
7. Improvements are **not** declared statistically significant here (limited seeds; no bootstrap table yet for all pairs).

## Not yet executed (do not treat as results)

- Full `medium.yaml` / `publication.yaml` matrices
- Matched Optuna budgets across all families
- Global / LOMO / ensemble / packet two-stage / per-core pilots
- Downsampling RQ8 and probabilistic calibration RQ12 at scale
- Holm-corrected paired tests for every winner claim

## Reproduce executed results

```bash
source .venv/bin/activate
export OMP_NUM_THREADS=1
python scripts/tt_cli.py test
python scripts/tt_cli.py run --config configs/smoke.yaml
python scripts/tt_cli.py run --config configs/medium_lite.yaml
python scripts/generate_report_artifacts.py
```
