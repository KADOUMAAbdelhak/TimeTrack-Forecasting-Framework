# TimeTrack Phase 2B-1 Corrected Deterministic Freeze Manifest

Freeze date: 2026-09-22 (Europe/Helsinki)

Branch: `main`

Pre-freeze HEAD: `0b4269270b0a121f0ba1e19355c6cd24b72abeb5`

Checkpoint tag to create: `phase2b1-corrected-deterministic-freeze-v1`

This checkpoint preserves the accepted, protocol-conforming deterministic
TimeTrack benchmark and the prospective matched-F0 correction. No benchmark
model, analysis result, raw dataset, or canonical dataset was regenerated while
creating this checkpoint.

## Frozen protocol and data identity

- Phase 2A freeze commit:
  `0b4269270b0a121f0ba1e19355c6cd24b72abeb5`
- Phase 2A freeze tag: `phase2a-benchmark-protocol-freeze-v1`
- Phase 2A frozen hash entries rechecked: 33/33 unchanged
- Canonical panel SHA-256:
  `c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`

Active raw datasets remained local, ignored, and unstaged:

| Path | SHA-256 |
|---|---|
| `data/raw/compute_dataset.csv` | `9204c25fe1079a18982f811131910d03f60d075aea29353f4198e434ecbe8904` |
| `data/raw/detailed_cpu_cores_dataset.csv` | `8630691e51d926269ebdc4f1df5c6848e2e879eafb67aa68958b5667713f708c` |
| `data/raw/disk_dataset.csv` | `2e4dcc1e2a79380dbba876422e42a6741a08da5cb55c15d29fb63a610d24aa6f` |
| `data/raw/network_dataset.csv` | `75ffdd7fc260010ad3a4549af3b3978eb1aa7657e5f992969b0c5a58e4fcf1d2` |
| `data/raw/packet-loss-dataset.csv` | `e586455adbb3561795ad6309c71ea3d8fb650251ec68c19c85ba08d2b4a5eb37` |
| `data/raw/throughputs_dataset.csv` | `22739d4527c56a15ba11ebf4090dc44138bc5549cea88d0eddc126a70053393f` |

## Original Phase 2B-1 deterministic execution

The original evidence and its audit are preserved under
`benchmark/phase2b1_original/`. The absolute F0 results are the original
deterministic benchmark results. The F1-F5 candidate configurations,
predictions, and metrics also remain the original valid candidate executions.

- Completed outer runs: 630
- Lead-level metric rows: 5,040
- Selected deterministic configurations: 420
- Prediction files: 630
- Stored validation status: PASS
- Persistence: 0 fitted models; 3.598026 s wall
- Ridge: 3,150 candidate fits; 210 final models; 7.857147 s wall
- LightGBM: 40,320 inner lead fits; 1,680 final lead models;
  26,982.400054 s wall
- Total original recorded wall time including analysis: 27,003.637989 s

The original contextual matched-F0 comparison reused independently trained
standalone F0 and restricted only its test predictions. Those nonconforming
comparison artifacts are retained for provenance and are not deleted,
overwritten, or relabelled as corrected results.

Original provenance identities:

- Compact inventory:
  `benchmark/phase2b1_original/COMPACT_ARTIFACT_SHA256.csv`
- Compact inventory SHA-256:
  `e7c3eaa3c92625ab8175131d14960eb6d8a77aea85b2aed864823734d6cc5f55`
- Original heavy inventory:
  `benchmark/phase2b1_original/HEAVY_ARTIFACT_SHA256.csv`
- Original heavy inventory SHA-256:
  `fb9a426089f65e97b2dd542de8cea078c905d08ae8a8eb7dabf06871425e4d62`
- Original heavy artifacts verified: 632/632 unchanged
- Original heavy bytes: 87,452,754
- Matched-F0 row audit SHA-256:
  `5f369d63e08add5e4a942890c3549083e722cfd04f9686f350c0684d13dcec52`

## Prospective matched-F0 correction semantics

The prospective decision was recorded before corrected results existed.

- Decision record:
  `benchmark/phase2b1_corrected/PROSPECTIVE_MATCHED_F0_DECISION.md`
- Decision record SHA-256:
  `72b5bf5b984c5eeb5b8d4b21b83f9b2fa9807f6fc944c79ee5edc89aeb33dd8e`
- Matched-support manifest SHA-256:
  `d5d9fcf14040a5b60794803bc054ffcc91418c0677073696a522ce4c220d0516`

For every F1-F5 contextual comparison, the corrected F0 comparator uses
exactly the candidate's inner-training, inner-validation, final outer-training,
and outer-test sample IDs. F0 configuration selection is independently
repeated on the exact matched inner supports using the frozen grid,
eight-lead mean validation-MAE objective, and frozen tie-breaking rule. The
selected matched F0 is then refit on the exact candidate outer-training rows
and evaluated once on the exact candidate outer-test rows.

Only these candidate-matched F0 comparators were newly selected and retrained.
No F1-F5 candidate was rerun, and standalone F0 results were not replaced.

## Corrected comparator execution and validation

- Exact-support preflight: PASS, 350/350 comparisons
- Corrected comparator runs: 350/350 completed, zero failed
- Ridge comparators: 175
- LightGBM comparators: 175
- Ridge: 2,625 inner fits; 175 final fits; 10.2 s wall
- LightGBM: 33,600 inner lead models; 1,400 final lead models;
  8,607.402822 s wall
- Analysis wall time: 3.2 s
- Validation wall time: 11.4 s
- Total corrected recorded wall time: 8,632.202822 s
- Corrected prediction files: 350
- Corrected lead-metric rows: 2,800
- Contextual candidate reruns: 0
- Support-hash failures: 0
- Candidate/F0 sample-ID mismatches: 0
- Candidate/F0 target mismatches: 0
- Maximum metric, Ridge-prediction, and gain recomputation differences: 0
- Corrected validation status: PASS

## Accepted corrected findings

Standalone F0 ranks `LightGBM > Ridge > Persistence` at every real lead.

For LightGBM F1 throughput, the corrected matched-F0 MAE-gain vector at leads
`[1, 2, 4, 8, 16, 32, 64, 128]` is:

`[+0.643, +0.592, +0.795, +1.010, +0.868, +0.643, +0.356, +0.848] %`

- Mean gain: +0.719%
- Positive machine-fold-lead cells: 72.9%
- Positive machine averages: 5/7 (`machine02`, `machine03`, `machine05`,
  `machine06`, `machine07`)
- Positive fold averages: 4/5 (folds 1, 2, 3, and 4)
- Ridge F1 remains negative.
- F2/F3 LOMO context remains broadly negative.
- F4/F5 combined context remains broadly negative.
- Context decision: **CONDITIONALLY_SUPPORTED**

## Retained ignored and temporary artifacts

Heavy files remain local and ignored; none is staged or deleted. Exact path,
byte size, and SHA-256 for every original heavy artifact are committed in
`benchmark/phase2b1_original/HEAVY_ARTIFACT_SHA256.csv`. That inventory covers
the two original metric parquet files and all 630 original prediction parquet
files.

Exact path, byte size, and SHA-256 for every corrected artifact are committed
in `benchmark/phase2b1_corrected/CORRECTION_ARTIFACT_SHA256.csv`:

- Inventory SHA-256:
  `daa408a710c2db7e4c1cb4199c0aa2b3bf30b550c7eb5aa64cda3ae983dd07db`
- Inventory entries verified: 1,070/1,070
- Total inventoried bytes: 60,611,263
- Ignored corrected parquet files: 354
- Ignored corrected parquet bytes: 55,588,065
- Retained temporary comparator checkpoints: 350 files, 2,011,105 bytes
- Retained temporary selection-progress records: 350 files, 1,647,997 bytes

The corrected parquet set comprises both matched-support manifests, the two
corrected metric parquet files, and all 350 corrected prediction parquet files.
The checkpoint and selection-progress directories are explicitly ignored and
are not staged. The committed inventory records every retained file exactly.

No DLinear or TCN scientific result exists, and neither model was executed for
this checkpoint. Phase 2B-2 was not started.
