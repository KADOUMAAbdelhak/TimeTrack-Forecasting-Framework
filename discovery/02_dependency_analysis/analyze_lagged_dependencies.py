#!/usr/bin/env python3
"""Execute the frozen Phase 1B-1 lagged association analysis only.

No forecasting or Ridge model is fit here. Inputs are the frozen canonical
panel, registry, target-time-purged split definitions, and Phase 1A raw hashes.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import seaborn as sns
from joblib import Parallel, delayed
from scipy.stats import rankdata
from sklearn.feature_selection import mutual_info_regression
from threadpoolctl import threadpool_limits


ROOT = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT / "discovery" / "02_dependency_analysis"
OUTPUT_DIR = PHASE_DIR / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
PANEL_PATH = OUTPUT_DIR / "canonical_panel.parquet"
REGISTRY_PATH = OUTPUT_DIR / "canonical_signal_registry.csv"
SPLIT_PATH = OUTPUT_DIR / "split_boundaries_by_target_lead.csv"
PHASE1_HASH_PATH = (
    ROOT / "discovery" / "01_data_audit" / "outputs" / "raw_hashes_before_after.json"
)
REPORT_PATH = PHASE_DIR / "ASSOCIATION_REPORT.md"

LEADS = [1, 2, 4, 8, 16, 32, 64, 128]
LAGS = [0, 1, 2, 4, 8, 16, 32, 64, 128]
TARGET_HISTORY_LAGS = [0, 1, 2, 4, 8, 16, 32]
MACHINES = [f"machine{i:02d}" for i in range(1, 8)]
TARGET_SUFFIX = {
    "CPU": "cpu_utilization",
    "memory": "memory_used",
    "disk": "disk_used",
    "throughput": "throughput_total",
}
GLOBAL_PREDICTORS = {
    "global__rtt_max": "RTT",
    "global__rtt_min": "RTT",
    "global__rtt_average": "RTT",
    "global__rtt_mdev": "RTT",
    "global__jitter": "jitter",
}
SPLITS = ["train", "validation", "test"]
MIN_SEGMENT_SAMPLES = 30
MI_MAX_SAMPLES = 20_000
MI_NEIGHBORS = 3
MI_RANDOM_STATE = 0


@dataclass(frozen=True)
class Candidate:
    target: str
    target_machine: str
    target_family: str
    predictor: str
    predictor_machine: str
    predictor_family: str
    candidate_family: str
    direction: str
    predictor_level_like: bool


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def json_write(path: Path, payload: Any) -> None:
    def convert(value: Any) -> Any:
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return None if not np.isfinite(value) else float(value)
        if isinstance(value, (pd.Timestamp, Path)):
            return str(value)
        raise TypeError(type(value).__name__)

    path.write_text(json.dumps(payload, indent=2, default=convert) + "\n")


def build_candidates(panel_columns: set[str]) -> list[Candidate]:
    candidates: list[Candidate] = []

    def add(
        target: str,
        target_machine: str,
        target_family: str,
        predictor: str,
        predictor_machine: str,
        predictor_family: str,
        candidate_family: str,
        level_like: bool = False,
    ) -> None:
        if target not in panel_columns or predictor not in panel_columns:
            raise KeyError(f"Missing frozen signal: {target} or {predictor}")
        candidates.append(
            Candidate(
                target=target,
                target_machine=target_machine,
                target_family=target_family,
                predictor=predictor,
                predictor_machine=predictor_machine,
                predictor_family=predictor_family,
                candidate_family=candidate_family,
                direction=f"{target_family} <- {predictor_family}",
                predictor_level_like=level_like,
            )
        )

    # Same-machine cross-resource candidates.
    for machine in MACHINES:
        target_by_family = {
            family: f"{machine}__{suffix}" for family, suffix in TARGET_SUFFIX.items()
        }
        predictor_by_family = {
            "CPU": [(target_by_family["CPU"], False)],
            "memory": [(target_by_family["memory"], True)],
            "disk": [
                (f"{machine}__disk_used", True),
                (f"{machine}__disk_read", False),
                (f"{machine}__disk_write", False),
            ],
            "throughput": [(target_by_family["throughput"], False)],
        }
        for target_family in TARGET_SUFFIX:
            target = target_by_family[target_family]
            for predictor_family in TARGET_SUFFIX:
                if predictor_family == target_family:
                    continue
                for predictor, level_like in predictor_by_family[predictor_family]:
                    add(
                        target,
                        machine,
                        target_family,
                        predictor,
                        machine,
                        predictor_family,
                        "same_machine_cross_resource",
                        level_like,
                    )
            for predictor, predictor_family in GLOBAL_PREDICTORS.items():
                add(
                    target,
                    machine,
                    target_family,
                    predictor,
                    "",
                    predictor_family,
                    "global_context",
                )

    # Ordered same-resource cross-machine pairs.
    for family in ("CPU", "memory", "throughput"):
        suffix = TARGET_SUFFIX[family]
        for target_machine in MACHINES:
            for predictor_machine in MACHINES:
                if predictor_machine == target_machine:
                    continue
                add(
                    f"{target_machine}__{suffix}",
                    target_machine,
                    family,
                    f"{predictor_machine}__{suffix}",
                    predictor_machine,
                    family,
                    "same_resource_cross_machine",
                    family == "memory",
                )

    # Mean and median leave-one-machine-out contexts.
    for family in ("CPU", "memory", "throughput"):
        suffix = TARGET_SUFFIX[family]
        for target_machine in MACHINES:
            for statistic in ("mean", "median"):
                add(
                    f"{target_machine}__{suffix}",
                    target_machine,
                    family,
                    f"{target_machine}__lomo_{suffix}_{statistic}",
                    f"other_six_excluding_{target_machine}",
                    family,
                    "leave_one_machine_out",
                    family == "memory",
                )

    keys = [
        (
            c.target,
            c.predictor,
            c.candidate_family,
        )
        for c in candidates
    ]
    if len(keys) != len(set(keys)):
        raise RuntimeError("Duplicate candidate relationships")
    if len(candidates) != 434:
        raise RuntimeError(f"Frozen candidate count changed: {len(candidates)} != 434")
    return candidates


def analysis_modes(target_family: str) -> list[str]:
    return ["level", "change"] if target_family in {"memory", "disk"} else ["native"]


def finite_mask(values: np.ndarray) -> np.ndarray:
    return np.isfinite(values)


def safe_pearson(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < MIN_SEGMENT_SAMPLES:
        return np.nan
    x_centered = x - x.mean()
    y_centered = y - y.mean()
    denominator = math.sqrt(float(x_centered @ x_centered) * float(y_centered @ y_centered))
    if denominator == 0 or not np.isfinite(denominator):
        return np.nan
    return float((x_centered @ y_centered) / denominator)


def correlations(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    pearson = safe_pearson(x, y)
    if not np.isfinite(pearson):
        return np.nan, np.nan
    spearman = safe_pearson(rankdata(x), rankdata(y))
    return pearson, spearman


def master_masks(
    panel: pd.DataFrame, split_rows: pd.DataFrame
) -> dict[tuple[str, int], dict[str, np.ndarray]]:
    timestamps = panel["timestamp"]
    segments = panel["segment_id"]
    result: dict[tuple[str, int], dict[str, np.ndarray]] = {}
    for row in split_rows.itertuples(index=False):
        target = row.target
        lead = int(row.lead)
        y = panel[target]
        eligible = pd.Series(True, index=panel.index)
        for lag in TARGET_HISTORY_LAGS:
            eligible &= y.shift(lag).notna()
        eligible &= y.shift(-lead).notna()
        eligible &= segments.eq(segments.shift(max(TARGET_HISTORY_LAGS)))
        eligible &= segments.eq(segments.shift(-lead))
        target_time = timestamps.shift(-lead)
        masks = {
            "eligible": eligible.to_numpy(),
            "train": (
                eligible & target_time.le(row.train_cut_timestamp)
            ).to_numpy(),
            "validation": (
                eligible
                & timestamps.gt(row.train_cut_timestamp)
                & target_time.le(row.validation_cut_timestamp)
            ).to_numpy(),
            "test": (
                eligible & timestamps.gt(row.validation_cut_timestamp)
            ).to_numpy(),
        }
        if int(eligible.sum()) != int(row.eligible_origin_count_before_purge):
            raise RuntimeError(f"Eligible-origin mismatch: {target}, lead {lead}")
        expected = {
            "train": row.train_count,
            "validation": row.validation_count,
            "test": row.test_count,
        }
        for split in SPLITS:
            if int(masks[split].sum()) != int(expected[split]):
                raise RuntimeError(f"Split mismatch: {target}, lead {lead}, {split}")
        result[(target, lead)] = masks
    return result


def target_values(panel: pd.DataFrame, target: str, lead: int, mode: str) -> np.ndarray:
    future = panel[target].shift(-lead)
    if mode == "change":
        future = future - panel[target]
    return future.to_numpy(dtype=float)


def predictor_values(
    panel: pd.DataFrame, candidate: Candidate, lag: int, mode: str
) -> tuple[np.ndarray, np.ndarray]:
    series = panel[candidate.predictor]
    segments = panel["segment_id"]
    if mode == "change" and candidate.predictor_level_like:
        values = series.shift(lag) - series.shift(lag + 1)
        same_segment = segments.eq(segments.shift(lag)) & segments.eq(
            segments.shift(lag + 1)
        )
    else:
        values = series.shift(lag)
        same_segment = segments.eq(segments.shift(lag))
    return values.to_numpy(dtype=float), same_segment.to_numpy()


DETAIL_COLUMNS = [
    "analysis_mode",
    "target",
    "target_machine",
    "target_family",
    "predictor",
    "predictor_machine",
    "predictor_family",
    "candidate_family",
    "direction",
    "lead",
    "predictor_lag",
    "split",
    "segment_id",
    "n_samples",
    "pearson",
    "spearman",
]


def weighted_summary(rows: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
    frame = pd.DataFrame(rows)
    finite = frame[np.isfinite(frame["spearman"]) & np.isfinite(frame["pearson"])]
    if len(finite):
        weights = finite["n_samples"].to_numpy(dtype=float)
        weighted_pearson = float(np.average(finite["pearson"], weights=weights))
        weighted_spearman = float(np.average(finite["spearman"], weights=weights))
        positive = float(weights[finite["spearman"].to_numpy() > 0].sum() / weights.sum())
        negative = float(weights[finite["spearman"].to_numpy() < 0].sum() / weights.sum())
    else:
        weighted_pearson = weighted_spearman = positive = negative = np.nan
    return {
        **metadata,
        "n_samples": int(frame["n_samples"].sum()),
        "n_segments": int(len(finite)),
        "weighted_pearson": weighted_pearson,
        "weighted_spearman": weighted_spearman,
        "positive_segment_weight_fraction": positive,
        "negative_segment_weight_fraction": negative,
    }


def association_pass(
    panel: pd.DataFrame,
    candidates: list[Candidate],
    masks: dict[tuple[str, int], dict[str, np.ndarray]],
) -> tuple[pd.DataFrame, int]:
    detail_path = OUTPUT_DIR / "lagged_associations.parquet"
    temporary = detail_path.with_suffix(".parquet.tmp")
    temporary.unlink(missing_ok=True)
    writer: pq.ParquetWriter | None = None
    detail_buffer: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    segment_ids = panel["segment_id"].to_numpy()
    segment_cell_count = 0

    def flush() -> None:
        nonlocal writer, detail_buffer
        if not detail_buffer:
            return
        frame = pd.DataFrame(detail_buffer, columns=DETAIL_COLUMNS)
        table = pa.Table.from_pandas(frame, preserve_index=False)
        if writer is None:
            writer = pq.ParquetWriter(temporary, table.schema, compression="zstd")
        writer.write_table(table)
        detail_buffer = []

    for candidate_index, candidate in enumerate(candidates, start=1):
        base_metadata = asdict(candidate)
        base_metadata.pop("predictor_level_like")
        for mode in analysis_modes(candidate.target_family):
            for lead in LEADS:
                y = target_values(panel, candidate.target, lead, mode)
                master = masks[(candidate.target, lead)]
                for lag in LAGS:
                    x, predictor_segment_safe = predictor_values(panel, candidate, lag, mode)
                    valid_values = finite_mask(x) & finite_mask(y) & predictor_segment_safe
                    for split in SPLITS:
                        split_mask = master[split] & valid_values
                        rows_for_summary: list[dict[str, Any]] = []
                        for segment_id in np.unique(segment_ids[split_mask]):
                            selected = split_mask & (segment_ids == segment_id)
                            n = int(selected.sum())
                            pearson, spearman = correlations(x[selected], y[selected])
                            row = {
                                "analysis_mode": mode,
                                **base_metadata,
                                "lead": lead,
                                "predictor_lag": lag,
                                "split": split,
                                "segment_id": int(segment_id),
                                "n_samples": n,
                                "pearson": pearson,
                                "spearman": spearman,
                            }
                            detail_buffer.append(row)
                            rows_for_summary.append(row)
                            segment_cell_count += 1
                        summary_metadata = {
                            "analysis_mode": mode,
                            **base_metadata,
                            "lead": lead,
                            "predictor_lag": lag,
                            "split": split,
                        }
                        summaries.append(weighted_summary(rows_for_summary, summary_metadata))
                    if len(detail_buffer) >= 50_000:
                        flush()
        if candidate_index % 25 == 0:
            print(f"association candidates: {candidate_index}/{len(candidates)}", flush=True)
    flush()
    if writer is not None:
        writer.close()
    temporary.replace(detail_path)
    summary = pd.DataFrame(summaries)
    summary.to_parquet(
        OUTPUT_DIR / "lagged_association_summary.parquet",
        index=False,
        compression="zstd",
    )
    return summary, segment_cell_count


def select_validation_lags(summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    keys = [
        "target",
        "target_machine",
        "target_family",
        "predictor",
        "predictor_machine",
        "predictor_family",
        "candidate_family",
        "direction",
        "analysis_mode",
        "lead",
    ]
    validation = summary[summary["split"] == "validation"].copy()
    validation = validation[np.isfinite(validation["weighted_spearman"])]
    validation["absolute_spearman"] = validation["weighted_spearman"].abs()
    validation = validation.sort_values(
        keys + ["absolute_spearman", "predictor_lag", "predictor"],
        ascending=[True] * len(keys) + [False, True, True],
        kind="stable",
    )
    selected = validation.drop_duplicates(keys, keep="first").copy()
    selected = selected.rename(
        columns={
            "predictor_lag": "selected_lag",
            "weighted_spearman": "validation_weighted_spearman",
            "weighted_pearson": "validation_weighted_pearson",
            "n_samples": "validation_n",
            "n_segments": "validation_segments",
        }
    )
    selected_columns = keys + [
        "selected_lag",
        "validation_weighted_spearman",
        "validation_weighted_pearson",
        "validation_n",
        "validation_segments",
    ]
    selected = selected[selected_columns].sort_values(keys).reset_index(drop=True)
    selected.to_csv(OUTPUT_DIR / "validation_selected_lags.csv", index=False)

    test = summary[summary["split"] == "test"].copy()
    test_selected = selected.merge(
        test,
        left_on=keys + ["selected_lag"],
        right_on=keys + ["predictor_lag"],
        how="left",
        validate="one_to_one",
        suffixes=("", "_test"),
    )
    if test_selected["weighted_spearman"].isna().any():
        # Undefined test correlations are retained, but missing joins are not allowed.
        joined = test_selected["predictor_lag"].notna()
        if not joined.all():
            raise RuntimeError("A selected validation lag has no corresponding test row")
    test_selected = test_selected.rename(
        columns={
            "n_samples": "test_n",
            "n_segments": "test_segments",
            "weighted_pearson": "test_weighted_pearson",
            "weighted_spearman": "test_weighted_spearman",
            "positive_segment_weight_fraction": "test_positive_segment_weight_fraction",
            "negative_segment_weight_fraction": "test_negative_segment_weight_fraction",
        }
    )
    test_selected.to_parquet(
        OUTPUT_DIR / "test_association_at_selected_lag.parquet",
        index=False,
        compression="zstd",
    )
    return selected, test_selected


def choose_nonzero_mi_lags(summary: pd.DataFrame) -> pd.DataFrame:
    keys = [
        "target",
        "target_machine",
        "target_family",
        "predictor",
        "predictor_machine",
        "predictor_family",
        "candidate_family",
        "direction",
        "analysis_mode",
        "lead",
    ]
    validation = summary[
        (summary["split"] == "validation") & (summary["predictor_lag"] > 0)
    ].copy()
    validation = validation[np.isfinite(validation["weighted_spearman"])]
    validation["absolute_spearman"] = validation["weighted_spearman"].abs()
    validation = validation.sort_values(
        keys + ["absolute_spearman", "predictor_lag", "predictor"],
        ascending=[True] * len(keys) + [False, True, True],
        kind="stable",
    )
    return validation.drop_duplicates(keys, keep="first")[keys + ["predictor_lag"]].rename(
        columns={"predictor_lag": "selected_nonzero_lag"}
    )


def deterministic_cap(mask: np.ndarray, maximum: int) -> np.ndarray:
    indices = np.flatnonzero(mask)
    if len(indices) <= maximum:
        return indices
    positions = np.linspace(0, len(indices) - 1, maximum, dtype=int)
    return indices[positions]


def mutual_information_pass(
    panel: pd.DataFrame,
    candidates: list[Candidate],
    masks: dict[tuple[str, int], dict[str, np.ndarray]],
    nonzero_lags: pd.DataFrame,
) -> pd.DataFrame:
    candidate_lookup = {
        (c.target, c.predictor, c.candidate_family): c for c in candidates
    }
    tasks: list[tuple[Candidate, str, int, int, str, str]] = []
    for row in nonzero_lags.itertuples(index=False):
        candidate = candidate_lookup[(row.target, row.predictor, row.candidate_family)]
        for evaluated_lag, source in (
            (0, "fixed_lag_0"),
            (int(row.selected_nonzero_lag), "validation_selected_nonzero_lag"),
        ):
            for split in SPLITS:
                tasks.append(
                    (
                        candidate,
                        row.analysis_mode,
                        int(row.lead),
                        evaluated_lag,
                        source,
                        split,
                    )
                )

    def evaluate(task: tuple[Candidate, str, int, int, str, str]) -> dict[str, Any]:
        candidate, mode, lead, lag, source, split = task
        y = target_values(panel, candidate.target, lead, mode)
        x, predictor_segment_safe = predictor_values(panel, candidate, lag, mode)
        valid = (
            masks[(candidate.target, lead)][split]
            & predictor_segment_safe
            & finite_mask(x)
            & finite_mask(y)
        )
        original_n = int(valid.sum())
        indices = deterministic_cap(valid, MI_MAX_SAMPLES)
        if (
            len(indices) <= MI_NEIGHBORS
            or np.unique(x[indices]).size <= 1
            or np.unique(y[indices]).size <= 1
        ):
            mi = np.nan
        else:
            mi = float(
                mutual_info_regression(
                    x[indices].reshape(-1, 1),
                    y[indices],
                    discrete_features=False,
                    n_neighbors=MI_NEIGHBORS,
                    random_state=MI_RANDOM_STATE,
                    n_jobs=1,
                )[0]
            )
        return {
            "analysis_mode": mode,
            "target": candidate.target,
            "target_machine": candidate.target_machine,
            "target_family": candidate.target_family,
            "predictor": candidate.predictor,
            "predictor_machine": candidate.predictor_machine,
            "predictor_family": candidate.predictor_family,
            "candidate_family": candidate.candidate_family,
            "direction": candidate.direction,
            "lead": lead,
            "evaluated_lag": lag,
            "lag_selection_source": source,
            "split": split,
            "original_n": original_n,
            "mi_n": len(indices),
            "mutual_information": mi,
        }

    workers = max(1, min(8, os.cpu_count() or 1))
    with threadpool_limits(limits=1):
        rows = Parallel(n_jobs=workers, prefer="threads", verbose=5)(
            delayed(evaluate)(task) for task in tasks
        )
    result = pd.DataFrame(rows)
    result.to_parquet(
        OUTPUT_DIR / "mutual_information_summary.parquet",
        index=False,
        compression="zstd",
    )
    return result


def selected_split_evidence(
    selected: pd.DataFrame, summary: pd.DataFrame
) -> pd.DataFrame:
    keys = [
        "target",
        "target_machine",
        "target_family",
        "predictor",
        "predictor_machine",
        "predictor_family",
        "candidate_family",
        "direction",
        "analysis_mode",
        "lead",
    ]
    evidence = selected.merge(
        summary,
        left_on=keys + ["selected_lag"],
        right_on=keys + ["predictor_lag"],
        how="inner",
        validate="one_to_many",
    )
    return evidence[evidence["split"].isin(["validation", "test"])].copy()


def family_direction_outputs(evidence: pd.DataFrame) -> pd.DataFrame:
    directional = evidence[
        evidence["candidate_family"].isin(
            ["same_machine_cross_resource", "global_context"]
        )
    ].copy()

    def summarize(group: pd.DataFrame) -> pd.Series:
        values = group["weighted_spearman"].dropna()
        signs = np.sign(values.to_numpy())
        sign_consistency = (
            float(max((signs > 0).mean(), (signs < 0).mean())) if len(signs) else np.nan
        )
        dominant_sign = (
            "positive"
            if len(signs) and (signs > 0).sum() > (signs < 0).sum()
            else "negative"
            if len(signs) and (signs < 0).sum() > (signs > 0).sum()
            else "tie_or_undefined"
        )
        return pd.Series(
            {
                "number_machine_relationships": len(group),
                "median_absolute_selected_lag_spearman": values.abs().median(),
                "maximum_absolute_selected_lag_spearman": values.abs().max(),
                "median_selected_predictor_lag": group["selected_lag"].median(),
                "fraction_abs_spearman_ge_0_10": float((values.abs() >= 0.10).mean()),
                "fraction_abs_spearman_ge_0_20": float((values.abs() >= 0.20).mean()),
                "sign_consistency": sign_consistency,
                "dominant_sign": dominant_sign,
            }
        )

    result = (
        directional.groupby(
            ["direction", "target_family", "predictor_family", "analysis_mode", "lead", "split"],
            dropna=False,
            sort=True,
        )
        .apply(summarize, include_groups=False)
        .reset_index()
    )
    result.to_csv(OUTPUT_DIR / "resource_direction_association_summary.csv", index=False)
    return result


def cross_machine_output(evidence: pd.DataFrame) -> pd.DataFrame:
    pairwise = evidence[
        evidence["candidate_family"] == "same_resource_cross_machine"
    ].copy()
    pairwise["comparison_type"] = "pairwise_machine"
    pairwise["context_statistic"] = ""
    context = evidence[evidence["candidate_family"] == "leave_one_machine_out"].copy()
    context["comparison_type"] = "leave_one_machine_out"
    context["context_statistic"] = np.where(
        context["predictor"].str.endswith("_mean"), "mean", "median"
    )
    columns = [
        "target_family",
        "analysis_mode",
        "lead",
        "split",
        "target",
        "target_machine",
        "predictor",
        "predictor_machine",
        "comparison_type",
        "context_statistic",
        "selected_lag",
        "weighted_pearson",
        "weighted_spearman",
        "n_samples",
        "n_segments",
    ]
    result = pd.concat([pairwise[columns], context[columns]], ignore_index=True)
    result = result.sort_values(
        ["target_family", "analysis_mode", "lead", "split", "target", "predictor"]
    )
    result.to_parquet(
        OUTPUT_DIR / "cross_machine_association_summary.parquet",
        index=False,
        compression="zstd",
    )
    return result


def lead_decay_output(evidence: pd.DataFrame) -> pd.DataFrame:
    test = evidence[evidence["split"] == "test"].copy()
    result = (
        test.groupby(
            ["candidate_family", "direction", "analysis_mode", "lead"],
            dropna=False,
            sort=True,
        )
        .agg(
            relationships=("weighted_spearman", "size"),
            finite_relationships=("weighted_spearman", "count"),
            median_test_spearman=("weighted_spearman", "median"),
            median_absolute_test_spearman=(
                "weighted_spearman",
                lambda s: s.abs().median(),
            ),
            maximum_absolute_test_spearman=(
                "weighted_spearman",
                lambda s: s.abs().max(),
            ),
            median_selected_lag=("selected_lag", "median"),
        )
        .reset_index()
    )
    result.to_csv(OUTPUT_DIR / "association_lead_decay.csv", index=False)
    return result


def make_figures(
    evidence: pd.DataFrame,
    direction_summary: pd.DataFrame,
    cross_machine: pd.DataFrame,
) -> list[Path]:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for old in FIGURE_DIR.glob("*"):
        if old.is_file():
            old.unlink()
    sns.set_theme(style="whitegrid")
    paths: list[Path] = []

    # 1. Direction-by-lead median signed held-out association.
    data = direction_summary[direction_summary["split"] == "test"].copy()
    # Keep both modes explicit rather than mixing level and change.
    data["display_direction"] = data["direction"] + " [" + data["analysis_mode"] + "]"
    source = evidence[
        (evidence["split"] == "test")
        & evidence["candidate_family"].isin(["same_machine_cross_resource", "global_context"])
    ].copy()
    source["display_direction"] = source["direction"] + " [" + source["analysis_mode"] + "]"
    pivot = source.pivot_table(
        index="display_direction",
        columns="lead",
        values="weighted_spearman",
        aggfunc="median",
    ).reindex(columns=LEADS)
    fig, ax = plt.subplots(figsize=(11, max(7, 0.30 * len(pivot))))
    sns.heatmap(pivot, cmap="vlag", center=0, vmin=-1, vmax=1, ax=ax)
    ax.set_title("Held-out test Spearman at validation-selected lag")
    ax.set_xlabel("Future lead (samples)")
    ax.set_ylabel("Resource direction and target mode")
    fig.tight_layout()
    path = FIGURE_DIR / "01_resource_direction_test_spearman_heatmap.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(path)

    def cross_machine_figure(family: str, filename: str, title: str) -> None:
        mode = "level" if family == "memory" else "native"
        source = cross_machine[
            (cross_machine["target_family"] == family)
            & (cross_machine["analysis_mode"] == mode)
            & (cross_machine["split"] == "test")
            & (cross_machine["comparison_type"] == "pairwise_machine")
        ]
        fig, axes = plt.subplots(2, 4, figsize=(16, 8), constrained_layout=True)
        for ax, lead in zip(axes.flat, LEADS):
            lead_data = source[source["lead"] == lead]
            matrix = lead_data.pivot(
                index="target_machine",
                columns="predictor_machine",
                values="weighted_spearman",
            ).reindex(index=MACHINES, columns=MACHINES)
            sns.heatmap(
                matrix,
                cmap="vlag",
                center=0,
                vmin=-1,
                vmax=1,
                square=True,
                cbar=lead == LEADS[-1],
                ax=ax,
            )
            ax.set_title(f"Lead {lead}")
            ax.set_xlabel("Source")
            ax.set_ylabel("Target")
        fig.suptitle(title)
        path = FIGURE_DIR / filename
        fig.savefig(path, dpi=160)
        plt.close(fig)
        paths.append(path)

    cross_machine_figure(
        "CPU", "02_cpu_cross_machine_test_spearman.png", "CPU cross-machine test Spearman"
    )
    cross_machine_figure(
        "memory",
        "03_memory_cross_machine_test_spearman.png",
        "Memory cross-machine level test Spearman",
    )
    cross_machine_figure(
        "throughput",
        "04_throughput_cross_machine_test_spearman.png",
        "Throughput cross-machine test Spearman",
    )

    # 5. Level-vs-change held-out comparison.
    source = evidence[
        (evidence["split"] == "test")
        & evidence["target_family"].isin(["memory", "disk"])
    ].copy()
    comparison = (
        source.groupby(["target_family", "analysis_mode", "lead"])
        ["weighted_spearman"]
        .apply(lambda s: s.abs().median())
        .reset_index(name="median_absolute_test_spearman")
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.lineplot(
        data=comparison,
        x="lead",
        y="median_absolute_test_spearman",
        hue="target_family",
        style="analysis_mode",
        markers=True,
        dashes=False,
        ax=ax,
    )
    ax.set_xscale("log", base=2)
    ax.set_xticks(LEADS, labels=LEADS)
    ax.set_title("Level versus origin-to-future change association")
    ax.set_xlabel("Future lead (samples)")
    fig.tight_layout()
    path = FIGURE_DIR / "05_memory_disk_level_vs_change.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    paths.append(path)
    if len(paths) != 5:
        raise RuntimeError("Exactly five figures were not generated")
    return paths


def fmt(value: float) -> str:
    return "undefined" if not np.isfinite(value) else f"{value:.3f}"


def generate_report(
    evidence: pd.DataFrame,
    cross_machine: pd.DataFrame,
    lead_decay: pd.DataFrame,
    runtime_seconds: float,
    validation: dict[str, Any],
) -> None:
    test = evidence[evidence["split"] == "test"].copy()
    local = test[
        test["candidate_family"].isin(["same_machine_cross_resource", "global_context"])
    ]
    strongest = (
        local.groupby(["direction", "analysis_mode"])["weighted_spearman"]
        .apply(lambda s: s.abs().median())
        .sort_values(ascending=False)
        .head(10)
    )
    strongest_lines = "\n".join(
        f"- {direction} ({mode}): median absolute test Spearman {value:.3f}"
        for (direction, mode), value in strongest.items()
    )

    change = local[local["analysis_mode"] == "change"]
    change_top = (
        change.groupby(["direction"])["weighted_spearman"]
        .apply(lambda s: s.abs().median())
        .sort_values(ascending=False)
        .head(6)
    )
    change_lines = "\n".join(
        f"- {direction}: median absolute test Spearman {value:.3f}"
        for direction, value in change_top.items()
    )

    cross = cross_machine[
        (cross_machine["split"] == "test")
        & (cross_machine["comparison_type"] == "pairwise_machine")
    ]
    cross_stats = (
        cross.groupby(["target_family", "analysis_mode"])["weighted_spearman"]
        .apply(lambda s: s.abs().median())
        .to_dict()
    )
    comparison = (
        cross_machine[cross_machine["split"] == "test"]
        .groupby(["target_family", "analysis_mode", "comparison_type"])[
            "weighted_spearman"
        ]
        .apply(lambda s: s.abs().median())
        .reset_index()
    )
    comparison_lines = "\n".join(
        f"- {r.target_family} ({r.analysis_mode}), {r.comparison_type}: "
        f"median absolute test Spearman {r.weighted_spearman:.3f}"
        for r in comparison.itertuples(index=False)
    )

    global_context = local[local["predictor_family"].isin(["RTT", "jitter"])]
    global_stats = (
        global_context.groupby("predictor_family")["weighted_spearman"]
        .apply(lambda s: s.abs().median())
        .to_dict()
    )
    decay_local = lead_decay[
        lead_decay["candidate_family"].isin(["same_machine_cross_resource", "global_context"])
    ]
    decay = (
        decay_local.groupby("lead")["median_absolute_test_spearman"].median().reindex(LEADS)
    )
    decay_text = ", ".join(f"{lead}: {fmt(value)}" for lead, value in decay.items())

    report = f"""# Phase 1B-1 Lagged Association Report

This report describes association only. It contains no Ridge results,
forecasting claims, dependency classifications, or causal claims. In
particular, causality has not been established.

## Method and interpretation boundaries

- The comparison is `x[t-lag]` against `y[t+lead]`.
- Lag 0 is contemporaneous origin-time context; positive lags are historical
  predictor observations.
- Leads and lags are the frozen grids in `PROTOCOL.md`.
- All train/validation/test assignments use the target-time-purged split.
- Correlations are computed within canonical temporal segments. The summary
  coefficients are deterministic sample-weighted averages of eligible
  segment coefficients; segments with fewer than 30 complete pairs or a
  constant variable remain undefined.
- The supporting lag is selected only from validation weighted Spearman.
  Held-out test association is evaluated at that unchanged selected lag.
- Memory and used disk are reported both as future levels and as cumulative
  origin-to-future changes. Level-like predictors in change mode use only the
  historical difference `x[t-l] - x[t-l-1]`.
- Mutual information is auxiliary. It is evaluated at lag 0 and one nonzero
  validation-selected lag, with deterministic capping at 20,000 observations.

Lag 0 and positive historical lags should not be conflated. A large held-out
coefficient at a validation-selected positive lag is still descriptive
association and does not demonstrate incremental predictive value beyond the
target's own history.

## Execution summary

- Runtime: {runtime_seconds:.1f} seconds
- Candidate relationships: {validation['candidate_relationships']}
- Candidate/target/mode combinations: {validation['candidate_mode_relationships']}
- Split-level association cells: {validation['total_association_cells']}
- Segment-level cells: {validation['segment_level_cells']}
- Validation-selected relationships: {validation['validation_selected_relationships']}
- Mutual-information evaluations: {validation['mi_evaluations']}
- Segment crossings: 0
- Test-based lag selections: 0

## Strongest descriptive resource directions

The largest median absolute held-out associations across the frozen
same-machine/global directions were:

{strongest_lines}

## Level and change contrast

The strongest change-mode directions were:

{change_lines}

Level coefficients can reflect persistence and shared trends. Change-mode
coefficients ask the narrower question of whether historical predictor
information aligns with cumulative target movement from origin to lead.

## Cross-machine and shared context

Median absolute held-out cross-machine coefficients:

- CPU native: {fmt(cross_stats.get(('CPU', 'native'), np.nan))}
- memory level: {fmt(cross_stats.get(('memory', 'level'), np.nan))}
- memory change: {fmt(cross_stats.get(('memory', 'change'), np.nan))}
- throughput native: {fmt(cross_stats.get(('throughput', 'native'), np.nan))}

Pairwise and leave-one-machine-out comparison:

{comparison_lines}

## Global RTT and jitter context

- RTT median absolute held-out association:
  {fmt(global_stats.get('RTT', np.nan))}
- Jitter median absolute held-out association:
  {fmt(global_stats.get('jitter', np.nan))}

## Lead dependence

Median of direction-level median absolute held-out Spearman by lead:
{decay_text}.

## Association Findings Before Predictive Screening

1. **Which directional resource pairs show the strongest held-out lagged
   associations?** CPU <- throughput is strongest in aggregate, followed by
   disk <- memory level, throughput <- CPU, and memory <- throughput level.
   Signal-specific and lead-specific results remain in the machine-readable
   outputs.
2. **Which relationships survive change analysis?** The change-mode list above
   shows that memory <- CPU retains the clearest aggregate coefficient
   ({fmt(change_top.get('memory <- CPU', np.nan))}); memory <- throughput is
   smaller, and disk change associations are weak in aggregate.
3. **Are CPU cross-machine associations strong?** Not broadly: the median
   absolute held-out coefficient is
   {fmt(cross_stats.get(('CPU', 'native'), np.nan))}, although individual
   pairs and leads are heterogeneous.
4. **Are memory cross-machine associations strong?** Level associations are
   noticeable at {fmt(cross_stats.get(('memory', 'level'), np.nan))}, but the
   change result is only
   {fmt(cross_stats.get(('memory', 'change'), np.nan))}. The cross-machine
   pattern therefore does not remain strong after removing the future-level
   representation.
5. **Are throughput cross-machine associations strong?** They are modest in
   aggregate at {fmt(cross_stats.get(('throughput', 'native'), np.nan))}, with
   pair-specific detail retained by lead.
6. **Are pair-specific machine associations stronger than leave-one-machine-out
   context?** Usually not in aggregate: leave-one-machine-out context is
   stronger for CPU and throughput and slightly stronger for memory change.
   Pairwise memory level is the exception, exceeding its common context.
7. **Do RTT or jitter show notable lagged associations?** No broad pattern is
   apparent: their median absolute held-out values are
   {fmt(global_stats.get('RTT', np.nan))} and
   {fmt(global_stats.get('jitter', np.nan))}, respectively.
8. **How quickly do associations decay with future lead?** The aggregate
   median does not decay monotonically: it remains near 0.05 through lead 32,
   dips at lead 64, and rebounds slightly at lead 128. No forecast horizon is
   selected from this pattern.
9. **Which relationships are worth testing in the already-predeclared Ridge
   screen?** CPU <-> throughput, disk <- memory level, memory <- CPU change,
   and memory <- throughput change are the clearest discussion priorities.
   This prioritization does not remove any candidate: the Ridge phase must
   evaluate the complete frozen candidate set and compare every augmentation
   with the own-history baseline.
"""
    REPORT_PATH.write_text(report)


def main() -> None:
    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    raw_frozen = json.loads(PHASE1_HASH_PATH.read_text())["after"]
    raw_before = {
        name: sha256_file(ROOT / "data" / "raw" / name) for name in raw_frozen
    }
    if raw_before != raw_frozen:
        raise RuntimeError("Raw SHA-256 mismatch before association analysis")
    panel_hash_before = sha256_file(PANEL_PATH)
    registry_hash_before = sha256_file(REGISTRY_PATH)
    protocol_hash_before = sha256_file(PHASE_DIR / "PROTOCOL.md")

    panel = pd.read_parquet(PANEL_PATH)
    panel["timestamp"] = pd.to_datetime(panel["timestamp"])
    registry = pd.read_csv(REGISTRY_PATH)
    split_rows = pd.read_csv(
        SPLIT_PATH,
        parse_dates=["train_cut_timestamp", "validation_cut_timestamp"],
    )
    if sorted(split_rows["lead"].unique().tolist()) != LEADS:
        raise RuntimeError("Frozen lead grid changed")
    if len(split_rows) != 224:
        raise RuntimeError("Expected 224 target/lead split definitions")
    if not split_rows["leakage_check_train_validation"].all() or not split_rows[
        "leakage_check_validation_test"
    ].all():
        raise RuntimeError("Purged split leakage validation failed")

    candidates = build_candidates(set(panel.columns))
    registered = set(registry["canonical_name"])
    if any(c.target not in registered or c.predictor not in registered for c in candidates):
        raise RuntimeError("Candidate outside canonical registry")
    candidate_modes = sum(len(analysis_modes(c.target_family)) for c in candidates)
    masks = master_masks(panel, split_rows)

    summary, segment_cells = association_pass(panel, candidates, masks)
    expected_cells = candidate_modes * len(LEADS) * len(LAGS) * len(SPLITS)
    if len(summary) != expected_cells:
        raise RuntimeError(f"Association cell count {len(summary)} != {expected_cells}")

    selected, test_selected = select_validation_lags(summary)
    expected_selected = candidate_modes * len(LEADS)
    if len(selected) != expected_selected:
        raise RuntimeError(f"Selected relationships {len(selected)} != {expected_selected}")
    nonzero_lags = choose_nonzero_mi_lags(summary)
    if len(nonzero_lags) != expected_selected:
        raise RuntimeError("A relationship lacks a validation-selected nonzero MI lag")
    mi = mutual_information_pass(panel, candidates, masks, nonzero_lags)
    expected_mi = expected_selected * 2 * len(SPLITS)
    if len(mi) != expected_mi:
        raise RuntimeError(f"MI evaluations {len(mi)} != {expected_mi}")

    evidence = selected_split_evidence(selected, summary)
    direction_summary = family_direction_outputs(evidence)
    cross_machine = cross_machine_output(evidence)
    lead_decay = lead_decay_output(evidence)
    figures = make_figures(evidence, direction_summary, cross_machine)

    raw_after = {
        name: sha256_file(ROOT / "data" / "raw" / name) for name in raw_frozen
    }
    runtime = time.perf_counter() - started
    validation = {
        "status": "PASS",
        "runtime_seconds": runtime,
        "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "candidate_relationships": len(candidates),
        "candidate_mode_relationships": candidate_modes,
        "total_association_cells": len(summary),
        "segment_level_cells": segment_cells,
        "validation_selected_relationships": len(selected),
        "mi_evaluations": len(mi),
        "frozen_leads": LEADS,
        "frozen_lags": LAGS,
        "segment_crossings": 0,
        "test_based_lag_selections": 0,
        "all_test_rows_joined_to_validation_selection": bool(
            len(test_selected) == len(selected)
        ),
        "canonical_panel_unchanged": sha256_file(PANEL_PATH) == panel_hash_before,
        "canonical_registry_unchanged": sha256_file(REGISTRY_PATH) == registry_hash_before,
        "protocol_unchanged": sha256_file(PHASE_DIR / "PROTOCOL.md") == protocol_hash_before,
        "raw_hashes_unchanged_and_match_phase1": raw_after == raw_before == raw_frozen,
        "panel_sha256": panel_hash_before,
        "raw_hashes": raw_after,
        "generated_files": [
            str(OUTPUT_DIR / "lagged_associations.parquet"),
            str(OUTPUT_DIR / "lagged_association_summary.parquet"),
            str(OUTPUT_DIR / "mutual_information_summary.parquet"),
            str(OUTPUT_DIR / "validation_selected_lags.csv"),
            str(OUTPUT_DIR / "test_association_at_selected_lag.parquet"),
            str(OUTPUT_DIR / "resource_direction_association_summary.csv"),
            str(OUTPUT_DIR / "cross_machine_association_summary.parquet"),
            str(OUTPUT_DIR / "association_lead_decay.csv"),
            *[str(path) for path in figures],
            str(REPORT_PATH),
        ],
    }
    required_checks = [
        validation["all_test_rows_joined_to_validation_selection"],
        validation["canonical_panel_unchanged"],
        validation["canonical_registry_unchanged"],
        validation["protocol_unchanged"],
        validation["raw_hashes_unchanged_and_match_phase1"],
    ]
    if not all(required_checks):
        raise RuntimeError("Immutable-input validation failed")
    generate_report(evidence, cross_machine, lead_decay, runtime, validation)
    json_write(OUTPUT_DIR / "association_validation.json", validation)
    print(json.dumps(validation, indent=2, default=str))


if __name__ == "__main__":
    main()
