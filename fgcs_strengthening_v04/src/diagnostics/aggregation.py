"""Complete-case-by-design D-4 K construction per entity, with no association tests."""

import math

from ..identity import BLOCK_ENTITIES, RESOURCES, ScientificIdentity, read_config

_CONFIG = read_config()


def entity_k(block, entity, scores):
    """Average the full fold x seed grid (5 x 3 in v0.4) of M1 final-slot K values, keyed by identity."""
    if entity not in BLOCK_ENTITIES[block]:
        raise ValueError("Entity is outside the frozen block cohort")
    expected = {
        ScientificIdentity(block, entity, fold, seed, "final", "diagnostic", "M1",
                           RESOURCES, "all", _CONFIG["lstm"]["primary_hidden_size"], "final")
        for fold in _CONFIG["folds"] for seed in _CONFIG["core_seeds"]
    }
    if scores.keys() - expected:
        raise ValueError("Score keys must be final-slot M1 identities for the requested entity")
    for value in scores.values():
        if value is not None and (type(value) is bool or not math.isfinite(value) or not -1 <= value <= 1):
            raise ValueError("K must be finite in [-1,1] or unavailable")
    if scores.keys() != expected or any(value is None for value in scores.values()):
        return None
    return math.fsum(scores.values()) / len(expected)
