# TimeTrack Forecasting Framework

Publication-oriented, leakage-safe multi-metric forecasting for the TimeTrack OpenAirInterface CI/CD telemetry dataset.

## What this repository contains

- **Raw data** (immutable): six CSV files at the project root, hard-linked into `data/raw/`
- **Audit & plans**: `docs/DATASET_AND_REPOSITORY_AUDIT.md`, `docs/RESEARCH_PLAN.md`, `docs/EXPERIMENT_MATRIX.md`
- **Framework**: `timetrack/`, `models/`, `experiments/`, `configs/`, `tests/`
- **Results**: `results/` (populated by executed runs only)

This is **not** a reproduction of prior CPU-only TimeTrack papers. Those are literature baselines. This project expands to multi-metric forecasting under a strict chronological protocol.

## Critical data facts (verified)

- Median sampling interval ≈ **42.3 s** (not 45 s)
- Span: 2024-06-24 → 2024-07-19 with a **~4.87-day outage** (2024-06-28 → 2024-07-03)
- Seven machines / hosts; packet **errors are all zero** in this download

See the audit document for full evidence.

## Setup

```bash
cd /Users/fgtek002/TimeTrack
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Commands

```bash
# Dataset fingerprint + segment counts
python scripts/tt_cli.py audit

# Build processed panel (parquet)
python scripts/tt_cli.py preprocess

# List models
python scripts/tt_cli.py list-models

# Unit tests
python scripts/tt_cli.py test
# or: pytest -q tests

# Smoke benchmark (fast)
python scripts/tt_cli.py run --config configs/smoke.yaml

# Medium / publication
python scripts/tt_cli.py run --config configs/medium.yaml
python scripts/tt_cli.py run --config configs/publication.yaml

# Rebuild leaderboards
python scripts/tt_cli.py leaderboard
```

## Model API

```python
from models.forecasting import build_model, fit, predict, save, load, list_available_models

model = build_model("lightgbm", horizon=4, context_length=32, seed=0)
fit(model, X_train, y_train, X_val=X_val, y_val=y_val)
yhat = predict(model, X_test)
save(model, "results/models/example")
```

## Evaluation protocol (summary)

1. Primary track = **post-outage** segment only
2. Chronological 70% / 15% / 15% train / val / test
3. Windows never cross split boundaries or the outage gap
4. Scalers / HPO use train / validation only
5. Final test is untouched until Stage E reporting
6. Stochastic models: multiple seeds; report mean±std

## Config tiers

| Config | Purpose |
|--------|---------|
| `configs/smoke.yaml` | Dev / CI smoke |
| `configs/medium.yaml` | Main comparative benchmark |
| `configs/publication.yaml` | Full repeated study |

## Evaluation stages (important)

Existing smoke/medium_lite runs are **pilot** artifacts under `results/pilot/`.
They inspected the terminal chronological holdout and are **not eligible** for
final publication claims. See `docs/EVALUATION_PROTOCOL_V2.md`.

```bash
# Pilot leaderboards only
python scripts/tt_cli.py leaderboard --stage pilot

# Final leaderboards (refuses pilot / missing final runs)
python scripts/tt_cli.py leaderboard --stage final
```

Do **not** run `configs/publication.yaml` as a final claim surface until the
experiment freeze documented in Protocol V2.

## Citation / provenance

Dataset files dated 2025-02-13 in this workspace drop. Paper claims of 45 s sampling are **not** confirmed by the files present here.
