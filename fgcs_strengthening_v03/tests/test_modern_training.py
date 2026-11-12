from dataclasses import replace
from functools import lru_cache
import json
import unittest
from unittest.mock import patch

import numpy as np

from fgcs_strengthening_v03.src.data_adapters import Windows
from fgcs_strengthening_v03.src.modern.design import FAMILIES, pilot_identities
from fgcs_strengthening_v03.src.modern.runner import ModernRunner, modern_fingerprints
from fgcs_strengthening_v03.src.provenance import DuplicateIdentity, ProvenanceError, sha256_file
from fgcs_strengthening_v03.tests.training_fixtures import partition, scratch_engine


@lru_cache(maxsize=1)
def seal():
    return modern_fingerprints()


def pilot(family, variant="independent"):
    return next(i for i in pilot_identities()
                if (i.block, i.formulation, i.variant) == ("Rnd", family, variant))


def synthetic_partition(identity, *, invalid_native_prediction=False):
    prepared, reads = partition(identity)
    base = prepared._adapter

    class Adapter:
        def _windows(self, frame, entity, context, origins, scaler):
            window = base._windows(frame, entity, context, origins, scaler)
            return Windows(window.inputs, window.targets, window.targets.astype(np.float64), window.origin_ids)

        def _inverse(self, scaler, values, task):
            if invalid_native_prediction:
                return np.full_like(values, np.nan), 0., values
            return values.astype(np.float64), 0., values.astype(np.float64)

    return replace(prepared, _adapter=Adapter()), reads


def run_synthetic(family, variant):
    inner = pilot(family, variant)
    final = replace(inner, phase="final")
    training, inner_reads = synthetic_partition(inner)
    refit, final_reads = synthetic_partition(final)
    with scratch_engine(seal()) as engine:
        runner = ModernRunner(engine.journal)
        with unittest.TestCase().assertRaises(ProvenanceError):
            runner.fit_inner(inner, training)
        assert inner_reads == []
        certificate = runner.validate_family(family)
        assert certificate["status"] == "complete"
        observed = runner.fit_inner(inner, training).evidence
        result = runner.fit_final(final, refit).evidence
        assert inner_reads == [0, 1] and final_reads == [0]
        assert observed["native_validation"]["verified_epochs"] == len(observed["epochs"])
        assert observed["native_validation"]["origins"] == 3
        assert "native_validation" not in result
        assert len(result["epochs"]) == observed["selection"]["joint_epoch"]
        assert result["initial_model_sha256"] == observed["initial_model_sha256"]
        assert result["initial_model_sha256"] != observed["terminal_model_sha256"]
        for evidence in (observed, result):
            optimizer = evidence["optimizer"]
            assert optimizer["name"] == ("Adam" if family == "DLinear" else "AdamW")
            assert optimizer["weight_decay"] == (0. if family == "DLinear" else 1e-4)
            assert optimizer["lr"] == .001
            assert evidence["architecture"]["variant"] == variant
            assert evidence["architecture"]["family"] == family
            assert evidence["context"] == 4
            assert evidence["parameter_count"] > 0
        return [{k: evidence[k] for k in ("architecture", "optimizer", "epochs", "selection",
                                         "initial_model_sha256", "terminal_model_sha256")}
                for evidence in (observed, result)]


class ModernTrainingTests(unittest.TestCase):
    def test_deterministic_inner_and_fresh_final_for_every_family_and_complement(self):
        for family in FAMILIES:
            for variant in ("independent", "shared"):
                with self.subTest(family=family, variant=variant):
                    self.assertEqual(run_synthetic(family, variant), run_synthetic(family, variant))

    def test_reuse_is_read_only_and_checks_context_fingerprints_and_checkpoint(self):
        unit = pilot("DLinear")
        partition, reads = synthetic_partition(unit)
        with scratch_engine(seal()) as engine:
            runner = ModernRunner(engine.journal)
            runner.validate_family("DLinear")
            with self.assertRaisesRegex(ProvenanceError, "Pilot partition context"):
                runner.fit_inner(unit, replace(partition, context=9))
            self.assertEqual(reads, [])
            fit = runner.fit_inner(unit, partition)
            outcome = engine.journal.runtime / "outcomes" / f"{unit.digest}.json"
            original = sha256_file(outcome)
            reused, digest = runner.reuse_pilot(unit, partition)
            self.assertEqual(reused, fit.evidence)
            self.assertEqual(digest, original)
            self.assertEqual(reads, [0, 1])
            with self.assertRaises(DuplicateIdentity):
                runner.fit_inner(unit, partition)
            with self.assertRaises(ProvenanceError):
                runner.reuse_pilot(unit, replace(partition, scaler_sha256="changed"))
            self.assertEqual(sha256_file(outcome), original)
            epoch = reused["selection"]["joint_epoch"]
            checkpoint = engine.journal.runtime / reused["checkpoints"][str(epoch)]["path"]
            checkpoint.write_bytes(b"tampered synthetic checkpoint")
            with self.assertRaisesRegex(ProvenanceError, "Checkpoint bytes differ"):
                runner.reuse_pilot(unit, partition)
            self.assertEqual(reads, [0, 1])

    def test_nonfinite_native_prediction_records_failure_and_halts_only_its_family(self):
        unit = pilot("iTransformer")
        prepared, accesses = synthetic_partition(unit, invalid_native_prediction=True)
        with scratch_engine(seal()) as engine:
            runner = ModernRunner(engine.journal)
            runner.validate_family("iTransformer")
            with self.assertRaisesRegex(ValueError, "Invalid native validation predictions"):
                runner.fit_inner(unit, prepared)
            self.assertEqual(accesses, [0, 1])
            outcome = engine.journal.runtime / "outcomes" / f"{unit.digest}.json"
            record = json.loads(outcome.read_text())
            self.assertEqual(record["status"], "failed")
            self.assertEqual(record["evidence"]["checkpoints"], {})
            self.assertEqual(record["fingerprint_sha256"], seal().digest)
            stopped = engine.journal.runtime / "modern/iTransformer/stop.json"
            self.assertEqual(json.loads(stopped.read_text())["outcome_sha256"], sha256_file(outcome))
            other = pilot("iTransformer", "shared")
            second, reads = synthetic_partition(other)
            with self.assertRaisesRegex(ProvenanceError, "author review"):
                ModernRunner(engine.journal).fit_inner(other, second)
            self.assertEqual(reads, [])
            self.assertEqual(runner.validate_family("DLinear")["status"], "complete")

    def test_structural_failure_is_persistent_and_data_free(self):
        unit = pilot("PatchTST")
        prepared, reads = synthetic_partition(unit)
        with scratch_engine(seal()) as engine:
            runner = ModernRunner(engine.journal)
            with patch("fgcs_strengthening_v03.src.modern.runner.validate_family_structure",
                       side_effect=RuntimeError("synthetic structural failure")):
                with self.assertRaisesRegex(RuntimeError, "synthetic structural"):
                    runner.validate_family("PatchTST")
            certificate = engine.journal.runtime / "modern/PatchTST/structure.json"
            self.assertEqual(json.loads(certificate.read_text())["status"], "failed")
            before = sha256_file(certificate)
            with self.assertRaisesRegex(ProvenanceError, "author review"):
                runner.validate_family("PatchTST")
            with self.assertRaisesRegex(ProvenanceError, "author review"):
                runner.fit_inner(unit, prepared)
            self.assertEqual(reads, [])
            self.assertEqual(before, sha256_file(certificate))
