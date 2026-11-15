"""Typed systems records tied to immutable scientific and environment fingerprints."""

from dataclasses import asdict, dataclass
from hashlib import sha256
import math
import re

from .identity import RESOURCES, ScientificIdentity, canonical_json

_SHA = re.compile(r"[0-9a-f]{64}")
MODES = ("forward_only", "end_to_end_in_memory")
BATCHES = (1, 128)
WARMUPS = 20
REPETITIONS = 100
COST_LABELS = ("selection_cost", "final_fit_cost", "checkpoint_tail_cost", "diagnostic_cost",
               "pcgrad_overhead", "gradnorm_overhead")


def digest(value):
    return sha256(canonical_json(value)).hexdigest()


def require_sha(*values):
    if any(not isinstance(value, str) or not _SHA.fullmatch(value) for value in values):
        raise ValueError("Exact SHA-256 model and measurement provenance are required")


@dataclass(frozen=True, slots=True)
class CheckpointRef:
    identity: ScientificIdentity
    checkpoint_sha256: str
    outcome_sha256: str
    epoch: int | None
    horizon: int | None = None

    def __post_init__(self):
        if not isinstance(self.identity, ScientificIdentity) or self.identity.phase != "final":
            raise ValueError("Expected a final scientific identity")
        require_sha(self.checkpoint_sha256, self.outcome_sha256)
        if self.identity.arm == "lightgbm":
            if self.epoch is not None or type(self.horizon) is not int or self.horizon not in (1, 2, 4, 9, 18):
                raise ValueError("LightGBM provenance requires a scalar horizon")
        elif type(self.epoch) is not int or not 1 <= self.epoch <= 50 or self.horizon is not None:
            raise ValueError("Neural provenance requires a selected checkpoint epoch")

    def payload(self):
        return {"identity": self.identity.payload(), "identity_sha256": self.identity.digest,
                "checkpoint_sha256": self.checkpoint_sha256, "outcome_sha256": self.outcome_sha256,
                "epoch": self.epoch, "horizon": self.horizon}


@dataclass(frozen=True, slots=True)
class MeasurementBinding:
    checkpoints: tuple[CheckpointRef, ...]
    formulation: str
    context: int
    tasks: tuple[str, ...]
    hardware_sha256: str
    software_sha256: str
    origins_sha256: str
    protocol_sha256: str
    config_sha256: str
    source_sha256: str
    input_sha256: str
    run_identities: tuple[ScientificIdentity, ...]
    target_checkpoint_sha256s: tuple[tuple[str, tuple[str, ...]], ...]
    warmups: int = WARMUPS
    repetitions: int = REPETITIONS

    def __post_init__(self):
        require_sha(self.hardware_sha256, self.software_sha256, self.origins_sha256,
                    self.protocol_sha256, self.config_sha256, self.source_sha256, self.input_sha256)
        if (not self.checkpoints or any(not isinstance(ref, CheckpointRef) for ref in self.checkpoints)
                or not self.run_identities or any(not isinstance(unit, ScientificIdentity) or unit.phase != "final"
                                                   for unit in self.run_identities)
                or not self.formulation or type(self.context) is not int or self.context < 1
                or not self.tasks or tuple(task for task in RESOURCES if task in self.tasks) != self.tasks
                or (self.warmups, self.repetitions) != (WARMUPS, REPETITIONS)):
            raise ValueError("Incomplete model, task or registered measurement condition")
        valid = {ref.checkpoint_sha256 for ref in self.checkpoints}
        if (tuple(task for task, _ in self.target_checkpoint_sha256s) != self.tasks
                or any(not hashes or set(hashes) - valid for _, hashes in self.target_checkpoint_sha256s)):
            raise ValueError("Every logical target requires its exact deployed checkpoint hash")

    def payload(self):
        record = asdict(self)
        record["checkpoints"] = [ref.payload() for ref in self.checkpoints]
        record["run_identities"] = [unit.payload() for unit in self.run_identities]
        return record


@dataclass(frozen=True, slots=True)
class MeasurementRecord:
    provenance: MeasurementBinding

    def __post_init__(self):
        if not isinstance(self.provenance, MeasurementBinding):
            raise ValueError("Measurement requires complete model and hardware provenance")


@dataclass(frozen=True, slots=True)
class Footprint(MeasurementRecord):
    artifact: CheckpointRef
    trainable_parameters: int | None
    raw_tensor_bytes: int
    uncompressed_model_bytes: int
    optimizer_state_bytes: int | None


@dataclass(frozen=True, slots=True)
class Deployment(MeasurementRecord):
    physical_checkpoint_count: int
    logical_target_models: int
    total_trainable_parameters: int | None
    total_deployed_bytes: int
    optimizer_state_bytes_by_fit: dict


@dataclass(frozen=True, slots=True)
class TrainingCost(MeasurementRecord):
    label: str
    worker_seconds: float
    validation_seconds: float
    checkpoint_serialization_seconds: float
    checkpoint_io_seconds: float
    failed_attempt_worker_seconds: float
    scheduler_elapsed_seconds: float | None
    optimisation_seconds: float
    completed_units: int
    failed_units: int
    outcome_sha256s: tuple[str, ...]
    tail_epochs: int = 0
    included_in_optimisation: bool = False

    def __post_init__(self):
        MeasurementRecord.__post_init__(self)
        if self.label not in COST_LABELS:
            raise ValueError("Unknown registered cost label")
        for value in (self.worker_seconds, self.optimisation_seconds, self.validation_seconds,
                      self.checkpoint_serialization_seconds, self.checkpoint_io_seconds,
                      self.failed_attempt_worker_seconds, self.scheduler_elapsed_seconds):
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError("Cost durations must be finite and nonnegative")
        require_sha(*self.outcome_sha256s)


@dataclass(frozen=True, slots=True)
class InferenceLatency(MeasurementRecord):
    timing_mode: str
    batch_size: int
    subject: str
    available: bool
    median_ms: float | None
    p95_ms: float | None
    mean_ms: float | None
    durations_ns: tuple[int, ...]
    unavailable_reason: str | None = None


@dataclass(frozen=True, slots=True)
class InferenceThroughput(MeasurementRecord):
    timing_mode: str
    batch_size: int
    subject: str
    forecasts_per_second: float | None


@dataclass(frozen=True, slots=True)
class PeakMemory(MeasurementRecord):
    subject: str
    timing_mode: str
    batch_size: int | None
    baseline_rss_bytes: int
    peak_rss_bytes: int
    peak_increment_bytes: int
    platform_interpretation: str
    worker_pid: int
