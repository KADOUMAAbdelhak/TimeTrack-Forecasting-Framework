import unittest

import torch

from fgcs_strengthening_v03.src.identity import RESOURCES
from fgcs_strengthening_v03.src.models.lstm import LSTM
from fgcs_strengthening_v03.src.training import _windows, cpu_seed_scope, task_mse
from fgcs_strengthening_v03.src.transfer.design import group_identities
from fgcs_strengthening_v03.tests.training_fixtures import partition


def model_for(unit):
    return LSTM(formulation=unit.formulation, block=unit.block, tasks=unit.tasks,
                hidden_size=unit.hidden_size).eval()


class TransferRoutingTests(unittest.TestCase):
    def test_own_input_pair_only_uses_the_targets_own_history(self):
        unit = next(group_identities("fastStorage", "697", 1, 0, "inner"))
        with cpu_seed_scope(0):
            model = model_for(unit)
            self.assertEqual(model.encoder.input_size, 1)
            self.assertEqual(tuple(model.heads), unit.tasks)
            X = torch.randn(3, 4, 4, requires_grad=True)
            gradients, = torch.autograd.grad(model(X)[:, 0].sum(), X)
            self.assertGreater(gradients[:, :, 0].abs().sum().item(), 0.)
            self.assertEqual(gradients[:, :, 1:].count_nonzero().item(), 0)

    def test_all_input_subsets_keep_all_predictors_and_only_retained_heads(self):
        with cpu_seed_scope(0):
            for unit in group_identities("fastStorage", "697", 1, 0, "inner"):
                if unit.input_scope != "all":
                    continue
                with self.subTest(arm=unit.arm, tasks=unit.tasks):
                    model = model_for(unit)
                    self.assertEqual(model.encoder.input_size, 4)
                    self.assertEqual(tuple(model.heads), unit.tasks)
                    X = torch.randn(3, 4, 4, requires_grad=True)
                    forecast = model(X)
                    self.assertEqual(forecast.shape, (3, len(unit.tasks), 5))
                    for i in range(len(unit.tasks)):
                        gradient, = torch.autograd.grad(forecast[:, i].sum(), X, retain_graph=True)
                        self.assertTrue((gradient.abs().sum(dim=(0, 1)) > 0).all())

    def test_omitted_targets_do_not_enter_equal_mean_loss(self):
        with cpu_seed_scope(0):
            for size in (2, 3):
                unit = next(i for i in group_identities("fastStorage", "697", 1, 0, "inner")
                            if i.input_scope == "all" and len(i.tasks) == size)
                prepared, _ = partition(unit)
                windows = prepared.training()
                X, targets = _windows(windows, unit, prepared.context)
                offsets = torch.arange(1., size + 1)[None, :, None]
                prediction = targets + offsets
                loss = task_mse(prediction, targets).mean()
                torch.testing.assert_close(loss, offsets.square().mean())
                omitted = [RESOURCES.index(task) for task in RESOURCES if task not in unit.tasks]
                windows.targets[:, omitted] = -100_000
                _, after = _windows(windows, unit, prepared.context)
                self.assertTrue(torch.equal(targets, after))
