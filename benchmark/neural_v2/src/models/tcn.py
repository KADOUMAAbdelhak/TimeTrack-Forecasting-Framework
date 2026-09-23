"""Full-receptive-field causal residual TCN baseline."""

from __future__ import annotations

import torch
from torch import nn


FROZEN_CHANNELS = (32, 32, 32, 32, 32, 32)
FROZEN_DILATIONS = (1, 2, 4, 8, 16, 32)
FROZEN_KERNEL_SIZE = 3
CONVOLUTIONS_PER_BLOCK = 2


def receptive_field(
    kernel_size: int = FROZEN_KERNEL_SIZE,
    dilations: tuple[int, ...] = FROZEN_DILATIONS,
    convolutions_per_block: int = CONVOLUTIONS_PER_BLOCK,
) -> int:
    return 1 + convolutions_per_block * (kernel_size - 1) * sum(dilations)


class CausalConv1d(nn.Conv1d):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        dilation: int,
    ) -> None:
        self.causal_padding = (kernel_size - 1) * dilation
        super().__init__(
            in_channels,
            out_channels,
            kernel_size,
            dilation=dilation,
            padding=self.causal_padding,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        values = super().forward(x)
        return values[..., : -self.causal_padding] if self.causal_padding else values


class ResidualBlock(nn.Module):
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        dilation: int,
        dropout: float,
    ) -> None:
        super().__init__()
        self.conv1 = CausalConv1d(in_channels, out_channels, kernel_size, dilation)
        self.conv2 = CausalConv1d(out_channels, out_channels, kernel_size, dilation)
        self.activation = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.residual = (
            nn.Identity()
            if in_channels == out_channels
            else nn.Conv1d(in_channels, out_channels, kernel_size=1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        output = self.dropout(self.activation(self.conv1(x)))
        output = self.dropout(self.activation(self.conv2(output)))
        return self.activation(output + self.residual(x))


class FullReceptiveFieldTCN(nn.Module):
    def __init__(
        self,
        input_channels: int,
        channels: tuple[int, ...] = FROZEN_CHANNELS,
        kernel_size: int = FROZEN_KERNEL_SIZE,
        dilations: tuple[int, ...] = FROZEN_DILATIONS,
        dropout: float = 0.1,
        output_size: int = 8,
    ) -> None:
        super().__init__()
        if len(channels) != len(dilations):
            raise ValueError("TCN channels and dilations must have equal length")
        blocks = []
        previous = input_channels
        for width, dilation in zip(channels, dilations):
            blocks.append(
                ResidualBlock(
                    previous,
                    width,
                    kernel_size=kernel_size,
                    dilation=dilation,
                    dropout=dropout,
                )
            )
            previous = width
        self.blocks = nn.Sequential(*blocks)
        self.head = nn.Linear(previous, output_size)

    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        return self.blocks(x.transpose(1, 2))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.forward_features(x)[:, :, -1])
