"""Synthetic preflight for every context and model in each modern complement."""

import torch

from ..identity import RESOURCES
from ..models.dlinear import DLinear, DLinearAllInput
from ..models.patchtst import PatchTST, PatchTSTChannelDependent
from ..models.registry import REGISTRY
from ..residual import anchor
from ..training import cpu_seed_scope, task_mse
from .design import CONTEXTS

_TASKS = tuple((task,) for task in RESOURCES) + (RESOURCES,)


def _tokens_and_coverage(family, model, windows):
    context = model.context
    if isinstance(model, DLinear):
        trend, residual = model.decompose(windows)
        if trend.shape[-1] != context or residual.shape != trend.shape or any(
                layer.in_features != context for layer in (model.trend_projection, model.residual_projection)):
            raise ValueError("DLinear does not project every lag in both paths")
        return None
    if isinstance(model, DLinearAllInput):
        trend, residual = model.decompose(windows)
        first = model.bottleneck if model.bottleneck is not None else next(iter(model.heads.values()))
        if (trend.shape[1:] != (4, context) or residual.shape != trend.shape
                or model.features(windows).shape[-1] != 8 * context or first.in_features != 8 * context):
            raise ValueError("All-input DLinear does not project every channel's trend and residual lags")
        return None
    if isinstance(model, PatchTSTChannelDependent):
        lags = torch.arange(context, dtype=windows.dtype)[None, :, None].expand(1, context, 4)
        patches = model.patches(lags)
        if (patches.shape[1:] != (context - 1, 4, 2) or model.patch_projection.in_features != 8
                or not torch.equal(patches[0, :, 0].unique(sorted=True), lags[0, :, 0])):
            raise ValueError("Channel-dependent patches do not cover every input lag of every channel")
        return patches.shape[1]
    if isinstance(model, PatchTST):
        lags = torch.arange(context, dtype=windows.dtype)[None, :, None].expand(1, context, model.channels)
        patches = model.patches(lags)
        if (patches.shape[-2:] != (context - 1, 2) or model.patch_projection.in_features != 2
                or not torch.equal(patches[0, 0].unique(sorted=True), lags[0, :, 0])):
            raise ValueError("PatchTST-style patches do not cover every input lag")
        return patches.shape[-2]
    tokens = model.variate_tokens(windows)
    if tokens.shape[1] != 4 or model.temporal_projection.in_features != context:
        raise ValueError("iTransformer-style must project the full history into four variate tokens")
    return tokens.shape[1]


def _perturbations(model, window, scope):
    """Finite perturbations test dependencies without thresholding numerical derivatives."""
    _, context, channels = window.shape
    resources = window.expand(channels, -1, -1).clone()
    for channel in range(channels):
        resources[channel, :, channel] += torch.linspace(0.5, 2.5, context)
    lags = window.expand(context, -1, -1).clone()
    for lag in range(context):
        lags[lag, lag, :] += 2.0
    with torch.no_grad():
        output = model(torch.cat((window, resources, lags), dim=0))
    if not torch.isfinite(output).all():
        raise ValueError("Nonfinite perturbation forecast")
    resource_delta = (output[1:channels + 1] != output[0]).any(dim=-1)
    expected = torch.ones_like(resource_delta) if scope == "all" else torch.eye(channels, dtype=torch.bool)
    if not torch.equal(resource_delta, expected):
        raise ValueError("Input perturbation contradicts the registered routing")
    if not ((output[channels + 1:] != output[0]).flatten(1).any(dim=1)).all():
        raise ValueError("An input lag has no observable path to any output")
    return resource_delta.tolist()


@torch.no_grad()
def _cross_variate_attention(model, window):
    base = model.variate_tokens(window)
    changed = base.expand(4, -1, -1).clone()
    for token in range(4):
        changed[token, token] += torch.linspace(-1., 2., base.shape[-1])
    encoded = model.backbone(torch.cat((base, changed), dim=0))
    effects = (encoded[1:] != encoded[0]).any(dim=-1)
    if not torch.isfinite(encoded).all() or not effects.all():
        raise ValueError("Encoded variates do not exhibit the registered cross-variate attention paths")
    return effects.tolist()


def validate_family_structure(family):
    """Return 15 synthetic check records per input scope, or raise with the exact failing path."""
    spec = REGISTRY[family]
    results = []
    with cpu_seed_scope(0):
        for scope, context, tasks in ((s, c, t) for s in spec.scopes for c in CONTEXTS for t in _TASKS):
            try:
                model = anchor(spec.build(context, tasks, scope), tasks).eval()
                channels = 4 if scope == "all" else len(tasks)
                windows = torch.randn(2, context, channels, requires_grad=True)
                tokens = _tokens_and_coverage(family, model, windows)
                if tokens is not None and tokens < 2:
                    raise ValueError("Transformer has fewer than two attention tokens")
                prediction = model(windows)
                if prediction.shape != (2, len(tasks), 5) or not torch.isfinite(prediction).all():
                    raise ValueError("Invalid five-horizon synthetic forecast")
                parameters = tuple(p for p in model.parameters() if p.requires_grad)
                if not all(torch.isfinite(p).all() for p in parameters):
                    raise ValueError("Nonfinite synthetic parameters")
                target = torch.linspace(-1., 1., prediction.numel()).reshape_as(prediction)
                loss = task_mse(prediction, target).mean()
                derivatives = torch.autograd.grad(loss, (windows, *parameters), allow_unused=True)
                if not torch.isfinite(loss) or any(g is None or not torch.isfinite(g).all() for g in derivatives):
                    raise ValueError("Nonfinite or disconnected input/parameter in synthetic backward pass")
                probe = windows[:1].detach()
                routing = _perturbations(model, probe, scope)
                attention = _cross_variate_attention(model, probe) if family == "iTransformer" else None
            except Exception as error:
                raise RuntimeError(f"{spec.label} {scope} L={context} tasks={tasks}: {error}") from error
            results.append({"scope": scope, "context": context, "tasks": list(tasks), "channels": channels,
                            "output_shape": list(prediction.shape), "tokens": tokens,
                            "parameter_count": sum(p.numel() for p in parameters),
                            "resource_to_target_dependencies": routing, "variate_attention_dependencies": attention,
                            "covered_lags": list(range(context))})
    return results
