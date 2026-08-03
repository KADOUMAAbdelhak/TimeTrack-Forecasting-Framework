#!/usr/bin/env bash
# Clean-environment reproduction helper (development / pre-freeze).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

python scripts/tt_cli.py test
python - <<'PY'
from timetrack.data import dataset_fingerprint
print("dataset_fingerprint", dataset_fingerprint())
PY

echo "Reproduction smoke complete. Do not run publication.yaml from this script."
