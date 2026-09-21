# Build instructions

## Local (repository checkout)

```bash
cd /Users/fgtek002/TimeTrack/fgcs
python scripts/validate_manuscript.py
bash scripts/build_manuscript.sh
bash scripts/package_overleaf.sh
bash scripts/verify_overleaf_package.sh
```

Requirements: TeX Live (or equivalent) with `latexmk`/`pdflatex`/`bibtex`, `pdfinfo`, `zip`/`unzip`, Python 3.

## Overleaf

1. Upload `dist/timetrack_fgcs_overleaf.zip` (ZIP root contains `manuscript.tex`).
2. Set main document to `manuscript.tex`.
3. Compile with pdfLaTeX + BibTeX (or latexmk).

Do not nest an extra `fgcs/` folder when uploading.
