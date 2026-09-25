# Phase 2B-2A3 PatchTST Scientific Report

Descriptive results only; no significance test was performed.

## Lead-level aggregation

| Lead | Macro F0 | Macro F1 | Primary % | Pooled % | Mean cell % | Median cell % | Positive fraction |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.348908 | 1.462756 | -8.440064 | -8.681950 | -6.653319 | -2.245327 | 0.400000 |
| 2 | 1.541915 | 1.599020 | -3.703514 | -3.844765 | -3.363532 | -1.371409 | 0.409524 |
| 4 | 1.799564 | 1.805180 | -0.312121 | -0.312712 | -2.406693 | 0.174228 | 0.514286 |
| 8 | 1.890924 | 1.895441 | -0.238882 | -0.456965 | -2.314501 | -0.490249 | 0.438095 |
| 16 | 1.929108 | 1.942017 | -0.669155 | -0.991625 | -2.417446 | -1.133340 | 0.419048 |
| 32 | 1.978855 | 1.977098 | 0.088763 | -0.077733 | -1.319214 | 0.405359 | 0.514286 |
| 64 | 2.040326 | 2.026881 | 0.658975 | 0.462220 | -0.588988 | -0.186339 | 0.485714 |
| 128 | 2.211267 | 2.213060 | -0.081060 | -0.291240 | -0.928518 | -0.585568 | 0.457143 |

## Required scientific answers

1. PatchTST F0 macro-MAE vector: [1.3489077292650384, 1.541914821536174, 1.7995636313160366, 1.89092367718214, 1.9291078280879086, 1.978854753850206, 2.0403262639065263, 2.211267190183154].
2. PatchTST F1 macro-MAE vector: [1.4627564103046506, 1.5990198569784964, 1.8051804468384698, 1.8954407553373795, 1.942016540682974, 1.9770982659274254, 2.026881031612167, 2.21305964304407].
3. Primary throughput-gain vector: [-8.440064399485903, -3.703514269707191, -0.31212097336761463, -0.238882098190809, -0.6691545390627628, 0.08876285231965304, 0.6589746224516179, -0.08105998537279566]%.
4. Pooled throughput-gain vector: [-8.681950458161271, -3.8447647659115147, -0.31271192955589416, -0.45696506216227156, -0.9916247784773177, -0.07773325746090855, 0.462219653866104, -0.29123998622019354]%.
5. Mean cell-relative gain vector: [-6.653319083200745, -3.3635324226054135, -2.4066927643476577, -2.314500827125227, -2.41744580983571, -1.3192142985573845, -0.5889877881576672, -0.9285175711757986]%.
6. Positive machines: ['machine04', 'machine07'] (2/7).
7. Positive folds: [3, 4] (2/5).
8. Seed effects: {0: 0.128255, 1: -3.585448, 2: -0.273552}; positive seeds 1/3.
9. F0 selected-L distribution: {32: 15, 64: 3, 128: 17}.
10. F1 selected-L distribution: {32: 13, 64: 4, 128: 18}.
11. Throughput changes selected L in 9/35 cells.
12. Versus LightGBM, PatchTST wins 0/8 F0 and 0/8 F1 leads.
13. Versus DLinear, PatchTST wins 3/8 F0 and 7/8 F1 leads; larger primary context gain at 6/8.
14. Versus LSTM, PatchTST wins 8/8 F0 and 8/8 F1 leads; larger primary context gain at 0/8.
15. PatchTST uses throughput more effectively than LightGBM at 1/8 leads.
16. PatchTST uses throughput more effectively than LSTM at 0/8 leads.
17. PatchTST F1 beats LightGBM F1 at 0/3 longer horizons (32/64/128).
18. The five-model results show architecture-dependent throughput effects; there is no universal direction across Ridge, LightGBM, DLinear, LSTM, and PatchTST.

## Five-model standardized overall context table

| model | primary_ratio_macro_mae_gain_pct | pooled_gain_pct | mean_cell_relative_gain_pct |
|---|---|---|---|
| Ridge | -3.838048 | -3.631815 | -1.716727 |
| LightGBM | 0.014935 | -0.086515 | 0.719205 |
| DLinear | -2.604757 | -2.589275 | -2.867954 |
| LSTM | 1.252207 | 0.849314 | 3.087378 |
| PatchTST | -1.225078 | -1.407016 | -2.499026 |

## Prospective PatchTST decision

**NEUTRAL**; overall primary macro-MAE gain -1.225078%.
Consistency counts: `{"negative_folds": 3, "negative_leads": 6, "negative_machines": 5, "negative_seeds": 2, "overall_primary_gain_pct": -1.2250776628779783, "positive_folds": 2, "positive_leads": 2, "positive_machines": 2, "positive_seeds": 1}`.

Comparisons use exact support/intersections without retraining. DLinear, LSTM, and LightGBM were not rerun. No TCN-v2, B4-v1, or multi-target model was executed.
