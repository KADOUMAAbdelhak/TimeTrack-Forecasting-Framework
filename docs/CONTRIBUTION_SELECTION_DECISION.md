# Contribution Selection Decision

Status: **development gate** (claim-ineligible). Manuscript embargo remains active.
Date: 2026-08-03. HEAD at decision drafting: see git log.

## Selected primary contribution

**A. Primary C1 — hierarchy-aware forecasting / reconciliation**

Rationale:

- Exact / near-exact telemetry hierarchies are audit-verified (memory, disk, bond0≈sum; CPU via core-weighted contributions).
- Development screen (558 runs) shows **accuracy gains with exact coherence** on `memory_um` and `cpu_core_weighted` (top MAE ≈0.94–0.96× independent for WLS/MinT/BU).
- Bond0 shows near-parity accuracy with coherence restoration.
- Disk requires **selective** reconciliation (top-down / avoid naive BU) — document as limitation, not a reason to drop C1.
- Systems novelty aligns with FGCS predictive resource management (coherent capacity planning).

## Supporting contribution (at most one)

**Downsampling + peak-operational analysis as supporting systems evidence** (not a second algorithmic primary).

- Fine-grained sampling claim tested directly (`docs/DOWNSAMPLING_PROTOCOL.md`).
- Peak metrics (train-derived thresholds) quantify operational value of C1 vs fixed models.

**C2 is not selected as primary** at this gate: routers/mixtures win intermittently on some targets but **mean MAE relative to the best constituent is >1** (~1.05–1.16). Retain C2 as optional follow-up / ablation after freeze, not the main claim.

## Rejected / revised candidates

| Candidate | Decision | Why |
|-----------|----------|-----|
| C3 global/entity residual | **Supporting negative / specialization study** | LOMO: local persistence wins; in-distribution: residual ≈ local, pooled/one-hot/embed worse (embed unstable on UM). No accuracy-win claim. |
| C2 adaptive router | **Revise / demote** | Does not robustly beat strongest fixed constituent across families. |
| C4 regime-aware | **Defer** | Partial overlap with C2 gating features; no standalone win. |
| Combined C2→C1 | **Not selected** | Requires both components to help; C2 lacks robust wins. |

## Development evidence summary

1. **MASE:** CU NaNs caused by train NaNs in `np.mean` lag diffs; fixed via finite-pair scale + `mase_valid` policy.
2. **In-distribution global/local (ridge):** residual ≈ local; pooled/one-hot worse; embed catastrophic on UM.
3. **DLinear:** single-series ~1–2s; unbounded multi-series grids gated; timeout/early-stop/thread caps added.
4. **Neural hierarchy confirmation:** running / pending artifact at decision time — must not reverse C1 unless it clearly nullifies tree/linear gains.
5. **C2 router:** 1320 rows; constrained mixture / stacking have sporadic beat_rate>0 but worse average MAE_rel.
6. **Peaks:** train q90/q95/MAD metrics implemented; persistence often high recall with different FA trade-offs.
7. **Downsampling:** error generally rises from native→5min for ridge/persistence on aggregated MAE.

## Ablation requirements before publication freeze

- C1: independent vs BU vs WLS vs MinT on memory+CPU; disk top-down vs BU failure case; nonnegative ablation.
- Optional neural confirmation must finish with ≥2 seeds on memory/CPU.
- Efficiency table (train/infer/params) for selected reconciling pipeline vs independent.
- Block-bootstrap CIs on primary MAE differences (infrastructure added).
- Conformal intervals on selected targets (infrastructure added).

## Expected final comparison set

- Targets: cluster_UM, machine CU set + core-weighted top, selected bond0, representative RTT/jitter, disk UD with selective recon.
- Models: persistence, ridge, LightGBM, bounded DLinear/LSTM.
- Methods: independent, bottom_up, WLS, MinT-shrink (± nonnegative).
- Horizons: h1,h4,h8,h16 (native seconds ≈42.285×h).
- Stages: final nested outer folds only after freeze; no pilot leakage.

## Remaining implementation work

- Finish neural hierarchy confirmation artifacts if not yet merged.
- Wire efficiency instrumentation into final runner reports.
- Final config freeze file + validator + artifact manifest generation (scripts added; not executed as publication).
- Clean-env reproduction script (`scripts/reproduce_clean_env.sh`).

## Estimated final compute

- Full final matrix (conservative): ~8–20 CPU-hours on laptop-class hardware if neural bounded; ~1–3 GPU-hours if expanded neural.
- Publication bootstrap + multi-seed: add ~30–50%.

## Publication-gate risks

- Disk hierarchy accuracy regression if BU is applied blindly.
- Overclaiming C2/C3 from LOMO/router intermittent wins.
- Sampling-interval mismatch with prior papers (42.3s vs 45s) must stay explicit.
- Manuscript embargo: no paper prose until freeze + literature pass.

## Decision rule check

Selected method is **not** the most complex; it is the one with clearest development accuracy+coherence evidence and systems fit.
