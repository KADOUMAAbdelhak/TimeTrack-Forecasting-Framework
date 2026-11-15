"""Orchestration on a tiny schedule of real generated fits, plus the production schedule's exact shape."""

from collections import Counter
from contextlib import contextmanager
from dataclasses import replace
import fcntl
from functools import lru_cache
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fgcs_strengthening_v04.src.identity import HOME, RESOURCES, ScientificIdentity
from fgcs_strengthening_v04.src.orchestrator import (
    FIT_PHASES, MAX_RETRIES, PHASES, TRAINING_WORKERS, Orchestrator, ProductionExecutors, Schedule, Unit, _digest, canary_identities,
    execution_fingerprints, execution_sources, registered_schedule, systems_population,
)
from fgcs_strengthening_v04.src.provenance import Fingerprints, Journal, ProvenanceError
from fgcs_strengthening_v04.tests.test_evaluation import heldout
from fgcs_strengthening_v04.tests.training_fixtures import identity, scratch_engine


@lru_cache(maxsize=1)
def seal():
    return execution_fingerprints()


def provider(block, entity, fold, phase):
    unit = ScientificIdentity(block, entity, fold, 0, phase, "core", "M1", RESOURCES, "all", 64, "baseline")
    return heldout(unit)[0]


def tiny_schedule():
    s1, m1 = identity("S1"), identity("M1")
    s1f, m1f = replace(s1, phase="final"), replace(m1, phase="final")
    diagnostic = replace(m1f, arm="diagnostic", variant="final")
    return Schedule([
        Unit("fit", "canary", s1.digest, s1),
        Unit("fit", "inner", m1.digest, m1),
        Unit("fit", "final", s1f.digest, s1f, (s1.digest,)),
        Unit("fit", "final", m1f.digest, m1f, (m1.digest,)),
        Unit("diagnostic", "diagnostics", diagnostic.digest, diagnostic, (m1f.digest,)),
        Unit("systems", "systems", "systems:test", None, (s1f.digest, m1f.digest), ()),
        Unit("evaluate", "evaluation", "evaluate:" + s1f.digest, s1f, (s1f.digest,)),
        Unit("evaluate", "evaluation", "evaluate:" + m1f.digest, m1f, (m1f.digest,)),
    ])


class OrchestratorTests(unittest.TestCase):
    @contextmanager
    def orchestrator(self, schedule=None, *, systems=None):
        with scratch_engine(seal()) as engine, tempfile.NamedTemporaryFile(dir=HOME) as registration:
            registration.write(b"synthetic registration record\n")
            registration.flush()
            executors = ProductionExecutors(engine.journal, partitions=provider)
            executors["systems"] = systems or (lambda unit: None)
            # The real thread check needs a fresh process (inter-op pools are fixed at first use); it is
            # exercised in test_fit_workers_must_be_single_threaded.
            stack = patch("fgcs_strengthening_v04.src.orchestrator.require_fit_threads")
            stack.start()
            self.addCleanup(stack.stop)
            yield Orchestrator(engine.journal, schedule or tiny_schedule(), executors,
                               registration=registration.name, workers=4)

    def advance(self, orchestrator, *phases):
        for phase in phases:
            orchestrator.run(phase)

    def test_phases_gates_blinding_resume_state_and_wall_time(self):
        with self.orchestrator() as orch:
            session = orch.run("canary")
            self.assertEqual(session.executed, {"complete": 1})
            self.assertEqual(orch.gate("canary")["counts"], {"complete": 1, "failed": 0, "abandoned": 0})
            with self.assertRaisesRegex(ProvenanceError, "canary"):
                orch.run("inner")
            orch.approve("canary", approver="author", note="technical checks reviewed; no outer test exists")
            self.advance(orch, "inner", "final", "diagnostics")
            journal = orch.journal
            self.assertTrue(journal._path("resume_states", f"{replace(identity('M1'), phase='final').digest}.pt")
                            .is_file())
            for phase in ("systems", "evaluation"):
                with self.assertRaisesRegex(ProvenanceError, "not closed"):
                    orch.run(phase)
            orch.close_fits()
            self.advance(orch, "systems", "evaluation")
            orch.close_evaluation()
            self.assertTrue(all(orch.state(unit) == "complete" for unit in orch.schedule.units))
            sessions = [json.loads(path.read_text()) for path in journal._path("orchestrator", "sessions").glob("*")]
            self.assertEqual(len(sessions), 6)  # refused runs open no session
            self.assertNotIn("mae", json.dumps(sessions))
            self.assertEqual({record["registered_workers"] for record in sessions}, {4})
            self.assertEqual(set(orch.scheduler_elapsed()), {"selection_cost", "final_fit_cost", "diagnostic_cost"})
            self.assertGreaterEqual(orch.wall_time("final")["span_seconds"], 0)
            costs = json.loads(journal._path("orchestrator", "costs.json").read_text())
            m1 = identity("M1")
            group = costs["groups"][f"{m1.block}/core/M1/final"]
            self.assertEqual((group["complete"], group["failed"], group["abandoned"]), (1, 0, 0))
            self.assertGreater(group["complete_seconds"]["elapsed"], 0)
            self.assertEqual(sum(g["complete"] for g in costs["groups"].values()), 5)  # every fit, not a sample
            self.assertEqual(costs["registered_workers"], TRAINING_WORKERS)

    def test_worker_count_slots_and_graceful_stop(self):
        with self.orchestrator() as orch:
            with self.assertRaisesRegex(ValueError, "registered worker count"):
                Orchestrator(orch.journal, orch.schedule, orch.executors,
                             registration=__file__,
                             workers=2)
            handles = []
            for index in range(TRAINING_WORKERS):
                path = orch._path("slots", f"{index}.lock")
                path.parent.mkdir(parents=True, exist_ok=True)
                handle = path.open("a+b")
                fcntl.flock(handle, fcntl.LOCK_EX)
                handles.append(handle)
            with self.assertRaisesRegex(ProvenanceError, "worker slots"):
                orch.run("canary")
            handles.pop().close()  # one slot frees
            orch.request_stop(reason="planned pause")
            session = orch.run("canary")
            self.assertEqual((session.executed, session.stopped, session.slot), ({}, True, TRAINING_WORKERS - 1))
            orch.clear_stop()
            self.assertEqual(orch.run("canary").executed, {"complete": 1})
            for handle in handles:
                handle.close()

    def test_interruptions_share_the_retry_budget(self):
        with self.orchestrator() as orch:
            self.advance(orch, "canary")
            orch.approve("canary", approver="author", note="ok")
            m1 = identity("M1")
            unit = orch.schedule.by_key[m1.digest]
            for attempt in range(MAX_RETRIES + 1):
                with patch("fgcs_strengthening_v04.src.training._optimise_epoch", side_effect=KeyboardInterrupt):
                    with self.assertRaises(KeyboardInterrupt):
                        orch.run("inner")
                self.assertEqual((orch.state(unit), orch.journal.quarantined(m1)), ("interrupted", attempt))
            session = orch.run("inner")
            self.assertEqual(session.executed, {"abandoned": 1})
            self.assertEqual(orch.state(unit), "abandoned")
            self.assertIn("retry budget exhausted", orch.abandoned(unit)["reason"])
            self.advance(orch, "final", "diagnostics")
            record = orch.close_fits()
            self.assertIn(m1.digest, record["abandoned_identity_sha256"])

    def test_interrupted_and_infrastructure_failures_retry_twice_then_stop(self):
        with self.orchestrator() as orch:
            self.advance(orch, "canary")
            orch.approve("canary", approver="author", note="ok")
            self.advance(orch, "inner")
            s1f = replace(identity("S1"), phase="final")
            orch.journal.start(s1f)  # a worker died after claiming the identity
            with patch("fgcs_strengthening_v04.src.training._optimise_epoch", side_effect=OSError("disk")):
                session = orch.run("final")
            unit = orch.schedule.by_key[s1f.digest]
            self.assertEqual(orch.journal.quarantined(s1f), 1)
            self.assertEqual(orch.state(unit), "retry")
            self.assertEqual(session.executed, {"failed": 2})
            with patch("fgcs_strengthening_v04.src.training._optimise_epoch", side_effect=OSError("disk")):
                orch.run("final")
            self.assertEqual((orch.journal.quarantined(s1f), orch.state(unit)), (2, "failed"))
            orch.run("final")
            self.assertEqual(orch.state(unit), "failed")
            quarantine = orch.journal._path("quarantine", s1f.digest, "fit", "01", "quarantine.json")
            self.assertIn("interrupted", json.loads(quarantine.read_text())["reason"])
            self.advance(orch, "diagnostics")
            orch.close_fits()
            self.advance(orch, "systems", "evaluation")
            self.assertEqual(orch.state(orch.schedule.by_key["evaluate:" + s1f.digest]), "abandoned")
            self.assertIn(s1f.digest, orch.abandoned_identities())
            self.assertEqual(orch.state(orch.schedule.by_key["systems:test"]), "abandoned")

    def test_non_retryable_and_pre_attempt_refusals_are_terminal(self):
        with self.orchestrator() as orch:
            self.advance(orch, "canary")
            orch.approve("canary", approver="author", note="ok")
            with patch("fgcs_strengthening_v04.src.training._evaluate", side_effect=ValueError("nonfinite")):
                orch.run("inner")
            m1 = orch.schedule.by_key[identity("M1").digest]
            self.assertEqual(orch.state(m1), "failed")
            original = orch.executors["fit"]
            orch.executors["fit"] = lambda unit: (_ for _ in ()).throw(ProvenanceError("family stopped"))
            orch.run("final")
            s1f = orch.schedule.by_key[replace(identity("S1"), phase="final").digest]
            self.assertEqual(orch.state(s1f), "abandoned")
            self.assertEqual(orch.state(orch.schedule.by_key[replace(identity("M1"), phase="final").digest]),
                             "abandoned")
            orch.reopen(s1f, reason="amended executor repaired a pre-attempt refusal")
            orch.executors["fit"] = original
            orch.run("final")
            self.assertEqual(orch.state(s1f), "complete")

    def test_leases_and_exclusive_host_lock(self):
        held = []
        with self.orchestrator(systems=lambda unit: held.append(unit.key)) as orch:
            self.advance(orch, "canary")
            orch.approve("canary", approver="author", note="ok")
            unit = orch.schedule.by_key[identity("M1").digest]
            lease = orch._path("leases", f"{_digest(unit.key)}.lock")
            lease.parent.mkdir(parents=True, exist_ok=True)
            with lease.open("a+b") as handle:
                fcntl.flock(handle, fcntl.LOCK_EX)
                orch.run("inner")
                self.assertEqual(orch.state(unit), "pending")
            orch.run("inner")
            self.assertEqual(orch.state(unit), "complete")
            self.advance(orch, "final", "diagnostics")
            orch.close_fits()
            host = orch._path("host.lock")
            with host.open("a+b") as handle:
                fcntl.flock(handle, fcntl.LOCK_SH)
                orch.run("systems")
                self.assertEqual(held, [])
            orch.run("systems")
            self.assertEqual(held, ["systems:test"])

    def test_seal_amendment_reruns_only_quarantined_identities(self):
        with self.orchestrator() as orch:
            self.advance(orch, "canary")
            orch.approve("canary", approver="author", note="ok")
            with patch("fgcs_strengthening_v04.src.training._evaluate", side_effect=ValueError("bug")):
                orch.run("inner")
            m1 = identity("M1")
            self.assertEqual(orch.state(orch.schedule.by_key[m1.digest]), "failed")
            journal = orch.journal
            with self.assertRaises(ProvenanceError):
                journal.amend(seal(), reason="fix", affected=[m1])
            with self.assertRaisesRegex(ProvenanceError, "terminal unless repaired"):
                journal.quarantine(m1, reason="same-seal retry of a code failure")
            with tempfile.NamedTemporaryFile(dir=HOME, suffix=".py") as source:
                source.write(b"# repaired source\n")
                source.flush()
                relative = Path(source.name).relative_to(HOME.parent).as_posix()
                successor = Fingerprints.capture_protocol(additional_sources=(*execution_sources(), relative))
                journal.quarantine(m1, reason="documented technical repair of the validation path",
                                   amendment=successor)
                with self.assertRaisesRegex(ProvenanceError, "awaits its sealed amendment"):
                    journal.start(m1)
                self.assertEqual(orch.state(orch.schedule.by_key[m1.digest]), "awaiting_amendment")
                self.assertEqual(orch.run("inner").executed, {})  # the old seal cannot re-run it
                with self.assertRaisesRegex(ProvenanceError, "not terminal"):
                    orch.close("inner-check", ("inner",))
                self.assertFalse(journal._record_path("outcomes", m1, False).exists())
                amended = journal.amend(successor, reason="validation repair", affected=[m1])
                with self.assertRaises(ProvenanceError):
                    Journal(seal())
                executors = ProductionExecutors(amended, partitions=provider)
                registration = orch._path("registration.txt")
                registration.write_text("synthetic registration record\n")
                again = Orchestrator(amended, orch.schedule, executors, registration=registration, workers=4)
                again.run("inner")
                self.assertEqual(again.state(again.schedule.by_key[m1.digest]), "complete")
                s1 = identity("S1")
                status, _, _ = amended.terminal_evidence(s1)
                self.assertEqual(status, "complete")
                record = json.loads(amended._path("outcomes", f"{m1.digest}.json").read_text())
                self.assertEqual(record["fingerprint_sha256"], successor.digest)

    def test_closed_fits_cannot_be_repaired_or_rerun(self):
        """F1 (second audit): no quarantine, reopen, amendment or fit run after fit closure."""
        with self.orchestrator() as orch:
            self.advance(orch, "canary")
            orch.approve("canary", approver="author", note="ok")
            with patch("fgcs_strengthening_v04.src.training._evaluate", side_effect=ValueError("bug")):
                orch.run("inner")
            self.advance(orch, "final", "diagnostics")
            m1, m1f = identity("M1"), replace(identity("M1"), phase="final")
            orch.close_fits()
            self.advance(orch, "systems", "evaluation")
            orch.close_evaluation()
            journal = orch.journal
            with tempfile.NamedTemporaryFile(dir=HOME, suffix=".py") as source:
                source.write(b"# repaired source\n")
                source.flush()
                relative = Path(source.name).relative_to(HOME.parent).as_posix()
                successor = Fingerprints.capture_protocol(additional_sources=(*execution_sources(), relative))
                for evaluation in (False, True):
                    with self.assertRaisesRegex(ProvenanceError, "closed"):
                        journal.quarantine(m1 if not evaluation else m1f, reason="repair", evaluation=evaluation,
                                           amendment=successor)
                with self.assertRaisesRegex(ProvenanceError, "awaits|Quarantine|quarantined"):
                    journal.amend(successor, reason="repair", affected=[m1])
            for unit in (orch.schedule.by_key[m1f.digest], orch.schedule.by_key["evaluate:" + m1f.digest]):
                with self.assertRaisesRegex(ProvenanceError, "closed"):
                    orch.reopen(unit, reason="repair")
            for phase in PHASES:
                with self.assertRaisesRegex(ProvenanceError, "closed"):
                    orch.run(phase)
            gate = orch.gate("fits")
            outcomes = json.loads(orch._path("gates", "fits.outcomes.json").read_text())
            self.assertEqual(_digest(outcomes), gate["outcomes_sha256"])
            self.assertIsNotNone(outcomes[m1.digest])  # the failed outcome is pinned by hash
            self.assertIsNone(outcomes[m1f.digest])  # abandoned: no outcome
            self.assertIn(m1f.digest, gate["abandoned_identity_sha256"])

    def test_fit_workers_must_be_single_threaded(self):
        import os
        import subprocess
        import sys

        code = ("from fgcs_strengthening_v04.src.orchestrator import configure_worker_process, require_fit_threads\n"
                "configure_worker_process()\nprint(require_fit_threads())\n")
        root = str(HOME.parent)
        single = {**os.environ, "PYTHONPATH": root, "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                  "OPENBLAS_NUM_THREADS": "1"}
        result = subprocess.run([sys.executable, "-B", "-c", code], env=single, capture_output=True, cwd=root)
        self.assertEqual(result.returncode, 0, result.stderr.decode()[-2000:])
        self.assertIn("'torch_inter_op': 1", result.stdout.decode())
        threaded = {**single, "OMP_NUM_THREADS": "8"}
        result = subprocess.run([sys.executable, "-B", "-c", code], env=threaded, capture_output=True, cwd=root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("single-threaded", result.stderr.decode())
        unconfigured = "from fgcs_strengthening_v04.src.orchestrator import require_fit_threads\nrequire_fit_threads()\n"
        result = subprocess.run([sys.executable, "-B", "-c", unconfigured], env=single, capture_output=True, cwd=root)
        self.assertNotEqual(result.returncode, 0)  # inter-op pool not configured

    def test_registered_schedule_shape(self):
        schedule = Schedule(registered_schedule())
        counts = {phase: len(schedule.phase(phase)) for phase in PHASES}
        self.assertEqual(counts, {"certify": 3, "canary": 96, "inner": 96_954, "final": 77_450,
                                  "diagnostics": 27_300, "systems": 182, "evaluation": 81_650})
        self.assertEqual(counts["canary"] + counts["inner"], 97_050)
        canary = list(canary_identities())
        self.assertEqual(Counter(unit.arm for unit in canary), {"modern": 30, "core": 60, "capacity": 6})
        self.assertTrue(all(unit.phase == "inner" and unit.seed == 0 and unit.fold == 1 for unit in canary))
        population = dict(systems_population())
        self.assertEqual(len(population), 182)
        self.assertEqual(len(population["TimeTrack", "machine01", 1]), 5)
        self.assertEqual(len(population["fastStorage", "697", 1]), 16)
        self.assertEqual(len(population["fastStorage", "434", 1]), 10)
        self.assertEqual(sum(len(units) for units in population.values()),
                         7 * 5 + 105 * 5 + 70 * 10 + 20 * 6)
        self.assertEqual(set(FIT_PHASES) & {"systems", "evaluation"}, set())


if __name__ == "__main__":
    unittest.main()
