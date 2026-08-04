"""Block-bootstrap statistical comparisons for paired forecast errors."""

from __future__ import annotations

from typing import Any, Sequence

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


def select_block_length(
    train_residuals: np.ndarray,
    *,
    forecast_horizon: int,
    context_length: int,
    acf_threshold: float = 0.1,
    max_lag: int = 256,
    lower: int = 8,
    upper: int = 256,
) -> dict[str, Any]:
    """
    Train-derived moving-block length policy (frozen before outer inspection).

    block_length = clamp(
        max(horizon, context, first ACF lag below threshold),
        lower, upper
    )
    """
    r = np.asarray(train_residuals, dtype=float).reshape(-1)
    r = r[np.isfinite(r)]
    first_lag = int(forecast_horizon)
    if len(r) >= 8:
        r = r - np.mean(r)
        var = float(np.dot(r, r))
        if var > 0:
            max_lag = int(min(max_lag, len(r) // 2))
            acf = np.correlate(r, r, mode="full")[len(r) - 1 :] / var
            for lag in range(1, max_lag + 1):
                if abs(float(acf[lag])) < acf_threshold:
                    first_lag = lag
                    break
            else:
                first_lag = max_lag
    raw = max(int(forecast_horizon), int(context_length), int(first_lag))
    bl = int(min(upper, max(lower, raw)))
    return {
        "block_length": bl,
        "acf_first_lag_below_threshold": int(first_lag),
        "acf_threshold": float(acf_threshold),
        "lower": int(lower),
        "upper": int(upper),
        "forecast_horizon": int(forecast_horizon),
        "context_length": int(context_length),
    }


def paired_block_bootstrap_comparison(
    y_true: np.ndarray,
    y_pred_a: np.ndarray,
    y_pred_b: np.ndarray,
    *,
    block_length: int,
    n_boot: int = 1000,
    seed: int = 0,
) -> dict[str, Any]:
    """Compare methods A vs B on absolute errors; positive mean_diff ⇒ A worse."""
    yt = np.asarray(y_true, dtype=float).reshape(-1)
    ya = np.asarray(y_pred_a, dtype=float).reshape(-1)
    yb = np.asarray(y_pred_b, dtype=float).reshape(-1)
    n = min(len(yt), len(ya), len(yb))
    yt, ya, yb = yt[:n], ya[:n], yb[:n]
    ea = np.abs(yt - ya)
    eb = np.abs(yt - yb)
    d = ea - eb
    boot = block_bootstrap_mean_diff(ea, eb, block_size=block_length, n_boot=n_boot, seed=seed)
    mae_a = float(np.mean(ea))
    mae_b = float(np.mean(eb))
    # P(B better than A) ≈ fraction of bootstrap means < 0 when d = ea-eb
    rng = np.random.default_rng(seed)
    bl = max(1, min(block_length, n))
    n_blocks = int(np.ceil(n / bl))
    means = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        starts = rng.integers(0, n - bl + 1, size=n_blocks)
        sample = np.concatenate([d[s : s + bl] for s in starts])[:n]
        means[i] = float(np.mean(sample))
    p_b_improves = float(np.mean(means < 0.0))
    # two-sided p from bootstrap CI excluding 0
    ci_lo, ci_hi = boot["ci_low"], boot["ci_high"]
    if not np.isfinite(ci_lo) or not np.isfinite(ci_hi):
        p_two = float("nan")
    elif ci_lo > 0 or ci_hi < 0:
        # approximate: fraction of bootstrap means on null side of 0
        p_two = float(2.0 * min(np.mean(means >= 0), np.mean(means <= 0)))
        p_two = min(1.0, max(0.0, p_two))
    else:
        p_two = float(2.0 * min(np.mean(means >= 0), np.mean(means <= 0)))
        p_two = min(1.0, max(p_two, 0.05))  # CI includes 0 ⇒ not significant at ~5%
    return {
        **boot,
        "mae_a": mae_a,
        "mae_b": mae_b,
        "median_paired_diff": float(np.median(d)),
        "relative_mae_diff": float((mae_a - mae_b) / max(mae_a, 1e-12)),
        "prob_b_improves": p_b_improves,
        "p_value_approx": float(p_two),
        "block_length": int(block_length),
    }


def holm_adjust(p_values: Sequence[float]) -> list[float]:
    """Holm–Bonferroni adjusted p-values (same order as input)."""
    p = np.asarray(p_values, dtype=float)
    m = len(p)
    if m == 0:
        return []
    order = np.argsort(p)
    adj = np.empty(m, dtype=float)
    running = 0.0
    for rank, idx in enumerate(order):
        raw = p[idx]
        if not np.isfinite(raw):
            adj[idx] = float("nan")
            continue
        val = (m - rank) * raw
        running = max(running, val)
        adj[idx] = min(1.0, running)
    # enforce monotonicity in sorted order
    for i in range(1, m):
        j_prev, j = order[i - 1], order[i]
        if np.isfinite(adj[j]) and np.isfinite(adj[j_prev]):
            adj[j] = max(adj[j], adj[j_prev])
    return [float(x) for x in adj]


# Predefined comparison families (final protocol)
COMPARISON_FAMILIES: dict[str, list[tuple[str, str]]] = {
    "memory": [
        ("independent", "bottom_up"),
        ("independent", "wls"),
        ("independent", "mint"),
    ],
    "cpu": [
        ("independent", "bottom_up"),
        ("independent", "wls"),
        ("independent", "mint"),
    ],
    "disk": [
        ("independent", "bottom_up"),
        ("independent", "top_down"),
    ],
    "network": [
        ("independent", "selected_coherent"),
    ],
}
