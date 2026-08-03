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

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from timetrack.constants import HOST_TO_MACHINE, MACHINE_TO_HOST

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

# Raw compute_dataset totalCpuCoresmachine0k labels (provenance; DO NOT use for aggregation)
RAW_CONFLICTING_CORE_LABELS = {
    "machine01": 36,
    "machine02": 48,
    "machine03": 36,
    "machine04": 36,
    "machine05": 24,  # conflicts with pegase=20
    "machine06": 36,
    "machine07": 20,  # conflicts with phaedra=24
}

MACHINES = [f"machine0{i}" for i in range(1, 8)]

# Member NIC suffixes used when bond0≈sum (from audit)
BOND_MEMBER_IFACES = {
    "acamas": ["eno1", "eno2np1", "ens3f0np0", "ens3f1np1"],
    "bellerophon": ["eno1", "eno2", "ens1f0np0", "ens1f1np1", "ens3f0", "ens3f1"],
    "dedale": ["eno1", "eno2", "eno3", "eno4", "ens3f0np0", "ens3f1np1"],
    "demophon": ["eno1np0", "eno2", "ens3f0np0", "ens3f1np1"],
    "pegase": ["eno1", "eno2", "ens1f0np0", "ens1f1np1", "ens3f0", "ens3f1"],
    "perse": ["eno1", "eno2", "eno3", "eno4", "ens3f0np0", "ens3f1np1"],
    "phaedra": ["eno1", "eno2", "ens1f0np0", "ens1f1np1", "ens3f0", "ens3f1"],
}


def machine_core_counts() -> dict[str, int]:
    """Core counts keyed by machine0k using correlation-based host mapping."""
    return {m: HOST_CORE_COUNTS[MACHINE_TO_HOST[m]] for m in MACHINES}


def assert_not_using_raw_conflicting_labels(cores: dict[str, int]) -> None:
    """Fail if aggregation cores match the known-swapped raw labels for m05/m07."""
    if cores.get("machine05") == RAW_CONFLICTING_CORE_LABELS["machine05"] and cores.get(
        "machine07"
    ) == RAW_CONFLICTING_CORE_LABELS["machine07"]:
        # Both match raw labels ⇒ likely using swapped compute_dataset fields
        if cores["machine05"] != HOST_CORE_COUNTS["pegase"] or cores["machine07"] != HOST_CORE_COUNTS["phaedra"]:
            raise AssertionError(
                "Aggregation appears to use swapped raw totalCpuCores labels for machine05/07. "
                "Use machine_core_counts() / HOST_CORE_COUNTS via MACHINE_TO_HOST."
            )


@dataclass(frozen=True)
class Hierarchy:
    name: str
    bottom_names: tuple[str, ...]
    top_name: str
    # S maps bottom vector b -> full series y = S @ b (bottoms then top)
    summing_matrix: np.ndarray  # shape (n_bottom + 1, n_bottom)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def n_bottom(self) -> int:
        return len(self.bottom_names)

    @property
    def n_series(self) -> int:
        return self.n_bottom + 1

    @property
    def series_names(self) -> tuple[str, ...]:
        return self.bottom_names + (self.top_name,)

    def project(self, bottom: np.ndarray) -> np.ndarray:
        """Return y = S @ b with shape (n, n_series)."""
        b = np.asarray(bottom, dtype=float)
        if b.ndim == 1:
            b = b.reshape(1, -1)
        if b.shape[1] != self.n_bottom:
            raise ValueError(f"bottom width {b.shape[1]} != {self.n_bottom}")
        return (self.summing_matrix @ b.T).T


def sum_hierarchy(
    name: str,
    bottom_names: list[str],
    top_name: str,
    meta: dict[str, Any] | None = None,
) -> Hierarchy:
    b = len(bottom_names)
    S = np.vstack([np.eye(b), np.ones((1, b))])
    return Hierarchy(name, tuple(bottom_names), top_name, S.astype(float), meta or {})


def memory_hierarchy() -> Hierarchy:
    return sum_hierarchy(
        "memory_um",
        [f"{m}_UM" for m in MACHINES],
        "cluster_UM",
        meta={"relation": "exact_sum", "source": "audit"},
    )


def disk_hierarchy() -> Hierarchy:
    return sum_hierarchy(
        "disk_ud",
        [f"{m}_UD" for m in MACHINES],
        "cluster_UD",
        meta={"relation": "exact_sum", "source": "audit"},
    )


def core_weighted_cpu_hierarchy() -> Hierarchy:
    """
    Reconcile on weighted contributions z_k = c_k * CU_k with top = sum z.
    Convert to weighted-mean CU via top / sum(c) after reconciliation.
    """
    cores = machine_core_counts()
    assert_not_using_raw_conflicting_labels(cores)
    bottoms = [f"{m}_CU_wcontrib" for m in MACHINES]
    return sum_hierarchy(
        "cpu_core_weighted",
        bottoms,
        "cluster_CU_wsum",
        meta={
            "relation": "sum_of_core_weighted_cu",
            "core_counts": cores,
            "raw_conflicting_labels": dict(RAW_CONFLICTING_CORE_LABELS),
            "machine_to_host": dict(MACHINE_TO_HOST),
            "weighted_mean_divisor": float(sum(cores.values())),
        },
    )


def bond0_hierarchy(host: str, direction: str = "transmitted") -> Hierarchy:
    """Approximate sum hierarchy: member NIC throughputs -> bond0."""
    if host not in BOND_MEMBER_IFACES:
        raise KeyError(host)
    if direction not in {"transmitted", "received"}:
        raise ValueError(direction)
    members = BOND_MEMBER_IFACES[host]
    bottoms = [f"{direction}_throughput_{host}:-network-device-{iface}" for iface in members]
    top = f"{direction}_throughput_{host}:-network-device-bond0"
    return sum_hierarchy(
        f"bond0_{direction}_{host}",
        bottoms,
        top,
        meta={"relation": "approximate_sum", "host": host, "direction": direction, "tolerance_note": "audit r~1"},
    )


def coherence_error(y_bottom: np.ndarray, y_top: np.ndarray) -> float:
    """Mean absolute |top - sum(bottom)| for sum hierarchies."""
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


def verify_summing_identity(hierarchy: Hierarchy, bottom: np.ndarray, full: np.ndarray, atol: float = 1e-6) -> bool:
    """Check full ≈ S @ bottom."""
    projected = hierarchy.project(bottom)
    full = np.asarray(full, dtype=float)
    if full.ndim == 1:
        full = full.reshape(1, -1)
    return bool(np.allclose(projected, full, atol=atol, rtol=1e-8))


def bottom_up(y_bottom: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    y_bottom = np.asarray(y_bottom, dtype=float)
    if y_bottom.ndim == 1:
        y_bottom = y_bottom.reshape(1, -1)
    top = y_bottom.sum(axis=1)
    return y_bottom, top


def top_down_proportional(
    y_bottom_base: np.ndarray, y_top: np.ndarray, eps: float = 1e-12
) -> tuple[np.ndarray, np.ndarray]:
    base = np.asarray(y_bottom_base, dtype=float)
    y_top = np.asarray(y_top, dtype=float).reshape(-1)
    if base.ndim == 1:
        base = base.reshape(1, -1)
    weights = base / (base.sum(axis=1, keepdims=True) + eps)
    bottom = weights * y_top.reshape(-1, 1)
    return bottom, y_top


def _as_batch(yhat: np.ndarray) -> tuple[np.ndarray, bool]:
    yhat = np.asarray(yhat, dtype=float)
    single = yhat.ndim == 1
    if single:
        yhat = yhat.reshape(1, -1)
    return yhat, single


def ols_reconcile(hierarchy: Hierarchy, yhat: np.ndarray) -> np.ndarray:
    """tilde y = S (S'S)^+ S' yhat."""
    S = hierarchy.summing_matrix
    yhat, single = _as_batch(yhat)
    if yhat.shape[1] != hierarchy.n_series:
        raise ValueError(f"yhat width {yhat.shape[1]} != n_series {hierarchy.n_series}")
    G = np.linalg.pinv(S.T @ S) @ S.T
    yb = (G @ yhat.T).T
    y_rec = hierarchy.project(yb)
    return y_rec.reshape(-1) if single else y_rec


def wls_reconcile(hierarchy: Hierarchy, yhat: np.ndarray, series_var: np.ndarray) -> np.ndarray:
    S = hierarchy.summing_matrix
    yhat, single = _as_batch(yhat)
    series_var = np.asarray(series_var, dtype=float).reshape(-1)
    if series_var.shape[0] != hierarchy.n_series:
        raise ValueError("series_var length mismatch")
    if yhat.shape[1] != hierarchy.n_series:
        raise ValueError("yhat width mismatch")
    w_inv = 1.0 / np.maximum(series_var, 1e-12)
    Winv = np.diag(w_inv)
    StW = S.T @ Winv
    G = np.linalg.pinv(StW @ S) @ StW
    yb = (G @ yhat.T).T
    y_rec = hierarchy.project(yb)
    return y_rec.reshape(-1) if single else y_rec


def mint_shrink_reconcile(
    hierarchy: Hierarchy,
    yhat: np.ndarray,
    residual_cov: np.ndarray,
    shrink: float = 0.1,
) -> np.ndarray:
    S = hierarchy.summing_matrix
    yhat, single = _as_batch(yhat)
    W = np.asarray(residual_cov, dtype=float)
    if W.shape != (hierarchy.n_series, hierarchy.n_series):
        raise ValueError(f"residual_cov shape {W.shape} invalid")
    # Handle singular / near-singular by shrinkage + ridge
    d = np.diag(np.maximum(np.diag(W), 1e-12))
    W_s = (1.0 - shrink) * W + shrink * d
    # If still ill-conditioned, add ridge
    try:
        cond = np.linalg.cond(W_s)
    except np.linalg.LinAlgError:
        cond = np.inf
    if not np.isfinite(cond) or cond > 1e12:
        W_s = W_s + 1e-6 * np.eye(W_s.shape[0])
    else:
        W_s = W_s + 1e-8 * np.eye(W_s.shape[0])
    Winv = np.linalg.pinv(W_s)
    StW = S.T @ Winv
    G = np.linalg.pinv(StW @ S) @ StW
    yb = (G @ yhat.T).T
    y_rec = hierarchy.project(yb)
    return y_rec.reshape(-1) if single else y_rec


def estimate_residual_covariance(
    y_true_full: np.ndarray,
    y_pred_full: np.ndarray,
    shrink_diag: float = 0.0,
) -> np.ndarray:
    """
    Estimate residual covariance from train/inner residuals ONLY.
    Caller must guarantee rows are not from outer evaluation.
    """
    yt = np.asarray(y_true_full, dtype=float)
    yp = np.asarray(y_pred_full, dtype=float)
    if yt.ndim == 1:
        yt = yt.reshape(1, -1)
        yp = yp.reshape(1, -1)
    if yt.shape != yp.shape:
        raise ValueError("true/pred shape mismatch")
    resid = yt - yp
    if resid.shape[0] < 2:
        return np.eye(resid.shape[1])
    cov = np.cov(resid, rowvar=False)
    if shrink_diag > 0:
        d = np.diag(np.diag(cov))
        cov = (1 - shrink_diag) * cov + shrink_diag * d
    # NaN/Inf guard
    if not np.isfinite(cov).all():
        cov = np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0)
        cov = cov + np.eye(cov.shape[0])
    return cov


def mask_missing_children(
    y_bottom: np.ndarray,
    missing_mask: np.ndarray,
    fill: float = 0.0,
) -> np.ndarray:
    """
    missing_mask True where child is unavailable.
    Fills missing with `fill` and returns copy. Caller should document exclusions.
    """
    y = np.asarray(y_bottom, dtype=float).copy()
    m = np.asarray(missing_mask, dtype=bool)
    if y.ndim == 1:
        y = y.reshape(1, -1)
        m = m.reshape(1, -1)
    if y.shape != m.shape:
        raise ValueError("mask shape mismatch")
    y[m] = fill
    return y


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
    missing_mask: np.ndarray | None = None,
) -> dict[str, Any]:
    yb = np.asarray(yhat_bottom, dtype=float)
    yt = np.asarray(yhat_top, dtype=float).reshape(-1)
    if yb.ndim == 1:
        yb = yb.reshape(1, -1)
    if yb.shape[0] != yt.shape[0]:
        raise ValueError("batch mismatch between bottom and top forecasts")
    if yb.shape[1] != hierarchy.n_bottom:
        raise ValueError("bottom width does not match hierarchy")
    if missing_mask is not None:
        yb = mask_missing_children(yb, missing_mask, fill=0.0)

    method = method.lower()
    if method in {"none", "independent"}:
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
                series_var = np.ones(hierarchy.n_series)
            rec = wls_reconcile(hierarchy, full, series_var)
        else:
            if residual_cov is None:
                residual_cov = np.eye(hierarchy.n_series)
            rec = mint_shrink_reconcile(hierarchy, full, residual_cov)
        bottom, top = rec[:, :-1], rec[:, -1]
    else:
        raise ValueError(f"unknown reconciliation method: {method}")

    if nonnegative:
        bottom = nonnegative_project_bottom(bottom)
        bottom, top = bottom_up(bottom)

    full = np.concatenate([bottom, top.reshape(-1, 1)], axis=1)
    # For reconciled methods (not independent), enforce S@b identity
    if method not in {"none", "independent"}:
        if not verify_summing_identity(hierarchy, bottom, full, atol=1e-4 * (1 + np.mean(np.abs(full)))):
            # numerical repair via projection of bottoms
            full = hierarchy.project(bottom)
            bottom, top = full[:, :-1], full[:, -1]

    return {
        "method": method,
        "bottom": bottom,
        "top": top,
        "full": full,
        "coherence_error": coherence_error(bottom, top),
        "hierarchy": hierarchy.name,
        "summing_ok": verify_summing_identity(hierarchy, bottom, full, atol=1e-3 * (1 + np.mean(np.abs(full)))),
    }


def cu_to_weighted_contrib(cu: np.ndarray, cores: dict[str, int] | None = None) -> np.ndarray:
    """Convert machine CU matrix (n, 7) to core-weighted contributions."""
    cores = cores or machine_core_counts()
    assert_not_using_raw_conflicting_labels(cores)
    cu = np.asarray(cu, dtype=float)
    if cu.ndim == 1:
        cu = cu.reshape(1, -1)
    w = np.array([cores[m] for m in MACHINES], dtype=float)
    return cu * w.reshape(1, -1)


def weighted_contrib_to_mean_cu(top_wsum: np.ndarray, cores: dict[str, int] | None = None) -> np.ndarray:
    cores = cores or machine_core_counts()
    div = float(sum(cores.values()))
    return np.asarray(top_wsum, dtype=float) / div
