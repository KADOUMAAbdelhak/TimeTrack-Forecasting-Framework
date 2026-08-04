#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ZIP="$ROOT/dist/timetrack_fgcs_overleaf.zip"
test -f "$ZIP"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP" -d "$TMP"

test -f "$TMP/manuscript.tex"
if [[ -d "$TMP/fgcs" ]]; then
  echo "ERROR: nested fgcs/ directory in ZIP root" >&2
  exit 1
fi

# Ensure no parent-repo absolute path required for compile
if grep -R "/Users/fgtek002/TimeTrack" --include='*.tex' --include='*.bib' "$TMP" >/dev/null 2>&1; then
  echo "ERROR: absolute parent path in packaged tex/bib" >&2
  exit 1
fi

LOCAL_PAGES="unknown"
if [[ -f "$ROOT/manuscript.pdf" ]]; then
  if command -v pdfinfo >/dev/null 2>&1; then
    LOCAL_PAGES=$(pdfinfo "$ROOT/manuscript.pdf" | awk '/Pages:/ {print $2}')
  else
    LOCAL_PAGES=$(python3 - <<PY
from pypdf import PdfReader
print(len(PdfReader("$ROOT/manuscript.pdf").pages))
PY
)
  fi
fi

cd "$TMP"
if command -v latexmk >/dev/null 2>&1; then
  latexmk -pdf -interaction=nonstopmode -halt-on-error manuscript.tex
elif command -v pdflatex >/dev/null 2>&1; then
  pdflatex -interaction=nonstopmode manuscript.tex
  bibtex manuscript
  pdflatex -interaction=nonstopmode manuscript.tex
  pdflatex -interaction=nonstopmode manuscript.tex
elif command -v tectonic >/dev/null 2>&1; then
  tectonic -X compile --keep-logs --keep-intermediates manuscript.tex
else
  echo "ERROR: no LaTeX engine available for isolated verify" >&2
  exit 1
fi

test -f manuscript.pdf
if command -v pdfinfo >/dev/null 2>&1; then
  ISO_PAGES=$(pdfinfo manuscript.pdf | awk '/Pages:/ {print $2}')
else
  ISO_PAGES=$(python3 - <<'PY'
from pypdf import PdfReader
print(len(PdfReader("manuscript.pdf").pages))
PY
)
fi
if [[ "$ISO_PAGES" -gt 15 ]]; then
  echo "ERROR: isolated page count $ISO_PAGES > 15" >&2
  exit 1
fi
if [[ "$LOCAL_PAGES" != "unknown" && "$LOCAL_PAGES" != "$ISO_PAGES" ]]; then
  echo "ERROR: page count mismatch local=$LOCAL_PAGES isolated=$ISO_PAGES" >&2
  exit 1
fi

echo "==== VERIFY REPORT ===="
echo "isolated_pages=$ISO_PAGES"
echo "local_pages=$LOCAL_PAGES"
echo "VERIFY OK"
