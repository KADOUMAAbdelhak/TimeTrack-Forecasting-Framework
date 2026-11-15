"""Combine locked endpoints and families from explicit normalised result tables."""

from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from itertools import product

from ..diagnostics.aggregation import entity_k, materna_k
from ..identity import RESOURCES, ScientificIdentity
from ..transfer.estimands import NativeMAECell, entity_effect as transfer_effect
from .bootstrap import Bootstrap, Inference, mean_log
from .design import CONFIG, CORE, FOLDS, TRACES, analysis_slots, cohort_for, model_slices
from .endpoints import Effect, cohort_native, contrast, entity_aggregate, exp, interaction, materna_effect, mean
from .mechanism import correlate
from .multiplicity import adjust_registered, decision
from .schema import AnalysisRow


@dataclass(frozen=True, slots=True)
class DiagnosticCell:
    block: str
    entity: str
    fold: int
    seed: int
    K: float | None
    slot: str = "final"
    formulation: str = "M1"
    evidence_sha256: str | None = None
    identity_sha256: str | None = None

    def identity(self):
        if self.slot != "final" or self.formulation != "M1":
            raise ValueError("Association consumes only final-slot M1 diagnostic results")
        return ScientificIdentity(self.block, self.entity, self.fold, self.seed, "final", "diagnostic", "M1",
                                  RESOURCES, "all", CONFIG["lstm"]["primary_hidden_size"], "final")


class ResultTable:
    def __init__(self, cells, diagnostics=()):
        self._cells = defaultdict(dict)
        self._aggregates = {}
        self.diagnostics = defaultdict(dict)
        for cell in cells:
            key = (cell.model, cell.block, cell.entity, cell.resource)
            coordinate = (cell.fold, cell.horizon, cell.seed)
            if (cell.block not in CONFIG["blocks"] or cell.entity not in CONFIG["blocks"][cell.block]["entities"]
                    or cell.resource not in RESOURCES or type(cell.fold) is not int or cell.fold not in FOLDS
                    or type(cell.horizon) is not int or cell.horizon not in CONFIG["blocks"][cell.block]["horizons"]
                    or (cell.seed is not None and (type(cell.seed) is not int or cell.seed not in CORE))
                    or cell.status not in {"ok", "missing", "failed", "nonfinite_prediction"}):
                raise ValueError("Cell lies outside the normalised scientific grid")
            if coordinate in self._cells[key]:
                raise ValueError("Duplicate scientific MAE cell")
            self._cells[key][coordinate] = cell
        for cell in diagnostics:
            identity = cell.identity()
            group = self.diagnostics[cell.block, cell.entity]
            if identity in group:
                raise ValueError("Duplicate M1 final diagnostic slot")
            if cell.K is not None and (type(cell.K) is bool or not -1 <= cell.K <= 1):
                raise ValueError("Invalid diagnostic K")
            group[identity] = cell.K

    def cells(self, model, block, entity, resource, seeds):
        grid = self._cells.get((model, block, entity, resource), {})
        # Explicitly take the registered slice of a stored core five-seed grid.
        return [cell for cell in grid.values() if cell.seed in seeds]

    def aggregate(self, model, block, entity, resource, seeds):
        key = model, block, entity, resource, seeds
        if key not in self._aggregates:
            self._aggregates[key] = entity_aggregate(self.cells(*key), model=model, block=block,
                                                    entity=entity, resource=resource, seeds=seeds)
        return self._aggregates[key]

    def validate_domains(self, *, complete=False):
        expected = defaultdict(set)
        for slot in analysis_slots():
            for (model, seeds), block, entity in product(model_slices(slot), slot.blocks, slot.cohort):
                expected[model, block, entity, slot.resource].update(seeds)
        for key, grid in self._cells.items():
            if key not in expected or any(seed not in expected[key] for _, _, seed in grid):
                raise ValueError(f"Unregistered normalised model/cohort/seed slice: {key}")
        if complete:
            for key, seeds in expected.items():
                grid = self._cells.get(key, {})
                leads = CONFIG["blocks"][key[1]]["horizons"]
                if set(grid) != set(product(FOLDS, leads, seeds)):
                    raise ValueError(f"Missing normalised cells or explicit failure markers: {key}")
            for block in ("fastStorage", "Rnd", *TRACES):
                for entity in cohort_for(block):
                    if len(self.diagnostics.get((block, entity), {})) != 25:
                        raise ValueError(f"Missing M1 diagnostic slots or explicit null markers: {block}/{entity}")

    def K(self, group, entity):
        if group == "Materna":
            merged = {key: value for block in TRACES for key, value in self.diagnostics.get((block, entity), {}).items()}
            return materna_k(entity, merged)
        return entity_k(group, entity, self.diagnostics.get((group, entity), {}))


def _transfer(table, slot, block, entity, effect):
    """Use the Stage 3E identities and F/Q implementation on complete matched cells."""
    if effect.issues:
        return effect
    entry = slot.transfer
    models = (slot.reference, slot.candidate)
    grids = []
    for index, model in enumerate(models):
        grids.append([
            NativeMAECell(entry.model_identities(entity, cell.fold, cell.seed)[index],
                          cell.resource, cell.horizon, cell.mae, cell.context, cell.support_sha256,
                          cell.scaler_sha256, cell.ordered_test_ids_sha256)
            for cell in table.cells(model, block, entity, slot.resource, slot.seeds)
        ])
    measured = transfer_effect(entry, entity, *grids)
    return replace(effect, value=measured.log_effect, ratio=measured.ratio)


def entity_for_slot(table, slot, entity):
    if entity not in slot.cohort:
        raise ValueError("Entity is outside the slot's registered cohort")

    def in_block(block):
        terms = {model: table.aggregate(model, block, entity, slot.resource, seeds)
                 for model, seeds in model_slices(slot)}
        if slot.estimand == "I":
            return interaction(block, terms)
        candidate, reference = ("M1", "S2") if slot.estimand == "Spearman" else (slot.candidate, slot.reference)
        effect = contrast(block, candidate, reference, terms[candidate], terms[reference],
                          match_context=slot.match_context, persistence=slot.estimand == "R_persist")
        return _transfer(table, slot, block, entity, effect) if slot.transfer else effect

    values = {block: in_block(block) for block in slot.blocks}
    return materna_effect(values) if slot.environment == "Materna" else values[slot.blocks[0]]


def _native_details(slot, effects):
    native = cohort_native(effects, slot.cohort)
    comparisons = (("M1", "S2", ""),) if slot.estimand == "Spearman" else (
        (("M1", "S2", "all/"), ("M0", "S1", "own/")) if slot.estimand == "I"
        else ((slot.candidate, slot.reference, ""),))
    differences, gains = {}, {}
    for block, models in native.items():
        for candidate, reference, prefix in comparisons:
            if candidate not in models or reference not in models:
                continue
            left, right = models[candidate], models[reference]
            differences[prefix + block] = {
                entity: left["entity_mae"][entity] - right["entity_mae"][entity] for entity in slot.cohort
                if entity in left["entity_mae"] and entity in right["entity_mae"] and not effects[entity].issues}
            a, b = left["macro_mae"], right["macro_mae"]
            gains[prefix + block] = (100 * ((b - a) / b)
                                     if len(differences[prefix + block]) == len(slot.cohort)
                                     and a is not None and b is not None and b > 0 else None)
    return {"native": native, "native_candidate_minus_reference": differences,
            "native_macro_mae_gain_percent": gains}


def _estimate(bootstrap, table, slot, effects, issues):
    values = {key: effect.value for key, effect in effects.items()}
    if slot.estimand == "Spearman":
        scores = {entity: table.K(slot.environment, entity) for entity in slot.cohort}
        missing = sum(value is None for value in scores.values())
        if missing:
            issues["incomplete_final_m1_K"] += missing
        if not missing and all(effect.available for effect in effects.values()):
            return correlate(bootstrap, slot.environment, scores, values)
    elif all(effect.available for effect in effects.values()):
        if slot.interval:
            return mean_log(bootstrap, slot.environment, values, test=slot.inferential)
        point = mean(values.values())
        ratio = exp(point)
        return Inference(ratio if slot.estimand == "R_persist" else point, ratio=ratio)
    return Inference(None, raw_p=1. if slot.inferential else None, reason="incomplete_or_nonfinite_entity_effect")


def analyse(table, provenance):
    """Calculate only from the caller's explicit tables, reusing one draw bank."""
    table.validate_domains()
    draws = Bootstrap()
    pending = []
    for slot in analysis_slots():
        effects = {entity: entity_for_slot(table, slot, entity) for entity in slot.cohort}
        zeros, issues = Counter(), Counter()
        for effect in effects.values():
            zeros.update(effect.zeros)
            issues.update(effect.issues)
        estimate = _estimate(draws, table, slot, effects, issues)
        details = _native_details(slot, effects)
        details["finite_entity_effects"] = sum(effect.available for effect in effects.values())
        details["entity_effects"] = {
            entity: {"log_effect": effect.value, "ratio": effect.ratio,
                     "zero_counts": effect.zeros, "issues": effect.issues}
            for entity, effect in effects.items()
        }
        if slot.estimand == "Spearman":
            details["entity_log_effects_role"] = "D(M1:S2)"
        pending.append((slot, estimate, dict(zeros), dict(issues), details))
    adjusted = adjust_registered({slot.analysis_id: estimate.raw_p for slot, estimate, *_ in pending if slot.inferential})
    output = []
    for slot, estimate, zeros, issues, details in pending:
        p_adjusted = rejected = supported = None
        if slot.inferential:
            raw, p_adjusted = adjusted[slot.analysis_id]
            estimate = replace(estimate, raw_p=raw)
            rejected, supported = decision(estimate.point, p_adjusted, slot.predicted_direction)
        output.append(AnalysisRow(slot, estimate, provenance, "incomplete" if issues else "complete",
                                  zeros, issues, details, p_adjusted, rejected, supported))
    return tuple(output)
