"""Turn closed v0.4 or A1 journal outcomes into analysis inputs. Nothing runs on import.

Outcome-based inputs (native MAE) are read only after the orchestrator has closed evaluation (P9
step 7). Training-side inputs (D-4 slots, D-7 loss shares) need only fit closure, and D-1 reads
inner-training windows only.
"""

import json

from ..provenance import ProvenanceError
from .grid import FOLDS, HORIZONS, INTERVENTION_CELLS, MAERow, lattice_cell
from .mechanism import d1_fold_summary, d4_slot, inner_training_series, lagged_cross_correlation

def _gate(journal, name, phases):
    try:
        record = json.loads(journal._path("orchestrator", "gates", f"{name}.json").read_text())
    except FileNotFoundError:
        raise ProvenanceError(f"The analysis requires the closed {name} gate") from None
    if record.get("gate") != name or not set(phases) <= set(record.get("phases", ())):
        raise ProvenanceError(f"The {name} gate does not cover {', '.join(phases)}")
    return record


def require_fits_closed(journal):
    return _gate(journal, "fits", ("certify", "canary", "inner", "final", "diagnostics"))


def require_evaluation_closed(journal):
    require_fits_closed(journal)
    return _gate(journal, "evaluation", ("evaluation",))


def label(identity):
    """(backbone, cell) of a final neural identity."""
    if identity.arm == "core":
        return "LSTM", identity.formulation
    if identity.arm == "modern":
        return identity.formulation, identity.cell
    if identity.arm in ("pairwise", "leave_one_out"):
        return "LSTM", lattice_cell(identity.tasks)
    if identity.arm == "intervention":
        return "LSTM", INTERVENTION_CELLS[identity.variant]
    raise ValueError(f"No analysis cell for arm {identity.arm}")


def final_identities():
    from ...plan_execution import fit_identities

    return tuple(identity for identity in fit_identities() if identity.phase == "final")


def _status(journal, identity):
    for evaluation in (False, True):
        try:
            status, _, _ = journal.terminal_evidence(identity, evaluation=evaluation)
        except ProvenanceError:
            return "missing"
        if status != "complete":
            return "failed"
    return None  # fit and evaluation both complete: a binding error, never a missing unit


def mae_rows(journal, identities=None, *, evaluator=None):
    """Explicit rows for every final identity x target x horizon: ok, failed or missing."""
    from ..evaluation import OuterEvaluator

    require_evaluation_closed(journal)
    evaluator = evaluator or OuterEvaluator(journal)
    rows, support = [], {}
    for identity in final_identities() if identities is None else identities:
        backbone, cell = label(identity)
        try:
            cells = evaluator.completed_cells(identity)
        except ProvenanceError:
            status = _status(journal, identity)
            if status is None:
                raise
            rows.extend(MAERow(backbone, cell, identity.block, identity.entity, task, identity.fold, horizon,
                               identity.seed, None, status)
                        for task in identity.tasks for horizon in HORIZONS[identity.block])
            continue
        key = identity.block, identity.entity, identity.fold
        for item in cells:
            if support.setdefault(key, item.matching_metadata) != item.matching_metadata:
                raise ProvenanceError(f"Context, support, scaler or test IDs differ across cells: {key}")
            rows.append(MAERow(backbone, cell, identity.block, identity.entity, item.target, identity.fold,
                               item.horizon, identity.seed, item.mae))
    return rows


def d4_slots(journal, identities=None):
    """{(formulation, block, entity, fold, seed): D-4 slot summary or None if unavailable}."""
    from ...plan_execution import overhead_identities

    require_fits_closed(journal)
    slots = {}
    for identity in overhead_identities() if identities is None else identities:
        key = identity.formulation, identity.block, identity.entity, identity.fold, identity.seed
        try:
            evidence, _ = journal.completed_evidence(identity)
        except ProvenanceError:
            slots[key] = None
            continue
        slots[key] = d4_slot(evidence) if evidence["summary"]["K"] is not None else None
    return slots


def d7_fits(journal, identities=None):
    """{(block, entity, fold, seed): epochs of the LSTM M1 final fit, or None}."""
    require_fits_closed(journal)
    fits = {}
    for identity in final_identities() if identities is None else identities:
        if (identity.arm, identity.formulation) != ("core", "M1"):
            continue
        try:
            evidence, _ = journal.completed_evidence(identity)
        except ProvenanceError:
            evidence = None
        fits[identity.block, identity.entity, identity.fold, identity.seed] = evidence and evidence["epochs"]
    return fits


def d1_summaries(prepare=None):
    """{(block, entity, fold): 4x4 max-|corr| summary} from inner-training windows only."""
    from ..data_adapters import adapter_for
    from .grid import BLOCKS, COHORT

    summaries = {}
    for block in BLOCKS:
        adapter = None if prepare else adapter_for(block)
        for entity in COHORT[block]:
            for fold in FOLDS:
                partition = prepare(block, entity, fold) if prepare else adapter.prepare(entity, fold, "inner")
                summaries[block, entity, fold] = d1_fold_summary(
                    lagged_cross_correlation(*inner_training_series(partition)))
    return summaries

