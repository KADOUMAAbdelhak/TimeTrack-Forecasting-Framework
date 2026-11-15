"""Sealed, one-identity modern fitting and explicit pilot reuse."""

from contextlib import contextmanager
from dataclasses import replace
import fcntl
import io
import json
from pathlib import Path

import numpy as np
import torch

from ..data_adapters import PreparedPartition
from ..diagnostics.batches import json_sha256
from ..diagnostics.engine import _SOURCES as _DIAGNOSTIC_SOURCES
from ..identity import RESOURCES, ROOT, ScientificIdentity, canonical_json, read_config
from ..models.registry import REGISTRY
from ..provenance import Fingerprints, ProvenanceError, _atomic_publish, sha256_file
from ..training import TrainingEngine, _state_hash, _windows
from ..transfer.runner import _SOURCES as _TRANSFER_SOURCES
from .design import dry_budget, pilot_context
from .structure import validate_family_structure

_CONFIG = read_config()
_SETTINGS = _CONFIG["modern"]
_HOME = Path(__file__).resolve().parents[1]
_SOURCES = tuple((_HOME / name).relative_to(ROOT).as_posix() for name in (
    "modern/runner.py", "modern/structure.py", "models/registry.py",
    "models/dlinear.py", "models/_transformer.py", "models/patchtst.py", "models/itransformer.py",
))


def modern_fingerprints():
    return Fingerprints.capture_protocol(additional_sources=(*_DIAGNOSTIC_SOURCES, *_TRANSFER_SOURCES, *_SOURCES))


def _architecture(identity, context):
    family = identity.formulation
    settings = _SETTINGS["families"][family]
    record = {"label": REGISTRY[family].label, "family": family, "variant": identity.variant,
              "scope": identity.input_scope, "tasks": list(identity.tasks), "context": context,
              "horizons": list(_CONFIG["blocks"][identity.block]["horizons"]), "settings": settings}
    if family != "DLinear":
        record["transformer"] = _SETTINGS["transformer"]
    return record


class ModernRunner(TrainingEngine):
    def __init__(self, journal):
        super().__init__(journal)
        journal.seal.require_protocol(additional_sources=_SOURCES)
        dry_budget()
        for key in ("batch_size", "max_inner_epochs", "patience", "gradient_clip", "learning_rate"):
            if _SETTINGS[key] != _CONFIG["lstm"][key]:
                raise ProvenanceError(f"Shared training lifecycle does not match modern {key}")

    @staticmethod
    def _check_fit_mode(identity, phase, mode):
        if (not isinstance(identity, ScientificIdentity) or identity.arm != "modern"
                or identity.phase != phase or mode != "equal_loss"):
            raise ValueError("Expected a declared modern identity with registered mean-loss training")

    @contextmanager
    def _family_lock(self, family):
        if family not in REGISTRY:
            raise ValueError(f"Unknown modern family: {family}")
        path = self.journal._path("modern", family, "lock")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def _family_paths(self, family):
        return tuple(self.journal._path("modern", family, name)
                     for name in ("structure.json", "stop.json", "active.json"))

    def _require_open_family(self, family):
        certificate, stopped, active = self._family_paths(family)
        if stopped.exists() or active.exists():
            raise ProvenanceError(f"{family} is halted or has an unresolved attempt; author review is required")
        return certificate

    def _read_certificate(self, family, path):
        try:
            record = json.loads(path.read_text())
        except FileNotFoundError as error:
            raise ProvenanceError(f"{family} requires explicit synthetic structural validation") from error
        if (record.get("family") != family or record.get("fingerprint_sha256") != self.journal.seal.digest
                or record.get("status") != "complete"
                or len(record.get("checks", [])) != 15 * len(REGISTRY[family].scopes)):
            raise ProvenanceError(f"{family} lacks a valid structural certificate; author review is required")
        return record

    def validate_family(self, family):
        """Run the synthetic-only gate once and retain a sealed pass or failure."""
        with self._family_lock(family):
            path = self._require_open_family(family)
            if path.exists():
                return self._read_certificate(family, path)
            record = {"family": family, "fingerprint_sha256": self.journal.seal.digest}
            try:
                checks = validate_family_structure(family)
            except Exception as error:
                _atomic_publish(path, {**record, "status": "failed",
                                       "error": {"type": type(error).__name__, "message": str(error)}})
                raise
            record.update(status="complete", checks=checks)
            _atomic_publish(path, record)
            return record

    def _fit(self, identity, partition, phase, mode):
        self._check_fit_mode(identity, phase, mode)
        if not isinstance(partition, PreparedPartition):
            raise TypeError("Expected a verified Stage 3A partition")
        expected_context = pilot_context(identity)
        if expected_context is not None and partition.context != expected_context:
            raise ProvenanceError("Pilot partition context differs from the registered frozen context")
        family = identity.formulation
        with self._family_lock(family):
            certificate = self._require_open_family(family)
            self._read_certificate(family, certificate)
            _, stopped, active = self._family_paths(family)
            path = self.journal._record_path("attempts", identity, False)
            existed = path.exists()
            _atomic_publish(active, {"identity": identity.payload(), "identity_sha256": identity.digest,
                                     "fingerprint_sha256": self.journal.seal.digest})
            try:
                result = super()._fit(identity, partition, phase, mode)
            except BaseException as error:
                if path.exists():
                    outcome = self.journal._record_path("outcomes", identity, False)
                    if not existed or not outcome.exists() or json.loads(outcome.read_text())["status"] != "complete":
                        _atomic_publish(stopped, {
                            "identity": identity.payload(), "identity_sha256": identity.digest,
                            "fingerprint_sha256": self.journal.seal.digest, "attempt_sha256": sha256_file(path),
                            "outcome_sha256": sha256_file(outcome) if outcome.exists() else None,
                            "error": {"type": type(error).__name__, "message": str(error)},
                        })
                active.unlink()
                raise
            active.unlink()
            return result

    def _prepare_windows(self, identity, partition, evidence, *, validation=False):
        raw = partition.validation() if validation else partition.training()
        inputs, targets = _windows(raw, identity, partition.context)
        if identity.input_scope == "own" and identity.variant == "independent":
            index = RESOURCES.index(identity.tasks[0])
            inputs = inputs[:, :, index:index + 1]
        if validation:
            native = np.asarray(raw.native_targets)
            ids = raw.origin_ids.tolist()
            if native.shape != raw.targets.shape or not np.isfinite(native).all() or len(ids) != len(set(ids)):
                raise ValueError("Invalid native validation targets or duplicated origins")
            evidence["native_validation"] = {
                "origins": len(ids), "ordered_origin_ids_sha256": json_sha256(ids),
                "support_sha256": partition.split_hashes["inner_validation"], "verified_epochs": 0,
            }
        return inputs, targets

    def _model_and_optimizer(self, identity, partition, evidence):
        spec = REGISTRY[identity.formulation]
        if identity.input_scope not in spec.scopes:
            raise ProvenanceError("Registry scope differs from the declared identity")
        model = spec.build(partition.context, identity.tasks, identity.input_scope)
        optimizer = spec.make_optimizer(model)
        evidence["architecture"] = _architecture(identity, partition.context)
        evidence["optimizer"] = {"name": type(optimizer).__name__, **json.loads(canonical_json(optimizer.defaults))}
        evidence["pilot_context"] = pilot_context(identity)
        certificate = self._family_paths(identity.formulation)[0]
        evidence["structural_certificate_sha256"] = sha256_file(certificate)
        return model, optimizer

    @torch.no_grad()
    def _validation_losses(self, model, windows, partition, identity, evidence):
        model.eval()
        inputs, targets = windows
        totals = torch.zeros(len(identity.tasks), dtype=torch.float64)
        for X, y in zip(inputs.split(_SETTINGS["batch_size"]), targets.split(_SETTINGS["batch_size"]), strict=True):
            forecast = model(X)
            if forecast.shape != y.shape or not torch.isfinite(forecast).all():
                raise ValueError("Invalid scaled validation predictions")
            scaled = forecast.numpy()
            for index, task in enumerate(identity.tasks):
                values, fraction, raw = partition.inverse_target(scaled[:, index], task)
                if (values.shape != scaled[:, index].shape or raw.shape != values.shape
                        or not np.isfinite(values).all() or not np.isfinite(raw).all() or not np.isfinite(fraction)):
                    raise ValueError(f"Invalid native validation predictions for {task}")
            totals += (forecast.double() - y.double()).square().sum(dim=(0, 2))
        evidence["native_validation"]["verified_epochs"] += 1
        return (totals / (len(inputs) * targets.shape[-1])).tolist()

    def _verify_inner(self, identity, observed, context):
        certificate = self._family_paths(identity.formulation)[0]
        if (observed.get("architecture") != _architecture(identity, context)
                or observed.get("structural_certificate_sha256") != sha256_file(certificate)
                or observed["native_validation"]["verified_epochs"] != len(observed["epochs"])):
            raise ProvenanceError("Modern inner outcome lacks matching technical evidence")
        epoch = observed["selection"]["joint_epoch"]
        if type(epoch) is not int or not 1 <= epoch <= min(50, len(observed["epochs"])):
            raise ProvenanceError("Invalid selected modern epoch")
        checkpoint = observed["checkpoints"][str(epoch)]
        encoded = self.journal.checkpoint_bytes(identity, epoch, checkpoint)
        state = torch.load(io.BytesIO(encoded), map_location="cpu", weights_only=True)
        if _state_hash(state) != checkpoint["model_sha256"] or not all(torch.isfinite(v).all() for v in state.values()):
            raise ProvenanceError("Modern selected inner model differs from its recorded hash")

    def _selected_final_plan(self, identity, evidence, mode):
        plan = super()._selected_final_plan(identity, evidence, mode)
        inner = replace(identity, phase="inner")
        outcome, _ = self.journal.completed_evidence(inner)
        self._verify_inner(inner, outcome, evidence["context"])
        return plan

    def reuse_pilot(self, identity, partition):
        """Read an existing exact pilot completion without a second fit or evaluation."""
        self._check_fit_mode(identity, "inner", "equal_loss")
        context = pilot_context(identity)
        if context is None or not isinstance(partition, PreparedPartition) or (
            partition.block, partition.entity, partition.fold, partition.phase, partition.context
        ) != (identity.block, identity.entity, identity.fold, "inner", context):
            raise ProvenanceError("Expected the exact registered pilot identity and partition")
        with self._family_lock(identity.formulation):
            self.journal.seal.verify()
            certificate = self._require_open_family(identity.formulation)
            self._read_certificate(identity.formulation, certificate)
            observed, digest = self.journal.completed_evidence(identity)
            expected = {"context": context, "pilot_context": context, "support_sha256": partition.support_sha256,
                        "split_hashes": dict(partition.split_hashes), "scaler_sha256": partition.scaler_sha256,
                        "configuration_sha256": self.journal.seal.configuration[1]}
            if any(observed.get(key) != value for key, value in expected.items()):
                raise ProvenanceError("Pilot completion differs from the exact requested input/context")
            self._verify_inner(identity, observed, context)
            return observed, digest
