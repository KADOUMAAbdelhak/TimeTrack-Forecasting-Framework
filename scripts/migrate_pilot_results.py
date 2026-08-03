#!/usr/bin/env python3
"""Relocate existing exploratory artifacts into results/pilot/ and stamp metadata.

Does not delete content: moves directories and leaves README pointers at legacy paths.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PILOT = RESULTS / "pilot"

STAGE_META = {
    "experiment_stage": "pilot",
    "eligible_for_final_claims": False,
    "evaluation_role": "development_benchmark",
}


def _move_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        # merge directories for raw_runs etc.
        if src.is_dir() and dst.is_dir():
            for child in src.iterdir():
                target = dst / child.name
                if not target.exists():
                    shutil.move(str(child), str(target))
            # remove emptied src if possible
            try:
                src.rmdir()
            except OSError:
                pass
            return True
        raise FileExistsError(f"destination exists: {dst}")
    shutil.move(str(src), str(dst))
    return True


def _write_legacy_pointer(legacy: Path, pilot_rel: str) -> None:
    legacy.mkdir(parents=True, exist_ok=True)
    readme = legacy / "README.md"
    readme.write_text(
        f"""# Relocated to pilot

These exploratory artifacts were moved to `{pilot_rel}` on
{datetime.now(timezone.utc).isoformat()}.

They are classified as:

- experiment_stage: pilot
- eligible_for_final_claims: false
- evaluation_role: development_benchmark

Do not use them for final FGCS claims. See `docs/EVALUATION_PROTOCOL_V2.md`.
"""
    )


def stamp_raw_runs(raw_dir: Path) -> int:
    n = 0
    for path in sorted(raw_dir.glob("*.json")):
        data = json.loads(path.read_text())
        data.update(STAGE_META)
        data.setdefault("config_meta", {})
        data["config_meta"].update(STAGE_META)
        path.write_text(json.dumps(data, indent=2, default=str))
        n += 1
    return n


def rebuild_pilot_all_runs(raw_dir: Path, out_csv: Path) -> int:
    rows = []
    for path in sorted(raw_dir.glob("*.json")):
        r = json.loads(path.read_text())
        mt = r["metrics_test"]
        rows.append(
            {
                "run_id": r["run_id"],
                **STAGE_META,
                "scope": r.get("scope"),
                "target": r["target"],
                "model": r["model"],
                "horizon": r["horizon"],
                "context": r["context"],
                "seed": r["seed"],
                "mae": mt.get("mae"),
                "rmse": mt.get("rmse"),
                "mse": mt.get("mse"),
                "smape": mt.get("smape"),
                "mape": mt.get("mape"),
                "mape_fraction_excluded": mt.get("mape_fraction_excluded"),
                "mase": mt.get("mase"),
                "r2": mt.get("r2"),
                "nrmse": mt.get("nrmse"),
                "medae": mt.get("medae"),
                "maxae": mt.get("maxae"),
                "peak_recall": mt.get("peak_recall"),
                "peak_precision": mt.get("peak_precision"),
                "training_time_sec": (r.get("model_metadata") or {}).get("training_time_sec"),
                "inference_time_sec": (r.get("model_metadata") or {}).get("inference_time_sec"),
                "n_parameters": (r.get("model_metadata") or {}).get("n_parameters"),
                "runtime_sec": r.get("runtime_sec"),
                "n_test_windows": r.get("n_test_windows"),
            }
        )
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    return len(df)


def main() -> None:
    PILOT.mkdir(parents=True, exist_ok=True)
    (RESULTS / "final" / "metrics").mkdir(parents=True, exist_ok=True)
    (RESULTS / "final" / "README.md").write_text(
        """# Final results (empty until freeze)

No final-eligible runs exist yet.

Pilot runs live under `results/pilot/` and are **not** eligible for final claims.
See `docs/EVALUATION_PROTOCOL_V2.md`.
"""
    )

    moves = [
        (RESULTS / "metrics" / "raw_runs", PILOT / "metrics" / "raw_runs"),
        (RESULTS / "predictions", PILOT / "predictions"),
        (RESULTS / "models", PILOT / "models"),
        (RESULTS / "paper", PILOT / "notes"),  # internal notes, not manuscript
        (RESULTS / "tables", PILOT / "tables"),
        (RESULTS / "figures", PILOT / "figures"),
        (RESULTS / "logs", PILOT / "logs"),
        (RESULTS / "tuning", PILOT / "tuning"),
    ]
    for src, dst in moves:
        moved = _move_if_exists(src, dst)
        print(f"move {src.relative_to(RESULTS)} -> {dst.relative_to(RESULTS)} : {moved}")

    # Move aggregate CSVs if present at legacy metrics/
    legacy_metrics = RESULTS / "metrics"
    pilot_metrics = PILOT / "metrics"
    pilot_metrics.mkdir(parents=True, exist_ok=True)
    for name in (
        "all_runs.csv",
        "leaderboard.csv",
        "per_target_leaderboard.csv",
        "per_horizon_leaderboard.csv",
        "statistical_summary.csv",
    ):
        src = legacy_metrics / name
        if src.exists():
            dst = pilot_metrics / name
            if not dst.exists():
                shutil.move(str(src), str(dst))
                print(f"moved {name}")

    if (RESULTS / "MANIFEST.json").exists():
        shutil.move(str(RESULTS / "MANIFEST.json"), str(PILOT / "MANIFEST.json"))

    # Stamp metadata on all pilot raw runs and rebuild all_runs
    raw = PILOT / "metrics" / "raw_runs"
    n_stamp = stamp_raw_runs(raw) if raw.exists() else 0
    n_rows = rebuild_pilot_all_runs(raw, pilot_metrics / "all_runs.csv") if raw.exists() else 0
    print(f"stamped {n_stamp} raw runs; all_runs rows={n_rows}")

    # Rebuild pilot leaderboards via stage-aware API
    import sys

    sys.path.insert(0, str(ROOT))
    from experiments.runner import build_leaderboards
    from timetrack.evaluation_stage import ExperimentStage

    if n_rows:
        build_leaderboards(stage=ExperimentStage.PILOT)

    # Legacy pointers
    _write_legacy_pointer(RESULTS / "metrics", "results/pilot/metrics/")
    _write_legacy_pointer(RESULTS / "predictions", "results/pilot/predictions/")
    _write_legacy_pointer(RESULTS / "models", "results/pilot/models/")
    _write_legacy_pointer(RESULTS / "paper", "results/pilot/notes/ (internal experimental notes, NOT a manuscript)")

    (PILOT / "README.md").write_text(
        f"""# Pilot / exploratory results

Migrated {datetime.now(timezone.utc).isoformat()}

- experiment_stage: pilot
- eligible_for_final_claims: **false**
- evaluation_role: development_benchmark

These runs inspected the terminal chronological holdout during development.
They remain valuable for debugging and candidate triage, but must not be mixed
into `results/final/` leaderboards.
"""
    )
    print("migration complete")


if __name__ == "__main__":
    main()
