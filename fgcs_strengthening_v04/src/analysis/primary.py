"""P4: gains, consistency classes, intervals, interaction and descriptives, per backbone.

Everything is descriptive (tier 2): no p-values and no multiplicity families. Intervals never enter
the classification predicates.
"""

from fractions import Fraction
import math

import numpy as np

from ..identity import RESOURCES
from .bootstrap import gain_interval, mean_interval
from .grid import BACKBONES, BLOCKS, CELLS, COHORT, DEFINED, entity_macro, gain, log_effect, macro, seed_average

CONTRASTS = (("S2", "S1", "context, independent"), ("M1", "M0", "context, shared"),
             ("M0", "S1", "sharing, own input"), ("M1", "S2", "sharing, all input"))
CLASSES = ("Broad Positive", "Conditionally Positive", "Broad Negative", "Neutral or Mixed")
_SIGN = {"Broad Positive": 1, "Conditionally Positive": 1, "Broad Negative": -1}


def defined(backbone, candidate, reference):
    return candidate in DEFINED[backbone] and reference in DEFINED[backbone]


def classify(overall, counts):
    """P4 consistency classes; thresholds are fractions of the units still available."""
    if overall is None or any(n == 0 for _, n in counts.values()):
        return "Undefined"
    f = {name: Fraction(positive, n) for name, (positive, n) in counts.items()}
    if (overall >= 1 and f["horizons"] >= Fraction(4, 5) and f["vms"] >= Fraction(4, 5)
            and f["folds"] >= Fraction(4, 5) and f["seeds"] >= Fraction(2, 3)):
        return "Broad Positive"
    if (overall > 0 and f["horizons"] >= Fraction(3, 5) and f["vms"] >= Fraction(1, 2)
            and f["folds"] >= Fraction(3, 5) and f["seeds"] >= Fraction(2, 3)):
        return "Conditionally Positive"
    if (overall <= -1 and f["horizons"] <= Fraction(1, 5) and f["vms"] <= Fraction(1, 5)
            and f["folds"] <= Fraction(1, 5) and f["seeds"] <= Fraction(1, 3)):
        return "Broad Negative"
    return "Neutral or Mixed"


def _count(pairs):
    gains = [gain(c, b) for c, b in pairs]
    available = [g for g in gains if g is not None]
    return [sum(g > 0 for g in available), len(available)]


def consistency_counts(candidate, reference):
    """Positive/available counts for horizons, VMs, folds and seeds of [entity, fold, horizon, seed] arrays."""
    c, b = seed_average(candidate), seed_average(reference)
    horizons = c.shape[2]

    def horizon_mean(values, h):
        column = values[:, :, h]
        return float(np.nanmean(column)) if np.isfinite(column).any() else None

    return {
        "horizons": _count((horizon_mean(c, h), horizon_mean(b, h)) for h in range(horizons)),
        "vms": _count((macro(c[e]), macro(b[e])) for e in range(c.shape[0])),
        "folds": _count((macro(c[:, f]), macro(b[:, f])) for f in range(c.shape[1])),
        "seeds": _count((macro(candidate[..., s]), macro(reference[..., s])) for s in range(candidate.shape[3])),
    }


def persistence_skill(model, persistence):
    """Mean per-cell skill 1 - MAE/MAE_pers over entity-fold cells, then horizons (paper eq. skill).

    model and persistence are seed-averaged [entity, fold, horizon]. Zero-denominator skills are
    excluded from the mean and counted, never replaced.
    """
    present = np.isfinite(model) & np.isfinite(persistence)
    zero = present & (persistence == 0)
    usable = present & ~zero
    per_horizon = []
    for h in range(model.shape[-1]):
        cells = usable[..., h]
        if cells.any():
            per_horizon.append(math.fsum(1 - model[..., h][cells] / persistence[..., h][cells]) / cells.sum())
    return {"skill": math.fsum(per_horizon) / len(per_horizon) if len(per_horizon) == model.shape[-1] else None,
            "undefined_zero_denominator": int(zero.sum()), "cells": int(present.sum())}


def matched_descriptives(candidate, reference):
    """Median matched-cell MAE ratio C/B and the win rate (C strictly lower) over seed-averaged cells."""
    present = np.isfinite(candidate) & np.isfinite(reference)
    positive = present & (reference > 0)
    ratios = candidate[positive] / reference[positive]
    return {"median_ratio": float(np.median(ratios)) if len(ratios) else None,
            "win_rate": float(np.mean(candidate[present] < reference[present])) if present.any() else None,
            "matched_cells": int(present.sum()), "zero_reference_cells": int((present & ~positive).sum())}


def _resource(values, r):
    return values[:, r]


def contrast_rows(grid, draws, persistence=None):
    """One row per backbone x defined contrast x resource x block."""
    rows = []
    for block in BLOCKS:
        for backbone in BACKBONES:
            mask = grid.mask(backbone, block)
            arrays = {cell: grid.masked(backbone, cell, block, mask) for cell in DEFINED[backbone]}
            for candidate, reference, label in CONTRASTS:
                if not defined(backbone, candidate, reference):
                    continue
                for r, resource in enumerate(RESOURCES):
                    c, b = _resource(arrays[candidate], r), _resource(arrays[reference], r)
                    cbar, bbar = seed_average(c), seed_average(b)
                    overall = gain(macro(cbar), macro(bbar))
                    counts = consistency_counts(c, b)
                    interval, undefined = gain_interval(draws, block, cbar, bbar)
                    row = {"backbone": backbone, "block": block, "resource": resource,
                           "contrast": f"{candidate}:{reference}", "label": label,
                           "macro_mae": {candidate: macro(cbar), reference: macro(bbar)},
                           "gain_percent": overall, "class": classify(overall, counts), "counts": counts,
                           "interval": interval, "undefined_replicates": undefined,
                           "entity_log_effect": dict(zip(COHORT[block], _floats(
                               log_effect(entity_macro(cbar), entity_macro(bbar))))),
                           **matched_descriptives(cbar, bbar)}
                    if persistence is not None:
                        p = persistence[block][:, r]
                        row["persistence_skill"] = {candidate: persistence_skill(cbar, p),
                                                    reference: persistence_skill(bbar, p)}
                    rows.append(row)
    return rows


def _floats(values):
    return [None if not math.isfinite(v) else float(v) for v in values]


def interaction_rows(grid, draws, contrasts):
    """Both sharing gains side by side, plus I = ln A_M1 - ln A_S2 - ln A_M0 + ln A_S1 (descriptive)."""
    lookup = {(row["backbone"], row["block"], row["resource"], row["contrast"]): row for row in contrasts}
    rows = []
    for block in BLOCKS:
        for backbone in BACKBONES:
            if DEFINED[backbone] != CELLS:
                continue
            mask = grid.mask(backbone, block)
            for r, resource in enumerate(RESOURCES):
                A = {cell: entity_macro(seed_average(grid.masked(backbone, cell, block, mask)[:, r]))
                     for cell in CELLS}
                entity = log_effect(A["M1"], A["S2"]) - log_effect(A["M0"], A["S1"])
                defined_entities = np.isfinite(entity)
                interval, undefined = mean_interval(draws, block, entity)
                share = {name: lookup[backbone, block, resource, name] for name in ("M0:S1", "M1:S2")}
                rows.append({"backbone": backbone, "block": block, "resource": resource,
                             "sharing_gain_own_input": share["M0:S1"]["gain_percent"],
                             "sharing_gain_all_input": share["M1:S2"]["gain_percent"],
                             "sharing_class_own_input": share["M0:S1"]["class"],
                             "sharing_class_all_input": share["M1:S2"]["class"],
                             "interaction_log_ratio": float(entity[defined_entities].mean())
                             if defined_entities.any() else None,
                             "interval": interval, "undefined_replicates": undefined,
                             "entities": int(defined_entities.sum()),
                             "entity_interaction": dict(zip(COHORT[block], _floats(entity)))})
    return rows


def cross_backbone_rows(contrasts):
    """An effect generalises only if every defined backbone has a non-neutral class of one sign."""
    rows = []
    for block in BLOCKS:
        for candidate, reference, label in CONTRASTS:
            name = f"{candidate}:{reference}"
            for resource in RESOURCES:
                classes = {row["backbone"]: row["class"] for row in contrasts
                           if (row["block"], row["contrast"], row["resource"]) == (block, name, resource)}
                signs = {_SIGN.get(value) for value in classes.values()}
                verdict = "generalises across backbones" if len(signs) == 1 and None not in signs \
                    else "backbone-dependent"
                direction = {1: "positive", -1: "negative"}.get(next(iter(signs))) if len(signs) == 1 else None
                rows.append({"block": block, "contrast": name, "label": label, "resource": resource,
                             "classes": classes, "summary": verdict,
                             "direction": direction if verdict.startswith("generalises") else None})
    return rows


def baseline_rows(grid, persistence=None):
    """Comment 1: every defined backbone's MacroMAE and skill per cell x resource x block.

    Backbones are compared on their common available units (the union of their P4 masks), so the
    side-by-side values share one support.
    """
    rows = []
    for block in BLOCKS:
        common = np.zeros_like(grid.mask("LSTM", block))
        for backbone in BACKBONES:
            common |= grid.mask(backbone, block)
        for cell in CELLS:
            backbones = [b for b in BACKBONES if cell in DEFINED[b]]
            for r, resource in enumerate(RESOURCES):
                entries = {}
                for backbone in backbones:
                    values = seed_average(grid.masked(backbone, cell, block, common)[:, r])
                    entry = {"macro_mae": macro(values)}
                    if persistence is not None:
                        entry["persistence_skill"] = persistence_skill(values, persistence[block][:, r])["skill"]
                    entries[backbone] = entry
                maes = [e["macro_mae"] for e in entries.values() if e["macro_mae"] is not None]
                best = min(maes) if maes else None
                lstm = entries["LSTM"]["macro_mae"]
                rows.append({"block": block, "cell": cell, "resource": resource, "backbones": entries,
                             "undefined_backbones": [b for b in BACKBONES if b not in backbones],
                             "most_accurate": min((b for b in entries if entries[b]["macro_mae"] is not None),
                                                  key=lambda b: entries[b]["macro_mae"], default=None),
                             "lstm_ratio_to_most_accurate": lstm / best if lstm is not None and best else None})
    return rows


def parameter_counts():
    """Trainable parameters of each cell's model complement (four models for S1/S2) per context."""
    from ..models.lstm import LSTM
    from ..models.registry import REGISTRY
    from ..modern.design import CONTEXTS

    def count(model):
        return sum(p.numel() for p in model.parameters() if p.requires_grad)

    scope = {"S1": "own", "S2": "all", "M0": "own", "M1": "all"}
    block = BLOCKS[0]
    rows = []
    for backbone in BACKBONES:
        for cell in DEFINED[backbone]:
            complements = [(task,) for task in RESOURCES] if cell.startswith("S") else [RESOURCES]
            for context in CONTEXTS:
                if backbone == "LSTM":
                    models = [LSTM(formulation=cell, block=block, tasks=tasks, hidden_size=64) for tasks in complements]
                else:
                    models = [REGISTRY[backbone].build(context, tasks, scope[cell]) for tasks in complements]
                rows.append({"backbone": backbone, "cell": cell, "context": context, "models": len(models),
                             "parameters_per_model": count(models[0]),
                             "complement_parameters": sum(map(count, models))})
    return rows
