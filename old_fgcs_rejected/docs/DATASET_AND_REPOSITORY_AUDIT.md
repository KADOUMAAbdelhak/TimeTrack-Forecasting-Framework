# TimeTrack Dataset and Repository Audit

**Audit date:** 2026-08-03  
**Project root:** `/Users/fgtek002/TimeTrack`  
**Auditor role:** Lead ML research engineer (Phase 1 — inspection only; no forecasting models implemented)

This document reports what is **actually present** in the workspace and what was **directly measured** from the downloaded CSV files. Claims from the dataset paper or prior TimeTrack studies are treated as hypotheses until verified here.

Supporting machine-readable caches (not publication artifacts) are stored under `docs/_audit_cache/`.

---

## Executive findings

1. **The repository is a greenfield data drop.** The project root contains **only six CSV files**. There is no existing source code, notebooks, configs, tests, models, results, README, requirements file, or Git history.
2. **Dataset span:** 2024-06-24 13:37:06 through 2024-07-19 16:27:05 (naive timestamps; **~25.12 calendar days**), with a **~4.87-day outage** from 2024-06-28 13:10:49 to 2024-07-03 10:05:20.
3. **Sampling interval is not 45 seconds.** The empirical median interval is **42.285 s** (≈99.93% of steps round to 42 s). The paper’s “45-second” claim does **not** match this download. Horizon design must use the **observed** interval (~42.3 s), not 45 s.
4. **Seven machines** appear as `machine01`–`machine07` in aggregate files and as Mythological hostnames (`acamas`, `bellerophon`, `dedale`, `demophon`, `pegase`, `perse`, `phaedra`) in per-core / NIC files.
5. **Strong deterministic redundancies** exist (CU↔CF, cluster↔sum of machines, bond0↔sum of member NICs, AM≈complement of UM). These must not be treated as independent multi-output targets.
6. **Packet errors are identically zero** across all observed interfaces. Packet drops are extremely sparse (~0.44% of timesteps have any drop). Classical regression on these series is not scientifically meaningful without a two-stage / rare-event framing.
7. **No forecasting code exists to reuse.** The entire research framework must be designed and implemented from scratch, with raw CSVs kept immutable.

---

## 3.1 Repository inventory

### Directory tree (as found)

```
TimeTrack/
├── compute_dataset.csv                 (25.7 MB)
├── detailed_cpu_cores_dataset.csv      (316.0 MB)
├── disk_dataset.csv                    (8.0 MB)
├── network_dataset.csv                 (2.8 MB)
├── packet-loss-dataset.csv             (11.8 MB)
└── throughputs_dataset.csv             (39.1 MB)
```

After this audit began, the following were created for analysis only (not pre-existing project assets):

- `.venv/` — local Python 3.13 virtualenv for audit scripts
- `docs/` — this audit and cached JSON/CSV analysis outputs
- `scripts/` — placeholder directory (empty at audit time except future use)
- `data/raw/` — placeholder (raw CSVs remain at project root; not relocated)

### Existing implementation status

| Category | Status |
|----------|--------|
| Source modules | **Absent** |
| Notebooks | **Absent** |
| Shell scripts | **Absent** |
| Configs | **Absent** |
| Requirements / environment files | **Absent** (venv created only for audit) |
| Tests | **Absent** |
| Models / checkpoints | **Absent** |
| Preprocessing code | **Absent** |
| Experimental outputs | **Absent** |
| Documentation | **Absent** prior to this file |
| Git repository | **Not initialized** (`git status` unavailable / no `.git`) |
| Hidden config (`.gitignore`, `.editorconfig`, etc.) | **Absent** |

### Existing reusable components

**None.** There is no prior forecasting, preprocessing, evaluation, or orchestration code in this workspace to preserve or redesign.

### Existing experiments and validity

**None present.** Prior TimeTrack publications (LSTM/RNN/GRU/CNN on CPU; NAS; Resource Exposer) are **external** to this repository and cannot be reproduced from this tree. They should be treated as literature baselines, not as runnable local experiments.

### Broken / incomplete / duplicated / obsolete scripts

**N/A** — no scripts exist.

### Dependencies

No project dependency pin file. Audit environment used:

- Python 3.13.2 (Homebrew)
- `pandas`, `numpy`, `scipy`, `matplotlib`, `seaborn`, `statsmodels`, `pyyaml` (installed into `.venv` for inspection)

### Testing status

No tests. No CI.

### Result files

None. Nothing to reproduce.

### Documentation vs code mismatch

No documentation existed. The only mismatch of scientific interest is between **external paper descriptions** (45 s sampling) and **measured data** (~42.3 s median). That mismatch is documented in §3.2 and §3.4.

### What must be built

Everything in the target research layout (`preprocessing/`, `features/`, `models/`, `evaluation/`, `experiments/`, `configs/`, `tests/`, `results/`, etc.) must be created. Raw CSVs should be **copied or hard-linked** into `data/raw/` without deleting or renaming the originals at the root until a deliberate, documented curation step is approved.

---

## 3.2 Dataset-file inventory

Common properties across all six files unless noted:

- **Format:** CSV, comma-separated, header row
- **Timestamp column:** `timestamp`
- **Timestamp format:** `YYYY-MM-DD HH:MM:SS.ffffff` (microseconds)
- **Time zone:** **Not identifiable** from the files (naive datetimes; no `Z`/`+00:00` offset). Treated as cluster-local wall clock until proven otherwise.
- **First timestamp:** `2024-06-24 13:37:06.164306`
- **Last timestamp:** `2024-07-19 16:27:05.246403`
- **Observed calendar duration:** 25.118 days
- **Expected interval (paper):** 45 s — **not confirmed**
- **Actual median interval:** **42.285166 s**
- **Duplicate rows:** 0 in every file
- **Duplicate timestamps:** 0 in every file
- **Timestamp ordering:** strictly increasing in every file
- **Clock resets (negative Δt):** 0

### Summary table

| Relative path | Size | Rows | Cols | Missing cells % | MD5 |
|---------------|------|------|------|-----------------|-----|
| `compute_dataset.csv` | 25.695 MB | 41,362 | 56 | 1.9238% | `21bcbb45d334e485eaabaca0ef2ee34b` |
| `detailed_cpu_cores_dataset.csv` | 316.004 MB | 41,362 | 473 | 0.2146% | `e380157483164d52ee1179f9b6b3c8ca` |
| `disk_dataset.csv` | 8.035 MB | 41,362 | 15 | 0.0% | `9167afb39d114b8dd7854b536137e30e` |
| `network_dataset.csv` | 2.796 MB | 41,356 | 6 | 0.0044% | `7b6b82738716462185f2af1d9bb22b82` |
| `packet-loss-dataset.csv` | 11.816 MB | 41,362 | 91 | 51.6307% | `f424ffe188eee08fa6a2694fc4227bd9` |
| `throughputs_dataset.csv` | 39.095 MB | 41,362 | 91 | 0.2165% | `c3784b476aadea7bdc3301ca0dba3e5f` |

**Row-count note:** Five files share 41,362 timestamps. `network_dataset.csv` has **6 fewer rows** (41,356). All of its timestamps are a subset of the compute timeline.

### Interval distribution (compute timeline; identical pattern in aligned files)

| Statistic | Value (seconds) |
|-----------|-----------------|
| min | 39.24 |
| p1 | 42.21 |
| median | **42.285** |
| p99 | 42.39 |
| max | **420,871.53** (~4.87 days) |
| mean | 52.47 (inflated by the long gap) |

Rounded-to-integer interval counts (dominant):

- 42 s: 41,258 steps
- 43 s: 86
- Other short anomalies: 39 s (7), 44 s (6), 65 s (1), 76 s (1)
- Long gaps: **330.08 s** (1), **420,871.53 s** (1)

**Irregular gaps (|Δt − 45| is the wrong reference):** relative to the **observed** ~42.3 s median, there are 2 gaps > 3× median and a handful of mild outliers. Using the paper’s 45 s as “expected” overstates irregularity.

### 3.2.1 `compute_dataset.csv`

**Entity level:** cluster + 7 machines (wide format).

**Columns (56):**

- `timestamp`
- Memory: `totalProvMemory`, `cluster AM`, `cluster UM`, `machine0{1–7} AM`, `machine0{1–7} UM`
- CPU capacity: `totalNumberOfCores`, `totalCpuCoresmachine0{1–7}`
- CPU utilization / free: `machine0{1–7} CU`, `machine0{1–7} CF`
- Disk (cluster): `cluster Available disk space`, `cluster UD`
- Disk throughput: `machine0{1–7} DRT`, `machine0{1–7} DWT`

**Dtypes:** `timestamp` object/string → parseable datetime; capacities mostly `int64`; utilizations/throughputs `float64`.

**Constant / near-constant:**

- `totalProvMemory` — **constant** `469804298240` bytes
- `totalCpuCoresmachine0{1–7}` — each **constant** (36, 48, 36, 36, 24, 36, 20)
- `totalNumberOfCores` — near-constant: value `236` except **one** row equal to `56`

**High missing:** `machine05 CF` — **100% missing**

**High zero (≥90% zeros):** `machine02/04/05/06/07 DRT`

**Candidate targets:** machine/cluster CU, UM, DRT, DWT, cluster UD (with caveats in §3.3).  
**Candidate exogenous / identifiers:** machine index, core counts (static), time features.  
**Suspected derived:** cluster AM/UM as sums; CF ≈ 100 − CU.  
**Suspected units:** memory/disk bytes; CU/CF percent; DRT/DWT bytes/s (rate-like magnitudes, not cumulative counters).

### 3.2.2 `detailed_cpu_cores_dataset.csv`

**Entity level:** host × CPU core.

**Structure:** 236 `free_cpu_{host}:cpu-{n}` + 236 `used_cpu_{host}:cpu-{n}` + `timestamp` = 473 columns.

**Hosts and core counts (from column inventory):**

| Host | Cores |
|------|------:|
| acamas | 36 |
| bellerophon | 48 |
| dedale | 36 |
| demophon | 36 |
| perse | 36 |
| phaedra | 24 |
| pegase | 20 |
| **Total** | **236** |

**Missing:** ~0.21% overall; per-core missing typically <0.3%. No column is ≥50% missing.

**Semantics check (sample cores):** `used + free ≈ 100` (means ≈100, small noise) → percentages that are near-complements.

**Machine ↔ host mapping ( empirically from corr(mean used cores, machine CU) ):**

| Host | Best machine | Pearson | Notes |
|------|--------------|--------:|-------|
| acamas | machine01 | 0.998 | cores match (36) |
| bellerophon | machine02 | 0.982 | cores match (48) |
| dedale | machine03 | 0.963 | cores match (36) |
| demophon | machine04 | 0.988 | cores match (36) |
| perse | machine06 | 0.996 | cores match (36) |
| pegase | machine05 | 0.790 | **core-count label mismatch** (host 20 vs machine05 labeled 24) |
| phaedra | machine07 | 0.976 | **core-count label mismatch** (host 24 vs machine07 labeled 20) |

**Critical data-quality finding:** For machines 05/07, **utilization series identity follows hostnames (pegase↔m05, phaedra↔m07)**, while `totalCpuCoresmachine05/07` appear **swapped** relative to per-core column counts. Prefer correlation-based identity for forecasting entity keys; treat static core-count labels for m05/m07 as unreliable.

### 3.2.3 `disk_dataset.csv`

**Columns (15):** `timestamp`, `machine01 FD`, **`machie02 FD`** (typo), `machine03–07 FD`, `machine01–07 UD`.

**Interpretation supported by data:**

- `FD` = free disk (bytes)
- `UD` = used disk (bytes)
- `FD + UD` ≈ per-machine capacity (low CV on several machines)
- Cluster disk fields in `compute_dataset.csv` equal the **exact sums** of machine FD / UD (corr = 1.0, relative MAE = 0)

**Missing / zeros / constants:** none material.

**Resets / cleanups:** frequent large **negative** jumps in UD (cleanup or log rotation), e.g. machine01 has 1,910 drops >100 MB; min diff ≈ −5.1×10¹⁰ bytes. Level forecasting without reset awareness is misleading.

### 3.2.4 `network_dataset.csv`

**Columns (6):** cluster-level (or collector-level) RTT to Google DNS:

- `maxrttWithGoogleDns`
- `minRttwithGoogleDns` (inconsistent camelCase)
- `averageRttWithGoogleDns`
- `mdevrttWithGoogleDns`
- `jitterWithGoogleDns`

**Rows:** 41,356 (6 timestamps present in other files are missing here).  
**Missing values:** only `jitterWithGoogleDns` has ~0.022% NA.  
**Constraint:** `min ≤ average ≤ max` holds on **100%** of rows.  
**Units:** milliseconds (magnitudes ~2–4 ms typical for average RTT).

### 3.2.5 `packet-loss-dataset.csv`

**Columns (91):** 45 `err_packet_*` + 45 `drop_packet_*` for host×NIC, plus timestamp.

**Severe sparsity / missingness:**

- ~51.6% of all cells missing (many NICs entirely NA — not present on that host)
- **All error columns are zero whenever observed** (`err_nonzero_event_rate_overall = 0`)
- Drop event rate overall ≈ **0.011%** of cells; ~**0.44%** of timesteps have any drop > 0
- Highest drop activity: `drop_packet_dedale:-network-device-bond0` (~0.39% nonzero)

**42 columns are entirely NA.** These are structural (interface absent), not intermittent sensor failures.

### 3.2.6 `throughputs_dataset.csv`

**Columns (91):** 45 transmitted + 45 received throughput series for the same host×NIC schema as packet-loss.

**Units:** consistent with Mbit/s-scale rates (bond0 means typically ~4–42 depending on host); **not** cumulative counters.

**Redundancy:** for every host, `bond0` transmitted throughput correlates with the sum of that host’s member NIC TX columns at **r ≈ 1.000**. Prefer **bond0** (or explicit aggregates) over training redundant member-NIC models.

**High-zero columns:** 41 columns ≥90% zeros (idle / unused NICs).

### Timestamp alignment across files

| File A vs File B | Intersect | Only A | Only B |
|------------------|----------:|-------:|-------:|
| All non-network pairs among compute/cores/disk/packet/throughput | 41,362 | 0 | 0 |
| network vs compute | 41,356 | 0 | 6 |

**Alignment conclusion:** Five files share an identical timestamp index and can be inner-joined without interpolation. Network must be left-joined; the 6 missing RTT points should be marked missing (no future-looking fill across the final test boundary).

---

## 3.3 Metric semantics

### Memory (AM / UM / totalProvMemory)

| Claim | Evidence |
|-------|----------|
| `cluster AM` = sum of machine AM | corr = 1.0, rel MAE = 0 |
| `cluster UM` = sum of machine UM | corr = 1.0, rel MAE = 0 |
| AM + UM ≈ total provisioned | mean relative error ≈ 1.23%; per-machine AM+UM nearly constant (CV 0.002%–1.2%) |
| `totalProvMemory` | constant exogenous capacity, not a forecast target |

**Implication:** Forecasting both AM and UM is redundant. Prefer **UM** (used memory). AM is a near-complement given stable capacity.

### CPU utilization (CU / CF) and per-core used/free

| Claim | Evidence |
|-------|----------|
| CU + CF ≈ 100% | means ≈ 100 for machines with CF present; residual noise / occasional outliers |
| machine05 CF | entirely missing — reconstructible as ≈100 − CU if needed, but do **not** score it as a separate target |
| per-core used + free ≈ 100% | confirmed on samples |
| Machine CU ≈ mean of host used cores | confirmed via high correlations (mapping table above) |

**Implication:** Forecast **CU** (or used cores), not CF/free as separate scientific targets.

### Disk capacity (FD / UD) and compute cluster disk

| Claim | Evidence |
|-------|----------|
| Cluster available disk = sum FD | exact |
| Cluster UD = sum machine UD | exact |
| FD and UD complements | approximately, with capacity stable per machine |
| Cumulative counter? | **No** — absolute used/free capacity levels |
| Resets | **Yes** — large negative UD jumps (cleanup) |

**Implication:** Prefer forecasting **ΔUD** (or rate of change) and/or reset-aware level reconstruction. Direct level forecasting will look artificially strong due to near-unit-root persistence (lag-1 ACF ≈ 0.999) without being operationally useful.

### Disk throughput (DRT / DWT)

- Behave as **non-negative rates**, not counters.
- Many machines have DRT highly zero-inflated (idle reads).
- DWT on machine01 is denser and weekday-sensitive (weekend/weekday mean ratio ≈ 0.24).
- Contemporaneous DRT↔DWT correlation on machine01 is near zero / slightly negative — **not** a strong joint pair on that machine.

### Network RTT / jitter

- Latency statistics to Google DNS (external path), **not** inter-machine fabric latency.
- `max` / `average` highly correlated (r ≈ 0.88).
- `average` / `mdev` r ≈ 0.70; `average` / `jitter` r ≈ 0.40; `jitter` / `mdev` r ≈ 0.38.
- Jitter is **not** a deterministic transform of mdev; both can be studied, but avoid claiming independent multivariate wins without ablation.

### Network throughput

- Interface-level **rates**.
- `bond0` is a deterministic aggregate of member interfaces (r ≈ 1) — do not multi-output bond0 + members as if independent.
- RX/TX correlation varies by host (0.10 on demophon to 0.93 on perse).

### Packet errors / drops

- Values appear as **percentages or rates already**, but empirically errors are all zero and drops are rare spikes.
- **Zero-inflated / event-like.** Direct MSE regression will be dominated by zeros.

### Suspected unit inconsistencies

- Memory/disk: bytes (large integers).
- CPU: percent.
- RTT/jitter: milliseconds.
- Throughput: likely Mbit/s (or similar rate unit) — **not explicitly labeled in the CSV**; treat unit as “rate units as recorded” and keep scaling per-series.
- Column naming inconsistent (`machie02`, `minRttwithGoogleDns` vs `maxrttWithGoogleDns`).

### Deterministic / redundant targets to exclude from multi-output scoring

1. `* CF` given `* CU`
2. `* AM` given `* UM` (+ static capacity)
3. `cluster *` given all `machine0k *` of the same metric (exact sums)
4. Member NIC throughputs given `bond0` (near-exact sums)
5. `free_cpu_*` given `used_cpu_*`
6. All `err_packet_*` (no positive observations)

---

## 3.4 Temporal-quality analysis

### Sampling regularity

- Dominant period **≈ 42.3 s**, highly regular outside outages.
- **Not** 45 s. All horizon labeling in this project should use:

  - 1 step ≈ 42.3 s  
  - 2 steps ≈ 84.6 s  
  - 4 steps ≈ 2.82 min  
  - 8 steps ≈ 5.64 min  
  - 16 steps ≈ 11.3 min  
  - 32 steps ≈ 22.5 min  

  (or resample to exact wall-clock grids after documenting the rule).

### Missing intervals and long gaps

1. **Major outage:** 2024-06-28 13:10:49 → 2024-07-03 10:05:20 (**4.871 days**, 420,871 s). Splits windows **must not cross** this gap; consider segmenting pre/post outage or inserting an explicit break in backtesting.
2. **Short gap:** 330 s on 2024-06-28 06:32:38 → 06:38:08.
3. Network file missing 6 scattered timestamps (listed in audit cache).

### Duplicates, ordering, clock resets, DST

- No duplicate timestamps; sorted ascending; no negative intervals.
- No explicit DST marker. The record spans late June–mid July 2024 (DST stable for EU/US summer). No evidence of a one-hour jump in Δt.

### Calendar coverage

| Day | Approx. rows |
|-----|-------------:|
| Thursday | 8,172 |
| Wednesday | 7,314 |
| Friday | 6,604 |
| Tuesday | 6,129 |
| Monday | 4,971 |
| Saturday | 4,086 |
| Sunday | 4,086 |

Weekend fraction ≈ **19.8%** (reduced by the weekday-heavy outage loss). Enough for weekday→weekend generalization tests, but weekend sample is smaller.

### Periodicity, trend, stationarity (selected series)

| Series | Lag-1 corr | Daily ACF (~1920 steps @45s; ~2014 @42.3s approx used 1920) | ADF stationary @5% | Notes |
|--------|----------:|-------------------------------------------------------------:|--------------------:|-------|
| machine01 CU | 0.59 | ~0.04 | Yes | Spikes ~1.7%; weekend mean ≈ 50% of weekday |
| machine06 CU | 0.88 | ~0.00 | Yes | Low mean util (~0.67%); more persistent |
| cluster mean CU | 0.70 | ~0.05 | Yes | Primary cluster CPU target |
| cluster UM | 0.70 | ~0.17 | Yes | Mild daily structure |
| machine01 UD | 0.999 | ~0.70 | **No** | Near-integrated level |
| machine01 UD diff | ~0.00 | ~0.01 | Yes | Noisy increments + resets |
| average RTT | 0.37 | ~0.00 | Yes | Weak daily seasonality |
| jitter | 0.14 | ~0.03 | Yes | Burstier / heavier tails |
| drop_any_event | 0.84 | ~0.00 | Yes | Rare events; high lag-1 among event runs |

**Seasonality:** Daily strength is **weak for CPU/RTT**, stronger for **disk usage levels** (but those are nonstationary). Weekly structure should be tested via weekday/weekend splits rather than assumed.

**Spectral peaks:** computed for candidates (see `docs/_audit_cache/temporal_profiles.json`); no universal strong circadian peak across all metrics.

**Regime / variance changes:** e.g. machine06 CU variance ratio second/first half ≈ 3.6 — nonstationary volatility. Disk cleanups create structural breaks in UD levels.

**Bursts/spikes:** CPU and disk write series show clear spike mass (>5σ events at ~1% level on some machines). These are operationally important; do not winsorize away by default.

**Autocorrelation takeaway:** Persistence varies sharply by machine and metric (CPU lag-1 from ≈0 on machine02/07 to 0.88 on machine06). A single global AR order is unlikely to be optimal.

### Cross-file temporal alignment safety

Joining on `timestamp` is safe and does **not** introduce future information **if** feature windows use only ≤ t₀ and targets use > t₀ within the same index. Because five files share the index exactly, multivariate windows can be built without asof-join ambiguity. Network’s 6 holes need explicit NA handling inside windows.

---

## 3.5 Correlation and dependency analysis

Artifacts: `docs/_audit_cache/pearson_corr.csv`, `spearman_corr.csv`, `correlations.json`.

### Contemporaneous Pearson highlights

- **CPU–memory (same machine):** m1 0.53, m3 0.64, m4 0.74; weak on m2/m5/m6/m7 (0.05–0.18).
- **Cross-machine CPU:** generally weak; notable pair **m1–m4 ≈ 0.69**; m2–m7 ≈ 0.39; m2–m5 ≈ 0.32. Most other pairs < 0.12.
- **RTT group:** max–avg 0.88; avg–mdev 0.70; avg–jitter 0.41.
- **RX–TX (bond0):** host-dependent 0.10–0.93.
- **Disk R/W (m1):** ≈ −0.04 (weak).

### Lagged cross-correlation (max lag 32 steps)

| Pair | Best lag | Best corr | Corr@0 |
|------|--------:|----------:|-------:|
| CU_m1–UM_m1 | 0 | 0.53 | 0.53 |
| cluster_CU–cluster_UM | 0 | 0.59 | 0.59 |
| avgRTT–jitter | 0 | 0.40 | 0.40 |
| tx_acamas–rx_acamas | 0 | 0.50 | 0.50 |
| CU_m1–tx_acamas | +5 | 0.22 | 0.03 |
| CU_m1–CU_m2 | −2 | 0.04 | 0.00 |
| DRT_m1–DWT_m1 | 0 | −0.04 | −0.04 |

**Takeaway:** Most useful multivariate coupling is **contemporaneous within machine** (CPU–memory) or **NIC RX/TX**. Cross-machine CPU coupling is selective (m1–m4), not cluster-wide. CU→TX shows a mild delayed association (~5 steps) worth testing as exogenous lags, not assuming strong instantaneous causality.

### Correlation stability

Mean absolute difference of pairwise correlations:

| Group | Weekday vs weekend MAD | First vs second half MAD |
|-------|------------------------:|-------------------------:|
| CU across machines | 0.030 | 0.046 |
| UM across machines | 0.195 | 0.136 |
| TX across hosts | 0.073 | 0.030 |
| RTT group | 0.048 | 0.043 |

Memory cross-machine correlations are **less stable** across calendar regimes than CPU — caution for global multi-machine memory models.

### Mutual information (histogram estimator)

Consistent ordering with Pearson for the tested pairs (CPU–memory and RX–TX show higher MI than cross-machine CPU). Exact values in `correlations.json` (binning-sensitive; use comparatively, not absolutely).

### Proposed joint-prediction groups (hypotheses for later experiments)

1. **Per-machine compute pair:** `{CU, UM}` for machines with CPU–mem corr ≳ 0.5 (especially m1, m3, m4).
2. **Cluster pressure group:** `{cluster_mean_CU, cluster_UM}` (+ optional cluster disk change).
3. **Latency group:** `{averageRTT, maxRTT, jitter}` (external DNS path) — shared exogenous time features; optional multi-output with care about max/avg redundancy.
4. **Per-host network rates:** `{tx_bond0, rx_bond0}` per host (exclude member NICs).
5. **Disk I/O:** `{DWT}` primary; add DRT only where non-sparse.
6. **Do not jointly score:** CU+CF, UM+AM, bond0+members, cluster+all-machines sums, free+used cores.

---

## 3.6 Forecastability assessment

Classification below is **pre-experimental triage**, not a claim of achievable accuracy.

### High-priority forecasting targets

| Target | Entity | Why |
|--------|--------|-----|
| `machine0k CU` (k=1..7) | machine | Core operational CPU load; prior literature baseline metric; varies in persistence |
| `cluster_mean_CU` (derived) | cluster | Cluster pressure summary without exact-sum leakage issues of “predict sum = predict parts” |
| `machine0k UM`, `cluster UM` | machine / cluster | Capacity planning; non-redundant vs AM |
| `*_bond0` TX/RX (7 hosts × 2) | NIC aggregate | Primary network rate signal; members redundant |
| `averageRttWithGoogleDns`, `maxrttWithGoogleDns`, `jitterWithGoogleDns` | cluster/collector | Latency / variability; operationally interpretable |
| `machine0k DWT` where not extremely sparse (esp. m1) | machine | Write pressure |
| `machine0k UD_diff` (and reset-aware variants) | machine | Disk growth / cleanup dynamics |

### Secondary forecasting targets

| Target | Why secondary |
|--------|----------------|
| Disk **level** UD / FD | Near-unit-root; prefer diffs / hybrid reconstruction |
| `minRtt`, `mdevrtt` | Partially redundant with avg/max/jitter |
| Highly zero-inflated DRT (m2, m5, …) | Sparse reads; weak signal |
| Selected busy member NICs | Only for ablation vs bond0, not primary leaderboard |

### Experimental targets

| Target | Why experimental |
|--------|------------------|
| Packet **drop** event indicator + magnitude | ~99.56% zero timesteps; two-stage models only |
| Per-core CPU series (236 used-cores) | Scientifically interesting for locality vs aggregation, but expensive; require staged justification vs machine CU |
| Global models on low-corr machines (e.g., m2 CU lag-1≈0) | Hard series; stress-test of model capacity |

### Unsuitable / redundant targets

| Target | Why exclude |
|--------|-------------|
| All `err_packet_*` | Identically zero in this download |
| `* CF`, `free_cpu_*` | Deterministic complements of used/CU |
| `* AM` (given UM + capacity) | Near complements |
| `totalProvMemory`, static core counts | Constants / metadata |
| Member NIC throughputs **and** bond0 as separate scored targets | Near-duplicate signals |
| `cluster UM` **and** all machine UM as simultaneous independent wins without hierarchical evaluation | Exact sum relationship |

### Special modeling notes by family

- **CPU:** regression appropriate; persistence heterogeneous — include strong baselines (last value, MA, seasonal-naive if validated).
- **Memory:** regression appropriate; mild daily ACF.
- **Disk level:** difference / reset segmentation / two-path (level via integrated increments).
- **Disk throughput & network rates:** non-negative; consider log1p; keep spikes.
- **RTT/jitter:** positive continuous; possible heavy tails — robust losses / quantile models for RQ12.
- **Packet drops:** two-stage (event classifier + conditional magnitude) vs trivial zero predictor.
- **Per-core CPU:** first compare (a) machine CU, (b) PCA/factor of cores, (c) few representative cores, (d) global-across-cores model — **before** training hundreds of local models.

### Observation count adequacy

After removing the 4.87-day gap, roughly **8.1k pre-gap + 33.2k post-gap** points remain. Post-gap alone (~16 days) supports chronological train/val/test splits and limited rolling-origin folds. Pre-gap segment is short for deep models but useful for domain-shift / cold-start checks.

---

## Data-quality issues checklist (actionable)

1. Sampling interval **42.3 s ≠ 45 s** — update all horizon docs.
2. **Multi-day outage** — hard break in time-series CV.
3. `machie02 FD` typo — normalize in loaders; preserve raw header.
4. `machine05 CF` all-NA.
5. `totalNumberOfCores` single-row anomaly (56).
6. machine05/07 **core-count vs hostname mismatch**.
7. Network file missing 6 timestamps.
8. Packet schema sparse / many all-NA NIC columns.
9. No timezone metadata.
10. Throughput/packet units not self-documented in-file.

---

## Implications for Phase 2 research design

1. Build the full forecasting framework from scratch; nothing to reuse locally.
2. Freeze a **leakage-safe chronological protocol** that respects the June 28–July 3 gap.
3. Use **observed Δt ≈ 42.3 s** for horizons; optionally also report wall-clock horizons (1, 3, 5, 10, 20 minutes) via resampling (RQ8).
4. Prioritize multi-metric study beyond CPU while excluding deterministic duplicates.
5. Treat packet errors as unavailable; packet drops as rare-event experiments only.
6. Map entities as `machine0k` ↔ hostname using the correlation table; document the m05/m07 labeling conflict.
7. Keep raw CSVs immutable at project root (and mirrored under `data/raw/` without overwrite of originals).

---

## Audit artifacts

| Path | Contents |
|------|----------|
| `docs/_audit_cache/file_inventory.json` | Per-file schema, hashes, interval stats, column summaries |
| `docs/_audit_cache/timestamp_alignment.json` | Pairwise timestamp set comparisons |
| `docs/_audit_cache/semantics.json` | Complement/sum/bond checks |
| `docs/_audit_cache/temporal_profiles.json` | ACF/PACF/ADF/seasonality/spike profiles |
| `docs/_audit_cache/correlations.json` | Pearson/Spearman highlights, lagged xcorr, stability, MI |
| `docs/_audit_cache/pearson_corr.csv` / `spearman_corr.csv` | Full matrices for the analysis panel |
| `docs/_audit_cache/machine_host_mapping.json` | Host↔machine correlation matrix |
| `docs/_audit_cache/forecastability.json` | Triage tiers |

---

## Next step

Proceed to Phase 2 documents:

- `docs/RESEARCH_PLAN.md`
- `docs/EXPERIMENT_MATRIX.md`

then implementation of the leakage-safe pipeline and staged experiments — **without** treating any model family as pre-selected winners.
