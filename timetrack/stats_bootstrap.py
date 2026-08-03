"""Block-bootstrap statistical comparisons for paired forecast errors."""

from __future__ import annotations

from typing import Any

import numpy as np


def block_bootstrap_mean_diff(
    err_a: np.ndarray,
    err_b: np.ndarray,
    *,
    block_size: int = 48,
    n_boot: int = 1000,
    seed: int = 0,
) -> dict[str, Any]:
    """
    Paired block bootstrap of mean(err_a - err_b).
    Positive mean_diff ⇒ A worse than B (higher absolute error).
    """
    a = np.asarray(err_a, dtype=float).reshape(-1)
    b = np.asarray(err_b, dtype=float).reshape(-1)
    if a.shape != b.shape:
        raise ValueError("paired errors must match")
    d = a - b
    n = len(d)
    if n == 0:
        return {"mean_diff": float("nan"), "ci_low": float("nan"), "ci_high": float("nan"), "n": 0}
    rng = np.random.default_rng(seed)
    block_size = max(1, min(block_size, n))
    n_blocks = int(np.ceil(n / block_size))
    means = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        starts = rng.integers(0, n - block_size + 1, size=n_blocks)
        sample = np.concatenate([d[s : s + block_size] for s in starts])[:n]
        means[i] = float(np.mean(sample))
    return {
        "mean_diff": float(np.mean(d)),
        "ci_low": float(np.quantile(means, 0.025)),
        "ci_high": float(np.quantile(means, 0.975)),
        "n": n,
        "block_size": block_size,
        "n_boot": n_boot,
    }
