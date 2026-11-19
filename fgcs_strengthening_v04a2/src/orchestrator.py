"""Registered execution schedule, worker leases, recovery, blinding gates and wall time.

Nothing executes on import. Phases run in a fixed order:

    certify -> canary (stop gate) -> inner -> final -> diagnostics -> [fit closure]
    -> evaluation -> [evaluation closure] -> bundle

v0.4 runs no systems benchmarks (protocol P8), so r3's systems phase is gone.

Amendment A2 schedules the tier-2 2x2 of all four backbones under the change parameterisation, with the
three modern structural certificates; it schedules no D-4 extractions, so the diagnostics phase is empty.

Outer-test data are materialised only in the evaluation phase, which refuses to start until every
fit and diagnostic unit is terminal and closed. Repairs therefore never see outer-test outcomes.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
import fcntl
from hashlib import sha256
import io
import json
from pathlib import Path
from time import monotonic
from uuid import uuid4

from .identity import RESOURCES, ROOT, SCOPES, ScientificIdentity, canonical_json, diagnostic_parent, read_config
from .provenance import (RETRYABLE, DuplicateIdentity, Journal, ProvenanceError, _atomic_publish,
                         _atomic_publish_bytes, sha256_file)

_CONFIG = read_config()
_SOURCES = (Path(__file__).resolve().relative_to(ROOT).as_posix(),)
PHASES = ("certify", "canary", "inner", "final", "diagnostics", "evaluation")
FIT_PHASES = ("canary", "inner", "final", "diagnostics")
MAX_RETRIES = 2
TRAINING_WORKERS = 6  # P9: exactly six concurrent single-thread workers, enforced by slot locks
if _CONFIG["execution"]["fit_workers"] != TRAINING_WORKERS:
    raise RuntimeError("Registered fit workers differ from the configuration")


def _digest(value):
    return sha256(canonical_json(value)).hexdigest()


THREAD_ENVIRONMENT = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")
CLOSURES = {"fits": ("certify", *FIT_PHASES), "evaluation": ("evaluation",)}


def configure_worker_process():
    """Call first in a fit-worker process: torch intra- and inter-op pools of one thread (C4, §9).

    BLAS/OpenMP pools are sized when their libraries load, so the launcher must also export
    OMP_NUM_THREADS=MKL_NUM_THREADS=OPENBLAS_NUM_THREADS=1; require_fit_threads verifies all of it.
    """
    import torch

    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass  # already fixed for this process; require_fit_threads checks the value
    torch.set_num_threads(1)


def require_fit_threads():
    """Refuse to fit unless every thread pool this process uses is single-threaded."""
    import os

    import torch

    observed = {"torch_intra_op": torch.get_num_threads(), "torch_inter_op": torch.get_num_interop_threads(),
                **{key: os.environ.get(key) for key in THREAD_ENVIRONMENT},
                "device": torch.get_default_device().type}
    expected = {"torch_intra_op": 1, "torch_inter_op": 1, **{key: "1" for key in THREAD_ENVIRONMENT},
                "device": "cpu"}
    if observed != expected:
        raise ProvenanceError(f"Fit workers must be single-threaded on CPU (C4): {observed}")
    return observed


def execution_sources():
    """Every engine and analysis source the runtime seal covers."""
    from .analysis import SOURCES as analysis
    from .diagnostics.engine import _SOURCES as diagnostics
    from .evaluation import _SOURCES as evaluation
    from .modern.runner import _SOURCES as modern
    from .transfer.runner import _SOURCES as transfer

    return tuple(dict.fromkeys((*diagnostics, *evaluation, *modern, *transfer, *analysis, *_SOURCES)))


def execution_fingerprints():
    """The single seal for the scientific runtime: every engine, analysis and orchestrator source."""
    from .provenance import Fingerprints

    return Fingerprints.capture_protocol(additional_sources=execution_sources())


@dataclass(frozen=True, slots=True)
class Unit:
    kind: str
    phase: str
    key: str
    identity: ScientificIdentity | None = None
    requires: tuple[str, ...] = ()
    payload: tuple = ()

    @property
    def evaluation(self):
        return self.kind == "evaluate"


def _fit_unit(phase, identity, requires=()):
    return Unit("fit", phase, identity.digest, identity, tuple(requires))


def _final_requires(identity):
    return (replace(identity, phase="inner").digest,)


def canary_identities():
    """A2: per block, the first cohort entity's fold-1 seed-0 inner fits of every 2x2 cell of every backbone.

    That is the LSTM 2x2 (10 fits), DLinear 10, PatchTST 10 and iTransformer 5: 35 per block, 70 in all.
    """
    from ..plan_execution import core_identities
    from .modern.design import FAMILIES, family_identities

    for block, entities in _CONFIG["cohort"].items():
        group = (block, entities[0], 1, 0, "inner")
        yield from core_identities(*group, _CONFIG)
        for family in FAMILIES:
            yield from family_identities(*group, family)


def registered_schedule():
    """The complete ordered A2 unit list. Pure enumeration; reads no data or results."""
    from ..plan_execution import fit_identities
    from .modern.design import FAMILIES

    units = [Unit("certify", "certify", f"certify:{family}") for family in FAMILIES]
    certify = {family: f"certify:{family}" for family in FAMILIES}
    canary = list(canary_identities())
    canary_keys = {identity.digest for identity in canary}

    def modern_requires(identity):
        return (certify[identity.formulation],) if identity.arm == "modern" else ()

    units += [_fit_unit("canary", identity, modern_requires(identity)) for identity in canary]
    fits = list(fit_identities())
    units += [_fit_unit("inner", identity, modern_requires(identity)) for identity in fits
              if identity.phase == "inner" and identity.digest not in canary_keys]
    units += [_fit_unit("final", identity, _final_requires(identity)) for identity in fits if identity.phase == "final"]
    deployments = [identity for identity in fits if identity.phase == "final"]
    from .evaluation import evaluation_source
    units += [Unit("evaluate", "evaluation", "evaluate:" + identity.digest, identity,
                   (evaluation_source(identity).digest,)) for identity in deployments]
    keys = [unit.key for unit in units]
    if len(keys) != len(set(keys)):
        raise RuntimeError("Duplicate scheduled unit")
    return tuple(units)


class Schedule:
    def __init__(self, units):
        self.units = tuple(units)
        self.by_key = {unit.key: unit for unit in self.units}
        if len(self.by_key) != len(self.units) or any(unit.phase not in PHASES for unit in self.units):
            raise ValueError("Invalid schedule")
        for unit in self.units:
            for key in unit.requires:
                if key not in self.by_key or PHASES.index(self.by_key[key].phase) > PHASES.index(unit.phase):
                    raise ValueError(f"Unresolvable or out-of-order dependency for {unit.key}")

    @property
    def digest(self):
        return _digest([[unit.kind, unit.phase, unit.key, list(unit.requires)] for unit in self.units])

    def phase(self, phase):
        return tuple(unit for unit in self.units if unit.phase == phase)


@dataclass
class Session:
    phase: str
    token: str = field(default_factory=lambda: uuid4().hex)
    utc_start: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started: float = field(default_factory=monotonic)
    executed: dict = field(default_factory=dict)
    slot: int | None = None
    stopped: bool = False


class Orchestrator:
    """One worker process. At most TRAINING_WORKERS run concurrently, each holding one slot lock."""

    def __init__(self, journal, schedule, executors, *, registration, workers):
        if not isinstance(journal, Journal) or not isinstance(schedule, Schedule):
            raise TypeError("Expected a sealed journal and a registered schedule")
        journal.seal.require_protocol(additional_sources=execution_sources())
        registration = Path(registration)
        if not registration.is_file():
            raise ProvenanceError("Execution requires the registration record")
        if workers != TRAINING_WORKERS or type(workers) is not int:
            raise ValueError(f"Expected the registered worker count ({TRAINING_WORKERS}, C4)")
        self.journal, self.schedule, self.executors, self.workers = journal, schedule, executors, workers
        self.registration_sha256 = sha256_file(registration)
        self._publish_exact(self._path("schedule.json"), {
            "schedule_sha256": schedule.digest, "units": len(schedule.units),
            "registration_sha256": self.registration_sha256, "registered_workers": workers})

    # -- records ---------------------------------------------------------------------------------
    def _path(self, *parts):
        return self.journal._path("orchestrator", *parts)

    @staticmethod
    def _publish_exact(path, record):
        try:
            _atomic_publish(path, record)
        except DuplicateIdentity:
            if json.loads(path.read_text()) != record:
                raise ProvenanceError(f"Existing orchestration record differs: {path.name}") from None

    def _record(self, unit):
        """(status, evidence) of a journalled unit, or None when it has no terminal record."""
        if unit.kind == "certify":
            path = self.journal._path("modern", unit.key.split(":", 1)[1], "structure.json")
            if not path.exists():
                return None
            return json.loads(path.read_text())["status"], {}
        path = self.journal._record_path("outcomes", unit.identity, unit.evaluation)
        if not path.exists():
            return None
        status, evidence, _ = self.journal.terminal_evidence(unit.identity, evaluation=unit.evaluation)
        return status, evidence

    def _interrupted(self, unit):
        return (unit.identity is not None and self._record(unit) is None
                and self.journal._record_path("attempts", unit.identity, unit.evaluation).exists())

    def abandoned(self, unit):
        path = self._path("abandoned", f"{_digest(unit.key)}.json")
        return json.loads(path.read_text()) if path.exists() else None

    def _abandon(self, unit, reason, blocking=()):
        self._publish_exact(self._path("abandoned", f"{_digest(unit.key)}.json"), {
            "unit": unit.key, "identity_sha256": None if unit.identity is None else unit.identity.digest,
            "reason": reason, "blocking": sorted(blocking)})

    def _closed_phase(self, phase):
        return next((name for name, phases in CLOSURES.items() if phase in phases and self.gate(name)), None)

    def reopen(self, unit, *, reason):
        """Move an abandonment aside after a documented amendment; the record is retained."""
        if self._closed_phase(unit.phase):
            raise ProvenanceError(f"{unit.phase} is closed; its units cannot be reopened (C6)")
        path = self._path("abandoned", f"{_digest(unit.key)}.json")
        if not path.exists() or not reason:
            raise ProvenanceError("Only an abandoned unit can be reopened, with a documented reason")
        target = self._path("reopened", _digest(unit.key), f"{uuid4().hex}.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        _atomic_publish(target.with_suffix(".reason.json"), {"unit": unit.key, "reason": reason,
                                                             "utc": datetime.now(timezone.utc).isoformat()})
        path.rename(target)

    def abandoned_identities(self):
        return frozenset(unit.identity.digest for unit in self.schedule.units
                         if unit.identity is not None and self.abandoned(unit) is not None)

    def close_fits(self):
        record = self.close("fits", CLOSURES["fits"])
        self.cost_report()
        return record

    def close_evaluation(self):
        return self.close("evaluation", CLOSURES["evaluation"])

    def _retries(self, unit):
        return 0 if unit.identity is None else self.journal.quarantined(unit.identity, evaluation=unit.evaluation)

    def state(self, unit):
        """complete | failed (terminal) | abandoned | retry | interrupted | awaiting_amendment | pending."""
        if self.abandoned(unit) is not None:
            return "abandoned"
        record = self._record(unit)
        if record is None and unit.identity is not None:
            bound = self.journal._pending_amendment(unit.identity.digest, unit.evaluation)
            if bound is not None and bound != self.journal.seal.digest:
                return "awaiting_amendment"  # quarantined for a code repair; never re-run under this seal
        if record is None:
            return "interrupted" if self._interrupted(unit) else "pending"
        status, evidence = record
        if status == "complete":
            return "complete"
        kind = evidence.get("error", {}).get("type")
        return "retry" if kind in RETRYABLE and self._retries(unit) < MAX_RETRIES else "failed"

    def terminal(self, unit):
        return self.state(unit) in {"complete", "failed", "abandoned"}

    # -- locks -----------------------------------------------------------------------------------
    @contextmanager
    def _lock(self, path, mode):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as handle:
            try:
                fcntl.flock(handle, mode | fcntl.LOCK_NB)
            except BlockingIOError:
                yield False
                return
            try:
                yield True
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def _host(self, unit):
        return self._lock(self._path("host.lock"), fcntl.LOCK_SH)

    def _lease(self, unit):
        return self._lock(self._path("leases", f"{_digest(unit.key)}.lock"), fcntl.LOCK_EX)

    @contextmanager
    def _slot(self):
        """C4: hold one of the registered worker slots for the whole session, or refuse to start."""
        for index in range(self.workers):
            with self._lock(self._path("slots", f"{index}.lock"), fcntl.LOCK_EX) as held:
                if held:
                    yield index
                    return
        raise ProvenanceError(f"All {self.workers} registered worker slots are in use (C4)")

    # -- graceful pause --------------------------------------------------------------------------
    def request_stop(self, *, reason):
        """Pause between units: running workers finish their current unit, then stop taking work."""
        if not reason:
            raise ProvenanceError("A stop request needs a reason")
        _atomic_publish(self._path("stop", "request.json"),
                        {"reason": reason, "utc": datetime.now(timezone.utc).isoformat()})

    def clear_stop(self):
        path = self._path("stop", "request.json")
        if path.exists():
            target = self._path("stop", f"cleared-{uuid4().hex}.json")
            path.rename(target)

    def stop_requested(self):
        return self._path("stop", "request.json").exists()

    # -- gates -----------------------------------------------------------------------------------
    def gate(self, name):
        path = self._path("gates", f"{name}.json")
        return json.loads(path.read_text()) if path.exists() else None

    def close(self, name, phases):
        """Record that every unit in the phases is terminal; list abandoned and failed identities."""
        units = [unit for phase in phases for unit in self.schedule.phase(phase)]
        open_units = [unit.key for unit in units if not self.terminal(unit)]
        if open_units:
            raise ProvenanceError(f"{len(open_units)} units are not terminal; cannot close {name}")
        states = {unit.key: self.state(unit) for unit in units}
        outcomes = {}
        for unit in units:
            if unit.identity is None:
                continue
            path = self.journal._record_path("outcomes", unit.identity, unit.evaluation)
            outcomes[unit.identity.digest] = (self.journal.terminal_evidence(unit.identity,
                                                                             evaluation=unit.evaluation)[2]
                                              if path.exists() else None)
        outcome_map = self._path("gates", f"{name}.outcomes.json")
        self._publish_exact(outcome_map, dict(sorted(outcomes.items())))
        record = {"gate": name, "phases": list(phases), "schedule_sha256": self.schedule.digest,
                  "outcomes_sha256": _digest(dict(sorted(outcomes.items()))),
                  "counts": {state: sum(1 for value in states.values() if value == state)
                             for state in ("complete", "failed", "abandoned")},
                  "incomplete_identity_sha256": sorted(unit.identity.digest for unit in units
                                                       if unit.identity is not None and states[unit.key] != "complete"),
                  "abandoned_identity_sha256": sorted(unit.identity.digest for unit in units
                                                      if unit.identity is not None and states[unit.key] == "abandoned"),
                  "terminal_sha256": _digest(sorted(states.items()))}
        self._publish_exact(self._path("gates", f"{name}.json"), record)
        return record

    def approve(self, name, *, approver, note):
        """Explicit human approval of a stop gate. Approval never cites outer-test results."""
        if self.gate(name) is None or not approver or not note:
            raise ProvenanceError("Only a closed gate can be approved, with an approver and note")
        self._publish_exact(self._path("gates", f"{name}.approval.json"),
                            {"gate": name, "gate_sha256": _digest(self.gate(name)), "approver": approver,
                             "note": note, "utc": datetime.now(timezone.utc).isoformat()})

    def _require_phase_open(self, phase):
        def approved(name):
            return self._path("gates", f"{name}.approval.json").exists()

        if PHASES.index(phase) > PHASES.index("canary") and not approved("canary"):
            raise ProvenanceError("The canary stop gate has not been approved")
        if phase == "evaluation" and self.gate("fits") is None:
            raise ProvenanceError("Fit and diagnostic phases are not closed")
        closed = self._closed_phase(phase)
        if closed:
            raise ProvenanceError(f"{phase} is closed by the {closed} closure record; nothing in it runs again (C6)")
        require_fit_threads()

    # -- execution -------------------------------------------------------------------------------
    def _blocked(self, unit):
        states = {key: self.state(self.schedule.by_key[key]) for key in unit.requires}
        failed = sorted(key for key, state in states.items() if state in {"failed", "abandoned"})
        waiting = [key for key, state in states.items() if state != "complete" and key not in failed]
        return failed, waiting

    def run(self, phase, *, limit=None):
        """Work through one phase once. Returns this session's record (no outer-test values)."""
        if phase not in PHASES:
            raise ValueError("Unknown phase")
        self._require_phase_open(phase)
        with self._slot() as slot:
            return self._run(phase, limit, slot)

    def _run(self, phase, limit, slot):
        session = Session(phase)
        session.slot = slot
        executed = session.executed
        for unit in self.schedule.phase(phase):
            if limit is not None and sum(executed.values()) >= limit:
                break
            if self.stop_requested():
                session.stopped = True
                break
            state = self.state(unit)
            if state in {"complete", "failed", "abandoned", "awaiting_amendment"}:
                continue
            failed, waiting = self._blocked(unit)
            if failed:
                self._abandon(unit, "blocked by a terminal failed or abandoned dependency", failed)
                executed["abandoned"] = executed.get("abandoned", 0) + 1
                continue
            if waiting:
                continue
            with self._lease(unit) as leased:
                if not leased:
                    continue
                with self._host(unit) as hosted:
                    if not hosted:
                        continue
                    state = self.state(unit)
                    if state == "interrupted" and self._retries(unit) >= MAX_RETRIES:
                        # C3: interruptions share the two-retry budget with infrastructure failures.
                        self._abandon(unit, f"retry budget exhausted: interrupted after {MAX_RETRIES} "
                                            "same-identity retries (C3)")
                        executed["abandoned"] = executed.get("abandoned", 0) + 1
                        continue
                    if state in {"interrupted", "retry"}:
                        self.journal.quarantine(unit.identity, evaluation=unit.evaluation,
                                                reason=f"same-identity retry after {state} attempt (v0.3 §2, C3)")
                    elif state != "pending":
                        continue
                    outcome = self._execute(unit)
                    executed[outcome] = executed.get(outcome, 0) + 1
        self._finish(session)
        if phase == "canary" and all(self.terminal(unit) for unit in self.schedule.phase("canary")):
            self.close("canary", ("canary",))
        return session

    def _execute(self, unit):
        try:
            self.executors[unit.kind](unit)
        except Exception as error:
            kind = type(error).__name__
            if unit.kind == "certify" or self._record(unit) is not None:
                return "failed"
            if kind in RETRYABLE:
                raise
            # Refused before any attempt (e.g. a stopped modern family): terminal, never silent.
            self._abandon(unit, f"refused before an attempt: {kind}: {error}")
            return "abandoned"
        return "complete"

    def _finish(self, session):
        record = {"phase": session.phase, "token": session.token, "utc_start": session.utc_start,
                  "utc_end": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": monotonic() - session.started,
                  "executed": session.executed, "registered_workers": self.workers, "slot": session.slot,
                  "stopped_on_request": session.stopped,
                  "schedule_sha256": self.schedule.digest, "registration_sha256": self.registration_sha256}
        _atomic_publish(self._path("sessions", f"{session.token}.json"), record)

    def wall_time(self, phase):
        """Scheduler wall time: first session start to last session end, plus summed session time."""
        records = [json.loads(path.read_text()) for path in self._path("sessions").glob("*.json")]
        records = [record for record in records if record["phase"] == phase]
        if not records:
            return None
        start = min(datetime.fromisoformat(record["utc_start"]) for record in records)
        end = max(datetime.fromisoformat(record["utc_end"]) for record in records)
        return {"span_seconds": (end - start).total_seconds(),
                "session_seconds": sum(record["elapsed_seconds"] for record in records), "sessions": len(records)}

    def scheduler_elapsed(self):
        """Elapsed schedule wall time per registered cost label."""
        mapping = {"selection_cost": ("canary", "inner"), "final_fit_cost": ("final",),
                   "diagnostic_cost": ("diagnostics",)}
        result = {}
        for label, phases in mapping.items():
            values = [self.wall_time(phase) for phase in phases]
            if any(value is not None for value in values):
                result[label] = sum(value["span_seconds"] for value in values if value is not None)
        return result

    def cost_report(self):
        """C2: training costs over every fit and diagnostic unit in the journal.

        Grouped by block, arm, formulation and phase. Seconds come from each terminal outcome's
        journalled timing; quarantined attempts are counted (their records stay in the quarantine).
        """
        import math

        if self.gate("fits") is None:
            raise ProvenanceError("The cost report requires the closed fit phases")
        groups = {}
        for unit in self.schedule.units:
            if unit.kind not in ("fit", "diagnostic"):
                continue
            identity = unit.identity
            key = "/".join((identity.block, identity.arm, identity.formulation, identity.phase))
            group = groups.setdefault(key, {"complete": 0, "failed": 0, "abandoned": 0, "quarantined_attempts": 0,
                                            "complete_seconds": {}, "failed_seconds": {}})
            group["quarantined_attempts"] += self._retries(unit)
            state = self.state(unit)
            if state == "abandoned" or self._record(unit) is None:
                group["abandoned"] += 1
                continue
            status, evidence, _ = self.journal.terminal_evidence(identity)
            timings = (evidence.get("timing_seconds", {}) if identity.arm != "diagnostic" else
                       {"diagnostic_seconds": evidence["diagnostic_seconds"]} if "diagnostic_seconds" in evidence else {})
            bucket = "complete" if status == "complete" else "failed"
            group[bucket] += 1
            for name, value in timings.items():
                group[f"{bucket}_seconds"].setdefault(name, []).append(value)
        for group in groups.values():
            for bucket in ("complete_seconds", "failed_seconds"):
                group[bucket] = {name: math.fsum(values) for name, values in sorted(group[bucket].items())}
        record = {"schedule_sha256": self.schedule.digest, "registered_workers": self.workers,
                  "scheduler_elapsed": self.scheduler_elapsed(), "groups": dict(sorted(groups.items()))}
        self._publish_exact(self._path("costs.json"), record)
        return record


# -- production executors (used only by scientific execution) --------------------------------------
def persist_resume_state(journal, identity, result):
    """Keep the terminal training state (hash-bound) so diagnostics survive a worker crash."""
    evidence, _ = journal.completed_evidence(identity)
    if sha256(result.resume_state).hexdigest() != evidence["resume_state_sha256"]:
        raise ProvenanceError("Resume state differs from its journalled hash")
    path = journal._path("resume_states", f"{identity.digest}.pt")
    try:
        _atomic_publish_bytes(path, result.resume_state)
    except DuplicateIdentity:
        if sha256_file(path) != evidence["resume_state_sha256"]:
            raise ProvenanceError("Existing resume state differs") from None
    return path


def restore_live_state(journal, identity):
    """Rebuild live model, optimizer and shuffle generator from the persisted terminal state."""
    import torch

    from .models.lstm import LSTM

    evidence, _ = journal.completed_evidence(identity)
    path = journal._path("resume_states", f"{identity.digest}.pt")
    encoded = path.read_bytes()
    if sha256(encoded).hexdigest() != evidence["resume_state_sha256"]:
        raise ProvenanceError("Persisted resume state differs from the final fit")
    state = torch.load(io.BytesIO(encoded), weights_only=True)
    model = LSTM(formulation=identity.formulation, block=identity.block, tasks=identity.tasks,
                 hidden_size=identity.hidden_size)
    model.load_state_dict(state["model"])
    model.train(state["model_training"])
    optimizer = torch.optim.Adam(model.parameters(), lr=_CONFIG["lstm"]["learning_rate"])
    optimizer.load_state_dict(state["optimizer"])
    generator = torch.Generator(device="cpu")
    generator.set_state(state["rng"]["shuffle"])
    return model, optimizer, generator


class ProductionExecutors(dict):
    """Unit-kind executors over frozen adapters. Never returns or logs outer-test values."""

    def __init__(self, journal, *, partitions=None):
        from .data_adapters import adapter_for

        super().__init__(certify=self.certify, fit=self.fit, diagnostic=self.diagnostic, evaluate=self.evaluate)
        self.journal = journal
        self._adapters = {}
        self._partitions = partitions or (lambda block, entity, fold, phase: self._adapter(block, adapter_for)
                                          .prepare(entity, fold, phase))

    def _adapter(self, block, factory):
        if block not in self._adapters:
            self._adapters[block] = factory(block)
        return self._adapters[block]

    def partition(self, identity, phase=None):
        return self._partitions(identity.block, identity.entity, identity.fold, phase or identity.phase)

    def certify(self, unit):
        from .modern.runner import ModernRunner
        ModernRunner(self.journal).validate_family(unit.key.split(":", 1)[1])

    def fit(self, unit):
        identity = unit.identity
        partition = self.partition(identity)
        if identity.arm == "modern":
            from .modern.runner import ModernRunner
            runner = ModernRunner(self.journal)
            (runner.fit_inner if identity.phase == "inner" else runner.fit_final)(identity, partition)
            return
        from .training import TrainingEngine
        engine = TrainingEngine(self.journal)
        mode = identity.variant if identity.arm == "intervention" else "equal_loss"
        result = (engine.fit_inner if identity.phase == "inner" else engine.fit_final)(identity, partition, mode=mode)
        if (identity.phase == "final" and identity.arm in {"core", "intervention"}
                and identity.formulation in _CONFIG["diagnostics"]["formulations"]):
            persist_resume_state(self.journal, identity, result)

    def diagnostic(self, unit):
        from .diagnostics.engine import DiagnosticEngine

        parent = diagnostic_parent(unit.identity)
        live, optimizer, generator = restore_live_state(self.journal, parent)
        DiagnosticEngine(self.journal).run(unit.identity, self.partition(parent), live, optimizer, generator)

    def evaluate(self, unit):
        identity = unit.identity
        partition = self.partition(identity, "final")
        from .evaluation import OuterEvaluator
        OuterEvaluator(self.journal).evaluate(identity, partition)
