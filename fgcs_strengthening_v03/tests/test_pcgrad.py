import unittest
from unittest.mock import patch

import torch

from fgcs_strengthening_v03.src.diagnostics.gradients import live_state_hashes
from fgcs_strengthening_v03.src.identity import RESOURCES
from fgcs_strengthening_v03.src.models.lstm import LSTM
from fgcs_strengthening_v03.src.optim import pcgrad
from fgcs_strengthening_v03.src.training import cpu_seed_scope, task_mse


class PCGradTests(unittest.TestCase):
    def test_aligned_and_zero_direction(self):
        vectors = torch.tensor([[1., 2.], [2., 4.], [0., 0.]])
        result = pcgrad.project_shared(vectors, [[1, 2], [0, 2], [0, 1]])
        torch.testing.assert_close(result.projected, vectors.double())
        torch.testing.assert_close(result.mean, vectors.mean(dim=0))
        self.assertEqual(result.projection_count, 0)
        self.assertEqual(result.zero_norm_skips, 2)

    def test_conflicting_two_task_vectors_use_immutable_originals(self):
        vectors = torch.tensor([[1., 0.], [-1., 1.]])
        result = pcgrad.project_shared(vectors, [[1], [0]])
        torch.testing.assert_close(result.projected, torch.tensor([[.5, .5], [0., 1.]], dtype=torch.float64))
        torch.testing.assert_close(result.mean, torch.tensor([.25, .75]))
        self.assertEqual(result.projection_count, 2)
        self.assertEqual([r["original_dot"] for r in result.comparisons], [-1, -1])
        self.assertEqual([r["dot_after"] for r in result.comparisons], [0, 0])
        torch.testing.assert_close(vectors, torch.tensor([[1., 0.], [-1., 1.]]))

    def test_sequential_projection_is_order_sensitive(self):
        vectors = torch.tensor([[1., 0.], [-1., 1.], [-1., -2.]])
        first = pcgrad.project_shared(vectors, [[1, 2], [0, 2], [0, 1]])
        reverse = pcgrad.project_shared(vectors, [[2, 1], [0, 2], [0, 1]])
        torch.testing.assert_close(first.projected[0], torch.tensor([.2, -.1], dtype=torch.float64))
        torch.testing.assert_close(reverse.projected[0], torch.tensor([.2, .2], dtype=torch.float64))

    def test_keyed_permutations_and_projection_leave_live_rngs_unchanged(self):
        with cpu_seed_scope(2) as shuffle:
            model = LSTM(formulation="M1", block="fastStorage", tasks=RESOURCES, hidden_size=64)
            optimizer = torch.optim.Adam(model.parameters())
            before = live_state_hashes(model, optimizer, shuffle)
            gradients = torch.tensor([[1., 0.], [-1., 1.], [-1., -2.], [0., 1.]])
            first = pcgrad.permutation_schedule(2, 3, 1)
            second = pcgrad.permutation_schedule(2, 3, 1)
            self.assertEqual(first, second)
            self.assertEqual(len(set(first[0])), 4)
            self.assertNotEqual(first[0], pcgrad.permutation_schedule(2, 3, 2)[0])
            for task, order in enumerate(first[1]):
                self.assertEqual(set(order), set(range(4)) - {task})
            one = pcgrad.project_shared(gradients, first[1])
            two = pcgrad.project_shared(gradients, second[1])
            self.assertTrue(torch.equal(one.mean, two.mean))
            self.assertEqual(live_state_hashes(model, optimizer, shuffle), before)

    def test_heads_keep_mean_loss_gradient_and_clip_sees_assembled_model(self):
        with cpu_seed_scope(0):
            model = LSTM(formulation="M1", block="fastStorage", tasks=RESOURCES, hidden_size=64)
            optimizer = torch.optim.Adam(model.parameters(), lr=.001)
            losses = task_mse(model(torch.randn(4, 4, 4)), 100 + torch.randn(4, 4, 5))
            heads = tuple(model.heads.parameters())
            expected = torch.autograd.grad(losses.mean(), heads, retain_graph=True)
            captured = {}
            real_clip = torch.nn.utils.clip_grad_norm_

            def clip(parameters, max_norm, **kwargs):
                parameters = tuple(parameters)
                self.assertEqual(max_norm, 1)
                self.assertTrue(all(p.grad is not None for p in parameters))
                for p, want in zip(heads, expected, strict=True):
                    self.assertTrue(torch.equal(p.grad, want))
                captured["shared"] = torch.cat([p.grad.flatten() for p in model.encoder.parameters()]).clone()
                return real_clip(parameters, max_norm, **kwargs)

            record = {}
            with patch("torch.nn.utils.clip_grad_norm_", side_effect=clip) as call:
                result = pcgrad.step(model, optimizer, losses, seed=0, epoch=1, batch=0, clip=1., record=record)
            call.assert_called_once()
            self.assertTrue(torch.equal(result.mean, captured["shared"]))
            self.assertGreater(record["model_gradient_norm_before_clip"], 1)
            self.assertLessEqual(torch.linalg.vector_norm(torch.cat([p.grad.flatten() for p in model.parameters()])), 1.)
