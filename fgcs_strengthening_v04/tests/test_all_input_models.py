"""v0.4 all-input DLinear (S2/M1) and channel-dependent PatchTST-style (S2/M1). Synthetic tensors only."""

import unittest

import torch
from torch.nn import functional as F

from fgcs_strengthening_v04.src.identity import RESOURCES
from fgcs_strengthening_v04.src.models.dlinear import DLinear, DLinearAllInput
from fgcs_strengthening_v04.src.models.itransformer import ITransformer
from fgcs_strengthening_v04.src.models.patchtst import PatchTST, PatchTSTChannelDependent
from fgcs_strengthening_v04.src.models.registry import REGISTRY
from fgcs_strengthening_v04.src.modern.structure import validate_family_structure
from fgcs_strengthening_v04.src.training import cpu_seed_scope

MEMORY = ("MEMORY",)


class RegistryTests(unittest.TestCase):
    def test_each_scope_builds_its_registered_class(self):
        expected = {("DLinear", "own"): DLinear, ("DLinear", "all"): DLinearAllInput,
                    ("PatchTST", "own"): PatchTST, ("PatchTST", "all"): PatchTSTChannelDependent,
                    ("iTransformer", "all"): ITransformer}
        self.assertEqual({(f, s) for f in REGISTRY for s in REGISTRY[f].scopes}, set(expected))
        for (family, scope), cls in expected.items():
            for tasks in (MEMORY, RESOURCES):
                self.assertIs(type(REGISTRY[family].build(9, tasks, scope)), cls)

    def test_undefined_cells_and_contexts_are_refused(self):
        with self.assertRaisesRegex(ValueError, "no 'own'-input model"):
            REGISTRY["iTransformer"].build(9, MEMORY, "own")
        with self.assertRaises(ValueError):
            REGISTRY["DLinear"].build(9, MEMORY, "both")
        with self.assertRaises(ValueError):
            REGISTRY["PatchTST"].build(10, MEMORY, "all")
        with self.assertRaises(ValueError):
            REGISTRY["DLinear"].build(9, RESOURCES[:2], "all")


class DLinearAllInputTests(unittest.TestCase):
    def setUp(self):
        self.windows = torch.randn(3, 18, 4, generator=torch.Generator().manual_seed(1))

    def test_s2_is_one_linear_map_over_every_channels_trend_and_residual(self):
        model = DLinearAllInput(18, MEMORY)
        self.assertIsNone(model.bottleneck)
        self.assertEqual(model.kernel, 17)
        histories = self.windows.transpose(1, 2)
        trend = F.avg_pool1d(F.pad(histories, (8, 8), mode="replicate"), 17, stride=1)
        features = torch.cat((trend, histories - trend), dim=-1).flatten(1)
        self.assertEqual(features.shape, (3, 8 * 18))
        head = model.heads["MEMORY"]
        expected = features @ head.weight.T + head.bias
        torch.testing.assert_close(model(self.windows), expected[:, None, :])

    def test_m1_shares_a_bias_free_rank_16_bottleneck_with_four_heads(self):
        model = DLinearAllInput(18, RESOURCES)
        self.assertEqual((model.bottleneck.in_features, model.bottleneck.out_features), (144, 16))
        self.assertIsNone(model.bottleneck.bias)
        self.assertEqual(tuple(model.heads), RESOURCES)
        latent = model.bottleneck(model.features(self.windows))
        expected = torch.stack([model.heads[t](latent) for t in RESOURCES], dim=1)
        torch.testing.assert_close(model(self.windows), expected)
        # The composed map from 8L features to all 20 outputs has rank at most 16.
        composed = torch.cat([model.heads[t].weight for t in RESOURCES]) @ model.bottleneck.weight
        self.assertLessEqual(torch.linalg.matrix_rank(composed).item(), 16)

    def test_kernels_and_parameter_counts_follow_the_context(self):
        for context, kernel in ((4, 3), (9, 9), (18, 17)):
            s2, m1 = DLinearAllInput(context, MEMORY), DLinearAllInput(context, RESOURCES)
            self.assertEqual((s2.kernel, m1.kernel), (kernel, kernel))
            self.assertEqual(sum(p.numel() for p in s2.parameters()), 8 * context * 5 + 5)
            self.assertEqual(sum(p.numel() for p in m1.parameters()), 8 * context * 16 + 4 * (16 * 5 + 5))

    def test_requires_all_four_channels(self):
        with self.assertRaisesRegex(ValueError, "four resource channels"):
            DLinearAllInput(18, MEMORY)(self.windows[:, :, :1])


class PatchTSTChannelDependentTests(unittest.TestCase):
    def test_each_token_holds_every_channels_values_for_one_patch(self):
        context = 9
        values = torch.arange(context * 4, dtype=torch.float32).reshape(1, context, 4)
        patches = PatchTSTChannelDependent(context, MEMORY).patches(values)
        self.assertEqual(patches.shape, (1, context - 1, 4, 2))
        for patch in range(context - 1):
            for channel in range(4):
                self.assertEqual(patches[0, patch, channel].tolist(),
                                 [values[0, patch, channel].item(), values[0, patch + 1, channel].item()])

    def test_shapes_heads_and_token_projection(self):
        windows = torch.randn(2, 18, 4)
        for tasks in (MEMORY, RESOURCES):
            model = PatchTSTChannelDependent(18, tasks).eval()
            self.assertEqual(model.patch_projection.in_features, 8)
            self.assertEqual(model.patch_count, 17)
            self.assertEqual(tuple(model.heads), tasks)
            self.assertEqual(model(windows).shape, (2, len(tasks), 5))
        with self.assertRaisesRegex(ValueError, "four resource channels"):
            PatchTSTChannelDependent(18, MEMORY)(windows[:, :, :1])

    def test_construction_is_deterministic_under_the_cpu_seed(self):
        states = []
        for _ in range(2):
            with cpu_seed_scope(7):
                states.append(PatchTSTChannelDependent(9, RESOURCES).state_dict())
        for name, tensor in states[0].items():
            self.assertTrue(torch.equal(tensor, states[1][name]), name)


class StructuralCheckTests(unittest.TestCase):
    def test_all_input_cells_route_every_resource_to_every_target(self):
        for family in ("DLinear", "PatchTST"):
            records = validate_family_structure(family)
            self.assertEqual(len(records), 30)
            for record in records:
                with self.subTest(family=family, scope=record["scope"], context=record["context"],
                                  tasks=record["tasks"]):
                    dependencies = torch.tensor(record["resource_to_target_dependencies"])
                    if record["scope"] == "all":
                        self.assertEqual(record["channels"], 4)
                        self.assertTrue(dependencies.all())
                    else:
                        self.assertTrue(torch.equal(dependencies, torch.eye(len(record["tasks"]), dtype=torch.bool)))

    def test_itransformer_has_only_all_input_cells(self):
        records = validate_family_structure("iTransformer")
        self.assertEqual({r["scope"] for r in records}, {"all"})
        self.assertEqual(len(records), 15)


if __name__ == "__main__":
    unittest.main()
