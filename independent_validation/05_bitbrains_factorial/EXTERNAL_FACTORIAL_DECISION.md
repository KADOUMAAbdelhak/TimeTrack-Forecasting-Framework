# Prospective Phase 4B Bitbrains Factorial Decision

Date: 2026-09-28  
Parent checkpoint: `59f5bed3fd7b385739d08dc088965341a29c2809`, tag `phase4a-external-confirmation-design-freeze-v1`  
Scope: implementation, support/split construction, tests, and a non-scientific timing/sanity pilot only.

This record is fixed before Phase 4B support counts, timing, loss-balance diagnostics, or validation metrics are produced. It authorizes no external scientific fit and no outer-test prediction or outcome inspection.

## Environments and cohorts

Bitbrains fastStorage and Rnd are independent primary confirmation environments. They remain separate through support construction, fitting, metrics, reporting, and future interpretation. Observations and VM identities are never pooled. Any future synthesis gives the two environments equal weight, not VM-count weight.

- fastStorage: exactly 35 frozen IDs; ID-list SHA-256 `97742a6e10858c9b8a021d3142419d66f41b2ac67e5944f95c2a4b8931f4632d`; selection-record SHA-256 `3ccbdb4d3615d323d54127f63eb72f588893d9bd48593a82dcccc10754a60b38`.
- Rnd: exactly 35 frozen IDs; ID-list SHA-256 `5674f15382d5efb795cbda46a34f1f766e859413857475212023afc36ffcdc1a`; selection-record SHA-256 `5cfbd93103881a8af258ed9ecc6e317601c7b6b44825d2f790a1a81ed1731f9c`.

No VM may be replaced based on support size, signal properties, runtime, or predictive behavior. A structurally failing selected VM stops Phase 4B.

## Targets and transformations

Fixed order: CPU, THROUGHPUT, MEMORY, DISK_WRITE.

- CPU: `CPU usage [%]`; identity transform.
- THROUGHPUT: `Network received throughput [KB/s] + Network transmitted throughput [KB/s]`; log1p.
- MEMORY: `Memory usage [KB]`; identity.
- DISK_WRITE: `Disk write throughput [KB/s]`; log1p.

Each resource then receives training-partition-only median/IQR scaling. IQR must be strictly positive. Native inversion is inverse scaling for CPU/memory and inverse scaling, `expm1`, then nonnegative projection for throughput/disk-write. Pre-projection negative fractions are retained.

## Cleaning and continuity

Raw official archives are read directly. Ten-digit timestamps are Unix seconds and convert deterministically to UTC. No resampling, interpolation, forward fill, clipping, imputation, duplicate resolution, or timestamp synthesis is permitted.

A row is valid only when CPU is finite in [0,100], both network components are finite/nonnegative, memory is finite/nonnegative, disk-write is finite/nonnegative, and their throughput sum is finite/nonnegative. Invalid rows are unavailable. Selected VMs must have zero duplicate timestamps or the phase stops.

After sorting valid observations, a segment breaks whenever the timestamp gap exceeds 450 seconds. History and targets cannot cross segments.

## Horizons, contexts, and common support

Fixed leads are `[1,2,4,9,18]`, representing `[5,10,20,45,90]` minutes. Fixed contexts are `[4,9,18]`, representing approximately `[20,45,90]` minutes.

One support universe is constructed at Lmax=18 per environment/VM. A legal origin has a full same-segment four-resource history, all four finite targets at every required lead, and no target crossing. L4 and L9 use exactly the L18 origins and gain none. All S1 resources, all S2 resources, and M1 share the identical split IDs and hashes.

## Folds and purge

For each VM, sort legal origins chronologically. The first 50% is the initial outer-training region; each following 10% block is one of five nonoverlapping outer tests. Integer boundaries are `floor(n * fraction)` for fractions 0.5 through 1.0, with the final boundary forced to `n`. Fold `k` outer train contains legal origins before its test block, purged so every lead-18 target timestamp precedes the first test origin timestamp.

Within purged outer train, the latest 15% by origin count is inner validation (`ceil(0.15*n)` with at least one when nonempty). Inner train is the earlier portion, then purged so every lead-18 target timestamp precedes the first inner-validation origin timestamp. There is no random split.

## Prospective technical support gate

No exact minimum was frozen in Phase 4A. Before support counts are computed, Phase 4B fixes these conservative technical minima using only batch size 256, the 18-sample maximum context/lead, and the five-fold structure:

- outer train: at least 1,024 origins;
- inner train after purge: at least 512 origins (two full batches);
- inner validation: at least 128 origins;
- outer test: at least 256 origins (one full batch).

Every selected VM/fold must pass. Failure stops the phase; IDs are not substituted.

## Frozen questions and model boundary

- H1: Does S2 fail to provide broad per-resource improvement over S1?
- H2: Does M1 fail to provide broad per-resource improvement over S2?
- H3: Are benefits heterogeneous rather than consistently positive across VMs, environments, resources, and horizons?

The only model is the frozen plain two-layer, unidirectional LSTM concept: hidden size 64, dropout 0.1, final recurrent representation. S1 has one input resource and one five-horizon head. S2 has four inputs and one target head. M1 has one shared four-input encoder and four independent five-horizon heads with equal normalized MSE weighting. No new architecture or task weighting is included.

## Non-scientific pilot boundary

The pilot VM is the first SHA-ranked frozen ID in each cohort: fastStorage `697`, Rnd `99`. It uses fold 1, seed 0, L=9, exactly five epochs, and inner train/validation only. It runs four S1, four S2, and one M1 per environment: 18 fits total. Outer-test IDs/counts/hashes may exist as metadata, but pilot code cannot load outer-test targets, produce outer-test predictions, perform scientific context selection, or perform final refits.

Pilot metrics and M1 loss shares are technical diagnostics only. They cannot change cohorts, transforms, weights, hypotheses, mappings, or scientific conclusions.

## Prospective compute-feasibility gate

Technical correctness and the support gate take precedence: any failure yields `TECHNICAL_PROTOCOL_FIX_REQUIRED`. Otherwise, using timing only:

- `FULL_35_VM_CONFIRMATION_FEASIBLE`: projected combined four-worker central wall time is at most 7 days, conservative wall time at most 14 days, retained storage at most 20 GB, and four concurrent pilot peak-RSS estimates remain below 80% of detected physical RAM.
- `FULL_35_VM_CONFIRMATION_EXPENSIVE_BUT_FEASIBLE`: the first threshold is missed, but central wall time is at most 21 days, conservative wall time at most 42 days, storage at most 100 GB, and memory remains safe.
- `PROSPECTIVE_COHORT_REDUCTION_REQUIRED`: technical/support checks pass but the expensive-feasible limits are exceeded. No reduction occurs in Phase 4B.

These thresholds cannot be changed after pilot timing is observed.
