# Hierarchical Forecasting Literature Audit (no manuscript prose)

Scope: support a **scoped** novelty claim for TimeTrack C1 before experiment freeze.  
This document is an evidence table, not Related Work writing.  
Date: 2026-08-04.

## Candidate contribution framing (pending evidence)

> A hierarchy-aware forecasting and reconciliation framework for multi-level
> compute, storage, and network telemetry collected from a physical
> OpenAirInterface CI/CD infrastructure.

Do **not** claim “first” unless no overlapping work covers the same combination
of domain + exact/approximate physical constraints + method selectivity (including
disk bottom-up degradation).

## Classification legend

| Field | Meaning |
|-------|---------|
| Infra domain | Cloud, DC, telecom, energy, retail, etc. |
| Hierarchy type | Product/geo tree, microservice, host↔cluster physical sum, etc. |
| Physical multi-level constraints | Exact summing / weighted cores / approximate NIC aggregation |
| Telecom / OAI CI telemetry | Explicitly yes/no |
| Overlap risk | none / partial / high |

---

## Core reconciliation methodology (general HTS)

| Citation | Year | Domain | Hierarchy | Models | Reconciliation | Metrics | Datasets | Physical multi-level? | Telecom/OAI? | Differs from TimeTrack |
|----------|------|--------|-----------|--------|----------------|---------|----------|----------------------|--------------|------------------------|
| Hyndman et al., “Optimal combination forecasts for hierarchical time series” | 2011 | General / retail-style | Tree | ARIMA/ETS-style | OLS combination | RMSE etc. | Standard HTS | No (economic aggregates) | No | Method foundation; not infra telemetry |
| Wickramasuriya, Athanasopoulos, Hyndman, “Optimal forecast reconciliation… MinT” (JASA) | 2019 | General | Hierarchical/grouped | Base + MinT | MinT / shrink | Accuracy | Multiple empirics | No | No | Core algorithm we reuse; not OAI multi-metric |
| Panagiotelis et al., geometric view of reconciliation | 2021 | General | HTS | Various | Geometric / bias insights | — | — | No | No | Theory; not our deployment domain |
| Hyndman & Athanasopoulos, FPP3 Ch.11 | book | Pedagogy | HTS | Many | BU/TD/OLS/WLS/MinT | — | — | No | No | Textbook baseline |

---

## Cloud / data-center / workload hierarchical forecasting

| Citation | Year | Domain | Hierarchy | Models | Reconciliation | Metrics | Datasets | Physical multi-level? | Telecom/OAI? | Differs from TimeTrack |
|----------|------|--------|-----------|--------|----------------|---------|----------|----------------------|--------------|------------------------|
| HARMONY — Adaptive two-stage cloud resource scaling via hierarchical multi-indicator forecasting (arXiv:2408.01000) | 2024 | Cloud GPU/resource scaling | Multi-indicator hierarchical attention | Deep hierarchical + Normalizing Flows + Bayesian decision | End-to-end hierarchical modeling (not classical MinT post-hoc) | Scaling cost / SLA / accuracy | Large cloud datasets + deployment | Soft hierarchical indicators, not machine→cluster exact sum + NIC approx | No | Different method class (end-to-end DL + decisions); not OAI CI multi-metric physical sums; we evaluate classical MinT/WLS/BU selectivity |
| FRT — Flow-based Reconcile Transformer (KDD 2025) | 2025 | Industrial + DC app-server workloads | Hierarchical TS | Flow + Transformer (joint forecast+reconcile) | Built-in coherent deep recon | Accuracy | Public HTS + company DC servers | Hierarchical workload levels | No | Deep end-to-end; not leakage-safe classical recon study on OAI physical memory/CPU/disk/network |
| MaMiClif — Macro-Micro Collaborative Learning for LDC microservice indicators (WWW companion / related 2025) | 2025 | Logical data-center microservices | Macro graph + micro indicator causality | Graph + causal attention | Collaborative learning (not MinT suite) | Indicator forecast accuracy | Ant Group LDC_MS | Microservice logical hierarchy | No | Microservice graphs ≠ machine UM/UD/CU summing + bond0 approx |
| TempoSight — hybrid DL resource forecasting for carbon-intelligent DCs | 2025 | Cloud DC / IIoT | Multivariate resource (not classical recon) | PatchTST+LSTM | None (forecast-focused) | RMSE/MAPE | Alibaba, Bitbrains | No MinT-style coherence enforcement | No | No reconciliation methods comparison |
| Adaptive hierarchical cloud resource scaling (related hierarchical multi-indicator literature) | 2024 | Cloud | Multi-indicator | DL | Decision-oriented | Utilization / cost | Cloud traces | Soft hierarchy | No | Overlaps “hierarchical cloud forecasting” language but not our reconciliation ablation + disk boundary |

**Overlap risk with HARMONY/FRT:** **partial**. Both address hierarchical cloud workloads and coherence. They do **not** invalidate a scoped claim about classical reconciliation on **physical OpenAirInterface CI/CD multi-level telemetry** (exact memory/disk sums, verified core-weighted CPU, approximate bond0 NIC) with method selectivity and negative disk-BU findings. Avoid “first hierarchical cloud forecasting” language.

---

## Energy / industrial hierarchical coherent forecasting (adjacent)

| Citation | Year | Domain | Hierarchy | Models | Reconciliation | Physical? | Telecom? | Differs |
|----------|------|--------|-----------|--------|----------------|-----------|----------|---------|
| Spatio-temporal coherent building loads (arXiv:2301.12967) | 2023 | Smart grid / buildings | Spatial+temporal | ML + recon taxonomy | Yes | Energy aggregates | No | Different domain |
| HAILS — hierarchical industrial demand with sparsity | 2024 | Manufacturing demand | Product hierarchy | Probabilistic hierarchical | Sparse-aware recon | Commercial demand | No | Not infra telemetry |
| Predictive optimization for hierarchical demand matching | ~2020 | Inventory / DC network hierarchies (mentioned) | Demand hierarchy | Bayesian hierarchical + stochastic opt | Optimization-facing | Abstract DC network mention | No | Optimization pipeline, not forecast recon benchmark on OAI |

---

## Network / telecom telemetry forecasting

| Citation | Year | Domain | Hierarchy | Recon | Telecom telemetry? | Differs |
|----------|------|--------|-----------|-------|--------------------|---------|
| Classical network traffic / RTT forecasting literature (broad) | various | Networks | Usually single-level | Rarely MinT | Often yes | Typically no machine↔cluster physical resource summing |
| OpenAirInterface monitoring / CI papers | various | Telecom CI | Ops metrics | Rarely hierarchical recon | Yes (platform) | Do not constitute MinT/WLS reconciliation study |

No work found that jointly evaluates **MinT/WLS/BU/TD** on **OAI CI** with **exact memory**, **verified core-weighted CPU**, **approximate bond0**, and **disk as boundary degradation**, under a nested leakage-safe protocol.

---

## Capacity planning using forecast reconciliation

| Finding | Implication |
|---------|-------------|
| Retail/energy capacity planning often cites MinT | Method is mature outside telecom CI |
| Cloud autoscaling papers prefer end-to-end DL coherency | Different contribution axis |
| TimeTrack angle | Decision-useful **coherence for capacity views** on measured physical aggregates, with honesty about when BU hurts |

---

## Novelty decision (pre-freeze)

| Question | Answer |
|----------|--------|
| Direct contribution conflict (same claim already published)? | **No** — no paper found that matches OAI physical multi-metric hierarchy + classical recon suite + disk selectivity boundary under nested CV |
| Overlapping adjacent work? | **Yes** — HARMONY, FRT, MaMiClif (cloud hierarchical forecasting / coherent workloads) |
| Safe claim? | Scoped framework/evaluation claim above — **not** “first hierarchical cloud forecasting”, **not** SOTA vs HARMONY/FRT without direct experimental comparison |
| Stop before freeze? | **No** — proceed; keep claims scoped |

## Unsupported claims (must not appear)

- Reconciliation always improves accuracy
- Bottom-up always appropriate
- Global models outperform local
- Adaptive routing is superior
- State of the art without scoped literature + experimental comparison
- bond0 is an exact hierarchy
- “First” without stronger exhaustive search + legal review
