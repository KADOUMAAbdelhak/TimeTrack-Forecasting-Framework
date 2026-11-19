"""Amendment A1: identities, loss-balancing modes, equal-loss identity with v0.4, D-4 binding and decisions."""

from contextlib import contextmanager
from dataclasses import replace
from functools import lru_cache
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from fgcs_strengthening_v04a2.src.diagnostics.engine import DiagnosticEngine, diagnostic_fingerprints
from fgcs_strengthening_v04a2.src.identity import (HOME, RESOURCES, ROOT, ScientificIdentity, diagnostic_parent,
                                                   diagnostic_slot, read_config)
from fgcs_strengthening_v04a2.src.models.lstm import LSTM
from fgcs_strengthening_v04a2.src.orchestrator import persist_resume_state, restore_live_state
from fgcs_strengthening_v04a2.src.training import (BALANCERS, GradNormBalancer, UncertaintyBalancer, cpu_seed_scope,
                                                   task_mse)
from fgcs_strengthening_v04a2.tests.training_fixtures import identity, partition, scratch_engine

CONFIG = read_config()
V04_RUNTIME = ROOT / "fgcs_strengthening_v04" / "runtime"


@lru_cache(maxsize=1)
def seal():
    return diagnostic_fingerprints()


def a1(mode, *, phase="inner", seed=0):
    return ScientificIdentity("fastStorage", "697", 1, seed, phase, "intervention", "M1", RESOURCES, "all", 64, mode)


def fit_pair(engine, unit):
    """Inner then final fit of one A1 identity on the synthetic partition."""
    inner_result = engine.fit_inner(unit, partition(unit)[0], mode=unit.variant)
    final = replace(unit, phase="final")
    return inner_result, engine.fit_final(final, partition(final)[0], mode=unit.variant)


class IdentityTests(unittest.TestCase):
    def test_intervention_identities_are_m1_lstm_only(self):
        for mode in ("gradnorm", "uncertainty"):
            self.assertEqual(a1(mode).arm, "intervention")
        for bad in (dict(formulation="S2", tasks=("CPU",), input_scope="all"),
                    dict(formulation="M0", input_scope="own"), dict(variant="baseline"), dict(variant="pcgrad"),
                    dict(tasks=("CPU", "MEMORY"))):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                replace(a1("gradnorm"), **bad)

    def test_diagnostic_slots_bind_to_their_parent(self):
        unit = replace(a1("gradnorm", phase="final"), arm="diagnostic", variant="gradnorm:final")
        self.assertEqual(diagnostic_slot(unit), "final")
        self.assertEqual(diagnostic_parent(unit), a1("gradnorm", phase="final"))
        core = replace(identity("M1", phase="final"), arm="diagnostic", variant="final")
        self.assertEqual(diagnostic_parent(core), identity("M1", phase="final"))
        for bad in ("gradnorm:mid", "pcgrad:final", "gradnorm"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                replace(unit, variant=bad)
        with self.assertRaises(ValueError):  # an inner-phase diagnostic slot
            replace(unit, phase="inner")

    def test_modes_match_the_configuration(self):
        self.assertEqual(set(BALANCERS), set(CONFIG["intervention"]["modes"]))
        self.assertEqual(CONFIG["intervention"]["modes"]["gradnorm"]["alpha"], 1.5)
        self.assertEqual(CONFIG["intervention"]["modes"]["gradnorm"]["shared_layer"],
                         ["weight_ih_l1", "weight_hh_l1", "bias_ih_l1", "bias_hh_l1"])


class BalancerTests(unittest.TestCase):
    def _batch(self):
        with cpu_seed_scope(3):
            model = LSTM(formulation="M1", block="fastStorage", tasks=RESOURCES, hidden_size=64)
            inputs = torch.randn(32, 18, 4)
            targets = torch.randn(32, 4, len(CONFIG["blocks"]["fastStorage"]["horizons"]))
            targets[:, 3] *= 5  # one task with a much larger loss
        return model, inputs, targets

    def test_gradnorm_weights_stay_positive_sum_to_four_and_receive_gradient(self):
        model, inputs, targets = self._batch()
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        balancer = GradNormBalancer(model, RESOURCES)
        history = []
        for _ in range(25):
            optimizer.zero_grad(set_to_none=True)
            losses = task_mse(model(inputs), targets)
            balancer.backward(model, losses)
            self.assertTrue(all(p.grad is not None for p in model.encoder.parameters()))
            optimizer.step()
            balancer.after_step(losses)
            weights = balancer.effective_weights()
            history.append(weights)
            self.assertTrue(all(w > 0 for w in weights))
            self.assertAlmostEqual(math.fsum(weights), 4.0, places=5)
        self.assertNotEqual(history[-1], [1.0] * 4, "the GradNorm loss must reach the task weights")
        evidence = balancer.evidence()
        self.assertEqual(len(evidence["initial_task_losses"]), 4)
        self.assertEqual(evidence["weight_floor_hits"], 0)

    def test_gradnorm_model_gradient_is_the_weighted_task_sum(self):
        model, inputs, targets = self._batch()
        model.eval()  # no dropout, so both forward passes are the same function
        balancer = GradNormBalancer(model, RESOURCES)
        with torch.no_grad():
            balancer.weights.copy_(torch.tensor([0.5, 1.5, 1.0, 1.0]))
        losses = task_mse(model(inputs), targets)
        balancer.backward(model, losses)
        observed = {name: p.grad.clone() for name, p in model.named_parameters()}
        model.zero_grad(set_to_none=True)
        (torch.tensor([0.5, 1.5, 1.0, 1.0]) * task_mse(model(inputs), targets)).sum().backward()
        for name, parameter in model.named_parameters():
            torch.testing.assert_close(observed[name], parameter.grad, rtol=1e-5, atol=1e-7)

    def test_gradnorm_floor_keeps_weights_positive(self):
        model, inputs, targets = self._batch()
        balancer = GradNormBalancer(model, RESOURCES)
        with torch.no_grad():
            balancer.weights.copy_(torch.tensor([-0.5, 1.5, 1.5, 1.5]))
        losses = task_mse(model(inputs), targets)
        balancer.backward(model, losses)
        balancer.after_step(losses)
        self.assertGreater(min(balancer.effective_weights()), 0)
        self.assertEqual(balancer.floor_hits, 1)
        self.assertAlmostEqual(math.fsum(balancer.effective_weights()), 4.0, places=5)

    def test_uncertainty_log_variances_receive_gradient(self):
        model, inputs, targets = self._batch()
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        balancer = UncertaintyBalancer(model, RESOURCES)
        for _ in range(5):
            optimizer.zero_grad(set_to_none=True)
            losses = task_mse(model(inputs), targets)
            weighted = balancer.backward(model, losses)
            expected = (torch.exp(-balancer.log_variance) * losses + balancer.log_variance).sum()
            self.assertAlmostEqual(float(weighted), float(expected.detach()), places=5)
            optimizer.step()
            balancer.after_step(losses)
        weights = balancer.effective_weights()
        self.assertNotEqual(weights, [1.0] * 4)
        self.assertEqual(min(range(4), key=weights.__getitem__), 3, "the high-loss task gets the lowest weight")


class TrainingModeTests(unittest.TestCase):
    def test_modes_are_bound_to_their_identities(self):
        with scratch_engine(seal()) as engine:
            unit = a1("gradnorm")
            for mode in ("equal_loss", "uncertainty"):
                with self.subTest(mode=mode), self.assertRaises(ValueError):
                    engine.fit_inner(unit, partition(unit)[0], mode=mode)
            with self.assertRaises(ValueError):
                engine.fit_inner(identity("M1"), partition(identity("M1"))[0], mode="gradnorm")

    def test_selection_uses_the_unweighted_validation_mse_and_final_reuses_the_mode(self):
        for mode in ("gradnorm", "uncertainty"):
            with self.subTest(mode=mode), scratch_engine(seal()) as engine:
                inner_result, final_result = fit_pair(engine, a1(mode))
                inner = inner_result.evidence
                self.assertEqual(inner["loss_mode"], mode)
                for row in inner["epochs"]:
                    values = [row["validation_task_mse"][task] for task in RESOURCES]
                    self.assertEqual(row["validation_joint_mse"], math.fsum(values) / 4)
                    self.assertEqual(set(row["loss_weights"]), set(RESOURCES))
                    self.assertIn("train_weighted_loss", row)
                joint = [row["validation_joint_mse"] for row in inner["epochs"]]
                self.assertEqual(inner["selection"]["joint_epoch"], joint.index(min(joint)) + 1)
                final = final_result.evidence
                self.assertEqual(final["selection"], inner["selection"])
                self.assertEqual(len(final["epochs"]), inner["selection"]["final_epoch"])
                self.assertEqual(set(final["diagnostic_slots"]), {"epoch0", "mid", "final"})
                state = torch.load(io.BytesIO(final_result.resume_state), weights_only=True)
                self.assertEqual(state["balancer"]["mode"], mode)

    def test_weighted_runs_are_deterministic_and_share_the_equal_loss_batch_order(self):
        outcomes = []
        for _ in range(2):
            with scratch_engine(seal()) as engine:
                evidence = engine.fit_inner(a1("gradnorm"), partition(a1("gradnorm"))[0], mode="gradnorm").evidence
                outcomes.append((evidence["terminal_model_sha256"], evidence["epochs"], evidence["balancer"]))
        self.assertEqual(outcomes[0], outcomes[1])
        with scratch_engine(seal()) as engine:
            core = engine.fit_inner(identity("M1"), partition(identity("M1"))[0]).evidence
            weighted = engine.fit_inner(a1("uncertainty"), partition(a1("uncertainty"))[0], mode="uncertainty").evidence
        self.assertEqual(core["initial_model_sha256"], weighted["initial_model_sha256"])
        self.assertEqual(core["epochs"][0]["batch_order_sha256"], weighted["epochs"][0]["batch_order_sha256"])
        self.assertNotIn("loss_mode", core)
        self.assertNotIn("loss_weights", core["epochs"][0])


@contextmanager
def v04_scratch_engine():
    """The v0.4 engine on a scratch journal outside the v0.4 package: nothing under v0.4 is written."""
    from fgcs_strengthening_v04.src.provenance import Journal
    from fgcs_strengthening_v04.src.training import TrainingEngine, training_fingerprints

    with tempfile.TemporaryDirectory(dir=HOME) as scratch, patch(
            "fgcs_strengthening_v04.src.provenance.HOME", Path(scratch)):
        yield TrainingEngine(Journal(training_fingerprints()))


@patch("fgcs_strengthening_v04a2.src.residual.PARAMETERISATION", "level")
class EqualLossIdentityTests(unittest.TestCase):
    """The level, equal-loss path is unchanged: this engine and the tagged v0.4 engine train identical models."""

    KEYS = ("initial_model_sha256", "terminal_model_sha256", "epochs", "selection", "parameter_count", "checkpoints")

    def test_synthetic_core_fits_match_the_v04_engine(self):
        from fgcs_strengthening_v04.tests import training_fixtures as v04_fixtures

        for formulation in ("M1", "S2"):
            with self.subTest(formulation=formulation):
                with scratch_engine(seal()) as engine:
                    inner = identity(formulation)
                    a1_inner = engine.fit_inner(inner, partition(inner)[0]).evidence
                    final = replace(inner, phase="final")
                    a1_final = engine.fit_final(final, partition(final)[0]).evidence
                with v04_scratch_engine() as engine:
                    inner = v04_fixtures.identity(formulation)
                    v04_inner = engine.fit_inner(inner, v04_fixtures.partition(inner)[0]).evidence
                    final = replace(inner, phase="final")
                    v04_final = engine.fit_final(final, v04_fixtures.partition(final)[0]).evidence
                for key in self.KEYS:
                    if key in a1_inner or key in v04_inner:
                        self.assertEqual(a1_inner.get(key), v04_inner.get(key), key)
                    self.assertEqual(a1_final.get(key) is None, v04_final.get(key) is None, key)
                for key in ("terminal_model_sha256", "epochs", "selection"):
                    self.assertEqual(a1_final[key], v04_final[key], key)

    @unittest.skipUnless((V04_RUNTIME / "outcomes").is_dir(), "closed v0.4 journal not present")
    def test_real_core_fit_reproduces_the_v04_journal(self):
        """Golden check: one real v0.4 LSTM M1 inner fit, retrained by A1, equals its journalled outcome."""
        from fgcs_strengthening_v04.src.identity import ScientificIdentity as V04Identity
        from fgcs_strengthening_v04a2.src.data_adapters import adapter_for

        unit = ScientificIdentity("fastStorage", "697", 1, 0, "inner", "core", "M1", RESOURCES, "all", 64, "baseline")
        reference = V04Identity(*(getattr(unit, name) for name in (
            "block", "entity", "fold", "seed", "phase", "arm", "formulation", "tasks", "input_scope", "hidden_size",
            "variant")))
        expected = json.loads((V04_RUNTIME / "outcomes" / f"{reference.digest}.json").read_text())["evidence"]
        with scratch_engine(seal()) as engine:
            observed = engine.fit_inner(unit, adapter_for("fastStorage").prepare("697", 1, "inner")).evidence
        for key in ("context", "support_sha256", "split_hashes", "scaler_sha256", "initial_model_sha256",
                    "terminal_model_sha256", "epochs", "selection"):
            self.assertEqual(observed[key], expected[key], key)


class InterventionDiagnosticTests(unittest.TestCase):
    def test_d4_reads_the_intervention_parent_with_the_v04_draws(self):
        with scratch_engine(seal()) as trainer:
            unit = a1("gradnorm")
            with patch("fgcs_strengthening_v04a2.src.training._evaluate", side_effect=[[2., 2., 2., 2.]] * 8):
                _, result = fit_pair(trainer, unit)
            final = replace(unit, phase="final")
            persist_resume_state(trainer.journal, final, result)
            live, optimizer, generator = restore_live_state(trainer.journal, final)
            diag = replace(final, arm="diagnostic", variant="gradnorm:final")
            prepared = partition(final)[0]
            record = DiagnosticEngine(trainer.journal).run(diag, prepared, live, optimizer, generator)
            parent, _ = trainer.journal.completed_evidence(final)
            joint = parent["selection"]["joint_epoch"]
            self.assertEqual(record["slot"], "final")
            self.assertTrue(record["is_primary"])
            self.assertEqual(record["loss_mode"], "gradnorm")
            self.assertEqual(record["loss_weights"], parent["epochs"][joint - 1]["loss_weights"])
            self.assertEqual(record["final_identity"], final.payload())
            # Same draw keys as the v0.4 M1 final slot of this group: paired gradient batches.
            core_slot = replace(identity("M1", phase="final"), arm="diagnostic", variant="final")
            from fgcs_strengthening_v04a2.src.diagnostics.batches import build_batch_pairs
            ids = prepared.training().origin_ids
            self.assertEqual([p.payload() for p in build_batch_pairs(diag, ids)],
                             [p.payload() for p in build_batch_pairs(core_slot, ids)])


class DecisionTests(unittest.TestCase):
    """The frozen section 5 rule on synthetic, fully specified inputs."""

    def _inputs(self, gn, uw, s2, gn_ratio, uw_ratio):
        from fgcs_strengthening_v04a2.analyse_intervention import CELLS
        from fgcs_strengthening_v04a2.src.analysis.grid import BLOCKS, COHORT, FOLDS, HORIZONS, SEEDS, MAERow

        factor = {"M1": 1.0, "S1": 1.05, "S2": s2, "M1-GN": gn, "M1-UW": uw}
        rows = []
        for block in BLOCKS:
            for e, entity in enumerate(COHORT[block]):
                for resource in RESOURCES:
                    for fold in FOLDS:
                        for horizon in HORIZONS[block]:
                            for seed in SEEDS:
                                base = 1.0 + e + 0.01 * horizon
                                rows += [MAERow("LSTM", cell, block, entity, resource, fold, horizon, seed,
                                                base * factor[cell]) for cell in CELLS]
        d4, d7 = {}, {}
        for cell, ratio in (("M1", 10.0), ("M1-GN", gn_ratio), ("M1-UW", uw_ratio)):
            d4[cell] = {(block, entity, fold, seed): {"K": -0.03, "norm_ratio": 10.0, "effective_norm_ratio": ratio,
                                                      "cosines": {}}
                        for block in BLOCKS for entity in COHORT[block] for fold in FOLDS for seed in SEEDS}
            row = {"train_task_mse": dict(zip(RESOURCES, (0.1, 0.2, 0.3, 0.4)))}
            if cell != "M1":
                row["loss_weights"] = dict(zip(RESOURCES, (1.6, 1.2, 0.8, 0.4)))
            d7[cell] = {(block, entity, fold, seed): [row] for block in BLOCKS for entity in COHORT[block]
                        for fold in FOLDS for seed in SEEDS}
        return rows, d4, d7

    def test_verdicts(self):
        from fgcs_strengthening_v04a2.analyse_intervention import analyse
        from fgcs_strengthening_v04a2.src.analysis.bootstrap import Draws

        draws = Draws(replicates=50)
        rows, d4, d7 = self._inputs(gn=0.9, uw=1.1, s2=0.95, gn_ratio=3.0, uw_ratio=2.0)
        decision = analyse(rows=rows, d4=d4, d7=d7, draws=draws)["decision"]
        self.assertEqual(decision["gradnorm"]["verdict"], "penalty removed")
        self.assertEqual(decision["gradnorm"]["better_than_equal_loss"], 8)
        self.assertEqual(decision["uncertainty"]["verdict"], "adverse")
        rows, d4, d7 = self._inputs(gn=0.97, uw=0.97, s2=0.95, gn_ratio=3.0, uw_ratio=12.0)
        results = analyse(rows=rows, d4=d4, d7=d7, draws=draws)
        self.assertEqual(results["decision"]["gradnorm"]["verdict"], "supported")
        self.assertEqual(results["decision"]["uncertainty"]["verdict"], "not supported")  # manipulation check failed
        self.assertFalse(results["decision"]["uncertainty"]["manipulation_check"]["passed"])
        self.assertEqual(results["missing_units"], [])
        weighted = next(row for row in results["manipulation"] if row["cell"] == "M1-GN")["mean_loss_share_at_E"]
        self.assertAlmostEqual(weighted["weighted"]["CPU"], 0.16 / 0.8)
        self.assertAlmostEqual(weighted["unweighted"]["CPU"], 0.1)

    def test_a_failed_unit_is_missing_for_every_cell(self):
        from fgcs_strengthening_v04a2.analyse_intervention import analyse
        from fgcs_strengthening_v04a2.src.analysis.bootstrap import Draws
        from fgcs_strengthening_v04a2.src.analysis.grid import MAERow

        rows, d4, d7 = self._inputs(gn=0.9, uw=1.1, s2=0.95, gn_ratio=3.0, uw_ratio=2.0)
        target = rows[0]
        rows = [MAERow(r.backbone, r.cell, r.block, r.entity, r.resource, r.fold, r.horizon, r.seed, None, "failed")
                if (r.cell, r.block, r.entity, r.resource, r.fold, r.seed) == ("M1-GN", target.block, target.entity,
                                                                              target.resource, target.fold, target.seed)
                else r for r in rows]
        results = analyse(rows=rows, d4=d4, d7=d7, draws=Draws(replicates=20))
        self.assertEqual(results["missing_units"], [{"block": target.block, "entity": target.entity,
                                                     "resource": target.resource, "fold": target.fold,
                                                     "seed": target.seed}])
        # The unit is dropped from every cell, so the reference contrast M1:S2 is affected too; the other
        # seeds keep the seed-averaged cell, so matched cells stay complete.
        horizons = len(CONFIG["blocks"][target.block]["horizons"])
        for contrast in ("M1:S2", "M1-GN:M1"):
            cell = next(row for row in results["endpoints"] if row["contrast"] == contrast
                        and (row["block"], row["resource"]) == (target.block, target.resource))
            self.assertEqual(cell["matched_cells"], 10 * 5 * horizons)
            self.assertEqual(cell["counts"]["seeds"][1], 3)


if __name__ == "__main__":
    unittest.main()
