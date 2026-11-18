"""Clone-only extraction and contamination checks for registered diagnostics."""

from copy import deepcopy
from hashlib import sha256
import random

import numpy as np
import torch

from ..identity import RESOURCES, canonical_json, read_config
from ..training import task_mse

PARAMETERS = tuple(read_config()["diagnostics"]["parameters"])


def _state_digest(value):
    """Hash nested CPU or device state without invoking an RNG or optimiser step."""
    digest = sha256()

    def update(item):
        if isinstance(item, torch.Tensor):
            tensor = item.detach().cpu().contiguous()
            update(("tensor", str(tensor.dtype), tuple(tensor.shape)))
            data = tensor.reshape(-1).view(torch.uint8).numpy().tobytes()
            digest.update(len(data).to_bytes(8, "little"))
            digest.update(data)
        elif isinstance(item, np.ndarray):
            update(("array", item.dtype.str, item.shape))
            data = item.tobytes()
            digest.update(len(data).to_bytes(8, "little"))
            digest.update(data)
        elif isinstance(item, dict):
            update(("dict", len(item)))
            for key in sorted(item, key=canonical_json):
                update(key)
                update(item[key])
        elif isinstance(item, (tuple, list)):
            digest.update(canonical_json([type(item).__name__, len(item)]) + b"\n")
            for child in item:
                update(child)
        else:
            digest.update(canonical_json(item) + b"\n")

    update(value)
    return digest.hexdigest()


def live_state_hashes(model, optimizer, shuffle_generator):
    return {
        "model": _state_digest(dict(model.named_parameters())),
        "buffers": _state_digest(dict(model.named_buffers())),
        "model_mode": _state_digest({name: module.training for name, module in model.named_modules()}),
        "optimizer": _state_digest(optimizer.state_dict()),
        "gradients": _state_digest({name: parameter.grad for name, parameter in model.named_parameters()}),
        "python_rng": _state_digest(random.getstate()),
        "numpy_rng": _state_digest(np.random.get_state()),
        "torch_cpu_rng": _state_digest(torch.random.get_rng_state()),
        "training_shuffle_rng": _state_digest(shuffle_generator.get_state()),
    }


class StateContamination(RuntimeError):
    pass


class DiagnosticClone:
    """An owned copy with CPU float32 weights and gradients restricted to the encoder."""

    def __init__(self, live_model, state):
        with torch.inference_mode(False):
            self.model = deepcopy(live_model).to(device="cpu", dtype=torch.float32)
            self.model.load_state_dict(state, strict=True)
            self.model.eval()
            self.model.requires_grad_(False)
            encoder = dict(self.model.encoder.named_parameters())
            if set(encoder) != set(PARAMETERS) or tuple(self.model.tasks) != RESOURCES:
                raise ValueError("Diagnostic model must expose the registered encoder and four task heads")
            self.parameters = tuple(encoder[name].requires_grad_(True) for name in PARAMETERS)

    def extract(self, inputs, targets):
        """Compute all four task gradients from the very same batch and forward pass."""
        with torch.inference_mode(False), torch.enable_grad(), torch.autocast("cpu", enabled=False):
            inputs = inputs.detach().to(device="cpu", dtype=torch.float32, copy=inputs.is_inference())
            targets = targets.detach().to(device="cpu", dtype=torch.float32, copy=targets.is_inference())
            losses = task_mse(self.model(inputs), targets)
            if not torch.isfinite(losses).all():
                raise FloatingPointError("Nonfinite diagnostic task loss")
            output = {}
            for index, task in enumerate(RESOURCES):
                gradient = torch.autograd.grad(losses[index], self.parameters, retain_graph=index < len(RESOURCES) - 1)
                vector = torch.cat([tensor.reshape(-1) for tensor in gradient]).detach()
                if not torch.isfinite(vector).all():
                    raise FloatingPointError(f"Nonfinite diagnostic gradient for {task}")
                output[task] = vector
            return output
