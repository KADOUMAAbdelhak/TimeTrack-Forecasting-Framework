from dataclasses import replace
import unittest

import torch

from fgcs_strengthening_v04.src.identity import RESOURCES
from fgcs_strengthening_v04.src.models.itransformer import ITransformer
from fgcs_strengthening_v04.src.modern.design import modern_identities
from fgcs_strengthening_v04.src.training import cpu_seed_scope


class ITransformerTests(unittest.TestCase):
    def test_four_tokens_and_every_input_can_affect_each_target(self):
        with cpu_seed_scope(0):
            for L in (4, 9, 18):
                for tasks in (("DISK_WRITE",), RESOURCES):
                    with self.subTest(L=L, tasks=tasks):
                        model = ITransformer(L, tasks).eval()
                        X = torch.randn(2, L, 4)
                        seen = []
                        hook = model.backbone.register_forward_pre_hook(lambda _, inputs: seen.append(inputs[0].shape))
                        base = model(X)
                        hook.remove()
                        self.assertEqual(seen, [(2, 4, 64)])
                        self.assertEqual(base.shape, (2, len(tasks), 5))
                        self.assertEqual(tuple(model.heads), tasks)
                        self.assertTrue(all(head.in_features == 256 for head in model.heads.values()))
                        for channel in range(4):
                            changed = X.clone()
                            changed[:, :, channel] += torch.linspace(.5, 2.5, L)
                            self.assertTrue(((model(changed) - base).abs().amax(dim=(0, 2)) > 0).all())
                        with self.assertRaises(ValueError):
                            model(X[:, :, :1])

    def test_no_registered_single_token_arm(self):
        identities = [identity for identity in modern_identities() if identity.formulation == "iTransformer"]
        self.assertEqual({identity.input_scope for identity in identities}, {"all"})
        self.assertEqual({identity.variant for identity in identities}, {"independent", "shared"})
        with self.assertRaises(ValueError):
            replace(identities[0], input_scope="own")
