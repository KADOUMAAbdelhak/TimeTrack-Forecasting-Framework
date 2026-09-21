# Phase 1C Rolling-Origin Robustness Report

This is rolling-origin robustness analysis on the **same TimeTrack dataset**,
not an independent replication dataset. It does not redefine Phase 1B.

## Frozen design

Seven machine CPU targets, eight frozen leads, seven predeclared candidates,
and five expanding chronological folds produced 1960 fold-level
experiments. Every fold applies lead-aware target-time purging, global training
across canonical segments, train-only feature scaling, and matched baseline
and augmented rows.

## Candidate-level stability

- Throughput: median machine/lead fold-median gain
  0.769%; ROBUST_POSITIVE
  15, CONSISTENT_SMALL_POSITIVE
  8, MIXED 25, NEGATIVE
  8.
- LOMO CPU mean: median -0.045%; ROBUST_POSITIVE
  5, small-positive 10.
- LOMO CPU median: median 0.156%; ROBUST_POSITIVE
  8, small-positive 4.
- Memory: median 0.069%; ROBUST_POSITIVE
  6, NEGATIVE 25.
- Used disk: median -0.088%; ROBUST_POSITIVE
  8, NEGATIVE 26.
- Mean RTT: median 0.219%; ROBUST_POSITIVE
  3, NEGATIVE 7.
- Jitter: median 0.285%; ROBUST_POSITIVE
  5, NEGATIVE 5.

## CPU-throughput lead evidence

 lead  median_fold_level_mae_gain_pct  median_machine_level_gain_pct  sample_weighted_mae_gain_pct  n_ROBUST_POSITIVE  n_CONSISTENT_SMALL_POSITIVE  n_MIXED  n_NEGATIVE  n_INSUFFICIENT_FOLDS  positive_machine_fold_fraction worst_machine  worst_machine_median_gain_pct best_machine  best_machine_median_gain_pct
    1                        0.723289                       0.780447                     -0.360366                  2                            1        3           1                     0                        0.685714     machine01                      -2.418711    machine06                      5.781136
    2                        0.797389                      -0.011768                      0.403899                  1                            0        4           2                     0                        0.542857     machine01                      -1.038969    machine04                      6.851021
    4                        1.522214                       0.756699                      1.386018                  2                            2        3           0                     0                        0.857143     machine01                       0.109608    machine04                      4.762634
    8                        0.639405                       0.639405                      1.200622                  1                            1        4           1                     0                        0.657143     machine06                      -0.533026    machine03                      3.886041
   16                        0.535503                       0.271124                      0.262426                  1                            2        3           1                     0                        0.685714     machine01                      -0.539039    machine06                      2.773733
   32                        1.157966                       1.133884                      0.531892                  3                            1        2           1                     0                        0.800000     machine01                      -0.252371    machine02                      3.189444
   64                        0.480026                       0.478581                      0.401651                  2                            1        4           0                     0                        0.714286     machine01                       0.029600    machine02                      2.604224
  128                        0.722508                       1.002916                      0.657473                  3                            0        2           2                     0                        0.657143     machine01                      -0.907091    machine02                      6.923719

## Explicit robustness questions

1. **Does CPU <- throughput remain positive across chronological folds?**
   Yes on a substantial but nonuniform subset: throughput has 15 ROBUST_POSITIVE and
   8 CONSISTENT_SMALL_POSITIVE machine/lead rows;
   25 MIXED rows show material regime dependence.
2. **On how many machines?** 5 machines have at
   least one ROBUST_POSITIVE throughput lead; 5
   have at least one robust or consistent-small-positive lead. Robust machines
   are ['machine02', 'machine03', 'machine05', 'machine06', 'machine07'].
3. **At which future leads?** Frozen decision-gate throughput support occurs at
   [1, 4, 32, 64, 128]; the best-supported throughput leads by
   robust count and weighted gain are [128, 32, 4].
4. **Are effects concentrated in particular machines?** Yes. Machine03 is
   ROBUST_POSITIVE at six leads, machine02 at four, machine07 at three, and
   machines05/06 at one each; machine01 and machine04 have none. The effect is
   multi-machine but not uniform.
5. **Are gains stable or highly regime-dependent?** ROBUST_POSITIVE and
   CONSISTENT_SMALL_POSITIVE require at least four positive folds. MIXED rows
   explicitly identify regime dependence; throughput has
   25 MIXED machine/lead rows.
6. **Does leave-one-machine-out CPU context outperform throughput?** Across the
   eight lead medians, context wins at
   0
   leads and throughput wins at
   8.
   Throughput therefore has the stronger broad median at every lead, although
   common context meets its separate robustness gate at lead 16.
7. **Does mean or median common-system context work better?** LOMO mean has
   5 robust rows and median gain
   -0.045%; LOMO median has 8
   robust rows and median gain 0.156%. Median context
   is stronger overall, while mean context supplies the two-machine robust
   support at lead 16.
8. **Do memory/disk contexts remain mostly non-beneficial?** Not uniformly.
   Memory's median is 0.069% with 6
   robust and 25 NEGATIVE rows; disk's median is
   -0.088% with 8 robust and
   26 NEGATIVE rows. Both are highly heterogeneous and are
   weaker primary evidence than throughput.
9. **Do RTT/jitter remain non-beneficial?** No, not uniformly across rolling
   folds. RTT's median is 0.219% with 3 robust
   rows; jitter's is 0.285% with 5.
   Their gains are mostly small and remain comparison evidence, not the
   primary hypothesis.
10. **Does cross-signal value become stronger or weaker as lead increases?**
    It is nonmonotonic. Throughput median gain peaks at lead 4, rises again at
    32, and remains positive but smaller at 64/128; common-context medians
    become more favorable from roughly lead 16 onward.
11. **Which leads have the strongest multi-fold evidence?** Throughput:
    [128, 32, 4]; common-context decision support:
    [16].
12. **Does Phase 1C support proceeding to a context-aware CPU forecasting
    model?** Yes, under the frozen gate.
13. **Does Phase 1C support a full joint multi-metric target model?** No. This
    robustness phase tests CPU as the sole target and cannot establish a joint
    multi-target design.
14. **Does Phase 1C support explicit multi-machine modeling, or is compact
    common-system context sufficient?**
    Common-system context meets the frozen multi-machine gate.
    This phase tests compact context, not a full explicit multi-machine model.

## Limitations

- All folds come from one dataset and are not external replication.
- Canonical segments constrain valid windows, and regimes are not guaranteed
  independent.
- Ridge measures incremental linear information only.
- The target is CPU only; conclusions cannot be generalized to joint
  memory/disk targets.
- Multiple machine/lead comparisons remain exploratory robustness evidence.

## Decision Gate for Model Development

**PROCEED_WITH_BOTH**
