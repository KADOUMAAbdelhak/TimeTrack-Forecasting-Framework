"""Registered short-context DLinear: channel-independent (own input) and decomposed ARX (all input)."""

import torch
from torch import nn
from torch.nn import functional as F

from ..identity import RESOURCES, read_config

_SETTINGS = read_config()["modern"]["families"]["DLinear"]


def kernel_for_context(context):
    if type(context) is not int or context < 1:
        raise ValueError("Expected a positive context length")
    return min(_SETTINGS["kernel_cap"], context if context % 2 else context - 1)


class DLinear(nn.Module):
    def __init__(self, context, tasks):
        super().__init__()
        self.context = context
        self.tasks = tuple(tasks)
        self.channels = len(self.tasks)
        if self.channels not in (1, len(RESOURCES)):
            raise ValueError("Expected one target or the full shared complement")
        self.kernel = kernel_for_context(context)
        self.trend_projection = nn.Linear(context, 5)
        self.residual_projection = nn.Linear(context, 5)

    def decompose(self, windows):
        if windows.ndim != 3 or windows.shape[1:] != (self.context, self.channels):
            raise ValueError("DLinear expects [batch, context, declared input channels]")
        histories = windows.transpose(1, 2)
        half = self.kernel // 2
        trend = F.avg_pool1d(F.pad(histories, (half, half), mode="replicate"), self.kernel, stride=1)
        return trend, histories - trend

    def forward(self, windows):
        trend, residual = self.decompose(windows)
        return self.trend_projection(trend) + self.residual_projection(residual)


class DLinearAllInput(nn.Module):
    """v0.4 all-input DLinear: S2 is a decomposed linear ARX; M1 adds a shared linear bottleneck."""

    def __init__(self, context, tasks):
        super().__init__()
        self.context = context
        self.tasks = tuple(tasks)
        self.channels = len(RESOURCES)
        if len(self.tasks) not in (1, len(RESOURCES)):
            raise ValueError("Expected one target or the full shared complement")
        self.kernel = kernel_for_context(context)
        features = 2 * self.channels * context
        settings = _SETTINGS["all_scope"]
        if len(self.tasks) == 1:
            self.bottleneck = None
            self.heads = nn.ModuleDict({self.tasks[0]: nn.Linear(features, 5)})
        else:
            width = settings["M1_bottleneck"]
            self.bottleneck = nn.Linear(features, width, bias=settings["M1_bottleneck_bias"])
            self.heads = nn.ModuleDict({task: nn.Linear(width, 5) for task in self.tasks})

    def decompose(self, windows):
        if windows.ndim != 3 or windows.shape[1:] != (self.context, self.channels):
            raise ValueError("All-input DLinear expects [batch, context, four resource channels]")
        histories = windows.transpose(1, 2)
        half = self.kernel // 2
        trend = F.avg_pool1d(F.pad(histories, (half, half), mode="replicate"), self.kernel, stride=1)
        return trend, histories - trend

    def features(self, windows):
        trend, residual = self.decompose(windows)
        # [batch, channel, (trend lags, residual lags)] flattened channel-major to 8L features.
        return torch.cat((trend, residual), dim=-1).flatten(1)

    def forward(self, windows):
        features = self.features(windows)
        if self.bottleneck is not None:
            features = self.bottleneck(features)
        return torch.stack([self.heads[task](features) for task in self.tasks], dim=1)
