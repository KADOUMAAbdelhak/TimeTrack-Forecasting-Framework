# Final-pack execution deviations

Non-blocking deviations observed during accepted final packs. These do **not**
alter frozen model or evaluation logic. They must be considered before final
efficiency and aggregation reporting.

## memory_classical (accepted)

1. **Reconciliation evaluation count mismatch.**  
   Configuration `estimated_recon_evals` was **144**, but the frozen ablation
   expansion (primary methods + h8 OLS + h8 nonnegative flags) produced
   **162** reconciliation evaluations.

2. **Provenance duplication.**  
   Execution/freeze provenance (`execution_commit`, `freeze_tag_commit`,
   `frozen_implementation_commit`, etc.) is complete in `MANIFEST.json` but is
   not duplicated on every generated CSV row. Per-row CSVs do carry
   `freeze_commit`, `freeze_tag`, `dataset_fingerprint`, `config_hash`, and
   `pack_hash`.

3. **Missing efficiency fields.**  
   Warm inference latency, reconciliation wall-clock overhead, and serialized
   model size were not persisted in pack metrics.

4. **Scientific impact.**  
   These deviations do **not** affect:
   - predictions,
   - evaluation timestamps,
   - model fitting,
   - reconciliation calculations,
   - coherence,
   - leakage controls.

5. **Downstream handling.**  
   Treat items 1–3 as known gaps before final efficiency tables and
   cross-pack aggregation. Do not invent or impute missing efficiency values;
   mark unavailable fields explicitly.

## memory_dlinear (accepted)

1. **Unavailable efficiency / runtime fields.**  
   Per-series fit times, warm inference latency, forecasts/second, early-stop
   counts, timeout counts, and reconciliation overhead were unavailable in the
   frozen pack metrics (only hierarchy-job `wall_train_sec_sum` and pack-level
   CPU/peak RSS were persisted).

2. **Provenance duplication.**  
   Complete provenance is available in `MANIFEST.json` but is not duplicated in
   every CSV row (same pattern as `memory_classical`).

3. **Peak underprediction.**  
   DLinear predictions capture the correct memory magnitude (~1e11) but compress
   the observed target range to roughly half, indicating peak underprediction.

4. **Scientific impact.**  
   These deviations do **not** affect:
   - split chronology,
   - training,
   - scaling correctness,
   - prediction alignment,
   - reconciliation,
   - coherence,
   - outer-fold metrics.

5. **Downstream handling.**  
   Do not rerun `memory_dlinear`. Mark missing efficiency fields as
   `unavailable_in_frozen_pack_metrics` in aggregation. Treat peak compression
   as a diagnostic finding for later peak analysis, not as a pack failure.

## cpu_classical (accepted)

1. **ISO vs monotonic wall-clock discrepancy.**  
   `MANIFEST.json` ISO start/end timestamps span approximately **1726 seconds**,
   while monotonic `actual_wall_seconds` and shell elapsed are approximately
   **358–361 seconds**.

2. **Runtime enforcement.**  
   Pack runtime enforcement used the monotonic wall-clock measurement
   (`time.perf_counter()` via `WallClockGuard`).

3. **Aggregation follow-up.**  
   During final aggregation, investigate whether the ISO timestamps include:
   - pre-launch waiting,
   - clock adjustment,
   - timezone conversion,
   - stale start timestamp,
   - parent-process initialization.

4. **No rerun.**  
   Do not modify or rerun `cpu_classical`.

5. **Scientific impact.**  
   The timestamp discrepancy does **not** affect predictions, split chronology,
   fitted models, metrics, reconciliation, or coherence.

6. **Unavailable efficiency fields (unchanged pattern).**  
   Warm inference latency, forecasts per second, reconciliation overhead, and
   serialized model size remain unavailable in frozen pack metrics.

7. **Unclipped out-of-range CPU predictions.**  
   Rare negative and >100% CPU predictions were retained because clipping was
   not part of the frozen protocol.

8. **Reconciliation evaluation count.**  
   The frozen ablation expansion produced **162** reconciliation evaluations
   rather than the configuration estimate of **144**.

## cpu_dlinear (accepted)

1. **Unavailable efficiency / runtime fields.**  
   Per-series fit times, early-stop counts, timeout counts, inference latency,
   forecasts/second, and reconciliation overhead were unavailable in the frozen
   pack metrics.

2. **Provenance duplication.**  
   Complete provenance exists in `MANIFEST.json` but is not duplicated in every
   result row.

3. **Out-of-range CPU predictions.**  
   DLinear produced some negative CPU predictions, especially for machine04,
   and rare values above 100%.

4. **No clipping.**  
   No clipping was applied because clipping was not part of the frozen protocol.

5. **Range compression.**  
   Some fold/horizon predictions compressed the CPU range, with the lowest
   prediction-to-target range ratio around **0.76**.

6. **Scientific impact.**  
   These observations do **not** affect chronology, fitting, scaling,
   reconciliation, coherence, or reported metrics.

7. **No rerun.**  
   Do not rerun `cpu_dlinear`.

## disk_boundary (accepted)

1. **Unavailable efficiency fields.**  
   Inference latency, forecasts/second, serialized model size, and
   reconciliation overhead were unavailable in the frozen pack metrics.

2. **Transferred LightGBM configuration.**  
   LightGBM used the frozen memory-family configuration because disk had no
   independent tuning pack.

3. **LightGBM disk base performance.**  
   LightGBM independent forecasts were approximately **7×** worse than
   persistence on disk levels.

4. **Interpretation of LightGBM recon failures.**  
   Its catastrophic bottom-up/WLS/MinT results must be interpreted as a
   transferred-configuration stress case, not evidence that every tree model
   behaves this way.

5. **Ridge independently reproduces the disk boundary.**  
   Bottom-up worsens top MAE by approximately **14–16%**, and all six ridge
   fold-horizon cells lose.

6. **Top-down behavior.**  
   Top-down preserves the independently forecast top exactly while changing
   bottom forecasts and degrading most machine-level results.

7. **Top-down numerical coherence.**  
   Top-down numerical coherence residuals around **1e-5–1e-4** are within the
   frozen floating-point tolerance.

8. **Covariance conditioning.**  
   Covariance condition numbers reached approximately **1.5e6**; no silent
   identity fallback occurred.

9. **No rerun.**  
   Do not rerun `disk_boundary`.

## downsampling (not executed — blocked)

### Downsampling pack — omitted before execution

1. The frozen helper does **not** call the real downsampling implementation.
2. For `factor > 1`, it would fit **native-resolution** windows and relabel
   metadata as coarse resolution.
3. Shared model parameters were **not** passed through the frozen helper.
4. The configured h1/h8 coarse horizons collapse to the same one-step coarse
   label while the actual helper still uses native horizons.
5. Executing the pack would produce scientifically invalid resolution claims.
6. **No downsampling experiment was launched.**
7. **No downsampling final artifact exists.**
8. **No downsampling claim is allowed in the manuscript.**
9. The study is deferred to future work or a separate corrected experiment
   freeze (not `experiment-freeze-v2` / not v3 under this thread).
10. This omission does **not** affect the primary hierarchical reconciliation
    experiments.

See also: `results/final/DOWNSAMPLING_OMISSION.md`.

## supporting_statistics — provisional analysis archived

The first `06_supporting_statistics` pack was demoted to
`results/development/provisional_final_analysis/experiment-freeze-v2/supporting_statistics/`
because timestamp-level bootstrap / Holm / claims were produced by an unfrozen
post-hoc script (`_analyze_stats.py`). It is **not** eligible for final claims.

Final claim statistics must be regenerated under `final-analysis-freeze-v1` via
`scripts/analyze_final_statistics.py` / `timetrack/statistical_reporting.py`.

## supporting_statistics — commit 38366f1 provenance-only verification

Commit `38366f1` (`statistics: resolve annotated freeze tags to peeled commits`)
changed **only** `timetrack/statistical_reporting.py` tag-resolution lines:

- `git rev-parse final-analysis-freeze-v1` → `…^{commit}` (annotated tag → peeled commit)
- `git rev-parse experiment-freeze-v2` → `…^{commit}`
- fallbacks unchanged in purpose

It did **not** change bootstrap, relative-effect, Holm, claim, trade-off, or
prediction-loading logic. No statistical analysis was re-run for this commit.

**SHA-256 of accepted final statistical numeric artifacts** (unchanged; produced
under `final-analysis-freeze-v1` before this correction and not regenerated):

| File | sha256 |
|------|--------|
| paired_block_bootstrap.csv | 3f7e35dbcf376d783cdf03258c85e03f4712dfb6de7631a4b6ea2be0f076e899 |
| relative_effect_bootstrap.csv | 1cc2b6503bf1edae1d40ad231e7f1c3e6f96ae97e9cb5d53c4eee3aa821458a8 |
| holm_corrected_tests.csv | b148fed4ca9eddba73ae8d2e552fcb297ddbe8ec8dff6a1789fde995fba6d863 |
| fold_consistency.csv | 3e850a3d867e9091ec736750cda79f6dadde6a4fc466f83bb3191beccd058873 |
| top_bottom_tradeoff.csv | 2ea928c9fb840bb586e3af918ffbf6ac9970683e38203f1c2c4532657b6b4ec6 |
| claim_support.csv | 0d4eac4cf58ca73c0b022454ac859e6aeeb7cb6f31c5ec6410bc0a75c5729b2c |
| claim_atomic_evidence.csv | e0beff2cceb5610d09da92580f3971fb54cd274daba1c0ee124dd039f7d4fc10 |

Required statement:

> Commit 38366f1 was a provenance-only correction. Statistical numeric
> artifacts and source predictions were unchanged.

Additional notes:

- Peak RSS was unavailable for the statistics entrypoint
  (`scripts/analyze_final_statistics.py` does not record peak RSS; pack-runner
  finalize RSS probe was not used for that run).
- Claim D must be interpreted as **separate** Ridge bottom_up harm and Ridge
  top_down top-preservation results, **not** via its combined median relative
  effect.

## peak_analysis — omitted before execution (frozen smoke stub)

**NOT EXECUTED / SCIENTIFICALLY BLOCKED** under `experiment-freeze-v2`.

`experiments/pack_runner.py::run_peak_analysis` (identical to freeze-v2) and
`experiments/final_supporting_analyses.py::peak_metrics` / `peak_threshold`:

1. Thresholds from `yt_train` only for q90/q95 — leakage-safe (acceptable).
2. Independent forecasts evaluated from stored `pt_test` — acceptable for that
   method alone.
3. Reconciliation comparison is a **smoke stub**: when a `bottom_up` recon CSV
   row exists, the pack appends `method=bottom_up_proxy` but recomputes peak
   metrics on the **same independent** `pt_test` vectors (“placeholder when
   recon vectors not stored”). This cannot support reconciliation peak claims.
4. WLS / MinT / top_down recon peaks are **not** evaluated.
5. Pack config leaves models/horizons/folds/methods empty; discovery is NPZ
   glob over memory/cpu packs only (disk excluded by dependencies — OK).
6. No event-level start/end/merge algorithm beyond ±2-step peak matching inside
   `peak_metrics` (timestamp tolerance is frozen helper behavior).
7. Intended protocol in `configs/final_fgcs_full.yaml` (`compare:
   [independent, retained_reconciled]`) is **not** implemented by the pack
   runner.

Therefore **no peak_analysis pack was launched**. No
`results/final/packs/07_peak_analysis/` final artifacts. No manuscript peak
claims from this freeze path until a corrected analysis layer (analogous to
`final-analysis-freeze-v1`) re-reconciles stored bottoms/tops without
retraining.

## peak_analysis — frozen runner blocked (detail)

Confirmed before any peak-analysis freeze:

1. `experiments/pack_runner.py::run_peak_analysis` uses `method=bottom_up_proxy`.
2. `bottom_up_proxy` recomputes peak metrics on **independent** `pt_test` (placeholder).
3. WLS and MinT prediction vectors were **never** evaluated by the frozen runner.
4. CPU weighted-sum tops were **not** converted to weighted-mean percentage (`/236`).
5. The pack was **stopped before execution**; `results/final/packs/07_peak_analysis/` remains absent.
6. **No peak claim** is allowed under `experiment-freeze-v2` alone.

See `results/final/PEAK_ANALYSIS_BLOCKER.md`. Peak metrics for publication must come from
`final-peak-analysis-freeze-v1` consuming freeze-v2 NPZs without retraining.
