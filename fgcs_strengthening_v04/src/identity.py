"""Canonical scientific identities, independent of execution metadata."""

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType

NAMESPACE = "fgcs-strengthening-v04"
HOME = Path(__file__).resolve().parents[1]
ROOT = HOME.parent
CONFIG = HOME / "configs/protocol_v04.json"


def read_config():
    return json.loads(CONFIG.read_text())


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


_config = read_config()
RESOURCES = tuple(_config["resources"])
# v0.4 fits only the 20-VM cohort; the full block entity lists remain frozen data references.
BLOCK_ENTITIES = MappingProxyType({block: frozenset(entities) for block, entities in _config["cohort"].items()})
SCOPES = MappingProxyType({name: spec["input_scope"] for name, spec in _config["formulations"].items()})
MODERN_SCOPES = MappingProxyType({name: tuple(spec["scopes"]) for name, spec in _config["modern"]["families"].items()})
ARMS = frozenset({"core", "pairwise", "leave_one_out", "modern", "diagnostic"})


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

    @property
    def cell(self):
        """The 2x2 cell (S1, S2, M0 or M1) of a core or modern fit; None otherwise."""
        if self.arm == "core":
            return self.formulation
        if self.arm == "modern":
            return {("own", "independent"): "S1", ("all", "independent"): "S2",
                    ("own", "shared"): "M0", ("all", "shared"): "M1"}[self.input_scope, self.variant]
        return None

    def _validate_design(self):
        arm, model, tasks = self.arm, self.formulation, self.tasks
        if arm in {"pairwise", "leave_one_out"}:
            secondary = _config["secondary"]
            if self.block not in secondary["blocks"] or self.seed not in secondary["seeds"]:
                raise ValueError("Identity outside the transfer lattice scope")
        if model in SCOPES:
            self._validate_lstm_identity(arm, model, tasks)
            return
        if arm == "modern" and model in MODERN_SCOPES:
            if (self.seed in _config["modern"]["seeds"] and self.hidden_size is None
                    and self.input_scope in MODERN_SCOPES[model]
                    and ((self.variant == "independent" and len(tasks) == 1)
                         or (self.variant == "shared" and tasks == RESOURCES))):
                return
        raise ValueError("Invalid non-LSTM scientific identity")

    def _validate_lstm_identity(self, arm, model, tasks):
        if self.input_scope != SCOPES[model] or self.hidden_size != _config["lstm"]["primary_hidden_size"]:
            raise ValueError("LSTM scope or width differs from protocol")
        if arm == "core" and self.variant == "baseline":
            if (model in {"S1", "S2"} and len(tasks) == 1) or (model in {"M0", "M1"} and tasks == RESOURCES):
                return
        sizes = _config["secondary"]["task_subset_sizes"]
        if (arm in sizes and model == "M1" and self.input_scope in _config["secondary"]["input_scopes"]
                and len(tasks) == sizes[arm] and self.variant == "baseline"):
            return
        if (self.phase == "final" and arm == "diagnostic" and model in _config["diagnostics"]["formulations"]
                and tasks == RESOURCES and self.variant in _config["diagnostics"]["extracted_slots"]):
            return
        raise ValueError("Invalid LSTM scientific identity")

    def payload(self):
        payload = asdict(self)
        payload["tasks"] = list(self.tasks)
        return {"namespace": NAMESPACE, "schema_version": 1, **payload}

    @property
    def digest(self):
        return sha256(canonical_json(self.payload())).hexdigest()

