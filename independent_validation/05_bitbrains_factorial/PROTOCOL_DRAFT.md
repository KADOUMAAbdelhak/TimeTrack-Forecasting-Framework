# Phase 4B Bitbrains External Factorial Protocol Draft

This implementation realizes the prospective decision in `EXTERNAL_FACTORIAL_DECISION.md`. It is preflight-only and does not authorize scientific execution.

## Data and support

Read selected members directly from the frozen official archives. Preserve member size/SHA-256 and reject duplicate timestamps. Remove physically invalid rows without repair, split valid observations at gaps greater than 450 seconds, and build maximum-history common support at L18 for four resources and five leads. L4/L9 reuse the same origin IDs.

Five expanding folds use the Phase 4A 50% initial train plus five 10% tests. Lead-18 target-time purges protect outer test and inner validation. The latest 15% of purged outer train is validation. All split IDs and hashes are persisted; compact reports contain no target arrays.

## Models and training

S1/S2/M1 preserve the Phase 3B plain LSTM: two unidirectional layers, hidden 64, dropout 0.1, final recurrent representation. Outputs have five horizons. Adam 0.001, batch 256, maximum 50 epochs, patience 7, gradient clipping 1.0, seeds `[0,1,2]`, contexts `[4,9,18]`.

Transforms are identity/log1p/identity/log1p in fixed resource order, followed by training-only robust scaling. M1 averages four normalized MSEs exactly. Inner fitting records each seed's best epoch. Future final refits start from scratch for the selected seed-specific epoch count and expose no validation/test callback.

## Selection and metrics

S1/S2 choose one L per environment/VM/fold/resource using mean normalized validation MAE over five horizons and three seeds. M1 chooses one L per environment/VM/fold with equal resource/horizon/seed mean. Smaller L wins ties. Outer test cannot influence selection.

Future native metrics are MAE, RMSE, R-squared, NMAE, and persistence skill. Seeds average within VM/fold/resource/lead; VM-fold cells then receive equal weight per environment. Native MAE never averages across resources. fastStorage/Rnd remain separate until equal-environment synthesis.

## Pilot and resumability

The non-scientific pilot is exactly 18 five-epoch inner fits on predeclared VMs/fold/seed/L and never accesses outer-test target values. Scientific run identity includes environment, formulation, resource, VM, fold, L, seed, phase, config hash, support hash, archive hash, and cohort hash. Atomic completion records validate all expected artifact hashes; epoch checkpoints are not retained.

