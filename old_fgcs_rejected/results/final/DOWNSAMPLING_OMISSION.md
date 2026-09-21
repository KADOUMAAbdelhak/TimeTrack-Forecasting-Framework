# Downsampling pack — omitted before execution

## Status

**NOT EXECUTED / SCIENTIFICALLY BLOCKED** under `experiment-freeze-v2`.

No final downsampling artifacts exist. No manuscript claim about telemetry
resolution or five-minute aggregation is allowed from this freeze.

## Blocker description

The frozen final pack path for `downsampling` does **not** perform actual
series aggregation. For `factor > 1` it would fit **native-resolution** windows
with native horizon/context and only **relabel** metadata as a coarse
resolution. Executing the pack would produce scientifically invalid
native-vs-coarse comparisons.

## Affected files / functions

| Path | Role |
|------|------|
| `configs/final_fgcs_packs.yaml` (`id: downsampling`) | Declares targets, factors `[1, 7]`, models, horizons, fold0 |
| `experiments/pack_runner.py` → `run_downsampling` | Enumerates jobs; computes shared kwargs but does not pass them |
| `experiments/final_supporting_analyses.py` → `downsampling_eval_row` | Smoke helper: native fit + relabeled horizon/context |
| `experiments/final_supporting_analyses.py` → `downsample_series` | Defined but **not called** from `downsampling_eval_row` |
| `scripts/run_downsampling_dev.py` | Real aggregation exists for **development** only (claim-ineligible) |
| `docs/DOWNSAMPLING_PROTOCOL.md` | Documents intended protocol (not wired into frozen pack path) |

## Frozen intended matrix (config)

- Targets: `cluster_UM`, `cluster_CU_weighted_mean`
- Factors: `1` (native), `7` (~5 min ≈ 296 s)
- Models: persistence, ridge, lightgbm
- Horizons: h1, h8 (sample steps)
- Outer folds: fold0 only
- Context: 32 native samples
- Expected jobs: 24

## Actual helper behavior

1. Always calls `prepare_split_windows(..., horizon_native, context_native)` on
   the native panel.
2. Does **not** call `downsample_series` when `factor > 1`.
3. Relabels `horizon` / `context` metadata using `round(native / factor)`.
4. For factor 7, both config h1 and h8 collapse to labeled horizon **1**, while
   the actual fit still uses native horizons 1 and 8.
5. Shared `ridge_*` / `lightgbm_*` parameters are computed in `run_downsampling`
   but not passed into the helper (defaults used).
6. Code comment: *"helper retains native fit for smoke."*

## Reason no results were generated

Pre-execution inspection detected the blocker. Per protocol, the pack was **not
launched**. No `results/final/packs/08_downsampling/` artifacts were created.

## Explicit unsupported claims

Do **not** claim, based on this freeze:

- that five-minute telemetry increases or decreases forecast error,
- that native TimeTrack resolution is empirically justified by a final
  downsampling experiment,
- any peak-retention or compute-savings conclusion from coarse aggregation,
- any comparison of “coarse” vs “native” MAE from pack `08_downsampling`.

## Future work

Defer a corrected downsampling study to a **separate** experiment freeze that:

1. wires real panel aggregation (as in the development script) into the final
   pack path,
2. documents physical lead-time and context-duration alignment,
3. passes frozen shared hyperparameters,
4. regenerates all related artifacts from scratch.

Do **not** patch this under `experiment-freeze-v2`.

## Impact on primary C1 evidence

This omission does **not** affect the primary hierarchical reconciliation
experiments (`memory_*`, `cpu_*`, `disk_boundary`) or their stored outer-
evaluation predictions.
