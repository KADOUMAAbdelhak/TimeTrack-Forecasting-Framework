from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fgcs_strengthening_v04.src.identity import HOME, ROOT, RESOURCES, ScientificIdentity, read_config
from fgcs_strengthening_v04.src.provenance import (
    DuplicateIdentity, Fingerprints, Journal, ProvenanceError, repository_path, sha256_file,
)


def example():
    return ScientificIdentity("Rnd", "151", 1, 2, "inner", "core",
                              "M1", RESOURCES, "all", 64, "baseline")


class PreservationTests(unittest.TestCase):
    def test_all_declared_frozen_inputs_and_historical_sources(self):
        seal = Fingerprints.capture_protocol()
        self.assertGreater(len(seal.inputs), 20)
        self.assertGreater(len(seal.sources), 15)
        self.assertEqual(len(seal.digest), 64)
        with self.assertRaises(FrozenInstanceError):
            seal.inputs = ()

    def test_journal_concurrent_duplicate_and_terminal_outcome(self):
        source = Path(__file__).resolve().relative_to(ROOT)
        protocol = read_config()["protocol"]["path"]
        seal = Fingerprints.capture(inputs=[protocol], sources=[source])
        with tempfile.TemporaryDirectory(dir=HOME) as scratch, patch(
                "fgcs_strengthening_v04.src.provenance.HOME", Path(scratch)):
            store = Journal(seal)
            identity = example()

            def start():
                try:
                    return Journal(seal).start(identity)
                except DuplicateIdentity:
                    return None

            with ThreadPoolExecutor(max_workers=8) as pool:
                winners = [attempt for attempt in pool.map(lambda _: start(), range(12)) if attempt]
            self.assertEqual(len(winners), 1)
            attempt = winners[0]
            with self.assertRaises(ProvenanceError):
                store.finish(replace(attempt, token="forged"), status="complete", evidence={})
            store.finish(attempt, status="failed", evidence={"synthetic": "failure"})
            path = store.runtime / "outcomes" / f"{identity.digest}.json"
            failure_sha = sha256_file(path)
            with self.assertRaises(DuplicateIdentity):
                store.finish(attempt, status="complete", evidence={})
            with self.assertRaises(DuplicateIdentity):
                Journal(seal).start(identity)
            self.assertEqual(sha256_file(path), failure_sha)
            self.assertEqual(json.loads(path.read_text())["identity"], identity.payload())
            other = replace(identity, seed=1)
            receipt = store.start(other)
            store.finish(receipt, status="complete", evidence={"synthetic": True})
            self.assertEqual(len(list((store.runtime / "attempts").iterdir())), 2)
            self.assertEqual(len(list((store.runtime / "outcomes").iterdir())), 2)

    def test_path_escape_symlink_and_changed_seal_rejected(self):
        protocol = read_config()["protocol"]["path"]
        seal = Fingerprints.capture(inputs=[protocol], sources=[])
        with self.assertRaises(ProvenanceError):
            repository_path("../TimeTrack")
        with tempfile.TemporaryDirectory(dir=HOME) as scratch, patch(
                "fgcs_strengthening_v04.src.provenance.HOME", Path(scratch)):
            runtime = Path(scratch) / "runtime"
            runtime.symlink_to(ROOT / "review_revision", target_is_directory=True)
            with self.assertRaises(ProvenanceError):
                Journal(seal)
            runtime.unlink()
            Journal(seal)
            different = Fingerprints.capture(inputs=[], sources=[])
            with self.assertRaises(ProvenanceError):
                Journal(different)
            corrupted = replace(seal, inputs=((protocol, "0" * 64),))
            with self.assertRaises(ProvenanceError):
                corrupted.verify()
