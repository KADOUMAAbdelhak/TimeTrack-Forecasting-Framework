# Reproduce compact manuscript evidence

This is the current **derived-only** replay path. It supersedes the private G1
CSV-export workflow, not the historical experiment runners or their seals.
No training, inference, raw-data access, Git operation or third-party Python
package is used. A byte-preserving checkout of the compact inputs is required;
automatic newline conversion must not change the recorded source bytes.

## A. Inspect published/frozen results

- Original TimeTrack: `multiresource/04_lstm_factorial/outputs/scientific/comparisons/`.
- Original fastStorage/Rnd: `independent_validation/05_bitbrains_factorial/outputs/scientific_v2/analysis/` and `comparisons/`.
- Original Materna: `independent_validation/06_materna_replication/outputs/scientific_v1/analysis/` and `comparisons/`.
- Post-hoc endpoints: `review_revision/experiments/{s2_common_context,m1_capacity_matched,ar_arx_baseline}/posthoc_results.csv`.
- Robustness/seed/context/sharing endpoints: `review_revision/stage18c1_evidence/`.
- Final exact tables: `review_revision/stage19g1_evidence/`; scale context: `review_revision/stage19h1_scale_context/analysis.json`.

Frozen primary results and post-hoc endpoints remain distinct. The 24-cell
robustness table uses seed-mean entity×fold×lead cells, not a new estimand.
Seed “stable” means no sign flip across the three recorded seeds, not stable
magnitude. Source files, scientific definitions and manuscript are not edited.

## B. Replay derived tables from compact saved endpoints

From the repository root, with public CPython 3.9 or newer:

```sh
python3 -I -S -B review_revision/stage19i2_portability/replay_derived.py --output-dir /absolute/path/to/new-scratch
```

The destination must be **new or empty and outside the source tree**; its parent
must exist. Existing non-empty destinations and output symlinks are refused.
No overwrite flag exists. The script locates the source root relative to itself;
`--repo-root /path/to/compact-checkout` is available for an isolated input tree.
It requires no `.git` directory, historical HEAD, network, Node.js, environment
symlink, model weights or predictions. `-I -S -B` disables user/site packages,
Python-path injection and bytecode writes. No pip install is needed.

`replay_sources.json` lists the 11 compact inputs and their exact SHA-256 values.
All 11 are in the proposed checkpoint allowlist; new files remain uncommitted
until a separately authorised checkpoint is created.
The manifest's digest is pinned in the replay code. Every input is verified
before any output is written. Do not refresh a failed hash check automatically;
investigate the source/version difference and explicitly review any successor.

Outputs in scratch only:

| Output | Operation and comparison |
|---|---|
| `m1_s2_robustness_24.csv` | Project the existing C1 M1:S2 rows; copy source numeric lexemes, convert stored win fraction to percent using the original fixed decimal convention; compare with G1 payload and authoritative CSV bytes |
| `seed_sensitivity_48.csv` | Project existing seed gains, range and population SD; map the existing Boolean sign-flip flag; no range/SD/seed recalculation |
| `timetrack_memory_attribution.csv` | Serialize the existing exact G1 payload; no new concentration calculation |
| `m1_s2_robustness_rows.tex`, `seed_sensitivity_rows.tex` | Format the existing table values, retaining full numeric lexemes; byte-compare with the current supplement row bodies; these are fragments, not a manuscript rebuild |
| `sharing_sensitivity.csv`, `contextual_evidence.csv` | Deterministically reserialize the existing C1 endpoints and compare bytes, without recomputing gains |
| `diagnostic_extract.json` | Select existing G1 attribution/capacity and H1 scale-summary fields; retain source JSON numeric lexemes as strings, explicitly labelled; no full saved-artifact check is rerun |
| `replay_checks.json` | Newly generated source/output hashes, exactness checks, row counts and counts of existing seed flags; runtime identity is metadata, not a scientific result |

The CSV contract is UTF-8 without BOM, original column/row order, comma
delimiter, doubled embedded quotes, quoting for comma/quote/CR/LF, LF record
endings and a final LF. Numeric text is not normalised. All three G1 CSVs match
byte-for-byte; no semantic-only fallback is used. Display rounding in the TeX
fragments follows the existing six-decimal supplement convention.

Run the public standard-library tests:

```sh
python3 -I -S -B review_revision/stage19i2_portability/test_replay.py
```

The tests make disposable compact checkouts and scratch destinations, including
no-Git/unrelated-HEAD fixtures, hash tampering, overwrite refusal and CSV edge
cases. See `ENVIRONMENT.md` for tested runtimes and the limits of the claim.

## C. Full saved-artifact audit

Git alone does **not** supply the full model/prediction/per-fit journal archive.
For full source-to-metric/scaler/inverse-map audits, restore the separately
preserved immutable artifacts to their recorded relative paths and verify their
original inventories. This audit has not created or published such an archive.
H1's raw-training-partition recheck also requires the original Materna ZIP.
Third-party raw data must be obtained upstream under source-specific terms:
TimeTrack's recorded Kaggle/Zenodo releases, GWA-T-12 Bitbrains and GWA-T-13
Materna. A code licence or a checksum is not data redistribution permission.

Level B reuses the already audited compact diagnostics. It does not rerun C1/G1/H1
from predictions, reconstruct native training partitions, refit models or establish
cross-platform bitwise training reproducibility.

## Historical scripts: preserve, do not casually rerun

| Historical entry point | Intentional boundary |
|---|---|
| `experiments/s2_common_context/run_control.py` | Original refs, source/config seals, completion journals and fixed output locations |
| `experiments/m1_capacity_matched/run_capacity_control.py` | Recorded manuscript/scientific parent HEADs, sealed source/plans and original output tree |
| `experiments/ar_arx_baseline/run_linear_control.py` | Original HEAD/parent, successor recovery seals, one-test evaluation and fixed artifacts |
| The three `analyse_*control.py` entry points | Historical seal/preservation gates; rerunning can overwrite audited reports, metric endpoints and inventories |
| `stage18c1_evidence/audit_synthesis.py`, its report builders and G1/H1 evidence scripts | Some commands require original HEAD/clean tree or full archives; builders write original evidence/report paths |
| `stage19g1_evidence/export_tables.mjs`, `inspect_artifact_api.mjs`, `node_modules` symlink | Retired private/local tooling; not needed by Level B, excluded from the refreshed candidate additions; historical evidence remains untouched |

Paths in this table are relative to `review_revision/`. No historical guard,
source/config seal, journal, report or output path was weakened or rewritten.

## Checkpoint planning

`checkpoint_candidate/` is the current successor to the **historical I1 plan**;
the I1 audit and its inventory remain byte-identical. The successor adds this
portable path and removes the two retired private-tool scripts from proposed
new staging. Nothing has been staged/committed/tagged/pushed. Licence approval,
rights/hosting for full saved artifacts, CAS obligations and final checkpoint
publication remain separate USER_ACTION decisions. No licence or submission
file is created by Level B.
