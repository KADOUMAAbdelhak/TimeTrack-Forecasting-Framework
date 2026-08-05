#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ZIP="$ROOT/dist/editorial_manager/timetrack_fgcs_em_flat.zip"
test -f "$ZIP"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP" -d "$TMP"

# no subdirs
if find "$TMP" -mindepth 1 -type d | grep -q .; then
  echo "ERROR: subdirectories present in flat ZIP extract" >&2
  find "$TMP" -mindepth 1 -type d >&2
  exit 1
fi
test -f "$TMP/manuscript.tex"
test -f "$TMP/references.bib"

cd "$TMP"
if command -v tectonic >/dev/null 2>&1; then
  tectonic -X compile --keep-logs --keep-intermediates manuscript.tex
elif command -v latexmk >/dev/null 2>&1; then
  latexmk -pdf -interaction=nonstopmode -halt-on-error manuscript.tex
else
  echo "ERROR: no LaTeX engine" >&2
  exit 1
fi

PAGES=$(python3 - <<'PY'
from pypdf import PdfReader
print(len(PdfReader("manuscript.pdf").pages))
PY
)
if [[ "$PAGES" -gt 15 ]]; then
  echo "ERROR: flat isolated pages $PAGES > 15" >&2
  exit 1
fi
HEAD=$(python3 - <<'PY'
from pypdf import PdfReader
t=(PdfReader("manuscript.pdf").pages[0].extract_text() or "").lstrip()
print(t.startswith("Highlights"))
PY
)
if [[ "$HEAD" == "True" ]]; then
  echo "ERROR: flat PDF begins with Highlights" >&2
  exit 1
fi

echo "==== EM FLAT VERIFY ===="
echo "isolated_pages=$PAGES"
echo "VERIFY OK"
