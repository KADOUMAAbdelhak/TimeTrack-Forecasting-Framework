# Freeze metadata policy (experiment-freeze-v1)

## Recorded hashes

| Field | Value |
|-------|-------|
| `implementation_commit` | `5d145354147d03548babcc43994defc03a9a7f78` |
| `freeze_commit` | `5d145354147d03548babcc43994defc03a9a7f78` |
| `freeze_tag` | `experiment-freeze-v1` |
| `freeze_tag_commit` | resolved at runtime from the annotated tag (metadata commit) |

## Fields

| Field | Meaning |
|-------|---------|
| `implementation_commit` | Git commit that freezes pack protocol / runners / registries (logic). |
| `freeze_commit` | Same as `implementation_commit` (literal hash in config; not self-referential). |
| `freeze_tag` | `experiment-freeze-v1` |
| `freeze_tag_commit` | Resolved at runtime via `git rev-parse experiment-freeze-v1` (metadata-only commit). |

## Procedure

1. Protocol logic commit: `experiments: freeze FGCS pack-based evaluation protocol v1` → `5d145354147d03548babcc43994defc03a9a7f78`
2. Metadata-only commit sets the hashes above and `freeze_tag: experiment-freeze-v1`
3. Annotated tag `experiment-freeze-v1` points at the metadata commit
4. Pack manifests record all four fields; `freeze_tag_commit` is filled when packs run

No experimental logic changes are allowed in the metadata-only commit.
