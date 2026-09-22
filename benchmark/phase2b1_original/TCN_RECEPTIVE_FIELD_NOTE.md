# Frozen TCN Receptive-Field Note

## Frozen architecture

The frozen B4 model has:

- two residual temporal blocks;
- two causal convolutions in each block;
- kernel size `k = 3`;
- block dilations `d = 1` and `d = 2`;
- channel widths `[32, 32]`;
- dropout 0.1;
- a head applied only to the final sequence position.

The residual paths are identity or pointwise `1x1` convolutions and do not
increase temporal receptive field.

## Calculation

For stride-one convolution, a layer with kernel `k` and dilation `d` expands
the receptive field by `(k - 1)d`. Starting with receptive field 1:

`R = 1 + 2(3-1)(1) + 2(3-1)(2) = 1 + 4 + 8 = 13`.

Equivalently, the four temporal convolutions add `2, 2, 4, 4` samples.
Therefore the final-position prediction can depend only on the final 13 input
positions.

## Relationship to context length

For all frozen candidates:

| L | Positions available | Positions reachable by the final head | Unreachable earlier positions |
|---:|---:|---:|---:|
| 32 | 32 | 13 | 19 |
| 64 | 64 | 13 | 51 |
| 128 | 128 | 13 | 115 |

The input tensor retains the full `L x channels` sequence, but observations
earlier than `t-12` cannot affect a sample's forward prediction. Train-fitted
feature mean and standard deviation use all training-window values, but this
does not transmit the earlier positions of an individual sample to the head.

## Assessment

B4 is executable exactly as frozen and the implementation satisfies the
protocol's literal architecture and causality statements. The protocol does
not explicitly claim that the final head's receptive field spans all of `L`.

It is nevertheless scientifically limited: selecting among `L=32/64/128`
does not select a longer usable temporal dependency range. Differences can
arise from eligibility, training samples, and scaling statistics, while the
per-sample learned receptive field remains 13. This limitation should be
declared in any later Phase 2B-2 decision. No TCN code or architecture was
changed by this audit.
