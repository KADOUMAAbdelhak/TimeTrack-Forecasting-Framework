"""Deliberately plain single-target and shared multi-target LSTMs."""

from __future__ import annotations

import torch
from torch import nn


class SingleTargetLSTM(nn.Module):
    def __init__(self, input_channels: int, hidden_size: int = 64, layers: int = 2, dropout: float = 0.1) -> None:
        super().__init__()
        self.input_channels = input_channels
        self.encoder = nn.LSTM(input_channels, hidden_size, layers, dropout=dropout, batch_first=True, bidirectional=False)
        self.head = nn.Linear(hidden_size, 8)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        sequence, _ = self.encoder(x)
        return self.head(sequence[:, -1, :])


class MultiTargetLSTM(nn.Module):
    def __init__(self, input_channels: int = 4, hidden_size: int = 64, layers: int = 2, dropout: float = 0.1) -> None:
        super().__init__()
        if input_channels != 4:
            raise ValueError("M1 requires exactly four ordered input resources")
        self.input_channels = input_channels
        self.encoder = nn.LSTM(input_channels, hidden_size, layers, dropout=dropout, batch_first=True, bidirectional=False)
        self.heads = nn.ModuleList([nn.Linear(hidden_size, 8) for _ in range(4)])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        sequence, _ = self.encoder(x)
        representation = sequence[:, -1, :]
        return torch.stack([head(representation) for head in self.heads], dim=1)
