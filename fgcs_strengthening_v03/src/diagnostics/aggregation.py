"""Complete-case-by-design v0.3 K construction, with no association tests."""

import math

from ..identity import BLOCK_ENTITIES, RESOURCES, ScientificIdentity, read_config

_CONFIG = read_config()
_MATERNA = ("Materna-T1", "Materna-T2", "Materna-T3")


def entity_k(block, entity, scores):
    """Average a full 5×5 M1 final-slot grid keyed by scientific identity."""
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


def materna_k(entity, scores):
    """Average the three complete trace scores for one exact Materna VM."""
    if any(not isinstance(key, ScientificIdentity) or key.block not in _MATERNA
           or key.entity != entity for key in scores):
        raise ValueError("Expected diagnostic identities for the same VM in Materna T1/T2/T3")
    traces = [entity_k(block, entity, {key: value for key, value in scores.items() if key.block == block})
              for block in _MATERNA]
    return math.fsum(traces) / len(traces) if all(value is not None for value in traces) else None
