# Phase 4A Independent Data + Research-Scope Audit

Date: 2026-09-28
Decision: **B. EXTERNAL_CONFIRMATION_FEASIBLE_WITH_PROTOCOL_ADAPTATION**

Phase 4A was structural and prospective. It trained zero forecasting models, inspected zero external predictive outcomes, implemented zero architectures, and did not change any frozen conclusion.

## 1. Frozen-history verification

Preflight HEAD and annotated-tag target both equal `f9b11adb5dc3a0c2802703ceb1cbafb060c6f341`. The Phase 3D validator was rerun with the historical source paths and returned `PASS`.

- Phase 3D inventory: 37 entries, 445,981,302 bytes; inventory SHA-256 `cd3ea3d730e99546e52c55720508685e269bb77017fcde27ecd6cbf0dca2f7a2`; tree SHA-256 `eddfd8e347c95b3aad7d8a0d97ae592cd06483c4712243303ddacadf3f62cd4d`.
- Phase 3C inventory: 5,706 entries, 651,721,110 bytes; inventory SHA-256 `95bbb842f60bbc8c2c1bc11704c413e8e654594476d16c40850a217913c5155e`; tree SHA-256 `ec35446710f90a7b1e1a86cdbca6bedd4face31ec68ea56e83fd682addd89a65`.
- Frozen-history inventories all passed: Phase 3B 31/31, Phase 3A 25/25, Neural-v2 29/29, DLinear 1,347/1,347, LSTM 1,349/1,349, PatchTST 1,352/1,352, Phase 2A 33/33, original deterministic 632/632, corrected deterministic 1,070/1,070.
- All six TimeTrack raw hashes passed. The canonical panel remains `c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`.
- Phase 3D reports zero forecasting fits and zero post-Phase3C architecture implementations. Repository inspection found no external confirmation experiment, no TCN-v2 scientific run, and no multi-resource PatchTST run.

## 2. Datasets investigated and raw availability

The official Bitbrains fastStorage/Rnd and Materna archives were downloaded to ignored `data/external/raw/`. They total 442,438,944 bytes compressed. Exact URLs, archive hashes, member counts, and layouts are recorded in `01_dataset_audit/RAW_ARCHIVE_MANIFEST.csv`; licensing/acknowledgement notes are in `SOURCE_AND_ACQUISITION_RECORD.md`.

Alibaba 2018, Google 2019, and Azure VM traces remained metadata-only. Their official schemas already establish absence of the exact four-resource tuple, and their approximate compressed sizes (49 GB, 2.4 TiB, and 78.5/156 GB respectively) make completeness-only downloads unjustified.

## 3. Independence ledger

Bitbrains fastStorage and Rnd have not previously been used in this repository or, to the available record, another user project. No result for the current question has been seen. They are the pristine confirmation candidates. Materna has prior exposure in separate DynAPM research and is explicitly secondary, although no S1/S2/M1 result for this question has been inspected. Full classifications are in `01_dataset_audit/INDEPENDENCE_LEDGER.md`.

## 4. Exact schema and target compatibility

Bitbrains and Materna expose all four close analogues: CPU usage %, total network throughput formed as received plus transmitted KB/s, active/used memory KB, and disk-write throughput KB/s. These preserve the scientific resource meanings. Unit scale differs and TimeTrack’s throughput/disk raw rate units are unknown, so this is not an exact data replication.

Alibaba’s disk field is utilization rather than write activity and cannot be silently substituted. Google lacks comparable network/disk-write targets. Azure provides CPU time series and static memory capacity rather than the required dynamic tuple. Exact field-level decisions are in `02_harmonization/TARGET_HARMONIZATION_MATRIX.csv`.

## 5. Structural audit: sampling, coverage, and quality

The scanner read official CSV members directly from each ZIP. Bitbrains headers label the timestamp as milliseconds, but raw 10-digit values resolve as Unix seconds; all environment medians are exactly 300 seconds. Materna uses day-first wall-clock strings and comma decimals; these were parsed explicitly and its cadence is also 300 seconds.

| Environment | VMs | Observations | UTC coverage | Median VM span | Missing required values | Duplicate timestamps | Invalid required values | Eligible VMs |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| Bitbrains fastStorage | 1,250 | 11,221,800 | 2013-08-12 to 2013-09-11 | 30.00 d | 0 | 452,577 | 319,082 | 916 |
| Bitbrains Rnd | 500 | 12,496,728 | 2013-06-30 to 2013-09-29 | 91.00 d | 0 | 168,359 | 221,529 | 416 |
| Materna trace 1 | 519 | 4,167,978 | 2015-11-05 to 2015-12-03 | 29.00 d | 84 | 0 | 0 | 475 |
| Materna trace 2 | 527 | 4,510,858 | 2015-12-04 to 2016-01-03 | 31.00 d | 0 | 0 | 0 | 483 |
| Materna trace 3 | 547 | 5,329,730 | 2016-01-04 to 2016-02-08 | 36.00 d | 0 | 0 | 0 | 495 |

The official Materna page describes 520 VMs in month 1; the downloaded official archive contains 519 CSV members, which is the raw-audited count used here. “Invalid” means negative resource values or CPU outside [0,100]; it is a structural count, not a prediction result. Duplicate and invalid rows are not repaired in Phase 4A. Entity-level details and exact eligibility are in `ENTITY_STRUCTURAL_ELIGIBILITY.csv`.

## 6. Four-resource eligibility and entity selection

Eligibility requires no duplicate timestamps, at least 14 days, at least 95% physically valid four-resource rows, four nonconstant targets, 300±1-second median cadence, and a contiguous run of at least 2,016 observations with gaps no larger than 450 seconds. The future design selects 35 eligible VMs per Bitbrains environment using an ascending SHA-256 rank over environment and ID. Materna uses 35 IDs from the 398 structurally eligible VMs shared across all three months. This policy is fully outcome-independent and specified in `03_evaluation_design/ENTITY_SELECTION_POLICY.md`.

## 7. Real-time horizon harmonization

The largest defensible common grid is **5, 10, 20, 45, and 90 minutes**. TimeTrack maps these to frozen leads [8,16,32,64,128], whose actual durations are 5.638, 11.276, 22.552, 45.104, and 90.208 minutes. Five-minute traces use [1,2,4,9,18] exactly. The predeclared tolerance is `max(2.5 minutes, 15% of the desired horizon)`; every mapping passes. See `02_harmonization/REAL_TIME_HORIZON_HARMONIZATION.csv`.

## 8. Context-window harmonization

The common contexts are approximately 22.5, 45, and 90 minutes. TimeTrack retains [32,64,128] samples (22.552, 45.104, 90.208 minutes); external traces use [4,9,18] samples (20,45,90 minutes). All mappings pass the same duration tolerance. See `CONTEXT_WINDOW_HARMONIZATION.csv`.

## 9. Transformation compatibility

CPU and memory retain identity; total throughput and disk-write retain log1p. Bitbrains/Materna values support these assumptions after prospectively removing physically invalid rows. All median/IQR scalers remain training-only and transformations retain exact inverse rules. No transformation may be changed after predictive results are seen. The audit is recorded in `TRANSFORMATION_COMPATIBILITY.csv`.

## 10. Bitbrains assessment

Both environments support the required tuple at 5-minute cadence with adequate durations and hundreds of eligible VMs. Raw duplicate and invalid records make structural filtering and support hashes essential. fastStorage and Rnd should remain **separate, equally weighted confirmation environments** because they represent distinct storage/workload conditions and have materially different duration/quality profiles. Combining them would hide environment heterogeneity; assigning one to development would unnecessarily consume pristine evidence.

## 11. Materna assessment

The three traces are adjacent monthly blocks with 519, 527, and 547 raw VM files. All 519 trace-1 IDs appear in traces 2 and 3; 527 IDs are shared between traces 2 and 3; 519 exist in all three. This strong continuity means month 3 is not an independent entity holdout. Moreover, prior DynAPM exposure prevents an untouched-confirmation claim. The convenient development/validation/confirmation split is therefore rejected. Materna may be used only as a prespecified secondary temporal replication with a common cohort after primary Bitbrains analysis is locked.

## 12. New TimeTrack data feasibility

Classification: **UNKNOWN_REQUIRES_CONTACT**. The repository contains the six original CSVs and analysis/forecasting machinery but no collector, exporter configuration, deployment credentials, later telemetry, or evidence that the seven hosts still exist. No external contact was made. Details are in `04_research_scope/NEW_TIMETRACK_DATA_FEASIBILITY.md`.

## 13. Future external S1/S2/M1 design

The future design preserves the plain two-layer LSTM backbone, S1/S2/M1 distinctions, seed handling, training-only transforms/scalers, common support, five chronological folds, maximum-lead purging, seed-mean context selection, per-seed fixed-epoch final refit, matched comparisons, and resource-specific macro aggregation. Only data fields, physical units, entity IDs, timestamps, and sample-index representations of elapsed time vary by dataset.

With 35 VMs per Bitbrains environment it entails 14,175 inner and 4,725 final fits per environment. Exact folds/support and selected-ID hashes must be frozen before any scientific run. The full prospective design is in `03_evaluation_design/EXTERNAL_REPLICATION_DESIGN.md`.

## 14. Publication scope and novelty/risk audit

Scope A, a multi-dataset empirical boundary study, is the recommended research direction. The potential contribution is not a new neural architecture; it is the controlled evidence package around cross-resource context utility, naive-sharing negative transfer, real-time multi-horizon matching, common support, efficiency, and independent environment replication.

Scope B is not justified because developing a method on Bitbrains would consume pristine evidence and require another untouched source. Scope C is premature while two compatible confirmation environments exist. Merely adding experiments, common models, metrics, or public datasets is not novel. A bounded literature check supports positioning this as an empirical/methodological boundary study, subject to a fresh formal review before writing. Risks and minimum evidence are detailed in `04_research_scope/PUBLICATION_SCOPE_AND_NOVELTY_AUDIT.md`.

## 15. Dataset roles

- Bitbrains fastStorage: `PRIMARY_EXTERNAL_CONFIRMATION`.
- Bitbrains Rnd: `PRIMARY_EXTERNAL_CONFIRMATION`.
- Materna: `SECONDARY_EXTERNAL_REPLICATION`.
- Alibaba 2018: `STRUCTURALLY_INCOMPATIBLE`.
- Google 2019: `STRUCTURALLY_INCOMPATIBLE`.
- Azure VM traces: `STRUCTURALLY_INCOMPATIBLE`.
- Later TimeTrack telemetry: `NOT_NEEDED_UNLESS_OBTAINED` under the present audit; potentially strongest exact temporal confirmation if obtained and audited.

## 16. Minimum evidence before manuscript writing

Freeze the external protocol/IDs/support first; complete and independently validate both Bitbrains environments; report the predeclared H1-H3 matched comparisons separately and under equal-environment synthesis; establish that invalid/duplicate handling and unit inversion do not drive the result; and perform final literature plus licensing/acknowledgement review. Materna can strengthen robustness but cannot replace pristine Bitbrains evidence.

## 17. Decision gate and execution boundary

**B. EXTERNAL_CONFIRMATION_FEASIBLE_WITH_PROTOCOL_ADAPTATION.**

The adaptation is limited to elapsed-time lead/context mapping and dataset-specific fields/units. Phase 4A authorizes no training. No S1/S2/M1 model, TimeTrack retraining, new architecture, gate, weighting method, TCN-v2 run, or multi-resource PatchTST run was executed. No commit or push was performed.
