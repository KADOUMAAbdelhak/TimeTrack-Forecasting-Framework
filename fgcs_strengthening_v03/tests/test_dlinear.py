import unittest

import torch

from fgcs_strengthening_v03.src.identity import RESOURCES
from fgcs_strengthening_v03.src.models.dlinear import DLinear, kernel_for_context


class DLinearTests(unittest.TestCase):
    def test_exact_kernel_rule_and_replicate_padding(self):
        self.assertEqual([kernel_for_context(L) for L in (4, 9, 18, 26)], [3, 9, 17, 25])
        model = DLinear(4, ("CPU",))
        X = torch.tensor([1., 4., 7., 10.]).reshape(1, 4, 1)
        trend, residual = model.decompose(X)
        torch.testing.assert_close(trend, torch.tensor([[[2., 4., 7., 9.]]]))
        torch.testing.assert_close(residual, torch.tensor([[[-1., 0., 0., 1.]]]))

    def test_shapes_and_projection_weights_are_reused_for_all_four_tasks(self):
        for L in (4, 9, 18):
            shared = DLinear(L, RESOURCES)
            single = DLinear(L, ("MEMORY",))
            single.load_state_dict(shared.state_dict())
            X = torch.arange(2 * L * 4, dtype=torch.float32).reshape(2, L, 4)
            independent = single(X[:, :, 2:3])
            together = shared(X)
            self.assertEqual(independent.shape, (2, 1, 5))
            self.assertEqual(together.shape, (2, 4, 5))
            self.assertEqual(len(list(shared.parameters())), 4)
            torch.testing.assert_close(together[:, 2:3], independent)
            changed = X.clone()
            changed[:, :, 1] += 11
            torch.testing.assert_close(shared(changed)[:, 2], together[:, 2], rtol=0, atol=0)
