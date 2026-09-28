"""Deterministic inner training and fixed-epoch future final lifecycle."""

from __future__ import annotations

import copy
import io
import random
import resource as system_resource
import time
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from . import RESOURCE_ORDER
from .models import MultiTargetLSTM, SingleTargetLSTM


LEARNING_RATE = 1e-3
BATCH_SIZE = 256
MAX_EPOCHS = 50
PATIENCE = 7
GRADIENT_CLIP = 1.0


@dataclass
class FitResult:
    model: nn.Module
    best_epoch: int
    epochs_trained: int
    epoch_logs: list[dict[str, object]]
    validation_prediction: np.ndarray | None
    epoch_train_seconds: list[float]
    epoch_validation_seconds: list[float]
    peak_rss_bytes: int


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def build_model(formulation: str, input_channels: int) -> nn.Module:
    if formulation in {"S1", "S2"}:
        return SingleTargetLSTM(input_channels)
    if formulation == "M1":
        return MultiTargetLSTM(input_channels)
    raise ValueError(formulation)


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


def encoder_parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.encoder.parameters())


def head_parameter_count(model: nn.Module) -> int:
    heads = model.heads if isinstance(model, MultiTargetLSTM) else [model.head]
    return sum(parameter.numel() for head in heads for parameter in head.parameters())


def serialized_state_bytes(model: nn.Module) -> int:
    buffer = io.BytesIO()
    torch.save(model.state_dict(), buffer)
    return buffer.tell()


def resource_losses(prediction: torch.Tensor, target: torch.Tensor, formulation: str, resource: str | None) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    if formulation == "M1":
        losses = {
            name: torch.mean((prediction[:, index, :] - target[:, index, :]) ** 2)
            for index, name in enumerate(RESOURCE_ORDER)
        }
        return torch.stack(list(losses.values())).mean(), losses
    if resource not in RESOURCE_ORDER:
        raise ValueError("S1/S2 loss requires a target resource")
    value = torch.mean((prediction - target) ** 2)
    return value, {resource: value}


def _loader(X: np.ndarray, y: np.ndarray, seed: int, batch_size: int) -> DataLoader:
    generator = torch.Generator().manual_seed(seed)
    return DataLoader(
        TensorDataset(torch.from_numpy(X.astype(np.float32)), torch.from_numpy(y.astype(np.float32))),
        batch_size=batch_size, shuffle=True, generator=generator, num_workers=0,
    )


def fit_inner(
    formulation: str,
    resource: str | None,
    seed: int,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_validation: np.ndarray,
    y_validation: np.ndarray,
    *,
    fixed_epochs: int | None = None,
    max_epochs: int = MAX_EPOCHS,
    patience: int = PATIENCE,
    batch_size: int = BATCH_SIZE,
    device: str = "cpu",
) -> FitResult:
    """Train with inner data only; the API intentionally has no outer-test argument."""
    if fixed_epochs is not None and fixed_epochs <= 0:
        raise ValueError("fixed_epochs must be positive")
    set_seed(seed)
    selected_device = torch.device(device)
    model = build_model(formulation, X_train.shape[-1]).to(selected_device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    loader = _loader(X_train, y_train, seed, batch_size)
    validation_x = torch.from_numpy(X_validation.astype(np.float32)).to(selected_device)
    validation_y = torch.from_numpy(y_validation.astype(np.float32)).to(selected_device)
    limit = fixed_epochs or max_epochs
    best_loss, best_epoch, stale = float("inf"), 0, 0
    best_state = copy.deepcopy(model.state_dict())
    logs = []
    train_times, validation_times = [], []
    for epoch in range(1, limit + 1):
        model.train()
        sums: dict[str, float] = {}
        seen = 0
        started = time.perf_counter()
        for batch_x, batch_y in loader:
            batch_x, batch_y = batch_x.to(selected_device), batch_y.to(selected_device)
            optimizer.zero_grad(set_to_none=True)
            joint, losses = resource_losses(model(batch_x), batch_y, formulation, resource)
            joint.backward()
            nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
            for name, value in losses.items():
                sums[name] = sums.get(name, 0.0) + float(value.detach()) * len(batch_x)
            seen += len(batch_x)
        train_times.append(time.perf_counter() - started)
        train_loss = {name: value / seen for name, value in sums.items()}
        model.eval()
        started = time.perf_counter()
        with torch.no_grad():
            validation_prediction = model(validation_x)
            joint_validation, validation_tensors = resource_losses(
                validation_prediction, validation_y, formulation, resource
            )
        validation_times.append(time.perf_counter() - started)
        validation_loss = {name: float(value) for name, value in validation_tensors.items()}
        train_total, validation_total = sum(train_loss.values()), sum(validation_loss.values())
        logs.append({
            "epoch": epoch,
            "train_resource_mse": train_loss,
            "validation_resource_mse": validation_loss,
            "train_loss_share": {name: value / train_total for name, value in train_loss.items()},
            "validation_loss_share": {name: value / validation_total for name, value in validation_loss.items()},
        })
        score = float(joint_validation)
        if score < best_loss:
            best_loss, best_epoch, stale = score, epoch, 0
            best_state = copy.deepcopy(model.state_dict())
        else:
            stale += 1
        if fixed_epochs is None and stale >= patience:
            break
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        final_prediction = model(validation_x).cpu().numpy()
    rss = system_resource.getrusage(system_resource.RUSAGE_SELF).ru_maxrss
    rss_bytes = int(rss if rss > 10_000_000 else rss * 1024)
    return FitResult(model, best_epoch, epoch, logs, final_prediction, train_times, validation_times, rss_bytes)


def fit_final_fixed_epochs(formulation: str, resource: str | None, seed: int, X_train: np.ndarray, y_train: np.ndarray, epoch_count: int) -> FitResult:
    """Future final refit from scratch; no validation or test input exists."""
    if epoch_count <= 0:
        raise ValueError("epoch_count must be positive")
    set_seed(seed)
    model = build_model(formulation, X_train.shape[-1])
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    loader = _loader(X_train, y_train, seed, BATCH_SIZE)
    train_times = []
    for _ in range(epoch_count):
        model.train()
        started = time.perf_counter()
        for batch_x, batch_y in loader:
            optimizer.zero_grad(set_to_none=True)
            joint, _ = resource_losses(model(batch_x), batch_y, formulation, resource)
            joint.backward()
            nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
        train_times.append(time.perf_counter() - started)
    return FitResult(model, epoch_count, epoch_count, [], None, train_times, [], 0)
