#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 scripts/validate_manuscript.py
bash scripts/build_manuscript.sh
python3 scripts/validate_manuscript.py

mkdir -p dist
ZIP="dist/timetrack_fgcs_overleaf.zip"
rm -f "$ZIP"

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

copy_path() {
  local rel="$1"
  if [[ -e "$rel" ]]; then
    mkdir -p "$STAGE/$(dirname "$rel")"
    if [[ -d "$rel" ]]; then
      mkdir -p "$STAGE/$rel"
      if command -v rsync >/dev/null 2>&1; then
        rsync -a --exclude '.DS_Store' --exclude '*.aux' --exclude '*.log' --exclude '*.out' --exclude '*.xdv' --exclude '*.fls' --exclude '*.fdb_latexmk' "$rel/" "$STAGE/$rel/"
      else
        cp -R "$rel"/. "$STAGE/$rel"/
      fi
    else
      cp "$rel" "$STAGE/$rel"
    fi
  fi
}

# Explicit allowlist
for f in manuscript.tex references.bib highlights.txt \
  cas-dc.cls cas-common.sty cas-model2-names.bst \
  README.md BUILD.md CLEANUP_REPORT.md AI_DECLARATION_CANDIDATE.txt \
  SUBMISSION_FILE_INVENTORY.md FINAL_MANUSCRIPT_REVIEW.md; do
  copy_path "$f"
done
copy_path figs
copy_path tables
copy_path supplementary
copy_path thumbnails
# Do not ship provenance audits or raw results CSVs in Overleaf ZIP
mkdir -p "$STAGE/scripts"
cp scripts/validate_manuscript.py scripts/build_manuscript.sh \
  scripts/build_supplementary.sh \
  scripts/package_overleaf.sh scripts/verify_overleaf_package.sh \
  scripts/package_editorial_manager_flat.py scripts/verify_editorial_manager_flat.sh \
  "$STAGE/scripts/" 2>/dev/null || true

# Reject symlinks
if find "$STAGE" -type l | grep -q .; then
  echo "ERROR: symlinks in package stage" >&2
  find "$STAGE" -type l >&2
  exit 1
fi

(
  cd "$STAGE"
  zip -r -X "$ROOT/$ZIP" . >/dev/null
)

SHA=$(shasum -a 256 "$ZIP" | awk '{print $1}')
SIZE=$(wc -c < "$ZIP" | tr -d ' ')
COUNT=$(unzip -Z1 "$ZIP" | wc -l | tr -d ' ')

echo "==== PACKAGE REPORT ===="
echo "zip=$ZIP"
echo "sha256=$SHA"
echo "bytes=$SIZE"
echo "file_count=$COUNT"
echo "---- inventory ----"
unzip -Z1 "$ZIP" | sort
echo "PACKAGE OK"
