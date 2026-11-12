from dataclasses import replace
import io
import unittest
from unittest.mock import patch

import torch

from fgcs_strengthening_v03.src.provenance import ProvenanceError, sha256_file
from fgcs_strengthening_v03.src.training import _state_hash
from fgcs_strengthening_v03.tests.training_fixtures import identity, partition, scratch_engine


class FinalRefitTests(unittest.TestCase):
    def test_fresh_refit_trains_exact_selected_epochs_and_never_reads_holdout(self):
        inner_id = identity("S1")
        final_id = replace(inner_id, phase="final")
        inner, inner_access = partition(inner_id)
        final, final_access = partition(final_id)
        with scratch_engine() as engine:
            with patch("fgcs_strengthening_v03.src.training._evaluate", side_effect=[[3.], [2.]] + [[2.]] * 7):
                fit = engine.fit_inner(inner_id, inner).evidence
            result = engine.fit_final(final_id, final)
            evidence = result.evidence
            self.assertEqual(fit["selection"]["joint_epoch"], 2)
            self.assertEqual(len(fit["epochs"]), 9)
            self.assertEqual(len(evidence["epochs"]), 2)
            self.assertEqual(evidence["initial_model_sha256"], fit["initial_model_sha256"])
            self.assertNotEqual(evidence["initial_model_sha256"], fit["terminal_model_sha256"])
            self.assertEqual(list(evidence["checkpoints"]), ["2"])
            self.assertEqual(evidence["timing_seconds"]["validation"], 0)
            self.assertEqual(evidence["timing_seconds"]["checkpoint_tail_optimisation"], 0)
            self.assertEqual(inner_access, [0, 1])
            self.assertEqual(final_access, [0])
            self.assertEqual(evidence["inner_identity_sha256"], inner_id.digest)
            inner_path = engine.journal.runtime / "outcomes" / f"{inner_id.digest}.json"
            self.assertEqual(evidence["inner_outcome_sha256"], sha256_file(inner_path))
            snapshot = torch.load(io.BytesIO(result.resume_state), weights_only=True)
            self.assertEqual(snapshot["epoch"], 2)
            self.assertEqual(snapshot["identity"], final_id.payload())
            self.assertEqual(_state_hash(snapshot["model"]), evidence["terminal_model_sha256"])
            self.assertTrue(snapshot["optimizer"]["state"])

    def test_final_requires_exact_inner_selection_before_claiming_an_attempt(self):
        final_id = identity("S2", phase="final")
        final, reads = partition(final_id)
        with scratch_engine() as engine, self.assertRaises(ProvenanceError):
            try:
                engine.fit_final(final_id, final)
            finally:
                self.assertEqual(reads, [])
                self.assertFalse((engine.journal.runtime / "attempts").exists())
