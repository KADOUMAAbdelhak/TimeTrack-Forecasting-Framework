#!/usr/bin/env python3
"""Aggregate robustness-aware final evidence (reporting freeze v2; no training)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from timetrack.final_reporting import load_yaml
from timetrack.final_reporting_v2 import (
    run_final_aggregation_v2,
    scientific_protocol_hash,
    validate_registry_v2,
    validate_reporting_config_v2,
)


def write_docs(result: dict, registry: dict, reporting: dict) -> None:
    out: Path = result["output_dir"]
    h = result["headlines"]
    claims = result["claims"]
    gates = result["gates"]

    (out / "SAFE_CLAIMS_V2.md").write_text(
        f"""# Safe claims v2 (robustness-aware frozen evidence)

Qualified by hierarchy, model, method, horizons h1/h8/h16 (disk h1/h8), folds 0–2,
seeds 0/1/2 where applicable, and freezes:
`experiment-freeze-v2`, `final-analysis-freeze-v1`, `final-peak-analysis-freeze-v1`,
`final-robustness-extension-freeze-v2`, `final-robustness-analysis-freeze-v2`,
`final-reporting-freeze-v2`.

1. **LightGBM independent** consistently outperforms Ridge, EWMA, and persistence
   for core-weighted CPU across seeds 0/1/2, folds 0–2, horizons 1/8/16
   (seed-invariant; vs Ridge relative MAE ≈ {h['cpu_lightgbm_vs_ridge_rel']:.2%};
   vs persistence ≈ {h['cpu_lightgbm_vs_persistence_rel']:.2%}).

2. **LightGBM MinT** further improves aggregate CPU accuracy
   (≈ {h['cpu_lightgbm_mint_vs_independent_rel']:.2%} vs independent) and restores
   exact coherence; LightGBM is seed-invariant under the frozen configuration
   (seed SD = {h['cpu_lightgbm_seed_std']:.4g}).

3. **DLinear CPU** results are practically seed-stable (seed SD ≈ {h['cpu_dlinear_seed_std']:.4g});
   bottom-up / WLS / MinT improve aggregate forecasts across all evaluated seeds
   (bottom-up mean relative ≈ {h['cpu_dlinear_seed_mean_bottom_up_effect']:.2%}).

4. **Bottom-up** provides a bottom-preserving CPU reconciliation alternative
   (`ridge+bottom_up`), whereas WLS/MinT can trade machine-level accuracy for
   aggregate accuracy.

5. For **memory**, WLS and MinT often improve DLinear relative to its own
   independent forecasts (WLS ≈ {h['memory_dlinear_wls_vs_independent_rel']:.2%};
   MinT ≈ {h['memory_dlinear_mint_vs_independent_rel']:.2%}), but **EWMA remains the
   strongest observed memory method** (MAE ≈ {h['memory_ewma_mae']:.6g}).

6. Reconciled DLinear memory forecasts do **not** robustly outperform EWMA across
   seeds (WLS vs EWMA seed-2 relative ≈ {h['memory_dlinear_wls_vs_ewma_seed2_rel']:+.2%}).

7. **Disk** is a stable boundary: Ridge bottom-up harms aggregate accuracy
   (≈ {h['disk_ridge_bottom_up_vs_independent_rel']:+.2%}), while top-down preserves
   the independent top at a bottom-level cost.

8. Ordinary aggregate forecasting gains do **not** imply general peak-operational
   gains (P1/P2/P4 unsupported).

9. **LightGBM** remains the strongest evaluated CPU model during high-load periods
   (P3 supported).

10. **DLinear memory peak underprediction and range compression** persist across
    seeds and are amplified rather than corrected by reconciliation
    (diagnostic; all-seeds bias present = {h['dlinear_memory_peak_bias_all_seeds']}).
"""
    )

    (out / "UNSUPPORTED_CLAIMS_V2.md").write_text(
        """# Unsupported claims v2 (must not appear as confirmed findings)

- Reconciliation universally improves forecasting
- One reconciliation method is universally best
- DLinear is the best CPU model
- DLinear or Ridge robustly beats EWMA for memory
- Memory reconciliation universally improves accuracy
- Reconciliation generally improves peak recall
- Reconciliation generally reduces peak false alarms
- Top-down improves disk top-level accuracy
- Top-down is cost-free at machine level
- LightGBM is suitable for memory or disk under the transferred configurations
- Native sampling resolution is empirically superior
- Network hierarchy claims
- Conformal-calibration claims
- Adaptive routing claims
- Global-model superiority
- State-of-the-art or first-method claims
- Independent multi-dataset generalization
"""
    )

    claim_txt = claims.to_string(index=False)
    (out / "FINAL_EVIDENCE_SUMMARY_V2.md").write_text(
        f"""# Final evidence summary v2

## Headlines (exact aggregates)

### CPU (weighted-mean % = wsum/236)

- Persistence independent MAE: **{h['cpu_persistence_mae']:.6g}**
- EWMA independent MAE: **{h['cpu_ewma_mae']:.6g}**
- Ridge independent MAE: **{h['cpu_ridge_independent_mae']:.6g}**
- LightGBM independent MAE: **{h['cpu_lightgbm_independent_mae']:.6g}**
  - vs Ridge: **{h['cpu_lightgbm_vs_ridge_rel']:.4%}**
  - vs persistence: **{h['cpu_lightgbm_vs_persistence_rel']:.4%}**
  - seed SD: **{h['cpu_lightgbm_seed_std']:.6g}** (seed-invariant)
- LightGBM MinT MAE: **{h['cpu_lightgbm_mint_mae']:.6g}**
  - vs independent: **{h['cpu_lightgbm_mint_vs_independent_rel']:.4%}**
  - vs persistence: **{h['cpu_lightgbm_mint_vs_persistence_rel']:.4%}**
- DLinear seed-mean independent MAE: **{h['cpu_dlinear_seed_mean_independent_mae']:.6g}**
  - bottom-up effect: **{h['cpu_dlinear_seed_mean_bottom_up_effect']:.4%}**
  - seed SD: **{h['cpu_dlinear_seed_std']:.6g}**; seed range: **{h['cpu_dlinear_seed_range']:.6g}**
- Best observed: `{h['best_observed_cpu']}`
- Bottom-preserving alternative: `{h['bottom_preserving_cpu']}`

### Memory

- EWMA MAE: **{h['memory_ewma_mae']:.6g}** (strongest observed)
- Persistence / Ridge MAE: **{h['memory_persistence_mae']:.6g}** / **{h['memory_ridge_mae']:.6g}**
- DLinear seed-mean independent: **{h['memory_dlinear_seed_mean_independent_mae']:.6g}**
- DLinear WLS/MinT vs independent: **{h['memory_dlinear_wls_vs_independent_rel']:.4%}** / **{h['memory_dlinear_mint_vs_independent_rel']:.4%}**
- DLinear WLS/MinT vs EWMA: **{h['memory_dlinear_wls_vs_ewma_rel']:.4%}** / **{h['memory_dlinear_mint_vs_ewma_rel']:.4%}**
- WLS vs EWMA seed-2 relative: **{h['memory_dlinear_wls_vs_ewma_seed2_rel']:.4%}**
- LightGBM vs EWMA: **{h['memory_lightgbm_vs_ewma_rel']:.4%}** (negative baseline)

### Disk / Peaks

- Persistence / EWMA / Ridge independent MAE: **{h['disk_persistence_mae']:.6g}** / **{h['disk_ewma_mae']:.6g}** / **{h['disk_ridge_independent_mae']:.6g}**
- Ridge BU vs independent: **{h['disk_ridge_bottom_up_vs_independent_rel']:.4%}**
- Ridge TD vs independent: **{h['disk_ridge_top_down_vs_independent_rel']:.4%}**
- DLinear memory peak bias all seeds: **{h['dlinear_memory_peak_bias_all_seeds']}**

## Claim matrix

```
{claim_txt}
```

## Publication gates

{json.dumps(gates, indent=2)}

## Final decision

**{gates['final_decision']}**
"""
    )

    (out / "REPRODUCIBILITY_REPORT_V2.md").write_text(
        f"""# Reproducibility report v2 — robustness-aware aggregate

## Freeze layers

| Layer | Tag | Peeled commit |
|-------|-----|---------------|
| Predictions | experiment-freeze-v2 | {registry['prediction_layer']['freeze_tag_commit']} |
| Statistics | final-analysis-freeze-v1 | {registry['statistics_layer']['freeze_tag_commit']} |
| Peaks | final-peak-analysis-freeze-v1 | {registry['peak_layer']['freeze_tag_commit']} |
| Robustness extension | final-robustness-extension-freeze-v2 | {registry['robustness_extension_layer']['freeze_tag_commit']} |
| Robustness statistics | final-robustness-analysis-freeze-v2 | {registry['robustness_statistics_layer']['freeze_tag_commit']} |
| Reporting | final-reporting-freeze-v2 | {result['manifest']['reporting_freeze_tag_commit']} |

Dataset fingerprint: `{registry['dataset_fingerprint']}`  
Scientific protocol hash: `{result['scientific_protocol_hash']}`  
Provenance envelope hash: `{result['provenance_envelope_hash']}`

## Regeneration

```bash
python scripts/tt_cli.py test
python scripts/aggregate_final_evidence_v2.py \\
  --registry configs/final_evidence_registry_v2.yaml \\
  --config configs/final_reporting_v2.yaml \\
  --output results/final/aggregate \\
  --require-frozen
```

Source prediction NPZs are not modified. See `SOURCE_ARTIFACT_HASHES.csv`.
Pre-robustness aggregate archived at `results/final/archive/pre_robustness_aggregate/`.
"""
    )

    (out / "EXECUTION_DEVIATIONS_SUMMARY_V2.md").write_text(
        """# Execution deviations summary v2

- Pre-robustness aggregate superseded and archived (not deleted).
- `final-robustness-analysis-freeze-v1` was force-updated historically; superseded by immutable v2; archived pack rejected.
- Robustness-statistics MANIFEST lacks a `pack_hash` field; registry uses scientific_config_hash `08859b8132f3d605` as the authoritative pack hash.
- Scientific protocol hash excludes freeze-tag/archive-path provenance; provenance envelope hash records them separately.
- Disk LightGBM remains transferred-configuration stress (supplementary only).
- Peak RSS / inference throughput often `not_recorded_by_frozen_runner` for older packs.
- Downsampling scientifically blocked; network/conformal/LSTM/router/LOMO excluded.
- One DLinear memory independent cell is seed-unstable; memory claims remain conditional.
"""
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", type=Path, default=ROOT / "configs" / "final_evidence_registry_v2.yaml")
    ap.add_argument("--config", type=Path, default=ROOT / "configs" / "final_reporting_v2.yaml")
    ap.add_argument("--reporting-config", type=Path, default=None, help="Alias for --config")
    ap.add_argument("--output", type=Path, default=ROOT / "results" / "final" / "aggregate")
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--require-frozen", action="store_true")
    args = ap.parse_args()
    reporting_path = args.reporting_config or args.config

    registry = load_yaml(args.registry)
    reporting = load_yaml(reporting_path)
    errs = validate_registry_v2(registry) + validate_reporting_config_v2(reporting)
    if errs:
        raise SystemExit("invalid configs:\n- " + "\n- ".join(errs))
    if args.validate_only:
        print(
            json.dumps(
                {
                    "ok": True,
                    "scientific_protocol_hash": scientific_protocol_hash(registry, reporting),
                },
                indent=2,
            )
        )
        return

    result = run_final_aggregation_v2(
        registry=registry,
        reporting=reporting,
        output_dir=args.output,
        smoke=args.smoke,
        require_frozen=args.require_frozen,
    )
    write_docs(result, registry, reporting)
    print("aggregate v2 complete", args.output)
    print(json.dumps({"final_decision": result["gates"]["final_decision"], "scientific_protocol_hash": result["scientific_protocol_hash"]}, indent=2))


if __name__ == "__main__":
    main()
