"""Pilot vs final evaluation stage enforcement.

Existing smoke/medium_lite runs inspected terminal chronological test metrics
and therefore cannot support final statistical claims (see EVALUATION_PROTOCOL_V2).
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = PROJECT_ROOT / "results"
PILOT_ROOT = RESULTS_ROOT / "pilot"
FINAL_ROOT = RESULTS_ROOT / "final"


class ExperimentStage(str, Enum):
    PILOT = "pilot"
    DEVELOPMENT = "development"
    FINAL = "final"


STAGE_METADATA = {
    ExperimentStage.PILOT: {
        "experiment_stage": "pilot",
        "eligible_for_final_claims": False,
        "evaluation_role": "development_benchmark",
    },
    ExperimentStage.DEVELOPMENT: {
        "experiment_stage": "development",
        "eligible_for_final_claims": False,
        "evaluation_role": "inner_model_selection",
    },
    ExperimentStage.FINAL: {
        "experiment_stage": "final",
        "eligible_for_final_claims": True,
        "evaluation_role": "outer_evaluation",
    },
}


def parse_stage(value: str | ExperimentStage | None) -> ExperimentStage:
    if value is None:
        return ExperimentStage.PILOT
    if isinstance(value, ExperimentStage):
        return value
    return ExperimentStage(str(value).lower())


def stage_metadata(stage: str | ExperimentStage) -> dict[str, Any]:
    st = parse_stage(stage)
    return dict(STAGE_METADATA[st])


def results_root_for_stage(stage: str | ExperimentStage) -> Path:
    st = parse_stage(stage)
    if st == ExperimentStage.FINAL:
        return FINAL_ROOT
    if st == ExperimentStage.DEVELOPMENT:
        return RESULTS_ROOT / "development"
    return PILOT_ROOT


def annotate_run_result(result: dict[str, Any], stage: str | ExperimentStage) -> dict[str, Any]:
    """Stamp stage metadata onto a run dict (in place and returned)."""
    meta = stage_metadata(stage)
    result.update(meta)
    result.setdefault("config_meta", {})
    result["config_meta"].update(meta)
    return result


def assert_eligible_for_final_leaderboard(rows: list[dict[str, Any]] | Any) -> None:
    """Raise if any row is not eligible for final claims."""
    import pandas as pd

    if isinstance(rows, pd.DataFrame):
        records = rows.to_dict(orient="records")
    else:
        records = list(rows)
    bad = []
    for r in records:
        stage = r.get("experiment_stage")
        eligible = r.get("eligible_for_final_claims")
        if stage != ExperimentStage.FINAL.value or eligible is not True:
            bad.append(
                {
                    "run_id": r.get("run_id"),
                    "experiment_stage": stage,
                    "eligible_for_final_claims": eligible,
                }
            )
    if bad:
        raise AssertionError(
            f"Refusing to build final leaderboard: {len(bad)} ineligible run(s). "
            f"Examples: {bad[:3]}"
        )


def filter_final_eligible(df: Any) -> Any:
    """Return only rows eligible for final claims; empty if none."""
    import pandas as pd

    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)
    if df.empty:
        return df
    if "eligible_for_final_claims" not in df.columns or "experiment_stage" not in df.columns:
        # Missing metadata => treat as pilot (ineligible)
        return df.iloc[0:0].copy()
    mask = (df["experiment_stage"] == ExperimentStage.FINAL.value) & (
        df["eligible_for_final_claims"] == True  # noqa: E712
    )
    return df.loc[mask].copy()


def is_pilot_path(path: Path | str) -> bool:
    p = Path(path).resolve()
    try:
        p.relative_to(PILOT_ROOT.resolve())
        return True
    except ValueError:
        return False
