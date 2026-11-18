"""Standard-library-only v0.4 modern 2x2 identities (protocol P2)."""

from collections import Counter
from itertools import product
import json

from ..identity import RESOURCES, ScientificIdentity, read_config

_CONFIG = read_config()
_SETTINGS = _CONFIG["modern"]
CONTEXTS = (4, 9, 18)
FAMILIES = tuple(_SETTINGS["families"])
SEEDS = tuple(_SETTINGS["seeds"])
COHORTS = {
    "fastStorage": ("697", "860", "366", "679", "360", "505", "481", "109", "680", "50"),
    "Rnd": ("99", "409", "269", "493", "474", "97", "118", "233", "142", "151"),
}
SCOPES = {"DLinear": ("own", "all"), "PatchTST": ("own", "all"), "iTransformer": ("all",)}


def family_identities(block, entity, fold, seed, phase, family):
    """Every defined cell of one family: per scope, four independent targets and one shared model."""
    group = (block, entity, fold, seed, phase, "modern", family)
    for scope in _SETTINGS["families"][family]["scopes"]:
        for resource in RESOURCES:
            yield ScientificIdentity(*group, (resource,), scope, None, "independent")
        yield ScientificIdentity(*group, RESOURCES, scope, None, "shared")


def modern_identities():
    for block, entities in _CONFIG["cohort"].items():
        for entity, fold, seed, phase, family in product(entities, _CONFIG["folds"], SEEDS,
                                                         _CONFIG["phases"], FAMILIES):
            yield from family_identities(block, entity, fold, seed, phase, family)


def dry_budget():
    configured = {block: tuple(entities) for block, entities in _CONFIG["cohort"].items()}
    scopes = {family: tuple(spec["scopes"]) for family, spec in _SETTINGS["families"].items()}
    if (configured != COHORTS or scopes != SCOPES or SEEDS != (0, 1, 2)
            or any(tuple(_CONFIG["blocks"][b]["entities"][:10]) != ids for b, ids in COHORTS.items())):
        raise RuntimeError("Modern cohort, scopes or seeds differ from v0.4")
    units = tuple(modern_identities())
    counts = Counter((unit.formulation, unit.phase) for unit in units)
    expected = {family: list(per_phase) for family, per_phase in _CONFIG["v04_budget"]["modern_by_family"].items()}
    observed = {family: [counts[family, phase] for phase in ("inner", "final")] for family in FAMILIES}
    if observed != expected or len({unit.digest for unit in units}) != len(units) != 15000:
        raise RuntimeError(f"Modern study budget differs from v0.4: {observed}")
    return {"families": {family: dict(zip(("inner", "final"), counts)) for family, counts in observed.items()},
            "inner": sum(c[0] for c in observed.values()), "final": sum(c[1] for c in observed.values())}


if __name__ == "__main__":
    print(json.dumps(dry_budget(), indent=2))
