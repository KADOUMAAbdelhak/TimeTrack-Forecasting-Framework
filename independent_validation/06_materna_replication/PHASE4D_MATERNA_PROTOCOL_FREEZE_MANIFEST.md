# Phase 4D Materna Secondary-Replication Protocol Freeze Manifest

## Checkpoint identity

- Freeze date: 2026-10-11 (Europe/Helsinki)
- Pre-freeze HEAD: `d9c8ed80a90085d989d1dacc40f1c27377a4a76f`
- Phase 4C scientific checkpoint: `d9c8ed80a90085d989d1dacc40f1c27377a4a76f`
- Phase 4C annotated tag: `phase4c-v2-bitbrains-external-confirmation-freeze-v1`
- Materna archive: `gwa_t_13_materna.zip`
- Materna archive SHA-256: `1380879f0de17cb57619e55c312b41f26ef95743a382f41692db72168fd9afb4`
- Scientific config: `configs/materna_replication_v1.json`
- Scientific config SHA-256: `064ef5a4864f5590b8149242c4011c37a49aee35cf60a4690f6aa126b98fce27`
- Independent Phase 4D preflight validation: **PASS**
- Compute decision: **FULL_35_VM_THREE_TRACE_REPLICATION_EXPENSIVE_BUT_FEASIBLE**

**NO MATERNA SCIENTIFIC PREDICTIVE OUTCOME EXISTED AT FREEZE TIME.**

Materna scientific fits, scientific context selections, final refits, outer-test
target accesses, outer-test predictions, persistence comparisons, and
predictive outcomes inspected were all zero. This checkpoint freezes the
protocol but does not itself authorize scientific execution.

## Prior frozen history

The independent validator reproduced the current HEAD and all 16 prior frozen
tag targets. It verified the Phase 4C analysis/scientific checkpoint, Phase 4C
execution, execution-conformance correction, training-scale amendment, Phase
4B, Phase 4A, Phase 3D, Phase 3C, Phase 3B, Phase 3A, Neural-v2, DLinear, LSTM,
PatchTST, Phase 2A, and corrected deterministic inventories. The six TimeTrack
raw inputs, canonical panel, Bitbrains raw archives, and Materna archive retain
their frozen identities. Four Phase 4C amendment files intentionally replaced
by the later execution-correction checkpoint are verified against the later
correction inventory.

## Frozen population definition

The scientific Materna population is:

> VMs structurally eligible in all three Materna traces and having nonzero
> transformed-resource IQR in every scientific scaler-fit partition across
> Materna-T1, Materna-T2, and Materna-T3.

- Structurally eligible common pool: **398**
- Training-scale eligible across all traces: **74**
- Rejected for one or more zero-IQR training partitions: **324**
- Retention: **18.5930%**

This is a materially narrower population than the structurally valid Materna
VM population. Results must not be generalized without qualification to idle,
quiescent, resource-constant, or temporally intermittent VMs, or to the full
Materna population.

The unique scaler partition key is `(trace, VM_ID, fold, phase, L)`. The audit
covered 398 × 3 traces × 5 folds × 2 phases × 3 contexts = **35,820** scaler
partitions and 143,280 transformed resource-partition cells. Formulation does
not alter scaler partitions.

## Frozen zero-IQR audit

| Trace | CPU | Throughput | Memory | Disk write |
|---|---:|---:|---:|---:|
| Materna-T1 | 187 | 5,070 | 171 | 3,088 |
| Materna-T2 | 123 | 5,167 | 150 | 3,120 |
| Materna-T3 | 135 | 5,186 | 108 | 3,004 |

Throughput and disk-write are by far the dominant causes of scale
ineligibility. This is a technical training-partition property, not a
predictive result.

## Frozen 35-VM cohort

After the structural and scale filters, exact VM IDs were ranked by ascending
SHA-256 of `phase4a-v1|Materna-shared|<exact-VM-ID>`:

`74, 134, 397, 266, 380, 281, 393, 227, 128, 299, 272, 08, 75, 133, 440, 306, 343, 305, 26, 302, 498, 103, 303, 76, 493, 416, 478, 442, 246, 345, 04, 98, 105, 92, 508`

- ID-list SHA-256: `4c9e8f4cfa5cf26c4188924c486cdfbe9d78972eec1f84f5e0f23b1e94353140`
- Selection-record SHA-256: `63c1a7266057c4344bfd6211ee7d3fd2deba283e4b41797fc4e412483469b24b`
- Retained from Phase 4A: `74, 134, 266, 397`
- Original retained count: **4**
- Replaced: **31**

No VM replacement is permitted after this freeze. The same 35 IDs are used in
all three traces.

## Temporal environments, folds, and support

Materna-T1, Materna-T2, and Materna-T3 are separate temporal replication
blocks from the same source, not independent datasets. Each trace independently
uses five chronological expanding outer folds. The latest legal 15% of outer
training is inner validation. Inner and outer training use lead-18 target-time
purge. T1/T2/T3 may not be used as a single train/validation/test chain.

Support uses complete L18 histories in one contiguous segment, finite histories
and five future four-resource target tuples, no segment crossing, and
max-horizon purge. L4 and L9 receive no additional origins. Exact support IDs,
split hashes, and scaler-partition identities are preserved in the manifests.

- Expected and observed support records: **1,575**
- Records per trace: **525**
- Formulation support mismatches: **0**
- Support-minimum failures: **0**
- Candidate scaler failures: **0**
- Leakage violations: **0**

S1, S2, and M1 use exact matched support.

## Resources, transforms, horizons, and contexts

| Resource | Native target | Transform |
|---|---|---|
| CPU | CPU usage % | identity |
| THROUGHPUT | network received + transmitted KB/s | `log1p` |
| MEMORY | memory usage KB | identity |
| DISK_WRITE | disk-write throughput KB/s | `log1p` |

Resource order is CPU, THROUGHPUT, MEMORY, DISK_WRITE. Each resource uses
training-only median/IQR robust scaling. IQR must be strictly positive; there
is no fallback and no epsilon.

- Cadence: 300 seconds
- Sample leads: `[1,2,4,9,18]`
- Horizon minutes: `[5,10,20,45,90]`
- Context candidates: `[4,9,18]`, approximately `[20,45,90]` minutes
- Common support context: L18

No additional horizon or context is permitted.

## Frozen architecture

The external Bitbrains plain-LSTM factorial is unchanged. Models are two-layer,
unidirectional LSTMs with hidden size 64 and dropout 0.1.

| Formulation | Input | Organization | Output | Parameters |
|---|---|---|---|---:|
| S1 | `[N,L,1]` | one model/resource | `[N,5]` | 50,757/model |
| S2 | `[N,L,4]` | one independent model/target | `[N,5]` | 51,525/model |
| M1 | `[N,L,4]` | shared encoder and four resource heads | `[N,4,5]` | 52,500 total |

No architectural modification is permitted.

## Frozen training and selection

- Optimizer: Adam
- Learning rate: 0.001
- Batch size: 256
- Maximum epochs: 50
- Patience: 7
- Gradient clipping: 1.0
- Seeds: `[0,1,2]`
- M1 loss: equal mean of CPU, throughput, memory, and disk-write MSE
- Adaptive weighting: prohibited

S1 and S2 select one L independently per trace/VM/fold/resource using mean
inner-validation NMAE across five horizons and three seeds. M1 selects one L
per trace/VM/fold using equal resource mean inner-validation NMAE across four
resources, five horizons, and three seeds. Ties choose the smaller L.

Each seed retains its own best epoch. Future final fits initialize from scratch,
use complete legal outer training at the fixed selected epoch, and evaluate
outer test exactly once.

## Frozen replication questions

- R1 — Cross-resource input: Is S2 benefit resource/time-block dependent rather
  than broadly beneficial?
- R2 — Shared representation: Does M1 again fail to provide broad improvement
  over S2?
- R3 — Total joint system: Does M1 again fail to outperform S1 broadly?
- R4 — Temporal heterogeneity: Do effects vary across Materna T1/T2/T3?

No new hypothesis is permitted.

## Frozen classification rules

Classification is per trace and comparison:

- `BROAD_POSITIVE` requires overall gain ≥ +1%, positive horizons ≥ 4/5,
  positive VMs ≥ 25/35, positive folds ≥ 4/5, and positive seeds ≥ 2/3.
- `CONDITIONALLY_POSITIVE` requires overall gain > 0, positive horizons ≥ 3/5,
  positive VMs ≥ 15/35, positive folds ≥ 3/5, positive seeds ≥ 2/3, and not
  `BROAD_POSITIVE`.
- `BROAD_NEGATIVE` requires overall gain ≤ −1%, positive horizons ≤ 1/5,
  positive VMs ≤ 10/35, positive folds ≤ 1/5, and positive seeds ≤ 1/3.
- Everything else is `NEUTRAL_OR_MIXED`.

All listed conditions in a class are conjunctive. These thresholds cannot
change after execution.

## Frozen temporal synthesis and bootstrap

Each trace is reported independently first. The descriptive combined point
estimate is `(gain_T1 + gain_T2 + gain_T3) / 3`, labelled
`EQUAL_TEMPORAL_BLOCK_SYNTHESIS`. It is not weighted by duration, origins, rows,
or predictions and is not an independent-dataset meta-analysis.

Future uncertainty uses 10,000 paired VM-cluster bootstrap replicates
separately within each trace. The unit is VM; all five folds and paired
formulation structure are retained. T1/T2/T3 are not statistically independent
bootstrap units. The deterministic Phase 4C RNG policy is preserved.

## Frozen scientific workload

| Scope | S1 inner | S1 final | S2 inner | S2 final | M1 inner | M1 final | Total fits | Metrics | Contexts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Per trace | 6,300 | 2,100 | 6,300 | 2,100 | 1,575 | 525 | 18,900 | 31,500 | 1,575 |
| Three traces | 18,900 | 6,300 | 18,900 | 6,300 | 4,725 | 1,575 | 56,700 | 94,500 | 4,725 |

Combined inner fits are 42,525 and combined final fits are 14,175.

## Preserved non-scientific pilot

The only training conducted for this preflight was the explicitly authorized
technical pilot: 27 models (3 traces × 9 models), first SHA-ranked VM 74, fold
1, seed 0, L9, exactly five epochs, and inner train/validation only. The mean
seconds/epoch range is 0.083989–0.108845. Peak RSS is 392,069,120 bytes.
Outer-test accesses, outer-test predictions, scientific metrics, scientific
context selections, and final refits are all zero. Pilot predictive values have
no scientific interpretation.

## Runtime, storage, and compute decision

| Effective epochs | Four-worker projected wall hours |
|---:|---:|
| 10 | 5.5424 |
| 25 | 13.8561 |
| 50 | 27.7122 |

Projected retained scientific storage is **4,383,480,273 bytes**. The frozen
compute decision is
`FULL_35_VM_THREE_TRACE_REPLICATION_EXPENSIVE_BUT_FEASIBLE`. No cohort
reduction is authorized.

## Frozen publication role

Materna is **SECONDARY_TEMPORAL_REPLICATION** because it has prior DynAPM
exposure and the three temporal traces come from the same source. It is not
pristine primary confirmation and cannot become so based on results. Its
purpose is temporal robustness, a constraint on generalizability,
clarification of mixed H1, an independent probe of the H2 negative-sharing
boundary, and a test of temporal heterogeneity.

## Artifact inventory

The inventory and this freeze manifest are excluded from their own digest to
avoid circular checksum dependencies; the Git commit and annotated tag protect
both metadata files. The Phase 4D tree digest is SHA-256 over sorted UTF-8
records `relative_path,byte_size,sha256\n` for all inventoried substantive
preflight and protocol artifacts. Final entry count, byte total, inventory
SHA-256, and tree SHA-256 are reported by
`build_phase4d_preflight_inventory.py` and in the checkpoint report.

- Inventory: `PHASE4D_MATERNA_PREFLIGHT_ARTIFACT_SHA256.csv`
- Inventory entries: **25**
- Inventory total bytes: **7,854,804**
- Inventory SHA-256: `fc440dcb3dc9039a919b1e38136f1567c239a7609bac3d01ec08c93c3a1d293b`
- Phase 4D preflight-tree SHA-256: `981dfef4b90e8056897bf91c0ad4643c012efc3110d5a348ecfac37bf8dbdc72`
