"""Hierarchical forecast reconciliation for TimeTrack aggregates.

Verified structures (audit):
- cluster_UM = sum_k machine0k_UM
- cluster_UD = sum_k machine0k_UD
- bond0 TX/RX ≈ sum of member NIC TX/RX (near-exact)
- cluster_mean_CU is a mean of machine CU (not a sum); optional core-weighted
  cluster CPU uses verified MACHINE_TO_HOST core counts (not mislabeled static
  totalCpuCores for m05/m07).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from timetrack.constants import MACHINE_TO_HOST

# Verified per-host core counts from detailed_cpu_cores columns (audit)
HOST_CORE_COUNTS = {
    "acamas": 36,
    "bellerophon": 48,
    "dedale": 36,
    "demophon": 36,
    "pegase": 20,  # maps to machine05 via correlation
    "perse": 36,
    "phaedra": 24,  # maps to machine07 via correlation
}

MACHINES = [f"machine0{i}" for i in range(1, 8)]


def machine_core_counts() -> dict[str, int]:
    """Core counts keyed by machine0k using correlation-based host mapping."""
    return {m: HOST_CORE_COUNTS[MACHINE_TO_HOST[m]] for m in MACHINES}


@dataclass(frozen=True)
class Hierarchy:
    name: str
    bottom_names: tuple[str, ...]
    top_name: str
    # S maps bottom vector -> top (and optionally identity bottoms). Shape (n_series, n_bottom)
    # For sum hierarchies used here: series order = bottoms + [top]
    summing_matrix: np.ndarray  # shape (n_bottom + 1, n_bottom)

    @property
    def n_bottom(self) -> int:
        return len(self.bottom_names)

    @property
    def series_names(self) -> tuple[str, ...]:
        return self.bottom_names + (self.top_name,)


def sum_hierarchy(name: str, bottom_names: list[str], top_name: str) -> Hierarchy:
    b = len(bottom_names)
    # rows: bottoms (identity) then top = 1' bottoms
    S = np.vstack([np.eye(b), np.ones((1, b))])
    return Hierarchy(name, tuple(bottom_names), top_name, S.astype(float))


def memory_hierarchy() -> Hierarchy:
    return sum_hierarchy("memory_um", [f"{m}_UM" for m in MACHINES], "cluster_UM")


def disk_hierarchy() -> Hierarchy:
    return sum_hierarchy("disk_ud", [f"{m}_UD" for m in MACHINES], "cluster_UD")


def core_weighted_cpu_hierarchy() -> Hierarchy:
    """
    Top series is core-weighted mean of machine CU:
        top = sum_k (c_k * CU_k) / sum_k c_k
    Represent as sum hierarchy on scaled bottoms z_k = c_k * CU_k with top = sum z,
    then convert predictions back when needed. For reconciliation on CU levels,
    we reconcile the weighted contributions.
    """
    bottoms = [f"{m}_CU_wcontrib" for m in MACHINES]
    return sum_hierarchy("cpu_core_weighted", bottoms, "cluster_CU_wsum")


def coherence_error(y_bottom: np.ndarray, y_top: np.ndarray, tol: float = 0.0) -> float:
    """Mean absolute |top - sum(bottom)|."""
    y_bottom = np.asarray(y_bottom, dtype=float)
    y_top = np.asarray(y_top, dtype=float).reshape(-1)
    if y_bottom.ndim == 1:
        y_bottom = y_bottom.reshape(1, -1)
    s = y_bottom.sum(axis=1)
    return float(np.mean(np.abs(s - y_top)))


def is_coherent(y_bottom: np.ndarray, y_top: np.ndarray, atol: float = 1e-6, rtol: float = 1e-8) -> bool:
    y_bottom = np.asarray(y_bottom, dtype=float)
    y_top = np.asarray(y_top, dtype=float).reshape(-1)
    if y_bottom.ndim == 1:
        y_bottom = y_bottom.reshape(1, -1)
    s = y_bottom.sum(axis=1)
    return bool(np.allclose(s, y_top, atol=atol, rtol=rtol))


def bottom_up(y_bottom: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (bottom, top=sum)."""
    y_bottom = np.asarray(y_bottom, dtype=float)
    if y_bottom.ndim == 1:
        y_bottom = y_bottom.reshape(1, -1)
    top = y_bottom.sum(axis=1)
    return y_bottom, top


def top_down_proportional(y_bottom_base: np.ndarray, y_top: np.ndarray, eps: float = 1e-12) -> tuple[np.ndarray, np.ndarray]:
    """Allocate top to bottoms using proportions of base bottom forecasts."""
    base = np.asarray(y_bottom_base, dtype=float)
    y_top = np.asarray(y_top, dtype=float).reshape(-1)
    if base.ndim == 1:
        base = base.reshape(1, -1)
    weights = base / (base.sum(axis=1, keepdims=True) + eps)
    bottom = weights * y_top.reshape(-1, 1)
    return bottom, y_top


def ols_reconcile(hierarchy: Hierarchy, yhat: np.ndarray) -> np.ndarray:
    """
    OLS reconciliation: tilde{y} = S (S'S)^{-1} S' yhat
    yhat ordered as hierarchy.series_names (bottoms then top), shape (n, n_series)
    """
    S = hierarchy.summing_matrix
    yhat = np.asarray(yhat, dtype=float)
    single = yhat.ndim == 1
    if single:
        yhat = yhat.reshape(1, -1)
    G = np.linalg.pinv(S.T @ S) @ S.T  # (n_bottom, n_series)
    yb = (G @ yhat.T).T  # (n, n_bottom)
    y_rec = (S @ yb.T).T
    return y_rec.reshape(-1) if single else y_rec


def wls_reconcile(hierarchy: Hierarchy, yhat: np.ndarray, series_var: np.ndarray) -> np.ndarray:
    """
    WLS with diagonal weights W = diag(series_var).
    tilde{y} = S (S' W^{-1} S)^{-1} S' W^{-1} yhat
    """
    S = hierarchy.summing_matrix
    yhat = np.asarray(yhat, dtype=float)
    series_var = np.asarray(series_var, dtype=float).reshape(-1)
    single = yhat.ndim == 1
    if single:
        yhat = yhat.reshape(1, -1)
    w_inv = 1.0 / np.maximum(series_var, 1e-12)
    Winv = np.diag(w_inv)
    StW = S.T @ Winv
    G = np.linalg.pinv(StW @ S) @ StW
    yb = (G @ yhat.T).T
    y_rec = (S @ yb.T).T
    return y_rec.reshape(-1) if single else y_rec


def mint_shrink_reconcile(
    hierarchy: Hierarchy,
    yhat: np.ndarray,
    residual_cov: np.ndarray,
    shrink: float = 0.1,
) -> np.ndarray:
    """
    MinT-style shrinkage: use residual covariance shrunk toward diagonal.
    residual_cov shape (n_series, n_series).
    """
    S = hierarchy.summing_matrix
    yhat = np.asarray(yhat, dtype=float)
    W = np.asarray(residual_cov, dtype=float)
    d = np.diag(np.diag(W))
    W_s = (1.0 - shrink) * W + shrink * d
    # stabilize
    W_s = W_s + 1e-8 * np.eye(W_s.shape[0])
    single = yhat.ndim == 1
    if single:
        yhat = yhat.reshape(1, -1)
    Winv = np.linalg.pinv(W_s)
    StW = S.T @ Winv
    G = np.linalg.pinv(StW @ S) @ StW
    yb = (G @ yhat.T).T
    y_rec = (S @ yb.T).T
    return y_rec.reshape(-1) if single else y_rec


def nonnegative_project_bottom(y_bottom: np.ndarray) -> np.ndarray:
    return np.maximum(np.asarray(y_bottom, dtype=float), 0.0)


def reconcile(
    method: str,
    hierarchy: Hierarchy,
    yhat_bottom: np.ndarray,
    yhat_top: np.ndarray,
    *,
    series_var: np.ndarray | None = None,
    residual_cov: np.ndarray | None = None,
    nonnegative: bool = False,
) -> dict[str, Any]:
    """
    Reconcile bottom and top forecasts.

    Returns dict with bottom, top, full (bottoms+top), method, coherence_error.
    """
    yb = np.asarray(yhat_bottom, dtype=float)
    yt = np.asarray(yhat_top, dtype=float).reshape(-1)
    if yb.ndim == 1:
        yb = yb.reshape(1, -1)
    if yb.shape[0] != yt.shape[0]:
        raise ValueError("batch mismatch between bottom and top forecasts")
    if yb.shape[1] != hierarchy.n_bottom:
        raise ValueError("bottom width does not match hierarchy")

    method = method.lower()
    if method == "none" or method == "independent":
        bottom, top = yb, yt
    elif method == "bottom_up":
        bottom, top = bottom_up(yb)
    elif method == "top_down":
        bottom, top = top_down_proportional(yb, yt)
    elif method in {"ols", "wls", "mint"}:
        full = np.concatenate([yb, yt.reshape(-1, 1)], axis=1)
        if method == "ols":
            rec = ols_reconcile(hierarchy, full)
        elif method == "wls":
            if series_var is None:
                series_var = np.ones(hierarchy.n_bottom + 1)
            rec = wls_reconcile(hierarchy, full, series_var)
        else:
            if residual_cov is None:
                residual_cov = np.eye(hierarchy.n_bottom + 1)
            rec = mint_shrink_reconcile(hierarchy, full, residual_cov)
        bottom, top = rec[:, :-1], rec[:, -1]
    else:
        raise ValueError(f"unknown reconciliation method: {method}")

    if nonnegative:
        bottom = nonnegative_project_bottom(bottom)
        # re-close hierarchy after projection via bottom-up for sum hierarchies
        bottom, top = bottom_up(bottom)

    err = coherence_error(bottom, top)
    full = np.concatenate([bottom, top.reshape(-1, 1)], axis=1)
    return {
        "method": method,
        "bottom": bottom,
        "top": top,
        "full": full,
        "coherence_error": err,
        "hierarchy": hierarchy.name,
    }
