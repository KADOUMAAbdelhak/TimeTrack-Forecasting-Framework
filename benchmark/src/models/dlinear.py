"""Multivariate-input, sparse-multi-horizon DLinear baseline."""

from __future__ import annotations

import torch
from torch import nn

from .neural import TorchForecaster


class DLinearNetwork(nn.Module):
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
        self.kernel = moving_average_kernel
        self.average = nn.AvgPool1d(
            kernel_size=moving_average_kernel, stride=1
        )
        self.trend_projection = nn.Linear(context_length, output_size)
        self.residual_projection = nn.Linear(context_length, output_size)
        self.channel_projection = nn.Linear(input_channels, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        channels_first = x.transpose(1, 2)
        left = (self.kernel - 1) // 2
        right = self.kernel - 1 - left
        padded = nn.functional.pad(channels_first, (left, right), mode="replicate")
        trend = self.average(padded)
        residual = channels_first - trend
        projected = self.trend_projection(trend) + self.residual_projection(residual)
        return self.channel_projection(projected.transpose(1, 2)).squeeze(-1)


class DLinearForecaster(TorchForecaster):
    def __init__(
        self,
        context_length: int,
        input_channels: int,
        seed: int,
        moving_average_kernel: int = 25,
        **training: object,
    ) -> None:
        torch.manual_seed(seed)
        network = DLinearNetwork(
            context_length=context_length,
            input_channels=input_channels,
            moving_average_kernel=moving_average_kernel,
        )
        super().__init__(network=network, seed=seed, **training)
