"""Format the completed existing-artifact scale audit; no new scientific endpoint."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
d=json.loads((OUT/'analysis.json').read_text())
def f(v,digits=6):return f'{v:.{digits}f}'
def extent(values,digits=None):
    low,high=min(values),max(values)
    show=lambda v:str(v) if digits is None else f(v,digits)
    return show(low) if low==high else show(low)+'–'+show(high)
def trip(m):return ' / '.join(f(m[k]) for k in ['cohort_min','cohort_median','cohort_max'])
def rank(m):
    a,b=m['ascending_rank_min'],m['ascending_rank_max']
    return (str(a) if a==b else f'{a}–{b}')+'/35 ('+f(m['ecdf_percent'],2)+'%)'
def table(header,rows):
    return '\n'.join(['| '+' | '.join(header)+' |','| '+' | '.join(['---']*len(header))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])+'\n\n'
def link(name):return f'[{name}](/Users/fgtek002/TimeTrack/review_revision/stage19h1_scale_context/{name})'

report='''# STAGE 19H1 — Dominant-VM scale context audit

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

'''
main=[r for r in d['selected_context_cohort_comparisons'] if r['formulation']=='M1']
report+=table(['Trace / VM','Fold','Log median','Log IQR','Log-IQR rank (ECDF)','Cohort log-IQR min / median / max','IQR / cohort median'],[
    [r['trace']+' / '+r['vm_id'],r['fold'],f(r['metrics']['transformed_median']['value']),f(r['metrics']['transformed_iqr']['value']),
     rank(r['metrics']['transformed_iqr']),trip(r['metrics']['transformed_iqr']),f(r['metrics']['transformed_iqr']['ratio_to_cohort_median'])] for r in main])
report+=table(['Trace / VM','Fold','Log-median rank (ECDF)','Native median','Native IQR','Native-IQR rank (ECDF)','Cohort native-IQR min / median / max','Native IQR / cohort median'],[
    [r['trace']+' / '+r['vm_id'],r['fold'],rank(r['metrics']['transformed_median']),f(r['metrics']['native_median']['value'],2),
     f(r['metrics']['native_iqr']['value'],2),rank(r['metrics']['native_iqr']),trip(r['metrics']['native_iqr']),f(r['metrics']['native_iqr']['ratio_to_cohort_median'])] for r in main])
report+='''Native-median ranks match the log-median ranks for these dominant
partitions, but the medians themselves are independently calculated from
native rows. Complete median distributions/ranks for both scale coordinates
are in Appendix A and the full-precision audit record.

### Separate fold summaries

'''
for trace,vm in [('Materna-T1','266'),('Materna-T3','272')]:
    rr=[r for r in main if r['trace']==trace]
    m=lambda key,field:[r['metrics'][key][field] for r in rr]
    report+=f'''**{trace} VM{vm}: SCALE_INSTABILITY_NOT_SUPPORTED.**
The actual M1 log IQR ranges from {f(min(m('transformed_iqr','value')))} to
{f(max(m('transformed_iqr','value')))}, with ascending ranks
{extent(m('transformed_iqr','ascending_rank_min'))}/35
({extent(m('transformed_iqr','ecdf_percent'),2)}% ECDF).
It is {f(min(m('transformed_iqr','ratio_to_cohort_median')))}–{f(max(m('transformed_iqr','ratio_to_cohort_median')))}
times the cohort median IQR. Its native IQR is
{f(min(m('native_iqr','value')),2)}–{f(max(m('native_iqr','value')),2)} KB/s,
rank 35/35 in every fold. Log-median rank is
{extent(m('transformed_median','ascending_rank_min'))}/35.
These values place the VM at the upper, not lower, end of the training-scale
distribution. No threshold for “near the minimum” is needed to establish
that the observed dominant scale is not in the lower cohort tail.

'''
report+='''The selected S1-disk/S2-disk cohort views also place both dominant
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

'''
for trace,vm in [('Materna-T1','266'),('Materna-T3','272')]:
    rr=[r for r in d['fixed_context_dominant_partitions'] if r['trace']==trace]
    lookup={(r['trace'],r['vm_id'],r['fold'],r['L']):r for r in d['cohort_partition_distribution']}
    report+=f'### {trace} VM{vm}: final partition values\n\n'
    report+=table(['Fold','L','Uses (all three seeds)','Fit rows','Log median','Log IQR','Native median KB/s','Native IQR KB/s'],[
        [r['fold'],r['L'],', '.join(v['formulation'] for v in r['selected_by']) or '—',
         lookup[(trace,vm,r['fold'],r['L'])]['fit_row_count'],
         f(r['metrics']['transformed_median']['value']),f(r['metrics']['transformed_iqr']['value']),
         f(r['metrics']['native_median']['value'],2),f(r['metrics']['native_iqr']['value'],2)] for r in rr])
    report+=f'### {trace} VM{vm}: log-space fixed-L cohort context\n\n'
    report+=table(['Fold/L','Median rank (ECDF)','IQR rank (ECDF)','Cohort median min / median / max','Cohort IQR min / median / max','IQR / cohort median IQR'],[
        [str(r['fold'])+'/'+str(r['L']),rank(r['metrics']['transformed_median']),rank(r['metrics']['transformed_iqr']),
         trip(r['metrics']['transformed_median']),trip(r['metrics']['transformed_iqr']),f(r['metrics']['transformed_iqr']['ratio_to_cohort_median'])] for r in rr])
    report+=f'### {trace} VM{vm}: native-unit fixed-L cohort context (KB/s)\n\n'
    report+=table(['Fold/L','Median rank (ECDF)','IQR rank (ECDF)','Cohort median min / median / max','Cohort IQR min / median / max','IQR / cohort median IQR'],[
        [str(r['fold'])+'/'+str(r['L']),rank(r['metrics']['native_median']),rank(r['metrics']['native_iqr']),
         trip(r['metrics']['native_median']),trip(r['metrics']['native_iqr']),f(r['metrics']['native_iqr']['ratio_to_cohort_median'])] for r in rr])
report+='''## Appendix B. Complete cohort distribution

The full unrounded vector for each 35-VM trace/fold/context group is retained
as the `cohort_partition_distribution` array in '''+link('analysis.json')+'''.
Select the trace, fold and L to obtain the exact corresponding 35 rows.
Each row includes native and transformed summaries, fit timestamp and scaler
partition hashes, raw-member hash, fit-row count and the training/test boundary.
The `selected_context_cohort_comparisons` array contains each formulation's
actual selected-context reference distribution summaries; its 35-member
vectors are identified by the `completion_scaler_checks` context mapping.
No VM is dropped and no cross-VM model/scaler fitting is performed.

STAGE_19H1_PASS
'''
(OUT/'STAGE19H1_DOMINANT_VM_SCALE_CONTEXT_REPORT.md').write_text(report)
print('REPORT_WRITTEN',len(report),'characters',flush=True)
