# Amendment A3 run record

- **Code:** commit 15231570d85ee5dbc369f33703c91e31b6fab0d7, the target of the annotated tag `fgcs-v04-a3-validation-gate`. The package
  was unchanged when the run started.
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
