"""Leakage-safe efficiency / resource instrumentation for final runs."""

from __future__ import annotations

import platform
import resource
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

import numpy as np


def _peak_rss_mb() -> float:
    """Peak resident set size in MiB (Unix ru_maxrss is bytes on macOS, KiB on Linux)."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss = float(usage.ru_maxrss)
    if sys.platform == "darwin":
        return rss / (1024.0 * 1024.0)
    return rss / 1024.0


def hardware_metadata() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": sys.version.split()[0],
        "cpu_count_logical": None,
    }


def software_versions() -> dict[str, str]:
    vers = {"python": sys.version.split()[0]}
    for mod in ("numpy", "pandas", "sklearn", "lightgbm", "xgboost", "torch", "optuna"):
        try:
            m = __import__(mod if mod != "sklearn" else "sklearn")
            vers[mod] = getattr(m, "__version__", "unknown")
        except Exception:
            vers[mod] = "not_installed"
    return vers


@dataclass
class EfficiencyRecord:
    wall_train_sec: float = float("nan")
    cpu_train_sec: float = float("nan")
    peak_rss_mb: float = float("nan")
    n_parameters: float | None = None
    serialized_model_bytes: float | None = None
    warm_infer_latency_ms_median: float = float("nan")
    warm_infer_latency_ms_p25: float = float("nan")
    warm_infer_latency_ms_p75: float = float("nan")
    cold_infer_latency_ms: float = float("nan")
    forecasts_per_sec: float = float("nan")
    n_train_samples: int = 0
    n_prediction_origins: int = 0
    end_to_end_latency_sec: float = float("nan")
    hardware: dict[str, Any] = field(default_factory=hardware_metadata)
    software: dict[str, str] = field(default_factory=software_versions)
    # reconciliation-specific (optional)
    recon_fit_sec: float | None = None
    recon_infer_sec: float | None = None
    recon_memory_overhead_mb: float | None = None
    cov_estimate_sec: float | None = None
    recon_artifact_bytes: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def assert_finite_required(self) -> None:
        required = (
            "wall_train_sec",
            "cpu_train_sec",
            "peak_rss_mb",
            "warm_infer_latency_ms_median",
            "cold_infer_latency_ms",
            "forecasts_per_sec",
        )
        for k in required:
            v = getattr(self, k)
            if v is None or not np.isfinite(float(v)):
                raise AssertionError(f"efficiency field {k} missing or non-finite: {v}")


def _latency_stats(times_sec: list[float]) -> tuple[float, float, float]:
    arr = np.asarray(times_sec, dtype=float) * 1000.0  # ms
    return (
        float(np.median(arr)),
        float(np.quantile(arr, 0.25)),
        float(np.quantile(arr, 0.75)),
    )


def measure_inference_latencies(
    predict_fn: Callable[[Any], Any],
    batch: Any,
    *,
    n_warm: int = 3,
    n_repeat: int = 11,
) -> dict[str, float]:
    """Warm up, then repeated timed inference; exclude data loading."""
    t0 = time.perf_counter()
    _ = predict_fn(batch)
    cold_ms = (time.perf_counter() - t0) * 1000.0
    for _ in range(max(0, n_warm - 1)):
        _ = predict_fn(batch)
    reps: list[float] = []
    for _ in range(n_repeat):
        t1 = time.perf_counter()
        out = predict_fn(batch)
        reps.append(time.perf_counter() - t1)
    med, p25, p75 = _latency_stats(reps)
    n_pred = int(np.asarray(out).reshape(-1).shape[0]) if out is not None else 0
    fps = float(n_pred / max(np.median(reps), 1e-12)) if n_pred else float("nan")
    return {
        "cold_infer_latency_ms": float(cold_ms),
        "warm_infer_latency_ms_median": med,
        "warm_infer_latency_ms_p25": p25,
        "warm_infer_latency_ms_p75": p75,
        "forecasts_per_sec": fps,
    }


def timed_train(fit_fn: Callable[[], Any]) -> tuple[Any, float, float, float]:
    """Return (result, wall_sec, cpu_sec, peak_rss_mb_after)."""
    cpu0 = time.process_time()
    wall0 = time.perf_counter()
    result = fit_fn()
    wall = time.perf_counter() - wall0
    cpu = time.process_time() - cpu0
    return result, wall, cpu, _peak_rss_mb()
