# Final evidence summary v2

## Headlines (exact aggregates)

### CPU (weighted-mean % = wsum/236)

- Persistence independent MAE: **1.32136**
- EWMA independent MAE: **1.32049**
- Ridge independent MAE: **1.25278**
- LightGBM independent MAE: **1.03614**
  - vs Ridge: **-17.2923%**
  - vs persistence: **-21.5850%**
  - seed SD: **0** (seed-invariant)
- LightGBM MinT MAE: **0.931141**
  - vs independent: **-10.1341%**
  - vs persistence: **-29.5316%**
- DLinear seed-mean independent MAE: **1.24866**
  - bottom-up effect: **-6.8448%**
  - seed SD: **0.00705637**; seed range: **0.377196**
- Best observed: `lightgbm+mint`
- Bottom-preserving alternative: `ridge+bottom_up`

### Memory

- EWMA MAE: **1.05127e+09** (strongest observed)
- Persistence / Ridge MAE: **1.05929e+09** / **1.08511e+09**
- DLinear seed-mean independent: **1.09112e+09**
- DLinear WLS/MinT vs independent: **-3.2242%** / **-3.3957%**
- DLinear WLS/MinT vs EWMA: **0.4438%** / **0.2658%**
- WLS vs EWMA seed-2 relative: **2.0567%**
- LightGBM vs EWMA: **36.8944%** (negative baseline)

### Disk / Peaks

- Persistence / EWMA / Ridge independent MAE: **1.55015e+09** / **1.55731e+09** / **1.75358e+09**
- Ridge BU vs independent: **13.9278%**
- Ridge TD vs independent: **0.0000%**
- DLinear memory peak bias all seeds: **True**

## Claim matrix

```
claim                                                                   statement classification                evidence_source
   A1                   LightGBM independent improves CPU over Ridge independent.      supported calculated_from_accepted_packs
   A2                LightGBM independent improves CPU over persistence and EWMA.      supported calculated_from_accepted_packs
   B1   MinT improves LightGBM CPU aggregate forecasts while restoring coherence.      supported calculated_from_accepted_packs
   B2              Bottom-up/WLS/MinT improve DLinear CPU forecasts across seeds.      supported calculated_from_accepted_packs
   B3                                Reconciliation improves Ridge CPU forecasts.      supported calculated_from_accepted_packs
   C1            WLS/MinT improve DLinear memory relative to DLinear independent.      supported calculated_from_accepted_packs
   C2                     Reconciled DLinear robustly outperforms EWMA on memory.   contradicted calculated_from_accepted_packs
   C3                            Memory reconciliation is universally beneficial.    unsupported calculated_from_accepted_packs
   D1                          Ridge bottom-up degrades aggregate disk forecasts.      supported calculated_from_accepted_packs
   D2               Ridge top-down preserves the independently forecast disk top.      supported calculated_from_accepted_packs
   D3             Top-down preserves disk top accuracy without bottom-level cost.   contradicted calculated_from_accepted_packs
   P1                        Reconciliation generally improves CPU high-load MAE.    unsupported calculated_from_accepted_packs
   P2 Reconciliation generally improves CPU peak recall without false-alarm cost.    unsupported calculated_from_accepted_packs
   P3          LightGBM remains the strongest CPU model during high-load periods.      supported calculated_from_accepted_packs
   P4                     Reconciliation generally improves memory peak behavior.    unsupported calculated_from_accepted_packs
   P5         DLinear memory peak compression persists across seeds (diagnostic).      supported calculated_from_accepted_packs
```

## Publication gates

{
  "gate1_reproducibility": "pass",
  "gate2_baseline_strength": "pass",
  "gate3_stochastic_robustness": "pass",
  "gate4_statistics": "pass",
  "gate5_practical_contribution": "pass",
  "gate6_breadth_negative_evidence": "pass",
  "gate7_novelty_risk": "pass",
  "gate8_honesty_limitations": "pass",
  "final_decision": "GO"
}

## Final decision

**GO**
