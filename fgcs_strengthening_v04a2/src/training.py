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

from .checkpoints import EpochSelector, diagnostic_slots
from .data_adapters import PARTITIONS, PreparedPartition
from .identity import CONFIG, RESOURCES, ROOT, ScientificIdentity, canonical_json, read_config
from .models.lstm import LSTM
from .provenance import Fingerprints, Journal, ProvenanceError, measure_seconds, verify_file
from .residual import anchor
from .transfer.design import ARMS as TRANSFER_ARMS

_CONFIG = read_config()
_SETTINGS = _CONFIG["lstm"]
_BATCH_SIZE = _SETTINGS["batch_size"]
_SOURCE_FILES = tuple(
    (Path(__file__).resolve().parent / name).relative_to(ROOT).as_posix()
    for name in ("training.py", "checkpoints.py", "residual.py")
)
_RNG_LOCK = Lock()
_INTERVENTION = _CONFIG["intervention"]


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


class GradNormBalancer:
    """A1 M1-GN: GradNorm task weights on the last shared layer (Chen et al., ICML 2018).

    The model step uses sum_i w_i L_i with the current weights. The weights then take one Adam step on
    sum_i |w_i ||grad_W L_i|| - target_i|, target_i = mean_j(w_j ||grad_W L_j||) * r_i ** alpha held constant,
    r_i the relative inverse training rate against the step-0 losses; they are then floored and rescaled
    to sum to the number of tasks.
    """

    mode = "gradnorm"

    def __init__(self, model, tasks):
        spec = _INTERVENTION["modes"]["gradnorm"]
        self.alpha = float(spec["alpha"])
        self.total = float(spec["task_weight_sum"])
        self.floor = float(spec["weight_floor"])
        if len(tasks) != spec["task_weight_sum"]:
            raise ValueError("GradNorm weights must sum to the number of tasks")
        encoder = dict(model.encoder.named_parameters())
        self.shared = tuple(encoder[name] for name in spec["shared_layer"])
        self.weights = torch.full((len(tasks),), float(spec["initial_weight"]), dtype=torch.float32,
                                  device="cpu", requires_grad=True)
        self.optimizer = torch.optim.Adam([self.weights], lr=spec["weight_learning_rate"])
        self.initial_losses = None
        self.floor_hits = 0
        self._norms = None

    def backward(self, model, losses):
        """Set the model gradients to the weighted per-task sum and keep the shared-layer norms."""
        if self.initial_losses is None:
            self.initial_losses = losses.detach().clone()
            if not (self.initial_losses > 0).all():
                raise FloatingPointError("GradNorm needs positive step-0 task losses")
        parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
        shared = {id(parameter) for parameter in self.shared}
        weights = self.weights.detach().clone()
        per_task, norms = [], []
        for index in range(len(losses)):
            gradients = torch.autograd.grad(losses[index], parameters, retain_graph=index < len(losses) - 1,
                                            allow_unused=True)
            layer = [gradient for parameter, gradient in zip(parameters, gradients, strict=True)
                     if id(parameter) in shared]
            if len(layer) != len(self.shared) or any(gradient is None for gradient in layer):
                raise ValueError("Every task must reach the last shared layer")
            norms.append(torch.linalg.vector_norm(torch.cat([gradient.reshape(-1) for gradient in layer])))
            per_task.append(gradients)
        for position, parameter in enumerate(parameters):
            total = None
            for task, gradients in enumerate(per_task):
                if gradients[position] is not None:
                    term = weights[task] * gradients[position]
                    total = term if total is None else total + term
            parameter.grad = total
        self._norms = torch.stack(norms).detach()
        return (weights * losses.detach()).sum()

    def after_step(self, losses):
        weighted_norms = self.weights * self._norms
        rate = losses.detach() / self.initial_losses
        target = (weighted_norms.detach().mean() * (rate / rate.mean()) ** self.alpha).detach()
        self.optimizer.zero_grad(set_to_none=True)
        (weighted_norms - target).abs().sum().backward()
        self.optimizer.step()
        with torch.no_grad():
            self.floor_hits += int((self.weights < self.floor).sum())
            self.weights.clamp_(min=self.floor)
            self.weights.mul_(self.total / self.weights.sum())
        self._norms = None
        if not torch.isfinite(self.weights).all():
            raise FloatingPointError("Nonfinite GradNorm weights")

    def effective_weights(self):
        return self.weights.detach().tolist()

    def evidence(self):
        return {"mode": self.mode, "initial_task_losses": self.initial_losses.tolist(),
                "weight_floor_hits": self.floor_hits, "weights": self.effective_weights()}

    def state_dict(self):
        return {"mode": self.mode, "weights": self.weights.detach().clone(),
                "optimizer": deepcopy(self.optimizer.state_dict()),
                "initial_losses": None if self.initial_losses is None else self.initial_losses.clone(),
                "floor_hits": self.floor_hits}


class UncertaintyBalancer:
    """A1 M1-UW: loss sum_i exp(-s_i) L_i + s_i with learnable s_i = log sigma_i^2 (Kendall et al., CVPR 2018).

    The s_i take Adam steps at the model's learning rate. Adam is per-parameter, so this separate instance
    is the same optimiser as one holding the model and s together; only the model is clipped.
    """

    mode = "uncertainty"

    def __init__(self, model, tasks):
        spec = _INTERVENTION["modes"]["uncertainty"]
        self.log_variance = torch.full((len(tasks),), float(spec["initial_log_variance"]), dtype=torch.float32,
                                       device="cpu", requires_grad=True)
        self.optimizer = torch.optim.Adam([self.log_variance], lr=_SETTINGS["learning_rate"])

    def backward(self, model, losses):
        self.optimizer.zero_grad(set_to_none=True)
        joint = (torch.exp(-self.log_variance) * losses + self.log_variance).sum()
        if not torch.isfinite(joint):
            raise FloatingPointError("Nonfinite weighted training loss")
        joint.backward()
        return joint.detach()

    def after_step(self, losses):
        self.optimizer.step()
        if not torch.isfinite(self.log_variance).all():
            raise FloatingPointError("Nonfinite uncertainty log variances")

    def effective_weights(self):
        return torch.exp(-self.log_variance.detach()).tolist()

    def evidence(self):
        return {"mode": self.mode, "log_variance": self.log_variance.detach().tolist(),
                "weights": self.effective_weights()}

    def state_dict(self):
        return {"mode": self.mode, "log_variance": self.log_variance.detach().clone(),
                "optimizer": deepcopy(self.optimizer.state_dict())}


BALANCERS = {balancer.mode: balancer for balancer in (GradNormBalancer, UncertaintyBalancer)}
if set(BALANCERS) != set(_INTERVENTION["modes"]):
    raise RuntimeError("Implemented A1 modes differ from the configuration")


def _optimise_weighted_epoch(model, optimizer, windows, generator, balancer):
    """The equal-loss epoch with the A1 weighting: same shuffle stream, batches, clipping and Adam step."""
    inputs, targets = windows
    order = torch.randperm(len(inputs), generator=generator, device="cpu")
    task_sums = torch.zeros(targets.shape[1], dtype=torch.float64, device="cpu")
    weighted_sum = 0.0
    model.train()
    for rows in order.split(_BATCH_SIZE):
        optimizer.zero_grad(set_to_none=True)
        losses = task_mse(model(inputs[rows]), targets[rows])
        if not torch.isfinite(losses).all():
            raise FloatingPointError("Nonfinite training MSE")
        weighted = balancer.backward(model, losses)
        if not torch.isfinite(weighted):
            raise FloatingPointError("Nonfinite weighted training loss")
        nn.utils.clip_grad_norm_(model.parameters(), _SETTINGS["gradient_clip"], error_if_nonfinite=True)
        optimizer.step()
        balancer.after_step(losses)
        task_sums += losses.detach().double() * len(rows)
        weighted_sum += float(weighted) * len(rows)
    if any(not torch.isfinite(parameter).all() for parameter in model.parameters()):
        raise FloatingPointError("Nonfinite trained parameters")
    return ((task_sums / len(inputs)).tolist(),
            sha256(order.numpy().astype("<i8", copy=False).tobytes()).hexdigest(), weighted_sum / len(inputs))


def _check_mode(identity, phase, mode):
    if not isinstance(identity, ScientificIdentity) or identity.phase != phase:
        raise ValueError("Expected a scientific identity for this phase")
    if mode == "equal_loss" and identity.arm in {"core", *TRANSFER_ARMS}:
        return
    if identity.arm == "intervention" and mode == identity.variant and mode in BALANCERS:
        return
    raise ValueError("Core and transfer LSTM identities use the equal-mean loss; A1 identities their own mode")


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


def capture_epoch_state(model, optimizer, generator, *, identity, fingerprint_sha256, evidence, balancer=None):
    """Capture the state after a whole epoch, including validation when applicable."""
    kind, keys, position, has_gaussian, gaussian = np.random.get_state()
    state = {
        "identity": identity.payload(), "fingerprint_sha256": fingerprint_sha256,
        "epoch": len(evidence["epochs"]), "evidence": deepcopy(evidence),
        "model": {name: tensor.detach().clone() for name, tensor in model.state_dict().items()},
        "model_training": model.training, "optimizer": deepcopy(optimizer.state_dict()),
        "rng": {
            "python": random.getstate(), "numpy": (kind, keys.tolist(), position, has_gaussian, gaussian),
            "torch_cpu": torch.random.get_rng_state(), "shuffle": generator.get_state(),
        },
    }
    if balancer is not None:
        state["balancer"] = balancer.state_dict()
    return state


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
        model = anchor(LSTM(formulation=identity.formulation, block=identity.block,
                            tasks=identity.tasks, hidden_size=identity.hidden_size), identity.tasks)
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
        if mode != "equal_loss":
            evidence["loss_mode"] = mode
        plan = None
        if phase == "final":
            plan = self._selected_final_plan(identity, evidence, mode)
            evidence["selection"] = plan.payload()
        attempt = self.journal.start(identity)
        start = perf_counter()
        try:
            with cpu_seed_scope(identity.seed) as generator:
                model, optimizer, balancer = self._run(attempt, partition, evidence, generator, plan, mode)
                evidence["terminal_model_sha256"] = _state_hash(model.state_dict())
                evidence["optimizer_state_bytes"] = len(_encode(optimizer.state_dict()))
                state = capture_epoch_state(model, optimizer, generator, identity=identity,
                                            fingerprint_sha256=self.journal.seal.digest, evidence=evidence,
                                            balancer=balancer)
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
        if "intervention" in observed or observed.get("loss_mode", "equal_loss") != mode:
            raise ProvenanceError("Inner and final optimisation modes differ")
        selector = EpochSelector(identity.tasks, task_control=False)
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
            selector = EpochSelector(identity.tasks, task_control=False)
        training = self._prepare_windows(identity, partition, evidence)
        validation = self._prepare_windows(identity, partition, evidence, validation=True) if inner else None
        model, optimizer = self._model_and_optimizer(identity, partition, evidence)
        evidence["parameter_count"] = sum(p.numel() for p in model.parameters() if p.requires_grad)
        evidence["initial_model_sha256"] = _state_hash(model.state_dict())
        balancer = None if mode == "equal_loss" else BALANCERS[mode](model, identity.tasks)
        slots = {}
        if (not inner and identity.arm in {"core", "intervention"}
                and identity.formulation in _CONFIG["diagnostics"]["formulations"]):
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
                if balancer is None:
                    train_mse, order_hash = _optimise_epoch(model, optimizer, training, generator)
                else:
                    train_mse, order_hash, weighted = _optimise_weighted_epoch(
                        model, optimizer, training, generator, balancer)
            finally:
                evidence["timing_seconds"][cost] += perf_counter() - started
            row = {"epoch": epoch, "train_task_mse": dict(zip(identity.tasks, train_mse, strict=True)),
                   "train_joint_mse": math.fsum(train_mse) / len(train_mse), "batch_order_sha256": order_hash}
            if balancer is not None:
                row["train_weighted_loss"] = weighted
                row["loss_weights"] = dict(zip(identity.tasks, balancer.effective_weights(), strict=True))
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
        if balancer is not None:
            evidence["balancer"] = balancer.evidence()
        return model, optimizer, balancer
