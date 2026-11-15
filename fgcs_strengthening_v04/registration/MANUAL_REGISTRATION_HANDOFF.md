# v0.4 manual registration handoff

**Status: pre-registration documentation, prepared 2026-11-15.** It is not part of package `24277248…8442` or execution seal `babe1fef…bd15`. Nothing has been submitted or published. `EXECUTION_UNLOCKED = NO`.

## Frozen values

Every external record must match these exactly.

| Item | Value |
|---|---|
| Title | Evaluating Contextual Input and Shared Representation in Multi-Metric Runtime Forecasting for Cloud Software Systems: Minimal Revision Protocol v0.4 |
| Protocol | `review_revision/fgcs_strengthening/analysis_plan_v0.4.md`, frozen 2026-11-15, SHA-256 `76652ad9231eed63245f38d2c7a80a73752a9f3b9fefdb0bd31e3c225af4b80f` |
| Tag / commit | `fgcs-v04-registration-package` / `9b94a066d2818ac726205954cb53f52e0ec3371d` |
| Package digest | `242772484617d4c21b6694b124540eebab60588d5e856b4b4a613498aa2e8442` |
| Execution seal | `babe1fefa7f48c462b7f628d3d98507ec03779a31df843cb7d6f044d257abd15` |
| Input archive | Zenodo `10.5281/zenodo.24189108`, reused unchanged (13 files; N3 manifest `cb2b005c…a3e`) |
| Related registration | OSF `kuwra` (v0.3), superseded before any v0.3 execution; not withdrawn |
| Independent audit | AUDIT_PASS_WITH_NOTES (2026-11-15); launcher notes N1 and N2 fixed in `d8da4746` |

The prepared texts are in `OSF_SECONDARY_DATA_FIELDS.json`: `metadata` (title, description, licence, tags, subjects, contributors) and `registration_responses` (24 fields, OSF keys `72-*`). The archive list is `EXTERNAL_ARCHIVE_UPLOAD_LIST.json`.

## What is different from v0.3

- **No Zenodo step.** Every sealed v0.4 input not held in Git is already in record `24189108`, and nothing new is uploaded.
- **Five attachments**, all from the tagged commit:
  - question 72-22: `analysis_plan_v0.4.md`, `PACKAGE.json`, `execution_seal.json`, `schedule.json`;
  - question 72-26: `analysis_catalogue.json`.
- **Do not attach `host_manifest.json`** (it contains the hostname); its hash is in `PACKAGE.json`.
- **No hypothesis tests.** Fields 72-4, 72-49 and 72-55 state that v0.4 is descriptive, with no p-values or multiplicity families.
- **72-57** lists the analysis choices the protocol leaves to the sealed code (audit note N4).

## Manual sequence

1. Review and approve every prepared field. The three contributors are as in v0.3; confirm that Amit Shukla and Mohammed Elmusrati are comfortable being named on this public record.
2. Run, from the repository root:

   ```bash
   PYTHONPATH=$PWD old_fgcs_rejected/.venv_legacy/bin/python -B -m fgcs_strengthening_v04.build_registration --verify
   ```

   It must report package `24277248…8442`, verified.
3. Create a new public OSF registration with the **Secondary Data Preregistration** template. Contributors: Kadouma (Admin, bibliographic), Shukla (Read, bibliographic), Elmusrati (Read, bibliographic). Only the Admin submits and approves.
4. Paste the title, description and all 24 responses exactly. OSF stores `<` and `>` as HTML entities; the prepared texts contain neither.
5. Attach the five files above to questions 72-22 and 72-26, taking each from the tagged commit (for example `git show fgcs-v04-registration-package:<path> > <file>`).
6. Link the registration to OSF `kuwra` (for example in the description, which already names it).
7. Submit and finalise; the sole Admin (Kadouma) approves. OSF may hold the registration pending for up to 48 hours.
8. Record the registration ID, DOI and timestamp, and set `OSF_REGISTRATION` in `fgcs_strengthening_v04/launch.py` to the ID. That edit is to the unsealed launcher only.
9. Once the registration is public, run:

   ```bash
   PYTHONPATH=$PWD old_fgcs_rejected/.venv_legacy/bin/python -B -m fgcs_strengthening_v04.launch verify-registration
   ```

   It must print `REGISTRATION VERIFIED`. It checks that the registration is public, not pending, withdrawn or embargoed, has a DOI, that the title, description and responses hash to this field map, that the five attachment SHA-256 values match, and that the Zenodo record holds exactly the 13 listed files. Its report is stored in `OSF_VERIFICATION.json`, which the launcher requires before any run.
10. Complete `REGISTRATION_EVIDENCE_TEMPLATE.md` (ID, DOI, date, the verification output, your decision).
11. Set `EXECUTION_UNLOCKED = YES` only after every check above has succeeded.

## STOP AND DO NOT SUBMIT

Stop, leave the draft unsubmitted and record the problem if any of the following happens:

- [ ] `build_registration --verify` fails, or reports another package or seal.
- [ ] The tag `fgcs-v04-registration-package` resolves to anything other than `9b94a066…`.
- [ ] Any pasted field differs from `OSF_SECONDARY_DATA_FIELDS.json`, or the title or protocol version differs from the frozen values.
- [ ] Any attachment differs from the tagged file, or `host_manifest.json` or any data file is attached.
- [ ] The prior-access disclosure (72-46 and the description) or the statement that no v0.4 fit, outer-test evaluation or analysis preceded registration is missing.
- [ ] The Zenodo record `24189108` no longer holds exactly the 13 listed files.

Until step 11 is complete, do not create a runtime journal or run `launch start`.
