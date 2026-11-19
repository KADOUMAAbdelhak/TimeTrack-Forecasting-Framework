"""Explicit model and optimiser registry for the modern reduced study."""

from dataclasses import dataclass

import torch
from torch import nn

from ..identity import RESOURCES, canonical_tasks, read_config
from ..modern.design import CONTEXTS
from .dlinear import DLinear, DLinearAllInput
from .itransformer import ITransformer
from .patchtst import PatchTST, PatchTSTChannelDependent

_SETTINGS = read_config()["modern"]


@dataclass(frozen=True, slots=True)
class Family:
    label: str
    models: tuple[tuple[str, type[nn.Module]], ...]
    optimizer: type[torch.optim.Optimizer]

    @property
    def scopes(self):
        return tuple(scope for scope, _ in self.models)

    def build(self, context, tasks, scope):
        tasks = canonical_tasks(tasks)
        if context not in CONTEXTS or len(tasks) not in (1, len(RESOURCES)):
            raise ValueError("Expected a registered modern context and complement")
        model = dict(self.models).get(scope)
        if model is None:
            raise ValueError(f"{self.label} has no {scope!r}-input model")
        return model(context, tasks)

    def make_optimizer(self, model):
        options = {"lr": _SETTINGS["learning_rate"]}
        if self.optimizer is torch.optim.AdamW:
            options["weight_decay"] = _SETTINGS["transformer"]["weight_decay"]
        return self.optimizer(model.parameters(), **options)


REGISTRY = {
    "DLinear": Family("DLinear", (("own", DLinear), ("all", DLinearAllInput)), torch.optim.Adam),
    "PatchTST": Family("PatchTST-style", (("own", PatchTST), ("all", PatchTSTChannelDependent)), torch.optim.AdamW),
    "iTransformer": Family("iTransformer-style", (("all", ITransformer),), torch.optim.AdamW),
}
