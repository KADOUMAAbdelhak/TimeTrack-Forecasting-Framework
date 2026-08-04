# FGCS Cleanup Report

Generated: 2026-08-04T16:03:42.114736Z

Checkpoint commit: `5337281` (chore: checkpoint repository before FGCS manuscript preparation).

## Classification of pre-existing files

| File | Action | Reason |
|---|---|---|
| `cas-dc.cls` | KEEP | KEEP — Elsevier CAS double-column class |
| `cas-common.sty` | KEEP | KEEP — required CAS style |
| `cas-model2-names.bst` | KEEP | KEEP — numbered BST for natbib |
| `Feature-Engineering.png` | REMOVE | Materna-manuscript figure; not used by TimeTrack paper |
| `Hybrid-based-approach.png` | REMOVE | Materna-manuscript figure |
| `figure_CPU_usage_pct.png` | REMOVE | Materna result figure |
| `figure_Disk_write_throughput_KB_s.png` | REMOVE | Materna result figure |
| `figure_Memory_usage_pct.png` | REMOVE | Materna result figure |
| `figure_Network_received_throughput_KB_s.png` | REMOVE | Materna result figure |
| `figure_Network_transmitted_throughput_KB_s.png` | REMOVE | Materna result figure |
| `summary_figure.png` | REMOVE | Materna summary figure |
| `cas-dc-sample.pdf` | REMOVE | template sample PDF |
| `cas-dc-sample.tex` | REMOVE | template sample; replaced by manuscript.tex |
| `cas-dc-template.tex` | REPLACE | old Materna scientific content; author metadata extracted then replaced |
| `cas-sc-sample.pdf` | REMOVE | single-column sample PDF unused |
| `cas-sc-sample.tex` | REMOVE | single-column sample unused |
| `cas-sc-template.tex` | REMOVE | single-column template unused |
| `cas-sc.cls` | REMOVE | single-column class not used for FGCS |
| `cas-refs.bib` | REPLACE | placeholder refs; replaced by verified references.bib |
| `README` | REPLACE | replaced by README.md |
| `manifest.txt` | REMOVE | old packaging manifest |
| `doc/rvdtx.sty` | REMOVE | CAS documentation not required for Overleaf compile |
| `doc/pdfwidgets.sty` | REMOVE | CAS documentation not required for Overleaf compile |
| `doc/sc-sample.pdf` | REMOVE | CAS documentation not required for Overleaf compile |
| `doc/makefile` | REMOVE | CAS documentation not required for Overleaf compile |
| `doc/elsdoc-cas.tex` | REMOVE | CAS documentation not required for Overleaf compile |
| `doc/elsdoc-cas.pdf` | REMOVE | CAS documentation not required for Overleaf compile |
| `doc/glyphtounicode.tex` | REMOVE | CAS documentation not required for Overleaf compile |
| `doc/dc-sample.pdf` | REMOVE | CAS documentation not required for Overleaf compile |
| `thumbnails/cas-email.jpeg` | KEEP | Required by `cas-common.sty` social icon hooks at `\maketitle` |
| `thumbnails/cas-linkedin.jpeg` | KEEP | Required by CAS template |
| `thumbnails/cas-gplus.jpeg` | KEEP | Required by CAS template |
| `thumbnails/cas-url.jpeg` | KEEP | Required by CAS template |
| `thumbnails/cas-facebook.jpeg` | KEEP | Required by CAS template |
| `thumbnails/cas-twitter.jpeg` | KEEP | Required by CAS template |
| `figs/cas-munnar-2024.jpg` | REMOVE | CAS sample decorative images unused |
| `figs/cas-pic1.pdf` | REMOVE | CAS sample decorative images unused |
| `figs/cas-grabs.pdf` | REMOVE | CAS sample decorative images unused |

## Notes

- Scientific narrative from Materna manuscript is discarded (self-plagiarism avoidance).
- Author/affiliation metadata from `cas-dc-template.tex` retained for authorship: Kadouma, Shukla, Elmusrati (University of Vaasa).
- Required CAS template files retained: `cas-dc.cls`, `cas-common.sty`, `cas-model2-names.bst`.
- No temporary LaTeX outputs were present at audit time.
