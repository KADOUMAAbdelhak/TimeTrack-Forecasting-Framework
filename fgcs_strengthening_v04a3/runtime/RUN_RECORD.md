# Amendment A3 run record

- **Code:** commit 15231570d85ee5dbc369f33703c91e31b6fab0d7, the target of the annotated tag `fgcs-v04-a3-validation-gate`
  (tag object 4a1e8d993366f7a3a0509a2da10c1161a3c5460c), created before the run. The package was unchanged when the run
  started.
- **Public tag:** `fgcs-v04-a3-validation-gate-r2` on commit 9ca21ff7c4823406bc0f82ffdbbd567e36a631a4. It was created
  after the run, on a history rewritten to leave out internal working notes. Its A3 package files are byte-identical to
  the run commit: package digest fae2173d…2836, unchanged. The first tag and commit are not in the public history.
- **Command:** `python -m fgcs_strengthening_v04a3.analyse_gate --run fgcs_strengthening_v04a3/runtime/analysis_a3.json`
  (OMP/MKL/OPENBLAS_NUM_THREADS=1).
- **Compute:** 146.9 s wall, 130.0 s user CPU, 1.35 GB peak resident memory (`analysis_a3.time`). No model was fitted.
- **Output:** `analysis_a3.json`, SHA-256 33e11a858ea338b3c3ff25bec2f59527a3a2100a386658443def77956501cee0.
- **Guards passed:**
  - tier-1 seed means matched the published cells (largest relative difference 3.0e-13);
  - 104 tier-2 contrasts were reproduced exactly;
  - the reference cost-cell counts were 22 and 13;
  - the persistence windows matched the recorded splits.
- **Verdicts, as printed in `analysis_a3.log`:**
  - H-A3a: "rarely consolidates" in tier 1 and in tier 2;
  - H-A3b: "detects" in 12 of 14 frames;
  - H-A3c: "grouping adds savings";
  - fallback: "fallback does not restore positive skill".
- **Post-hoc note (23 Nov 2026):** `analysis_a3.time` records numpy divide-by-zero warnings from the H-A3b statistic
  (`gate.py`, `detection`).
  - **Cause:** in tier-1 Rnd, tier-2 LSTM Rnd and tier-2 PatchTST-style Rnd, 3 units each have an S2 outer MAE of exactly
    zero at one horizon. Their outer scores are undefined, and the frozen statistic ranks them instead of dropping them.
  - **Check:** `manuscript/fgcs/tools/a3_zero_reference_check.py` reproduces the frozen values, then drops those units.
    Its output is `manuscript/fgcs/tools/derived/a3_zero_reference_check.json`, SHA-256 0250a457…0a44.
  - **Effect:** rho changes by at most 0.032 and no verdict changes.
  - **Scope:** no other A3 statistic is affected. The gates use validation errors only, and the accuracy statistics
    exclude zero references. The frozen output is unchanged.
