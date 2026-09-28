# New TimeTrack Data Feasibility

## Classification

**UNKNOWN_REQUIRES_CONTACT**

## Repository evidence

The repository describes the source as OpenAirInterface CI/CD telemetry and instructs users to obtain six CSV files from an “authorized dataset source.” It contains ingestion, auditing, panel construction, and forecasting code, but no first-party collector, scraper, Prometheus/Telegraf configuration, deployment credentials, collection endpoint, or operational runbook.

The only local raw TimeTrack files are the six frozen CSVs under `data/raw/`. Their shared coverage is 2024-06-24 through 2024-07-19, with median sampling near 42.285 seconds and a documented approximately 4.87-day outage. No later compatible telemetry file was found in the repository outside the canonical source set. Archived root-level files are byte-identical duplicates, not a temporal extension.

The repository cannot establish whether the same seven hosts, CI/CD environment, metric exporters, or authorized source remain available. It also cannot establish whether collection can be resumed. That requires contact with the dataset owner/operator, which Phase 4A explicitly did not perform.

If a later drop is obtained, compatibility requires the same timestamp semantics and the four frozen per-host targets: CPU utilization, TX+RX total throughput, used-memory level, and disk-write activity. Its provenance, host continuity, collection changes, units, and missing/outage structure must be audited before it is called an exact temporal confirmation. Until then, later TimeTrack data are potentially strongest but not available evidence.
