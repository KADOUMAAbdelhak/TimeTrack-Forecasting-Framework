# STAGE 18A1 REVIEWER-CHALLENGE DIAGNOSTIC REPORT

Date: 21 October 2026 (Europe/Helsinki)  
Branch: `paper/jss-review-revision`  
HEAD: `f6936cd111d911e40ec2725a18fdfc53768d9ccf`  
Scientific parent: `fee20c316040c57b69ba12a193530c955b539771`

## 1. Status, scope and source precedence

**STAGE_18A1_PASS — diagnostic audit completed. No scientific implementation/data/scaling defect demonstrated by the inspected evidence.** This is not a claim that optimisation is ideal or that a sharing mechanism has been isolated.

A material manuscript-description conflict requires later clarification: inner context selection uses **transformed-and-scaled validation MAE**, whereas the manuscript calls it NMAE without distinguishing it from **native MAE / native training IQR**. The frozen TimeTrack protocol explicitly specifies transformed/scaled validation MAE, and the external execution inherits that implementation. This is reported as a documentation/estimand distinction, not silently treated as a new algorithm or as proof the frozen fits are defective.

Precedence applied: frozen results/manifests; exact configuration/provenance; executable training/evaluation code; persisted per-fit/per-seed records; logs; manuscript. Reviewer interpretations were tested, not accepted as facts.

All newly calculated diagnostic summaries below are **POST-HOC DIAGNOSTICS, NOT FROZEN PRIMARY RESULTS**. Frozen primary gains, syntheses, classifications and bootstrap endpoints were read from existing files, not recalculated. No bootstrap draws or new confidence intervals were generated. Capacity arithmetic, seed-specific aggregates, context pairings, per-VM summaries, training-accounting summaries, raw training-distribution checks and affine validation-score rank checks are diagnostic computations authorised by this task.

## 2. Diagnostic artifact inventory (established before interpretation)

Artifact-root aliases (paths are authoritative local artifacts):
- T: [multiresource/04_lstm_factorial/outputs/scientific](/Users/fgtek002/TimeTrack/multiresource/04_lstm_factorial/outputs/scientific)
- B: [independent_validation/05_bitbrains_factorial/outputs/scientific_v2](/Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/outputs/scientific_v2); separate `fastStorage/` and `Rnd/`.
- M: [independent_validation/06_materna_replication/outputs/scientific_v1](/Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/outputs/scientific_v1); separate `Materna-T1/`, `Materna-T2/`, `Materna-T3/`.

| Evidence block | Metric rows | Final networks S1 / S2 / M1 | Predictions/targets | Selections and histories |
|---|---|---|---|---|
| TimeTrack | 10080 | 420 / 420 / 105 | Per-final-fit Parquet: seed, target, native prediction, scaled prediction, support IDs | selected_contexts.csv; selected_epochs.csv; inner/final registries; M1 per-epoch histories |
| fastStorage | 31500 | 2100 / 2100 / 525 | Per-final-fit Parquet: seed, target, native prediction, scaled prediction, support IDs | selected_contexts.csv; selected_epochs.csv; inner/final registries; M1 per-epoch histories |
| Rnd | 31500 | 2100 / 2100 / 525 | Per-final-fit Parquet: seed, target, native prediction, scaled prediction, support IDs | selected_contexts.csv; selected_epochs.csv; inner/final registries; M1 per-epoch histories |
| Materna-T1 | 31500 | 2100 / 2100 / 525 | Per-final-fit Parquet: seed, target, native prediction, scaled prediction, support IDs | selected_contexts.csv; selected_epochs.csv; inner/final registries; M1 per-epoch histories |
| Materna-T2 | 31500 | 2100 / 2100 / 525 | Per-final-fit Parquet: seed, target, native prediction, scaled prediction, support IDs | selected_contexts.csv; selected_epochs.csv; inner/final registries; M1 per-epoch histories |
| Materna-T3 | 31500 | 2100 / 2100 / 525 | Per-final-fit Parquet: seed, target, native prediction, scaled prediction, support IDs | selected_contexts.csv; selected_epochs.csv; inner/final registries; M1 per-epoch histories |

Each block also has persistence metrics and support records. Final completion JSON records contain training-only scaler statistics, hashes, timing and model/prediction paths. Materna preserves separate inner-history JSON files; **S1/S2 files contain best epochs and validation-score arrays but empty epoch-loss logs**. S1/S2 loss curves cannot be reconstructed from their filenames. M1 inner and final curves exist; final refits deliberately have no validation curve.

Configurations:
- [multiresource/04_lstm_factorial/configs/lstm_factorial.json](/Users/fgtek002/TimeTrack/multiresource/04_lstm_factorial/configs/lstm_factorial.json)
- [independent_validation/05_bitbrains_factorial/configs/bitbrains_lstm_factorial_phase4c_v2.json](/Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/configs/bitbrains_lstm_factorial_phase4c_v2.json)
- [independent_validation/06_materna_replication/configs/materna_replication_v1.json](/Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/configs/materna_replication_v1.json)

Cohort/provenance/support:
- [multiresource/04_lstm_factorial/PHASE3C_SCIENTIFIC_FREEZE_MANIFEST.md](/Users/fgtek002/TimeTrack/multiresource/04_lstm_factorial/PHASE3C_SCIENTIFIC_FREEZE_MANIFEST.md)
- [independent_validation/05_bitbrains_factorial/PHASE4C_V2_SCIENTIFIC_ANALYSIS_FREEZE_MANIFEST.md](/Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/PHASE4C_V2_SCIENTIFIC_ANALYSIS_FREEZE_MANIFEST.md)
- [independent_validation/06_materna_replication/PHASE4D_MATERNA_FINAL_SCIENTIFIC_FREEZE_MANIFEST.md](/Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/PHASE4D_MATERNA_FINAL_SCIENTIFIC_FREEZE_MANIFEST.md)
- [independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_SELECTED_COHORTS.csv](/Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_SELECTED_COHORTS.csv)
- [independent_validation/06_materna_replication/manifests/CANDIDATE_35_VM_COHORT.csv](/Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/manifests/CANDIDATE_35_VM_COHORT.csv)
- [independent_validation/06_materna_replication/manifests/MATERNA_SCALER_PARTITIONS.csv](/Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/manifests/MATERNA_SCALER_PARTITIONS.csv)
- [independent_validation/06_materna_replication/manifests/MATERNA_SUPPORT_MANIFEST.parquet](/Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/manifests/MATERNA_SUPPORT_MANIFEST.parquet)
- Frozen Materna raw archive: [data/external/raw/gwa_t_13_materna.zip](/Users/fgtek002/TimeTrack/data/external/raw/gwa_t_13_materna.zip).

Unavailable diagnostics: gradient norms/clipping activation counts; S1/S2 per-epoch MSE curves; saved native validation predictions for every inner candidate; alternative native-MAE candidate rankings; saved individual bootstrap replicate draws. Absence of these records limits causal optimisation diagnoses. There are no seasonality or operational-controller experiments to reinterpret.

## 3. Exact model granularity

The training loops create **separate entity-specific networks**. TimeTrack uses seven machines; each Bitbrains environment uses 35 VMs; each Materna block uses the same 35 selected VM identifiers. There is **no pooling across machines/VMs**. Each entity has five expanding outer folds. Every fold and seed receives an independent from-scratch final refit.

Trace:
- [multiresource/04_lstm_factorial/run_factorial_scientific.py:104](/Users/fgtek002/TimeTrack/multiresource/04_lstm_factorial/run_factorial_scientific.py:104) and its context/final loops.
- [independent_validation/05_bitbrains_factorial/run_phase4c_scientific.py:266](/Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/run_phase4c_scientific.py:266), `select_all_contexts`, `final_worker`.
- [independent_validation/06_materna_replication/run_phase4d_scientific.py:75](/Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/run_phase4d_scientific.py:75) reuses the external engine with a trace/VM-specific loader.

| Counting unit | S1 | S2 | M1 |
|---|---|---|---|
| One target, entity, fold, seed, candidate context | 1 independent network | 1 independent network | 1 joint network serving all 4 targets (not 1 per target) |
| Complete target set, entity, fold, seed, one context | 4 networks | 4 networks | 1 network |
| Inner search per entity/fold: 3 contexts × 3 seeds | 36 fits | 36 fits | 9 fits |
| Final evaluated instances per entity/fold: 3 seeds | 12 networks | 12 networks | 3 networks |
| Final evaluated instances per entity across 5 folds | 60 networks | 60 networks | 15 networks |
| TimeTrack inner / final fits | 1260 / 420 | 1260 / 420 | 315 / 105 |
| Each external environment or Materna trace: inner / final fits | 6300 / 2100 | 6300 / 2100 | 1575 / 525 |

Architecture families are two implementation classes: `SingleTargetLSTM` (used by S1/S2) and `MultiTargetLSTM` (M1). Resource-specific separately fitted instances are not four novel architecture families. Inner fits and final refits are different training runs, not a single persistent deployed model. No production deployment was evaluated.

## 4. Meaning of “4 models” versus “1 model”

It counts the network complement for **one entity × outer-fold × seed target set**: four independently fitted target networks versus one four-output-resource network. It does not count the entire experiment, a global cloud-wide model, or all final checkpoints.

Exact sentence suitable for later manuscript clarification:

> For each machine or VM, outer fold and seed, S1 and S2 fit four independent target-specific networks, whereas M1 fits one joint four-resource network; these models are not pooled across entities, and the reported four-versus-one counts describe this local target-set complement rather than the total number of training runs or saved instances.

## 5. Exact architecture and current parameter counts

Two unidirectional LSTM layers, hidden size H, last recurrent output, input width D, and K total linear output coordinates. Each LSTM layer has input/recurrent weights and **two** bias vectors. There is no extra dense hidden layer. Dropout has no trainable parameters.

First layer: `4H(D+H)+8H`. Second layer: `8H²+8H`. Linear head(s): `K(H+1)`.

**P(D,H,K) = 12H² + (4D + 16 + K)H + K.**

Sources: [independent_validation/05_bitbrains_factorial/src/models/lstm.py](/Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/src/models/lstm.py) and [multiresource/04_lstm_factorial/src/models/lstm.py](/Users/fgtek002/TimeTrack/multiresource/04_lstm_factorial/src/models/lstm.py).

| Five-horizon external instance | D | H | K | Parameters |
|---|---|---|---|---|
| S1 per target | 1 | 64 | 5 | 50757 |
| S2 per target | 4 | 64 | 5 | 51525 |
| S1 four-target aggregate | 4 separate networks | 64 | 4 × 5 | 203028 |
| S2 four-target aggregate | 4 separate networks | 64 | 4 × 5 | 206100 |
| M1 total | 4 | 64 | 20 | 52500 |

The existing reduction is `100 × (206100 − 52500) / 206100 = 74.5269286754%`, conventionally reported as approximately 74.5%; four to one networks is 75%. These are local-complement inventories, not corpus-wide parameter totals.

TimeTrack has eight horizons: S1 50,952 per target / 203,808 aggregate; S2 51,720 / 206,880 aggregate; M1 53,280.

## 6. Capacity-matched hidden-size calculation — DESIGN DIAGNOSTIC ONLY

External M1: `P(H)=12H²+52H+20`; match to aggregate S2 = 206,100. The positive continuous root lies between 128 and 129. P(H) is strictly increasing for H>0.

| Hidden size | M1 parameters (five horizons) | Difference from aggregate S2 | Mismatch |
|---|---|---|---|
| 128 | 203284 | -2816 | -1.366327% |
| 129 | 206420 | 320 | 0.155264% |

**Nearest integer: H=129, P=206,420, +0.155264% mismatch.** H=128 is a useful approximation but is not the nearest integer match. For eight-horizon TimeTrack, H=129 yields 207,980 versus 206,880 (+0.531709%); H=128 yields 204,832 (−0.989946%). No such network was instantiated or trained.

## 7. Full context-selection matrix

There is no unique L per resource/block: selections vary by entity and fold and are shared across the three seeds. Below each cell gives **L: number of entity–fold selections**. M1's common context is repeated across resource rows to make the comparison explicit. TimeTrack has 35 entity–fold units; every other block has 175.

| Block | Resource | S1 contexts | S2 contexts | M1 common contexts | S2=M1 | S2≠M1 | Absolute L difference:count |
|---|---|---|---|---|---|---|---|
| TimeTrack | CPU | 32:8, 64:15, 128:12 | 32:8, 64:17, 128:10 | 32:10, 64:10, 128:15 | 13 | 22 | 0:13, 32:7, 64:12, 96:3 |
| TimeTrack | THROUGHPUT | 32:8, 64:7, 128:20 | 32:6, 64:8, 128:21 | 32:10, 64:10, 128:15 | 11 | 24 | 0:11, 32:4, 64:10, 96:10 |
| TimeTrack | MEMORY | 32:12, 64:11, 128:12 | 32:11, 64:10, 128:14 | 32:10, 64:10, 128:15 | 18 | 17 | 0:18, 32:10, 64:4, 96:3 |
| TimeTrack | DISK_WRITE | 32:10, 64:2, 128:23 | 32:8, 64:5, 128:22 | 32:10, 64:10, 128:15 | 13 | 22 | 0:13, 32:5, 64:8, 96:9 |
| fastStorage | CPU | 4:34, 9:42, 18:99 | 4:43, 9:46, 18:86 | 4:66, 9:42, 18:67 | 85 | 90 | 0:85, 5:21, 9:31, 14:38 |
| fastStorage | THROUGHPUT | 4:68, 9:39, 18:68 | 4:68, 9:47, 18:60 | 4:66, 9:42, 18:67 | 77 | 98 | 0:77, 5:27, 9:34, 14:37 |
| fastStorage | MEMORY | 4:21, 9:32, 18:122 | 4:28, 9:45, 18:102 | 4:66, 9:42, 18:67 | 72 | 103 | 0:72, 5:28, 9:39, 14:36 |
| fastStorage | DISK_WRITE | 4:35, 9:51, 18:89 | 4:62, 9:29, 18:84 | 4:66, 9:42, 18:67 | 72 | 103 | 0:72, 5:24, 9:33, 14:46 |
| Rnd | CPU | 4:41, 9:54, 18:80 | 4:70, 9:43, 18:62 | 4:57, 9:64, 18:54 | 86 | 89 | 0:86, 5:31, 9:30, 14:28 |
| Rnd | THROUGHPUT | 4:44, 9:40, 18:91 | 4:60, 9:46, 18:69 | 4:57, 9:64, 18:54 | 92 | 83 | 0:92, 5:30, 9:34, 14:19 |
| Rnd | MEMORY | 4:21, 9:22, 18:132 | 4:28, 9:40, 18:107 | 4:57, 9:64, 18:54 | 77 | 98 | 0:77, 5:29, 9:41, 14:28 |
| Rnd | DISK_WRITE | 4:14, 9:35, 18:126 | 4:26, 9:32, 18:117 | 4:57, 9:64, 18:54 | 72 | 103 | 0:72, 5:16, 9:54, 14:33 |
| Materna-T1 | CPU | 4:38, 9:53, 18:84 | 4:61, 9:36, 18:78 | 4:55, 9:57, 18:63 | 84 | 91 | 0:84, 5:18, 9:41, 14:32 |
| Materna-T1 | THROUGHPUT | 4:27, 9:29, 18:119 | 4:41, 9:34, 18:100 | 4:55, 9:57, 18:63 | 86 | 89 | 0:86, 5:26, 9:43, 14:20 |
| Materna-T1 | MEMORY | 4:15, 9:29, 18:131 | 4:36, 9:29, 18:110 | 4:55, 9:57, 18:63 | 81 | 94 | 0:81, 5:13, 9:53, 14:28 |
| Materna-T1 | DISK_WRITE | 4:16, 9:45, 18:114 | 4:41, 9:56, 18:78 | 4:55, 9:57, 18:63 | 91 | 84 | 0:91, 5:27, 9:34, 14:23 |
| Materna-T2 | CPU | 4:39, 9:40, 18:96 | 4:44, 9:48, 18:83 | 4:43, 9:60, 18:72 | 84 | 91 | 0:84, 5:22, 9:48, 14:21 |
| Materna-T2 | THROUGHPUT | 4:17, 9:48, 18:110 | 4:27, 9:48, 18:100 | 4:43, 9:60, 18:72 | 96 | 79 | 0:96, 5:21, 9:39, 14:19 |
| Materna-T2 | MEMORY | 4:16, 9:36, 18:123 | 4:31, 9:31, 18:113 | 4:43, 9:60, 18:72 | 85 | 90 | 0:85, 5:15, 9:48, 14:27 |
| Materna-T2 | DISK_WRITE | 4:25, 9:37, 18:113 | 4:24, 9:52, 18:99 | 4:43, 9:60, 18:72 | 80 | 95 | 0:80, 5:22, 9:50, 14:23 |
| Materna-T3 | CPU | 4:51, 9:42, 18:82 | 4:55, 9:46, 18:74 | 4:44, 9:44, 18:87 | 88 | 87 | 0:88, 5:32, 9:32, 14:23 |
| Materna-T3 | THROUGHPUT | 4:21, 9:38, 18:116 | 4:34, 9:37, 18:104 | 4:44, 9:44, 18:87 | 85 | 90 | 0:85, 5:17, 9:36, 14:37 |
| Materna-T3 | MEMORY | 4:15, 9:17, 18:143 | 4:40, 9:32, 18:103 | 4:44, 9:44, 18:87 | 90 | 85 | 0:90, 5:17, 9:37, 14:31 |
| Materna-T3 | DISK_WRITE | 4:19, 9:25, 18:131 | 4:28, 9:46, 18:101 | 4:44, 9:44, 18:87 | 98 | 77 | 0:98, 5:21, 9:33, 14:23 |

Appendix A preserves **every exact machine/VM × fold × resource S1/S2/M1 triplet**, rather than substituting a modal context for the frozen selections.

## 8. Context-confound assessment

M1 and S2 differ both in representation organisation/capacity and in whether context is common or target-specific. A pure sharing attribution is not identified.

| Requested case | Mismatched units / all units | Context mismatches among 10 largest raw M1−S2 excess-error units |
|---|---|---|
| TimeTrack MEMORY | 17 / 35 | 6 / 10 |
| fastStorage THROUGHPUT | 98 / 175 | 3 / 10 |
| Rnd CPU | 89 / 175 | 6 / 10 |
| Materna-T1 DISK_WRITE | 84 / 175 | 3 / 10 |
| Materna-T3 DISK_WRITE | 77 / 175 | 3 / 10 |

These top-10 order statistics are post-hoc descriptive inspection, not a significance test or a formal concentration threshold.

Crucially, T1 VM 266 has S2=M1=L18 in **all five folds**, yet all 15 fold–seed M1 disk-write errors are substantially worse. T3 VM 272 mismatches in folds 2, 3 and 5, but its largest raw excess occurs in **matched** fold 1 (both L18); fold 4 is matched and also poor. The largest fastStorage throughput excess is also context-matched. TimeTrack memory's two largest excesses are mismatched. Coincidence is therefore mixed; mismatch is neither a demonstrated cause nor a necessary condition for the largest degradations.

An S2-common-context control is technically implementable without changing the frozen support, cohort, preprocessing algorithm or model architecture; see §26. It is a new post-hoc control requiring authorisation, not a reinterpretation of frozen S2.

## 9. Seed-level artifact availability

All three frozen seeds (0,1,2) exist in the per-fit metrics for all six blocks. Reference/candidate MAEs can be aggregated within each seed over matched entities, folds and horizons. No seed-averaged prediction was artificially decomposed.

For the five external/temporal blocks, the resulting seed gains were cross-checked against **180 already-produced `positive_seed_signs.csv` rows**, with zero disagreements at numerical tolerance. TimeTrack seed identities and MAEs are preserved in its metric/cell tables.

## 10. Seed-noise diagnostic — POST-HOC, NOT FROZEN PRIMARY RESULTS

Appendix B lists all 72 block × resource × comparison cells, including the three reference MAEs, candidate MAEs and seed gains, minimum, maximum, range and **population SD (ddof=0)**.

| Comparison | Sign-stable cells | Sign-variable cells |
|---|---|---|
| S2_vs_S1 | 15 | 9 |
| M1_vs_S2 | 20 | 4 |
| M1_vs_S1 | 24 | 0 |

“Sign-variable” means at least one strictly negative and one strictly positive seed gain; no zero values were used to manufacture a flip. Of 24 S2-versus-S1 cells, **22 have |frozen gain|<4.5%**. In this requested near-zero subset, **13 are sign-stable and 9 sign-variable**. The two larger effects (Rnd throughput and T1 disk write) are sign-stable.

| Near-zero S2–S1 cell with sign changes | Seed 0 gain % | Seed 1 gain % | Seed 2 gain % |
|---|---|---|---|
| TimeTrack MEMORY | -0.785691 | 0.899901 | 2.433501 |
| fastStorage THROUGHPUT | -2.800638 | -0.007372 | 2.847229 |
| Rnd DISK_WRITE | 1.617878 | -3.608960 | 2.407804 |
| Materna-T1 THROUGHPUT | 1.232345 | -0.027270 | 1.739481 |
| Materna-T1 MEMORY | -0.346447 | 0.512781 | -0.226086 |
| Materna-T2 THROUGHPUT | 1.730628 | -1.933453 | 1.069596 |
| Materna-T3 CPU | 1.409130 | -10.244289 | 0.420759 |
| Materna-T3 THROUGHPUT | -1.240197 | -0.483881 | 1.844526 |
| Materna-T3 DISK_WRITE | -0.138669 | 3.366183 | 2.447212 |

Thus seed sensitivity is observed in some near-zero effects, not merely hypothesised. It does not explain all signs, and all 24 M1-versus-S1 cell signs are stable across these seeds. Three fixed seeds do not estimate a universal stochastic noise floor, establish independence, or justify significance claims. Frozen seed-averaged primary results remain unchanged.

## 11. T1 disk-write fitting diagnosis

**C. NO_TRAINING_FAILURE_VISIBLE**, not proof that the joint optimiser found a globally good solution.

- Existing primary MAEs: S1 237.998971, S2 253.944097, M1 323.671421 KB/s.
- Frozen M1–S2 gain: −27.457746%; existing M1 mean persistence skill −1.758953.
- All 525 selected M1 inner curves and final logs have finite stored train/validation MSE where validation is defined. Largest successive joint-validation multiplier in selected curves is 1.587844; no NaN/Inf event is present in these logs.
- All 1,575 relevant S1/S2/M1 final checkpoints and their disk-write predictions were inspected: hashes, parameter counts, finite weights and saved inverse transforms pass.
- The only preserved failed attempt concerns **S1 CPU / VM74 / fold1 / seed0**, a post-test `KeyError: support_hash` fixed by the documented execution-only field adapter. It is not an M1 disk-write training failure; the attempt remains non-reusable and is not counted as a successful fit.
- VM266 drives much of the magnitude, in all seeds and with matched S2/M1 contexts. Selected M1 epochs are 26–50 for this VM, not a systematic epoch-1 collapse.
- At selected M1 validation epochs for VM266, existing loss-share records average approximately **63.27% throughput, 35.01% memory, 1.41% CPU and 0.305% disk write**. Joint loss can therefore be dominated by other resources despite nominal equal resource weights. This is evidence of unequal realised loss contributions, not measurement of gradient conflict or proof of a cause.

## 12. T3 disk-write fitting diagnosis

**C. NO_TRAINING_FAILURE_VISIBLE**, with substantial finite native-prediction excursions and incomplete optimisation diagnostics.

- Existing primary MAEs: S1 74.617325, S2 73.194247, M1 125.378155 KB/s.
- Frozen M1–S2 gain −71.295095%; existing M1 mean persistence skill −1.349340.
- Finite selected M1 inner/final losses; largest successive joint-validation multiplier 1.589895. No failed-attempt records in T3.
- All 1,575 relevant final checkpoints and predictions pass finite/hash/parameter/inverse checks.
- VM272 is the main magnitude contributor, with M1 worse in all 15 fold–seed cells, including matched-context folds. Its M1 epochs are 40–50. The largest saved M1 native prediction is 109,920.414001 KB/s, versus maximum observed disk-write target 53,018 KB/s in T3.
- Selected validation loss shares for VM272 average approximately **92.36% throughput, 7.48% memory, 0.115% CPU and 0.0465% disk write**. This supports investigating the implemented joint objective's balance, not asserting numerical divergence.

For both traces, S1/S2 per-epoch training/validation MSE curves, clipping activation and gradient norms are unavailable. Inner best epoch, executed stopping epoch and final refit epoch are available separately. Final refits do not early-stop and do not have validation callbacks. Detailed epoch and loss summaries are in Appendix C.

## 13. Scaler/transformation diagnosis

Exact Materna disk-write path:
1. Read raw disk-write throughput in KB/s; reject invalid/nonfinite/negative rows under the common physical-validity filter. Raw negatives are **removed**, not clipped into training data.
2. Apply `log1p`.
3. Fit resource-wise median/IQR scaling using the union of historical-window and target rows belonging to the **legal training origins** for the entity, fold, phase and L. No cross-VM pooling.
4. Inner scaler uses inner-training rows only. Final scaler is refit on legal outer training; no validation/test fitting.
5. Inverse: `expm1(z × transformed_IQR + transformed_median)`, then `max(native_prediction,0)`. No upper clipping.

The raw archive SHA-256 matches the frozen value:
`1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4`.

**All 3150 scaler partitions** (35 VMs × 5 folds × 3 contexts × 2 phases × 3 traces) were reconstructed read-only from the frozen archive and exact timestamp IDs. Fit-row counts, fit-timestamp hashes, transformed medians/IQRs and native IQRs matched, with **zero discrepancies**. Origin IDs in the persisted manifest are timestamps; they were mapped back to cleaned row indices before recreating the historical/target row union.

Disk-write partition summaries below are **min / median / max across all inner/final partitions**, not one global scaler or population statistic:

| Trace | log-space centre | log-space IQR | Native IQR KB/s | Zero proportion | IQR / transformed range |
|---|---|---|---|---|---|
| Materna-T1 | 0.000000 / 3.713572 / 7.510431 | 0.048009 / 0.607185 / 7.081640 | 1.000000 / 13.000000 / 24252.000000 | 0.000000 / 0.000000 / 0.596154 | 0.016756 / 0.108612 / 0.981412 |
| Materna-T2 | 0.000000 / 3.135494 / 6.532334 | 0.051672 / 0.615398 / 5.735260 | 1.000000 / 8.000000 / 10942.000000 | 0.000000 / 0.000000 / 0.510582 | 0.011673 / 0.107862 / 0.818121 |
| Materna-T3 | 0.693147 / 2.995732 / 6.678342 | 0.052644 / 0.639756 / 4.908543 | 1.000000 / 14.000000 / 24334.000000 | 0.000000 / 0.000000 / 0.367031 | 0.009663 / 0.098259 / 0.980240 |

Raw min/max, quartiles and other-resource comparisons are included in Appendix D. No arbitrary “near-zero” cutoff was introduced. Some IQRs are small relative to the full tail range, but disk-write minima around 0.048–0.053 in log space are positive finite scales, not machine-precision singularities. CPU has smaller central-spread/range ratios in some partitions.

The main excess-error VMs instead have **large disk-write log IQRs**: T1 VM266 4.861493–4.883498, T3 VM272 4.902993–4.908543. Their native IQRs are approximately 24,233–24,334 KB/s. This does not support a tiny-IQR numerical pathology explanation for those VMs. A large inverse log-space scale can amplify finite scaled errors after exponentiation; no causal contribution was isolated. All 3,150 inspected final inverse mappings matched saved native predictions.

## 14. Percentage-gain denominator diagnosis

The implemented frozen primary formula is

`G(C:B) = 100 × (MacroMAE(B) − MacroMAE(C)) / MacroMAE(B)`.

For M1 versus S2 the denominator is **S2 native MacroMAE**, not transformed IQR and not native IQR. IQR affects model optimisation and diagnostic NMAE, not this percentage normaliser.

Neither reference MacroMAE is numerically close to zero. T3's reference error is lower than T1's, so its percentage is more sensitive to a given native error difference. Nevertheless, the evidence is a large candidate error relative to a nonzero reference, with concentrated entity-level excess—not an IQR denominator explosion. No external threshold establishes what constitutes an “unusually small” reference; the audit does not invent one.

The stored T3 interval [−239.63%, −5.94%] comes from paired VM-cluster resampling of the existing matched seed-averaged inputs. VM272 has a large candidate/reference ratio and dominates positive excess; these inputs support **cluster heterogeneity and candidate-error concentration** as plausible contributors to interval width. The largest excess-error VM has S2 MAE 126.056883, not the minimum reference error. No replicate-level draws were saved, and the bootstrap was not rerun, so a precise allocation of interval-tail width to individual draws/VMs is not claimed.

## 15. T1/T3 raw MAEs and persistence context

| Trace | S1 MAE | S2 reference MAE | M1 candidate MAE | M1−S2 absolute MAE | Frozen gain % | Persistence MAE* |
|---|---|---|---|---|---|---|
| Materna-T1 | 237.998971 | 253.944097 | 323.671421 | 69.727324 | -27.457746 | 807.358929 |
| Materna-T3 | 74.617325 | 73.194247 | 125.378155 | 52.183908 | -71.295095 | 400.373976 |

Units are KB/s. Primary formulation MAEs/gains are existing frozen rows. Absolute differences are audit arithmetic. *No overall persistence MAE row was stored; the displayed persistence MAE is a diagnostic equal-horizon average of the existing native persistence-MAE rows, as permitted by the request.*

**Do not equate the published mean persistence skill to 1 − aggregate learned MAE / aggregate persistence MAE.** Stored skill first forms per-cell relative skills and then averages them. Its denominator/weighting differs from a ratio of macro MAEs. Consequently, a negative average skill can coexist with a lower learned macro MAE than persistence. Both numbers are valid under their respective aggregation rules; silently substituting one for the other would change the endpoint.

## 16. Per-VM error concentration — POST-HOC DIAGNOSTIC

Appendix E lists all 35 VMs for each extreme trace: S2 MAE, M1 MAE, ratio and difference. These average the already-produced seed-averaged matched VM/fold/horizon errors; no model is rerun.

| Trace | VMs | Median M1/S2 | Min ratio | Max ratio | M1 worse | M1 better | Largest magnitude contributor |
|---|---|---|---|---|---|---|---|
| Materna-T1 | 35 | 1.034334 | 0.947823 | 12.756226 | 28 | 7 | VM266 |
| Materna-T3 | 35 | 1.045846 | 0.992329 | 13.601156 | 32 | 3 | VM272 |

Materna-T1: the largest VM accounts for 82.10% of the **sum of positive per-VM excess MAEs**; the largest three account for 91.72%. This is not a recomputed headline gain or a leave-one-VM-out estimate.

Materna-T3: the largest VM accounts for 86.97% of the **sum of positive per-VM excess MAEs**; the largest three account for 92.93%. This is not a recomputed headline gain or a leave-one-VM-out estimate.

Qualitative assessment: **C. MIXED — broadly adverse direction, concentrated magnitude.** Most VMs are worse, but median ratios are close to one and the extreme magnitude is concentrated in a small subset. “Uniform catastrophic failure across all VMs” would be inaccurate. No formal concentration threshold was introduced.

## 17. Fit-hour accounting

Frozen Materna totals remain S1 85.594240 h; S2 75.303186 h; M1 20.405083 h. They sum **successful unique fit records** across three traces, all VMs, five folds, three seeds, all three inner context candidates and selected-context final refits. Inner duration includes training-loop and validation-forward time; final duration includes the training loop. Early-stopped epochs are included.

Excluded: failed attempts without a successful completion record, repeated skipped/resumed encounters, model construction/preprocessing/window construction, checkpoint serialization, final prediction/inversion time and general wall-clock orchestration. These are summed worker fit-hours, not elapsed runtime or production/deployment savings.

Source: [independent_validation/06_materna_replication/build_phase4d_execution_report.py:107](/Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/build_phase4d_execution_report.py:107) and the frozen [independent_validation/06_materna_replication/outputs/scientific_v1/runtime/combined_runtime_storage_accounting.json](/Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/outputs/scientific_v1/runtime/combined_runtime_storage_accounting.json).

| Formulation | Inner / final fits | Inner / final epochs | Total epochs | Median epochs/fit | Mean / median recorded fit seconds | Mean selected final L |
|---|---|---|---|---|---|---|
| S1 | 18900 / 6300 | 685902 / 200681 | 886583 | 38 | 12.228 / 9.663 | 14.125 |
| S2 | 18900 / 6300 | 644209 / 184721 | 828930 | 34 | 10.758 / 8.393 | 12.799 |
| M1 | 4725 / 1575 | 174345 / 53274 | 227619 | 39 | 11.660 / 9.193 | 11.453 |

**FIT_TIME_ORDER_PARTIALLY_EXPLAINED.** S1 and S2 have identical fit counts, but S1 executes 886,583 epochs versus 828,930 and selects longer final contexts on average. These are directly recorded workload differences; input-channel count alone does not determine elapsed cost. They do not fully causally decompose the timing difference: thermal/frequency, scheduling and per-batch hardware traces were not logged. It would be speculation to assign the residual to one mechanism.

## 18. Training/selection/evaluation objective audit

- **Training and early-stopping score:** transformed-and-robust-scaled MSE. S1/S2 use one target; M1 takes the arithmetic mean over four resource losses. Inner best epoch minimises validation MSE, not validation MAE.
- **Context selection:** mean absolute error of the **scaled transformed** validation targets/predictions at each seed's MSE-selected epoch; mean over horizons and seeds, also resources for M1.
- **Primary evaluation:** inverse scaling; expm1 and non-negativity projection for log targets; native-unit per-resource MAE, followed by the frozen matched aggregation.
- **Evaluation NMAE:** native MAE / native training IQR, distinct from the selection metric for throughput/disk write.

Mathematically the selection score for a log target is proportional to `mean |log1p(y) − log1p(yhat_unprojected)| / IQR(log1p(y_train))`, not native `mean |y − yhat| / IQR(y_train)`. Squaring increases the relative weight of larger residuals in the *training space*. Exponentiation and projection are nonlinear, so native-MAE rankings need not preserve MSE or log-MAE rankings.

For one identity-transformed resource with the same fixed scale, multiplying MAE by a positive constant preserves rankings. Across contexts, scaler-fit row sets and IQRs may differ; across resources, normalisation changes weighting. There is therefore no general guarantee of identical rankings.

Native validation predictions/alternative native-MAE ranking tables were not persisted. For **CPU and memory only**, affine back-projection of the stored float32 scaled validation MAEs by their training IQRs is possible. This audit found **147 / 3,640** entity–fold/formulation/resource candidate-order changes under that diagnostic rescaling; all 3,640 stored selected contexts match the implemented normalised-score ranking. This is an affine-score reconstruction subject to float32 scaling/rounding, not a direct saved-native-prediction evaluation or a newly selected scientific result. No analogous exact recovery was invented for log targets.

The frozen TimeTrack protocol explicitly documents “transformed/scaled validation MAE”; external/Materna code follows this inherited implementation. Manuscript §4.7 lines 862–865 should later distinguish selection-space MAE from §4.8's native NMAE. This wording conflict is genuine, but does not establish a training or preprocessing implementation defect. No stored rationale proves why this specific mismatch was optimal, and this audit does not assert it caused M1 degradation. Appendix F contains the diagnostic rank-change counts.

## 19. Frozen decision-rule audit

Authoritative source: [independent_validation/06_materna_replication/PHASE4D_MATERNA_SCIENTIFIC_ANALYSIS_CRITERIA.json](/Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/PHASE4D_MATERNA_SCIENTIFIC_ANALYSIS_CRITERIA.json). Its percentage units are explicit: BROAD thresholds are ±1%, matching analysis code. The older protocol configuration's ±0.01 entries must not be read as ±0.01 percentage points in place of this frozen analysis-criteria source.

Appendix G extracts the exact frozen resource, trace and R1–R4 predicates and bootstrap/count semantics **without rewriting their strings**. Conditions are conjunctive; exact zero is not positive. Bootstrap intervals do **not** assign/change the resource classes. There are no significance-test or CI-exclusion requirements inside BROAD/CONDITIONAL classification.

TimeTrack thresholds adapt to 7 machines/8 horizons (BP: gain≥1%, leads≥6, machines≥5, folds≥4, seeds≥2; CP: gain>0, leads≥4, machines≥3, folds≥3, seeds≥2; BN: gain≤−1%, leads≤2, machines≤2, folds≤1, seeds≤1). External thresholds use 35 VMs/5 horizons as shown in Appendix G.

Conclusions depending primarily on raw gains: signs in Figure 2, all-six-block adverse throughput/memory/disk M1–S2 point estimates, limited CPU exceptions, M1–S1 underperformance except T2 CPU, parameter counts and persistence values. Class-dependent conclusions: “broad/conditional” language, trace support/non-support labels and the mechanical R1–R4 outcomes, including the seven temporal class changes.

A small four-row threshold table and one paragraph distinguishing raw gains, consistency classes and intervals could be moved into the main manuscript without substantial length. Full trace/R1–R4 predicates should remain accessible verbatim in the supplement. No rule or manuscript text was changed.

## 20. Seven temporal-class changes with magnitudes and intervals

Each entry is `class; point gain%; [stored 95% interval]`. BP=BROAD_POSITIVE, CP=CONDITIONALLY_POSITIVE, BN=BROAD_NEGATIVE, NM=NEUTRAL_OR_MIXED.

| Comparison/resource | T1 | T2 | T3 |
|---|---|---|---|
| S2_vs_S1 CPU | NM; -4.317958; [-8.51, -0.18] | BP; 4.207624; [0.59, 7.41] | NM; -2.787548; [-14.65, 3.81] |
| S2_vs_S1 THROUGHPUT | CP; 0.986935; [-1.96, 5.21] | NM; 0.294315; [-5.10, 4.63] | NM; 0.044766; [-2.25, 4.72] |
| S2_vs_S1 MEMORY | NM; -0.019692; [-5.53, 4.51] | BP; 3.948171; [0.35, 6.95] | CP; 3.089002; [-0.19, 6.56] |
| S2_vs_S1 DISK_WRITE | NM; -6.699662; [-28.00, 3.98] | NM; -1.120181; [-5.68, 1.71] | CP; 1.907168; [-1.92, 6.48] |
| M1_vs_S2 CPU | NM; 0.882699; [-2.57, 4.50] | BN; -2.564363; [-5.30, -0.29] | NM; -8.099015; [-16.41, -2.28] |
| M1_vs_S1 CPU | NM; -3.397145; [-6.44, -0.98] | CP; 1.751160; [-3.52, 6.07] | BN; -11.112327; [-31.11, -0.61] |
| M1_vs_S1 THROUGHPUT | BN; -6.249291; [-9.44, -2.07] | NM; -8.372862; [-12.78, -3.45] | BN; -7.865970; [-11.94, -2.20] |

Near-zero cases include S2–S1 T1 memory −0.019692%, throughput T1 +0.986935% / T2 +0.294315% / T3 +0.044766%, and M1–S2 T1 CPU +0.882699%. These merit restraint but are not automatically invalid. The seven changes are **not all near-zero sign flips**: M1–S1 throughput changes classes while all three gains are substantially negative; M1–S2 T3 CPU is −8.099015% with an entirely negative interval yet NM because the independent consistency predicates are not all met. All seven changes follow the stored rule definition; their scientific interpretation should remain descriptive.

## 21. Persistence audit — existing authoritative skill values

These are existing mean per-cell persistence-skill summaries, **not newly calculated ratios of macro errors**.

| Block | Resource | S1 skill | S2 skill | M1 skill | Outcome |
|---|---|---|---|---|---|
| TimeTrack | CPU | 0.151100 | 0.136800 | 0.116300 | All beat |
| TimeTrack | THROUGHPUT | 0.297300 | 0.295600 | 0.290900 | All beat |
| TimeTrack | MEMORY | -0.127200 | -0.149400 | -0.604700 | None beat |
| TimeTrack | DISK_WRITE | 0.355300 | 0.350200 | 0.346200 | All beat |
| fastStorage | CPU | -0.171065 | -0.192722 | -0.233417 | None beat |
| fastStorage | THROUGHPUT | -0.147756 | -0.217996 | -0.316246 | None beat |
| fastStorage | MEMORY | 0.254025 | 0.265227 | 0.233780 | All beat |
| fastStorage | DISK_WRITE | 0.255840 | 0.252270 | 0.162607 | All beat |
| Rnd | CPU | -0.049945 | -0.091360 | -0.274207 | None beat |
| Rnd | THROUGHPUT | 0.038412 | -0.025654 | -0.117640 | Mixed |
| Rnd | MEMORY | 0.204907 | 0.212340 | 0.161015 | All beat |
| Rnd | DISK_WRITE | 0.361573 | 0.328347 | 0.231204 | All beat |
| Materna-T1 | CPU | 0.118963 | 0.050980 | 0.088852 | All beat |
| Materna-T1 | THROUGHPUT | -0.143269 | 0.081347 | -0.060838 | Mixed |
| Materna-T1 | MEMORY | 0.319763 | 0.322302 | 0.276180 | All beat |
| Materna-T1 | DISK_WRITE | 0.173869 | 0.154283 | -1.758953 | Mixed |
| Materna-T2 | CPU | 0.199651 | 0.223126 | 0.190974 | All beat |
| Materna-T2 | THROUGHPUT | 0.301309 | 0.314746 | 0.245664 | All beat |
| Materna-T2 | MEMORY | 0.322750 | 0.329413 | 0.267503 | All beat |
| Materna-T2 | DISK_WRITE | 0.405716 | 0.392817 | 0.368236 | All beat |
| Materna-T3 | CPU | 0.140544 | 0.103629 | 0.005393 | All beat |
| Materna-T3 | THROUGHPUT | 0.025915 | 0.059412 | -0.262904 | Mixed |
| Materna-T3 | MEMORY | 0.261037 | 0.270899 | 0.218590 | All beat |
| Materna-T3 | DISK_WRITE | 0.233905 | 0.208474 | -1.349340 | Mixed |

Reviewer factual checks: TimeTrack memory loses under all formulations; CPU loses under all formulations in both Bitbrains environments; fastStorage throughput also loses under all formulations. Materna M1 has negative mean skill for T1 throughput/disk write and T3 throughput/disk write; it is not uniformly worse on all Materna resources or all T2 resources. These are absolute-skill boundaries under the stored aggregation, not evidence of fit corruption.

## 22. Reviewer-claim verification table

| Reviewer claim | Verdict | Evidence | Implication |
|---|---|---|---|
| A. M1–S2 capacity confound | SUPPORTED | 52,500 versus 206,100 parameters per local target complement; model count also differs | Operational contrast, not parameter-matched mechanistic isolation |
| B. Context-selection confound | SUPPORTED | 1,904 of 3,640 resource/entity/fold pairs differ in L; largest degradations also occur with matched L | Implement S2-common-context control if authorised; coincidence is not causality |
| C. T1/T3 disk-write fitting failure | NOT_SUPPORTED | Finite logged M1 losses and all inspected weights/predictions; correct hashes/inversion/scalers; no relevant failed fit | No blind fix/rerun justified; missing gradients/S1/S2 curves limit stronger exclusion |
| D. IQR is the extreme gain denominator | NOT_SUPPORTED | Primary denominator is native S2 MacroMAE; raw scalers reproduce exactly | Separate optimisation scaling from gain normalisation |
| E. Learned models often lose to persistence | PARTIALLY_SUPPORTED | Named memory/CPU/throughput cells and four Materna M1 trace-resource cells fail; many other cells beat | Retain absolute-skill scope and aggregation semantics |
| F. Seed variation could explain small sign changes | SUPPORTED | 9/22 requested near-zero S2–S1 cells are sign-variable across the three frozen seeds | Observed sensitivity, not a causal/probabilistic explanation for every flip |
| G. Capacity-match hidden size is about 128 | PARTIALLY_SUPPORTED | 128 gives −1.366327%; nearest integer is 129, +0.155264% externally | Specify 129 rather than assume 128 |
| H. Four-versus-one granularity is ambiguous | SUPPORTED | Actual counts are per entity/fold/seed target set; no pooled-across-VM model | Add precise local-instance wording later |
| I. S1>S2 fit hours are unexplained | PARTIALLY_SUPPORTED | Same fit count; more S1 epochs and longer selected contexts; hardware-level residual unlogged | FIT_TIME_ORDER_PARTIALLY_EXPLAINED; no input-width-only argument |
| J. Objective mismatch may matter | SUPPORTED | Different losses/spaces; 147 affine-score ranking changes; native log-target ranks unavailable | Clarify objectives; causation of M1 degradation remains SPECULATIVE |
| K. Temporal-class changes rely on near-zero effects | PARTIALLY_SUPPORTED | Some near-zero cases contribute, but large all-negative class changes also exist | Show point estimates, consistency counts and intervals together |

## 23. Scientific defect status

**NO_SCIENTIFIC_DEFECT_DEMONSTRATED.** No corrupted selected cohort, incorrect persisted scaler, nonfinite inspected model/prediction, wrong final parameter count, broken inverse transform or relevant unrecovered failed fit was found. This is bounded by inspected artifacts, not a proof against every optimisation issue.

Documentation conflicts/ambiguities: selection-space “NMAE” versus native NMAE; four/one local model count versus corpus-wide instances; fit-hours exclude unsuccessful attempts/preprocessing and include inner validation. They require later wording decisions, not silent changes to frozen outcomes. No frozen experiment is currently identified as requiring a superseding rerun on defect grounds.

## 24. Ranked follow-up experiment necessity

These are proposals, **not authorisations**. No experiment is automatically required to preserve the validity of the explicitly operational frozen comparison. If authors wish to claim a capacity/context-isolated sharing mechanism, appropriate controls or narrower claims would be necessary.

| Rank | Candidate | Classification | Reason |
|---|---|---|---|
| 1 | E2 S2 with frozen M1 common context | HIGH_VALUE | Directly removes target-specific context-selection freedom within S2; existing inner fits permit a tightly scoped control |
| 2 | E1 capacity-matched M1 | HIGH_VALUE | Directly addresses the large aggregate parameter gap; H129 is the closest match |
| 3 | E5 additional seeds | HIGH_VALUE | Targeted uncertainty about small context effects is supported by observed seed sign variability; freeze a new seed plan prospectively |
| 4 | E3 matched AR / ARX | HIGH_VALUE | Cheap second-family input-information control; does not explain shared-network mechanisms |
| 5 | E4 seasonal-naive | OPTIONAL | Useful only with a prospectively justified seasonal period; persistence already exposes absolute-skill limits |
| 6 | E7 pooled-across-VM model | OPTIONAL | Tests a different sharing axis and deployment scope, not the current local-instance contrast |
| 7 | E6 rerun/fix T1/T3 disk write | NOT_JUSTIFIED | No implementation/scaling defect shown; blind rerunning poor cells risks outcome-driven replacement |
| 8 | E8 replay-based operational proxy | NOT_JUSTIFIED | Requires a new decision/controller objective and assumptions; no operational-benefit claim needs rescuing here |

No candidate is classified BLOCKED_BY_DEFECT because no genuine scientific defect was demonstrated. Clarifying the documented objective/count/timing semantics is required before a defensible revised submission, but is not a new experiment and is not performed here.

## 25. Exact capacity-matched M1 proposal — DO NOT RUN

External/Bitbrains/Materna:
- Hidden size **129**; two unidirectional LSTM layers; four inputs; four separate linear five-horizon heads; total **206,420** parameters, **+0.155264%** versus aggregate S2.
- Same source-specific selected cohorts, resource definitions, original splits/purges, maximum-history common support, three context candidates [4,9,18], training-only transforms/scalers and inverse projection.
- Same seeds [0,1,2], Adam lr=0.001, batch size256, dropout0.1, maximum50 epochs, patience7, gradient clipping1.0, equal resource scaled-MSE objective.
- Same M1 **common-context selection policy**: inner-only transformed/scaled MAE averaged over resources/horizons/seeds, shorter-L ties; each seed retains its MSE-selected best epoch; fresh final refit, one test evaluation.
- Only intended design intervention: encoder hidden width64→129. Resulting context/epoch selections may change as downstream consequences of that intervention; this is not a fixed-context capacity-only counterfactual.
- If TimeTrack is included, retain its four eight-horizon output heads and contexts [32,64,128]; H129 gives207,980, +0.531709% versus206,880. Do not change horizons to manufacture an exact match.

This controls approximate aggregate trainable parameter budget. It does not make four independent encoders equivalent to one shared encoder, equalise task-specific capacity, optimisation geometry/compute, or remove S2's context freedom. It cannot alone establish a pure causal “representation-sharing effect”.

## 26. Exact S2-common-context proposal — DO NOT RUN

For each source × entity × outer fold, take **the already frozen M1-selected L directly**, without looking at outer-test performance and without introducing a new selector. Apply that L to all four independent S2 target networks.

Keep all-resource inputs, four independent H64/two-layer target models, unchanged per-model capacity (51,525 externally / 51,720 TimeTrack), same horizons, cohorts, splits, seeds, transforms, training objective, optimiser and support. At the forced L use its corresponding training-only scaler; do not carry over a scaler fitted for another L.

Use each S2 target/seed's **existing best inner epoch at that forced L**, not M1's epoch and not S2's best epoch from a different L. All context candidates were already fitted, so the required inner records exist. Valid final fits whose identity already matches can be reused only under exact completion/hash semantics; other final fits would require newly authorised refits. Never reuse pilot work.

This removes target-specific versus common **context-selection freedom within S2**, without sharing target weights or changing parameter count. Comparison with original S2 measures the cost of that restriction; comparison with original M1 is input-length matched but still capacity/architecture/optimisation confounded.

## 27. AR / ARX feasibility — AUDIT ONLY

Available implementation: [benchmark/src/models/ridge.py](/Users/fgtek002/TimeTrack/benchmark/src/models/ridge.py) already flattens lag windows, applies training-only StandardScaler and fits scikit-learn multi-output Ridge. The existing [benchmark/src/selection.py](/Users/fgtek002/TimeTrack/benchmark/src/selection.py) has a small alpha grid [0.01,0.1,1,10,100] and inner-validation-only selection.

A simple pair is feasible: AR uses own-resource lags; ARX uses the same lags for all four resources; each independently predicts one target at all frozen horizons via direct multi-output linear regression. Use the same legal origins, target timestamps, VM-specific folds, purges and training-only preprocessing. Regularisation is sensible with correlated lags, especially TimeTrack's up-to512 ARX input coordinates. No elaborate neural baseline is needed.

Prespecify matched context handling for the pair; independent context retuning would reintroduce the very selection-freedom ambiguity under audit. A fixed, prospectively stated common context or a nested shared-context rule is possible. Any alpha/scaler/context selection must remain inside legal inner training/validation; no test-based tuning, cross-VM leakage or future-label overlap.

Expected computational burden is much lower than recurrent search for these small dense lag dimensions, but no measured runtime is claimed and no fit was launched. Linear baselines would strengthen information-input interpretation; they do not isolate the shared LSTM mechanism.

## 28–33. Preservation and terminal status

- Manuscript/jss files modified = **0**; 38-file SHA-256 set checked.
- Frozen scientific artifacts modified = **0**.
- Existing results modified = **0**.
- Training runs launched = **0**.
- New models created = **0**; existing state dictionaries were inspected with `torch.load(..., weights_only=True)`, without instantiating/training networks.
- Commit = **NO**; push = **NO**.
- Branch, HEAD, scientific checkpoint and existing tags unchanged.
- Only this diagnostic report is newly created. No scientific script/module was executed as a runner; read-only analysis used existing tables/files and pure parser definitions.
- Artifact preservation check: pre/post file-name/size/mtime-nanosecond fingerprints of the four protected trees, plus manuscript content SHA-256s and clean tracked Git diffs. This is not misrepresented as a full rehash of every multi-gigabyte scientific artifact.

Final checks passed: all 204,747 existing files across the four protected trees retain identical name/size/mtime fingerprints; all 38 manuscript files retain identical content SHA-256 hashes. The only added Git-status entry is `?? review_revision/`, containing this report alone. Both tracked and staged diffs remain empty. HEAD remains `f6936cd111d911e40ec2725a18fdfc53768d9ccf`; `paper/jss` remains there, `main` remains `fee20c316040c57b69ba12a193530c955b539771`, and the scientific tag still resolves to that scientific checkpoint.

## Appendix A. Every exact selected context triplet

Each resource cell lists **folds1→5**, separated by semicolons. Each triplet is **S1_L/S2_L/M1_L**. Thus all 3,640 resource/entity/fold selections can be recovered exactly; M1 common contexts repeat across target columns by design.

| Block | Machine/VM | CPU folds1–5 | Throughput folds1–5 | Memory folds1–5 | Disk-write folds1–5 |
|---|---|---|---|---|---|
| TimeTrack | machine01 | 32/64/128;128/128/64;64/64/64;32/32/128;128/128/128 | 32/128/128;32/32/64;32/64/64;128/64/128;64/128/128 | 64/128/128;64/128/64;64/32/64;128/128/128;32/128/128 | 32/64/128;128/128/64;128/128/64;128/128/128;128/128/128 |
| TimeTrack | machine02 | 128/128/64;64/64/64;128/64/32;128/64/128;64/64/64 | 64/32/64;32/64/64;128/64/32;128/32/128;128/128/64 | 64/32/64;64/64/64;64/64/32;32/32/128;32/32/64 | 128/32/64;128/128/64;128/128/32;64/128/128;64/64/64 |
| TimeTrack | machine03 | 64/64/32;32/128/128;128/128/128;128/64/128;64/32/32 | 128/128/32;32/32/128;128/128/128;128/32/128;32/128/32 | 128/32/32;32/128/128;128/128/128;128/128/128;32/64/32 | 128/128/32;128/128/128;128/128/128;128/32/128;32/32/32 |
| TimeTrack | machine04 | 64/32/32;64/32/64;64/64/128;128/64/128;32/64/64 | 128/128/32;128/128/64;128/128/128;128/128/128;128/128/64 | 128/32/32;128/128/64;128/128/128;128/128/128;32/128/64 | 128/128/32;32/32/64;128/128/128;32/64/128;32/32/64 |
| TimeTrack | machine05 | 64/64/32;64/64/32;32/128/128;64/64/32;64/128/128 | 64/64/32;64/128/32;128/128/128;128/128/32;128/64/128 | 64/32/32;32/64/32;64/32/128;64/64/32;128/128/128 | 128/32/32;128/128/32;128/128/128;128/128/32;128/128/128 |
| TimeTrack | machine06 | 64/64/128;64/32/32;64/64/128;32/32/64;32/32/32 | 64/128/128;128/128/32;128/128/128;128/128/64;32/32/32 | 128/32/128;32/64/32;32/64/128;32/64/64;128/64/32 | 32/128/128;32/64/32;32/64/128;128/32/64;32/128/32 |
| TimeTrack | machine07 | 128/128/64;128/128/32;128/64/128;128/128/64;32/32/128 | 64/128/64;32/128/32;64/64/128;128/128/64;128/64/128 | 32/32/64;32/32/32;128/128/128;64/64/64;64/128/128 | 128/128/64;128/128/32;128/32/128;128/128/64;32/128/128 |
| fastStorage | 1005 | 18/18/9;18/9/9;18/9/18;18/9/18;18/9/18 | 18/18/9;18/9/9;18/18/18;18/18/18;18/18/18 | 18/4/9;4/18/9;18/9/18;18/9/18;9/9/18 | 18/9/9;18/9/9;18/18/18;18/18/18;18/18/18 |
| fastStorage | 1044 | 9/9/18;18/18/18;4/18/18;18/9/9;18/18/18 | 9/9/18;9/9/18;9/9/18;9/9/9;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/9;18/18/18 | 18/18/18;18/18/18;4/4/18;18/18/9;18/18/18 |
| fastStorage | 109 | 18/9/18;18/18/9;18/18/9;18/9/9;18/18/9 | 9/9/18;9/4/9;18/4/9;18/4/9;4/9/9 | 9/9/18;9/4/9;4/4/9;4/9/9;18/18/9 | 9/4/18;9/4/9;9/18/9;4/4/9;9/9/9 |
| fastStorage | 1161 | 9/9/18;18/18/18;18/18/18;18/18/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/9/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 |
| fastStorage | 1164 | 18/4/4;9/4/4;18/18/4;18/18/9;18/18/4 | 4/4/4;18/18/4;4/4/4;4/9/9;9/4/4 | 18/18/4;18/18/4;18/4/4;18/18/9;4/4/4 | 18/18/4;18/18/4;18/18/4;4/18/9;18/18/4 |
| fastStorage | 1172 | 18/18/4;18/18/18;18/18/4;18/18/4;18/18/4 | 4/4/4;9/9/18;4/4/4;4/4/4;9/4/4 | 18/18/4;18/18/18;18/18/4;18/18/4;18/18/4 | 18/18/4;18/18/18;18/18/4;18/9/4;18/18/4 |
| fastStorage | 326 | 18/4/18;18/18/18;18/18/18;18/18/4;18/18/9 | 18/9/18;18/18/18;4/4/18;4/4/4;18/18/9 | 18/4/18;18/18/18;9/9/18;9/18/4;18/18/9 | 9/18/18;18/18/18;9/18/18;18/18/4;18/18/9 |
| fastStorage | 330 | 9/9/18;18/18/18;4/18/18;4/18/18;4/18/9 | 18/9/18;18/18/18;18/18/18;18/18/18;18/18/9 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/9 | 18/9/18;18/18/18;9/18/18;9/18/18;18/18/9 |
| fastStorage | 360 | 18/18/4;18/18/9;18/18/18;18/18/18;18/18/18 | 9/4/4;18/4/9;18/4/18;9/9/18;4/9/18 | 9/18/4;9/18/9;18/18/18;18/18/18;18/18/18 | 4/4/4;18/18/9;4/9/18;18/4/18;4/9/18 |
| fastStorage | 366 | 18/18/4;9/18/18;18/9/9;4/4/9;4/4/4 | 18/18/4;4/18/18;4/4/9;18/18/9;4/18/4 | 18/18/4;9/18/18;4/18/9;4/4/9;9/9/4 | 4/4/4;4/9/18;18/4/9;18/18/9;18/4/4 |
| fastStorage | 382 | 4/4/9;18/9/9;9/9/18;4/4/4;4/4/4 | 4/18/9;9/4/9;18/4/18;4/18/4;4/18/4 | 18/18/9;18/18/9;4/9/18;18/18/4;18/18/4 | 4/4/9;4/4/9;9/4/18;4/9/4;18/18/4 |
| fastStorage | 396 | 18/18/18;18/4/18;18/18/18;18/18/18;18/18/18 | 9/4/18;9/9/18;4/4/18;18/18/18;4/4/18 | 18/18/18;4/18/18;9/9/18;4/9/18;4/9/18 | 4/4/18;4/4/18;9/9/18;9/4/18;18/4/18 |
| fastStorage | 410 | 18/18/18;9/4/4;18/4/9;9/4/4;18/18/18 | 4/4/18;9/4/4;4/9/9;18/4/4;4/4/18 | 18/9/18;9/18/4;4/9/9;4/4/4;4/4/18 | 9/4/18;18/4/4;4/9/9;9/4/4;4/4/18 |
| fastStorage | 434 | 4/4/9;18/18/4;9/4/4;18/18/4;18/18/4 | 9/9/9;4/18/4;18/9/4;9/4/4;18/4/4 | 9/9/9;9/9/4;18/9/4;18/4/4;9/4/4 | 4/18/9;18/18/4;9/18/4;4/4/4;4/4/4 |
| fastStorage | 450 | 4/18/18;9/4/4;18/9/9;9/9/9;18/9/4 | 18/4/18;4/18/4;4/9/9;4/4/9;18/4/4 | 9/18/18;9/9/4;18/4/9;9/4/9;9/9/4 | 4/4/18;4/9/4;9/9/9;4/4/9;18/4/4 |
| fastStorage | 480 | 9/9/4;9/18/4;18/18/4;4/4/9;18/18/4 | 18/4/4;4/4/4;4/9/4;4/4/9;4/4/4 | 18/4/4;9/4/4;18/18/4;18/18/9;18/18/4 | 9/4/4;18/18/4;9/18/4;18/9/9;4/9/4 |
| fastStorage | 481 | 4/4/4;18/9/18;9/9/9;18/4/9;9/9/4 | 4/18/4;4/18/18;4/9/9;18/18/9;18/18/4 | 18/9/4;18/18/18;18/18/9;18/18/9;4/9/4 | 9/4/4;9/4/18;9/4/9;9/4/9;18/4/4 |
| fastStorage | 50 | 18/18/4;18/4/9;9/4/18;9/4/18;18/18/9 | 4/4/4;18/4/9;9/9/18;4/9/18;4/9/9 | 9/18/4;4/4/9;9/9/18;18/18/18;9/18/9 | 9/4/4;9/18/9;9/18/18;9/4/18;9/18/9 |
| fastStorage | 503 | 18/18/4;18/18/4;18/18/4;9/4/4;4/4/4 | 4/4/4;4/18/4;9/9/4;9/4/4;18/4/4 | 18/4/4;18/4/4;18/4/4;18/9/4;18/18/4 | 4/4/4;9/9/4;9/9/4;9/18/4;4/4/4 |
| fastStorage | 504 | 9/9/4;18/18/4;9/9/9;18/9/18;9/4/4 | 9/4/4;18/18/4;4/18/9;18/4/18;9/4/4 | 18/4/4;18/9/4;18/18/9;18/18/18;18/18/4 | 9/4/4;9/9/4;9/4/9;9/4/18;9/4/4 |
| fastStorage | 505 | 18/18/4;18/18/18;9/18/4;4/18/4;18/4/4 | 9/4/4;4/18/18;4/9/4;4/4/4;18/9/4 | 18/4/4;18/9/18;18/18/4;18/9/4;18/4/4 | 18/4/4;9/18/18;9/4/4;4/4/4;18/4/4 |
| fastStorage | 513 | 18/18/4;9/4/4;9/18/4;4/4/4;9/9/4 | 4/9/4;4/4/4;4/9/4;18/9/4;9/4/4 | 18/18/4;18/18/4;9/9/4;18/18/4;4/18/4 | 4/9/4;18/4/4;9/4/4;9/4/4;18/4/4 |
| fastStorage | 516 | 4/9/4;9/9/4;4/4/4;18/4/4;18/9/18 | 4/4/4;18/18/4;4/9/4;18/4/4;18/9/18 | 18/9/4;18/18/4;18/18/4;4/18/4;18/18/18 | 4/4/4;9/9/4;9/4/4;18/4/4;18/4/18 |
| fastStorage | 530 | 18/18/4;18/18/18;18/18/18;18/18/18;4/18/18 | 18/4/4;4/4/18;4/4/18;4/4/18;4/4/18 | 9/18/4;18/18/18;18/18/18;18/18/18;18/18/18 | 4/4/4;18/4/18;9/4/18;9/4/18;18/4/18 |
| fastStorage | 678 | 4/4/9;18/4/4;18/9/9;4/4/9;9/9/4 | 18/18/9;9/9/4;4/4/9;18/18/9;4/4/4 | 18/4/9;18/18/4;18/18/9;18/18/9;9/18/4 | 18/4/9;18/18/4;18/18/9;18/18/9;18/18/4 |
| fastStorage | 679 | 4/4/18;9/18/18;4/18/18;4/18/18;4/9/4 | 9/9/18;4/9/18;18/18/18;9/9/18;9/4/4 | 18/18/18;18/4/18;18/9/18;4/9/18;9/9/4 | 18/18/18;18/18/18;18/18/18;18/18/18;4/9/4 |
| fastStorage | 680 | 18/4/18;9/18/18;9/18/18;9/9/9;18/18/9 | 4/4/18;4/4/18;4/4/18;9/4/9;18/18/9 | 18/18/18;18/18/18;18/18/18;18/9/9;18/9/9 | 18/9/18;18/18/18;18/18/18;18/18/9;9/18/9 |
| fastStorage | 697 | 18/9/18;4/4/18;4/4/4;18/18/9;18/18/18 | 4/4/18;4/4/18;4/9/4;9/9/9;18/18/18 | 18/4/18;4/9/18;18/9/4;18/18/9;18/18/18 | 9/9/18;4/4/18;9/9/4;18/18/9;18/18/18 |
| fastStorage | 703 | 9/9/9;18/18/18;4/4/18;4/4/4;9/9/9 | 4/4/9;4/9/18;18/18/18;4/18/4;18/18/9 | 18/18/9;18/18/18;18/18/18;18/18/4;9/9/9 | 18/18/9;4/4/18;9/18/18;18/18/4;18/18/9 |
| fastStorage | 742 | 4/4/4;18/18/18;9/18/18;9/9/18;18/18/4 | 18/18/4;4/4/18;9/18/18;4/4/18;4/18/4 | 18/9/4;18/18/18;18/18/18;18/18/18;18/9/4 | 9/18/4;18/18/18;18/9/18;9/18/18;4/18/4 |
| fastStorage | 79 | 18/18/18;9/18/18;18/18/9;9/9/9;9/9/18 | 9/9/18;9/18/18;9/18/9;18/18/9;18/18/18 | 18/18/18;18/18/18;18/18/9;18/18/9;9/18/18 | 18/18/18;4/18/18;18/18/9;18/18/9;18/9/18 |
| fastStorage | 854 | 18/9/18;18/18/4;18/4/4;4/4/9;9/18/9 | 18/18/18;9/9/4;9/9/4;18/18/9;18/18/9 | 18/18/18;18/9/4;18/9/4;9/9/9;18/9/9 | 9/18/18;9/9/4;18/4/4;9/9/9;4/4/9 |
| fastStorage | 860 | 18/4/4;4/18/4;18/9/4;4/9/4;9/18/4 | 9/9/4;4/4/4;9/4/4;4/4/4;4/18/4 | 18/4/4;4/18/4;18/4/4;18/9/4;9/18/4 | 18/18/4;18/18/4;18/18/4;18/18/4;18/18/4 |
| fastStorage | 880 | 18/9/9;18/18/9;18/9/9;18/9/9;18/18/18 | 18/9/9;18/9/9;18/9/9;18/9/9;18/18/18 | 4/18/9;18/9/9;18/18/9;18/9/9;18/18/18 | 18/18/9;18/18/9;18/18/9;18/18/9;18/18/18 |
| fastStorage | 949 | 18/4/4;4/9/9;9/9/18;18/18/18;9/9/18 | 9/9/4;18/18/9;18/18/18;18/18/18;18/18/18 | 9/18/4;9/4/9;18/18/18;18/18/18;18/18/18 | 18/18/4;4/4/9;18/18/18;18/18/18;18/9/18 |
| Rnd | 1 | 4/4/9;18/4/18;4/4/9;9/18/9;9/18/9 | 18/4/9;9/9/18;18/9/9;18/9/9;4/18/9 | 18/18/9;18/18/18;9/4/9;9/9/9;18/4/9 | 9/9/9;18/18/18;18/18/9;18/18/9;9/18/9 |
| Rnd | 109 | 9/9/18;9/9/9;9/4/18;18/18/9;18/18/18 | 18/18/18;18/9/9;9/9/18;9/4/9;18/9/18 | 18/18/18;18/9/9;18/18/18;9/9/9;18/18/18 | 18/18/18;9/9/9;18/18/18;18/18/9;18/18/18 |
| Rnd | 115 | 18/18/18;9/4/4;4/4/4;18/18/4;4/4/4 | 4/18/18;9/4/4;9/4/4;18/4/4;4/18/4 | 18/18/18;18/9/4;18/4/4;9/4/4;4/9/4 | 18/4/18;9/18/4;9/9/4;4/4/4;18/4/4 |
| Rnd | 118 | 9/4/18;18/4/4;4/4/4;4/18/4;4/4/4 | 4/4/18;9/4/4;4/4/4;4/9/4;18/4/4 | 18/18/18;18/18/4;18/4/4;4/18/4;4/4/4 | 18/18/18;18/9/4;9/9/4;9/4/4;9/18/4 |
| Rnd | 120 | 9/4/18;18/18/4;4/4/4;9/4/4;9/4/9 | 4/4/18;4/4/4;4/4/4;4/9/4;9/4/9 | 18/18/18;18/9/4;18/4/4;4/4/4;4/4/9 | 18/9/18;9/9/4;18/18/4;18/18/4;18/18/9 |
| Rnd | 142 | 9/4/4;18/9/9;18/18/4;9/18/18;18/9/18 | 9/4/4;4/9/9;4/4/4;18/18/18;4/9/18 | 18/18/4;18/18/9;18/18/4;18/18/18;18/18/18 | 4/4/4;18/9/9;18/4/4;18/18/18;18/18/18 |
| Rnd | 143 | 9/4/4;18/18/18;9/4/18;4/4/9;9/9/4 | 4/4/4;4/4/18;4/9/18;18/9/9;9/18/4 | 18/9/4;18/18/18;18/18/18;18/18/9;18/18/4 | 4/9/4;18/18/18;4/4/18;18/18/9;18/9/4 |
| Rnd | 151 | 18/9/18;18/18/4;4/18/18;18/9/4;18/18/9 | 4/18/18;4/4/4;18/4/18;18/18/4;4/18/9 | 18/9/18;18/18/4;18/18/18;18/9/4;18/18/9 | 9/9/18;9/18/4;4/4/18;18/18/4;18/18/9 |
| Rnd | 154 | 4/4/18;18/18/18;9/4/4;18/9/4;9/9/9 | 4/4/18;4/18/18;18/18/4;4/9/4;4/4/9 | 18/18/18;18/18/18;18/18/4;18/18/4;18/9/9 | 9/4/18;18/9/18;9/18/4;18/18/4;18/18/9 |
| Rnd | 158 | 4/9/9;9/18/9;9/18/4;4/18/4;18/4/4 | 18/4/9;18/4/9;4/4/4;18/18/4;4/4/4 | 18/18/9;18/9/9;18/18/4;4/18/4;18/18/4 | 9/4/9;4/18/9;4/4/4;18/18/4;18/18/4 |
| Rnd | 198 | 18/18/9;18/18/18;18/18/18;18/18/18;18/18/18 | 18/18/9;18/18/18;18/18/18;18/18/18;18/18/18 | 18/18/9;18/18/18;18/18/18;18/18/18;18/18/18 | 18/18/9;18/18/18;18/18/18;18/18/18;18/18/18 |
| Rnd | 204 | 9/18/4;4/4/4;18/18/9;18/18/9;9/9/9 | 4/4/4;4/4/4;4/4/9;18/9/9;9/9/9 | 18/9/4;9/4/4;18/9/9;18/18/9;18/9/9 | 18/9/4;18/18/4;18/18/9;18/18/9;18/18/9 |
| Rnd | 22 | 9/4/9;18/9/9;9/4/9;18/9/4;4/4/4 | 18/4/9;9/4/9;18/18/9;18/18/4;18/4/4 | 18/4/9;18/4/9;18/18/9;18/9/4;18/18/4 | 4/9/9;9/4/9;9/18/9;4/4/4;9/4/4 |
| Rnd | 232 | 4/4/4;9/9/9;9/9/18;4/4/18;18/4/18 | 4/4/4;18/4/9;18/9/18;18/18/18;18/18/18 | 9/9/4;9/4/9;9/18/18;18/9/18;18/18/18 | 9/4/4;9/9/9;18/18/18;18/18/18;18/9/18 |
| Rnd | 233 | 18/9/9;9/9/4;18/9/18;18/18/18;18/4/18 | 9/9/9;18/4/4;18/18/18;18/18/18;18/18/18 | 9/9/9;18/9/4;9/18/18;9/9/18;18/18/18 | 18/4/9;9/9/4;18/18/18;18/18/18;18/18/18 |
| Rnd | 241 | 4/4/4;9/18/4;18/4/9;18/18/9;18/18/18 | 9/4/4;4/9/4;18/18/9;18/18/9;18/18/18 | 18/4/4;18/9/4;18/9/9;18/18/9;18/18/18 | 18/18/4;18/18/4;18/18/9;18/18/9;18/18/18 |
| Rnd | 252 | 9/18/9;18/4/18;9/9/9;18/4/9;18/4/9 | 9/4/9;9/18/18;18/18/9;18/9/9;9/9/9 | 9/9/9;18/18/18;18/9/9;18/18/9;18/18/9 | 18/18/9;18/18/18;9/18/9;18/18/9;18/9/9 |
| Rnd | 269 | 18/18/18;4/18/18;9/18/18;9/18/9;4/9/18 | 4/9/18;18/18/18;9/18/18;18/18/9;18/9/18 | 18/18/18;18/18/18;18/18/18;4/4/9;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/9;18/9/18 |
| Rnd | 29 | 9/9/4;9/4/4;4/4/4;4/4/4;4/4/4 | 9/4/4;9/4/4;4/4/4;9/4/4;18/4/4 | 18/4/4;4/18/4;9/9/4;9/18/4;18/9/4 | 18/18/4;9/18/4;18/18/4;18/18/4;18/18/4 |
| Rnd | 304 | 18/18/18;9/9/18;18/18/18;4/18/18;18/9/18 | 9/18/18;18/18/18;18/18/18;18/4/18;18/9/18 | 4/18/18;18/9/18;9/18/18;18/9/18;4/9/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 |
| Rnd | 306 | 18/18/9;9/4/18;9/9/9;9/4/9;9/9/18 | 4/9/9;9/4/18;18/9/9;18/4/9;4/9/18 | 9/9/9;18/18/18;18/18/9;18/18/9;18/18/18 | 18/18/9;18/9/18;18/18/9;18/9/9;18/18/18 |
| Rnd | 332 | 18/18/18;18/18/18;18/18/18;18/18/18;9/9/9 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/9 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/9 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/9 |
| Rnd | 387 | 18/9/9;18/4/18;9/4/4;9/18/9;4/18/9 | 18/18/9;18/18/18;18/18/4;18/18/9;18/18/9 | 18/18/9;18/18/18;18/9/4;18/18/9;18/18/9 | 18/18/9;18/18/18;18/18/4;18/18/9;18/18/9 |
| Rnd | 409 | 18/9/9;18/18/9;9/18/18;18/18/18;18/18/9 | 9/18/9;9/4/9;9/18/18;18/18/18;9/18/9 | 18/4/9;9/9/9;4/18/18;4/4/18;4/4/9 | 18/18/9;18/18/9;9/9/18;9/9/18;9/4/9 |
| Rnd | 413 | 18/4/9;4/9/9;18/18/9;18/4/9;9/4/9 | 18/18/9;18/9/9;18/4/9;9/18/9;9/9/9 | 18/18/9;18/18/9;9/9/9;18/18/9;18/18/9 | 9/18/9;9/18/9;18/9/9;18/18/9;9/9/9 |
| Rnd | 436 | 4/4/4;18/18/4;18/9/4;18/4/18;18/18/18 | 18/4/4;4/4/4;18/9/4;18/18/18;9/18/18 | 4/9/4;18/18/4;18/18/4;18/18/18;18/18/18 | 9/4/4;18/18/4;18/18/4;18/18/18;18/18/18 |
| Rnd | 462 | 4/9/9;9/18/9;4/4/4;18/9/4;18/4/4 | 18/18/9;18/4/9;9/9/4;18/18/4;9/9/4 | 4/9/9;18/18/9;18/18/4;18/18/4;18/18/4 | 18/18/9;18/18/9;18/18/4;18/18/4;18/18/4 |
| Rnd | 474 | 4/4/9;18/18/18;4/4/4;18/4/18;18/4/9 | 18/9/9;18/18/18;18/9/4;18/18/18;9/18/9 | 4/4/9;18/18/18;18/9/4;18/18/18;18/18/9 | 18/18/9;18/18/18;18/18/4;18/18/18;18/18/9 |
| Rnd | 488 | 4/9/4;9/4/18;4/4/4;4/9/9;4/4/4 | 9/18/4;18/18/18;9/4/4;18/4/9;18/18/4 | 18/18/4;18/18/18;18/18/4;9/18/9;4/4/4 | 18/4/4;18/18/18;18/18/4;18/18/9;18/9/4 |
| Rnd | 493 | 18/18/4;18/18/18;9/9/9;9/9/9;9/9/9 | 18/18/4;4/18/18;18/18/9;18/18/9;18/9/9 | 4/4/4;4/4/18;18/4/9;4/9/9;18/18/9 | 18/18/4;18/18/18;4/4/9;18/18/9;18/18/9 |
| Rnd | 85 | 4/18/9;4/4/9;18/4/9;4/4/18;4/4/9 | 9/18/9;4/9/9;18/9/9;18/18/18;4/9/9 | 18/18/9;18/18/9;18/18/9;18/18/18;18/18/9 | 18/9/9;18/18/9;18/18/9;18/18/18;18/18/9 |
| Rnd | 92 | 18/9/9;9/9/9;9/18/9;18/18/9;18/18/18 | 4/9/9;18/18/9;18/9/9;9/9/9;18/9/18 | 18/18/9;18/18/9;18/18/9;18/18/9;18/18/18 | 9/18/9;18/18/9;18/18/9;18/18/9;18/18/18 |
| Rnd | 93 | 18/9/9;4/4/4;4/4/4;18/4/9;18/4/9 | 18/4/9;18/9/4;18/4/4;18/18/9;9/9/9 | 18/9/9;18/4/4;9/4/4;18/18/9;9/18/9 | 18/9/9;18/4/4;18/18/4;4/9/9;18/18/9 |
| Rnd | 97 | 18/4/4;9/4/4;18/9/9;18/18/18;18/9/4 | 4/4/4;9/9/4;18/4/9;4/4/18;4/9/4 | 18/18/4;18/4/4;4/4/9;9/18/18;18/9/4 | 9/9/4;4/4/4;18/9/9;4/18/18;9/4/4 |
| Rnd | 99 | 18/18/4;9/4/4;9/4/4;18/4/4;9/9/4 | 4/4/4;4/4/4;9/4/4;18/9/4;9/4/4 | 18/18/4;18/9/4;18/18/4;18/18/4;18/18/4 | 9/9/4;9/4/4;9/4/4;4/4/4;18/18/4 |
| Materna-T1 | 04 | 4/18/9;18/9/18;18/9/9;9/18/18;9/18/9 | 18/4/9;4/4/18;18/18/9;4/18/18;9/9/9 | 18/18/9;18/18/18;18/18/9;18/18/18;18/18/9 | 4/4/9;4/4/18;9/9/9;18/18/18;18/18/9 |
| Materna-T1 | 08 | 4/4/4;4/4/4;4/4/18;4/4/9;9/9/9 | 4/4/4;9/4/4;9/4/18;4/9/9;9/9/9 | 4/4/4;18/18/4;18/18/18;18/18/9;18/18/9 | 4/18/4;9/9/4;18/18/18;18/9/9;18/18/9 |
| Materna-T1 | 103 | 9/9/4;9/18/18;18/9/4;9/9/9;18/9/18 | 9/9/4;9/18/18;18/9/4;18/4/9;9/9/18 | 18/18/4;9/9/18;18/4/4;4/4/9;9/18/18 | 4/4/4;18/18/18;18/4/4;4/9/9;18/18/18 |
| Materna-T1 | 105 | 9/4/4;18/4/9;4/4/18;18/4/4;18/18/9 | 18/9/4;9/4/9;18/9/18;18/9/4;18/18/9 | 9/4/4;18/18/9;9/9/18;18/4/4;9/18/9 | 9/4/4;4/4/9;4/9/18;18/4/4;18/9/9 |
| Materna-T1 | 128 | 9/9/4;4/4/4;18/18/9;18/9/18;18/9/9 | 18/4/4;9/9/4;9/9/9;9/9/18;9/18/9 | 18/18/4;18/18/4;18/18/9;18/18/18;18/18/9 | 9/4/4;4/9/4;18/18/9;18/18/18;18/4/9 |
| Materna-T1 | 133 | 18/18/18;18/18/18;18/18/18;9/18/18;4/4/4 | 18/18/18;4/18/18;18/18/18;9/4/18;9/9/4 | 9/18/18;18/18/18;18/18/18;18/18/18;18/9/4 | 18/18/18;18/18/18;9/4/18;18/4/18;9/4/4 |
| Materna-T1 | 134 | 9/18/9;18/18/18;9/4/4;4/4/4;4/4/4 | 18/4/9;9/18/18;18/4/4;18/18/4;18/9/4 | 18/4/9;9/4/18;4/4/4;9/9/4;9/4/4 | 9/4/9;18/9/18;18/9/4;18/18/4;9/9/4 |
| Materna-T1 | 227 | 18/4/4;4/18/4;18/4/4;18/4/9;9/4/4 | 9/18/4;18/18/4;18/18/4;18/18/9;18/9/4 | 9/4/4;18/4/4;9/4/4;9/4/9;9/4/4 | 9/4/4;9/9/4;18/9/4;18/18/9;18/18/4 |
| Materna-T1 | 246 | 18/18/9;18/18/18;18/18/9;18/18/18;18/18/18 | 18/18/9;18/18/18;18/9/9;18/18/18;18/18/18 | 18/9/9;18/18/18;9/9/9;18/18/18;9/9/18 | 18/18/9;18/18/18;18/18/9;18/18/18;18/18/18 |
| Materna-T1 | 26 | 18/18/4;18/18/4;9/18/9;4/4/4;18/18/18 | 4/4/4;18/4/4;4/4/9;4/4/4;4/4/18 | 18/18/4;18/9/4;9/18/9;9/18/4;18/18/18 | 9/18/4;9/18/4;18/4/9;18/4/4;18/18/18 |
| Materna-T1 | 266 | 9/4/18;4/9/18;18/18/18;9/18/18;18/18/18 | 18/18/18;18/9/18;18/18/18;18/18/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 9/18/18;9/18/18;18/18/18;9/18/18;18/18/18 |
| Materna-T1 | 272 | 9/4/4;18/4/4;9/4/4;18/4/4;18/18/4 | 18/4/4;4/4/4;4/4/4;18/4/4;4/4/4 | 18/18/4;18/4/4;18/18/4;18/18/4;18/18/4 | 9/4/4;18/18/4;18/9/4;18/18/4;18/18/4 |
| Materna-T1 | 281 | 18/18/9;18/18/9;18/18/9;18/18/18;18/18/9 | 18/18/9;18/18/9;18/18/9;18/18/18;18/18/9 | 18/18/9;18/18/9;18/18/9;18/18/18;18/18/9 | 9/18/9;9/9/9;9/9/9;18/18/18;9/9/9 |
| Materna-T1 | 299 | 9/9/9;18/4/18;4/9/9;4/4/4;9/4/4 | 4/18/9;18/9/18;18/4/9;4/4/4;18/4/4 | 18/18/9;9/4/18;18/9/9;18/4/4;18/9/4 | 18/18/9;18/9/18;18/9/9;18/18/4;18/4/4 |
| Materna-T1 | 302 | 18/18/18;4/18/18;9/4/18;18/4/9;4/4/4 | 18/18/18;18/18/18;18/18/18;18/9/9;4/9/4 | 18/4/18;18/18/18;18/18/18;18/18/9;4/4/4 | 18/4/18;18/18/18;18/9/18;9/9/9;18/4/4 |
| Materna-T1 | 303 | 18/18/18;4/4/18;18/9/18;18/18/9;18/18/9 | 18/18/18;18/18/18;18/18/18;4/18/9;18/9/9 | 4/18/18;18/18/18;18/18/18;18/18/9;18/18/9 | 18/18/18;18/18/18;4/18/18;18/9/9;18/9/9 |
| Materna-T1 | 305 | 9/9/4;18/9/9;9/4/4;9/4/4;4/4/18 | 18/18/4;18/18/9;18/18/4;18/9/4;9/18/18 | 18/18/4;18/9/9;18/18/4;18/18/4;18/18/18 | 4/4/4;4/9/9;18/4/4;4/4/4;4/4/18 |
| Materna-T1 | 306 | 4/18/18;18/18/9;18/9/18;18/9/9;9/9/18 | 18/18/18;18/18/9;18/18/18;18/18/9;18/18/18 | 18/18/18;18/4/9;4/9/18;18/18/9;18/4/18 | 9/9/18;9/4/9;18/9/18;4/4/9;18/18/18 |
| Materna-T1 | 343 | 18/4/4;18/18/4;18/18/4;4/18/4;18/4/4 | 18/9/4;18/9/4;18/18/4;18/18/4;18/18/4 | 18/4/4;18/9/4;9/4/4;9/4/4;9/4/4 | 9/9/4;18/18/4;18/18/4;18/18/4;18/18/4 |
| Materna-T1 | 345 | 18/18/9;18/18/18;9/4/9;18/9/4;18/4/4 | 18/18/9;18/9/18;18/4/9;4/4/4;18/4/4 | 18/18/9;18/18/18;18/9/9;18/9/4;18/4/4 | 9/9/9;18/18/18;18/4/9;4/9/4;18/4/4 |
| Materna-T1 | 380 | 9/18/9;4/4/4;4/4/9;18/4/4;4/4/4 | 9/18/9;18/9/4;18/18/9;18/4/4;9/9/4 | 18/18/9;18/18/4;18/18/9;18/18/4;18/18/4 | 9/4/9;9/18/4;9/4/9;9/4/4;18/4/4 |
| Materna-T1 | 393 | 18/9/9;18/18/9;18/9/9;18/18/18;9/4/4 | 18/18/9;18/18/9;18/18/9;18/18/18;9/4/4 | 18/18/9;18/18/9;18/9/9;18/18/18;18/4/4 | 18/9/9;18/18/9;18/9/9;18/18/18;9/4/4 |
| Materna-T1 | 397 | 9/18/18;4/18/4;4/4/18;9/4/18;4/4/4 | 18/18/18;18/18/4;18/18/18;18/18/18;18/18/4 | 18/4/18;4/4/4;4/4/18;4/9/18;18/9/4 | 18/9/18;18/18/4;18/18/18;18/18/18;18/18/4 |
| Materna-T1 | 416 | 18/4/18;4/4/4;4/18/4;4/4/9;18/18/4 | 18/18/18;18/18/4;18/4/4;18/18/9;18/18/4 | 9/18/18;4/4/4;9/4/4;9/9/9;18/18/4 | 18/18/18;18/18/4;18/9/4;18/18/9;18/9/4 |
| Materna-T1 | 440 | 9/9/9;4/9/9;9/18/9;9/9/4;9/18/4 | 9/4/9;9/4/9;9/9/9;9/4/4;9/4/4 | 18/18/9;18/9/9;18/18/9;18/18/4;18/18/4 | 18/9/9;18/9/9;18/9/9;18/9/4;18/9/4 |
| Materna-T1 | 442 | 9/4/9;9/4/9;18/18/9;9/9/9;9/4/9 | 18/9/9;18/18/9;18/9/9;18/18/9;18/9/9 | 18/18/9;18/18/9;18/18/9;18/18/9;18/18/9 | 9/9/9;9/9/9;18/9/9;18/18/9;18/18/9 |
| Materna-T1 | 478 | 18/18/18;18/18/18;9/18/18;9/18/9;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/9;18/18/18 | 18/9/18;9/18/18;9/18/18;18/9/9;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/9;9/18/18 |
| Materna-T1 | 493 | 4/4/4;4/18/4;18/18/4;9/18/9;4/18/4 | 4/4/4;4/4/4;4/4/4;4/4/9;4/4/4 | 9/4/4;18/18/4;18/9/4;9/4/9;18/4/4 | 4/4/4;18/4/4;18/4/4;9/4/9;9/4/4 |
| Materna-T1 | 498 | 4/4/18;18/4/18;9/4/9;4/18/18;4/4/4 | 18/18/18;18/18/18;18/18/9;18/18/18;18/18/4 | 4/18/18;4/18/18;4/18/9;4/9/18;4/4/4 | 9/9/18;9/4/18;9/4/9;9/18/18;18/4/4 |
| Materna-T1 | 508 | 9/18/4;9/18/4;9/18/9;18/18/9;18/18/18 | 4/18/4;18/18/4;4/18/9;4/18/9;4/18/18 | 18/18/4;18/18/4;18/18/9;9/18/9;18/18/18 | 18/9/4;18/9/4;18/9/9;18/9/9;18/9/18 |
| Materna-T1 | 74 | 18/18/18;18/18/18;18/9/18;18/9/18;18/9/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 18/18/18;18/9/18;18/9/18;18/18/18;18/9/18 | 18/18/18;18/18/18;18/9/18;18/18/18;18/9/18 |
| Materna-T1 | 75 | 18/18/9;9/9/9;9/9/18;18/4/9;18/9/9 | 18/18/9;18/18/9;9/18/18;18/18/9;9/18/9 | 18/18/9;18/18/9;18/18/18;18/9/9;18/18/9 | 18/18/9;18/18/9;18/18/18;18/18/9;18/9/9 |
| Materna-T1 | 76 | 18/18/18;9/18/9;18/18/18;9/9/18;9/18/18 | 18/18/18;18/18/9;18/18/18;18/9/18;18/9/18 | 18/18/18;18/18/9;18/18/18;18/18/18;18/18/18 | 18/18/18;18/9/9;18/9/18;18/9/18;9/9/18 |
| Materna-T1 | 92 | 9/9/9;18/18/9;18/18/18;18/9/9;18/18/9 | 18/18/9;18/18/9;18/9/18;18/4/9;4/4/9 | 18/18/9;18/18/9;18/18/18;18/18/9;18/18/9 | 9/18/9;9/9/9;9/9/18;9/18/9;18/18/9 |
| Materna-T1 | 98 | 18/9/18;9/4/18;9/4/18;4/4/18;9/4/18 | 18/18/18;18/18/18;9/18/18;18/18/18;9/18/18 | 18/18/18;18/18/18;18/18/18;18/9/18;18/18/18 | 18/18/18;18/18/18;18/18/18;9/18/18;18/18/18 |
| Materna-T2 | 04 | 4/9/18;4/9/18;18/18/18;18/18/9;18/18/18 | 9/18/18;9/9/18;9/4/18;18/9/9;9/18/18 | 18/18/18;18/18/18;18/18/18;18/18/9;18/18/18 | 4/4/18;18/9/18;18/9/18;18/4/9;18/9/18 |
| Materna-T2 | 08 | 4/9/18;4/4/9;18/9/4;9/4/9;18/4/4 | 18/18/18;9/18/9;18/18/4;18/18/9;18/9/4 | 18/18/18;18/9/9;18/18/4;18/18/9;18/18/4 | 18/18/18;18/9/9;4/4/4;9/18/9;18/18/4 |
| Materna-T2 | 103 | 18/18/9;18/4/4;18/18/4;18/4/4;18/18/9 | 9/9/9;9/9/4;18/18/4;18/18/4;9/9/9 | 9/18/9;9/4/4;18/18/4;18/9/4;18/9/9 | 18/18/9;9/18/4;18/9/4;18/18/4;18/18/9 |
| Materna-T2 | 105 | 4/4/4;18/18/9;18/18/9;18/18/18;18/9/4 | 18/9/4;18/4/9;9/9/9;9/9/18;18/9/4 | 18/18/4;18/18/9;18/18/9;18/18/18;9/18/4 | 9/9/4;18/18/9;18/18/9;18/18/18;18/4/4 |
| Materna-T2 | 128 | 4/9/18;18/18/9;18/18/18;18/18/18;18/18/9 | 18/18/18;9/18/9;18/18/18;18/18/18;9/9/9 | 18/18/18;18/18/9;18/18/18;18/9/18;18/18/9 | 18/18/18;18/18/9;18/18/18;18/9/18;18/4/9 |
| Materna-T2 | 133 | 4/4/18;9/9/9;9/18/9;9/18/18;18/18/18 | 18/18/18;18/18/9;18/18/9;9/18/18;9/18/18 | 9/18/18;9/18/9;18/18/9;18/18/18;18/18/18 | 9/18/18;9/18/9;9/18/9;18/18/18;18/18/18 |
| Materna-T2 | 134 | 18/9/18;9/9/18;4/4/18;4/9/9;4/18/9 | 18/9/18;9/18/18;18/18/18;9/18/9;18/18/9 | 18/18/18;18/18/18;18/18/18;18/18/9;18/18/9 | 9/18/18;18/4/18;9/18/18;18/18/9;18/18/9 |
| Materna-T2 | 227 | 18/9/9;18/18/9;18/18/9;18/18/9;18/18/18 | 18/18/9;18/18/9;18/18/9;18/18/9;18/18/18 | 9/18/9;18/18/9;18/18/9;18/18/9;18/18/18 | 9/18/9;18/18/9;9/18/9;18/18/9;18/18/18 |
| Materna-T2 | 246 | 18/18/9;18/18/9;18/18/9;18/18/9;18/18/18 | 18/18/9;18/4/9;18/4/9;4/9/9;9/4/18 | 18/18/9;18/18/9;18/18/9;18/18/9;18/18/18 | 4/4/9;4/18/9;9/18/9;4/18/9;9/9/18 |
| Materna-T2 | 26 | 18/4/4;9/9/9;9/4/9;18/4/18;9/9/9 | 4/4/4;9/4/9;18/4/9;18/4/18;4/18/9 | 18/18/4;18/18/9;9/18/9;9/9/18;18/18/9 | 9/4/4;9/9/9;18/9/9;9/9/18;18/9/9 |
| Materna-T2 | 266 | 4/4/9;18/4/4;18/9/9;4/4/4;9/4/9 | 4/4/9;18/18/4;18/4/9;18/4/4;18/4/9 | 18/9/9;18/4/4;18/18/9;18/18/4;18/18/9 | 18/18/9;18/9/4;18/9/9;18/9/4;18/9/9 |
| Materna-T2 | 272 | 18/18/9;18/18/9;18/18/9;18/18/9;18/18/9 | 18/9/9;18/9/9;18/9/9;18/9/9;18/9/9 | 18/18/9;18/18/9;18/18/9;18/9/9;18/18/9 | 18/18/9;18/18/9;18/18/9;18/9/9;18/18/9 |
| Materna-T2 | 281 | 18/18/18;4/4/4;18/18/18;9/18/18;18/18/18 | 18/18/18;18/9/4;18/18/18;18/9/18;18/18/18 | 18/18/18;9/9/4;18/18/18;18/18/18;18/18/18 | 4/9/18;4/4/4;9/18/18;4/9/18;18/18/18 |
| Materna-T2 | 299 | 18/18/4;9/9/18;18/4/9;18/9/18;18/18/4 | 18/18/4;18/18/18;18/9/9;18/18/18;18/18/4 | 9/18/4;18/4/18;18/18/9;9/4/18;4/18/4 | 4/18/4;4/18/18;9/18/9;18/18/18;18/18/4 |
| Materna-T2 | 302 | 18/18/18;18/4/9;4/4/4;4/4/4;9/4/18 | 18/18/18;9/9/9;9/18/4;4/9/4;4/18/18 | 18/18/18;18/18/9;18/9/4;9/9/4;9/18/18 | 18/9/18;9/9/9;9/18/4;4/18/4;18/18/18 |
| Materna-T2 | 303 | 18/18/18;4/4/4;4/4/4;9/4/4;4/4/4 | 18/18/18;9/4/4;9/4/4;4/4/4;4/4/4 | 18/18/18;4/4/4;4/9/4;9/9/4;4/18/4 | 18/9/18;4/9/4;4/4/4;9/4/4;4/9/4 |
| Materna-T2 | 305 | 4/18/18;4/4/4;4/9/18;4/4/9;4/9/18 | 18/18/18;9/9/4;9/18/18;4/9/9;4/18/18 | 18/18/18;18/4/4;9/9/18;9/9/9;4/18/18 | 18/18/18;9/9/4;9/4/18;18/9/9;18/9/18 |
| Materna-T2 | 306 | 9/9/4;18/18/9;4/4/18;4/4/18;4/4/4 | 18/9/4;18/18/9;9/18/18;18/18/18;18/18/4 | 4/9/4;9/4/9;18/18/18;18/4/18;18/18/4 | 4/4/4;4/4/9;4/4/18;4/4/18;9/4/4 |
| Materna-T2 | 343 | 18/18/18;9/18/18;18/9/9;18/18/18;18/18/18 | 18/18/18;18/18/18;18/18/9;18/18/18;18/18/18 | 9/18/18;9/4/18;9/9/9;18/18/18;18/18/18 | 18/18/18;18/9/18;18/18/9;18/18/18;18/18/18 |
| Materna-T2 | 345 | 9/4/4;9/18/18;18/18/4;9/18/18;9/4/4 | 18/4/4;9/9/18;18/9/4;18/18/18;18/18/4 | 4/4/4;4/4/18;9/9/4;9/18/18;18/18/4 | 4/18/4;18/18/18;4/4/4;18/18/18;18/18/4 |
| Materna-T2 | 380 | 4/4/9;18/18/4;18/9/4;18/18/9;4/4/4 | 9/9/9;18/18/4;18/4/4;18/9/9;9/9/4 | 4/4/9;9/4/4;9/4/4;18/4/9;18/4/4 | 18/9/9;18/18/4;18/18/4;18/18/9;18/18/4 |
| Materna-T2 | 393 | 18/9/9;18/4/9;9/9/9;9/9/9;9/9/9 | 18/18/9;18/18/9;18/18/9;18/18/9;18/18/9 | 9/9/9;9/18/9;18/18/9;9/18/9;18/9/9 | 18/18/9;18/18/9;18/9/9;18/9/9;18/9/9 |
| Materna-T2 | 397 | 18/18/18;4/18/18;4/4/18;4/4/18;9/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 4/18/18;18/18/18;9/9/18;18/4/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 |
| Materna-T2 | 416 | 4/18/9;18/18/4;18/9/9;9/18/18;18/18/18 | 4/18/9;4/18/4;18/9/9;9/18/18;4/18/18 | 18/18/9;18/9/4;18/18/9;18/18/18;18/18/18 | 18/18/9;18/18/4;18/9/9;18/18/18;18/18/18 |
| Materna-T2 | 440 | 9/18/4;4/4/4;4/4/9;4/4/4;4/4/4 | 4/18/4;9/18/4;18/9/9;9/18/4;9/18/4 | 4/4/4;4/4/4;9/18/9;4/4/4;9/4/4 | 9/4/4;9/9/4;18/4/9;9/4/4;18/18/4 |
| Materna-T2 | 442 | 9/9/4;9/9/4;9/9/4;9/18/4;9/9/4 | 9/4/4;9/4/4;9/4/4;9/4/4;9/4/4 | 18/18/4;18/18/4;18/18/4;18/18/4;18/18/4 | 18/9/4;18/9/4;18/9/4;18/9/4;18/9/4 |
| Materna-T2 | 478 | 9/9/18;18/18/9;9/4/18;9/9/9;9/9/9 | 9/9/18;18/18/9;9/18/18;18/9/9;18/9/9 | 18/9/18;18/18/9;18/18/18;18/9/9;18/9/9 | 18/18/18;9/9/9;18/9/18;18/9/9;18/18/9 |
| Materna-T2 | 493 | 9/9/18;18/9/18;18/18/18;18/18/18;18/18/18 | 18/18/18;18/18/18;9/18/18;18/18/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 18/9/18;18/9/18;9/4/18;9/4/18;18/18/18 |
| Materna-T2 | 498 | 9/18/4;9/9/4;4/18/4;4/4/9;18/18/18 | 18/18/4;9/9/4;4/4/4;4/9/9;9/9/18 | 18/18/4;9/4/4;18/4/4;9/4/9;18/18/18 | 4/18/4;4/9/4;4/18/4;4/4/9;4/18/18 |
| Materna-T2 | 508 | 18/18/9;18/18/18;4/9/4;18/18/18;18/18/18 | 18/18/9;18/18/18;4/9/4;18/18/18;18/18/18 | 4/4/9;9/4/18;18/4/4;4/4/18;18/4/18 | 18/18/9;18/18/18;9/9/4;18/18/18;18/18/18 |
| Materna-T2 | 74 | 18/9/18;18/18/18;18/18/18;18/9/18;18/9/18 | 9/9/18;18/18/18;18/18/18;18/18/18;18/9/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 |
| Materna-T2 | 75 | 18/9/9;18/9/9;18/18/9;18/9/18;18/9/18 | 18/9/9;18/18/9;18/9/9;18/18/18;18/18/18 | 18/9/9;18/18/9;18/18/9;18/18/18;9/9/18 | 18/9/9;18/18/9;9/18/9;9/18/18;9/18/18 |
| Materna-T2 | 76 | 18/9/9;18/9/9;18/18/18;18/18/4;18/9/9 | 18/4/9;18/18/9;18/18/18;18/4/4;18/18/9 | 18/4/9;18/9/9;18/9/18;18/4/4;4/9/9 | 9/9/9;18/18/9;18/18/18;9/9/4;9/9/9 |
| Materna-T2 | 92 | 18/18/9;18/18/18;18/18/9;18/9/18;18/18/18 | 18/18/9;18/9/18;9/9/9;18/18/18;18/18/18 | 9/9/9;18/18/18;18/18/9;18/18/18;9/18/18 | 18/18/9;18/18/18;18/9/9;18/18/18;18/18/18 |
| Materna-T2 | 98 | 9/18/18;18/18/18;9/18/18;9/18/18;18/4/18 | 18/18/18;9/18/18;9/9/18;9/9/18;9/18/18 | 18/18/18;18/18/18;18/9/18;18/18/18;18/18/18 | 18/9/18;18/18/18;9/18/18;18/18/18;18/18/18 |
| Materna-T3 | 04 | 9/9/18;4/9/18;4/9/18;9/9/18;18/18/18 | 9/9/18;18/4/18;4/9/18;4/4/18;4/9/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 9/4/18;18/4/18;18/18/18;18/18/18;18/4/18 |
| Materna-T3 | 08 | 18/4/9;4/4/4;4/9/4;9/9/9;18/9/9 | 9/9/9;9/9/4;18/18/4;18/18/9;18/4/9 | 18/9/9;18/4/4;18/18/4;18/9/9;18/18/9 | 9/4/9;9/9/4;4/18/4;9/9/9;4/9/9 |
| Materna-T3 | 103 | 4/4/4;4/4/18;9/4/9;4/4/9;9/4/18 | 18/18/4;18/18/18;18/18/9;18/18/9;18/18/18 | 18/18/4;18/18/18;18/18/9;18/18/9;18/9/18 | 18/9/4;18/18/18;9/18/9;18/9/9;18/18/18 |
| Materna-T3 | 105 | 9/9/18;9/9/9;9/9/4;9/18/18;18/18/18 | 9/18/18;18/18/9;9/9/4;9/18/18;18/18/18 | 18/18/18;18/9/9;18/18/4;18/18/18;18/18/18 | 18/18/18;18/9/9;18/18/4;18/18/18;9/9/18 |
| Materna-T3 | 128 | 18/18/4;9/18/9;18/18/4;4/4/4;18/18/9 | 4/18/4;9/9/9;4/4/4;9/9/4;9/9/9 | 18/18/4;9/9/9;9/9/4;18/18/4;18/18/9 | 18/18/4;18/9/9;18/18/4;18/9/4;18/18/9 |
| Materna-T3 | 133 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 9/4/18;18/18/18;18/9/18;18/18/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 18/18/18;4/4/18;18/18/18;18/18/18;18/18/18 |
| Materna-T3 | 134 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 9/4/18;9/4/18;18/9/18;18/18/18;9/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 9/4/18;18/4/18;18/18/18;18/18/18;18/18/18 |
| Materna-T3 | 227 | 4/18/18;18/18/18;18/18/18;18/18/18;4/4/9 | 18/4/18;18/18/18;18/18/18;9/18/18;4/9/9 | 18/18/18;18/18/18;18/9/18;18/4/18;18/9/9 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/9 |
| Materna-T3 | 246 | 18/4/9;18/18/18;4/18/4;18/9/4;4/4/18 | 4/18/9;9/18/18;4/4/4;4/4/4;4/4/18 | 18/18/9;18/4/18;18/9/4;9/9/4;18/9/18 | 18/4/9;4/18/18;18/18/4;4/18/4;4/9/18 |
| Materna-T3 | 26 | 18/18/18;18/18/4;18/18/18;9/18/4;4/4/4 | 18/9/18;18/4/4;18/4/18;18/18/4;18/18/4 | 18/4/18;18/18/4;4/9/18;9/9/4;18/9/4 | 18/4/18;18/9/4;9/9/18;9/4/4;18/9/4 |
| Materna-T3 | 266 | 18/18/4;4/4/4;4/9/18;9/4/4;4/4/9 | 18/4/4;18/4/4;18/4/18;18/9/4;18/4/9 | 18/18/4;18/18/4;18/18/18;18/18/4;18/18/9 | 18/9/4;18/9/4;18/18/18;18/18/4;18/18/9 |
| Materna-T3 | 272 | 4/18/18;4/18/18;4/9/18;4/18/18;9/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 18/9/18;18/4/18;18/18/18;18/18/18;18/18/18 | 9/18/18;18/9/18;18/9/18;18/18/18;9/9/18 |
| Materna-T3 | 281 | 4/9/4;4/9/18;18/18/9;4/9/9;4/18/18 | 9/18/4;18/18/18;18/9/9;18/9/9;9/18/18 | 18/18/4;18/9/18;18/18/9;18/9/9;18/18/18 | 18/18/4;18/18/18;18/18/9;9/9/9;18/18/18 |
| Materna-T3 | 299 | 18/4/9;18/4/18;18/9/9;9/4/4;18/9/18 | 18/9/9;9/9/18;9/9/9;9/4/4;4/4/18 | 18/18/9;18/9/18;18/18/9;9/9/4;9/9/18 | 18/18/9;18/9/18;18/18/9;18/18/4;18/18/18 |
| Materna-T3 | 302 | 18/18/18;18/18/18;9/4/18;4/4/4;4/4/4 | 18/18/18;18/18/18;9/4/18;18/4/4;4/18/4 | 18/18/18;18/18/18;4/9/18;4/4/4;18/18/4 | 4/9/18;18/9/18;4/18/18;18/4/4;4/18/4 |
| Materna-T3 | 303 | 18/18/18;18/18/9;9/9/9;9/4/4;18/4/4 | 18/18/18;9/9/9;4/4/9;18/9/4;9/18/4 | 18/18/18;18/9/9;4/9/9;18/4/4;18/4/4 | 9/9/18;9/9/9;4/18/9;9/4/4;18/9/4 |
| Materna-T3 | 305 | 9/9/4;4/4/4;4/4/4;4/4/4;18/18/9 | 18/4/4;18/18/4;18/18/4;9/4/4;4/9/9 | 18/4/4;9/4/4;18/4/4;18/4/4;18/4/9 | 18/4/4;4/4/4;4/4/4;18/4/4;4/4/9 |
| Materna-T3 | 306 | 4/9/9;18/9/4;18/18/18;9/9/4;18/4/4 | 18/4/9;18/18/4;18/18/18;18/18/4;18/18/4 | 18/18/9;9/4/4;18/4/18;18/9/4;18/4/4 | 4/9/9;18/18/4;18/18/18;18/9/4;18/18/4 |
| Materna-T3 | 343 | 9/4/4;9/4/4;4/4/4;4/4/9;4/4/9 | 4/18/4;18/18/4;9/4/4;18/18/9;18/18/9 | 18/4/4;18/4/4;18/4/4;18/18/9;18/18/9 | 18/18/4;18/9/4;4/9/4;4/18/9;18/4/9 |
| Materna-T3 | 345 | 4/9/18;18/18/18;4/18/18;18/18/18;9/9/4 | 18/18/18;18/18/18;18/18/18;18/18/18;18/9/4 | 4/4/18;18/4/18;9/4/18;4/4/18;4/4/4 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/4 |
| Materna-T3 | 380 | 18/18/18;9/18/9;9/18/4;18/18/4;18/18/4 | 18/18/18;18/18/9;18/18/4;18/18/4;18/18/4 | 18/18/18;18/18/9;18/18/4;18/18/4;18/18/4 | 18/18/18;9/4/9;18/4/4;18/9/4;18/4/4 |
| Materna-T3 | 393 | 9/4/9;4/9/9;9/4/9;4/4/4;4/4/4 | 18/18/9;9/9/9;18/18/9;18/18/4;9/9/4 | 4/18/9;4/4/9;4/4/9;4/4/4;4/4/4 | 18/18/9;18/9/9;18/9/9;18/4/4;18/9/4 |
| Materna-T3 | 397 | 9/9/18;9/9/18;18/18/18;18/9/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 |
| Materna-T3 | 416 | 9/4/9;9/9/9;4/4/9;4/9/9;4/18/9 | 18/18/9;4/4/9;18/18/9;18/9/9;18/9/9 | 9/18/9;18/9/9;18/18/9;9/4/9;18/18/9 | 18/18/9;18/18/9;9/18/9;18/9/9;18/18/9 |
| Materna-T3 | 440 | 4/4/4;18/9/9;18/9/4;18/9/4;18/18/9 | 18/4/4;18/18/9;9/18/4;18/9/4;9/18/9 | 18/9/4;9/18/9;18/18/4;18/18/4;18/18/9 | 9/4/4;18/18/9;18/9/4;9/9/4;18/18/9 |
| Materna-T3 | 442 | 18/4/9;18/4/9;18/9/18;18/18/18;18/18/18 | 4/18/9;9/18/9;18/9/18;9/18/18;18/9/18 | 18/18/9;18/18/9;18/18/18;18/18/18;18/18/18 | 9/9/9;18/9/9;18/18/18;18/18/18;18/18/18 |
| Materna-T3 | 478 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 |
| Materna-T3 | 493 | 18/18/18;18/9/18;18/18/4;9/18/4;4/9/4 | 18/18/18;18/18/18;18/18/4;9/18/4;18/18/4 | 4/4/18;18/18/18;4/4/4;9/18/4;18/18/4 | 4/9/18;9/9/18;4/4/4;4/4/4;9/4/4 |
| Materna-T3 | 498 | 18/18/18;18/18/18;18/18/18;18/18/18;9/9/9 | 18/9/18;9/18/18;18/18/18;18/18/18;18/9/9 | 9/18/18;18/9/18;18/18/18;18/9/18;18/18/9 | 18/4/18;9/18/18;18/18/18;18/18/18;18/9/9 |
| Materna-T3 | 508 | 4/4/9;4/4/18;4/4/9;9/4/9;18/18/9 | 18/4/9;18/9/18;9/4/9;18/4/9;18/4/9 | 18/4/9;4/4/18;18/4/9;9/4/9;9/4/9 | 18/18/9;9/18/18;18/9/9;18/9/9;18/9/9 |
| Materna-T3 | 74 | 4/9/18;18/4/18;18/18/18;18/18/18;18/4/18 | 4/18/18;9/18/18;9/9/18;9/18/18;18/18/18 | 18/18/18;18/4/18;18/18/18;18/18/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 |
| Materna-T3 | 75 | 4/9/18;4/4/4;18/4/18;18/4/18;18/4/18 | 4/4/18;9/18/4;18/18/18;18/18/18;18/18/18 | 9/4/18;18/4/4;18/18/18;18/18/18;18/18/18 | 18/18/18;18/18/4;18/18/18;18/18/18;18/18/18 |
| Materna-T3 | 76 | 4/9/9;9/4/9;4/4/9;9/4/9;18/18/9 | 18/18/9;18/18/9;18/18/9;18/18/9;18/18/9 | 18/18/9;18/4/9;18/9/9;18/9/9;18/18/9 | 18/4/9;18/18/9;18/9/9;18/18/9;18/18/9 |
| Materna-T3 | 92 | 9/9/18;9/9/18;9/18/18;18/18/18;9/18/18 | 18/18/18;4/18/18;4/4/18;18/18/18;18/18/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/9/18 | 18/18/18;18/18/18;18/18/18;18/18/18;18/18/18 |
| Materna-T3 | 98 | 9/18/18;18/9/18;18/9/18;9/9/18;9/4/18 | 18/9/18;18/9/18;18/9/18;18/18/18;18/18/18 | 18/18/18;18/9/18;18/18/18;18/18/18;18/18/18 | 18/18/18;18/9/18;18/18/18;18/18/18;9/18/18 |

## Appendix B. All seed-specific MAEs and gains

**POST-HOC DIAGNOSTIC, NOT FROZEN PRIMARY RESULTS.** Lists are seeds0/1/2. MAEs retain each source/resource's native units; gains/ranges/SD are percentages. No cross-resource MAE pooling is performed. Population SD uses ddof=0.

| Block | Resource | Comparison | Reference MAEs (0/1/2) | Candidate MAEs (0/1/2) | Gains % (0/1/2) | Min % | Max % | Range pp | SD pp | Sign-variable |
|---|---|---|---|---|---|---|---|---|---|---|
| TimeTrack | CPU | S2_vs_S1 | 1.813496/1.791688/1.819967 | 1.849423/1.827532/1.927934 | -1.981093/-2.000568/-5.932358 | -5.932358 | -1.981093 | 3.951265 | 1.858071 | NO |
| TimeTrack | CPU | M1_vs_S2 | 1.849423/1.827532/1.927934 | 1.816691/1.886419/1.875460 | 1.769837/-3.222215/2.721758 | -3.222215 | 2.721758 | 5.943973 | 2.606776 | YES |
| TimeTrack | CPU | M1_vs_S1 | 1.813496/1.791688/1.819967 | 1.816691/1.886419/1.875460 | -0.176194/-5.287246/-3.049136 | -5.287246 | -0.176194 | 5.111052 | 2.091936 | NO |
| TimeTrack | THROUGHPUT | S2_vs_S1 | 29.825293/29.655577/29.913389 | 29.964889/29.711456/29.934920 | -0.468046/-0.188427/-0.071978 | -0.468046 | -0.071978 | 0.396068 | 0.166205 | NO |
| TimeTrack | THROUGHPUT | M1_vs_S2 | 29.964889/29.711456/29.934920 | 29.937657/30.256796/30.169622 | 0.090879/-1.835451/-0.784043 | -1.835451 | 0.090879 | 1.926331 | 0.787521 | YES |
| TimeTrack | THROUGHPUT | M1_vs_S1 | 29.825293/29.655577/29.913389 | 29.937657/30.256796/30.169622 | -0.376741/-2.027337/-0.856585 | -2.027337 | -0.376741 | 1.650596 | 0.693251 | NO |
| TimeTrack | MEMORY | S2_vs_S1 | 313953740.083457/320558046.176150/319858313.023288 | 316420447.907393/317673340.339408/312074558.037281 | -0.785691/0.899901/2.433501 | -0.785691 | 2.433501 | 3.219192 | 1.314718 | YES |
| TimeTrack | MEMORY | M1_vs_S2 | 316420447.907393/317673340.339408/312074558.037281 | 378481105.672318/362725165.269306/379784519.761985 | -19.613352/-14.181809/-21.696726 | -21.696726 | -14.181809 | 7.514917 | 3.167826 | NO |
| TimeTrack | MEMORY | M1_vs_S1 | 313953740.083457/320558046.176150/319858313.023288 | 378481105.672318/362725165.269306/379784519.761985 | -20.553144/-13.154285/-18.735235 | -20.553144 | -13.154285 | 7.398859 | 3.148102 | NO |
| TimeTrack | DISK_WRITE | S2_vs_S1 | 3129502.364775/3131292.305693/3134142.269842 | 3154168.289861/3146760.174558/3140261.576511 | -0.788174/-0.493977/-0.195247 | -0.788174 | -0.195247 | 0.592927 | 0.242064 | NO |
| TimeTrack | DISK_WRITE | M1_vs_S2 | 3154168.289861/3146760.174558/3140261.576511 | 3164334.811581/3180755.450952/3171211.233309 | -0.322320/-1.080326/-0.985576 | -1.080326 | -0.322320 | 0.758006 | 0.337220 | NO |
| TimeTrack | DISK_WRITE | M1_vs_S1 | 3129502.364775/3131292.305693/3134142.269842 | 3164334.811581/3180755.450952/3171211.233309 | -1.113035/-1.579640/-1.182747 | -1.579640 | -1.113035 | 0.466605 | 0.205509 | NO |
| fastStorage | CPU | S2_vs_S1 | 1.217693/1.245933/1.214088 | 1.274354/1.256351/1.264642 | -4.653158/-0.836111/-4.163935 | -4.653158 | -0.836111 | 3.817046 | 1.695864 | NO |
| fastStorage | CPU | M1_vs_S2 | 1.274354/1.256351/1.264642 | 1.266831/1.266093/1.260713 | 0.590294/-0.775436/0.310718 | -0.775436 | 0.590294 | 1.365730 | 0.589078 | YES |
| fastStorage | CPU | M1_vs_S1 | 1.217693/1.245933/1.214088 | 1.266831/1.266093/1.260713 | -4.035396/-1.618031/-3.840279 | -4.035396 | -1.618031 | 2.417365 | 1.096465 | NO |
| fastStorage | THROUGHPUT | S2_vs_S1 | 150.993256/153.762045/150.958188 | 155.222031/153.773380/146.660064 | -2.800638/-0.007372/2.847229 | -2.800638 | 2.847229 | 5.647867 | 2.305777 | YES |
| fastStorage | THROUGHPUT | M1_vs_S2 | 155.222031/153.773380/146.660064 | 191.273125/189.678751/198.159583 | -23.225501/-23.349536/-35.114890 | -35.114890 | -23.225501 | 11.889389 | 5.575706 | NO |
| fastStorage | THROUGHPUT | M1_vs_S1 | 150.993256/153.762045/150.958188 | 191.273125/189.678751/198.159583 | -26.676602/-23.358629/-31.267860 | -31.267860 | -23.358629 | 7.909231 | 3.242847 | NO |
| fastStorage | MEMORY | S2_vs_S1 | 81437.509510/81634.892741/81595.605119 | 79673.368894/79463.339823/79536.968265 | 2.166251/2.660079/2.522975 | 2.166251 | 2.660079 | 0.493829 | 0.208144 | NO |
| fastStorage | MEMORY | M1_vs_S2 | 79673.368894/79463.339823/79536.968265 | 83718.266974/82932.173763/83639.630237 | -5.076851/-4.365326/-5.158182 | -5.158182 | -4.365326 | 0.792856 | 0.356137 | NO |
| fastStorage | MEMORY | M1_vs_S1 | 81437.509510/81634.892741/81595.605119 | 83718.266974/82932.173763/83639.630237 | -2.800623/-1.589126/-2.505068 | -2.800623 | -1.589126 | 1.211497 | 0.515755 | NO |
| fastStorage | DISK_WRITE | S2_vs_S1 | 12.458138/12.521097/12.622275 | 12.156577/12.182589/12.251162 | 2.420594/2.703501/2.940147 | 2.420594 | 2.940147 | 0.519553 | 0.212387 | NO |
| fastStorage | DISK_WRITE | M1_vs_S2 | 12.156577/12.182589/12.251162 | 12.739438/12.655266/12.685630 | -4.794609/-3.879942/-3.546337 | -4.794609 | -3.546337 | 1.248271 | 0.527688 | NO |
| fastStorage | DISK_WRITE | M1_vs_S1 | 12.458138/12.521097/12.622275 | 12.739438/12.655266/12.685630 | -2.257956/-1.071547/-0.501923 | -2.257956 | -0.501923 | 1.756034 | 0.731490 | NO |
| Rnd | CPU | S2_vs_S1 | 1.579036/1.572446/1.586265 | 1.547700/1.566242/1.556867 | 1.984487/0.394542/1.853304 | 0.394542 | 1.984487 | 1.589945 | 0.720580 | NO |
| Rnd | CPU | M1_vs_S2 | 1.547700/1.566242/1.556867 | 1.801000/1.823421/1.817534 | -16.366236/-16.420187/-16.743094 | -16.743094 | -16.366236 | 0.376858 | 0.166400 | NO |
| Rnd | CPU | M1_vs_S1 | 1.579036/1.572446/1.586265 | 1.801000/1.823421/1.817534 | -14.056963/-15.960861/-14.579489 | -15.960861 | -14.056963 | 1.903898 | 0.803192 | NO |
| Rnd | THROUGHPUT | S2_vs_S1 | 282.130639/281.325670/282.642086 | 297.515398/302.623247/307.001445 | -5.453062/-7.570435/-8.618447 | -8.618447 | -5.453062 | 3.165385 | 1.316614 | NO |
| Rnd | THROUGHPUT | M1_vs_S2 | 297.515398/302.623247/307.001445 | 347.812867/342.549902/346.670589 | -16.905837/-13.193519/-12.921484 | -16.905837 | -12.921484 | 3.984353 | 1.817519 | NO |
| Rnd | THROUGHPUT | M1_vs_S1 | 282.130639/281.325670/282.642086 | 347.812867/342.549902/346.670589 | -23.280785/-21.762761/-22.653563 | -23.280785 | -21.762761 | 1.518025 | 0.622837 | NO |
| Rnd | MEMORY | S2_vs_S1 | 166831.405468/167694.768306/166419.706458 | 163840.407082/164965.631165/163758.603355 | 1.792827/1.627443/1.599031 | 1.599031 | 1.792827 | 0.193796 | 0.085450 | NO |
| Rnd | MEMORY | M1_vs_S2 | 163840.407082/164965.631165/163758.603355 | 179222.631980/178347.693193/178910.085664 | -9.388542/-8.112030/-9.252328 | -9.388542 | -8.112030 | 1.276511 | 0.572355 | NO |
| Rnd | MEMORY | M1_vs_S1 | 166831.405468/167694.768306/166419.706458 | 179222.631980/178347.693193/178910.085664 | -7.427394/-6.352568/-7.505349 | -7.505349 | -6.352568 | 1.152780 | 0.526015 | NO |
| Rnd | DISK_WRITE | S2_vs_S1 | 102.023778/99.644963/100.961035 | 100.373158/103.241110/98.530092 | 1.617878/-3.608960/2.407804 | -3.608960 | 2.407804 | 6.016764 | 2.669691 | YES |
| Rnd | DISK_WRITE | M1_vs_S2 | 100.373158/103.241110/98.530092 | 105.387090/108.725295/104.804712 | -4.995292/-5.312017/-6.368227 | -6.368227 | -4.995292 | 1.372935 | 0.586974 | NO |
| Rnd | DISK_WRITE | M1_vs_S1 | 102.023778/99.644963/100.961035 | 105.387090/108.725295/104.804712 | -3.296596/-9.112686/-3.807089 | -9.112686 | -3.296596 | 5.816089 | 2.629678 | NO |
| Materna-T1 | CPU | S2_vs_S1 | 0.932739/0.944012/0.938190 | 0.959896/0.986568/0.990026 | -2.911522/-4.507909/-5.525094 | -5.525094 | -2.911522 | 2.613572 | 1.075685 | NO |
| Materna-T1 | CPU | M1_vs_S2 | 0.959896/0.986568/0.990026 | 0.976112/0.966775/0.967682 | -1.689360/2.006228/2.256878 | -1.689360 | 2.256878 | 3.946238 | 1.804100 | YES |
| Materna-T1 | CPU | M1_vs_S1 | 0.932739/0.944012/0.938190 | 0.976112/0.966775/0.967682 | -4.650068/-2.411242/-3.143521 | -4.650068 | -2.411242 | 2.238826 | 0.932038 | NO |
| Materna-T1 | THROUGHPUT | S2_vs_S1 | 222.587938/219.808102/223.647974 | 219.844886/219.868044/219.757659 | 1.232345/-0.027270/1.739481 | -0.027270 | 1.739481 | 1.766752 | 0.742760 | YES |
| Materna-T1 | THROUGHPUT | M1_vs_S2 | 219.844886/219.868044/219.757659 | 239.765371/236.023228/231.878442 | -9.061155/-7.347673/-5.515523 | -9.061155 | -5.515523 | 3.545632 | 1.447768 | NO |
| Materna-T1 | THROUGHPUT | M1_vs_S1 | 222.587938/219.808102/223.647974 | 239.765371/236.023228/231.878442 | -7.717145/-7.376946/-3.680100 | -7.717145 | -3.680100 | 4.037045 | 1.828179 | NO |
| Materna-T1 | MEMORY | S2_vs_S1 | 232568.783632/232949.966507/232790.589698 | 233374.511710/231755.443584/233316.897758 | -0.346447/0.512781/-0.226086 | -0.346447 | 0.512781 | 0.859228 | 0.379866 | YES |
| Materna-T1 | MEMORY | M1_vs_S2 | 233374.511710/231755.443584/233316.897758 | 264945.047504/262910.492672/262914.532112 | -13.527842/-13.443071/-12.685594 | -13.527842 | -12.685594 | 0.842248 | 0.378644 | NO |
| Materna-T1 | MEMORY | M1_vs_S1 | 232568.783632/232949.966507/232790.589698 | 264945.047504/262910.492672/262914.532112 | -13.921156/-12.861357/-12.940361 | -13.921156 | -12.861357 | 1.059800 | 0.482053 | NO |
| Materna-T1 | DISK_WRITE | S2_vs_S1 | 235.410679/238.601250/239.984983 | 255.027123/252.027729/254.777438 | -8.332861/-5.627162/-6.163909 | -8.332861 | -5.627162 | 2.705699 | 1.169675 | NO |
| Materna-T1 | DISK_WRITE | M1_vs_S2 | 255.027123/252.027729/254.777438 | 326.799219/322.774043/321.441001 | -28.142927/-28.070846/-26.165410 | -28.142927 | -26.165410 | 1.977516 | 0.915693 | NO |
| Materna-T1 | DISK_WRITE | M1_vs_S1 | 235.410679/238.601250/239.984983 | 326.799219/322.774043/321.441001 | -38.820898/-35.277600/-33.942131 | -38.820898 | -33.942131 | 4.878767 | 2.058608 | NO |
| Materna-T2 | CPU | S2_vs_S1 | 0.918229/0.936510/0.924643 | 0.886810/0.892346/0.883281 | 3.421791/4.715797/4.473312 | 3.421791 | 4.715797 | 1.294006 | 0.561639 | NO |
| Materna-T2 | CPU | M1_vs_S2 | 0.886810/0.892346/0.883281 | 0.910013/0.912790/0.907908 | -2.616513/-2.291012/-2.788161 | -2.788161 | -2.291012 | 0.497148 | 0.206174 | NO |
| Materna-T2 | CPU | M1_vs_S1 | 0.918229/0.936510/0.924643 | 0.910013/0.912790/0.907908 | 0.894810/2.532824/1.809875 | 0.894810 | 2.532824 | 1.638014 | 0.670248 | NO |
| Materna-T2 | THROUGHPUT | S2_vs_S1 | 288.007463/285.346188/286.369030 | 283.023125/290.863221/283.306039 | 1.730628/-1.933453/1.069596 | -1.933453 | 1.730628 | 3.664080 | 1.594461 | YES |
| Materna-T2 | THROUGHPUT | M1_vs_S2 | 283.023125/290.863221/283.306039 | 310.567953/312.906225/308.231894 | -9.732359/-7.578477/-8.798208 | -9.732359 | -7.578477 | 2.153882 | 0.881891 | NO |
| Materna-T2 | THROUGHPUT | M1_vs_S1 | 288.007463/285.346188/286.369030 | 310.567953/312.906225/308.231894 | -7.833301/-9.658456/-7.634507 | -9.658456 | -7.634507 | 2.023949 | 0.910865 | NO |
| Materna-T2 | MEMORY | S2_vs_S1 | 252303.486296/252337.894053/252157.884599 | 241983.336632/243074.170534/241862.030293 | 4.090371/3.671158/4.083098 | 3.671158 | 4.090371 | 0.419213 | 0.195927 | NO |
| Materna-T2 | MEMORY | M1_vs_S2 | 241983.336632/243074.170534/241862.030293 | 264577.656046/264602.853173/265101.376982 | -9.337139/-8.856837/-9.608514 | -9.608514 | -8.856837 | 0.751677 | 0.310797 | NO |
| Materna-T2 | MEMORY | M1_vs_S1 | 252303.486296/252337.894053/252157.884599 | 264577.656046/264602.853173/265101.376982 | -4.864843/-4.860530/-5.133090 | -5.133090 | -4.860530 | 0.272560 | 0.127482 | NO |
| Materna-T2 | DISK_WRITE | S2_vs_S1 | 142.604611/143.268440/142.811939 | 146.005969/143.991019/143.490053 | -2.385167/-0.504353/-0.474830 | -2.385167 | -0.474830 | 1.910337 | 0.893664 | NO |
| Materna-T2 | DISK_WRITE | M1_vs_S2 | 146.005969/143.991019/143.490053 | 157.173401/155.797680/154.711599 | -7.648613/-8.199582/-7.820435 | -8.199582 | -7.648613 | 0.550969 | 0.230179 | NO |
| Materna-T2 | DISK_WRITE | M1_vs_S1 | 142.604611/143.268440/142.811939 | 157.173401/155.797680/154.711599 | -10.216212/-8.745290/-8.332398 | -10.216212 | -8.332398 | 1.883814 | 0.808486 | NO |
| Materna-T3 | CPU | S2_vs_S1 | 1.142581/1.116692/1.100843 | 1.126480/1.231089/1.096211 | 1.409130/-10.244289/0.420759 | -10.244289 | 1.409130 | 11.653418 | 5.275965 | YES |
| Materna-T3 | CPU | M1_vs_S2 | 1.126480/1.231089/1.096211 | 1.187780/1.262279/1.283443 | -5.441695/-2.533563/-17.079941 | -17.079941 | -2.533563 | 14.546378 | 6.284930 | NO |
| Materna-T3 | CPU | M1_vs_S1 | 1.142581/1.116692/1.100843 | 1.187780/1.262279/1.283443 | -3.955885/-13.037397/-16.587317 | -16.587317 | -3.955885 | 12.631432 | 5.319032 | NO |
| Materna-T3 | THROUGHPUT | S2_vs_S1 | 344.080608/341.971447/346.109128 | 348.347887/343.626183/339.725056 | -1.240197/-0.483881/1.844526 | -1.240197 | 1.844526 | 3.084723 | 1.312716 | YES |
| Materna-T3 | THROUGHPUT | M1_vs_S2 | 348.347887/343.626183/339.725056 | 369.905117/370.300729/373.144821 | -6.188420/-7.762664/-9.837298 | -9.837298 | -6.188420 | 3.648878 | 1.494310 | NO |
| Materna-T3 | THROUGHPUT | M1_vs_S1 | 344.080608/341.971447/346.109128 | 369.905117/370.300729/373.144821 | -7.505366/-8.284107/-7.811321 | -8.284107 | -7.505366 | 0.778742 | 0.320343 | NO |
| Materna-T3 | MEMORY | S2_vs_S1 | 278459.744247/277664.237327/279313.802342 | 270216.420827/269358.248911/270056.427763 | 2.960329/2.991379/3.314328 | 2.960329 | 3.314328 | 0.353999 | 0.160061 | NO |
| Materna-T3 | MEMORY | M1_vs_S2 | 270216.420827/269358.248911/270056.427763 | 289082.925180/294452.682740/296554.387490 | -6.981998/-9.316378/-9.812009 | -9.812009 | -6.981998 | 2.830011 | 1.233961 | NO |
| Materna-T3 | MEMORY | M1_vs_S1 | 278459.744247/277664.237327/279313.802342 | 289082.925180/294452.682740/296554.387490 | -3.814979/-6.046312/-6.172479 | -6.172479 | -3.814979 | 2.357500 | 1.082824 | NO |
| Materna-T3 | DISK_WRITE | S2_vs_S1 | 73.567403/75.461267/74.823306 | 73.669419/72.921102/72.992221 | -0.138669/3.366183/2.447212 | -0.138669 | 3.366183 | 3.504852 | 1.483812 | YES |
| Materna-T3 | DISK_WRITE | M1_vs_S2 | 73.669419/72.921102/72.992221 | 113.931155/125.093601/137.109709 | -54.651899/-71.546504/-87.841536 | -87.841536 | -54.651899 | 33.189637 | 13.550350 | NO |
| Materna-T3 | DISK_WRITE | M1_vs_S1 | 73.567403/75.461267/74.823306 | 113.931155/125.093601/137.109709 | -54.866353/-65.771934/-83.244656 | -83.244656 | -54.866353 | 28.378302 | 11.688340 | NO |

## Appendix C. Epoch, loss and prediction-integrity diagnostics

Selected-context disk-write S1/S2 epochs and M1 joint epochs: **min / Q25 / median / Q75 / max**. Every row has525 final fits. The “inner stop epoch” is epochs actually executed (patience stop or maximum50); final refit epoch is the seed-specific best inner epoch, not the later stopping epoch.

| Trace | Formulation | Selected/final epochs | Inner stop epochs | Patience stops / max-epoch stops | Best epoch=1 |
|---|---|---|---|---|---|
| Materna-T1 | S1 | 1.000 / 24.000 / 41.000 / 49.000 / 50.000 | 8.000 / 31.000 / 48.000 / 50.000 / 50.000 | 269 / 256 | 1 |
| Materna-T1 | S2 | 1.000 / 19.000 / 34.000 / 48.000 / 50.000 | 8.000 / 26.000 / 41.000 / 50.000 / 50.000 | 310 / 215 | 4 |
| Materna-T1 | M1 | 2.000 / 19.000 / 36.000 / 48.000 / 50.000 | 9.000 / 26.000 / 43.000 / 50.000 / 50.000 | 308 / 217 | 0 |
| Materna-T3 | S1 | 1.000 / 24.000 / 38.000 / 48.000 / 50.000 | 8.000 / 31.000 / 45.000 / 50.000 / 50.000 | 301 / 224 | 5 |
| Materna-T3 | S2 | 1.000 / 18.000 / 30.000 / 45.000 / 50.000 | 8.000 / 25.000 / 37.000 / 50.000 / 50.000 | 375 / 150 | 7 |
| Materna-T3 | M1 | 2.000 / 19.000 / 32.000 / 45.000 / 50.000 | 9.000 / 26.000 / 39.000 / 50.000 / 50.000 | 376 / 149 | 0 |

| Trace | M1 loss at selected inner epoch | Min / Q25 / median / Q75 / max |
|---|---|---|
| Materna-T1 | selected_joint_validation_mse | 0.038 / 0.466 / 1.139 / 3.509 / 390.083 |
| Materna-T1 | selected_disk_validation_mse | 0.001 / 0.225 / 0.470 / 0.879 / 50.356 |
| Materna-T1 | selected_joint_train_mse | 0.043 / 0.616 / 1.710 / 3.975 / 69.107 |
| Materna-T1 | selected_disk_train_mse | 0.002 / 0.253 / 0.494 / 0.895 / 45.332 |
| Materna-T1 | final_disk_train_mse | 0.001 / 0.232 / 0.601 / 1.627 / 55.692 |
| Materna-T3 | selected_joint_validation_mse | 0.065 / 0.638 / 1.445 / 8.818 / 592.528 |
| Materna-T3 | selected_disk_validation_mse | 0.002 / 0.218 / 0.608 / 1.935 / 45.843 |
| Materna-T3 | selected_joint_train_mse | 0.062 / 0.647 / 1.200 / 7.941 / 320.366 |
| Materna-T3 | selected_disk_train_mse | 0.004 / 0.214 / 0.591 / 2.028 / 9.501 |
| Materna-T3 | final_disk_train_mse | 0.002 / 0.226 / 0.518 / 1.874 / 9.826 |

These are distributions of existing finite curve values, not universal thresholds for acceptable fit quality. M1 early stopping minimises the joint validation MSE, so the disk-only minimum need not occur at that epoch. S1/S2 per-epoch minimum validation MSE and full curves are unavailable; their best/stopping epochs and MAE-score arrays remain available. Gradient norm/clipping counts are unavailable for all formulations.

| Trace | Formulation | Checkpoints checked | Prediction points | Nonfinite weights / predictions | Wrong counts / inverse mismatches | Native prediction min / median / Q99 / Q99.9 / max |
|---|---|---|---|---|---|---|
| Materna-T1 | S1 | 525 | 2162955 | 0 / 0 | 0 / 0 | 0.000 / 40.392 / 24437.160 / 30722.243 / 74381.671 |
| Materna-T1 | S2 | 525 | 2162955 | 0 / 0 | 0 / 0 | 0.000 / 40.429 / 24050.409 / 31237.939 / 205268.234 |
| Materna-T1 | M1 | 525 | 2162955 | 0 / 0 | 0 / 0 | 0.000 / 39.910 / 21729.200 / 32717.494 / 148062.521 |
| Materna-T3 | S1 | 525 | 2685720 | 0 / 0 | 0 / 0 | 0.000 / 21.221 / 2842.917 / 25280.441 / 48319.961 |
| Materna-T3 | S2 | 525 | 2685720 | 0 / 0 | 0 / 0 | 0.000 / 21.458 / 3402.198 / 25210.785 / 56328.917 |
| Materna-T3 | M1 | 525 | 2685720 | 0 / 0 | 0 / 0 | 0.000 / 21.630 / 3254.066 / 31003.405 / 109920.414 |

No arbitrary outlier threshold was introduced. Saved prediction order statistics describe pooled prediction points for integrity/tail inspection, not the primary MacroMAE weighting. Negative pre-projection values are handled by the frozen non-negativity rule; there is no upper clipping.

Top-VM M1 epoch triples (seeds0/1/2) and realised validation-loss shares:

| Trace/VM | Fold1 epochs | Fold2 | Fold3 | Fold4 | Fold5 | Disk log IQR min / median / max | Selected validation loss shares |
|---|---|---|---|---|---|---|---|
| Materna-T1/266 | 30/47/37 | 41/37/26 | 34/45/44 | 37/48/50 | 38/46/48 | 4.861493/4.872418/4.883498 | CPU=0.014093; DISK_WRITE=0.003054; MEMORY=0.350125; THROUGHPUT=0.632728 |
| Materna-T3/272 | 50/46/50 | 49/43/49 | 49/40/50 | 45/43/46 | 50/50/49 | 4.902993/4.908503/4.908543 | CPU=0.001150; DISK_WRITE=0.000465; MEMORY=0.074811; THROUGHPUT=0.923575 |

## Appendix D. Training-only distribution summaries

All entries are **min / median / max across partition-specific statistics**, over all inner/final phases and contexts. The exact persisted per-partition centre/IQR values remain in MATERNA_SCALER_PARTITIONS.csv. Reconstructed extrema/quartiles/zero proportions are diagnostic and do not alter those scalers.

| Trace | Resource | Transformed IQR | Native IQR | IQR/transformed range | Zero fraction |
|---|---|---|---|---|---|
| Materna-T1 | CPU | 0.090000 / 0.680000 / 24.920000 | 0.090000 / 0.680000 / 24.920000 | 0.005537 / 0.021193 / 0.325039 | 0.000000 / 0.000000 / 0.000000 |
| Materna-T1 | DISK_WRITE | 0.048009 / 0.607185 / 7.081640 | 1.000000 / 13.000000 / 24252.000000 | 0.016756 / 0.108612 / 0.981412 | 0.000000 / 0.000000 / 0.596154 |
| Materna-T1 | MEMORY | 22230.000000 / 376858.500000 / 2717909.000000 | 22230.000000 / 376858.500000 / 2717909.000000 | 0.014561 / 0.092795 / 0.548146 | 0.000000 / 0.000000 / 0.032936 |
| Materna-T1 | THROUGHPUT | 0.076373 / 1.148654 / 8.545392 | 1.000000 / 47.875000 / 8769.500000 | 0.010433 / 0.151778 / 0.718342 | 0.000000 / 0.000000 / 0.657581 |
| Materna-T2 | CPU | 0.030000 / 0.670000 / 22.867500 | 0.030000 / 0.670000 / 22.867500 | 0.002519 / 0.031390 / 0.356995 | 0.000000 / 0.000000 / 0.000000 |
| Materna-T2 | DISK_WRITE | 0.051672 / 0.615398 / 5.735260 | 1.000000 / 8.000000 / 10942.000000 | 0.011673 / 0.107862 / 0.818121 | 0.000000 / 0.000000 / 0.510582 |
| Materna-T2 | MEMORY | 20972.000000 / 461374.000000 / 4385564.000000 | 20972.000000 / 461374.000000 / 4385564.000000 | 0.011933 / 0.084635 / 0.461646 | 0.000000 / 0.000000 / 0.018853 |
| Materna-T2 | THROUGHPUT | 0.051960 / 1.017106 / 6.436150 | 1.000000 / 34.500000 / 3992.750000 | 0.010284 / 0.123223 / 0.576208 | 0.000000 / 0.000000 / 0.535979 |
| Materna-T3 | CPU | 0.020000 / 0.911250 / 35.150000 | 0.020000 / 0.911250 / 35.150000 | 0.001011 / 0.024452 / 0.707498 | 0.000000 / 0.000000 / 0.000000 |
| Materna-T3 | DISK_WRITE | 0.052644 / 0.639756 / 4.908543 | 1.000000 / 14.000000 / 24334.000000 | 0.009663 / 0.098259 / 0.980240 | 0.000000 / 0.000000 / 0.367031 |
| Materna-T3 | MEMORY | 23908.000000 / 419430.000000 / 3154117.000000 | 23908.000000 / 419430.000000 / 3154117.000000 | 0.013358 / 0.085366 / 0.540382 | 0.000000 / 0.000000 / 0.489069 |
| Materna-T3 | THROUGHPUT | 0.068993 / 0.864997 / 5.348279 | 1.000000 / 26.750000 / 13601.000000 | 0.007242 / 0.123392 / 0.476222 | 0.000000 / 0.000000 / 0.667350 |

| Trace disk-write partitions | Native minimum | Native Q25 | Native median | Native Q75 | Native maximum | Transformed minimum | Transformed Q25 | Transformed Q75 | Transformed maximum |
|---|---|---|---|---|---|---|---|---|---|
| Materna-T1 | 0.000000 / 12.500000 / 174.000000 | 0.000000 / 30.000000 / 1008.000000 | 0.000000 / 40.000000 / 1826.000000 | 1.000000 / 61.000000 / 24436.000000 | 87.000000 / 2934.000000 / 673985.000000 | 0.000000 / 2.602003 / 5.164786 | 0.000000 / 3.433987 / 6.916715 | 0.693147 / 4.127134 / 10.103854 | 4.477337 / 7.984463 / 13.420965 |
| Materna-T2 | 0.000000 / 6.000000 / 215.000000 | 0.000000 / 15.000000 / 426.000000 | 0.000000 / 22.000000 / 686.000000 | 1.000000 / 34.000000 / 10977.000000 | 92.000000 / 2120.000000 / 93037.000000 | 0.000000 / 1.945910 / 5.375278 | 0.000000 / 2.772589 / 6.056784 | 0.693147 / 3.555348 / 9.303647 | 4.532599 / 7.659643 / 11.440763 |
| Materna-T3 | 0.000000 / 4.000000 / 183.000000 | 0.000000 / 13.000000 / 471.000000 | 1.000000 / 19.000000 / 794.000000 | 2.000000 / 37.000000 / 24514.000000 | 68.000000 / 2530.000000 / 89132.000000 | 0.000000 / 1.609438 / 5.214936 | 0.000000 / 2.639057 / 6.156979 | 1.098612 / 3.637586 / 10.107040 | 4.234107 / 7.836352 / 11.397885 |

No existing near-zero threshold was defined; only the directly computed exact-zero proportion is reported.

## Appendix E. Every VM's T1/T3 disk-write errors

POST-HOC DIAGNOSTIC. Native MAE units KB/s, ratio dimensionless. Equal fold/seed/horizon averages of already-produced matched errors. Sorting is lexical exact VM identifier (leading zeros preserved).

| Trace | VM | S2 MAE | M1 MAE | M1/S2 | M1−S2 |
|---|---|---|---|---|---|
| Materna-T1 | 04 | 1.135757 | 1.132254 | 0.996915 | -0.003503 |
| Materna-T1 | 08 | 5.742846 | 6.528369 | 1.136783 | 0.785523 |
| Materna-T1 | 103 | 1220.593160 | 1203.204181 | 0.985754 | -17.388979 |
| Materna-T1 | 105 | 339.687602 | 351.878829 | 1.035890 | 12.191227 |
| Materna-T1 | 128 | 23.689825 | 23.792878 | 1.004350 | 0.103053 |
| Materna-T1 | 133 | 1364.473522 | 1293.278778 | 0.947823 | -71.194744 |
| Materna-T1 | 134 | 650.568942 | 691.483073 | 1.062890 | 40.914131 |
| Materna-T1 | 227 | 10.455147 | 11.424334 | 1.092700 | 0.969187 |
| Materna-T1 | 246 | 717.018004 | 788.845437 | 1.100175 | 71.827433 |
| Materna-T1 | 26 | 44.042334 | 44.012903 | 0.999332 | -0.029431 |
| Materna-T1 | 266 | 176.658776 | 2253.499329 | 12.756226 | 2076.840553 |
| Materna-T1 | 272 | 5.051907 | 5.225361 | 1.034334 | 0.173453 |
| Materna-T1 | 281 | 2758.336578 | 2757.697267 | 0.999768 | -0.639311 |
| Materna-T1 | 299 | 18.028664 | 61.130522 | 3.390741 | 43.101858 |
| Materna-T1 | 302 | 5.332419 | 5.317254 | 0.997156 | -0.015166 |
| Materna-T1 | 303 | 5.469010 | 5.478084 | 1.001659 | 0.009074 |
| Materna-T1 | 305 | 28.349731 | 32.068161 | 1.131163 | 3.718430 |
| Materna-T1 | 306 | 2.436375 | 2.442161 | 1.002375 | 0.005787 |
| Materna-T1 | 343 | 18.245999 | 18.466281 | 1.012073 | 0.220282 |
| Materna-T1 | 345 | 3.660863 | 3.703258 | 1.011581 | 0.042395 |
| Materna-T1 | 380 | 5.973878 | 6.137269 | 1.027351 | 0.163391 |
| Materna-T1 | 393 | 334.947012 | 352.515775 | 1.052452 | 17.568763 |
| Materna-T1 | 397 | 0.912289 | 0.984158 | 1.078778 | 0.071868 |
| Materna-T1 | 416 | 1.562698 | 1.624131 | 1.039313 | 0.061434 |
| Materna-T1 | 440 | 19.504348 | 26.611836 | 1.364405 | 7.107488 |
| Materna-T1 | 442 | 594.815182 | 762.607080 | 1.282091 | 167.791898 |
| Materna-T1 | 478 | 124.342370 | 131.229892 | 1.055392 | 6.887522 |
| Materna-T1 | 493 | 3.212915 | 3.315972 | 1.032076 | 0.103058 |
| Materna-T1 | 498 | 0.908239 | 0.935385 | 1.029888 | 0.027146 |
| Materna-T1 | 508 | 16.925326 | 16.923918 | 0.999917 | -0.001408 |
| Materna-T1 | 74 | 45.156342 | 45.983106 | 1.018309 | 0.826764 |
| Materna-T1 | 75 | 42.093361 | 42.098170 | 1.000114 | 0.004809 |
| Materna-T1 | 76 | 53.137155 | 55.731921 | 1.048831 | 2.594766 |
| Materna-T1 | 92 | 244.253437 | 319.799375 | 1.309293 | 75.545938 |
| Materna-T1 | 98 | 1.321367 | 1.393027 | 1.054232 | 0.071660 |
| Materna-T3 | 04 | 0.984095 | 0.995275 | 1.011360 | 0.011180 |
| Materna-T3 | 08 | 4.068691 | 4.057442 | 0.997235 | -0.011249 |
| Materna-T3 | 103 | 3.765787 | 3.886765 | 1.032126 | 0.120978 |
| Materna-T3 | 105 | 589.928739 | 617.236881 | 1.046291 | 27.308142 |
| Materna-T3 | 128 | 10.300430 | 10.221418 | 0.992329 | -0.079012 |
| Materna-T3 | 133 | 21.567378 | 21.568920 | 1.000072 | 0.001542 |
| Materna-T3 | 134 | 21.656235 | 22.224387 | 1.026235 | 0.568152 |
| Materna-T3 | 227 | 26.477548 | 28.409495 | 1.072965 | 1.931947 |
| Materna-T3 | 246 | 6.351634 | 6.459205 | 1.016936 | 0.107571 |
| Materna-T3 | 26 | 11.158819 | 12.005500 | 1.075876 | 0.846681 |
| Materna-T3 | 266 | 1.276635 | 1.624699 | 1.272641 | 0.348064 |
| Materna-T3 | 272 | 126.056883 | 1714.519358 | 13.601156 | 1588.462475 |
| Materna-T3 | 281 | 23.254637 | 25.037782 | 1.076679 | 1.783144 |
| Materna-T3 | 299 | 30.574696 | 82.920848 | 2.712074 | 52.346152 |
| Materna-T3 | 302 | 136.352015 | 149.582586 | 1.097032 | 13.230570 |
| Materna-T3 | 303 | 152.549486 | 159.543266 | 1.045846 | 6.993779 |
| Materna-T3 | 305 | 20.401088 | 27.068221 | 1.326803 | 6.667133 |
| Materna-T3 | 306 | 2.094740 | 2.582239 | 1.232726 | 0.487500 |
| Materna-T3 | 343 | 0.944428 | 0.948852 | 1.004684 | 0.004423 |
| Materna-T3 | 345 | 6.359597 | 9.391989 | 1.476821 | 3.032392 |
| Materna-T3 | 380 | 6.341284 | 6.448201 | 1.016861 | 0.106918 |
| Materna-T3 | 393 | 1.504039 | 1.506887 | 1.001894 | 0.002848 |
| Materna-T3 | 397 | 254.383129 | 310.991427 | 1.222532 | 56.608298 |
| Materna-T3 | 416 | 36.104423 | 37.660309 | 1.043094 | 1.555886 |
| Materna-T3 | 440 | 136.817175 | 136.936658 | 1.000873 | 0.119482 |
| Materna-T3 | 442 | 85.096058 | 85.233549 | 1.001616 | 0.137490 |
| Materna-T3 | 478 | 4.560419 | 4.553840 | 0.998557 | -0.006579 |
| Materna-T3 | 493 | 1.132270 | 1.173528 | 1.036438 | 0.041258 |
| Materna-T3 | 498 | 0.877861 | 0.889830 | 1.013634 | 0.011969 |
| Materna-T3 | 508 | 1.200939 | 1.266330 | 1.054451 | 0.065392 |
| Materna-T3 | 74 | 122.577608 | 129.093596 | 1.053158 | 6.515988 |
| Materna-T3 | 75 | 114.709157 | 130.032866 | 1.133587 | 15.323708 |
| Materna-T3 | 76 | 433.750112 | 447.929723 | 1.032691 | 14.179611 |
| Materna-T3 | 92 | 157.701880 | 184.624406 | 1.170718 | 26.922526 |
| Materna-T3 | 98 | 8.918737 | 9.609149 | 1.077411 | 0.690412 |

## Appendix F. Objective-rank diagnostic and context-association detail

CPU/memory affine-score ordering differences, using stored scaled validation MAE × its inner native IQR. This is a post-hoc score reconstruction, not a rerun of validation predictions or model selection.

| Block | Formulation | Resource | Entity–fold units | Different affine raw-score ranking | Stored selector disagreements |
|---|---|---|---|---|---|
| TimeTrack | S1 | CPU | 35 | 3 | 0 |
| TimeTrack | S1 | MEMORY | 35 | 10 | 0 |
| TimeTrack | S2 | CPU | 35 | 3 | 0 |
| TimeTrack | S2 | MEMORY | 35 | 10 | 0 |
| fastStorage | S1 | CPU | 175 | 11 | 0 |
| fastStorage | S1 | MEMORY | 175 | 6 | 0 |
| fastStorage | S2 | CPU | 175 | 12 | 0 |
| fastStorage | S2 | MEMORY | 175 | 7 | 0 |
| Rnd | S1 | CPU | 175 | 9 | 0 |
| Rnd | S1 | MEMORY | 175 | 4 | 0 |
| Rnd | S2 | CPU | 175 | 6 | 0 |
| Rnd | S2 | MEMORY | 175 | 6 | 0 |
| Materna-T1 | S1 | CPU | 175 | 4 | 0 |
| Materna-T1 | S1 | MEMORY | 175 | 7 | 0 |
| Materna-T1 | S2 | CPU | 175 | 2 | 0 |
| Materna-T1 | S2 | MEMORY | 175 | 8 | 0 |
| Materna-T2 | S1 | CPU | 175 | 6 | 0 |
| Materna-T2 | S1 | MEMORY | 175 | 7 | 0 |
| Materna-T2 | S2 | CPU | 175 | 7 | 0 |
| Materna-T2 | S2 | MEMORY | 175 | 6 | 0 |
| Materna-T3 | S1 | CPU | 175 | 6 | 0 |
| Materna-T3 | S1 | MEMORY | 175 | 1 | 0 |
| Materna-T3 | S2 | CPU | 175 | 2 | 0 |
| Materna-T3 | S2 | MEMORY | 175 | 4 | 0 |

Five largest native excess-error entity/fold units per requested concern (averages of existing seed/horizon metrics):

| Case | Entity | Fold | S2 L | M1 L | S2 MAE | M1 MAE | M1−S2 | Context mismatch |
|---|---|---|---|---|---|---|---|---|
| TimeTrack MEMORY | machine01 | 2 | 128 | 64 | 446438210.313781 | 926941614.623825 | 480503404.310044 | YES |
| TimeTrack MEMORY | machine01 | 3 | 32 | 64 | 232483216.839856 | 704202764.155635 | 471719547.315779 | YES |
| TimeTrack MEMORY | machine03 | 5 | 64 | 32 | 1108870763.903581 | 1281883958.789564 | 173013194.885983 | YES |
| TimeTrack MEMORY | machine01 | 4 | 128 | 128 | 506758999.943608 | 640660816.221478 | 133901816.277871 | NO |
| TimeTrack MEMORY | machine03 | 3 | 128 | 128 | 364521978.123427 | 483894225.361283 | 119372247.237856 | NO |
| fastStorage THROUGHPUT | 949 | 3 | 18 | 18 | 3931.285434 | 6721.022656 | 2789.737223 | NO |
| fastStorage THROUGHPUT | 949 | 5 | 18 | 18 | 5942.140304 | 7605.820876 | 1663.680572 | NO |
| fastStorage THROUGHPUT | 949 | 4 | 18 | 18 | 4617.313695 | 5822.761737 | 1205.448042 | NO |
| fastStorage THROUGHPUT | 949 | 1 | 9 | 4 | 5699.566279 | 6684.203038 | 984.636759 | YES |
| fastStorage THROUGHPUT | 949 | 2 | 18 | 9 | 3183.397147 | 3458.035135 | 274.637989 | YES |
| Rnd CPU | 232 | 4 | 4 | 18 | 11.274261 | 17.312786 | 6.038525 | YES |
| Rnd CPU | 233 | 4 | 18 | 18 | 11.969034 | 17.055795 | 5.086760 | NO |
| Rnd CPU | 232 | 3 | 9 | 18 | 12.855841 | 17.641210 | 4.785369 | YES |
| Rnd CPU | 232 | 5 | 4 | 18 | 7.261660 | 11.670356 | 4.408696 | YES |
| Rnd CPU | 233 | 3 | 9 | 18 | 12.758435 | 17.030357 | 4.271923 | YES |
| Materna-T1 DISK_WRITE | 266 | 1 | 18 | 18 | 260.189445 | 6429.199023 | 6169.009578 | NO |
| Materna-T1 DISK_WRITE | 266 | 2 | 18 | 18 | 171.302197 | 1819.455478 | 1648.153282 | NO |
| Materna-T1 DISK_WRITE | 266 | 3 | 18 | 18 | 152.575217 | 1284.035806 | 1131.460589 | NO |
| Materna-T1 DISK_WRITE | 266 | 4 | 18 | 18 | 136.868146 | 916.176544 | 779.308398 | NO |
| Materna-T1 DISK_WRITE | 266 | 5 | 18 | 18 | 162.358876 | 818.629795 | 656.270919 | NO |
| Materna-T3 DISK_WRITE | 272 | 1 | 18 | 18 | 157.362751 | 2405.550567 | 2248.187816 | NO |
| Materna-T3 DISK_WRITE | 272 | 3 | 9 | 18 | 109.495984 | 1656.492102 | 1546.996117 | YES |
| Materna-T3 DISK_WRITE | 272 | 4 | 18 | 18 | 106.729286 | 1602.727099 | 1495.997813 | NO |
| Materna-T3 DISK_WRITE | 272 | 2 | 9 | 18 | 138.989859 | 1525.024605 | 1386.034747 | YES |
| Materna-T3 DISK_WRITE | 272 | 5 | 9 | 18 | 117.706533 | 1382.802415 | 1265.095882 | YES |

## Appendix G. Verbatim frozen rule fields

The following predicate strings/values are extracted unchanged from the authoritative frozen analysis criteria. Field selection/JSON indentation is for this diagnostic report only; the source file is unchanged. Trace/RQ outcomes, including all seven class changes, were read from frozen result artifacts rather than recalculated.

```json
{
  "positive_count_semantics": {
    "scope": [
      "trace",
      "comparison",
      "resource"
    ],
    "positive_horizons_range": [
      0,
      5
    ],
    "positive_VMs_range": [
      0,
      35
    ],
    "positive_folds_range": [
      0,
      5
    ],
    "positive_seed_aggregate_signs_range": [
      0,
      3
    ],
    "VM_positivity": "aggregate_over_folds_and_horizons_first",
    "fold_positivity": "aggregate_over_VMs_and_horizons_first",
    "seed_positivity": "aggregate_over_VMs_folds_and_horizons_for_that_seed",
    "matching": "matched_formulation_comparisons"
  },
  "resource_classification": {
    "BROAD_POSITIVE": {
      "all_required": true,
      "overall_gain_minimum_percent": 1.0,
      "positive_horizons_minimum": 4,
      "positive_VMs_minimum": 25,
      "positive_folds_minimum": 4,
      "positive_seeds_minimum": 2
    },
    "CONDITIONALLY_POSITIVE": {
      "all_required": true,
      "precedence_exclusion": "not_BROAD_POSITIVE",
      "overall_gain_strictly_greater_than_percent": 0.0,
      "positive_horizons_minimum": 3,
      "positive_VMs_minimum": 15,
      "positive_folds_minimum": 3,
      "positive_seeds_minimum": 2
    },
    "BROAD_NEGATIVE": {
      "all_required": true,
      "overall_gain_maximum_percent": -1.0,
      "positive_horizons_maximum": 1,
      "positive_VMs_maximum": 10,
      "positive_folds_maximum": 1,
      "positive_seeds_maximum": 1
    },
    "otherwise": "NEUTRAL_OR_MIXED",
    "threshold_changes_permitted": false
  },
  "mechanical_definitions": {
    "positive_resource": "resource_classification_is_BROAD_POSITIVE_or_CONDITIONALLY_POSITIVE",
    "negative_resource_for_M1_vs_S1_trace_summary": "overall_primary_gain_strictly_less_than_zero",
    "materially_negative_resource": "overall_primary_gain_less_than_or_equal_to_minus_1_percent",
    "strong_target_specific_tradeoffs": "maximum_resource_overall_primary_gain_at_least_plus_1_percent_and_minimum_resource_overall_primary_gain_at_most_minus_1_percent",
    "material_positive_and_negative_synthesis": "at_least_one_synthesized_resource_gain_at_least_plus_1_percent_and_at_least_one_at_most_minus_1_percent",
    "sign": "positive_if_gain_greater_than_zero_negative_if_less_than_zero_zero_otherwise"
  },
  "trace_decisions": {
    "S2_vs_S1": {
      "precedence": [
        "CROSS_RESOURCE_INPUT_SUPPORTED",
        "CROSS_RESOURCE_INPUT_NOT_SUPPORTED",
        "CROSS_RESOURCE_INPUT_MIXED"
      ],
      "CROSS_RESOURCE_INPUT_SUPPORTED": "positive_resource_count >= 3 and equal_resource_mean_primary_gain > 0 and BROAD_NEGATIVE_count <= 1",
      "CROSS_RESOURCE_INPUT_NOT_SUPPORTED": "(positive_resource_count <= 1 and equal_resource_mean_primary_gain <= 0) or BROAD_NEGATIVE_count >= 2",
      "CROSS_RESOURCE_INPUT_MIXED": "otherwise"
    },
    "M1_vs_S2": {
      "conservative_precedence": [
        "SHARED_REPRESENTATION_NEGATIVE_TRANSFER",
        "SHARED_REPRESENTATION_NOT_SUPPORTED",
        "SHARED_REPRESENTATION_SUPPORTED",
        "SHARED_REPRESENTATION_CONDITIONALLY_SUPPORTED"
      ],
      "SHARED_REPRESENTATION_SUPPORTED": "positive_resource_count >= 3 and equal_resource_mean_primary_gain > 0 and BROAD_NEGATIVE_count == 0",
      "SHARED_REPRESENTATION_CONDITIONALLY_SUPPORTED": "equal_resource_mean_primary_gain > 0 and positive_resource_count >= 2 and full_supported_criteria_fail",
      "SHARED_REPRESENTATION_NEGATIVE_TRANSFER": "(positive_resource_count >= 1 and count_of_resources_that_are_BROAD_NEGATIVE_or_materially_negative >= 2) or strong_target_specific_tradeoffs",
      "SHARED_REPRESENTATION_NOT_SUPPORTED": "positive_resource_count <= 1 and equal_resource_mean_primary_gain <= 0",
      "residual_rule": "if_no_named_predicate_applies_assign_SHARED_REPRESENTATION_NOT_SUPPORTED_and_persist_reason_residual_no_support"
    },
    "M1_vs_S1": {
      "JOINT_SYSTEM_BROADLY_BENEFICIAL": "positive_overall_gain_resource_count >= 3 and equal_resource_mean_primary_gain > 0",
      "JOINT_SYSTEM_BROADLY_HARMFUL": "negative_overall_gain_resource_count >= 3 and equal_resource_mean_primary_gain < 0",
      "JOINT_SYSTEM_MIXED": "otherwise",
      "use": "R3_only"
    }
  },
  "bootstrap": {
    "procedure": "paired_VM_cluster_bootstrap_separately_within_each_trace",
    "resampling_unit": "VM",
    "VM_draws_with_replacement": 35,
    "retain_all_five_folds": true,
    "preserve_paired_formulation_structure": true,
    "input": "seed_averaged_matched_MAEs",
    "replicates": 10000,
    "interval": "percentile_95_percent",
    "percentiles": [
      2.5,
      97.5
    ],
    "scopes": [
      "trace_comparison_resource_lead",
      "trace_comparison_resource_overall"
    ],
    "rng_seed": 20261007,
    "rng_seed_provenance": "Phase_4C_scientific_analysis_provenance",
    "bootstrap_traces_as_independent_observations": false,
    "temporal_synthesis_nominal_CI": false,
    "inferential_uncertainty_result": "trace_specific_intervals"
  },
  "R1": {
    "question": "Is cross-resource S2 benefit resource/time-block dependent rather than broadly beneficial?",
    "precedence": [
      "R1_BROAD_CROSS_RESOURCE_BENEFIT",
      "R1_RESOURCE_TEMPORAL_DEPENDENCE_CONFIRMED",
      "R1_CROSS_RESOURCE_INPUT_NOT_SUPPORTED",
      "R1_MIXED_OR_INCONCLUSIVE"
    ],
    "R1_BROAD_CROSS_RESOURCE_BENEFIT": "supported_trace_count >= 2 and mean_of_four_synthesized_resource_gains > 0 and positive_synthesized_resource_count >= 3",
    "R1_RESOURCE_TEMPORAL_DEPENDENCE_CONFIRMED": "broad_benefit_fails and (trace_level_cross_resource_decisions_not_identical or resource_sign_change_count >= 2 or resource_classification_change_count >= 2)",
    "R1_CROSS_RESOURCE_INPUT_NOT_SUPPORTED": "supported_trace_count == 0 and mean_of_four_synthesized_resource_gains <= 0 and positive_synthesized_resource_count <= 1 and temporal_dependence_does_not_apply",
    "R1_MIXED_OR_INCONCLUSIVE": "otherwise"
  },
  "R2": {
    "question": "Does naive M1 sharing again fail to provide broad improvement over S2?",
    "precedence": [
      "R2_NEGATIVE_SHARING_REPLICATED",
      "R2_MIXED_SHARING_EFFECT",
      "R2_SHARING_BENEFIT_REPLICATED",
      "R2_INCONCLUSIVE"
    ],
    "R2_NEGATIVE_SHARING_REPLICATED": "supported_trace_count == 0 and conditionally_supported_trace_count <= 1 and mean_of_four_synthesized_resource_gains <= 0 and positive_synthesized_resource_count <= 1",
    "R2_MIXED_SHARING_EFFECT": "supported_trace_count == 0 and material_positive_and_negative_synthesis",
    "R2_SHARING_BENEFIT_REPLICATED": "supported_or_conditionally_supported_trace_count >= 2 and mean_of_four_synthesized_resource_gains > 0 and positive_synthesized_resource_count >= 3",
    "R2_INCONCLUSIVE": "otherwise"
  },
  "R3": {
    "question": "Does the complete shared M1 system again fail to outperform separate local S1 models broadly?",
    "precedence": [
      "R3_JOINT_SYSTEM_UNDERPERFORMANCE_REPLICATED",
      "R3_JOINT_SYSTEM_PARTIAL_UNDERPERFORMANCE",
      "R3_JOINT_SYSTEM_BENEFIT",
      "R3_MIXED_OR_INCONCLUSIVE"
    ],
    "R3_JOINT_SYSTEM_UNDERPERFORMANCE_REPLICATED": "all_four_synthesized_resource_gains_negative and broadly_harmful_trace_count >= 2",
    "R3_JOINT_SYSTEM_PARTIAL_UNDERPERFORMANCE": "mean_of_four_synthesized_resource_gains <= 0 and positive_synthesized_resource_count <= 2 and full_replicated_criterion_fails",
    "R3_JOINT_SYSTEM_BENEFIT": "positive_synthesized_resource_count >= 3 and mean_of_four_synthesized_resource_gains > 0 and broadly_beneficial_trace_count >= 2",
    "R3_MIXED_OR_INCONCLUSIVE": "otherwise"
  },
  "R4": {
    "question": "Do effects vary across Materna T1/T2/T3?",
    "primary_heterogeneity_basis": "frozen_resource_classifications",
    "TEMPORALLY_CLASSIFICATION_VARIABLE": "resource_comparison_classification_not_identical_across_T1_T2_T3",
    "report_raw_sign_reversal_separately": true,
    "precedence": [
      "R4_TEMPORAL_HETEROGENEITY_CONFIRMED",
      "R4_TEMPORAL_HETEROGENEITY_WEAK",
      "R4_TEMPORAL_HETEROGENEITY_NOT_SUPPORTED"
    ],
    "R4_TEMPORAL_HETEROGENEITY_CONFIRMED": "classification_variable_resource_comparison_count >= 2 or S2_vs_S1_global_trace_decisions_differ or M1_vs_S2_global_trace_decisions_differ",
    "R4_TEMPORAL_HETEROGENEITY_WEAK": "classification_variable_resource_comparison_count == 1 and global_trace_decisions_identical",
    "R4_TEMPORAL_HETEROGENEITY_NOT_SUPPORTED": "classification_variable_resource_comparison_count == 0 and global_trace_decisions_identical",
    "post_hoc_regime_mining": false
  }
}
```

## Evidence sources and reproducibility notes

- Model and fit lifecycle: model definitions plus scientific drivers linked above; no pilot fitted outcome was reused.
- Contexts/epochs: each block's `selected_contexts.csv`, `selected_epochs.csv` and `inner_run_registry.csv`.
- Seed/VM diagnostics: each block's existing `metrics.parquet`; external/Materna `analysis/matched_vm_fold_cells.csv` and `positive_seed_signs.csv`.
- Primary native errors, intervals and classifications: existing `analysis/primary_macro_mae.csv`, `comparisons/secondary_aggregation_diagnostics.csv`, `resource_classifications.csv`, `bootstrap_uncertainty.csv`, and `analysis/temporal_classification_changes.csv`.
- Persistence: existing `analysis/persistence_skill_summary.csv`, `persistence_summary.csv`; TimeTrack's frozen PHASE3C_FACTORIAL_SCIENTIFIC_REPORT.md persistence table.
- Inner M1 curves: existing `m1_resource_loss_history.parquet`; final curves/scalers: per-fit completion JSON.
- Parameter/state integrity: 3,150 existing final S1/S2/M1 disk-write-relevant checkpoints across T1/T3 loaded weights-only, exact state parameter counts and registry SHA-256 checked.
- Scaler integrity: frozen139-MB Materna archive;105 selected trace/VM series; exact3150 training partitions, original physical validity rules and timestamp mapping; no new cleaned-data artifact.
- No scientific runner, training function, experiment, bootstrap or headline-aggregation program was launched. Diagnostic calculations were inline read-only Python using the existing environment, with bytecode writing disabled.
- No manuscript, figure, table, reference, scientific manifest, model or prediction artifact was written.

STOP. No follow-up experiment or manuscript revision is authorised or started by this report.

STAGE_18A1_PASS

