"""Native-MAE grids, seed averaging and the P4 missing-fit rule.

Every coordinate of the design must arrive as an explicit row: a finite MAE ("ok") or a recorded
"failed" or "missing" status. A non-ok row marks its block x entity x fold x resource x seed unit
missing. P4 then makes that unit missing for every cell of the backbone, so contrasts stay paired.
"""

from dataclasses import dataclass
from itertools import combinations
import math

import numpy as np

from ..identity import RESOURCES, canonical_tasks, read_config

_CONFIG = read_config()
BLOCKS = tuple(_CONFIG["cohort"])
COHORT = {block: tuple(entities) for block, entities in _CONFIG["cohort"].items()}
FOLDS = tuple(_CONFIG["folds"])
SEEDS = tuple(_CONFIG["core_seeds"])
HORIZONS = {block: tuple(_CONFIG["blocks"][block]["horizons"]) for block in BLOCKS}
CELLS = ("S1", "S2", "M0", "M1")
BACKBONES = ("LSTM", "DLinear", "PatchTST", "iTransformer")
DEFINED = {"LSTM": CELLS, "DLinear": CELLS, "PatchTST": CELLS, "iTransformer": ("S2", "M1")}
STATUSES = ("ok", "failed", "missing")


def lattice_cell(tasks):
    """The D-5 all-input subset model's cell label, e.g. M1/CPU+MEMORY."""
    return "M1/" + "+".join(canonical_tasks(tasks))


PAIRWISE = tuple(lattice_cell(pair) for pair in combinations(RESOURCES, 2))
LEAVE_ONE_OUT = tuple(lattice_cell(task for task in RESOURCES if task != omitted) for omitted in RESOURCES)
LATTICE = PAIRWISE + LEAVE_ONE_OUT


def cell_targets(backbone, cell):
    """Resources a cell predicts; raises for an undefined backbone x cell."""
    if backbone in DEFINED and cell in DEFINED[backbone]:
        return RESOURCES
    if backbone == "LSTM" and cell in LATTICE:
        return tuple(cell.split("/", 1)[1].split("+"))
    raise ValueError(f"Undefined cell {backbone}/{cell}")


def all_cells():
    for backbone in BACKBONES:
        yield from ((backbone, cell) for cell in DEFINED[backbone])
    yield from (("LSTM", cell) for cell in LATTICE)


@dataclass(frozen=True, slots=True)
class MAERow:
    backbone: str
    cell: str
    block: str
    entity: str
    resource: str
    fold: int
    horizon: int
    seed: int
    mae: float | None
    status: str = "ok"

    def __post_init__(self):
        if (self.block not in BLOCKS or self.entity not in COHORT[self.block]
                or self.resource not in cell_targets(self.backbone, self.cell)
                or type(self.fold) is not int or self.fold not in FOLDS
                or type(self.horizon) is not int or self.horizon not in HORIZONS[self.block]
                or type(self.seed) is not int or self.seed not in SEEDS or self.status not in STATUSES):
            raise ValueError(f"Row outside the v0.4 grid: {self}")
        if self.status == "ok":
            if type(self.mae) not in (float, int) or not math.isfinite(self.mae) or self.mae < 0:
                raise ValueError("An ok row needs a finite nonnegative native MAE")
        elif self.mae is not None:
            raise ValueError("A failed or missing row carries no MAE")

    @property
    def coordinate(self):
        return (self.backbone, self.cell, self.block, self.entity, self.resource,
                self.fold, self.horizon, self.seed)


def _shape(block):
    return len(COHORT[block]), len(RESOURCES), len(FOLDS), len(HORIZONS[block]), len(SEEDS)


class Grid:
    """Values [entity, resource, fold, horizon, seed] per backbone x cell x block, NaN where unusable."""

    def __init__(self, rows, *, cells=None):
        self.cells = tuple(all_cells()) if cells is None else tuple(cells)
        self.values = {(b, c, block): np.full(_shape(block), np.nan) for b, c in self.cells for block in BLOCKS}
        self.failed = {key: np.zeros(array.shape[:3] + array.shape[4:], dtype=bool)
                       for key, array in self.values.items()}
        seen = set()
        for row in rows:
            key = row.backbone, row.cell, row.block
            if key not in self.values:
                raise ValueError(f"Row for an unrequested cell: {row}")
            if row.coordinate in seen:
                raise ValueError(f"Duplicate native-MAE row: {row.coordinate}")
            seen.add(row.coordinate)
            index = (COHORT[row.block].index(row.entity), RESOURCES.index(row.resource),
                     FOLDS.index(row.fold), HORIZONS[row.block].index(row.horizon), SEEDS.index(row.seed))
            if row.status == "ok":
                self.values[key][index] = row.mae
            else:
                self.failed[key][index[:3] + index[4:]] = True
        expected = sum(len(cell_targets(b, c)) * math.prod(_shape(block)) // len(RESOURCES)
                       for b, c in self.cells for block in BLOCKS)
        if len(seen) != expected:
            raise ValueError(f"Incomplete grid: {len(seen)} of {expected} coordinates; record failures explicitly")

    def mask(self, backbone, block, cells=None):
        """Missing units [entity, resource, fold, seed]: failed in any of the named cells (P4 default: the 2x2)."""
        cells = DEFINED[backbone] if cells is None else cells
        result = np.zeros(_shape(block)[:3] + _shape(block)[4:], dtype=bool)
        for cell in cells:
            result |= self.failed[backbone, cell, block]
        return result

    def masked(self, backbone, cell, block, mask):
        values = self.values[backbone, cell, block].copy()
        values[np.broadcast_to(mask[:, :, :, None, :], values.shape)] = np.nan
        return values

    def missing_units(self):
        """Every failed unit with the cells that failed, for the results listing (P4)."""
        listing = []
        for block in BLOCKS:
            for backbone in BACKBONES:
                cells = DEFINED[backbone] + (LATTICE if backbone == "LSTM" else ())
                cells = tuple(c for c in cells if (backbone, c) in self.cells)
                for e, r, f, s in zip(*np.nonzero(self.mask(backbone, block, cells))):
                    listing.append({"backbone": backbone, "block": block, "entity": COHORT[block][e],
                                    "resource": RESOURCES[r], "fold": FOLDS[f], "seed": SEEDS[s],
                                    "failed_cells": [c for c in cells if self.failed[backbone, c, block][e, r, f, s]]})
        return listing


# -- aggregation primitives (P4) -----------------------------------------------------------------

def seed_average(values):
    """Mean over the remaining seeds; NaN only where every seed is missing."""
    count = np.count_nonzero(~np.isnan(values), axis=-1)
    total = np.nansum(values, axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(count > 0, total / np.maximum(count, 1), np.nan)


def macro(values):
    """MacroMAE of [..., horizon]: equal-weight available cells per horizon, then equal horizons."""
    values = np.asarray(values, dtype=np.float64)
    flat = values.reshape(-1, values.shape[-1])
    present = ~np.isnan(flat)
    if not present.any(axis=0).all():
        return None
    return math.fsum(math.fsum(flat[present[:, h], h]) / present[:, h].sum() for h in range(flat.shape[1])) \
        / flat.shape[1]


def entity_macro(values):
    """A_X per entity from seed-averaged [entity, fold, horizon]; NaN for an entity with no folds."""
    return np.array([np.nan if (value := macro(values[e])) is None else value for e in range(len(values))])


def gain(candidate, reference):
    """G(C:B) = 100 (B - C) / B in percent; None when undefined."""
    if candidate is None or reference is None or reference == 0:
        return None
    return 100. * (reference - candidate) / reference


def log_effect(candidate, reference):
    """D(C:B) = ln A_C - ln A_B per entity; NaN where either aggregate is missing or not positive."""
    candidate, reference = np.asarray(candidate, dtype=np.float64), np.asarray(reference, dtype=np.float64)
    valid = (candidate > 0) & (reference > 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(valid, np.log(np.where(valid, candidate, 1.)) - np.log(np.where(valid, reference, 1.)), np.nan)
