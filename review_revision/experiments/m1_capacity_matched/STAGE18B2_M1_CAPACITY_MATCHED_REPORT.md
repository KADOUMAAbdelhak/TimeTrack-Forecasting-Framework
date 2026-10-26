# STAGE 18B2 CAPACITY-MATCHED M1 SENSITIVITY REPORT

POST-HOC SENSITIVITY CONTROL

Status: COMPLETE — all six blocks, independent result/identity audits and full protected-tree preservation PASS. The result table and its interpretation have been reviewed. This is a post-hoc control, not a replacement for frozen M1 or a prospective primary result.

## Execution and provenance

Repository: `/Users/fgtek002/TimeTrack`; branch: `paper/jss-review-revision`.
Manuscript/source-code parent: `f6936cd111d911e40ec2725a18fdfc53768d9ccf`.
Scientific parent: `fee20c316040c57b69ba12a193530c955b539771`.

New output root: `review_revision/experiments/m1_capacity_matched/`.
Files created: `control_config.json`, `run_capacity_control.py`, `test_capacity_control.py`, `analyse_capacity_control.py`, `RUN_NOTES.md`, this report, and the isolated `plans/`, `provenance/`, `attempts/`, `selections/`, `completions/`, `models/`, `predictions/`, `metrics/`, `progress/` and `validation/` records. Final tabular outputs are `posthoc_results.csv` and `posthoc_metric_rows.parquet`; the full output hash inventory is `output_sha256_inventory.json`.

The uncommitted adapter is identified explicitly by SHA-256 `afe50555e5f794d651d4b42b0c89116436df72b1c89f275b52590b400a7c3770`; configuration SHA-256 is `200f8ba6f3b1f9a688812ee589e85c6b9cfc5ce2bdc5f81ad79c860038c1538f`. Source/configuration/plan hashes are sealed in `provenance/experiment.json`; this experiment is not represented as code contained in the parent commit. Stage18B1R outputs and its predecessor recovery snapshot are protected, read-only comparators.

| Evidence block | Inner fits | Final refits | Metric rows | Audit |
|---|---:|---:|---:|---|
| TimeTrack | 315 | 105 | 3,360 | PASS |
| fastStorage | 1,575 | 525 | 10,500 | PASS |
| Rnd | 1,575 | 525 | 10,500 | PASS |
| Materna T1 | 1,575 | 525 | 10,500 | PASS |
| Materna T2 | 1,575 | 525 | 10,500 | PASS |
| Materna T3 | 1,575 | 525 | 10,500 | PASS |
| Total, technical accounting only | 8,190 | 2,730 | 55,860 | PASS |

All 10,920 fits are fresh H129 fits; frozen-fit reuse=0. Valid inner completions=8,190; valid final completions=2,730; context selections=910; seed-specific selected epochs=2,730. Model checkpoints=10,920 (8,190 inner plus 2,730 final); final prediction files=2,730. Failed fits=0; unresolved attempts=0; duplicate scientific identities=0. Each final completion records exactly one test evaluation; inner completions record none. Forty-eight non-training safety checks passed before execution. No training, inference or test evaluation was rerun during the final audit.

Frozen cohorts are preserved: seven TimeTrack machines and 35 VMs in each external evidence block, with the original five purged folds and three seeds. Materna traces remain dependent temporal evidence, not independent datasets. The selected context and epoch come exclusively from the new H129 inner fits. All support/scaler identities and exact-L reconstruction checks passed. Final predictions, primary MAEs and model weights passed finite-value checks; model and prediction hashes were rechecked independently. Evidence: `validation/full_audit_*.json`, `validation/final_independent_audit.json` and `provenance/preservation_after.json`.

## Design and capacity

H64→H129 is the only intended design change. The original M1 inner context/epoch procedure was rerun, followed by one fixed-epoch final refit and one test evaluation. 8,190 inner fits and 2,730 final fits; no frozen fit reuse. External: H129=206,420 versus aggregate S2=206,100 (+0.155264%); TimeTrack: H129=207,980 versus aggregate S2=206,880 (+0.531709%).

For two unidirectional, biased LSTM layers, four linear output heads, input channels D and total head outputs K, the exact count is `P(D,H,K) = 12H² + (4D + 16 + K)H + K`. Here D=4; K=20 externally (four resources × five horizons) or K=32 for TimeTrack (four × eight). The instantiated H129 models match the counts above. Aggregate S2 retains four separate H64 networks: 4×51,525=206,100 externally; 4×51,720=206,880 for TimeTrack. This matches total parameter count approximately, not each target's independently available capacity.

All-resource inputs, two layers, dropout=0.1, original context grids (32/64/128 for TimeTrack; 4/9/18 externally), horizons, seeds [0,1,2], training-only transforms/scalers, Adam learning rate=0.001, batch size=256, max epochs=50, patience=7 and gradient clipping=1 are unchanged. Best epochs minimise the original scaled-space joint validation MSE; context selection uses the original seed/resource/horizon-mean normalised MAE and shorter-context tie rule. Each selected seed is refitted from scratch for its own new inner best epoch.

## Results

POST-HOC SENSITIVITY RESULT

| Block / resource | S2 MAE | Common-S2 MAE | H64 MAE | H129 MAE | H64:S2 % | H129:S2 % | H129:H64 % | H129:common-S2 % | Gap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| TimeTrack / CPU | 1.8682962 | 1.84467005 | 1.85952338 | 1.9230185 | 0.469562155 | -2.92899493 | -3.41459071 | -4.24728768 | GAP_REVERSED |
| TimeTrack / THROUGHPUT | 29.8704216 | 29.9600003 | 30.1213583 | 29.9169105 | -0.840084191 | -0.155635222 | 0.678746922 | 0.143824371 | GAP_REDUCED |
| TimeTrack / MEMORY | 315389449 | 317228559 | 373663597 | 373688413 | -18.4768858 | -18.4847542 | -0.00664134767 | -17.797847 | GAP_WIDENED |
| TimeTrack / DISK_WRITE | 3147063.35 | 3154439.57 | 3172100.5 | 3165977.04 | -0.795571899 | -0.600994949 | 0.193041169 | -0.365753463 | GAP_REDUCED |
| fastStorage / CPU | 1.26511559 | 1.26907405 | 1.26454569 | 1.22542195 | 0.0450473868 | 3.13755089 | 3.09389722 | 3.4396811 | GAP_WIDENED |
| fastStorage / THROUGHPUT | 151.885158 | 160.45416 | 193.037153 | 203.266375 | -27.0941515 | -33.8289914 | -5.29909501 | -26.681898 | GAP_WIDENED |
| fastStorage / MEMORY | 79557.8923 | 79889.5268 | 83430.0237 | 82889.444 | -4.86706123 | -4.18758164 | 0.647943765 | -3.75508202 | GAP_REDUCED |
| fastStorage / DISK_WRITE | 12.1967762 | 12.4747054 | 12.6934446 | 12.6910685 | -4.07212856 | -4.05264746 | 0.0187188427 | -1.73441482 | GAP_REDUCED |
| Rnd / CPU | 1.55693618 | 1.55944909 | 1.81398543 | 1.83043476 | -16.5099408 | -17.5664603 | -0.906806258 | -17.3770129 | GAP_WIDENED |
| Rnd / THROUGHPUT | 302.38003 | 307.084119 | 345.677786 | 349.439572 | -14.3189866 | -15.5630456 | -1.08823485 | -13.7927851 | GAP_WIDENED |
| Rnd / MEMORY | 164188.214 | 164535.998 | 178826.804 | 177428.751 | -8.91573725 | -8.06424354 | 0.781791255 | -7.835825 | GAP_REDUCED |
| Rnd / DISK_WRITE | 100.714787 | 102.495494 | 106.305699 | 107.618051 | -5.55123314 | -6.85427129 | -1.23450774 | -4.99783607 | GAP_WIDENED |
| Materna-T1 / CPU | 0.97882995 | 0.964300026 | 0.970189829 | 0.947626335 | 0.882698801 | 3.18784838 | 2.32567832 | 1.72909785 | GAP_WIDENED |
| Materna-T1 / THROUGHPUT | 219.82353 | 220.075943 | 235.889014 | 230.191001 | -7.3083551 | -4.71627024 | 2.41554803 | -4.59616733 | GAP_REDUCED |
| Materna-T1 / MEMORY | 232815.618 | 239306.362 | 263590.024 | 261492.839 | -13.21836 | -12.3175678 | 0.795623719 | -9.27116074 | GAP_REDUCED |
| Materna-T1 / DISK_WRITE | 253.944097 | 252.906062 | 323.671421 | 316.472712 | -27.4577457 | -24.6229844 | 2.22407926 | -25.1344903 | GAP_REDUCED |
| Materna-T2 / CPU | 0.887478754 | 0.897817973 | 0.910236932 | 0.885951932 | -2.56436309 | 0.172040498 | 2.66798672 | 1.32165338 | GAP_REVERSED |
| Materna-T2 / THROUGHPUT | 285.730795 | 289.537514 | 310.568691 | 296.167765 | -8.69276116 | -3.65272849 | 4.63695339 | -2.28994543 | GAP_REDUCED |
| Materna-T2 / MEMORY | 242306.512 | 246249.943 | 264760.629 | 258586.879 | -9.26682326 | -6.71891432 | 2.33182302 | -5.00992449 | GAP_REDUCED |
| Materna-T2 / DISK_WRITE | 144.49568 | 144.437272 | 155.894226 | 154.903783 | -7.88850311 | -7.20305468 | 0.635330375 | -7.24640597 | GAP_REDUCED |
| Materna-T3 / CPU | 1.15125995 | 1.15870567 | 1.24450067 | 1.24574127 | -8.09901546 | -8.20677545 | -0.0996863743 | -7.51145027 | GAP_WIDENED |
| Materna-T3 / THROUGHPUT | 343.899709 | 345.427121 | 371.116889 | 363.932275 | -7.91427836 | -5.82511874 | 1.93594365 | -5.35718044 | GAP_REDUCED |
| Materna-T3 / MEMORY | 269877.033 | 272151.783 | 293363.332 | 287508.381 | -8.70259284 | -6.5331046 | 1.99580174 | -5.64265941 | GAP_REDUCED |
| Materna-T3 / DISK_WRITE | 73.1942472 | 73.8961942 | 125.378155 | 120.040575 | -71.2950946 | -64.0027458 | 4.2571848 | -62.4448682 | GAP_REDUCED |

Every MAE is the native-unit MacroMAE for that block/resource, using the frozen equal-seed, equal-entity/fold and equal-horizon aggregation. Do not compare absolute MAEs across resource units or pool blocks. Gains use `100 × (reference MacroMAE − candidate MacroMAE) / reference MacroMAE`. Positive H64:S2 gains favour H64; positive gains in the three H129 columns favour H129. No block pooling, new endpoint, significance test or bootstrap was introduced.

Gap labels describe numerical direction, not formal classes or threshold-based tests. `GAP_REVERSED` means the signed advantage changes side; the direction is stated below. `GAP_REDUCED` means the absolute gap shrinks without changing side; `GAP_WIDENED` means its magnitude grows, which is an increased advantage when both gains are positive. No cell has an exactly zero H129:S2 gap, so none is labelled removed. A tiny numerical change need not be substantively important.

## All 24 gap directions

- TimeTrack CPU: +0.469562% → -2.928995%; GAP_REVERSED from H64 advantage to H129 disadvantage.
- TimeTrack THROUGHPUT: -0.840084% → -0.155635%; GAP_REDUCED.
- TimeTrack MEMORY: -18.476886% → -18.484754%; GAP_WIDENED.
- TimeTrack DISK_WRITE: -0.795572% → -0.600995%; GAP_REDUCED.
- fastStorage CPU: +0.045047% → +3.137551%; GAP_WIDENED in M1's favour (increased advantage, not increased degradation).
- fastStorage THROUGHPUT: -27.094152% → -33.828991%; GAP_WIDENED.
- fastStorage MEMORY: -4.867061% → -4.187582%; GAP_REDUCED.
- fastStorage DISK_WRITE: -4.072129% → -4.052647%; GAP_REDUCED.
- Rnd CPU: -16.509941% → -17.566460%; GAP_WIDENED.
- Rnd THROUGHPUT: -14.318987% → -15.563046%; GAP_WIDENED.
- Rnd MEMORY: -8.915737% → -8.064244%; GAP_REDUCED.
- Rnd DISK_WRITE: -5.551233% → -6.854271%; GAP_WIDENED.
- Materna-T1 CPU: +0.882699% → +3.187848%; GAP_WIDENED in M1's favour (increased advantage, not increased degradation).
- Materna-T1 THROUGHPUT: -7.308355% → -4.716270%; GAP_REDUCED.
- Materna-T1 MEMORY: -13.218360% → -12.317568%; GAP_REDUCED.
- Materna-T1 DISK_WRITE: -27.457746% → -24.622984%; GAP_REDUCED.
- Materna-T2 CPU: -2.564363% → +0.172040%; GAP_REVERSED from H64 disadvantage to a small H129 advantage.
- Materna-T2 THROUGHPUT: -8.692761% → -3.652728%; GAP_REDUCED.
- Materna-T2 MEMORY: -9.266823% → -6.718914%; GAP_REDUCED.
- Materna-T2 DISK_WRITE: -7.888503% → -7.203055%; GAP_REDUCED.
- Materna-T3 CPU: -8.099015% → -8.206775%; GAP_WIDENED.
- Materna-T3 THROUGHPUT: -7.914278% → -5.825119%; GAP_REDUCED.
- Materna-T3 MEMORY: -8.702593% → -6.533105%; GAP_REDUCED.
- Materna-T3 DISK_WRITE: -71.295095% → -64.002746%; GAP_REDUCED.

## Five priority cases

- TimeTrack MEMORY: H64:S2 -18.476886%; H129:S2 -18.484754%; H129:H64 -0.006641%; H129:common-S2 -17.797847%. GAP_WIDENED.
- fastStorage THROUGHPUT: H64:S2 -27.094152%; H129:S2 -33.828991%; H129:H64 -5.299095%; H129:common-S2 -26.681898%. GAP_WIDENED.
- Rnd CPU: H64:S2 -16.509941%; H129:S2 -17.566460%; H129:H64 -0.906806%; H129:common-S2 -17.377013%. GAP_WIDENED.
- Materna-T1 DISK_WRITE: H64:S2 -27.457746%; H129:S2 -24.622984%; H129:H64 +2.224079%; H129:common-S2 -25.134490%. GAP_REDUCED.
- Materna-T3 DISK_WRITE: H64:S2 -71.295095%; H129:S2 -64.002746%; H129:H64 +4.257185%; H129:common-S2 -62.444868%. GAP_REDUCED.

TimeTrack memory is essentially unchanged in magnitude: the disadvantage grows by only 0.007868 percentage points, so the literal widening label must not be read as a material deterioration. Capacity matching does not resolve this case. fastStorage throughput instead deteriorates: its disadvantage grows by 6.734840 percentage points. Rnd CPU also deteriorates, by 1.056519 percentage points. Neither case is explained away by matching aggregate capacity.

Materna T1 disk write improves from H64, but its S2-relative disadvantage only narrows from 27.457746% to 24.622984% (2.834761 percentage points); it remains adverse versus common-S2 as well. Materna T3 disk write also improves from H64, narrowing the S2-relative disadvantage from 71.295095% to 64.002746% (7.292349 percentage points), but the large residual disadvantage remains. Capacity matching provides partial mitigation in these two cells, not removal or reversal of their degradation. Percentage-point differences here are derived directly from the authorised gain comparisons; they are not additive gains or causal effect estimates.

## Six-block resource checks

- THROUGHPUT: H129 remains adverse versus original S2 in 6/6 blocks; versus common-S2 in 5/6 blocks.
- MEMORY: H129 remains adverse versus original S2 in 6/6 blocks; versus common-S2 in 6/6 blocks.
- DISK_WRITE: H129 remains adverse versus original S2 in 6/6 blocks; versus common-S2 in 6/6 blocks.

The common-S2 throughput exception is TimeTrack: H129 gains +0.143824% against common-S2, while remaining -0.155635% against original S2. Thus the all-six adverse statement holds for throughput, memory and disk write against original S2; it holds only for memory and disk write against common-S2.

## Central answer and unexpected findings

Aggregate-capacity matching does not remove the original M1 degradation pattern and is not a sufficient explanation of it. H129 still underperforms original S2 for throughput, memory and disk write in every evidence block. Several gaps are reduced, including the two extreme Materna disk-write cases, but none of those resource/block disadvantages is removed or reversed. TimeTrack memory remains practically unchanged, whereas fastStorage throughput and Rnd CPU become worse. These outcomes support a limited conclusion: inadequate aggregate parameter count alone does not explain away the observed shared-LSTM disadvantage; they do not establish that capacity plays no role.

CPU remains environment-dependent: Materna T2 changes from a disadvantage to a small +0.172040% advantage, while TimeTrack changes from a small advantage to a -2.928995% disadvantage. The existing fastStorage and Materna T1 CPU advantages increase. The small positive TimeTrack throughput comparison against common-S2 is another exception that prevents an all-six adverse claim for that comparator. These directional exceptions and the deterioration of fastStorage throughput show that increasing capacity is not uniformly beneficial. No statistical reliability claim is attached to the small sign reversals.

## Limitations and preservation

Aggregate parameter matching does not equalise optimisation geometry, per-target capacity allocation, model count or representation structure. Optimisation settings remain fixed; there was no capacity retuning. H129 uses its own newly selected context/epoch; those changes are downstream consequences of the unchanged selection policy, not separately isolated interventions. The Stage18B1R common-S2 comparator was aligned to H64's contexts and may not match H129's contexts, so H129 versus common-S2 is not a strictly context-matched comparison. The two sensitivity controls were not crossed into a new factorial experiment. Conclusions are post-hoc and limited to the original eligible populations, resources, three seeds and conventional shared-LSTM implementation. No additional seeds, uncertainty intervals or significance tests were added; small differences are descriptive. Runtime is not a clean hardware comparison. No architecture-wide or causal-isolation claim follows.

Full protected-tree SHA256 and refs verified over 246,779 files, with zero modifications. Original frozen scientific bytes also match the original pre-18B1 baseline. Manuscript modifications=0; frozen artifacts modified=0; original results modified=0; Stage18B1R modified=0; `paper/jss`, `main` and the scientific tag unchanged. Only the new review-revision namespace was written. Commit=NO; push=NO.

The final human review clarified the sign convention, the two pre-existing positive CPU advantages and the negligible TimeTrack-memory widening; it did not change computed results, sealed code, configuration or scientific artefacts. The independent final audit reproduced the 24 H129 MacroMAEs and all three authorised gain comparisons from persisted completion metrics, and checked all output model/prediction hashes. The output SHA256 inventory is refreshed after report finalisation. Automatic follow-up is paused after terminal completion.

STAGE_18B2_PASS
