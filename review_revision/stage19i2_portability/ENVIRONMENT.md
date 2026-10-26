# Derived-only environment

## Required runtime

Public **CPython >=3.9**, standard library only. No pip/conda/npm package, BLAS,
GPU, Git executable, network service or Codex runtime is required by
`replay_derived.py`. Its imports are `argparse`, `csv`, `decimal`, `hashlib`,
`io`, `json`, `pathlib` and `sys`. Tests additionally use standard-library
`unittest`, `tempfile`, `shutil`, `subprocess`, `ast` and `importlib`.

Verified here on CPython **3.9.6** and **3.12.14**, both with `-I -S -B`.
These are observed successful versions, not a security recommendation, a
package lock or a claim that every Python/platform combination was tested.
Use byte-preserving UTF-8 input files. LF output is explicit, not OS-dependent.

`requirements-derived.txt` deliberately contains comments only: Level B has
zero third-party dependencies. No empty environment is represented as a lock
for historical training.

## Optional public tooling, not used by Level B

- A text editor/CSV reader for inspection.
- A LaTeX distribution and the existing CAS dependencies for a separate
  manuscript/supplement build; Level B produces row fragments only.
- Matplotlib (existing figure generator verified previously with 3.11.1) for
  a separately authorised figure render. Neither figures nor PDFs are rebuilt
  by this portability task.

## Historical metadata, not Level-B requirements

Ridge's `provenance/experiment.json` records NumPy 2.5.1, pandas 3.0.5,
SciPy 1.18.0 and scikit-learn 1.9.0. I1's **current installed** metadata records
torch 2.13.0, PyArrow 25.0.0 and Matplotlib 3.11.1, among other packages.
Current installed metadata must not be mistaken for a complete, immutable
training-environment lock for every original experiment.

Full Level-C saved-artifact audits may require compatible public NumPy,
pandas, PyArrow and torch packages, plus the restored frozen artifacts; native
training-partition verification needs the source raw archive. Actual model
training would require the original recorded configuration/environment and is
outside this replay path. The legacy lower-bound `requirements.txt` does not
prove bitwise cross-platform training reproducibility.

The private G1 spreadsheet package is neither required nor redistributed.
The old symlink is preserved as historical local state, excluded from the
checkpoint candidate, and never followed by the new replay entry point.
