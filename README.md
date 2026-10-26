# TimeTrack forecasting research: reproducibility checkpoint

This repository supports inspection of the frozen original S1/S2/M1 results,
the completed post-hoc controls, and compact derived replay of manuscript-facing
robustness and seed tables. The controls/diagnostics supplement, rather than
replace, the frozen primary results.

## Three reproducibility levels

**A — Inspect results.** Original comparison tables and protocols are under
`multiresource/04_lstm_factorial/` and
`independent_validation/{05_bitbrains_factorial,06_materna_replication}/`.
The current post-hoc endpoints are the `posthoc_results.csv` files under
`review_revision/experiments/{s2_common_context,m1_capacity_matched,ar_arx_baseline}/`.
Robustness, seed and final diagnostic evidence is under
`review_revision/stage18c1_evidence/`, `stage19g1_evidence/` and
`stage19h1_scale_context/`.

**B — Compact derived replay.** Use public Python 3.9 or newer, standard library
only. No private package, Node.js, raw data, model weights, inference or
historical Git HEAD is required:

```sh
python3 -I -S -B review_revision/stage19i2_portability/replay_derived.py --output-dir /absolute/path/to/new-scratch
```

The scratch parent must exist. The destination must be new/empty and outside
the source checkout; existing artifacts are never overwritten. Source hashes
are checked before use. The three G1 CSVs and two supplement row fragments
regenerate byte-for-byte from the saved compact endpoints. See
[the replay guide](review_revision/stage19i2_portability/README.md) and
[environment documentation](review_revision/stage19i2_portability/ENVIRONMENT.md)
for exact inputs, outputs, tests and historical-script boundaries. The replay
does not recompute original model predictions or claim bitwise cross-platform
training reproducibility.

**C — Full saved-artifact audit.** Full fitted-model, per-fit-prediction and
execution-journal audits require separately preserved immutable artifacts that
are **not included in Git**. SHA-256 inventories identify those artifacts;
they are not download links and do not supply the files. No public companion
archive or DOI is promised. Third-party raw datasets must be obtained from
their upstream sources and verified against recorded hashes. Source terms
remain applicable to copies and derivatives; see `NOTICE`.

## Licence boundaries

Only the original research source files identified in
`PROJECT_AUTHORED_CODE.txt` are licensed under Apache-2.0. Read
[LICENSE_SCOPE.md](LICENSE_SCOPE.md), [LICENSE](LICENSE) and [NOTICE](NOTICE).
Datasets, Elsevier CAS files, publication material, dependencies and uncertain
legacy/imported code are not relicensed by this code grant. No ownership names
are invented, and original third-party notices are retained.

## Checkpoint identity and history

The lean release is identified by the annotated tag
`jss-review-robustness-reproducibility-v1`. Use the tag's full commit SHA when
citing a particular checkout. The original scientific checkpoint and all
historical execution seals remain unchanged. Historical audit reports and
candidate plans describe their state at the time; their old HEADs, pending
decisions and pre-release statements are not rewritten retrospectively.

The current public entry point is this README and the portable Level-B replay,
not retired private CSV tools or historical training/analysis commands. The
release uses the audited Stage 19I2 candidate plus the five licence/scope and
front-page files. Git's commit/tree supplies the exact public file set; the
final post-publication receipt is reported separately, after its commit SHA
and remote visibility exist. Large local artifacts, raw copies, environments,
caches, private dependencies and unrelated local material are not added to
this lean checkpoint.
