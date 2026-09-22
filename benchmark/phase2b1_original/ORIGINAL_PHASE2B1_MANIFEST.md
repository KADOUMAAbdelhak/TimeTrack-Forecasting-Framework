# Original Phase 2B-1 Artifact Manifest

## Identity and status

- Preservation label: `ORIGINAL_PHASE2B1_NONCONFORMING_MATCHED_TRAIN_COMPARATOR`
- Repository HEAD: `0b4269270b0a121f0ba1e19355c6cd24b72abeb5`
- Active branch at preservation: `main`
- Phase 2A freeze tag: `phase2a-benchmark-protocol-freeze-v1`
- Recoverable execution interval from prediction-file timestamps:
  `2026-09-21 17:45:52 +0300` through `2026-09-22 01:16:27 +0300`
- Completed outer runs: 630
- Lead-level metric rows: 5,040
- Selected deterministic configurations: 420
- Prediction files: 630
- Stored validation status: PASS

These results are numerically valid for their executed row semantics, but the
contextual F0 comparison is not fully protocol-conforming for matched training
support. The F1-F5 candidates were trained on their feature-specific finite
rows. The reported matched F0 metric instead reused the independently selected
and independently trained standalone F0 model and restricted only its test
predictions to the candidate's test rows. It did not retrain F0 on the
candidate's exact training rows.

The raw predictions and results are preserved evidence. They must not be
silently replaced, overwritten, or relabelled as corrected results.

## Runtime record

| Family | Wall seconds | Candidate fits | Final models |
|---|---:|---:|---:|
| Persistence | 3.598026 | 0 | 0 |
| Ridge | 7.857147 | 3,150 | 210 |
| LightGBM | 26,982.400054 | 40,320 lead fits | 1,680 lead models |

Total recorded wall time, including analysis: 27,003.637989 seconds.

## Preserved compact artifacts

Exact copies are under `artifacts/` and include:

- the execution, analysis, and validation scripts;
- `DETERMINISTIC_BENCHMARK_REPORT.md`;
- run and selected-configuration registries;
- deterministic aggregate, context, runtime, and validation tables;
- all six deterministic figures.

Individual sizes and SHA-256 values for the 18 compact files are recorded in
`COMPACT_ARTIFACT_SHA256.csv`.

- Compact artifact bytes: 2,495,968
- SHA-256 of `COMPACT_ARTIFACT_SHA256.csv`:
  `e7c3eaa3c92625ab8175131d14960eb6d8a77aea85b2aed864823734d6cc5f55`

The copied script hashes are:

| Script | SHA-256 |
|---|---|
| `run_deterministic_benchmark.py` | `88dafd6ed17ee44b1a4cf0842a4885f561cd378a73155e81d6cefa72d787e39b` |
| `analyze_deterministic_benchmark.py` | `b75d2475528d76367b7d9cba79a1075ca2915104d53459867ffc9b4ac4d5d67f` |
| `validate_deterministic_benchmark.py` | `39ed8a25c7dc7888d0c53dceb881da3d5498c7594308394e2139118a1617580b` |

## Preserved ignored heavy artifacts

The heavy artifacts remain at their original paths under
`benchmark/outputs/`; they were not duplicated. `HEAVY_ARTIFACT_SHA256.csv`
records the path, byte size, and SHA-256 of every file:

- `benchmark/outputs/metrics.parquet`;
- `benchmark/outputs/context_matched_metrics.parquet`;
- all 630 files under `benchmark/outputs/predictions/`.

Inventory totals:

- Heavy files: 632
- Total heavy bytes: 87,452,754
- Prediction bytes: 86,955,568
- SHA-256 of `HEAVY_ARTIFACT_SHA256.csv`:
  `fb9a426089f65e97b2dd542de8cea078c905d08ae8a8eb7dabf06871425e4d62`

Any future correction must write to new paths and verify that all entries in
this inventory remain byte-identical.

## Audit artifacts

- `matched_f0_row_mismatch.csv` contains all 350 Ridge/LightGBM contextual
  model-feature-machine-fold comparisons.
- SHA-256 of `matched_f0_row_mismatch.csv`:
  `5f369d63e08add5e4a942890c3549083e722cfd04f9686f350c0684d13dcec52`
- `MATCHED_F0_PROTOCOL_AUDIT.md` records the literal protocol interpretation.
- `TCN_RECEPTIVE_FIELD_NOTE.md` records the frozen TCN receptive field.
- `ENVIRONMENT_SNAPSHOT.md` and `package_freeze.txt` record the available
  execution environment without rebuilding it.
