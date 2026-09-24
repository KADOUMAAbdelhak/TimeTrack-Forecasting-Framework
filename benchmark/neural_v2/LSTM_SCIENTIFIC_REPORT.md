# Phase 2B-2A2 LSTM Scientific Report

This is a descriptive report; no statistical-significance test is performed.

## Aggregate lead results

| Lead | LSTM F0 MAE | LSTM F1 MAE | Matched F1 gain (%) |
|---:|---:|---:|---:|
| 1 | 1.5860 | 1.6241 | 2.351 |
| 2 | 1.6835 | 1.6648 | 2.962 |
| 4 | 1.8714 | 1.8344 | 3.487 |
| 8 | 1.9594 | 1.9391 | 2.185 |
| 16 | 1.9966 | 1.9745 | 1.693 |
| 32 | 2.0786 | 2.0390 | 3.135 |
| 64 | 2.1138 | 2.0649 | 4.212 |
| 128 | 2.2672 | 2.2208 | 4.675 |

## Descriptive answers

1. LSTM F0 MAE vector: [1.5859528145581223, 1.6835143598572995, 1.8714209280813672, 1.959361167419031, 1.9965591268946195, 2.078602980236807, 2.1138327404958654, 2.2671551321919363].
2. LSTM F1 MAE vector: [1.6241272977253938, 1.6647605914007375, 1.8344460020667046, 1.9390767192239704, 1.9744535096299163, 2.0390384663902914, 2.0649307387617584, 2.220767675311272].
3. Matched F1 gain vector: [2.3506093373924006, 2.9622043214738696, 3.48664682646964, 2.184511936071945, 1.6931839087056202, 3.135048703251541, 4.212019646874782, 4.674799923961725]%; overall cell-mean gain 3.087%.
4. Positive aggregate leads: [1, 2, 4, 8, 16, 32, 64, 128] (8/8).
5. Positive machine means: ['machine02', 'machine03', 'machine05', 'machine07'] (4/7).
6. Positive fold means: [1, 2, 3, 4, 5] (5/5).
7. Seed mean gains: {0: 1.326, 1: 3.738, 2: 4.198}; 3/3 positive seeds.
8. F0 selected-L counts: {32: 8, 64: 14, 128: 13}.
9. F1 selected-L counts: {32: 10, 64: 14, 128: 11}.
10. Throughput changes preferred L in 20/35 cells.
11. LSTM beats frozen DLinear F0 at 1/8 leads and DLinear F1 at 3/8 leads on compatible support.
12. LSTM beats accepted LightGBM F0 at 0/8 leads and LightGBM F1 at 0/8 leads on compatible support.
13. LSTM has larger incremental throughput gain than DLinear at 8/8 leads.
14. LSTM has larger incremental throughput gain than LightGBM at 8/8 leads.
15. Architecture-dependent interpretation: corrected Ridge throughput was negative at all eight leads; accepted LightGBM throughput was conditionally positive; frozen DLinear was broad negative; LSTM is CONDITIONALLY_POSITIVE. This pattern is descriptive evidence that extracted throughput value depends on architecture, not evidence of universal usefulness or uselessness.

All cross-model comparisons use exact identical support or exact prediction intersections without retraining. Per-cell support relations and hashes are retained in the comparison CSV files.

## LSTM throughput decision

Prospective rule: `BROAD_POSITIVE` requires positive overall gain, 8/8 positive leads, at least 5/7 positive machines, at least 4/5 positive folds, and 3/3 positive seeds; `CONDITIONALLY_POSITIVE` requires positive overall gain, at least 4/8 leads, 4/7 machines, 3/5 folds, and 2/3 seeds; `BROAD_NEGATIVE` requires negative overall gain, at least 6/8 negative leads, 5/7 machines, 4/5 folds, and 3/3 seeds; all other patterns are `NEUTRAL`.

**CONDITIONALLY_POSITIVE**

Observed consistency counts: {'overall_mean_gain_pct': 3.0873780755251907, 'positive_leads': 8, 'positive_machines': 4, 'positive_folds': 5, 'positive_seeds': 3, 'negative_leads': 0, 'negative_machines': 3, 'negative_folds': 0, 'negative_seeds': 0}.

No DLinear rerun, PatchTST, TCN-v2, B4-v1, or multi-target model was executed.
