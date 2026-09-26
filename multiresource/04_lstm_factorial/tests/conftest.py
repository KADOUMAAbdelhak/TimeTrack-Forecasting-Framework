from __future__ import annotations

import sys
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]
for path in (str(BASE), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture(scope="session")
def panel():
    from src.data import load_panel
    return load_panel()


@pytest.fixture(scope="session")
def machine01_folds(panel):
    from src.splits import build_factorial_folds
    return {length: build_factorial_folds(panel, "machine01", length) for length in (32, 64, 128)}
