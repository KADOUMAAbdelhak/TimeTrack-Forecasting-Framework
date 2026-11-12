import unittest

from fgcs_strengthening_v03.src.identity import RESOURCES
from fgcs_strengthening_v03.src.systems import inference_condition
from fgcs_strengthening_v03.tests.systems_fixtures import complement, plan_for


class SystemsComplementTests(unittest.TestCase):
    def test_independent_runs_targets_sequentially(self):
        for formulation in ("S1", "S2"):
            calls = []
            plan = plan_for(complement(formulation, calls))
            latency, throughput = inference_condition(plan, 128, "forward_only")
            self.assertEqual(calls, [(tuple([task]), 128) for task in RESOURCES] * 120)
            self.assertEqual((latency.subject, latency.provenance.formulation), ("complement", formulation))
            self.assertGreater(throughput.forecasts_per_second, 0)

    def test_shared_uses_one_joint_forward_even_for_target_slice(self):
        for formulation in ("M0", "M1"):
            calls = []
            plan = plan_for(complement(formulation, calls))
            latency, _ = inference_condition(plan, 1, "forward_only", "MEMORY")
            self.assertEqual(calls, [(RESOURCES, 1)] * 120)
            self.assertEqual(latency.subject, "MEMORY")
            self.assertTrue(latency.provenance.formulation.startswith(formulation))
            calls.clear()
            inference_condition(plan, 1, "forward_only")
            self.assertEqual(calls, [(RESOURCES, 1)] * 120)


from dataclasses import replace as _replace
from hashlib import sha256 as _sha256

import numpy as _np
import torch as _torch

from fgcs_strengthening_v03.src.identity import ScientificIdentity
from fgcs_strengthening_v03.src.models.lightgbm import FeatureLayout, encode_booster, fit_horizon
from fgcs_strengthening_v03.src.models.registry import REGISTRY
from fgcs_strengthening_v03.src.systems import (
    CheckpointRef, Complement, ForwardPath, PhysicalState, deployment_rows,
)
from fgcs_strengthening_v03.src.tree.design import GRID
from fgcs_strengthening_v03.tests.systems_fixtures import TinyModel, physical
from fgcs_strengthening_v03.tests.training_fixtures import digest, identity


def _modern(family, variant, task=None):
    tasks = (task,) if variant == "independent" else RESOURCES
    unit = ScientificIdentity("fastStorage", "697", 1, 0, "final", "modern", family, tasks,
                              REGISTRY[family].scope, None, variant)
    with _torch.random.fork_rng(devices=[]):
        _torch.manual_seed(0)
        model = REGISTRY[family].build(4, tasks).eval()
    return unit, model


class ModernTreeAndInterventionComplementTests(unittest.TestCase):
    def test_modern_independent_routes_own_inputs_and_shared_runs_once(self):
        for family in REGISTRY:
            with self.subTest(family=family):
                shapes, paths = [], []
                for task in RESOURCES:
                    unit, model = _modern(family, "independent", task)
                    model.register_forward_pre_hook(lambda module, args, task=task: shapes.append(
                        (task, tuple(args[0].shape))))
                    paths.append(ForwardPath((task,), (physical(unit, model),), model, 4))
                deployment = Complement(paths)
                self.assertEqual(deployment.formulation, f"{family}-independent")
                self.assertEqual(deployment.logical_target_models, 4)
                plan = plan_for(deployment)
                inference_condition(plan, 128, "forward_only")
                width = 1 if REGISTRY[family].scope == "own" else 4
                self.assertEqual(shapes, [(task, (128, 4, width)) for task in RESOURCES] * 120)
                values = _np.random.default_rng(3).normal(size=(2, 4, 4)).astype("float32")
                with _torch.inference_mode():
                    output = deployment.forward(deployment.prepared(values, "complement"), "complement")
                for index, (task, path) in enumerate(zip(RESOURCES, paths)):
                    columns = slice(index, index + 1) if width == 1 else slice(None)
                    with _torch.inference_mode():
                        expected = path.model(_torch.from_numpy(values[:, :, columns]))[:, 0]
                    self.assertTrue(_torch.equal(output[task], expected))

                unit, model = _modern(family, "shared")
                calls = []
                model.register_forward_pre_hook(lambda module, args: calls.append(tuple(args[0].shape)))
                shared = Complement([ForwardPath(RESOURCES, (physical(unit, model),), model, 4)])
                self.assertEqual((shared.formulation, shared.logical_target_models), (f"{family}-shared", 1))
                inference_condition(plan_for(shared), 1, "forward_only", "CPU")
                self.assertEqual(calls, [(1, 4, 4)] * 120)

    def test_lightgbm_wrappers_time_five_scalar_models_per_target(self):
        config = min(GRID, key=lambda item: (item.n_estimators, item.num_leaves))
        generator = _np.random.default_rng(7)
        windows = generator.normal(size=(64, 4, 4)).astype("float32")
        paths, expected = [], {}
        for task in RESOURCES:
            unit = ScientificIdentity("fastStorage", "697", 1, 0, "final", "lightgbm", "LightGBM", (task,), "all",
                                      None, "selected")
            layout = FeatureLayout(4, task, "all")
            states, boosters = [], []
            for horizon in (1, 2, 4, 9, 18):
                fitted = fit_horizon(config, layout.flatten(windows), generator.normal(size=64), layout.names)
                encoded = encode_booster(fitted.booster_)
                import lightgbm
                booster = lightgbm.Booster(model_str=encoded.decode())
                ref = CheckpointRef(unit, _sha256(encoded).hexdigest(), digest("tree" + task), None, horizon)
                states.append(PhysicalState(ref, len(encoded), None, 0, None))
                boosters.append(booster)
            paths.append(ForwardPath((task,), tuple(states), tuple(boosters), 4))
            expected[task] = (layout, boosters)
        deployment = Complement(paths)
        self.assertEqual((deployment.formulation, deployment.logical_target_models), ("LightGBM-all", 4))
        plan = plan_for(deployment, history_calls=[])
        output = deployment.forward(deployment.prepared(plan.scaled_histories[:3], "complement"), "complement")
        for task, (layout, boosters) in expected.items():
            reference = _np.stack([b.predict(layout.flatten(plan.scaled_histories[:3]), num_threads=1)
                                   for b in boosters], axis=-1)
            _np.testing.assert_array_equal(output[task], reference)
        for mode in ("forward_only", "end_to_end_in_memory"):
            latency, throughput = inference_condition(plan, 128, mode)
            self.assertTrue(latency.available)
            self.assertAlmostEqual(throughput.forecasts_per_second, 128 / (latency.mean_ms / 1e3))
        footprints, row = deployment_rows(deployment, plan.binding)
        self.assertEqual((row.physical_checkpoint_count, row.logical_target_models), (20, 4))
        self.assertIsNone(row.total_trainable_parameters)
        self.assertEqual(row.optimizer_state_bytes_by_fit, {})
        self.assertEqual(row.total_deployed_bytes, sum(state.encoded_bytes for state in deployment.states))
        with self.assertRaises(ValueError):
            Complement([_replace(paths[0], states=paths[0].states[:4]), *paths[1:]])

    def test_capacity_and_interventions_are_labelled_single_joint_models(self):
        base = identity("M1", phase="final")
        cases = (
            (_replace(identity("M0", phase="final"), arm="capacity", hidden_size=128), "M0-H128"),
            (identity("M0", phase="final"), "M0-H64"),
            (_replace(base, arm="pcgrad", variant="pcgrad"), "pcgrad-M1"),
            (_replace(base, arm="gradnorm", variant="gradnorm"), "gradnorm-M1"),
        )
        for unit, label in cases:
            calls = []
            model = TinyModel(RESOURCES, calls)
            deployment = Complement([ForwardPath(RESOURCES, (physical(unit, model),), model, 4)])
            self.assertEqual((deployment.formulation, deployment.logical_target_models), (label, 1))
            latency, _ = inference_condition(plan_for(deployment), 128, "forward_only")
            self.assertEqual(latency.provenance.formulation, label)
            self.assertEqual(calls, [(RESOURCES, 128)] * 120)

    def test_incompatible_complements_are_rejected(self):
        calls = []
        s1 = complement("S1", calls)
        with self.assertRaises(ValueError):
            Complement(s1.paths[:3])
        with self.assertRaises(ValueError):
            Complement(s1.paths, task_checkpoints=True)
        other_seed = _replace(s1.paths[0].identity, seed=1)
        moved = ForwardPath(("CPU",), (physical(other_seed, TinyModel(("CPU",), calls)),),
                            s1.paths[0].model, 4)
        with self.assertRaises(ValueError):
            Complement([moved, *s1.paths[1:]])
        with self.assertRaises(ValueError):
            Complement([_replace(s1.paths[0], context=9), *s1.paths[1:]])
        with self.assertRaises(ValueError):
            s1.prepared(_np.ones((1, 4, 4), dtype="float64"), "complement")
