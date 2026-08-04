# Final reporting protocol v2 (robustness-aware)

Tag: `final-reporting-freeze-v2`  
Supersedes: `final-reporting-freeze-v1` (archived under `results/final/archive/pre_robustness_aggregate/`)

## Purpose

Aggregate claim-eligible final evidence from accepted prediction, analysis, and
robustness packs. Never train models. Never regenerate predictions. Never
consume rejected provisional packs.

## Freeze immutability

Tags are immutable. Corrections require a new versioned freeze tag.
Never use `git tag -f` or force-push for freeze tags.

## Hash separation

- `scientific_protocol_hash`: numerical evidence, claim rules, rounding, gates
- `provenance_envelope_hash`: freeze tags, peels, paths, archive/supersedes, artifact hashes

A provenance-only change is not a scientific protocol change.

## Runner

```bash
python scripts/aggregate_final_evidence.py \
  --registry configs/final_evidence_registry_v2.yaml \
  --config configs/final_reporting_v2.yaml \
  --output results/final/aggregate \
  --require-frozen
```
