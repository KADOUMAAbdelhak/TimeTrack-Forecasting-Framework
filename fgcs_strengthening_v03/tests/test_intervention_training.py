from dataclasses import replace
import io
import json
import unittest
from unittest.mock import patch

import torch

from fgcs_strengthening_v03.src.models.lstm import LSTM
from fgcs_strengthening_v03.src.optim.gradnorm import GradNorm
from fgcs_strengthening_v03.src.provenance import DuplicateIdentity, sha256_file
from fgcs_strengthening_v03.src.training import _evaluate, _windows, cpu_seed_scope, task_mse
from fgcs_strengthening_v03.tests.training_fixtures import identity, partition, scratch_engine


def run(mode):
    inner = replace(identity(), arm=mode, variant=mode)
    final = replace(inner, phase="final")
    results = []
    with scratch_engine() as engine:
        for fit, unit in ((engine.fit_inner, inner), (engine.fit_final, final)):
            prepared, accesses = partition(unit, n=257 if mode == "gradnorm" else 9)
            validated = []

            def validation(model, windows):
                values = _evaluate(model, windows)
                with torch.no_grad():
                    manual = (model(windows[0]).double() - windows[1].double()).square().mean(dim=(0, 2))
                torch.testing.assert_close(torch.tensor(values, dtype=torch.float64), manual)
                validated.append(values)
                return values

            with patch("fgcs_strengthening_v03.src.training._evaluate", side_effect=validation):
                result = fit(unit, prepared, mode=mode)
            evidence = result.evidence
            assert accesses == ([0, 1] if unit.phase == "inner" else [0])
            assert len(validated) == (len(evidence["epochs"]) if unit.phase == "inner" else 0)
            outcome = engine.journal.runtime / "outcomes" / f"{unit.digest}.json"
            before = sha256_file(outcome)
            saved = json.loads(outcome.read_text())
            assert saved["identity"] == unit.payload()
            assert saved["fingerprint_sha256"] == engine.journal.seal.digest
            assert saved["evidence"] == evidence
            try:
                fit(unit, prepared, mode=mode)
            except DuplicateIdentity:
                pass
            else:
                raise AssertionError("Duplicate intervention accepted")
            assert sha256_file(outcome) == before
            intervention = evidence["intervention"]
            assert intervention["mode"] == mode
            assert intervention["model_optimizer"]["lr"] == .001
            if mode == "gradnorm":
                snapshot = torch.load(io.BytesIO(result.resume_state), weights_only=True)
                reference = intervention["optimizer_state"]
                path = engine.journal.runtime / reference["path"]
                assert sha256_file(path) == reference["sha256"]
                state = torch.load(path, weights_only=True)
                assert state["identity"] == unit.payload()
                assert state["fingerprint_sha256"] == engine.journal.seal.digest
                assert state["epoch"] == len(evidence["epochs"])
                assert state["model_optimizer"]["state"]
                assert state["gradnorm"]["weight_optimizer"]["state"]
                assert torch.equal(state["gradnorm"]["weights"], snapshot["gradnorm"]["weights"])
                X, y = _windows(prepared.training(), unit, prepared.context)
                with cpu_seed_scope(unit.seed) as shuffle:
                    model = LSTM(formulation="M1", block=unit.block, tasks=unit.tasks, hidden_size=64)
                    indices = torch.randperm(len(X), generator=shuffle)[:256]
                    expected = (task_mse(model(X[indices]), y[indices]) / 4).detach().tolist()
                steps = intervention["epochs"][0]["steps"]
                assert len(steps) == 2
                assert steps[0]["initial_losses"] == expected
                assert steps[1]["initial_losses"] == expected
                assert intervention["alpha"] == 1.5
                assert intervention["weight_optimizer"]["lr"] == .025
            else:
                step = intervention["epochs"][0]["steps"][0]
                assert len(step["permutation_orders"]) == len(step["permutation_seeds"]) == 4
                assert step["clip_max_norm"] == 1
            results.append({key: evidence[key] for key in
                            ("epochs", "initial_model_sha256", "terminal_model_sha256", "selection")})
            results[-1]["intervention_steps"] = intervention["epochs"]
    assert results[0]["initial_model_sha256"] == results[1]["initial_model_sha256"]
    assert len(results[1]["epochs"]) == results[0]["selection"]["joint_epoch"]
    assert results[0]["selection"]["task_epochs"] == {}
    return results


class InterventionTrainingTests(unittest.TestCase):
    def test_modes_require_declared_m1_intervention_identity(self):
        with scratch_engine() as engine:
            for formulation in ("S1", "S2", "M0", "M1"):
                unit = identity(formulation)
                for mode in ("pcgrad", "gradnorm"):
                    prepared, accesses = partition(unit)
                    with self.assertRaises(ValueError):
                        engine.fit_inner(unit, prepared, mode=mode)
                    self.assertEqual(accesses, [])
            unit = replace(identity(), arm="pcgrad", variant="pcgrad")
            prepared, accesses = partition(unit)
            with self.assertRaises(ValueError):
                engine.fit_inner(unit, prepared, mode="gradnorm")
            with self.assertRaises(ValueError):
                engine.fit_inner(unit, prepared)
            self.assertEqual(accesses, [])

    def test_explicit_equal_loss_matches_default_stage3b_trajectory(self):
        unit = identity("M0")
        histories = []
        for options in ({}, {"mode": "equal_loss"}):
            with scratch_engine() as engine:
                result = engine.fit_inner(unit, partition(unit)[0], **options).evidence
                self.assertNotIn("intervention", result)
                histories.append({key: result[key] for key in
                                  ("epochs", "initial_model_sha256", "terminal_model_sha256", "selection")})
        self.assertEqual(*histories)

    def test_both_interventions_repeat_exact_inner_and_final_trajectories(self):
        for mode in ("pcgrad", "gradnorm"):
            with self.subTest(mode=mode):
                self.assertEqual(run(mode), run(mode))

    def test_invalid_gradnorm_reference_is_terminal(self):
        unit = replace(identity(), arm="gradnorm", variant="gradnorm")
        phase, _ = partition(unit)
        actual = GradNorm.step

        def zero_reference(controller, model, optimizer, losses, **kwargs):
            return actual(controller, model, optimizer, losses * 0, **kwargs)

        with scratch_engine() as engine, patch.object(GradNorm, "step", new=zero_reference):
            with self.assertRaisesRegex(FloatingPointError, "reference loss"):
                engine.fit_inner(unit, phase, mode="gradnorm")
            record = json.loads((engine.journal.runtime / "outcomes" / f"{unit.digest}.json").read_text())
            self.assertEqual(record["status"], "failed")
            step = record["evidence"]["intervention"]["epochs"][0]["steps"][0]
            self.assertEqual(step["initial_losses"], [0.] * 4)
            with self.assertRaises(DuplicateIdentity):
                engine.fit_inner(unit, phase, mode="gradnorm")
