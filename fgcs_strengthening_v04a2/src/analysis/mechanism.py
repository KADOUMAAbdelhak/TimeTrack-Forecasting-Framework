"""P5 mechanism diagnostics: descriptive and associational only. None alters a model."""

import math

import numpy as np

from ..identity import RESOURCES
from .bootstrap import spearman_interval
from .grid import BLOCKS, COHORT, PAIRWISE, FOLDS, entity_macro, gain, lattice_cell, log_effect, seed_average

LAGS = tuple(range(1, 19))
_ORDERED = tuple((i, j) for i in range(len(RESOURCES)) for j in range(len(RESOURCES)) if i != j)


# -- D-1 lagged cross-correlation (inner-training windows only) --------------------------------------

def inner_training_series(partition):
    """Transformed, robust-scaled values at each inner-training origin, with row and segment positions.

    The value at an origin is the last row of its training window, so only inner-training windows
    are read (P5 D-1).
    """
    if partition.phase != "inner":
        raise ValueError("D-1 uses inner-training windows only")
    windows = partition.training()
    rows = np.asarray(partition._train_origins, dtype=np.int64)
    segments = partition._frame.segment_id.to_numpy(dtype=np.int64)[rows]
    values = np.asarray(windows.inputs[:, -1, :], dtype=np.float64)
    if values.shape != (len(rows), len(RESOURCES)):
        raise ValueError("Inner-training windows and origins differ")
    return values, rows, segments


def _pearson(x, y):
    if len(x) < 3:
        return math.nan
    x, y = x - x.mean(), y - y.mean()
    norm = math.sqrt(float((x * x).sum()) * float((y * y).sum()))
    return float((x * y).sum()) / norm if norm > 0 else math.nan


def lagged_cross_correlation(values, rows, segments, lags=LAGS):
    """corr[i, j, k] = Pearson(x_i[t], x_j[t + lag_k]) over origin pairs in one segment.

    rows are strictly increasing frame positions; within a segment, consecutive rows are
    consecutive time steps, so t + lag must itself be an inner-training origin in the same segment.
    """
    values, rows, segments = (np.asarray(a) for a in (values, rows, segments))
    if len(rows) and not np.all(np.diff(rows) > 0):
        raise ValueError("Origins must be strictly increasing")
    result = np.full((len(RESOURCES), len(RESOURCES), len(lags)), np.nan)
    for k, lag in enumerate(lags):
        position = np.searchsorted(rows, rows + lag)
        inside = position < len(rows)
        valid = np.zeros(len(rows), dtype=bool)
        valid[inside] = (rows[position[inside]] == rows[inside] + lag) & (segments[position[inside]] == segments[inside])
        x, y = values[valid], values[position[valid]]
        for i, j in _ORDERED:
            result[i, j, k] = _pearson(x[:, i], y[:, j])
    return result


def d1_fold_summary(correlations):
    """Per entity x fold: maximum absolute correlation over lags for each ordered pair (i -> j)."""
    summary = np.full(correlations.shape[:2], np.nan)
    for i, j in _ORDERED:
        values = np.abs(correlations[i, j])
        if np.isfinite(values).any():
            summary[i, j] = np.nanmax(values)
    return summary


def d1_target_dependence(fold_summaries):
    """Entity value per target j for D-3: mean over the five folds of the mean over sources i != j."""
    stacked = np.asarray(fold_summaries, dtype=np.float64)
    if stacked.shape != (len(FOLDS), len(RESOURCES), len(RESOURCES)):
        raise ValueError("Expected one summary per fold")
    output = np.full(len(RESOURCES), np.nan)
    for j in range(len(RESOURCES)):
        sources = stacked[:, [i for i in range(len(RESOURCES)) if i != j], j]
        if np.isfinite(sources).all():
            output[j] = float(sources.mean())
    return output


def d1_rows(summaries):
    """summaries: {(block, entity, fold): 4x4 summary}. Returns entity tables and target dependence."""
    rows, dependence = [], {}
    for block in BLOCKS:
        dependence[block] = np.full((len(COHORT[block]), len(RESOURCES)), np.nan)
        for e, entity in enumerate(COHORT[block]):
            folds = [summaries[block, entity, fold] for fold in FOLDS]
            dependence[block][e] = d1_target_dependence(folds)
            for fold, summary in zip(FOLDS, folds):
                rows.append({"block": block, "entity": entity, "fold": fold,
                             "max_abs_correlation": {f"{RESOURCES[i]}->{RESOURCES[j]}": _float(summary[i, j])
                                                     for i, j in _ORDERED}})
    return rows, dependence


def _float(value):
    return None if value is None or not math.isfinite(value) else float(value)


# -- D-2 conditional predictive dependence (reused Ridge AR/ARX) ---------------------------------------

def d2_dependence(ridge):
    """ridge: {block: {"AR": [entity, resource, fold, horizon], "ARX": ...}} -> G(ARX:AR) per entity x target."""
    output = {}
    for block in BLOCKS:
        ar, arx = ridge[block]["AR"], ridge[block]["ARX"]
        output[block] = np.full((len(COHORT[block]), len(RESOURCES)), np.nan)
        for r in range(len(RESOURCES)):
            a_ar, a_arx = entity_macro(ar[:, r]), entity_macro(arx[:, r])
            for e in range(len(COHORT[block])):
                value = gain(_float(a_arx[e]), _float(a_ar[e]))
                output[block][e, r] = np.nan if value is None else value
    return output


# -- D-3 dependence versus effects ---------------------------------------------------------------------

def d3_rows(draws, dependence, contrasts):
    """Spearman across each block's 10 VMs between D-1/D-2 and the LSTM D(S2:S1) and D(M1:S2)."""
    effects = {(row["block"], row["resource"], row["contrast"]): row["entity_log_effect"] for row in contrasts
               if row["backbone"] == "LSTM" and row["contrast"] in ("S2:S1", "M1:S2")}
    rows = []
    for measure, values in dependence.items():
        for block in BLOCKS:
            for r, resource in enumerate(RESOURCES):
                for contrast in ("S2:S1", "M1:S2"):
                    effect = effects[block, resource, contrast]
                    y = np.array([np.nan if effect[e] is None else effect[e] for e in COHORT[block]])
                    rows.append({"dependence": measure, "block": block, "resource": resource,
                                 "effect": f"D({contrast})", **spearman_interval(draws, block, values[block][:, r], y)})
    return rows


# -- D-4 gradient conflict and magnitude imbalance -------------------------------------------------

def d4_slot(evidence):
    """Six mean cross-task cosines, the mean max/min norm ratio and K for one final-slot extraction."""
    pairs = evidence["pairs"]
    cosines = {}
    for index, comparison in enumerate(pairs[0]["cross_task"]):
        values = [pair["cross_task"][index]["cosine"] for pair in pairs
                  if pair["cross_task"][index]["cosine"] is not None]
        cosines[f"{comparison['left_task']}|{comparison['right_task']}"] = \
            math.fsum(values) / len(values) if values else None
    ratios = []
    for pair in pairs:
        for side in ("A", "B"):
            norms = list(pair["norms"][side].values())
            if min(norms) > 0:
                ratios.append(max(norms) / min(norms))
    return {"K": evidence["summary"]["K"], "cosines": cosines,
            "norm_ratio": math.fsum(ratios) / len(ratios) if ratios else None}


def d4_rows(slots):
    """slots: {(formulation, block, entity, fold, seed): d4_slot or None}. Entity means over available slots."""
    rows = []
    for formulation in ("M1", "M0"):
        for block in BLOCKS:
            for entity in COHORT[block]:
                found = [value for (f, b, e, *_), value in slots.items()
                         if (f, b, e) == (formulation, block, entity) and value is not None]

                def mean(get):
                    values = [v for v in map(get, found) if v is not None]
                    return math.fsum(values) / len(values) if values else None

                names = found[0]["cosines"] if found else {}
                rows.append({"formulation": formulation, "role": "primary" if formulation == "M1" else "descriptive",
                             "block": block, "entity": entity, "slots": len(found),
                             "K": mean(lambda s: s["K"]), "norm_ratio": mean(lambda s: s["norm_ratio"]),
                             "cosines": {name: mean(lambda s, n=name: s["cosines"][n]) for name in names}})
    return rows


# -- D-6 task affinity from the D-5 lattice -------------------------------------------------------

def _entity_a(grid, cell, block, resource, mask):
    r = RESOURCES.index(resource)
    return entity_macro(seed_average(grid.masked("LSTM", cell, block, mask)[:, r]))


def d6_rows(grid):
    """F_i(j) = ln[A(S2_i) / A(pair_ij, i)] and Q_ij = ln[A(subset without j, i) / A(M1, i)], per entity.

    Each entry pairs only its two cells: a unit missing in either is missing for both.
    """
    rows = []
    for block in BLOCKS:
        for target in RESOURCES:
            for source in RESOURCES:
                if source == target:
                    continue
                pair = lattice_cell((target, source))
                without = lattice_cell(task for task in RESOURCES if task != source)
                for estimand, numerator, denominator in (("F", "S2", pair), ("Q", without, "M1")):
                    mask = grid.mask("LSTM", block, (numerator, denominator))
                    entity = log_effect(_entity_a(grid, numerator, block, target, mask),
                                        _entity_a(grid, denominator, block, target, mask))
                    present = entity[np.isfinite(entity)]
                    rows.append({"estimand": estimand, "block": block, "target": target, "source": source,
                                 "numerator": numerator, "denominator": denominator,
                                 "mean": float(present.mean()) if len(present) else None,
                                 "median": float(np.median(present)) if len(present) else None,
                                 "positive_entities": int((present > 0).sum()), "entities": int(len(present)),
                                 "entity_values": dict(zip(COHORT[block], (_float(v) for v in entity)))})
    if {row["numerator"] for row in rows if row["estimand"] == "F"} != {"S2"} or \
            {row["denominator"] for row in rows if row["estimand"] == "F"} != set(PAIRWISE):
        raise RuntimeError("D-6 affinity does not cover the six pairwise subsets")
    return rows


# -- D-7 per-task loss shares -------------------------------------------------------------------------

def loss_shares(epochs):
    """Each task's share of the summed training MSE per epoch, from a fit's train_task_mse rows."""
    shares = []
    for row in epochs:
        losses = [row["train_task_mse"][task] for task in RESOURCES]
        total = math.fsum(losses)
        shares.append({task: (loss / total if total > 0 else None) for task, loss in zip(RESOURCES, losses)})
    return shares


def d7_rows(fits):
    """fits: {(block, entity, fold, seed): epochs of an M1 final fit, or None}. Shares at E and per epoch."""
    rows = []
    for block in BLOCKS:
        trajectories = [loss_shares(epochs) for (b, *_), epochs in fits.items() if b == block and epochs]
        longest = max((len(t) for t in trajectories), default=0)
        for task in RESOURCES:
            final = [t[-1][task] for t in trajectories if t[-1][task] is not None]
            per_epoch = []
            for epoch in range(longest):
                values = [t[epoch][task] for t in trajectories if len(t) > epoch and t[epoch][task] is not None]
                per_epoch.append({"epoch": epoch + 1, "mean_share": math.fsum(values) / len(values),
                                  "fits": len(values)} if values else {"epoch": epoch + 1, "mean_share": None,
                                                                      "fits": 0})
            rows.append({"block": block, "resource": task, "fits": len(final),
                         "mean_share_at_E": math.fsum(final) / len(final) if final else None,
                         "per_epoch": per_epoch})
    return rows
