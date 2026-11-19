"""Runtime backup: verified hard-linked snapshots, refusals, detection and restore. Scratch directories only."""

from datetime import datetime, timedelta, timezone
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fgcs_strengthening_v04a2 import backup_runtime as backup
from fgcs_strengthening_v04a2 import launch as launcher


def tree_digest(root):
    digest = sha256()
    for path in sorted(Path(root).rglob("*")):
        if path.is_file():
            stat = path.stat()
            digest.update(f"{path.relative_to(root)}|{stat.st_size}|{stat.st_mtime_ns}|".encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


class BackupTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.base = Path(scratch.name)
        self.runtime = self.base / "runtime"
        self.dest = self.base / "drive" / "fgcs_runtime_backups"
        self.dest.mkdir(parents=True)
        self.status = self.base / "backup_status.json"
        for relative, content in {"fingerprints.json": "{}", "outcomes/a.json": "{\"a\": 1}",
                                  "attempts/a.json": "{}", "checkpoints/a/epoch-01.pt": "x" * 5000,
                                  "launcher/workers/123.json": "{}", "outcomes/tmpabc123": "partial write",
                                  "orchestrator/gates/canary.json": "{}"}.items():
            path = self.runtime / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        self.clock = datetime(2026, 11, 20, 12, 0, 0, tzinfo=timezone.utc)

    def run_backup(self, minutes=0, **kwargs):
        return backup.backup_once(self.runtime, self.dest, allow_same_device=True, status_path=self.status,
                                  now=self.clock + timedelta(minutes=minutes), **kwargs)

    def test_snapshot_is_published_verified_and_leaves_the_runtime_untouched(self):
        before = tree_digest(self.runtime)
        record = self.run_backup()
        self.assertEqual(tree_digest(self.runtime), before)
        snapshot = self.dest / "snapshots" / record["snapshot"]
        manifest = json.loads((snapshot / "MANIFEST.json").read_text())
        self.assertEqual(set(manifest["files"]), {"fingerprints.json", "outcomes/a.json", "attempts/a.json",
                                                  "checkpoints/a/epoch-01.pt", "orchestrator/gates/canary.json"})
        self.assertFalse((snapshot / "outcomes" / "tmpabc123").exists())
        self.assertFalse((snapshot / "launcher" / "workers").exists())
        self.assertEqual(json.loads((self.dest / "latest.json").read_text())["manifest_sha256"],
                         backup._sha256(snapshot / "MANIFEST.json"))
        self.assertEqual(backup.verify_snapshot(self.dest), (True, {"snapshot": record["snapshot"], "file_count": 5,
                                                                    "problems": []}))
        self.assertEqual(json.loads(self.status.read_text())["result"], "ok")
        self.assertFalse(list(self.dest.rglob("*.tmp")))

    def test_incremental_snapshots_hard_link_unchanged_files_and_keep_two(self):
        first = self.run_backup()
        (self.runtime / "outcomes" / "b.json").write_text("{\"b\": 2}")
        second = self.run_backup(60)
        one, two = (self.dest / "snapshots" / record["snapshot"] for record in (first, second))
        self.assertEqual(os.stat(one / "checkpoints/a/epoch-01.pt").st_ino, os.stat(two / "checkpoints/a/epoch-01.pt").st_ino)
        self.assertTrue((two / "outcomes" / "b.json").exists())
        self.assertEqual(second["previous_snapshot"], first["snapshot"])
        third = self.run_backup(120)
        self.assertEqual(backup.verified_snapshots(self.dest), [second["snapshot"], third["snapshot"]])
        self.assertTrue(backup.verify_snapshot(self.dest)[0])

    def test_refusals_change_nothing(self):
        cases = {
            "drive missing": dict(dest=self.base / "absent"),
            "inside runtime": dict(dest=self.runtime),
            "no journal": dict(runtime=self.base / "empty"),
        }
        (self.base / "empty").mkdir()
        for name, change in cases.items():
            with self.assertRaises(backup.BackupRefused, msg=name):
                backup.backup_once(change.get("runtime", self.runtime), change.get("dest", self.dest),
                                   allow_same_device=True, status_path=self.status)
        with self.assertRaisesRegex(backup.BackupRefused, "same device"):
            backup.backup_once(self.runtime, self.dest, status_path=self.status)
        with self.assertRaisesRegex(backup.BackupRefused, "GB free"):
            self.run_backup(free=lambda: 0)
        with open(self.dest / ".backup.lock", "a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            with self.assertRaisesRegex(backup.BackupRefused, "already running"):
                self.run_backup()
        self.assertEqual(list((self.dest / "snapshots").iterdir()), [])
        self.assertIsNone(backup.read_latest(self.dest))

    def test_failed_copy_stays_partial_and_is_cleaned_next_time(self):
        good = self.run_backup()
        with self.assertRaises(backup.BackupFailed):
            self.run_backup(60, rsync="false")
        self.assertEqual(backup.read_latest(self.dest)["snapshot"], good["snapshot"])
        (self.dest / "snapshots" / "20261120T130000Z.partial").mkdir(exist_ok=True)
        self.assertEqual(backup.backup_status(self.dest, now=self.clock)["verdict"], "PARTIAL")
        later = self.run_backup(120)
        self.assertEqual(list((self.dest / "snapshots").glob("*.partial")), [])
        self.assertEqual(backup.read_latest(self.dest)["snapshot"], later["snapshot"])

    def test_verification_detects_corruption_missing_and_extra_files(self):
        record = self.run_backup()
        root = self.dest / "snapshots" / record["snapshot"]
        target = root / "outcomes" / "a.json"
        os.chmod(target, 0o644)
        target.write_text("{\"a\": 9}")
        ok, report = backup.verify_snapshot(self.dest)
        self.assertFalse(ok)
        self.assertIn("corrupted", " ".join(report["problems"]))
        target.unlink()
        (root / "stray.json").write_text("{}")
        ok, report = backup.verify_snapshot(self.dest)
        self.assertTrue(any("missing" in p for p in report["problems"]) and any("unexpected" in p for p in report["problems"]))

    def test_status_and_freshness_verdicts(self):
        self.assertEqual(backup.backup_status(self.base / "absent")["verdict"], "DRIVE_MISSING")
        self.assertEqual(backup.backup_status(self.dest)["verdict"], "NO_SNAPSHOT")
        self.assertEqual(backup.backup_freshness(self.base / "none.json")["verdict"], "NO_BACKUP_RECORDED")
        record = self.run_backup()
        created = datetime.fromisoformat(record["utc"])
        self.assertEqual(backup.backup_status(self.dest, now=created + timedelta(hours=1))["verdict"], "OK")
        self.assertEqual(backup.backup_status(self.dest, now=created + timedelta(hours=3))["verdict"], "STALE")
        self.assertEqual(backup.backup_freshness(self.status, now=created + timedelta(hours=1))["verdict"], "OK")
        self.assertEqual(backup.backup_freshness(self.status, now=created + timedelta(hours=3))["verdict"], "STALE")
        backup.write_status({"result": "failed", "error": "drive missing", "utc": record["utc"]}, self.status)
        self.assertEqual(backup.backup_freshness(self.status)["verdict"], "LAST_BACKUP_FAILED")

    def test_restore_only_into_a_new_path_outside_the_live_runtime(self):
        record = self.run_backup()
        for target in (self.runtime, self.runtime / "restored", self.base):
            with self.assertRaises(backup.BackupRefused, msg=str(target)):
                backup.restore(self.dest, target, live_runtime=self.runtime)
        into = self.base / "restore" / "runtime"
        result = backup.restore(self.dest, into, live_runtime=self.runtime)
        self.assertEqual((result["snapshot"], result["file_count"]), (record["snapshot"], 5))
        self.assertFalse((into / "MANIFEST.json").exists())
        self.assertEqual((into / "checkpoints/a/epoch-01.pt").read_text(), "x" * 5000)
        root = self.dest / "snapshots" / record["snapshot"]
        os.chmod(root / "outcomes" / "a.json", 0o644)
        (root / "outcomes" / "a.json").write_text("tampered")
        with self.assertRaises(backup.BackupFailed):
            backup.restore(self.dest, self.base / "restore2", live_runtime=self.runtime)

    def test_cli_status_reports_a_missing_drive(self):
        self.assertEqual(backup.main(["status", "--dest", str(self.base / "absent")]), 0)


class LauncherBackupGateTests(unittest.TestCase):
    def test_full_run_phases_need_20_gb_but_no_backup(self):
        self.assertIsNone(launcher.require_full_run_capacity("canary", free=lambda: 1e9))
        for phase in ("inner", "final"):
            with self.assertRaisesRegex(launcher.LaunchRefused, "at least 20 GB"):
                launcher.require_full_run_capacity(phase, free=lambda: 19.9e9)
            self.assertEqual(launcher.require_full_run_capacity(phase, free=lambda: 20e9), 20e9)
        # The mandatory backup gate is gone: no missing, failed or stale backup blocks a phase start.
        self.assertFalse(hasattr(launcher, "require_backup_fresh"))
        for state in ({"verdict": "STALE"}, {"verdict": "LAST_BACKUP_FAILED"}, {"verdict": "NO_BACKUP_RECORDED"}):
            with patch.object(backup, "backup_freshness", lambda *a, s=state, **k: s):
                self.assertEqual(launcher.require_full_run_capacity("inner", free=lambda: 25e9), 25e9)
        # The 15 GB running guard is unchanged.
        self.assertEqual((launcher.MIN_FREE_GB, launcher.FULL_RUN_MIN_FREE_GB), (15, 20))
        monitor = launcher.Monitor(request_stop=lambda r: None, free=lambda: 14.9e9, power=lambda: True,
                                   thermal=lambda: 0, load=lambda: [0, 0, 0])
        self.assertIn("below 15 GB", monitor.check())

    def test_health_snapshot_reports_backup_freshness_and_survives_errors(self):
        monitor = launcher.Monitor(request_stop=lambda r: None, free=lambda: 100e9, power=lambda: True,
                                   thermal=lambda: 0, load=lambda: [0, 0, 0], backup=lambda: {"verdict": "STALE"})
        self.assertEqual(monitor.snapshot()["backup"], {"verdict": "STALE"})
        monitor.backup = lambda: (_ for _ in ()).throw(OSError("drive gone"))
        self.assertEqual(monitor.snapshot()["backup"]["verdict"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
