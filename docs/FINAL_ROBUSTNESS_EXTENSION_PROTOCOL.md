# Final robustness extension protocol

Tag: `final-robustness-extension-freeze-v1`  
Source prediction freeze: `experiment-freeze-v2`  
Status before extension: **CONDITIONAL GO** (see `docs/PUBLICATION_GATE_CORRECTION.md`)

## Purpose

Close only the pre-registered gaps that blocked unconditional GO:

1. **Gate 2** — include EWMA in the final baseline set.
2. **Gate 3 / 4** — provide ≥3 seeds for stochastic models (LightGBM, DLinear)
   without deriving primary claims from seed 0 alone.

Do **not** alter existing freeze tags, do **not** rewrite gate definitions, and do
**not** rerun accepted seed-0 forecasting packs.

## Invariants (must match freeze-v2)

- Dataset fingerprint `bf06dc0e7fe6ff5e`
- Post-outage analysis panel / timeline
- Outer-fold indices (`n_outer_folds=3`)
- Hierarchy definitions (`memory_um`, `cpu_core_weighted`, `disk_ud`)
- Horizons and context policy (`context=32`)
- Reconciliation implementation (`models/hybrid/reconciliation.py`)
- Verified CPU core mapping (total 236)
- Target units (CPU reported as core-weighted sum / equivalent mean %)

## Packs (manual sequential)

| Order | Pack ID | Role |
|------:|---------|------|
| 1 | `ewma_baselines` | Select α on inner val only; outer eval + recon |
| 2 | `lightgbm_seed_robustness` | Seeds 1–2 only; reuse seed 0 |
| 3 | `dlinear_seed_robustness` | Seeds 1–2 only; reuse seed 0 |
| 4 | `robustness_statistics` | No training; claim updates |

Do not launch packs automatically. After each pack, report and wait for approval
before the next.

## Disk LightGBM

Do **not** extend disk LightGBM seeds. That result remains a
transferred-configuration stress result, not a primary claim. EWMA completes
the disk baseline set; primary disk evidence remains Ridge / persistence /
top-down–bottom-up boundary.

## Freeze procedure

1. Implement packs + validators + tests.
2. Synthetic smoke tests; verify seed-0 prediction hashes unchanged.
3. Commit: `experiments: freeze EWMA and multi-seed robustness extension`
4. Push `main`; create annotated tag `final-robustness-extension-freeze-v1`.
5. Verify peeled remote commit.

## Runner

```bash
python scripts/run_robustness_pack.py \
    --config configs/final_robustness_extension.yaml \
    --pack ewma_baselines \
    --resume
```

Artifacts: `results/final/robustness/<pack_dir>/`
