"""Standard-library-only modern study and exact pilot identities."""

from collections import Counter
from itertools import product
import json

from ..identity import RESOURCES, ScientificIdentity, read_config

_CONFIG = read_config()
_SETTINGS = _CONFIG["modern"]
CONTEXTS = (4, 9, 18)
FAMILIES = tuple(_SETTINGS["families"])
COHORTS = {
    "fastStorage": ("697", "860", "366", "679", "360", "505", "481", "109", "680", "50"),
    "Rnd": ("99", "409", "269", "493", "474", "97", "118", "233", "142", "151"),
}
_PILOTS = {("fastStorage", "697", 1): 18, ("Rnd", "99", 1): 4}


def modern_identities():
    for block, entities in _SETTINGS["cohorts"].items():
        for entity, fold, phase, family in product(entities, _CONFIG["folds"], _CONFIG["phases"], FAMILIES):
            group = (block, entity, fold, _SETTINGS["seed"], phase, "modern", family)
            scope = _SETTINGS["families"][family]["scope"]
            for resource in RESOURCES:
                yield ScientificIdentity(*group, (resource,), scope, None, "independent")
            yield ScientificIdentity(*group, RESOURCES, scope, None, "shared")


def pilot_context(identity):
    if identity.arm == "modern" and identity.phase == "inner" and identity.seed == 0:
        return _PILOTS.get((identity.block, identity.entity, identity.fold))
    return None


def pilot_identities():
    return tuple(identity for identity in modern_identities() if pilot_context(identity) is not None)


def dry_budget():
    configured = {block: tuple(entities) for block, entities in _SETTINGS["cohorts"].items()}
    pilots = {(row["block"], row["entity"], row["fold"]): row["context"] for row in _SETTINGS["pilot"]}
    if (configured != COHORTS or pilots != _PILOTS or _SETTINGS["seed"] != 0
            or any(tuple(_CONFIG["blocks"][b]["entities"][:10]) != ids for b, ids in COHORTS.items())):
        raise RuntimeError("Modern cohorts, pilots or seed differ from v0.3")
    units = tuple(modern_identities())
    counts = Counter((unit.formulation, unit.phase) for unit in units)
    pilot = pilot_identities()
    complements = tuple((task,) for task in RESOURCES) + (RESOURCES,)
    expected = {(block, entity, family, tasks) for block, entity, _ in _PILOTS
                for family, tasks in product(FAMILIES, complements)}
    actual = {(unit.block, unit.entity, unit.formulation, unit.tasks) for unit in pilot}
    if (len(units) != 3000 or len({unit.digest for unit in units}) != 3000
            or len(pilot) != 30 or actual != expected or not set(pilot) <= set(units)
            or any(counts[family, phase] != 500 for family in FAMILIES for phase in ("inner", "final"))):
        raise RuntimeError("Modern study budget or pilot membership differs from v0.3")
    return {"families": {family: {phase: counts[family, phase] for phase in ("inner", "final")}
                         for family in FAMILIES}, "inner": 1500, "final": 1500, "pilot_subset": 30}


if __name__ == "__main__":
    print(json.dumps(dry_budget(), indent=2))
