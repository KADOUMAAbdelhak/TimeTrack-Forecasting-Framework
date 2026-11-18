"""P5 diagnostics, journal collection and the historical reader, on generated inputs only."""

import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np

from fgcs_strengthening_v04a1.src.analysis import SOURCES
from fgcs_strengthening_v04a1.src.analysis.bootstrap import Draws
from fgcs_strengthening_v04a1.src.analysis.collect import d4_slots, d7_fits, label, mae_rows
from fgcs_strengthening_v04a1.src.analysis.grid import COHORT, FOLDS, HORIZONS, Grid, LATTICE, lattice_cell
from fgcs_strengthening_v04a1.src.analysis.historical import HistoricalReader, PartitionMetadata
from fgcs_strengthening_v04a1.src.analysis.mechanism import (d1_fold_summary, d1_target_dependence, d2_dependence,
                                                           d3_rows, d4_slot, d6_rows, d7_rows, inner_training_series,
                                                           lagged_cross_correlation, loss_shares)
from fgcs_strengthening_v04a1.src.identity import HOME, RESOURCES, ROOT, ScientificIdentity
from fgcs_strengthening_v04a1.src.orchestrator import execution_sources
from fgcs_strengthening_v04a1.src.provenance import ProvenanceError, sha256_file
from fgcs_strengthening_v04a1.src.transfer.estimands import NativeMAECell
from fgcs_strengthening_v04a1.tests.analysis_fixtures import synthetic_rows


class D1Tests(unittest.TestCase):
    def test_lagged_correlation_finds_a_lead_and_respects_segments(self):
        generator = np.random.default_rng(0)
        n = 400
        values = generator.normal(size=(n, 4))
        values[3:, 2] = values[:-3, 0]  # CPU leads MEMORY by three steps
        rows = np.arange(n)
        segments = np.zeros(n, dtype=int)
        corr = lagged_cross_correlation(values, rows, segments)
        self.assertAlmostEqual(corr[0, 2, 2], 1.)
        self.assertLess(abs(corr[0, 2, 0]), 0.2)
        self.assertTrue(np.isnan(corr[1, 1]).all())
        summary = d1_fold_summary(corr)
        self.assertAlmostEqual(summary[0, 2], 1.)
        # A new segment at every row leaves no lagged pair inside a segment.
        self.assertTrue(np.isnan(lagged_cross_correlation(values, rows, np.arange(n))).all())
        # Gaps in the inner-training origins are never bridged.
        kept = rows[rows % 2 == 0]
        sparse = lagged_cross_correlation(values[kept], kept, segments[kept])
        self.assertTrue(np.isnan(sparse[:, :, 0]).all())
        self.assertAlmostEqual(sparse[0, 2, 1], corr[0, 2, 1], delta=0.15)

    def test_target_dependence_and_inner_only_series(self):
        summaries = np.zeros((5, 4, 4))
        summaries[:, 0, 2], summaries[:, 1, 2], summaries[:, 3, 2] = 0.9, 0.3, 0.
        np.testing.assert_allclose(d1_target_dependence(summaries)[2], 0.4)
        frame = SimpleNamespace(segment_id=SimpleNamespace(to_numpy=lambda dtype: np.array([0, 0, 1, 1, 1])))
        windows = SimpleNamespace(inputs=np.arange(3 * 2 * 4, dtype=float).reshape(3, 2, 4))
        partition = SimpleNamespace(phase="inner", training=lambda: windows, _train_origins=np.array([1, 2, 4]),
                                    _frame=frame)
        values, rows, segments = inner_training_series(partition)
        np.testing.assert_array_equal(values, windows.inputs[:, -1])
        np.testing.assert_array_equal(segments, [0, 1, 1])
        with self.assertRaisesRegex(ValueError, "inner-training"):
            inner_training_series(SimpleNamespace(phase="final"))


class DependenceTests(unittest.TestCase):
    def test_d2_gain_and_d3_association_direction(self):
        shape = {block: (10, 4, 5, len(HORIZONS[block])) for block in COHORT}
        scale = np.linspace(0.5, 0.95, 10)[:, None, None, None]
        ridge = {block: {"AR": np.ones(shape[block]), "ARX": np.ones(shape[block]) * scale} for block in COHORT}
        dependence = d2_dependence(ridge)
        np.testing.assert_allclose(dependence["Rnd"][:, 0], 100 * (1 - np.linspace(0.5, 0.95, 10)))
        effects = {block: dict(zip(COHORT[block], 1 - np.linspace(0.5, 0.95, 10))) for block in COHORT}
        contrasts = [{"backbone": "LSTM", "block": block, "resource": resource, "contrast": contrast,
                      "entity_log_effect": {e: float(v) for e, v in effects[block].items()}}
                     for block in COHORT for resource in RESOURCES for contrast in ("S2:S1", "M1:S2")]
        rows = d3_rows(Draws(replicates=200), {"D-2": dependence}, contrasts)
        self.assertEqual(len(rows), 16)
        self.assertTrue(all(row["rho"] == 1. for row in rows))
        dependence["Rnd"][0, 0] = np.nan
        partial = [r for r in d3_rows(Draws(replicates=50), {"D-2": dependence}, contrasts)
                   if (r["block"], r["resource"]) == ("Rnd", "CPU")]
        self.assertEqual({r["entities"] for r in partial}, {9})


def pair(norm_a, norm_b, cosines):
    cross = [{"left_task": a, "right_task": b, "cosine": c} for (a, b), c in
             zip([(a, b) for i, a in enumerate(RESOURCES) for b in RESOURCES[i + 1:]], cosines)]
    return {"cross_task": cross, "norms": {"A": dict(zip(RESOURCES, norm_a)), "B": dict(zip(RESOURCES, norm_b))}}


class GradientAndLossTests(unittest.TestCase):
    def test_d4_slot_summary(self):
        pairs = [pair([1, 2, 4, 1], [1, 1, 1, 1], [0.5, -0.5, None, 0, 0, 0])] * 7 + \
                [pair([1, 0, 1, 1], [1, 1, 1, 2], [0.1, -0.5, None, 0, 0, 0])]
        slot = d4_slot({"pairs": pairs, "summary": {"K": 0.25}})
        self.assertEqual(slot["K"], 0.25)
        self.assertAlmostEqual(slot["cosines"]["CPU|THROUGHPUT"], (0.5 * 7 + 0.1) / 8)
        self.assertIsNone(slot["cosines"]["CPU|DISK_WRITE"])
        self.assertAlmostEqual(slot["norm_ratio"], (4 * 7 + 1 * 7 + 2) / 15)

    def test_d7_shares_sum_to_one_and_use_the_final_epoch(self):
        epochs = [{"train_task_mse": dict(zip(RESOURCES, (1., 1., 1., 1.)))},
                  {"train_task_mse": dict(zip(RESOURCES, (4., 2., 1., 1.)))}]
        shares = loss_shares(epochs)
        self.assertAlmostEqual(sum(shares[1].values()), 1.)
        rows = d7_rows({("Rnd", "99", 1, 0): epochs, ("Rnd", "99", 1, 1): epochs[:1], ("Rnd", "99", 2, 0): None})
        cpu = [r for r in rows if (r["block"], r["resource"]) == ("Rnd", "CPU")][0]
        self.assertEqual(cpu["fits"], 2)
        self.assertAlmostEqual(cpu["mean_share_at_E"], (0.5 + 0.25) / 2)
        self.assertEqual(cpu["per_epoch"][1], {"epoch": 2, "mean_share": 0.5, "fits": 1})


class AffinityTests(unittest.TestCase):
    def test_signs_follow_the_protocol_definitions(self):
        factors = {("LSTM", "S2"): 1.0, ("LSTM", "M1"): 1.0}
        factors.update({("LSTM", lattice_cell(("CPU", "MEMORY"))): 0.9})  # pairing CPU with MEMORY helps
        without_memory = lattice_cell(task for task in RESOURCES if task != "MEMORY")
        factors[("LSTM", without_memory)] = 1.2  # dropping MEMORY hurts the retained targets
        cells = [("LSTM", c) for c in ("S1", "S2", "M0", "M1", *LATTICE)]
        grid = Grid(synthetic_rows(factors, cells=cells), cells=cells)
        rows = {(r["estimand"], r["block"], r["target"], r["source"]): r for r in d6_rows(grid)}
        self.assertEqual(len(rows), 48)
        self.assertAlmostEqual(rows["F", "Rnd", "CPU", "MEMORY"]["mean"], -math.log(0.9), delta=0.01)
        self.assertEqual(rows["F", "Rnd", "CPU", "MEMORY"]["positive_entities"], 10)
        self.assertAlmostEqual(rows["Q", "Rnd", "CPU", "MEMORY"]["mean"], math.log(1.2), delta=0.01)
        self.assertAlmostEqual(rows["F", "Rnd", "CPU", "THROUGHPUT"]["mean"], 0, delta=0.01)


class FakeJournal:
    def __init__(self, root, outcomes):
        self.root, self.outcomes = Path(root), outcomes

    def _path(self, *parts):
        return self.root.joinpath(*parts)

    def terminal_evidence(self, identity, *, evaluation=False):
        if (identity, evaluation) not in self.outcomes:
            raise ProvenanceError("No completed outcome")
        status, evidence = self.outcomes[identity, evaluation]
        return status, evidence, "0" * 64

    def completed_evidence(self, identity, *, evaluation=False):
        status, evidence, digest = self.terminal_evidence(identity, evaluation=evaluation)
        if status != "complete":
            raise ProvenanceError("Outcome is not complete")
        return evidence, digest


def close(root, *gates):
    phases = {"fits": ["certify", "canary", "inner", "final", "diagnostics"], "evaluation": ["evaluation"]}
    for gate in gates:
        path = Path(root, "orchestrator", "gates", f"{gate}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"gate": gate, "phases": phases[gate]}))


class CollectTests(unittest.TestCase):
    def setUp(self):
        self.ids = {name: ScientificIdentity("Rnd", "99", 1, 0, "final", arm, model, tasks, scope, width, variant)
                    for name, arm, model, tasks, scope, width, variant in (
                        ("s1", "core", "S1", ("CPU",), "own", 64, "baseline"),
                        ("m1", "core", "M1", RESOURCES, "all", 64, "baseline"),
                        ("pair", "pairwise", "M1", ("CPU", "MEMORY"), "all", 64, "baseline"),
                        ("modern", "modern", "PatchTST", RESOURCES, "all", None, "shared"))}

    def test_labels(self):
        self.assertEqual(label(self.ids["s1"]), ("LSTM", "S1"))
        self.assertEqual(label(self.ids["pair"]), ("LSTM", "M1/CPU+MEMORY"))
        self.assertEqual(label(self.ids["modern"]), ("PatchTST", "M1"))

    def test_outcomes_need_the_closed_gates_and_failures_become_explicit_rows(self):
        s1, m1, modern = self.ids["s1"], self.ids["m1"], self.ids["modern"]
        meta = (9, "a" * 64, "b" * 64, "c" * 64)

        class Evaluator:
            def __init__(self, metadata):
                self.metadata = metadata

            def completed_cells(self, identity):
                if identity != s1:
                    raise ProvenanceError("No completed evaluation")
                return tuple(NativeMAECell(identity, "CPU", h, 1. + h, *self.metadata) for h in HORIZONS["Rnd"])

        with tempfile.TemporaryDirectory() as root:
            journal = FakeJournal(root, {(s1, False): ("complete", {}), (s1, True): ("complete", {}),
                                         (m1, False): ("failed", {}),
                                         (modern, False): ("complete", {}), (modern, True): ("complete", {})})
            with self.assertRaisesRegex(ProvenanceError, "fits gate"):
                mae_rows(journal, [s1], evaluator=Evaluator(meta))
            close(root, "fits")
            with self.assertRaisesRegex(ProvenanceError, "evaluation gate"):
                mae_rows(journal, [s1], evaluator=Evaluator(meta))
            close(root, "evaluation")
            rows = mae_rows(journal, [s1, m1], evaluator=Evaluator(meta))
            self.assertEqual(len(rows), 5 + 4 * 5)
            self.assertEqual({r.status for r in rows if r.cell == "M1"}, {"failed"})
            self.assertEqual([r.mae for r in rows if r.cell == "S1"], [2., 3., 5., 10., 19.])
            with self.assertRaises(ProvenanceError):  # both outcomes complete but unreadable: never "missing"
                mae_rows(journal, [modern], evaluator=Evaluator(meta))

    def test_d4_and_d7_readers(self):
        diagnostic = ScientificIdentity("Rnd", "99", 1, 0, "final", "diagnostic", "M1", RESOURCES, "all", 64, "final")
        evidence = {"pairs": [pair([1, 1, 1, 1], [1, 1, 1, 1], [0.] * 6)] * 8, "summary": {"K": 0.}}
        m1 = self.ids["m1"]
        with tempfile.TemporaryDirectory() as root:
            journal = FakeJournal(root, {(diagnostic, False): ("complete", evidence),
                                         (m1, False): ("complete", {"epochs": [{"train_task_mse": {}}]})})
            with self.assertRaises(ProvenanceError):
                d4_slots(journal, [diagnostic])
            close(root, "fits")
            self.assertEqual(d4_slots(journal, [diagnostic])["M1", "Rnd", "99", 1, 0]["K"], 0.)
            self.assertEqual(d7_fits(journal, [m1, self.ids["s1"]]), {("Rnd", "99", 1, 0): [{"train_task_mse": {}}]})


class HistoricalTests(unittest.TestCase):
    def test_ridge_rows_are_bound_to_the_frozen_support_and_context(self):
        import pandas as pd

        def metadata(block, entity, fold):
            return PartitionMetadata(block, entity, fold, 9, "h" * 64, 100)

        records = [{"block": block, "entity": entity, "fold": fold, "formulation": name, "L": 9, "lead": lead,
                    "mae": 1. if name == "AR" else 0.8, "n": 100, "resource": resource}
                   for block in COHORT for entity in COHORT[block] for fold in FOLDS
                   for name in ("AR", "ARX") for lead in HORIZONS[block] for resource in RESOURCES]
        records.append({**records[0], "block": "TimeTrack", "entity": "machine01"})  # outside the cohort
        with tempfile.TemporaryDirectory(dir=HOME) as scratch:
            def reader(rows):
                path = Path(scratch, f"ridge{len(rows)}-{rows[0]['L']}-{rows[0]['n']}.parquet")
                pd.DataFrame(rows).to_parquet(path)
                manifest = Path(scratch, "manifest.json")
                manifest.write_text(json.dumps({"tables": [{"kind": "ridge", "block": None,
                                                            "path": path.relative_to(ROOT).as_posix(),
                                                            "sha256": sha256_file(path)}]}))
                return HistoricalReader(metadata, manifest=manifest)

            ridge = reader(records).ridge()
            self.assertTrue((ridge["Rnd"]["ARX"] == 0.8).all())
            with self.assertRaisesRegex(ProvenanceError, "frozen H64-M1 context"):
                reader([{**r, "L": 4} for r in records]).ridge()
            with self.assertRaisesRegex(ProvenanceError, "outer-test support"):
                reader([{**r, "n": 99} for r in records]).ridge()
            with self.assertRaisesRegex(ProvenanceError, "cover"):
                reader(records[1:]).ridge()


class SealTests(unittest.TestCase):
    def test_analysis_sources_join_the_execution_seal(self):
        self.assertTrue(set(SOURCES) <= set(execution_sources()))
        self.assertTrue(all((ROOT / source).is_file() for source in SOURCES))


if __name__ == "__main__":
    unittest.main()
