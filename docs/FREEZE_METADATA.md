# Freeze metadata policy (experiment-freeze-v1)

## Fields

| Field | Meaning |
|-------|---------|
| `implementation_commit` | Git commit that freezes pack protocol / runners / registries (logic). |
| `freeze_commit` | Same as `implementation_commit` (literal hash in config; not self-referential). |
| `freeze_tag` | `experiment-freeze-v1` |
| `freeze_tag_commit` | Resolved at runtime via `git rev-parse experiment-freeze-v1` (may be the metadata-only commit). |

## Procedure

1. Commit protocol logic: `experiments: freeze FGCS pack-based evaluation protocol v1`
2. Metadata-only commit sets `implementation_commit` / `freeze_commit` to that logic hash and `freeze_tag: experiment-freeze-v1`
3. Annotated tag `experiment-freeze-v1` points at the metadata commit
4. Pack manifests record all four fields; `freeze_tag_commit` is filled when packs run

No experimental logic changes are allowed in the metadata-only commit.
