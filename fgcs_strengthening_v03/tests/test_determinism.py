import io
import random
import unittest

import numpy as np
import torch

from fgcs_strengthening_v03.src.training import (
    LSTM, _encode, _optimise_epoch, _state_hash, _windows, capture_epoch_state, cpu_seed_scope,
)
from fgcs_strengthening_v03.tests.training_fixtures import identity, partition, scratch_engine


def run(unit):
    with scratch_engine() as engine:
        phase, _ = partition(unit, n=15)
        return engine.fit_inner(unit, phase)


class DeterminismTests(unittest.TestCase):
    def test_same_identity_is_exact_and_changed_seed_changes_training(self):
        unit = identity("M0")
        caller_python, caller_numpy = random.getstate(), np.random.get_state()
        caller_torch = torch.random.get_rng_state()
        first = run(unit)
        second = run(unit)
        other = run(identity("M0", seed=1))
        for field in ("initial_model_sha256", "epochs", "selection", "terminal_model_sha256"):
            self.assertEqual(first.evidence[field], second.evidence[field])
        self.assertNotEqual(first.evidence["initial_model_sha256"], other.evidence["initial_model_sha256"])
        self.assertNotEqual(first.evidence["epochs"][0]["batch_order_sha256"], other.evidence["epochs"][0]["batch_order_sha256"])
        self.assertNotEqual(first.evidence["terminal_model_sha256"], other.evidence["terminal_model_sha256"])
        self.assertEqual(random.getstate(), caller_python)
        np.testing.assert_equal(np.random.get_state(), caller_numpy)
        self.assertTrue(torch.equal(torch.random.get_rng_state(), caller_torch))

    def test_serialised_epoch_state_replays_same_next_optimisation_epoch(self):
        unit = identity("M0")
        phase, _ = partition(unit, n=15)
        windows = _windows(phase.training(), unit, phase.context)

        def initialise():
            model = LSTM(formulation=unit.formulation, block=unit.block, tasks=unit.tasks, hidden_size=64)
            return model, torch.optim.Adam(model.parameters(), lr=0.001)

        def next_epoch(model, optimizer, generator):
            return (random.random(), np.random.random(),
                    _optimise_epoch(model, optimizer, windows, generator), _state_hash(model.state_dict()))

        with cpu_seed_scope(unit.seed) as gen:
            model, optimizer = initialise()
            _optimise_epoch(model, optimizer, windows, gen)
            encoded = _encode(capture_epoch_state(model, optimizer, gen, identity=unit,
                                                 fingerprint_sha256="a" * 64, evidence={"epochs": [{}]}))
            uninterrupted = next_epoch(model, optimizer, gen)
        state = torch.load(io.BytesIO(encoded), weights_only=True)
        self.assertEqual(state["identity"], unit.payload())
        self.assertEqual(state["epoch"], 1)
        with cpu_seed_scope(9) as gen:
            model, optimizer = initialise()
            model.load_state_dict(state["model"])
            model.train(state["model_training"])
            optimizer.load_state_dict(state["optimizer"])
            random.setstate(state["rng"]["python"])
            kind, keys, *rest = state["rng"]["numpy"]
            np.random.set_state((kind, np.array(keys, dtype=np.uint32), *rest))
            torch.random.set_rng_state(state["rng"]["torch_cpu"])
            gen.set_state(state["rng"]["shuffle"])
            restored = next_epoch(model, optimizer, gen)
        self.assertEqual(uninterrupted, restored)
