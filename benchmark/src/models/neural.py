"""Shared deterministic neural training scaffold."""

from __future__ import annotations

import copy
import random

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from .base import ForecastModel


def select_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class TorchForecaster(ForecastModel):
    def __init__(
        self,
        network: nn.Module,
        seed: int,
        learning_rate: float = 1e-3,
        batch_size: int = 256,
        max_epochs: int = 50,
        patience: int = 7,
        gradient_clip_norm: float = 1.0,
        device: str | None = None,
    ) -> None:
        self.network = network
        self.seed = seed
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.max_epochs = max_epochs
        self.patience = patience
        self.gradient_clip_norm = gradient_clip_norm
        self.device = torch.device(device) if device else select_device()
        self.feature_mean: np.ndarray | None = None
        self.feature_std: np.ndarray | None = None
        self.epochs_trained = 0

    def _set_seed(self) -> None:
        random.seed(self.seed)
        np.random.seed(self.seed)
        torch.manual_seed(self.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.seed)
        torch.use_deterministic_algorithms(True, warn_only=True)

    def _fit_scale(self, X: np.ndarray) -> None:
        self.feature_mean = X.mean(axis=(0, 1), keepdims=True)
        self.feature_std = X.std(axis=(0, 1), keepdims=True)
        self.feature_std[self.feature_std == 0] = 1.0

    def _scale(self, X: np.ndarray) -> np.ndarray:
        if self.feature_mean is None or self.feature_std is None:
            raise RuntimeError("Feature scaler is not fitted")
        return ((X - self.feature_mean) / self.feature_std).astype(np.float32)

    def fit(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_validation: np.ndarray | None = None,
        y_validation: np.ndarray | None = None,
    ) -> "TorchForecaster":
        use_early_stopping = X_validation is not None and y_validation is not None
        self._set_seed()
        self._fit_scale(X_train)
        self.network.to(self.device)
        train_dataset = TensorDataset(
            torch.from_numpy(self._scale(X_train)),
            torch.from_numpy(y_train.astype(np.float32)),
        )
        generator = torch.Generator().manual_seed(self.seed)
        loader = DataLoader(
            train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            generator=generator,
        )
        validation_x = (
            torch.from_numpy(self._scale(X_validation)).to(self.device)
            if use_early_stopping
            else None
        )
        validation_y = (
            torch.from_numpy(y_validation.astype(np.float32)).to(self.device)
            if use_early_stopping
            else None
        )
        optimizer = torch.optim.Adam(self.network.parameters(), lr=self.learning_rate)
        loss_function = nn.MSELoss()
        best_loss = float("inf")
        best_state = copy.deepcopy(self.network.state_dict())
        stale = 0
        for epoch in range(self.max_epochs):
            self.network.train()
            for batch_x, batch_y in loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)
                optimizer.zero_grad(set_to_none=True)
                loss = loss_function(self.network(batch_x), batch_y)
                loss.backward()
                nn.utils.clip_grad_norm_(
                    self.network.parameters(), self.gradient_clip_norm
                )
                optimizer.step()
            self.epochs_trained = epoch + 1
            if not use_early_stopping:
                best_state = copy.deepcopy(self.network.state_dict())
                continue
            self.network.eval()
            with torch.no_grad():
                validation_loss = float(
                    loss_function(self.network(validation_x), validation_y).item()
                )
            if validation_loss < best_loss:
                best_loss = validation_loss
                best_state = copy.deepcopy(self.network.state_dict())
                stale = 0
            else:
                stale += 1
                if stale >= self.patience:
                    break
        self.network.load_state_dict(best_state)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        self.network.eval()
        with torch.no_grad():
            tensor = torch.from_numpy(self._scale(X)).to(self.device)
            return self.network(tensor).cpu().numpy()
