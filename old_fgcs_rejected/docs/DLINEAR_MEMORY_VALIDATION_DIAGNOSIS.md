# DLinear memory validation diagnosis (experiment-freeze-v1 rejection)

Date: 2026-08-04  
Context: rejected `shared_tuning` under `experiment-freeze-v1`

## Observed pathology

| Metric | Value |
|--------|-------|
| Target | `cluster_UM` |
| Persistence val MAE | ~3.71×10⁸ |
| DLinear val MAE | ~1.38×10¹¹ (~372× persistence) |
| Predictions | negative (~−2.5×10¹⁰ … −1.7×10¹⁰) |
| Targets | ~1.13×10¹¹ … 1.81×10¹¹ |

## Root cause

`DLinearForecaster` trained **without input/target standardization** on raw float32
series with magnitude ~1e11.

1. **No train-only scaler** for X (channel 0) or y.
2. Adam + MSE on unscaled ~1e11 values → linear heads fail to track level;
   predictions collapse to wrong-sign / wrong-magnitude outputs.
3. **Not** a wrong-column or CPU/memory scaler mix-up (univariate `[:,:,0]` only;
   no cross-target scaler existed).
4. Inverse transform was N/A because scaling was absent.

## Fix (for experiment-freeze-v2)

Train-only standardize X and y; train in scaled space; inverse-transform
predictions with stored `y_mean_` / `y_std_`. Record scaler stats in
`runtime_meta_`. Regression test: `tests/test_dlinear_target_scaling.py`.

## Eligibility

After the fix, apply the pre-registered 2×/5× persistence inner-validation gate
separately to DLinear CPU and DLinear memory. Demote required packs if the gate
fails despite a technically correct scaling path.
