# Official requirements ledger

Checked 23 October 2026. This is a paraphrased audit record, not a submission
document. No policy publication/update date is inferred from a crawl date.

## JSS journal-specific authority

The current [JSS Guide for Authors](https://www.sciencedirect.com/journal/journal-of-systems-and-software/publish/guide-for-authors)
was read directly in the in-app browser, including the complete relevant
sections. The web retrieval endpoint returned HTTP 403; the ordinary browser
rendered the official guide successfully. No access control was bypassed.
No explicit guide revision date was displayed. The content below is the live
guide observed on the audit date, not a dated historical snapshot.

| Guide section | Requirement observed / audit interpretation |
|---|---|
| Peer review | Single-anonymised; retain author information in the manuscript. |
| File format; LaTeX | Editable text/source required; PDF does not replace source. Two-column format is permitted for LaTeX. Relevant editable sources are requested on submission or revision. Prepare them now rather than assume a PDF-only initial route. |
| Title page | Informative title, accurate ordered author names, full affiliation postal addresses including country, identified corresponding author and published email. |
| Abstract; Keywords | Abstract at most 250 words; 1–7 English keywords. |
| Highlights | Mandatory at submission, separate editable file with highlights in its name; 3–5 items, at most 85 characters including spaces per item. |
| Graphical abstract | Encouraged, not mandatory. If supplied, separate file; at least 1,328 pixels wide, horizontal longest side, readable at 13 cm; TIFF/EPS/PDF/Office preferred. |
| Tables | Editable text, cited in prose, consecutive numbers, captions and notes; avoid vertical rules/shaded cells. |
| Figures / formats / captions | Separate logically named artwork, cited consecutively, captions; vector EPS/PDF with embedded fonts or outlined text accepted. |
| Supplementary material | Relevant and cited, concise file captions, submitted with the manuscript; published as supplied, without publisher typesetting. |
| Research data | Option C: repository deposit, article citation/link, or explanation why sharing is not possible. |
| Data statement | Availability statement required at submission. |
| Author contributions | CRediT roles required. |
| Funding | Declare support and sponsor role, or the no-specific-grant statement where true. |
| Declaration of competing interests | All authors disclose; complete the declarations tool even for no interests. Upload its Word output at attach/upload files; signatures not required. |
| Declaration of generative AI use | Substantive manuscript preparation requires a declaration before References at first submission; basic checking exemption is not a blanket exemption for rewriting. |
| Generative AI / artwork | Reproducible, data-derived visualisation and explanatory artwork assistance are permitted under the linked policy, with applicable disclosure. Fabricating observed data is not permitted. |
| Vitae | Editable author biographies, no more than 100 words for each author, requested. No demand to insert a biography section in the main manuscript was found. |
| Journal-specific length | Full research papers are encouraged to be shorter than 36 single-column or 18 double-column pages; longer papers need justification. This is not a hard 17-page maximum. |
| References | Consistent initial format; author–year journal style, alphabetical reference list; complete real sources and reciprocal citation/reference coverage. |
| Submission declaration | Authors must approve final submission; no simultaneous consideration; prior publication restrictions apply. Do not infer author answers from technical readiness. |
| Preprints | SSRN posting offered as an opt-in; all co-authors must agree. It does not determine the editorial decision. |
| Open Science | JSS initiative is opt-in; availability/usability review follows acceptance and does not determine paper acceptance. A badge must not be claimed in advance. |
| Language | American or British English accepted, not a mixture; this manuscript uses British English. |

No explicit cover-letter mandate, reviewer-suggestion count, or mandatory
ORCID requirement was found in the guide. Their live submission-question
status is not established. The public [JSS Editorial Manager landing page](https://www.editorialmanager.com/jssoftware/default.aspx)
was accessible; authenticated author forms were not entered or answered.

## Supporting official authorities

- [Elsevier LaTeX instructions](https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions),
  retrieved 23 October 2026, no displayed update date: include all source
  dependencies; Editorial Manager cannot process subdirectories. Keep sources
  flat, and use the correct source/manuscript/figure/table upload categories,
  not Supplementary Material for manuscript source. General PDF-first advice
  does not override JSS's current editable-file guidance.
- [Highlights support](https://www.elsevier.support/publishing/answer/how-do-i-include-highlights-with-my-manuscript),
  updated 1 June 2026: editable separate source, 3–5 items, 85-character limit;
  whether mandatory depends on the journal. The current JSS guide makes it
  mandatory here.
- [Submission-file preparation](https://www.elsevier.support/publishing/answer/how-do-i-prepare-my-files-for-submission-in-editorial-manager),
  updated 15 June 2026: journal-specific instructions govern file types,
  declarations and metadata. Use unique, standard filenames without special
  characters, at most 80 characters. Submission questions are configurable.
- [Declarations support](https://www.elsevier.support/publishing/answer/what-are-conflict-of-interest-statements-funding-source-declarations-author-agreementsdeclarations-and-permission-notes),
  updated 3 October 2026: interest declarations require explicit author answers;
  funding and permission declarations have distinct purposes. The JSS-specific
  declarations-tool/Word-file workflow above governs this submission.
- [Elsevier generative-AI policy](https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals),
  retrieved 23 October 2026, no displayed update date: substantive restructuring
  requires manuscript disclosure; identify tool, purpose and human oversight.
  Explanatory-image assistance requires caption disclosure. AI-supported data
  visualisation must be reproducible and faithfully derived from data, with
  tool/version/developer information in Methods; the JSS guide also asks for
  applicable caption and general disclosure. AI used in the research process
  rather than manuscript preparation requires Methods reporting.

## Historical-record reconciliation

No Stage 0/JSS-guideline audit or archived official guideline could be located
in the current checkout: manuscript/submission contains only `.gitkeep`;
tracked-tree searches and filename/content searches of manuscript, review
records and research-scope records found no such document. Existing literature
audits and Stage 19A–19F1 evidence were inspected but do not establish a newer
publisher-policy exception. A historical FGCS guide is for a different journal
and is not an authority for JSS. If a Stage 0 record exists elsewhere, it should
be supplied for reconciliation; its missing location does not waive the live
requirements.

The live guide resolves the manuscript length, Highlights, graphical abstract,
biographies, declarations and research-data questions. There is no verified
official exemption permitting omission of a substantive AI-use declaration.
There is also no verified waiver of requested biographies. The user's
no-biography-section constraint can be respected with a separate editable
biography file; the no-AI-disclosure-section constraint cannot presently be
certified as compliant for the documented substantive writing workflow.
