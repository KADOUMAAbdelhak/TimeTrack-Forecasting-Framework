#!/usr/bin/env python3
"""Isolated Stage 18B1 control. No frozen driver main/writer is called."""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import importlib
import copy
import json
import math
import numbers
import multiprocessing as mp
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
CONFIG = HERE / "control_config.json"
LABEL = "POST-HOC SENSITIVITY CONTROL"
RESULT_LABEL = "POST-HOC SENSITIVITY RESULT"
FROZEN = {
    "TimeTrack": "multiresource/04_lstm_factorial/outputs/scientific",
    "fastStorage": "independent_validation/05_bitbrains_factorial/outputs/scientific_v2/fastStorage",
    "Rnd": "independent_validation/05_bitbrains_factorial/outputs/scientific_v2/Rnd",
    **{f"Materna-T{i}": f"independent_validation/06_materna_replication/outputs/scientific_v1/Materna-T{i}" for i in (1,2,3)},
}
PROTECTED = ("multiresource/04_lstm_factorial", "independent_validation/05_bitbrains_factorial", "independent_validation/06_materna_replication", "manuscript/jss")
_ENGINE = None
_RECOVERING = False


class Conflict(RuntimeError):
    def __init__(self, code, detail):
        self.code = code
        super().__init__(f"{code}: {detail}")


def require(condition, detail, code="PROVENANCE_CONFLICT"):
    if not condition:
        raise Conflict(code, detail)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def output(path):
    path = Path(path).resolve()
    require(path.is_relative_to(HERE), f"Write outside review namespace: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write(path, value):
    path = output(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    os.replace(temp, path)


def finite_primary(value, path="primary"):
    """Never apply optional-metric null conversion to scientific inputs/outputs."""
    if isinstance(value, dict):
        for key, part in value.items(): finite_primary(part, f"{path}/{key}")
    elif isinstance(value, (list, tuple)):
        for index, part in enumerate(value): finite_primary(part, f"{path}/{index}")
    elif isinstance(value, numbers.Real):
        require(math.isfinite(float(value)), f"Nonfinite primary field {path}", "PRIMARY_NONFINITE_RESULT_CONFLICT")
    elif value is None:
        raise Conflict("PRIMARY_NONFINITE_RESULT_CONFLICT", f"Missing primary field {path}")


def validate_prediction_primary(prediction):
    import numpy as np
    from pandas.api.types import is_numeric_dtype
    required = ["y_true", "y_pred", "y_pred_scaled", "origin_index", "target_index", "lead", "selected_L", "selected_epoch", "seed", "fold", "support_hash"]
    required += [name for name in prediction if "timestamp" in name]
    require(all(name in prediction for name in required), "Missing prediction identity fields", "PRIMARY_NONFINITE_RESULT_CONFLICT")
    require(not prediction[required].isna().any().any(), "Missing primary prediction/timestamp/identity", "PRIMARY_NONFINITE_RESULT_CONFLICT")
    for name in required + (["y_pred_unclipped"] if "y_pred_unclipped" in prediction else []):
        if is_numeric_dtype(prediction[name]):
            require(bool(np.isfinite(prediction[name].to_numpy()).all()), f"Nonfinite prediction field {name}", "PRIMARY_NONFINITE_RESULT_CONFLICT")


def strict_reuse_metrics(original, prediction):
    """Null only recognised undefined optional metrics, retaining exact raw semantics."""
    validate_prediction_primary(prediction)
    metrics = copy.deepcopy(original["metrics"])
    persistence = {int(row["lead"]): row for row in original.get("persistence_metrics", [])}
    semantics = []
    for index, row in enumerate(metrics):
        for key, value in list(row.items()):
            if isinstance(value, numbers.Real) and not math.isfinite(float(value)):
                lead = int(row["lead"])
                targets = prediction.loc[prediction.lead.eq(lead), "y_true"].to_numpy()
                reason = None
                # Infinity is not an undefined-zero-denominator marker.
                if math.isnan(float(value)) and key == "r2" and len(targets) and bool((targets == targets[0]).all()):
                    reason = "undefined_zero_target_variance"
                if math.isnan(float(value)) and key == "persistence_skill" and lead in persistence:
                    denominator = persistence[lead].get("mae")
                    finite_primary(denominator, "persistence_reference_mae")
                    if denominator == 0: reason = "undefined_zero_persistence_mae"
                require(reason is not None, f"Unrecognised nonfinite metric {key} at lead {lead}", "PRIMARY_NONFINITE_RESULT_CONFLICT")
                row[key] = None
                row[f"{key}_status"] = reason
                semantics.append({"metric_index": index, "lead": lead, "field": key, "original_raw_value": "NaN", "reason": reason})
        finite_primary({k:v for k,v in row.items() if not (k in ("r2", "persistence_skill") and v is None)}, f"metrics/{index}")
        require("mae" in row and row["mae"] is not None, "Primary MAE absent", "PRIMARY_NONFINITE_RESULT_CONFLICT")
    return metrics, semantics


def recovery_authorisation(spec):
    record = read(HERE / "provenance/recovery_stage18b1r.json")
    require(spec["control_run_id"] in record["authorised_run_ids"], "Unapproved interrupted retry", "INTERRUPTED_REFIT_IDENTITY_CONFLICT")
    snapshot = Path(record["snapshot_root"])
    predecessor = read(snapshot / f"attempts/{spec['block']}/{spec['control_run_id']}.json")
    require(predecessor["spec"] == spec, "Interrupted scientific identity differs", "INTERRUPTED_REFIT_IDENTITY_CONFLICT")
    require(sha(HERE / f"attempts/{spec['block']}/{spec['control_run_id']}.json") == sha(snapshot / f"attempts/{spec['block']}/{spec['control_run_id']}.json"), "Original attempt changed", "INTERRUPTED_REFIT_IDENTITY_CONFLICT")
    return {"stage": "18B1R", "authorisation_path": str(HERE / "provenance/recovery_stage18b1r.json"), "authorisation_sha256": sha(HERE / "provenance/recovery_stage18b1r.json"), "predecessor_attempt_path": str(HERE / f"attempts/{spec['block']}/{spec['control_run_id']}.json"), "predecessor_attempt_sha256": sha(snapshot / f"attempts/{spec['block']}/{spec['control_run_id']}.json"), "successor_adapter_sha256": sha(Path(__file__))}


def unresolved_failures():
    unresolved = []
    for directory in (HERE / "failures", HERE / "recovery/failures"):
        for failure in directory.rglob("*.json") if directory.exists() else []:
            evidence = HERE / "recovery/evidence" / failure.parent.name / failure.name
            if not evidence.exists(): unresolved.append(str(failure)); continue
            value = read(evidence)
            require(value.get("original_failure_sha256") == sha(failure), f"Failure-resolution identity mismatch {failure}")
            require(sha(value["completion_path"]) == value["completion_sha256"], "Recovered completion changed")
    return unresolved


def verify_adapter_provenance():
    original = read(HERE / "provenance/experiment.json")
    recovery_path = HERE / "provenance/recovery_stage18b1r_successor.json"
    if not recovery_path.exists():
        for rel, digest in original["source_hashes"].items(): require(sha(ROOT / rel) == digest, f"Source changed {rel}")
        return
    successor = read(recovery_path)
    predecessor = read(HERE / "provenance/recovery_stage18b1r.json")
    require(sha(CONFIG) == predecessor["predecessor_config_sha256"], "Recovery would change config", "RECOVERY_CONFIG_CHANGE_REQUIRED")
    require(sha(HERE / "provenance/experiment.json") == predecessor["original_provenance_sha256"], "Original provenance changed")
    require(successor["tests"]["status"] == "PASS", "Recovery regression tests not passed")
    for rel, digest in successor["source_hashes"].items(): require(sha(ROOT / rel) == digest, f"Successor source changed {rel}")


def parquet(path, frame):
    path = output(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(temp, index=False, compression="zstd")
    os.replace(temp, path)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def refs():
    return {key: git("rev-parse", ref) for key, ref in {
        "HEAD": "HEAD", "paper/jss": "paper/jss", "main": "main",
        "scientific_tag_object": "refs/tags/phase4d-materna-final-scientific-freeze-v1",
        "scientific_tag_target": "phase4d-materna-final-scientific-freeze-v1^{}",
    }.items()}


def verify_refs():
    cfg = read(CONFIG)
    require(git("branch", "--show-current") == cfg["branch"], "Branch mismatch")
    require(git("rev-parse", "HEAD") == cfg["parent_manuscript_checkpoint"], "HEAD mismatch")
    require(git("rev-parse", "HEAD^") == cfg["parent_scientific_checkpoint"], "Scientific parent mismatch")
    require(git("rev-parse", "phase4d-materna-final-scientific-freeze-v1^{}") == cfg["parent_scientific_checkpoint"], "Scientific tag mismatch")
    require(not git("diff", "--name-only"), "Tracked modifications exist")
    require(not git("diff", "--cached", "--name-only"), "Staged modifications exist")


def preservation_capture():
    """Full content SHA-256 inventory, including untracked scientific artifacts."""
    path = output(HERE / "provenance/preservation_before.jsonl")
    require(not path.exists(), "Baseline already exists; refuse overwrite")
    counts = {}
    with path.open("x") as stream:
        for rel in PROTECTED:
            count = 0
            for directory, dirs, files in os.walk(ROOT / rel):
                dirs.sort()
                for name in sorted(files):
                    p = Path(directory) / name
                    s = p.stat()
                    stream.write(json.dumps({"path": p.relative_to(ROOT).as_posix(), "size": s.st_size, "mtime_ns": s.st_mtime_ns, "sha256": sha(p)}, sort_keys=True) + "\n")
                    count += 1
            counts[rel] = count
            print(f"PRESERVATION_BASELINE {rel} files={count}", flush=True)
    write(HERE / "provenance/preservation_baseline.json", {"label": LABEL, "timestamp": now(), "counts": counts, "inventory_sha256": sha(path), "refs": refs()})


def preservation_check(full=True):
    baseline = read(HERE / "provenance/preservation_baseline.json")
    path = HERE / "provenance/preservation_before.jsonl"
    require(sha(path) == baseline["inventory_sha256"], "Preservation inventory changed")
    seen = set()
    with path.open() as stream:
        for line in stream:
            row = json.loads(line); p = ROOT / row["path"]; seen.add(row["path"])
            require(p.is_file(), f"Frozen file removed: {p}")
            s = p.stat()
            require(s.st_size == row["size"] and s.st_mtime_ns == row["mtime_ns"], f"Frozen metadata changed: {p}")
            if full:
                require(sha(p) == row["sha256"], f"Frozen content changed: {p}")
    current = {p.relative_to(ROOT).as_posix() for rel in PROTECTED for p in (ROOT / rel).rglob("*") if p.is_file()}
    require(current == seen, "Protected tree membership changed")
    require(refs() == baseline["refs"], "Git checkpoint/tag/branch changed")
    verify_refs()
    result = {"status": "PASS", "full_content_hashes_checked": full, "files_checked": len(seen), "timestamp": now(), "refs_unchanged": True}
    write(HERE / "provenance" / ("preservation_after.json" if full else "preservation_pretrain.json"), result)
    return result


class Engine:
    def __init__(self, block):
        import numpy as np
        import pandas as pd
        import torch
        self.np, self.pd, self.torch = np, pd, torch
        self.block = block; self.tt = block == "TimeTrack"
        self.root = ROOT / FROZEN[block]
        self.base = self.root.parents[1] if self.tt else self.root.parents[2]
        module_root = ROOT / ("multiresource/04_lstm_factorial" if self.tt else "independent_validation/05_bitbrains_factorial")
        sys.path.insert(0, str(module_root))
        if self.tt:
            self.core = importlib.import_module("run_factorial_scientific")
            self.config_path = self.core.CONFIG
            self.support_path = self.root / "support_manifest.parquet"
            self.cohort_paths = [module_root / "configs/lstm_factorial.json"]
        else:
            self.core = importlib.import_module("run_phase4c_scientific")
            if block.startswith("Materna"):
                materna_root = ROOT / "independent_validation/06_materna_replication"
                sys.path.insert(0, str(materna_root))
                self.materna = importlib.import_module("run_phase4d_scientific")
                self.config_path = self.materna.CONFIG_PATH
                self.support_path = self.materna.SUPPORT_PATH
                self.cohort_paths = [self.materna.COHORT_PATH, materna_root / "manifests/CANDIDATE_35_VM_COHORT_SUMMARY.json"]
            else:
                self.config_path = self.core.CONFIG_PATH
                self.support_path = self.core.SUPPORT
                self.cohort_paths = [self.core.COHORT_PATH, self.core.ELIGIBILITY]
        self.resources = tuple(self.core.RESOURCE_ORDER)
        self.leads = tuple(self.core.FUTURE_LEADS if self.tt else self.core.LEADS)
        self.contexts = pd.read_csv(self.root / "selected_contexts.csv", dtype={"vm_id": str})
        self.registry = pd.read_csv(self.root / "run_registry.csv", dtype={"vm_id": str})
        self.inner_registry = pd.read_csv(self.root / "inner_run_registry.csv", dtype={"vm_id": str})
        self.entity_key = "machine" if self.tt else "vm_id"
        self.support = pd.read_parquet(self.support_path)
        self.cache = {}
        torch.set_num_threads(1)
        try: torch.set_num_interop_threads(1)
        except RuntimeError: pass

    def entities(self):
        if self.tt: return list(self.core.MACHINES)
        if self.block.startswith("Materna"): return list(self.materna.SELECTED_IDS)
        return self.core.selected_ids()[self.core.ENVIRONMENTS[self.block]]

    def data(self, entity, length):
        key = (entity, length if self.tt else None)
        if key not in self.cache:
            if self.tt:
                frame = self.core.panel()
                folds = self.core.build_factorial_folds(frame, entity, length)
            else:
                clean, folds = self.materna.vm_data(self.block, entity) if self.block.startswith("Materna") else self.core.vm_data(self.block, entity)
                frame = clean.frame
                self.clean = clean
            self.cache[key] = frame, folds
        elif not self.tt:
            clean, _ = self.materna.vm_data(self.block, entity) if self.block.startswith("Materna") else self.core.vm_data(self.block, entity)
            self.clean = clean
        return self.cache[key]

    def scaler(self, frame, entity, origins, length):
        return self.core.fit_partition_scaler(frame, entity, origins, length) if self.tt else self.core.fit_partition_scaler(frame, origins, length)

    def scaler_payload(self, scaler):
        return scaler.metadata() if self.tt else self.core.scaler_payload(scaler)

    def scaler_from_record(self, row):
        return row["scaler_metadata" if self.tt else "scaler"]

    def identity(self, entity, fold, length, target, seed, phase, support, epoch=None):
        if self.tt:
            value = self.core.identity("S2", target, entity, fold, length, seed, phase, support)
            if epoch is not None: value["selected_epoch"] = epoch
            return value
        if self.block.startswith("Materna"):
            return self.materna.run_identity(self.block, "S2", target, entity, fold, length, seed, phase, support, selected_epoch=epoch)
        return self.core.run_identity(self.block, "S2", target, entity, fold, length, seed, phase, support, selected_epoch=epoch)

    def support_hash(self, fold, phase):
        names = ("inner_train", "inner_validation") if phase == "inner" else ("outer_train", "outer_test")
        keys = ("train", "validation" if phase == "inner" else "test") if self.tt else names
        return self.core.canonical_hash({key: fold.hashes[name] for key, name in zip(keys, names)})

    def record(self, row, phase):
        p = self.root / f"runtime/completions/{phase}/{row.run_id}.json"
        require(p.is_file(), f"{self.block}/{row.run_id}", "S2_COMMON_CONTEXT_INNER_RECORD_MISSING" if phase == "inner" else "PROVENANCE_CONFLICT")
        value = read(p)
        require(value["status"] == "complete", f"Incomplete frozen record {p}")
        if self.block.startswith("Materna"):
            require(value.get("run_kind") == "scientific", f"Non-scientific record {p}")
            for kind in (["history"] if phase == "inner" else ["metrics"]):
                artifact = self.base / value[f"{kind}_path"]
                require(sha(artifact) == value[f"{kind}_sha256"], f"Frozen {kind} hash mismatch {p}")
        if phase == "inner":
            require(1 <= int(value["best_epoch"]) <= 50, f"Invalid inner epoch {p}")
            require(int(value["best_epoch"]) == int(row.best_epoch), f"Inner registry epoch mismatch {p}")
            require(value.get("outer_test_accessed") in (None, False), f"Inner test access {p}")
        return p, value

    def artifact(self, row, kind):
        return (ROOT if self.tt else self.base) / row[f"{kind}_path"]

    def unique(self, frame, **fields):
        selected = frame
        for key, value in fields.items(): selected = selected[selected[key].eq(value)]
        require(len(selected) == 1, f"{self.block} expected unique {fields}; found {len(selected)}", "S2_COMMON_CONTEXT_INNER_RECORD_MISSING" if "best_epoch" in frame else "PROVENANCE_CONFLICT")
        return selected.iloc[0]

    def windows(self, frame, entity, length, origins):
        if self.tt:
            raw = self.core.build_raw_windows(frame, entity, length, origins)
            return raw.X, raw.y, raw
        X, y, persistence = self.core.build_windows(frame, origins, length)
        return X, y, persistence


def plan_block(block):
    engine = Engine(block); pd = engine.pd; tasks = []
    cfg_hash = sha(engine.config_path)
    expected_cfg = engine.core.FROZEN_CONFIG_HASH if engine.tt else (engine.materna.CONFIG_SHA256 if block.startswith("Materna") else engine.core.CONFIG_HASH)
    require(cfg_hash == expected_cfg, f"{block} frozen configuration hash")
    entity_ids = engine.entities()
    require(len(entity_ids) == (7 if engine.tt else 35), f"{block} cohort size")
    m1 = engine.contexts[engine.contexts.formulation.eq("M1")]
    require(set(m1[engine.entity_key]) == set(entity_ids), f"{block} executed cohort differs")
    require(len(m1) == len(entity_ids) * 5, f"{block} M1 selection count")
    sources = [engine.config_path, engine.support_path, *engine.cohort_paths, engine.root / "selected_contexts.csv", engine.root / "selected_epochs.csv", engine.root / "inner_run_registry.csv", engine.root / "run_registry.csv"]
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in set(sources)}
    for entity in entity_ids:
        for fold_number in range(1,6):
            context = engine.unique(m1, **{engine.entity_key: entity, "fold": fold_number})
            length = int(context.selected_L)
            frame, folds = engine.data(entity, length); fold = folds[fold_number-1]
            manifest = engine.support
            if "environment" in manifest:
                env = block if block.startswith("Materna") else engine.core.ENVIRONMENTS[block]
                manifest = manifest[manifest.environment.eq(env)]
            srow = engine.unique(manifest, **{engine.entity_key: entity, "fold": fold_number, "context_length" if engine.tt else "L": length})
            for name, hash_value in fold.hashes.items():
                require(srow[f"{name}_hash"] == hash_value, f"{block}/{entity}/{fold_number}/{name} support manifest", "SCIENTIFIC_SUPPORT_CONFLICT")
            outer_scaler = engine.scaler(frame, entity, fold.outer_train, length)
            inner_scaler = engine.scaler(frame, entity, fold.inner_train, length)
            outer_payload = engine.scaler_payload(outer_scaler); inner_payload = engine.scaler_payload(inner_scaler)
            m1_final = engine.unique(engine.registry, **{engine.entity_key: entity, "fold": fold_number, "formulation": "M1", "seed": 0})
            m1_path, m1_record = engine.record(m1_final, "final")
            require(int(m1_record["identity"]["L"]) == length, f"{block}/{entity}/{fold_number} M1 context artifact disagreement")
            require(engine.scaler_from_record(m1_record) == outer_payload, f"{block}/{entity}/{fold_number} forced-L scaler reconstruction", "SCIENTIFIC_SUPPORT_CONFLICT")
            for name in ("outer_train", "outer_test"):
                require(m1_record[f"{name}_hash"] == fold.hashes[name], f"{block}/{entity}/{fold_number} M1 support", "SCIENTIFIC_SUPPORT_CONFLICT")
            for target in engine.resources:
                s2_context = engine.unique(engine.contexts, **{engine.entity_key: entity, "fold": fold_number, "formulation": "S2", "resource": target})
                for seed in (0,1,2):
                    inner_row = engine.unique(engine.inner_registry, **{engine.entity_key: entity, "fold": fold_number, "formulation": "S2", "resource": target, "seed": seed, "L": length})
                    inner_path, inner_record = engine.record(inner_row, "inner")
                    inner_identity = engine.identity(entity, fold_number, length, target, seed, "inner", engine.support_hash(fold, "inner"))
                    require(inner_record["identity"] == inner_identity, f"Exact inner identity differs {inner_path}")
                    require(engine.scaler_from_record(inner_record) == inner_payload, f"Inner scaler differs {inner_path}", "SCIENTIFIC_SUPPORT_CONFLICT")
                    epoch = int(inner_record["best_epoch"])
                    final_identity = engine.identity(entity, fold_number, length, target, seed, "final", engine.support_hash(fold, "final"), epoch)
                    original_row = engine.unique(engine.registry, **{engine.entity_key: entity, "fold": fold_number, "formulation": "S2", "resource": target, "seed": seed})
                    original_path, original = engine.record(original_row, "final")
                    reuse = original["identity"] == final_identity
                    require(reuse == (int(s2_context.selected_L) == length), f"Context-matched original has nonmatching epoch/identity {original_path}")
                    if reuse:
                        require(engine.scaler_from_record(original) == outer_payload, f"Reused scaler mismatch {original_path}", "SCIENTIFIC_SUPPORT_CONFLICT")
                        for kind in ("model", "prediction"):
                            require(sha(engine.artifact(original, kind)) == original[f"{kind}_sha256"], f"Reused frozen {kind} corrupted {original_path}")
                    spec = {"label": LABEL, "block": block, "entity": entity, "fold": fold_number, "resource": target, "seed": seed, "L": length, "epoch": epoch, "reuse": reuse, "original_selected_L": int(s2_context.selected_L), "frozen_final_identity": final_identity, "split_hashes": fold.hashes, "scaler": outer_payload, "scaler_sha256": canonical(outer_payload), "inner_completion": str(inner_path.relative_to(ROOT)), "inner_completion_sha256": sha(inner_path), "original_completion": str(original_path.relative_to(ROOT)), "original_completion_sha256": sha(original_path), "m1_context_completion": str(m1_path.relative_to(ROOT)), "m1_context_completion_sha256": sha(m1_path), "forced_context_source": str((engine.root / "selected_contexts.csv").relative_to(ROOT)), "forced_context_source_sha256": source_hashes[str((engine.root / "selected_contexts.csv").relative_to(ROOT))]}
                    spec["control_run_id"] = canonical({"namespace": "stage18b1-s2-common-context-v1", "config_sha256": sha(CONFIG), "parent": read(CONFIG)["parent_scientific_checkpoint"], "spec": spec})
                    tasks.append(spec)
        print(f"PLAN {block} entity={entity} required={len(tasks)}", flush=True)
    result = {"label": LABEL, "block": block, "timestamp": now(), "cohort": entity_ids, "source_hashes": source_hashes, "required": len(tasks), "reused": sum(t["reuse"] for t in tasks), "new": sum(not t["reuse"] for t in tasks), "tasks": tasks}
    write(HERE / f"plans/{block}.json", result)
    print(f"PLAN_COMPLETE {block} required={result['required']} reused={result['reused']} new={result['new']}", flush=True)


def check_spec(engine, spec):
    finite_primary(spec, "spec")
    for key in ("inner_completion", "original_completion", "m1_context_completion", "forced_context_source"):
        require(sha(ROOT / spec[key]) == spec[key + "_sha256"], f"Source changed: {spec[key]}")
    frame, folds = engine.data(spec["entity"], spec["L"]); fold = folds[spec["fold"]-1]
    require(fold.hashes == spec["split_hashes"], f"Support changed {spec['control_run_id']}", "SCIENTIFIC_SUPPORT_CONFLICT")
    scaler = engine.scaler(frame, spec["entity"], fold.outer_train, spec["L"])
    require(engine.scaler_payload(scaler) == spec["scaler"], f"Scaler changed {spec['control_run_id']}", "SCIENTIFIC_SUPPORT_CONFLICT")
    return frame, fold, scaler


def init_worker(block, recovering=False):
    global _ENGINE, _RECOVERING
    _RECOVERING = recovering
    _ENGINE = Engine(block)
    # The frozen finite-data computation is unchanged. Fail fast on nonfinite loss/gradient.
    core = _ENGINE.core; torch = _ENGINE.torch
    original_loss = core.resource_losses
    def guarded_loss(*args, **kwargs):
        result = original_loss(*args, **kwargs)
        require(bool(torch.isfinite(result[0])), "Nonfinite training loss", "PRIMARY_NONFINITE_RESULT_CONFLICT")
        return result
    core.resource_losses = guarded_loss
    original_clip = torch.nn.utils.clip_grad_norm_
    def guarded_clip(*args, **kwargs):
        kwargs["error_if_nonfinite"] = True
        try: return original_clip(*args, **kwargs)
        except RuntimeError as exc:
            if "non-finite" in str(exc): raise Conflict("PRIMARY_NONFINITE_RESULT_CONFLICT", str(exc)) from exc
            raise
    torch.nn.utils.clip_grad_norm_ = guarded_clip


def validate_prediction_support(engine, spec, predicted):
    original = read(ROOT / spec["original_completion"])
    old = engine.pd.read_parquet(engine.artifact(original, "prediction"))
    keys = ["origin_index", "lead", "target_index", "support_hash", "y_true"]
    keys += ["sample_id", "origin_timestamp", "target_timestamp"] if engine.tt else ["origin_timestamp_seconds", "target_timestamp_seconds"]
    require(len(old) == len(predicted), f"Test row count {spec['control_run_id']}", "SCIENTIFIC_SUPPORT_CONFLICT")
    for key in keys:
        require(engine.np.array_equal(old[key].to_numpy(), predicted[key].to_numpy()), f"Test support/target column {key}: {spec['control_run_id']}", "SCIENTIFIC_SUPPORT_CONFLICT")


def validate_completion(engine, spec, value):
    require(value["spec"] == spec and value["status"] == "complete", "Existing control completion identity differs")
    require(value["label"] == LABEL, "Control namespace label")
    for kind in ("model", "prediction"):
        p = Path(value[f"{kind}_path"])
        require(sha(p) == value[f"{kind}_sha256"], f"Control {kind} hash mismatch {p}")
    require(value["test_evaluations"] == (0 if spec["reuse"] else 1), "Test evaluation count")
    require(len(value["metrics"]) == len(engine.leads), "Metric count")
    finite_primary(spec, "completion/spec")
    for metric in value["metrics"]: finite_primary(metric["mae"], "completion/mae")


def run_group(specs):
    engine = _ENGINE; np, torch, core = engine.np, engine.torch, engine.core
    train_cache = {}; completed = []
    for spec in specs:
        run_id = spec["control_run_id"]
        completion = HERE / f"completions/{engine.block}/{run_id}.json"
        failure = HERE / f"failures/{engine.block}/{run_id}.json"
        started_path = HERE / f"attempts/{engine.block}/{run_id}.json"
        if completion.exists():
            value = read(completion); validate_completion(engine, spec, value)
            completed.append({"reuse": spec["reuse"], "resumed": True}); continue
        recovery = None
        if _RECOVERING:
            recovery = recovery_authorisation(spec)
            if failure.exists(): recovery["original_failure_sha256"] = sha(failure)
            failure = HERE / f"recovery/failures/{engine.block}/{run_id}.json"
            started_path = HERE / f"recovery/attempts/{engine.block}/{run_id}.json"
        require(not failure.exists() and not started_path.exists(), f"Unresolved prior attempt {run_id}; never silently retrain", "STAGE_18B1R_BLOCKED")
        try:
            frame, fold, scaler = check_spec(engine, spec)
            started = now()
            write(started_path, {"label": LABEL, "spec": spec, "started": started, "pid": os.getpid(), **({"recovery": recovery} if recovery else {})})
            original = read(ROOT / spec["original_completion"])
            if spec["reuse"]:
                require(original["identity"] == spec["frozen_final_identity"], "Reused frozen identity changed")
                require(engine.scaler_from_record(original) == spec["scaler"], "Reused scaler changed", "SCIENTIFIC_SUPPORT_CONFLICT")
                for kind in ("model", "prediction"):
                    require(sha(engine.artifact(original, kind)) == original[f"{kind}_sha256"], f"Reused {kind} changed")
                prediction = engine.pd.read_parquet(engine.artifact(original, "prediction"))
                validate_prediction_primary(prediction)
                state = torch.load(engine.artifact(original, "model"), map_location="cpu", weights_only=True)
                require(all(bool(torch.isfinite(v).all()) for v in state.values()), "Nonfinite reused weights", "PRIMARY_NONFINITE_RESULT_CONFLICT")
                require(sum(v.numel() for v in state.values()) == (51720 if engine.tt else 51525), "Reused parameter count")
                metrics, semantics = strict_reuse_metrics(original, prediction)
                value = {"status": "complete", "label": LABEL, "spec": spec, "started": started, "completed": now(), "mode": "EXACT_FROZEN_REUSE", "equality_check": {"identity": True, "selected_epoch": True, "scaler": True, "support": True, "configuration": True, "seed": True}, "test_evaluations": 0, "metrics": metrics, "train_seconds": 0.0, "original_completion_sha256": sha(ROOT / spec["original_completion"]), "original_completion_path": str(ROOT / spec["original_completion"]), "reuse": True, "no_training": True, "no_new_test_evaluation": True, "original_raw_ancillary_semantics": semantics}
                for kind in ("model", "prediction"):
                    value[f"{kind}_path"] = str(engine.artifact(original, kind))
                    value[f"{kind}_sha256"] = original[f"{kind}_sha256"]
            else:
                key = (spec["entity"], spec["fold"], spec["L"])
                if key not in train_cache:
                    X, y, _ = engine.windows(frame, spec["entity"], spec["L"], fold.outer_train)
                    train_cache[key] = core.scale_windows(X, y, scaler)
                X, y = train_cache[key]
                train_x, train_y = core.scaled_views(X, y, "S2", spec["resource"])
                model, loss_logs, seconds, rss = core.fit_final_model("S2", spec["resource"], spec["seed"], train_x, train_y, spec["epoch"])
                require(len(loss_logs) == spec["epoch"], "Refit epoch count")
                require(np.isfinite([r["joint_loss"] for r in loss_logs]).all(), "Nonfinite loss history", "PRIMARY_NONFINITE_RESULT_CONFLICT")
                require(all(bool(torch.isfinite(v).all()) for v in model.state_dict().values()), "Nonfinite trained weights", "PRIMARY_NONFINITE_RESULT_CONFLICT")
                require(core.parameter_count(model) == (51720 if engine.tt else 51525), "New parameter count")
                model_path = output(HERE / f"models/{engine.block}/{run_id}.pt")
                torch.save(model.state_dict(), model_path)
                # Exactly one outer-test forward pass, after the fixed-epoch refit.
                X_test_native, y_test_native, raw = engine.windows(frame, spec["entity"], spec["L"], fold.outer_test)
                X_test, y_test = core.scale_windows(X_test_native, y_test_native, scaler)
                test_x, _ = core.scaled_views(X_test, y_test, "S2", spec["resource"])
                tick = time.perf_counter()
                with torch.no_grad(): prediction_scaled = model(torch.from_numpy(test_x.astype(np.float32))).numpy()
                pred_seconds = time.perf_counter() - tick
                index = engine.resources.index(spec["resource"])
                inverse = core.inverse_one(prediction_scaled, scaler, spec["resource"], project=True) if engine.tt else scaler.inverse_one(prediction_scaled, spec["resource"], project=True)
                native, negative, unclipped = inverse
                require(np.isfinite(y_test_native).all() and np.isfinite(prediction_scaled).all() and np.isfinite(native).all() and np.isfinite(unclipped).all(), "Nonfinite test target/prediction", "PRIMARY_NONFINITE_RESULT_CONFLICT")
                artifact_identity = dict(spec["frozen_final_identity"])
                artifact_identity.update(run_id=run_id, formulation="S2-COMMON-CONTEXT", selected_epoch=spec["epoch"], support_hash=engine.support_hash(fold, "final"))
                if engine.tt:
                    predicted = core.prediction_frame(artifact_identity, spec["resource"], raw, prediction_scaled, native, unclipped)
                else:
                    predicted = core.prediction_frame(artifact_identity, spec["resource"], engine.clean, fold.outer_test, spec["epoch"], y_test_native[:,index,:], prediction_scaled, native, unclipped)
                predicted["control_label"] = LABEL
                validate_prediction_primary(predicted)
                validate_prediction_support(engine, spec, predicted)
                pred_path = HERE / f"predictions/{engine.block}/{run_id}.parquet"
                parquet(pred_path, predicted)
                truth = y_test_native[:,index,:]
                mae = np.mean(np.abs(truth - native), axis=0)
                require(np.isfinite(mae).all(), "Nonfinite MAE", "PRIMARY_NONFINITE_RESULT_CONFLICT")
                metrics = [{"block": engine.block, "formulation": "S2-COMMON-CONTEXT", "entity": spec["entity"], "fold": spec["fold"], "resource": spec["resource"], "seed": spec["seed"], "lead": int(lead), "mae": float(mae[i]), "n": len(truth), "selected_L": spec["L"], "selected_epoch": spec["epoch"], "run_id": run_id, "outer_test_hash": fold.hashes["outer_test"]} for i,lead in enumerate(engine.leads)]
                value = {"status": "complete", "label": LABEL, "spec": spec, "started": started, "completed": now(), "mode": "NEW_FIXED_EPOCH_REFIT", "test_evaluations": 1, "model_path": str(model_path), "model_sha256": sha(model_path), "prediction_path": str(pred_path), "prediction_sha256": sha(pred_path), "support_hash": engine.support_hash(fold, "final"), "scaler_sha256": spec["scaler_sha256"], "train_seconds": seconds, "prediction_seconds": pred_seconds, "peak_rss_bytes": rss, "parameter_count": core.parameter_count(model), "loss_logs": loss_logs, "metrics": metrics}
            if recovery: value["recovery"] = recovery
            write(completion, value)
            if recovery:
                write(HERE / f"recovery/evidence/{engine.block}/{run_id}.json", {"status": "RECOVERED", "timestamp": now(), "spec": spec, **recovery, "completion_path": str(completion), "completion_sha256": sha(completion), "mode": value["mode"], "test_evaluations": value["test_evaluations"], "no_training": bool(spec["reuse"]), "scientific_identity_unchanged": True})
            completed.append({"reuse": spec["reuse"], "resumed": False})
            print(f"FIT_COMPLETE {engine.block} {spec['entity']} fold={spec['fold']} {spec['resource']} seed={spec['seed']} mode={value['mode']}", flush=True)
        except BaseException as exc:
            write(failure, {"status": "FAILED_STOP", "label": LABEL, "timestamp": now(), "spec": spec, "error": repr(exc), "traceback": traceback.format_exc()})
            raise
    return completed


def execute_block(block, workers):
    plan = read(HERE / f"plans/{block}.json")
    for rel, digest in plan["source_hashes"].items():
        require(sha(ROOT / rel) == digest, f"Plan source changed {rel}")
    groups = {}
    for spec in plan["tasks"]: groups.setdefault((spec["entity"], spec["fold"]), []).append(spec)
    done = 0
    with mp.get_context("spawn").Pool(workers, initializer=init_worker, initargs=(block,)) as pool:
        for values in pool.imap_unordered(run_group, groups.values(), chunksize=1):
            done += len(values)
            write(HERE / f"progress/{block}.json", {"label": LABEL, "completed": done, "required": plan["required"], "timestamp": now()})
            print(f"PROGRESS {block} completed={done}/{plan['required']}", flush=True)
    require(done == plan["required"], f"Incomplete block {block}")
    write(HERE / f"validation/{block}.json", {"status": "PASS", "required": done, "planned_reuse": plan["reused"], "planned_new": plan["new"], "timestamp": now()})


def recover_units():
    verify_refs(); verify_adapter_provenance()
    authorisation = read(HERE / "provenance/recovery_stage18b1r.json")
    plan = read(HERE / "plans/Rnd.json")
    lookup = {s["control_run_id"]:s for s in plan["tasks"]}
    init_worker("Rnd", recovering=True)
    results = []
    for run_id in authorisation["authorised_run_ids"]:
        spec = lookup[run_id]
        run_group([spec])
        evidence = read(HERE / f"recovery/evidence/Rnd/{run_id}.json")
        require(evidence["scientific_identity_unchanged"], "Recovered identity differs", "INTERRUPTED_REFIT_IDENTITY_CONFLICT")
        results.append(evidence)
    require(not unresolved_failures(), "Unresolved failure after four-unit recovery")
    write(HERE / "recovery/four_units_recovered.json", {"status": "PASS", "timestamp": now(), "units": results, "determinism": {"same_seed": True, "same_frozen_set_seed_function": True, "torch_deterministic_algorithms": True, "warn_only": True, "cpu_threads": 1, "bitwise_across_environments_guaranteed": False, "note": "Frozen warn-only deterministic policy retained; no completed interrupted output exists for bitwise comparison"}})


def audit_block(block):
    """Read-only numerical/provenance audit; no model inference or fitting."""
    engine = Engine(block); plan = read(HERE / f"plans/{block}.json")
    specs = {s["control_run_id"]:s for s in plan["tasks"]}
    files = list((HERE / f"completions/{block}").glob("*.json"))
    require(len(files) == len(specs) and {p.stem for p in files} == set(specs), f"Duplicate/missing completion files {block}", "CONTROL_COMPLETION_DUPLICATION_CONFLICT")
    identities = set(); checked_groups = set(); counts = {"reused": 0, "new": 0}; metric_rows = 0
    for path in sorted(files):
        spec = specs[path.stem]; value = read(path)
        identity = canonical(spec["frozen_final_identity"])
        require(identity not in identities, f"Duplicate scientific identity {block}/{path.stem}", "CONTROL_COMPLETION_DUPLICATION_CONFLICT")
        identities.add(identity); validate_completion(engine, spec, value)
        group = (spec["entity"], spec["fold"], spec["L"])
        if group not in checked_groups:
            check_spec(engine, spec)
            selected = engine.unique(engine.contexts, **{engine.entity_key:spec["entity"], "fold":spec["fold"], "formulation":"M1"})
            require(int(selected.selected_L) == spec["L"], "Forced context differs")
            checked_groups.add(group)
        inner = read(ROOT / spec["inner_completion"])
        require(sha(ROOT / spec["inner_completion"]) == spec["inner_completion_sha256"] and int(inner["best_epoch"]) == spec["epoch"], "Forced-L S2 epoch provenance differs")
        prediction = engine.pd.read_parquet(value["prediction_path"])
        validate_prediction_primary(prediction)
        validate_prediction_support(engine, spec, prediction)
        state = engine.torch.load(value["model_path"], map_location="cpu", weights_only=True)
        require(all(bool(engine.torch.isfinite(v).all()) for v in state.values()), "Nonfinite checkpoint", "PRIMARY_NONFINITE_RESULT_CONFLICT")
        require(sum(v.numel() for v in state.values()) == (51720 if engine.tt else 51525), "Model parameter count differs")
        counts["reused" if spec["reuse"] else "new"] += 1; metric_rows += len(value["metrics"])
    require(counts == {"reused":plan["reused"], "new":plan["new"]}, "Reuse/new counts differ")
    write(HERE / f"validation/full_audit_{block}.json", {"status":"PASS", "timestamp":now(), "valid_completions":len(files), "counts":counts, "metric_rows":metric_rows, "duplicate_scientific_identities":0, "support_scaler_context_epoch_and_numerical_checks":"PASS", "test_evaluations_during_audit":0})


def prepare():
    verify_refs()
    require(not (HERE / "provenance/experiment.json").exists(), "Experiment already prepared; do not overwrite")
    preservation_capture()
    cfg = read(CONFIG)
    code_paths = sorted(HERE.glob("*.py")) + [CONFIG]
    for rel in PROTECTED[:3]:
        code_paths += sorted((ROOT / rel).glob("*.py"))
        code_paths += sorted((ROOT / rel / "src").rglob("*.py"))
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in code_paths}
    provenance = {"label": LABEL, "namespace": "stage18b1-s2-common-context-v1", "created": now(), "source_code_commit": git("rev-parse", "HEAD"), "parent_scientific_checkpoint": cfg["parent_scientific_checkpoint"], "parent_manuscript_checkpoint": cfg["parent_manuscript_checkpoint"], "diagnostic_report_sha256": sha(ROOT / "review_revision/stage18a1_diagnostic_audit.md"), "configuration_sha256": sha(CONFIG), "source_hashes": source_hashes, "python": sys.version, "platform": sys.platform, "note": "New uncommitted adapter source hashes are part of provenance; not a prospective frozen protocol"}
    write(HERE / "provenance/experiment.json", provenance)
    for block in cfg["blocks"]:
        subprocess.run([sys.executable, "-B", str(Path(__file__)), "plan-block", "--block", block], cwd=ROOT, check=True)
    plans = [read(HERE / f"plans/{b}.json") for b in cfg["blocks"]]
    summary = {"label": LABEL, "required": sum(p["required"] for p in plans), "reused": sum(p["reused"] for p in plans), "new": sum(p["new"] for p in plans), "blocks": [{k:p[k] for k in ("block","required","reused","new")} for p in plans], "timestamp": now()}
    require(summary["required"] == 10920, f"Unexpected total required fits {summary}")
    write(HERE / "plans/summary.json", summary)
    preservation_check(full=False)
    print(json.dumps(summary), flush=True)


def run_all(workers):
    verify_refs()
    verify_adapter_provenance()
    if (HERE / "provenance/recovery_stage18b1r_successor.json").exists():
        require(read(HERE / "recovery/four_units_recovered.json")["status"] == "PASS", "Recover four units before general resume")
    require(not unresolved_failures(), "Unresolved failed units")
    for block in read(CONFIG)["blocks"]:
        subprocess.run([sys.executable, "-B", str(Path(__file__)), "run-block", "--block", block, "--workers", str(workers)], cwd=ROOT, check=True)
    for block in read(CONFIG)["blocks"]:
        subprocess.run([sys.executable, "-B", str(Path(__file__)), "audit-block", "--block", block], cwd=ROOT, check=True)
    preservation_check(full=True)
    print("ALL_FITS_COMPLETE_PRESERVATION_PASS analysis_pending=true", flush=True)
    subprocess.run([sys.executable, "-B", str(HERE / "analyse_control.py")], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "plan-block", "run", "run-block", "verify", "recover-units", "audit-block"))
    parser.add_argument("--block", choices=list(FROZEN))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    # Parent lock is not used by child plan/run-block processes.
    lock = None
    if args.action in ("prepare", "run", "recover-units"):
        lock = output(HERE / "runtime.lock").open("a")
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise Conflict("PROVENANCE_CONFLICT", "Control process already active")
    try:
        if args.action == "prepare": prepare()
        elif args.action == "plan-block": plan_block(args.block)
        elif args.action == "run": run_all(args.workers)
        elif args.action == "run-block": execute_block(args.block, args.workers)
        elif args.action == "verify": print(json.dumps(preservation_check(full=True)))
        elif args.action == "recover-units": recover_units()
        elif args.action == "audit-block": audit_block(args.block)
    except BaseException as exc:
        if args.action in ("prepare", "run", "recover-units"):
            stop_path = HERE / ("recovery/STOP.json" if (HERE / "provenance/recovery_stage18b1r.json").exists() else "STOP.json")
            write(stop_path, {"status": getattr(exc,"code","STAGE_18B1R_BLOCKED"), "timestamp": now(), "error": repr(exc), "traceback": traceback.format_exc()})
        raise


if __name__ == "__main__":
    main()
