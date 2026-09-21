#!/usr/bin/env python3
"""Build the frozen Phase 1B canonical panel without altering raw data.

This script is intentionally self-contained. It does not import historical
project code. Inputs are the six active CSV files plus read-only Phase 1A audit
metadata; outputs are written only below this phase's ``outputs`` directory.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
AUDIT_OUTPUTS = ROOT / "discovery" / "01_data_audit" / "outputs"
OUTPUT_DIR = ROOT / "discovery" / "02_dependency_analysis" / "outputs"

RAW_FILES = [
    "compute_dataset.csv",
    "detailed_cpu_cores_dataset.csv",
    "disk_dataset.csv",
    "network_dataset.csv",
    "packet-loss-dataset.csv",
    "throughputs_dataset.csv",
]

MACHINE_TO_HOST = {
    "machine01": "acamas",
    "machine02": "bellerophon",
    "machine03": "dedale",
    "machine04": "demophon",
    "machine05": "pegase",
    "machine06": "perse",
    "machine07": "phaedra",
}
MACHINES = list(MACHINE_TO_HOST)
HOSTS = list(MACHINE_TO_HOST.values())

FUTURE_LEADS = [1, 2, 4, 8, 16, 32, 64, 128]
ASSOCIATION_LAGS = [0, 1, 2, 4, 8, 16, 32, 64, 128]
RIDGE_HISTORY_LAGS = [0, 1, 2, 4, 8, 16, 32]
NEAR_CONSTANT_THRESHOLD = 0.99
ZERO_DOMINATED_THRESHOLD = 0.95

# A bond interface is accepted as the compact host-direction representation
# only if it independently reconstructs from all named non-bond interfaces.
NETWORK_MAX_RELATIVE_MAE = 0.005
NETWORK_MIN_CORRELATION = 0.999
NETWORK_MIN_OVERLAP_FRACTION = 0.95


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    def convert(value: Any) -> Any:
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return None if not np.isfinite(value) else float(value)
        if isinstance(value, (pd.Timestamp, Path)):
            return str(value)
        raise TypeError(type(value).__name__)

    path.write_text(json.dumps(payload, indent=2, default=convert) + "\n")


def read_timestamped_csv(name: str, usecols: list[str] | None = None) -> pd.DataFrame:
    path = RAW_DIR / name
    if not path.is_file():
        raise FileNotFoundError(path)
    columns = None if usecols is None else ["timestamp", *usecols]
    frame = pd.read_csv(path, usecols=columns, low_memory=False)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="raise")
    if frame["timestamp"].duplicated().any():
        raise ValueError(f"{name}: duplicate timestamps")
    if not frame["timestamp"].is_monotonic_increasing:
        raise ValueError(f"{name}: timestamps not increasing")
    return frame


def aligned(frame: pd.DataFrame, common: pd.DatetimeIndex) -> pd.DataFrame:
    indexed = frame.set_index("timestamp")
    result = indexed.reindex(common)
    result.index.name = "timestamp"
    return result


def series_quality(series: pd.Series) -> dict[str, Any]:
    numeric = pd.to_numeric(series, errors="coerce")
    finite = numeric.replace([np.inf, -np.inf], np.nan).dropna()
    missing_fraction = float(numeric.isna().mean())
    unique = int(finite.nunique())
    constant = unique <= 1
    dominant = float(finite.value_counts(normalize=True).iloc[0]) if len(finite) else np.nan
    unchanged = float((numeric.diff().dropna() == 0).mean()) if len(numeric) > 1 else np.nan
    zero_fraction = float((finite == 0).mean()) if len(finite) else np.nan
    near_constant = bool(
        not constant
        and (
            (np.isfinite(dominant) and dominant >= NEAR_CONSTANT_THRESHOLD)
            or (np.isfinite(unchanged) and unchanged >= NEAR_CONSTANT_THRESHOLD)
        )
    )
    return {
        "missing_fraction": missing_fraction,
        "constant": constant,
        "near_constant": near_constant,
        "zero_dominated": bool(
            np.isfinite(zero_fraction) and zero_fraction >= ZERO_DOMINATED_THRESHOLD
        ),
        "zero_fraction": zero_fraction,
        "negative_count": int((finite < 0).sum()),
        "positive_infinity_count": int(np.isposinf(numeric.to_numpy(dtype=float)).sum()),
        "negative_infinity_count": int(np.isneginf(numeric.to_numpy(dtype=float)).sum()),
    }


def registry_row(
    canonical_name: str,
    resource_family: str,
    metric: str,
    machine: str,
    host: str,
    scope: str,
    raw_dataset: str,
    raw_column: str,
    component_columns: list[str],
    transformation: str,
    unit: str,
    known_redundancy_relationship: str,
    selection_rationale: str,
    role: str = "primary",
) -> dict[str, Any]:
    return {
        "canonical_name": canonical_name,
        "resource_family": resource_family,
        "metric": metric,
        "machine": machine,
        "host": host,
        "scope": scope,
        "raw_dataset": raw_dataset,
        "raw_column": raw_column,
        "component_columns": json.dumps(component_columns),
        "transformation": transformation,
        "unit_if_inferable": unit,
        "missing_fraction": np.nan,
        "constant": False,
        "near_constant": False,
        "zero_dominated": False,
        "zero_fraction": np.nan,
        "quality_warnings": "",
        "known_redundancy_relationship": known_redundancy_relationship,
        "selection_rationale": selection_rationale,
        "analysis_role": role,
    }


def add_quality(
    row: dict[str, Any],
    series: pd.Series,
    phase1_quality: pd.DataFrame,
    extra_warnings: list[str] | None = None,
) -> dict[str, Any]:
    quality = series_quality(series)
    for field in ("missing_fraction", "constant", "near_constant", "zero_dominated", "zero_fraction"):
        row[field] = quality[field]
    warnings = list(extra_warnings or [])
    if quality["missing_fraction"] > 0:
        warnings.append(f"aligned missing fraction={quality['missing_fraction']:.6f}")
    if quality["constant"]:
        warnings.append("constant on canonical panel")
    if quality["near_constant"]:
        warnings.append("near-constant on canonical panel")
    if quality["zero_dominated"]:
        warnings.append(f"zero-dominated; zero fraction={quality['zero_fraction']:.6f}")
    if quality["negative_count"]:
        warnings.append(f"{quality['negative_count']} negative values retained")
    if quality["positive_infinity_count"] or quality["negative_infinity_count"]:
        warnings.append("infinite values retained")

    # Carry forward Phase 1A warnings for direct raw columns.
    if row["raw_column"]:
        match = phase1_quality[
            (phase1_quality["dataset"] == row["raw_dataset"])
            & (phase1_quality["column"] == row["raw_column"])
        ]
        if len(match):
            audit = match.iloc[0]
            if int(audit.get("bounded_percentage_violation_count", 0)) > 0:
                warnings.append(
                    "Phase 1A bounded-range violations="
                    f"{int(audit['bounded_percentage_violation_count'])}"
                )
            note = str(audit.get("quality_notes", ""))
            if note and note != "nan":
                warnings.append(f"Phase 1A: {note}")
    row["quality_warnings"] = "; ".join(dict.fromkeys(warnings))
    return row


def validate_network_representations(
    throughput: pd.DataFrame,
    catalogue: pd.DataFrame,
    exact_duplicates: pd.DataFrame,
    high_correlations: pd.DataFrame,
    discovered: pd.DataFrame,
) -> pd.DataFrame:
    """Evaluate one compact host-direction signal without blindly summing interfaces."""
    rows: list[dict[str, Any]] = []
    signal_names = set(catalogue[catalogue["resource_family"] == "network throughput"]["column"])
    n_total = len(throughput)
    for machine, host in MACHINE_TO_HOST.items():
        for direction, short in (("transmitted", "tx"), ("received", "rx")):
            prefix = f"{direction}_throughput_{host}:-network-device-"
            channels = sorted(c for c in signal_names if c.startswith(prefix))
            bond = prefix + "bond0"
            components = [c for c in channels if c != bond]
            direction_supported = all(c.startswith(f"{direction}_throughput_") for c in channels)
            reason_parts: list[str] = []
            decision = "unresolved"
            selected = ""
            corr = rel_mae = max_abs = np.nan
            overlap = 0
            exact_duplicate_count = 0
            high_corr_count = 0
            relation_row = discovered[
                (discovered["relationship_family"] == "network_bond0_interface_sum")
                & (discovered["lhs"] == bond)
            ]
            if len(relation_row):
                rr = relation_row.iloc[0]
                corr = float(rr["pearson_correlation"])
                rel_mae = float(rr["relative_mean_abs_error"])
                max_abs = float(rr["max_abs_error"])
                overlap = int(rr["n"])
            if channels:
                channel_set = set(channels)
                exact_duplicate_count = int(
                    (
                        exact_duplicates["column_a"].isin(channel_set)
                        & exact_duplicates["column_b"].isin(channel_set)
                    ).sum()
                )
                high_corr_count = int(
                    (
                        high_correlations["column_a"].isin(channel_set)
                        & high_correlations["column_b"].isin(channel_set)
                    ).sum()
                )
            bond_nonmissing = float(throughput[bond].notna().mean()) if bond in throughput else 0.0
            gate = (
                bond in throughput
                and len(components) > 0
                and direction_supported
                and overlap / n_total >= NETWORK_MIN_OVERLAP_FRACTION
                and np.isfinite(corr)
                and corr >= NETWORK_MIN_CORRELATION
                and np.isfinite(rel_mae)
                and rel_mae <= NETWORK_MAX_RELATIVE_MAE
                and bond_nonmissing >= NETWORK_MIN_OVERLAP_FRACTION
            )
            if gate:
                decision = "selected_aggregate_interface"
                selected = bond
                reason_parts.append(
                    "single direction-explicit bond0 channel selected as the smallest representation"
                )
                reason_parts.append(
                    f"independently validated against {len(components)} named non-bond components"
                )
            else:
                reason_parts.append("semantic/numerical aggregate gate failed; no machine total selected")
            rows.append(
                {
                    "machine": machine,
                    "host": host,
                    "direction": short,
                    "all_interface_channels": json.dumps(channels),
                    "aggregate_candidate": bond if bond in throughput else "",
                    "component_channels": json.dumps(components),
                    "direction_semantics_supported_by_names": direction_supported,
                    "exact_duplicate_pairs_within_host_direction": exact_duplicate_count,
                    "high_correlation_pairs_within_host_direction": high_corr_count,
                    "overlap_rows": overlap,
                    "overlap_fraction": overlap / n_total,
                    "aggregate_nonmissing_fraction": bond_nonmissing,
                    "aggregate_vs_component_sum_correlation": corr,
                    "aggregate_vs_component_sum_relative_mae": rel_mae,
                    "aggregate_vs_component_sum_max_abs_error": max_abs,
                    "decision": decision,
                    "selected_raw_column": selected,
                    "decision_rationale": "; ".join(reason_parts),
                }
            )
    return pd.DataFrame(rows)


def deterministic_split_boundaries(panel: pd.DataFrame, targets: list[str]) -> pd.DataFrame:
    """Compute leakage-safe, target-time-purged chronological split boundaries."""
    rows: list[dict[str, Any]] = []
    segment = panel["segment_id"]
    max_history = max(RIDGE_HISTORY_LAGS)
    for target in targets:
        y = panel[target]
        for lead in FUTURE_LEADS:
            eligible = pd.Series(True, index=panel.index)
            for lag in RIDGE_HISTORY_LAGS:
                eligible &= y.shift(lag).notna()
            eligible &= y.shift(-lead).notna()
            eligible &= segment.eq(segment.shift(max_history))
            eligible &= segment.eq(segment.shift(-lead))
            origins = pd.DataFrame(
                {
                    "origin_timestamp": panel.loc[eligible, "timestamp"],
                    "target_timestamp": panel["timestamp"].shift(-lead).loc[eligible],
                    "segment_id": segment.loc[eligible],
                    "target_segment_id": segment.shift(-lead).loc[eligible],
                    "history_segment_id": segment.shift(max_history).loc[eligible],
                }
            ).reset_index(drop=True)
            n = len(origins)
            if n == 0:
                raise ValueError(f"insufficient eligible origins for {target}, lead={lead}")
            train_cut_index = math.floor(0.60 * n)
            validation_cut_index = math.floor(0.80 * n)
            if validation_cut_index >= n:
                raise ValueError(f"invalid cut index for {target}, lead={lead}")
            train_cut = origins.loc[train_cut_index, "origin_timestamp"]
            validation_cut = origins.loc[validation_cut_index, "origin_timestamp"]

            train_mask = origins["target_timestamp"].le(train_cut)
            validation_mask = origins["origin_timestamp"].gt(train_cut) & origins[
                "target_timestamp"
            ].le(validation_cut)
            test_mask = origins["origin_timestamp"].gt(validation_cut)
            purge_train_validation_mask = origins["origin_timestamp"].le(train_cut) & origins[
                "target_timestamp"
            ].gt(train_cut)
            purge_validation_test_mask = (
                origins["origin_timestamp"].gt(train_cut)
                & origins["origin_timestamp"].le(validation_cut)
                & origins["target_timestamp"].gt(validation_cut)
            )

            membership = (
                train_mask.astype(int)
                + validation_mask.astype(int)
                + test_mask.astype(int)
                + purge_train_validation_mask.astype(int)
                + purge_validation_test_mask.astype(int)
            )
            if not membership.eq(1).all():
                raise RuntimeError(f"nonexclusive split assignment for {target}, lead={lead}")

            train = origins.loc[train_mask]
            validation = origins.loc[validation_mask]
            test = origins.loc[test_mask]
            if min(len(train), len(validation), len(test)) <= 0:
                raise ValueError(f"empty purged split for {target}, lead={lead}")

            segment_crossings = int(
                (
                    origins["segment_id"].ne(origins["target_segment_id"])
                    | origins["segment_id"].ne(origins["history_segment_id"])
                ).sum()
            )
            train_validation_safe = bool(
                train["target_timestamp"].max()
                <= train_cut
                < validation["origin_timestamp"].min()
            )
            validation_test_safe = bool(
                validation["target_timestamp"].max()
                <= validation_cut
                < test["origin_timestamp"].min()
            )
            if not train_validation_safe or not validation_test_safe or segment_crossings:
                raise RuntimeError(f"purged split validation failed for {target}, lead={lead}")

            rows.append(
                {
                    "target": target,
                    "lead": lead,
                    "eligible_origin_count_before_purge": n,
                    "train_cut_timestamp": train_cut,
                    "validation_cut_timestamp": validation_cut,
                    "train_count": len(train),
                    "purged_train_validation_count": int(purge_train_validation_mask.sum()),
                    "validation_count": len(validation),
                    "purged_validation_test_count": int(purge_validation_test_mask.sum()),
                    "test_count": len(test),
                    "max_train_origin": train["origin_timestamp"].max(),
                    "max_train_target": train["target_timestamp"].max(),
                    "min_validation_origin": validation["origin_timestamp"].min(),
                    "max_validation_target": validation["target_timestamp"].max(),
                    "min_test_origin": test["origin_timestamp"].min(),
                    "leakage_check_train_validation": train_validation_safe,
                    "leakage_check_validation_test": validation_test_safe,
                    "segment_crossing_count": segment_crossings,
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    started = time.perf_counter()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for required in RAW_FILES:
        if not (RAW_DIR / required).is_file():
            raise FileNotFoundError(RAW_DIR / required)

    phase1_hashes = json.loads(
        (AUDIT_OUTPUTS / "raw_hashes_before_after.json").read_text()
    )["after"]
    hashes_before = {name: sha256_file(RAW_DIR / name) for name in RAW_FILES}
    if hashes_before != phase1_hashes:
        raise RuntimeError("Active raw hashes do not match frozen Phase 1A hashes")

    catalogue = pd.read_csv(AUDIT_OUTPUTS / "signal_catalogue.csv").fillna("")
    quality = pd.read_csv(AUDIT_OUTPUTS / "data_quality_screening.csv")
    duplicates = pd.read_csv(AUDIT_OUTPUTS / "exact_duplicate_columns.csv")
    correlations = pd.read_csv(AUDIT_OUTPUTS / "high_correlation_pairs.csv")
    relationships = pd.read_csv(AUDIT_OUTPUTS / "discovered_relationships.csv")

    compute_cols = []
    disk_cols = []
    for machine in MACHINES:
        compute_cols += [
            f"{machine} CU",
            f"{machine} UM",
            f"{machine} DRT",
            f"{machine} DWT",
        ]
        disk_cols.append(f"{machine} UD")
    network_cols = [
        "maxrttWithGoogleDns",
        "minRttwithGoogleDns",
        "averageRttWithGoogleDns",
        "mdevrttWithGoogleDns",
        "jitterWithGoogleDns",
    ]

    compute = read_timestamped_csv("compute_dataset.csv", compute_cols)
    disk = read_timestamped_csv("disk_dataset.csv", disk_cols)
    network = read_timestamped_csv("network_dataset.csv", network_cols)
    throughput = read_timestamped_csv("throughputs_dataset.csv")
    packet = read_timestamped_csv("packet-loss-dataset.csv")
    # Timestamp only; per-core values are deliberately excluded from primary panel.
    core_timestamp = read_timestamped_csv("detailed_cpu_cores_dataset.csv", [])

    frames = [compute, disk, network, throughput, packet, core_timestamp]
    common = pd.DatetimeIndex(frames[0]["timestamp"])
    union = pd.DatetimeIndex(frames[0]["timestamp"])
    for frame in frames[1:]:
        idx = pd.DatetimeIndex(frame["timestamp"])
        common = common.intersection(idx)
        union = union.union(idx)
    common = common.sort_values()
    if not common.is_monotonic_increasing or common.has_duplicates:
        raise RuntimeError("Canonical timestamp intersection invalid")

    compute_a = aligned(compute, common)
    disk_a = aligned(disk, common)
    network_a = aligned(network, common)
    throughput_a = aligned(throughput, common)
    packet_a = aligned(packet, common)

    network_decisions = validate_network_representations(
        throughput_a.reset_index(),
        catalogue,
        duplicates,
        correlations,
        relationships,
    )
    network_decisions.to_csv(OUTPUT_DIR / "network_representation_decisions.csv", index=False)

    panel = pd.DataFrame({"timestamp": common})
    panel["interval_seconds"] = panel["timestamp"].diff().dt.total_seconds()
    median_interval = float(panel["interval_seconds"].iloc[1:].median())
    gap_threshold = 2.0 * median_interval
    panel["segment_id"] = (
        panel["interval_seconds"].gt(gap_threshold).fillna(False).cumsum().astype(int)
    )
    registry: list[dict[str, Any]] = []

    # Direct dense machine resources.
    direct_specs = [
        ("cpu_utilization", "CPU", "CPU utilization", "compute_dataset.csv", "CU", "percent (raw semantics inferred)", "continuous utilization"),
        ("memory_used", "memory", "used memory", "compute_dataset.csv", "UM", "bytes (inferred)", "level"),
        ("disk_used", "disk", "used disk", "disk_dataset.csv", "UD", "bytes (inferred)", "level"),
        ("disk_read", "disk", "disk read activity/rate", "compute_dataset.csv", "DRT", "raw rate unit unknown", "rate/activity"),
        ("disk_write", "disk", "disk write activity/rate", "compute_dataset.csv", "DWT", "raw rate unit unknown", "rate/activity"),
    ]
    for machine, host in MACHINE_TO_HOST.items():
        for suffix, family, metric, dataset, raw_suffix, unit, role in direct_specs:
            raw_col = f"{machine} {raw_suffix}"
            source = compute_a if dataset == "compute_dataset.csv" else disk_a
            canonical = f"{machine}__{suffix}"
            panel[canonical] = source[raw_col].to_numpy()
            row = registry_row(
                canonical,
                family,
                metric,
                machine,
                host,
                "machine",
                dataset,
                raw_col,
                [],
                "identity (exact timestamp selection only)",
                unit,
                "Phase 1A aggregate/complement relationships recorded; no redundant complement included",
                f"Direct machine-level {metric}; compact repeated seven-machine schema.",
                role,
            )
            registry.append(add_quality(row, panel[canonical], quality))

    # Directional bond channels validated against all non-bond components.
    throughput_primary_resolved = True
    for machine, host in MACHINE_TO_HOST.items():
        selected_directions: dict[str, str] = {}
        for direction in ("tx", "rx"):
            decision = network_decisions[
                (network_decisions["machine"] == machine)
                & (network_decisions["direction"] == direction)
            ].iloc[0]
            if decision["decision"] != "selected_aggregate_interface":
                throughput_primary_resolved = False
                continue
            raw_col = decision["selected_raw_column"]
            selected_directions[direction] = raw_col
            canonical = f"{machine}__network_{direction}"
            panel[canonical] = throughput_a[raw_col].to_numpy()
            components = json.loads(decision["component_channels"])
            relation = (
                f"bond0 vs sum({len(components)} components): r="
                f"{decision['aggregate_vs_component_sum_correlation']:.9f}, "
                f"relative MAE={decision['aggregate_vs_component_sum_relative_mae']:.6g}"
            )
            row = registry_row(
                canonical,
                "throughput",
                f"{direction.upper()} network throughput",
                machine,
                host,
                "machine/aggregate-interface",
                "throughputs_dataset.csv",
                raw_col,
                components,
                "identity: selected single aggregate-interface channel; components not summed into panel",
                "raw throughput unit unknown",
                relation,
                "Smallest direction-explicit representation passing predeclared numerical reconstruction gate; not selected from historical usage.",
                "directional component",
            )
            registry.append(add_quality(row, panel[canonical], quality))

        if set(selected_directions) == {"tx", "rx"}:
            canonical = f"{machine}__throughput_total"
            tx_name, rx_name = f"{machine}__network_tx", f"{machine}__network_rx"
            # min_count=2 prevents silently treating a missing direction as zero.
            panel[canonical] = panel[[tx_name, rx_name]].sum(axis=1, min_count=2)
            row = registry_row(
                canonical,
                "throughput",
                "bidirectional machine throughput",
                machine,
                host,
                "machine",
                "throughputs_dataset.csv",
                "",
                [selected_directions["tx"], selected_directions["rx"]],
                f"{tx_name} + {rx_name}; missing if either direction missing",
                "raw throughput unit unknown",
                "TX and RX remain separate registry signals; total does not include interface components again",
                "Primary compact throughput target/context; direction names explicitly support addition without interface double counting.",
                "primary",
            )
            registry.append(add_quality(row, panel[canonical], quality))
        else:
            throughput_primary_resolved = False

    # Global latency/jitter, all raw and not machine-resolved.
    for raw_col, suffix, family, metric in [
        ("maxrttWithGoogleDns", "rtt_max", "latency", "maximum RTT"),
        ("minRttwithGoogleDns", "rtt_min", "latency", "minimum RTT"),
        ("averageRttWithGoogleDns", "rtt_average", "latency", "average RTT"),
        ("mdevrttWithGoogleDns", "rtt_mdev", "latency", "RTT mean deviation"),
        ("jitterWithGoogleDns", "jitter", "jitter", "network jitter"),
    ]:
        canonical = f"global__{suffix}"
        panel[canonical] = network_a[raw_col].to_numpy()
        row = registry_row(
            canonical,
            family,
            metric,
            "",
            "",
            "global",
            "network_dataset.csv",
            raw_col,
            [],
            "identity",
            "milliseconds (inferred)",
            "No machine attribution; global context only.",
            "Nonconstant global latency/jitter signal available on exact intersection.",
            "global context",
        )
        registry.append(add_quality(row, panel[canonical], quality))

    # Optional packet context: only Phase 1A nonconstant raw channels.
    packet_quality = quality[
        (quality["dataset"] == "packet-loss-dataset.csv") & (~quality["constant"])
    ]
    for _, audit_row in packet_quality.iterrows():
        raw_col = audit_row["column"]
        cat = catalogue[
            (catalogue["dataset"] == "packet-loss-dataset.csv")
            & (catalogue["column"] == raw_col)
        ].iloc[0]
        host = str(cat["host"])
        machine = str(cat["machine"])
        interface = str(cat["interface"])
        raw_name = f"{machine}__packet_drop_{interface}_raw"
        event_name = f"{machine}__packet_drop_{interface}_event"
        panel[raw_name] = packet_a[raw_col].to_numpy()
        # Preserve unknown/missing as missing; do not map it to "no event".
        panel[event_name] = panel[raw_name].gt(0).astype("Float64")
        panel.loc[panel[raw_name].isna(), event_name] = pd.NA
        raw_registry = registry_row(
            raw_name,
            "packet events",
            "raw dropped-packet signal",
            machine,
            host,
            f"interface:{interface}",
            "packet-loss-dataset.csv",
            raw_col,
            [],
            "identity",
            "count/rate (raw semantics unclear)",
            "Selected solely because Phase 1A found it nonconstant; still near-constant and sparse.",
            "Raw values preserved for provenance; excluded as dense target.",
            "optional event context/raw",
        )
        registry.append(add_quality(raw_registry, panel[raw_name], quality))
        event_registry = registry_row(
            event_name,
            "packet events",
            "packet drop positive-value event",
            machine,
            host,
            f"interface:{interface}",
            "packet-loss-dataset.csv",
            "",
            [raw_col],
            f"1 if {raw_col} > 0; 0 if observed and <= 0; missing if raw missing",
            "binary indicator",
            "Derived from one explicitly named nonconstant drop channel; no aggregation with constant channels.",
            "Optional event/context only; never a dense regression target in frozen protocol.",
            "optional event context/indicator",
        )
        registry.append(add_quality(event_registry, panel[event_name], quality))

    # Leave-one-machine-out mean and median contexts for repeated primary families.
    # Consolidate blocks first so adding the context set stays efficient and quiet.
    panel = panel.copy()
    context_specs = [
        ("cpu_utilization", "CPU", "CPU utilization"),
        ("memory_used", "memory", "used memory"),
    ]
    if throughput_primary_resolved:
        context_specs.append(("throughput_total", "throughput", "bidirectional throughput"))
    for suffix, family, metric in context_specs:
        all_columns = [f"{m}__{suffix}" for m in MACHINES]
        for target_machine in MACHINES:
            others = [c for c in all_columns if not c.startswith(f"{target_machine}__")]
            for statistic in ("mean", "median"):
                canonical = f"{target_machine}__lomo_{suffix}_{statistic}"
                values = panel[others]
                if statistic == "mean":
                    panel[canonical] = values.mean(axis=1, skipna=False)
                else:
                    panel[canonical] = values.median(axis=1, skipna=False)
                row = registry_row(
                    canonical,
                    f"{family} common context",
                    f"leave-one-machine-out {statistic} {metric}",
                    target_machine,
                    MACHINE_TO_HOST[target_machine],
                    "other-six-machine context",
                    "derived canonical panel",
                    "",
                    others,
                    f"{statistic} of six comparable machine signals, excluding {target_machine}; missing if any component missing",
                    "same as components",
                    "Target machine explicitly excluded; no cluster aggregate used.",
                    "Transparent one-dimensional shared-system comparator for later cross-machine screening.",
                    "leave-one-machine-out context",
                )
                registry.append(add_quality(row, panel[canonical], quality))

    registry_frame = pd.DataFrame(registry)
    if registry_frame["canonical_name"].duplicated().any():
        raise RuntimeError("Duplicate canonical registry names")

    target_columns = []
    for machine in MACHINES:
        target_columns += [
            f"{machine}__cpu_utilization",
            f"{machine}__memory_used",
            f"{machine}__disk_used",
        ]
        if f"{machine}__throughput_total" in panel:
            target_columns.append(f"{machine}__throughput_total")
    split_boundaries = deterministic_split_boundaries(panel, target_columns)

    segment_summary = (
        panel.groupby("segment_id", as_index=False)
        .agg(
            start=("timestamp", "min"),
            end=("timestamp", "max"),
            rows=("timestamp", "size"),
            min_interval_seconds=("interval_seconds", "min"),
            max_interval_seconds=("interval_seconds", "max"),
        )
    )
    segment_summary["duration_seconds"] = (
        segment_summary["end"] - segment_summary["start"]
    ).dt.total_seconds()

    lead_rows = []
    for lead in FUTURE_LEADS:
        seconds = lead * median_interval
        lead_rows.append(
            {
                "lead_samples": lead,
                "median_interval_seconds": median_interval,
                "approx_seconds": seconds,
                "approx_minutes": seconds / 60.0,
            }
        )
    grid = pd.DataFrame(lead_rows)

    # Write outputs only after all construction checks pass.
    panel.to_parquet(OUTPUT_DIR / "canonical_panel.parquet", index=False)
    registry_frame.to_csv(OUTPUT_DIR / "canonical_signal_registry.csv", index=False)
    segment_summary.to_csv(OUTPUT_DIR / "canonical_temporal_segments.csv", index=False)
    split_boundaries.to_csv(OUTPUT_DIR / "split_boundaries_by_target_lead.csv", index=False)
    grid.to_csv(OUTPUT_DIR / "future_lead_wallclock.csv", index=False)

    hashes_after = {name: sha256_file(RAW_DIR / name) for name in RAW_FILES}
    hash_pass = hashes_before == hashes_after == phase1_hashes
    validation = {
        "status": "PASS" if hash_pass else "FAIL",
        "raw_hashes_match_phase1_and_unchanged": hash_pass,
        "rows": len(panel),
        "columns_including_timestamp_interval_segment": len(panel.columns),
        "registered_signals": len(registry_frame),
        "timestamp_min": panel["timestamp"].min(),
        "timestamp_max": panel["timestamp"].max(),
        "timestamps_strictly_increasing": bool(panel["timestamp"].is_monotonic_increasing),
        "duplicate_timestamps": int(panel["timestamp"].duplicated().sum()),
        "all_file_intersection_size": len(common),
        "all_file_union_size": len(union),
        "median_interval_seconds": median_interval,
        "segment_gap_threshold_seconds": gap_threshold,
        "temporal_segments": int(panel["segment_id"].nunique()),
        "network_missing_timestamp_boundaries_preserved": int(
            panel["interval_seconds"].between(gap_threshold, 5 * median_interval).sum()
        ),
        "throughput_primary_resolved_all_machines": throughput_primary_resolved,
        "per_core_columns_in_primary_panel": int(
            sum("cpu-" in c or "free_cpu_" in c or "used_cpu_" in c for c in panel.columns)
        ),
        "split_rows": len(split_boundaries),
        "split_window_crossings": int(split_boundaries["segment_crossing_count"].sum()),
        "split_total_purged_origins": int(
            (
                split_boundaries["purged_train_validation_count"]
                + split_boundaries["purged_validation_test_count"]
            ).sum()
        ),
        "train_validation_leakage_failures": int(
            (~split_boundaries["leakage_check_train_validation"]).sum()
        ),
        "validation_test_leakage_failures": int(
            (~split_boundaries["leakage_check_validation_test"]).sum()
        ),
        "association_lags": ASSOCIATION_LAGS,
        "ridge_history_lags": RIDGE_HISTORY_LAGS,
        "future_leads": FUTURE_LEADS,
        "runtime_seconds": time.perf_counter() - started,
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "pyarrow_engine": "pandas default parquet engine",
        "hashes_before": hashes_before,
        "hashes_after": hashes_after,
    }
    write_json(OUTPUT_DIR / "panel_validation.json", validation)
    if not hash_pass:
        raise RuntimeError("Raw hashes changed")
    if (
        validation["split_window_crossings"] != 0
        or validation["train_validation_leakage_failures"] != 0
        or validation["validation_test_leakage_failures"] != 0
    ):
        raise RuntimeError("Split/window boundary validation failed")
    print(json.dumps(validation, indent=2, default=str))


if __name__ == "__main__":
    main()
