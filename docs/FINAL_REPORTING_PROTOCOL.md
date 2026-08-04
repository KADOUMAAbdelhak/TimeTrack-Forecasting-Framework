# Final reporting protocol

Separate freeze for aggregating accepted TimeTrack final evidence into
publication tables/figures. Does **not** retrain models or alter prediction /
analysis freezes.

| Layer | Tag |
|-------|-----|
| Predictions | `experiment-freeze-v2` |
| Statistics | `final-analysis-freeze-v1` |
| Peaks | `final-peak-analysis-freeze-v1` |
| Reporting | `final-reporting-freeze-v1` |

## Inputs

Only packs listed in `configs/final_evidence_registry.yaml`. Exclusions
(downsampling, optional packs, development studies) are **not** required.

## Rules

- Never pool raw MAE across CPU % / memory bytes / disk units.
- Distinguish **best observed** outer configuration from **recommended
  operational** configuration.
- Prefer pack CSV metrics; compute RMSE/R²/MASE from frozen NPZs only when
  needed and never by training.
- Hash all consumed artifacts before/after; abort if sources change.

## Entrypoint

```bash
python scripts/aggregate_final_evidence.py \
  --registry configs/final_evidence_registry.yaml \
  --reporting-config configs/final_reporting.yaml \
  --output results/final/aggregate
```
