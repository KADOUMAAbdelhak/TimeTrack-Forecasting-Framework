# Reproducibility report v2 — robustness-aware aggregate

## Freeze layers

| Layer | Tag | Peeled commit |
|-------|-----|---------------|
| Predictions | experiment-freeze-v2 | bb34ddfc52f5f54f47f0ca644d7c95c619ad95a7 |
| Statistics | final-analysis-freeze-v1 | a93997feca8c2b383a1d0838410509fd582b2447 |
| Peaks | final-peak-analysis-freeze-v1 | 7586be02c0a6fa8432030753b159c63a5e8caa96 |
| Robustness extension | final-robustness-extension-freeze-v2 | 9750626607e4bf8bc6d45f89f6ee5805c87f3251 |
| Robustness statistics | final-robustness-analysis-freeze-v2 | a4337a8e11c62205ac7aa4002d0059327159017f |
| Reporting | final-reporting-freeze-v2 | 4408cd1733d57014026cfa6fb477842fe4645a20 |

Dataset fingerprint: `bf06dc0e7fe6ff5e`  
Scientific protocol hash: `8bce84c8007fa60d`  
Provenance envelope hash: `323036f95a253e82`

## Regeneration

```bash
python scripts/tt_cli.py test
python scripts/aggregate_final_evidence_v2.py \
  --registry configs/final_evidence_registry_v2.yaml \
  --config configs/final_reporting_v2.yaml \
  --output results/final/aggregate \
  --require-frozen
```

Source prediction NPZs are not modified. See `SOURCE_ARTIFACT_HASHES.csv`.
Pre-robustness aggregate archived at `results/final/archive/pre_robustness_aggregate/`.
