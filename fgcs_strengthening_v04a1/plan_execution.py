"""Enumerate and validate the fixed A1 schedule (amendment A1 to v0.4) without executing any units.

Invoke from the repository root with python -m fgcs_strengthening_v04a1.plan_execution.
"""

import argparse
from collections import Counter
from itertools import product
import json
import sys

from .src.identity import (DIAGNOSTIC_SLOT_SEPARATOR, INTERVENTION_MODES, RESOURCES, SCOPES, ScientificIdentity,
                           read_config)

ARMS = ("intervention",)
PHASES = ("inner", "final")
# The v0.4 arms stay defined (identity validation, the v0.4 reference reader) but A1 schedules none of them.
V04_ARMS = ("core", "pairwise", "leave_one_out", "modern")


def _groups(config, blocks, seeds):
    for block in blocks:
        yield from ((block, entity, fold, seed)
                    for entity, fold, seed in product(config["cohort"][block], config["folds"], seeds))


def core_identities(block, entity, fold, seed, phase, config=None):
    """The LSTM 2x2 for one group: S1 and S2 per target, M0 and M1 shared (v0.4 P2)."""
    width = (config or read_config())["lstm"]["primary_hidden_size"]
    for model, scope in SCOPES.items():
        for tasks in tuple((task,) for task in RESOURCES) if model.startswith("S") else (RESOURCES,):
            yield ScientificIdentity(block, entity, fold, seed, phase, "core", model, tasks, scope, width, "baseline")


def intervention_identities(block, entity, fold, seed, phase, config=None):
    """A1: the shared all-input LSTM (M1) once per loss-balancing mode."""
    intervention = (config or read_config())["intervention"]
    model = intervention["formulation"]
    for mode in INTERVENTION_MODES:
        yield ScientificIdentity(block, entity, fold, seed, phase, "intervention", model, RESOURCES, SCOPES[model],
                                 intervention["hidden_size"], mode)


def fit_identities():
    config = read_config()
    for group in _groups(config, config["cohort"], config["intervention"]["seeds"]):
        for phase in PHASES:
            yield from intervention_identities(*group, phase, config)


def overhead_identities():
    """D-4 gradient extractions of each A1 mode at its final selected epoch (the v0.4 P5 slot)."""
    config = read_config()
    intervention = config["intervention"]
    slot = intervention["diagnostics"]["slot"]
    for group in _groups(config, config["cohort"], intervention["seeds"]):
        for mode in INTERVENTION_MODES:
            yield ScientificIdentity(*group, "final", "diagnostic", intervention["formulation"], RESOURCES,
                                     SCOPES[intervention["formulation"]], intervention["hidden_size"],
                                     f"{mode}{DIAGNOSTIC_SLOT_SEPARATOR}{slot}")


def _expect(label, actual, expected):
    if actual != expected:
        raise RuntimeError(f"{label}: observed {actual}, expected {expected}")


def validate_schedule():
    config = read_config()
    budget = config["budget"]
    _expect("A1 seeds", config["intervention"]["seeds"], [0, 1, 2])
    _expect("fit workers", config["execution"]["fit_workers"], 6)
    _expect("A1 modes", list(INTERVENTION_MODES), ["gradnorm", "uncertainty"])
    ids = set()
    counts = Counter()
    modes = Counter()

    def register(identity):
        digest = identity.digest
        if digest in ids:
            raise RuntimeError(f"Duplicate scientific identity: {identity.payload()}")
        ids.add(digest)

    for unit in fit_identities():
        register(unit)
        counts[unit.arm, unit.phase] += 1
        modes[unit.variant, unit.phase] += 1
    _expect("scheduled fit arms", {arm for arm, _ in counts}, set(ARMS))
    for arm in ARMS:
        _expect(arm, [counts[arm, phase] for phase in PHASES], budget[arm])
    for mode, expected in budget["intervention_by_mode"].items():
        _expect(mode, [modes[mode, phase] for phase in PHASES], expected)
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
            {"fit_total": 1200, "diagnostic_slots": 600, "diagnostic_batch_pairs": 4800,
             "gradient_extractions": 38400})
    for label, value in totals.items():
        _expect(f"configuration {label}", budget[label], value)
    return {**{arm: budget[arm] for arm in ARMS}, "intervention_by_mode": budget["intervention_by_mode"],
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
