# Phase 4D Materna Execution-Conformance Freeze Manifest

Date: 2026-10-11 (Europe/Helsinki)

Classification: `IMPLEMENTATION_CONFORMANCE_CHECKPOINT`  
Not a `SCIENTIFIC_PROTOCOL_AMENDMENT`.

## Defects and correction boundary

The checkpoint corrects two execution blockers: the preflight validator tied
validity to an obsolete current HEAD, and the frozen protocol had no scientific
runner with namespace isolation, exact resumability, atomic completion, pilot
rejection, or outer-test provenance. The validator now separately checks the
historical protocol tag and the current tree's protected scientific content.
The runner and validators implement the already-frozen protocol without
changing it.

Parent Phase 4D protocol checkpoint:

- commit: `c4077318bfbb02e112b439baa3ae7a0e35db0dc5`
- tag: `phase4d-materna-secondary-replication-protocol-freeze-v1`
- parent Phase 4C commit: `d9c8ed80a90085d989d1dacc40f1c27377a4a76f`
- parent Phase 4C tag: `phase4c-v2-bitbrains-external-confirmation-freeze-v1`

Frozen identities remain unchanged:

- scientific config SHA-256: `064ef5a4864f5590b8149242c4011c37a49aee35cf60a4690f6aa126b98fce27`
- Materna archive SHA-256: `1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4`
- selected-cohort SHA-256: `4c9e8f4cfa5cf26c4188924c486cdfbe9d78972eec1f84f5e0f23b1e94353140`
- selection-record SHA-256: `63c1a7266057c4344bfd6211ee7d3fd2deba283e4b41797fc4e412483469b24b`
- preflight inventory SHA-256: `fc440dcb3dc9039a919b1e38136f1567c239a7609bac3d01ec08c93c3a1d293b`
- preflight tree SHA-256: `981dfef4b90e8056897bf91c0ad4643c012efc3110d5a348ecfac37bf8dbdc72`
- execution-conformance decision SHA-256: `3f5a780128f0d7931a44078d2f55f8168e3b444d51d2eb03cd635266b6bd368b`

## Execution implementation

The one canonical scientific output root is:

`independent_validation/06_materna_replication/outputs/scientific_v1/`

All progress, completion, history, selection, model, prediction, metric,
persistence, runtime, validation, inventory, and later analysis paths are
constrained beneath that root. Trace entry points accept `T1`, `T2`, `T3`, or
sequential `all`, and execute in T1/T2/T3 order with at most four workers.

The exact scientific run identity contains:

`run_kind`, `trace`, `environment`, `formulation`, `resource`, `vm_id`, `fold`,
`L`, `seed`, `phase`, `config_sha256`, `archive_sha256`, `cohort_sha256`,
`support_sha256`, `execution_conformance_sha256`, and `run_id`; final identities
also contain `selected_epoch`. Scientific equality is exact. Technical-pilot
identities use a different run kind, config identity, and execution identity,
so copying a pilot completion into a scientific-looking location cannot make it
reusable.

Resumability accepts only a complete scientific record with an exact identity,
correct phase/access semantics, existing required artifacts, and matching
artifact hashes. Inner success is published atomically only after training and
history persistence and records `outer_test_accessed=false`. Final success is
published only after fixed-epoch refit, exactly one authorized test evaluation,
and model, prediction, and metric persistence with verified hashes; it records
`outer_test_accessed=true`. Failures are separate non-reusable attempt records,
preserving whether outer-test access had already occurred.

The runner reuses the frozen, tested Phase 4C training primitives with the
Materna config, cohort, trace loader, support, and namespace rebound explicitly.
It retains Adam, learning rate 0.001, batch size 256, 50 maximum epochs,
patience 7, gradient clipping 1.0, contexts `[4,9,18]`, seeds `[0,1,2]`, leads
`[1,2,4,9,18]`, the frozen S1/S2/M1 definitions, and equal four-resource M1
MSE. Context selection is inner-validation-only with the frozen seed/resource/
horizon means and smaller-L tie break. Each seed's best inner epoch is used for
a from-scratch, fixed-epoch final refit on legal outer-training support.
Persistence is generated on the matched final support.

## Zero-training plan and validation

The dry-run planner produced 56,700 unique scientific run IDs:

- each trace: 18,900
- S1 inner/final: 18,900 / 6,300
- S2 inner/final: 18,900 / 6,300
- M1 inner/final: 4,725 / 1,575
- combined inner/final: 42,525 / 14,175
- duplicate run IDs: 0
- pilot/scientific collisions: 0
- optimizer executions: 0
- real outer-test accesses: 0

`validate_phase4d_trace.py` provides the post-execution technical gate for
exactly one of T1/T2/T3. `validate_phase4d_combined.py` provides the combined
three-trace technical gate. Neither performs scientific interpretation.

The dedicated synthetic/mock suite passed 41 tests. The corrected full
preflight validator passed, reproducing all 1,575 support records with zero
mismatch, leakage, scale, or minimum-support failures. The zero-training
execution-conformance validator passed. The implementation-only diff audit
passed with zero scientific-setting mutations.

At freeze preparation time:

- scientific fits: 0
- optimizer executions: 0
- scientific outer-test accesses: 0
- scientific predictions: 0
- predictive outcomes inspected: 0
- scientific figures: 0
- real `scientific_v1` execution artifacts: 0

**THIS CHECKPOINT CHANGES EXECUTION IMPLEMENTATION ONLY.**

**NO SCIENTIFIC PROTOCOL SETTING WAS CHANGED.**

**NO MATERNA SCIENTIFIC EXECUTION OCCURRED BEFORE THIS FREEZE.**
