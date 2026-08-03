"""Chronological splits and leakage-safe window construction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from timetrack.constants import OUTAGE_END, OUTAGE_START


@dataclass(frozen=True)
class SplitSpec:
    name: str
    train_idx: np.ndarray
    val_idx: np.ndarray
    test_idx: np.ndarray
    meta: dict[str, Any]


def _contiguous_indices(n: int, train_frac: float, val_frac: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not (0 < train_frac < 1 and 0 < val_frac < 1 and train_frac + val_frac < 1):
        raise ValueError("fractions must be positive and train+val < 1")
    n_train = int(n * train_frac)
    n_val = int(n * val_frac)
    n_test = n - n_train - n_val
    if min(n_train, n_val, n_test) < 1:
        raise ValueError(f"split too small for n={n}")
    train = np.arange(0, n_train)
    val = np.arange(n_train, n_train + n_val)
    test = np.arange(n_train + n_val, n)
    return train, val, test


def post_outage_split(
    panel: pd.DataFrame,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
) -> SplitSpec:
    """Primary track: chronological split on post-outage segment only."""
    mask = panel["segment"] == "post_outage"
    idx = np.flatnonzero(mask.to_numpy())
    if len(idx) < 100:
        raise ValueError("post-outage segment too short")
    # local contiguous positions within post-outage
    local_train, local_val, local_test = _contiguous_indices(len(idx), train_frac, val_frac)
    train_idx = idx[local_train]
    val_idx = idx[local_val]
    test_idx = idx[local_test]
    # assert chronological and non-overlapping
    assert train_idx.max() < val_idx.min()
    assert val_idx.max() < test_idx.min()
    ts = panel["timestamp"]
    meta = {
        "track": "post_outage",
        "train_frac": train_frac,
        "val_frac": val_frac,
        "n_train": int(len(train_idx)),
        "n_val": int(len(val_idx)),
        "n_test": int(len(test_idx)),
        "train_start": str(ts.iloc[train_idx[0]]),
        "train_end": str(ts.iloc[train_idx[-1]]),
        "val_start": str(ts.iloc[val_idx[0]]),
        "val_end": str(ts.iloc[val_idx[-1]]),
        "test_start": str(ts.iloc[test_idx[0]]),
        "test_end": str(ts.iloc[test_idx[-1]]),
        "outage_start": OUTAGE_START,
        "outage_end": OUTAGE_END,
    }
    return SplitSpec("post_outage", train_idx, val_idx, test_idx, meta)


def assert_no_gap_crossing(indices: np.ndarray, panel: pd.DataFrame) -> None:
    """Fail if a contiguous window index range includes both sides of the outage."""
    if len(indices) == 0:
        return
    segs = panel["segment"].iloc[indices.min() : indices.max() + 1].unique()
    if "pre_outage" in segs and "post_outage" in segs:
        raise AssertionError("window crosses outage gap")


@dataclass
class WindowDataset:
    X: np.ndarray  # (n, context, n_features) or (n, n_features) for flat
    y: np.ndarray  # (n, horizon) or (n,)
    origin_idx: np.ndarray  # index of last context timestep in panel
    target_idx: np.ndarray  # index of first target timestep
    feature_names: list[str]
    flat: bool


def build_windows(
    values: np.ndarray,
    origin_positions: np.ndarray,
    context: int,
    horizon: int,
    feature_names: list[str] | None = None,
    flat: bool = False,
    panel_for_gap_check: pd.DataFrame | None = None,
) -> WindowDataset:
    """
    Build windows where context uses positions [o-context+1, ..., o]
    and targets use [o+1, ..., o+horizon].

    origin_positions are integer positions into `values` (and panel rows).
    Windows that would require indices outside [0, n) are skipped.
    """
    values = np.asarray(values, dtype=float)
    if values.ndim == 1:
        values = values[:, None]
    n, f = values.shape
    feature_names = feature_names or [f"f{i}" for i in range(f)]
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    origins: list[int] = []
    targets: list[int] = []

    for o in origin_positions:
        o = int(o)
        start = o - context + 1
        t0 = o + 1
        t1 = o + horizon
        if start < 0 or t1 >= n:
            continue
        # refuse crossing split is caller's job; still refuse outage crossing if panel given
        if panel_for_gap_check is not None:
            try:
                assert_no_gap_crossing(np.arange(start, t1 + 1), panel_for_gap_check)
            except AssertionError:
                continue
        ctx = values[start : o + 1]
        tgt = values[t0 : t1 + 1, 0]  # forecast first column as primary target channel
        if np.isnan(ctx).any() or np.isnan(tgt).any():
            continue
        if flat:
            xs.append(ctx.reshape(-1))
        else:
            xs.append(ctx)
        ys.append(tgt)
        origins.append(o)
        targets.append(t0)

    if not xs:
        raise ValueError("no valid windows constructed")
    X = np.stack(xs, axis=0)
    y = np.stack(ys, axis=0)
    if horizon == 1:
        y = y.reshape(-1)
    return WindowDataset(
        X=X,
        y=y,
        origin_idx=np.asarray(origins, dtype=int),
        target_idx=np.asarray(targets, dtype=int),
        feature_names=feature_names if not flat else [f"{fn}_lag{c}" for c in range(context, 0, -1) for fn in feature_names],
        flat=flat,
    )


def origins_for_split(
    split_idx: np.ndarray,
    context: int,
    horizon: int,
    panel_len: int,
) -> np.ndarray:
    """
    Origins o such that full window [o-context+1, o+horizon] lies inside split_idx range
    and is contiguous in index space.
    """
    lo, hi = int(split_idx.min()), int(split_idx.max())
    # require contiguous split block
    if hi - lo + 1 != len(split_idx):
        # allow non-contiguous by checking membership
        members = set(int(i) for i in split_idx)
        origins = []
        for o in split_idx:
            o = int(o)
            start = o - context + 1
            end = o + horizon
            if start < 0 or end >= panel_len:
                continue
            if all(i in members for i in range(start, end + 1)):
                origins.append(o)
        return np.asarray(origins, dtype=int)

    first_origin = lo + context - 1
    last_origin = hi - horizon
    if first_origin > last_origin:
        return np.asarray([], dtype=int)
    return np.arange(first_origin, last_origin + 1, dtype=int)
