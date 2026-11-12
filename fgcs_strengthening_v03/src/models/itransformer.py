"""Registered iTransformer-style four-variate attention for both complements."""

import torch
from torch import nn

from ..identity import RESOURCES
from ._transformer import SETTINGS as TRANSFORMER, make_encoder


class ITransformer(nn.Module):
    def __init__(self, context, tasks):
        super().__init__()
        self.context = context
        self.tasks = tuple(tasks)
        if len(self.tasks) not in (1, len(RESOURCES)):
            raise ValueError("Expected one target or the full joint complement")
        width = TRANSFORMER["width"]
        self.temporal_projection = nn.Linear(context, width, bias=TRANSFORMER["bias"])
        self.backbone = make_encoder()
        self.heads = nn.ModuleDict({
            task: nn.Linear(len(RESOURCES) * width, 5, bias=TRANSFORMER["bias"]) for task in self.tasks
        })

    def variate_tokens(self, windows):
        if windows.ndim != 3 or windows.shape[1:] != (self.context, len(RESOURCES)):
            raise ValueError("iTransformer-style requires all four real input histories")
        return self.temporal_projection(windows.transpose(1, 2))

    def forward(self, windows):
        encoded = self.backbone(self.variate_tokens(windows)).flatten(start_dim=1)
        return torch.stack([self.heads[task](encoded) for task in self.tasks], dim=1)
