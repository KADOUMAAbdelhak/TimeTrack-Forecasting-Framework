"""Stage 4A launcher: gates, four-process workers, graceful stop. Generated data and scratch journals only."""

import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from fgcs_strengthening_v03 import launch_stage4a as launcher
from fgcs_strengthening_v03.src.identity import HOME

FIXTURE = [sys.executable, "-B", "-m", "fgcs_strengthening_v03.tests.launcher_fixture"]


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
                         ["approve-canary", "--approver", "a", "--note", "n"]):
                self.assertEqual(launcher.main(argv), 2, argv)
        self.assertEqual(runtime.exists(), existed)

    def test_repository_gate_matches_the_registered_tag(self):
        result = launcher.check_repository()
        self.assertEqual(result["tag_commit"], launcher.REGISTERED_COMMIT)


class LauncherWorkerTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(dir=HOME)
        self.addCleanup(self.scratch.cleanup)
        (Path(self.scratch.name) / "registration.txt").write_text("synthetic registration record\n")

    def open(self):
        from fgcs_strengthening_v03.tests.launcher_fixture import open_orchestrator
        return open_orchestrator(self.scratch.name)

    def test_four_worker_processes_complete_the_canary_once(self):
        state, rounds = launcher.launch("canary", worker_command=[*FIXTURE, self.scratch.name],
                                        request_stop=lambda reason: self.fail("no stop expected"), log=lambda *_: None)
        self.assertEqual(state, "complete", rounds)
        workers = rounds[0]["workers"]
        self.assertEqual(len(workers), 4)
        # Each worker held one of the four registered slot locks (a slot freed early may be reused).
        self.assertTrue({worker["slot"] for worker in workers} <= {0, 1, 2, 3})
        with patch("fgcs_strengthening_v03.src.provenance.HOME", Path(self.scratch.name)):
            orch = self.open()
            units = orch.schedule.phase("canary")
            self.assertTrue(all(orch.state(unit) == "complete" for unit in units))
            self.assertEqual([orch.journal.quarantined(unit.identity) for unit in units], [0] * len(units))
            self.assertEqual(orch.gate("canary")["counts"], {"complete": len(units), "failed": 0, "abandoned": 0})
            self.assertEqual(sum(sum(worker["executed"].values()) for round_ in rounds
                                 for worker in round_["workers"]), len(units))  # each unit fitted exactly once

    def test_active_stop_request_runs_nothing(self):
        with patch("fgcs_strengthening_v03.src.provenance.HOME", Path(self.scratch.name)):
            self.open().request_stop(reason="planned pause")
        state, rounds = launcher.launch("canary", worker_command=[*FIXTURE, self.scratch.name],
                                        request_stop=lambda reason: None, log=lambda *_: None)
        self.assertEqual(state, "stopped")
        self.assertTrue(all(worker["state"] == "stopped" and not worker["executed"] for worker in rounds[0]["workers"]))

    def test_interrupt_becomes_a_graceful_stop_and_workers_are_not_killed(self):
        calls = []
        sleeper = [sys.executable, "-c", "import json, sys, time; time.sleep(1.5); "
                   "print(json.dumps({'state': 'stopped', 'executed': {}})); sys.exit(3)"]
        timer = threading.Timer(0.4, lambda: os.kill(os.getpid(), signal.SIGINT))
        timer.start()
        state, rounds = launcher.launch("canary", worker_command=sleeper, request_stop=calls.append,
                                        workers=4, log=lambda *_: None)
        timer.join()
        self.assertEqual(len(calls), 1)
        self.assertEqual(state, "stopped")
        self.assertEqual([worker["returncode"] for worker in rounds[0]["workers"]], [3, 3, 3, 3])

    def test_worker_processes_are_single_threaded(self):
        result = launcher.subprocess.run([sys.executable, "-B", "-c",
                                          "from fgcs_strengthening_v03.src.orchestrator import "
                                          "configure_worker_process, require_fit_threads; "
                                          "configure_worker_process(); import json; print(json.dumps(require_fit_threads()))"],
                                         cwd=launcher.ROOT, env=launcher.worker_env(), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        threads = json.loads(result.stdout)
        self.assertEqual((threads["torch_intra_op"], threads["torch_inter_op"], threads["device"]), (1, 1, "cpu"))


if __name__ == "__main__":
    unittest.main()
