"""A1 registration builder: build, verify and tamper detection in scratch package folders only.

The real, tagged package folder is only read (verified), never written.
"""

from functools import lru_cache
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fgcs_strengthening_v04a2 import build_registration as registration
from fgcs_strengthening_v04a2 import launch as launcher
from fgcs_strengthening_v04a2.host import EXPECTED_CONDITIONS
from fgcs_strengthening_v04a2.src.identity import HOME, ROOT, read_config

HOST = {"hardware": {"hostname": "synthetic.local", "cpu_model": "Synthetic CPU", "physical_cores": 8,
                     "logical_cores": 8, "ram_bytes": 1, "os": "Darwin", "kernel": "synthetic", "power_mode": "x"},
        "software": {"python": "3", "numpy": "2", "pandas": "2", "pytorch": "2", "torch_blas": "accelerate"},
        "conditions": EXPECTED_CONDITIONS}


_GENERATE = registration.generated  # the real function, captured before any patch


@lru_cache(maxsize=1)
def contents():
    return _GENERATE()


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(dir=HOME)
        self.addCleanup(scratch.cleanup)
        self.package = Path(scratch.name)
        (self.package / "host_manifest.json").write_text(json.dumps(HOST))
        patches = (patch.object(registration, "require_frozen_protocol", lambda path=None: None),
                   patch.object(registration, "generated", contents))
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def test_the_real_package_folder_is_untouched_and_drafts_are_refused(self):
        patch.stopall()
        # The tagged package verifies and these tests never write to its folder.
        self.assertEqual(registration.verify()[1], [])
        registration.require_frozen_protocol()  # the configured v0.4 protocol and A1 amendment are frozen
        for name, text in (("plan_DRAFT.md", "# Plan\n"), ("plan.md", "# Plan — DRAFT\n"),
                           ("plan2.md", "# Plan\n\n**Status: Not frozen.**\n")):
            draft = self.package / name
            draft.write_text(text)
            with self.assertRaisesRegex(registration.RegistrationRefused, "still a draft"):
                registration.require_frozen_protocol(draft.relative_to(ROOT).as_posix())
            draft.unlink()
        with patch.object(registration, "require_frozen_protocol",
                          side_effect=registration.RegistrationRefused("still a draft")):
            with self.assertRaisesRegex(registration.RegistrationRefused, "still a draft"):
                registration.build(self.package)
        self.assertEqual(sorted(p.name for p in self.package.iterdir()), ["host_manifest.json"])

    def test_build_then_verify_records_the_a2_design(self):
        digest = registration.build(self.package)
        self.assertEqual(registration.verify(self.package), (digest, []))
        record = json.loads((self.package / "PACKAGE.json").read_text())
        self.assertEqual(record["package_sha256"], digest)
        self.assertEqual(set(record["generated_files"]), {*registration.GENERATED, "host_manifest.json"})
        self.assertNotIn("hostname", record["host"]["hardware_without_hostname"])
        self.assertEqual(record["protocol"], read_config()["protocol"]["path"])
        self.assertEqual(record["amendment"], read_config()["amendment"]["path"])
        self.assertIn(read_config()["amendment"]["path"], record["referenced_files"])
        schedule = json.loads((self.package / "schedule.json").read_text())
        self.assertEqual(schedule["phases"], {"certify": 3, "canary": 70, "inner": 10430, "final": 10500,
                                              "diagnostics": 0, "evaluation": 10500})
        self.assertEqual((schedule["identity_count"], len(schedule["canary"])), (21000, 70))
        self.assertEqual(schedule["lineage"]["a1_tag"], "fgcs-v04-a1-intervention")
        self.assertEqual(schedule["residual"]["parameterisation"], "change")
        self.assertEqual(schedule["execution"]["fit_workers"], 6)
        self.assertEqual(schedule["lineage"]["v04_tag"], "fgcs-v04-min-final-r2")
        catalogue = json.loads((self.package / "analysis_catalogue.json").read_text())
        self.assertEqual(catalogue["evaluation_identity_count"], 10500)
        self.assertEqual(catalogue["format"], "fgcs-v04-a2-analysis/1")
        seal = json.loads((self.package / "execution_seal.json").read_text())
        self.assertTrue(any(path.endswith("analyse_residual.py") for path, _ in seal["sources"]))
        self.assertTrue(any(path.endswith("src/residual.py") for path, _ in seal["sources"]))
        self.assertTrue(any(path == read_config()["amendment"]["path"] for path, _ in seal["inputs"]))
        self.assertFalse(launcher.execution_unlocked(self.package / "REGISTRATION_EVIDENCE_TEMPLATE.md"))

    def test_any_change_is_detected(self):
        registration.build(self.package)
        for name, edit in (("schedule.json", lambda text: text.replace('"inner": 10430', '"inner": 10431')),
                           ("host_manifest.json", lambda text: text.replace("Synthetic CPU", "Other CPU")),
                           ("PACKAGE.json", lambda text: text.replace("scientific_execution\": \"none", "scientific_execution\": \"started"))):
            with self.subTest(name=name):
                path = self.package / name
                original = path.read_text()
                self.assertNotEqual(edit(original), original, "the tamper edit must change the file")
                path.write_text(edit(original))
                _, problems = registration.verify(self.package)
                self.assertTrue(problems)
                path.write_text(original)
        self.assertEqual(registration.verify(self.package)[1], [])

    def test_a_package_is_never_overwritten_and_needs_a_single_thread_host(self):
        registration.build(self.package)
        with self.assertRaisesRegex(registration.RegistrationRefused, "never overwritten"):
            registration.build(self.package)
        with tempfile.TemporaryDirectory(dir=HOME) as other:
            other = Path(other)
            with self.assertRaisesRegex(registration.RegistrationRefused, "host manifest first"):
                registration.build(other)
            loose = json.loads(json.dumps(HOST))
            loose["conditions"]["torch_intraop_threads"] = 4
            (other / "host_manifest.json").write_text(json.dumps(loose))
            with self.assertRaisesRegex(registration.RegistrationRefused, "single-thread"):
                registration.build(other)
            self.assertEqual(sorted(p.name for p in other.iterdir()), ["host_manifest.json"])
        self.assertEqual(registration.verify(Path("/nonexistent")), (None, ["no PACKAGE.json"]))

    def test_the_launcher_package_gate_uses_the_builder(self):
        digest = registration.build(self.package)
        with patch.object(registration, "PACKAGE", self.package), \
                patch.object(launcher, "tagged_state", lambda tag=None: {"package_sha256": digest}):
            self.assertEqual(launcher.check_package(), digest)
        with patch.object(registration, "PACKAGE", self.package), \
                patch.object(launcher, "tagged_state", lambda tag=None: {"package_sha256": "0" * 64}):
            with self.assertRaisesRegex(launcher.LaunchRefused, "does not verify"):
                launcher.check_package()


if __name__ == "__main__":
    unittest.main()
