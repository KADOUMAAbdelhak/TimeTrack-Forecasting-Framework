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

Post-extension-freeze analysis-only commits produced DLinear derived
summaries/figures. Those are **not** final-claim evidence:

`results/development/provisional_robustness_analysis/dlinear_seed_robustness_postfreeze/`

### Provisional mutated analysis freeze (archived)

`final-robustness-analysis-freeze-v1` was force-updated after analysis bugs.
The pack executed under the final v1 peel is archived to:

`results/development/provisional_robustness_analysis/final-robustness-analysis-freeze-v1/robustness_statistics/`

| Field | Value |
|-------|-------|
| experiment_stage | development |
| eligible_for_final_claims | false |
| evaluation_role | provisional_mutated_analysis_freeze |

Rejection reasons:

- `analysis_freeze_tag_force_updated`
- `reconciliation_path_bug_fixed_after_initial_tag`
- `seed_column_clobber_fixed_after_initial_tag`
- `freeze_immutability_violated`

**Never force-update `final-robustness-analysis-freeze-v1` again.**
Corrections require a new versioned freeze tag.

Authoritative analysis freeze: `final-robustness-analysis-freeze-v2`.

## V1 tag force-update incident

Tags are immutable. The following peels are recorded for audit only.

| Order | Peeled commit | Approx. annotated tag object | Reason | Affected files | Numerical results changed? | Predictions changed? |
|-------|---------------|------------------------------|--------|----------------|-------------|----------------------|
| 1 (initial) | `a8fd9a5c662d69632df2ca46a843fab65a5b69b1` | `f1180f65ee0b49cfb9c93dc5010145ca8c3cadbc` | Initial analysis freeze + first execution | analysis/reporting + docs/tests/config | N/A (first) | **No** |
| 2 (force update 1) | `af8634c5d9c93bfb2bedfe36a02ff88fe6ed72fb` | `bc63fd57670ba462adc7451c43579182d7299de8` (replaced prior object `e1515b2…`) | Seed-0 classical recon CSV path omitted `source_artifact_root` (`missing_source_row`) | `timetrack/robustness_reporting.py`, tests, docs, config stamp | Yes — reconstruction verification completed for seed 0; bootstrap labels still wrong | **No** |
| 3 (force update 2 / final v1 peel) | `19c540693a444054c534c2db48043ade2ccbf5cc` | `b92d201fe8d6f80c086fa0188c5f3a6483bcab49` | Bootstrap effect dict overwrote model `seed` with RNG seed `0` | `timetrack/robustness_reporting.py`, tests, config stamp | Yes — seed-aware summaries/claims restored | **No** |

Final v1 peel (archived pack source): `19c540693a444054c534c2db48043ade2ccbf5cc`.

Post-peel docs-only commit (not retagged): `3dd6d0f` (provenance note).

### Confirmation

Accepted model prediction NPZs and pack hashes were **never** modified by any
v1 force update. Changes were analysis/reporting only.

## Post-extension-freeze commit audit (`9750626` → analysis code)

| Commit | Message | Classification |
|--------|---------|----------------|
| `6416188` | DLinear seed analysis-only reporting + docs | documentation + **analysis/reporting only** |
| `2002bf3` | preserve DLinear peak threshold names | **analysis/reporting only** |
| `a0354d0` | freeze multi-seed robustness statistics | **statistical analysis** + reporting + tests + docs |
| `a8fd9a5` | record freeze-v1 implementation commit | documentation/config stamp only |
| `7d71597` | seed-0 recon path fix + claim IDs | **statistical analysis** + tests + docs |
| `af8634c` | record corrected v1 peel | config stamp only |
| `905c76e` | preserve model seed vs bootstrap RNG seed | **statistical analysis** + tests |
| `19c5406` | record seed-column fix peel | config stamp only |
| `3dd6d0f` | provenance note | documentation only |

### Zero changes to accepted prediction science

Verified unchanged relative to `final-robustness-extension-freeze-v2`:

- training logic
- feature construction / scaling / splits / horizons
- reconciliation implementation used to create accepted predictions
- prediction serialization
- source NPZ files
- scientific robustness-extension configuration (`f19707c2a6f24478`)

**Conclusion:** no accepted prediction was produced using post-freeze scientific
logic. Analysis may reconstruct reconciliation from accepted predictions and
must match accepted metrics within tolerance.

## Freeze immutability policy

> Tags are immutable. Corrections require a new versioned freeze tag.

Do **not** use:

- `git tag -f`
- `git push --force`
- `git push --force-with-lease`

for any freeze tag. Use `scripts/create_immutable_freeze_tag.py` (refuses if the
tag already exists locally or on origin).

Protected prediction/analysis tags must remain untouched:

- `experiment-freeze-v2`
- `final-analysis-freeze-v1`
- `final-peak-analysis-freeze-v1`
- `final-reporting-freeze-v1`
- `final-robustness-extension-freeze-v2`
- `final-robustness-analysis-freeze-v1` (historical; do not move)
