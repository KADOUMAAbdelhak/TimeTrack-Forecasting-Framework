"""Strict validation selection and logical-to-physical checkpoint planning."""

from dataclasses import dataclass
import math

from .identity import RESOURCES, read_config

_CONFIG = read_config()
MAX_EPOCHS = _CONFIG["lstm"]["max_inner_epochs"]
PATIENCE = _CONFIG["lstm"]["patience"]


def checkpoint_control_applies(identity):
    reduced = _CONFIG["secondary"]
    return (identity.arm == "core" and identity.formulation == "M1"
            and identity.block in reduced["blocks"] and identity.seed in reduced["seeds"])


def diagnostic_slots(joint_epoch):
    """Map the three logical v0.3 slots to the joint trajectory's epochs."""
    if type(joint_epoch) is not int or not 1 <= joint_epoch <= MAX_EPOCHS:
        raise ValueError("Invalid joint checkpoint epoch")
    return dict(zip(_CONFIG["diagnostics"]["slots"], (0, (joint_epoch + 1) // 2, joint_epoch), strict=True))


@dataclass(frozen=True, slots=True)
class CheckpointPlan:
    joint_epoch: int
    task_epochs: tuple[tuple[str, int], ...] = ()

    def __post_init__(self):
        if type(self.joint_epoch) is not int or not 1 <= self.joint_epoch <= MAX_EPOCHS:
            raise ValueError("Invalid joint checkpoint epoch")
        if self.task_epochs and tuple(task for task, _ in self.task_epochs) != RESOURCES:
            raise ValueError("Checkpoint control requires four canonical task requests")
        if any(type(epoch) is not int or not 1 <= epoch <= MAX_EPOCHS for _, epoch in self.task_epochs):
            raise ValueError("Invalid task checkpoint epoch")

    @property
    def physical_epochs(self):
        return tuple(sorted({self.joint_epoch, *(epoch for _, epoch in self.task_epochs)}))

    @property
    def final_epoch(self):
        return self.physical_epochs[-1]

    def payload(self):
        return {"joint_epoch": self.joint_epoch, "task_epochs": dict(self.task_epochs),
                "physical_epochs": list(self.physical_epochs), "final_epoch": self.final_epoch}


class EpochSelector:
    """One observed inner trajectory, with stopping determined by joint MSE."""

    def __init__(self, tasks, *, task_control):
        self.tasks = tuple(tasks)
        if not self.tasks or (task_control and self.tasks != RESOURCES):
            raise ValueError("Invalid selection task axis")
        self.task_control = task_control
        self.observed = 0
        self.joint_epoch = None
        self.best_joint = math.inf
        self.task_best = {}

    @property
    def stopped(self):
        return self.observed >= MAX_EPOCHS or (
            self.joint_epoch is not None and self.observed - self.joint_epoch >= PATIENCE)

    def observe(self, task_mse):
        if self.stopped:
            raise ValueError("Validation trajectory already ended")
        values = tuple(float(value) for value in task_mse)
        if len(values) != len(self.tasks) or any(not math.isfinite(value) or value < 0 for value in values):
            raise ValueError("Invalid per-task validation MSE")
        self.observed += 1
        joint = math.fsum(values) / len(values)
        if joint < self.best_joint:
            self.joint_epoch, self.best_joint = self.observed, joint
        if self.task_control:
            for task, value in zip(self.tasks, values, strict=True):
                if task not in self.task_best or value < self.task_best[task][1]:
                    self.task_best[task] = self.observed, value
        return joint

    def plan(self):
        if self.joint_epoch is None:
            raise ValueError("No validation epoch was observed")
        requests = tuple((task, self.task_best[task][0]) for task in self.tasks) if self.task_control else ()
        return CheckpointPlan(self.joint_epoch, requests)
