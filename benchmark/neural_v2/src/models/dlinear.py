"""Multivariate-input, CPU-output DLinear baseline."""

from __future__ import annotations

import torch
from torch import nn


class DLinear(nn.Module):
    def __init__(
        self,
        context_length: int,
        input_channels: int,
        output_size: int = 8,
        moving_average_kernel: int = 25,
    ) -> None:
        super().__init__()
        self.context_length = context_length
        self.input_channels = input_channels
        self.output_size = output_size
        self.moving_average_kernel = moving_average_kernel
        self.average = nn.AvgPool1d(moving_average_kernel, stride=1)
        self.trend_projection = nn.Linear(context_length, output_size)
        self.residual_projection = nn.Linear(context_length, output_size)
        self.channel_projection = nn.Linear(input_channels, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3 or x.shape[1:] != (
            self.context_length,
            self.input_channels,
        ):
            raise ValueError("DLinear input must have shape [batch, L, channels]")
        channels_first = x.transpose(1, 2)
        left = (self.moving_average_kernel - 1) // 2
        right = self.moving_average_kernel - 1 - left
        padded = nn.functional.pad(channels_first, (left, right), mode="replicate")
        trend = self.average(padded)
        residual = channels_first - trend
        projected = self.trend_projection(trend) + self.residual_projection(residual)
        return self.channel_projection(projected.transpose(1, 2)).squeeze(-1)
