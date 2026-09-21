# Final evidence summary

## Headlines (exact aggregates)

### CPU (weighted-mean %)

- Persistence independent MAE (mean over folds/horizons): **1.3214**
  - h1=1.3203, h8=1.3160, h16=1.3278
- LightGBM independent vs persistence: **-21.58%**
- LightGBM MinT vs persistence: **-29.53%**
- LightGBM MinT vs LightGBM independent: **-10.13%**
- Ridge bottom_up vs independent: **-9.22%**
- DLinear bottom_up vs independent: **-7.04%**
- Best observed: `lightgbm+mint`
- Recommended operational: lightgbm+mint (accuracy/coherence); ridge+bottom_up when bottom preservation preferred

### Memory / Disk / Peaks

- Best observed memory: `dlinear+mint (by outer MAE)`
- Recommended memory: ridge/dlinear+mint or wls; persistence independent remains competitive baseline
- Disk Ridge BU vs independent: **14.83%**
- Best observed disk: `persistence+independent`
- Peaks: P3 supported; P1/P2/P4 unsupported; P5 partially supported

## Claim matrix

```
claim                                                                 statement             support  n_support  n_uncertain  n_contradict                                                                                   qualification
    A                       LightGBM improves CPU forecasting over persistence.           supported          9            0             0              CPU LightGBM independent vs persistence; separate Holm family; not reconciliation.
    B                  Reconciliation improves learned CPU aggregate forecasts.           supported         81            0             0                       CPU recon (ridge/lgbm/dlinear × BU/WLS/MinT); bottoms unchanged under BU.
    C                          WLS/MinT improve memory forecasts conditionally. partially_supported         24           12             0                     Memory WLS/MinT for Ridge/DLinear only; LightGBM remains negative baseline.
   D1                         Disk bottom-up harms learned aggregate forecasts.           supported          6            2             0                                         Ridge BU mean rel=0.1483; interpret separately from D2.
   D2 Disk top-down preserves the independently forecast top but harms bottoms.           supported          6            0             0 Top MAE unchanged; bottom macro degradation from trade-off tables (accuracy_costly at bottoms).
   P1                             General CPU peak benefit from reconciliation.         unsupported         77           85             0                                                       Persistence excluded from positive claim.
   P2                                            General CPU detection benefit.         unsupported         33          101            28                                                                   FA materiality threshold +5%.
   P3                                  LightGBM remains best for high-load CPU.           supported         18            0             0                                              Within 2% of best high-load MAE counts as support.
   P4                                              General memory peak benefit.         unsupported         22           38            12                                                                    LightGBM not in claim scope.
   P5                                          DLinear memory peak compression. partially_supported         61            0            11                                                              Independent bias must be negative.
```
