"""Registered v0.4 transfer-lattice identities and directed matrix entries (D-5, D-6)."""

from collections import Counter
from dataclasses import dataclass
from itertools import combinations, product
import json

from ..identity import RESOURCES, ScientificIdentity, read_config

_CONFIG = read_config()
_SECONDARY = _CONFIG["secondary"]
BLOCKS = tuple(_SECONDARY["blocks"])
SEEDS = tuple(_SECONDARY["seeds"])
FOLDS = tuple(_CONFIG["folds"])
SCOPES = tuple(_SECONDARY["input_scopes"])
ARMS = tuple(_SECONDARY["task_subset_sizes"])
PAIRWISE = tuple(combinations(RESOURCES, 2))
LEAVE_ONE_OUT = tuple(tuple(task for task in RESOURCES if task != omitted) for omitted in RESOURCES)
_SUBSETS = {"pairwise": PAIRWISE, "leave_one_out": LEAVE_ONE_OUT}
_MODELS = {"own": ("S1", "M0"), "all": ("S2", "M1")}
_SIGNS = {"F": "positive favours sharing", "Q": "positive favours adding source supervision"}
_WIDTH = _CONFIG["lstm"]["primary_hidden_size"]


def group_identities(block, entity, fold, seed, phase):
    for arm in ARMS:
        for scope, tasks in product(SCOPES, _SUBSETS[arm]):
            yield ScientificIdentity(block, entity, fold, seed, phase, arm, _MODELS[scope][1],
                                     tasks, scope, _WIDTH, "baseline")


def transfer_identities():
    for block in BLOCKS:
        for entity, fold, seed, phase in product(_CONFIG["cohort"][block], FOLDS, SEEDS,
                                                 _CONFIG["phases"]):
            yield from group_identities(block, entity, fold, seed, phase)


def dry_budget():
    counts = Counter()
    seen = set()
    for identity in transfer_identities():
        if identity.digest in seen:
            raise RuntimeError("Duplicate transfer identity")
        seen.add(identity.digest)
        counts[identity.arm, identity.phase] += 1
    budget = {arm: {phase: counts[arm, phase] for phase in ("inner", "final")} for arm in ARMS}
    expected = {arm: dict(zip(("inner", "final"), _CONFIG["budget"][arm])) for arm in ARMS}
    if budget != expected or len(seen) != sum(sum(_CONFIG["budget"][arm]) for arm in ARMS):
        raise RuntimeError(f"Transfer identity budget differs from v0.4: {budget}")
    return budget


@dataclass(frozen=True, slots=True)
class MatrixEntry:
    block: str
    scope: str
    arm: str
    estimand: str
    source_task: str
    target_task: str
    subset: tuple[str, ...]
    source_role: str
    comparator: str
    sign_convention: str

    @property
    def test_id(self):
        return "/".join((self.block, self.scope, self.arm, self.estimand, self.target_task, self.source_task))

    def model_identities(self, entity, fold, seed):
        """Exact final scientific identities in the order of the log ratio."""
        if type(seed) is not int or seed not in SEEDS:
            raise ValueError("Transfer comparisons require the registered three-seed slice")
        independent, shared = _MODELS[self.scope]
        prefix = (self.block, entity, fold, seed, "final")
        subset = ScientificIdentity(*prefix, self.arm, shared, self.subset, self.scope, _WIDTH, "baseline")
        if self.estimand == "F":
            reference = ScientificIdentity(*prefix, "core", independent, (self.target_task,),
                                           self.scope, _WIDTH, "baseline")
            return reference, subset
        full = ScientificIdentity(*prefix, "core", shared, RESOURCES, self.scope, _WIDTH, "baseline")
        return subset, full


@dataclass(frozen=True, slots=True)
class TransferMatrix:
    block: str
    scope: str
    arm: str
    estimand: str
    entries: tuple[MatrixEntry, ...]

    @property
    def matrix_id(self):
        return "/".join((self.block, self.scope, self.arm, self.estimand))


def _matrix(block, scope, arm, estimand):
    independent, shared = _MODELS[scope]
    comparator = independent if estimand == "F" else shared
    entries = []
    for target, source in product(RESOURCES, repeat=2):
        if target == source:
            continue
        if arm == "pairwise":
            subset = tuple(task for task in RESOURCES if task in (target, source))
            role = "sharing_partner"
        else:
            subset = tuple(task for task in RESOURCES if task != source)
            role = "omitted_supervision"
        entries.append(MatrixEntry(block, scope, arm, estimand, source, target, subset, role,
                                   comparator, _SIGNS[estimand]))
    return TransferMatrix(block, scope, arm, estimand, tuple(entries))


def transfer_matrices():
    for block, scope in product(BLOCKS, SCOPES):
        for arm, estimand in (("pairwise", "F"), ("leave_one_out", "F"), ("leave_one_out", "Q")):
            yield _matrix(block, scope, arm, estimand)


if __name__ == "__main__":
    print(json.dumps(dry_budget(), indent=2))
