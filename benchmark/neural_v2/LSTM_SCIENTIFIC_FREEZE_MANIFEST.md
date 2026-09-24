# Neural-v2 LSTM Scientific Freeze Manifest

## Checkpoint identity

- Freeze date: 2026-09-24 (Europe/Helsinki)
- Pre-freeze HEAD: `2aa7e795fa3c7ccb5657ced43c19eb3e5922a1b6`
- Neural-v2 protocol checkpoint: `08697069cf54f4c94cbd2a449b3e2050405328fb`
  (`neural-v2-protocol-freeze-v1`)
- DLinear scientific checkpoint: `2aa7e795fa3c7ccb5657ced43c19eb3e5922a1b6`
  (`neural-v2-dlinear-scientific-freeze-v1`)
- LSTM prospective-decision criteria SHA-256:
  `ac5630eb55e4034a60ee32f778e5c0c1f251a8877d1216c2f3b21bbc1a13a4f6`

## Frozen architecture and training identity

The frozen model consumes `[batch, L, channels]`, with one F0 channel or two
F1 channels. It is a two-layer, unidirectional LSTM with hidden size 64,
dropout 0.1 between recurrent layers, the final recurrent representation, and
an eight-value CPU forecast head for real leads `[1,2,4,8,16,32,64,128]`.
Parameter counts are 50,952 for F0 and 51,208 for F1.

Training used Adam, learning rate 0.001, batch size 256, MSE loss, maximum 50
epochs, patience 7, gradient clipping 1.0, seeds `[0,1,2]`, and train-only
preprocessing. Context was selected from `[32,64,128]` using seed-mean inner
validation MAE over all eight leads with a smaller-L tie-break. Every final
refit used its seed's selected fixed epoch and never used outer-test labels for
selection, fitting, or early stopping.

## Execution and runtime

- Inner fits: 630
- Final fits: 210
- Total fits: 840
- Lead-level metric rows: 1,680
- Selected-context records: 70
- Prediction files: 210
- Figures: 5
- Inner-selection wall time: 37,203.074 seconds
- Final-refit wall time: 14,671.802 seconds
- Scientific execution wall time: 51,947.052 seconds
- Total recorded wall time including analysis and validation: 51,956.105 seconds
- Peak recorded RSS: 704,839,680 bytes
- Prediction artifact bytes: 49,964,838

Selected-L counts:

| Feature | L=32 | L=64 | L=128 |
|---|---:|---:|---:|
| F0_LOCAL | 8 | 14 | 13 |
| F1_THROUGHPUT | 10 | 14 | 11 |

The 210 per-seed selected epochs range from 2 through 50, with mean 30.638,
median 34, and 39 selections at epoch 50. The complete distribution is frozen
in `outputs/lstm/runtime_accounting.json` and `outputs/lstm/selected_epochs.csv`.
Across all 630 inner fits, mean best epoch was 29.160 and median best epoch was
30.

## Validation and prospective decision

Independent validation status: **PASS**.

Validation confirmed exact run/metric coverage, all seeds and real leads, zero
duplicate or missing runs, zero segment crossings, zero target-time leakage,
zero F0/F1 support mismatches, train-only preprocessing, inner-only context
selection with the correct tie-break, per-seed fixed-epoch final refits, exact
timestamps and targets, and exact metric recomputation.

The authoritative prospective LSTM decision is **CONDITIONALLY_POSITIVE**. Its
criteria file existed before the first LSTM fit and used the frozen **mean
matched cell-level relative MAE gain** definition. Accepted prospective
quantities are:

- overall mean cell-relative gain: +3.087%;
- positive lead cell-means: 8/8;
- positive machine aggregates: 4/7;
- positive fold aggregates: 5/5; and
- positive seed aggregates: 3/3.

## Post-audit aggregation summaries

The aggregation audit preserved the prospective result while separating it
from later cross-model reporting. LSTM overall summaries are:

- mean matched cell-relative gain: +3.087%;
- ratio of macro-aggregated matched MAEs: +1.252%; and
- pooled-prediction MAE gain: +0.849%.

At lead 1, the prospective cell-relative gain is +2.3506%, while the macro-MAE
ratio is -2.4070% and pooled gain is -2.8834%. Positive cells tended to have
smaller baseline MAE, while fewer negative cells had larger baseline MAE and
larger absolute degradation. Leads 2 through 128 are positive under all three
summaries.

The audit found that accepted Ridge, LightGBM, DLinear, and LSTM headline gains
all used the same mean matched cell-relative percentage definition, with seed
replicates additionally present for neural models. No prediction or trained
model was changed.

## Post-audit cross-model reporting identity

Future cross-model reporting uses the separately frozen **POST-AUDIT REPORTING
STANDARD** in `CROSS_MODEL_AGGREGATION_STANDARD.md`. Its primary statistic is
the ratio of separately macro-aggregated matched F0 and F1 MAEs, with neural
seeds averaged within machine-fold-lead cells before equal machine-fold
weighting. Pooled gain and cell-relative distribution summaries remain
secondary.

- Aggregation-standard SHA-256:
  `327ad544769fc13fc619f6d60abf9fa8f206863fa231a8f325c5220217403875`
- Cross-model CSV SHA-256:
  `f129c67e68ce1f028de77ffd6796d24d416abbb866d6b139b9984e74065bc218`
- Cross-model report SHA-256:
  `372e546f02b7daa2581f27f3e8d43c74d9a14ee8a2da4ee4042275873689834e`
- Aggregation-audit document SHA-256:
  `e969f6dff5c4165ea27250394e71baacef3041190384253c9a1a85e80815846f`

**This reporting standard was selected after model results existed and does
not retroactively redefine the prospective LSTM decision or any other frozen
decision label.**

## Heavy scientific artifact preservation

The local LSTM scientific output tree under `benchmark/neural_v2/outputs/lstm/`
was not deleted or regenerated during freeze creation.

- Files: 1,349
- Bytes: 52,475,190
- Output-tree SHA-256:
  `5fd46acfad0b49adad0b7a88961bab41b53c3ad6741ca89b340ef04408a4ce23`
- Inventory SHA-256:
  `d67142e064478670df91470eabca059c67de03766050cdc54f087e158591c88f`

`LSTM_SCIENTIFIC_ARTIFACT_SHA256.csv` records repository-relative path, byte
size, and SHA-256 for every local LSTM output, including ignored heavy parquet
predictions and atomic progress records. The tree digest is computed over
sorted records encoded as `path + NUL + sha256 + newline`. Heavy predictions
remain local and are represented by the committed inventory rather than being
blindly staged.

## Frozen-history integrity

- Neural-v2 source/test/config inventory: 29/29 unchanged.
- DLinear scientific inventory: 1,347/1,347 unchanged.
- Phase 2A: 33/33 unchanged.
- Original deterministic inventory: 632/632 unchanged.
- Corrected deterministic inventory: 1,070/1,070 unchanged.
- Raw hashes: unchanged.
- Canonical panel SHA-256:
  `c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`.
- Neural-v2 tests: 28/28 passed.
- PatchTST scientific runs: 0.
- TCN-v2 scientific runs: 0.
- Multi-target scientific models: 0.
