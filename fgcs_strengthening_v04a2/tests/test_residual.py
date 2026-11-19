"""Amendment A2: the change parameterisation (last value plus learned change), its nesting of persistence,
the unchanged level path, anchored structural certificates and the frozen decision rule."""

import json
import math
import unittest
from unittest.mock import patch

import numpy as np
import torch
from torch import nn

from fgcs_strengthening_v04a2.src.identity import RESOURCES, ROOT, ScientificIdentity, read_config
from fgcs_strengthening_v04a2.src.models.lstm import LSTM
from fgcs_strengthening_v04a2.src.models.registry import REGISTRY
from fgcs_strengthening_v04a2.src.modern.structure import validate_family_structure
from fgcs_strengthening_v04a2.src.residual import PARAMETERISATION, anchor, anchor_indices, last_values
from fgcs_strengthening_v04a2.src.training import cpu_seed_scope
from fgcs_strengthening_v04a2.tests.training_fixtures import identity, partition, scratch_engine

CONFIG = read_config()
V04_RUNTIME = ROOT / "fgcs_strengthening_v04" / "runtime"
HORIZONS = len(CONFIG["blocks"]["fastStorage"]["horizons"])


class Zero(nn.Module):
    def __init__(self, tasks):
        super().__init__()
        self.tasks = len(tasks)

    def forward(self, windows):
        return torch.zeros(windows.shape[0], self.tasks, HORIZONS)


class AnchorTests(unittest.TestCase):
    def test_configuration_fixes_the_change_parameterisation(self):
        self.assertEqual(PARAMETERISATION, "change")
        self.assertEqual(CONFIG["residual"]["resources"], list(RESOURCES))
        self.assertEqual(CONFIG["residual"]["backbones"], ["LSTM", "DLinear", "PatchTST", "iTransformer"])

    def test_anchor_channel_per_input_layout(self):
        self.assertEqual(anchor_indices(("MEMORY",), 1), (0,))
        self.assertEqual(anchor_indices(("MEMORY",), 4), (2,))
        self.assertEqual(anchor_indices(RESOURCES, 4), (0, 1, 2, 3))
        for tasks, channels in ((RESOURCES, 1), (("CPU",), 2)):
            with self.subTest(tasks=tasks, channels=channels), self.assertRaises(ValueError):
                anchor_indices(tasks, channels)

    def test_anchor_adds_only_the_last_input_row_of_each_tasks_channel(self):
        """No leakage: the added term depends on the last input row only, never on targets or earlier rows."""
        generator = torch.Generator().manual_seed(4)
        for tasks, channels in ((("THROUGHPUT",), 1), (("THROUGHPUT",), 4), (RESOURCES, 4)):
            with self.subTest(tasks=tasks, channels=channels):
                model = anchor(Zero(tasks), tasks)
                windows = torch.randn(3, 9, channels, generator=generator)
                expected = windows[:, -1, list(anchor_indices(tasks, channels))].unsqueeze(-1).expand(-1, -1, HORIZONS)
                torch.testing.assert_close(model(windows), expected)
                earlier = windows.clone()
                earlier[:, :-1] += 5.0
                torch.testing.assert_close(model(earlier), model(windows))
                torch.testing.assert_close(last_values(windows, tasks), expected[..., 0])

    def test_every_backbone_cell_is_anchored_without_changing_its_state_dict(self):
        windows = torch.randn(2, 9, 4)
        cells = [("S1", ("DISK_WRITE",), "own"), ("S2", ("DISK_WRITE",), "all"), ("M0", RESOURCES, "own"),
                 ("M1", RESOURCES, "all")]
        for formulation, tasks, scope in cells:
            with self.subTest(backbone="LSTM", cell=formulation), cpu_seed_scope(0):
                base = LSTM(formulation=formulation, block="fastStorage", tasks=tasks, hidden_size=64).eval()
                anchored = anchor(LSTM(formulation=formulation, block="fastStorage", tasks=tasks, hidden_size=64),
                                  tasks).eval()
                anchored.load_state_dict(base.state_dict(), strict=True)
                self.assertEqual(list(base.state_dict()), list(anchored.state_dict()))
                torch.testing.assert_close(anchored(windows) - base(windows),
                                           last_values(windows, tasks).unsqueeze(-1).expand(-1, -1, HORIZONS))
        for family, spec in REGISTRY.items():
            for scope in spec.scopes:
                for tasks in (("CPU",), RESOURCES):
                    channels = 4 if scope == "all" else len(tasks)
                    with self.subTest(backbone=family, scope=scope, tasks=len(tasks)), cpu_seed_scope(0):
                        try:
                            base = spec.build(9, tasks, scope).eval()
                        except ValueError:
                            continue  # undefined cell (e.g. iTransformer own scope)
                        anchored = anchor(spec.build(9, tasks, scope), tasks).eval()
                        anchored.load_state_dict(base.state_dict(), strict=True)
                        x = torch.randn(2, 9, channels)
                        torch.testing.assert_close(anchored(x) - base(x),
                                                   last_values(x, tasks).unsqueeze(-1).expand(-1, -1, HORIZONS))

    def test_level_is_a_no_op_and_double_anchoring_is_refused(self):
        model = Zero(("CPU",))
        self.assertIs(anchor(model, ("CPU",), parameterisation="level"), model)
        self.assertFalse(hasattr(model, "a2_anchored"))
        anchor(model, ("CPU",))
        with self.assertRaises(ValueError):
            anchor(model, ("CPU",))

    def test_anchored_structural_certificates_pass_for_every_modern_family(self):
        for family in REGISTRY:
            with self.subTest(family=family):
                records = validate_family_structure(family)
                self.assertTrue(records)


class ChangeTrainingTests(unittest.TestCase):
    def test_change_parameterised_fits_are_deterministic_and_differ_from_level(self):
        outcomes = []
        for _ in range(2):
            with scratch_engine() as engine:
                outcomes.append(engine.fit_inner(identity("M1"), partition(identity("M1"))[0]).evidence)
        self.assertEqual(outcomes[0]["terminal_model_sha256"], outcomes[1]["terminal_model_sha256"])
        self.assertEqual(outcomes[0]["epochs"], outcomes[1]["epochs"])
        with patch("fgcs_strengthening_v04a2.src.residual.PARAMETERISATION", "level"), scratch_engine() as engine:
            level = engine.fit_inner(identity("M1"), partition(identity("M1"))[0]).evidence
        self.assertEqual(level["initial_model_sha256"], outcomes[0]["initial_model_sha256"])
        self.assertNotEqual(level["terminal_model_sha256"], outcomes[0]["terminal_model_sha256"])

    def test_identities_record_the_parameterisation(self):
        payload = identity("M1").payload()
        self.assertEqual((payload["schema_version"], payload["target_parameterisation"]), (2, "change"))


@unittest.skipUnless((V04_RUNTIME / "outcomes").is_dir(), "closed v0.4 journal and data not present")
class RealDataTests(unittest.TestCase):
    def test_zero_change_reproduces_v1_persistence_on_real_units(self):
        """With f = 0, the anchored native forecast is persistence: its MAE equals the frozen v1 persistence MAE."""
        from fgcs_strengthening_v04a2.src.analysis.grid import COHORT, FOLDS
        from fgcs_strengthening_v04a2.src.analysis.historical import HistoricalReader
        from fgcs_strengthening_v04a2.src.data_adapters import adapter_for

        persistence = HistoricalReader().persistence()
        for block in ("fastStorage", "Rnd"):
            adapter = adapter_for(block)
            entity = COHORT[block][0]
            for fold in (1, 5):
                part = adapter.prepare(entity, fold, "final")
                windows = part.outer_test()
                scaled = anchor(Zero(RESOURCES), RESOURCES)(torch.as_tensor(windows.inputs)).numpy()
                native = np.asarray(windows.native_targets, dtype=np.float64)
                for r, resource in enumerate(RESOURCES):
                    with self.subTest(block=block, fold=fold, resource=resource):
                        predicted, _, _ = part.inverse_target(scaled[:, r], resource)
                        mae = np.abs(np.asarray(predicted, dtype=np.float64) - native[:, r]).mean(axis=0)
                        reference = persistence[block][COHORT[block].index(entity), r, FOLDS.index(fold)]
                        np.testing.assert_allclose(mae, reference, rtol=1e-5)

    @patch("fgcs_strengthening_v04a2.src.residual.PARAMETERISATION", "level")
    def test_level_dlinear_fit_reproduces_the_v04_journal(self):
        """Golden check for the modern path: a level DLinear S1 inner fit equals its tier-2 journal record."""
        from fgcs_strengthening_v04.src.identity import ScientificIdentity as V04Identity
        from fgcs_strengthening_v04a2.src.data_adapters import adapter_for
        from fgcs_strengthening_v04a2.src.modern.runner import ModernRunner
        from fgcs_strengthening_v04a2.src.orchestrator import execution_fingerprints

        unit = ScientificIdentity("fastStorage", "697", 1, 0, "inner", "modern", "DLinear", ("CPU",), "own", None,
                                  "independent")
        reference = V04Identity(*(getattr(unit, name) for name in (
            "block", "entity", "fold", "seed", "phase", "arm", "formulation", "tasks", "input_scope", "hidden_size",
            "variant")))
        expected = json.loads((V04_RUNTIME / "outcomes" / f"{reference.digest}.json").read_text())["evidence"]
        with scratch_engine(execution_fingerprints()) as engine:
            runner = ModernRunner(engine.journal)
            runner.validate_family("DLinear")
            observed = runner.fit_inner(unit, adapter_for("fastStorage").prepare("697", 1, "inner")).evidence
        for key in ("context", "scaler_sha256", "initial_model_sha256", "terminal_model_sha256", "epochs", "selection"):
            self.assertEqual(observed[key], expected[key], key)


class DecisionTests(unittest.TestCase):
    """The frozen section 5 rule on fully specified synthetic inputs."""

    def _inputs(self, shared, persistence_factor):
        from fgcs_strengthening_v04a2.analyse_residual import CELLS
        from fgcs_strengthening_v04a2.src.analysis.grid import BLOCKS, COHORT, FOLDS, HORIZONS as H, SEEDS, MAERow

        def rows(level):
            out = []
            for backbone, cell in CELLS:
                factor = (shared if cell.startswith("M") else 1.0) * (1.1 if level else 1.0)
                for block in BLOCKS:
                    for e, entity in enumerate(COHORT[block]):
                        for resource in RESOURCES:
                            for fold in FOLDS:
                                for horizon in H[block]:
                                    for seed in SEEDS:
                                        out.append(MAERow(backbone, cell, block, entity, resource, fold, horizon,
                                                          seed, (1.0 + e + 0.01 * horizon) * factor))
            return out

        persistence = {}
        for block in BLOCKS:
            values = np.empty((len(COHORT[block]), len(RESOURCES), len(FOLDS), len(H[block])))
            for e in range(len(COHORT[block])):
                for r, resource in enumerate(RESOURCES):
                    base = (1.0 + e + 0.01 * np.asarray(H[block], dtype=float))
                    values[e, r] = base * (persistence_factor if resource in ("CPU", "THROUGHPUT") else 1.5)
            persistence[block] = values
        return rows(False), rows(True), persistence

    def _decide(self, shared, persistence_factor):
        from fgcs_strengthening_v04a2.analyse_residual import analyse
        from fgcs_strengthening_v04a2.src.analysis.bootstrap import Draws

        change, level, persistence = self._inputs(shared, persistence_factor)
        return analyse(change_rows=change, level_rows=level, persistence=persistence, draws=Draws(replicates=20))

    def test_cost_holds_when_models_beat_persistence(self):
        results = self._decide(shared=1.03, persistence_factor=1.05)
        decision = results["decision"]
        self.assertTrue(decision["precondition"]["met"])
        self.assertEqual(decision["precondition"]["positive"], 16)
        self.assertEqual((decision["sharing"]["verdict"], decision["sharing"]["median_ratio_above_one"]), ("holds", 32))
        self.assertEqual(decision["restricted"]["verdict"], "holds among persistence-beating models")
        self.assertEqual(decision["restricted"]["cells"], 32)
        self.assertEqual(decision["contrast_counts"]["M0:S1"], {"cells": 24, "median_ratio_above_one": 24})
        effect = results["parameterisation_effect"]
        self.assertTrue(all(math.isclose(row["median_ratio"], 1 / 1.1) for row in effect))
        self.assertEqual(results["missing_units"], [])

    def test_no_cost_and_failed_precondition(self):
        decision = self._decide(shared=0.98, persistence_factor=0.9)["decision"]
        self.assertFalse(decision["precondition"]["met"])
        self.assertEqual(decision["precondition"]["positive"], 0)
        self.assertEqual(decision["sharing"]["verdict"], "does not hold")
        self.assertEqual(decision["restricted"]["cells"], 16)  # memory and disk write only
        self.assertEqual(decision["restricted"]["verdict"], "does not hold among persistence-beating models")


if __name__ == "__main__":
    unittest.main()
