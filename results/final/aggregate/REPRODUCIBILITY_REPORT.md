# Reproducibility report — final evidence aggregate

## Freeze layers

| Layer | Tag | Peeled commit |
|-------|-----|---------------|
| Predictions | experiment-freeze-v2 | bb34ddfc52f5f54f47f0ca644d7c95c619ad95a7 |
| Statistics | final-analysis-freeze-v1 | a93997feca8c2b383a1d0838410509fd582b2447 |
| Peaks | final-peak-analysis-freeze-v1 | 7586be02c0a6fa8432030753b159c63a5e8caa96 |
| Reporting | final-reporting-freeze-v1 | see MANIFEST |

Dataset fingerprint: `bf06dc0e7fe6ff5e`

## Regeneration

```bash
python scripts/tt_cli.py test
python scripts/aggregate_final_evidence.py \
  --registry configs/final_evidence_registry.yaml \
  --reporting-config configs/final_reporting.yaml \
  --output results/final/aggregate
```

Source prediction NPZs are not modified. See `SOURCE_ARTIFACT_HASHES.csv` and
`MANIFEST.json` (`source_files_unchanged`).

## Exclusions

Downsampling scientifically blocked; optional network/conformal/LSTM not
executed; adaptive router / global LOMO development-only.
