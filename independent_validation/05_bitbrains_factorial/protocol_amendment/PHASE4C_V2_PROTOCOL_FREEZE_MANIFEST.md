# Phase 4C V2 Bitbrains Protocol-Amendment Freeze Manifest

## Checkpoint identity

- Freeze date: 2026-10-05 (Europe/Helsinki)
- Pre-freeze HEAD: `b162b8907f5f063ef969c02bd5d175edd3471028`
- Parent Phase 4B commit: `b162b8907f5f063ef969c02bd5d175edd3471028`
- Parent annotated tag: `phase4b-bitbrains-factorial-protocol-freeze-v1`
- Parent Phase 4B config SHA-256:
  `deedcd31616861f1f6ee4517cc0552a05d54d0b334364f9674b06a1dcab6dc1a`
- Original Phase 4C criteria SHA-256:
  `79df6a168d7021dbafd6080640a506d22699e9d4989d422f924b178600465f12`
- Amendment decision: `REVISE_ENTITY_ELIGIBILITY_AND_RESELECT`
- Amendment-decision SHA-256:
  `4261300afd29362cf3d7faecc068bfc8170d5ac046691e80dd7b642d0a0add57`
- Phase 4C V2 config SHA-256:
  `627391b84887411d8b930fd5d00cdd9a1f90f3990f958d582f4329424353fa4e`
- Training-scale eligibility version: `phase4c-training-scale-eligibility-v1`
- Training-scale eligibility CSV SHA-256:
  `1ab811bc94b130a7a496eb56a0d90eac0aa6cb5616a10c5e362289476349b6a4`
- Training-scale audit validation SHA-256:
  `033a81db0059f5084298de1cc8649f480144fbe6eca2386bca4fedb88e365458`
- Independent amended-protocol validation: **PASS**.

**NO VALID PHASE 4C V2 SCIENTIFIC FIT OR EXTERNAL OUTER-TEST PREDICTION
EXISTED AT FREEZE TIME.**

## Rationale and eligibility amendment

The frozen no-fallback median/IQR scaler cannot operate when a transformed
training resource has IQR zero. The training-only audit found this condition in
approximately 35% of both structurally eligible Bitbrains pools. Changing the
scaler would change normalized optimization and possibly M1 resource balance;
dropping or masking resources would change the four-resource factorial.

Phase 4C V2 therefore adds one entity-level rule. A VM must satisfy the original
structural rule and have transformed training IQR greater than zero for every
resource in every scaler partition keyed by
`(environment, VM_ID, fold, phase, L)`. Each VM has 30 unique partitions: five
folds × inner/final training phases × contexts 4/9/18. There is no epsilon,
fallback, alternate statistic, or outcome-dependent exception.

## Audited populations and zero-IQR prevalence

| Environment | Structurally eligible | Scale eligible | Rejected | Retained |
|---|---:|---:|---:|---:|
| fastStorage | 916 | 596 | 320 | 65.07% |
| Rnd | 416 | 272 | 144 | 65.38% |

| Environment | CPU | THROUGHPUT | MEMORY | DISK_WRITE |
|---|---:|---:|---:|---:|
| fastStorage | 14.00% | 27.05% | 5.31% | 6.04% |
| Rnd | 17.14% | 23.80% | 1.51% | 4.18% |

THROUGHPUT was the most common source. Failures were not meaningfully
concentrated by fold, inner/final phase, or context length.

## Frozen V2 cohorts

Selection retains the original ascending SHA-256 ranking of
`phase4a-v1|<environment>|<exact-VM-ID>` after the binary structural-plus-scale
eligibility filter. No VM was substituted manually.

### fastStorage

- Selected: 35; original retained: 25; replaced: 10.
- Rank order: 697, 860, 366, 679, 360, 505, 481, 109, 680, 50, 434, 949,
  1161, 513, 79, 396, 1172, 503, 1164, 742, 330, 880, 480, 326, 410, 678,
  516, 1005, 382, 1044, 504, 450, 530, 703, 854.
- ID-list SHA-256:
  `ff2d65ff43bedae076f913e4b9e175e7762d835eafe5efc8c2a2590e487fc07c`.
- Selection-record SHA-256:
  `168ccae403488cc06a60b5a2d6da1c57a88f32f793c4356bcecdfa4bf445d648`.

### Rnd

- Selected: 35; original retained: 22; replaced: 13.
- Rank order: 99, 409, 269, 493, 474, 97, 118, 233, 142, 151, 387, 115,
  232, 488, 413, 158, 109, 92, 93, 154, 22, 204, 1, 241, 29, 198, 143,
  436, 252, 85, 304, 332, 120, 306, 462.
- ID-list SHA-256:
  `f175f8b443adbed472caf5a2b26f9d73f989faf9f68334e520655c33ae982d2e`.
- Selection-record SHA-256:
  `09f6b782a8cc5df7683e1dccf6a05551b0bf91daa64fde7868c1c145f48f0357`.

Canonical selected-cohort artifact SHA-256:
`a56192c6d0f7c3274b0899a18cc6b2748586d5a3950ca79a40692358e9617ccf`.

## Frozen V2 support and scaler partitions

| Check | Result |
|---|---:|
| fastStorage support records | 525 |
| Rnd support records | 525 |
| Combined support records | 1,050 |
| Unique scaler partitions | 2,100 |
| Scaler partitions per VM | 30 |
| Support-minimum failures | 0 |
| Zero-IQR transformed resource failures | 0 |
| S1/S2/M1 support mismatches | 0 |

- V2 support-manifest SHA-256:
  `690677c99d4e7cb3b790bf4ef60041282d28877deaa75d5cc53ced400490ce22`.
- V2 support-summary SHA-256:
  `5a3fd5c3022485a4b9af45efd780586d970636b28a2c675ed63f7cfa361ca33a`.
- V2 scaler-partition SHA-256:
  `50e8af2151c8e2170089073791405e23da7dd99cdeb0269edbbb2bacfbd0d1ca`.
- V2 support-validation SHA-256:
  `707bd6c1c3a8443eba3ea47b015f40e1515be14bb1ade5f6b5d4c2e4a7ef0d12`.

The support manifest freezes origin IDs, support and split hashes, segment IDs,
boundary timestamps, counts, V2 config/cohort identity, and eligibility identity.
The scaler manifest freezes fit-row timestamp hashes, robust statistics, and a
canonical hash per scaler partition. No outer-test target value is stored.

## Unchanged scientific settings

- Resources/order: CPU, THROUGHPUT, MEMORY, DISK_WRITE.
- Transforms: identity, `log1p`, identity, `log1p`, respectively.
- Scaling: training-only median/IQR; IQR strictly positive; no fallback.
- Leads: `[1,2,4,9,18]`; horizons: `[5,10,20,45,90]` minutes.
- Contexts: `[4,9,18]`; seeds: `[0,1,2]`; five rolling outer folds.
- Maximum-history common four-resource support and lead-18 target-time purge.
- Inner validation: latest 15% of purged outer train, with its own lead-18 purge.
- Architectures: frozen two-layer unidirectional plain-LSTM S1, S2, and M1.
- Hidden size 64, dropout 0.1, Adam 0.001, batch 256, maximum 50 epochs,
  patience 7, gradient clipping 1.0.
- M1 loss: equal arithmetic mean of the four resource MSEs; no weighting.
- Context selection: three-seed mean inner objective, smaller-L tie break.
- Final refit: from scratch on complete outer train for the selected seed-specific
  fixed epoch; one subsequent outer-test evaluation.
- Aggregation: seed mean, then equally weighted VM-fold cells; environments
  analyzed independently before equal-environment synthesis.
- Uncertainty: 10,000-replicate paired VM-cluster bootstrap retaining all folds.
- Original Phase 4C H1/H2/H3 criteria remain byte-identical.
- Materna remains outside Phase 4C.

## Run identity and old-run invalidation

Every V2 run identity contains the amended config SHA-256, V2 cohort hash,
training-scale eligibility version and SHA-256, amendment-decision SHA-256,
environment, formulation, resource, VM, fold, L, seed, phase, support hash,
archive hash, criteria hash, and Phase 4B decision hash.

V2 execution writes to a separate `outputs/scientific_v2` namespace. The 154
pre-amendment completions remain unchanged under `outputs/scientific`; every
one is fastStorage/S1/inner/VM 697 with no outer-test access. They are labelled
`ABORTED_PRE_AMENDMENT_PROVENANCE`, are permanently scientifically non-reusable,
and fail V2 identity matching because their config/cohort/amendment identity is
different. `ABORTED_PRE_AMENDMENT_RUNS.csv` SHA-256 is
`bf8b21b878b3203608084dc215793a927b8d1d4bc349decfc169e6fbe4a2d049`.

The amended protocol begins at **0/37,800 valid scientific fits**.

## Generalizability restriction

The external estimand is restricted from all structurally valid Bitbrains VMs
to structurally valid VMs with nondegenerate four-resource training variability
in every scientific scaler-fit partition. Future claims must describe this as a
dynamic/scale-estimable VM population and must not generalize to excluded idle,
quiescent, or resource-constant VMs without qualification.

## Independent validation

`PHASE4C_V2_PROTOCOL_VALIDATION.json` reports **PASS** with zero failures and
SHA-256 `44a6d3cf15a966f9455e3fc8a3038bf5edf8fea42cecc900057d867f77c0bcd4`.
It verifies all 32 requested identity, cohort, support, unchanged-semantics,
old-run invalidation, and zero-execution conditions.

At validation and freeze time:

- valid V2 scientific fits: 0;
- optimizer executions during amendment: 0;
- outer-test target values accessed: 0;
- outer-test predictions generated: 0;
- predictive outcomes inspected: 0.

## Artifact inventory

- Inventory entries: **29**.
- Inventory total bytes: **65,659,421**.
- Inventory SHA-256:
  `323b5a0ca9ba1a7c0180a4faf973f74676dd6a40f99106ab497ebf51baeb4dc0`.
- Amendment-tree SHA-256:
  `3fa66a780e4e87553325ae8bb136d31289f560c37fce20f1f3a2be514bb6de74`.

The amendment tree is SHA-256 over sorted UTF-8 records
`relative_path,byte_size,sha256\n`. The inventory, its builder, and this manifest
are excluded from their own tree to avoid circular checksums; the Git commit and
annotated tag protect them.
