"""Registered M1 PCGrad with independent, reproducibly keyed task permutations."""

from dataclasses import dataclass
from hashlib import sha256

import numpy as np
import torch
from torch import nn

from ..identity import RESOURCES
from ..provenance import measure_seconds


@dataclass(frozen=True, slots=True)
class Projection:
    projected: torch.Tensor
    mean: torch.Tensor
    comparisons: list[dict]
    projection_count: int
    zero_norm_skips: int


def permutation_schedule(seed, epoch, batch):
    seeds, orders = [], []
    for index, task in enumerate(RESOURCES):
        key = f"fgcs-v03|pcgrad|{seed}|{epoch}|{batch}|{task}"
        stream = int.from_bytes(sha256(key.encode()).digest()[:8], "little")
        rng = np.random.Generator(np.random.PCG64(stream))
        seeds.append(stream)
        orders.append(rng.permutation([other for other in range(len(RESOURCES)) if other != index]).tolist())
    return seeds, orders


def project_shared(gradients, orders):
    """Project rows against immutable original rows, then average."""
    if gradients.ndim != 2 or gradients.shape[0] < 2 or len(orders) != len(gradients):
        raise ValueError("Expected one gradient row and comparison order per task")
    original = gradients.detach().double()
    if not torch.isfinite(original).all():
        raise FloatingPointError("Nonfinite PCGrad task gradient")
    projected = original.clone()
    norms_squared = original.square().sum(dim=1)
    original_dots = original @ original.T
    comparisons = []
    projections = zero_skips = 0
    for i, order in enumerate(orders):
        if len(order) != len(original) - 1 or set(order) != set(range(len(original))) - {i}:
            raise ValueError("Comparison order must contain every other task exactly once")
        for j in order:
            direction = original[j]
            before = torch.dot(projected[i], direction)
            zero_norm = norms_squared[j].item() == 0
            apply = not zero_norm and before.item() < 0
            if apply:
                projected[i] -= (before / norms_squared[j]) * direction
            projections += int(apply)
            zero_skips += int(zero_norm)
            comparisons.append({"task": i, "reference": j, "original_dot": original_dots[i, j].item(),
                                "dot_before": before.item(), "dot_after": torch.dot(projected[i], direction).item(),
                                "projected": apply, "zero_norm_skip": zero_norm})
    mean = projected.mean(dim=0).to(gradients.dtype)
    if not torch.isfinite(mean).all():
        raise FloatingPointError("Nonfinite PCGrad aggregate")
    return Projection(projected, mean, comparisons, projections, zero_skips)


def step(model, optimizer, losses, *, seed, epoch, batch, clip, record, timings=None):
    """Install projected encoder gradients and ordinary mean-loss head gradients."""
    if model.formulation != "M1" or tuple(model.tasks) != RESOURCES or losses.shape != (4,):
        raise ValueError("PCGrad requires the four-task M1")
    shared = tuple(model.encoder.parameters())
    heads = tuple(model.heads.parameters())
    with measure_seconds(timings, "pcgrad_overhead"):
        seeds, orders = permutation_schedule(seed, epoch, batch)
        record.update(permutation_seeds=seeds, permutation_orders=orders)
        rows = [
            torch.cat([g.reshape(-1) for g in torch.autograd.grad(loss, shared, retain_graph=True)])
            for loss in losses.unbind()
        ]
        result = project_shared(torch.stack(rows), orders)
    head_gradients = torch.autograd.grad(losses.mean(), heads)
    for parameter, gradient in zip(shared, result.mean.split([p.numel() for p in shared]), strict=True):
        parameter.grad = gradient.reshape_as(parameter).clone()
    for parameter, gradient in zip(heads, head_gradients, strict=True):
        parameter.grad = gradient
    record.update(projection_count=result.projection_count, zero_norm_skips=result.zero_norm_skips,
                  comparisons=result.comparisons, shared_gradient_sha256=sha256(
                      result.mean.contiguous().cpu().numpy().tobytes()).hexdigest(),
                  shared_gradient_l2=torch.linalg.vector_norm(result.mean.double()).item())
    preclip = nn.utils.clip_grad_norm_(model.parameters(), clip, error_if_nonfinite=True)
    record.update(clip_max_norm=clip, model_gradient_norm_before_clip=preclip.item())
    optimizer.step()
    return result
