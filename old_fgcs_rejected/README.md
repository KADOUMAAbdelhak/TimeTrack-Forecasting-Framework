# TimeTrack Forecasting Framework

Leakage-safe, multi-metric infrastructure time-series forecasting for the
TimeTrack OpenAirInterface CI/CD telemetry dataset, aimed at predictive
resource management for cloud-edge and distributed systems.

**Official repository:** https://github.com/KADOUMAAbdelhak/TimeTrack-Forecasting-Framework

This is **not** a reproduction of prior CPU-only TimeTrack papers. Those are
literature baselines. Version-control and artifact rules:
[`docs/VERSION_CONTROL_POLICY.md`](docs/VERSION_CONTROL_POLICY.md).

## Repository contents

- **Code:** `timetrack/`, `models/`, `experiments/`, `configs/`, `scripts/`, `tests/`
- **Docs:** audit, research plan, experiment matrix, evaluation protocol V2, publication gates
- **Results:** lightweight summaries under `results/pilot/` (and later `results/final/`)
- **Raw data:** **not** distributed via Git — restore locally (see below)

## Dataset (not in Git)

Obtain the six TimeTrack CSV files from the authorized dataset source and place
them at the project root **or** under `data/raw/`:

- `compute_dataset.csv`
- `detailed_cpu_cores_dataset.csv`
- `disk_dataset.csv`
- `network_dataset.csv`
- `packet-loss-dataset.csv`
- `throughputs_dataset.csv`

Verify identity:

```bash
python scripts/tt_cli.py audit
```

Compare `dataset_fingerprint` to recorded manifests. Median sampling in this
drop is ≈ **42.3 s** (not 45 s); see `docs/DATASET_AND_REPOSITORY_AUDIT.md`.

## Environment setup

```bash
cd /Users/fgtek002/TimeTrack   # or your clone path
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Smoke test

```bash
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python scripts/tt_cli.py test
python scripts/tt_cli.py run --config configs/smoke.yaml
```

`configs/smoke.yaml` is **`experiment_stage: pilot`**. Outputs go under
`results/pilot/` and are **not final evidence**.

## Development benchmark

```bash
python scripts/tt_cli.py run --config configs/medium_lite.yaml
# optional inner-fold HPO example:
python scripts/tune_optuna.py --target cluster_mean_CU --model ridge --horizon 1 --trials 20
```

Do **not** treat pilot/development leaderboards as FGCS final results. Protocol:
[`docs/EVALUATION_PROTOCOL_V2.md`](docs/EVALUATION_PROTOCOL_V2.md).

```bash
python scripts/tt_cli.py leaderboard --stage pilot
python scripts/tt_cli.py leaderboard --stage final   # refuses pilot / missing finals
```

`configs/publication.yaml` must not be used for claim-making until an
`experiment-freeze-v*` tag.

## Model API

```python
from models.forecasting import build_model, fit, predict, save, load, list_available_models

model = build_model("lightgbm", horizon=4, context_length=32, seed=0)
fit(model, X_train, y_train, X_val=X_val, y_val=y_val)
yhat = predict(model, X_test)
```

## Config tiers

| Config | Stage | Purpose |
|--------|-------|---------|
| `configs/smoke.yaml` | pilot | Fast pipeline check |
| `configs/medium_lite.yaml` | pilot | Expanded development screen |
| `configs/medium.yaml` | development | Broader nested-dev work |
| `configs/publication.yaml` | blocked until freeze | Final outer-fold study |

## Critical verified data facts

- Median sampling ≈ **42.3 s** (not 45 s)
- Span 2024-06-24 → 2024-07-19 with a **~4.87-day outage**
- Seven machines; packet **errors are all zero** in this download

## Provenance note

Dataset files in the original workspace drop are dated 2025-02-13. Paper claims
of 45 s sampling are **not** confirmed by the files present here.
