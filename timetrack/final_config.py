"""Validation for configs/final_fgcs.yaml."""

from __future__ import annotations

from typing import Any

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

FORBIDDEN_PATH_MARKERS = (
    "results/pilot",
    "results/development",
    "pilot/",
    "development/",
)

ALLOWED_MODELS = {"persistence", "ridge", "lightgbm", "lstm", "dlinear"}
PRIMARY_RECON = {"independent", "bottom_up", "wls", "mint"}
REQUIRED_ABLATIONS = {"ols", "top_down"}


def _is_pending(val: Any) -> bool:
    s = str(val or "").strip().upper()
    return s.startswith("PENDING") or s in {"", "NONE", "NULL", "TODO"}


def validate_final_config(cfg: dict[str, Any], *, require_frozen: bool = False) -> list[str]:
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

    # Reject pilot/development artifact paths
    blob = str(cfg)
    for marker in FORBIDDEN_PATH_MARKERS:
        if marker in blob and "artifact_paths" in cfg:
            # allow mentions only outside artifact paths? Strict: scan artifact_paths + hpo storage
            pass
    paths = cfg.get("artifact_paths") or {}
    hpo = cfg.get("hpo") or {}
    for label, obj in (("artifact_paths", paths), ("hpo", hpo)):
        text = str(obj)
        for marker in FORBIDDEN_PATH_MARKERS:
            if marker in text:
                errs.append(f"{label} must not reference {marker}")

    if cfg.get("mixed_stages"):
        errs.append("mixed_stages not allowed")

    # HPO must be inner-only
    if hpo.get("use_outer_labels") is True:
        errs.append("outer-label HPO forbidden")
    if hpo.get("objective_scope") != "inner_fold_only":
        errs.append("hpo.objective_scope must be inner_fold_only")

    # Hierarchies
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

    # DLinear bounds
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
