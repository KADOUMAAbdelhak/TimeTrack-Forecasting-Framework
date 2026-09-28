# Prospective External S1/S2/M1 Replication Design

## Confirmatory questions

- H1: adding all-resource input to an independent plain LSTM does not provide broad improvement over own-resource input (S2 versus S1).
- H2: naive shared multi-target representation does not provide broad improvement over matched independent all-resource models (M1 versus S2).
- H3: any cross-resource benefits are heterogeneous rather than consistently positive across machines, resources, horizons, folds, and independent environments.

These are boundary hypotheses inherited from frozen TimeTrack evidence. No new architecture hypothesis is introduced.

## Environments and replication type

Bitbrains fastStorage and Rnd are two separate, equally weighted pristine confirmation environments. They must not be combined into one pool or assigned development/confirmation roles after observing outcomes. Because their sampling interval and physical units differ from TimeTrack, this is a **conceptual replication**, not an exact replication. Materna is a secondary conceptual replication because its semantics are close but it has prior DynAPM exposure. Alibaba, Google, and Azure do not enter the four-target experiment.

## Fixed model comparison

Retain the Phase 3 plain-LSTM concept: two unidirectional layers, hidden size 64, dropout 0.1, last recurrent output, and linear horizon heads. S1 receives one resource and predicts that resource; S2 receives all four and independently predicts one resource; M1 receives all four and uses one shared encoder with four independent heads. Retain Adam 0.001, batch size 256, maximum 50 epochs, patience 7, clipping 1.0, seeds [0,1,2], equal normalized-space resource weighting for M1, seed-mean context selection, per-seed epoch recording, and fixed-epoch outer refit from scratch.

Dataset-specific adaptations are limited to fields/units, structural invalid-row removal, sample-index representations of elapsed time, eligible entities, and chronological fold timestamps. Transforms remain identity for CPU/memory and log1p for total network throughput/disk-write throughput. Robust median/IQR scalers are fit on the relevant training partition only.

## Time grid, support, and folds

The common real horizons are 5, 10, 20, 45, and 90 minutes. External 5-minute traces use leads [1,2,4,9,18]. Contexts are approximately 22.5, 45, and 90 minutes, represented externally by [4,9,18] samples. Exact mappings and prospective error tolerance `max(2.5 minutes, 15% of desired duration)` are recorded in the harmonization CSVs.

All S1/S2/M1 formulations and all context candidates use one common-support universe built with maximum context 18. Histories must contain all four finite/valid inputs; every one of the four targets at all five leads must be finite/valid and remain inside the same contiguous segment. Shorter contexts receive no extra origins.

Use five expanding chronological outer folds per entity. The first 50% of legal chronological origins forms the initial training region; each successive 10% block is one nonoverlapping outer test. Purge training origins unless their 90-minute target timestamp precedes the first test origin. In each outer training set, the latest 15% is inner validation and the preceding inner train is purged by the same maximum target lead. Exact timestamp boundaries and common-support hashes must be frozen before execution.

## Selection, metrics, and inference

S1/S2 select context independently per entity/fold/resource by the seed-mean transformed/scaled validation MAE over five horizons. M1 selects one context per entity/fold by equal mean across four resources, five horizons, and three seeds. Smaller context wins exact ties. Outer test values cannot affect filtering, scaling, context, epochs, or fitting.

Retain native MAE, RMSE, R-squared, NMAE by training-native IQR, and persistence skill. Average seeds within entity-fold-resource-horizon cells. Report resource-specific macro results with entity-fold cells equally weighted; never average native MAE across resources. Primary matched comparisons are S2-S1 and M1-S2 on identical support. Environment-specific effects precede any equal-environment synthesis. Use paired entity-level bootstrap intervals (resampling entities with all their folds) as uncertainty, fixed before viewing outcomes.

## Workload and stopping boundaries

With 35 VMs per Bitbrains environment, the fixed design implies 14,175 inner fits and 4,725 final fits per environment (28,350 inner and 9,450 final across both). Materna, if separately authorized later, has the same fit counts for its 35-VM shared cohort when the three monthly traces are treated as data blocks within one secondary analysis plan. A non-scientific timing pilot may revise only worker count or establish infeasibility; it may not alter targets, horizons, contexts, entities, models, or hypotheses.

Any identity, support, leakage, fit-count, or validation failure stops interpretation. No conditional gate, selective sharing, adaptive weighting, TCN-v2, or multi-resource PatchTST is authorized.
