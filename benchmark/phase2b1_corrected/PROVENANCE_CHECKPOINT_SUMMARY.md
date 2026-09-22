# Phase 2B-1 Matched-F0 Provenance Checkpoint

Status: **COMPLETE — VALIDATION PASS**

- Prospective decision SHA-256:
  `72b5bf5b984c5eeb5b8d4b21b83f9b2fa9807f6fc944c79ee5edc89aeb33dd8e`
- Matched-support manifest SHA-256:
  `d5d9fcf14040a5b60794803bc054ffcc91418c0677073696a522ce4c220d0516`
- Completed comparators: 350/350
- Failed comparators: 0
- Ridge: 2,625 inner fits; 175 final fits; 10.2 s wall
- LightGBM: 33,600 inner lead models; 1,400 final lead models;
  8,607.403 s wall
- Contextual candidate reruns: 0
- Corrected prediction files: 350
- Corrected lead-metric rows: 2,800
- Support-hash failures: 0
- Candidate/F0 sample-ID mismatches: 0
- Candidate/F0 target mismatches: 0
- Metric, Ridge prediction, and gain recomputation maximum differences: 0
- Frozen source/config/protocol hashes: 33/33 unchanged
- Original heavy artifacts: 632/632 unchanged
- Raw hashes: unchanged
- Canonical panel SHA-256:
  `c5a878881afb06b7406a922c06f0c8e9104b2bb89d9519c4f7869b8ddc15625a`
- Scientific decision: **CONDITIONALLY_SUPPORTED**

The condition is narrow: LightGBM with same-machine throughput is positive at
all eight aggregate leads and on five of seven machine averages and four of
five fold averages. Ridge throughput, both LOMO variants, and both combined
contexts remain adverse in aggregate.

No Phase 2B-2 model, TCN change, multi-target model, commit, push, or Git
staging operation was performed.
