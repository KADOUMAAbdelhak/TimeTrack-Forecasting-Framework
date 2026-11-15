"""Model definitions only. Inputs are [batch, context, four frozen resources]."""

from torch import nn
import torch

from ..identity import RESOURCES, SCOPES, canonical_tasks, read_config

_CONFIG = read_config()
_SETTINGS = _CONFIG["lstm"]


class LSTM(nn.Module):
    """One declared target complement, with outputs [batch, task, horizon]."""

    def __init__(self, *, formulation, block, tasks, hidden_size):
        super().__init__()
        self.tasks = canonical_tasks(tasks)
        self.formulation = formulation
        self.input_scope = SCOPES[formulation]
        self.horizons = tuple(_CONFIG["blocks"][block]["horizons"])
        self.contexts = tuple(_CONFIG["blocks"][block]["contexts"])
        self.indices = tuple(RESOURCES.index(task) for task in self.tasks)
        if formulation in {"S1", "S2"} and len(self.tasks) != 1:
            raise ValueError("An independent network must declare exactly one target")
        allowed = {_SETTINGS["primary_hidden_size"]}
        if formulation == "M0" and self.tasks == RESOURCES:
            allowed.add(_SETTINGS["m0_capacity_hidden_size"])
        if type(hidden_size) is not int or hidden_size not in allowed:
            raise ValueError("Unsupported hidden size for formulation/task subset")
        self.encoder = nn.LSTM(
            input_size=1 if self.input_scope == "own" else len(RESOURCES),
            hidden_size=hidden_size, num_layers=_SETTINGS["layers"],
            dropout=_SETTINGS["dropout"], bidirectional=_SETTINGS["bidirectional"],
            batch_first=True,
        )
        self.heads = nn.ModuleDict({
            task: nn.Linear(hidden_size, len(self.horizons), bias=_SETTINGS["head_bias"])
            for task in self.tasks
        })

    def _last_state(self, histories):
        encoded, _ = self.encoder(histories)
        return encoded[:, -1, :]

    def encode(self, windows):
        """Return the pre-head latent used by each task in canonical order."""
        if windows.ndim != 3 or windows.shape[1] not in self.contexts or windows.shape[2] != len(RESOURCES):
            raise ValueError("Expected [batch, legal context, four resources]")
        if self.input_scope == "own":
            return {task: self._last_state(windows[:, :, index:index + 1])
                    for task, index in zip(self.tasks, self.indices, strict=True)}
        shared = self._last_state(windows)
        return dict.fromkeys(self.tasks, shared)

    def forward(self, windows):
        latent = self.encode(windows)
        return torch.stack([self.heads[task](latent[task]) for task in self.tasks], dim=1)
