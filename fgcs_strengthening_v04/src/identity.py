"""Canonical scientific identities, independent of execution metadata."""

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType

NAMESPACE = "fgcs-strengthening-v03"
HOME = Path(__file__).resolve().parents[1]
ROOT = HOME.parent
CONFIG = HOME / "configs/protocol_v03.json"


def read_config():
    return json.loads(CONFIG.read_text())


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


_config = read_config()
RESOURCES = tuple(_config["resources"])
BLOCK_ENTITIES = MappingProxyType({block: frozenset(spec["entities"]) for block, spec in _config["blocks"].items()})
SCOPES = MappingProxyType({name: spec["input_scope"] for name, spec in _config["formulations"].items()})
MODERN_SCOPES = MappingProxyType({name: spec["scope"] for name, spec in _config["modern"]["families"].items()})
ARMS = frozenset({
    "core", "capacity", "pairwise", "leave_one_out", "pcgrad", "gradnorm",
    "lightgbm", "modern", "diagnostic", "checkpoint_request",
})


def canonical_tasks(tasks):
    """Treat a declared task subset as a set, with one canonical axis order."""
    tasks = tuple(tasks)
    if not tasks or len(set(tasks)) != len(tasks) or not set(tasks) <= set(RESOURCES):
        raise ValueError(f"Invalid task subset: {tasks}")
    return tuple(task for task in RESOURCES if task in tasks)


@dataclass(frozen=True, slots=True)
class ScientificIdentity:
    block: str
    entity: str
    fold: int
    seed: int
    phase: str
    arm: str
    formulation: str
    tasks: tuple[str, ...]
    input_scope: str
    hidden_size: int | None
    variant: str

    def __post_init__(self):
        if (self.block not in BLOCK_ENTITIES or self.entity not in BLOCK_ENTITIES[self.block]
                or type(self.fold) is not int or self.fold not in _config["folds"]
                or type(self.seed) is not int or self.seed not in _config["core_seeds"]
                or self.phase not in _config["phases"] or self.arm not in ARMS
                or self.input_scope not in ("own", "all")
                or not isinstance(self.variant, str) or not self.variant
                or (self.hidden_size is not None and type(self.hidden_size) is not int)):
            raise ValueError("Invalid scientific identity")
        object.__setattr__(self, "tasks", canonical_tasks(self.tasks))
        self._validate_design()

    def _validate_design(self):
        arm, model, tasks = self.arm, self.formulation, self.tasks
        secondary = _config["secondary"]
        if arm in {"pairwise", "leave_one_out", "pcgrad", "gradnorm", "lightgbm", "checkpoint_request"}:
            if self.block not in secondary["blocks"] or self.seed not in secondary["seeds"]:
                raise ValueError("Identity outside reduced scope")
        if model in SCOPES:
            self._validate_lstm_identity(arm, model, tasks)
            return
        if arm == "modern" and model in MODERN_SCOPES:
            if (self.entity in _config["modern"]["cohorts"].get(self.block, [])
                    and self.seed == _config["modern"]["seed"] and self.hidden_size is None
                    and self.input_scope == MODERN_SCOPES[model]
                    and ((self.variant == "independent" and len(tasks) == 1)
                         or (self.variant == "shared" and tasks == RESOURCES))):
                return
        if arm == "lightgbm" and model == "LightGBM":
            grid = _config["lightgbm"]["grid"]
            variants = {
                tree_variant(leaves, rate, estimators)
                for leaves in grid["leaves"] for rate in grid["learning_rate"]
                for estimators in grid["estimators"]
            } if self.phase == "inner" else {"selected"}
            if (self.seed == _config["lightgbm"]["seed"] and self.hidden_size is None
                    and len(tasks) == 1 and self.variant in variants):
                return
        raise ValueError("Invalid non-LSTM scientific identity")

    def _validate_lstm_identity(self, arm, model, tasks):
        lstm = _config["lstm"]
        if (self.input_scope != SCOPES[model] or self.hidden_size !=
                lstm["m0_capacity_hidden_size" if arm == "capacity" else "primary_hidden_size"]):
            raise ValueError("LSTM scope or width differs from protocol")
        if arm == "core" and self.variant == "baseline":
            if (model in {"S1", "S2"} and len(tasks) == 1) or (model in {"M0", "M1"} and tasks == RESOURCES):
                return
        if arm == "capacity" and model == "M0" and tasks == RESOURCES and self.variant == "baseline":
            return
        sizes = _config["secondary"]["task_subset_sizes"]
        if arm in sizes and model in {"M0", "M1"} and len(tasks) == sizes[arm] and self.variant == "baseline":
            return
        if arm in {"pcgrad", "gradnorm"} and model == "M1" and tasks == RESOURCES and self.variant == arm:
            return
        if self.phase == "final":
            if arm == "diagnostic" and model in {"M0", "M1"} and tasks == RESOURCES and self.variant in _config["diagnostics"]["slots"]:
                return
            if arm == "checkpoint_request" and model == "M1" and len(tasks) == 1 and self.variant == "task_selected":
                return
        raise ValueError("Invalid LSTM scientific identity")

    def payload(self):
        payload = asdict(self)
        payload["tasks"] = list(self.tasks)
        return {"namespace": NAMESPACE, "schema_version": 1, **payload}

    @property
    def digest(self):
        return sha256(canonical_json(self.payload())).hexdigest()


def tree_variant(leaves, rate, estimators):
    return f"leaves={leaves},lr={rate},estimators={estimators}"
