import unittest

import torch

from fgcs_strengthening_v04.src.identity import RESOURCES
from fgcs_strengthening_v04.src.models.patchtst import PatchTST
from fgcs_strengthening_v04.src.training import cpu_seed_scope


class PatchTSTTests(unittest.TestCase):
    def test_patch_count_lag_coverage_and_transformer_spec(self):
        for L, count in ((4, 3), (9, 8), (18, 17)):
            model = PatchTST(L, ("CPU",))
            lags = torch.arange(L, dtype=torch.float32).reshape(1, L, 1)
            patches = model.patches(lags)
            self.assertEqual(patches.shape, (1, 1, count, 2))
            torch.testing.assert_close(patches[0, 0], torch.stack((lags[0, :-1, 0], lags[0, 1:, 0]), dim=1))
            self.assertEqual(tuple(model.position.shape), (count, 64))
            self.assertTrue(model.position.requires_grad)
            self.assertEqual(len(model.backbone.layers), 2)
            for layer in model.backbone.layers:
                self.assertEqual(layer.self_attn.num_heads, 4)
                self.assertEqual(layer.linear1.out_features, 128)
                self.assertEqual(layer.dropout.p, .1)
                self.assertFalse(layer.norm_first)

    def test_shared_backbone_separate_heads_and_no_cross_channel_mixing(self):
        with cpu_seed_scope(0):
            model = PatchTST(9, RESOURCES).eval()
            independent = PatchTST(9, ("MEMORY",)).eval()
            independent.patch_projection.load_state_dict(model.patch_projection.state_dict())
            independent.backbone.load_state_dict(model.backbone.state_dict())
            independent.heads["MEMORY"].load_state_dict(model.heads["MEMORY"].state_dict())
            with torch.no_grad():
                independent.position.copy_(model.position)
            seen = []
            hook = model.backbone.register_forward_pre_hook(lambda _, inputs: seen.append(inputs[0].shape))
            X = torch.randn(2, 9, 4)
            base = model(X)
            hook.remove()
            self.assertEqual(seen, [(8, 8, 64)])
            self.assertEqual(len({id(head.weight) for head in model.heads.values()}), 4)
            torch.testing.assert_close(base[:, 2:3], independent(X[:, :, 2:3]))
            changed = X.clone()
            changed[:, :, 1] += 10
            self.assertTrue(torch.equal(model(changed)[:, (0, 2, 3)], base[:, (0, 2, 3)]))

    def test_seeded_training_mode_forward_backward(self):
        def run():
            with cpu_seed_scope(0):
                model = PatchTST(4, RESOURCES)
                X = torch.randn(2, 4, 4)
                output = model(X)
                gradients = torch.autograd.grad(output.square().mean(), tuple(model.parameters()))
                return output.detach(), gradients

        first, gradients = run()
        second, repeated = run()
        self.assertTrue(torch.equal(first, second))
        self.assertTrue(all(torch.equal(a, b) and torch.isfinite(a).all()
                            for a, b in zip(gradients, repeated, strict=True)))
