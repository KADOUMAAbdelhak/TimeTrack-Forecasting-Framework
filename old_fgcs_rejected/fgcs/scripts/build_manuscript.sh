#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

rm -f manuscript.aux manuscript.bbl manuscript.blg manuscript.bcf manuscript.out \
  manuscript.log manuscript.run.xml manuscript.fls manuscript.fdb_latexmk \
  manuscript.synctex.gz manuscriptNotes.bib

if command -v latexmk >/dev/null 2>&1; then
  latexmk -pdf -interaction=nonstopmode -halt-on-error manuscript.tex
elif command -v pdflatex >/dev/null 2>&1; then
  pdflatex -interaction=nonstopmode manuscript.tex
  bibtex manuscript
  pdflatex -interaction=nonstopmode manuscript.tex
  pdflatex -interaction=nonstopmode manuscript.tex
elif command -v tectonic >/dev/null 2>&1; then
  # Tectonic resolves BibTeX via cas-model2-names.bst when present.
  tectonic -X compile --keep-logs --keep-intermediates manuscript.tex
else
  echo "ERROR: no latexmk/pdflatex/tectonic found" >&2
  exit 1
fi

test -f manuscript.pdf

PAGES="unknown"
if command -v pdfinfo >/dev/null 2>&1; then
  PAGES=$(pdfinfo manuscript.pdf | awk '/Pages:/ {print $2}')
elif command -v python3 >/dev/null 2>&1; then
  PAGES=$(python3 - <<'PY'
from pypdf import PdfReader
print(len(PdfReader("manuscript.pdf").pages))
PY
) || PAGES="unknown"
fi
SIZE=$(wc -c < manuscript.pdf | tr -d ' ')

echo "==== BUILD REPORT ===="
echo "pdf=manuscript.pdf"
echo "pages=${PAGES}"
echo "bytes=${SIZE}"
echo "unresolved_citations=$(grep -c 'Citation .* undefined' manuscript.log || true)"
echo "unresolved_references=$(grep -c 'Reference .* undefined' manuscript.log || true)"
echo "overfull_boxes=$(grep -c 'Overfull' manuscript.log || true)"
echo "underfull_boxes=$(grep -c 'Underfull' manuscript.log || true)"
if [[ "${PAGES}" != "unknown" && "${PAGES}" -gt 15 ]]; then
  echo "ERROR: page count ${PAGES} exceeds 15" >&2
  exit 1
fi
echo "BUILD OK"
