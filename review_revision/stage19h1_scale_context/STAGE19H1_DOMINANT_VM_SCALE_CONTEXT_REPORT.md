# STAGE 19H1 — Dominant-VM scale context audit

## Status and answer

**SCALE_INSTABILITY_NOT_SUPPORTED for both Materna T1 VM266 and T3 VM272.**
The specific explanation that their disk-write tails arise from an unusually
small training IQR is not supported by the existing frozen partitions.
Their log-space IQRs are at the upper end of the executed cohort and their
native IQRs are the largest. This does not identify why the models err or
establish a causal sharing mechanism.

No model was instantiated, fitted or called. No new prediction or test
evaluation was performed. All outputs of this audit are written only under
`review_revision/stage19h1_scale_context`; frozen results, manuscript,
supplement, bibliography and repository refs remain unchanged.

## 1. Cohort and partition definitions

The cohort is exactly the 35 frozen executed VMs, with original identifiers
preserved (including leading zeroes). The comparison is within the same
trace and outer fold, never pooled across traces, folds or VMs for fitting.

Two cohort views are distinguished:

1. **Actual selected-context cohort:** one final scaler per VM using that
   formulation's frozen selected context in the same fold. The headline
   table uses the M1 cohort; S1-disk and S2-disk views are also retained.
2. **Fixed-context cohort:** all 35 VMs at the same trace, fold and L as the
   dominant partition. This avoids mixing context lengths when locating
   each specific partition in its cohort. Appendix A covers all L=4/9/18
   final partitions, including unused contexts, so no relevant selected
   final partition is omitted. The three frozen seeds share context/scaler
   selection here and are not counted as three independent scale observations.

For a cohort value x, ascending rank is 1+#(values<x), with the tied rank
range ending at #(values≤x). Percentile is the empirical cumulative
percentage 100×#(values≤x)/35, including the dominant VM. These are descriptive
ranks, not an inferential percentile estimate. IQR/median-IQR divides the
dominant VM's IQR by the median of the 35 individual IQRs. It is not the IQR
of pooled training rows. No small-scale or concentration threshold is added.

Training quantiles use the exact frozen linear-interpolation convention.
The stored transformed median/IQR and native IQR were reproduced exactly
from the legal outer-training history/target row union. Native medians were
recovered directly from those native rows, not inferred by exponentiating
the log median: interpolation and a nonlinear inverse need not commute.
Native units remain the original disk-write KB/s; transformed statistics
are in natural-log1p coordinates.

## 2. Actual M1-selected cohort: fold-by-fold scale context

M1 selected L=18 in all five folds for both dominant VMs. The cohort uses
each of the other VMs' actual frozen M1 context for the same fold. Numbers
are rounded only for display; `analysis.json` retains the full numeric
values, cohort vectors, partition hashes, usage mapping and check identities.

| Trace / VM | Fold | Log median | Log IQR | Log-IQR rank (ECDF) | Cohort log-IQR min / median / max | IQR / cohort median |
| --- | --- | --- | --- | --- | --- | --- |
| Materna-T1 / 266 | 1 | 5.323010 | 4.861575 | 33/35 (94.29%) | 0.048009 / 0.593662 / 5.983936 | 8.189134 |
| Materna-T1 / 266 | 2 | 5.298317 | 4.872356 | 34/35 (97.14%) | 0.048009 / 0.608929 / 5.595176 | 8.001516 |
| Materna-T1 / 266 | 3 | 5.293305 | 4.872499 | 34/35 (97.14%) | 0.048009 / 0.612458 / 5.563562 | 7.955643 |
| Materna-T1 / 266 | 4 | 5.288267 | 4.877984 | 34/35 (97.14%) | 0.048009 / 0.620827 / 5.451038 | 7.857242 |
| Materna-T1 / 266 | 5 | 5.283204 | 4.883498 | 34/35 (97.14%) | 0.048009 / 0.616651 / 5.172612 | 7.919385 |
| Materna-T3 / 272 | 1 | 5.257495 | 4.908503 | 35/35 (100.00%) | 0.052644 / 0.646848 / 4.908503 | 7.588339 |
| Materna-T3 / 272 | 2 | 5.257495 | 4.904370 | 35/35 (100.00%) | 0.068993 / 0.639708 / 4.904370 | 7.666574 |
| Materna-T3 / 272 | 3 | 5.257495 | 4.908543 | 35/35 (100.00%) | 0.068993 / 0.639756 / 4.908543 | 7.672527 |
| Materna-T3 / 272 | 4 | 5.257495 | 4.908543 | 35/35 (100.00%) | 0.068993 / 0.635353 / 4.908543 | 7.725691 |
| Materna-T3 / 272 | 5 | 5.257495 | 4.908543 | 35/35 (100.00%) | 0.068993 / 0.632987 / 4.908543 | 7.754574 |

| Trace / VM | Fold | Log-median rank (ECDF) | Native median | Native IQR | Native-IQR rank (ECDF) | Cohort native-IQR min / median / max | Native IQR / cohort median |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Materna-T1 / 266 | 1 | 30/35 (85.71%) | 204.00 | 24235.00 | 35/35 (100.00%) | 1.000000 / 13.000000 / 24235.000000 | 1864.230769 |
| Materna-T1 / 266 | 2 | 30/35 (85.71%) | 199.00 | 24240.50 | 35/35 (100.00%) | 1.000000 / 13.000000 / 24240.500000 | 1864.653846 |
| Materna-T1 / 266 | 3 | 30/35 (85.71%) | 198.00 | 24244.00 | 35/35 (100.00%) | 1.000000 / 14.000000 / 24244.000000 | 1731.714286 |
| Materna-T1 / 266 | 4 | 29/35 (82.86%) | 197.00 | 24248.00 | 35/35 (100.00%) | 1.000000 / 13.000000 / 24248.000000 | 1865.230769 |
| Materna-T1 / 266 | 5 | 29/35 (82.86%) | 196.00 | 24252.00 | 35/35 (100.00%) | 1.000000 / 12.000000 / 24252.000000 | 2021.000000 |
| Materna-T3 / 272 | 1 | 30/35 (85.71%) | 191.00 | 24333.00 | 35/35 (100.00%) | 1.000000 / 14.000000 / 24333.000000 | 1738.071429 |
| Materna-T3 / 272 | 2 | 30/35 (85.71%) | 191.00 | 24332.25 | 35/35 (100.00%) | 1.000000 / 13.000000 / 24332.250000 | 1871.711538 |
| Materna-T3 / 272 | 3 | 30/35 (85.71%) | 191.00 | 24334.00 | 35/35 (100.00%) | 1.000000 / 14.000000 / 24334.000000 | 1738.142857 |
| Materna-T3 / 272 | 4 | 30/35 (85.71%) | 191.00 | 24334.00 | 35/35 (100.00%) | 1.000000 / 14.000000 / 24334.000000 | 1738.142857 |
| Materna-T3 / 272 | 5 | 30/35 (85.71%) | 191.00 | 24334.00 | 35/35 (100.00%) | 1.000000 / 19.000000 / 24334.000000 | 1280.736842 |

Native-median ranks match the log-median ranks for these dominant
partitions, but the medians themselves are independently calculated from
native rows. Complete median distributions/ranks for both scale coordinates
are in Appendix A and the full-precision audit record.

### Separate fold summaries

**Materna-T1 VM266: SCALE_INSTABILITY_NOT_SUPPORTED.**
The actual M1 log IQR ranges from 4.861575 to
4.883498, with ascending ranks
33–34/35
(94.29–97.14% ECDF).
It is 7.857242–8.189134
times the cohort median IQR. Its native IQR is
24235.00–24252.00 KB/s,
rank 35/35 in every fold. Log-median rank is
29–30/35.
These values place the VM at the upper, not lower, end of the training-scale
distribution. No threshold for “near the minimum” is needed to establish
that the observed dominant scale is not in the lower cohort tail.

**Materna-T3 VM272: SCALE_INSTABILITY_NOT_SUPPORTED.**
The actual M1 log IQR ranges from 4.904370 to
4.908543, with ascending ranks
35/35
(100.00% ECDF).
It is 7.588339–7.754574
times the cohort median IQR. Its native IQR is
24332.25–24334.00 KB/s,
rank 35/35 in every fold. Log-median rank is
30/35.
These values place the VM at the upper, not lower, end of the training-scale
distribution. No threshold for “near the minimum” is needed to establish
that the observed dominant scale is not in the lower cohort tail.

The selected S1-disk/S2-disk cohort views also place both dominant
VMs' log and native IQRs above their corresponding cohort medians; the
classification does not depend on restricting the view to M1. The fixed-L
cohort comparisons give the same bounded conclusion. Different cohort
context choices can change min/median/max slightly, so they are not silently
combined with the actual M1-selected values above.

## 3. Fresh conformance checks, not model reruns

- **1,050 final training partitions reconstructed:** two traces × 35 VMs ×
  five folds × three contexts. Every fit-row count, timestamp SHA-256,
  transformed disk median/IQR and native disk IQR matches the frozen scaler
  manifest exactly. All 1,050 native medians are directly recoverable.
- Raw archive SHA-256 remains
  `1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4`.
  The frozen reader and physical-validity cleaner were reused read-only.
- Training-origin and test-origin hashes match the frozen support manifest.
  Final fit rows are exactly the historical/target row union for legal
  outer-training origins. All fit timestamps and all training target times
  precede the first outer-test origin. The former inner-validation rows may
  legitimately belong to the final outer-training refit; outer-test data do not.
- **3,150 original final completion scalers checked:** S1-disk, S2-disk and
  M1 for all 35 VMs in both traces, five folds and three seeds. They are
  finite with positive IQRs, match their exact final partition, and record
  `complete_legal_outer_train_only`, one completed final test evaluation and
  the correct training/test support hashes. The pre-existing technical
  validations remain PASS with zero recorded violations.
- **90 dominant-VM saved prediction files** (two VMs × three formulations ×
  five folds × three seeds) have finite targets/scaled/native/unclipped
  predictions and the expected saved support. For every saved row,
  `expm1(z × transformed_IQR + transformed_median)` exactly reproduces the
  saved unclipped prediction; `max(native,0)` exactly reproduces the saved
  projected prediction. There is no upper clipping. Checkpoint and prediction
  file hashes match the original registries/completions. No checkpoint was
  executed and no new MAE or test score was computed.

Stage18A1 §13 had already reconstructed all 3,150 inner/final scaler
partitions across all three Materna traces and reported large dominant-VM
IQRs. This audit freshly checks only the 1,050 **final** partitions of T1/T3
and adds within-cohort ranks. Its ranges need not equal Stage18A1's ranges
over inner plus final partitions. The source manifest and raw archive agree
exactly, not merely within display precision. Existing G1 finite-checkpoint
and broader fitting diagnostics are preserved rather than rerun or overstated.

## 4. Exact manuscript-safe conclusion

> A post-hoc audit of the frozen outer-training partitions did not support
> unusually small training IQRs as an explanation for the dominant Materna
> disk-write tails. T1 VM266 and T3 VM272 had log-space IQRs near the upper
> end of their respective 35-VM cohorts and the largest native IQRs across
> all five M1 folds. Training-only scaler values and saved inverse
> transforms/projection reproduced exactly. These checks demonstrate no
> scaler or inversion defect, but do not identify a causal sharing mechanism
> or exclude other optimisation and modelling limitations.

A large, correctly implemented log-space scale can amplify finite scaled
errors after exponentiation; this algebraic possibility does not establish
its causal contribution to observed tails. Finite artifacts also do not
prove ideal optimisation. No new numerical instability cutoff, significance
claim, cross-block pooling or attribution to sharing alone is introduced.

**Implementation defect demonstrated: NO. Further experiment scientifically
required for this concern: NO.** No corrective rerun is justified by the
specific small-training-IQR hypothesis on these existing artifacts.

## 5. Provenance and preservation

Direct inputs and scripts are bound by `input_sha256_inventory.json`;
`analysis.json` contains all 1,050 cohort partitions, all 30 dominant fixed-L
partitions, 30 actual selected-context cohort comparisons, 3,150 completion
identities and 90 saved-inverse checks. Hash inventories and before/after
preservation records are included in this directory. No prior report is edited.

Both protected-tree scans verify all **395,787** files unchanged, including
the current manuscript and new G2 supplement. The 25 C1, 19 G1 and 47 G2
output hashes are also reverified. Refs/branch remain unchanged and the index
has no staged changes. `git diff --check` passes. The final verification
record gates PASS on these checks and rehashes every directly read input.

Training=0; inference=0; manuscript modifications=0; scientific modifications=0;
frozen/post-hoc artifact modifications=0; commit=no; push=no.

## Appendix A. Every dominant-VM final partition and fixed-L cohort

All 30 manifest partitions are shown below. “Uses” lists the original final
formulations that actually selected the partition, each for seeds 0/1/2.
An em dash means the final scaler was frozen but not selected by these
dominant-VM disk/M1 fits. Native summaries were recovered from the exact
original native training rows; no interpolation from log summaries is used.

### Materna-T1 VM266: final partition values

| Fold | L | Uses (all three seeds) | Fit rows | Log median | Log IQR | Native median KB/s | Native IQR KB/s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 4 | — | 4161 | 5.323010 | 4.861575 | 204.00 | 24235.00 |
| 1 | 9 | S1 | 4166 | 5.323010 | 4.861575 | 204.00 | 24235.00 |
| 1 | 18 | M1, S2 | 4175 | 5.323010 | 4.861575 | 204.00 | 24235.00 |
| 2 | 4 | — | 4993 | 5.298317 | 4.872377 | 199.00 | 24241.00 |
| 2 | 9 | S1 | 4998 | 5.298317 | 4.872377 | 199.00 | 24241.00 |
| 2 | 18 | M1, S2 | 5007 | 5.298317 | 4.872356 | 199.00 | 24240.50 |
| 3 | 4 | — | 5824 | 5.293305 | 4.872499 | 198.00 | 24244.00 |
| 3 | 9 | — | 5829 | 5.293305 | 4.872499 | 198.00 | 24244.00 |
| 3 | 18 | M1, S1, S2 | 5838 | 5.293305 | 4.872499 | 198.00 | 24244.00 |
| 4 | 4 | — | 6656 | 5.288267 | 4.878025 | 197.00 | 24249.00 |
| 4 | 9 | S1 | 6661 | 5.288267 | 4.878025 | 197.00 | 24249.00 |
| 4 | 18 | M1, S2 | 6670 | 5.288267 | 4.877984 | 197.00 | 24248.00 |
| 5 | 4 | — | 7488 | 5.283204 | 4.883498 | 196.00 | 24252.00 |
| 5 | 9 | — | 7493 | 5.283204 | 4.883498 | 196.00 | 24252.00 |
| 5 | 18 | M1, S1, S2 | 7502 | 5.283204 | 4.883498 | 196.00 | 24252.00 |

### Materna-T1 VM266: log-space fixed-L cohort context

| Fold/L | Median rank (ECDF) | IQR rank (ECDF) | Cohort median min / median / max | Cohort IQR min / median / max | IQR / cohort median IQR |
| --- | --- | --- | --- | --- | --- |
| 1/4 | 30/35 (85.71%) | 33/35 (94.29%) | 0.000000 / 3.688879 / 7.509883 | 0.048009 / 0.593662 / 5.983936 | 8.189134 |
| 1/9 | 30/35 (85.71%) | 33/35 (94.29%) | 0.000000 / 3.688879 / 7.509883 | 0.048009 / 0.593662 / 5.979517 | 8.189134 |
| 1/18 | 30/35 (85.71%) | 33/35 (94.29%) | 0.000000 / 3.688879 / 7.509883 | 0.048009 / 0.591565 / 5.964864 | 8.218155 |
| 2/4 | 30/35 (85.71%) | 34/35 (97.14%) | 0.000000 / 3.688879 / 7.509883 | 0.048009 / 0.608929 / 5.636125 | 8.001550 |
| 2/9 | 30/35 (85.71%) | 34/35 (97.14%) | 0.000000 / 3.688879 / 7.509883 | 0.048009 / 0.608929 / 5.628068 | 8.001550 |
| 2/18 | 30/35 (85.71%) | 34/35 (97.14%) | 0.000000 / 3.688879 / 7.509883 | 0.048009 / 0.608929 / 5.595176 | 8.001516 |
| 3/4 | 30/35 (85.71%) | 34/35 (97.14%) | 0.000000 / 3.713572 / 7.510431 | 0.048009 / 0.612458 / 5.563562 | 7.955643 |
| 3/9 | 30/35 (85.71%) | 34/35 (97.14%) | 0.000000 / 3.713572 / 7.510431 | 0.048009 / 0.612458 / 5.560682 | 7.955643 |
| 3/18 | 30/35 (85.71%) | 34/35 (97.14%) | 0.000000 / 3.713572 / 7.510431 | 0.048009 / 0.612458 / 5.541264 | 7.955643 |
| 4/4 | 29/35 (82.86%) | 34/35 (97.14%) | 0.000000 / 3.737670 / 7.510431 | 0.048009 / 0.620827 / 5.455319 | 7.857308 |
| 4/9 | 29/35 (82.86%) | 34/35 (97.14%) | 0.000000 / 3.737670 / 7.510431 | 0.048009 / 0.620827 / 5.451038 | 7.857308 |
| 4/18 | 29/35 (82.86%) | 34/35 (97.14%) | 0.000000 / 3.737670 / 7.510431 | 0.048009 / 0.620827 / 5.434813 | 7.857242 |
| 5/4 | 29/35 (82.86%) | 34/35 (97.14%) | 0.000000 / 3.737670 / 7.510431 | 0.048009 / 0.616651 / 5.186687 | 7.919385 |
| 5/9 | 29/35 (82.86%) | 34/35 (97.14%) | 0.000000 / 3.737670 / 7.510431 | 0.048009 / 0.616651 / 5.182485 | 7.919385 |
| 5/18 | 29/35 (82.86%) | 34/35 (97.14%) | 0.000000 / 3.725621 / 7.510431 | 0.048009 / 0.616651 / 5.172612 | 7.919385 |

### Materna-T1 VM266: native-unit fixed-L cohort context (KB/s)

| Fold/L | Median rank (ECDF) | IQR rank (ECDF) | Cohort median min / median / max | Cohort IQR min / median / max | IQR / cohort median IQR |
| --- | --- | --- | --- | --- | --- |
| 1/4 | 30/35 (85.71%) | 35/35 (100.00%) | 0.000000 / 39.000000 / 1825.000000 | 1.000000 / 13.000000 / 24235.000000 | 1864.230769 |
| 1/9 | 30/35 (85.71%) | 35/35 (100.00%) | 0.000000 / 39.000000 / 1825.000000 | 1.000000 / 13.000000 / 24235.000000 | 1864.230769 |
| 1/18 | 30/35 (85.71%) | 35/35 (100.00%) | 0.000000 / 39.000000 / 1825.000000 | 1.000000 / 13.000000 / 24235.000000 | 1864.230769 |
| 2/4 | 30/35 (85.71%) | 35/35 (100.00%) | 0.000000 / 39.000000 / 1825.000000 | 1.000000 / 13.000000 / 24241.000000 | 1864.692308 |
| 2/9 | 30/35 (85.71%) | 35/35 (100.00%) | 0.000000 / 39.000000 / 1825.000000 | 1.000000 / 13.000000 / 24241.000000 | 1864.692308 |
| 2/18 | 30/35 (85.71%) | 35/35 (100.00%) | 0.000000 / 39.000000 / 1825.000000 | 1.000000 / 13.000000 / 24240.500000 | 1864.653846 |
| 3/4 | 30/35 (85.71%) | 35/35 (100.00%) | 0.000000 / 40.000000 / 1826.000000 | 1.000000 / 14.000000 / 24244.000000 | 1731.714286 |
| 3/9 | 30/35 (85.71%) | 35/35 (100.00%) | 0.000000 / 40.000000 / 1826.000000 | 1.000000 / 14.000000 / 24244.000000 | 1731.714286 |
| 3/18 | 30/35 (85.71%) | 35/35 (100.00%) | 0.000000 / 40.000000 / 1826.000000 | 1.000000 / 14.000000 / 24244.000000 | 1731.714286 |
| 4/4 | 29/35 (82.86%) | 35/35 (100.00%) | 0.000000 / 41.000000 / 1826.000000 | 1.000000 / 13.000000 / 24249.000000 | 1865.307692 |
| 4/9 | 29/35 (82.86%) | 35/35 (100.00%) | 0.000000 / 41.000000 / 1826.000000 | 1.000000 / 13.000000 / 24249.000000 | 1865.307692 |
| 4/18 | 29/35 (82.86%) | 35/35 (100.00%) | 0.000000 / 41.000000 / 1826.000000 | 1.000000 / 13.000000 / 24248.000000 | 1865.230769 |
| 5/4 | 29/35 (82.86%) | 35/35 (100.00%) | 0.000000 / 41.000000 / 1826.000000 | 1.000000 / 12.000000 / 24252.000000 | 2021.000000 |
| 5/9 | 29/35 (82.86%) | 35/35 (100.00%) | 0.000000 / 41.000000 / 1826.000000 | 1.000000 / 12.000000 / 24252.000000 | 2021.000000 |
| 5/18 | 29/35 (82.86%) | 35/35 (100.00%) | 0.000000 / 40.500000 / 1826.000000 | 1.000000 / 12.000000 / 24252.000000 | 2021.000000 |

### Materna-T3 VM272: final partition values

| Fold | L | Uses (all three seeds) | Fit rows | Log median | Log IQR | Native median KB/s | Native IQR KB/s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 4 | — | 5169 | 5.257495 | 4.908503 | 191.00 | 24333.00 |
| 1 | 9 | S1 | 5174 | 5.257495 | 4.908503 | 191.00 | 24333.00 |
| 1 | 18 | M1, S2 | 5183 | 5.257495 | 4.908503 | 191.00 | 24333.00 |
| 2 | 4 | — | 6202 | 5.257495 | 4.902993 | 191.00 | 24332.00 |
| 2 | 9 | S2 | 6207 | 5.257495 | 4.902993 | 191.00 | 24332.00 |
| 2 | 18 | M1, S1 | 6216 | 5.257495 | 4.904370 | 191.00 | 24332.25 |
| 3 | 4 | — | 7236 | 5.257495 | 4.908543 | 191.00 | 24334.00 |
| 3 | 9 | S2 | 7241 | 5.257495 | 4.908543 | 191.00 | 24334.00 |
| 3 | 18 | M1, S1 | 7250 | 5.257495 | 4.908543 | 191.00 | 24334.00 |
| 4 | 4 | — | 8269 | 5.257495 | 4.908543 | 191.00 | 24334.00 |
| 4 | 9 | — | 8274 | 5.257495 | 4.908543 | 191.00 | 24334.00 |
| 4 | 18 | M1, S1, S2 | 8283 | 5.257495 | 4.908543 | 191.00 | 24334.00 |
| 5 | 4 | — | 9302 | 5.257495 | 4.908543 | 191.00 | 24334.00 |
| 5 | 9 | S1, S2 | 9307 | 5.257495 | 4.908543 | 191.00 | 24334.00 |
| 5 | 18 | M1 | 9316 | 5.257495 | 4.908543 | 191.00 | 24334.00 |

### Materna-T3 VM272: log-space fixed-L cohort context

| Fold/L | Median rank (ECDF) | IQR rank (ECDF) | Cohort median min / median / max | Cohort IQR min / median / max | IQR / cohort median IQR |
| --- | --- | --- | --- | --- | --- |
| 1/4 | 30/35 (85.71%) | 35/35 (100.00%) | 0.693147 / 2.995732 / 6.645091 | 0.052644 / 0.646848 / 4.908503 | 7.588339 |
| 1/9 | 30/35 (85.71%) | 35/35 (100.00%) | 0.693147 / 2.995732 / 6.644440 | 0.052644 / 0.646848 / 4.908503 | 7.588339 |
| 1/18 | 30/35 (85.71%) | 35/35 (100.00%) | 0.693147 / 2.995732 / 6.643790 | 0.052644 / 0.646848 / 4.908503 | 7.588339 |
| 2/4 | 30/35 (85.71%) | 35/35 (100.00%) | 0.693147 / 2.995732 / 6.656727 | 0.068993 / 0.637448 / 4.902993 | 7.691593 |
| 2/9 | 30/35 (85.71%) | 35/35 (100.00%) | 0.693147 / 2.995732 / 6.655440 | 0.068993 / 0.637448 / 4.902993 | 7.691593 |
| 2/18 | 30/35 (85.71%) | 35/35 (100.00%) | 0.693147 / 2.995732 / 6.655440 | 0.068993 / 0.639708 / 4.904370 | 7.666574 |
| 3/4 | 30/35 (85.71%) | 35/35 (100.00%) | 0.693147 / 2.995732 / 6.664409 | 0.068993 / 0.639756 / 4.908543 | 7.672527 |
| 3/9 | 30/35 (85.71%) | 35/35 (100.00%) | 0.693147 / 2.995732 / 6.664409 | 0.068993 / 0.639756 / 4.908543 | 7.672527 |
| 3/18 | 30/35 (85.71%) | 35/35 (100.00%) | 0.693147 / 2.995732 / 6.664409 | 0.068993 / 0.639756 / 4.908543 | 7.672527 |
| 4/4 | 30/35 (85.71%) | 35/35 (100.00%) | 0.693147 / 2.995732 / 6.673298 | 0.068993 / 0.635353 / 4.908543 | 7.725691 |
| 4/9 | 30/35 (85.71%) | 35/35 (100.00%) | 0.693147 / 2.995732 / 6.673298 | 0.068993 / 0.635353 / 4.908543 | 7.725691 |
| 4/18 | 30/35 (85.71%) | 35/35 (100.00%) | 0.693147 / 2.995732 / 6.673298 | 0.068993 / 0.637515 / 4.908543 | 7.699489 |
| 5/4 | 30/35 (85.71%) | 35/35 (100.00%) | 0.693147 / 2.944439 / 6.678342 | 0.068993 / 0.630866 / 4.908543 | 7.780644 |
| 5/9 | 30/35 (85.71%) | 35/35 (100.00%) | 0.693147 / 2.944439 / 6.677083 | 0.068993 / 0.630866 / 4.908543 | 7.780644 |
| 5/18 | 30/35 (85.71%) | 35/35 (100.00%) | 0.693147 / 2.944439 / 6.677083 | 0.068993 / 0.632987 / 4.908543 | 7.754574 |

### Materna-T3 VM272: native-unit fixed-L cohort context (KB/s)

| Fold/L | Median rank (ECDF) | IQR rank (ECDF) | Cohort median min / median / max | Cohort IQR min / median / max | IQR / cohort median IQR |
| --- | --- | --- | --- | --- | --- |
| 1/4 | 30/35 (85.71%) | 35/35 (100.00%) | 1.000000 / 19.000000 / 768.000000 | 1.000000 / 14.000000 / 24333.000000 | 1738.071429 |
| 1/9 | 30/35 (85.71%) | 35/35 (100.00%) | 1.000000 / 19.000000 / 767.500000 | 1.000000 / 14.000000 / 24333.000000 | 1738.071429 |
| 1/18 | 30/35 (85.71%) | 35/35 (100.00%) | 1.000000 / 19.000000 / 767.000000 | 1.000000 / 14.000000 / 24333.000000 | 1738.071429 |
| 2/4 | 30/35 (85.71%) | 35/35 (100.00%) | 1.000000 / 19.000000 / 777.000000 | 1.000000 / 13.000000 / 24332.000000 | 1871.692308 |
| 2/9 | 30/35 (85.71%) | 35/35 (100.00%) | 1.000000 / 19.000000 / 776.000000 | 1.000000 / 13.000000 / 24332.000000 | 1871.692308 |
| 2/18 | 30/35 (85.71%) | 35/35 (100.00%) | 1.000000 / 19.000000 / 776.000000 | 1.000000 / 13.000000 / 24332.250000 | 1871.711538 |
| 3/4 | 30/35 (85.71%) | 35/35 (100.00%) | 1.000000 / 19.000000 / 783.000000 | 1.000000 / 14.000000 / 24334.000000 | 1738.142857 |
| 3/9 | 30/35 (85.71%) | 35/35 (100.00%) | 1.000000 / 19.000000 / 783.000000 | 1.000000 / 14.000000 / 24334.000000 | 1738.142857 |
| 3/18 | 30/35 (85.71%) | 35/35 (100.00%) | 1.000000 / 19.000000 / 783.000000 | 1.000000 / 14.000000 / 24334.000000 | 1738.142857 |
| 4/4 | 30/35 (85.71%) | 35/35 (100.00%) | 1.000000 / 19.000000 / 790.000000 | 1.000000 / 14.000000 / 24334.000000 | 1738.142857 |
| 4/9 | 30/35 (85.71%) | 35/35 (100.00%) | 1.000000 / 19.000000 / 790.000000 | 1.000000 / 14.000000 / 24334.000000 | 1738.142857 |
| 4/18 | 30/35 (85.71%) | 35/35 (100.00%) | 1.000000 / 19.000000 / 790.000000 | 1.000000 / 14.000000 / 24334.000000 | 1738.142857 |
| 5/4 | 30/35 (85.71%) | 35/35 (100.00%) | 1.000000 / 18.000000 / 794.000000 | 1.000000 / 19.000000 / 24334.000000 | 1280.736842 |
| 5/9 | 30/35 (85.71%) | 35/35 (100.00%) | 1.000000 / 18.000000 / 793.000000 | 1.000000 / 19.000000 / 24334.000000 | 1280.736842 |
| 5/18 | 30/35 (85.71%) | 35/35 (100.00%) | 1.000000 / 18.000000 / 793.000000 | 1.000000 / 19.000000 / 24334.000000 | 1280.736842 |

## Appendix B. Complete cohort distribution

The full unrounded vector for each 35-VM trace/fold/context group is retained
as the `cohort_partition_distribution` array in [analysis.json](/Users/fgtek002/TimeTrack/review_revision/stage19h1_scale_context/analysis.json).
Select the trace, fold and L to obtain the exact corresponding 35 rows.
Each row includes native and transformed summaries, fit timestamp and scaler
partition hashes, raw-member hash, fit-row count and the training/test boundary.
The `selected_context_cohort_comparisons` array contains each formulation's
actual selected-context reference distribution summaries; its 35-member
vectors are identified by the `completion_scaler_checks` context mapping.
No VM is dropped and no cross-VM model/scaler fitting is performed.

STAGE_19H1_PASS
