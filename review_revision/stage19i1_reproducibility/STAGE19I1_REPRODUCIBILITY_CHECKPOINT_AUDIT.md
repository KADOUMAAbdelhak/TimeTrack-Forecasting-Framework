# STAGE 19I1 — Reproducibility checkpoint and licence audit

Date: 26 October 2026 (Europe/Helsinki). Repository: `/Users/fgtek002/TimeTrack`; branch: `paper/jss-review-revision`; HEAD: `f6936cd111d911e40ec2725a18fdfc53768d9ccf`; scientific parent: `fee20c316040c57b69ba12a193530c955b539771`.

**STAGE_19I1_PASS — audit and exact checkpoint plan completed, with USER_ACTION release decisions. This is not a finding that a fresh public checkout is already self-contained or legally cleared for blanket redistribution.** No commit, tag, push, licence grant, manuscript/declaration edit or submission-package creation was performed.

## 1. Reproducibility coverage

All named scientific inputs and final diagnostic outputs are present locally. No missing named scientific file was found. Existing hash inventories, source/configuration/successor seals, terminal handoffs and six-block audit records reconcile; no experiment, inference or scientific aggregation was rerun.

| Evidence | Authoritative current files | Audit result |
|---|---|---|
| Frozen TimeTrack S1/S2/M1 | `multiresource/04_lstm_factorial/outputs/scientific/metrics.parquet`, `persistence_metrics.parquet`, `comparisons/{s2_vs_s1,m1_vs_s2,m1_vs_s1}.csv`; selected contexts/epochs, support, registries and prospective criteria in the same experiment | 5,706 scientific-inventory entries verified |
| Frozen fastStorage/Rnd | `independent_validation/05_bitbrains_factorial/outputs/scientific_v2/{fastStorage,Rnd}/metrics.parquet`; `analysis/primary_macro_mae.csv`, `analysis/matched_vm_fold_cells.csv`, `comparisons/secondary_aggregation_diagnostics.csv` | 56,723 full execution entries plus compact freeze inventories verified; `scientific_v2`, not superseded `scientific`, is authoritative |
| Frozen Materna T1/T2/T3 | `independent_validation/06_materna_replication/outputs/scientific_v1/Materna-T{1,2,3}/metrics.parquet`; shared `analysis/primary_macro_mae.csv`, `analysis/matched_vm_fold_cells.csv`, `comparisons/secondary_aggregation_diagnostics.csv`; cohort/scaler/support manifests | 141,785 full execution entries plus compact freeze inventories verified |
| S2 common-context control | `review_revision/experiments/s2_common_context/{posthoc_results.csv,posthoc_metric_rows.parquet,completion_summary.json}`; final `STAGE18B1R_S2_COMMON_CONTEXT_REPORT.md`; active `provenance/recovery_stage18b1r_successor.json` | STAGE_18B1R_PASS; 10,920 valid finals: 5,208 reuses and 5,712 new fits; zero unresolved failures; 33,336 output hashes verified |
| H129 M1 control | `review_revision/experiments/m1_capacity_matched/{posthoc_results.csv,posthoc_metric_rows.parquet,completion_summary.json}`; `STAGE18B2_M1_CAPACITY_MATCHED_REPORT.md`; `provenance/experiment.json` | STAGE_18B2_PASS; 8,190 inner + 2,730 final fits; zero failed finals; 36,442 output hashes verified |
| Ridge AR/ARX | `review_revision/experiments/ar_arx_baseline/{posthoc_results.csv,posthoc_metric_rows.parquet,completion_summary.json}`; `STAGE18B3R_AR_ARX_RECOVERY_REPORT.md`; active `recovery/successor_audit_reduction_fix.json` | STAGE_18B3R_PASS; 36,400 inner + 7,280 final valid fits; 35 historical failed finals preserved and resolved; 109,360 output hashes verified |
| C1 synthesis | `review_revision/stage18c1_final_robustness_synthesis.md`; `stage18c1_evidence/{robust_seed_mean_cells.csv,robust_seed_matched_cells.csv,seed_sensitivity.csv,sharing_sensitivity.csv,contextual_evidence.csv,matched_seed_mean_errors.csv,timetrack_throughput_diagnosis.json}` | STAGE_18C1_PASS; 25 output hashes verified |
| G1/G2 final evidence | `review_revision/stage19g1_evidence/{m1_s2_robustness_24.csv,seed_sensitivity_48.csv,timetrack_memory_attribution.csv,analysis.json}`; G1/G2 reports and verification records; current `manuscript/jss/supplementary/final_evidence_supplement.tex` | 19 G1 and 47 G2 output hashes verified; all 6,955 recorded G1 inputs accounted for |
| H1 scale context | `review_revision/stage19h1_scale_context/{STAGE19H1_DOMINANT_VM_SCALE_CONTEXT_REPORT.md,analysis.json,input_sha256_inventory.json}` | STAGE_19H1_PASS; 10 output hashes and 3,347 direct inputs verified |
| Current manuscript evidence | `manuscript/jss/manuscript.tex`, `manuscript.pdf`, active tables/figures/references, final supplement source and `review_revision/stage19h2b_housekeeping/build/supplement/final_evidence_supplement.pdf` | H2A/H2B output inventories verified: 50/70 files. Latest recorded successful builds are 18 main + 3 supplement pages; no rebuild in this audit |

Every post-hoc result CSV has 24 unique block/resource rows. The three post-hoc inventories total **179,138 verified entries** (not a count of distinct files across all nested inventories). Original freeze manifests and criteria remain authoritative for the primary experiment; controls/diagnostics remain post-hoc.

Two G1 input hashes refer to pre-integration manuscript versions, not current scientific drift. Their exact predecessors survive at `review_revision/stage19g2_evidence/manuscript_before.tex` and `review_revision/stage19h2a_evidence/before_2.tex`. These are explicitly resolved in `coverage_checks.json`; no historical hash was silently replaced with a current manuscript hash.

### Reanalysis levels and portability gaps

1. **Inspect results and format current tables:** files are complete. Frozen comparison CSVs, three control CSV/Parquet endpoints, C1 robust/seed tables, G1 exact CSVs/payload, current table sources and the figure generator are available. `manuscript/jss/figures/results_signed_matrix.py` consumes frozen displayed values and verifies its source hashes; `tables/primary_gains.tex` is still a required generator input even though not included as a manuscript table.
2. **Regenerate diagnostics from saved artifacts without fitting:** the required models/checkpoints, predictions, completions, cohorts, support and scaler records are local and hash-verified. C1 uses `audit_synthesis.py`, `extract_peak.py`, `build_report.py`; G1 uses `surface_evidence.py`, `verify_materna_saved.py`, `export_tables.mjs`, `build_report.py`; H1 uses `audit_scale_context.py` and `build_report.py`. H1 also needs the original Materna raw ZIP to recover native training medians. These are saved-artifact/raw-partition checks, not unavailable external fitting work.
3. **Fresh public-checkout replay:** **not yet self-contained**. The proposed lean Git checkpoint deliberately excludes bulky saved models/predictions and per-fit journals; full audits require their separately restored immutable archive. A checksum list is not an artifact download.

Specific engineering gaps, not missing scientific outcomes:

- G1's historical CSV exporter imports private `@oai/artifact-tool` (local package version 2.8.106, `private=true`, no public licence field) through an absolute `node_modules` symlink. Do not vendor it. Existing exact CSVs and `table_payload.json` permit inspection without this dependency; a future standard-library, lexeme-preserving CSV exporter can remove the replay dependency without changing statistics. None was implemented here.
- Several historical runners/analysis entry points enforce HEAD `f6936cd…`, its parent, clean-tree conditions or original output locations. Running them unmodified at a new checkpoint can legitimately fail; some report builders would overwrite manually audited reports. Preserve sealed code and original execution identities. A future derived-only replay guide/wrapper must use a scratch destination and explain restoration/historical-checkout requirements; do not rewrite seals to the new commit or rerun analysis over audited reports.
- `old_fgcs_rejected/requirements.txt` provides broad lower bounds, not a unified locked replay environment. Ridge records NumPy/pandas/SciPy/scikit-learn versions; local runtime metadata is captured separately. That is not a proof of an installable historical lock or cross-platform bitwise training equivalence. No portable top-level replay README or unified dependency lock was found.
- No published companion-artifact DOI/URL is assigned by this audit. Its public redistribution, host and retention policy need approval. Original raw data should be obtained from upstream using recorded hashes, not silently relicensed or added to Git.

Thus **local scientific coverage is complete**, while claiming fully portable, artifact-complete public reproducibility would require the above follow-up. These are documentation/access/packaging decisions, not a reason to rerun experiments.

## 2. Licence audit and recommended approach

No root/repository-wide `LICENSE`, `LICENCE`, `COPYING` or `NOTICE` was found. The existing owner policy explicitly leaves the choice undecided (`old_fgcs_rejected/docs/VERSION_CONTROL_POLICY.md:113`). Public repository access alone is not an explicit reuse grant. This audit is a scoped technical/licensing inventory, not legal clearance or an ownership determination.

| Material | Evidence and retained rights | Consequence |
|---|---|---|
| Author-owned research code | No existing project-wide grant identified in inspected research sources | **Recommend Apache-2.0 for an explicit author-owned code allowlist, subject to rights-holder approval.** MIT or BSD-3-Clause are viable simpler alternatives for that same owned scope, not replacements for upstream terms |
| TimeTrack data | Live [Kaggle metadata](https://www.kaggle.com/api/v1/datasets/list?search=open-air-interface-cicd-timeseries-dataset) says Apache 2.0; live [Zenodo DOI 10.5281/zenodo.15442251 metadata](https://zenodo.org/api/records/15442251) says CC BY 4.0. All six local CSV sizes/MD5s match that Zenodo record exactly | Record source-specific grants, not a fabricated single repository licence. The verified Zenodo route provides an attributable CC BY 4.0 source for these exact bytes. Keep credit, licence link and changes notices as applicable; exclude raw copies from the proposed Git delta |
| Bitbrains fastStorage/Rnd | [Official GWA-T-12 page](https://atlarge-research.com/gwa-t-12/) requires source acknowledgement and refers to the CCGrid 2015 paper | No standard SPDX/open-data licence established. Do not label data, traces or source-derived prediction collections Apache/MIT/BSD or infer unrestricted redistribution from public downloads |
| Materna T1/T2/T3 | [Official GWA-T-13 page](https://atlarge-research.com/gwa-t-13/) requires Materna acknowledgement and refers to two source papers | Same separate-terms boundary. ZIP filename/document scans found no additional conventional licence grant. Public archive redistribution rights remain USER_ACTION |
| Elsevier CAS template | `manuscript/jss/cas-dc.cls`: LPPL 1.2-or-later header; `cas-common.sty`, `cas-model2-names.bst`: LPPL 1.3c-or-later headers, including Elsevier copyright/attribution | These remain LPPL, not the proposed code licence. Full bundle `manifest.txt`/licence text is absent locally; upstream completeness and any modified-file obligations must be resolved before a distribution-clearance claim |
| Installed dependencies | Local metadata records 11 packages. Examples: scikit-learn BSD-3-Clause, PyArrow Apache-2.0, LightGBM MIT; NumPy and torch wheel expressions contain multiple third-party terms | Dependencies are imports, not a basis to relicense project data. Exclude the environment. If later vendoring/distributing binaries, retain each component's actual notices and obligations, not a blanket simplified “all BSD” statement |
| Manuscript, figures, article and supplement | Separate author/publication material, with publisher-template components identified above | Do not sweep article text/figures into a code licence. Publication/posting rights and any separate document/data licence require author/publisher decisions; no declaration or publishing agreement changed |

The [Apache-2.0 text](https://www.apache.org/licenses/LICENSE-2.0.html) includes patent terms and notice/modified-file obligations. The [MIT](https://opensource.org/license/mit) and [BSD-3-Clause](https://opensource.org/license/bsd-3-clause) texts require preservation of their notices; BSD also restricts endorsement. None authorises overriding another party's dataset, template or article rights. CC BY 4.0 has separate [attribution/change-notice requirements](https://creativecommons.org/licenses/by/4.0/). The [LPPL](https://www.latex-project.org/lppl/lppl-1-3c/) must remain attached to the CAS components.

**Compatibility finding:** no specific conflict was identified that prevents applying Apache-2.0, MIT or BSD-3-Clause to approved, genuinely author-owned research code while keeping separately licensed components separate. That is conditional, not clearance for every legacy file or a blanket relicensing recommendation. Dataset permission uncertainty, unverified historical ownership and template distribution obligations cannot be cured by selecting a permissive code licence.

Recommended later structure (proposal only): a code licence with an explicit scope statement for approved original Python/JavaScript research code; a third-party/data-rights ledger and required upstream notices; exclusions for raw/source-derived datasets, vendor templates, manuscript/publication material and legacy/imported material without cleared ownership. Confirm all relevant authors/institutional rights first. No licence or notice file was added.

## 3. Exact candidate checkpoint plan

This is an **unstaged proposal**, not authority to execute Git operations or publication. Exact paths, not a broad directory/glob staging instruction:

- `candidate_commit_paths.txt`: **8,572 paths** for the proposed commit delta: 11 existing tracked modifications, 8,542 existing untracked additions, and 19 compact audit-documentation additions. The existing-file portion is **137,178,508 bytes**, excluding the new audit documents. The largest candidate existing file is 25,072,904 bytes; none reaches 100,000,000 bytes.
- `candidate_commit_delta.jsonl`: action, exact path, reason and baseline SHA-256/size for pre-existing candidates. New audit-document hashes are bound by the audit output inventory (self-referential inventory has no self-hash).
- `candidate_tree_paths.txt`: **10,552 paths** in the proposed resulting tree: 1,980 unchanged tracked files plus that delta. Existing tracked legacy files, Highlights and submission metadata are inherited, not newly packaged, edited, cleared for relicensing or advertised as current evidence. **No deletion is proposed.**
- `inherited_tracked.jsonl`: exact inherited tracked paths/hashes. Excluding a path from new staging does not remove an already tracked path or its history.
- `candidate_requires_ignore_override.txt`: **21 exact ignored Parquet candidates** needing deliberate per-file override if later approved. No override/staging was performed. Never use blanket `git add .` or blanket force-add.
- `files_excluded.jsonl`: exact disposition/reason for **432,928 pre-existing paths** outside the proposed Git tree. The full before inventory retains their hashes. This large audit ledger itself is not proposed for normal Git.

### Included content

Current manuscript/figure/table/supplement source changes and current main PDF; the existing final H2B supplement PDF is an explicit single build-directory exception. Original scientific protocols/source/configs/manifests/comparison tables/metrics already tracked remain inherited. New content adds all three active post-hoc control adapters, tests, configs, plans, selections, authoritative endpoint CSVs/metric Parquets, source/successor seals, output inventories, final reports and recovery metadata; Stage18A1/C1 and G1/G2/H1 plus revision/housekeeping evidence, exact supplement CSVs, source snapshots/diffs and compact audit documentation. Historical source snapshots retain historical titles/hashes; they are not current publication artifacts.

### Excluded from normal Git, retained separately

| Disposition of pre-existing untracked files | Files | Bytes | Treatment |
|---|---:|---:|---|
| Scientific saved-artifact archive | 374,869 | 27,540,958,344 | Original/control fitted models, predictions, per-fit completions/attempts/runtime artifacts; essential for full saved-artifact re-audits, not disposable caches |
| Historical archive | 12,041 | 834,672,156 | Blocked predecessors, superseded first Bitbrains execution/reports, historical execution logs; retain failures/recovery evidence, never present as current endpoints |
| Full provenance ledgers | 4 | 296,861,645 | Protected-tree JSONL inventories; retain immutable archive + digest anchors, including C1's 100,362,639-byte ledger |
| Build/visual archive | 245 | 97,917,160 | Older PDFs, root `.aux/.bbl/.blg/.log/.out/.abs`, page renders and archived predecessor build trees; do not confuse with current PDFs |
| Local environments/caches/links | 38,640 | 1,259,131,463 | `.venv_legacy`, bytecode, pytest caches, advisory locks, symlinks/`node_modules`, placeholders; exclude, not newly archive as research evidence |
| Upstream raw data/duplicates | 15 | 1,288,516,370 | Retain locally; use official sources + hashes; do not add ZIPs/CSV duplicates to the code checkpoint |
| Untracked raw-derived/canonical caches | 1,639 | 779,812,092 | Preserve where needed for replay under source rights; not a new code-licence grant |
| Other out-of-scope local content | 5,475 | 582,776,853 | Unrelated/legacy runs and existing submission material; no new staging, deletion or publication designation |

No archive/package was assembled, copied, uploaded or assigned a fictitious location. A future companion archive must include the exact required saved artifacts/provenance, preserve relative paths and all failure/predecessor history, and state access/rights clearly. The proposed Git checkpoint supports inspection of committed endpoints; it must not claim that hashing archived files makes them downloadable. Rights and hosting for trace-derived prediction/model collections require approval before public distribution.

## 4. Proposed commit/tag and Data Availability reference

Proposed commit subject: **`JSS reviewer robustness and manuscript evidence checkpoint`**. Keep branch `paper/jss-review-revision`. Proposed new annotated tag: **`jss-review-robustness-reproducibility-v1`** (valid syntax, currently absent). Do not move old scientific tags or rewrite the original experiment commits/seals.

The exact proposed repository reference, **only once the corresponding approved checkpoint/tag exists and is publicly accessible**, is:

`https://github.com/KADOUMAAbdelhak/TimeTrack-Forecasting-Framework/tree/jss-review-robustness-reproducibility-v1`

Prefer also recording the final full 40-character commit SHA after creation. It does not exist yet and cannot honestly be supplied now. If a permanent deposit is later made, add its real DOI, not a planned one.

Proposed Data Availability replacement for a later authorised edit:

> Source code, protocols, derived analysis outputs and SHA-256 inventories for the original experiment, post-hoc controls and robustness diagnostics are available at the project repository's `jss-review-robustness-reproducibility-v1` checkpoint (full commit SHA to be inserted after creation). The Git checkpoint does not include the full fitted-model or per-fit prediction collections; checksum inventories identify but do not themselves provide those files. Third-party raw data remain available from their original sources under their separate terms.

Use the exact link above for the checkpoint label. Replace the archive sentence only if an actual accessible, approved companion artifact deposit exists. Do not describe a local-only commit as publicly available or promise open reuse before licence approval. **The current `fee20c3` declaration was not edited.**

### USER_ACTION decisions and before-release gates

1. Approve Apache-2.0 (recommended) or an alternative, copyright holders and precise author-owned code scope; confirm co-author/institutional authority. Authorise any future licence/notice additions separately.
2. Choose inspection-only Git release versus a full saved-artifact companion deposit; approve archive hosting/access and third-party/derived-data redistribution. Resolve CAS bundle/LPPL obligations and any modified-template status. No repository-wide or article-wide grant is inferred.
3. Authorise portability-only work if a clean-checkout replay claim is wanted: public CSV exporter, a recorded/locked environment and scratch-safe replay instructions that respect historical seals. Do not rerun models or alter scientific results to solve these engineering gaps.
4. Approve the exact commit delta and eventual tag/publication. If later licence, README, dependency or declaration files change, **regenerate the candidate allowlist/hashes before committing**; this list covers only the audited current state. Submission-system/cover-letter/packaging work remains separate.

## 5. Preservation and verification

`working_tree_before.jsonl` covers **443,461 files/symlinks, 33,092,681,050 bytes**, excluding `.git` and only this newly authorised audit directory. Before/after checks bind regular-file SHA-256, bytes/mode and symlink targets; the Git branch, every ref, index and tracked status are unchanged. The after audit reports **443,461 unchanged**, with no changes outside this audit directory. This explicitly preserves the 11 pre-existing manuscript modifications rather than resetting or committing them.

Only audit report/scripts/ledgers were created here. Manuscript modifications=0; declarations/affiliations/AI statement/licence/Highlights/biographies/submission material modifications=0; scientific artifact modifications=0; training=0; inference=0; scientific recomputation=0; package generation=0. Commit=no; tag=no; push=no.

Evidence: `coverage_checks.json`, `licence_findings.json`, `dataset_licence_metadata.json`, exact candidate/exclusion ledgers, `preservation_before.json`, `preservation_after.json`, `verification.json` and `output_sha256_inventory.json` in this directory.

STAGE_19I1_PASS
