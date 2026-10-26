# STAGE 19F2A — JSS submission-readiness audit

Date: 23 October 2026. Repository: `/Users/fgtek002/TimeTrack`.
Branch: `paper/jss-review-revision`; HEAD: `f6936cd111d911e40ec2725a18fdfc53768d9ccf`.

**Audit complete; submission readiness BLOCKED.** The current manuscript
builds to 17 double-column pages and its scientific evidence is preserved.
Remaining blocks concern metadata/declarations, one missing table citation,
supplement preparation, Highlights scope and submission packaging—not a
demonstrated scientific defect or a need for another experiment.

This was read-only except for this report and diagnostic evidence in this
directory. Manuscript edits=0; submission assets created=0; scientific
modifications=0; training/inference=0; commit=no; push=no.

## 1. Authority and policy conflicts

The [current official JSS Guide for Authors](https://www.sciencedirect.com/journal/journal-of-systems-and-software/publish/guide-for-authors)
was read successfully in the ordinary browser after web retrieval returned
403. Relevant sections include File format, Title page, Highlights, Vitae,
Declarations, Research data and journal-specific Length. No revision date was
displayed; this is live guidance retrieved on the audit date, not a claim that
an undated page is a newly published policy. Supporting official sources,
explicit update dates and the historical-record search are recorded in
[official_requirements_ledger.md](/Users/fgtek002/TimeTrack/review_revision/stage19f2a_submission_audit/official_requirements_ledger.md).

No Stage 0/JSS-guideline audit could be located in the current checkout,
including tracked files, the manuscript/submission directory and targeted
untracked audit searches. The latter directory contains only `.gitkeep`.
Later manuscript/literature audits provide technical evidence, not a policy
waiver. If the earlier guideline record exists outside this checkout, supply
it for reconciliation; no unseen record is assumed authoritative.

Three distinctions matter:

- **Length:** the live guide encourages full papers shorter than 18
  double-column pages, rather than imposing a hard 17-page maximum. The
  current 17-page paper satisfies that encouragement.
- **Biographies:** there is no biography section in the manuscript, as
  requested. However, JSS requests editable biographies of at most 100 words
  per author. A separate file can satisfy that request without adding a main
  manuscript biography section; no waiver has been established.
- **AI disclosure:** the absence of a disclosure section is confirmed but
  cannot be certified compliant. The documented substantive drafting,
  restructuring and compression exceed basic spelling/grammar checking.
  JSS requires applicable disclosure before References at initial submission.
  The [Elsevier policy](https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals)
  expressly distinguishes substantive restructuring from exempt basic checks.
  This conflicts with retaining no disclosure section. Obtain author-approved
  accurate disclosure and permission for the necessary edit, or written
  editorial clarification; do not silently omit it or describe the workflow
  as grammar-only. Authors must confirm the tool/use history and actual human
  review; this audit does not certify their review on their behalf.

## 2. Requirements checklist

PASS means the inspected item satisfies the stated check; USER_ACTION needs
author information, approval or a submission-system choice; ISSUE needs a
later authorised correction/preparation; N/A means optional/not applicable as
specified. These are submission checks, not an editorial acceptance decision.

| Item | Status | Evidence / remaining action |
|---|---|---|
| Title | PASS | Current title is informative and matches the authorised revision; no formulae or unexplained acronym in the title. |
| Abstract | PASS | **228 words** by whitespace count with hyphenated compounds counted as one; limit 250. Purpose, design, primary/post-hoc distinction, findings and limitations present; no citations. |
| Keywords | PASS | **6** English keywords, within 1–7. |
| Length and layout | PASS | **17 pages**, including references; LaTeX double-column layout permitted. No length justification currently needed. |
| British English | PASS | Prose scan and page review found consistent British usage. Published titles, official CRediT role names and software identifiers retain their original spelling. |
| Section structure | PASS | Numbered Sections 1–9; unnumbered abstract and end declarations. Four substantive RQs remain; these are not internal implementation tokens. |
| Author–year references | PASS | natbib author–year and CAS name/year bibliography; alphabetical reference list. Initial-submission formatting is flexible. `longnamesfirst` produces full initial author lists; consider normalising three-plus-author citations to the guide's et-al examples in a later polish pass, not a missing-reference defect. |
| Reciprocal citations/references | PASS | **35 retained entries, all cited** in main text/input tables; no missing citation keys, orphan entries, duplicate labels or undefined refs/citations. Existing literature-verification records retained. |
| Figure order/citations | PASS | Figures 1–2 cited in that order, with captions and separate vector PDFs; all detected fonts embedded. |
| Table order/citations | ISSUE | Tables 1–5 displayed consecutively, but **Table 4 (`tab:efficiency`) has no explicit prose citation**. Other first table references follow order 1,2,3,5. Add a Table 4 reference in §5.6 before the Table 5 discussion. |
| Readability / editable tables | PASS | All 17 current pages visually inspected; both figures and all five tables legible. Table sources are editable LaTeX, not screenshots; no vertical rules/shaded cells. Figure 2 prints every signed value and discloses its nonlinear colour aid. |
| Data Availability statement | USER_ACTION | Present and candid about omitted model/prediction collections. But the linked `fee20c3` checkpoint predates all post-hoc work; it contains no `review_revision` tree. Specify repository access to the new controls/robustness materials, or an accurate reason for non-sharing. JSS's **Option C** deposit/link-or-explain policy is separate from optional Open Science participation. Public availability of the new materials is not established. |
| Funding | PASS | Existing no-specific-grant statement matches the guide's permitted form. Authors must confirm it is factually current and enter matching submission metadata. |
| CRediT | PASS | Roles for all three authors appear in the PDF; no invented role additions. Authors must confirm the assignments and mirror them in the system. |
| Corresponding author | USER_ACTION | Abdelhak Kadouma is identified with `abdelhak.kadouma@uwasa.fi`; author order and all three emails present. Confirm author details and supply the missing full postal affiliation/contact address. |
| Full affiliations | USER_ACTION | Current affiliation is only University of Vaasa, Vaasa, Finland. Supply authoritative full postal address and any required unit/department; no address inferred. Present-address footnotes only if factually applicable. |
| Highlights | ISSUE | Existing `highlights.tex`: 4 bullets of **68,73,79,82 characters**, including spaces after rendering percent escapes—all within 85. Separate editable asset exists, but wording predates controls: scope the parameter/model reductions to original H64 and a local target complement; avoid an unqualified mechanism reading of adverse transfer. Finalise before packaging. |
| Competing interests | USER_ACTION | No completed declaration found. Every author must provide an explicit answer. Complete the JSS declarations tool and upload its `.doc/.docx` output, even if the truthful answer is no interests. Funding absence is not a COI declaration. No signatures requested by the current guide. |
| Graphical abstract | N/A | Encouraged, not required. None supplied; do not create one automatically or relabel Figure 1 as one. |
| Supplementary material | ISSUE | Two editable fragments exist but neither is a standalone document or upload-ready supplement. Decision criteria are mentioned generically in §4.8. Prepare a named/captioned reader-ready supplement and explicit file/content references; inspect its rendering. Preserve scientific bodies/values. |
| Cover letter | USER_ACTION | No current file. An explicit mandatory cover-letter requirement was not found in the live guide. Prepare a concise author-approved letter if requested by the upload system or chosen by the authors; submission/prior-publication assurances need author confirmation. |
| Reviewer suggestions | USER_ACTION | No mandatory number or exact field requirement verified in the guide. Authenticated submission questions were not inspected. Authors must inspect them and, if required, supply qualified, conflict-free names/contact details. No identities invented. |
| Editable manuscript / source files | ISSUE | Sources exist and compile, but are not an upload-ready flat set. JSS requires editable source; do not assume generic PDF-first advice grants a JSS exemption. Prepare complete sources and follow actual EM item categories. |
| Open Science / replication | USER_ACTION | JSS initiative opt-in; review occurs after acceptance, independently of acceptance. Decide participation and usable/permission-cleared archive scope. No badge claim now. Optional Data in Brief/MethodsX co-submission is not required and not authorised here. |
| ORCID / telephone | USER_ACTION | No ORCIDs supplied; no mandatory ORCID or telephone requirement identified in the current title-page guidance. Supply only if authors wish or actual EM fields require them; do not import an old-guide telephone requirement as current. |
| Author biographies | USER_ACTION | No main-text biography section, but separate editable biographies requested by current guide; obtain ≤100 words per author. Do not invent them or assume optionality without a waiver. |
| Generative-AI disclosure | USER_ACTION | Section absent as requested, but conflicts with applicable current disclosure requirement; see §1. Confirm artwork/research-code assistance and its corresponding caption/Methods disclosure obligations too. |
| Submission ethics / permissions | USER_ACTION | All-author approval, originality/prior-publication status, no concurrent consideration, permissions and data redistribution rights require author confirmation. No upload or system declaration made. |
| Scientific preservation | PASS | **395,786 protected files unchanged**, all **25 Stage 18C1 output hashes match**, branch/HEAD/scientific refs unchanged. |

## 3. Exact manuscript / asset issues for a later authorised stage

1. **Uncited Table 4:** add a `\ref{tab:efficiency}` prose callout in
   `manuscript.tex` §5.6. Its caption/values need no change.
2. **Postal details:** complete the affiliation/title-page address from
   author-supplied information, and confirm corresponding-author metadata.
3. **AI-policy conflict:** approve an accurate preparation disclosure before
   References. Confirm Figure 1 schematic and Figure 2 data-visualisation
   assistance and the applicable caption/Methods details. Figure 2 is generated
   by reproducible code from frozen values, not synthetic results; do not
   invent tool versions or assert that human oversight occurred without author
   confirmation. Research-process AI/code assistance, if applicable, must also
   be described appropriately rather than hidden under language editing.
4. **Availability scope:** identify accessible post-hoc result/protocol/audit
   materials or explain their non-availability. An immutable archive can link
   to third-party raw data under their own terms; it need not redistribute all
   raw traces or automatically include every checkpoint. No publication,
   deposit, commit or push is authorised by this audit.
5. **Highlights scope:** revise the separate Highlights wording without new
   statistics, distinguishing original H64 consolidation from H129 capacity
   control and operational adverse evidence from causal mechanism.
6. **Supplement:** build an upload-ready wrapper around the two existing
   fragments, give it a concise caption and identifiable main-text citation.
   Remove only obsolete draft comments in a submission copy: decision criteria
   line 2 mentions Stage 3; bootstrap fragment lines 2–3 mention Stage 4/future
   wrapper work. Their frozen numerical/predicate bodies must not be rewritten.

No unsupported priority, universal contextual-benefit, causal-sharing or
measured SLA/energy/monetary/production-saving claim was found in current
main-text prose. Such terms occur in literature descriptions and explicit
limitations, not as measured benefits. Post-hoc controls are clearly separated
from frozen primary results in §4.11, Results, Table 3 and interpretation.
The main rendered manuscript has no internal Stage/R4 tokens, TODO/FIXME,
biography or AI-declaration section. The supplement's source comments above
are the specific remaining draft-footprint issue; legitimate RQ1–RQ4 names
and frozen decision-class names are not removable implementation debris.

## 4. Initial submission files and Stage 19F2B package plan

No exact mandatory live upload-item list can be certified without the selected
article type's authenticated EM screens. The public landing page was inspected,
but no account/login, submission or declaration was performed. The following
content set is established by the current guide; container/item choices must
be checked at upload rather than guessed.

### Required content to prepare for initial submission

- **Current editable manuscript and complete dependencies**, plus a newly
  compiled review PDF. A PDF alone is not editable source.
- **Separate editable Highlights** (3–5 compliant bullets).
- **Declarations-tool Word output** with all authors' truthful competing-interest
  answers.
- **Editable author biographies**, at most 100 words each, separate from the
  main manuscript to respect the no-biography-section constraint.
- **Separate artwork:** Figure 1 and Figure 2 vector PDFs, with captions in the
  manuscript (a separate caption file only if the upload instructions ask).
- **Cited supplementary material**, reader-ready with caption, since the paper
  relies on supplementary decision criteria; provide its editable source too
  where requested. It must accompany the initial manuscript, not be promised
  for a later unspecified upload.
- **Availability/data links and manuscript declarations** incorporating the
  author-approved decisions above. These are not replaceable by an unsupported
  checkbox answer.

The [official Elsevier LaTeX instructions](https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions)
require a flat source layout for EM. Current `tables/`, `figures/` and
`thumbnails/` paths therefore need rewriting **only in a future staging copy**,
including the CAS email-icon path in that copy of `cas-common.sty`. Do not
flatten or modify the working manuscript tree during this read-only stage.
Upload source under the proper Manuscript/LaTeX-source categories, not as
scientific Supplementary Material.

Exact main-document dependency content currently needed, relative to
`/Users/fgtek002/TimeTrack/manuscript/jss/`:

| Content | Existing files / treatment |
|---|---|
| Main text and references | `manuscript.tex`; `references.bib`; **fresh** `manuscript.bbl` from the final authorised source build, not the stale root `.bbl`. |
| Local class/style | `cas-dc.cls`; `cas-common.sty`; `cas-model2-names.bst`. |
| Five input table sources | `tables/related_work_comparison.tex`; `tables/dataset_summary.tex`; `tables/posthoc_controls.tex`; `tables/efficiency_summary.tex`; `tables/cross_study_synthesis.tex`. |
| Two artwork PDFs | `figures/framework_s1_s2_m1.pdf`; `figures/results_signed_matrix.pdf`. |
| Used CAS icon | `thumbnails/cas-email.jpeg`, with its staging-copy path adjusted for a flat layout. Other stock icons are only needed if enabled; do not treat them as scientific figures. |
| Editable artwork provenance | `figures/framework_s1_s2_m1.tex` and `figures/results_signed_matrix.py` exist; preserve them in the artwork/replication source set as appropriate. The Python renderer depends on repository-frozen inputs and is not a standalone EM main document. Do not rerun it merely to package an unchanged PDF. |

Proposed **new Stage 19F2B assets**, only after explicit authority and required
author information: `manuscript.pdf` freshly built from the corrected staging
source; a flat `LaTeXSource.zip`; `Highlights.docx` (or another accepted editable
source format); `DeclarationOfInterest.docx` from the declarations tool;
`AuthorBiographies.docx`; `SupplementaryMaterial.pdf` and its editable wrapper.
Use unambiguous artwork names such as `Figure1.pdf`/`Figure2.pdf` in the staging
copy and update its references consistently. Record a staging manifest/hashes
and verify its independent build. All these are planned names, not files
created by this audit.

**Conditional, not verified mandatory:** `CoverLetter.docx`, any separately
requested title-page/caption/funding/author-agreement file, and a reviewer list
or system entries. Supply them according to actual upload fields and truthful
author answers. A blinded manuscript is not required by the current
single-anonymised policy. A graphical abstract, SSRN posting, Open Science
opt-in and companion Data in Brief/MethodsX article are not automatic tasks.

Do **not** upload the stale root `manuscript.pdf` (**18 pages**), root build
intermediates, literature-audit notes, review-stage reports, old submission
material, unused `tables/primary_gains.tex` as an extra displayed table, or the
entire experiment/model/prediction tree as a LaTeX package. The frozen
primary-gains source can belong in a separately scoped replication archive;
it is an input to the plot's reproducibility workflow, not a sixth main table.

## 5. Metadata requiring user input

Before package finalisation, obtain one consolidated author confirmation of:

1. Full postal affiliation(s), any department/unit and changed/present addresses;
   final names/order, corresponding author, emails and optional identifiers.
2. All authors' competing interests, including any journal role; truthful
   declarations-tool answers and resulting Word file.
3. The actual AI tools/versions/purposes used in writing, literature/code/figure
   work, the extent of human review, and permission for required disclosure edits.
4. Three author-approved biographies of at most 100 words each, or a written
   journal waiver if they are to be omitted entirely.
5. Public availability/permissions/licensing decisions for the post-hoc controls
   and robustness materials; accurate reasons for anything not shared. Existing
   code/results must not be deposited or pushed without separate authority.
6. All-author approval and submission ethics/permissions; article type and
   cover-letter assurances; reviewer candidates only if required by the system.
7. Open Science/SSRN/open-access choices and any funding/institutional
   obligations. Do not select an APC, licence or posting agreement on their behalf.

## 6. Build, visual and integrity evidence

- Fresh Tectonic cached build: **success**, 17 pages. Independent desktop
  compiler: **success**. No unresolved references/citations or rerun request in
  the final build. All 35 bibliography entries are used.
- All 17 fresh pages rendered and inspected: title/front matter, equations,
  Tables 1–5, Figures 1–2, end declarations and references readable; no clipped
  content or overlapping cells. Both figure PDFs have embedded fonts. No
  primary/artwork value or scientific claim was recomputed or changed.
- Remaining nonfatal warnings: pre-existing CAS title-box overfull warning
  (123.62721 pt), empty anchors/underfull boxes, and missing-pages warnings for
  two ICLR conference references. No title clipping observed; no bibliographic
  data invented to suppress non-paginated-record warnings.
- Current source SHA-256:
  `5d4e4d67cb60cf19b7aaf0fc0ae46202d74c26c0696666e9cd4502e471481ef9`.
  Bibliography SHA-256:
  `f7efdff564455a709cda5459319f8f3c25811ca3a1a409187dd2cd7e0f7eef8b`.
  Fresh diagnostic PDF SHA-256:
  `5a38f0f0fce8aa4ad17d6a1d1fca3f8a6741f61b56032fd198eb03e0cc2d7b2f`.
- Full protected membership/content audit: **395,786 files unchanged** against
  the Stage 18C1 inventory with previously authorised 19C/19E/19F1 manuscript
  overlays. All **25 Stage 18C1 output hashes** match. HEAD, branch and
  scientific refs unchanged; no staged changes; `git diff --check` passes.
  Existing authorised dirty manuscript files were preserved, not reset.

Detailed machine checks are in
[verification.json](/Users/fgtek002/TimeTrack/review_revision/stage19f2a_submission_audit/verification.json);
all-page review is recorded in
[visual_signoff.json](/Users/fgtek002/TimeTrack/review_revision/stage19f2a_submission_audit/visual_signoff.json).
The audit used the PDF workflow for fresh rendering and review and the writing
guidance for a concise, status-led report; no personal writing samples were
available through connected sources. A diagnostic build is evidence, not a
created submission package or an approval to submit.

**Disposition:** finish the bounded editorial/package tasks after obtaining
the missing author information and resolving the disclosure conflict. No
additional experiment is indicated by this readiness audit. Do not claim
submission PASS while these obligations remain unresolved.

Scientific modifications=0; manuscript modifications=0;
submission assets created=0; commit=no; push=no.

STAGE_19F2A_BLOCKED_METADATA_DECLARATIONS_AND_PACKAGE_READINESS
