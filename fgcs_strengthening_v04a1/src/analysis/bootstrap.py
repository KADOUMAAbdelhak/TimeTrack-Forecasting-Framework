"""Paired VM-cluster bootstrap (P4) and the Spearman statistic (D-3).

One draw matrix per block, generated once in configured block order from seed 20261007, is reused
for every statistic of that block, so all intervals within a block share the same resamples.
"""

import math

import numpy as np

from .grid import BLOCKS, COHORT

SEED = 20261007
REPLICATES = 10000


class Draws:
    def __init__(self, *, seed=SEED, replicates=REPLICATES):
        generator = np.random.Generator(np.random.PCG64(seed))
        self._indices = {}
        for block in BLOCKS:
            size = len(COHORT[block])
            drawn = generator.integers(0, size, size=(replicates, size), dtype=np.int64)
            self._indices[block] = np.frombuffer(drawn.tobytes(), dtype=np.int64).reshape(replicates, size)

    def indices(self, block):
        return self._indices[block]


def percentile_interval(replicates):
    """Percentile 95 % interval over defined replicates, with the count of undefined ones."""
    values = np.asarray(replicates, dtype=np.float64)
    defined = values[np.isfinite(values)]
    undefined = int(len(values) - len(defined))
    if not len(defined):
        return None, undefined
    low, high = np.percentile(defined, [2.5, 97.5], method="linear")
    return [float(low), float(high)], undefined


def gain_interval(draws, block, candidate, reference):
    """Resample VMs of seed-averaged [entity, fold, horizon] arrays (paired) and recompute G(C:B)."""
    indices = draws.indices(block)

    def replicate_macro(values):
        present = ~np.isnan(values)
        sums = np.where(present, values, 0.).sum(axis=1)[indices].sum(axis=1)
        counts = present.sum(axis=1)[indices].sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            per_horizon = np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)
        return per_horizon.mean(axis=1)

    c, b = replicate_macro(candidate), replicate_macro(reference)
    with np.errstate(invalid="ignore", divide="ignore"):
        gains = np.where(b != 0, 100. * (b - c) / b, np.nan)
    return percentile_interval(gains)


def mean_interval(draws, block, values):
    """Resample VMs of an entity-level statistic and recompute its mean over defined entities."""
    values = np.asarray(values, dtype=np.float64)
    drawn = values[draws.indices(block)]
    present = np.isfinite(drawn)
    counts = present.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        means = np.where(counts > 0, np.where(present, drawn, 0.).sum(axis=1) / np.maximum(counts, 1), np.nan)
    return percentile_interval(means)


def average_ranks(values):
    values = np.asarray(values, dtype=np.float64)
    n = values.shape[-1]
    order = np.argsort(values, axis=-1, kind="stable")
    ordered = np.take_along_axis(values, order, axis=-1)
    positions = np.arange(n)
    different = ordered[..., 1:] != ordered[..., :-1]
    edge = np.ones((*values.shape[:-1], 1), dtype=bool)
    starts = np.maximum.accumulate(np.where(np.concatenate((edge, different), axis=-1), positions, 0), axis=-1)
    last = np.where(np.concatenate((different, edge), axis=-1), positions, n - 1)
    ends = np.minimum.accumulate(last[..., ::-1], axis=-1)[..., ::-1]
    ranks = np.empty_like(values)
    np.put_along_axis(ranks, order, (starts + ends) / 2 + 1, axis=-1)
    return ranks


def spearman(left, right):
    """Spearman rho along the last axis (average ranks for ties); NaN when either side is constant."""
    left, right = average_ranks(left), average_ranks(right)
    left -= left.mean(axis=-1, keepdims=True)
    right -= right.mean(axis=-1, keepdims=True)
    cross = (left * right).sum(axis=-1)
    norm = np.sqrt((left * left).sum(axis=-1) * (right * right).sum(axis=-1))
    return np.clip(np.divide(cross, norm, out=np.full_like(cross, np.nan), where=norm > 0), -1, 1)


def spearman_interval(draws, block, x, y):
    """D-3: rho over entities where both values exist, with a paired VM-cluster bootstrap interval."""
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    both = np.isfinite(x) & np.isfinite(y)
    n = int(both.sum())
    if n < 3:
        return {"rho": None, "interval": None, "undefined_replicates": None, "entities": n}
    point = float(spearman(x[both], y[both]))
    indices = draws.indices(block)
    if both.all():
        replicates = spearman(x[indices], y[indices])
    else:
        # Entities lacking either value drop out of each replicate, as from the point estimate.
        replicates = np.array([spearman(x[row][both[row]], y[row][both[row]]) if both[row].sum() >= 3 else np.nan
                               for row in indices])
    interval, undefined = percentile_interval(replicates)
    return {"rho": None if math.isnan(point) else point, "interval": interval,
            "undefined_replicates": undefined, "entities": n}
