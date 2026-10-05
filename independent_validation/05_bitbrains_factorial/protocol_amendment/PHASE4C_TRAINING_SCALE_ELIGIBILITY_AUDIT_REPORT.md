# Phase 4C IQR-Zero Protocol-Amendment Audit Report

Date: 2026-09-30 (Europe/Helsinki)

## Decision status

This is prospective decision support only. It does not amend the frozen Phase
4B protocol, replace the Phase 4A cohorts, authorize reuse of aborted fits, or
authorize Phase 4C execution.

Recommended prospective decision:

`REVISE_ENTITY_ELIGIBILITY_AND_RESELECT`

All four prerequisites for that recommendation passed: each environment retains
at least 35 eligible VMs; candidate V2 support has zero IQR failures; no
outer-test predictive outcome was used; and the four-resource S1/S2/M1
semantics remain intact.

## Validation and frozen identity

- Independent validation: **PASS**, with zero failures.
- Current HEAD and Phase 4B annotated-tag target:
  `b162b8907f5f063ef969c02bd5d175edd3471028`.
- Phase 4C prospective criteria SHA-256:
  `79df6a168d7021dbafd6080640a506d22699e9d4989d422f924b178600465f12`.
- Phase 4A inventory: 27/27 artifacts unchanged.
- Phase 4B inventory: 43/43 artifacts unchanged.
- External raw archives: 3/3 hashes unchanged.
- TimeTrack raw inputs: all frozen hashes unchanged.
- Canonical panel SHA-256:
  `c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`.
- Model-fit calls: 0. Optimizer executions: 0.
- Outer-test target values accessed: 0. Outer-test predictions generated: 0.
- Scientific performance results inspected: 0. H1/H2/H3 analyses performed: 0.

## Blocked-run provenance

The 154 completion artifacts are preserved and labelled
`ABORTED_PRE_AMENDMENT_PROVENANCE`. Every record is fastStorage, S1, inner
phase, VM 697, and has `outer_test_accessed=false`. Final fits, Rnd fits, and
outer-test predictions remain zero. The compact record stores each run ID,
config/support/split/archive/cohort/criteria hashes, completion-file SHA-256,
artifact path, and filesystem timestamp. The source completion JSONs contain no
start/end timestamps, so those fields are explicitly null.

These artifacts are **not eligible for reuse** by any amended execution unless
that reuse is separately and explicitly authorized later. No validation metric
or other predictive result was read into the provenance record.

## Candidate eligibility rule and exact partition semantics

`TRAINING_SCALE_ELIGIBLE` requires strictly positive training IQR for every
one of the four transformed resources in every unique scaler-fit partition.
Transforms remain CPU identity, THROUGHPUT `log1p`, MEMORY identity, and
DISK_WRITE `log1p`.

The unique key is:

`(environment, VM_ID, fold, phase, L)`

There are exactly 30 partitions per VM: five folds × two training phases
(`inner_train` and final `outer_train`) × three contexts (`L=4,9,18`). The
frozen implementation fits the scaler over the union of history and target rows
belonging to the relevant training origins. Scalers are formulation-independent:
S1, S2, and M1 consume the same partition scaler. Context-specific row unions
can differ, so all three L values were checked. No artificial formulation
duplicates were introduced. Transformed- and native-IQR gates disagreed in zero
resource-partition cells.

Legal origins were reconstructed from timestamps and segment IDs. Because
physical cleaning retains only finite four-resource rows, the frozen finiteness
condition is already satisfied; no designated outer-test target value was read.
Only training-partition resource values entered IQR calculations.

## Full structurally eligible pools

| Environment | Structurally eligible | Training-scale eligible | Rejected only for zero IQR | Retained |
|---|---:|---:|---:|---:|
| fastStorage | 916 | 596 | 320 | 65.07% |
| Rnd | 416 | 272 | 144 | 65.38% |

The blocker is therefore not a small exceptional subset: approximately 35% of
each structurally eligible pool fails the all-partition rule.

### Zero-IQR resource-partition prevalence

Each denominator counts VM/fold/phase/context resource cells.

| Environment | CPU | THROUGHPUT | MEMORY | DISK_WRITE |
|---|---:|---:|---:|---:|
| fastStorage | 3,848/27,480 (14.00%) | 7,434/27,480 (27.05%) | 1,459/27,480 (5.31%) | 1,660/27,480 (6.04%) |
| Rnd | 2,139/12,480 (17.14%) | 2,970/12,480 (23.80%) | 189/12,480 (1.51%) | 522/12,480 (4.18%) |

THROUGHPUT is the dominant source in both environments, followed by CPU.

### Fold, phase, and context concentration

| Dimension | fastStorage range | Rnd range | Interpretation |
|---|---:|---:|---|
| Fold 1–5 | 12.94%–13.18% | 11.45%–11.87% | No early-fold concentration |
| Inner vs final | 13.14% vs 13.07% | 11.64% vs 11.67% | No meaningful phase concentration |
| L4/L9/L18 | 13.11%/13.10%/13.09% | 11.66%/11.66%/11.66% | Context has negligible effect |

Resources constant by the IQR criterion in every one of the 30 partitions were:
fastStorage CPU 115 VMs, THROUGHPUT 239, MEMORY 39, DISK_WRITE 49; Rnd CPU 68,
THROUGHPUT 91, MEMORY 6, DISK_WRITE 15. Counts can overlap within a VM.

## Candidate V2 cohorts — derived, not applied

The original `phase4a-v1|<environment>|<exact-VM-ID>` salt and ascending
SHA-256 ranking were retained. Filtering used only structural eligibility plus
the binary all-training-partition IQR rule. No correlations, persistence,
performance, support-size optimization, or variance magnitude ranking entered
selection.

### fastStorage

- Retained from original cohort: 25; replaced: 10.
- Removed original IDs: 52, 58, 563, 733, 757, 813, 908, 947, 1111, 1225.
- Replacement IDs: 382, 450, 504, 516, 530, 678, 703, 854, 1005, 1044.
- Candidate rank order: 697, 860, 366, 679, 360, 505, 481, 109, 680, 50,
  434, 949, 1161, 513, 79, 396, 1172, 503, 1164, 742, 330, 880, 480, 326,
  410, 678, 516, 1005, 382, 1044, 504, 450, 530, 703, 854.
- Candidate ID-list SHA-256:
  `ff2d65ff43bedae076f913e4b9e175e7762d835eafe5efc8c2a2590e487fc07c`.
- Candidate selection-record SHA-256:
  `168ccae403488cc06a60b5a2d6da1c57a88f32f793c4356bcecdfa4bf445d648`.

### Rnd

- Retained from original cohort: 22; replaced: 13.
- Removed original IDs: 184, 276, 283, 350, 370, 381, 391, 404, 448, 454,
  480, 486, 491.
- Replacement IDs: 1, 29, 85, 120, 143, 198, 241, 252, 304, 306, 332, 436,
  462.
- Candidate rank order: 99, 409, 269, 493, 474, 97, 118, 233, 142, 151,
  387, 115, 232, 488, 413, 158, 109, 92, 93, 154, 22, 204, 1, 241, 29,
  198, 143, 436, 252, 85, 304, 332, 120, 306, 462.
- Candidate ID-list SHA-256:
  `f175f8b443adbed472caf5a2b26f9d73f989faf9f68334e520655c33ae982d2e`.
- Candidate selection-record SHA-256:
  `09f6b782a8cc5df7683e1dccf6a05551b0bf91daa64fde7868c1c145f48f0357`.

## Candidate V2 support validation

| Check | Result |
|---|---:|
| VMs/environment | 35 / 35 |
| Folds | 5 |
| Contexts | 4, 9, 18 |
| Support records/environment | 525 / 525 |
| Combined support records | 1,050 |
| Support-minimum failures | 0 |
| Zero-IQR resource-partition failures | 0 |
| S1/S2/M1 support mismatches | 0 |
| Outer-test target values accessed | 0 |
| Outer-test predictions generated | 0 |

The candidate manifest retains exact split origin IDs, timestamps, counts,
hashes, and segment IDs. Segment safety, target-position safety, lead-18 purge,
and the frozen 15% inner split are produced by the unchanged frozen split logic.
The candidate records do not overwrite the Phase 4A or Phase 4B manifests.

## Scientific consequence

The estimand population changes materially. The original design sampled from
all structurally eligible VMs; the candidate design samples from structurally
eligible VMs that also exhibit nondegenerate four-resource training variability
under every scientific fold. Since about 35% of both pools are excluded, the
result should be generalized primarily to dynamic, scale-estimable four-resource
VM traces, not to all structurally valid Bitbrains VMs. It will underrepresent
idle, quiescent, or resource-constant workloads, especially traces with
degenerate throughput or CPU.

The amendment uses no outer-test outcome and preserves pristine external
confirmation with respect to predictive outcomes: eligibility depends only on
training-partition scale feasibility, and deterministic SHA ranking supplies
the cohort. Nevertheless, it is a post-freeze protocol amendment prompted by a
feasibility failure, so it must be prospectively frozen before any amended run
and disclosed as a population restriction.

H1/H2/H3 retain their matched architectural meaning because S1, S2, and M1 keep
the same resources, transforms, support, loss, folds, horizons, contexts, and
training protocol. What changes is their scope: the hypotheses become claims
about the scale-eligible dynamic-VM population, and cannot establish behavior
for the excluded degenerate/idle population.

## Four-option comparison

| Option | Population changes? | Optimization semantics? | M1 loss semantics? | Four-resource factorial? | Arbitrary scale? | Matched S1/S2/M1? | Confirmatory risk |
|---|---|---|---|---|---|---|---|
| A. Training-scale eligibility + deterministic reselection | Yes, explicit dynamic/scale-estimable subset | No | No | Preserved | No | Preserved | Moderate: post-freeze population restriction, but outcome-independent and deterministic |
| B. Scaler fallback | No intended population restriction | Yes; training geometry changes for degenerate partitions | Yes; resource-loss comparability/weighting can change | Nominally preserved | Yes, unless a new scale is independently justified | Potentially weakened because fallback behavior differs by resource/partition | High |
| C. Drop or conditionally mask resources/partitions | Yes, conditionally and unevenly | Yes | Yes; four-way equal M1 loss is lost or conditional | Not preserved | Not necessarily, but masking rules add discretion | Not fully preserved | Very high |
| D. Declare infeasible | No new analyzed population | No | No | No experiment is executed | No | Not applicable | Lowest analytic contamination; no external answer |

Option A is preferable on scientific and reproducibility grounds, not runtime
convenience: it makes the population restriction explicit, applies the exact
same binary rule before deterministic selection, and leaves the factorial and
optimization semantics untouched. Options B and C alter the intervention being
compared. Option D remains defensible but is unnecessary because both candidate
pools are ample and candidate support validates cleanly.

## Artifacts

- `TRAINING_SCALE_ELIGIBILITY.csv`: all 1,332 structurally eligible VMs.
- `ZERO_IQR_PREVALENCE.csv`: environment/resource/fold/phase/context summary.
- `CANDIDATE_V2_COHORTS.csv` and summary JSON: candidate selection only.
- `CANDIDATE_V2_SUPPORT_MANIFEST.parquet`, compact CSV summary, and validation
  JSON: candidate support only.
- `ABORTED_PRE_AMENDMENT_PROVENANCE.json`: preserved 154-fit provenance.
- `TRAINING_SCALE_ELIGIBILITY_VALIDATION.json`: independent PASS record.
- Audit and validation scripts: data-only reproducibility code.

**Confirmation predictive outcomes inspected = 0. Phase 4C was not resumed.**
