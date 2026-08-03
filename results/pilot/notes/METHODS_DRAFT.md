# Methods Draft (from implemented code)

## Data

TimeTrack CSVs mirrored under `data/raw/`. Analysis panel built by `timetrack.data.build_analysis_panel` joining compute, disk, network, throughputs, and packet aggregates on timestamp.

## Splits

`post_outage_split`: chronological 70/15/15 on rows with `segment==post_outage`. Windows constructed so context and horizon indices lie entirely inside one split (`timetrack.splits`).

## Models

Registered via `models.forecasting`: persistence, seasonal_persistence, historical_mean, moving_average, ewma, drift, ridge/lasso/elasticnet, RF/ET/LightGBM/XGBoost/(CatBoost), MLP/LSTM/GRU/TCN/DLinear.

## Metrics

MAE, MSE, RMSE, MedAE, MaxAE, R² (negative preserved), sMAPE, MAPE with exclusion of `|y|<eps`, MASE, nRMSE, peak precision/recall vs train 95th percentile.

## Hyperparameters

Smoke uses defaults / light budgets in `configs/smoke.yaml`. Optuna planned in medium/publication configs; not required for smoke.
