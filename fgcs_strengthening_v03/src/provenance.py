"""Content seals and write-once scientific execution records."""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import file_digest, sha256
import json
import os
import re
from pathlib import Path
import tempfile
from time import perf_counter
from uuid import uuid4

from .identity import CONFIG, HOME, ROOT, ScientificIdentity, canonical_json, read_config

# C3: the only error types retried without a code change.
RETRYABLE = frozenset({"OSError", "MemoryError", "TimeoutError", "InterruptedError", "BrokenPipeError",
                       "ConnectionError", "BlockingIOError", "ChildProcessError", "KeyboardInterrupt"})


@contextmanager
def measure_seconds(timings, name):
    if timings is None:
        yield
        return
    start = perf_counter()
    try:
        yield
    finally:
        timings[name] = timings.get(name, 0.) + (perf_counter() - start)


class ProvenanceError(RuntimeError):
    pass


class DuplicateIdentity(ProvenanceError):
    pass


def sha256_file(path):
    with Path(path).open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def verify_file(path, expected):
    if sha256_file(path) != expected:
        raise ProvenanceError(f"SHA-256 mismatch: {path}")


def repository_path(relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ProvenanceError(f"Expected a repository-relative path: {relative}")
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ProvenanceError(f"Path escapes the repository: {relative}")
    return resolved


def verified_reference(reference):
    path = repository_path(reference["path"])
    verify_file(path, reference["sha256"])
    return path


def _fingerprints(paths):
    paths = tuple(Path(path).as_posix() for path in paths)
    if len(set(paths)) != len(paths):
        raise ProvenanceError("Duplicate fingerprint path")
    return tuple((path, sha256_file(repository_path(path))) for path in sorted(paths))


def _protocol_references(additional_sources):
    config = read_config()
    refs = [config["protocol"], config["historical_reader_config"]]
    for block in config["blocks"].values():
        refs.extend(block[field] for field in ("cohort_source", "common_context_source", "support_manifest",
                                               "frozen_scaler_reference", "raw_input"))
        refs.extend(block["v1_registries"].values())
    inputs = {}
    for ref in refs:
        if inputs.setdefault(ref["path"], ref["sha256"]) != ref["sha256"]:
            raise ProvenanceError(f"Conflicting frozen references: {ref['path']}")
    historical = config["historical_source_hashes"]
    foundation = ("plan_execution.py", "src/identity.py", "src/provenance.py",
                  "src/data_adapters.py", "src/models/lstm.py", "src/transfer/design.py", "src/modern/design.py", "src/tree/design.py")
    sources = (*historical, *((CONFIG.parents[1] / name).relative_to(ROOT).as_posix() for name in foundation),
               *(Path(name).as_posix() for name in additional_sources))
    return inputs, historical, sources


@dataclass(frozen=True, slots=True)
class Fingerprints:
    configuration: tuple[str, str]
    inputs: tuple[tuple[str, str], ...]
    sources: tuple[tuple[str, str], ...]

    def __post_init__(self):
        pairs = (self.configuration, *self.inputs, *self.sources)
        if (not isinstance(self.inputs, tuple) or not isinstance(self.sources, tuple)
                or any(not isinstance(pair, tuple) or len(pair) != 2 for pair in pairs)):
            raise TypeError("Fingerprint components must be immutable path/digest pairs")
        paths = tuple(relative for relative, _ in pairs)
        if (self.configuration[0] != CONFIG.relative_to(ROOT).as_posix()
                or len(set(paths)) != len(paths)
                or any(not re.fullmatch(r"[0-9a-f]{64}", digest) for _, digest in pairs)):
            raise ProvenanceError("Invalid fingerprint set")

    @classmethod
    def capture(cls, *, inputs, sources):
        return cls(
            (CONFIG.relative_to(ROOT).as_posix(), sha256_file(CONFIG)),
            _fingerprints(inputs),
            _fingerprints(sources),
        )

    @classmethod
    def capture_protocol(cls, *, additional_sources=()):
        """Verify frozen references and seal Stage 3A plus declared engine source."""
        additional_sources = tuple(additional_sources)
        inputs, _, sources = _protocol_references(additional_sources)
        seal = cls.capture(inputs=inputs, sources=sources)
        seal.require_protocol(additional_sources=additional_sources)
        return seal

    def require_protocol(self, *, additional_sources=()):
        inputs, historical, sources = _protocol_references(additional_sources)
        sealed_inputs, sealed_sources = dict(self.inputs), dict(self.sources)
        for expected, actual in ((inputs, sealed_inputs), (historical, sealed_sources)):
            for path, digest in expected.items():
                if actual.get(path) != digest:
                    raise ProvenanceError(f"Missing or changed frozen fingerprint: {path}")
        missing = set(sources) - sealed_sources.keys()
        if missing:
            raise ProvenanceError(f"Protocol sources missing from the fingerprint seal: {sorted(missing)}")

    def verify(self):
        for relative, digest in (self.configuration, *self.inputs, *self.sources):
            verify_file(repository_path(relative), digest)

    def payload(self):
        return {"configuration": list(self.configuration),
                "inputs": [list(pair) for pair in self.inputs],
                "sources": [list(pair) for pair in self.sources]}

    @property
    def digest(self):
        return sha256(canonical_json(self.payload())).hexdigest()


def _atomic_publish(path, payload):
    """Publish a complete JSON record exactly once, including across workers."""
    _atomic_publish_bytes(path, canonical_json(payload) + b"\n")


def _atomic_publish_bytes(path, encoded):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
            os.link(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except FileExistsError as error:
            raise DuplicateIdentity(f"Record already exists: {path}") from error
        finally:
            temporary.unlink()


@dataclass(frozen=True, slots=True)
class Attempt:
    identity: ScientificIdentity
    token: str
    evaluation: bool = False


class Journal:
    """Record one attempt and at most one outcome per identity and run namespace."""

    def __init__(self, seal):
        self.runtime = HOME / "runtime"
        if self.runtime != self.runtime.resolve():
            raise ProvenanceError("Journal must be under the new namespace runtime directory")
        seal.verify()
        self.seal = seal
        path = self._path("fingerprints.json")
        record = {"digest": seal.digest, **seal.payload()}
        try:
            _atomic_publish(path, record)
        except DuplicateIdentity:
            root = json.loads(path.read_text())
            if root != record and self._amendment_head(root["digest"]) != seal.digest:
                raise ProvenanceError("Journal already bound to different fingerprints") from None
        self._accepted, self._minimum = self._chain(json.loads(path.read_text())["digest"])

    def _amendments(self):
        directory = self._path("amendments")
        records = [json.loads(path.read_text()) for path in sorted(directory.glob("*.json"))] if directory.is_dir() else []
        if [record["sequence"] for record in records] != list(range(1, len(records) + 1)):
            raise ProvenanceError("Seal amendment chain is not contiguous")
        return records

    def _amendment_head(self, root):
        head = root
        for record in self._amendments():
            if record["previous_digest"] != head:
                raise ProvenanceError("Seal amendment chain is broken")
            head = record["digest"]
        return head

    def _chain(self, root):
        """Accepted record fingerprints and, per amended identity, the earliest valid chain position."""
        accepted, minimum = [root], {}
        for record in self._amendments():
            if record["previous_digest"] != accepted[-1]:
                raise ProvenanceError("Seal amendment chain is broken")
            accepted.append(record["digest"])
            for digest in record["affected_identity_sha256"]:
                minimum[digest] = len(accepted) - 1
        if accepted[-1] != self.seal.digest:
            raise ProvenanceError("Journal seal is not the head of its amendment chain")
        return tuple(accepted), minimum

    def _fingerprint_ok(self, identity, digest):
        return digest in self._accepted and self._accepted.index(digest) >= self._minimum.get(identity.digest, 0)

    def amend(self, seal, *, reason, affected):
        """Chain a documented code repair. Affected identities must already be quarantined."""
        if not isinstance(seal, Fingerprints) or not isinstance(reason, str) or not reason.strip():
            raise ProvenanceError("An amendment requires a successor seal and a documented reason")
        affected = sorted({identity.digest for identity in affected})
        if not affected:
            raise ProvenanceError("An amendment must name its affected identities")
        for digest in affected:
            for prefix in ((), ("evaluations",)):
                for kind in ("attempts", "outcomes"):
                    if self._path(*prefix, kind, f"{digest}.json").exists():
                        raise ProvenanceError("Quarantine affected identities before amending the seal")
            if not self._path("quarantine", digest).is_dir():
                raise ProvenanceError("Every affected identity must have a quarantined attempt")
            if self._closed(False) and self._path("quarantine", digest, "fit").is_dir():
                raise ProvenanceError("Fit identities cannot be amended after fit closure (C6)")
            for kind in ("fit", "evaluation"):
                bound = self._pending_amendment(digest, kind == "evaluation")
                if bound is not None and bound != seal.digest:
                    raise ProvenanceError("A quarantine is bound to a different successor seal")
        seal.verify()
        sequence = len(self._amendments()) + 1
        record = {"sequence": sequence, "previous_digest": self.seal.digest, "digest": seal.digest,
                  "seal": seal.payload(), "reason": reason, "affected_identity_sha256": affected,
                  "utc": datetime.now(timezone.utc).isoformat()}
        _atomic_publish(self._path("amendments", f"{sequence:04d}.json"), record)
        return Journal(seal)

    def _artifact_paths(self, identity, evaluation):
        prefix = ("evaluations",) if evaluation else ()
        paths = [self._record_path(kind, identity, evaluation) for kind in ("attempts", "outcomes")]
        if not evaluation:
            paths += [self._path(directory, identity.digest)
                      for directory in ("checkpoints", "diagnostic_checkpoints", "lightgbm_models")]
            paths.append(self._path("optimizer_states", f"{identity.digest}.pt"))
        return [path for path in paths if path.exists()], prefix

    def _closed(self, evaluation):
        """True once the orchestrator's closure record for this kind of record exists (C6)."""
        return self._path("orchestrator", "gates", "evaluation.json" if evaluation else "fits.json").exists()

    def _quarantine_records(self, digest, evaluation):
        base = self._path("quarantine", digest, "evaluation" if evaluation else "fit")
        return sorted(base.glob("*/quarantine.json")) if base.is_dir() else []

    def _pending_amendment(self, digest, evaluation):
        """The successor seal digest the latest quarantine waits for, if any."""
        records = self._quarantine_records(digest, evaluation)
        return json.loads(records[-1].read_text()).get("amendment_sha256") if records else None

    def quarantine(self, identity, *, reason, evaluation=False, amendment=None):
        """Move an interrupted or failed attempt's evidence aside, retaining every byte, so it can be retried.

        Interrupted attempts and infrastructure failures may be retried under the same seal. Any other
        failure is terminal unless it is repaired: the quarantine then names its successor seal, and the
        identity cannot start again until that amendment is the journal's seal (C3). Nothing is quarantined
        after the matching closure record exists (C6).
        """
        if not isinstance(reason, str) or not reason.strip():
            raise ProvenanceError("Quarantine requires a documented reason")
        if self._closed(evaluation):
            raise ProvenanceError("Records cannot be quarantined after their phase is closed (C6)")
        paths, _ = self._artifact_paths(identity, evaluation)
        if not paths:
            raise ProvenanceError("Nothing to quarantine for this identity")
        outcome = self._record_path("outcomes", identity, evaluation)
        error_type = None
        if outcome.exists():
            stored = json.loads(outcome.read_text())
            if stored.get("status") == "complete":
                raise ProvenanceError("A complete outcome is never quarantined")
            error_type = stored.get("evidence", {}).get("error", {}).get("type")
        if amendment is not None:
            if not isinstance(amendment, Fingerprints) or amendment.digest == self.seal.digest:
                raise ProvenanceError("A repair quarantine must name a different successor seal")
            amendment = amendment.digest
        elif outcome.exists() and error_type not in RETRYABLE:
            raise ProvenanceError("A non-infrastructure failure is terminal unless repaired by a sealed amendment (C3)")
        base = self._path("quarantine", identity.digest, "evaluation" if evaluation else "fit")
        sequence = len(list(base.glob("*"))) + 1 if base.is_dir() else 1
        target = base / f"{sequence:02d}"
        files = []
        for path in paths:
            items = sorted(item for item in path.rglob("*") if item.is_file()) if path.is_dir() else [path]
            files.extend({"path": item.relative_to(self.runtime).as_posix(), "sha256": sha256_file(item)}
                         for item in items)
        target.mkdir(parents=True, exist_ok=False)
        record = {"identity": identity.payload(), "identity_sha256": identity.digest, "evaluation": evaluation,
                  "sequence": sequence, "reason": reason, "fingerprint_sha256": self.seal.digest,
                  "outcome_error_type": error_type, "amendment_sha256": amendment, "files": files, "utc": datetime.now(timezone.utc).isoformat()}
        _atomic_publish(target / "quarantine.json", record)
        for path in paths:
            destination = target / path.relative_to(self.runtime)
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.rename(path, destination)
        return sequence

    def quarantined(self, identity, *, evaluation=False):
        base = self._path("quarantine", identity.digest, "evaluation" if evaluation else "fit")
        return len([path for path in base.glob("*") if path.is_dir()]) if base.is_dir() else 0

    def _path(self, *parts):
        path = self.runtime.joinpath(*parts)
        if path.resolve() != path:
            raise ProvenanceError("Symlink in journal path")
        return path

    def _record(self, attempt, status):
        operation = {"operation": "outer_test_evaluation"} if attempt.evaluation else {}
        return {
            **operation, "identity": attempt.identity.payload(), "identity_sha256": attempt.identity.digest,
            "fingerprint_sha256": self.seal.digest, "attempt_token": attempt.token,
            "status": status, "utc": datetime.now(timezone.utc).isoformat(),
        }

    def _record_path(self, kind, identity, evaluation):
        prefix = ("evaluations",) if evaluation else ()
        return self._path(*prefix, kind, f"{identity.digest}.json")

    def start(self, identity, *, evaluation=False, source=None):
        if source is not None and (not evaluation or identity.arm != "checkpoint_request"
                                   or source.arm != "core" or source.phase != "final"):
            raise ProvenanceError("Only a task-checkpoint evaluation may name its parent final fit")
        if evaluation:
            if identity.phase != "final":
                raise ProvenanceError("Evaluation requires a final-fit identity")
            self.completed_evidence(identity if source is None else source)
        if self._record_path("outcomes", identity, evaluation).exists():
            raise DuplicateIdentity(f"Outcome already exists: {identity.digest}")
        bound = self._pending_amendment(identity.digest, evaluation)
        if bound is not None and bound != self.seal.digest:
            raise ProvenanceError("This identity awaits its sealed amendment before it can run again (C3)")
        attempt = Attempt(identity, uuid4().hex, evaluation)
        _atomic_publish(self._record_path("attempts", identity, evaluation), self._record(attempt, "started"))
        return attempt

    def _check_attempt(self, attempt):
        expected = self._record(attempt, "started")
        try:
            started = json.loads(self._record_path("attempts", attempt.identity, attempt.evaluation).read_text())
        except FileNotFoundError as error:
            raise ProvenanceError("No attempt for this identity") from error
        if (any(started.get(key) != value for key, value in expected.items()
                if key not in {"utc", "fingerprint_sha256"})
                or not self._fingerprint_ok(attempt.identity, started.get("fingerprint_sha256"))):
            raise ProvenanceError("Attempt identity, token or fingerprints differ")
        return started

    def finish(self, attempt, *, status, evidence):
        if status not in {"complete", "failed"} or not isinstance(evidence, dict):
            raise ValueError("An outcome must contain an explicit status and evidence")
        self._check_attempt(attempt)
        path = self._record_path("outcomes", attempt.identity, attempt.evaluation)
        _atomic_publish(path, {**self._record(attempt, status), "evidence": evidence})

    def completed_evidence(self, identity, *, evaluation=False):
        status, evidence, digest = self.terminal_evidence(identity, evaluation=evaluation)
        if status != "complete":
            raise ProvenanceError(f"Outcome is not complete: {identity.digest}")
        return evidence, digest

    def terminal_evidence(self, identity, *, evaluation=False):
        try:
            encoded = self._record_path("outcomes", identity, evaluation).read_bytes()
            record = json.loads(encoded)
        except FileNotFoundError as error:
            raise ProvenanceError(f"No completed outcome for {identity.digest}") from error
        status = record.get("status")
        if status not in {"complete", "failed"} or not isinstance(record.get("evidence"), dict):
            raise ProvenanceError(f"Outcome is not terminal: {identity.digest}")
        attempt = Attempt(identity, record.get("attempt_token"), evaluation)
        started_fingerprint = self._check_attempt(attempt)["fingerprint_sha256"]
        expected = self._record(attempt, status)
        if (any(record.get(key) != value for key, value in expected.items()
                if key not in {"utc", "fingerprint_sha256"})
                or record.get("fingerprint_sha256") != started_fingerprint):
            raise ProvenanceError("Outcome identity or fingerprints differ")
        return status, record["evidence"], sha256(encoded).hexdigest()

    def save_checkpoint(self, attempt, epoch, encoded, *, diagnostic=False):
        """Write a model-only checkpoint once and return its exact file identity."""
        if type(epoch) is not int or epoch < (0 if diagnostic else 1) or not isinstance(encoded, bytes):
            raise ValueError("Invalid checkpoint epoch or encoded bytes")
        directory = "diagnostic_checkpoints" if diagnostic else "checkpoints"
        return self._save_artifact(attempt, encoded, directory, attempt.identity.digest, f"epoch-{epoch:02d}.pt")

    def save_optimizer_state(self, attempt, encoded):
        return self._save_artifact(attempt, encoded, "optimizer_states", f"{attempt.identity.digest}.pt")

    def save_lightgbm_model(self, attempt, horizon, encoded):
        if attempt.identity.arm != "lightgbm" or attempt.identity.phase != "final":
            raise ProvenanceError("Expected a final LightGBM wrapper attempt")
        return self._save_artifact(attempt, encoded, *self._lightgbm_model_path(attempt.identity, horizon))

    def _lightgbm_model_path(self, identity, horizon):
        if type(horizon) is not int or horizon not in (1, 2, 4, 9, 18):
            raise ValueError("Unknown LightGBM horizon")
        return "lightgbm_models", identity.digest, f"horizon-{horizon:02d}.txt"

    def lightgbm_model_bytes(self, identity, horizon, reference):
        path = self._path(*self._lightgbm_model_path(identity, horizon))
        if path.relative_to(self.runtime).as_posix() != reference["path"]:
            raise ProvenanceError("Artifact path differs from its recorded identity")
        encoded = path.read_bytes()
        if len(encoded) != reference["bytes"] or sha256(encoded).hexdigest() != reference["sha256"]:
            raise ProvenanceError("Artifact bytes differ from the fit record")
        return encoded

    def _save_artifact(self, attempt, encoded, *path_parts):
        if attempt.evaluation:
            raise ProvenanceError("Training artifacts require a training attempt")
        self._check_attempt(attempt)
        name = f"{attempt.identity.digest}.json"
        if self._path("outcomes", name).exists():
            raise DuplicateIdentity(f"Outcome already exists: {attempt.identity.digest}")
        path = self._path(*path_parts)
        _atomic_publish_bytes(path, encoded)
        return {"path": path.relative_to(self.runtime).as_posix(), "sha256": sha256(encoded).hexdigest(),
                "bytes": len(encoded)}

    def checkpoint_bytes(self, identity, epoch, reference):
        filename = f"{identity.digest}/epoch-{epoch:02d}.pt"
        relative = reference["path"]
        if relative not in {f"checkpoints/{filename}", f"diagnostic_checkpoints/{filename}"}:
            raise ProvenanceError("Checkpoint path differs from the final-fit identity or epoch")
        encoded = self._path(relative).read_bytes()
        if len(encoded) != reference["bytes"] or sha256(encoded).hexdigest() != reference["sha256"]:
            raise ProvenanceError("Checkpoint bytes differ from the final-fit record")
        return encoded
