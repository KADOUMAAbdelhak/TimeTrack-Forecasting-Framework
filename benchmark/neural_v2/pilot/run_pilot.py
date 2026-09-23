#!/usr/bin/env python3
"""Run the authorized five-epoch, non-scientific neural-v2 CPU timing pilot."""

from __future__ import annotations

import json
import os
import platform
import threading
import time
from pathlib import Path

import psutil
import torch

from benchmark.neural_v2.src.data import build_windows, load_canonical_panel
from benchmark.neural_v2.src.splits import build_supported_folds
from benchmark.neural_v2.src.training import fit_inner, parameter_count, select_device
from benchmark.neural_v2.src.validation import atomic_json_write


ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "benchmark" / "neural_v2" / "pilot" / "timing_results.json"
MODELS = ("DLinear", "LSTM", "TCN-v2", "PatchTST")
FEATURES = ("F0_LOCAL", "F1_THROUGHPUT")
MACHINE = "machine01"
FOLD = 1
SEED = 0
CONTEXT_LENGTH = 64
EPOCHS = 5


class ProcessMonitor:
    def __init__(self) -> None:
        self.process = psutil.Process()
        self.stop_event = threading.Event()
        self.peak_rss_bytes = self.process.memory_info().rss
        self.cpu_samples: list[float] = []
        self.thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        self.process.cpu_percent(interval=None)
        while not self.stop_event.wait(0.05):
            self.peak_rss_bytes = max(
                self.peak_rss_bytes, self.process.memory_info().rss
            )
            self.cpu_samples.append(self.process.cpu_percent(interval=None))

    def __enter__(self) -> "ProcessMonitor":
        self.thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.stop_event.set()
        self.thread.join()
        self.peak_rss_bytes = max(
            self.peak_rss_bytes, self.process.memory_info().rss
        )

    @property
    def mean_process_cpu_percent(self) -> float | None:
        return (
            sum(self.cpu_samples) / len(self.cpu_samples)
            if self.cpu_samples
            else None
        )


def main() -> None:
    if select_device().type != "cpu":
        raise RuntimeError("This authorized pilot is specified for the current CPU")
    panel = load_canonical_panel()
    fold = build_supported_folds(panel, MACHINE, CONTEXT_LENGTH)[FOLD - 1]
    batches = {}
    for feature in FEATURES:
        batches[feature] = {
            "train": build_windows(
                panel,
                MACHINE,
                feature,
                CONTEXT_LENGTH,
                fold.inner_train_indices,
            ),
            "validation": build_windows(
                panel,
                MACHINE,
                feature,
                CONTEXT_LENGTH,
                fold.inner_validation_indices,
            ),
        }
    if not all(
        batches["F0_LOCAL"][stage].sample_set_hash
        == batches["F1_THROUGHPUT"][stage].sample_set_hash
        for stage in ("train", "validation")
    ):
        raise RuntimeError("Pilot F0/F1 common support differs")
    payload = {
        "pilot_status": "NON_SCIENTIFIC_TIMING_ONLY",
        "accuracy_interpretation_prohibited": True,
        "machine": MACHINE,
        "outer_fold": FOLD,
        "seed": SEED,
        "context_length": CONTEXT_LENGTH,
        "epochs": EPOCHS,
        "full_legal_support": True,
        "train_samples": len(fold.inner_train_indices),
        "validation_samples": len(fold.inner_validation_indices),
        "train_sample_set_hash": fold.inner_train_hash,
        "validation_sample_set_hash": fold.inner_validation_hash,
        "device": "cpu",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "logical_cpu_count": os.cpu_count(),
            "torch": torch.__version__,
            "torch_threads": torch.get_num_threads(),
            "mps_available": torch.backends.mps.is_available(),
            "cuda_available": torch.cuda.is_available(),
        },
        "runs": [],
    }
    for model_name in MODELS:
        for feature in FEATURES:
            train = batches[feature]["train"]
            validation = batches[feature]["validation"]
            started = time.perf_counter()
            with ProcessMonitor() as monitor:
                result = fit_inner(
                    model_name,
                    CONTEXT_LENGTH,
                    train.X.shape[-1],
                    SEED,
                    train.X,
                    train.y,
                    validation.X,
                    validation.y,
                    fixed_epochs=EPOCHS,
                    device="cpu",
                )
            wall_seconds = time.perf_counter() - started
            run = {
                "model": model_name,
                "feature_set": feature,
                "input_channels": int(train.X.shape[-1]),
                "parameter_count": parameter_count(result.model),
                "epochs_completed": result.epochs_trained,
                "train_seconds": result.train_seconds,
                "validation_seconds": result.validation_seconds,
                "wall_seconds": wall_seconds,
                "seconds_per_epoch": (
                    result.train_seconds + result.validation_seconds
                )
                / EPOCHS,
                "training_samples_per_second": (
                    len(train.origin_indices) * EPOCHS / result.train_seconds
                ),
                "peak_rss_bytes": monitor.peak_rss_bytes,
                "mean_process_cpu_percent": monitor.mean_process_cpu_percent,
                "common_train_sample_set_hash": train.sample_set_hash,
                "common_validation_sample_set_hash": validation.sample_set_hash,
            }
            payload["runs"].append(run)
            atomic_json_write(OUTPUT, payload)
            print(
                f"completed {model_name}/{feature}: "
                f"{run['seconds_per_epoch']:.3f}s/epoch",
                flush=True,
            )
    payload["completed_runs"] = len(payload["runs"])
    payload["complete"] = len(payload["runs"]) == len(MODELS) * len(FEATURES)
    atomic_json_write(OUTPUT, payload)


if __name__ == "__main__":
    main()
