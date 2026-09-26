# Phase 3B Plain-LSTM Factorial Decision

Date: 2026-09-26 (Europe/Helsinki)

This record is prospective. It is frozen before implementation testing and
before the bounded timing pilot. Phase 3B is a preflight for a deliberately
plain LSTM S1/S2/M1 factorial; it is not a scientific benchmark execution.

## Frozen targets

The selected four-resource tuple and transforms are exactly those accepted in
Phase 3A:

| Resource index | Resource | Canonical column | Transform |
|---:|---|---|---|
| 0 | CPU | `machineXX__cpu_utilization` | identity |
| 1 | THROUGHPUT | `machineXX__throughput_total` (bond0 TX + bond0 RX) | `log1p` |
| 2 | MEMORY | `machineXX__memory_used` | identity |
| 3 | DISK_WRITE | `machineXX__disk_write` | `log1p` |

The fixed resource order is `CPU, THROUGHPUT, MEMORY, DISK_WRITE`. The fixed
horizon order is `[1,2,4,8,16,32,64,128]`.

No disk occupancy, disk read, memory-utilization percentage, raw throughput,
separate TX/RX, LOMO, RTT, jitter, or packet-telemetry substitution is allowed.

## Factorial definitions

- **S1:** one independent plain LSTM per target resource, consuming only that
  resource's history and producing eight horizons.
- **S2:** one independent plain LSTM per target resource, consuming the ordered
  four-resource history and producing eight horizons for that target.
- **M1:** one shared plain LSTM consuming the ordered four-resource history,
  with exactly four independent linear heads producing the ordered
  `[resource, horizon]` outputs.

All primary S1/S2/M1 cells use identical legal origins derived from complete
four-resource finiteness with maximum context `Lmax=128`, segment-safe histories
and targets, all eight target leads, and lead-128 target-time purges. Shorter
contexts and single-resource formulations receive no additional samples. The
predicted resource does not alter support.

## Backbone and exclusions

LSTM is the primary Phase 3B factorial backbone: hidden size 64, two
unidirectional recurrent layers, dropout 0.1, final recurrent representation,
and linear output head(s). No proposed or novel architecture is being tested.
Attention, adapters, private encoders, selective fusion, gating, adaptive loss
weighting, machine embeddings, mixture-of-experts, and Transformers are outside
this phase.

## Pilot boundary

The only permitted pilot is non-scientific: `machine01`, outer fold 1, seed 0,
`L=64`, exactly five epochs, nine models (four S1, four S2, one M1). It does not
select context length, does not early-stop, and must use only the full legal
inner-training and inner-validation partitions.

Outer-test origins, values, metrics, predictions, and performance are
inaccessible to the pilot. No final outer refit or scientific outer evaluation
is permitted. Pilot accuracy may be used only for transform, ordering,
numerical, timing, and loss-balance sanity checks.
