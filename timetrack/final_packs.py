"""Pack definitions, status, and wall-clock helpers for manual final execution."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

PACK_STATUSES = ("pending", "running", "complete", "partial", "failed", "skipped")


def load_packs_config(path: Path | str | None = None) -> dict[str, Any]:
    path = Path(path) if path else ROOT / "configs" / "final_fgcs_packs.yaml"
    return yaml.safe_load(path.read_text())


def config_hash(cfg: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest()[:16]


def pack_hash(pack: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(pack, sort_keys=True, default=str).encode()).hexdigest()[:16]


def pack_by_id(cfg: dict[str, Any], pack_id: str) -> dict[str, Any]:
    for p in cfg.get("packs") or []:
        if p["id"] == pack_id:
            return p
    raise KeyError(f"unknown pack_id: {pack_id}")


def pack_output_dir(cfg: dict[str, Any], pack: dict[str, Any]) -> Path:
    root = ROOT / (cfg.get("artifact_root") or "results/final/packs")
    return root / pack["pack_dir"]


@dataclass
class RunStatus:
    pack_id: str
    status: str = "pending"
    completed_runs: list[str] = field(default_factory=list)
    failed_runs: list[str] = field(default_factory=list)
    skipped_runs: list[str] = field(default_factory=list)
    remaining_runs: int | None = None
    total_runs: int | None = None
    wall_seconds: float = 0.0
    cpu_seconds: float = 0.0
    start_time: str | None = None
    end_time: str | None = None
    last_message: str | None = None
    sessions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def load(cls, path: Path) -> "RunStatus":
        if not path.exists():
            return cls(pack_id=path.parent.name)
        data = json.loads(path.read_text())
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})  # type: ignore[arg-type]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))


def read_pack_status(cfg: dict[str, Any], pack: dict[str, Any]) -> str:
    out = pack_output_dir(cfg, pack)
    if (out / "COMPLETE").exists():
        return "complete"
    if (out / "SKIPPED_INELIGIBLE").exists():
        return "skipped"
    status_path = out / "RUN_STATUS.json"
    if not status_path.exists():
        return "pending"
    st = RunStatus.load(status_path)
    if st.status in PACK_STATUSES:
        return st.status
    return "pending"


def dependencies_satisfied(cfg: dict[str, Any], pack: dict[str, Any]) -> tuple[bool, list[str]]:
    missing = []
    for dep in pack.get("dependencies") or []:
        dep_pack = pack_by_id(cfg, dep)
        if read_pack_status(cfg, dep_pack) != "complete":
            missing.append(dep)
    return (len(missing) == 0, missing)


def list_pack_rows(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for pack in cfg.get("packs") or []:
        out = pack_output_dir(cfg, pack)
        status = read_pack_status(cfg, pack)
        ok, missing = dependencies_satisfied(cfg, pack)
        if status == "pending" and not ok:
            display = "blocked"
        else:
            display = status
        wall = None
        remaining = None
        st_path = out / "RUN_STATUS.json"
        if st_path.exists():
            st = RunStatus.load(st_path)
            wall = st.wall_seconds
            if st.total_runs is not None and st.completed_runs is not None:
                remaining = max(0, int(st.total_runs) - len(st.completed_runs) - len(st.failed_runs))
        rows.append(
            {
                "pack_id": pack["id"],
                "required": bool(pack.get("required")),
                "dependencies": list(pack.get("dependencies") or []),
                "dependencies_missing": missing,
                "estimated_minutes": pack.get("estimated_runtime_minutes"),
                "actual_wall_seconds": wall,
                "status": display,
                "remaining_runs": remaining,
                "output_path": str(out),
                "estimated_base_fits": pack.get("estimated_base_fits"),
                "estimated_recon_evals": pack.get("estimated_recon_evals"),
            }
        )
    return rows


class WallClockGuard:
    """Hard session wall-clock control for a single pack launch."""

    def __init__(self, hard_minutes: float, stop_launch_minutes: float):
        self.hard_sec = float(hard_minutes) * 60.0
        self.stop_launch_sec = float(stop_launch_minutes) * 60.0
        self.t0 = time.perf_counter()
        self.cpu0 = time.process_time()

    def elapsed(self) -> float:
        return time.perf_counter() - self.t0

    def cpu_elapsed(self) -> float:
        return time.process_time() - self.cpu0

    def may_launch_new_run(self) -> bool:
        return self.elapsed() < self.stop_launch_sec

    def format_elapsed(self) -> str:
        s = int(self.elapsed())
        return f"{s // 60}m {s % 60:02d}s"
