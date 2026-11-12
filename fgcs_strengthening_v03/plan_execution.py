"""Enumerate and validate the fixed v0.3 schedule without executing any units.

Invoke from the repository root with python -m fgcs_strengthening_v03.plan_execution.
"""

import argparse
from collections import Counter
from itertools import product
import json
import sys

from .src.identity import RESOURCES, SCOPES, ScientificIdentity, read_config
from .src.transfer.design import group_identities
from .src.modern.design import modern_identities, pilot_context
from .src.tree.design import tree_identities


def _groups(config, blocks, seeds):
    for block in blocks:
        yield from ((block, entity, fold, seed)
                    for entity, fold, seed in product(config["blocks"][block]["entities"], config["folds"], seeds))


def fit_identities():
    config = read_config()
    primary = config["lstm"]["primary_hidden_size"]
    width = config["lstm"]["m0_capacity_hidden_size"]
    phases = config["phases"]
    single = tuple((task,) for task in RESOURCES)
    for group in _groups(config, config["blocks"], config["core_seeds"]):
        for phase in phases:
            for model, scope in SCOPES.items():
                for tasks in single if model.startswith("S") else (RESOURCES,):
                    yield ScientificIdentity(*group, phase, "core", model, tasks, scope, primary, "baseline")
            yield ScientificIdentity(*group, phase, "capacity", "M0", RESOURCES, "own", width, "baseline")

    secondary = config["secondary"]
    for group in _groups(config, secondary["blocks"], secondary["seeds"]):
        for phase in phases:
            yield from group_identities(*group, phase)
            for arm in ("pcgrad", "gradnorm"):
                yield ScientificIdentity(*group, phase, arm, "M1", RESOURCES, "all", primary, arm)

    yield from tree_identities()

    yield from modern_identities()


def overhead_identities():
    config = read_config()
    width = config["lstm"]["primary_hidden_size"]
    diagnostics = config["diagnostics"]
    for group in _groups(config, config["blocks"], config["core_seeds"]):
        for model, slot in product(diagnostics["formulations"], diagnostics["slots"]):
            yield ScientificIdentity(*group, "final", "diagnostic", model, RESOURCES, SCOPES[model], width, slot)
    secondary = config["secondary"]
    for group in _groups(config, secondary["blocks"], secondary["seeds"]):
        for task in RESOURCES:
            yield ScientificIdentity(*group, "final", "checkpoint_request", "M1", (task,), "all", width, "task_selected")


def _expect(label, actual, expected):
    if actual != expected:
        raise RuntimeError(f"{label}: observed {actual}, expected {expected}")


def validate_schedule():
    config = read_config()
    budget = config["budget"]
    locked_fits = {
        "core": [45500, 45500], "capacity": [4550, 4550],
        "pairwise": [12600, 12600], "leave_one_out": [8400, 8400],
        "pcgrad": [1050, 1050], "gradnorm": [1050, 1050],
        "modern": [1500, 1500], "lightgbm": [22400, 2800],
    }
    _expect("core seeds", config["core_seeds"], [0, 1, 2, 3, 4])
    phases = ("inner", "final")
    ids = set()
    counts = Counter()
    pilot = Counter()
    core_seeds = set()
    modern = Counter()
    checkpoints = set()

    def register(identity):
        digest = identity.digest
        if digest in ids:
            raise RuntimeError(f"Duplicate scientific identity: {identity.payload()}")
        ids.add(digest)

    for unit in fit_identities():
        register(unit)
        counts[unit.arm, unit.phase] += 1
        if unit.arm == "core":
            core_seeds.add(unit.seed)
        if unit.arm == "modern":
            modern[unit.formulation, unit.phase] += 1
            if pilot_context(unit) is not None:
                pilot[unit.block, unit.entity, unit.fold, unit.formulation] += 1

    _expect("enumerated core seeds", core_seeds, {0, 1, 2, 3, 4})
    _expect("scheduled fit arms", {arm for arm, _ in counts}, set(locked_fits))
    for arm, expected in locked_fits.items():
        _expect(f"configuration {arm}", budget[arm], expected)
        _expect(arm, [counts[arm, phase] for phase in phases], expected)
    for family in ("DLinear", "PatchTST", "iTransformer"):
        _expect(family, [modern[family, phase] for phase in phases], [500, 500])
    expected_pilot = {(block, entity, 1, family): 5
                      for block, entity in (("fastStorage", "697"), ("Rnd", "99"))
                      for family in ("DLinear", "PatchTST", "iTransformer")}
    _expect("pilot complements", dict(pilot), expected_pilot)

    overhead = Counter()
    for unit in overhead_identities():
        register(unit)
        overhead[unit.arm] += 1
        if unit.arm == "checkpoint_request":
            checkpoints.add((unit.block, unit.entity, unit.fold, unit.seed))
    pairs = overhead["diagnostic"] * config["diagnostics"]["pairs"]
    gradients = pairs * len(config["diagnostics"]["batches"]) * config["diagnostics"]["tasks_per_batch"]
    neural = [sum(counts[arm, phase] for arm in locked_fits if arm != "lightgbm") for phase in phases]
    tree = [counts["lightgbm", phase] for phase in phases]
    scalar = [value * config["lightgbm"]["estimators_per_wrapper"] for value in tree]
    wrappers = [net + wrapped for net, wrapped in zip(neural, tree, strict=True)]
    totals = {
        "modern_pilot_subset": sum(pilot.values()), "diagnostic_slots": overhead["diagnostic"],
        "diagnostic_batch_pairs": pairs, "gradient_extractions": gradients,
        "checkpoint_trajectories": len(checkpoints), "checkpoint_requests": overhead["checkpoint_request"],
        "neural": neural, "tree_scalar": scalar, "wrappers_total": wrappers,
        "scalar_adjusted_total": sum(neural) + sum(scalar),
    }
    fixed = {
        "modern_pilot_subset": 30, "diagnostic_slots": 27300, "diagnostic_batch_pairs": 218400,
        "gradient_extractions": 1747200, "checkpoint_trajectories": 1050, "checkpoint_requests": 4200,
        "neural": [74650, 74650], "tree_scalar": [112000, 14000], "wrappers_total": [97050, 77450],
        "scalar_adjusted_total": 275300,
    }
    _expect("logical and fit totals", totals, fixed)
    for label, value in totals.items():
        _expect(f"configuration {label}", budget[label], value)
    return {**locked_fits, **totals, "fit_total": sum(wrappers), "identity_total": len(ids)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-identities", action="store_true", help="emit JSON Lines to stdout instead of totals")
    args = parser.parse_args(argv)
    summary = validate_schedule()
    if args.list_identities:
        config = read_config()
        for identity_group in (fit_identities(), overhead_identities()):
            for unit in identity_group:
                print(json.dumps({"id": unit.digest, **unit.payload(), "pilot_context": pilot_context(unit)}))
    else:
        json.dump(summary, sys.stdout, indent=2)
        print()


if __name__ == "__main__":
    main()
