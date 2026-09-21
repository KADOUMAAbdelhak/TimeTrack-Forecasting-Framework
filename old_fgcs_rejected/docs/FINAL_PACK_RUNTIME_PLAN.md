# Final Pack Runtime Plan

Date: 2026-08-04  
Config: `configs/final_fgcs_packs.yaml`  
Machine context: local macOS, `OMP/MKL/OPENBLAS_NUM_THREADS=1`  
HPO policy: family-level shared configs (**≤16 LightGBM trials** + Ridge 5-value grid).  
Monolithic `final_fgcs_full.yaml` remains `optional_extended` / not default.

## Measured unit costs (memory_um, fold0, h1, 8 series + recon)

| Model | Seconds per hierarchy job |
|-------|---------------------------|
| persistence | 6.6 |
| ridge | 7.6 |
| lightgbm | 8.3 |
| dlinear | 9.1 |

`shared_tuning` full pack measured wall: **~35–48 s** (complete).

## Required packs

| Pack | Required | Base fits (series) | Recon evals | Measured/projected wall | Hard limit | Dependencies | Split needed? |
|------|----------|--------------------|-------------|-------------------------|------------|--------------|---------------|
| shared_tuning | yes | ~27 tuning runs | 0 | **0.6 min measured** | 45 | — | no |
| memory_classical | yes | 216 | 144 | **~3.4 min** (proj) / plan 12 | 45 | shared_tuning | no |
| memory_dlinear | yes | 72 | 36 | **~1.4 min** (proj) / plan 8 | 45 | shared_tuning | no |
| cpu_classical | yes | 216 | 144 | **~3.5 min** (proj) / plan 12 | 45 | shared_tuning | no |
| cpu_dlinear | yes | 72 | 36 | **~1.4 min** (proj) / plan 8 | 45 | shared_tuning | no |
| disk_boundary | yes | 144 | 90 | **~2.3 min** (proj) / plan 10 | 45 | shared_tuning | no |
| supporting_statistics | yes | 0 | 0 | ≤10 min | 45 | model packs | no |
| peak_analysis | yes | 0 | 0 | ≤8 min | 45 | memory+cpu packs | no |
| downsampling | yes | 24 | 0 | ≤10 min | 45 | shared_tuning | no |

**Longest required pack (projected):** memory/cpu classical ≈ 3–4 minutes (plan buffer 12).  
**No required pack projects above 45 minutes.**

## Optional packs

| Pack | Required | Fits | Projected | Notes |
|------|----------|------|-----------|-------|
| network_secondary | no | 72 | ~12 min | Admit only if bond0 error < 0.02 |
| conformal_intervals | no | 4 | ~8 min | 90% coverage only |
| lstm_confirmation | no | 48 | ≤28 / hard 30 | Skip if DLinear confirmation sufficient |

## Total required compute

| Metric | Value |
|--------|-------|
| Required HPO trials | **16** (8 mem + 8 CPU LightGBM) + Ridge grid (not Optuna) |
| Required series-level base fits | 216+72+216+72+144+24 = **744** |
| Required recon evaluations | 144+36+144+36+90 ≈ **450** |
| Sum of required pack plan buffers | **~83 minutes** across sessions |
| Sum of measured/projected model-pack wall | **~13 minutes** (+ stats/peak/downsample ≤28) |
| Peak RSS expectation | Modest (single-threaded; DLinear cleaned per run) |

## Wall-clock control

- `hard_wall_clock_minutes: 45`
- `stop_launching_new_runs_minutes: 40`
- Partial packs write `RUN_STATUS.json`, keep completed runs, print resume command
- Resume verified: forced partial after 1/2 jobs → resume completed pack

## Aggregator gate

`aggregate_final_packs.py` refuses claim tables until all required packs are `complete`.

## Manual launch (no auto-queue)

```bash
python scripts/list_final_packs.py --config configs/final_fgcs_packs.yaml
python scripts/run_final_pack.py --config configs/final_fgcs_packs.yaml --pack shared_tuning --resume
# later, one pack per session:
python scripts/run_final_pack.py --config configs/final_fgcs_packs.yaml --pack memory_classical --resume
```
