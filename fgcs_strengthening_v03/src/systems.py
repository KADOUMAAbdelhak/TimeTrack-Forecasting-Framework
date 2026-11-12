"""Registered CPU systems measurements. Nothing is executed on import."""

from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
import fcntl
from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter_ns
import zipfile

import numpy as np
import torch
from torch import nn

from .data_adapters import PreparedPartition
from .identity import RESOURCES, ROOT, ScientificIdentity, canonical_json, read_config
from .models.lightgbm import FeatureLayout
from .models.lstm import LSTM
from .models.registry import REGISTRY
from .provenance import DuplicateIdentity, Fingerprints, Journal, ProvenanceError, _atomic_publish
from .systems_environment import ENV_THREADS, MachineManifest, require_environment
from .systems_records import (
    BATCHES, COST_LABELS, MODES, REPETITIONS, WARMUPS, CheckpointRef, Deployment, Footprint, InferenceLatency,
    InferenceThroughput, MeasurementBinding, PeakMemory, TrainingCost, digest, require_sha,
)
from .training import _state_hash

_CONFIG = read_config()
_SPEC = _CONFIG["systems_spec"]
_SOURCES = tuple((Path(__file__).parent / name).resolve().relative_to(ROOT).as_posix() for name in (
    "systems.py", "systems_environment.py", "systems_records.py", "systems_worker.py",
))
_MODELS = {"core", "capacity", "pcgrad", "gradnorm", "modern", "lightgbm", "checkpoint_request"}
_ROW_TYPES = (Footprint, Deployment, TrainingCost, InferenceLatency, InferenceThroughput, PeakMemory)


def systems_fingerprints():
    from ..analyse_study import _sources
    return Fingerprints.capture_protocol(additional_sources=(*_sources(), *_SOURCES))


@dataclass(frozen=True, slots=True)
class OriginManifest:
    origin_key_sha256: str
    legal_support_sha256: str
    legal_origin_count: int
    positions: tuple[int, ...]
    origin_ids: tuple[int | str, ...]

    @property
    def sha256(self):
        return digest(asdict(self))

    def count_for(self, batch_size):
        if type(batch_size) is not int or batch_size not in BATCHES:
            raise ValueError("Only batch 1 and batch 128 are registered")
        return batch_size if len(self.positions) >= batch_size else None


def partition_origin_key(block, entity, fold):
    """C1: one benchmark origin sample per partition, shared by every model compared there."""
    return digest(["fgcs-v03", "systems-origins", block, entity, fold])


def sample_origins(origin_key_sha256, legal_ids):
    """Sample 128 origins once; on short support draw only the batch-1 origin."""
    require_sha(origin_key_sha256)
    ids = tuple(legal_ids)
    if any(type(value) not in (int, str) for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("Expected unique exact legal test origin IDs")
    key = sha256(f"fgcs-v03|systems-origins|{origin_key_sha256}".encode()).digest()
    rng = np.random.Generator(np.random.PCG64(int.from_bytes(key[:8], "little")))
    count = 128 if len(ids) >= 128 else int(bool(ids))
    positions = tuple(rng.choice(len(ids), size=count, replace=False).tolist()) if count else ()
    return OriginManifest(origin_key_sha256, digest(ids), len(ids), positions, tuple(ids[i] for i in positions))


def _uncompressed_torch(encoded):
    with zipfile.ZipFile(io.BytesIO(encoded)) as stream:
        if any(member.compress_type != zipfile.ZIP_STORED for member in stream.infolist()):
            raise ProvenanceError("Expected uncompressed Torch state_dict checkpoint bytes")
    return len(encoded)


@dataclass(frozen=True, slots=True)
class PhysicalState:
    ref: CheckpointRef
    encoded_bytes: int
    trainable_parameters: int | None
    raw_tensor_bytes: int
    optimizer_state_bytes: int | None


def torch_footprint(ref, model, encoded, *, optimizer_state_bytes=None):
    if sha256(encoded).hexdigest() != ref.checkpoint_sha256:
        raise ProvenanceError("Footprint model bytes do not match the checkpoint fingerprint")
    state = model.state_dict()
    return PhysicalState(ref, _uncompressed_torch(encoded),
                         sum(p.numel() for p in model.parameters() if p.requires_grad),
                         sum(t.numel() * t.element_size() for t in state.values()), optimizer_state_bytes)


@dataclass(frozen=True, slots=True)
class ForwardPath:
    """One neural state or one five-scalar tree wrapper with explicit target routing."""

    tasks: tuple[str, ...]
    states: tuple[PhysicalState, ...]
    model: object
    context: int

    @property
    def identity(self):
        return self.states[0].ref.identity

    def prepare(self, scaled):
        identity = self.identity
        if identity.arm == "lightgbm":
            return FeatureLayout(self.context, identity.tasks[0], identity.input_scope).flatten(scaled)
        if identity.arm == "modern" and identity.input_scope == "own" and identity.variant == "independent":
            index = RESOURCES.index(identity.tasks[0])
            scaled = scaled[:, :, index:index + 1]
        return torch.from_numpy(np.ascontiguousarray(scaled))

    def forward(self, prepared):
        if self.identity.arm == "lightgbm":
            output = np.stack([booster.predict(prepared, num_threads=1, num_iteration=-1)
                               for booster in self.model], axis=-1)[:, None, :]
        else:
            output = self.model(prepared)
        return {task: output[:, self.identity.tasks.index(task), :] for task in self.tasks}


class Complement:
    def __init__(self, paths, *, task_checkpoints=False):
        self.paths = tuple(paths)
        self.task_checkpoints = task_checkpoints
        if not self.paths or any(not path.states for path in self.paths):
            raise ValueError("Expected a registered complement with checkpoint states")
        first = self.paths[0].identity
        group = (first.block, first.entity, first.fold, first.seed, first.arm, first.formulation,
                 first.hidden_size, first.input_scope, first.variant)
        if any((i.block, i.entity, i.fold, i.seed, i.arm, i.formulation, i.hidden_size, i.input_scope, i.variant)
               != group or i.phase != "final" for path in self.paths for i in (path.identity,)):
            raise ValueError("Complement mixes incompatible model identities")
        contexts = {path.context for path in self.paths}
        routed = tuple(task for path in self.paths for task in path.tasks)
        if len(contexts) != 1 or len(routed) != 4 or set(routed) != set(RESOURCES):
            raise ValueError("Complement must cover the four targets at one frozen context")
        if any(not set(path.tasks) <= set(path.identity.tasks) for path in self.paths):
            raise ValueError("Path does not produce its declared targets")
        independent = first.formulation in ("S1", "S2", "LightGBM") or first.variant == "independent"
        if task_checkpoints:
            if first.formulation != "M1" or first.arm != "core" or independent or len(self.paths) > 4:
                raise ValueError("Task checkpoints require the registered core M1 complement")
        elif len(self.paths) != (4 if independent else 1) or (
                independent and tuple(path.tasks for path in self.paths) != tuple((r,) for r in RESOURCES)):
            raise ValueError("Physical paths differ from the registered complement")
        for path in self.paths:
            if first.arm == "lightgbm":
                if tuple(state.ref.horizon for state in path.states) != (1, 2, 4, 9, 18):
                    raise ValueError("LightGBM wrapper requires five direct scalar artifacts")
            elif len(path.states) != 1:
                raise ValueError("Each neural path requires one exact checkpoint")
        if len({(ref.identity.digest, ref.epoch, ref.horizon) for ref in self.refs}) != len(self.refs):
            raise ValueError("Shared physical states must be consolidated before measuring")
        self.context = contexts.pop()
        self.formulation = (f"{first.formulation}-task-checkpoints" if task_checkpoints else
                            f"{first.formulation}-{first.variant}" if first.arm == "modern" else
                            f"LightGBM-{first.input_scope}" if first.arm == "lightgbm" else
                            f"M0-H{first.hidden_size}" if first.formulation == "M0" else
                            f"{first.variant}-M1" if first.arm in ("pcgrad", "gradnorm") else first.formulation)
        self.logical_target_models = 4 if independent or task_checkpoints else 1

    @property
    def refs(self):
        return tuple(state.ref for path in self.paths for state in path.states)

    @property
    def states(self):
        return tuple(state for path in self.paths for state in path.states)

    def paths_for(self, subject):
        if subject == "complement":
            return self.paths
        if subject not in RESOURCES:
            raise ValueError("Unknown benchmark subject")
        return tuple(path for path in self.paths if subject in path.tasks)

    def prepared(self, scaled, subject):
        scaled = np.asarray(scaled)
        if scaled.dtype != np.float32 or scaled.ndim != 3 or scaled.shape[1:] != (self.context, 4):
            raise ValueError("Prepared benchmark inputs must be [batch, context, four] float32")
        return tuple((path, path.prepare(scaled)) for path in self.paths_for(subject))

    @staticmethod
    def forward(prepared, subject):
        output = {}
        for path, values in prepared:
            output.update(path.forward(values))
        tasks = RESOURCES if subject == "complement" else (subject,)
        return {task: output[task] for task in tasks}


def _load_complement(journal, identities, partition):
    if not identities or not isinstance(partition, PreparedPartition) or partition.phase != "final":
        raise ProvenanceError("Systems inputs require selected final fits and a verified final partition")
    if any(not isinstance(identity, ScientificIdentity) or identity.phase != "final" or identity.arm not in _MODELS
           or (identity.block, identity.entity, identity.fold) != (partition.block, partition.entity, partition.fold)
           for identity in identities):
        raise ProvenanceError("Invalid systems identity or final partition")
    task_control = identities[0].arm == "checkpoint_request"
    if task_control and tuple(i.tasks for i in identities) != tuple((r,) for r in RESOURCES):
        raise ProvenanceError("Expected four canonical logical checkpoint requests")
    groups = {}
    for identity in identities:
        if (identity.arm == "checkpoint_request") != task_control:
            raise ProvenanceError("Mixed checkpoint-request and standard deployment")
        parent = replace(identity, arm="core", tasks=RESOURCES, variant="baseline") if task_control else identity
        outcome, outcome_hash = journal.completed_evidence(parent)
        expected = {"context": partition.context, "split_hashes": dict(partition.split_hashes),
                    "support_sha256": partition.support_sha256, "scaler_sha256": partition.scaler_sha256,
                    "configuration_sha256": journal.seal.configuration[1]}
        if any(outcome.get(key) != value for key, value in expected.items()):
            raise ProvenanceError("Systems partition does not match the completed final fit")
        if task_control:
            epoch = outcome["selection"]["task_epochs"][identity.tasks[0]]
        else:
            epoch = outcome.get("primary_checkpoint_epoch")
        key = parent.digest, epoch
        if key not in groups:
            groups[key] = (parent, outcome, outcome_hash, [])
        groups[key][3].extend(identity.tasks)

    paths = []
    for (_, epoch), (parent, outcome, outcome_hash, tasks) in groups.items():
        if parent.arm == "lightgbm":
            import lightgbm
            if (outcome["lightgbm_version"] != lightgbm.__version__
                    or outcome["estimator_parameters"]["native"].get("num_threads") != 1
                    or outcome["estimator_parameters"]["native"].get("device_type", "cpu") != "cpu"):
                raise ProvenanceError("LightGBM runtime does not match the sealed CPU fit")
            boosters, states = [], []
            for row in outcome["models"]:
                encoded = journal.lightgbm_model_bytes(parent, row["horizon"], row["artifact"])
                ref = CheckpointRef(parent, row["model_sha256"], outcome_hash, None, row["horizon"])
                if sha256(encoded).hexdigest() != ref.checkpoint_sha256:
                    raise ProvenanceError("Scalar model fingerprint differs")
                booster = lightgbm.Booster(model_str=encoded.decode())
                if tuple(booster.feature_name()) != FeatureLayout(
                        partition.context, parent.tasks[0], parent.input_scope).names:
                    raise ProvenanceError("Restored LightGBM feature layout differs")
                boosters.append(booster)
                states.append(PhysicalState(ref, len(encoded), None, 0, None))
            paths.append(ForwardPath(tuple(tasks), tuple(states), tuple(boosters), partition.context))
            continue
        if not task_control and epoch != outcome["selection"]["joint_epoch"]:
            raise ProvenanceError("Systems model is not the primary selected checkpoint")
        artifact = outcome["checkpoints"][str(epoch)]
        encoded = journal.checkpoint_bytes(parent, epoch, artifact)
        state = torch.load(io.BytesIO(encoded), map_location="cpu", weights_only=True)
        if _state_hash(state) != artifact["model_sha256"]:
            raise ProvenanceError("Neural checkpoint tensor fingerprint differs")
        # Model construction is outside timed work and preserves the caller's CPU RNG.
        with torch.random.fork_rng(devices=[]), torch.device("cpu"):
            if parent.arm == "modern":
                model = REGISTRY[parent.formulation].build(partition.context, parent.tasks)
            else:
                model = LSTM(formulation=parent.formulation, block=parent.block, tasks=parent.tasks,
                             hidden_size=parent.hidden_size)
        model.load_state_dict(state, strict=True)
        model.eval()
        if any(p.device.type != "cpu" or p.dtype != torch.float32 for p in model.parameters()):
            raise ProvenanceError("Benchmarks require CPU float32 neural parameters")
        ref = CheckpointRef(parent, artifact["sha256"], outcome_hash, epoch)
        optimizer = outcome.get("optimizer_state_bytes")
        if optimizer is not None:
            optimizer += outcome.get("weight_optimizer_state_bytes", 0)
        footprint = torch_footprint(ref, model, encoded, optimizer_state_bytes=optimizer)
        paths.append(ForwardPath(tuple(tasks), (footprint,), model, partition.context))
    return Complement(paths, task_checkpoints=task_control)


def run_identity(identities):
    identities = tuple(identities)
    if not identities or len({identity.digest for identity in identities}) != len(identities):
        raise ValueError("Expected unique logical deployment identities")
    return identities[0].digest if len(identities) == 1 else digest([i.digest for i in identities])


def _seal_hashes(seal):
    inputs = dict(seal.inputs)
    return (inputs[_CONFIG["protocol"]["path"]], seal.configuration[1],
            digest(dict(seal.sources)), digest(inputs))


@dataclass(frozen=True, slots=True)
class BenchmarkPlan:
    complement: Complement
    origins: OriginManifest
    binding: MeasurementBinding
    raw_histories: np.ndarray
    scaled_histories: np.ndarray
    partition: PreparedPartition


def measure_calls(operation, *, clock=perf_counter_ns):
    """Time exactly the registered 20 warm-ups and 100 in-memory calls."""
    for _ in range(WARMUPS):
        operation()
    durations = []
    for _ in range(REPETITIONS):
        start = clock()
        operation()
        durations.append(clock() - start)
    if any(duration <= 0 for duration in durations):
        raise ValueError("Benchmark clock did not advance monotonically")
    return tuple(durations)


def summarise_durations(durations, batch_size):
    if (type(batch_size) is not int or batch_size not in BATCHES or len(durations) != REPETITIONS
            or any(type(value) is not int or value <= 0 for value in durations)):
        raise ValueError("Invalid registered batch or timing sample")
    samples = np.asarray(durations, dtype=np.float64)
    median, p95 = np.percentile(samples, [50, 95], method="linear") / 1e6
    mean_seconds = float(samples.mean() / 1e9)
    return float(median), float(p95), mean_seconds * 1e3, batch_size / mean_seconds


def _operation(plan, batch_size, mode, subject):
    if mode not in MODES:
        raise ValueError("Unknown benchmark timing mode")
    plan.complement.paths_for(subject)
    if plan.origins.count_for(batch_size) is None:
        return None
    if mode == "forward_only":
        prepared = plan.complement.prepared(plan.scaled_histories[:batch_size], subject)
        return lambda: plan.complement.forward(prepared, subject)
    raw = plan.raw_histories[:batch_size]

    def end_to_end():
        scaled = plan.partition.scale_benchmark_histories(raw)
        prepared = plan.complement.prepared(scaled, subject)
        output = plan.complement.forward(prepared, subject)
        return {task: plan.partition.inverse_target(
            value.numpy() if isinstance(value, torch.Tensor) else value, task)[0] for task, value in output.items()}

    return end_to_end


def inference_condition(plan, batch_size, mode, subject="complement", *, clock=perf_counter_ns):
    binding = plan.binding
    for path in plan.complement.paths_for(subject):
        if isinstance(path.model, nn.Module):
            path.model.eval()
    operation = _operation(plan, batch_size, mode, subject)
    if operation is None:
        latency = InferenceLatency(binding, mode, batch_size, subject, False, None, None, None, (),
                                   "insufficient_legal_test_origins")
        return latency, InferenceThroughput(binding, mode, batch_size, subject, None)
    with torch.inference_mode():
        durations = measure_calls(operation, clock=clock)
    median, p95, mean_ms, throughput = summarise_durations(durations, batch_size)
    return (InferenceLatency(binding, mode, batch_size, subject, True, median, p95, mean_ms, durations),
            InferenceThroughput(binding, mode, batch_size, subject, throughput))


def deployment_rows(complement, binding):
    if complement.refs != binding.checkpoints:
        raise ProvenanceError("Footprints differ from the measurement checkpoint provenance")
    footprints = tuple(Footprint(binding, state.ref, state.trainable_parameters, state.raw_tensor_bytes,
                                 state.encoded_bytes, state.optimizer_state_bytes) for state in complement.states)
    total = None if any(row.trainable_parameters is None for row in footprints) else sum(
        row.trainable_parameters for row in footprints)
    optimizer = {row.artifact.identity.digest: row.optimizer_state_bytes for row in footprints
                 if row.optimizer_state_bytes is not None}
    summary = Deployment(binding, len(footprints), complement.logical_target_models, total,
                         sum(row.uncompressed_model_bytes for row in footprints), optimizer)
    return footprints, summary


@dataclass(frozen=True, slots=True)
class FitTiming:
    identity: ScientificIdentity
    outcome_sha256: str
    status: str
    timings: dict
    tail_epochs: int = 0

    def __post_init__(self):
        require_sha(self.outcome_sha256)
        if (not isinstance(self.identity, ScientificIdentity) or self.status not in ("complete", "failed")
                or type(self.tail_epochs) is not int or self.tail_epochs < 0
                or any(not math.isfinite(value) or value < 0 for value in self.timings.values())):
            raise ValueError("Invalid journalled training timing")
        if self.identity.arm == "diagnostic":
            if set(self.timings) != {"diagnostic_seconds"} or self.tail_epochs:
                raise ValueError("Diagnostic timing must remain separate from training")
        elif "elapsed" not in self.timings or "diagnostic_seconds" in self.timings:
            raise ValueError("Fit timing requires elapsed worker time and excludes diagnostics")
        if self.identity.phase == "inner" and (self.tail_epochs or self.timings.get("checkpoint_tail_optimisation", 0)):
            raise ValueError("Inner candidates cannot carry checkpoint-tail time")


def read_fit_timing(journal, identity):
    status, evidence, outcome_hash = journal.terminal_evidence(identity)
    if identity.arm == "diagnostic":
        return FitTiming(identity, outcome_hash, status, {"diagnostic_seconds": evidence["diagnostic_seconds"]})
    return FitTiming(identity, outcome_hash, status, evidence["timing_seconds"],
                     evidence.get("checkpoint_tail_epochs", 0))


def training_costs(binding, timings, *, scheduler_elapsed=None):
    """Separate charged work. Intervention-only spans are included in optimisation."""
    timings = tuple(timings)
    if len({item.identity.digest for item in timings}) != len(timings):
        raise ValueError("Duplicate fit or diagnostic timing")
    scheduler = {} if scheduler_elapsed is None else scheduler_elapsed
    if set(scheduler) - set(COST_LABELS):
        raise ValueError("Scheduler elapsed time needs a registered cost label")
    inner = [item for item in timings if item.identity.phase == "inner"]
    final = [item for item in timings if item.identity.phase == "final" and item.identity.arm != "diagnostic"]
    diagnostic = [item for item in timings if item.identity.arm == "diagnostic"]

    def cost(label, items, fields, *, use_elapsed=False, overhead=False, captures=()):
        good = [item for item in items if item.status == "complete"]
        failures = [item for item in items if item.status == "failed"]
        sums = [math.fsum(item.timings.get(field, 0.) for item in good + list(captures)) for field in fields]
        worker = math.fsum(item.timings["elapsed"] for item in good) if use_elapsed else math.fsum(sums)
        failed_key = "diagnostic_seconds" if label == "diagnostic_cost" else "elapsed"
        failed = math.fsum(item.timings[failed_key] for item in failures)
        return TrainingCost(binding, label, worker, sums[1], sums[2], sums[3], failed, scheduler.get(label),
                            sums[0], len(good), len(failures),
                            tuple(item.outcome_sha256 for item in (*items, *captures)),
                            sum(item.tail_epochs for item in good) if label == "checkpoint_tail_cost" else 0, overhead)

    primary = ("primary_optimisation", "validation", "checkpoint_serialization", "checkpoint_io")
    rows = [cost("selection_cost", inner, primary, use_elapsed=True), cost("final_fit_cost", final, primary)]
    tails = [item for item in final if item.status == "complete" and (
        item.tail_epochs or item.timings.get("task_checkpoint_serialization", 0.))]
    rows.append(cost("checkpoint_tail_cost", tails,
                     ("checkpoint_tail_optimisation", "", "task_checkpoint_serialization", "task_checkpoint_io")))
    captures = [item for item in final if item.status == "complete"
                and item.timings.get("diagnostic_checkpoint_serialization", 0.)]
    rows.append(cost("diagnostic_cost", diagnostic,
                     ("diagnostic_seconds", "", "diagnostic_checkpoint_serialization", "diagnostic_checkpoint_io"),
                     captures=captures))
    for arm in ("pcgrad", "gradnorm"):
        label = arm + "_overhead"
        items = [item for item in timings if item.identity.arm == arm and item.status == "complete"]
        rows.append(cost(label, items, (label, "", "", ""), overhead=True))
    return tuple(rows)


def run_isolated(module, function, arguments, *, manifest=None):
    """Start a fresh interpreter. A null manifest is for generated test workloads."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.update({name: "1" for name in ENV_THREADS})
    request = {"module": module, "function": function, "arguments": arguments,
               "manifest": None if manifest is None else manifest.payload()}
    result = subprocess.run([sys.executable, "-B", "-m", "fgcs_strengthening_v03.src.systems_worker"],
                            cwd=ROOT, env=env, input=canonical_json(request), capture_output=True, check=True)
    return json.loads(result.stdout)


class SystemsRunner:
    """Explicit measured conditions on one sealed host and one verified deployment."""

    def __init__(self, journal, manifest):
        if not isinstance(journal, Journal):
            raise TypeError("Expected a Stage 3A journal")
        if not isinstance(manifest, MachineManifest):
            raise ProvenanceError("An explicit machine manifest is required")
        journal.seal.require_protocol(additional_sources=_SOURCES)
        manifest.conditions.require_registered()
        if (tuple(_SPEC["batches"]) != BATCHES or _SPEC["warmup_forwards"] != WARMUPS
                or _SPEC["timed_forwards"] != REPETITIONS or _SPEC["concurrent_workers"] != 1):
            raise ProvenanceError("Systems conditions differ from v0.3")
        self.journal, self.manifest = journal, manifest

    @contextmanager
    def _worker(self):
        require_environment(self.manifest)
        path = self.journal._path("systems", "worker.lock")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise ProvenanceError("Another benchmark worker already holds this run's CPU lock") from error
            self._publish_exact(self.journal._path("systems", "manifest.json"), self.manifest.payload())
            yield

    @staticmethod
    def _publish_exact(path, record):
        try:
            _atomic_publish(path, record)
        except DuplicateIdentity:
            if json.loads(path.read_text()) != record:
                raise ProvenanceError("Existing systems manifest differs") from None

    def prepare(self, identities, partition):
        with self._worker():
            plan = self._prepare(tuple(identities), partition)
            origin_record = json.loads(canonical_json(asdict(plan.origins)))
            self._publish_exact(self.journal._path("systems", "origins", f"{plan.origins.sha256}.json"), origin_record)
            return plan

    def _prepare(self, identities, partition):
        complement = _load_complement(self.journal, identities, partition)
        origins = sample_origins(partition_origin_key(partition.block, partition.entity, partition.fold),
                                 partition.benchmark_origin_ids())
        if origins.positions:
            raw = partition.benchmark_histories(origins.positions)
            scaled = partition.scale_benchmark_histories(raw)
            if (raw.shape != scaled.shape or scaled.shape != (len(origins.positions), partition.context, 4)
                    or scaled.dtype != np.float32 or not np.isfinite(raw).all() or not np.isfinite(scaled).all()):
                raise ProvenanceError("Invalid prepared benchmark histories")
        else:
            raw = scaled = np.empty((0, partition.context, 4), dtype=np.float32)
        routing = tuple((task, tuple(state.ref.checkpoint_sha256 for path in complement.paths_for(task)
                                     for state in path.states)) for task in RESOURCES)
        binding = MeasurementBinding(complement.refs, complement.formulation, partition.context, RESOURCES,
                                     self.manifest.hardware_sha256, self.manifest.software_sha256, origins.sha256,
                                     *_seal_hashes(self.journal.seal), identities, routing)
        return BenchmarkPlan(complement, origins, binding, raw, scaled, partition)

    def _verify_binding(self, binding):
        if not isinstance(binding, MeasurementBinding):
            raise ProvenanceError("Measurement requires complete model and hardware provenance")
        if ((binding.hardware_sha256, binding.software_sha256) !=
                (self.manifest.hardware_sha256, self.manifest.software_sha256)
                or (binding.protocol_sha256, binding.config_sha256, binding.source_sha256, binding.input_sha256)
                != _seal_hashes(self.journal.seal)):
            raise ProvenanceError("Measurement differs from the sealed host or study")

    def _verify_plan(self, plan):
        self._verify_binding(plan.binding)
        if (plan.complement.refs != plan.binding.checkpoints or plan.origins.sha256 != plan.binding.origins_sha256
                or plan.origins.origin_key_sha256 != partition_origin_key(
                    *(getattr(plan.binding.run_identities[0], name) for name in ("block", "entity", "fold")))):
            raise ProvenanceError("Prepared models or origins differ from the sealed measurement")

    def measure(self, plan, batch_size, mode, subject="complement"):
        self._verify_plan(plan)
        with self._worker():
            return inference_condition(plan, batch_size, mode, subject)

    def measure_complement(self, plan):
        self._verify_plan(plan)
        with self._worker():
            return tuple(row for subject in ("complement", *RESOURCES) for mode in MODES for batch in BATCHES
                         for row in inference_condition(plan, batch, mode, subject))

    def costs(self, plan, *, diagnostic_identities=(), scheduler_elapsed=None):
        from .tree.design import GRID

        self._verify_plan(plan)
        finals = {ref.identity for ref in plan.binding.checkpoints}
        units = set(finals)
        for unit in finals:
            if unit.arm == "lightgbm":
                units.update(replace(unit, phase="inner", variant=config.variant) for config in GRID)
            else:
                units.add(replace(unit, phase="inner"))
        for diagnostic in diagnostic_identities:
            if (diagnostic.arm != "diagnostic"
                    or replace(diagnostic, arm="core", variant="baseline") not in finals):
                raise ProvenanceError("Diagnostic timing does not belong to the measured deployment")
            units.add(diagnostic)
        timing = [read_fit_timing(self.journal, unit) for unit in sorted(units, key=lambda unit: unit.digest)]
        return training_costs(plan.binding, timing, scheduler_elapsed=scheduler_elapsed)

    def memory(self, plan, batch_size, mode, subject="complement"):
        self._verify_plan(plan)
        if mode not in MODES or subject not in ("complement", *RESOURCES):
            raise ValueError("Invalid registered inference memory condition")
        if plan.origins.count_for(batch_size) is None:
            return None
        with self._worker():
            result = run_isolated(
                __name__, "_memory_condition",
                {"seal": self.journal.seal.payload(), "manifest": self.manifest.payload(),
                 "identities": [unit.payload() for unit in plan.binding.run_identities],
                 "binding_sha256": digest(plan.binding.payload()), "batch_size": batch_size,
                 "mode": mode, "subject": subject}, manifest=self.manifest)
        payload = result.pop("result")
        if payload != {"binding_sha256": digest(plan.binding.payload())}:
            raise ProvenanceError("RSS worker measured a different deployment")
        return PeakMemory(plan.binding, subject, mode, batch_size, **result)

    def publish(self, row):
        if not isinstance(row, _ROW_TYPES):
            raise TypeError("Expected a typed systems measurement")
        binding = row.provenance
        self._verify_binding(binding)
        require_environment(self.manifest)
        self._publish_exact(self.journal._path("systems", "manifest.json"), self.manifest.payload())
        origin_path = self.journal._path("systems", "origins", f"{binding.origins_sha256}.json")
        if not origin_path.is_file() or digest(json.loads(origin_path.read_text())) != binding.origins_sha256:
            raise ProvenanceError("Measurement requires its authenticated origin manifest")
        record = asdict(row)
        record.update(provenance=binding.payload(), record_type=type(row).__name__,
                      timing_mode=getattr(row, "timing_mode", None), batch_size=getattr(row, "batch_size", None),
                      observed_background_load=list(os.getloadavg()))
        if isinstance(row, Footprint):
            record["artifact"] = row.artifact.payload()
        if isinstance(row, TrainingCost):
            record["total_worker_seconds"] = row.worker_seconds + row.failed_attempt_worker_seconds
        key = digest({
            "record_type": record["record_type"], "run": run_identity(binding.run_identities),
            "timing_mode": record["timing_mode"], "batch_size": record["batch_size"],
            "subject": record.get("subject"), "label": record.get("label"), "artifact": record.get("artifact"),
        })
        path = self.journal._path("systems", "measurements", f"{key}.json")
        _atomic_publish(path, record)
        return path


def _memory_condition(seal, manifest, identities, binding_sha256, batch_size, mode, subject):
    """Child-only replay from the verified frozen adapter after the RSS baseline."""
    from .data_adapters import adapter_for

    fingerprints = Fingerprints(tuple(seal["configuration"]), tuple(tuple(x) for x in seal["inputs"]),
                                tuple(tuple(x) for x in seal["sources"]))
    runner = SystemsRunner(Journal(fingerprints), MachineManifest.from_payload(manifest))
    units = tuple(ScientificIdentity(**{key: value for key, value in row.items()
                                      if key not in {"namespace", "schema_version"}}) for row in identities)
    first = units[0]
    partition = adapter_for(first.block).prepare(first.entity, first.fold, "final")
    plan = runner._prepare(units, partition)
    if digest(plan.binding.payload()) != binding_sha256:
        raise ProvenanceError("RSS replay differs from the declared checkpoint or origins")
    inference_condition(plan, batch_size, mode, subject)
    return {"binding_sha256": binding_sha256}
