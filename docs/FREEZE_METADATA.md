# Freeze metadata policy (experiment-freeze-v2)

## Active freeze

| Field | Value |
|-------|-------|
| Tag | `experiment-freeze-v2` |
| Supersedes | `experiment-freeze-v1` (unchanged; rejected shared_tuning archived) |

## Fields

| Field | Meaning |
|-------|---------|
| `implementation_commit` | Protocol logic commit for v2 |
| `freeze_commit` | Same as implementation_commit |
| `freeze_tag` | `experiment-freeze-v2` |
| `freeze_tag_commit` | Resolved via `git rev-parse experiment-freeze-v2` (metadata commit) |

## v2 corrections vs v1

- Three-fold inner validation for shared tuning
- Separate `ridge_cpu` / `ridge_memory`
- DLinear train-only scaling + eligibility gate
- Complete manifest provenance + peak memory fields
