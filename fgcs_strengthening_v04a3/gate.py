"""Amendment A3, pure analysis: validation-gated policies, savings, accuracy, detection and verdicts.

Nothing here reads data. A frame holds, for one block (and backbone), per candidate cell:
- val[cell]: inner-validation error [entity, fold, seed, resource] (NaN where the cell has no such target);
- outer[cell]: native outer-test MAE [entity, fold, seed, resource, horizon];
- params[cell]: parameters of the model serving each target [entity, fold, seed, resource], or None;
and optionally persistence errors (val_p [entity, fold, resource], outer_p [entity, fold, resource, horizon]).

A policy assigns, per unit (entity, fold, seed) and resource, the cell whose model forecasts that
resource, using only that unit's inner-validation errors. Everything is descriptive: no p-values.
"""

from dataclasses import dataclass, field
import math

import numpy as np

from fgcs_strengthening_v04.src.analysis.bootstrap import gain_interval, percentile_interval, spearman
from fgcs_strengthening_v04.src.analysis.grid import gain, macro, seed_average
from fgcs_strengthening_v04.src.analysis.primary import matched_descriptives, persistence_skill

RESOURCES = ("CPU", "THROUGHPUT", "MEMORY", "DISK_WRITE")
PERSISTENCE = "persistence"
INDEPENDENT = ("S1", "S2")


@dataclass
class Frame:
    tier: str
    block: str
    backbone: str
    entities: tuple
    val: dict
    outer: dict
    params: dict = field(default_factory=dict)
    val_p: np.ndarray | None = None
    outer_p: np.ndarray | None = None

    @property
    def shape(self):
        return next(iter(self.outer.values())).shape  # [E, F, S, R, H]

    def has(self, cell):
        return cell in self.val and cell in self.outer


# -- partitions ---------------------------------------------------------------------------------

def _set_partitions(items):
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for partition in _set_partitions(rest):
        yield [[first], *partition]
        for i in range(len(partition)):
            yield partition[:i] + [[first, *partition[i]]] + partition[i + 1:]


def group_cell(tasks):
    tasks = tuple(r for r in RESOURCES if r in tasks)
    if len(tasks) == 1:
        return "S2"
    if len(tasks) == len(RESOURCES):
        return "M1"
    return "M1/" + "+".join(tasks)


def partitions():
    """The 15 partitions of the four resources, in a fixed order: fewer groups first, then by label."""
    found = []
    for partition in _set_partitions(list(RESOURCES)):
        groups = sorted((tuple(r for r in RESOURCES if r in g) for g in partition),
                        key=lambda g: [RESOURCES.index(r) for r in g])
        found.append(tuple(groups))
    found = sorted(set(found), key=lambda p: (len(p), " | ".join("+".join(g) for g in p)))
    assert len(found) == 15
    return tuple(found)


def partition_label(partition):
    return " | ".join("+".join(group) for group in partition)


def partition_cells(partition):
    """Cell serving each resource, in RESOURCES order."""
    cell = {}
    for group in partition:
        for resource in group:
            cell[resource] = group_cell(group)
    return tuple(cell[r] for r in RESOURCES)


# -- assignment, models and outcomes ------------------------------------------------------------

def fixed(frame, cell):
    E, F, S, R, _ = frame.shape
    return np.full((E, F, S, R), cell, dtype=object)


def models_and_params(frame, assignment):
    """Distinct models per unit [E, F, S] and their summed parameters (NaN when unknown)."""
    E, F, S, R = assignment.shape
    models = np.zeros((E, F, S), dtype=np.int64)
    params = np.zeros((E, F, S))
    for index in np.ndindex(E, F, S):
        seen = {}
        for r in range(R):
            cell = assignment[index + (r,)]
            if cell == PERSISTENCE:
                continue
            key = (cell, RESOURCES[r]) if cell in INDEPENDENT else (cell,)
            if key not in seen:
                table = frame.params.get(cell)
                seen[key] = np.nan if table is None else float(table[index + (r,)])
        models[index] = len(seen)
        params[index] = math.fsum(seen.values()) if seen else 0.0
    return models, params


def policy_outer(frame, assignment):
    """Native outer MAE [E, F, S, R, H] of the assigned forecasts."""
    out = np.full(frame.shape, np.nan)
    for cell in set(assignment.ravel()):
        chosen = assignment == cell
        if cell == PERSISTENCE:
            source = np.broadcast_to(frame.outer_p[:, :, None, :, :], frame.shape)
        else:
            source = frame.outer[cell]
        out[chosen] = source[chosen]
    if np.isnan(out).any():
        raise ValueError(f"{frame.block}/{frame.backbone}: assigned forecasts with missing outer MAE")
    return out


def seed_mean(values, r):
    """Seed-averaged [E, F, H] for resource r of [E, F, S, R, H]."""
    return seed_average(np.moveaxis(values[:, :, :, r, :], 2, -1))


# -- policies -----------------------------------------------------------------------------------

def _ratio(frame, candidate, reference):
    return frame.val[candidate] / frame.val[reference]


def g_ctx(frame):
    """Per unit and resource, S2 if strictly lower validation error than S1, else S1."""
    if not frame.has("S1"):
        return fixed(frame, "S2")
    return np.where(frame.val["S2"] < frame.val["S1"], "S2", "S1").astype(object)


def g_share(frame, tolerance):
    score = _ratio(frame, "M1", "S2").mean(axis=-1)  # [E, F, S]
    consolidate = np.broadcast_to((score <= 1 + tolerance)[..., None], frame.val["S2"].shape)
    return np.where(consolidate, "M1", "S2").astype(object)


def g_full(frame, tolerance):
    base = g_ctx(frame)
    base_val = np.where(base == "S1", frame.val.get("S1", frame.val["S2"]), frame.val["S2"])
    shared = [cell for cell in ("M1", "M0") if frame.has(cell)]
    scores = np.stack([(frame.val[cell] / base_val).mean(axis=-1) for cell in shared])  # [k, E, F, S]
    best = np.argmin(scores, axis=0)  # ties: M1 first
    best_score = np.take_along_axis(scores, best[None], axis=0)[0]
    names = np.array(shared, dtype=object)[best]
    consolidate = best_score <= 1 + tolerance
    return np.where(consolidate[..., None], names[..., None], base).astype(object)


def partition_scores(frame):
    """[P, E, F, S] mean validation ratio against S2 of each partition."""
    S2 = frame.val["S2"]
    scores = []
    for partition in partitions():
        cells = partition_cells(partition)
        ratios = [frame.val[cell][..., r] / S2[..., r] for r, cell in enumerate(cells)]
        scores.append(np.mean(ratios, axis=0))
    return np.stack(scores)


def partition_assignment(frame, choice):
    """Assignment from a partition index per unit [E, F, S]."""
    table = np.array([partition_cells(p) for p in partitions()], dtype=object)  # [P, R]
    return table[choice]


def g_group(frame, tolerance):
    scores = partition_scores(frame)
    groups = np.array([len(p) for p in partitions()])
    feasible = scores <= 1 + tolerance
    # Fewest models, then lowest score, then fixed order; S2 (score 1, four groups) is always feasible.
    key = np.where(feasible, groups[:, None, None, None] * 1e6 + scores, np.inf)
    return partition_assignment(frame, np.argmin(key, axis=0))


def with_fallback(frame, assignment):
    """Replace a resource's model by persistence where persistence validates strictly better."""
    current = np.full(assignment.shape, np.nan)
    for cell in set(assignment.ravel()):
        chosen = assignment == cell
        current[chosen] = frame.val[cell][chosen]
    better = np.broadcast_to(frame.val_p[:, :, None, :], assignment.shape) < current
    return np.where(better, PERSISTENCE, assignment).astype(object)


def outer_scores(frame, cells_per_resource):
    """Per unit [E, F, S]: mean over resources of the horizon-mean outer MAE ratio against S2."""
    S2 = frame.outer["S2"].mean(axis=-1)
    return np.mean([frame.outer[cell][..., r, :].mean(axis=-1) / S2[..., r]
                    for r, cell in enumerate(cells_per_resource)], axis=0)


def oracle_share(frame):
    better = outer_scores(frame, ("M1",) * len(RESOURCES)) < 1
    return np.where(np.broadcast_to(better[..., None], frame.val["S2"].shape), "M1", "S2").astype(object)


def oracle_group(frame):
    scores = np.stack([outer_scores(frame, partition_cells(p)) for p in partitions()])
    return partition_assignment(frame, np.argmin(scores, axis=0))


# -- outcomes -----------------------------------------------------------------------------------

def median_interval(draws, block, candidate, reference):
    present = np.isfinite(candidate) & np.isfinite(reference) & (reference > 0)
    ratios = np.where(present, candidate / np.where(present, reference, 1.0), np.nan).reshape(len(candidate), -1)
    indices = draws.indices(block)
    return percentile_interval(np.nanmedian(ratios[indices].reshape(len(indices), -1), axis=1))


def accuracy_rows(frame, name, assignment, draws):
    """One row per resource: policy against S2 and against M1, with VM-cluster intervals."""
    out = policy_outer(frame, assignment)
    models, params = models_and_params(frame, assignment)
    rows = []
    for r, resource in enumerate(RESOURCES):
        p, s2, m1 = (seed_mean(out, r), seed_mean(frame.outer["S2"], r), seed_mean(frame.outer["M1"], r))
        versus_s2 = matched_descriptives(p, s2)
        interval, undefined = median_interval(draws, frame.block, p, s2)
        gain_ci, _ = gain_interval(draws, frame.block, p, s2)
        row = {"tier": frame.tier, "block": frame.block, "backbone": frame.backbone, "policy": name,
               "resource": resource, "median_ratio_vs_S2": versus_s2["median_ratio"],
               "median_ratio_vs_S2_interval": interval, "win_rate_vs_S2": versus_s2["win_rate"],
               "median_ratio_vs_M1": matched_descriptives(p, m1)["median_ratio"],
               "macro_gain_vs_S2_percent": gain(macro(p), macro(s2)), "macro_gain_vs_S2_interval": gain_ci,
               "share_assigned": {cell: float(np.mean(assignment[..., r] == cell))
                                  for cell in sorted(set(assignment[..., r].ravel()))}}
        if frame.outer_p is not None:
            persistence = frame.outer_p[:, :, r, :]
            row["persistence_skill"] = persistence_skill(p, persistence)["skill"]
        rows.append(row)
    summary = {"tier": frame.tier, "block": frame.block, "backbone": frame.backbone, "policy": name,
               "mean_models": float(models.mean()), "units": int(models.size),
               "mean_parameters": None if np.isnan(params).any() else float(params.mean())}
    return rows, summary


def savings_retained(mean_models, s2_models, m1_models):
    if s2_models == m1_models:
        return None
    return (s2_models - mean_models) / (s2_models - m1_models)


def detection(frame, draws):
    """H-A3b: unit-level validation score against outer score (both M1/S2)."""
    x = _ratio(frame, "M1", "S2").mean(axis=-1)  # [E, F, S]
    y = (frame.outer["M1"] / frame.outer["S2"]).mean(axis=(-1, -2))
    E = x.shape[0]
    xs, ys = x.reshape(E, -1), y.reshape(E, -1)
    rho = float(spearman(xs.ravel(), ys.ravel()))
    replicates = np.array([spearman(xs[row].ravel(), ys[row].ravel()) for row in draws.indices(frame.block)])
    interval, undefined = percentile_interval(replicates)
    worse = ys.ravel() > 1
    flagged = xs.ravel() > 1
    tpr = float(flagged[worse].mean()) if worse.any() else None
    tnr = float((~flagged[~worse]).mean()) if (~worse).any() else None
    balanced = None if tpr is None or tnr is None else (tpr + tnr) / 2
    return {"tier": frame.tier, "block": frame.block, "backbone": frame.backbone, "units": int(x.size),
            "rho": rho, "interval": interval, "undefined_replicates": undefined,
            "outer_worse_share": float(worse.mean()), "validation_worse_share": float(flagged.mean()),
            "balanced_accuracy": balanced, "sensitivity": tpr, "specificity": tnr}


def detection_verdict(row):
    low = None if row["interval"] is None else row["interval"][0]
    if low is not None and low > 0 and row["rho"] >= 0.3:
        return "detects"
    if low is not None and low > 0:
        return "weak"
    return "does not detect"


def cost_cells(rows, policy, threshold=1.01):
    return sum(row["median_ratio_vs_S2"] > threshold for row in rows if row["policy"] == policy)


def h_a3a_verdict(retained, cost, reference_cost):
    cost_ok = cost <= reference_cost // 2
    if retained >= 0.5 and cost_ok:
        return "keeps most savings at reduced cost"
    if retained < 0.25:
        return "rarely consolidates"
    if cost_ok:
        return "keeps some savings at reduced cost"
    return "does not avoid the cost"


def h_a3c_verdict(group_models, share_models, group_cost, share_cost):
    if group_models > share_models - 0.25:
        return "no added savings"
    if group_cost <= share_cost + 1:
        return "grouping adds savings"
    return "adds savings at a cost"


def fallback_verdict(positive):
    return "fallback restores positive skill" if positive >= 8 else "fallback does not restore positive skill"
