from dataclasses import replace
from functools import lru_cache
import json
import unittest
from unittest.mock import patch

import numpy as np

from fgcs_strengthening_v04.src.data_adapters import Windows
from fgcs_strengthening_v04.src.provenance import DuplicateIdentity, ProvenanceError, sha256_file
from fgcs_strengthening_v04.src.transfer.design import group_identities
from fgcs_strengthening_v04.src.transfer.runner import TransferRunner, transfer_fingerprints
from fgcs_strengthening_v04.tests.training_fixtures import partition, scratch_engine


@lru_cache(maxsize=1)
def seal():
    return transfer_fingerprints()


def unit_for(arm, scope):
    return next(unit for unit in group_identities("fastStorage", "697", 1, 0, "inner")
                if (unit.arm, unit.input_scope) == (arm, scope))


def heldout_partition(unit, *, broken=False):
    prepared, accesses = partition(unit)
    base = prepared._adapter

    class Adapter:
        def _windows(self, frame, entity, length, origins, scaler):
            if origins[0] != 2:
                return base._windows(frame, entity, length, origins, scaler)
            accesses.append(2)
            inputs = np.full((3, length, 4), .25, dtype=np.float32)
            target = np.ones((3, 4, 5), dtype=np.float32)
            native = target.astype(np.float64)
            if broken:
                native[0, 0, 0] = np.nan
            return Windows(inputs, target, native, np.arange(100, 103))

        def _inverse(self, scaler, values, resource):
            return values.astype(np.float64), 0., values.astype(np.float64)

    return replace(prepared, _adapter=Adapter()), accesses


class TransferRunnerTests(unittest.TestCase):
    def test_one_identity_fits_then_explicit_evaluation_once(self):
        for arm, scope in (("pairwise", "own"), ("leave_one_out", "all")):
            inner = unit_for(arm, scope)
            final = replace(inner, phase="final")
            inner_partition, inner_reads = partition(inner)
            final_partition, reads = heldout_partition(final)
            with self.subTest(arm=arm), scratch_engine(seal(), closed_fits=True) as engine:
                runner = TransferRunner(engine)
                with self.assertRaises(ProvenanceError):
                    runner.fit(final, final_partition)
                with self.assertRaises(ProvenanceError):
                    runner.evaluate(final, final_partition)
                self.assertEqual(reads, [])
                self.assertFalse((engine.journal.runtime / "attempts").exists())
                self.assertFalse((engine.journal.runtime / "evaluations").exists())

                runner.fit(inner, inner_partition)
                fit = runner.fit(final, final_partition).evidence
                self.assertEqual(inner_reads, [0, 1])
                self.assertEqual(reads, [0])
                self.assertEqual(len(fit["epochs"]), fit["selection"]["joint_epoch"])
                self.assertEqual(set(fit["epochs"][0]["train_task_mse"]), set(final.tasks))
                self.assertNotIn("intervention", fit)
                self.assertNotIn("diagnostic_slots", fit)
                with self.assertRaises(DuplicateIdentity):
                    runner.fit(final, final_partition)
                self.assertEqual(reads, [0])

                evaluation = runner.evaluate(final, final_partition)
                self.assertEqual(reads, [0, 2])
                self.assertEqual(len(evaluation["cells"]), len(final.tasks) * 5)
                self.assertEqual(evaluation["test_origins"], 3)
                self.assertEqual(evaluation["checkpoint"], fit["checkpoints"][str(fit["primary_checkpoint_epoch"])])
                cells = runner.completed_cells(final)
                self.assertEqual(tuple(dict.fromkeys(cell.target for cell in cells)), final.tasks)
                self.assertTrue(all(cell.identity == final and cell.mae >= 0 for cell in cells))
                fit_path = engine.journal.runtime / "outcomes" / f"{final.digest}.json"
                self.assertEqual(evaluation["final_outcome_sha256"], sha256_file(fit_path))
                path = engine.journal.runtime / "evaluations" / "outcomes" / f"{final.digest}.json"
                before = sha256_file(path)
                record = json.loads(path.read_text())
                self.assertEqual(record["operation"], "outer_test_evaluation")
                self.assertEqual(record["identity"], final.payload())
                self.assertEqual(record["fingerprint_sha256"], seal().digest)
                with self.assertRaises(DuplicateIdentity):
                    runner.evaluate(final, final_partition)
                self.assertEqual(reads, [0, 2])
                self.assertEqual(sha256_file(path), before)

    def test_failed_fit_is_terminal_and_does_not_enable_evaluation(self):
        inner = unit_for("leave_one_out", "own")
        final = replace(inner, phase="final")
        with scratch_engine(seal(), closed_fits=True) as engine:
            runner = TransferRunner(engine)
            prepared, reads = partition(inner)
            with patch("fgcs_strengthening_v04.src.training._evaluate", return_value=[float("nan")] * 3):
                with self.assertRaises(ValueError):
                    runner.fit(inner, prepared)
            path = engine.journal.runtime / "outcomes" / f"{inner.digest}.json"
            checksum = sha256_file(path)
            self.assertEqual(json.loads(path.read_text())["status"], "failed")
            with self.assertRaises(DuplicateIdentity):
                runner.fit(inner, prepared)
            self.assertEqual(reads, [0, 1])
            final_partition, final_reads = heldout_partition(final)
            for call in (runner.fit, runner.evaluate):
                with self.assertRaises(ProvenanceError):
                    call(final, final_partition)
            self.assertEqual(final_reads, [])
            self.assertEqual(sha256_file(path), checksum)

    def test_invalid_evaluation_is_terminal_and_has_no_partial_cells(self):
        inner = unit_for("pairwise", "all")
        final = replace(inner, phase="final")
        prepared, reads = heldout_partition(final, broken=True)
        with scratch_engine(seal(), closed_fits=True) as engine:
            runner = TransferRunner(engine)
            runner.fit(inner, partition(inner)[0])
            runner.fit(final, prepared)
            with self.assertRaisesRegex(ValueError, "native outer-test targets"):
                runner.evaluate(final, prepared)
            path = engine.journal.runtime / "evaluations" / "outcomes" / f"{final.digest}.json"
            result = json.loads(path.read_text())
            self.assertEqual(result["status"], "failed")
            self.assertNotIn("cells", result["evidence"])
            with self.assertRaises(DuplicateIdentity):
                runner.evaluate(final, prepared)
            self.assertEqual(reads, [0, 2])
            with self.assertRaises(ProvenanceError):
                runner.completed_cells(final)
