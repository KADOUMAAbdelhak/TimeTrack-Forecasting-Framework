# Prospective Neural Benchmark V2 Decision

Decision date: 2026-09-23 (Europe/Helsinki)

Repository state at decision:

- Current HEAD: `bdc7c9243cb33cbb3fadee7b911810a164d8da43`
- Corrected deterministic freeze tag:
  `phase2b1-corrected-deterministic-freeze-v1`
- Phase 2A freeze commit:
  `0b4269270b0a121f0ba1e19355c6cd24b72abeb5`
- Phase 2A freeze tag: `phase2a-benchmark-protocol-freeze-v1`

## Prospective architecture decision

Phase 2A froze DLinear and a shallow B4 TCN design, but neither model received
a scientific full benchmark run. Before any scientific neural execution,
source inspection established that the frozen B4 TCN has an effective
receptive field of only 13 samples, shorter than every candidate context length
in `{32, 64, 128}`.

A separate neural-v2 benchmark extension is therefore created prospectively.
The Phase 2A protocol and B4-v1 source remain preserved exactly for provenance;
neural-v2 does not retroactively modify or replace them. No neural scientific
result was executed or inspected before this decision.

Neural-v2 will evaluate four fixed baselines: DLinear, a conventional
unidirectional LSTM, a full-receptive-field causal TCN, and a compact
PatchTST-style encoder. The v2 TCN uses two causal convolutions per residual
block, kernel size 3, and dilations `[1, 2, 4, 8, 16, 32]`, giving an effective
receptive field of 253 samples and covering the maximum history length 128.

## Prospective feature-scope decision

The already frozen corrected deterministic Phase 2B-1 evidence found:

- LightGBM F1 throughput mean matched-F0 MAE gain: `+0.719%`;
- LightGBM F1 positive machine averages: `5/7`;
- LightGBM F1 positive fold averages: `4/5`;
- LightGBM F1 positive aggregate gain at all eight real leads;
- F2/F3 leave-one-machine-out context: broadly negative;
- F4/F5 combined context: broadly negative.

Accordingly, neural-v2 investigates exactly two feature sets:

- `F0_LOCAL`: target-machine CPU only;
- `F1_THROUGHPUT`: target-machine CPU plus validated same-machine total
  throughput (`bond0 TX + bond0 RX`).

This narrowing is explicitly evidence-informed by the frozen deterministic
phase. It is not claimed to be an untouched confirmatory hypothesis. LOMO CPU,
memory, disk, RTT, jitter, packet telemetry, and per-core CPU are excluded.

Both feature sets will use the same F1-finite sample support by construction so
that feature-value comparisons differ only by the throughput input channel.
No final proposed model or multi-target forecaster is part of this extension.
