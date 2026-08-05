#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/supplementary"

# Ensure CAS class/style resolve from the FGCS root
export TEXINPUTS="${ROOT}:.:${TEXINPUTS:-}"

rm -f supplementary_material.aux supplementary_material.log \
  supplementary_material.out supplementary_material.xdv

if command -v tectonic >/dev/null 2>&1; then
  tectonic -X compile --keep-logs --keep-intermediates supplementary_material.tex
elif command -v latexmk >/dev/null 2>&1; then
  latexmk -pdf -interaction=nonstopmode -halt-on-error supplementary_material.tex
elif command -v pdflatex >/dev/null 2>&1; then
  pdflatex -interaction=nonstopmode supplementary_material.tex
  pdflatex -interaction=nonstopmode supplementary_material.tex
else
  echo "ERROR: no LaTeX engine" >&2
  exit 1
fi

test -f supplementary_material.pdf
PAGES=$(python3 - <<'PY'
from pypdf import PdfReader
print(len(PdfReader("supplementary_material.pdf").pages))
PY
)
echo "==== SUPPLEMENT BUILD ===="
echo "pdf=supplementary/supplementary_material.pdf"
echo "pages=$PAGES"
echo "SUPPLEMENT OK"
