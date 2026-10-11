# Phase 4D Execution-Conformance Decision

Classification: **IMPLEMENTATION_CONFORMANCE_CHECKPOINT**  
Not classified as: `SCIENTIFIC_PROTOCOL_AMENDMENT`

Date: 2026-10-11 (Europe/Helsinki)

## Parent protocol checkpoint

- Commit: `c4077318bfbb02e112b439baa3ae7a0e35db0dc5`
- Tag: `phase4d-materna-secondary-replication-protocol-freeze-v1`
- Frozen scientific config SHA-256: `064ef5a4864f5590b8149242c4011c37a49aee35cf60a4690f6aa126b98fce27`

## Blocking defects

### Defect 1 — validator HEAD semantics

`validate_phase4d_preflight.py` required the current checkout to remain at the
parent Phase 4C commit
`d9c8ed80a90085d989d1dacc40f1c27377a4a76f`, although the valid frozen Phase
4D protocol checkpoint is
`c4077318bfbb02e112b439baa3ae7a0e35db0dc5`. This made the validator fail after
the protocol freeze and would recur after every later implementation-only
commit.

The correction separates historical checkpoint integrity from current-tree
protected-content integrity. The historical Phase 4D protocol tag must resolve
exactly to its frozen commit, and protected scientific protocol artifacts in
the current tree must remain identical to the frozen tag. Current HEAD is not
required to equal the historical checkpoint.

### Defect 2 — missing execution-conformance implementation

The frozen Phase 4D tree contained no scientific execution layer providing:

- `scientific_v1` namespace isolation;
- canonical scientific run identity;
- exact resumability checks;
- atomic completion records;
- explicit pilot-reuse rejection;
- outer-test access provenance lifecycle;
- per-trace technical validation; and
- combined technical validation.

The correction implements this execution plumbing plus synthetic/mock
regression tests and zero-training dry-run enumeration.

## Scientific invariants

Correcting these defects changes execution plumbing and validation only. It
does **not** change data, population definition, selected VM cohort or ordering,
support, resources, transforms, scaler semantics, horizons, contexts, folds,
seeds, architecture, optimizer, hyperparameters, M1 loss, context selection,
epoch selection, final-refit lifecycle, classification thresholds, bootstrap,
R1/R2/R3/R4, or publication role.

No scientific training, optimizer execution, real outer-test access,
prediction generation, persistence evaluation, predictive inspection, or
scientific interpretation is authorized by this implementation checkpoint.
