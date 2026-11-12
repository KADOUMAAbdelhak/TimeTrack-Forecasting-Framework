"""Registered Spearman association with paired entity resampling."""

import numpy as np

from .bootstrap import Inference, centred_p, ordered_values, percentile_ci


def average_ranks(values):
    values = np.asarray(values, dtype=np.float64)
    n = values.shape[-1]
    order = np.argsort(values, axis=-1, kind="stable")
    sorted_values = np.take_along_axis(values, order, axis=-1)
    positions = np.arange(n)
    different = sorted_values[..., 1:] != sorted_values[..., :-1]
    edge = np.ones((*values.shape[:-1], 1), dtype=bool)
    starts = np.maximum.accumulate(np.where(np.concatenate((edge, different), axis=-1), positions, 0), axis=-1)
    last = np.where(np.concatenate((different, edge), axis=-1), positions, n - 1)
    ends = np.minimum.accumulate(last[..., ::-1], axis=-1)[..., ::-1]
    ranks = np.empty_like(values)
    np.put_along_axis(ranks, order, (starts + ends) / 2 + 1, axis=-1)
    return ranks


def spearman(left, right):
    left, right = average_ranks(left), average_ranks(right)
    left -= left.mean(axis=-1, keepdims=True)
    right -= right.mean(axis=-1, keepdims=True)
    cross = (left * right).sum(axis=-1)
    norm = np.sqrt((left * left).sum(axis=-1) * (right * right).sum(axis=-1))
    result = np.divide(cross, norm, out=np.full_like(cross, np.nan), where=norm > 0)
    return np.clip(result, -1, 1)


def correlate(bootstrap, group, K, sharing_D):
    x, y = ordered_values(group, K), ordered_values(group, sharing_D)
    if ((x < -1) | (x > 1)).any():
        raise ValueError("Final-slot M1 K must be in [-1,1]")
    point = float(spearman(x, y))
    if not np.isfinite(point):
        return Inference(None, raw_p=1., reason="constant_original")
    indices = bootstrap.indices(group)
    observed = spearman(x[indices], y[indices])
    defined = observed[np.isfinite(observed)]
    undefined = len(observed) - len(defined)
    return Inference(point, None if undefined else percentile_ci(defined),
                     centred_p(point, defined, undefined=undefined), undefined_replicates=undefined)
