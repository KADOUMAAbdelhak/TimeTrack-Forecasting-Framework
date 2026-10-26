# STAGE 19G2 — Final evidence integration

## Outcome and changed sources

The final reviewer-facing diagnostics are integrated without replacing frozen
primary estimates or post-hoc control results. No training, inference, new
statistical analysis, experiment, commit or push was performed.

Manuscript source changes are limited to:

- `manuscript/jss/manuscript.tex`: abstract; Results §§5.1, 5.2 and 5.4;
  Discussion §§7.2 and 7.4; Threats §8.2; Conclusion.
- `manuscript/jss/supplementary/final_evidence_supplement.tex`: new standalone
  three-page diagnostic supplement, containing exactly two new tables.

Existing supplementary decision-criteria/bootstrap fragments, main-text table
and figure files, bibliography, Methods/protocol, author/declaration content,
licence/checkpoint statements and packaging metadata remain unchanged.
The source snapshot and stage-only diff are retained alongside this report.

## Evidence placement and exact traceability

Supplementary Table S1 (page 1) contains all **24** original M1:S2
block/resource rows: frozen MacroMAE gain, median matched-cell M1/S2 MAE
ratio, M1 win percentage and exact ties. Results §5.2 cites it and retains
the short all-24 directional summary. Its unit remains entity × fold ×
forecast lead after averaging the three existing seed MAEs.

Supplementary Table S2 (pages 2–3) contains all **48** existing-seed rows:
24 S2:S1 rows in Panel A and 24 M1:S2 rows in Panel B. Seed0/1/2 gains,
range, population SD and stable/FLIP status are copied, not recalculated.
Results and Threats cite it and retain the **9/24** and **4/24** sign-variable
counts. The table defines FLIP, percentage-point units, population SD and
the non-IID/descriptive boundary without adding a meaningfulness threshold.

All **312** numeric decimal strings in these two tables match the input CSVs
literally. Each LaTeX `\evidencevalue{exact CSV string}{display value}` preserves
the original decimal and displays six decimal places. This is formatting,
not a changed estimand or recomputation of gains, medians, ranges or SDs.
Rows/identities, statuses and ties also match exactly. No existing table was
duplicated. Main-text S1/S2 identifiers match the supplement's compiled labels;
their locations and all ordinary LaTeX references/citations were checked.

## Attribution and bounded interpretation

Results §5.2 now states that Materna T1/T3 disk errors worsen in **28/35**
and **32/35** VM averages. VM266/VM272 account for **82.10%/86.97%** of
positive excess, and the respective top three VMs for **91.72%/92.93%**.
No training or scaling defect was demonstrated.

TimeTrack memory worsens in **all seven machine averages** and **31/35**
machine/fold pairs; the median pair ratio is **1.195276**. The largest pair
accounts for **21.80%**, and the top three for **51.06%**, of positive excess
at that same pair level. The text explicitly distinguishes these attribution
units from Table S1's finer matched cells. It describes broad adverse
direction with uneven magnitude, not uniform catastrophic failure.

These insertions were checked against the existing G1 attribution records
and Stage18C1 interpretation. No new attribution calculation was run.

RQ4 now reads: **“The prespecified RQ4 criterion for temporal heterogeneity
was met.”** The seven classification changes, five raw-sign changes and
12 comparison/resource pairs are retained. The text explicitly notes small
seed-variable S2 effects and that the criterion is descriptive, not an IID
or inferential claim.

The abstract uses **“Ridge indicates”** and **per-entity model consolidation**;
it contains **229 words**, without detailed attribution or the large Ridge
throughput penalty. Discussion/Conclusion distinguish typical-cell magnitude
from tail-sensitive MacroMAE, allowing that per-entity consolidation may be
attractive when target-specific penalties are acceptable while requiring
assessment of adverse tails. Neither universal M1 adoption nor causal
identification of sharing is claimed.

## Table A, builds and visual checks

TimeTrack memory gains remain **−18.476885757816117% (H64)** and
**−18.484754219705916% (H129)**. Both legitimately display **−18.48%**.
The original/common/H129 Table A source is byte-unchanged.

- Main PDF: **18 double-column pages** (previously 17).
- Diagnostic supplement PDF: **3 pages**.
- Both final cached-only Tectonic builds succeed; all 35 retained bibliography
  entries are cited, with zero unresolved references/citations or duplicate labels.
- All 18 main-page layouts and all three supplement pages were visually
  inspected, with full-page checks of the changed abstract, attribution,
  RQ4, Discussion/Conclusion and both complete supplementary tables.
  No clipping, overlapping content, illegible new tables or new overfull
  body lines remains. The readable fonts and original figures/tables were retained.
- Existing CAS front-matter box/empty-anchor and underfull-line warnings,
  PDF-version notice and two empty-pages bibliography warnings remain
  non-fatal. No integration blocker remains. Earlier submission-readiness
  metadata/package items and the pre-existing Table 4 prose-citation issue
  were not addressed or certified by this scoped stage.

Final PDFs are in `build/manuscript.pdf` and
`build/supplement/final_evidence_supplement.pdf` under this evidence directory;
the stale historical root PDF was not overwritten.

## Preservation and status

`preservation_before.json` verifies all **395,786** predecessor protected
files. `preservation_after.json` verifies **395,785** unchanged existing
protected files, permitting only the main TeX edit and one new supplement
source; protected membership is **395,787**. All 25 Stage18C1 output hashes
and 19 Stage19G1 output hashes are reverified. Refs/branch remain unchanged,
the index is unstaged, and `git diff --check` passes.

`verification.json`, `visual_signoff.json`, input/output SHA-256 inventories
and the stage-only diff bind the final sources, PDFs and checks.

Scientific modifications=0; frozen/post-hoc artifact modifications=0;
training=0; inference=0; new statistics=0; commit=no; push=no.

**STAGE_19G2_PASS**
