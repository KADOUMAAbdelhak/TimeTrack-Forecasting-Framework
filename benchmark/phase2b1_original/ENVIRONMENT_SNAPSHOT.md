# Phase 2B-1 Environment Snapshot

Snapshot date: 2026-09-22, Europe/Helsinki.

The recoverable environment used by the Phase 2B-1 scripts is:

- Virtual environment: `/private/tmp/timetrack-phase1b-venv`
- Python executable: `/private/tmp/timetrack-phase1b-venv/bin/python`
- Python: 3.13.2, Clang 16.0.0
- NumPy: 2.5.3
- pandas: 3.0.6
- scikit-learn: 1.9.1
- LightGBM: 4.7.0
- PyTorch: 2.14.0
- PyArrow: 25.0.1
- OS: macOS 26.6.2, Darwin arm64
- Logical CPU count: 8
- CUDA available: no; CUDA devices: 0
- PyTorch MPS built: yes
- PyTorch MPS available in the current environment: no
- Neural device selected by the frozen implementation: CPU

The system `/opt/homebrew/bin/python3` is also Python 3.13.2 but does not have
the project packages installed. The active study has no requirements file or
lockfile, so the temporary virtual environment is currently the only complete
recoverable dependency record.

`package_freeze.txt` contains the unmodified output of `python -m pip freeze`.
No packages were installed, removed, or upgraded during this audit.
