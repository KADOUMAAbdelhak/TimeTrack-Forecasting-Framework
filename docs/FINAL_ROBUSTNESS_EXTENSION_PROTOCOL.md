# Final robustness extension protocol

## Active freeze

Tag: `final-robustness-extension-freeze-v2`  
Supersedes (preserved, not altered): `final-robustness-extension-freeze-v1`  
Source prediction freeze: `experiment-freeze-v2`  
Status: **CONDITIONAL GO** until multi-seed packs complete under v2

## Why v2

`final-robustness-extension-freeze-v1` LightGBM seed execution was rejected:

- execution logic / config hash differed from the freeze tag
- `n_jobs=1` broke parity with seed-0 (`n_jobs=-1`)
- seed was not the only changed variable

Provisional rejected artifacts:

`results/development/provisional_robustness/final-robustness-extension-freeze-v1/lightgbm_seed_robustness/`

## Scientific config hash boundary

`scientific_config_hash` / `config_hash` covers the scientific payload only.

**Included:** dataset fingerprint, context, folds, EWMA grid, model hparams,
`lightgbm_n_jobs`, pack matrix, wall-clock limits, artifact roots, seed-reuse
maps, efficiency defaults, bootstrap policy.

**Excluded:** `implementation_commit`, `freeze_commit`, `freeze_tag_commit`,
and the self-referential `frozen_scientific_config_hash` field.

Acceptance requires:

```text
frozen_scientific_config_hash
  == validated scientific_config_hash
  == executed config_hash
  == MANIFEST.config_hash
```

## LightGBM seed comparability

Seed 0 (experiment-freeze-v2) used:

```text
random_state = seed
n_jobs = -1
```

plus frozen `n_estimators` / `learning_rate` / `num_leaves`.

Seeds 1 and 2 must use the **same** constructor fields; only `random_state`
may differ. Do not pass extra bagging / feature-fraction arguments.

Library defaults (LightGBM 4.7 sklearn): `subsample=1.0`, `subsample_freq=0`,
`colsample_bytree=1.0`, `boosting_type=gbdt` — may imply determinism; that is
valid.

## Packs (manual sequential)

| Order | Pack ID | Notes |
|------:|---------|-------|
| 1 | `ewma_baselines` | Accepted under prior run; do not rerun unless required |
| 2 | `lightgbm_seed_robustness` | Corrected under freeze-v2 |
| 3 | `dlinear_seed_robustness` | Not auto-launched |
| 4 | `robustness_statistics` | Not auto-launched |

## Runner

```bash
python scripts/run_robustness_pack.py \
    --config configs/final_robustness_extension.yaml \
    --pack lightgbm_seed_robustness \
    --resume
```
