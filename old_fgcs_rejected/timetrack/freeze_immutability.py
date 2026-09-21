"""Freeze-tag immutability helpers.

Tags are immutable. Corrections require a new versioned freeze tag.
Never use ``git tag -f``, ``git push --force``, or ``git push --force-with-lease``
for any freeze tag.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

PROTECTED_ANALYSIS_TAGS = (
    "final-robustness-analysis-freeze-v1",
    "final-robustness-analysis-freeze-v2",
)


def _git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(["git", *args], cwd=str(cwd or ROOT), text=True).strip()


def tag_exists_local(tag: str) -> bool:
    out = _git("tag", "-l", tag)
    return bool(out.strip())


def tag_exists_remote(tag: str, remote: str = "origin") -> bool:
    try:
        out = subprocess.check_output(
            ["git", "ls-remote", "--tags", remote, tag, f"{tag}^{{}}"],
            cwd=str(ROOT),
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        return False
    return bool(out)


def peeled_commit(tag: str) -> str:
    return _git("rev-parse", f"{tag}^{{commit}}")


def tag_object(tag: str) -> str:
    return _git("rev-parse", tag)


def current_head() -> str:
    return _git("rev-parse", "HEAD")


def create_annotated_tag_immutable(tag: str, message: str) -> str:
    """Create an annotated tag. Fails if the tag already exists locally or remotely."""
    if tag_exists_local(tag):
        raise SystemExit(
            f"Refuse to create {tag}: tag already exists locally. "
            "Tags are immutable; corrections require a new versioned freeze tag."
        )
    if tag_exists_remote(tag):
        raise SystemExit(
            f"Refuse to create {tag}: tag already exists on origin. "
            "Tags are immutable; never force-update a freeze tag."
        )
    subprocess.check_call(
        ["git", "tag", "-a", tag, "-m", message],
        cwd=str(ROOT),
    )
    return peeled_commit(tag)


def verify_execution_matches_freeze(
    freeze_tag: str,
    *,
    expected_peel: str | None = None,
    require_head_equals_peel: bool = True,
) -> list[str]:
    """Return validation errors for freeze immutability at execution time."""
    errs: list[str] = []
    if not tag_exists_local(freeze_tag):
        errs.append(f"freeze tag missing locally: {freeze_tag}")
        return errs
    peel = peeled_commit(freeze_tag)
    head = current_head()
    if expected_peel and peel != expected_peel:
        errs.append(f"local peel {peel} != expected {expected_peel}")
    if require_head_equals_peel and head != peel:
        errs.append(f"execution HEAD {head} != freeze peel {peel}")
    return errs


def assert_config_freeze_runtime(cfg: dict[str, Any], *, smoke: bool = False) -> None:
    """Hard-fail when frozen analysis is executed off the immutable peel."""
    if smoke:
        return
    tag = str(cfg.get("freeze_tag") or "")
    if not tag:
        raise SystemExit("freeze_tag missing from robustness statistics config")
    raw_expected = cfg.get("freeze_tag_commit") or cfg.get("expected_freeze_tag_commit")
    expected = None
    if raw_expected and str(raw_expected).upper() != "PENDING":
        expected = str(raw_expected)
    errs = verify_execution_matches_freeze(
        tag,
        expected_peel=expected,
        require_head_equals_peel=True,
    )
    if errs:
        raise SystemExit(f"freeze immutability check failed: {errs}")
