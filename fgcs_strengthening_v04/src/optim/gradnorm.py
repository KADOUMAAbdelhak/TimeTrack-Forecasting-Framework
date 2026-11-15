"""Registered M1 GradNorm with pre-update model gradients and detached targets."""

from copy import deepcopy
import math

import torch
from torch import nn

from ..identity import RESOURCES, read_config
from ..provenance import measure_seconds

_SETTINGS = read_config()["secondary"]["gradnorm"]
ALPHA = _SETTINGS["alpha"]
NORM_PARAMETERS = tuple(_SETTINGS["norm_parameters"])
WEIGHT_SUM = _SETTINGS["weight_sum"]
WEIGHT_LR = _SETTINGS["weight_lr"]


def _finite(value, name):
    if not torch.isfinite(value).all():
        raise FloatingPointError(f"Nonfinite GradNorm {name}")


def _positive(value, name):
    _finite(value, name)
    if (value <= 0).any():
        raise FloatingPointError(f"Nonpositive GradNorm {name}")


def norm_parameters(model):
    encoder = dict(model.encoder.named_parameters())
    return tuple(encoder[name] for name in NORM_PARAMETERS)


def unweighted_norms(scaled_losses, parameters):
    norms = []
    for loss in scaled_losses.unbind():
        gradients = torch.autograd.grad(loss, parameters, retain_graph=True)
        vector = torch.cat([gradient.detach().reshape(-1) for gradient in gradients])
        norms.append(torch.linalg.vector_norm(vector.double()))
    return torch.stack(norms)


def balance_terms(scaled_losses, initial, weights, norms):
    """Form detached relative rates and targets and a weight-only objective."""
    _positive(initial, "reference loss")
    _positive(weights, "task weight")
    ratios = scaled_losses.detach().double() / initial.detach().double()
    _finite(ratios, "loss ratios")
    mean_ratio = ratios.mean()
    _positive(mean_ratio, "mean loss ratio")
    rates = ratios / mean_ratio
    # The positive scalar task weight multiplies every component of grad_W L_i.
    G = weights.abs() * norms.detach()
    target = (G.detach().mean() * rates.pow(ALPHA)).detach()
    objective = (G - target).abs().sum()
    for value, name in ((rates, "relative rates"), (G, "gradient norms"),
                        (target, "targets"), (objective, "weight objective")):
        _finite(value, name)
    return ratios, rates, G, target, objective


def _serialisable_weights(weights):
    return [value if math.isfinite(value) else str(value)
            for value in weights.detach().tolist()]


class GradNorm:
    def __init__(self, model):
        if model.formulation != "M1" or tuple(model.tasks) != RESOURCES:
            raise ValueError("GradNorm requires the four-task M1")
        first = next(model.parameters())
        self.weights = nn.Parameter(first.new_tensor(_SETTINGS["initial_weights"]))
        self.weight_optimizer = torch.optim.Adam([self.weights], lr=WEIGHT_LR)
        self.initial_losses = None

    def state_dict(self):
        return {"weights": self.weights.detach().clone(), "initial_losses": self.initial_losses.clone(),
                "weight_optimizer": deepcopy(self.weight_optimizer.state_dict())}

    def step(self, model, model_optimizer, losses, *, clip, record, timings=None):
        if losses.shape != (4,):
            raise ValueError("Expected the four unweighted resource MSEs")
        scaled = losses / len(RESOURCES)
        _finite(scaled, "task losses")
        record.update(scaled_losses=scaled.detach().tolist(), weights_before=_serialisable_weights(self.weights))
        if self.initial_losses is None:
            self.initial_losses = scaled.detach().clone()
        record["initial_losses"] = self.initial_losses.tolist()
        _positive(self.initial_losses, "reference loss")
        parameters = tuple(model.parameters())
        with measure_seconds(timings, "gradnorm_overhead"):
            shared_norms = unweighted_norms(scaled, norm_parameters(model))
            ratios, rates, G, target, objective = balance_terms(scaled, self.initial_losses, self.weights, shared_norms)
        model_loss = (self.weights.detach() * scaled).sum()
        _finite(model_loss, "model loss")
        with measure_seconds(timings, "gradnorm_overhead"):
            weight_gradient, = torch.autograd.grad(objective, self.weights)
        model_gradients = torch.autograd.grad(model_loss, parameters)
        _finite(weight_gradient, "weight gradient")
        for gradient in model_gradients:
            _finite(gradient, "model gradient")
        record.update(q=ratios.tolist(), r=rates.tolist(), G=G.detach().tolist(),
                      target=target.tolist(), weight_objective=objective.item(),
                      weight_gradient=weight_gradient.tolist(), model_loss=model_loss.item())

        with measure_seconds(timings, "gradnorm_overhead"):
            self.weight_optimizer.zero_grad(set_to_none=True)
            self.weights.grad = weight_gradient
            self.weight_optimizer.step()
            record["weights_proposed"] = _serialisable_weights(self.weights)
            _positive(self.weights, "proposed task weight")
            for value in self.weight_optimizer.state[self.weights].values():
                if isinstance(value, torch.Tensor):
                    _finite(value, "weight optimiser state")
            denominator = self.weights.detach().sum()
            _positive(denominator, "proposed weight sum")
            factor = WEIGHT_SUM / denominator
            normalised = self.weights.detach() * factor
            _positive(normalised, "renormalised task weight")

        for parameter, gradient in zip(parameters, model_gradients, strict=True):
            parameter.grad = gradient
        preclip = nn.utils.clip_grad_norm_(parameters, clip, error_if_nonfinite=True)
        record.update(clip_max_norm=clip, model_gradient_norm_before_clip=preclip.item())
        model_optimizer.step()
        with measure_seconds(timings, "gradnorm_overhead"), torch.no_grad():
            self.weights.copy_(normalised)
        record.update(renormalisation_factor=factor.item(), weights_after=self.weights.detach().tolist())
