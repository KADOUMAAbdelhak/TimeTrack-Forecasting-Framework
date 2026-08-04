# TimeTrack FGCS Manuscript Workspace

**Title:** Hierarchy-Aware Forecast Reconciliation for Multi-Level Cloud Telemetry: Accuracy Gains, Trade-offs, and Failure Boundaries

**Target journal:** Future Generation Computer Systems (Elsevier CAS double-column, `cas-dc`)

## Scope

Primary contribution: hierarchy-aware CPU forecasting with exact reconciliation.
Secondary: conditional memory reconciliation (EWMA remains strongest observed).
Boundary: disk reconciliation failure modes.
Operational qualification: ordinary aggregate-MAE gains do not imply universal peak gains.
Robustness: EWMA baseline and three-seed LightGBM/DLinear evaluation.

## Authoritative sources (do not replace with development/pilot results)

- `../results/final/aggregate/` and its V2 claim/reproducibility documents
- `../docs/FGCS_PUBLICATION_READINESS_FINAL.md`
- `../docs/FINAL_REPORTING_PROTOCOL_V2.md`

## Exclusions

Do not use archived pre-robustness aggregate, development/pilot results, rejected LightGBM seed pack v1, mutated robustness statistics v1, provisional DLinear summaries, downsampling, network, conformal, LSTM, adaptive routing, or LOMO results.

## Directory structure

```
fgcs/
├── manuscript.tex
├── references.bib
├── highlights.txt
├── README.md
├── BUILD.md
├── CLEANUP_REPORT.md
├── cas-dc.cls / cas-common.sty / cas-model2-names.bst
├── figs/
├── tables/
├── results/{main,supplementary,provenance}/
├── supplementary/
├── scripts/
└── dist/   (generated locally; usually not committed)
```

## Build / validate / package

From this directory:

```bash
python scripts/validate_manuscript.py
bash scripts/build_manuscript.sh
bash scripts/package_overleaf.sh
bash scripts/verify_overleaf_package.sh
```

See `BUILD.md` for the full local absolute-path command block.

## Final evidence freezes

`experiment-freeze-v2`, `final-analysis-freeze-v1`, `final-peak-analysis-freeze-v1`,
`final-robustness-extension-freeze-v2`, `final-robustness-analysis-freeze-v2`,
`final-reporting-freeze-v2`.
