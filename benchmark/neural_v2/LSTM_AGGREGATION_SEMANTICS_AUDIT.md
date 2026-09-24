# LSTM Aggregation Semantics Audit

## Accepted conclusion

The completed LSTM report displayed F0 and F1 MAEs as equal-weight means of
run-level MAEs over 105 matched `machine x fold x seed` cells per lead. Its
reported context gain was a different valid aggregation: the equal-weight mean
of the 105 within-cell relative MAE gains.

The prospective LSTM decision criterion was written before the first LSTM fit
and explicitly used macro averages over matched machine-fold-seed cells. The
implemented mean matched cell-level relative MAE gain is therefore
authoritative for the prospective **CONDITIONALLY_POSITIVE** label.

Prospective quantities preserved without reinterpretation:

- overall mean matched cell-relative gain: **+3.087%**;
- positive lead cell-means: **8/8**;
- positive machine aggregates under the prospective criterion: **4/7**;
- positive fold aggregates: **5/5**; and
- positive seed aggregates: **3/3**.

## Alternative LSTM summaries

Ordered by real lead `[1, 2, 4, 8, 16, 32, 64, 128]`:

- mean cell-relative gain:
  `[+2.3506, +2.9622, +3.4866, +2.1845, +1.6932, +3.1350, +4.2120, +4.6748]%`;
- ratio of macro-aggregated MAEs:
  `[-2.4070, +1.1140, +1.9758, +1.0353, +1.1072, +1.9034, +2.3134, +2.0461]%`;
- pooled-prediction gain:
  `[-2.8834, +0.6066, +1.5792, +0.6363, +0.8141, +1.5917, +1.8542, +1.6404]%`.

Overall:

- mean cell-relative gain: **+3.087%**;
- ratio of macro-aggregated MAEs: **+1.252%**; and
- pooled-prediction gain: **+0.849%**.

Lead 1 is positive under the prospective cell-relative metric but negative
under both absolute-error-oriented summaries. Positive lead-1 cells generally
had smaller baseline MAE, while fewer negative cells had substantially larger
baseline MAE and larger absolute degradation. Prediction-count differences
slightly strengthened, but did not cause, the reversal. Leads 2 through 128 are
positive under all three summaries.

## Reporting consequence

The post-audit reporting convention is frozen separately in
`CROSS_MODEL_AGGREGATION_STANDARD.md`. It does not retroactively redefine the
prospective LSTM decision or any earlier accepted decision label.
