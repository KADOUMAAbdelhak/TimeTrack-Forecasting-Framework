# Phase 3B Plain-LSTM Factorial Freeze Manifest

## Checkpoint identity

- Freeze date: 2026-09-27 (Europe/Helsinki)
- Pre-freeze HEAD: `70eea336302aebfaaa20c79b1972b1ebb835442c`
- Phase 3A commit: `70eea336302aebfaaa20c79b1972b1ebb835442c`
- Phase 3A tag: `phase3a-multiresource-design-freeze-v1`
- Prospective decision SHA-256:
  `2bfb2610bd8e869dc038bccd6b18656cd2c968b9d548c758487cae500cbf5677`
- Configuration SHA-256:
  `fe985007ebd72417dcab8e8a1851c358d3d9a3da26f372595ac7ff6b499eedd6`
- Artifact inventory: `multiresource/04_lstm_factorial/PHASE3B_ARTIFACT_SHA256.csv`
- Inventory entries: 31
- Inventory SHA-256:
  `7e4d5b7dd858ecb79dab0ea3355fad0b029e34a18cbfb15b25d114e1886ead65`

The inventory contains repository-relative path, byte size, and SHA-256 for all
substantive Phase 3B implementation, test, protocol, validation, and compact
pilot artifacts that existed before checkpoint metadata was added. The
inventory and this manifest are excluded from the inventory to avoid a circular
checksum dependency.

**NO SCIENTIFIC S1/S2/M1 RESULT EXISTED AT FREEZE TIME.**

Scientific S1 runs: **0**. Scientific S2 runs: **0**. Scientific M1 runs:
**0**. Outer-test predictions: **0**. Proposed multi-task architectures: **0**.

## Frozen target and horizon order

| Index | Resource | Canonical target | Transform |
|---:|---|---|---|
| 0 | CPU | `machineXX__cpu_utilization` | identity |
| 1 | THROUGHPUT | `machineXX__throughput_total` | `log1p` |
| 2 | MEMORY | `machineXX__memory_used` | identity |
| 3 | DISK_WRITE | `machineXX__disk_write` | `log1p` |

The horizon order is `[1,2,4,8,16,32,64,128]`. Every resource is scaled after
its transform with the median and IQR fitted only on the applicable training
partition. Inner preprocessing uses inner train; final preprocessing must be
refit on complete legal outer train. Non-positive IQR is a fatal error.

## Frozen common support

The primary factorial uses a single legal-origin universe derived from the
complete four-resource tuple, maximum history `L=128`, all eight future targets,
canonical segment safety, required history, and lead-128 target-time purging.
Contexts 32 and 64 do not gain samples. Target identity does not alter support.

For every machine/fold/context, S1, S2, and M1 must share identical inner-train,
inner-validation, final outer-train, and outer-test origin IDs and hashes. The
frozen support manifest contains 105 machine/fold/context records and has
**0 support mismatches**.

## Frozen factorial and architecture

- **S1:** one independent model per target resource; own-resource history only,
  input `[N,L,1]`, output `[N,8]`.
- **S2:** one independent model per target resource; ordered four-resource
  history, input `[N,L,4]`, output `[N,8]`.
- **M1:** one shared LSTM encoder consuming `[N,L,4]`, with exactly four
  independent linear resource heads and output `[N,4,8]`. The heads contain no
  hidden layers.

S2 versus S1 measures cross-resource input value. M1 versus S2 measures shared-
representation/multi-task value. M1 versus S1 measures total joint-system
value.

All models use a two-layer unidirectional LSTM, hidden size 64, dropout 0.1,
and the final recurrent representation. No attention, adapters, gating,
private encoders, selective fusion, task weighting, machine embeddings,
mixture-of-experts, Transformer, or other proposed novelty is present.

| Formulation | Parameter accounting | Total system parameters |
|---|---|---:|
| S1 | 50,952 per resource model | 203,808 across four models |
| S2 | 51,720 per target model | 206,880 across four models |
| M1 | 51,200 shared encoder + 2,080 across four heads | 53,280 |

Parameter counts are not artificially equalized. Future reporting must include
both forecasting accuracy and total-system efficiency.

## Frozen training and loss

- Optimizer: Adam
- Learning rate: 0.001
- Batch size: 256
- Maximum epochs: 50
- Early-stopping patience: 7
- Gradient clipping: 1.0
- Seeds: `[0,1,2]`
- Context candidates: `[32,64,128]`
- Additional hyperparameter search: none

S1 and S2 minimize mean squared error over batch and eight horizons in
transformed, training-only robust-scaled space. M1 computes one such mean MSE
per resource and minimizes exactly:

```text
(L_CPU + L_THR + L_MEM + L_DISK) / 4
```

There is no uncertainty weighting, GradNorm, learned weighting, loss rescaling,
dynamic weighting, or manually chosen resource coefficient. M1 is the naive
shared-representation baseline.

## Preserved pre-execution M1 loss imbalance

The non-scientific pilot's final-three-epoch means are frozen exactly:

| Resource | Train MSE | Train share | Validation MSE | Validation share |
|---|---:|---:|---:|---:|
| CPU | 273.197 | 83.96% | 266.109 | 80.81% |
| Throughput | 2.227 | 0.68% | 1.805 | 0.55% |
| Memory | 28.129 | 8.65% | 33.812 | 10.27% |
| Disk-write | 21.828 | 6.71% | 27.597 | 8.38% |

Although each resource has an equal nominal coefficient of one quarter, the
numerical MSE magnitudes remain highly unequal after the frozen transforms and
scaling. Optimization pressure may therefore be dominated by CPU. This is a
**pre-execution scientific risk**.

This diagnostic does not establish that M1 will fail, that negative transfer
will occur, or that adaptive weighting would improve results. Those questions
require the full scientific factorial. The observation may motivate a later
ablation or mechanism only if the scientific factorial exhibits an appropriate
failure pattern. The imbalance was not modified or "fixed" during freeze.

## Frozen physical inversion

CPU and memory predictions receive inverse robust scaling. Throughput and
disk-write receive inverse robust scaling, `expm1`, and deterministic physical
projection `max(0, prediction)`. Primary native-unit metrics use the projected
prediction, while the pre-projection negative fraction is retained as a
diagnostic. The pilot observed a 0% negative fraction for both throughput and
disk-write.

## Frozen selection and epoch lifecycle

S1 and S2 select one context per target resource/machine/fold by mean inner-
validation normalized MAE over eight horizons and three seeds. M1 selects one
context per machine/fold by an equal mean over four resources, eight horizons,
and three seeds. Candidate contexts are 32, 64, and 128; smaller context wins a
tie. Outer test has no role.

Inner fitting may early-stop only against inner validation. At the selected
context, each seed retains its own best epoch. Final scientific models must be
initialized from scratch, use full legal outer-training support and refitted
scalers, train for the seed-specific fixed epoch count, and expose no outer-test
early stopping. Outer test is evaluated once after fitting.

## Frozen metrics and aggregation

Native MAE, RMSE, R-squared, NMAE, and persistence skill are recorded for every
resource/machine/fold/seed/lead. Native MAEs are never aggregated across
resources.

For primary stochastic aggregation, metrics are computed at machine-fold-seed-
resource-lead level; seeds are averaged within machine-fold-resource-lead;
machine-fold cells receive equal weight; formulation macro MAEs are aggregated
separately; and relative improvement is calculated from those macro MAEs.

Per resource, the primary comparisons are:

```text
S2 vs S1 = 100 * (MacroMAE_S1 - MacroMAE_S2) / MacroMAE_S1
M1 vs S2 = 100 * (MacroMAE_S2 - MacroMAE_M1) / MacroMAE_S2
M1 vs S1 = 100 * (MacroMAE_S1 - MacroMAE_M1) / MacroMAE_S1
```

Pooled metrics, cell-relative gains, and machine/fold/seed consistency remain
secondary diagnostics.

## Frozen scientific workload

| Formulation | Inner fits | Final fits | Total fits | Final resource-lead rows |
|---|---:|---:|---:|---:|
| S1 | 1,260 | 420 | 1,680 | 3,360 |
| S2 | 1,260 | 420 | 1,680 | 3,360 |
| M1 | 315 | 105 | 420 | 3,360 |
| **Total** | **2,835** | **945** | **3,780** | **10,080** |

None of this scientific workload had run at freeze time.

## Non-scientific pilot and planning projection

The sole pilot used machine01, outer fold 1, seed 0, context 64, exactly five
epochs, and full legal inner-training/validation support. It contained four S1,
four S2, and one M1 model. No context selection, outer refit, or outer-test
value/prediction/performance access occurred.

- S1 five-epoch training: approximately 5.08-5.10 seconds/model
- S2 five-epoch training: approximately 5.11-5.13 seconds/model
- M1 five-epoch training: approximately 5.14 seconds
- Peak process RSS: approximately 1.33 GB

Pilot-derived full-factorial planning estimates are 12.27 CPU-hours at 10
effective epochs, 30.68 CPU-hours at 25 effective epochs, and 61.36 CPU-hours
at 50 epochs. Expected retained disk use is approximately 1.073 GB. These are
planning estimates, not scientific results.

## Source and test identities

| Source | SHA-256 |
|---|---|
| `src/__init__.py` | `97c77ec6e02ef6f2d9e31349f3f4189921f5fa6a000d0a5a583b76c626b0dfa8` |
| `src/data.py` | `d3cdee2b0743250065599c331d3263fb9cbb7a27a355ba262d347b8500b44f68` |
| `src/metrics.py` | `9dd8a23d7649127a1a4b4f1cb12bbe452c63785be7d0eb646d7883fc2fbad87d` |
| `src/models/__init__.py` | `9b91a721934b809fcf8b2ac7c97c5c59dcfb00ddee78f48854c13326c82fa33c` |
| `src/models/lstm.py` | `e1eb8cfa453ce8cc119cac8d422e84af5186a478c4dfa1cff8d2e7a9961a8f08` |
| `src/runner.py` | `50cae33c6e4381bdc57e7e1ace2307b36bc078d43efecc16a487222847ce82f6` |
| `src/selection.py` | `080a1018a66b5b835fd1adcc9f4a76a1ce2b44a2efb81d1ee899e67cf063ffab` |
| `src/splits.py` | `f7f2927928bc409888e4cffd025aa3d7ac416326a674065a0b504c296b9d081c` |
| `src/support.py` | `9bbd330f731feb29542ffe69cf2007ea5e546560972d9ba3cfeda85b13644796` |
| `src/training.py` | `a05bbbf72b3d39c211a9ebca7eecfbaf2e27164cbc11e711495b8bd50ca63678` |
| `src/transforms.py` | `5ffe639620277ac5923e018db7099048bd3b8a9171c69601cd816dd2bfca8b86` |
| `src/validation.py` | `31496f86e8bc765f35bbfbcaa59dbc3e6e03731d28cdef0c38b9710d416004d4` |
| `validate_preflight.py` | `68b884eae21d6d2af713430fd7bbf5d3bef63fff075983cea853df70d5a553d8` |

| Test | SHA-256 |
|---|---|
| `tests/conftest.py` | `94df2cad22f2f29527f86a56b3c702406053ee2ea735eea02f6b03e2d9fb8f8d` |
| `tests/test_data_support_transforms.py` | `c462e012815a9b718e333142977b8b7eb19b5cfc9cef7623562f6847387d5094` |
| `tests/test_models_training.py` | `d90789ce180444bc93aceb324d6c19acf2f1dac3a19baafaebf1b800d5b35cea` |
| `tests/test_selection_metrics_validation.py` | `acbc242a0af2c771f7ec71a901c2b85c431295d78a6b9845ccc9a5a0d4465ef5` |

## Scientific risks

1. Four-resource common support is materially smaller than CPU-only support.
2. Separate-machine S1/S2 requires many models.
3. CPU and memory have different persistence behavior.
4. Throughput and disk-write require transformed-space training and physical
   inversion.
5. Equal robust scaling does not equalize task difficulty; the pilot showed
   CPU-dominated numerical loss.
6. M1 uses one inference system where S2 uses four, so accuracy and efficiency
   both matter.
7. Weak cross-resource dependencies make negative transfer plausible.
8. Plain M1 is intentionally not novel; it tests naive sharing first.

## Validation and prior-history integrity

The Phase 3B test suite passed **48/48**. Independent preflight validation is
**PASS**, with nine pilot models at exactly five epochs, 96 non-scientific
sanity-metric rows, 105 support records, zero support mismatches, and no
scientific execution, scientific selection, final outer refit, outer-test
prediction, proposed architecture, or TCN-v2 run.

Prior frozen evidence also passes unchanged:

| Evidence | Verified entries | Result |
|---|---:|---|
| Phase 3A | 25 | PASS |
| Neural-v2 | 29 | PASS |
| DLinear | 1,347 | PASS |
| LSTM | 1,349 | PASS |
| PatchTST | 1,352 | PASS |
| Phase 2A | 33 | PASS |
| Original deterministic | 632 | PASS |
| Corrected deterministic | 1,070 | PASS |
| Raw files | 6 | PASS |

The canonical panel remains
`c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`.
No prior scientific artifact, raw input, Phase 3A artifact, or canonical panel
was modified while creating this checkpoint.
