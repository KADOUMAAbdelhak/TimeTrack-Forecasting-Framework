# FGCS publication readiness

Assessment date: 2026-08-04  
Evidence registry: `configs/final_evidence_registry.yaml`  
Aggregate: `results/final/aggregate/`  

Gates evaluated against `docs/PUBLICATION_GATES.md` **without rewriting thresholds**
after seeing final outcomes. Deviations are disclosed, not redefined.

---

## Gate 1 — Reproducibility

**Pass (with disclosed gaps).**

- Tests: 112 passed at reporting freeze.
- Freeze tags + peeled commits recorded for prediction, statistics, peaks, reporting.
- Dataset fingerprint `bf06dc0e7fe6ff5e`; source pack + artifact hashes in aggregate MANIFEST.
- Locked deps / smoke reproduce path available via project scripts.
- Known deviations: analysis CLIs often omit peak RSS; provisional stats archived;
  downsampling omitted; 38366f1 provenance-only tag peel.

## Gate 2 — Baseline strength

**Pass with documented deviation.**

Present in freeze-v2 finals: persistence, Ridge, LightGBM, DLinear, hierarchical
reconciliation (independent / bottom_up / WLS / MinT; OLS ablation; disk top_down).

**Deviation:** EWMA is listed in Gate 2 but was **not** included in the
`experiment-freeze-v2` pack matrix. Persistence is the primary naive baseline.
This is disclosed under Gate 8; it does not invalidate the hierarchical CPU claim.

## Gate 3 — Experimental breadth

**Pass with documented deviation.**

- Metric families: CPU, memory, disk (≥2). Network not in finals.
- Horizons: 3 (CPU/memory); 2 (disk).
- Machines: 7-machine hierarchy bottoms.
- Outer folds: 3 chronological.
- **Deviation:** stochastic models use seed `0` only (not ≥3 seeds). Disclosed.

## Gate 4 — Statistical support

**Pass.**

- Paired moving-block bootstrap (n_boot=5000), direct relative-effect CIs.
- Holm within predefined families; fold consistency; effect sizes.
- Claims use atomic counts (not one pooled CI).
- Peak analysis separately frozen and reconstruction-verified.

## Gate 5 — Practical significance

**Pass (criterion A on CPU; B coherence).**

- CPU same-model reconciliation: ~7–10% relative MAE vs independent across
  Ridge/LightGBM/DLinear; **all** evaluated fold×horizon recon cells improve
  (Claim B supported).
- LightGBM MinT ≈ **29.5%** vs persistence (best observed).
- Coherence error reduced to ~0 for BU/WLS/MinT on CPU and memory (≫50%
  coherence-error reduction with non-inferior / improved accuracy).
- Memory: conditional modest gains (Claim C partial) — secondary evidence.
- Disk: boundary negative result (practical contribution as limitation map).

## Gate 6 — Robustness / Ablation

**Pass.**

- Not single-horizon or single-fold driven for primary CPU claim.
- Ablations: independent, bottom_up, WLS, MinT; OLS where present; disk top_down;
  nonnegative flags recorded as false in primary tables.
- Negative results retained: memory LightGBM; disk Ridge BU; unsupported peak
  generality (P1/P2/P4); DLinear peak compression (P5 partial).

## Gate 7 — Novelty risk

**Pass (honest positioning).**

Literature audit (HARMONY, FRT, MaMiClif, classical MinT) implies **no “first”**
and **no SOTA** claims. Contribution is empirical hierarchy-aware forecasting +
reconciliation for cloud telemetry under a frozen protocol, with boundary and
peak qualifications.

## Gate 8 — Honesty and limitations

**Pass.**

Disclosed: 42.285 s sampling; major outage context in dataset docs; verified CPU
cores (20/24 for m05/m07); disk transferred memory-family hyperparameters;
no network final experiment; downsampling blocked; no probabilistic finals;
missing inference/recon timing fields; peak claims narrow (P3 + LGBM-specific).

---

## Decision

# GO

### Justification

Primary CPU hierarchical claim is statistically and practically supported under
frozen dual analysis layers; coherence contribution is clear; memory is useful
secondary/conditional evidence; disk supplies a meaningful boundary; provenance
and hashes are adequate; exclusions (downsampling/optional packs) are not
required blockers under Gate 5–8 as written for this contribution.

Gate 2 EWMA absence and Gate 3 single-seed are **limitations**, not unresolved
validity blockers for the primary claim.

---

## Proposed manuscript scope (GO only)

**Scoped title (proposal):**  
*Hierarchy-Aware Forecasting and Reconciliation for Cloud Cluster Telemetry*

**Research questions (scoped):**

1. Does hierarchical reconciliation improve aggregate CPU forecast accuracy while
   restoring machine–cluster coherence?
2. How do WLS/MinT behave for memory relative to persistence and independent
   forecasts?
3. Where does reconciliation fail (disk boundary)?
4. Do aggregate MAE gains imply peak-operational gains?

**Contributions:**

1. Frozen multi-fold evaluation of hierarchy-aware forecasting on verified CPU /
   memory / disk structures.
2. Evidence that reconciliation improves learned CPU aggregates fold-consistently
   with exact coherence restoration.
3. Method-dependent boundary result on disk and conditional memory effects.
4. Peak analysis showing LightGBM high-load strength without claiming universal
   recon peak benefits.

**Main tables:** Table 1–6 (registry, CPU, memory, disk, statistics, claims).  
**Main figures:** cpu/memory accuracy vs horizon; coherence; trade-off; bootstrap;
disk boundary; method selection map.  
**Supplementary:** peak tables/figures; efficiency; OLS/nonnegative ablations;
LightGBM disk stress.

**Explicit exclusions from manuscript claims:** downsampling, network, conformal,
LSTM confirmation, adaptive router, global LOMO, SOTA/first language.

**Next step:** provide the official FGCS LaTeX template before any manuscript
prose.
