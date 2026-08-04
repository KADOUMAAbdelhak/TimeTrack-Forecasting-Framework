# Pre-Freeze Status (pack redesign)

Verified: 2026-08-04

## Decision

**Do not freeze the monolithic 34.6 CPU-hour plan.**  
Default final execution is **manual packs** (`configs/final_fgcs_packs.yaml`).  
`configs/final_fgcs_full.yaml` is preserved as `optional_extended` / `default_execution: false`.

## Compute reduction

| Item | Old | New |
|------|-----|-----|
| Required HPO trials | 16,992 | **16** |
| Per-series nested Optuna | yes | **removed** |
| LSTM in required packs | yes | **optional only** |
| DLinear HPO | yes | **fixed development config** |
| Longest required pack | n/a (monolith) | **≪45 min** (proj ~3–12 min) |

## Dry-run gates

| Gate | Status |
|------|--------|
| Tests | 79 passed (pre-commit of this phase; re-verify before freeze) |
| Pack list | OK |
| shared_tuning smoke | **complete** (~35–48 s) |
| Resume / partial recovery | **OK** |
| Aggregator rejection | **OK** (refuses incomplete required packs) |
| Required pack >45 min | **none** |

## Remaining before freeze tag

1. Commit + push pack redesign.
2. Re-run full tests on clean tree.
3. Confirm no required pack projects >45 min (`docs/FINAL_PACK_RUNTIME_PLAN.md`).
4. Then freeze **implementation + pack definitions only** (not experiment outputs).
5. User launches packs manually, one per session.
