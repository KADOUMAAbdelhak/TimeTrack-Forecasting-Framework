from copy import deepcopy
import unittest

import torch

from fgcs_strengthening_v04a1.src.diagnostics.gradients import PARAMETERS, DiagnosticClone
from fgcs_strengthening_v04a1.src.identity import RESOURCES
from fgcs_strengthening_v04a1.src.models.lstm import LSTM
from fgcs_strengthening_v04a1.src.training import cpu_seed_scope


class ExtractionTests(unittest.TestCase):
    def test_parameter_order_excludes_heads_and_matches_direct_reference(self):
        names = ("weight_ih_l0", "weight_hh_l0", "bias_ih_l0", "bias_hh_l0",
                 "weight_ih_l1", "weight_hh_l1", "bias_ih_l1", "bias_hh_l1")
        self.assertEqual(PARAMETERS, names)
        for formulation in ("M0", "M1"):
            with self.subTest(formulation=formulation), cpu_seed_scope(13):
                live = LSTM(formulation=formulation, block="fastStorage", tasks=RESOURCES, hidden_size=64)
                X = torch.randn(6, 4, 4)
                y = torch.randn(6, 4, 5)
                clone = DiagnosticClone(live, live.state_dict())
                self.assertFalse(clone.model.training)
                self.assertTrue(all(not p.requires_grad for p in clone.model.heads.parameters()))
                encoder = dict(clone.model.encoder.named_parameters())
                self.assertEqual([id(p) for p in clone.parameters], [id(encoder[n]) for n in names])
                self.assertTrue(all(p.device.type == "cpu" and p.dtype == torch.float32 for p in clone.parameters))
                forwards = []
                handle = clone.model.register_forward_pre_hook(lambda _, inputs: forwards.append(inputs[0].clone()))
                actual = clone.extract(X, y)
                handle.remove()
                self.assertEqual(len(forwards), 1)
                torch.testing.assert_close(forwards[0], X, atol=0, rtol=0)
                direct = deepcopy(live).eval()
                p = dict(direct.encoder.named_parameters())
                for index, task in enumerate(RESOURCES):
                    loss = torch.nn.functional.mse_loss(direct(X)[:, index, :], y[:, index, :])
                    expected = torch.cat([g.flatten() for g in torch.autograd.grad(loss, tuple(p[n] for n in names))])
                    torch.testing.assert_close(actual[task], expected, atol=1e-8, rtol=1e-6)
                    self.assertFalse(actual[task].requires_grad)
                self.assertTrue(all(p.grad is None for p in live.parameters()))
