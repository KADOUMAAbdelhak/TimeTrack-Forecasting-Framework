import unittest

import torch

from fgcs_strengthening_v04.src.checkpoints import EpochSelector
from fgcs_strengthening_v04.src.identity import RESOURCES
from fgcs_strengthening_v04.src.training import _evaluate, _windows, task_mse
from fgcs_strengthening_v04.tests.training_fixtures import identity, partition


class SelectionTests(unittest.TestCase):
    def test_ties_preserve_earliest_and_patience_resets_only_on_strict_improvement(self):
        s = EpochSelector(("CPU",), task_control=False)
        for loss in (3, 3, 2, 2, 4, 2, 5, 2, 2):
            s.observe((loss,))
            self.assertFalse(s.stopped)
        s.observe((2,))
        self.assertTrue(s.stopped)
        self.assertEqual(s.plan().joint_epoch, 3)
        self.assertEqual(s.observed, 10)
        with self.assertRaises(ValueError):
            s.observe((0,))

    def test_50_epoch_cap_and_nonfinite_validation(self):
        selector = EpochSelector(("CPU",), task_control=False)
        with self.assertRaises(ValueError):
            selector.observe((float("nan"),))
        for value in range(50, 0, -1):
            selector.observe((value,))
        self.assertTrue(selector.stopped)
        self.assertEqual(selector.plan().joint_epoch, 50)

    def test_s1_s2_loss_uses_only_declared_scaled_target(self):
        for formulation in ("S1", "S2"):
            unit = identity(formulation)
            phase, _ = partition(unit)
            raw = phase.training()
            X, y = _windows(raw, unit, phase.context)
            self.assertTrue(torch.equal(y[:, 0], torch.from_numpy(raw.targets[:, RESOURCES.index("MEMORY"), :])))
            loss = task_mse(y + 2, y)
            torch.testing.assert_close(loss, torch.tensor([4.0]))

    def test_m0_m1_equal_task_mean_and_validation_weights_final_short_batch(self):
        for formulation in ("M0", "M1"):
            unit = identity(formulation)
            phase, _ = partition(unit, n=257)
            X, y = _windows(phase.training(), unit, phase.context)
            model = torch.nn.Identity()
            target = torch.zeros_like(y)
            pred = torch.arange(1, 5, dtype=y.dtype)[None, :, None].expand_as(y).clone()
            pred[-1] *= 2
            loss = task_mse(pred, target)
            expected = torch.tensor([1., 4., 9., 16.]) * (260 / 257)
            torch.testing.assert_close(loss, expected)
            torch.testing.assert_close(loss.mean(), expected.mean())
            result = _evaluate(model, (pred, target))
            torch.testing.assert_close(torch.tensor(result), expected)
