"""Registered short-context DLinear with channel-independent projections."""

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
