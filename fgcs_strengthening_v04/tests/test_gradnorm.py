import math
import unittest
from unittest.mock import patch

import torch

from fgcs_strengthening_v04.src.identity import RESOURCES
from fgcs_strengthening_v04.src.models.lstm import LSTM
from fgcs_strengthening_v04.src.optim import gradnorm
from fgcs_strengthening_v04.src.training import cpu_seed_scope, task_mse


def m1():
    return LSTM(formulation="M1", block="fastStorage", tasks=RESOURCES, hidden_size=64)


class GradNormTests(unittest.TestCase):
    def test_manual_ratios_rates_norms_targets_and_weight_only_derivative(self):
        loss = torch.tensor([1., 2., 3., 4.], requires_grad=True)
        initial = torch.tensor([1., 1., 3., 2.])
        weights = torch.tensor([1., 2., .5, .5], requires_grad=True)
        norms = torch.tensor([2., 3., 4., 6.], requires_grad=True)
        q, r, G, target, objective = gradnorm.balance_terms(loss, initial, weights, norms)
        expected_q = torch.tensor([1., 2., 1., 2.], dtype=torch.float64)
        expected_r = expected_q / 1.5
        expected_G = torch.tensor([2., 6., 2., 3.])
        expected_target = 3.25 * expected_r.pow(1.5)
        self.assertEqual(gradnorm.ALPHA, 1.5)
        torch.testing.assert_close(q, expected_q)
        torch.testing.assert_close(r, expected_r)
        torch.testing.assert_close(G, expected_G)
        torch.testing.assert_close(target, expected_target)
        self.assertFalse(target.requires_grad)
        torch.testing.assert_close(objective, (expected_G - expected_target).abs().sum())
        dw, dl, dn = torch.autograd.grad(objective, (weights, loss, norms), allow_unused=True)
        torch.testing.assert_close(dw, torch.tensor([2., 3., 4., -6.]))
        self.assertIsNone(dl)
        self.assertIsNone(dn)

    def test_norm_uses_all_four_registered_layer_two_tensors(self):
        with cpu_seed_scope(2):
            model = m1()
            names = ("weight_ih_l1", "weight_hh_l1", "bias_ih_l1", "bias_hh_l1")
            self.assertEqual(gradnorm.NORM_PARAMETERS, names)
            by_name = dict(model.encoder.named_parameters())
            parameters = gradnorm.norm_parameters(model)
            self.assertEqual([id(p) for p in parameters], [id(by_name[name]) for name in names])
            linear = sum((i + 1) * p.flatten()[0] for i, p in enumerate(parameters))
            losses = torch.stack([(i + 1) * linear for i in range(4)])
            expected = torch.arange(1, 5, dtype=torch.float64) * math.sqrt(30)
            torch.testing.assert_close(gradnorm.unweighted_norms(losses, parameters), expected)

    def test_first_forward_reference_unit_weights_and_update_order(self):
        with cpu_seed_scope(0):
            model = m1()
            controller = gradnorm.GradNorm(model)
            optimizer = torch.optim.Adam(model.parameters(), lr=.001)
            X, y = torch.randn(6, 4, 4), torch.randn(6, 4, 5)
            losses = task_mse(model(X), y)
            expected = torch.autograd.grad(losses.mean(), tuple(model.parameters()), retain_graph=True)
            initial_model = [p.detach().clone() for p in model.parameters()]
            order = []
            weight_step, model_step = controller.weight_optimizer.step, optimizer.step
            real_clip = torch.nn.utils.clip_grad_norm_

            def weights_first():
                order.append("weights")
                self.assertTrue(all(torch.equal(a, b) for a, b in zip(initial_model, model.parameters(), strict=True)))
                self.assertTrue(all(p.grad is None for p in model.parameters()))
                return weight_step()

            def clip(parameters, max_norm, **kwargs):
                order.append("clip")
                self.assertEqual(max_norm, 1.)
                for p, want in zip(parameters, expected, strict=True):
                    self.assertTrue(torch.equal(p.grad, want))
                return real_clip(parameters, max_norm, **kwargs)

            def model_second():
                order.append("model")
                self.assertFalse(torch.equal(controller.weights, torch.ones(4)))
                return model_step()

            original_grad = torch.autograd.grad

            def guarded_grad(*args, **kwargs):
                self.assertEqual(order, [], "A gradient was computed after the weight update")
                return original_grad(*args, **kwargs)

            record = {}
            with patch.object(controller.weight_optimizer, "step", side_effect=weights_first), patch.object(
                optimizer, "step", side_effect=model_second
            ), patch("torch.nn.utils.clip_grad_norm_", side_effect=clip), patch(
                "torch.autograd.grad", side_effect=guarded_grad
            ):
                controller.step(model, optimizer, losses, clip=1., record=record)
            self.assertEqual(order, ["weights", "clip", "model"])
            torch.testing.assert_close(controller.initial_losses, losses.detach() / 4, atol=0, rtol=0)
            self.assertEqual(record["model_loss"], losses.mean().item())
            self.assertEqual(record["q"], [1.] * 4)
            self.assertAlmostEqual(controller.weights.sum().item(), 4., places=6)
            self.assertEqual(controller.weight_optimizer.param_groups[0]["lr"], .025)
            self.assertIsNotNone(record["renormalisation_factor"])

    def test_zero_subgradient_at_ties_and_zero_norm(self):
        weights = torch.ones(4, requires_grad=True)
        losses = torch.ones(4)
        equal = gradnorm.balance_terms(losses, losses, weights, torch.ones(4))[-1]
        self.assertEqual(equal.item(), 0.)
        self.assertTrue(torch.equal(torch.autograd.grad(equal, weights)[0], torch.zeros(4)))
        with_zero = gradnorm.balance_terms(losses, losses, weights, torch.tensor([0., 1., 1., 1.]))[-1]
        self.assertEqual(torch.autograd.grad(with_zero, weights)[0][0].item(), 0.)

    def test_invalid_reference_rates_and_proposed_weight_fail_closed(self):
        weights = torch.ones(4, requires_grad=True)
        losses, norms = torch.ones(4), torch.ones(4)
        for actual, reference, error in (
            (losses, torch.tensor([0., 1., 1., 1.]), "reference loss"),
            (torch.zeros(4), losses, "mean loss ratio"),
            (torch.tensor([float("nan"), 1., 1., 1.]), losses, "loss ratios"),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(FloatingPointError, error):
                gradnorm.balance_terms(actual, reference, weights, norms)
        with cpu_seed_scope(4):
            model = m1()
            controller = gradnorm.GradNorm(model)
            optimizer = torch.optim.Adam(model.parameters(), lr=.001)
            actual = task_mse(model(torch.randn(5, 4, 4)), torch.randn(5, 4, 5))
            saved = [p.detach().clone() for p in model.parameters()]

            def bad_weight_step():
                with torch.no_grad():
                    controller.weights[0] = 0.

            record = {}
            with patch.object(controller.weight_optimizer, "step", side_effect=bad_weight_step), patch.object(
                optimizer, "step", wraps=optimizer.step
            ) as forbidden, self.assertRaisesRegex(FloatingPointError, "proposed task weight"):
                controller.step(model, optimizer, actual, clip=1., record=record)
            forbidden.assert_not_called()
            self.assertEqual(record["weights_proposed"][0], 0.)
            self.assertTrue(all(torch.equal(a, b) for a, b in zip(saved, model.parameters(), strict=True)))
