# STAGE 19I2 — Reproducibility portability cleanup

**Status: STAGE_19I2_PASS.** Public standard-library derived replay verified.
Repository `/Users/fgtek002/TimeTrack`; branch `paper/jss-review-revision`.
No scientific result, manuscript/supplement source, historical seal or I1
audit artifact changed. This stage creates portability code/documentation and
scratch validation only, not a model run or submission package.

## 1. Private CSV dependency replaced in the active replay path

`replay_derived.py` is the repository-local replacement. It uses only public
Python standard-library modules; no Node.js, `@oai/artifact-tool`, environment
symlink, installed third-party package or network access is required. The old
G1 exporter, inspection script and local symlink remain byte-identical as
historical evidence, are not used, and are excluded from proposed new staging.
Their recorded G1/I1 hashes were not rewritten to disguise a source change.

The CSV serializer preserves original column/row order and every cell lexeme,
including trailing zeros and scientific notation. It uses UTF-8 without BOM,
comma separation, doubled embedded quotes, quoting for comma/quote/CR/LF,
explicit LF record endings and a final LF. Bare CR quoting is tested explicitly;
it is an important difference from a default Python writer configured only
with an LF terminator. No conversion through floating-point spreadsheet cells.

| Existing authoritative G1 table | Rows × columns | Regenerated SHA-256 | Result |
|---|---:|---|---|
| `m1_s2_robustness_24.csv` | 24 × 6 | `8b085b0279bb02422ab3c84bc48a7044e0b0f1f8dfff48a4a56881910da6f9c0` | Byte-identical |
| `seed_sensitivity_48.csv` | 48 × 9 | `d32061414cd18bed523d3851f833c534d8b43235e6651be4410f0e9806f1f363` | Byte-identical |
| `timetrack_memory_attribution.csv` | 47 × 10 | `903ec0ecf0c9e98398d52dc4f1a99557efa92382fb24639744c4a65d209be95d` | Byte-identical |

All three authoritative CSVs were read, never overwritten. Robustness and seed
tables are independently projected from the existing C1 endpoints and checked
against both the G1 payload and existing CSVs. The sole unit conversion follows
the existing fixed decimal fraction-to-percent convention; no ratios, gains,
medians, ranges, SDs, fits or seed outcomes are newly estimated.

## 2. Safe derived-only entry point

From the repository root:

```sh
python3 -I -S -B review_revision/stage19i2_portability/replay_derived.py --output-dir /absolute/path/to/new-scratch
```

The parent must exist and the destination must be new/empty and outside the
source tree. Existing non-empty output directories, output symlinks and input
symlink escapes are rejected. Every scratch file uses exclusive creation; no
overwrite option exists. All hash/schema/expected-byte comparisons finish
before output writes begin. Source hashes are rechecked after completion.

`replay_sources.json` records 11 compact source inputs. Its SHA-256
`97fe4f8930f00604d2ada85f625dd7ff9b7017467d716b5e2ed875de7d6a5dad`
is pinned in the new replay code. All 11 inputs are included in the refreshed
candidate tree. No Git command, historical HEAD check, model import, prediction,
raw-data read or historical runner invocation occurs in the replay.

Besides the three G1 CSVs, the replay produces:

- Two supplement row fragments generated from the exact source numbers and
  existing six-decimal display convention; both are **byte-identical to the
  current supplement row bodies**. Fragment hashes are
  `b3095589b871ce5a9a5f8bb69fb6b655c7311562bcc8e927c82a5089fb87081e`
  and `2a333d6892504bad105fe314be937140ebb5898295f06d74325be1de3da7abd9`.
- Byte-identical reserialization of existing C1 contextual/sharing CSVs.
- A selected diagnostic JSON extract from existing G1/H1 summaries. Numeric
  lexemes are explicitly retained as strings; it is a new labelled projection,
  not a byte-copy of the entire original JSON, nor a rerun of the saved-artifact
  audits. Existing attribution/capacity/scale values are not recalculated.
- New verification metadata: source/output hashes, existing row counts and
  counts of existing sign-flip flags (9 S2:S1 and 4 M1:S2). Runtime identity is
  metadata and may differ across interpreters; the eight scientific/presentation
  output files are byte-identical across the verified runtimes.

No semantic-only CSV fallback was needed. Source decimal strings, parsed tables
and serialized bytes match exactly. Scratch TeX fragments are not a manuscript
edit, new supplementary document or PDF build.

## 3. Public environment and README

Created `README.md`, `ENVIRONMENT.md`, `environment.json` and
`requirements-derived.txt` (comments only; no pip dependencies). Required
runtime: public CPython >=3.9. Verified here: **3.9.6 and 3.12.14**, each with
`-I -S -B` so no user/site package or Python-path injection is needed.

Documentation distinguishes:

- **A — Inspect:** original frozen results, completed controls and compact
  C1/G1/H1 endpoints, without substituting diagnostics for primary estimates.
- **B — Derived replay:** the new 11-input standard-library path; no models,
  raw archives, private package or `.git` directory is required.
- **C — Full saved-artifact audit:** separately restored immutable models,
  predictions, per-fit records and original inventories are still required.
  H1's native-training-partition recheck also needs the original Materna ZIP.
  Git alone does not provide these collections. Raw third-party data remain
  sourced upstream under their separate terms.

Historical Ridge package versions and current installed full-audit metadata
are identified as metadata, not a training lock or Level-B requirement.
Optional LaTeX/Matplotlib and full-audit NumPy/pandas/PyArrow/torch needs are
separate. No cross-platform bitwise training-reproducibility claim is made.

## 4. Verification

`test_replay.py`: **25/25 tests pass on each of two runtimes** (50 executed
test cases). Cases cover quote/CR/LF/UTF-8/empty cells and numeric lexemes,
ordered serialization, strict standard-library imports, overwrite refusal,
hash/manifest tampering, missing sources, symlink escape/refusal, determinism,
supplement fragments and fail-closed behaviour even under Python `-O`.

A disposable compact checkout containing only the pinned inputs, replay code
and manifest succeeds with **no `.git`, environment, raw data or model files**;
a fixture with an unrelated simulated HEAD also succeeds. Source bytes are
compared before/after in that fixture. Replays also succeed from an unrelated
working directory. Two fresh full replays under the verified interpreters have
identical hashes for all eight scientific/presentation outputs. Evidence is
in `validation_results.json` and `validation/` (test logs/check metadata only;
no duplicate model/data collection).

The full protected-tree audit rechecks **443,484 pre-existing files/symlinks**,
**33,337,571,391 bytes**, including every original/post-hoc/manuscript file and
all I1 report/inventory/plan files. All remain unchanged. Git branch, refs,
index and tracked status remain unchanged; existing user-owned modifications
are preserved. No historical seal or historical script was patched.

## 5. Historical seals and checkpoint successor

The README identifies the common-context/H129/Ridge runners, their analysis
entry points, C1 synthesis commands and G1/H1 report/audit scripts that enforce
historical refs/clean-tree assumptions or write original output paths. Do not
rerun them casually at a new HEAD or regenerate over audited reports. Their
guards, configs, source seals, failure history and original paths are intact.

The refreshed **I1-successor** plan is in `checkpoint_candidate/`; I1 remains
an immutable historical audit, so its old plan is not silently overwritten.

- Candidate commit delta: **8,598 paths** = previous 8,572 − 2 retired private
  scripts + 28 portability/compact audit files.
- Proposed resulting tree: **10,578 paths**; still 11 pre-existing tracked
  modifications and no proposed deletion. All 11 compact replay inputs are
  included; 21 pre-existing ignored Parquets still require explicit approval
  for a later per-file override.
- Exact include/delta/tree/ignore-override lists, regenerated full exclusion
  ledger and compact exclusion digest/summary are provided. The large full
  exclusion ledger is deliberately not a normal-Git candidate.
- Proposed tag remains `jss-review-robustness-reproducibility-v1`; no tag exists
  or is created by this stage. No staging, commit or push occurred.

## 6. Remaining USER_ACTION and scope

Level-B private-dependency and historical-HEAD obstacles are resolved for the
new compact replay. Remaining decisions are those not authorised here:
approve code licence/rights-holder scope and CAS obligations; decide rights,
hosting/access and restoration for a full Level-C companion archive; approve
the final candidate commit/tag/publication and only then update Data
Availability. A hermetic historical training environment is not supplied or
claimed. No scientific rerun is needed for the deterministic table path.

Scientific-result modifications=0; manuscript/supplement modifications=0;
training=0; inference=0; historical-seal changes=0; licence files=0; dataset
redistribution=0; declaration/submission-package changes=0.

Commit=no; tag=no; push=no.

STAGE_19I2_PASS
