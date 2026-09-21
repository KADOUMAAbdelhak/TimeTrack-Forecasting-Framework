from __future__ import annotations

import pytest

from benchmark.src.data import load_canonical_panel, load_registry


@pytest.fixture(scope="session")
def panel():
    return load_canonical_panel()


@pytest.fixture(scope="session")
def registry():
    return load_registry()
