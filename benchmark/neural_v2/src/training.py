"""Leakage-safe neural-v2 training, early stopping, and fixed-epoch refits."""

from __future__ import annotations

import copy
import random
import time
from dataclasses import dataclass
from typing import Callable

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from .models import DLinear, FullReceptiveFieldTCN, LSTMForecaster, PatchTST


BATCH_SIZE = 256
LEARNING_RATE = 1e-3
MAX_EPOCHS = 50
PATIENCE = 7
GRADIENT_CLIP = 1.0


@dataclass(frozen=True)
class FeatureStandardizer:
    mean: np.ndarray
    std: np.ndarray

    @classmethod
    def fit(cls, X_train: np.ndarray) -> "FeatureStandardizer":
        mean = X_train.mean(axis=(0, 1), keepdims=True)
        std = X_train.std(axis=(0, 1), keepdims=True)
        std[std == 0] = 1.0
        return cls(mean=mean, std=std)

    def transform(self, values: np.ndarray) -> np.ndarray:
        return ((values - self.mean) / self.std).astype(np.float32)


@dataclass
class FitResult:
    model: nn.Module
    standardizer: FeatureStandardizer
    epochs_trained: int
    best_epoch: int
    best_validation_loss: float | None
    validation_mae_by_lead: np.ndarray | None
    train_seconds: float
    validation_seconds: float


def set_deterministic_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def select_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def model_factory(
    model_name: str, context_length: int, input_channels: int
) -> Callable[[], nn.Module]:
    factories: dict[str, Callable[[], nn.Module]] = {
        "DLinear": lambda: DLinear(context_length, input_channels),
        "LSTM": lambda: LSTMForecaster(input_channels),
        "TCN-v2": lambda: FullReceptiveFieldTCN(input_channels),
        "PatchTST": lambda: PatchTST(context_length, input_channels),
    }
    if model_name not in factories:
        raise KeyError(f"Unknown neural-v2 model: {model_name}")
    return factories[model_name]


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())


def _optimizer(model_name: str, model: nn.Module) -> torch.optim.Optimizer:
    if model_name == "PatchTST":
        return torch.optim.AdamW(
            model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4
        )
    return torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)


def _loader(
    X: np.ndarray, y: np.ndarray, seed: int, batch_size: int
) -> DataLoader:
    generator = torch.Generator().manual_seed(seed)
    return DataLoader(
        TensorDataset(torch.from_numpy(X), torch.from_numpy(y.astype(np.float32))),
        batch_size=batch_size,
        shuffle=True,
        generator=generator,
        num_workers=0,
    )


def fit_inner(
    model_name: str,
    context_length: int,
    input_channels: int,
    seed: int,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_validation: np.ndarray,
    y_validation: np.ndarray,
    *,
    max_epochs: int = MAX_EPOCHS,
    patience: int = PATIENCE,
    batch_size: int = BATCH_SIZE,
    fixed_epochs: int | None = None,
    device: str | torch.device | None = None,
) -> FitResult:
    """Fit using only inner train/validation; fixed_epochs disables stopping."""
    if fixed_epochs is not None and fixed_epochs <= 0:
        raise ValueError("fixed_epochs must be positive")
    set_deterministic_seed(seed)
    selected_device = torch.device(device) if device else select_device()
    model = model_factory(model_name, context_length, input_channels)().to(
        selected_device
    )
    standardizer = FeatureStandardizer.fit(X_train)
    train_x = standardizer.transform(X_train)
    validation_x = torch.from_numpy(standardizer.transform(X_validation)).to(
        selected_device
    )
    validation_y = torch.from_numpy(y_validation.astype(np.float32)).to(
        selected_device
    )
    loader = _loader(train_x, y_train, seed, batch_size)
    optimizer = _optimizer(model_name, model)
    loss_function = nn.MSELoss()
    epoch_limit = fixed_epochs if fixed_epochs is not None else max_epochs
    best_loss = float("inf")
    best_epoch = 0
    best_state = copy.deepcopy(model.state_dict())
    stale = 0
    train_seconds = 0.0
    validation_seconds = 0.0
    for epoch in range(1, epoch_limit + 1):
        model.train()
        started = time.perf_counter()
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(selected_device)
            batch_y = batch_y.to(selected_device)
            optimizer.zero_grad(set_to_none=True)
            loss = loss_function(model(batch_x), batch_y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
        train_seconds += time.perf_counter() - started
        model.eval()
        started = time.perf_counter()
        with torch.no_grad():
            validation_prediction = model(validation_x)
            validation_loss = float(
                loss_function(validation_prediction, validation_y).item()
            )
        validation_seconds += time.perf_counter() - started
        if validation_loss < best_loss:
            best_loss = validation_loss
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            stale = 0
        else:
            stale += 1
        if fixed_epochs is None and stale >= patience:
            break
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        prediction = model(validation_x).cpu().numpy()
    validation_mae = np.mean(np.abs(y_validation - prediction), axis=0)
    return FitResult(
        model=model,
        standardizer=standardizer,
        epochs_trained=epoch,
        best_epoch=best_epoch,
        best_validation_loss=best_loss,
        validation_mae_by_lead=validation_mae,
        train_seconds=train_seconds,
        validation_seconds=validation_seconds,
    )


def fit_final_fixed_epochs(
    model_name: str,
    context_length: int,
    input_channels: int,
    seed: int,
    X_train: np.ndarray,
    y_train: np.ndarray,
    epoch_count: int,
    *,
    batch_size: int = BATCH_SIZE,
    device: str | torch.device | None = None,
) -> FitResult:
    """Train from scratch on full outer training without any test callback."""
    if epoch_count <= 0:
        raise ValueError("epoch_count must be positive")
    set_deterministic_seed(seed)
    selected_device = torch.device(device) if device else select_device()
    model = model_factory(model_name, context_length, input_channels)().to(
        selected_device
    )
    standardizer = FeatureStandardizer.fit(X_train)
    loader = _loader(
        standardizer.transform(X_train), y_train, seed, batch_size
    )
    optimizer = _optimizer(model_name, model)
    loss_function = nn.MSELoss()
    train_seconds = 0.0
    for _epoch in range(1, epoch_count + 1):
        model.train()
        started = time.perf_counter()
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(selected_device)
            batch_y = batch_y.to(selected_device)
            optimizer.zero_grad(set_to_none=True)
            loss = loss_function(model(batch_x), batch_y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP)
            optimizer.step()
        train_seconds += time.perf_counter() - started
    return FitResult(
        model=model,
        standardizer=standardizer,
        epochs_trained=epoch_count,
        best_epoch=epoch_count,
        best_validation_loss=None,
        validation_mae_by_lead=None,
        train_seconds=train_seconds,
        validation_seconds=0.0,
    )


def predict(result: FitResult, X: np.ndarray, device: str = "cpu") -> np.ndarray:
    result.model.eval()
    model_device = next(result.model.parameters()).device
    if str(model_device) != device and device != "cpu":
        raise ValueError("Requested device differs from fitted model device")
    values = torch.from_numpy(result.standardizer.transform(X)).to(model_device)
    with torch.no_grad():
        return result.model(values).cpu().numpy()
