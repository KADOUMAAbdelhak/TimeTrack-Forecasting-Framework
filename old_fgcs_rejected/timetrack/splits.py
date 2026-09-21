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


@dataclass(frozen=True)
class FoldSpec:
    """Single chronological fold with train/val(/test) index arrays into the panel."""

    fold_id: str
    level: str  # "outer" | "inner"
    train_idx: np.ndarray
    val_idx: np.ndarray
    test_idx: np.ndarray | None
    meta: dict[str, Any]


def _post_outage_indices(panel: pd.DataFrame) -> np.ndarray:
    idx = np.flatnonzero((panel["segment"] == "post_outage").to_numpy())
    if len(idx) < 100:
        raise ValueError("post-outage segment too short")
    # must be contiguous in panel index space for standard folds
    if idx[-1] - idx[0] + 1 != len(idx):
        raise ValueError("post-outage indices are not contiguous")
    return idx


def _fold_meta(panel: pd.DataFrame, train_idx: np.ndarray, val_idx: np.ndarray, test_idx: np.ndarray | None) -> dict[str, Any]:
    ts = panel["timestamp"]

    def _span(ix: np.ndarray) -> dict[str, Any]:
        return {
            "n": int(len(ix)),
            "start": str(ts.iloc[ix[0]]),
            "end": str(ts.iloc[ix[-1]]),
            "i_min": int(ix.min()),
            "i_max": int(ix.max()),
        }

    meta = {"train": _span(train_idx), "val": _span(val_idx), "outage_start": OUTAGE_START, "outage_end": OUTAGE_END}
    if test_idx is not None and len(test_idx):
        meta["test"] = _span(test_idx)
    return meta


def assert_indices_chronological_disjoint(*blocks: np.ndarray) -> None:
    nonempty = [np.asarray(b, dtype=int) for b in blocks if b is not None and len(b)]
    for b in nonempty:
        if len(b) > 1 and np.any(np.diff(b) <= 0):
            raise AssertionError("indices not strictly increasing")
    for i, a in enumerate(nonempty):
        for b in nonempty[i + 1 :]:
            if set(a.tolist()).intersection(b.tolist()):
                raise AssertionError("index blocks overlap")
    for i in range(len(nonempty) - 1):
        if nonempty[i].max() >= nonempty[i + 1].min():
            raise AssertionError("index blocks are not chronological")


def make_outer_chronological_folds(
    panel: pd.DataFrame,
    n_folds: int = 3,
    val_frac_within_train: float = 0.15,
    min_train: int = 2000,
    min_test: int = 500,
) -> list[FoldSpec]:
    """
    Expanding-window outer folds on the post-outage segment.

    The full post-outage span is partitioned into (n_folds + 1) contiguous blocks:
    initial train seed + n_folds successive test blocks.
    Fold k uses all data before test block k as outer train span; within that span,
    the last val_frac_within_train fraction is held out as inner-style val for
    early stopping when nested HPO is not used.
    """
    if n_folds < 2:
        raise ValueError("n_folds must be >= 2")
    idx = _post_outage_indices(panel)
    n = len(idx)
    # n_folds test blocks + 1 initial train block
    n_parts = n_folds + 1
    part = n // n_parts
    if part < min_test:
        raise ValueError(f"post-outage too short for {n_folds} outer folds (part={part})")
    folds: list[FoldSpec] = []
    for k in range(n_folds):
        test_start = (k + 1) * part
        test_end = (k + 2) * part if k < n_folds - 1 else n
        train_span = idx[:test_start]
        test_idx = idx[test_start:test_end]
        if len(train_span) < min_train or len(test_idx) < min_test:
            raise ValueError(f"outer fold {k} too small: train={len(train_span)} test={len(test_idx)}")
        n_val = max(1, int(len(train_span) * val_frac_within_train))
        if n_val >= len(train_span):
            raise ValueError("val_frac_within_train too large")
        train_idx = train_span[:-n_val]
        val_idx = train_span[-n_val:]
        assert_indices_chronological_disjoint(train_idx, val_idx, test_idx)
        assert_no_gap_crossing(np.arange(train_idx.min(), test_idx.max() + 1), panel)
        fid = f"outer_{k}"
        meta = _fold_meta(panel, train_idx, val_idx, test_idx)
        meta.update(
            {
                "fold_id": fid,
                "level": "outer",
                "mode": "expanding",
                "n_folds": n_folds,
                "fold_index": k,
                "val_frac_within_train": val_frac_within_train,
            }
        )
        folds.append(FoldSpec(fid, "outer", train_idx, val_idx, test_idx, meta))
    return folds


def make_inner_rolling_folds(
    panel: pd.DataFrame,
    outer_train_idx: np.ndarray,
    n_inner: int = 3,
    mode: str = "expanding",
    val_size: int | None = None,
    val_frac: float = 0.2,
    step: int | None = None,
    min_train: int = 500,
) -> list[FoldSpec]:
    """
    Inner folds inside an outer training span (no access to outer test indices).

    mode:
      - expanding: train grows; validation is a trailing block that rolls forward
      - sliding: fixed-size train window that slides forward
    """
    if mode not in {"expanding", "sliding"}:
        raise ValueError(mode)
    span = np.asarray(outer_train_idx, dtype=int)
    if span[-1] - span[0] + 1 != len(span):
        raise ValueError("outer_train_idx must be contiguous")
    n = len(span)
    if val_size is None:
        val_size = max(1, int(n * val_frac / max(n_inner, 1)))
    if step is None:
        step = val_size
    folds: list[FoldSpec] = []
    # Place n_inner validation windows ending before span end
    for i in range(n_inner):
        val_end = n - (n_inner - 1 - i) * step
        val_start = val_end - val_size
        if val_start < min_train:
            continue
        if mode == "expanding":
            train_local = span[:val_start]
        else:
            train_start = max(0, val_start - max(min_train, val_size * 3))
            train_local = span[train_start:val_start]
        val_local = span[val_start:val_end]
        if len(train_local) < min_train or len(val_local) < 1:
            continue
        assert_indices_chronological_disjoint(train_local, val_local)
        assert_no_gap_crossing(np.arange(train_local.min(), val_local.max() + 1), panel)
        fid = f"inner_{i}"
        meta = _fold_meta(panel, train_local, val_local, None)
        meta.update(
            {
                "fold_id": fid,
                "level": "inner",
                "mode": mode,
                "n_inner": n_inner,
                "fold_index": i,
                "val_size": int(val_size),
                "step": int(step),
            }
        )
        folds.append(FoldSpec(fid, "inner", train_local, val_local, None, meta))
    if not folds:
        raise ValueError("no inner folds constructed; relax min_train/val_size")
    return folds


def nested_fold_plan(
    panel: pd.DataFrame,
    n_outer: int = 3,
    n_inner: int = 3,
    inner_mode: str = "expanding",
    val_frac_within_train: float = 0.15,
) -> list[dict[str, Any]]:
    """Return a serializable nested plan: each outer fold plus its inner folds."""
    outer = make_outer_chronological_folds(
        panel, n_folds=n_outer, val_frac_within_train=val_frac_within_train
    )
    plan = []
    for of in outer:
        # Inner folds use the full outer train∪val span (everything before outer test)
        outer_fit_span = np.concatenate([of.train_idx, of.val_idx])
        inner = make_inner_rolling_folds(panel, outer_fit_span, n_inner=n_inner, mode=inner_mode)
        # Guard: no inner index may touch outer test
        test_set = set(int(x) for x in of.test_idx)
        for inn in inner:
            if test_set.intersection(int(x) for x in inn.train_idx) or test_set.intersection(
                int(x) for x in inn.val_idx
            ):
                raise AssertionError("inner fold leaked into outer test")
        plan.append(
            {
                "outer": {
                    "fold_id": of.fold_id,
                    "meta": of.meta,
                    "n_train": len(of.train_idx),
                    "n_val": len(of.val_idx),
                    "n_test": len(of.test_idx),
                },
                "inner": [{"fold_id": i.fold_id, "meta": i.meta} for i in inner],
            }
        )
    return plan


def fold_to_split_spec(fold: FoldSpec) -> SplitSpec:
    """Adapter so existing window builders can consume a FoldSpec."""
    test = fold.test_idx if fold.test_idx is not None else fold.val_idx
    return SplitSpec(
        name=fold.fold_id,
        train_idx=fold.train_idx,
        val_idx=fold.val_idx,
        test_idx=test,
        meta=dict(fold.meta),
    )
