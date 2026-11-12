"""Generated CPU models, manifests, and histories for systems tests."""

from dataclasses import replace
from hashlib import sha256

import numpy as np
import torch
from torch import nn

from fgcs_strengthening_v03.src.identity import RESOURCES
from fgcs_strengthening_v03.src.systems import (
    BenchmarkPlan, CheckpointRef, Complement, ForwardPath, MeasurementBinding,
    partition_origin_key, sample_origins, torch_footprint,
)
from fgcs_strengthening_v03.src.systems_environment import Hardware, MachineManifest, REGISTERED, Software
from fgcs_strengthening_v03.src.training import _encode
from fgcs_strengthening_v03.tests.training_fixtures import digest, identity


def manifest():
    return MachineManifest(Hardware("test-host", "synthetic CPU", 2, 4, 1024, "Darwin", "kernel", "unavailable"),
                           Software("python", "numpy", "torch", "tree", "sklearn", "backend"), REGISTERED)


class TinyModel(nn.Module):
    def __init__(self, tasks, calls):
        super().__init__()
        self.scale = nn.Parameter(torch.ones(()))
        self.register_buffer("offset", torch.zeros(()))
        self.tasks, self.calls = tasks, calls

    def forward(self, values):
        assert not self.training
        assert not torch.is_grad_enabled()
        self.calls.append((self.tasks, len(values)))
        return (values[:, :1, :1] * self.scale + self.offset).expand(-1, len(self.tasks), 5)


def physical(unit, model, *, epoch=1, optimizer=123):
    encoded = _encode(model.state_dict())
    ref = CheckpointRef(unit, sha256(encoded).hexdigest(), digest("outcome:" + unit.digest), epoch)
    return torch_footprint(ref, model, encoded, optimizer_state_bytes=optimizer)


def complement(formulation, calls, *, task_control=False):
    unit = identity(formulation, phase="final")
    if task_control:
        groups = (RESOURCES[:2], RESOURCES[2:])
    else:
        groups = tuple((task,) for task in RESOURCES) if formulation.startswith("S") else (RESOURCES,)
    paths = []
    for epoch, tasks in enumerate(groups, start=1):
        model_id = replace(unit, tasks=tasks) if formulation.startswith("S") else unit
        model = TinyModel(model_id.tasks, calls)
        paths.append(ForwardPath(tasks, (physical(model_id, model, epoch=epoch),), model, 4))
    return Complement(paths, task_checkpoints=task_control)


def plan_for(deployment, *, origin_count=130, history_calls=None):
    hardware = manifest()
    units = tuple(dict.fromkeys(ref.identity for ref in deployment.refs))
    origins = sample_origins(partition_origin_key(units[0].block, units[0].entity, units[0].fold),
                             tuple(range(origin_count)))
    histories = np.ones((len(origins.positions), 4, 4), dtype=np.float32)
    targets = tuple((task, tuple(ref.checkpoint_sha256 for path in deployment.paths_for(task)
                                 for ref in (state.ref for state in path.states))) for task in RESOURCES)
    binding = MeasurementBinding(deployment.refs, deployment.formulation, 4, RESOURCES, hardware.hardware_sha256,
                                 hardware.software_sha256, origins.sha256,
                                 *(digest(value) for value in ("protocol", "config", "source", "input")), units, targets)

    class Preprocessing:
        @staticmethod
        def scale_benchmark_histories(raw):
            history_calls.append("transform")
            return raw * 2

        @staticmethod
        def inverse_target(predictions, task):
            history_calls.append(task)
            return predictions * 3, None

    return BenchmarkPlan(deployment, origins, binding, histories, histories * 2, Preprocessing())
