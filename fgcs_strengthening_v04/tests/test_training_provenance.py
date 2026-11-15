from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fgcs_strengthening_v04.src.identity import HOME
from fgcs_strengthening_v04.src.provenance import DuplicateIdentity, Fingerprints, Journal, ProvenanceError, sha256_file
from fgcs_strengthening_v04.src.training import TrainingEngine, training_fingerprints
from fgcs_strengthening_v04.tests.training_fixtures import identity, partition, scratch_engine


class TrainingProvenanceTests(unittest.TestCase):
    def test_exact_identity_fingerprints_parameter_history_and_no_overwrite(self):
        unit = identity("S2")
        phase, reads = partition(unit)
        with scratch_engine() as engine:
            journal = engine.journal
            with patch("fgcs_strengthening_v04.src.training._evaluate", return_value=[1.]):
                result = engine.fit_inner(unit, phase)
            path = journal.runtime / "outcomes" / f"{unit.digest}.json"
            before = sha256_file(path)
            record = json.loads(path.read_text())
            self.assertEqual(record["identity"], unit.payload())
            self.assertEqual(record["identity_sha256"], unit.digest)
            self.assertEqual(record["fingerprint_sha256"], journal.seal.digest)
            self.assertEqual(record["status"], "complete")
            self.assertEqual(record["evidence"], result.evidence)
            self.assertEqual(record["evidence"]["parameter_count"], 51525)
            self.assertEqual(record["evidence"]["resume_state_sha256"], sha256(result.resume_state).hexdigest())
            self.assertEqual(record["evidence"]["context"], phase.context)
            self.assertEqual(record["evidence"]["scaler_sha256"], phase.scaler_sha256)
            self.assertEqual(record["evidence"]["configuration_sha256"], journal.seal.configuration[1])
            with self.assertRaises(DuplicateIdentity):
                engine.fit_inner(unit, phase)
            self.assertEqual(sha256_file(path), before)
            self.assertEqual(reads, [0, 1])
            with self.assertRaises(ProvenanceError):
                engine.fit_inner(replace(unit, entity="860"), phase)
            attempt = journal.runtime / "attempts" / f"{unit.digest}.json"
            attempt_payload = json.loads(attempt.read_text())
            self.assertEqual(attempt_payload["attempt_token"], record["attempt_token"])

    def test_failed_outcome_terminal_and_preserves_partial_history(self):
        unit = identity("S1")
        phase, _ = partition(unit)
        with scratch_engine() as engine:
            with patch("fgcs_strengthening_v04.src.training._evaluate", side_effect=[[1.], [float("nan")]]):
                with self.assertRaises(ValueError):
                    engine.fit_inner(unit, phase)
            path = engine.journal.runtime / "outcomes" / f"{unit.digest}.json"
            digest = sha256_file(path)
            record = json.loads(path.read_text())
            self.assertEqual(record["status"], "failed")
            self.assertEqual(record["evidence"]["selection"]["joint_epoch"], 1)
            self.assertEqual(len(record["evidence"]["epochs"]), 2)
            self.assertIn("error", record["evidence"])
            with self.assertRaises(DuplicateIdentity):
                engine.fit_inner(unit, phase)
            with self.assertRaises(ProvenanceError):
                engine.journal.completed_evidence(unit)
            self.assertEqual(sha256_file(path), digest)

    def test_full_stage_seal_preserves_frozen_input_hashes(self):
        seal = training_fingerprints()
        self.assertEqual(len(seal.inputs), 36)
        self.assertEqual(len(seal.sources), 24)  # r3's 27 minus tree/design.py and the two optim sources
        seal.verify()

    def test_engine_rejects_an_incomplete_journal_seal(self):
        seal = Fingerprints.capture(inputs=[], sources=[])
        with tempfile.TemporaryDirectory(dir=HOME) as scratch, patch(
                "fgcs_strengthening_v04.src.provenance.HOME", Path(scratch)):
            with self.assertRaises(ProvenanceError):
                TrainingEngine(Journal(seal))
