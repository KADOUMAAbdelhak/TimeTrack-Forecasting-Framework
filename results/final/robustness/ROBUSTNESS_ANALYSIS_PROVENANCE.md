# Robustness analysis provenance

## Distinction

### Accepted source evidence

DLinear seeds 1–2 (and LightGBM seeds 1–2, EWMA) were trained using scientific
code/config matching `final-robustness-extension-freeze-v2`:

| Field | Value |
|-------|-------|
| Extension freeze | `final-robustness-extension-freeze-v2` |
| Peeled commit | `9750626607e4bf8bc6d45f89f6ee5805c87f3251` |
| Implementation commit | `bb6e12a267e3121c689224c66f605eb9efc63384` |
| Scientific config hash | `f19707c2a6f24478` |
| DLinear pack hash | `ecd66cd4bc4a7770` |
| LightGBM v2 pack hash | `446473103b0cf235` |
| Dataset fingerprint | `bf06dc0e7fe6ff5e` |

Prediction NPZs and fit-level `base_forecasts.csv` /
`reconciliation_results.csv` are **accepted source data**.

### Provisional derived evidence (archived)

Post-freeze analysis-only commits produced derived summaries/figures. Those are
**not** final-claim evidence and were archived to:

`results/development/provisional_robustness_analysis/dlinear_seed_robustness_postfreeze/`

Rejection reasons:

- `derived_analysis_not_frozen`
- `reporting_logic_added_after_extension_freeze`
- `peak_threshold_column_fixed_after_extension_freeze`

## Post-freeze commit audit (`9750626` → HEAD at analysis freeze)

| Commit | Message | Files | Classification |
|--------|---------|-------|----------------|
| `6416188` | docs: record accepted LightGBM v2; add DLinear seed analysis-only reporting | `docs/ROBUSTNESS_EXECUTION_NOTES.md`, `experiments/dlinear_seed_analysis.py`, `scripts/analyze_dlinear_seed_robustness.py` | documentation only + **analysis/reporting only** |
| `2002bf3` | fix: preserve DLinear peak threshold names in seed analysis | `experiments/dlinear_seed_analysis.py` | **analysis/reporting only** |

### Zero post-freeze changes to scientific source path

Verified unchanged relative to `final-robustness-extension-freeze-v2`:

- DLinear training (`models/deep_learning/neural.py`)
- feature construction / splits / horizons
- scaling
- reconciliation / covariance
- prediction serialization (`experiments/robustness_extension.py` training path)
- scientific configuration (`configs/final_robustness_extension.yaml` scientific hash)

**Conclusion:** source predictions were **not** generated using changed scientific
logic. Derived tables from analysis-only commits are provisional and superseded
by `final-robustness-analysis-freeze-v1`.

## Analysis-freeze verification note

An initial peel of `final-robustness-analysis-freeze-v1` omitted
`source_artifact_root` when locating seed-0 classical
`reconciliation_results.csv`, so seed-0 reconstruction rows were marked
`missing_source_row` without failing the run. That path bug is corrected in the
analysis layer only (no prediction regeneration). Corrected freeze peel requires
all 216 DLinear reconstruction cells `status=ok`.
