"""Enumerate and validate the fixed v0.4 schedule without executing any units.

Invoke from the repository root with python -m fgcs_strengthening_v04.plan_execution.
"""

import argparse
from collections import Counter
from itertools import product
import json
import sys

from .src.identity import RESOURCES, SCOPES, ScientificIdentity, read_config
from .src.transfer.design import group_identities
from .src.modern.design import modern_identities

ARMS = ("core", "pairwise", "leave_one_out", "modern")
PHASES = ("inner", "final")


def _groups(config, blocks, seeds):
    for block in blocks:
        yield from ((block, entity, fold, seed)
                    for entity, fold, seed in product(config["cohort"][block], config["folds"], seeds))


def core_identities(block, entity, fold, seed, phase, config=None):
    """The LSTM 2x2 for one group: S1 and S2 per target, M0 and M1 shared (P2)."""
    width = (config or read_config())["lstm"]["primary_hidden_size"]
    for model, scope in SCOPES.items():
        for tasks in tuple((task,) for task in RESOURCES) if model.startswith("S") else (RESOURCES,):
            yield ScientificIdentity(block, entity, fold, seed, phase, "core", model, tasks, scope, width, "baseline")


def fit_identities():
    config = read_config()
    for group in _groups(config, config["cohort"], config["core_seeds"]):
        for phase in PHASES:
            yield from core_identities(*group, phase, config)
    secondary = config["secondary"]
    for group in _groups(config, secondary["blocks"], secondary["seeds"]):
        for phase in PHASES:
            yield from group_identities(*group, phase)
    yield from modern_identities()


def overhead_identities():
    """D-4 gradient extractions: LSTM M0 and M1 at the final selected epoch only (P5)."""
    config = read_config()
    width = config["lstm"]["primary_hidden_size"]
    diagnostics = config["diagnostics"]
    for group in _groups(config, config["cohort"], config["core_seeds"]):
        for model, slot in product(diagnostics["formulations"], diagnostics["extracted_slots"]):
            yield ScientificIdentity(*group, "final", "diagnostic", model, RESOURCES, SCOPES[model], width, slot)


def _expect(label, actual, expected):
    if actual != expected:
        raise RuntimeError(f"{label}: observed {actual}, expected {expected}")


def validate_schedule():
    config = read_config()
    budget = config["budget"]
    _expect("core seeds", config["core_seeds"], [0, 1, 2])
    _expect("fit workers", config["execution"]["fit_workers"], 6)
    ids = set()
    counts = Counter()
    modern = Counter()
    cells = Counter()

    def register(identity):
        digest = identity.digest
        if digest in ids:
            raise RuntimeError(f"Duplicate scientific identity: {identity.payload()}")
        ids.add(digest)

    for unit in fit_identities():
        register(unit)
        counts[unit.arm, unit.phase] += 1
        if unit.arm == "modern":
            modern[unit.formulation, unit.phase] += 1
        if unit.cell is not None:
            cells[unit.arm if unit.arm == "core" else unit.formulation, unit.cell] += 1

    _expect("scheduled fit arms", {arm for arm, _ in counts}, set(ARMS))
    for arm in ARMS:
        _expect(arm, [counts[arm, phase] for phase in PHASES], budget[arm])
    for family, expected in budget["modern_by_family"].items():
        _expect(family, [modern[family, phase] for phase in PHASES], expected)
    # 100 groups x 3 seeds x 2 phases = 600 trajectories per shared cell, four times that per independent cell.
    expected_cells = {(backbone, cell): 2400 if cell.startswith("S") else 600
                      for backbone in ("core", "DLinear", "PatchTST") for cell in ("S1", "S2", "M0", "M1")}
    expected_cells.update({("iTransformer", "S2"): 2400, ("iTransformer", "M1"): 600})
    _expect("2x2 cells", dict(cells), expected_cells)
    fits = [sum(counts[arm, phase] for arm in ARMS) for phase in PHASES]
    _expect("fits per phase", fits, budget["fits"])

    overhead = Counter()
    for unit in overhead_identities():
        register(unit)
        overhead[unit.arm] += 1
    diagnostics = config["diagnostics"]
    pairs = overhead["diagnostic"] * diagnostics["pairs"]
    totals = {"fit_total": sum(fits), "diagnostic_slots": overhead["diagnostic"], "diagnostic_batch_pairs": pairs,
              "gradient_extractions": pairs * len(diagnostics["batches"]) * diagnostics["tasks_per_batch"]}
    _expect("fit and diagnostic totals", totals,
            {"fit_total": 27000, "diagnostic_slots": 600, "diagnostic_batch_pairs": 4800,
             "gradient_extractions": 38400})
    for label, value in totals.items():
        _expect(f"configuration {label}", budget[label], value)
    return {**{arm: budget[arm] for arm in ARMS}, "modern_by_family": budget["modern_by_family"],
            "fits": fits, **totals, "identity_total": len(ids)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-identities", action="store_true", help="emit JSON Lines to stdout instead of totals")
    args = parser.parse_args(argv)
    summary = validate_schedule()
    if args.list_identities:
        for identity_group in (fit_identities(), overhead_identities()):
            for unit in identity_group:
                print(json.dumps({"id": unit.digest, **unit.payload()}))
    else:
        json.dump(summary, sys.stdout, indent=2)
        print()


if __name__ == "__main__":
    main()
