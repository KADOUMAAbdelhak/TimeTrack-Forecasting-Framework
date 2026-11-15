"""Complete-grid native MAE aggregation and registered entity contrasts."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import math

from .design import CONFIG, CORE, DETERMINISTIC, FOLDS, SECONDARY, SEED0, TRACES


@dataclass(frozen=True, slots=True)
class Cell:
    model: str
    block: str
    entity: str
    resource: str
    fold: int
    horizon: int
    seed: int | None
    mae: float | None
    context: int | None
    support_sha256: str | None
    scaler_sha256: str | None
    ordered_test_ids_sha256: str | None
    status: str = "ok"
    evidence_sha256: str | None = None
    identity_sha256: str | None = None

    @property
    def metadata(self):
        return self.support_sha256, self.ordered_test_ids_sha256, self.context, self.scaler_sha256


@dataclass(frozen=True, slots=True)
class Aggregate:
    mae: float | None
    status: str
    folds: dict = field(default_factory=dict)
    identity: tuple = ()
    issues: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Effect:
    value: float | None
    ratio: float | None = None
    native: dict = field(default_factory=dict)
    zeros: dict = field(default_factory=dict)
    issues: dict = field(default_factory=dict)
    subject: tuple = ()

    @property
    def available(self):
        return self.value is not None and math.isfinite(self.value) and not self.issues


def mean(values):
    values = tuple(values)
    if not values:
        raise ValueError("Cannot average an empty registered slice")
    try:
        return math.fsum(values) / len(values)
    except OverflowError:
        return math.fsum(value / len(values) for value in values)


def exp(value):
    try:
        return math.exp(value)
    except OverflowError:
        return math.inf


def entity_aggregate(cells, *, model, block, entity, resource, seeds):
    """A = equal seeds of equal folds of equal horizons, after exact grid validation."""
    if (not isinstance(seeds, tuple) or seeds not in (CORE, SECONDARY, SEED0, DETERMINISTIC)
            or any(seed is not None and type(seed) is not int for seed in seeds)):
        raise ValueError("Invalid registered seed slice")
    if entity not in CONFIG["blocks"][block]["entities"] or resource not in CONFIG["resources"]:
        raise ValueError("Entity or resource is outside the frozen grid")
    horizons = CONFIG["blocks"][block]["horizons"]
    grid, by_fold = {}, {}
    issues = Counter()
    for cell in cells:
        key = cell.fold, cell.horizon, cell.seed
        if ((cell.model, cell.block, cell.entity, cell.resource) != (model, block, entity, resource)
                or type(cell.fold) is not int or cell.fold not in FOLDS
                or type(cell.horizon) is not int or cell.horizon not in horizons
                or (cell.seed is not None and type(cell.seed) is not int) or cell.seed not in seeds):
            raise ValueError("Cell is outside the exact model/entity/fold/horizon/seed grid")
        if key in grid:
            raise ValueError("Duplicate scientific MAE cell")
        grid[key] = cell.mae
        if cell.status not in {"ok", "missing", "failed", "nonfinite_prediction"}:
            raise ValueError("Unknown scientific cell status")
        if cell.status != "ok":
            issues[cell.status] += 1
            continue
        if cell.mae is None or type(cell.mae) is bool or not math.isfinite(cell.mae) or cell.mae < 0:
            issues["invalid_mae"] += 1
        if (not cell.support_sha256 or not cell.ordered_test_ids_sha256
                or (model != "persistence" and (type(cell.context) is not int
                    or cell.context not in CONFIG["blocks"][block]["contexts"] or not cell.scaler_sha256))
                or by_fold.setdefault(cell.fold, cell.metadata) != cell.metadata):
            issues["support_mismatch"] += 1
    missing = len(FOLDS) * len(horizons) * len(seeds) - len(grid)
    if missing:
        issues["incomplete_grid"] += missing
    identity = (model, block, entity, resource, seeds)
    if issues:
        return Aggregate(None, "+".join(sorted(issues)), identity=identity, issues=dict(issues))
    return Aggregate(mean(mean(mean(grid[f, h, s] for h in horizons) for f in FOLDS) for s in seeds),
                     "complete", by_fold, identity)


def _native(block, aggregates):
    return {(block, model): result.mae for model, result in aggregates.items() if result.mae is not None}


def _issues(aggregates):
    counts = Counter()
    for result in aggregates.values():
        counts.update(result.issues)
    return dict(counts)


def _matched(aggregates, match_context):
    span = slice(None) if match_context else slice(0, 2)
    first, *remaining = aggregates
    return all(first.folds[fold][span] == other.folds[fold][span] for fold in FOLDS for other in remaining)


def contrast(block, candidate, reference, left, right, *, match_context=True, persistence=False):
    if (left.identity[:2] != (candidate, block) or right.identity[:2] != (reference, block)
            or left.identity[2:4] != right.identity[2:4]
            or (not persistence and left.identity[4] != right.identity[4])
            or (persistence and right.identity[4] != (None,))):
        raise ValueError("Incompatible model, entity, resource or seed aggregates")
    subject = left.identity[2:4]
    terms = {candidate: left, reference: right}
    native, issues = _native(block, terms), _issues(terms)
    zeros = {f"{model}_aggregate_zero": 1 for model, result in terms.items() if result.mae == 0}
    if issues:
        return Effect(None, native=native, zeros=zeros, issues=issues, subject=subject)
    if not _matched((left, right), match_context):
        return Effect(None, native=native, zeros=zeros, issues={"support_mismatch": 1}, subject=subject)
    a, b = left.mae, right.mae
    if a == b == 0:
        return Effect(None, native=native, zeros={**zeros, "both_zero": 1}, subject=subject)
    if a == 0:
        return Effect(None if persistence else -math.inf, None if persistence else 0.,
                      native, {**zeros, "candidate_only_zero": 1}, subject=subject)
    if b == 0:
        return Effect(None if persistence else math.inf, None if persistence else math.inf,
                      native, {**zeros, "reference_only_zero": 1}, subject=subject)
    relative = (a - b) / b
    log_ratio = math.log1p(relative) if abs(relative) <= 0.5 else math.log(a) - math.log(b)
    return Effect(log_ratio, a / b, native, subject=subject)


def interaction(block, aggregates):
    if set(aggregates) != {"M1", "S2", "M0", "S1"}:
        raise ValueError("Interaction requires exactly M1, S2, M0 and S1")
    all_input = contrast(block, "M1", "S2", aggregates["M1"], aggregates["S2"])
    own = contrast(block, "M0", "S1", aggregates["M0"], aggregates["S1"])
    if aggregates["M1"].identity[2:] != aggregates["M0"].identity[2:]:
        raise ValueError("Interaction terms must have the same entity, resource and seeds")
    subject = all_input.subject
    native = all_input.native | own.native
    zeros = {f"{scope}/{key}": count for scope, effect in (("all", all_input), ("own", own))
             for key, count in effect.zeros.items()}
    issues = Counter(all_input.issues) + Counter(own.issues)
    if not issues and not _matched(tuple(aggregates.values()), True):
        issues["support_mismatch"] += 1
    if issues or not all_input.available or not own.available:
        return Effect(None, native=native, zeros=zeros, issues=dict(issues), subject=subject)
    value = all_input.value - own.value
    return Effect(value, exp(value), native, zeros, subject=subject)


def materna_effect(trace_effects):
    if set(trace_effects) - set(TRACES):
        raise ValueError("Expected Materna T1/T2/T3 effects for one exact VM")
    subjects = {effect.subject for effect in trace_effects.values()}
    if len(subjects) > 1:
        raise ValueError("Materna effects must belong to the same exact VM and resource")
    subject = next(iter(subjects), ())
    native, zeros, issues = {}, {}, {}
    for trace in TRACES:
        effect = trace_effects.get(trace)
        if effect is None:
            issues[f"{trace}/missing_trace"] = 1
            continue
        if any(block != trace for block, _ in effect.native):
            raise ValueError("Materna trace result has incompatible native values")
        native.update(effect.native)
        zeros.update({f"{trace}/{key}": count for key, count in effect.zeros.items()})
        issues.update({f"{trace}/{key}": count for key, count in effect.issues.items()})
    if issues or any(not trace_effects[trace].available for trace in TRACES):
        return Effect(None, native=native, zeros=zeros, issues=issues, subject=subject)
    value = mean(trace_effects[trace].value for trace in TRACES)
    return Effect(value, exp(value), native, zeros, subject=subject)


def cohort_native(effects, cohort):
    """Retain native entity values and complete-cohort MacroMAE separately by trace."""
    grouped = defaultdict(dict)
    for entity, effect in effects.items():
        for (block, model), mae in effect.native.items():
            grouped[block, model][entity] = mae
    output = {}
    for (block, model), values in grouped.items():
        output.setdefault(block, {})[model] = {
            "entity_mae": {entity: values[entity] for entity in cohort if entity in values},
            "macro_mae": mean(values[entity] for entity in cohort) if values.keys() == set(cohort) else None,
        }
    return output
