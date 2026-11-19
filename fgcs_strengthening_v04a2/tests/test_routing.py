import unittest

import torch

from fgcs_strengthening_v04a2.src.identity import RESOURCES
from fgcs_strengthening_v04a2.src.models.lstm import LSTM


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.rng = torch.random.fork_rng(devices=[])
        self.rng.__enter__()
        self.addCleanup(self.rng.__exit__, None, None, None)
        torch.manual_seed(73)
        self.windows = torch.randn(3, 9, 4)

    def model(self, formulation, tasks=RESOURCES, hidden_size=64):
        return LSTM(formulation=formulation, block="fastStorage", tasks=tasks, hidden_size=hidden_size).eval()

    @torch.no_grad()
    def test_s1_uses_only_own_channel_for_every_target(self):
        for index, task in enumerate(RESOURCES):
            with self.subTest(task=task):
                model = self.model("S1", (task,))
                changed = self.windows + 3
                changed[:, :, index] = self.windows[:, :, index]
                self.assertTrue(torch.equal(model(self.windows), model(changed)))
                changed[:, :, index] += 3
                self.assertFalse(torch.equal(model(self.windows), model(changed)))
                self.assertEqual(model(self.windows).shape, (3, 1, 5))

    @torch.no_grad()
    def test_s2_and_m1_joint_encoder_sees_all_four_histories(self):
        for formulation in ("S2", "M1"):
            complements = ((task,) for task in RESOURCES) if formulation == "S2" else (RESOURCES,)
            for tasks in complements:
                with self.subTest(formulation=formulation, tasks=tasks):
                    model = self.model(formulation, tasks)
                    captured = []
                    hook = model.encoder.register_forward_pre_hook(lambda _, args: captured.append(args[0]))
                    try:
                        baseline = model(self.windows)
                    finally:
                        hook.remove()
                    self.assertEqual(len(captured), 1)
                    self.assertIs(captured[0], self.windows)
                    for index in range(4):
                        changed = self.windows.clone()
                        changed[:, :, index] += 3
                        delta = (baseline - model(changed)).abs().amax(dim=(0, 2))
                        self.assertTrue((delta > 0).all())

    @torch.no_grad()
    def test_m0_reuses_encoder_and_isolates_every_other_history(self):
        for width in (64,):
            model = self.model("M0", hidden_size=width)
            calls = []
            hook = model.encoder.register_forward_pre_hook(
                lambda encoder, args: calls.append((encoder.weight_ih_l0, args[0].clone())))
            try:
                latent = model.encode(self.windows)
            finally:
                hook.remove()
            self.assertEqual(len(calls), 4)
            self.assertEqual([name for name, _ in model.named_children()], ["encoder", "heads"])
            for index, (parameter, history) in enumerate(calls):
                self.assertIs(parameter, model.encoder.weight_ih_l0)
                self.assertTrue(torch.equal(history, self.windows[:, :, index:index + 1]))
            output = model(self.windows)
            for index, task in enumerate(RESOURCES):
                changed = self.windows.clone()
                changed[:, :, index] += 3
                observed = model.encode(changed)
                changed_output = model(changed)
                for other_index, other in enumerate(RESOURCES):
                    self.assertEqual(torch.equal(latent[other], observed[other]), other != task)
                    self.assertEqual(torch.equal(output[:, other_index], changed_output[:, other_index]), other != task)

    @torch.no_grad()
    def test_transfer_subset_routes_omitted_inputs_correctly(self):
        tasks = ("MEMORY", "CPU")
        changed = self.windows.clone()
        changed[:, :, RESOURCES.index("DISK_WRITE")] += 3
        own = self.model("M0", tasks)
        joint = self.model("M1", tasks)
        self.assertEqual(own.tasks, ("CPU", "MEMORY"))
        self.assertEqual(tuple(own.heads), own.tasks)
        self.assertEqual(tuple(joint.heads), joint.tasks)
        self.assertEqual(own(self.windows).shape, (3, 2, 5))
        self.assertTrue(torch.equal(own(self.windows), own(changed)))
        self.assertFalse(torch.equal(joint(self.windows), joint(changed)))
