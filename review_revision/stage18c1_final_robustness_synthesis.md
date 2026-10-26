# STAGE 18C1 — FINAL ROBUSTNESS AND EVIDENCE SYNTHESIS

Date: 23 October 2026 (Europe/Helsinki). Branch: `paper/jss-review-revision`. HEAD: `f6936cd111d911e40ec2725a18fdfc53768d9ccf`.

**STAGE_18C1_PASS. Further experiments scientifically required before a bounded JSS submission: NO.** No current scientific implementation defect is demonstrated. This is a read-only synthesis of existing results, not a new experiment. Training calls=0; model-inference calls=0. The only recomputation on saved scaled predictions is deterministic inverse-transform/projection verification, not new model inference.

All newly derived medians, log ratios, win rates, seed summaries and error-concentration summaries are **POST-HOC DIAGNOSTICS, NOT FROZEN PRIMARY RESULTS**. Frozen MacroMAE gains and post-hoc control endpoints are retained unchanged. No significance test, bootstrap, extra seed, cross-block pooled performance statistic, retuning or manuscript edit was performed.

## 1. Authority, completeness and provenance

Source precedence: frozen native-unit outputs and executable/hash-sealed protocol; completed post-hoc results and recovery evidence; Stage 18A1 diagnostics; interpretation. Historical STOP/failure records in recovered controls are retained evidence, not current unresolved failures.

| Experiment | Verified terminal status | Valid completions | Authoritative numerical files |
|---|---|---|---|
| s2_common_context | STAGE_18B1R_PASS | 10920 final: 5208 exact reuses + 5712 new fits | [24-row results](/Users/fgtek002/TimeTrack/review_revision/experiments/s2_common_context/posthoc_results.csv); [per-cell metrics](/Users/fgtek002/TimeTrack/review_revision/experiments/s2_common_context/posthoc_metric_rows.parquet) |
| m1_capacity_matched | STAGE_18B2_PASS | 8190 inner + 2730 final | [24-row results](/Users/fgtek002/TimeTrack/review_revision/experiments/m1_capacity_matched/posthoc_results.csv); [per-cell metrics](/Users/fgtek002/TimeTrack/review_revision/experiments/m1_capacity_matched/posthoc_metric_rows.parquet) |
| ar_arx_baseline | STAGE_18B3R_PASS | 36400 inner + 7280 final; 35 historical failed finals resolved | [24-row results](/Users/fgtek002/TimeTrack/review_revision/experiments/ar_arx_baseline/posthoc_results.csv); [per-cell metrics](/Users/fgtek002/TimeTrack/review_revision/experiments/ar_arx_baseline/posthoc_metric_rows.parquet) |

All three final report hashes, active successor/source/config/plan seals, result coverage and six-block audit statuses were checked. The full before/after inventory additionally verifies every protected scientific/post-hoc artifact, not merely summaries. Stage 18B1R's 4 recovery completions and Stage 18B3R's 35 same-identity recovery completions match their recorded hashes. There are no unresolved scientific identities. AR/ARX's 35 historical failed evaluations are not erased: its original actual-fit count is 43715 versus 43680 completed scientific units; none is repeated by this audit.

Frozen metric roots are `multiresource/04_lstm_factorial/outputs/scientific` (TimeTrack), `independent_validation/05_bitbrains_factorial/outputs/scientific_v2/{fastStorage,Rnd}` and `independent_validation/06_materna_replication/outputs/scientific_v1/Materna-T{1,2,3}`. Primary gains come directly from TimeTrack `comparisons/{s2_vs_s1,m1_vs_s2}.csv` OVERALL rows and external `comparisons/secondary_aggregation_diagnostics.csv` overall rows. Per-seed values come from each block's `metrics.parquet`. Matched inputs were checked against TimeTrack's existing `*_cells.csv` and external `analysis/matched_vm_fold_cells.csv`. [Stage18A1 diagnostic audit](/Users/fgtek002/TimeTrack/review_revision/stage18a1_diagnostic_audit.md) supplies the earlier mechanism/objective/persistence and Materna-VM concentration audits.

Exact source paths/SHA256s and checks are in [posthoc_provenance.json](/Users/fgtek002/TimeTrack/review_revision/stage18c1_evidence/posthoc_provenance.json). Input membership/content and refs are recorded in the preservation manifests. Support evidence and calculation code are in `review_revision/stage18c1_evidence/`; no source experiment was executed.

## 2. Robust matched-cell summaries — original comparisons

The main matched unit is entity×outer-fold×forecast-lead, after averaging the 3 existing per-seed MAEs separately for candidate and reference (not averaging predictions). This matches the external frozen seed-mean cell construction: 280 cells/resource in TimeTrack and 875 elsewhere. Candidate/reference is S2/S1 or M1/S2. Median log ratio is natural-log `median[ln(candidate_MAE/reference_MAE)]`; the ratio median is calculated separately. Negative median log, ratio<1 and win rate>50% favour the candidate. Frozen gain is `100*(MacroMAE_reference−MacroMAE_candidate)/MacroMAE_reference`, a different estimand, and is not replaced by these summaries.

Win rates count all matched cells; exact equality is a tie. No epsilon or ad-hoc zero replacement is used. In the main seed-mean panel all ties=0 and all 0/0 counts=0. Rnd S2:S1 throughput has 3 positive-candidate/zero-reference cells: their ratios/logs are +infinity and retained in the median calculation; the reported medians remain finite.

### S2_vs_S1

| Block/resource | Frozen gain % | Median ln ratio | Median ratio | Win % | Ties |
|---|---:|---:|---:|---:|---:|
| TimeTrack / CPU | -3.313049 | +0.001171 | 1.001171 | 48.571 | 0 |
| TimeTrack / THROUGHPUT | -0.242752 | -0.000426 | 0.999574 | 52.857 | 0 |
| TimeTrack / MEMORY | +0.859389 | +0.009885 | 1.009934 | 44.643 | 0 |
| TimeTrack / DISK_WRITE | -0.492319 | +0.000262 | 1.000262 | 48.929 | 0 |
| fastStorage / CPU | -3.198519 | -0.004041 | 0.995967 | 52.914 | 0 |
| fastStorage / THROUGHPUT | +0.012731 | +0.000291 | 1.000291 | 49.029 | 0 |
| fastStorage / MEMORY | +2.449985 | -0.015426 | 0.984692 | 69.829 | 0 |
| fastStorage / DISK_WRITE | +2.689207 | -0.000292 | 0.999709 | 50.400 | 0 |
| Rnd / CPU | +1.412867 | -0.000356 | 0.999644 | 50.514 | 0 |
| Rnd / THROUGHPUT | -7.214491 | +0.003455 | 1.003461 | 44.343 | 0 |
| Rnd / MEMORY | +1.673083 | -0.018120 | 0.982043 | 64.571 | 0 |
| Rnd / DISK_WRITE | +0.160400 | +0.007995 | 1.008027 | 38.171 | 0 |
| Materna T1 / CPU | -4.317958 | -0.006048 | 0.993970 | 54.743 | 0 |
| Materna T1 / THROUGHPUT | +0.986935 | -0.002868 | 0.997136 | 54.400 | 0 |
| Materna T1 / MEMORY | -0.019692 | -0.025151 | 0.975163 | 69.486 | 0 |
| Materna T1 / DISK_WRITE | -6.699662 | -0.003496 | 0.996510 | 54.629 | 0 |
| Materna T2 / CPU | +4.207624 | -0.031741 | 0.968757 | 66.629 | 0 |
| Materna T2 / THROUGHPUT | +0.294315 | -0.006460 | 0.993561 | 58.514 | 0 |
| Materna T2 / MEMORY | +3.948171 | -0.018464 | 0.981706 | 66.171 | 0 |
| Materna T2 / DISK_WRITE | -1.120181 | -0.003292 | 0.996713 | 55.543 | 0 |
| Materna T3 / CPU | -2.787548 | +0.000555 | 1.000555 | 49.600 | 0 |
| Materna T3 / THROUGHPUT | +0.044766 | +0.001173 | 1.001174 | 46.857 | 0 |
| Materna T3 / MEMORY | +3.089002 | -0.014488 | 0.985616 | 65.029 | 0 |
| Materna T3 / DISK_WRITE | +1.907168 | -0.002579 | 0.997424 | 53.371 | 0 |

### M1_vs_S2

| Block/resource | Frozen gain % | Median ln ratio | Median ratio | Win % | Ties |
|---|---:|---:|---:|---:|---:|
| TimeTrack / CPU | +0.469562 | +0.027756 | 1.028145 | 35.357 | 0 |
| TimeTrack / THROUGHPUT | -0.840084 | +0.002155 | 1.002157 | 40.357 | 0 |
| TimeTrack / MEMORY | -18.476886 | +0.175744 | 1.192135 | 14.643 | 0 |
| TimeTrack / DISK_WRITE | -0.795572 | +0.002097 | 1.002100 | 34.643 | 0 |
| fastStorage / CPU | +0.045047 | +0.025958 | 1.026297 | 32.457 | 0 |
| fastStorage / THROUGHPUT | -27.094152 | +0.054315 | 1.055817 | 25.829 | 0 |
| fastStorage / MEMORY | -4.867061 | +0.012574 | 1.012653 | 24.000 | 0 |
| fastStorage / DISK_WRITE | -4.072129 | +0.027144 | 1.027516 | 28.914 | 0 |
| Rnd / CPU | -16.509941 | +0.047917 | 1.049083 | 24.343 | 0 |
| Rnd / THROUGHPUT | -14.318987 | +0.015100 | 1.015214 | 32.343 | 0 |
| Rnd / MEMORY | -8.915737 | +0.024844 | 1.025155 | 23.771 | 0 |
| Rnd / DISK_WRITE | -5.551233 | +0.049355 | 1.050593 | 18.286 | 0 |
| Materna T1 / CPU | +0.882699 | +0.010361 | 1.010415 | 43.543 | 0 |
| Materna T1 / THROUGHPUT | -7.308355 | +0.021887 | 1.022128 | 22.171 | 0 |
| Materna T1 / MEMORY | -13.218360 | +0.032718 | 1.033259 | 25.257 | 0 |
| Materna T1 / DISK_WRITE | -27.457746 | +0.024268 | 1.024565 | 22.514 | 0 |
| Materna T2 / CPU | -2.564363 | +0.020490 | 1.020701 | 38.057 | 0 |
| Materna T2 / THROUGHPUT | -8.692761 | +0.015243 | 1.015360 | 25.943 | 0 |
| Materna T2 / MEMORY | -9.266823 | +0.032717 | 1.033259 | 25.829 | 0 |
| Materna T2 / DISK_WRITE | -7.888503 | +0.014557 | 1.014664 | 32.229 | 0 |
| Materna T3 / CPU | -8.099015 | +0.020654 | 1.020868 | 34.971 | 0 |
| Materna T3 / THROUGHPUT | -7.914278 | +0.016905 | 1.017049 | 26.171 | 0 |
| Materna T3 / MEMORY | -8.702593 | +0.020827 | 1.021046 | 27.657 | 0 |
| Materna T3 / DISK_WRITE | -71.295095 | +0.034153 | 1.034743 | 20.800 | 0 |

Interpretation: a favourable mean-error gain does not establish a majority of improved cells. TimeTrack S2:S1 memory has frozen gain+0.859389%, but median ratio 1.009934 and win rate44.643%; fastStorage/T1 M1:S2 CPU have tiny favourable headline gains but median ratios>1 and fewer than half of cells improved. Conversely, T1 S2:S1 memory has headline−0.019692% but median ratio 0.975163 and 69.486% wins. These are differences in error magnitude/weighting, not contradictions or reasons to overwrite the primary endpoint.

Every M1:S2 block/resource has median seed-mean ratio>1 and win rate<50%, including its three small positive frozen CPU headline gains. The throughput/memory/disk adverse findings therefore have a directional-cell component, not only a few extreme absolute errors; their severity still varies substantially. T1/T3 M1 disk median cell ratios are 1.024565/1.034743, while the frozen gains are−27.457746%/−71.295095%: large average-error penalties must not be described as equally catastrophic in the typical cell.

A second, explicitly seed-matched panel (entity×fold×lead×seed;840 TimeTrack or 2625 external cells/resource) is provided in [robust_seed_matched_cells.csv](/Users/fgtek002/TimeTrack/review_revision/stage18c1_evidence/robust_seed_matched_cells.csv) so the seed-mean convention is not silently imposed on TimeTrack's raw cell file. Its48 rows contain the same median-log/median-ratio/win/tie outputs. Only Rnd throughput has exact seed-matched ties: S2:S1 has 2 (both0/0, undefined ratios excluded with counts), 2 zero-candidate/positive-reference ratios and 36 positive-candidate/zero-reference ratios; M1:S2 has 4 positive-candidate/zero-reference ratios and 0 ties. All other seed-matched ties/zero cases are 0. Extended-real ratios are retained, undefined0/0 ratios are explicitly counted, and win rates still include tied cells. The main and seed-matched panels are not mixed.

[Main 48-row robust table](/Users/fgtek002/TimeTrack/review_revision/stage18c1_evidence/robust_seed_mean_cells.csv); [matched seed-mean errors](/Users/fgtek002/TimeTrack/review_revision/stage18c1_evidence/matched_seed_mean_errors.csv). No cell is treated as an independent statistical replicate.

## 3. Existing-seed sensitivity — no additional seeds

Seed0/1/2 gains below use the unchanged equal-entity/fold, then equal-horizon MacroMAE formula within each seed. Range is max−min in percentage points; SD is population SD (`ddof=0`) of exactly these3 gains, not a standard error or an inferred noise floor. **FLIP** means at least one strictly positive and one strictly negative seed gain; no magnitude threshold defines it.

Local-cell W/L/V counts below refer instead to each entity×fold×lead across its 3 matched seeds: W=all 3 candidate wins, L=all 3 candidate losses, V=strictly positive and negative gains both occur. All-tie/tie-mixed-without-flip local groups=0 here. Median local range/SD is descriptive; cells with any zero reference MAE have undefined percentage spreads and are enumerated rather than assigned an epsilon.

### S2_vs_S1 seed summary

| Block/resource | Seed0 / Seed1 / Seed2 gain % | Range / SD pp | Block sign | Local W / L / V | Median local range / SD pp |
|---|---|---|---|---|---|
| TimeTrack / CPU | -1.981093 / -2.000568 / -5.932358 | 3.951265 / 1.858071 | stable | 57 / 81 / 142 | 8.75350 / 3.80082 |
| TimeTrack / THROUGHPUT | -0.468046 / -0.188427 / -0.071978 | 0.396068 / 0.166205 | stable | 79 / 63 / 138 | 3.18877 / 1.35068 |
| TimeTrack / MEMORY | -0.785691 / +0.899901 / +2.433501 | 3.219192 / 1.314718 | **FLIP** | 49 / 77 / 154 | 14.95643 / 6.25214 |
| TimeTrack / DISK_WRITE | -0.788174 / -0.493977 / -0.195247 | 0.592927 / 0.242064 | stable | 82 / 88 / 110 | 1.41822 / 0.61459 |
| fastStorage / CPU | -4.653158 / -0.836111 / -4.163935 | 3.817046 / 1.695864 | stable | 218 / 213 / 444 | 9.92664 / 4.23211 |
| fastStorage / THROUGHPUT | -2.800638 / -0.007372 / +2.847229 | 5.647867 / 2.305777 | **FLIP** | 242 / 223 / 410 | 9.55024 / 4.05124 |
| fastStorage / MEMORY | +2.166251 / +2.660079 / +2.522975 | 0.493829 / 0.208144 | stable | 488 / 159 / 228 | 2.26083 / 0.96990 |
| fastStorage / DISK_WRITE | +2.420594 / +2.703501 / +2.940147 | 0.519553 / 0.212387 | stable | 250 / 209 / 416 | 7.99275 / 3.38751 |
| Rnd / CPU | +1.984487 / +0.394542 / +1.853304 | 1.589945 / 0.720580 | stable | 216 / 256 / 403 | 9.16423 / 3.87942 |
| Rnd / THROUGHPUT | -5.453062 / -7.570435 / -8.618447 | 3.165385 / 1.316614 | stable | 178 / 290 / 407 | 4.88526 / 2.11843 |
| Rnd / MEMORY | +1.792827 / +1.627443 / +1.599031 | 0.193796 / 0.085450 | stable | 434 / 173 / 268 | 3.55085 / 1.52609 |
| Rnd / DISK_WRITE | +1.617878 / -3.608960 / +2.407804 | 6.016764 / 2.669691 | **FLIP** | 180 / 342 / 353 | 5.17322 / 2.25912 |
| Materna T1 / CPU | -2.911522 / -4.507909 / -5.525094 | 2.613572 / 1.075685 | stable | 276 / 204 / 395 | 9.56224 / 4.16164 |
| Materna T1 / THROUGHPUT | +1.232345 / -0.027270 / +1.739481 | 1.766752 / 0.742760 | **FLIP** | 284 / 240 / 351 | 4.01178 / 1.72111 |
| Materna T1 / MEMORY | -0.346447 / +0.512781 / -0.226086 | 0.859228 / 0.379866 | **FLIP** | 462 / 168 / 245 | 4.50392 / 1.94373 |
| Materna T1 / DISK_WRITE | -8.332861 / -5.627162 / -6.163909 | 2.705699 / 1.169675 | stable | 270 / 228 / 377 | 4.32811 / 1.84388 |
| Materna T2 / CPU | +3.421791 / +4.715797 / +4.473312 | 1.294006 / 0.561639 | stable | 385 / 126 / 364 | 9.81202 / 4.18028 |
| Materna T2 / THROUGHPUT | +1.730628 / -1.933453 / +1.069596 | 3.664080 / 1.594461 | **FLIP** | 306 / 186 / 383 | 4.13819 / 1.77726 |
| Materna T2 / MEMORY | +4.090371 / +3.671158 / +4.083098 | 0.419213 / 0.195927 | stable | 420 / 158 / 297 | 4.43121 / 1.87958 |
| Materna T2 / DISK_WRITE | -2.385167 / -0.504353 / -0.474830 | 1.910337 / 0.893664 | stable | 263 / 195 / 417 | 5.00702 / 2.10880 |
| Materna T3 / CPU | +1.409130 / -10.244289 / +0.420759 | 11.653418 / 5.275965 | **FLIP** | 221 / 226 / 428 | 9.93128 / 4.26405 |
| Materna T3 / THROUGHPUT | -1.240197 / -0.483881 / +1.844526 | 3.084723 / 1.312716 | **FLIP** | 240 / 289 / 346 | 3.56981 / 1.51071 |
| Materna T3 / MEMORY | +2.960329 / +2.991379 / +3.314328 | 0.353999 / 0.160061 | stable | 438 / 189 / 248 | 3.91355 / 1.66697 |
| Materna T3 / DISK_WRITE | -0.138669 / +3.366183 / +2.447212 | 3.504852 / 1.483812 | **FLIP** | 277 / 239 / 359 | 4.70982 / 2.04703 |

### M1_vs_S2 seed summary

| Block/resource | Seed0 / Seed1 / Seed2 gain % | Range / SD pp | Block sign | Local W / L / V | Median local range / SD pp |
|---|---|---|---|---|---|
| TimeTrack / CPU | +1.769837 / -3.222215 / +2.721758 | 5.943973 / 2.606776 | **FLIP** | 47 / 91 / 142 | 9.65850 / 4.09553 |
| TimeTrack / THROUGHPUT | +0.090879 / -1.835451 / -0.784043 | 1.926331 / 0.787521 | **FLIP** | 42 / 99 / 139 | 3.53591 / 1.51216 |
| TimeTrack / MEMORY | -19.613352 / -14.181809 / -21.696726 | 7.514917 / 3.167826 | stable | 5 / 198 / 77 | 20.87879 / 8.88467 |
| TimeTrack / DISK_WRITE | -0.322320 / -1.080326 / -0.985576 | 0.758006 / 0.337220 | stable | 47 / 118 / 115 | 1.53690 / 0.66400 |
| fastStorage / CPU | +0.590294 / -0.775436 / +0.310718 | 1.365730 / 0.589078 | **FLIP** | 127 / 359 / 389 | 9.87289 / 4.27395 |
| fastStorage / THROUGHPUT | -23.225501 / -23.349536 / -35.114890 | 11.889389 / 5.575706 | stable | 101 / 461 / 313 | 13.66437 / 5.87613 |
| fastStorage / MEMORY | -5.076851 / -4.365326 / -5.158182 | 0.792856 / 0.356137 | stable | 93 / 460 / 322 | 2.50065 / 1.08276 |
| fastStorage / DISK_WRITE | -4.794609 / -3.879942 / -3.546337 | 1.248271 / 0.527688 | stable | 109 / 416 / 350 | 8.55071 / 3.64612 |
| Rnd / CPU | -16.366236 / -16.420187 / -16.743094 | 0.376858 / 0.166400 | stable | 71 / 443 / 361 | 10.39117 / 4.46627 |
| Rnd / THROUGHPUT | -16.905837 / -13.193519 / -12.921484 | 3.984353 / 1.817519 | stable | 117 / 371 / 387 | 6.53223 / 2.83806 |
| Rnd / MEMORY | -9.388542 / -8.112030 / -9.252328 | 1.276511 / 0.572355 | stable | 75 / 489 / 311 | 4.23045 / 1.81870 |
| Rnd / DISK_WRITE | -4.995292 / -5.312017 / -6.368227 | 1.372935 / 0.586974 | stable | 53 / 546 / 276 | 6.43631 / 2.78755 |
| Materna T1 / CPU | -1.689360 / +2.006228 / +2.256878 | 3.946238 / 1.804100 | **FLIP** | 161 / 263 / 451 | 9.59378 / 4.05920 |
| Materna T1 / THROUGHPUT | -9.061155 / -7.347673 / -5.515523 | 3.545632 / 1.447768 | stable | 76 / 466 / 333 | 5.35997 / 2.28167 |
| Materna T1 / MEMORY | -13.527842 / -13.443071 / -12.685594 | 0.842248 / 0.378644 | stable | 87 / 461 / 327 | 5.79000 / 2.47870 |
| Materna T1 / DISK_WRITE | -28.142927 / -28.070846 / -26.165410 | 1.977516 / 0.915693 | stable | 82 / 459 / 334 | 5.21044 / 2.20697 |
| Materna T2 / CPU | -2.616513 / -2.291012 / -2.788161 | 0.497148 / 0.206174 | stable | 134 / 328 / 413 | 9.98622 / 4.25211 |
| Materna T2 / THROUGHPUT | -9.732359 / -7.578477 / -8.798208 | 2.153882 / 0.881891 | stable | 83 / 412 / 380 | 4.35628 / 1.86308 |
| Materna T2 / MEMORY | -9.337139 / -8.856837 / -9.608514 | 0.751677 / 0.310797 | stable | 103 / 477 / 295 | 5.66539 / 2.38573 |
| Materna T2 / DISK_WRITE | -7.648613 / -8.199582 / -7.820435 | 0.550969 / 0.230179 | stable | 122 / 376 / 377 | 5.11268 / 2.17561 |
| Materna T3 / CPU | -5.441695 / -2.533563 / -17.079941 | 14.546378 / 6.284930 | stable | 127 / 327 / 421 | 11.23575 / 4.85777 |
| Materna T3 / THROUGHPUT | -6.188420 / -7.762664 / -9.837298 | 3.648878 / 1.494310 | stable | 109 / 452 / 314 | 4.62573 / 1.99793 |
| Materna T3 / MEMORY | -6.981998 / -9.316378 / -9.812009 | 2.830011 / 1.233961 | stable | 98 / 446 / 331 | 4.64070 / 1.96818 |
| Materna T3 / DISK_WRITE | -54.651899 / -71.546504 / -87.841536 | 33.189637 / 13.550350 | stable | 80 / 513 / 282 | 5.31959 / 2.25719 |

The aggregate seed signs reproduce Stage 18A1: S2:S1 has 15 sign-stable and 9 sign-variable block/resource summaries; M1:S2 has 20 stable and 4 variable. These are descriptive counts, not a pooled cross-block effect estimate. The nine S2 flips are TimeTrack memory; fastStorage throughput; Rnd disk; T1 throughput/memory; T2 throughput; and T3 CPU/throughput/disk. The four M1 flips are TimeTrack CPU/throughput, fastStorage CPU and T1 CPU.

Especially small frozen effects with observed sign changes include fastStorage S2:S1 throughput+0.012731%, T1 S2:S1 memory−0.019692%, T3 S2:S1 throughput+0.044766% and fastStorage M1:S2 CPU+0.045047%. They must not be promoted into reliable improvements or stable temporal reversals. No new near-zero cutoff is invented. Even some aggregate sign-stable rows contain many sign-variable local cells; neither notion implies uniform benefit/harm.

Rnd throughput local percentage spreads are undefined for21 S2:S1 and 4 M1:S2 groups with a zero reference in at least one seed; local sign categories still use direct finite MAE differences. All other local spread denominators are positive. The per-seed matching and all local gains/ranges/SDs are retained in [seed_matched_cell_sensitivity.csv](/Users/fgtek002/TimeTrack/review_revision/stage18c1_evidence/seed_matched_cell_sensitivity.csv). All 120 relevant external existing `positive_seed_signs.csv` values were cross-checked; TimeTrack raw paired outputs were checked directly. Three fixed seeds, overlapping folds/horizons and related temporal blocks do not support an IID sampling interpretation or an estimated universal stochastic noise floor.

## 4. TimeTrack Ridge throughput diagnosis

**CONCENTRATED_DEGRADATION.** This classification is a descriptive reading of the exact contributions below, not a new threshold rule. No implementation defect is demonstrated; the corrected persistence adapter/checker issues are historical and unrelated to generating the stored throughput predictions.

AR MacroMAE=28.739891294; ARX MacroMAE=269.709435639; frozen post-hoc gain=−838.449742%. Across 35 machine/fold pairs, ARX improves 21, worsens 14 and ties 0; median ARX/AR ratio=0.996277043. Thus the aggregate deterioration is not broad by machine/fold direction.

machine06/fold3 (L=128, both alphas 100) has AR MAE 92.273361 versus ARX 8535.657577: ratio 92.504029 and excess 8443.384217. It contributes 99.931577% of the sum of **positive** machine/fold excess MAEs; the top 3 contribute 99.979061%. Its contribution is 100.112049% of the **net** excess because improvements elsewhere offset part of it. Contributions use the same equally weighted machine/fold means as the headline endpoint; no unit is removed, winsorised, replaced or retuned.

Selected-alpha distribution (35 contexts per formulation): AR uses 0.01 in 12 and 100 in 23; ARX uses 1 in 1, 10 in 1 and 100 in 33. Every alpha was verified against its 5 saved inner scores and tie rule, without test-driven reselection. The prescribed grid ending at 100 bounds this result; selecting its boundary is not itself an implementation defect or an authorisation to expand it after inspecting test error.

All 70 saved final prediction files and targets are finite. Native target range across them is 0.949999988 to 3746.737793; AR predictions range 0 to 1594.761928 and ARX 0 to 7611415.626105. ARX's extreme maximum is in machine06/fold3, lead 8, origin 30957, whose saved target is 1512.025513 (the fold's maximum target is 1729.206665). Its largest per-lead mean errors occur at leads 16 and 8. The native explosion is consistent with finite extrapolation passed through the correctly implemented log1p inverse, not numeric infinity or proof of a defective model implementation. The stored artifacts do not uniquely decompose which input shifts/correlations/coefficients caused extrapolation.

Verification: prediction/model hashes, all origin/target/lead/timestamp/support columns and native targets match the frozen M1 support; selected L matches frozen M1; source median/IQR scaler payloads exactly match frozen final records; feature-standardiser sample counts match outer training counts; coefficients/scalers are finite with the correct 1-channel or 4-channel lag dimensions. Inverting saved scaled throughput predictions with the recorded median/IQR, expm1 and nonnegative projection reproduces saved unclipped/clipped predictions exactly. Frozen helper/source hashes and completed audits authenticate training-only scaling/input construction; no training data/scaler/model was refitted or model prediction recomputed here.

### All 35 machine/fold means

| Machine | Fold | L | AR MAE | ARX MAE | ARX/AR | AR alpha | ARX alpha |
|---|---:|---:|---:|---:|---:|---:|---:|
| machine01 | 1 | 128 | 39.115793 | 39.134991 | 1.000491 | 100 | 100 |
| machine01 | 2 | 64 | 39.783969 | 38.816368 | 0.975679 | 0.01 | 100 |
| machine01 | 3 | 64 | 27.441001 | 27.311865 | 0.995294 | 100 | 100 |
| machine01 | 4 | 128 | 48.294870 | 47.623604 | 0.986101 | 100 | 100 |
| machine01 | 5 | 128 | 61.338545 | 60.536889 | 0.986931 | 100 | 100 |
| machine02 | 1 | 64 | 34.350213 | 32.873924 | 0.957022 | 100 | 100 |
| machine02 | 2 | 64 | 35.039126 | 32.927098 | 0.939724 | 0.01 | 100 |
| machine02 | 3 | 32 | 32.940084 | 32.085035 | 0.974042 | 0.01 | 100 |
| machine02 | 4 | 128 | 33.908968 | 33.782727 | 0.996277 | 0.01 | 100 |
| machine02 | 5 | 64 | 38.736116 | 38.324670 | 0.989378 | 0.01 | 10 |
| machine03 | 1 | 32 | 9.956610 | 10.251020 | 1.029569 | 100 | 100 |
| machine03 | 2 | 128 | 5.719837 | 5.873698 | 1.026900 | 100 | 100 |
| machine03 | 3 | 128 | 6.745962 | 7.214499 | 1.069454 | 100 | 100 |
| machine03 | 4 | 128 | 23.578639 | 25.354850 | 1.075331 | 100 | 100 |
| machine03 | 5 | 32 | 32.123636 | 32.048267 | 0.997654 | 100 | 100 |
| machine04 | 1 | 32 | 50.212992 | 50.381725 | 1.003360 | 100 | 100 |
| machine04 | 2 | 64 | 10.093613 | 10.050200 | 0.995699 | 100 | 100 |
| machine04 | 3 | 128 | 1.061256 | 1.058423 | 0.997330 | 100 | 100 |
| machine04 | 4 | 128 | 8.309867 | 8.547223 | 1.028563 | 100 | 100 |
| machine04 | 5 | 64 | 10.771419 | 10.899214 | 1.011864 | 100 | 100 |
| machine05 | 1 | 32 | 22.421078 | 22.137419 | 0.987349 | 0.01 | 1 |
| machine05 | 2 | 32 | 23.297877 | 22.759465 | 0.976890 | 100 | 100 |
| machine05 | 3 | 128 | 17.981782 | 17.836271 | 0.991908 | 0.01 | 100 |
| machine05 | 4 | 32 | 22.599030 | 22.145747 | 0.979942 | 100 | 100 |
| machine05 | 5 | 128 | 11.974344 | 12.077897 | 1.008648 | 100 | 100 |
| machine06 | 1 | 128 | 22.825491 | 22.953627 | 1.005614 | 100 | 100 |
| machine06 | 2 | 32 | 7.085026 | 7.144701 | 1.008423 | 100 | 100 |
| machine06 | 3 | 128 | 92.273361 | 8535.657577 | 92.504029 | 100 | 100 |
| machine06 | 4 | 64 | 21.366046 | 21.373982 | 1.000371 | 0.01 | 100 |
| machine06 | 5 | 32 | 13.205459 | 13.190242 | 0.998848 | 0.01 | 100 |
| machine07 | 1 | 64 | 51.190799 | 48.931081 | 0.955857 | 100 | 100 |
| machine07 | 2 | 32 | 45.990518 | 43.488909 | 0.945606 | 100 | 100 |
| machine07 | 3 | 128 | 26.873144 | 29.108940 | 1.083198 | 0.01 | 100 |
| machine07 | 4 | 64 | 35.197747 | 34.297192 | 0.974414 | 0.01 | 100 |
| machine07 | 5 | 128 | 42.091979 | 41.630908 | 0.989046 | 0.01 | 100 |

Full ranges and checks per saved model/prediction are in [timetrack_throughput_prediction_checks.csv](/Users/fgtek002/TimeTrack/review_revision/stage18c1_evidence/timetrack_throughput_prediction_checks.csv); machine/fold values and machine summaries are separate linked CSVs in the evidence directory. No fresh inference, outlier removal or alternative experiment was performed.

## 5. Cross-model contextual evidence: one matrix per resource

Numbers are existing frozen LSTM S2:S1 gains and completed Ridge ARX:AR gains in percent. Positive means context helps; negative means it hurts. Agreement is only a point-direction agreement under these two implemented designs, not equal magnitude, significance or an architecture-only causal replication.

### CPU

| Block | Frozen LSTM S2:S1 % | Ridge ARX:AR % | Point direction |
|---|---:|---:|---|
| TimeTrack | -3.313049 | -14.003655 | same |
| fastStorage | -3.198519 | -4.365672 | same |
| Rnd | +1.412867 | +0.222863 | same |
| Materna-T1 | -4.317958 | +6.271617 | opposite |
| Materna-T2 | +4.207624 | +9.668215 | same |
| Materna-T3 | -2.787548 | +2.173782 | opposite |

Point signs agree adversely on TimeTrack/fastStorage and favourably on Rnd/T2; they reverse on T1/T3. Rnd's positive Ridge gain is much smaller than its LSTM gain. A universal beneficial CPU-context claim is unsupported.

### THROUGHPUT

| Block | Frozen LSTM S2:S1 % | Ridge ARX:AR % | Point direction |
|---|---:|---:|---|
| TimeTrack | -0.242752 | -838.449742 | same |
| fastStorage | +0.012731 | -20.745935 | opposite |
| Rnd | -7.214491 | +0.365879 | opposite |
| Materna-T1 | +0.986935 | -13.900364 | opposite |
| Materna-T2 | +0.294315 | +0.911081 | same |
| Materna-T3 | +0.044766 | -2.148804 | opposite |

Only T2 has favourable point-sign agreement; TimeTrack has adverse agreement, but Ridge's extreme magnitude is concentrated as diagnosed. fastStorage, Rnd, T1 and T3 reverse signs. Most favourable LSTM throughput point effects are seed-variable. No broad throughput-context benefit replicates.

### MEMORY

| Block | Frozen LSTM S2:S1 % | Ridge ARX:AR % | Point direction |
|---|---:|---:|---|
| TimeTrack | +0.859389 | -23.213529 | opposite |
| fastStorage | +2.449985 | +2.875732 | same |
| Rnd | +1.673083 | +4.258510 | same |
| Materna-T1 | -0.019692 | +7.221757 | opposite |
| Materna-T2 | +3.948171 | +6.469006 | same |
| Materna-T3 | +3.089002 | +1.812428 | same |

fastStorage, Rnd, T2 and T3 have positive point gains in both families. Ridge memory improves in all 5 external blocks, including T1, whose LSTM primary gain is slightly negative/seed-variable even though its robust matched-cell direction is favourable. TimeTrack reverses, and its original LSTM gain is also seed-variable with fewer than half of seed-mean cells improved. This is the strongest recurring external contextual signal, not a universal or model-invariant effect.

### DISK_WRITE

| Block | Frozen LSTM S2:S1 % | Ridge ARX:AR % | Point direction |
|---|---:|---:|---|
| TimeTrack | -0.492319 | -7.575291 | same |
| fastStorage | +2.689207 | +1.048266 | same |
| Rnd | +0.160400 | +1.683458 | same |
| Materna-T1 | -6.699662 | +2.046668 | opposite |
| Materna-T2 | -1.120181 | +10.072815 | opposite |
| Materna-T3 | +1.907168 | -0.690740 | opposite |

fastStorage/Rnd have favourable point agreement and TimeTrack adverse agreement. T1/T2 change from adverse LSTM to favourable Ridge, while T3 changes from favourable LSTM to adverse Ridge. Rnd/T3 LSTM point gains are seed-variable. Cross-family and temporal disk-write conclusions must remain conditional.

## 6. Controlled-sharing sensitivity matrix

All entries are existing percent gains: positive favours M1, negative favours the indicated S2 reference. Common-S2 uses frozen H64-M1 contexts; H129 reruns its own original inner context/epoch selection. These are separate controls, not one jointly capacity/context-matched factorial intervention.

| Block/resource | H64 : original S2 % | H64 : common-context S2 % | H129 : original S2 % | Adverse in all 3 |
|---|---:|---:|---:|---|
| TimeTrack / CPU | +0.469562 | -0.805203 | -2.928995 | no |
| TimeTrack / THROUGHPUT | -0.840084 | -0.538578 | -0.155635 | yes |
| TimeTrack / MEMORY | -18.476886 | -17.790024 | -18.484754 | yes |
| TimeTrack / DISK_WRITE | -0.795572 | -0.559875 | -0.600995 | yes |
| fastStorage / CPU | +0.045047 | +0.356824 | +3.137551 | no |
| fastStorage / THROUGHPUT | -27.094152 | -20.306730 | -33.828991 | yes |
| fastStorage / MEMORY | -4.867061 | -4.431741 | -4.187582 | yes |
| fastStorage / DISK_WRITE | -4.072129 | -1.753462 | -4.052647 | yes |
| Rnd / CPU | -16.509941 | -16.322196 | -17.566460 | yes |
| Rnd / THROUGHPUT | -14.318987 | -12.567783 | -15.563046 | yes |
| Rnd / MEMORY | -8.915737 | -8.685519 | -8.064244 | yes |
| Rnd / DISK_WRITE | -5.551233 | -3.717436 | -6.854271 | yes |
| Materna T1 / CPU | +0.882699 | -0.610785 | +3.187848 | no |
| Materna T1 / THROUGHPUT | -7.308355 | -7.185279 | -4.716270 | yes |
| Materna T1 / MEMORY | -13.218360 | -10.147521 | -12.317568 | yes |
| Materna T1 / DISK_WRITE | -27.457746 | -27.980887 | -24.622984 | yes |
| Materna T2 / CPU | -2.564363 | -1.383238 | +0.172040 | no |
| Materna T2 / THROUGHPUT | -8.692761 | -7.263714 | -3.652728 | yes |
| Materna T2 / MEMORY | -9.266823 | -7.517031 | -6.718914 | yes |
| Materna T2 / DISK_WRITE | -7.888503 | -7.932132 | -7.203055 | yes |
| Materna T3 / CPU | -8.099015 | -7.404383 | -8.206775 | yes |
| Materna T3 / THROUGHPUT | -7.914278 | -7.437102 | -5.825119 | yes |
| Materna T3 / MEMORY | -8.702593 | -7.794014 | -6.533105 | yes |
| Materna T3 / DISK_WRITE | -71.295095 | -69.667946 | -64.002746 | yes |

Every throughput, memory and disk-write block/resource retains an adverse M1 **MacroMAE point estimate** under both controls. Rnd and T3 CPU also remain adverse in all 3comparisons. This is not a claim that every entity/fold/seed worsens: original TimeTrack throughput, for example, has a seed sign flip. CPU exceptions are fragile: TimeTrack's small original positive gain reverses under both controls; T1 CPU changes direction with the reference; T2 CPU reverses to a small+0.172040% under H129.

Context matching changes magnitude but is not a general cure: fastStorage throughput moves−27.094152% to −20.306730%, whereas T1 disk moves−27.457746% to −27.980887%. Approximate aggregate-capacity matching also does not remove the pattern: H129 T1/T3 disk remains−24.622984%/−64.002746%; fastStorage throughput worsens to−33.828991%. TimeTrack memory is nearly unchanged at−18.484754%. Exact S2 versus H129 parameter counts are 206100 versus 206420 externally and 206880 versus 207980 in TimeTrack (+0.155264%/+0.531709%). Parameter-count parity is not equivalence of architecture, optimisation geometry or function class.

## 7. Manuscript-facing conclusions bounded to the evidence

### Contextual inputs

> Under the evaluated per-entity forecasting protocols, cross-resource lagged inputs provide selective rather than uniform benefits. External memory is a recurring favourable case, but individual directions and magnitudes vary by resource, block, seed and model family; TimeTrack memory and several throughput/disk comparisons do not support a model-independent benefit.

Do not claim that all resources, all six blocks or the typical matched cell improve whenever a headline gain is positive. Distinguish frozen MacroMAE, matched-cell medians/wins, seed stability and existing consistency classes. The Ridge outlier limits claims about broad degradation as much as it limits claims about universal benefit.

### Shared representation

> Replacing four separately fitted target networks with one jointly trained four-resource network generally increases native MacroMAE for throughput, memory and disk write in these evaluated blocks. Their adverse point directions survive separate common-context and approximate aggregate-capacity controls. The experiment demonstrates an operational sharing trade-off, not a uniquely identified universal sharing mechanism.

Do not state that gradient interference, negative transfer in every target/VM, or representation sharing alone has been causally proven. Missing gradient/clipping traces and incomplete S1/S2 loss histories from Stage 18A1 still limit optimisation attribution. Models are per entity×fold×seed, not globally pooled across VMs.

### Capacity

> The original large aggregate parameter difference is a genuine confound, but increasing M1 to H129—approximately matching the four-network S2 complement—does not suffice to remove the adverse throughput/memory/disk point estimates. Capacity contributes to some magnitudes but is not a complete explanation within this pipeline.

Remove either extreme claim: neither 'the degradation is simply fewer parameters' nor 'capacity has been perfectly eliminated as a causal factor' follows. H129 changes hidden width and selection; it does not reproduce four independent optimisers/representations.

### Context selection

> Giving S2 the same frozen H64-M1 context often narrows differences but does not remove the adverse pattern; context-selection freedom is contributory rather than a sufficient explanation. The H129 and common-context controls are separate sensitivity analyses, not a complete joint mechanistic isolation.

Clarify that context choice uses transformed/robust-scaled validation MAE at an MSE-selected epoch, while native evaluation NMAE is native MAE divided by native training IQR. The manuscript's current ambiguous use of 'NMAE' for selection needs a later wording correction, not a retrospective change to fitted results. Training, early stopping, context selection and native evaluation are distinct objectives/spaces.

### Persistence / absolute skill

> Relative gains do not guarantee useful absolute prediction skill. Existing mean per-cell persistence skills are negative for all original formulations on TimeTrack memory, Bitbrains CPU and fastStorage throughput; Materna M1 also has negative mean skill on T1/T3 throughput and disk write. Several other cells beat persistence, so blanket failure claims are equally unwarranted.

Keep the existing mean-relative-skill definition: it is not 1−MacroMAE/MacroPersistenceMAE. Positive MacroMAE gains can coexist with lower mean skill, as seen in Ridge disk/CPU cases. Ridge Rnd throughput has 30 undefined zero-denominator skills per formulation, explicitly counted; none is a nonfinite prediction/primary MAE. Source-specific target units and transforms preclude pooling raw resource errors.

### Seeds / noise

> Several small primary context effects change sign across the three recorded seeds, while many larger adverse sharing effects remain negative across them. These observations support caution around small positive/negative point estimates; three fixed seeds do not establish a general noise floor, statistical significance or stability under arbitrary retraining.

Remove language treating tiny seed-variable gains or mechanically changing frozen consistency labels as conclusive improvements/temporal reversals. Existing classification predicates and bootstrap intervals remain separate from point signs and from this audit's descriptive diagnostics. Overlapping expanding folds, multiple horizons and repeated Materna VM populations must not be portrayed as independent replicates.

### Materna disk write

> T1/T3 M1 disk-write degradation has a broadly adverse matched-cell direction but a concentrated absolute-error magnitude. Median cell ratios are near 1.025/1.035, while the existing Stage 18A1 per-VM analysis attributes 82.10%/86.97% of positive per-VM excess to VM266/VM272. Native gains remain adverse under common-context and H129 controls; finite artifacts and correct scalers/inversion do not demonstrate a fitting defect requiring rerun.

Do not describe uniform catastrophic failure across all VMs or dismiss the results as an IQR denominator artifact: primary gain divides by native S2 MacroMAE, not IQR. Original M1 disk seed gains remain negative on T1 (−28.142927% to −26.165410%) and T3 (−87.841536% to −54.651899%), despite different magnitudes. Ridge reverses to+2.046668% on T1 but remains negative−0.690740% on T3; contextual input and joint-network sharing answer different questions.

### Claims to weaken/remove and remaining reviewer concerns

- Remove universal cross-resource or universal-memory benefit claims; retain a qualified recurring external-memory pattern.
- Replace 'sharing causes negative transfer everywhere' with an operational, per-entity and resource-specific comparison that acknowledges the separate controls and residual mechanism confounds.
- Do not attribute all degradation to capacity/context choice, or claim either control alone is complete causal isolation.
- Do not turn tiny seed-variable effects into reliable superiority, or median/win diagnostics into substitutes for frozen primary gains.
- Remove uniform catastrophic-VM, general linear-ARX failure and proven numerical/scaling-defect narratives. The TimeTrack Ridge penalty is overwhelmingly one machine/fold, under a specified context/alpha grid.
- Correct objective-space wording, local four-versus-one model counts and fit-hour semantics when manuscript revision is separately authorised. Summed worker fit-hours are not elapsed runtime, energy or demonstrated production savings.
- Retain limitations: fixed eligible cohorts, three seeds, related temporal blocks, no operational/controller evaluation, missing mechanistic training diagnostics, Ridge's finite five-alpha grid and frozen M1 contexts. Hitting alpha 100 frequently is a scope limitation, not proof of a defect; post-test retuning would answer a new question.
- Keep all post-hoc controls/diagnostics clearly labelled and provenance-linked. Reviewer concerns about generality, uncertainty and mechanism remain reasons to narrow claims, not to silently add experiments or replace frozen outcomes.

## 8. Further-experiment decision

**NO — no further experiment is scientifically necessary before submission of the bounded descriptive/operational claims above.** All authorised controls are complete and provenance-clean; the existing-artifact audit shows concentration/seed/estimand limitations, not an unresolved scientific implementation defect. The resolved persistence adapter and audit-checker defects did not alter training/selection or justify new outcome-driven reruns. Do not retrain the outlier, widen the alpha grid after seeing it, add seeds retrospectively or replace poor frozen cells.

Stronger claims about universal contextual value, independently identified sharing mechanisms, production benefits or stochastic superiority would require a separately designed prospective study; those stronger claims should instead be weakened/removed for this submission. Editorial/objective-description corrections and explicit uncertainty/provenance reporting remain necessary author decisions. No manuscript revision or new experiment is authorised or started here.

## 9. Preservation and reproducibility

Before and after diagnostics, all 395785 protected files passed SHA256 content/membership and Git-ref checks: all frozen scientific/manuscript trees, Stage 18A1, all 3 post-hoc experiment trees, their predecessor snapshots and benchmark/src. Historical experiment inventories and recovery snapshots were checked before accepting the new baseline. Added/removed/modified protected files=0. Manuscript modifications=0; frozen/post-hoc result modifications=0; training=0; model inference=0; commit=no; push=no.

No existing experiment's writers, main routine, training/evaluation driver or model methods were invoked. Only new `review_revision/stage18c1_evidence/` files and this requested report were written. Transform arithmetic uses saved predictions only. Stage 18C1 sources and outputs are hash-inventoried separately; the original post-hoc inventories remain unchanged.

Traceability: `audit_synthesis.py` performs read-only provenance/matching/diagnosis/calculations; `build_report.py` composes this report. `preservation_before.jsonl`, `preservation_baseline.json`, `preservation_after.json`, `posthoc_provenance.json`, `matched_checks.json`, the 48-row robust/seed tables, full matched-cell seed records, 35 machine/fold diagnosis rows, prediction-range/support checks and both evidence matrices are in the evidence directory. All gain/SD units and zero/tie conventions are explicit above. No new inferential statistic or significance test is generated.

STAGE_18C1_PASS
