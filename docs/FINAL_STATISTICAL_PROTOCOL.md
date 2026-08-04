# Final statistical protocol (analysis freeze)

This document freezes the **statistical analysis layer** applied to
`experiment-freeze-v2` outer-evaluation predictions. It does **not** change the
prediction protocol.

| Layer | Tag |
|-------|-----|
| Predictions | `experiment-freeze-v2` |
| Statistics | `final-analysis-freeze-v1` |

## Scope

- Consume stored NPZ predictions from: `memory_classical`, `memory_dlinear`,
  `cpu_classical`, `cpu_dlinear`, `disk_boundary`.
- Never train or retune a forecasting model.
- Never regenerate or modify source prediction artifacts.
- Prove source SHA-256 hashes unchanged after analysis.

## Bootstrap

Paired moving-block bootstrap on identical timestamps:

\[
d_t = |e^{\mathrm{recon}}_t| - |e^{\mathrm{ind}}_t|
\]

- `n_boot = 5000`, `seed = 0`
- Block length: clamp(`max(horizon, context, first ACF lag below 0.1)`, 8, 256)
  from validation residuals of the independent top series
- Fold × model × horizon × method cells are **never** pooled

For each replicate \(b\) with shared block starts:

\[
\mathrm{relative\_effect}_b = \frac{\mathrm{mean}(d_b)}{\mathrm{mean}(|e^{\mathrm{ind}}|_b)}
\]

Relative CIs come from the replicate distribution of
`relative_effect_b`, not from dividing an absolute CI by a point estimate.

Report: `n_paired`, `block_length`, mean/median `d`, relative MAE effect,
percentile 95% CIs (absolute and relative), `P(mean(d)<0)`, two-sided bootstrap
p-value, effect class.

## Holm families

Separate families (α = 0.05):

1. `memory_ridge` 2. `memory_dlinear` 3. `memory_lightgbm`
4. `cpu_ridge` 5. `cpu_dlinear` 6. `cpu_lightgbm`
7. `disk_ridge` 8. `disk_lightgbm`

Persistence ties: descriptive only.

Claim A uses family `cpu_base_model_lightgbm_vs_persistence` (not mixed into
reconciliation Holm families).

## Fold consistency

- **strongly_consistent**: all folds improve; no fold worsens by >2%
- **directionally_consistent**: ≥2 folds improve; no fold worsens by >5%
- **mixed**: directions differ without catastrophic harm
- **consistently_harmful**: all folds degrade
- **unstable**: any fold degrades by ≥20%

## Trade-offs

- **pareto_improvement**: top improves >2%; bottom macro does not worsen >2%; coherence improves
- **aggregate_focused_improvement**: top improves >2%; bottom macro or worst worsens >2%; coherence improves
- **coherence_only**: top within ±2%; coherence improves; no catastrophic bottom degradation
- **accuracy_costly_coherence**: top worsens >2% **or** bottom macro worsens >5%

## Claims A–D

Derived from atomic fold×horizon(×model×method) comparisons. No pooling of
timestamps across folds/horizons/models into one synthetic sample.

Classifications: `supported`, `partially_supported`, `unsupported`, `contradicted`
(see `configs/final_statistics.yaml` and `timetrack/statistical_reporting.py`).

## Entrypoint

```bash
python scripts/analyze_final_statistics.py \
  --config configs/final_statistics.yaml \
  --source-config configs/final_fgcs_packs.yaml \
  --output results/final/packs/06_supporting_statistics
```

Config: `configs/final_statistics.yaml`  
Implementation: `timetrack/statistical_reporting.py`
