# Source and Acquisition Record

Acquisition date: 2026-09-28. Raw archives are stored under ignored `data/external/raw/`; they were read in place and not modified or extracted. Exact sizes and SHA-256 values are in `RAW_ARCHIVE_MANIFEST.csv`.

## Downloaded official archives

- Bitbrains GWA-T-12 fastStorage: official @Large Research / Grid Workloads Archive page `https://atlarge-research.com/gwa-t-12/`; archive `https://atlarge-research.com/gwa-traces/gwa_t_12_fastStorage.zip`.
- Bitbrains GWA-T-12 Rnd: same official source; archive `https://atlarge-research.com/gwa-traces/gwa_t_12_rnd.zip`.
- Materna GWA-T-13: official page `https://atlarge-research.com/gwa-t-13/`; archive `https://atlarge-research.com/gwa-traces/gwa_t_13_materna.zip`.

The archive pages request acknowledgement of Bitbrains or Materna and citation of the papers listed by the Grid Workloads Archive. Redistribution/publication must retain those acknowledgements and should receive a final license review; the pages provide public downloads but do not present a conventional SPDX license identifier.

## Metadata-only candidates

- Alibaba 2018: official schema and trace documentation at `https://github.com/alibaba/clusterdata/tree/master/cluster-trace-v2018`. The complete archive is about 49 GB compressed; no download was needed because the official schema establishes that disk I/O utilization, not disk-write throughput, is supplied.
- Google 2019: official documentation at `https://github.com/google/cluster-data/blob/master/ClusterData2019.md`. The release is about 2.4 TiB compressed and does not provide the required four comparable resource targets. It is licensed CC BY 4.0.
- Azure VM traces: official repository at `https://github.com/Azure/AzurePublicDataset` with V1/V2 documentation. The CPU-series releases are about 78.5/156 GB compressed and lack dynamic throughput, active-memory, and disk-write series. They are licensed CC BY 4.0.

Third-party preprocessed copies were not used.
