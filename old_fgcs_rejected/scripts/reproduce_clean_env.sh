#!/usr/bin/env bash
# Clean-environment reproduction helper.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

TMP_VENV="${TMPDIR:-/tmp}/timetrack_clean_venv_$$"
python3 -m venv "$TMP_VENV"
# shellcheck disable=SC1090
source "$TMP_VENV/bin/activate"
pip install -U pip
pip install -r requirements.txt

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1

python scripts/tt_cli.py test
python scripts/validate_final_config.py --config configs/final_fgcs.yaml
python scripts/reproduce.py --tier smoke --config configs/final_fgcs.yaml

python - <<'PY'
from timetrack.data import dataset_fingerprint
print("dataset_fingerprint", dataset_fingerprint()["fingerprint"])
PY

echo "Clean-env smoke complete. Do not run --tier final until experiment-freeze-v1."
deactivate || true
rm -rf "$TMP_VENV"
