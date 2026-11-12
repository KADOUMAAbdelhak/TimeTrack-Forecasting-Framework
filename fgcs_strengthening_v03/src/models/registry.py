"""Explicit model and optimiser registry for the modern reduced study."""

from dataclasses import dataclass

import torch
from torch import nn

from ..identity import RESOURCES, canonical_tasks, read_config
from ..modern.design import CONTEXTS
from .dlinear import DLinear
from .itransformer import ITransformer
from .patchtst import PatchTST

_SETTINGS = read_config()["modern"]


@dataclass(frozen=True, slots=True)
class Family:
    label: str
    model: type[nn.Module]
    scope: str
    optimizer: type[torch.optim.Optimizer]

    def build(self, context, tasks):
        tasks = canonical_tasks(tasks)
        if context not in CONTEXTS or len(tasks) not in (1, len(RESOURCES)):
            raise ValueError("Expected a registered modern context and complement")
        return self.model(context, tasks)

    def make_optimizer(self, model):
        options = {"lr": _SETTINGS["learning_rate"]}
        if self.optimizer is torch.optim.AdamW:
            options["weight_decay"] = _SETTINGS["transformer"]["weight_decay"]
        return self.optimizer(model.parameters(), **options)


REGISTRY = {
    "DLinear": Family("DLinear", DLinear, "own", torch.optim.Adam),
    "PatchTST": Family("PatchTST-style", PatchTST, "own", torch.optim.AdamW),
    "iTransformer": Family("iTransformer-style", ITransformer, "all", torch.optim.AdamW),
}
