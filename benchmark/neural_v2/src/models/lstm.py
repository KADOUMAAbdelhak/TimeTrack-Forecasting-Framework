"""Conventional unidirectional LSTM forecasting baseline."""

from __future__ import annotations

import torch
from torch import nn


class LSTMForecaster(nn.Module):
    def __init__(
        self,
        input_channels: int,
        hidden_size: int = 64,
        layers: int = 2,
        dropout: float = 0.1,
        output_size: int = 8,
    ) -> None:
        super().__init__()
        self.input_channels = input_channels
        self.hidden_size = hidden_size
        self.layers = layers
        self.bidirectional = False
        self.lstm = nn.LSTM(
            input_size=input_channels,
            hidden_size=hidden_size,
            num_layers=layers,
            dropout=dropout if layers > 1 else 0.0,
            batch_first=True,
            bidirectional=False,
        )
        self.head = nn.Linear(hidden_size, output_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        sequence, _ = self.lstm(x)
        return self.head(sequence[:, -1, :])
