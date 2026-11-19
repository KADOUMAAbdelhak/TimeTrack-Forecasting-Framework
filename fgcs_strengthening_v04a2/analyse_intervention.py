"""Amendment A1 analysis (A1 protocol, sections 4 and 5): dry plan by default; --run after both journals close.

Invoke from the repository root:
    python -m fgcs_strengthening_v04a2.analyse_intervention               # table sizes only; reads no data
    python -m fgcs_strengthening_v04a2.analyse_intervention --run OUTPUT  # A1 and v0.4 evaluation gates closed

Inputs are the closed A1 journal (M1-GN, M1-UW) and, read only, the closed v0.4 journal (equal-loss LSTM
M1, S2 and S1 on the same units). The v0.4 journal is opened through ReadOnlyJournal, which never
publishes, so nothing under fgcs_strengthening_v04/ is written. Everything is descriptive: no p-values.
"""

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import math
from pathlib import Path
import statistics
import sys

import numpy as np

from .src.identity import RESOURCES, read_config
from .src.analysis.bootstrap import REPLICATES, SEED, Draws, gain_interval
from .src.analysis.grid import BLOCKS, COHORT, FOLDS, INTERVENTION_CELLS, SEEDS, Grid, MAERow, gain, macro, \
    seed_average
from .src.analysis.mechanism import d4_slot, loss_shares
from .src.analysis.primary import classify, consistency_counts, matched_descriptives

FORMAT = "fgcs-v04-a1-analysis/1"
_CONFIG = read_config()
LINEAGE = _CONFIG["lineage"]
REFERENCE_CELLS = ("M1", "S2", "S1")
MODE_CELLS = tuple(INTERVENTION_CELLS.values())
CELLS = REFERENCE_CELLS + MODE_CELLS
# (candidate, reference) per mode; the last pair is the existing equal-loss sharing contrast, for comparison.
COMPARISONS = tuple((cell, reference) for cell in MODE_CELLS for reference in REFERENCE_CELLS) + (("M1", "S2"),)
THRESHOLD = 6  # cells of 8 (A1 section 5)
GRID_CELLS = len(BLOCKS) * len(RESOURCES)


# -- pure analysis ------------------------------------------------------------------------------

def endpoint_rows(grid, draws):
    """One row per comparison x resource x block over the masked LSTM cells (paired across all five)."""
    rows = []
    for block in BLOCKS:
        mask = grid.mask("LSTM", block, CELLS)
        arrays = {cell: grid.masked("LSTM", cell, block, mask) for cell in CELLS}
        for candidate, reference in COMPARISONS:
            for r, resource in enumerate(RESOURCES):
                c, b = arrays[candidate][:, r], arrays[reference][:, r]
                cbar, bbar = seed_average(c), seed_average(b)
                overall = gain(macro(cbar), macro(bbar))
                counts = consistency_counts(c, b)
                interval, undefined = gain_interval(draws, block, cbar, bbar)
                rows.append({"block": block, "resource": resource, "contrast": f"{candidate}:{reference}",
                             "macro_mae": {candidate: macro(cbar), reference: macro(bbar)},
                             "gain_percent": overall, "class": classify(overall, counts), "counts": counts,
                             "interval": interval, "undefined_replicates": undefined,
                             **matched_descriptives(cbar, bbar)})
    return rows


def effective_d4_slot(evidence):
    """d4_slot with each task's D-4 norm scaled by its training weight at the checkpoint epoch.

    K and the cosines are unchanged by positive per-task scaling; only the norm ratio moves.
    """
    weights = evidence["loss_weights"]
    ratios = []
    for pair in evidence["pairs"]:
        for side in ("A", "B"):
            norms = [pair["norms"][side][task] * weights[task] for task in RESOURCES]
            if min(norms) > 0:
                ratios.append(max(norms) / min(norms))
    return math.fsum(ratios) / len(ratios) if ratios else None


def _median(values):
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def _entity_means(slots, block, field):
    """Entity means over available slots, as in v0.4 D-4 rows; slots: {(block, entity, fold, seed): dict|None}."""
    means = {}
    for entity in COHORT[block]:
        values = [slot[field] for (b, e, *_), slot in slots.items()
                  if (b, e) == (block, entity) and slot is not None and slot[field] is not None]
        means[entity] = math.fsum(values) / len(values) if values else None
    return means


def manipulation_rows(d4, d7):
    """d4: {cell: {(block, entity, fold, seed): slot or None}}; d7: {cell: {(block, entity, fold, seed): epochs}}.

    Slot dicts carry K, norm_ratio (unweighted) and effective_norm_ratio. The equal-loss reference has
    equal weights, so its effective ratio is its unweighted ratio.
    """
    rows = []
    for block in BLOCKS:
        for cell in ("M1", *MODE_CELLS):
            slots = d4[cell]
            entity = {field: _entity_means(slots, block, field) for field in ("K", "norm_ratio", "effective_norm_ratio")}
            trajectories = [epochs for (b, *_), epochs in d7[cell].items() if b == block and epochs]
            shares = {}
            for kind in ("unweighted", "weighted"):
                final = [_shares(epochs[-1], kind) for epochs in trajectories]
                shares[kind] = {task: (math.fsum(s[task] for s in final) / len(final) if final else None)
                                for task in RESOURCES}
            rows.append({"block": block, "cell": cell, "slots": sum(v is not None for (b, *_), v in slots.items()
                                                                   if b == block),
                         "median_K": _median(entity["K"].values()),
                         "median_norm_ratio": _median(entity["norm_ratio"].values()),
                         "median_effective_norm_ratio": _median(entity["effective_norm_ratio"].values()),
                         "entity": entity, "fits": len(trajectories), "mean_loss_share_at_E": shares,
                         "mean_weights_at_E": _mean_weights(trajectories)})
    return rows


def _shares(row, kind):
    weights = row.get("loss_weights") or dict.fromkeys(RESOURCES, 1.0)
    terms = {task: row["train_task_mse"][task] * (weights[task] if kind == "weighted" else 1.0) for task in RESOURCES}
    total = math.fsum(terms.values())
    return {task: (value / total if total > 0 else 0.0) for task, value in terms.items()}


def _mean_weights(trajectories):
    rows = [epochs[-1].get("loss_weights") for epochs in trajectories]
    if not rows or any(row is None for row in rows):
        return None
    return {task: math.fsum(row[task] for row in rows) / len(rows) for task in RESOURCES}


def decide(rows, manipulation):
    """The frozen A1 decision rule, per mode (section 5)."""
    by = {(row["contrast"], row["block"], row["resource"]): row for row in rows}
    check = {(row["cell"], row["block"]): row for row in manipulation}
    decisions = {}
    for mode, cell in INTERVENTION_CELLS.items():
        better = worse = no_penalty = 0
        for block in BLOCKS:
            for resource in RESOURCES:
                own = by[f"{cell}:M1", block, resource]
                ratio, win = own["median_ratio"], own["win_rate"]
                better += ratio is not None and win is not None and ratio < 1 and win > 0.5
                worse += ratio is not None and ratio > 1
                penalty = by[f"{cell}:S2", block, resource]["median_ratio"]
                no_penalty += penalty is not None and penalty <= 1
        blocks = {}
        for block in BLOCKS:
            arm, reference = check[cell, block], check["M1", block]
            value, base = arm["median_effective_norm_ratio"], reference["median_norm_ratio"]
            blocks[block] = {"arm": value, "equal_loss": base,
                             "passed": value is not None and base is not None and value < base}
        passed = all(item["passed"] for item in blocks.values())
        supported = better >= THRESHOLD and passed
        if supported:
            verdict = "penalty removed" if no_penalty >= THRESHOLD else "supported"
        elif worse >= THRESHOLD:
            verdict = "adverse"
        else:
            verdict = "not supported"
        decisions[mode] = {"cell": cell, "cells": GRID_CELLS, "threshold": THRESHOLD,
                           "better_than_equal_loss": better, "worse_than_equal_loss": worse,
                           "at_most_S2": no_penalty, "manipulation_check": {"passed": passed, "blocks": blocks},
                           "verdict": verdict}
    return decisions


def analyse(*, rows, d4, d7, draws=None):
    """All A1 tables from collected inputs (pure; used by --run and the synthetic tests)."""
    draws = draws or Draws()
    grid = Grid(rows, cells=[("LSTM", cell) for cell in CELLS])
    endpoints = endpoint_rows(grid, draws)
    manipulation = manipulation_rows(d4, d7)
    missing = [{"block": block, "entity": COHORT[block][e], "resource": RESOURCES[r], "fold": FOLDS[f],
                "seed": SEEDS[s]}
               for block in BLOCKS for e, r, f, s in zip(*np.nonzero(grid.mask("LSTM", block, CELLS)))]
    return {"endpoints": endpoints, "manipulation": manipulation, "decision": decide(endpoints, manipulation),
            "missing_units": missing}


def dry_plan():
    """Row counts of every table, from the design alone."""
    return {"endpoint_rows": len(COMPARISONS) * GRID_CELLS, "comparisons": [f"{c}:{r}" for c, r in COMPARISONS],
            "manipulation_rows": len(BLOCKS) * (1 + len(MODE_CELLS)), "decisions": list(INTERVENTION_CELLS),
            "threshold": f"{THRESHOLD} of {GRID_CELLS} resource x block cells",
            "bootstrap": {"seed": SEED, "replicates": REPLICATES, "draw_matrices": list(BLOCKS)}}


# -- journal readers ----------------------------------------------------------------------------

def read_only_v04_journal():
    """The closed v0.4 journal, bound to its tagged seal, with every write path refused."""
    from fgcs_strengthening_v04.src import provenance
    from fgcs_strengthening_v04.src.orchestrator import execution_fingerprints

    class ReadOnlyJournal(provenance.Journal):
        def __init__(self, seal):  # noqa: D401 - mirrors Journal.__init__ without publishing
            self.runtime = provenance.HOME / "runtime"
            seal.verify()
            self.seal = seal
            root = json.loads(self._path("fingerprints.json").read_text())
            if root != {"digest": seal.digest, **seal.payload()}:
                raise provenance.ProvenanceError("v0.4 journal is bound to different fingerprints")
            self._accepted, self._minimum = self._chain(root["digest"])

        def _refuse(self, *args, **kwargs):
            raise provenance.ProvenanceError("The v0.4 journal is read only for amendment A1")

        start = finish = save_checkpoint = quarantine = amend = _refuse

    seal = execution_fingerprints()
    if seal.digest != LINEAGE["v04_execution_seal"]:
        raise RuntimeError(f"The v0.4 seal differs from the A1 lineage: {seal.digest}")
    return ReadOnlyJournal(seal)


def v04_reference_identities(cell, *, phase="final"):
    """The v0.4 core LSTM identities of one reference cell (all seeds, folds and cohort VMs)."""
    from fgcs_strengthening_v04.src.identity import ScientificIdentity as V04Identity

    width = _CONFIG["lstm"]["primary_hidden_size"]
    scope = _CONFIG["formulations"][cell]["input_scope"]
    tasks = [(task,) for task in RESOURCES] if cell.startswith("S") else [RESOURCES]
    for block in BLOCKS:
        for entity in COHORT[block]:
            for fold in FOLDS:
                for seed in SEEDS:
                    for subset in tasks:
                        yield V04Identity(block, entity, fold, seed, phase, "core", cell, subset, scope, width,
                                          "baseline")


def _metadata(evaluator, identities):
    """{(block, entity, fold): matching metadata} from every available evaluation; must agree within a key."""
    from .src.provenance import ProvenanceError as A1Error
    from fgcs_strengthening_v04.src.provenance import ProvenanceError as V04Error

    found = {}
    for identity in identities:
        try:
            cells = evaluator.completed_cells(identity)
        except (A1Error, V04Error):
            continue
        key = identity.block, identity.entity, identity.fold
        for item in cells:
            if found.setdefault(key, item.matching_metadata) != item.matching_metadata:
                raise RuntimeError(f"Context, support, scaler or test IDs differ within {key}")
    return found


def collect(a1_journal, v04_journal):
    """MAE rows, D-4 slots and D-7 trajectories from both closed journals."""
    from fgcs_strengthening_v04.src.analysis import collect as v04_collect
    from fgcs_strengthening_v04.src.evaluation import OuterEvaluator as V04Evaluator
    from .plan_execution import fit_identities, overhead_identities
    from .src.analysis import collect as a1_collect
    from .src.evaluation import OuterEvaluator as A1Evaluator
    from .src.identity import diagnostic_parent

    a1_collect.require_evaluation_closed(a1_journal)
    v04_collect.require_evaluation_closed(v04_journal)
    a1_finals = [identity for identity in fit_identities() if identity.phase == "final"]
    references = {cell: list(v04_reference_identities(cell)) for cell in REFERENCE_CELLS}
    rows = list(a1_collect.mae_rows(a1_journal, a1_finals))
    for cell, identities in references.items():
        rows += [MAERow(**asdict(row)) for row in v04_collect.mae_rows(v04_journal, identities)]

    a1_support = _metadata(A1Evaluator(a1_journal), a1_finals)
    v04_support = _metadata(V04Evaluator(v04_journal), [i for ids in references.values() for i in ids])
    differing = sorted(key for key in a1_support.keys() & v04_support.keys() if a1_support[key] != v04_support[key])
    if differing:
        raise RuntimeError(f"A1 and v0.4 evaluations differ in context, support, scaler or test IDs: {differing[:5]}")

    d4 = {cell: {} for cell in ("M1", *MODE_CELLS)}
    for identity in overhead_identities():
        cell = INTERVENTION_CELLS[diagnostic_parent(identity).variant]
        key = identity.block, identity.entity, identity.fold, identity.seed
        d4[cell][key] = _slot(a1_journal, identity, effective=True)
    from fgcs_strengthening_v04.src.identity import ScientificIdentity as V04Identity
    width = _CONFIG["lstm"]["primary_hidden_size"]
    for block in BLOCKS:
        for entity in COHORT[block]:
            for fold in FOLDS:
                for seed in SEEDS:
                    identity = V04Identity(block, entity, fold, seed, "final", "diagnostic", "M1", RESOURCES, "all",
                                           width, "final")
                    d4["M1"][block, entity, fold, seed] = _slot(v04_journal, identity, effective=False)

    d7 = {cell: {} for cell in ("M1", *MODE_CELLS)}
    for identity in a1_finals:
        d7[INTERVENTION_CELLS[identity.variant]][identity.block, identity.entity, identity.fold, identity.seed] = \
            _epochs(a1_journal, identity)
    for identity in references["M1"]:
        d7["M1"][identity.block, identity.entity, identity.fold, identity.seed] = _epochs(v04_journal, identity)
    return rows, d4, d7


def _completed(journal, identity):
    try:
        return journal.completed_evidence(identity)
    except Exception as error:  # a missing or failed unit, from either package's ProvenanceError
        if type(error).__name__ != "ProvenanceError":
            raise
        return None, None


def _slot(journal, identity, *, effective):
    evidence, _ = _completed(journal, identity)
    if evidence is None or evidence["summary"]["K"] is None:
        return None
    slot = d4_slot(evidence)
    slot["effective_norm_ratio"] = effective_d4_slot(evidence) if effective else slot["norm_ratio"]
    return slot


def _epochs(journal, identity):
    evidence, _ = _completed(journal, identity)
    return evidence and evidence["epochs"]


def run(output):
    from .src.orchestrator import execution_fingerprints
    from .src.provenance import Journal

    output = Path(output)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    seal = execution_fingerprints()
    a1_journal = Journal(seal)
    v04_journal = read_only_v04_journal()
    rows, d4, d7 = collect(a1_journal, v04_journal)
    results = analyse(rows=rows, d4=d4, d7=d7)
    gates = {name: sha256(journal._path("orchestrator", "gates", "evaluation.json").read_bytes()).hexdigest()
             for name, journal in (("A1", a1_journal), ("v0.4", v04_journal))}
    document = {"format": FORMAT, "amendment": _CONFIG["amendment"], "lineage": LINEAGE,
                "tier": "tier 2 amendment A1; descriptive, no p-values",
                "fingerprint_sha256": seal.digest, "evaluation_gate_sha256": gates, "results": results}
    encoded = json.dumps(document, indent=1, allow_nan=False) + "\n"
    output.write_text(encoded)
    Path(f"{output}.sha256").write_text(f"{sha256(encoded.encode()).hexdigest()}  {output.name}\n")
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", metavar="OUTPUT", help="analyse both closed journals and write OUTPUT (JSON)")
    args = parser.parse_args(argv)
    if args.run:
        document = run(args.run)
        print(json.dumps({mode: item["verdict"] for mode, item in document["results"]["decision"].items()}))
    else:
        json.dump(dry_plan(), sys.stdout, indent=2)
        print()


if __name__ == "__main__":
    main()
