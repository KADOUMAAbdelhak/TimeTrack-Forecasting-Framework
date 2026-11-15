"""Frozen LightGBM grid, identity enumeration and native validation selection."""

from collections import Counter
from dataclasses import asdict, dataclass
from itertools import product
import json
import math

from ..identity import RESOURCES, ScientificIdentity, read_config, tree_variant

_CONFIG = read_config()
SETTINGS = _CONFIG["lightgbm"]
BLOCKS = tuple(_CONFIG["secondary"]["blocks"])
FOLDS = tuple(_CONFIG["folds"])
HORIZONS = tuple(_CONFIG["blocks"][BLOCKS[0]]["horizons"])
SCOPE = tuple(SETTINGS["scopes"])
SEED = SETTINGS["seed"]


@dataclass(frozen=True, order=True, slots=True)
class TreeConfig:
    num_leaves: int
    learning_rate: float
    n_estimators: int

    @property
    def variant(self):
        return tree_variant(self.num_leaves, self.learning_rate, self.n_estimators)

    def payload(self):
        return asdict(self)


_GRID = SETTINGS["grid"]
GRID = tuple(TreeConfig(*values) for values in product(
    _GRID["leaves"], _GRID["learning_rate"], _GRID["estimators"]))
_BY_VARIANT = {config.variant: config for config in GRID}


def tree_identities():
    for block in BLOCKS:
        for entity, fold, target, scope in product(_CONFIG["blocks"][block]["entities"], FOLDS, RESOURCES, SCOPE):
            group = (block, entity, fold, SEED)
            for config in GRID:
                yield ScientificIdentity(*group, "inner", "lightgbm", "LightGBM", (target,), scope, None, config.variant)
            yield ScientificIdentity(*group, "final", "lightgbm", "LightGBM", (target,), scope, None, "selected")


def require_tree(identity, phase):
    if (not isinstance(identity, ScientificIdentity) or identity.arm != "lightgbm"
            or identity.formulation != "LightGBM" or identity.phase != phase):
        raise ValueError(f"Expected a declared LightGBM {phase} identity")


def inner_configuration(identity):
    require_tree(identity, "inner")
    return _BY_VARIANT[identity.variant]


def native_score(horizon_mae):
    if (tuple(sorted(horizon_mae)) != HORIZONS
            or any(not math.isfinite(value) or value < 0 for value in horizon_mae.values())):
        raise ValueError("Expected all five finite nonnegative native validation MAEs")
    return math.fsum(horizon_mae[lead] for lead in HORIZONS) / len(HORIZONS)


def select_configuration(scores):
    if scores.keys() != set(GRID):
        raise ValueError("Selection requires all eight completed registered configurations")
    return min(GRID, key=lambda config: (native_score(scores[config]), config))


def dry_budget():
    counts = Counter()
    seen = set()
    for identity in tree_identities():
        digest = identity.digest
        if digest in seen:
            raise RuntimeError("Duplicate LightGBM wrapper identity")
        seen.add(digest)
        counts[identity.phase] += 1
    if (BLOCKS != ("fastStorage", "Rnd") or FOLDS != (1, 2, 3, 4, 5) or SEED != 0
            or SCOPE != ("own", "all") or HORIZONS != (1, 2, 4, 9, 18)
            or any(tuple(_CONFIG["blocks"][b]["horizons"]) != HORIZONS
                   or len(_CONFIG["blocks"][b]["entities"]) != 35 for b in BLOCKS)
            or SETTINGS["estimators_per_wrapper"] != len(HORIZONS)
            or GRID != tuple(TreeConfig(*v) for v in product((15, 31), (.03, .05), (200, 400)))):
        raise RuntimeError("LightGBM scope, horizons or grid differ from v0.3")
    phases = ("inner", "final")
    wrappers = {phase: counts[phase] for phase in phases}
    scalars = {phase: wrappers[phase] * len(HORIZONS) for phase in phases}
    wrappers["total"] = sum(wrappers.values())
    scalars["total"] = sum(scalars.values())
    if (wrappers != {"inner": 22400, "final": 2800, "total": 25200}
            or scalars != {"inner": 112000, "final": 14000, "total": 126000}):
        raise RuntimeError("LightGBM wrapper/scalar accounting differs from v0.3")
    return {"wrappers": wrappers, "scalar_estimators": scalars}


if __name__ == "__main__":
    print(json.dumps(dry_budget(), indent=2))
