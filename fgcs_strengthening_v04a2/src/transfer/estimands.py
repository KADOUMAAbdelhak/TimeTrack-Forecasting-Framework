"""Matched native-MAE contrasts for the registered empirical transfer study."""

from dataclasses import dataclass
import math

from ..identity import BLOCK_ENTITIES, ScientificIdentity, read_config
from .design import FOLDS, SEEDS, MatrixEntry

_CONFIG = read_config()


@dataclass(frozen=True, slots=True)
class NativeMAECell:
    identity: ScientificIdentity
    target: str
    horizon: int
    mae: float
    context: int
    support_sha256: str
    scaler_sha256: str
    ordered_test_ids_sha256: str

    @property
    def matching_metadata(self):
        return self.context, self.support_sha256, self.scaler_sha256, self.ordered_test_ids_sha256


@dataclass(frozen=True, slots=True)
class EntityEffect:
    numerator_mae: float | None
    denominator_mae: float | None
    ratio: float | None
    log_effect: float | None
    status: str

    @property
    def available(self):
        return self.status == "available"

    @property
    def native_difference(self):
        if self.numerator_mae is None or self.denominator_mae is None:
            return None
        return self.numerator_mae - self.denominator_mae


def _index(cells, identities, horizons, target):
    indexed = {}
    for cell in cells:
        key = (cell.identity.fold, cell.identity.seed, cell.horizon)
        if (cell.identity != identities.get(key[:2]) or cell.target != target
                or type(cell.horizon) is not int or cell.horizon not in horizons):
            raise ValueError("Cell is outside the exact formulation, target, fold, horizon or three-seed grid")
        if key in indexed:
            raise ValueError("Duplicate native-MAE cell")
        indexed[key] = cell
    return indexed


def _mean(values):
    return math.fsum(values) / len(values)


def entity_effect(entry, entity, numerator_cells, denominator_cells):
    """Apply §2 horizon → fold → seed aggregation before the §7 log contrast."""
    if not isinstance(entry, MatrixEntry) or entity not in BLOCK_ENTITIES[entry.block]:
        raise ValueError("Expected a registered transfer entry and exact cohort entity ID")
    horizons = _CONFIG["blocks"][entry.block]["horizons"]
    identities = {(fold, seed): entry.model_identities(entity, fold, seed)
                  for fold in FOLDS for seed in SEEDS}
    numerator, denominator = (
        _index(cells, {key: pair[i] for key, pair in identities.items()}, horizons, entry.target_task)
        for i, cells in enumerate((numerator_cells, denominator_cells))
    )
    if any(len(grid) != len(identities) * len(horizons) for grid in (numerator, denominator)):
        return EntityEffect(None, None, None, None, "incomplete_grid")
    block_contexts = _CONFIG["blocks"][entry.block]["contexts"]
    fold_metadata = {}
    for key, left in numerator.items():
        right = denominator[key]
        metadata = left.matching_metadata
        if (metadata != right.matching_metadata or left.context not in block_contexts
                or not all(metadata[1:]) or fold_metadata.setdefault(key[0], metadata) != metadata):
            return EntityEffect(None, None, None, None, "mismatched_support_context_or_scaler")
        if any(not math.isfinite(cell.mae) or cell.mae < 0 for cell in (left, right)):
            return EntityEffect(None, None, None, None, "invalid_native_mae")

    def aggregate(grid):
        return _mean([_mean([_mean([grid[fold, seed, h].mae for h in horizons]) for fold in FOLDS])
                      for seed in SEEDS])

    left, right = aggregate(numerator), aggregate(denominator)
    if left == right == 0:
        return EntityEffect(left, right, None, None, "both_aggregates_zero")
    if left == 0:
        return EntityEffect(left, right, 0., -math.inf, "numerator_zero")
    if right == 0:
        return EntityEffect(left, right, math.inf, math.inf, "denominator_zero")
    return EntityEffect(left, right, left / right, math.log(left) - math.log(right), "available")


def group_effect(entry, entities):
    """Mean entity log effect for one complete matrix entry over the block's 10 cohort VMs."""
    expected = BLOCK_ENTITIES[entry.block]
    if entities.keys() - expected:
        raise ValueError("Effect keys must be exact frozen cohort IDs")
    if entities.keys() != expected or any(not effect.available for effect in entities.values()):
        return None
    cohort = _CONFIG["cohort"][entry.block]
    return _mean([entities[entity].log_effect for entity in cohort])
