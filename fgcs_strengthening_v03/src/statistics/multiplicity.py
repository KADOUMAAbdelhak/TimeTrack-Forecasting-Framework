"""Fixed v0.3 families with deterministic Holm and BH adjustment."""

from collections import defaultdict
import math

from .design import SPEC, analysis_slots


def ranked_ids(raw):
    if not raw or any(type(p) is bool or not math.isfinite(p) or not 0 <= p <= 1 for p in raw.values()):
        raise ValueError("Expected finite raw p-values in [0,1]")
    return sorted(raw, key=lambda identity: (raw[identity], identity))


def holm(raw):
    ordered = ranked_ids(raw)
    m, running, adjusted = len(ordered), 0., {}
    for j, identity in enumerate(ordered):
        running = max(running, (m - j) * raw[identity])
        adjusted[identity] = min(1., running)
    return {identity: adjusted[identity] for identity in raw}


def bh(raw):
    ordered = ranked_ids(raw)
    m, running, adjusted = len(ordered), 1., {}
    for j, identity in reversed(list(enumerate(ordered, start=1))):
        running = min(running, m * raw[identity] / j)
        adjusted[identity] = running
    return {identity: adjusted[identity] for identity in raw}


def registered_families():
    families = defaultdict(list)
    for slot in analysis_slots():
        if slot.inferential:
            families[slot.family].append(slot)
    holm_sizes = {name: len(slots) for name, slots in families.items() if slots[0].correction == "Holm"}
    bh_sizes = [len(slots) for slots in families.values() if slots[0].correction == "BH"]
    if holm_sizes != SPEC["holm_sizes"] or bh_sizes != [12] * 8:
        raise RuntimeError("Multiplicity families differ from v0.3")
    return {name: tuple(slots) for name, slots in families.items()}


def adjust_registered(raw):
    """Preserve every fixed slot, representing unavailable tests as raw p=1."""
    families = registered_families()
    ids = {slot.analysis_id for slots in families.values() for slot in slots}
    if raw.keys() - ids:
        raise ValueError("Unregistered multiplicity slot")
    output = {}
    for slots in families.values():
        values = {slot.analysis_id: 1. if raw.get(slot.analysis_id) is None else raw[slot.analysis_id]
                  for slot in slots}
        adjusted = (holm if slots[0].correction == "Holm" else bh)(values)
        output.update({key: (values[key], adjusted[key]) for key in values})
    return output


def decision(point, adjusted, direction):
    rejected = adjusted is not None and adjusted < SPEC["threshold"]
    supports = None if direction is None else bool(rejected and point is not None and
                                                  (point > 0 if direction == "positive" else point < 0))
    return rejected, supports
