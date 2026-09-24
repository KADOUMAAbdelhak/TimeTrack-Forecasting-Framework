# Prospective DLinear Throughput Decision Criteria

Recorded before the first Neural-v2 scientific fit on 2026-09-23
(Europe/Helsinki).

The DLinear F1 throughput decision is based on macro averages over the exact
matched F0/F1 machine-fold-seed cells. Positive means lower F1 MAE than F0.

- `BROAD_POSITIVE`: overall mean MAE gain is positive; all 8 aggregate lead
  gains are positive; at least 5/7 machine means are positive; at least 4/5
  fold means are positive; and all 3 seed means are positive.
- `CONDITIONALLY_POSITIVE`: `BROAD_POSITIVE` is not met, but overall mean MAE
  gain is positive; at least 4/8 aggregate lead gains are positive; at least
  4/7 machine means are positive; at least 3/5 fold means are positive; and at
  least 2/3 seed means are positive.
- `BROAD_NEGATIVE`: overall mean MAE gain is negative; at least 6/8 aggregate
  lead gains are negative; at least 5/7 machine means are negative; at least
  4/5 fold means are negative; and all 3 seed means are negative.
- `NEUTRAL`: every other result pattern.

These are descriptive consistency criteria, not statistical-significance
rules. They must not be changed after scientific DLinear results are observed.
