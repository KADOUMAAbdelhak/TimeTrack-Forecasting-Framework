"""Registered PatchTST-style adaptations: channel-independent (own input) and channel-dependent (all input)."""

import torch
from torch import nn

from ..identity import RESOURCES, read_config
from ._transformer import SETTINGS as TRANSFORMER, make_encoder

_SETTINGS = read_config()["modern"]["families"]["PatchTST"]


class PatchTST(nn.Module):
    def __init__(self, context, tasks):
        super().__init__()
        self.context = context
        self.tasks = tuple(tasks)
        self.channels = len(self.tasks)
        if self.channels not in (1, len(RESOURCES)):
            raise ValueError("Expected one target or the full shared complement")
        self.patch_length = _SETTINGS["patch"]
        self.stride = _SETTINGS["stride"]
        self.patch_count = (context - self.patch_length) // self.stride + 1
        if self.patch_count < 2 or (self.patch_count - 1) * self.stride + self.patch_length != context:
            raise ValueError("Patch layout must cover the entire history with at least two tokens")
        width = TRANSFORMER["width"]
        self.patch_projection = nn.Linear(self.patch_length, width, bias=TRANSFORMER["bias"])
        self.position = nn.Parameter(torch.zeros(self.patch_count, width))
        self.backbone = make_encoder()
        self.heads = nn.ModuleDict({task: nn.Linear(width, 5, bias=TRANSFORMER["bias"]) for task in self.tasks})

    def patches(self, windows):
        if windows.ndim != 3 or windows.shape[1:] != (self.context, self.channels):
            raise ValueError("PatchTST-style expects [batch, context, declared input channels]")
        return windows.transpose(1, 2).unfold(-1, self.patch_length, self.stride)

    def forward(self, windows):
        patches = self.patches(windows)
        # Each channel is a separate batch element, so attention sees only its patch tokens.
        tokens = self.patch_projection(patches.flatten(0, 1)) + self.position
        latent = self.backbone(tokens).mean(dim=1).reshape(windows.shape[0], self.channels, -1)
        return torch.stack([self.heads[task](latent[:, i]) for i, task in enumerate(self.tasks)], dim=1)


class PatchTSTChannelDependent(nn.Module):
    """v0.4 all-input PatchTST-style adaptation: each token holds every channel's values in one patch."""

    def __init__(self, context, tasks):
        super().__init__()
        self.context = context
        self.tasks = tuple(tasks)
        self.channels = len(RESOURCES)
        if len(self.tasks) not in (1, len(RESOURCES)):
            raise ValueError("Expected one target or the full shared complement")
        self.patch_length = _SETTINGS["patch"]
        self.stride = _SETTINGS["stride"]
        self.patch_count = (context - self.patch_length) // self.stride + 1
        if self.patch_count < 2 or (self.patch_count - 1) * self.stride + self.patch_length != context:
            raise ValueError("Patch layout must cover the entire history with at least two tokens")
        width = TRANSFORMER["width"]
        self.patch_projection = nn.Linear(self.channels * self.patch_length, width, bias=TRANSFORMER["bias"])
        self.position = nn.Parameter(torch.zeros(self.patch_count, width))
        self.backbone = make_encoder()
        self.heads = nn.ModuleDict({task: nn.Linear(width, 5, bias=TRANSFORMER["bias"]) for task in self.tasks})

    def patches(self, windows):
        """Return [batch, patch, channel, patch value]."""
        if windows.ndim != 3 or windows.shape[1:] != (self.context, self.channels):
            raise ValueError("Channel-dependent PatchTST-style expects [batch, context, four resource channels]")
        return windows.transpose(1, 2).unfold(-1, self.patch_length, self.stride).transpose(1, 2)

    def forward(self, windows):
        tokens = self.patch_projection(self.patches(windows).flatten(2)) + self.position
        latent = self.backbone(tokens).mean(dim=1)
        return torch.stack([self.heads[task](latent) for task in self.tasks], dim=1)
