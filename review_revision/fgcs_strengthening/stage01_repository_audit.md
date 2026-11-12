# Stage 01 — repository baseline and implementation feasibility audit

Date: 10 November 2026, Europe/Helsinki. Repository: /Users/fgtek002/TimeTrack.

**STAGE01_PASS — sufficient verified baseline information is available to finalise a prespecified analysis plan. This is an audit pass, not authorisation to implement or execute the planned experiments.** All implementation choices below remain proposals. Only this report was created. Training, inference, dependency installation, downloads, manuscript/supplement/package/result edits, commit/tag/push: **0**.

## 1. Authority and current state

**VERIFIED.** Current branch: `paper/jss-review-revision`; HEAD: `0e8cad884896a706f62f0fae4ab2b52812f9b033`. Annotated tag `jss-review-robustness-reproducibility-v1` peels to this HEAD; tag object is `e9eeeceb237f51763be356a255f7ec18d5776b47`. This is the newest current reproducibility/evidence checkpoint, including original science and completed Stage18 controls/diagnostics. It does not make the controls prospective original results.

The original final scientific freeze is tag `phase4d-materna-final-scientific-freeze-v1` → `fee20c316040c57b69ba12a193530c955b539771` (also local `main`). `paper/jss` points to `f6936cd111d911e40ec2725a18fdfc53768d9ccf`, the intervening manuscript freeze. Local origin-tracking refs agree with these named tips; **no remote fetch or live public-remote verification** was performed.

All six original metrics.parquet inputs and the existing seed_sensitivity.csv were byte-compared with their blobs at the current reproducibility tag: exact matches. Git's tracked diff from that tag contains only the pre-existing changes to /Users/fgtek002/TimeTrack/manuscript/jss/manuscript.tex and manuscript.pdf. Neither was touched here. Later L1/L2 and Array work is manuscript/metadata/packaging work; it is not a later scientific experiment.

**Local state beyond what Git alone supplies.** Before this report there were 306,198 untracked, nonignored files: 147,127 under review_revision/experiments; 113,407 under independent_validation/06_materna_replication; 37,961 under independent_validation/05_bitbrains_factorial; 3,780 under multiresource/04_lstm_factorial; 3,360 under benchmark/neural_v2; the remainder principally manuscript and audit evidence. Ignored model/prediction archives are additionally present. The untracked research files inspected are existing completion journals/registries, recovery/predecessor evidence and older neural-v2 records; no new strengthening implementation or completed M0/five-seed/mechanistic experiment was found. Project Python searches, including legacy research code and excluding environments/generated outputs, found no M0, iTransformer, PCGrad, GradNorm or autograd.grad implementation. Git status alone cannot authenticate ignored/untracked archives or establish the chronology of every local file.

Thus: **scientific local artifacts exist outside the lean tagged Git file set**, but no newer scientific endpoint or protocol than the tagged Stage18 evidence was identified. This audit did not rehash the entire approximately 27.5 GB model/prediction archive; it does not certify every historical journal's bytes. It verified compact endpoints and active seals and sampled saved artifact hashes as described below. Do not mistake older failed attempts or predecessor snapshots for current unresolved failures.

## 2. Exact baseline locations and counts

Paths below are absolute. Define these exact frozen output roots:

- **TT** = /Users/fgtek002/TimeTrack/multiresource/04_lstm_factorial/outputs/scientific
- **FS** = /Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/outputs/scientific_v2/fastStorage
- **RN** = /Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/outputs/scientific_v2/Rnd
- **T1/T2/T3** = /Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/outputs/scientific_v1/Materna-T1, Materna-T2 and Materna-T3, respectively.

Each root contains metrics.parquet, persistence_metrics.parquet, selected_contexts.csv, selected_epochs.csv, inner_run_registry.csv, run_registry.csv and runtime/completions/{inner,final}. Original model/prediction namespaces are s1/models, s2/models, m1/models and matching predictions subdirectories. Model filenames are run_id.pt; predictions are run_id.parquet. These are entity-specific fits, never models pooled across VMs.

| Block | Entities (each resource) | Metric rows | Inner completions | Final completions | S1/S2/M1 saved models | S1/S2/M1 prediction files |
|---|---:|---:|---:|---:|---|---|
| TimeTrack | 7 | 10080 | 2835 | 945 | 420 / 420 / 105 | 420 / 420 / 105 |
| fastStorage | 35 | 31500 | 14175 | 4725 | 2100 / 2100 / 525 | 2100 / 2100 / 525 |
| Rnd | 35 | 31500 | 14175 | 4725 | 2100 / 2100 / 525 | 2100 / 2100 / 525 |
| Materna-T1 | 35 | 31500 | 14175 | 4725 | 2100 / 2100 / 525 | 2100 / 2100 / 525 |
| Materna-T2 | 35 | 31500 | 14175 | 4725 | 2100 / 2100 / 525 | 2100 / 2100 / 525 |
| Materna-T3 | 35 | 31500 | 14175 | 4725 | 2100 / 2100 / 525 | 2100 / 2100 / 525 |

Totals: **167,580** primary metric rows, **73,710** original inner completions and **24,570** original final models/prediction files (98,280 successful fit units). Every metric table was read directly; scientific identity (resource, entity, fold, lead, seed, formulation) is unique, native MAEs are finite/nonnegative, and paired evaluation sample counts agree. Every resource has the same 7/35 executed entities within its block. Seeds are 0/1/2, five folds, eight TimeTrack leads or five external leads. There are 182 entity-block records, not 182 independent entities: the same 35 Materna VMs recur across T1–T3. Across TimeTrack + the two Bitbrains cohorts + the shared Materna cohort there are 112 source-specific entity records; numerical ID coincidences across different sources do not imply the same entity.

One original completion/model/prediction triple per formulation per block was checked against its completion-record SHA-256: **18 model hashes and 18 prediction hashes matched**, without loading weights or invoking a model. This is a presence/schema/sample-hash audit, not an exhaustive replay of all 24,570 models.

### Required companion files

- TT support: TT/support_manifest.parquet. Comparisons: TT/comparisons/{s2_vs_s1,m1_vs_s2,m1_vs_s1}.csv and *_cells.csv. M1 logs: TT/m1_resource_loss_history.parquet and m1_loss_balance_summary.csv.
- External matched/aggregate endpoints: /Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/outputs/scientific_v2/analysis/{matched_vm_fold_cells.csv,primary_macro_mae.csv}; comparisons/secondary_aggregation_diagnostics.csv under the same scientific_v2 root.
- Materna equivalents: /Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/outputs/scientific_v1/analysis/{matched_vm_fold_cells.csv,primary_macro_mae.csv}, comparisons/secondary_aggregation_diagnostics.csv.
- Original final completion JSON stores identity, selected epoch/context, support hashes, training-only scaler metadata, model/prediction hashes, train/prediction seconds, file bytes and RSS. Prediction Parquets store native/scaled predictions, truth and support identity. These plus original inputs permit later checkpoint-gradient reconstruction; saved predictions alone cannot recover gradients.
- **Original inner fits do not have an epoch checkpoint bank.** They retain scores/best_epoch, and M1 per-resource loss logs; S1/S2 inner loss-history arrays are generally empty. Final checkpoints are fixed-selected-epoch refits, not inner best-state trajectories, and have no final validation curve. No saved optimizer/RNG trajectory was established by the inspected state_dict writers. Existing final weights cannot establish earlier per-task-best checkpoints.
- Local raw inputs exist: /Users/fgtek002/TimeTrack/discovery/02_dependency_analysis/outputs/canonical_panel.parquet; /Users/fgtek002/TimeTrack/data/external/raw/gwa_t_12_fastStorage.zip (134,047,207 bytes), gwa_t_12_rnd.zip (163,099,172), gwa_t_13_materna.zip (145,292,565). No downloads or new extraction were performed. Input admission must verify their existing hash manifests before any future training.

## 3. Implemented scientific protocol

### Architectures and objectives — VERIFIED

TimeTrack source: /Users/fgtek002/TimeTrack/multiresource/04_lstm_factorial/src/models/lstm.py.
External source: /Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/src/models/lstm.py. Materna deliberately adapts/reuses that external implementation through /Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/run_phase4d_scientific.py and phase4d_execution.py.

All use two unidirectional nn.LSTM layers, H=64, dropout=0.1 between layers, final recurrent output and linear direct-horizon heads; biases enabled. No resource embedding, attention, gradient surgery or learned task weights is present.

| Formulation | Per-entity/fold/seed complement | Input to each model | Output | Parameters TT / external |
|---|---|---|---|---:|
| S1 | four independent encoders/optimizers, one target each | own resource [N,L,1] | [N,8] / [N,5] | 50,952 / 50,757 each |
| S2 | four independent encoders/optimizers, one target each | all four resources [N,L,4] | [N,8] / [N,5] | 51,720 / 51,525 each |
| M1 | one joint encoder/optimizer, four heads | all resources [N,L,4] | [N,4,8] / [N,4,5] | 53,280 / 52,500 total |

Four-network S2 totals are 206,880 / 206,100; four-network S1 totals 203,808 / 203,028. M1's objective is the equal arithmetic mean of four transformed/robust-scaled resource MSEs, averaged over samples and horizons; equal scalar coefficients do not imply equal loss or gradient contribution.

Training/selection sources: /Users/fgtek002/TimeTrack/multiresource/04_lstm_factorial/src/{training.py,selection.py}, run_factorial_scientific.py at the parent root; /Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/src/{training.py,selection.py}, run_phase4c_scientific.py at the parent root.

Adam lr=0.001, batch=256, maximum 50 inner epochs, patience=7, global gradient-norm clipping=1.0. Seed function sets Python/NumPy/Torch and deterministic algorithms with **warn_only=True**, not an unconditional proof of device-independent determinism. Frozen executions request CPU. Final fitting refits from scratch on the full legal outer training partition for the seed-specific chosen epoch and evaluates outer test once.

**Objective terminology trap:** fields/docstrings named nmae/normalized_mae in selection contain **MAE of transformed/robust-scaled targets**, evaluated at each seed's validation-MSE-selected epoch. They are NOT native MAE divided by native training IQR. Selection averages validation MAEs across three seeds and horizons, additionally four resources for M1; smaller L wins exact score ties. S1/S2 choose context separately per target; M1 chooses jointly. Native evaluation NMAE is separately native MAE/native training IQR. Preserve this distinction in the new API and schema; do not change v1 algorithms retroactively.

### Splits, scaling and horizons — VERIFIED

- TimeTrack: /Users/fgtek002/TimeTrack/multiresource/04_lstm_factorial/src/{data.py,support.py,splits.py,transforms.py}; imported split primitives /Users/fgtek002/TimeTrack/benchmark/src/{splits.py,windows.py}. L grid [32,64,128], common maximum support L=128; leads [1,2,4,8,16,32,64,128]. Median cadence ≈42.285 seconds, lead minutes ≈[0.705,1.410,2.819,5.638,11.276,22.552,45.104,90.208]; actual timestamp IDs define support.
- External: /Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/src/{ingestion.py,cleaning.py,panel.py,support.py,splits.py,transforms.py}. L=[4,9,18], common support L=18; leads=[1,2,4,9,18] at five-minute cadence → [5,10,20,45,90] minutes. Drop invalid physical/nonfinite rows, prohibit duplicate timestamps, segment gaps >450 seconds; windows must remain in a contiguous segment.
- Five chronological expanding folds: first ~50% training, then nonoverlapping ~10% test blocks starting at 50/60/70/80/90% of eligible origin count. Outer and inner purge retain training origins only when the latest target timestamp is strictly earlier than the next partition's first origin timestamp. Inner validation is the last 15% of legal outer training origins. No shuffling across temporal partitions; minibatches are seed-shuffled within training only. Shorter contexts must not enlarge support.
- All four resources share legal finite support. Inner scalers fit **unique union of history and target rows belonging to inner-training origins**. Final scalers refit that union for legal outer-training origins. This can include future targets of training origins, never validation/test targets. Scaling is resource-wise transformed median/IQR, not per-horizon scaling, with no cross-entity fitting. CPU/memory identity; throughput/disk log1p; inverse expm1 for log targets and projection max(0,prediction), without upper clipping. Native IQR is retained separately. Zero/nonpositive IQR fails, with no epsilon or fallback.
- Primary native MAE is calculated per entity/fold/seed/resource/horizon; original MacroMAE averages seeds within matched cells, then equal entity/fold cells and horizons. Persistence uses last observed resource repeated over prescribed leads; mean cell skill is not 1−MacroMAE/MacroPersistenceMAE.

### Cohorts — VERIFIED

- TimeTrack all seven machine01…machine07, configured in /Users/fgtek002/TimeTrack/multiresource/04_lstm_factorial/configs/lstm_factorial.json.
- Bitbrains active **V2** cohorts: /Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/protocol_amendment/PHASE4C_V2_SELECTED_COHORTS.csv; active config configs/bitbrains_lstm_factorial_phase4c_v2.json. fastStorage structural 1,250 / scale-eligible 596; Rnd structural 416 / scale-eligible 272. Execute frozen deterministic SHA-256-ranked 35 each, not original pre-amendment cohorts from independent_validation/03_evaluation_design. Positive IQR required across relevant train partitions; scale eligibility conditions the population.
- Materna shared 35 IDs: /Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/manifests/CANDIDATE_35_VM_COHORT.csv, configs/materna_replication_v1.json and phase4d_execution.py. Joint structural pool 398, joint all-three-trace scale-eligible pool 74; selected by frozen SHA-256 key phase4a-v1|Materna-shared|exact-ID. Eligible ≠ executed. T1–T3 are dependent temporal replications, not three independent datasets. Support/scaler evidence: manifests/{MATERNA_SUPPORT_MANIFEST.parquet,MATERNA_SCALER_PARTITIONS.csv,MATERNA_SUPPORT_VALIDATION.json}.
- Bitbrains active support/scalers: /Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/protocol_amendment/{PHASE4C_V2_SUPPORT_MANIFEST.parquet,PHASE4C_V2_SCALER_PARTITIONS.csv,TRAINING_SCALE_ELIGIBILITY.csv}. The older manifests/EXTERNAL_SUPPORT_MANIFEST.parquet belongs to the earlier design; do not substitute it for the V2 execution support.

## 4. Post-hoc and robustness baseline — VERIFIED

All roots below are under /Users/fgtek002/TimeTrack/review_revision/. Controls remain POST-HOC, not new primary estimates.

| Root / authoritative report | Completion evidence | Reuse/limitations |
|---|---|---|
| experiments/s2_common_context / STAGE18B1R_S2_COMMON_CONTEXT_REPORT.md | completion_summary.json status COMPLETE, 10,920 required finals, 5,208 reuses + 5,712 fresh fits, failed=0; C1 active handoff STAGE_18B1R_PASS | frozen H64-M1 context imposed on S2; reuse S2's existing seed-specific inner epoch at forced L; no new inner selection |
| experiments/m1_capacity_matched / STAGE18B2_M1_CAPACITY_MATCHED_REPORT.md | STAGE_18B2_PASS; 8,190 inner + 2,730 final, failed=0, duplicates=0; 10,920 saved .pt files including 8,190 inner checkpoints | H129, fresh original inner selection; 207,980 TT / 206,420 external parameters. Common-S2 still matches H64 contexts, not necessarily H129 |
| experiments/ar_arx_baseline / STAGE18B3R_AR_ARX_RECOVERY_REPORT.md | STAGE_18B3R_PASS; 36,400 inner + 7,280 final valid units; failed=0, duplicates=0 | deterministic Ridge AR/ARX, fixed frozen-M1 contexts, five-alpha inner selection; 35 historical failed finals recovered by same-identity reruns, evidence retained. Actual fits 43,715 versus 43,680 valid units |

Each has posthoc_results.csv (24 unique block/resource endpoints), posthoc_metric_rows.parquet, control_config.json, plans/, provenance/experiment.json and per-unit completion/prediction artifacts. Ridge model artifacts are not .pt; zero .pt files is expected, not missing models. Its .npz predictions and saved model artifacts require the specific adapter, not the LSTM loader.

Active provenance is explicitly recorded by /Users/fgtek002/TimeTrack/review_revision/stage18c1_evidence/posthoc_provenance.json. This audit freshly checked the SHA-256 of **all three active seals, final reports, metric Parquets and result CSVs** against that record: all match. Active seals: common-S2 provenance/recovery_stage18b1r_successor.json; H129 provenance/experiment.json; Ridge recovery/successor_audit_reduction_fix.json. Do not reject the recovered experiments solely because their original seals describe predecessor adapters.

Robustness authority:
- /Users/fgtek002/TimeTrack/review_revision/stage18a1_diagnostic_audit.md — objective/scale/fitting and attribution audit.
- /Users/fgtek002/TimeTrack/review_revision/stage18c1_final_robustness_synthesis.md and stage18c1_evidence/{matched_seed_mean_errors.csv,robust_seed_mean_cells.csv,robust_seed_matched_cells.csv,seed_matched_cell_sensitivity.csv,seed_sensitivity.csv,contextual_evidence.csv,sharing_sensitivity.csv}.
- /Users/fgtek002/TimeTrack/review_revision/stage19g1_evidence/{m1_s2_robustness_24.csv,seed_sensitivity_48.csv,timetrack_memory_attribution.csv,analysis.json}.
- /Users/fgtek002/TimeTrack/review_revision/stage19h1_scale_context/{STAGE19H1_DOMINANT_VM_SCALE_CONTEXT_REPORT.md,analysis.json,input_sha256_inventory.json}.
- Derived-only portability entry point /Users/fgtek002/TimeTrack/review_revision/stage19i2_portability/replay_derived.py, README.md, replay_sources.json and environment documentation: reusable conventions, **not invoked** here because this stage permits only the present report.

Historical runners bind frozen hashes/HEADs, paths, contexts, seeds and legal identities. Do not weaken these seals, run their main functions at a new HEAD or rerun report builders over audited reports. A new, separately frozen study namespace is required.

## 5. Extension implementation feasibility

Labels below distinguish existing components from **NOT IMPLEMENTED / DECISION REQUIRED**. Static feasibility is not a runtime validation.

| Extension | Existing reusable components | Minimum new implementation and prespecification |
|---|---|---|
| M0 shared encoder, own-history paths | LSTM encoders, ModuleList heads, raw four-resource windows, task MSE | **Not implemented.** One input_size=1 LSTM reused for each resource; each head consumes only that resource's encoded history. Input [N,L,4] → four [N,L,1] views, or reshape to [N×4,L,1] then restore axis. No resource embeddings, no cross-resource input mixing; one shared parameter set/optimizer. Assert channel routing, permutation and no-other-input dependence; define dropout/RNG treatment. Joint learning still couples gradients across tasks |
| Five-seed common-context S1/S2/M0/M1 | frozen supports/scalers and context records; common-S2 forcing logic | **Not implemented for five seeds.** Parameterise allowed seeds and heads/horizons; replace exact-three-seed validation in a NEW selector/identity layer. Decide common-L authority before results: frozen v1 M1 L, fixed L, or a new explicitly symmetric inner rule. Force the same L/support/scaler for every formulation; select epochs using inner data only. Original selected S1/S2/M1 fits are not automatically valid common-context reruns |
| M0 capacity match | H129 adapter's count/architecture verification pattern | **Not implemented.** Define comparison target (aggregate S1, aggregate S2, or M1) and matching tolerance/rule; choose width from parameter arithmetic before seeing performance. Match architecture specification, record exact total/encoder/head counts and compute, do not label approximate parameter parity causal isolation |
| Per-task shared-parameter gradients | resource_losses returns individual differentiable task losses | **Not implemented.** autograd.grad each task loss over exactly named encoder parameters; consistent flatten order, zero/unused-gradient handling, loss scale, norms/dots/cosines, pre-clipping location. Keep diagnostic passes from changing optimizer/model/RNG state |
| Deterministic diagnostic batches + same-task noise control | persisted support IDs, train-only windows, seeded loaders | **Not implemented.** Freeze batch-ID manifests/hashes per entity/fold/checkpoint; use training partitions only. Fix checkpoint schedule, batch sizes, resource alignment and dropout/eval-mode policy. A repeat of the SAME batch under deterministic evaluation is a numerical-repeatability check, NOT a sampling-noise floor. Compare two prespecified disjoint/independent batches for the SAME task/checkpoint as the noise control; retain matched cross-task batches and zero-norm cases |
| Per-task checkpoint selection | M1 validation resource-MSE histories exist; S1/S2 own early stops | **Not implemented as shared-task checkpoint bank.** Save task-specific best validation states/epochs with fixed ties and criteria. Decide inner-only selection plus outer fixed-epoch refit versus an explicitly new train/validation final lifecycle. Four independently selected shared states require up to four model copies; record lost consolidation. Never select on outer test. Existing final states cannot reconstruct unsaved earlier epochs |
| Pairwise sharing / leave-one-task-out | task heads, masks and losses can be generalised | **Not implemented.** Six unordered two-task combinations and four three-task leave-one-out subsets if exhaustive. Define input scope separately from output-task subset: all four inputs versus only retained tasks answer different questions. Explicit task ordering, loss normalization, capacity/count/control budget and family-wise analysis hierarchy required |
| PCGrad | raw per-task encoder gradients can be exposed | **Not implemented.** Define projection algorithm/order RNG, shared versus head updates, aggregation and clipping order; preserve equal-gradient baseline as a special case. Synthetic conflicting/aligned/zero-gradient checks and logged projection diagnostics needed before pilots |
| GradNorm | individual losses, encoder gradients, Adam loop | **Not implemented.** Define adaptive weight initialization/normalization, loss reference epoch, balancing exponent, chosen shared layer/parameter set and weight optimizer. Store learned weights/norms and test update math. This changes the objective; do not conflate it with PCGrad or ordinary equal-loss M1 |
| DLinear pilot | /Users/fgtek002/TimeTrack/benchmark/neural_v2/src/models/dlinear.py; alternate benchmark/src/models/dlinear.py | **Existing CPU-target pilot family, not four-resource v1 drop-in.** Trend/residual linear projections plus late channel projection, kernel25 padded average, output defaults8. Reuse network only after explicit 5/8-horizon and own/all-input adaptation; use v1 train-only target transforms/scalers, not neural-v2's different preprocessing |
| PatchTST pilot | /Users/fgtek002/TimeTrack/benchmark/neural_v2/src/models/patchtst.py | **Existing compact PatchTST-style CPU model**, not a claim of full official implementation. Per-channel shared transformer; mean patch pooling; concatenated channel representations, late linear mixing. Defaults patch8/stride4/d_model64/heads4/layers2/FF128/dropout0.1, output8. **External L=4 is rejected by constructor**; choose prespecified shorter patch or padding/admissible context policy without test tuning. Externals/output heads/scaling need adapters |
| iTransformer pilot | no implementation located; original citation is not executable support | **New implementation required** (or later approved dependency/source acquisition). Must specify inverted variate tokens, temporal projection, normalization, sparse horizons, target/output mapping, and small-channel behaviour. Current stage forbids downloads and installs; none attempted |
| LightGBM own/all input | /Users/fgtek002/TimeTrack/benchmark/src/models/lightgbm_model.py; selection.py | **Existing deterministic direct per-horizon regressors**, flatten lag window, regression_l1, random_state0, one thread, deterministic/force_col_wise, no subsampling. Existing grid 2 leaves ×2 learning rates ×2 estimator counts =8 configs per L. Adapter must target each of four resources, common-L/legal supports, transforms/inversion and nested selection. No artificial seed repetitions absent actual stochasticity |
| Training/inference/footprint | original completion train_seconds, prediction_seconds, parameter/model bytes, peak_rss; serialized_state_bytes helper | **Partial existing workload data; new standardized measurement harness needed.** Existing successful worker fit-hours sum inner/final work, not wall time. Inference is a one-shot full test forward timing and may include conversion overhead, not warmed latency. Prespecify device/threads, warm-up/repetitions, batching, synchronization, preprocessing inclusion, peak memory method, state vs optimizer bytes, complement counts and diagnostic overhead |

DLinear/PatchTST already have frozen CPU F0_LOCAL/F1_THROUGHPUT experiments, separate from the S1/S2/M1 study: /Users/fgtek002/TimeTrack/benchmark/neural_v2/{configs/neural_v2.json,DLINEAR_SCIENTIFIC_REPORT.md,PATCHTST_SCIENTIFIC_REPORT.md,src/training.py}. They use feature standardization, CPU-only output, and different selection/target conventions; PatchTST uses AdamW(weight_decay=1e-4), not the plain LSTM's Adam. These are reusable architecture/pilot experience, not completed four-resource tests. /Users/fgtek002/TimeTrack/benchmark/neural_v2/src/training.py:model_factory currently exposes DLinear/LSTM/TCN-v2/PatchTST only.

### Capacity and execution-budget planning arithmetic (not experimental results)

For the proposed two-layer biased M0 with hidden H, one channel and four K-output heads:
`P_M0(H,K) = 12 H² + 20 H + 4 K(H+1)`.
At H64 this is **52,512 TT / 51,732 external**, versus M1 53,280 / 52,500. Reusing one encoder four times changes forward/activation work without multiplying its parameter storage by four. H128 gives **203,296 / 201,748**; H129 gives **206,432 / 204,872**. Matching the four-S1 complement suggests a different nearest-width choice from matching four-S2 (these examples are arithmetic, not an approved width search). H129 is NOT automatically the proper M0 control because it was used for M1.

If all current entity-blocks and five folds are retained, five seeds at ONE common context with S1 four + S2 four + M0 one + M1 one model per complement imply **45,500 final fits**. One inner fit per final identity implies another 45,500 inner fits, **91,000 total**, before capacity/subset/adaptive/pilot arms. Context search across three Ls would change that budget and must be specified separately. This is fit arithmetic, not a runtime forecast. Earlier freezes' flags do not authorise these new fits.

### Environment — verified without installing or importing model drivers

Existing /Users/fgtek002/TimeTrack/old_fgcs_rejected/.venv_legacy/bin/python provides package metadata: NumPy 2.5.1, pandas 3.0.5, PyArrow 25.0.0, torch 2.13.0, scikit-learn 1.9.0, LightGBM 4.7.0. That interpreter was used with -B and PYTHONDONTWRITEBYTECODE=1 for Parquet reads and elementary NumPy/pandas planning calculations only. The bundled desktop Python lacks PyArrow/torch/scikit-learn/LightGBM; its failed Parquet-engine probe was resolved by using the existing legacy environment, not by installing anything. No training forward/backward pass was invoked. Installed version metadata alone does not validate future device determinism or algorithm compatibility; pin a new environment record in the later protocol.

## 6. V1-only planning inputs: log-ratio variance

**NEW DESCRIPTIVE PLANNING CALCULATION FROM EXISTING V1 MAEs ONLY.** It does not replace any v1 estimate, run any model or supply an inferential variance/noise-floor claim. We analyse S2:S1 and M1:S2 separately for each block/resource; no cross-block or cross-resource pooling.

Let `z_e,f,h,s = ln(MAE_candidate / MAE_reference)`, matched by entity/fold/horizon/seed. Use only pairs with both MAEs strictly positive for finite log-variance summaries. Let N be their count, m the overall mean, m_e each entity's finite-row mean, and m_c the finite-seed mean for each c=(e,f,h).

- `B = Σ_e n_e (m_e−m)²/N`: weighted descriptive between-entity variance.
- `W = Σ_rows (z−m_e)²/N`: within-entity variance including folds, horizons and seeds.
- `S = Σ_rows (z−m_c)²/N`: within-matched-cell seed component.
- `C = Σ_rows (m_c−m_e)²/N = W−S`: within-entity cell component.
- `V_total = B + C + S = B+W`. This weighted population-moment identity holds even after unequal finite-row exclusions; equality was checked to 1e-10. Denominators are N, **not ddof=1**. Folds/horizons are correlated repeated observations; S is observed dispersion of the three complete seeded fits, not a gradient-batch noise floor.

For entity-level planning also define `z_es = mean_f,h z_efhs`, `B_z = sample variance_e(mean_s z_es)`, `W_z = mean_e sample variance_s(z_es)` (ddof=1). B_z still includes uncertainty from averaging only three seeds and is **not** a de-noised random-effect variance. For the two Rnd-throughput rows, exclusions unbalance the groups: weighted m_e and equally averaged z_es means are different conventions; B_z/W_z are explicitly supplementary finite-only summaries. No infinite value was silently substituted or winsorised.

| Block/resource | Contrast | Finite N / excluded | B | W | S | B_z | W_z |
|---|---|---:|---:|---:|---:|---:|---:|
| TimeTrack / CPU | S2:S1 | 840 / 0 | 0.001213688 | 0.01845049 | 0.004418712 | 0.001415970 | 0.0006327650 |
| TimeTrack / DISK_WRITE | S2:S1 | 840 / 0 | 0.00006464901 | 0.002023607 | 0.0004147038 | 0.00007542384 | 0.00002837560 |
| TimeTrack / MEMORY | S2:S1 | 840 / 0 | 0.006572924 | 0.06246847 | 0.03420940 | 0.007668411 | 0.006741874 |
| TimeTrack / THROUGHPUT | S2:S1 | 840 / 0 | 0.0005581362 | 0.003648040 | 0.001352680 | 0.0006511589 | 0.0003397767 |
| TimeTrack / CPU | M1:S2 | 840 / 0 | 0.001011453 | 0.01438567 | 0.006862931 | 0.001180029 | 0.001208225 |
| TimeTrack / DISK_WRITE | M1:S2 | 840 / 0 | 0.0001779122 | 0.001932612 | 0.0004500132 | 0.0002075643 | 0.00002878784 |
| TimeTrack / MEMORY | M1:S2 | 840 / 0 | 0.03265466 | 0.1019968 | 0.03485947 | 0.03809710 | 0.007535409 |
| TimeTrack / THROUGHPUT | M1:S2 | 840 / 0 | 0.0001774477 | 0.002407121 | 0.001223537 | 0.0002070223 | 0.0002647266 |
| fastStorage / CPU | S2:S1 | 2625 / 0 | 0.005395067 | 0.02655845 | 0.01025896 | 0.005553746 | 0.002538027 |
| fastStorage / DISK_WRITE | S2:S1 | 2625 / 0 | 0.003443403 | 0.03884937 | 0.01980849 | 0.003544679 | 0.004714218 |
| fastStorage / MEMORY | S2:S1 | 2625 / 0 | 0.001366184 | 0.004560302 | 0.0009109289 | 0.001406366 | 0.0003050886 |
| fastStorage / THROUGHPUT | S2:S1 | 2625 / 0 | 0.01425447 | 0.08186911 | 0.03731952 | 0.01467372 | 0.004479898 |
| fastStorage / CPU | M1:S2 | 2625 / 0 | 0.01384194 | 0.02849081 | 0.009609291 | 0.01424905 | 0.002313842 |
| fastStorage / DISK_WRITE | M1:S2 | 2625 / 0 | 0.009277867 | 0.05025871 | 0.01729622 | 0.009550746 | 0.003951010 |
| fastStorage / MEMORY | M1:S2 | 2625 / 0 | 0.003626574 | 0.005021268 | 0.001091273 | 0.003733238 | 0.0003452845 |
| fastStorage / THROUGHPUT | M1:S2 | 2625 / 0 | 0.02775854 | 0.06634996 | 0.02951961 | 0.02857497 | 0.006942955 |
| Rnd / CPU | S2:S1 | 2625 / 0 | 0.006815402 | 0.02792408 | 0.008913759 | 0.007015855 | 0.002443984 |
| Rnd / DISK_WRITE | S2:S1 | 2625 / 0 | 0.002408868 | 0.01806780 | 0.005660148 | 0.002479717 | 0.001489325 |
| Rnd / MEMORY | S2:S1 | 2625 / 0 | 0.003720936 | 0.008915013 | 0.001650911 | 0.003830376 | 0.0003360256 |
| Rnd / THROUGHPUT | S2:S1 | 2585 / 40 | 0.02722200 | 0.2192351 | 0.05836536 | 0.03195772 | 0.02826688 |
| Rnd / CPU | M1:S2 | 2625 / 0 | 0.02025439 | 0.05023932 | 0.01267107 | 0.02085011 | 0.003206890 |
| Rnd / DISK_WRITE | M1:S2 | 2625 / 0 | 0.02573642 | 0.02697625 | 0.005524141 | 0.02649338 | 0.001301218 |
| Rnd / MEMORY | M1:S2 | 2625 / 0 | 0.004032410 | 0.01191963 | 0.002144771 | 0.004151010 | 0.0005438046 |
| Rnd / THROUGHPUT | M1:S2 | 2621 / 4 | 0.06799386 | 0.3841892 | 0.1803299 | 0.07118455 | 0.02548400 |
| Materna-T1 / CPU | S2:S1 | 2625 / 0 | 0.006369343 | 0.03852960 | 0.009599530 | 0.006556677 | 0.002718870 |
| Materna-T1 / DISK_WRITE | S2:S1 | 2625 / 0 | 0.005527042 | 0.03600750 | 0.01259537 | 0.005689602 | 0.002432053 |
| Materna-T1 / MEMORY | S2:S1 | 2625 / 0 | 0.004350791 | 0.01796254 | 0.003134705 | 0.004478755 | 0.0006253968 |
| Materna-T1 / THROUGHPUT | S2:S1 | 2625 / 0 | 0.008763173 | 0.01739738 | 0.005504190 | 0.009020914 | 0.0007809479 |
| Materna-T1 / CPU | M1:S2 | 2625 / 0 | 0.007379296 | 0.02731208 | 0.007943643 | 0.007596334 | 0.001928208 |
| Materna-T1 / DISK_WRITE | M1:S2 | 2625 / 0 | 0.1824300 | 0.04698611 | 0.007539554 | 0.1877956 | 0.001016936 |
| Materna-T1 / MEMORY | M1:S2 | 2625 / 0 | 0.02128837 | 0.01177660 | 0.004266995 | 0.02191450 | 0.0007982188 |
| Materna-T1 / THROUGHPUT | M1:S2 | 2625 / 0 | 0.009294162 | 0.01762721 | 0.008497602 | 0.009567520 | 0.002041405 |
| Materna-T2 / CPU | S2:S1 | 2625 / 0 | 0.002892526 | 0.01711167 | 0.007064936 | 0.002977601 | 0.001625842 |
| Materna-T2 / DISK_WRITE | S2:S1 | 2625 / 0 | 0.003596459 | 0.01981152 | 0.003926519 | 0.003702237 | 0.0007342640 |
| Materna-T2 / MEMORY | S2:S1 | 2625 / 0 | 0.003991430 | 0.01022999 | 0.001873409 | 0.004108825 | 0.0003858261 |
| Materna-T2 / THROUGHPUT | S2:S1 | 2625 / 0 | 0.004934370 | 0.01817659 | 0.006495041 | 0.005079499 | 0.001806011 |
| Materna-T2 / CPU | M1:S2 | 2625 / 0 | 0.005110295 | 0.01681518 | 0.006608172 | 0.005260598 | 0.001613242 |
| Materna-T2 / DISK_WRITE | M1:S2 | 2625 / 0 | 0.006910272 | 0.01461674 | 0.004594636 | 0.007113515 | 0.0006359055 |
| Materna-T2 / MEMORY | M1:S2 | 2625 / 0 | 0.02070297 | 0.008886374 | 0.002243146 | 0.02131188 | 0.0005135066 |
| Materna-T2 / THROUGHPUT | M1:S2 | 2625 / 0 | 0.008379186 | 0.01341709 | 0.004611639 | 0.008625633 | 0.0007745652 |
| Materna-T3 / CPU | S2:S1 | 2625 / 0 | 0.01024076 | 0.04035153 | 0.02002540 | 0.01054196 | 0.005246334 |
| Materna-T3 / DISK_WRITE | S2:S1 | 2625 / 0 | 0.007143336 | 0.02872072 | 0.01536639 | 0.007353434 | 0.001452395 |
| Materna-T3 / MEMORY | S2:S1 | 2625 / 0 | 0.003563132 | 0.007273732 | 0.001403219 | 0.003667930 | 0.0003272401 |
| Materna-T3 / THROUGHPUT | S2:S1 | 2625 / 0 | 0.008231886 | 0.01268108 | 0.005161607 | 0.008474000 | 0.0003883167 |
| Materna-T3 / CPU | M1:S2 | 2625 / 0 | 0.02837999 | 0.05292264 | 0.01919051 | 0.02921469 | 0.006432082 |
| Materna-T3 / DISK_WRITE | M1:S2 | 2625 / 0 | 0.2137408 | 0.03313098 | 0.01242330 | 0.2200273 | 0.003550924 |
| Materna-T3 / MEMORY | M1:S2 | 2625 / 0 | 0.009565836 | 0.01224170 | 0.003865460 | 0.009847184 | 0.0009618819 |
| Materna-T3 / THROUGHPUT | M1:S2 | 2625 / 0 | 0.01575263 | 0.03711454 | 0.01992020 | 0.01621594 | 0.008430712 |

All variances are squared natural-log-ratio units. Unrounded source MAEs were used; table display is seven significant digits. Each TimeTrack resource has 7×5×8×3=840 matched pairs/contrast; each external resource 35×5×5×3=2,625. The finite-only exclusions are entirely **Rnd throughput**: S2:S1 excludes 40 pairs (2 zero/zero, 2 zero-candidate/positive-reference, 36 positive-candidate/zero-reference); M1:S2 excludes 4 positive-candidate/zero-reference pairs. They remain part of v1's scientific results, not bad predictions to delete retrospectively. The preregistration must specify how a zero MAE is handled in the NEW log-ratio estimand. Arbitrary epsilon addition would change it. Ratio of pre-aggregated entity errors is a different possible endpoint, not a silent repair of the cell-log endpoint.

A finite-only variance need not represent the full ratio population, especially Rnd throughput. The inputs and explicit exclusions are sufficient to plan an alternative zero-safe aggregation and its sensitivity analysis prospectively; this audit does not choose one.

### Existing three-seed variability

Source /Users/fgtek002/TimeTrack/review_revision/stage18c1_evidence/seed_sensitivity.csv, independently retained in /Users/fgtek002/TimeTrack/review_revision/stage19g1_evidence/seed_sensitivity_48.csv. Gains below are the existing MacroMAE-gain seed range and population SD (percentage points), not SDs of log ratios. FLIP means strictly positive and negative gains across seeds 0/1/2; stable means no sign flip, not stable magnitude. Original counts: **9/24 S2:S1** and **4/24 M1:S2** summaries flip sign.

| Block/resource | Contrast | Seed gain range (pp) | Seed gain population SD (pp) | Status |
|---|---|---:|---:|---|
| TimeTrack / CPU | S2:S1 | 3.951265 | 1.858071 | stable |
| TimeTrack / THROUGHPUT | S2:S1 | 0.396068 | 0.166205 | stable |
| TimeTrack / MEMORY | S2:S1 | 3.219192 | 1.314718 | FLIP |
| TimeTrack / DISK_WRITE | S2:S1 | 0.592927 | 0.242064 | stable |
| TimeTrack / CPU | M1:S2 | 5.943973 | 2.606776 | FLIP |
| TimeTrack / THROUGHPUT | M1:S2 | 1.926331 | 0.787521 | FLIP |
| TimeTrack / MEMORY | M1:S2 | 7.514917 | 3.167826 | stable |
| TimeTrack / DISK_WRITE | M1:S2 | 0.758006 | 0.337220 | stable |
| fastStorage / CPU | S2:S1 | 3.817046 | 1.695864 | stable |
| fastStorage / THROUGHPUT | S2:S1 | 5.647867 | 2.305777 | FLIP |
| fastStorage / MEMORY | S2:S1 | 0.493829 | 0.208144 | stable |
| fastStorage / DISK_WRITE | S2:S1 | 0.519553 | 0.212387 | stable |
| fastStorage / CPU | M1:S2 | 1.365730 | 0.589078 | FLIP |
| fastStorage / THROUGHPUT | M1:S2 | 11.889389 | 5.575706 | stable |
| fastStorage / MEMORY | M1:S2 | 0.792856 | 0.356137 | stable |
| fastStorage / DISK_WRITE | M1:S2 | 1.248271 | 0.527688 | stable |
| Rnd / CPU | S2:S1 | 1.589945 | 0.720580 | stable |
| Rnd / THROUGHPUT | S2:S1 | 3.165385 | 1.316614 | stable |
| Rnd / MEMORY | S2:S1 | 0.193796 | 0.085450 | stable |
| Rnd / DISK_WRITE | S2:S1 | 6.016764 | 2.669691 | FLIP |
| Rnd / CPU | M1:S2 | 0.376858 | 0.166400 | stable |
| Rnd / THROUGHPUT | M1:S2 | 3.984353 | 1.817519 | stable |
| Rnd / MEMORY | M1:S2 | 1.276511 | 0.572355 | stable |
| Rnd / DISK_WRITE | M1:S2 | 1.372935 | 0.586974 | stable |
| Materna-T1 / CPU | S2:S1 | 2.613572 | 1.075685 | stable |
| Materna-T1 / THROUGHPUT | S2:S1 | 1.766752 | 0.742760 | FLIP |
| Materna-T1 / MEMORY | S2:S1 | 0.859228 | 0.379866 | FLIP |
| Materna-T1 / DISK_WRITE | S2:S1 | 2.705699 | 1.169675 | stable |
| Materna-T1 / CPU | M1:S2 | 3.946238 | 1.804100 | FLIP |
| Materna-T1 / THROUGHPUT | M1:S2 | 3.545632 | 1.447768 | stable |
| Materna-T1 / MEMORY | M1:S2 | 0.842248 | 0.378644 | stable |
| Materna-T1 / DISK_WRITE | M1:S2 | 1.977516 | 0.915693 | stable |
| Materna-T2 / CPU | S2:S1 | 1.294006 | 0.561639 | stable |
| Materna-T2 / THROUGHPUT | S2:S1 | 3.664080 | 1.594461 | FLIP |
| Materna-T2 / MEMORY | S2:S1 | 0.419213 | 0.195927 | stable |
| Materna-T2 / DISK_WRITE | S2:S1 | 1.910337 | 0.893664 | stable |
| Materna-T2 / CPU | M1:S2 | 0.497148 | 0.206174 | stable |
| Materna-T2 / THROUGHPUT | M1:S2 | 2.153882 | 0.881891 | stable |
| Materna-T2 / MEMORY | M1:S2 | 0.751677 | 0.310797 | stable |
| Materna-T2 / DISK_WRITE | M1:S2 | 0.550969 | 0.230179 | stable |
| Materna-T3 / CPU | S2:S1 | 11.653418 | 5.275965 | FLIP |
| Materna-T3 / THROUGHPUT | S2:S1 | 3.084723 | 1.312716 | FLIP |
| Materna-T3 / MEMORY | S2:S1 | 0.353999 | 0.160061 | stable |
| Materna-T3 / DISK_WRITE | S2:S1 | 3.504852 | 1.483812 | FLIP |
| Materna-T3 / CPU | M1:S2 | 14.546378 | 6.284930 | stable |
| Materna-T3 / THROUGHPUT | M1:S2 | 3.648878 | 1.494310 | stable |
| Materna-T3 / MEMORY | M1:S2 | 2.830011 | 1.233961 | stable |
| Materna-T3 / DISK_WRITE | M1:S2 | 33.189637 | 13.550350 | stable |

### Cohort/seed decisions still required before registration

1. **Primary question, contrast, aggregation and unit.** Choose log-ratio endpoint and whether entity-average MAEs are formed before logging; retain resource-specific native MacroMAE as an explicitly distinct endpoint if desired. Define zero handling, missing/failure treatment, paired supports, loss metric and primary versus exploratory resources/arms.
2. **Precision/effect criterion and inferential population.** Supply the smallest scientifically relevant effect or desired interval precision and analysis family; none is inferred from favourable v1 outcomes. Use entity clustering, with folds/leads/seeds nested rather than independent n. Deterministic ranked cohorts and TimeTrack's seven known machines constrain population claims.
3. **Final cohort size.** The executed v1 n is 7 TT and 35 in each external block/resource. Available scale-eligible pools are 596 FS, 272 Rnd and 74 jointly eligible Materna, not automatic new sample sizes. V1 provides no outcome variance for the unexecuted eligible entities. Prespecify any expansion by a fixed rank-based rule without outcome-driven replacement; repeat admissibility checks for any changed protocol. TimeTrack has no verified larger machine pool here.
4. **Seed count and IDs.** Five is the proposed budget, not a power result. Only three v1 seeds exist; W_z and sign variability cannot prove five is adequate or independent. Use v1 variance ranges for conservative sensitivity planning/simulation (in a later authorised planning step), account for entity×seed heterogeneity, and choose explicit IDs plus deterministic device/RNG policy. Do not present 5×35×5×5 cells as independent entities.
5. **Materna dependency.** Cluster a VM's three temporal blocks jointly if combining blocks, or report separate block conclusions with declared dependence/multiplicity. No six-block pooled raw-MAE statistic is warranted.
6. **No M0 variance available.** S2:S1/M1:S2 variance can bound planning scenarios, not estimate a future M0 contrast's effect/variance or guarantee PCGrad/GradNorm gains. Context-forced reruns may have different variance from original independently selected contexts.
7. **Mechanistic and efficiency sampling.** Choose checkpoint/batch schedules, same-task control, task-subset family, capacity comparator, training budget and measurement tolerances before new pilots. Define how outlier magnitude and typical-cell summaries coexist and whether diagnostics are confirmatory or exploratory.

Practical implication of the decomposition: in many resources within-entity variability exceeds between-entity variability; Materna M1 disk has large between-entity variance (T1 B≈0.18243; T3 B≈0.21374), consistent with its existing concentration diagnostics. Extra seeds cannot substitute for extra entities or eliminate temporal/task heterogeneity. No new effect threshold, power result, significance test or formal random-effects model has been fitted in this audit.

## 7. Minimal implementation map for the next stages (PROPOSED, not created)

Use a new strengthening namespace, with immutable references to v1; do not patch historical code.

1. **Protocol/config/identity layer:** arbitrary declared seeds, task sets, formulation/input-scope, capacity target, loss/optimizer, common-L rule, checkpoint/diagnostic settings, environment and source hashes; identity must distinguish diagnostic, pilot, inner and final records. Fail closed on unresolved attempts and duplicate identities. Explicit launch gate after protocol approval.
2. **Data adapters:** read frozen TT/external support and scaler partitions; match origin IDs/counts across all formulations. Unit checks for segment boundaries, target-time purge, training-only scaler row unions, projection, zero IQR and timestamp/string VM identities (including leading-zero IDs such as Materna 08/04).
3. **Model registry:** horizon-parameterised S1/S2/M1 plus M0; arbitrary task subset/routing and exact parameter-count assertions. Architecture-only tests before any scientific fit. Preserve v1 model classes unchanged.
4. **Training/checkpoint engine:** task-vector losses, aggregate baseline, PCGrad/GradNorm as explicit variants; task-best inner checkpoint bank; seed-specific epoch choices and clean outer refits. Serializable optimizer/RNG state if resumption needs exact stochastic continuity. Never import frozen run main functions.
5. **Gradient diagnostics:** detached copy/read-only evaluation of a declared checkpoint, train-only fixed batch manifest, pre-clipping task gradients and same-task sampling controls. Log parameter names, norms, inner products, zero gradients, checkpoint epoch and data hashes; verify no optimizer/RNG contamination.
6. **Pilot adapters:** DLinear/PatchTST external short-L/output/scaler wrappers, a validated new iTransformer implementation, and own/all-input LightGBM nested-grid wrapper. No downloading or implementing these in Stage 1.
7. **Measurement harness:** isolated successful fit accounting, wall-clock separately, train/validation/diagnostic components, warmed inference distributions, batch/device/thread context, peak memory and complement footprint. Existing one-shot timings are historical workload references only.
8. **Independent validators:** exact grid counts, hash-bound supports/scalers, no leakage, finite predictions/primary metrics, correct native inversion, duplicate/failure handling, and immutable original artifacts. Synthetic routing/gradient mathematics and checkpoint selection tests before data pilots.
9. **Planning analysis:** implement the prespecified hierarchical/paired analysis, zero-safe endpoint and cohort/seed sensitivity calculation from existing inputs; classify what can be confirmed versus exploratory.
10. **Freeze and gated pilot:** once the above protocol decisions are approved, freeze implementation/config/test evidence before any new scientific execution. No full rerun or broader search should precede that gate.

### Specific implementation blockers (not blockers to this audit pass)

- No M0 or multi-seed common-context runner; current constants/shape checks reject extra seeds/tasks.
- No saved original per-epoch task-best state bank, gradient traces, clipping traces, same-task noise controls or optimizer trajectory; retrospective mechanism identification is not available.
- No iTransformer, PCGrad or GradNorm implementation located; subset routing/per-task selection absent.
- PatchTST cannot accept external L=4 with its current patch8; DLinear/PatchTST old CPU preprocessing and outputs do not match v1 multi-resource protocol.
- Capacity comparison target, common-context selection rule, primary estimand/zero-MAE policy, cohort/seed precision criterion, multiplicity and diagnostic/measurement budgets remain required decisions.
- Full artifact-level audits depend on locally preserved archives, not Git alone. Sample hashes and compact seals passed here, but a complete pre-execution restoration/preservation audit must be a separate future gate.
- Current legacy package metadata is known, but no new clean pinned environment or runtime compatibility/determinism test was installed or executed.

## 8. Input fingerprints and audit scope

All six native metrics below match the current frozen tag byte-for-byte. Exact current SHA-256:

| Existing input | SHA-256 |
|---|---|
| /Users/fgtek002/TimeTrack/multiresource/04_lstm_factorial/outputs/scientific/metrics.parquet | `3787d0026ee9cefcec64124e8686abb79d9b4dfc9554fd2312b808380bfff8b4` |
| /Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/outputs/scientific_v2/fastStorage/metrics.parquet | `3edbbe0d74a76b4a99ee110ef9f42919700cf4b88273b568924816e828a05309` |
| /Users/fgtek002/TimeTrack/independent_validation/05_bitbrains_factorial/outputs/scientific_v2/Rnd/metrics.parquet | `4072332fde01457e7d1fc89086d840a730844d8a25366c0abaaf6d69c472de4c` |
| /Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/outputs/scientific_v1/Materna-T1/metrics.parquet | `f4ed6252ce72c3bb0b05b78cd471331c86ac9701a72756968207088c7f36d370` |
| /Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/outputs/scientific_v1/Materna-T2/metrics.parquet | `24b670e03c152018cccf9fc23a6d2b7fe1d9a693783d53b2290c167144b4720d` |
| /Users/fgtek002/TimeTrack/independent_validation/06_materna_replication/outputs/scientific_v1/Materna-T3/metrics.parquet | `50767c5f371a6dc5c528b6c5bd777a7660faa8176d7c1f8d2a7a443f18e8b843` |

Post-hoc result fingerprints (each 24 rows):

| Existing endpoint | SHA-256 |
|---|---|
| /Users/fgtek002/TimeTrack/review_revision/experiments/s2_common_context/posthoc_results.csv | `83746b1d7639d03877a3993edcf8fb7a6282f3cb0cec6f672799d64826c03693` |
| /Users/fgtek002/TimeTrack/review_revision/experiments/m1_capacity_matched/posthoc_results.csv | `c7122b25f76f7e8d44abfeb5068d6a29d7dd38e6641346771f845205ea47a5b5` |
| /Users/fgtek002/TimeTrack/review_revision/experiments/ar_arx_baseline/posthoc_results.csv | `a8fa3afa5084d0be27d560613f084cebc2dd794370ed8290646f80324f66f665` |

The variance calculation reads only the six existing metrics tables; pivots by resource/entity/fold/lead/seed; validates uniqueness, nonnegative finite MAEs and equal matched n; forms the two candidate/reference pairs; excludes only nonpositive MAE pairs for finite log moments with explicit counts; calculates the formulas in §6. It uses pandas groupby means/counts and NumPy arithmetic; no scientific module, runner, model constructor or checkpoint loader is invoked. The 48 seed-range/SD rows are copied from the existing C1 endpoint, not newly fitted.

Audit verification is deliberately bounded: current refs/diff, source inspection, actual file/row counts, active compact provenance hashes, tagged metric equality, and 18 model+prediction sample pairs. Existing terminal six-block validations are identified as historical evidence rather than falsely reported as rerun today. No claim is made that every ignored archive byte or external service state was freshly verified.

The only new persistent file is /Users/fgtek002/TimeTrack/review_revision/fgcs_strengthening/stage01_repository_audit.md. All computations ran from inline commands with bytecode writes disabled. No new script, CSV, environment, report inventory or data file was created. No original scientific artifact, manuscript, supplement or submission package was written. No dependency installation/download, training/inference, Git staging, commit, tag or push occurred.

**Outstanding decisions are explicit and the required baseline inputs are available; the repository is understood well enough to finalise the prespecified plan. Execution readiness is not claimed.**

STAGE01_PASS

