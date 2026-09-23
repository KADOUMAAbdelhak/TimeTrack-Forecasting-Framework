"""Compact PatchTST-style channel-independent history encoder."""

from __future__ import annotations

import torch
from torch import nn


class PatchTST(nn.Module):
    """Shared per-channel encoder with fixed late mixing in the output head."""

    def __init__(
        self,
        context_length: int,
        input_channels: int,
        patch_length: int = 8,
        stride: int = 4,
        d_model: int = 64,
        attention_heads: int = 4,
        encoder_layers: int = 2,
        feed_forward_dimension: int = 128,
        dropout: float = 0.1,
        output_size: int = 8,
    ) -> None:
        super().__init__()
        if context_length < patch_length:
            raise ValueError("Context length is shorter than one patch")
        self.context_length = context_length
        self.input_channels = input_channels
        self.patch_length = patch_length
        self.stride = stride
        self.patch_count = 1 + (context_length - patch_length) // stride
        self.patch_projection = nn.Linear(patch_length, d_model)
        self.position = nn.Parameter(torch.zeros(1, self.patch_count, d_model))
        layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=attention_heads,
            dim_feedforward=feed_forward_dimension,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=False,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=encoder_layers)
        self.head = nn.Linear(input_channels * d_model, output_size)

    def construct_patches(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3 or x.shape[1:] != (
            self.context_length,
            self.input_channels,
        ):
            raise ValueError("PatchTST input must have shape [batch, L, channels]")
        return x.transpose(1, 2).unfold(-1, self.patch_length, self.stride)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        patches = self.construct_patches(x)
        batch, channels, patch_count, patch_length = patches.shape
        tokens = patches.reshape(batch * channels, patch_count, patch_length)
        encoded = self.encoder(self.patch_projection(tokens) + self.position)
        channel_representations = encoded.mean(dim=1).reshape(batch, -1)
        return self.head(channel_representations)
