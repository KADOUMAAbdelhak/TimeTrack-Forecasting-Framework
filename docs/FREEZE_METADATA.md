# Freeze metadata policy (experiment-freeze-v2)

## Recorded hashes

| Field | Value |
|-------|-------|
| implementation_commit | 9f1bebb5d5998aab24fbffe33b048fd16b8095a6 |
| freeze_commit | 9f1bebb5d5998aab24fbffe33b048fd16b8095a6 |
| freeze_tag | experiment-freeze-v2 |
| freeze_tag_commit | bb34ddfc52f5f54f47f0ca644d7c95c619ad95a7 (annotated tag target) |

experiment-freeze-v1 remains unchanged. Rejected v1 shared_tuning is archived under
results/development/rejected_final_pack_validation/experiment-freeze-v1/.

## v2 corrections

- Three-fold inner validation for shared tuning
- Separate ridge_cpu / ridge_memory
- DLinear train-only scaling + eligibility gate
- Complete manifest provenance + peak memory fields
