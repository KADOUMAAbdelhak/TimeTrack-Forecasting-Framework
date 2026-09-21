# Limitations

1. Smoke-tier evidence only for many planned RQs; medium/publication matrices incomplete.
2. Single seed in smoke — no statistical significance claims.
3. Sampling is ~42.3 s; older 45 s literature not directly comparable without resampling.
4. Outage removes ~5 days; primary track ignores pre-gap data.
5. External Google DNS RTT is not intra-cluster fabric latency.
6. Packet errors absent; drops too sparse for standard regression leaderboards.
7. machine05/07 core-count vs hostname label conflict unresolved beyond correlation mapping.
8. No GPU timing in smoke; torch models CPU-only here.
9. Nested/module save paths for some torch nets require state_dict discipline.
10. Feature-engineering ablations and multivariate/global studies not yet run at scale.
