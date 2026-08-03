"""CLI entrypoints for TimeTrack forecasting experiments."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def cmd_audit(_args: argparse.Namespace) -> None:
    from timetrack.data import build_analysis_panel, dataset_fingerprint, detect_sampling_seconds

    fp = dataset_fingerprint()
    panel = build_analysis_panel()
    med = detect_sampling_seconds(panel["timestamp"])
    print(json.dumps({
        "fingerprint": fp["fingerprint"],
        "n_rows": len(panel),
        "n_cols": panel.shape[1],
        "sampling_median_sec": med,
        "segments": panel["segment"].value_counts().to_dict(),
    }, indent=2, default=str))


def cmd_preprocess(args: argparse.Namespace) -> None:
    from timetrack.data import build_analysis_panel, dataset_fingerprint

    panel = build_analysis_panel()
    fp = dataset_fingerprint()
    out = ROOT / "data" / "processed" / "analysis_panel.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(out, index=False)
    meta = {"fingerprint": fp, "rows": len(panel), "cols": list(panel.columns)}
    (ROOT / "data" / "processed" / "analysis_panel.meta.json").write_text(json.dumps(meta, indent=2, default=str))
    print(f"Wrote {out}")


def cmd_run(args: argparse.Namespace) -> None:
    from experiments.runner import run_from_config

    run_from_config(args.config)


def cmd_leaderboard(args: argparse.Namespace) -> None:
    from experiments.runner import build_final_leaderboards, build_leaderboards
    from timetrack.evaluation_stage import ExperimentStage

    stage = args.stage
    if stage == "final":
        paths = build_final_leaderboards()
    else:
        paths = build_leaderboards(stage=ExperimentStage(stage))
    for k, v in paths.items():
        print(k, "->", v)


def cmd_list_models(_args: argparse.Namespace) -> None:
    from models import forecasting as F

    print("\n".join(F.list_available_models()))


def cmd_test_smoke(_args: argparse.Namespace) -> None:
    import pytest

    raise SystemExit(pytest.main(["-q", str(ROOT / "tests")]))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="TimeTrack forecasting framework")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("audit", help="Quick dataset audit summary")
    s.set_defaults(func=cmd_audit)

    s = sub.add_parser("preprocess", help="Build processed analysis panel")
    s.set_defaults(func=cmd_preprocess)

    s = sub.add_parser("run", help="Run experiments from a YAML config")
    s.add_argument("--config", required=True)
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("leaderboard", help="Rebuild leaderboards from stage all_runs.csv")
    s.add_argument(
        "--stage",
        choices=["pilot", "development", "final"],
        default="pilot",
        help="Aggregation stage (final refuses ineligible/pilot rows)",
    )
    s.set_defaults(func=cmd_leaderboard)

    s = sub.add_parser("list-models", help="List registered models")
    s.set_defaults(func=cmd_list_models)

    s = sub.add_parser("test", help="Run unit tests")
    s.set_defaults(func=cmd_test_smoke)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
