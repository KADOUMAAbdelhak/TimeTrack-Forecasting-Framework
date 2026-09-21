# Experimental protocol revision audit (Section 5)

## Length
| Metric | Before | After |
|--------|--------|-------|
| Section 5 words (prose, excl. table body) | ~100 | ~886 |
| Rendered Section 5 | ≪1 page (thin stubs) | ~1.0–1.2 pages (pp. 8–9) |
| Full article pages | 15 | 15 |

## Subsection structure
**Before:** Temporal Splits and Output Widths; Hyperparameter Selection and Leakage Prevention; Statistical Analysis; Multi-Seed and Reproducibility Protocol.

**After:**
1. Chronological Evaluation Design
2. Model Selection and Leakage Prevention
3. Statistical and Multi-Seed Analysis
4. Reproducibility and Frozen Evidence

## Exact fold source
- Calendar spans: `timetrack.splits.make_outer_chronological_folds` on `build_analysis_panel()` with dataset fingerprint `bf06dc0e7fe6ff5e`.
- Window counts and scored endpoints: `fgcs/results/provenance/forecast_semantics_eval_sets.csv` (aligned with `forecast_semantics_by_pack.csv`).
- Supplementary tables: `fgcs/tables/supplementary_fold_boundaries.tex`.

## Context length
- \(L=32\); median interval \(42.285\) s ⇒ \(\approx 22.6\) min (approximate elapsed-time reading only).

## Output-width semantics
- \(H\in\{1,8,16\}\) (disk \(\{1,8\}\)): jointly predicted target length.
- Target vector \((y_{t+1},\ldots,y_{t+H})\); frozen metrics use component 0 only.
- Approximate joint target spans: \(42.285\) s / \(5.64\) min / \(11.28\) min.
- \(H\) is **not** evaluated forecast lead / horizon.

## Scored lead
- One-step ahead: \(y_{t+1}\) vs \(\hat y_{t+1|t}\).

## H-specific row-set differences
- Larger \(H\) drops final origins.
- Especially visible for CPU fold 0 (test windows \(4847\to4295\to3707\)); memory/disk endpoint losses are smaller.

## Preprocessing / tuning chronology
1. Outer chronological split.
2. Train-only scaler fitting (DLinear only).
3. Tune on train/inner validation.
4. Freeze one configuration per family.
5. Evaluate once on outer test.
6. Reconciliation covariance from outer-train **validation** residuals only.

## Reconciliation residual source
- `outer_train_val_residuals` (never outer-test).

## Seed policy
- Seeds \(\{0,1,2\}\) for LightGBM and DLinear.
- LightGBM: bitwise seed invariance under frozen config → reported as invariance, not independent replicates.
- DLinear: genuine seed variation; seed-level results remain visible.

## Bootstrap policy
- \(n_{\mathrm{boot}}=5000\), paired moving-block.
- Block length: \(\mathrm{clamp}(\max(H,L,\ell_{\mathrm{ACF}}),8,256)\) with ACF threshold \(0.1\) on validation residuals of the independent top series (often \(32\)).
- Direct relative effect \((\mathrm{MAE}_A^\ast-\mathrm{MAE}_B^\ast)/\mathrm{MAE}_B^\ast\) inside each resample.

## Holm policy
- Holm within predefined families (\(\alpha=0.05\)).
- Final robustness analysis: eight families (listed in supplementary material).

## Peak-threshold policy
- Train-only \(q_{90}/q_{95}\); exact-timestamp matching; no event tolerance/merging.

## Frozen evidence stages
1. Prediction generation  
2. Primary statistical analysis  
3. Peak analysis  
4. Robustness extension  
5. Robustness statistics  
6. Final reporting aggregation  

Exact tags/hashes deferred to supplementary provenance.

## Details moved to supplementary
- Exact fold calendar + \(H\)-specific window counts/endpoints.
- Full hyperparameter grids and selected values.
- Holm family lists and support-classification rules.
- Seed/thread policy detail.
- Freeze tags, peeled commits, pack hashes, fingerprint.

## Unsupported-claim review
- No unpublished numerical performance claims introduced in Section 5.
- No long-horizon / lead-time interpretation of \(H\).
- LightGBM seeds not treated as independent replicates.
- Result claims deferred to Section 6.

## Page/layout result
- Article: 15 pages; 0 overfull boxes; 0 unresolved citations/references.
- Protocol table in Section 5; Results starts on p. 9; tables/figures before references.
- Minimal Section 4 duplication corrections (HP/seed/budget deferred to protocol).
- Late Results float placement tightened (`[!ht]` on summary tables; slight figure width trim) to keep page budget without float/ref collisions.

## Terminology
- Section 5: zero occurrences of horizon / lead time / h1/h8/h16.
- Remaining manuscript “horizon”: only incidental (e.g., “Horizontal lines” in a caption).
