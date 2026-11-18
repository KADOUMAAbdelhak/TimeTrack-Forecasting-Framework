"""Generated native-MAE rows for the v0.4 analysis tests. No study data are read."""

from itertools import product

import numpy as np

from fgcs_strengthening_v04a1.src.analysis.grid import BLOCKS, COHORT, FOLDS, HORIZONS, SEEDS, MAERow, all_cells, \
    cell_targets
from fgcs_strengthening_v04a1.src.identity import RESOURCES


def synthetic_rows(factors=None, *, failed=(), seed=3, cells=None):
    """Rows for every coordinate: MAE = factor(backbone, cell) x (1 + horizon/10) x small noise.

    failed: (backbone, cell, block, entity, resource, fold, seed) units recorded as failed.
    """
    factors = factors or {}
    failed = set(failed)
    generator = np.random.default_rng(seed)
    rows = []
    for backbone, cell in all_cells() if cells is None else cells:
        factor = factors.get((backbone, cell), 1.)
        for block in BLOCKS:
            for entity, resource, fold, s in product(COHORT[block], cell_targets(backbone, cell), FOLDS, SEEDS):
                unit_failed = (backbone, cell, block, entity, resource, fold, s) in failed
                for horizon in HORIZONS[block]:
                    if unit_failed:
                        rows.append(MAERow(backbone, cell, block, entity, resource, fold, horizon, s, None, "failed"))
                    else:
                        noise = 1 + 0.01 * generator.normal()
                        rows.append(MAERow(backbone, cell, block, entity, resource, fold, horizon, s,
                                           float(factor * (1 + horizon / 10) * noise)))
    return rows


def persistence(value=2.):
    return {block: np.full((len(COHORT[block]), len(RESOURCES), len(FOLDS), len(HORIZONS[block])), value)
            for block in BLOCKS}
