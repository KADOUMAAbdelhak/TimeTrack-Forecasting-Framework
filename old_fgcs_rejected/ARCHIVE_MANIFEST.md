# Archive Manifest — Rejected FGCS / Computer Networks Study

- **Archival date:** 2026-09-21
- **Branch:** `main`
- **Original HEAD commit:** `b0154ce7affbce5ff47fb2164f2df2b4a7c0eb4c`
- **Remote tip at archival:** `main` tracking `origin/main` (clean relative to tracked files except untracked FGCS submission artifacts)

## Purpose of this directory

This directory archives the implementation, experiments, frozen results, documentation, and manuscript artifacts associated with the rejected **FGCS / Computer Networks** hierarchy-reconciliation study.

**Old manuscript title:**

> Hierarchy-Aware Forecast Reconciliation for Multi-Level Cloud Telemetry: Accuracy Gains, Trade-offs, and Failure Boundaries

The repository was reset because the next TimeTrack forecasting study will be redesigned independently from the previous **per-metric univariate forecasting + hierarchical reconciliation** architecture. Original TimeTrack raw datasets remain active under `data/raw/` as the scientific starting point.

## Existing freeze tags (preserved in git; not deleted)

- `experiment-freeze-v1`
- `experiment-freeze-v2`
- `final-analysis-freeze-v1`
- `final-peak-analysis-freeze-v1`
- `final-reporting-freeze-v1`
- `final-reporting-freeze-v2`
- `final-robustness-analysis-freeze-v1`
- `final-robustness-analysis-freeze-v2`
- `final-robustness-extension-freeze-v1`
- `final-robustness-extension-freeze-v2`

## Active raw datasets retained at `data/raw/` (pre-move verification)

Root-level CSV copies were verified **byte-identical** and **same-inode hardlinks** (`nlink=2`) to `data/raw/` before archival. Root copies were then moved to `old_fgcs_rejected/root_dataset_duplicates/` (hardlink rename; active `data/raw/` retained).

| File | Size (bytes) | Rows | Cols | Timestamp range | SHA-256 | inode |
|------|-------------:|-----:|-----:|-----------------|---------|------:|
| `compute_dataset.csv` | 26942966 | 41362 | 56 | 2024-06-24 13:37:06.164306 → 2024-07-19 16:27:05.246403 | `9204c25fe1079a18982f811131910d03f60d075aea29353f4198e434ecbe8904` | 43767063 |
| `detailed_cpu_cores_dataset.csv` | 331354469 | 41362 | 473 | 2024-06-24 13:37:06.164306 → 2024-07-19 16:27:05.246403 | `8630691e51d926269ebdc4f1df5c6848e2e879eafb67aa68958b5667713f708c` | 43767064 |
| `disk_dataset.csv` | 8425241 | 41362 | 15 | 2024-06-24 13:37:06.164306 → 2024-07-19 16:27:05.246403 | `2e4dcc1e2a79380dbba876422e42a6741a08da5cb55c15d29fb63a610d24aa6f` | 43767068 |
| `network_dataset.csv` | 2932318 | 41356 | 6 | 2024-06-24 13:37:06.164306 → 2024-07-19 16:27:05.246403 | `75ffdd7fc260010ad3a4549af3b3978eb1aa7657e5f992969b0c5a58e4fcf1d2` | 43767069 |
| `packet-loss-dataset.csv` | 12389830 | 41362 | 91 | 2024-06-24 13:37:06.164306 → 2024-07-19 16:27:05.246403 | `e586455adbb3561795ad6309c71ea3d8fb650251ec68c19c85ba08d2b4a5eb37` | 43767070 |
| `throughputs_dataset.csv` | 40993889 | 41362 | 91 | 2024-06-24 13:37:06.164306 → 2024-07-19 16:27:05.246403 | `22739d4527c56a15ba11ebf4090dc44138bc5549cea88d0eddc126a70053393f` | 43767071 |

## Hardlink note

Pre-move: each of the six CSVs existed as two directory entries (repository root and `data/raw/`) sharing one inode. Archival moved only the root directory entries into `root_dataset_duplicates/`; content bytes were not rewritten.

## Hardlink materialization (dataset safety)

After the initial archival move, `data/raw/*.csv` and `old_fgcs_rejected/root_dataset_duplicates/*.csv` still shared the same inodes (`nlink=2`). On **2026-09-21**, the archive-side hardlinks were broken by materializing **independent byte-identical copies** at `old_fgcs_rejected/root_dataset_duplicates/` only. Active `data/raw/*.csv` files were not rewritten. Post-materialization: SHA-256 digests remain identical to the table above; active and archive pairs now have **different inodes** and `nlink=1`.

## What was archived (moved, not deleted)

Implementation and study assets moved into this directory include, when present:

- `fgcs/` (manuscript, EM anonymous package, submission artifacts)
- `results/` (pilot / development / final frozen evidence)
- `timetrack/`, `models/`, `experiments/`, `scripts/`, `configs/`, `tests/`, `docs/`
- `evaluation/`, `features/`, `preprocessing/`, `notebooks/`
- `data/interim/`, `data/processed/` (empty legacy placeholders)
- `requirements.txt`, `README.md`
- root duplicate CSVs → `root_dataset_duplicates/`
- `.venv/` → `.venv_legacy/`
- `.pytest_cache/` and archival probe JSON

## Explicit non-goals of this archival phase

- No deletion of scientific code, results, manuscripts, or git tags
- No new forecasting framework created
- Active raw datasets under `data/raw/` remain the scientific starting point and are not tracked by git

