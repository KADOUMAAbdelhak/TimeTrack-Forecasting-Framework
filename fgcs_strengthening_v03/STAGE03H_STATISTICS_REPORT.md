# Stage 3H registered statistics and synthesis

Implemented the analysis layer for `review_revision/fgcs_strengthening/analysis_plan_v0.3.md`. The protocol and configuration SHA-256 values remain `7b8f80be597148f5413582bf936d13a79bfc05d0725d734dfec83b5443246076` and `59cda69a3e9b6b789aa09f70d2c606fce41a5d4b37d5a1d8dfe0a9b819cff62b`. No protocol deviation was identified.

## Files

- `src/statistics/endpoints.py` implements complete-grid native MAE aggregation, log ratios, interaction-like effects, matched Materna aggregation and native descriptive summaries.
- `src/statistics/bootstrap.py` implements the fixed cluster draw bank, centred tests and linear percentile intervals. `src/statistics/mechanism.py` implements average-rank Spearman and undefined-replicate handling.
- `src/statistics/design.py` enumerates the registered tests and descriptive slices. `src/statistics/multiplicity.py` implements Holm and BH. `src/statistics/schema.py` requires provenance and serialises zero and unavailable outcomes explicitly.
- `src/statistics/synthesis.py` assembles model, mechanism, intervention, F/Q and persistence rows. `analyse_study.py` provides dry planning, validation and explicit manifest-driven input.
- Added the ten requested test modules and `tests/statistics_fixtures.py` for generated cells and provenance.

## Endpoints and missingness

For each model, entity and resource, A first averages native MAE equally across prescribed horizons within each fold, then across folds within each seed, then across the exact registered seeds. D is ln(A_candidate/A_reference), with positive values indicating higher candidate error. I is D(M1:S2) − D(M0:S1), with positive values indicating the larger operational sharing penalty under all-input sharing. All interaction terms use the same entity, seed slice, folds, horizons, support, scaler and context. Materna first calculates each VM's three trace effects and averages those logs within that VM. Its native MacroMAEs remain trace-specific. TimeTrack reports descriptive entity and cohort effects without p-values or intervals.

Zero MAE cells contribute to A. Zero candidate aggregate alone gives ratio 0 and log −∞. Zero reference aggregate alone gives ratio +∞ and log +∞. Both zero yield an undefined ratio and log. The row records exact zero categories, missing or failed cells, and available native aggregates and differences. Any unavailable entity log prevents the registered group effect and leaves raw and adjusted p=1. No complete-case subset is used. The code keeps mismatched native values visible individually while withholding paired comparisons on incompatible support.

Persistence has its own deterministic seedless reference. R_persist is exp(mean of entity log model/persistence ratios) on the complete positive matched grid. Zero persistence aggregates are counted and the ratio remains undefined. Equal-entity native MacroMAE and its descriptive gain are retained separately.

## Bootstrap and fixed tests

A single NumPy PCG64 stream seeded with 20261110 generates the three read-only 10,000×35 index matrices in fastStorage, Rnd and Materna order. Every eligible resource, contrast and association reuses its group's exact matrix. Materna draws carry all three traces with a VM. Folds, horizons and seeds remain within the entity. The estimate is the arithmetic mean of entity logs. Intervals use linear 2.5/97.5 percentiles and exponentiated endpoints are reported for ratios. The two-sided centred p-value uses (1 + count(|replicate − point| ≥ |point|))/10001, including exact equality. These are approximate cluster-bootstrap tests with marginal intervals at n=35.

| Correction | Family | Slots |
| --- | --- | ---: |
| Holm | Primary sharing and interaction | 24 |
| Holm | Gradient association | 12 |
| Holm | PCGrad | 8 |
| Holm | GradNorm | 8 |
| Holm | Task-selected checkpoint | 8 |
| BH | Eight registered transfer F matrices | 96 |
| **Total** | | **156** |

Primary includes nine positive sharing predictions for throughput, memory and disk, three nondirectional CPU comparisons and twelve nondirectional interaction contrasts. Adjustments use raw p ascending and lexicographic test ID at ties, preserving each fixed family. Decisions require adjusted p<.05. Predicted-direction support additionally requires the prescribed sign. Q remains descriptive with percentile intervals. The dry catalogue has 832 rows including 156 inferential and 676 descriptive rows. The descriptive rows comprise 256 D, 48 Q and 372 persistence rows.

## Synthesis semantics

Gradient association uses complete final-slot M1 K and matched M1:S2 D. A constant original variable makes the test unavailable. Each constant-variable replicate contributes an exceedance, and any undefined replicate suppresses the numeric interval. The undefined count is retained. PCGrad, GradNorm and task-specific checkpoints compare against the exact seeds 0–2 slice of equal-loss M1 for fastStorage and Rnd. Negative D indicates improved error.

The transfer layer reuses the Stage 3E F/Q identity and estimand functions. F is ln(A_independent/A_shared-subset) and Q is ln(A_shared-without-source/A_full-shared). The twelve directed entries per matrix carry source, target, scope and subset. Positive F favours sharing. Positive Q favours adding the omitted supervision in the operational comparison. Only F enters BH.

Descriptive D rows cover contextual inputs, both sharing comparisons, H128 M0, historical H129 and common-context S2, Ridge, LightGBM and all three modern families. Historical context exceptions require exact matched test origins and remain separate from the five-seed study. Ridge has a seedless deterministic slice, LightGBM has only seed 0, and modern comparisons use only their first-ten V2 cohorts and seed 0. No inferential family is assigned to these descriptive comparisons.

## Analytical examples and runner

Generated examples verified A=11.8 from fold + horizon + seed cells and D=ln(5.9) against A=2, I=ln(2) from sharing ratios 4 and 2, and Materna averaging to ln(4) from within-VM ratios 2, 4 and 8. An exact-tie centred test with point 2 and replicates [0,1,4,6] gives 4/5. The rank example [1,2,2,4] versus [1,2,3,4] gives Spearman √0.9. A persistence cohort with one ratio 4 and 34 ratios 1 yields 4^(1/35). F and Q synthetic tests independently recover ln(2), with a test result and adjusted p-value only for F.

```sh
old_fgcs_rejected/.venv_legacy/bin/python -B -m fgcs_strengthening_v03.analyse_study --dry-run
old_fgcs_rejected/.venv_legacy/bin/python -B -m fgcs_strengthening_v03.analyse_study --enumerate
old_fgcs_rejected/.venv_legacy/bin/python -B -m fgcs_strengthening_v03.analyse_study --validate path/to/manifest.json
old_fgcs_rejected/.venv_legacy/bin/python -B -m fgcs_strengthening_v03.analyse_study --synthetic-input path/to/generated-manifest.json
```

The runner reads only explicitly supplied manifests. The manifest carries mode, protocol/config hashes, source/input hash maps and SHA-256 references to two JSON Lines tables, `cells` and `diagnostics`. Cells use the `Cell` schema and a canonical test-support hash and ordered-test-ID hash across compatible arms. For later scientific execution the explicit `--scientific-input` entry verifies the repository seal, table hashes, complete registered coordinates, exact v0.3 identities, frozen contexts, and evidence artifact hashes. Missing or failed scientific work is represented by explicit cell status or null diagnostic markers. The combined code/input seal covers 36 inputs and 51 sources with digest `6060afc66d49184c868cad8521cc1c5fa0a5dbe387131a4c2e2be7889d715bf5`.

## Tests and preservation

```sh
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  old_fgcs_rejected/.venv_legacy/bin/python -B -m unittest discover -s fgcs_strengthening_v03/tests
```

**124 tests passed in 57.576 seconds**, including 27 Stage 3H tests and 97 Stage 3A–3G regression tests. Static compilation and whitespace checks passed. The before/after preservation inventory matched for 449,563 entries outside the implementation namespace on path, mode, size, modification time and change time. Both inventories had SHA-256 `d05c4bf4e0936fbf15615876570b30697ff4bd5ecb74aa2338cc650d16c791b4`. Tracked-file status was identical and no test runtime journal remained. Stage 3H used generated result tables only. Existing Stage 3A adapter conformance tests read frozen support/scaler inputs without running models on them. The manuscript, supplement, submission files, protocol and historical artifacts were preserved. No scientific training, inference, diagnostics, pilots or final analyses ran. No dependencies were installed or downloaded. No staging, commit, tag or push occurred.

**Wall-clock start:** `2026-11-11T15:29:32+02:00` (first repository check). **End:** `2026-11-12T12:58:09+02:00` (report finalisation). **Elapsed:** 21 h 28 min 37 s, including the overnight interval.

## Stage 3I handoff

No implementation blocker for Stage 3I. Scientific synthesis awaits an explicitly supplied, validated normalised artifact manifest.

STAGE03H_PASS
