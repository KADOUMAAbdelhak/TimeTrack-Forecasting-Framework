# Related Work revision audit (Stage 2)

Date: 2026-08-05  
Base Introduction commit: `5ff867d`  
Revision commit: (see git after push)

## Length

| Metric | Before | After |
|--------|--------|-------|
| Approximate word count | ~304 | ~1244 |
| Rendered Related Work | ~0.55–0.7 double-column pages | ~2.0–2.3 pages including Table~1 (starts late article p.~2; §3 begins article p.~5) |
| Article page count | 11 | 12 |
| PDF pages (with highlights) | 12 | 13 |
| Substantive prose paragraphs | ~6 | 13 |
| Unique references cited in §2 | 25 | 34 |
| Citation instances in §2 | — | 51 |

## Paragraph-purpose map

### 2.1 Application profiling (3 paragraphs)
1. Profile/lifecycle encodings and multi-granularity orchestration loops.
2. Telemetry-aware adaptation; multi-level consistency difficulty; contrast with forecast-only management.
3. Prior unified profile paper continuity; this paper evaluates coherent forecasts, not a new schema.

### 2.2 Cloud telemetry and forecasting (5 paragraphs)
1. Classical persistence/smoothing/ARIMA; why EWMA/persistence remain evaluation hygiene.
2. ML/tree/neural practice as independent-stream model selection.
3. Deep forecasting caution; DLinear/LightGBM as competitive baselines, not novelty claims.
4. Cloud-native/edge controllers; signature/spike literature motivating RQ5.
5. TimeTrack / Kaggle / Zero-Touch distinctions; this paper’s reconciliation scope.

### 2.3 Hierarchical forecasting and reconciliation (5 paragraphs)
1. Base vs coherent forecasts; summing-matrix concept (equations deferred).
2. BU/TD/OLS/WLS assumptions and error propagation.
3. MinT + shrinkage + geometric/linear extensions; no new algorithm claim.
4. Probabilistic/review context (Athanasopoulos 2024; Panagiotelis 2023).
5. HARMONY / FRT / MaMiClif as adjacent computing hierarchies with different semantics.

### 2.4 Research gap (2 paragraphs)
1. Synthesis of independent-stream forecasting, non-infra HTS empirics, and incomplete computing hierarchical evaluations.
2. Scoped addition relative to closest work; link to RQ1–RQ5 without contribution dump.

## Unique references cited in Section 2 (34)

agullo2025spikes, ashouri2022fast, athanasopoulos2024hierarchical, buyya2019manifesto, calheiros2015workload, casalicchio2019container, duc2020survey, gao2026mamiclif, harmony2024, hyndman2011optimal, hyndman2021forecasting, islam2012empirical, kadouma2025unifiedprofile, ke2017lightgbm, khan2022workload, lim2021temporal, lorido2014review, makridakis2018statistical, masdari2020workload, meliani2025timetrack, meliani2025timetrackkaggle, meliani2026zerotouch, panagiotelis2021geometric, panagiotelis2023probabilistic, qu2018auto, rossi2020geo, schafer2005shrinkage, sus2024signature, taherizadeh2018monitoring, toka2021kubernetes, wang2025frt, wen2023transformers, wickramasuriya2019mint, zeng2023dlinear

### Year buckets (by bibliography year)
- 2021–2026: 19
- 2022–2026: 15
- Before 2021: 15

## Newly added bibliography entries (verified)

| Key | Verification source | Status |
|-----|---------------------|--------|
| wang2025frt | Crossref DOI 10.1145/3711896.3737224 (KDD 2025) | peer-reviewed proceedings |
| gao2026mamiclif | Crossref DOI 10.1145/3774904.3792125 (WWW 2026) | peer-reviewed proceedings |
| ashouri2022fast | Crossref DOI 10.1080/10618600.2021.1939038 | peer-reviewed journal |
| panagiotelis2023probabilistic | Crossref DOI 10.1016/j.ejor.2022.07.040 | peer-reviewed journal |
| agullo2025spikes | Crossref DOI 10.1016/j.future.2025.107833 | peer-reviewed journal (FGCS) |
| sus2024signature | Crossref DOI 10.1007/s10723-024-09764-4 | peer-reviewed journal |
| harmony2024 (updated authors) | arXiv abs/2408.01000 citation_author meta | preprint |

## Removed references
None removed from the bibliography. Table row set changed: Zero-Touch retained; TimeTrack dataset paper cited in prose; Hyndman 2011 and MinT retained as methodological comparators; HARMONY/FRT/MaMiClif verified and retained.

## Comparison table studies
1. Hyndman et al. 2011 (OLS combination)
2. Wickramasuriya et al. 2019 (MinT)
3. HARMONY / Luo et al. 2024 (E2E multi-indicator)
4. FRT / Wang et al. 2025 (E2E flow recon)
5. MaMiClif / Gao et al. 2026 (macro–micro collaborative)
6. Zero-Touch / Meliani et al. 2026 (model generation)
7. Kadouma et al. 2025 (unified profile)
8. This work

All table studies are cited in prose. No supplementary extended table required for this stage.

## Key analytical distinctions added
- Profile representation vs coherent predictive signals
- Independent-stream forecasting vs exact machine-to-cluster summing
- Classical post-hoc MinT/WLS/BU/TD vs E2E neural hierarchical methods (HARMONY/FRT) and microservice collaborative learning (MaMiClif)
- TimeTrack dataset paper / Kaggle / Zero-Touch / this reconciliation study
- Average MAE vs peak/spike operational evaluation (RQ5 motivation)

## Unsupported-claim review
Section 2 does **not** claim: first cloud reconciliation study; SOTA; all prior work ignores hierarchy; universal MinT superiority; TimeTrack creation; Zero-Touch reconciliation; evaluated profile integration; cross-dataset numerical superiority; universal reconciliation or peak gains.

## Layout result
- `bash scripts/build_manuscript.sh`: BUILD OK
- `python scripts/validate_manuscript.py`: OK
- compilation errors: 0
- unresolved citations/references: 0
- overfull boxes: 0
- article pages: 12
- §3 starts cleanly after Table~1
- Introduction and §§3–8 not edited (except §2 content/table/bib)
