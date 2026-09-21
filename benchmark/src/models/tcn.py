"""Small causal temporal convolutional baseline."""

from __future__ import annotations

import torch
from torch import nn

from .neural import TorchForecaster


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
        output = super().forward(x)
        return output[..., : -self.causal_padding] if self.causal_padding else output


class TemporalBlock(nn.Module):
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


class TCNNetwork(nn.Module):
    def __init__(
        self,
        input_channels: int,
        channels: tuple[int, ...] = (32, 32),
        kernel_size: int = 3,
        dropout: float = 0.1,
        output_size: int = 8,
    ) -> None:
        super().__init__()
        blocks = []
        previous = input_channels
        for level, width in enumerate(channels):
            blocks.append(
                TemporalBlock(
                    previous,
                    width,
                    kernel_size,
                    dilation=2**level,
                    dropout=dropout,
                )
            )
            previous = width
        self.blocks = nn.Sequential(*blocks)
        self.head = nn.Linear(previous, output_size)

    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        return self.blocks(x.transpose(1, 2))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        sequence = self.forward_features(x)
        return self.head(sequence[:, :, -1])


class TCNForecaster(TorchForecaster):
    def __init__(
        self,
        input_channels: int,
        seed: int,
        channels: tuple[int, ...] = (32, 32),
        kernel_size: int = 3,
        dropout: float = 0.1,
        **training: object,
    ) -> None:
        torch.manual_seed(seed)
        network = TCNNetwork(
            input_channels=input_channels,
            channels=channels,
            kernel_size=kernel_size,
            dropout=dropout,
        )
        super().__init__(network=network, seed=seed, **training)
