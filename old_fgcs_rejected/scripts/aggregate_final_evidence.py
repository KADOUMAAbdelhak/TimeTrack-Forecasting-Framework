#!/usr/bin/env python3
"""Aggregate accepted final evidence into publication tables/figures (no training)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from timetrack.final_reporting import (
    config_hash,
    load_yaml,
    run_final_aggregation,
    validate_registry,
    validate_reporting_config,
)


def write_docs(result: dict, registry: dict, reporting: dict) -> None:
    out: Path = result["output_dir"]
    h = result["headlines"]
    claims = result["claims"]

    (out / "SAFE_CLAIMS.md").write_text(
        f"""# Safe claims (final frozen evidence only)

Qualified by hierarchy, model, horizons, folds, and freeze tags
(`experiment-freeze-v2`, `final-analysis-freeze-v1`, `final-peak-analysis-freeze-v1`,
`final-reporting-freeze-v1`).

1. **Hierarchical reconciliation restores machine–cluster coherence** for CPU
   (`cpu_core_weighted`) and memory (`memory_um`): coherence error after
   bottom_up / WLS / MinT is essentially zero on evaluated outer folds.

2. **For core-weighted CPU**, reconciliation reduces aggregate MAE versus the
   same-model independent forecast for Ridge, LightGBM, and DLinear across
   horizons h1/h8/h16 and folds 0–2 (Claim B supported; mean relative effects
   about {h['cpu_ridge_bu_vs_ind_rel']:.1%} to {h['cpu_lgbm_mint_vs_ind_rel']:.1%} depending on model/method).

3. **LightGBM + MinT is the best observed CPU configuration** in the frozen
   outer evaluation (MAE {h['cpu_lightgbm_mint_mae']:.4f} weighted-mean %), about
   {h['cpu_lgbm_mint_vs_pers_rel']:.1%} versus persistence independent.
   Bottom-up remains preferable when bottom-level preservation is required.

4. **For memory**, WLS/MinT provide modest aggregate improvements for Ridge and
   DLinear in many cells, but Claim C is only partially supported (fold/horizon
   uncertainty). Persistence independent remains a strong baseline; LightGBM is
   a frozen negative baseline versus persistence.

5. **Disk is hierarchy- and method-dependent**: Ridge bottom_up degrades
   aggregate MAE (Claim D1; mean relative ≈ {h['disk_ridge_bu_vs_ind_rel']:.1%}).
   Top-down preserves the independently forecast top while harming bottoms
   (Claim D2). Persistence independent is the best observed disk base.

6. **Ordinary aggregate-MAE gains do not imply universal peak-operational
   gains** (P1/P2 unsupported). Peak benefits are model-specific (esp. LightGBM).

7. **LightGBM remains the strongest evaluated CPU model during high-load
   periods** (Claim P3 supported across q90/q95 × folds × horizons).

Numbers: best observed / recommended operational wording only — not prospective
deployment selection.
"""
    )

    (out / "UNSUPPORTED_CLAIMS.md").write_text(
        """# Unsupported claims (must not appear as confirmed findings)

- Reconciliation always improves accuracy.
- One reconciliation method is universally best across CPU, memory, and disk.
- Reconciliation generally improves peak recall (P2 unsupported).
- Reconciliation generally improves high-load memory prediction (P4 unsupported).
- DLinear is the best CPU model (LightGBM is).
- LightGBM is competitive for memory or disk under every configuration.
- Top-down improves top-level disk accuracy (it preserves, does not improve).
- Downsampling degrades forecasting / native resolution is empirically superior
  (downsampling not executed; scientifically blocked).
- Network hierarchy final results (not evaluated).
- Probabilistic calibration final claims (optional pack not executed).
- Global models beat local models / adaptive routing is superior
  (development-only; not claim-eligible).
- State-of-the-art claims against HARMONY/FRT.
- “First” hierarchical cloud forecasting claim.
"""
    )

    (out / "REPRODUCIBILITY_REPORT.md").write_text(
        f"""# Reproducibility report — final evidence aggregate

## Freeze layers

| Layer | Tag | Peeled commit |
|-------|-----|---------------|
| Predictions | experiment-freeze-v2 | {registry['prediction_layer']['freeze_tag_commit']} |
| Statistics | final-analysis-freeze-v1 | {registry['statistics_layer']['freeze_tag_commit']} |
| Peaks | final-peak-analysis-freeze-v1 | {registry['peak_layer']['freeze_tag_commit']} |
| Reporting | final-reporting-freeze-v1 | see MANIFEST |

Dataset fingerprint: `{registry['dataset_fingerprint']}`

## Regeneration

```bash
python scripts/tt_cli.py test
python scripts/aggregate_final_evidence.py \\
  --registry configs/final_evidence_registry.yaml \\
  --reporting-config configs/final_reporting.yaml \\
  --output results/final/aggregate
```

Source prediction NPZs are not modified. See `SOURCE_ARTIFACT_HASHES.csv` and
`MANIFEST.json` (`source_files_unchanged`).

## Exclusions

Downsampling scientifically blocked; optional network/conformal/LSTM not
executed; adaptive router / global LOMO development-only.
"""
    )

    claim_lines = claims.to_string(index=False)
    (out / "FINAL_EVIDENCE_SUMMARY.md").write_text(
        f"""# Final evidence summary

## Headlines (exact aggregates)

### CPU (weighted-mean %)

- Persistence independent MAE (mean over folds/horizons): **{h['cpu_persistence_independent_mae']:.4f}**
  - h1={h['cpu_pers_h1']:.4f}, h8={h['cpu_pers_h8']:.4f}, h16={h['cpu_pers_h16']:.4f}
- LightGBM independent vs persistence: **{h['cpu_lgbm_ind_vs_pers_rel']:.2%}**
- LightGBM MinT vs persistence: **{h['cpu_lgbm_mint_vs_pers_rel']:.2%}**
- LightGBM MinT vs LightGBM independent: **{h['cpu_lgbm_mint_vs_ind_rel']:.2%}**
- Ridge bottom_up vs independent: **{h['cpu_ridge_bu_vs_ind_rel']:.2%}**
- DLinear bottom_up vs independent: **{h['cpu_dlinear_bu_vs_ind_rel']:.2%}**
- Best observed: `{h['best_observed_cpu']}`
- Recommended operational: {h['recommended_operational_cpu']}

### Memory / Disk / Peaks

- Best observed memory: `{h['best_observed_memory']}`
- Recommended memory: {h['recommended_operational_memory']}
- Disk Ridge BU vs independent: **{h['disk_ridge_bu_vs_ind_rel']:.2%}**
- Best observed disk: `{h['best_observed_disk']}`
- Peaks: P3 supported; P1/P2/P4 unsupported; P5 partially supported

## Claim matrix

```
{claim_lines}
```
"""
    )

    (out / "EXECUTION_DEVIATIONS_SUMMARY.md").write_text(
        """# Execution deviations summary (aggregate)

Full detail: `results/final/EXECUTION_DEVIATIONS.md`.

- Downsampling omitted (smoke stub).
- Provisional supporting_statistics archived; replaced by final-analysis-freeze-v1.
- Commit 38366f1 provenance-only for peeled tags.
- Frozen peak pack runner blocked; replaced by final-peak-analysis-freeze-v1.
- Peak RSS often unavailable on analysis CLIs.
- Claim D interpreted as D1 (BU harm) and D2 (TD top preservation) separately.
- Disk LightGBM is transferred-hyperparameter stress, not headline effect.
- EWMA and multi-seed (≥3) not in experiment-freeze-v2 pack matrix (disclosed).
"""
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", type=Path, default=ROOT / "configs" / "final_evidence_registry.yaml")
    ap.add_argument("--reporting-config", type=Path, default=None)
    ap.add_argument("--config", type=Path, default=None, help="Alias for --reporting-config (v2)")
    ap.add_argument("--output", type=Path, default=ROOT / "results" / "final" / "aggregate")
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--smoke-root", type=Path, default=None)
    ap.add_argument("--require-frozen", action="store_true")
    args = ap.parse_args()
    reporting_path = args.reporting_config or args.config or (ROOT / "configs" / "final_reporting.yaml")

    registry = load_yaml(args.registry)
    # Route robustness-aware registry/reporting to v2 aggregator
    if int(registry.get("registry_version", 1)) >= 2 or "v2" in Path(reporting_path).name:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "aggregate_final_evidence_v2",
            ROOT / "scripts" / "aggregate_final_evidence_v2.py",
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        sys.argv = [
            "aggregate_final_evidence_v2.py",
            "--registry",
            str(args.registry),
            "--config",
            str(reporting_path),
            "--output",
            str(args.output),
        ]
        if args.validate_only:
            sys.argv.append("--validate-only")
        if args.smoke:
            sys.argv.append("--smoke")
        if args.require_frozen:
            sys.argv.append("--require-frozen")
        raise SystemExit(mod.main())

    reporting = load_yaml(reporting_path)
    errs = validate_registry(registry) + validate_reporting_config(reporting)
    if errs:
        raise SystemExit("invalid configs:\n- " + "\n- ".join(errs))
    if args.validate_only:
        print("OK", args.registry, reporting_path)
        print("registry_hash", config_hash(registry), "reporting_hash", config_hash(reporting))
        return

    result = run_final_aggregation(
        registry=registry,
        reporting=reporting,
        output_dir=args.output,
        smoke=args.smoke,
        smoke_root=args.smoke_root,
    )
    write_docs(result, registry, reporting)
    print("aggregate complete", args.output)
    print(json.dumps(result["headlines"], indent=2))


if __name__ == "__main__":
    main()
