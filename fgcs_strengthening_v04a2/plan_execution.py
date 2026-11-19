"""Enumerate and validate the fixed A2 schedule (amendment A2 to v0.4) without executing any units.

Invoke from the repository root with python -m fgcs_strengthening_v04a2.plan_execution.
"""

import argparse
from collections import Counter
from itertools import product
import json
import sys

from .src.identity import INTERVENTION_MODES, RESOURCES, SCOPES, ScientificIdentity, read_config
from .src.modern.design import modern_identities

ARMS = ("core", "modern")
PHASES = ("inner", "final")
# Defined but unscheduled in A2: the v0.4 transfer lattice and diagnostics, and A1's intervention arm.
V04_ARMS = ("core", "pairwise", "leave_one_out", "modern")


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


def intervention_identities(block, entity, fold, seed, phase, config=None):
    """A1 (unscheduled in A2): the shared all-input LSTM once per loss-balancing mode."""
    intervention = (config or read_config())["intervention"]
    model = intervention["formulation"]
    for mode in INTERVENTION_MODES:
        yield ScientificIdentity(block, entity, fold, seed, phase, "intervention", model, RESOURCES, SCOPES[model],
                                 intervention["hidden_size"], mode)


def fit_identities():
    """A2: the tier-2 2x2 for all four backbones under the change parameterisation."""
    config = read_config()
    for group in _groups(config, config["cohort"], config["core_seeds"]):
        for phase in PHASES:
            yield from core_identities(*group, phase, config)
    yield from modern_identities()


def overhead_identities():
    """A2 schedules no D-4 extractions."""
    return iter(())


def _expect(label, actual, expected):
    if actual != expected:
        raise RuntimeError(f"{label}: observed {actual}, expected {expected}")


def validate_schedule():
    config = read_config()
    budget = config["budget"]
    _expect("core seeds", config["core_seeds"], [0, 1, 2])
    _expect("fit workers", config["execution"]["fit_workers"], 6)
    _expect("A2 parameterisation", config["residual"]["parameterisation"], "change")
    ids = set()
    counts = Counter()
    modern = Counter()
    cells = Counter()
    for unit in fit_identities():
        if unit.digest in ids:
            raise RuntimeError(f"Duplicate scientific identity: {unit.payload()}")
        ids.add(unit.digest)
        counts[unit.arm, unit.phase] += 1
        if unit.arm == "modern":
            modern[unit.formulation, unit.phase] += 1
        cells[unit.arm if unit.arm == "core" else unit.formulation, unit.cell] += 1
    _expect("scheduled fit arms", {arm for arm, _ in counts}, set(ARMS))
    for arm in ARMS:
        _expect(arm, [counts[arm, phase] for phase in PHASES], budget[arm])
    for family, expected in budget["modern_by_family"].items():
        _expect(family, [modern[family, phase] for phase in PHASES], expected)
    expected_cells = {(backbone, cell): 2400 if cell.startswith("S") else 600
                      for backbone in ("core", "DLinear", "PatchTST") for cell in ("S1", "S2", "M0", "M1")}
    expected_cells.update({("iTransformer", "S2"): 2400, ("iTransformer", "M1"): 600})
    _expect("2x2 cells", dict(cells), expected_cells)
    fits = [sum(counts[arm, phase] for arm in ARMS) for phase in PHASES]
    _expect("fits per phase", fits, budget["fits"])
    _expect("fit total", sum(fits), budget["fit_total"])
    _expect("overhead", list(overhead_identities()), [])
    return {**{arm: budget[arm] for arm in ARMS}, "modern_by_family": budget["modern_by_family"],
            "fits": fits, "fit_total": sum(fits), "evaluations": fits[1], "identity_total": len(ids)}


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
