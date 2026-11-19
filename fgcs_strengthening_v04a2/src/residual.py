"""Amendment A2: every forecast is the last observed scaled value plus a learned change.

A forward hook adds, to each task's output at every horizon, the task's own channel in the last input row.
Inputs and targets share one training-only scaler per resource, so with a zero learned change the inverse
transform returns the last observed native value (persistence). The hook adds no parameters, so state
dicts, checkpoints and architectures are those of the level-parameterised models.
"""

from .identity import RESOURCES, canonical_tasks, read_config

PARAMETERISATION = read_config()["residual"]["parameterisation"]
if PARAMETERISATION not in ("change", "level"):
    raise RuntimeError("Unknown A2 target parameterisation")


def anchor_indices(tasks, channels):
    """Input channel holding each task's own history: the resource index, or 0 for a one-channel input."""
    tasks = canonical_tasks(tasks)
    if channels == 1 and len(tasks) == 1:
        return (0,)
    if channels == len(RESOURCES):
        return tuple(RESOURCES.index(task) for task in tasks)
    raise ValueError(f"No anchor channel for tasks {tasks} with {channels} input channels")


def last_values(windows, tasks):
    """[batch, task] scaled last-row values of each task's own channel; reads inputs only."""
    if windows.ndim != 3:
        raise ValueError("Expected [batch, context, channels] windows")
    return windows[:, -1, list(anchor_indices(tasks, windows.shape[-1]))]


def anchor(model, tasks, *, parameterisation=None):
    """Attach the change parameterisation to a freshly built model (no-op for 'level'); returns the model."""
    parameterisation = PARAMETERISATION if parameterisation is None else parameterisation
    if parameterisation == "level":
        return model
    if parameterisation != "change":
        raise ValueError(f"Unknown parameterisation {parameterisation!r}")
    if getattr(model, "a2_anchored", False):
        raise ValueError("Model already anchored")
    tasks = canonical_tasks(tasks)

    def hook(module, args, output):
        base = last_values(args[0], tasks)
        if output.ndim != 3 or output.shape[:2] != base.shape:
            raise ValueError("Forecast shape does not match the anchored tasks")
        return output + base.to(output.dtype).unsqueeze(-1)

    model.register_forward_hook(hook)
    model.a2_anchored = True
    return model


__all__ = ("PARAMETERISATION", "anchor", "anchor_indices", "last_values")
