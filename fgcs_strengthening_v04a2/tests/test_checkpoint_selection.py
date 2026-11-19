from dataclasses import replace
import unittest
from unittest.mock import patch

import torch

from fgcs_strengthening_v04a2.src.checkpoints import EpochSelector
from fgcs_strengthening_v04a2.src.identity import RESOURCES
from fgcs_strengthening_v04a2.src.provenance import sha256_file
from fgcs_strengthening_v04a2.src.residual import anchor
from fgcs_strengthening_v04a2.src.training import _optimise_epoch, _state_hash, _windows, cpu_seed_scope, LSTM
from fgcs_strengthening_v04a2.tests.training_fixtures import identity, partition, scratch_engine


def losses():
    return [[2., 2., 2., 2.], [1., 1., 4., 4.], [1., 1., 1., 8.]] + [[2., 2., 2., 2.]] * 5


class CheckpointTests(unittest.TestCase):
    def test_selection_keeps_the_earliest_strictly_lowest_joint_epoch(self):
        selector = EpochSelector(RESOURCES, task_control=False)
        for row in losses():
            selector.observe(row)
        self.assertTrue(selector.stopped)
        self.assertEqual(selector.observed, 8)
        plan = selector.plan()
        self.assertEqual((plan.joint_epoch, plan.task_epochs, plan.physical_epochs, plan.final_epoch),
                         (1, (), (1,), 1))
        with self.assertRaises(ValueError):
            selector.observe([0.] * 4)

    def test_core_m1_final_trains_to_the_selected_epoch_with_one_checkpoint(self):
        """v0.4 drops task-checkpoint control (P8): no tail epochs and no task-selected checkpoints."""
        unit = identity()
        final_id = replace(unit, phase="final")
        inner, _ = partition(unit)
        final, accesses = partition(final_id)
        with scratch_engine() as engine:
            with patch("fgcs_strengthening_v04a2.src.training._evaluate", side_effect=losses()):
                engine.fit_inner(unit, inner)
            result = engine.fit_final(final_id, final).evidence
            self.assertEqual(accesses, [0])
            self.assertEqual((result["primary_checkpoint_epoch"], result["checkpoint_tail_epochs"]), (1, 0))
            self.assertEqual(len(result["epochs"]), 1)
            self.assertEqual(result["selection"]["task_epochs"], {})
            self.assertEqual(list(result["checkpoints"]), ["1"])
            self.assertEqual(len(list((engine.journal.runtime / "checkpoints" / final_id.digest).iterdir())), 1)
            checkpoint = result["checkpoints"]["1"]
            saved = engine.journal.runtime / checkpoint["path"]
            self.assertEqual(sha256_file(saved), checkpoint["sha256"])
            self.assertEqual(_state_hash(torch.load(saved, weights_only=True)), checkpoint["model_sha256"])
            self.assertEqual(result["timing_seconds"]["checkpoint_tail_optimisation"], 0)
            with cpu_seed_scope(unit.seed) as gen:
                model = anchor(LSTM(formulation="M1", block=unit.block, tasks=unit.tasks, hidden_size=64), unit.tasks)
                optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
                _optimise_epoch(model, optimizer, _windows(final.training(), final_id, final.context), gen)
            self.assertEqual(checkpoint["model_sha256"], _state_hash(model.state_dict()))
            self.assertEqual(checkpoint["model_sha256"], result["terminal_model_sha256"])


if __name__ == "__main__":
    unittest.main()
