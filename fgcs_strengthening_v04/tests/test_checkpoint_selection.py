from dataclasses import replace
import unittest
from unittest.mock import patch

import torch

from fgcs_strengthening_v04.src.checkpoints import EpochSelector, checkpoint_control_applies
from fgcs_strengthening_v04.src.identity import RESOURCES
from fgcs_strengthening_v04.src.provenance import sha256_file
from fgcs_strengthening_v04.src.training import _optimise_epoch, _state_hash, _windows, cpu_seed_scope, LSTM
from fgcs_strengthening_v04.tests.training_fixtures import identity, partition, scratch_engine


def losses():
    return [[2., 2., 2., 2.], [1., 1., 4., 4.], [1., 1., 1., 8.]] + [[2., 2., 2., 2.]] * 5


class CheckpointTests(unittest.TestCase):
    def test_task_requests_use_observed_epochs_and_earliest_ties(self):
        selector = EpochSelector(RESOURCES, task_control=True)
        for row in losses():
            selector.observe(row)
        self.assertTrue(selector.stopped)
        self.assertEqual(selector.observed, 8)
        plan = selector.plan()
        self.assertEqual(plan.joint_epoch, 1)
        self.assertEqual(dict(plan.task_epochs), dict(zip(RESOURCES, (2, 2, 3, 1), strict=True)))
        self.assertEqual(plan.physical_epochs, (1, 2, 3))
        self.assertEqual(plan.final_epoch, 3)
        with self.assertRaises(ValueError):
            selector.observe([0.] * 4)
        self.assertTrue(checkpoint_control_applies(identity()))
        self.assertFalse(checkpoint_control_applies(identity(seed=3)))
        self.assertFalse(checkpoint_control_applies(identity("M0")))

    def test_extension_preserves_primary_state_and_deduplicates_physical_epochs(self):
        unit = identity()
        final_id = replace(unit, phase="final")
        inner, _ = partition(unit)
        final, accesses = partition(final_id)
        with scratch_engine() as engine:
            with patch("fgcs_strengthening_v04.src.training._evaluate", side_effect=losses()):
                engine.fit_inner(unit, inner)
            result = engine.fit_final(final_id, final).evidence
            self.assertEqual(accesses, [0])
            self.assertEqual(result["primary_checkpoint_epoch"], 1)
            self.assertEqual(result["checkpoint_tail_epochs"], 2)
            self.assertEqual(len(result["epochs"]), 3)
            self.assertEqual(result["selection"]["task_epochs"], dict(zip(RESOURCES, (2, 2, 3, 1), strict=True)))
            self.assertEqual(list(result["checkpoints"]), ["1", "2", "3"])
            self.assertEqual(len(list((engine.journal.runtime / "checkpoints" / final_id.digest).iterdir())), 3)
            for checkpoint in result["checkpoints"].values():
                saved = engine.journal.runtime / checkpoint["path"]
                self.assertEqual(sha256_file(saved), checkpoint["sha256"])
                self.assertEqual(saved.stat().st_size, checkpoint["bytes"])
                self.assertEqual(_state_hash(torch.load(saved, weights_only=True)), checkpoint["model_sha256"])
            self.assertGreater(result["timing_seconds"]["primary_optimisation"], 0)
            self.assertGreater(result["timing_seconds"]["checkpoint_tail_optimisation"], 0)
            with cpu_seed_scope(unit.seed) as gen:
                model = LSTM(formulation="M1", block=unit.block, tasks=unit.tasks, hidden_size=64)
                optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
                _optimise_epoch(model, optimizer, _windows(final.training(), final_id, final.context), gen)
            self.assertEqual(result["checkpoints"]["1"]["model_sha256"], _state_hash(model.state_dict()))
            self.assertNotEqual(result["checkpoints"]["1"]["model_sha256"], result["terminal_model_sha256"])
