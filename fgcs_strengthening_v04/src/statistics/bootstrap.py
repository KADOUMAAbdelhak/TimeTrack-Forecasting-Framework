"""Fixed, reusable entity-cluster draws and v0.3 centred tests."""

from dataclasses import dataclass

import numpy as np

from .design import GROUPS, SPEC, cohort_for
from .endpoints import exp

SEED = 20261110
REPLICATES = 10000
SIZE = 35


@dataclass(frozen=True, slots=True)
class Inference:
    point: float | None
    ci: tuple[float, float] | None = None
    raw_p: float | None = None
    ratio: float | None = None
    ratio_ci: tuple[float, float] | None = None
    undefined_replicates: int = 0
    reason: str | None = None


class Bootstrap:
    """Generate the three matrices once, in registered order, per analysis run."""

    def __init__(self):
        if (GROUPS != ("fastStorage", "Rnd", "Materna") or SPEC["bootstrap_seed"] != SEED
                or SPEC["bootstrap_replicates"] != REPLICATES or SPEC["bootstrap_draws_per_group"] != SIZE):
            raise RuntimeError("Bootstrap configuration differs from v0.3")
        generator = np.random.Generator(np.random.PCG64(SEED))
        self._draws = {}
        for group in GROUPS:
            indices = generator.integers(0, SIZE, size=(REPLICATES, SIZE), dtype=np.int64)
            # A bytes backing store prevents callers from making the draws writable.
            self._draws[group] = np.frombuffer(indices.tobytes(), dtype=np.int64).reshape(REPLICATES, SIZE)

    def indices(self, group):
        return self._draws[group]


def ordered_values(group, values):
    cohort = cohort_for(group)
    if values.keys() != set(cohort):
        raise ValueError("Bootstrap requires the complete frozen cohort")
    if any(value is None or not np.isfinite(value) for value in values.values()):
        raise ValueError("Bootstrap requires finite complete entity values")
    return np.asarray([values[entity] for entity in cohort], dtype=np.float64)


def percentile_ci(replicates):
    return tuple(float(value) for value in np.percentile(replicates, [2.5, 97.5], method="linear"))


def centred_p(point, replicates, *, undefined=0):
    values = np.asarray(replicates, dtype=np.float64)
    if not np.isfinite(point) or not np.isfinite(values).all() or undefined < 0:
        raise ValueError("Expected a finite point and finite defined replicates")
    exceed = np.count_nonzero(np.abs(values - point) >= abs(point)) + undefined
    return float((1 + exceed) / (1 + len(values) + undefined))


def mean_log(bootstrap, group, values, *, test=True):
    data = ordered_values(group, values)
    point = float(data.mean())
    replicates = data[bootstrap.indices(group)].mean(axis=1)
    ci = percentile_ci(replicates)
    return Inference(point, ci, centred_p(point, replicates) if test else None,
                     exp(point), tuple(exp(value) for value in ci))
