"""Frozen final hierarchy registry for FGCS C1 evaluation."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

import numpy as np

from models.hybrid.reconciliation import (
    BOND_MEMBER_IFACES,
    Hierarchy,
    HOST_CORE_COUNTS,
    MACHINES,
    RAW_CONFLICTING_CORE_LABELS,
    assert_not_using_raw_conflicting_labels,
    bond0_hierarchy,
    core_weighted_cpu_hierarchy,
    disk_hierarchy,
    machine_core_counts,
    memory_hierarchy,
)

# Approximation threshold for secondary network hierarchies (relative mean abs error)
NETWORK_APPROX_THRESHOLD = 0.02


def summing_matrix_hash(hierarchy: Hierarchy) -> str:
    blob = hierarchy.summing_matrix.astype(np.float64).tobytes()
    return hashlib.sha256(blob).hexdigest()[:16]


def hierarchy_metadata_hash(meta: dict[str, Any]) -> str:
    blob = json.dumps(meta, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def memory_registry_entry() -> dict[str, Any]:
    h = memory_hierarchy()
    meta = {
        "role": "primary_exact",
        "claim_eligible": True,
        "relation": "cluster_UM = sum(machine01_UM ... machine07_UM)",
        "bottom": list(h.bottom_names),
        "top": h.top_name,
        "identity": "exact_sum",
    }
    return {
        "name": h.name,
        "hierarchy": h,
        "meta": meta,
        "summing_matrix_hash": summing_matrix_hash(h),
        "hierarchy_metadata_hash": hierarchy_metadata_hash(meta),
    }


def cpu_weighted_registry_entry() -> dict[str, Any]:
    cores = machine_core_counts()
    assert_not_using_raw_conflicting_labels(cores)
    # Guard: verified cores must not equal swapped raw pair
    if cores["machine05"] == RAW_CONFLICTING_CORE_LABELS["machine05"]:
        raise AssertionError("CPU registry must not use raw conflicting machine05 core label")
    if cores["machine07"] == RAW_CONFLICTING_CORE_LABELS["machine07"]:
        raise AssertionError("CPU registry must not use raw conflicting machine07 core label")
    h = core_weighted_cpu_hierarchy()
    meta = {
        "role": "primary_core_weighted",
        "claim_eligible": True,
        "relation": "cluster_CU_wsum = sum(verified_core_count_k * machine_k_CU)",
        "equivalent_mean": "cluster_CU_weighted_mean = cluster_CU_wsum / sum(verified_core_counts)",
        "verified_cores": cores,
        "host_cores": dict(HOST_CORE_COUNTS),
        "forbidden_raw_labels": dict(RAW_CONFLICTING_CORE_LABELS),
        "bottom": list(h.bottom_names),
        "top": h.top_name,
        "identity": "weighted_sum",
    }
    return {
        "name": h.name,
        "hierarchy": h,
        "meta": meta,
        "summing_matrix_hash": summing_matrix_hash(h),
        "hierarchy_metadata_hash": hierarchy_metadata_hash(meta),
    }


def disk_registry_entry() -> dict[str, Any]:
    h = disk_hierarchy()
    meta = {
        "role": "boundary_failure_case",
        "claim_eligible": False,  # must not support universal accuracy-improvement claim
        "relation": "cluster_UD = sum(machine01_UD ... machine07_UD)",
        "note": "Use for method selectivity; bottom-up may degrade top MAE",
        "bottom": list(h.bottom_names),
        "top": h.top_name,
        "identity": "exact_sum_if_reset_aware_levels_coherent",
        "reset_aware_policy": (
            "If reset-aware target construction breaks summing identity, "
            "reconstruct coherent levels before reconciliation or exclude from hierarchy scoring."
        ),
    }
    return {
        "name": h.name,
        "hierarchy": h,
        "meta": meta,
        "summing_matrix_hash": summing_matrix_hash(h),
        "hierarchy_metadata_hash": hierarchy_metadata_hash(meta),
    }


def network_bond0_candidates() -> list[dict[str, Any]]:
    """Secondary approximate hierarchies; admission requires empirical error ≤ threshold."""
    out = []
    for host, ifaces in BOND_MEMBER_IFACES.items():
        for direction in ("transmitted", "received"):
            try:
                h = bond0_hierarchy(host=host, direction=direction)
            except Exception:
                continue
            meta = {
                "role": "secondary_approximate",
                "claim_eligible": False,
                "never_describe_as_exact": True,
                "host": host,
                "direction": direction,
                "member_interfaces": list(ifaces),
                "excluded_interfaces": [],
                "approx_threshold": NETWORK_APPROX_THRESHOLD,
                "empirical_hierarchy_error": None,  # filled at runtime
                "bottom": list(h.bottom_names),
                "top": h.top_name,
                "identity": "approximate_sum",
            }
            out.append(
                {
                    "name": h.name,
                    "hierarchy": h,
                    "meta": meta,
                    "summing_matrix_hash": summing_matrix_hash(h),
                    "hierarchy_metadata_hash": hierarchy_metadata_hash(meta),
                }
            )
    return out


def final_hierarchy_registry(
    *,
    include_network: bool = True,
    network_filter: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, dict[str, Any]]:
    """Primary + boundary registries; network only if filter admits."""
    reg = {
        "memory_um": memory_registry_entry(),
        "cpu_core_weighted": cpu_weighted_registry_entry(),
        "disk_ud": disk_registry_entry(),
    }
    if include_network:
        for e in network_bond0_candidates():
            if network_filter is None or network_filter(e):
                reg[e["name"]] = e
    return reg


KNOWN_FINAL_HIERARCHIES = (
    "memory_um",
    "cpu_core_weighted",
    "disk_ud",
)
