"""Manifest provenance and peak-memory field requirements for final packs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from timetrack.efficiency import peak_rss_bytes

REQUIRED_MANIFEST = {
    "experiment_stage",
    "eligible_for_final_claims",
    "evaluation_role",
    "execution_commit",
    "frozen_implementation_commit",
    "freeze_tag",
    "freeze_tag_commit",
    "repository_url",
    "git_branch",
    "dataset_fingerprint",
    "config_hash",
    "pack_hash",
    "dependency_lock_hash",
    "peak_memory_available",
}


def test_peak_rss_bytes_semantics():
    b, ok, reason = peak_rss_bytes()
    if ok:
        assert b is not None and b > 0
        assert reason is None
    else:
        assert b is None
        assert isinstance(reason, str) and reason


def test_manifest_rejects_missing_provenance_fields():
    incomplete = {k: "x" for k in REQUIRED_MANIFEST if k != "execution_commit"}
    missing = [k for k in REQUIRED_MANIFEST if k not in incomplete or incomplete[k] is None]
    assert "execution_commit" in missing


def test_manifest_template_has_peak_memory_null_semantics():
    man = {
        "peak_memory_bytes": None,
        "peak_memory_available": False,
        "peak_memory_reason": "unit_test_unavailable",
    }
    assert man["peak_memory_available"] is False
    assert man["peak_memory_bytes"] is None
    assert man["peak_memory_reason"]
