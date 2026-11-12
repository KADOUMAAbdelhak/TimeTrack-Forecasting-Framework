"""Deterministic LSTM fits on already verified phase partitions."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, replace
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import random
from threading import Lock
from time import perf_counter

import numpy as np
import torch
from torch import nn

from .checkpoints import EpochSelector, checkpoint_control_applies, diagnostic_slots
from .data_adapters import PARTITIONS, PreparedPartition
from .identity import CONFIG, RESOURCES, ROOT, ScientificIdentity, canonical_json, read_config
from .models.lstm import LSTM
from .optim import gradnorm, pcgrad
from .provenance import Fingerprints, Journal, ProvenanceError, measure_seconds, verify_file
from .transfer.design import ARMS as TRANSFER_ARMS

_CONFIG = read_config()
_SETTINGS = _CONFIG["lstm"]
_BATCH_SIZE = _SETTINGS["batch_size"]
_SOURCE_FILES = tuple(
    (Path(__file__).resolve().parent / name).relative_to(ROOT).as_posix()
    for name in ("training.py", "checkpoints.py", "optim/pcgrad.py", "optim/gradnorm.py")
)
_RNG_LOCK = Lock()


def training_fingerprints():
    return Fingerprints.capture_protocol(additional_sources=_SOURCE_FILES)


@contextmanager
def cpu_seed_scope(seed):
    """Isolate the CPU RNGs and deterministic settings for one trajectory."""
    with _RNG_LOCK:
        python_state, numpy_state = random.getstate(), np.random.get_state()
        torch_state = torch.random.get_rng_state()
        deterministic = torch.are_deterministic_algorithms_enabled()
        warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
        default_dtype = torch.get_default_dtype()
        try:
            random.seed(seed)
            np.random.seed(seed)
            torch.random.default_generator.manual_seed(seed)
            torch.use_deterministic_algorithms(True)
            torch.set_default_dtype(torch.float32)
            with torch.device("cpu"):
                yield torch.Generator(device="cpu").manual_seed(seed)
        finally:
            torch.set_default_dtype(default_dtype)
            torch.use_deterministic_algorithms(deterministic, warn_only=warn_only)
            torch.random.set_rng_state(torch_state)
            np.random.set_state(numpy_state)
            random.setstate(python_state)


def task_mse(prediction, target):
    """Scaled MSE over origins and horizons, one value per declared task."""
    if prediction.shape != target.shape or prediction.ndim != 3:
        raise ValueError("Expected matching [origin, task, horizon] tensors")
    return (prediction - target).square().mean(dim=(0, 2))


def _windows(windows, identity, context):
    horizons = len(_CONFIG["blocks"][identity.block]["horizons"])
    if (windows.inputs.ndim != 3 or windows.inputs.shape[1:] != (context, len(RESOURCES))
            or not len(windows.inputs)
            or windows.targets.shape != (len(windows.inputs), len(RESOURCES), horizons)
            or len(windows.origin_ids) != len(windows.inputs)):
        raise ValueError("Window shape or origin count differs from the declared partition")
    inputs = torch.as_tensor(windows.inputs, dtype=torch.float32, device="cpu")
    targets = torch.as_tensor(windows.targets, dtype=torch.float32, device="cpu")
    targets = targets[:, [RESOURCES.index(task) for task in identity.tasks], :]
    if not torch.isfinite(inputs).all() or not torch.isfinite(targets).all():
        raise ValueError("Nonfinite scaled training or validation windows")
    return inputs, targets


def _optimise_epoch(model, optimizer, windows, generator):
    inputs, targets = windows
    order = torch.randperm(len(inputs), generator=generator, device="cpu")
    task_sums = torch.zeros(targets.shape[1], dtype=torch.float64, device="cpu")
    model.train()
    for rows in order.split(_BATCH_SIZE):
        optimizer.zero_grad(set_to_none=True)
        losses = task_mse(model(inputs[rows]), targets[rows])
        joint = losses.mean()
        if not torch.isfinite(joint):
            raise FloatingPointError("Nonfinite training MSE")
        joint.backward()
        nn.utils.clip_grad_norm_(model.parameters(), _SETTINGS["gradient_clip"], error_if_nonfinite=True)
        optimizer.step()
        task_sums += losses.detach().double() * len(rows)
    if any(not torch.isfinite(parameter).all() for parameter in model.parameters()):
        raise FloatingPointError("Nonfinite trained parameters")
    return (task_sums / len(inputs)).tolist(), sha256(order.numpy().astype("<i8", copy=False).tobytes()).hexdigest()


def _intervention_epoch(model, optimizer, windows, generator, identity, epoch, mode, controller, steps, timings):
    inputs, targets = windows
    order = torch.randperm(len(inputs), generator=generator, device="cpu")
    task_sums = torch.zeros(targets.shape[1], dtype=torch.float64, device="cpu")
    model.train()
    for batch, rows in enumerate(order.split(_BATCH_SIZE)):
        record = {"batch": batch}
        steps.append(record)
        optimizer.zero_grad(set_to_none=True)
        losses = task_mse(model(inputs[rows]), targets[rows])
        if not torch.isfinite(losses).all():
            raise FloatingPointError("Nonfinite intervention task MSE")
        clip = _SETTINGS["gradient_clip"]
        if mode == "pcgrad":
            pcgrad.step(model, optimizer, losses, seed=identity.seed, epoch=epoch, batch=batch,
                        clip=clip, record=record, timings=timings)
        else:
            controller.step(model, optimizer, losses, clip=clip, record=record, timings=timings)
        if any(not torch.isfinite(parameter).all() for parameter in model.parameters()):
            raise FloatingPointError("Nonfinite trained intervention parameters")
        task_sums += losses.detach().double() * len(rows)
    return (task_sums / len(inputs)).tolist(), sha256(order.numpy().astype("<i8", copy=False).tobytes()).hexdigest()


def _check_mode(identity, phase, mode):
    if not isinstance(identity, ScientificIdentity) or identity.phase != phase:
        raise ValueError("Expected a scientific identity for this phase")
    if mode == "equal_loss" and identity.arm in {"core", "capacity", *TRANSFER_ARMS}:
        return
    if mode in {"pcgrad", "gradnorm"} and identity.arm == mode and identity.formulation == "M1":
        return
    raise ValueError("Optimisation mode does not match the declared intervention identity")


def _adam_configuration(optimizer):
    return {"name": "Adam", **json.loads(canonical_json(optimizer.defaults))}


@torch.no_grad()
def _evaluate(model, windows):
    model.eval()
    inputs, targets = windows
    task_sums = torch.zeros(targets.shape[1], dtype=torch.float64, device="cpu")
    for X, y in zip(inputs.split(_BATCH_SIZE), targets.split(_BATCH_SIZE), strict=True):
        squared = (model(X).double() - y.double()).square()
        task_sums += squared.sum(dim=(0, 2))
    return (task_sums / (len(inputs) * targets.shape[-1])).tolist()


def _state_hash(state):
    digest = sha256()
    for name, tensor in sorted(state.items()):
        tensor = tensor.detach().cpu().contiguous()
        digest.update(canonical_json([name, str(tensor.dtype), list(tensor.shape), tensor.nbytes]) + b"\n")
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def _encode(state):
    output = io.BytesIO()
    torch.save(state, output)
    return output.getvalue()


def capture_epoch_state(model, optimizer, generator, *, identity, fingerprint_sha256, evidence):
    """Capture the state after a whole epoch, including validation when applicable."""
    kind, keys, position, has_gaussian, gaussian = np.random.get_state()
    return {
        "identity": identity.payload(), "fingerprint_sha256": fingerprint_sha256,
        "epoch": len(evidence["epochs"]), "evidence": deepcopy(evidence),
        "model": {name: tensor.detach().clone() for name, tensor in model.state_dict().items()},
        "model_training": model.training, "optimizer": deepcopy(optimizer.state_dict()),
        "rng": {
            "python": random.getstate(), "numpy": (kind, keys.tolist(), position, has_gaussian, gaussian),
            "torch_cpu": torch.random.get_rng_state(), "shuffle": generator.get_state(),
        },
    }


@dataclass(frozen=True, slots=True)
class FitResult:
    evidence: dict
    resume_state: bytes


class TrainingEngine:
    """Final selection comes from the paired journalled inner fit in the same mode."""

    def __init__(self, journal):
        if not isinstance(journal, Journal):
            raise TypeError("Expected a Stage 3A journal")
        journal.seal.require_protocol(additional_sources=_SOURCE_FILES)
        verify_file(CONFIG, journal.seal.configuration[1])
        if read_config() != _CONFIG:
            raise ProvenanceError("Training configuration changed after module import")
        self.journal = journal

    def fit_inner(self, identity, partition, *, mode="equal_loss"):
        return self._fit(identity, partition, "inner", mode)

    def fit_final(self, identity, partition, *, mode="equal_loss"):
        return self._fit(identity, partition, "final", mode)

    _check_fit_mode = staticmethod(_check_mode)

    def _prepare_windows(self, identity, partition, evidence, *, validation=False):
        windows = partition.validation() if validation else partition.training()
        return _windows(windows, identity, partition.context)

    def _model_and_optimizer(self, identity, partition, evidence):
        model = LSTM(formulation=identity.formulation, block=identity.block,
                     tasks=identity.tasks, hidden_size=identity.hidden_size)
        return model, torch.optim.Adam(model.parameters(), lr=_SETTINGS["learning_rate"])

    def _validation_losses(self, model, windows, partition, identity, evidence):
        return _evaluate(model, windows)

    def _fit(self, identity, partition, phase, mode):
        self._check_fit_mode(identity, phase, mode)
        if not isinstance(partition, PreparedPartition):
            raise TypeError("Expected a Stage 3A prepared partition")
        key = (identity.block, identity.entity, identity.fold, phase)
        if (partition.block, partition.entity, partition.fold, partition.phase) != key:
            raise ProvenanceError("Partition does not belong to this exact training identity")
        if (partition.context not in _CONFIG["blocks"][identity.block]["contexts"]
                or set(partition.split_hashes) != {name for pair in PARTITIONS.values() for name in pair}):
            raise ProvenanceError("Invalid prepared partition context or split metadata")
        evidence = {
            "context": partition.context, "support_sha256": partition.support_sha256,
            "split_hashes": dict(partition.split_hashes), "scaler_sha256": partition.scaler_sha256,
            "configuration_sha256": self.journal.seal.configuration[1],
            "epochs": [], "selection": None, "checkpoints": {},
            "timing_seconds": {"primary_optimisation": 0.0, "checkpoint_tail_optimisation": 0.0, "validation": 0.0},
        }
        plan = None
        if mode != "equal_loss":
            evidence["intervention"] = {"mode": mode, "algorithm_variant": f"v0.3-{mode}-M1", "epochs": []}
        if phase == "final":
            plan = self._selected_final_plan(identity, evidence, mode)
            evidence["selection"] = plan.payload()
        attempt = self.journal.start(identity)
        start = perf_counter()
        try:
            with cpu_seed_scope(identity.seed) as generator:
                model, optimizer, controller = self._run(attempt, partition, evidence, generator, plan, mode)
                evidence["terminal_model_sha256"] = _state_hash(model.state_dict())
                evidence["optimizer_state_bytes"] = len(_encode(optimizer.state_dict()))
                state = capture_epoch_state(model, optimizer, generator, identity=identity,
                                            fingerprint_sha256=self.journal.seal.digest, evidence=evidence)
                if controller is not None:
                    state["gradnorm"] = controller.state_dict()
                    evidence["weight_optimizer_state_bytes"] = len(_encode(state["gradnorm"]["weight_optimizer"]))
                    optimizer_state = {"identity": identity.payload(), "fingerprint_sha256": self.journal.seal.digest,
                                       "epoch": len(evidence["epochs"]), "model_optimizer": state["optimizer"],
                                       "gradnorm": state["gradnorm"]}
                    evidence["intervention"]["optimizer_state"] = self.journal.save_optimizer_state(
                        attempt, _encode(optimizer_state))
                encoded_state = _encode(state)
                evidence["resume_state_sha256"] = sha256(encoded_state).hexdigest()
                evidence["timing_seconds"]["elapsed"] = perf_counter() - start
        except Exception as error:
            evidence["timing_seconds"]["elapsed"] = perf_counter() - start
            evidence["error"] = {"type": type(error).__name__, "message": str(error)}
            self.journal.finish(attempt, status="failed", evidence=evidence)
            raise
        self.journal.finish(attempt, status="complete", evidence=evidence)
        return FitResult(evidence, encoded_state)

    def _selected_final_plan(self, identity, evidence, mode):
        inner = replace(identity, phase="inner")
        observed, outcome_hash = self.journal.completed_evidence(inner)
        if any(observed.get(key) != evidence[key] for key in ("context", "split_hashes", "configuration_sha256")):
            raise ProvenanceError("Inner selection and final partition do not share the frozen design")
        if observed.get("intervention", {}).get("mode", "equal_loss") != mode:
            raise ProvenanceError("Inner and final optimisation modes differ")
        selector = EpochSelector(identity.tasks, task_control=checkpoint_control_applies(identity))
        for expected_epoch, row in enumerate(observed["epochs"], start=1):
            if row["epoch"] != expected_epoch:
                raise ProvenanceError("Inner validation history has a missing or duplicate epoch")
            joint = selector.observe(row["validation_task_mse"][task] for task in identity.tasks)
            if joint != row["validation_joint_mse"]:
                raise ProvenanceError("Inner joint validation MSE differs from task mean")
        if not selector.stopped or selector.plan().payload() != observed["selection"]:
            raise ProvenanceError("Inner checkpoint selection differs from the observed trajectory")
        evidence["inner_outcome_sha256"] = outcome_hash
        evidence["inner_identity_sha256"] = inner.digest
        return selector.plan()

    def _save_model_checkpoint(self, attempt, epoch, state, evidence, *, category="checkpoint", diagnostic=False):
        timings = evidence["timing_seconds"]
        with measure_seconds(timings, category + "_serialization"):
            encoded = _encode(state)
        with measure_seconds(timings, category + "_io"):
            reference = self.journal.save_checkpoint(attempt, epoch, encoded, diagnostic=diagnostic)
        return {**reference, "model_sha256": _state_hash(state)}

    def _run(self, attempt, partition, evidence, generator, plan, mode):
        identity = attempt.identity
        inner = identity.phase == "inner"
        if inner:
            selector = EpochSelector(identity.tasks, task_control=checkpoint_control_applies(identity))
        training = self._prepare_windows(identity, partition, evidence)
        validation = self._prepare_windows(identity, partition, evidence, validation=True) if inner else None
        model, optimizer = self._model_and_optimizer(identity, partition, evidence)
        controller = gradnorm.GradNorm(model) if mode == "gradnorm" else None
        if mode != "equal_loss":
            evidence["intervention"]["model_optimizer"] = _adam_configuration(optimizer)
            if controller is not None:
                evidence["intervention"].update(alpha=gradnorm.ALPHA, norm_parameters=list(gradnorm.NORM_PARAMETERS),
                                                weight_optimizer=_adam_configuration(controller.weight_optimizer))
        evidence["parameter_count"] = sum(p.numel() for p in model.parameters() if p.requires_grad)
        evidence["initial_model_sha256"] = _state_hash(model.state_dict())
        slots = {}
        if not inner and identity.arm == "core" and identity.formulation in _CONFIG["diagnostics"]["formulations"]:
            slots = diagnostic_slots(plan.joint_epoch)
            evidence["diagnostic_slots"] = slots
            evidence["diagnostic_checkpoints"] = {
                "0": self._save_model_checkpoint(attempt, 0, model.state_dict(), evidence,
                                                 category="diagnostic_checkpoint", diagnostic=True)
            }
        selected_state = None
        limit = _SETTINGS["max_inner_epochs"] if inner else plan.final_epoch
        for epoch in range(1, limit + 1):
            started = perf_counter()
            cost = "primary_optimisation" if inner or epoch <= plan.joint_epoch else "checkpoint_tail_optimisation"
            try:
                if mode == "equal_loss":
                    train_mse, order_hash = _optimise_epoch(model, optimizer, training, generator)
                else:
                    steps = []
                    evidence["intervention"]["epochs"].append({"epoch": epoch, "steps": steps})
                    train_mse, order_hash = _intervention_epoch(
                        model, optimizer, training, generator, identity, epoch, mode, controller, steps,
                        evidence["timing_seconds"])
            finally:
                evidence["timing_seconds"][cost] += perf_counter() - started
            row = {"epoch": epoch, "train_task_mse": dict(zip(identity.tasks, train_mse, strict=True)),
                   "train_joint_mse": math.fsum(train_mse) / len(train_mse), "batch_order_sha256": order_hash}
            evidence["epochs"].append(row)
            if inner:
                started = perf_counter()
                try:
                    losses = self._validation_losses(model, validation, partition, identity, evidence)
                    joint = selector.observe(losses)
                finally:
                    evidence["timing_seconds"]["validation"] += perf_counter() - started
                row["validation_task_mse"] = dict(zip(identity.tasks, losses, strict=True))
                row["validation_joint_mse"] = joint
                evidence["selection"] = selector.plan().payload()
                if identity.arm == "modern" and selector.joint_epoch == epoch:
                    selected_state = {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
                if selector.stopped:
                    break
            else:
                reference = None
                if epoch in plan.physical_epochs:
                    reference = self._save_model_checkpoint(
                        attempt, epoch, model.state_dict(), evidence,
                        category="checkpoint" if epoch == plan.joint_epoch else "task_checkpoint")
                    evidence["checkpoints"][str(epoch)] = reference
                if epoch in slots.values():
                    evidence["diagnostic_checkpoints"][str(epoch)] = reference or self._save_model_checkpoint(
                        attempt, epoch, model.state_dict(), evidence, category="diagnostic_checkpoint", diagnostic=True
                    )
        if selected_state is not None:
            epoch = selector.joint_epoch
            evidence["checkpoints"][str(epoch)] = self._save_model_checkpoint(
                attempt, epoch, selected_state, evidence)
        if not inner:
            evidence["primary_checkpoint_epoch"] = plan.joint_epoch
            evidence["checkpoint_tail_epochs"] = plan.final_epoch - plan.joint_epoch
        return model, optimizer, controller
