"""Stage 4A launcher: gates, supervision, guards, recovery and registration checks.

Generated data, scratch journals and recorded API responses only; the real runtime is never created.
"""

import fcntl
import html
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from fgcs_strengthening_v03 import launch_stage4a as launcher
from fgcs_strengthening_v03.src.identity import HOME, ROOT

FIXTURE = [sys.executable, "-B", "-m", "fgcs_strengthening_v03.tests.launcher_fixture"]


def fake_worker(code):
    return [sys.executable, "-c", code]


class LauncherGateTests(unittest.TestCase):
    def test_unlock_flag_must_be_a_single_explicit_line(self):
        with tempfile.TemporaryDirectory() as scratch:
            path = Path(scratch) / "evidence.md"
            for text, expected in (("x\nEXECUTION_UNLOCKED = NO\n", False), ("EXECUTION_UNLOCKED = YES\n", True)):
                path.write_text(text)
                self.assertIs(launcher.execution_unlocked(path), expected)
            for text in ("nothing here\n", "EXECUTION_UNLOCKED = YES\nEXECUTION_UNLOCKED = NO\n",
                         "EXECUTION_UNLOCKED = yes\n", "EXECUTION_UNLOCKED = MAYBE\n"):
                path.write_text(text)
                with self.assertRaises(launcher.LaunchRefused):
                    launcher.execution_unlocked(path)

    def test_thread_variables_are_required(self):
        launcher.require_thread_env(dict(launcher.THREAD_ENV))
        for key in launcher.THREAD_ENV:
            for value in (None, "2", ""):
                env = dict(launcher.THREAD_ENV)
                if value is None:
                    env.pop(key)
                else:
                    env[key] = value
                with self.assertRaises(launcher.LaunchRefused):
                    launcher.require_thread_env(env)

    def test_locked_execution_refuses_without_creating_a_runtime(self):
        runtime = HOME / "runtime"
        existed = runtime.exists()
        with patch.object(launcher, "execution_unlocked", return_value=False):
            for argv in (["stage4a"], ["run", "--phase", "canary"], ["status"], ["stop", "--reason", "x"],
                         ["recover-check"], ["resume"], ["approve-canary", "--approver", "a", "--note", "n"]):
                self.assertEqual(launcher.main(argv), 2, argv)
        self.assertEqual(runtime.exists(), existed)

    def test_repository_gate_matches_the_registered_tag(self):
        self.assertEqual(launcher.check_repository()["tag_commit"], launcher.REGISTERED_COMMIT)

    def test_power_disk_and_systems_gates(self):
        launcher.require_ac_power(lambda: True)
        for state in (False, None):
            with self.assertRaises(launcher.LaunchRefused):
                launcher.require_ac_power(lambda: state)
        launcher.require_free_disk(15, lambda: 16e9)
        with self.assertRaises(launcher.LaunchRefused):
            launcher.require_free_disk(15, lambda: 14e9)
        ok = dict(thermal=lambda: 0, load=lambda: [0.5, 0, 0], power=lambda: True)
        launcher.require_systems_conditions(**ok)
        for change in (dict(thermal=lambda: 2), dict(thermal=lambda: None), dict(load=lambda: [3.0, 0, 0]),
                       dict(power=lambda: False)):
            with self.assertRaises(launcher.LaunchRefused):
                launcher.require_systems_conditions(**{**ok, **change})

    def test_runtime_is_git_ignored(self):
        result = subprocess.run(["git", "check-ignore", "-q", "fgcs_strengthening_v03/runtime/outcomes/x.json"],
                                cwd=ROOT)
        self.assertEqual(result.returncode, 0)

    def test_host_probes_are_read_only_and_parse(self):
        self.assertIn(launcher.on_ac_power(), (True, False, None))
        self.assertIn(launcher.thermal_state(), (0, 1, 2, 3, None))
        self.assertGreater(launcher.free_bytes(), 0)


class MonitorTests(unittest.TestCase):
    def test_low_disk_requests_one_stop(self):
        calls = []
        monitor = launcher.Monitor(request_stop=calls.append, free=lambda: 10e9, power=lambda: True,
                                   thermal=lambda: 0, load=lambda: [0, 0, 0])
        self.assertIn("free disk", monitor.check())
        self.assertIsNone(monitor.check())  # already stopped: no second request
        self.assertEqual(len(calls), 1)

    def test_battery_grace_period(self):
        calls, now = [], {"t": 0.0}
        power = {"ac": False}
        monitor = launcher.Monitor(request_stop=calls.append, free=lambda: 100e9, power=lambda: power["ac"],
                                   clock=lambda: now["t"], battery_grace=120)
        self.assertIsNone(monitor.check())
        now["t"] = 60
        self.assertIsNone(monitor.check())
        power["ac"] = True  # back on AC resets the grace period
        self.assertIsNone(monitor.check())
        power["ac"], now["t"] = False, 100
        self.assertIsNone(monitor.check())
        now["t"] = 221
        self.assertIn("battery", monitor.check())
        self.assertEqual(len(calls), 1)

    def test_health_snapshots_track_disk_growth(self):
        with tempfile.TemporaryDirectory() as scratch:
            free, now = {"b": 100e9}, {"t": 0.0}
            monitor = launcher.Monitor(request_stop=lambda r: None, health_dir=Path(scratch), phase="inner",
                                       count_outcomes=lambda: 7, free=lambda: free["b"], power=lambda: True,
                                       thermal=lambda: 0, load=lambda: [1.0, 1.0, 1.0], clock=lambda: now["t"])
            first = monitor.snapshot(4, False)
            self.assertIsNone(first["disk_use_bytes_per_hour"])
            free["b"], now["t"] = 99e9, 3600.0
            second = monitor.snapshot(4, False)
            self.assertAlmostEqual(second["disk_use_bytes_per_hour"], 1e9)
            self.assertAlmostEqual(second["hours_until_disk_guard"], (99e9 - 15e9) / 1e9)
            rows = [json.loads(line) for path in Path(scratch).glob("*.jsonl") for line in path.read_text().splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertEqual({row["outcomes"] for row in rows}, {7})

    def test_keep_awake_holds_and_releases_an_assertion(self):
        with launcher.keep_awake(("caffeinate", "-i")) as process:
            self.assertIsNotNone(process)
            self.assertIsNone(process.poll())
        self.assertIsNotNone(process.poll())


class RegistrationVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fields = json.loads(launcher.OSF_FIELDS.read_text())
        responses = {key: html.escape(value, quote=False) for key, value in fields["registration_responses"].items()}
        names = [Path(path).name for path in fields["attachments"]]
        hashes = {Path(path).name: launcher._sha256(ROOT / path) for path in fields["attachments"]}
        responses["72-22"] = [{"file_name": name, "file_hashes": {"sha256": hashes[name]}} for name in names[:5]]
        responses["72-26"] = [{"file_name": name, "file_hashes": {"sha256": hashes[name]}} for name in names[5:]]
        cls.osf = {"data": {"attributes": {
            "public": True, "pending_registration_approval": False, "withdrawn": False, "embargo_end_date": None,
            "date_registered": "2026-11-13T12:36:33", "title": fields["metadata"]["title"],
            "description": fields["metadata"]["description"], "registration_responses": responses},
            "embeds": {"identifiers": {"data": [{"attributes": {"category": "doi", "value": "10.17605/OSF.IO/KUWRA"}}]}}}}
        uploads = json.loads(launcher.UPLOAD_LIST.read_text())["uploads"]
        cls.zenodo = {"entries": [{"key": item["upload_filename"], "size": item["size_bytes"],
                                   "checksum": "md5:" + launcher._md5(ROOT / item["source_path"])} for item in uploads]}

    def verify(self, osf=None, zenodo=None):
        osf, zenodo = osf or self.osf, zenodo or self.zenodo
        return launcher.verify_registration(fetch=lambda url: json.loads(json.dumps(osf if "osf" in url else zenodo)))

    def test_public_matching_registration_passes(self):
        passed, report = self.verify()
        self.assertTrue(passed, report["problems"])
        self.assertEqual(report["responses_sha256"], report["expected_responses_sha256"])
        self.assertTrue(report["responses_sha256"].startswith("f457dd928bae4a85"))

    def mutate(self, change):
        osf = json.loads(json.dumps(self.osf))
        change(osf["data"])
        return self.verify(osf=osf)

    def test_pending_undoi_changed_or_mismatched_registrations_fail(self):
        cases = {
            "pending": lambda d: d["attributes"].update(public=False, pending_registration_approval=True),
            "no DOI": lambda d: d["embeds"]["identifiers"].update(data=[]),
            "changed response": lambda d: d["attributes"]["registration_responses"].update({"72-46": "edited"}),
            "changed title": lambda d: d["attributes"].update(title="Other"),
            "attachment hash": lambda d: d["attributes"]["registration_responses"]["72-22"][0]["file_hashes"]
            .update(sha256="0" * 64),
            "withdrawn": lambda d: d["attributes"].update(withdrawn=True),
        }
        for name, change in cases.items():
            passed, report = self.mutate(change)
            self.assertFalse(passed, name)

    def test_zenodo_file_change_fails(self):
        zenodo = json.loads(json.dumps(self.zenodo))
        zenodo["entries"][0]["size"] += 1
        passed, report = self.verify(zenodo=zenodo)
        self.assertFalse(passed)
        self.assertFalse(report["zenodo_files_match"])


class LauncherWorkerTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(dir=HOME)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        (self.root / "registration.txt").write_text("synthetic registration record\n")
        self.logs = self.root / "logs"

    def open(self):
        from fgcs_strengthening_v03.tests.launcher_fixture import open_orchestrator
        return open_orchestrator(self.scratch.name)

    def scratch_home(self):
        return patch("fgcs_strengthening_v03.src.provenance.HOME", self.root)

    def test_four_worker_processes_complete_the_canary_once(self):
        state, rounds = launcher.launch("canary", worker_command=[*FIXTURE, self.scratch.name], log_dir=self.logs,
                                        request_stop=lambda reason: self.fail("no stop expected"), log=lambda *_: None)
        self.assertEqual(state, "complete", rounds)
        workers = rounds[0]["workers"]
        self.assertEqual(len(workers), 4)
        # Each worker held one of the four registered slot locks (a slot freed early may be reused).
        self.assertTrue({worker["slot"] for worker in workers} <= {0, 1, 2, 3})
        with self.scratch_home():
            orch = self.open()
            units = orch.schedule.phase("canary")
            self.assertTrue(all(orch.state(unit) == "complete" for unit in units))
            self.assertEqual([orch.journal.quarantined(unit.identity) for unit in units], [0] * len(units))
            self.assertEqual(orch.gate("canary")["counts"], {"complete": len(units), "failed": 0, "abandoned": 0})
            self.assertEqual(sum(sum(worker["executed"].values()) for round_ in rounds
                                 for worker in round_["workers"]), len(units))  # each unit fitted exactly once
            report = launcher.recovery_report(self.root / "runtime")
            self.assertEqual((report["verdict"], report["interrupted_attempts"]), ("OK", 0))
        self.assertEqual(len(list(self.logs.glob("*.err"))), 4)

    def test_active_stop_request_runs_nothing(self):
        with self.scratch_home():
            launcher.safe_request_stop(self.open(), "planned pause")
            self.assertFalse(launcher.safe_request_stop(self.open(), "second request is ignored"))
        state, rounds = launcher.launch("canary", worker_command=[*FIXTURE, self.scratch.name], log_dir=self.logs,
                                        request_stop=lambda reason: None, log=lambda *_: None)
        self.assertEqual(state, "stopped")
        self.assertTrue(all(worker["state"] == "stopped" and not worker["executed"] for worker in rounds[0]["workers"]))

    def test_disk_guard_stops_workers_gracefully(self):
        with self.scratch_home():
            orch = self.open()
        monitor = launcher.Monitor(request_stop=None, health_dir=self.root / "health", phase="canary",
                                   free=lambda: 1e9, power=lambda: True, thermal=lambda: 0, load=lambda: [0, 0, 0])

        def request(reason):
            with self.scratch_home():
                launcher.safe_request_stop(orch, reason)

        state, rounds = launcher.launch("canary", worker_command=[*FIXTURE, self.scratch.name], log_dir=self.logs,
                                        request_stop=request, monitor=monitor, log=lambda *_: None)
        self.assertEqual(state, "stopped")
        self.assertIn("free disk", monitor.stopped_reason)
        with self.scratch_home():
            orch = self.open()
            self.assertTrue(orch.stop_requested())
            self.assertEqual(sum(orch.journal.quarantined(unit.identity) for unit in orch.schedule.phase("canary")), 0)
        self.assertGreaterEqual(len(list((self.root / "health").glob("*.jsonl"))), 1)

    def test_signals_become_a_graceful_stop_and_workers_are_not_killed(self):
        sleeper = fake_worker("import json, sys, time; time.sleep(1.5); "
                              "print(json.dumps({'state': 'stopped', 'executed': {}})); sys.exit(3)")
        for signum in (signal.SIGINT, signal.SIGHUP, signal.SIGTERM):
            calls = []
            timer = threading.Timer(0.4, lambda: os.kill(os.getpid(), signum))
            timer.start()
            state, rounds = launcher.launch("canary", worker_command=sleeper, request_stop=calls.append, workers=4,
                                            log_dir=self.logs, log=lambda *_: None, poll_seconds=0.1)
            timer.join()
            self.assertEqual(len(calls), 1, signum)
            self.assertEqual(state, "stopped")
            self.assertEqual([worker["returncode"] for worker in rounds[0]["workers"]], [3, 3, 3, 3])

    def test_chatty_workers_cannot_block_the_controller(self):
        noisy = fake_worker("import json, sys; sys.stderr.write('x' * 2_000_000); sys.stdout.write('y' * 500_000 + '\\n'); "
                            "print(json.dumps({'state': 'complete', 'executed': {'complete': 1}})); sys.exit(0)")
        state, rounds = launcher.launch("canary", worker_command=noisy, request_stop=lambda r: None, workers=4,
                                        log_dir=self.logs, log=lambda *_: None, poll_seconds=0.1)
        self.assertEqual(state, "complete")
        self.assertEqual(sorted(path.stat().st_size for path in self.logs.glob("*.err")), [2_000_000] * 4)

    def test_pid_records_and_recovery_report(self):
        runtime = self.root / "runtime"
        with self.scratch_home():
            orch = self.open()
            from fgcs_strengthening_v03.tests.launcher_fixture import tiny_canary
            unit = tiny_canary().units[0]
            orch.journal.start(unit.identity)  # a worker died mid-fit
        workers = runtime / "launcher" / "workers"
        workers.mkdir(parents=True)
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        (workers / f"{dead.pid}.json").write_text(json.dumps({"pid": dead.pid, "phase": "canary"}))
        report = launcher.recovery_report(runtime)
        self.assertEqual(report["interrupted_attempts"], 1)
        self.assertEqual(report["stale_worker_records"], [dead.pid])
        self.assertEqual(report["verdict"], "OK")
        (runtime / "modern" / "DLinear").mkdir(parents=True)
        (runtime / "modern" / "DLinear" / "active.json").write_text("{}")
        lock = runtime / "orchestrator" / "slots" / "0.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with lock.open("a+b") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            report = launcher.recovery_report(runtime)
            self.assertEqual(report["slots_held"], [0])
        self.assertEqual(report["modern_family_markers"], {"DLinear": ["active.json"]})
        self.assertEqual(report["verdict"], "REVIEW_REQUIRED")
        self.assertEqual(len(report["blocking"]), 2)

    def test_worker_processes_are_single_threaded(self):
        result = subprocess.run([sys.executable, "-B", "-c",
                                 "from fgcs_strengthening_v03.src.orchestrator import "
                                 "configure_worker_process, require_fit_threads; "
                                 "configure_worker_process(); import json; print(json.dumps(require_fit_threads()))"],
                                cwd=launcher.ROOT, env=launcher.worker_env(), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        threads = json.loads(result.stdout)
        self.assertEqual((threads["torch_intra_op"], threads["torch_inter_op"], threads["device"]), (1, 1, "cpu"))


if __name__ == "__main__":
    unittest.main()
