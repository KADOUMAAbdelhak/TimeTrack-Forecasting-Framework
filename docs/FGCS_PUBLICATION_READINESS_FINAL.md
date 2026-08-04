# FGCS publication readiness — FINAL assessment

**Decision: GO**

Date: 2026-08-04  
Reporting freeze: `final-reporting-freeze-v2`  
Peeled commit: `4408cd1733d57014026cfa6fb477842fe4645a20`

Historical status before this assessment: **CONDITIONAL GO**  
(see `docs/FGCS_PUBLICATION_READINESS_PRE_ROBUSTNESS.md` and
`docs/PUBLICATION_GATE_CORRECTION.md`).

## Authoritative freezes (immutable)

| Layer | Tag | Implementation | Peeled commit |
|-------|-----|----------------|---------------|
| Predictions | experiment-freeze-v2 | `9f1bebb5…` | `bb34ddfc…` |
| Primary statistics | final-analysis-freeze-v1 | `c4f5a18e…` | `a93997fe…` |
| Peak analysis | final-peak-analysis-freeze-v1 | `96e1218e…` | `7586be02…` |
| Robustness extension | final-robustness-extension-freeze-v2 | `bb6e12a2…` | `97506266…` |
| Robustness statistics | final-robustness-analysis-freeze-v2 | `19bf5a4e…` | `a4337a8e…` |
| Reporting | final-reporting-freeze-v2 | `88ea98f8…` | `4408cd17…` |

Dataset fingerprint: `bf06dc0e7fe6ff5e`  
Scientific protocol hash: `8bce84c8007fa60d`  
Provenance envelope hash: `323036f95a253e82`

## Gate assessment

| Gate | Name | Status |
|------|------|--------|
| 1 | Reproducibility | **PASS** — immutable tags; dual hashes; source hashes unchanged; full suite 138 passed |
| 2 | Baseline strength | **PASS** — persistence, EWMA, Ridge, LightGBM, DLinear |
| 3 | Stochastic robustness | **PASS** — LightGBM/DLinear seeds 0/1/2; individual-seed evidence |
| 4 | Statistics | **PASS** — MBB, direct relative CIs, Holm, seed-aware, immutable analysis freeze |
| 5 | Practical contribution | **PASS** — LightGBM vs Ridge (~−17.3%); MinT vs independent (~−10.1%); DLinear recon consistent; coherence restored; trade-offs disclosed |
| 6 | Breadth / negative evidence | **PASS** — CPU positive; memory conditional; disk boundary; peaks; EWMA; multi-seed; negative memory/disk disclosed |
| 7 | Novelty risk | **PASS** — no first/SOTA/universal claims |
| 8 | Honesty / limitations | **PASS** — single dataset; 42.285 s sampling; core mapping; disk semantics; transferred LGBM disk; no network/downsampling/conformal; EWMA strongest on memory; peak non-generality; LGBM seed invariance from deterministic config; one DLinear memory seed-unstable cell |

## Decision rule application

Primary CPU claims survive EWMA and multi-seed testing. Provenance for
authoritative v2 tags is immutable. Memory and peak claims are correctly scoped
as conditional / diagnostic. No unresolved blocker affects the primary
contribution.

**Final decision: GO**

## Manuscript scope (not written here)

See the aggregation report section *Final manuscript scope*.
Next action: `READY_FOR_OFFICIAL_FGCS_LATEX_TEMPLATE`.
