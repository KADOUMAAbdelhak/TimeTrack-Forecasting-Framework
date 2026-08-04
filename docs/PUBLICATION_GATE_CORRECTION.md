# Publication gate correction

Date: 2026-08-04

## Superseded decision

The report `docs/FGCS_PUBLICATION_READINESS.md` initially concluded **GO**.
That conclusion is **not accepted**.

The pre-correction snapshot is preserved as:

    docs/FGCS_PUBLICATION_READINESS_PRE_ROBUSTNESS.md

It retains the original GO result, provenance, and the disclosure that EWMA and
multiple seeds were absent.

## Why GO was incorrect

Against the **unchanged** pre-registered gates in `docs/PUBLICATION_GATES.md`:

1. **Gate 2** was not fully satisfied because **EWMA was absent** from the final
   baseline set (only persistence / Ridge / LightGBM / DLinear were frozen).

2. **Gate 3** was not satisfied because stochastic models used **seed 0 only**
   (LightGBM and DLinear), not ≥3 seeds.

3. **Gate 4** prohibits deriving a primary claim from a **single seed**.

## Correct current status

**CONDITIONAL GO**

- Existing frozen prediction packs under `experiment-freeze-v2` remain valid.
- Frozen analysis/reporting tags remain valid and are not modified.
- A compact robustness extension (`final-robustness-extension-freeze-v1`) will
  add EWMA baselines and seeds 1–2 for LightGBM/DLinear.
- The final GO / CONDITIONAL GO / NO-GO decision is deferred until that
  extension completes.

Do not alter the pre-registered gate definitions.
