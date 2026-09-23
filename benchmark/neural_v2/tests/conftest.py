from __future__ import annotations

import pytest

from benchmark.neural_v2.src.data import load_canonical_panel


@pytest.fixture(scope="session")
def panel():
    return load_canonical_panel()
