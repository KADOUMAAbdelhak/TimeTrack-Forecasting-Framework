"""Validation for configs/final_fgcs.yaml and pack-based final configs."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_TOP = {
    "experiment_stage",
    "eligible_for_final_claims",
    "evaluation_role",
    "repository_url",
    "branch",
    "freeze_commit",
    "freeze_tag",
    "dataset_fingerprint",
    "dependency_lock_hash",
    "hierarchy_registry",
    "targets",
    "models",
    "reconciliation_methods",
    "folds",
    "horizons",
    "contexts",
    "seeds",
    "hpo",
    "timeouts",
    "statistical_comparisons",
    "bootstrap_policy",
    "efficiency_protocol",
    "conformal_protocol",
    "peak_protocol",
    "downsampling_protocol",
    "artifact_paths",
}

REQUIRED_PACKS_TOP = {
    "experiment_stage",
    "execution_mode",
    "eligible_for_final_claims",
    "evaluation_role",
    "repository_url",
    "branch",
    "freeze_commit",
    "freeze_tag",
    "implementation_commit",
    "dataset_fingerprint",
    "dependency_lock_hash",
    "packs",
    "required_packs_for_aggregation",
    "max_required_hpo_trials",
    "bootstrap_policy",
    "hard_wall_clock_minutes_default",
    "stop_launching_new_runs_minutes_default",
    "artifact_root",
}

FORBIDDEN_PATH_MARKERS = (
    "results/pilot",
    "results/development",
    "pilot/",
    "development/",
)

ALLOWED_MODELS = {"persistence", "ridge", "lightgbm", "lstm", "dlinear"}
PRIMARY_RECON = {"independent", "bottom_up", "wls", "mint"}
REQUIRED_ABLATIONS = {"ols", "top_down"}
_HASH_RE = re.compile(r"^[0-9a-f]{40}$")


def _is_pending(val: Any) -> bool:
    s = str(val or "").strip().upper()
    return s.startswith("PENDING") or s in {"", "NONE", "NULL", "TODO"}


def _is_git_hash(val: Any) -> bool:
    return bool(_HASH_RE.match(str(val or "").strip().lower()))


def resolve_freeze_tag_commit(tag: str, *, repo: Path | None = None) -> str | None:
    """Resolve freeze_tag_commit dynamically from Git (annotated tag → peeled commit)."""
    repo = repo or ROOT
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", f"{tag}^{{}}"],
            cwd=str(repo),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out if _is_git_hash(out) else None
    except Exception:
        try:
            out = subprocess.check_output(
                ["git", "rev-parse", tag],
                cwd=str(repo),
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            return out if _is_git_hash(out) else None
        except Exception:
            return None


def freeze_metadata(cfg: dict[str, Any]) -> dict[str, Any]:
    """Return implementation_commit / freeze_tag / freeze_tag_commit for manifests."""
    tag = str(cfg.get("freeze_tag") or "")
    return {
        "implementation_commit": cfg.get("implementation_commit") or cfg.get("freeze_commit"),
        "freeze_commit": cfg.get("freeze_commit"),
        "freeze_tag": tag,
        "freeze_tag_commit": resolve_freeze_tag_commit(tag),
    }


def validate_packs_config(cfg: dict[str, Any], *, require_frozen: bool = False) -> list[str]:
    errs: list[str] = []
    for k in REQUIRED_PACKS_TOP:
        if k not in cfg:
            errs.append(f"missing key: {k}")

    if cfg.get("experiment_stage") != "final":
        errs.append("experiment_stage must be 'final'")
    if cfg.get("execution_mode") != "manual_packs":
        errs.append("execution_mode must be manual_packs")
    if cfg.get("eligible_for_final_claims") is not True:
        errs.append("eligible_for_final_claims must be true")
    if cfg.get("evaluation_role") != "outer_evaluation":
        errs.append("evaluation_role must be outer_evaluation")
    if cfg.get("default_execution") is False:
        errs.append("pack config should be default_execution: true")

    freeze_commit = cfg.get("freeze_commit")
    freeze_tag = cfg.get("freeze_tag")
    impl = cfg.get("implementation_commit")
    if freeze_commit is None or str(freeze_commit).strip() == "":
        errs.append("missing freeze_commit")
    if freeze_tag is None or str(freeze_tag).strip() == "":
        errs.append("missing freeze_tag")
    if impl is None or str(impl).strip() == "":
        errs.append("missing implementation_commit")

    if require_frozen:
        if _is_pending(freeze_commit) or not _is_git_hash(freeze_commit):
            errs.append("freeze_commit must be a full 40-char git hash after freeze")
        if _is_pending(impl) or not _is_git_hash(impl):
            errs.append("implementation_commit must be a full 40-char git hash after freeze")
        if str(freeze_tag) not in {"experiment-freeze-v1", "experiment-freeze-v2"} and not str(freeze_tag).startswith("experiment-freeze-"):
            errs.append("freeze_tag must be an experiment-freeze-* tag after freeze")
        if _is_pending(freeze_tag):
            errs.append("freeze_tag is PENDING; freeze procedure not complete")
        # Prefer exact active tag from config when set to v2
        if str(freeze_tag) == "experiment-freeze-v1":
            # still valid historically; v2 supersedes for new runs
            pass
        tag_commit = resolve_freeze_tag_commit(str(freeze_tag))
        if not tag_commit:
            errs.append(f"freeze_tag {freeze_tag!r} does not resolve in git")

    if int(cfg.get("max_required_hpo_trials", 999)) > 16:
        errs.append("max_required_hpo_trials must be <= 16")

    hard_default = float(cfg.get("hard_wall_clock_minutes_default", 999))
    if hard_default > 45:
        errs.append("hard_wall_clock_minutes_default must be <= 45")

    packs = cfg.get("packs") or []
    if not packs:
        errs.append("packs list empty")
    ids = set()
    for p in packs:
        pid = p.get("id")
        if not pid:
            errs.append("pack missing id")
            continue
        ids.add(pid)
        if float(p.get("estimated_runtime_minutes", 999)) > 45 and p.get("required"):
            errs.append(f"required pack {pid} projects above 45 minutes")
        if float(p.get("hard_wall_clock_minutes", 999)) > 45:
            errs.append(f"pack {pid} hard_wall_clock_minutes must be <= 45")
        if "stop_launching_new_runs_minutes" not in p:
            errs.append(f"pack {pid} missing stop_launching_new_runs_minutes")

    required_agg = set(cfg.get("required_packs_for_aggregation") or [])
    for pid in required_agg:
        if pid not in ids:
            errs.append(f"required aggregation pack unknown: {pid}")

    # Artifact root must be under results/final/packs
    root = str(cfg.get("artifact_root") or "")
    if root and not root.startswith("results/final"):
        errs.append("artifact_root must be under results/final")
    for marker in FORBIDDEN_PATH_MARKERS:
        if marker in root:
            errs.append(f"artifact_root must not reference {marker}")

    boot = cfg.get("bootstrap_policy") or {}
    if not boot:
        errs.append("absent block-bootstrap policy")
    else:
        for k in ("n_boot", "acf_threshold", "lower", "upper", "seed"):
            if k not in boot:
                errs.append(f"bootstrap_policy missing {k}")

    return errs


def validate_final_config(cfg: dict[str, Any], *, require_frozen: bool = False) -> list[str]:
    """Validate monolithic optional-extended config OR dispatch pack configs."""
    if cfg.get("execution_mode") == "manual_packs" or (cfg.get("packs") and "hierarchy_registry" not in cfg):
        return validate_packs_config(cfg, require_frozen=require_frozen)

    errs: list[str] = []
    for k in REQUIRED_TOP:
        if k not in cfg:
            errs.append(f"missing key: {k}")

    if cfg.get("experiment_stage") != "final":
        errs.append("experiment_stage must be 'final'")
    if cfg.get("eligible_for_final_claims") is not True:
        errs.append("eligible_for_final_claims must be true")
    if cfg.get("evaluation_role") != "outer_evaluation":
        errs.append("evaluation_role must be outer_evaluation")

    freeze_commit = cfg.get("freeze_commit")
    freeze_tag = cfg.get("freeze_tag")
    if freeze_commit is None or str(freeze_commit).strip() == "":
        errs.append("missing freeze_commit")
    if freeze_tag is None or str(freeze_tag).strip() == "":
        errs.append("missing freeze_tag")
    if require_frozen:
        if _is_pending(freeze_commit):
            errs.append("freeze_commit is PENDING; freeze procedure not complete")
        if _is_pending(freeze_tag):
            errs.append("freeze_tag is PENDING; freeze procedure not complete")
        if freeze_commit and len(str(freeze_commit)) < 12 and not _is_pending(freeze_commit):
            errs.append("freeze_commit looks too short for a full git hash")

    paths = cfg.get("artifact_paths") or {}
    hpo = cfg.get("hpo") or {}
    for label, obj in (("artifact_paths", paths), ("hpo", hpo)):
        text = str(obj)
        for marker in FORBIDDEN_PATH_MARKERS:
            if marker in text:
                errs.append(f"{label} must not reference {marker}")

    if cfg.get("mixed_stages"):
        errs.append("mixed_stages not allowed")

    if hpo.get("use_outer_labels") is True:
        errs.append("outer-label HPO forbidden")
    if hpo.get("objective_scope") != "inner_fold_only":
        errs.append("hpo.objective_scope must be inner_fold_only")

    reg = cfg.get("hierarchy_registry") or {}
    for required in ("memory_um", "cpu_core_weighted", "disk_ud"):
        if required not in reg:
            errs.append(f"unknown/missing target hierarchy: {required}")
    cpu = reg.get("cpu_core_weighted") or {}
    if cpu.get("use_raw_conflicting_core_labels") is True:
        errs.append("use of raw conflicting CPU counts is forbidden")

    models = set(cfg.get("models") or [])
    unknown = models - ALLOWED_MODELS
    if unknown:
        errs.append(f"unexpected final models (keep minimal set): {sorted(unknown)}")
    for m in ("persistence", "ridge", "lightgbm", "lstm", "dlinear"):
        if m not in models:
            errs.append(f"required base model missing: {m}")

    seeds = cfg.get("seeds") or {}
    for m in ("lightgbm", "lstm", "dlinear"):
        s = seeds.get(m) or []
        if set(s) != {0, 1, 2} and sorted(s) != [0, 1, 2]:
            if not (isinstance(s, list) and len(s) >= 3):
                errs.append(f"absent required seeds for {m}: need [0,1,2]")

    timeouts = cfg.get("timeouts") or {}
    mk = (cfg.get("model_kwargs") or {}).get("dlinear") or {}
    if mk.get("num_threads", 1) != 1 and mk.get("threads", 1) != 1:
        errs.append("unbounded DLinear settings: threads must be 1")
    if not timeouts.get("dlinear_per_run_sec"):
        errs.append("unbounded DLinear settings: missing dlinear_per_run_sec timeout")
    if int(mk.get("epochs", 999)) > 80:
        errs.append("unbounded DLinear settings: epochs too high")

    methods = set(cfg.get("reconciliation_methods") or [])
    missing_p = PRIMARY_RECON - methods
    if missing_p:
        errs.append(f"missing primary reconciliation methods: {sorted(missing_p)}")
    missing_a = REQUIRED_ABLATIONS - methods
    if missing_a:
        errs.append(f"missing required ablations: {sorted(missing_a)}")

    boot = cfg.get("bootstrap_policy") or {}
    if not boot:
        errs.append("absent block-bootstrap policy")
    else:
        for k in ("n_boot", "acf_threshold", "lower", "upper", "seed"):
            if k not in boot:
                errs.append(f"bootstrap_policy missing {k}")

    horizons = cfg.get("horizons") or []
    if list(horizons) != [1, 4, 8, 16]:
        errs.append("horizons must be [1, 4, 8, 16]")

    folds = cfg.get("folds") or {}
    if int(folds.get("n_outer", 0)) != 3:
        errs.append("folds.n_outer must be 3")

    return errs
