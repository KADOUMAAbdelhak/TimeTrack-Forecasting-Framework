# Peak analysis — blocked under experiment-freeze-v2

## Status

**NOT EXECUTED / SCIENTIFICALLY BLOCKED** for the frozen pack runner
`experiments/pack_runner.py::run_peak_analysis`.

`results/final/packs/07_peak_analysis/` must remain absent until a separate
peak-analysis freeze regenerates metrics from stored NPZs.

## Blocker

| Issue | Detail |
|-------|--------|
| `bottom_up_proxy` | Labels reconciliation rows but uses independent `pt_test` |
| WLS / MinT | Never reconstructed or scored for peaks |
| CPU units | Stored `cluster_CU_wsum` not converted to weighted-mean % |
| Config matrix | Empty models/horizons/folds/methods; NPZ glob discovery |
| Event matching | Frozen helper uses ±2-step tolerance and `>`; not used for claims |

## Frozen helper excerpts

- Thresholds from `yt_train` (q90/q95) — leakage-safe if used alone.
- Independent `pt_test` peak metrics would be valid for **independent only**.
- Comment in runner: *"approximate using independent preds as placeholder when recon vectors not stored"*.

## Allowed path

Implement tracked analysis under `final-peak-analysis-freeze-v1`:

- `timetrack/peak_reporting.py`
- `scripts/analyze_final_peaks.py`
- `configs/final_peak_analysis.yaml`

Reconstruct reconciliation from NPZs, verify against accepted
`reconciliation_results.csv`, convert CPU tops by `/236`, evaluate the full
predefined method matrix without outer MAE cherry-picking.

## Explicit unsupported claims

Do **not** claim, from the freeze-v2 pack runner alone:

- that bottom_up / WLS / MinT improve peak recall or high-load MAE,
- any operational peak benefit of reconciliation,
- any peak conclusion that depends on `bottom_up_proxy` rows.
